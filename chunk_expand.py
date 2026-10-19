"""Read-only expansion of indexed units/chunks back to source conversation windows."""

from __future__ import annotations

import contextlib
import hashlib
import json
import re
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from adapters.detect import TOOL_BY_FORMAT, detect_format, get_parser
from chroma_store import SUMMARIES
from ingest import _chunk_date, _path_is_excluded, load_processed, render_chunk
from provenance_binding import envelope_from_unit

DEFAULT_MAX_CHARS = 20_000

_EXPAND_JSONL_FORMATS = frozenset(
    {
        "jsonl_cursor",
        "jsonl_kiro_session",
        "jsonl_codex_history",
        "jsonl_codex_rollout",
        "jsonl_copilot_session",
        "jsonl_claude_session",
    }
)
_EXPAND_SQLITE_FORMATS = frozenset({"sqlite_crush", "sqlite_kiro"})

_NON_SESSION_TOOLS = frozenset({"inter-model", "repository-knowledge", "ryan"})
_NON_SESSION_FORMATS = frozenset(
    {"inter_model_doc", "repository_knowledge_v1", "kiro_steering"}
)

_REDACT_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\bsk-[A-Za-z0-9_-]{8,}\b"), "[REDACTED]"),
    (re.compile(r"\bghp_[A-Za-z0-9]{20,}\b"), "[REDACTED]"),
    (re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}\b"), "[REDACTED]"),
    (re.compile(r"\bAKIA[0-9A-Z]{16}\b"), "[REDACTED]"),
    (re.compile(r"\bBearer\s+[A-Za-z0-9._~+/=-]{8,}\b", re.I), "Bearer [REDACTED]"),
    (
        re.compile(
            r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----[\s\S]*?"
            r"-----END (?:RSA |EC |OPENSSH )?PRIVATE KEY-----",
            re.M,
        ),
        "[REDACTED]",
    ),
    (re.compile(r"(?i)(password|token)\s*=\s*[^\s&'\"]+"), r"\1=[REDACTED]"),
]


@dataclass(frozen=True)
class ExpandResult:
    """Outcome of a single expand request."""

    record_id: str
    status: str
    source_path: str = ""
    tool: str = ""
    format: str = ""
    start_offset: int | None = None
    end_offset: int | None = None
    date: str = ""
    text: str = ""
    warning: str = ""
    truncated: bool = False
    message: str = ""

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "record_id": self.record_id,
            "status": self.status,
            "source_path": self.source_path,
            "tool": self.tool,
            "format": self.format,
            "start_offset": self.start_offset,
            "end_offset": self.end_offset,
            "date": self.date,
            "truncated": self.truncated,
            "text": self.text,
        }
        if self.warning:
            payload["warning"] = self.warning
        if self.message:
            payload["message"] = self.message
        return payload


def redact_secrets(text: str) -> str:
    out = text
    for pattern, repl in _REDACT_PATTERNS:
        out = pattern.sub(repl, out)
    return out


def truncate_text(text: str, max_chars: int) -> tuple[str, bool]:
    if max_chars <= 0 or len(text) <= max_chars:
        return text, False
    marker = "\n\n[… truncated — use --max-chars to raise the cap …]\n\n"
    keep = max(0, max_chars - len(marker))
    return text[:keep] + marker, True


def format_expand_output(result: ExpandResult) -> str:
    lines = [
        f"--- expand: {result.record_id} ---",
        f"path: {result.source_path or '(unknown)'}",
    ]
    if result.start_offset is not None and result.end_offset is not None:
        lines.append(f"messages: {result.start_offset}–{result.end_offset}")
    if result.date:
        lines.append(f"date: {result.date}")
    if result.tool:
        lines.append(f"tool: {result.tool}")
    if result.format:
        lines.append(f"format: {result.format}")
    lines.append(f"status: {result.status}")
    if result.warning:
        lines.append(f"warning: {result.warning}")
    if result.message and result.status not in ("exact", "drifted"):
        lines.append(f"detail: {result.message}")
    lines.append("")
    if result.text:
        lines.append(result.text)
    return "\n".join(lines).rstrip() + "\n"


def _coerce_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _selection_parameters(meta: Mapping[str, Any]) -> dict[str, Any]:
    envelope = envelope_from_unit(meta)
    if not envelope:
        return {}
    selection = envelope.get("selection_parameters")
    return dict(selection) if isinstance(selection, Mapping) else {}


def _expected_chunk_sha(meta: Mapping[str, Any]) -> str:
    selection = _selection_parameters(meta)
    raw = selection.get("rendered_chunk_sha256")
    return str(raw).strip() if raw else ""


def _bounds_from_meta(meta: Mapping[str, Any]) -> tuple[int | None, int | None]:
    selection = _selection_parameters(meta)
    start = _coerce_int(meta.get("start_offset"))
    end = _coerce_int(meta.get("end_offset"))
    if start is None:
        start = _coerce_int(selection.get("chunk_start"))
    if end is None:
        end = _coerce_int(selection.get("chunk_end"))
    return start, end


def _is_non_session_hit(meta: Mapping[str, Any], path_key: str) -> bool:
    tool = str(meta.get("tool") or "").strip().lower()
    if tool in _NON_SESSION_TOOLS:
        return True
    fmt = detect_format(Path(path_key))
    return fmt in _NON_SESSION_FORMATS


def _is_excluded_source(cfg: Mapping[str, Any], path_key: str) -> bool:
    processed_path = str(cfg.get("index", {}).get("processed_log") or "")
    if processed_path:
        processed = load_processed(processed_path)
        if _path_is_excluded(processed, path_key):
            return True
    try:
        from watch import is_excluded_from_index

        return bool(is_excluded_from_index(path_key))
    except ImportError:
        return False


def _format_supported(fmt: str | None) -> bool:
    if not fmt:
        return False
    if fmt in _EXPAND_JSONL_FORMATS:
        return True
    if fmt in _EXPAND_SQLITE_FORMATS:
        return True
    return False


def _get_summary_row(store: Any, summary_id: str) -> dict | None:
    col = store._collection(SUMMARIES)
    res = col.get(ids=[summary_id], include=["metadatas", "documents"])
    ids = res.get("ids") or []
    if not ids:
        return None
    metas = res.get("metadatas") or [{}]
    meta = dict(metas[0] or {})
    meta["id"] = ids[0]
    return meta


def _find_summary_meta(store: Any, source_path: str, start_offset: int) -> dict | None:
    for row in store.summaries_metadata():
        if row.get("source_path") != source_path:
            continue
        if _coerce_int(row.get("start_offset")) == start_offset:
            return dict(row)
    return None


def _resolve_binding(store: Any, record_id: str) -> tuple[str, dict] | tuple[None, str]:
    """Return (metadata, kind) where kind is unit|summary, or (None, error)."""
    rid = record_id.strip()
    if not rid:
        return None, "empty id"

    unit = store.get_unit(rid)
    if unit:
        return dict(unit.get("metadata") or {}), "unit"

    summary = _get_summary_row(store, rid)
    if summary:
        return summary, "summary"

    # Chunk-summary doc id is sha256(f"{path_key}:{start_offset}")
    for row in store.summaries_metadata():
        if str(row.get("id") or "") == rid:
            return dict(row), "summary"

    return None, f"no unit or chunk summary found for id {rid}"


def _render_window(
    *,
    source_path: str,
    start: int,
    end: int,
    tool: str,
    expected_sha: str,
) -> ExpandResult:
    path = Path(source_path)
    fmt = detect_format(path)
    if not _format_supported(fmt):
        return ExpandResult(
            record_id="",
            status="unsupported format",
            source_path=source_path,
            tool=tool,
            format=fmt or "",
            start_offset=start,
            end_offset=end,
            message=(
                "Full-chunk expansion supports JSONL session adapters "
                "(Cursor, Codex, Claude, Kiro, Copilot), Kiro legacy SQLite, "
                "and Crush SQLite when message offsets match ingest."
            ),
        )

    parser = get_parser(path)
    if parser is None:
        return ExpandResult(
            record_id="",
            status="unsupported format",
            source_path=source_path,
            tool=tool,
            format=fmt or "",
            start_offset=start,
            end_offset=end,
            message="No parser available for this format.",
        )

    if not path.is_file():
        return ExpandResult(
            record_id="",
            status="missing",
            source_path=source_path,
            tool=tool,
            format=fmt or "",
            start_offset=start,
            end_offset=end,
            message="Source file is not on disk.",
        )

    try:
        messages = parser(str(path))
    except Exception as exc:  # pylint: disable=broad-exception-caught
        return ExpandResult(
            record_id="",
            status="unsupported format",
            source_path=source_path,
            tool=tool,
            format=fmt or "",
            start_offset=start,
            end_offset=end,
            message=f"Failed to parse source: {exc}",
        )

    if start < 0 or end < start or end >= len(messages):
        return ExpandResult(
            record_id="",
            status="unsupported format",
            source_path=source_path,
            tool=tool,
            format=fmt or "",
            start_offset=start,
            end_offset=end,
            message=(
                "Message offsets are out of range for the parsed source "
                f"({len(messages)} messages)."
            ),
        )

    window = messages[start : end + 1]
    text = render_chunk(window)
    live_sha = hashlib.sha256(text.encode("utf-8")).hexdigest()
    status = "exact"
    warning = ""
    if expected_sha:
        if live_sha != expected_sha:
            status = "drifted"
            warning = (
                "Source file changed since indexing; rendered text may differ "
                "from the distilled unit."
            )
    date = _chunk_date(window)
    resolved_tool = tool or TOOL_BY_FORMAT.get(fmt or "", fmt or "")
    return ExpandResult(
        record_id="",
        status=status,
        source_path=source_path,
        tool=resolved_tool,
        format=fmt or "",
        start_offset=start,
        end_offset=end,
        date=date,
        text=text,
        warning=warning,
    )


def expand_record(
    record_id: str,
    *,
    max_chars: int = DEFAULT_MAX_CHARS,
    redact: bool = True,
    cfg: Mapping[str, Any] | None = None,
) -> ExpandResult:
    """Expand a knowledge-unit id or chunk-summary id to indexed source text."""

    from config import load_config
    from chroma_store import open_chroma_for_verify

    live_cfg = dict(cfg or load_config())
    chroma_dir = str(live_cfg.get("index", {}).get("chroma_dir") or "")
    with contextlib.closing(open_chroma_for_verify(chroma_dir)) as store:
        meta, kind_or_err = _resolve_binding(store, record_id)
        if meta is None:
            return ExpandResult(
                record_id=record_id,
                status="not_found",
                message=kind_or_err,
            )

        source_path = str(meta.get("source_path") or "").strip()
        if not source_path:
            return ExpandResult(
                record_id=record_id,
                status="not_found",
                message="Hit metadata has no source_path.",
            )

        path_key = str(Path(source_path).expanduser().resolve())
        archived_note = _is_excluded_source(live_cfg, path_key)

        if _is_non_session_hit(meta, path_key):
            tool = str(meta.get("tool") or "")
            fmt = detect_format(Path(path_key)) or ""
            return ExpandResult(
                record_id=record_id,
                status="not_session",
                source_path=path_key,
                tool=tool,
                format=fmt,
                message="This hit is not a session transcript chunk; open the source path.",
            )

        start, end = _bounds_from_meta(meta)
        if start is None:
            return ExpandResult(
                record_id=record_id,
                status="not_found",
                source_path=path_key,
                message="Could not resolve chunk start_offset for this hit.",
            )

        if end is None and kind_or_err == "unit":
            summary = _find_summary_meta(store, path_key, start)
            if summary:
                end = _coerce_int(summary.get("end_offset"))
        if end is None:
            if _is_non_session_hit(meta, path_key):
                tool = str(meta.get("tool") or "")
                fmt = detect_format(Path(path_key)) or ""
                return ExpandResult(
                    record_id=record_id,
                    status="not_session",
                    source_path=path_key,
                    tool=tool,
                    format=fmt,
                    start_offset=start,
                    message="This hit is not a session transcript chunk; open the source path.",
                )
            return ExpandResult(
                record_id=record_id,
                status="not_found",
                source_path=path_key,
                start_offset=start,
                message="Could not resolve chunk end_offset for this hit.",
            )

        expected_sha = _expected_chunk_sha(meta)
        if not expected_sha and kind_or_err == "unit":
            summary = _find_summary_meta(store, path_key, start)
            if summary:
                expected_sha = _expected_chunk_sha(summary)

        tool = str(meta.get("tool") or "")
        rendered = _render_window(
            source_path=path_key,
            start=start,
            end=end,
            tool=tool,
            expected_sha=expected_sha,
        )
        body = rendered.text
        if redact:
            body = redact_secrets(body)
        body, truncated = truncate_text(body, max_chars)
        warning = rendered.warning
        if archived_note:
            archive_msg = "Source archived from re-indexing."
            warning = f"{warning} {archive_msg}".strip() if warning else archive_msg
        return ExpandResult(
            record_id=record_id,
            status=rendered.status,
            source_path=rendered.source_path,
            tool=rendered.tool,
            format=rendered.format,
            start_offset=rendered.start_offset,
            end_offset=rendered.end_offset,
            date=rendered.date,
            text=body,
            warning=warning,
            truncated=truncated,
            message=rendered.message,
        )


def register_expand_cli(typer_app) -> None:
    """Attach the ``expand`` subcommand to the main Typer app."""

    import typer

    @typer_app.command("expand")
    def expand_command(
        record_id: str = typer.Argument(
            ..., help="Knowledge unit id or chunk-summary id"
        ),
        max_chars: int = typer.Option(
            DEFAULT_MAX_CHARS,
            "--max-chars",
            min=1,
            help="Maximum characters of chunk text to print",
        ),
        no_redact: bool = typer.Option(
            False, "--no-redact", help="Disable light secret redaction"
        ),
    ):
        """Re-render the source conversation window for an indexed unit or chunk."""
        result = expand_record(record_id, max_chars=max_chars, redact=not no_redact)
        typer.echo(format_expand_output(result))
        if result.status in ("not_found", "not_session", "unsupported format"):
            raise typer.Exit(1)


def print_expanded_search_hits(results: list[dict]) -> None:
    """CLI helper: expand each search hit id to stdout."""

    import typer

    for r in results:
        hit_id = (r.get("id") or "").strip()
        if not hit_id:
            continue
        typer.echo("")
        typer.echo(format_expand_output(expand_record(hit_id)))


__all__ = [
    "DEFAULT_MAX_CHARS",
    "ExpandResult",
    "expand_record",
    "format_expand_output",
    "print_expanded_search_hits",
    "register_expand_cli",
    "redact_secrets",
    "truncate_text",
]

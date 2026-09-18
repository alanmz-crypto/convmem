"""Adapter for Codex CLI user prompt history (~/.codex/history.jsonl).

Each line is a user prompt only — assistant replies are NOT stored in this file.
Units indexed from here carry source_type=prompt_only so ask synthesis can treat
them differently later (v1: metadata only; ask wiring deferred).
"""

from datetime import datetime, timezone
from pathlib import Path

from adapters.jsonl_prefix import (
    CompletePrefixView,
    complete_prefix_view,
    legacy_parse_jsonl_messages,
)


def is_codex_history_jsonl(path: Path | str) -> bool:
    p = Path(path).expanduser().resolve()
    expected = (Path.home() / ".codex" / "history.jsonl").resolve()
    return p == expected


def _message_from_record(record: object) -> dict | None:
    if not isinstance(record, dict):
        return None
    text = record.get("text")
    if not isinstance(text, str) or not text.strip():
        return None
    session_id = record.get("session_id")
    sid = session_id if isinstance(session_id, str) else ""
    ts_raw = record.get("ts")
    timestamp = None
    if isinstance(ts_raw, (int, float)):
        try:
            timestamp = datetime.fromtimestamp(
                float(ts_raw), tz=timezone.utc
            ).isoformat()
        except (OSError, OverflowError, ValueError):
            timestamp = None
    return {
        "role": "user",
        "content": text.strip(),
        "timestamp": timestamp,
        "session_id": sid,
        "source_type": "prompt_only",
    }


def parse(filepath: str) -> list[dict]:
    """Parse Codex history.jsonl into canonical user-only messages."""
    return legacy_parse_jsonl_messages(filepath, _message_from_record)


def parse_complete_prefix(filepath: str, *, raw: bytes | None = None) -> CompletePrefixView:
    """Return messages, line outcomes, and prefix identity for history JSONL."""
    return complete_prefix_view(
        filepath, raw=raw, message_from_record=_message_from_record
    )

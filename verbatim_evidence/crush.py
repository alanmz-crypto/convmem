"""Read-only Crush SQLite adapter for bounded session-only verbatim evidence."""

from __future__ import annotations

import json
import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import quote

from adapters.sqlite_chat import (
    _crush_timestamp_to_iso,
    is_sqlite_crush_schema,
)
from verbatim_evidence.normalize import (
    digest_excerpt,
    find_match_span,
    message_matches,
    normalize_evidence_text,
)
from verbatim_evidence.types import (
    EvidenceExcerpt,
    EvidenceLocator,
    EvidenceResult,
    EvidenceScope,
    EvidenceStatus,
)

ADAPTER_KIND_CRUSH = "sqlite_crush"

MAX_SCAN_ROWS = 10_000
MAX_SCAN_BYTES = 16 * 1024 * 1024
MAX_PARTS_BYTES = 1 * 1024 * 1024
MAX_RESULTS = 3
MAX_EXCERPT_CHARS = 2_000
MAX_QUERY_CHARS = 2_000

DEFAULT_MAX_SCAN_ROWS = MAX_SCAN_ROWS
DEFAULT_MAX_CANDIDATE_MESSAGES = MAX_SCAN_ROWS
DEFAULT_MAX_RESULT_MESSAGES = MAX_RESULTS
DEFAULT_MAX_EXCERPT_CHARS = MAX_EXCERPT_CHARS

TOTAL_READ_DEADLINE_SECONDS = 2.0
BUSY_TIMEOUT_MAX_SECONDS = 0.25
PROGRESS_OPCODE_INTERVAL = 1_000

TRUNCATION_MARKER = "…[truncated]"

_SHADOW_ID_COLUMNS = frozenset({"rowid", "oid", "_rowid_"})
_ALLOWED_READ_TABLES = frozenset({"messages", "sqlite_master"})
_ALLOWED_PRAGMAS = frozenset({"table_info", "query_only", "trusted_schema"})

_STAGE1_SQL = """
SELECT id, session_id, role, created_at, length(CAST(parts AS BLOB)) AS parts_len
FROM messages
WHERE session_id = ? AND role IN ('user', 'assistant')
ORDER BY created_at, id
LIMIT ?
"""

_STAGE2_SQL = """
SELECT id, session_id, role, parts, created_at
FROM messages
WHERE id = ? AND session_id = ?
"""


@dataclass
class _ReadState:
    deadline_hit: bool = False


@dataclass(frozen=True)
class _SourceSnapshot:
    resolved: Path
    st_dev: int
    st_ino: int


def _validate_positive_int(
    name: str,
    value: object,
    *,
    minimum: int,
    maximum: int,
) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int):
        return None
    if value < minimum or value > maximum:
        return None
    return value


def _validate_budgets(
    *,
    max_scan_rows: int,
    max_candidate_messages: int,
    max_result_messages: int,
    max_excerpt_chars: int,
) -> str | None:
    checks = (
        ("max_scan_rows", max_scan_rows, 1, MAX_SCAN_ROWS),
        ("max_candidate_messages", max_candidate_messages, 1, MAX_SCAN_ROWS),
        ("max_result_messages", max_result_messages, 1, MAX_RESULTS),
        ("max_excerpt_chars", max_excerpt_chars, 1, MAX_EXCERPT_CHARS),
    )
    for name, value, minimum, maximum in checks:
        if _validate_positive_int(name, value, minimum=minimum, maximum=maximum) is None:
            return "invalid_budget"
    return None


def _session_key(locator: EvidenceLocator) -> str | None:
    session = locator.session_id if isinstance(locator.session_id, str) else None
    conversation = (
        locator.conversation_id if isinstance(locator.conversation_id, str) else None
    )
    session = (session or "").strip() or None
    conversation = (conversation or "").strip() or None
    if session and conversation and session != conversation:
        return None
    return session


def _has_offsets(locator: EvidenceLocator) -> bool:
    return locator.start_offset is not None and locator.end_offset is not None


def _sqlite_uri(path: Path) -> str:
    encoded = quote(path.as_posix(), safe="/")
    return f"file:{encoded}?mode=ro"


def _source_snapshot(path: Path) -> _SourceSnapshot | None:
    try:
        resolved = path.resolve()
        stat = resolved.stat()
    except OSError:
        return None
    return _SourceSnapshot(resolved=resolved, st_dev=stat.st_dev, st_ino=stat.st_ino)


def _snapshot_unchanged(before: _SourceSnapshot) -> bool:
    after = _source_snapshot(before.resolved)
    if after is None:
        return False
    return before.st_dev == after.st_dev and before.st_ino == after.st_ino


def _sqlite_authorizer(
    action: int,
    arg1: str | None,
    arg2: str | None,
    _arg3: str | None,
    _arg4: str | None,
) -> int:
    if action == sqlite3.SQLITE_SELECT:
        if arg2 in _ALLOWED_READ_TABLES or arg2 is None:
            return sqlite3.SQLITE_OK
        return sqlite3.SQLITE_DENY
    if action == sqlite3.SQLITE_READ:
        if arg1 in _ALLOWED_READ_TABLES:
            return sqlite3.SQLITE_OK
        return sqlite3.SQLITE_DENY
    if action == sqlite3.SQLITE_FUNCTION:
        func_name = (arg2 or arg1 or "").lower()
        if func_name == "length":
            return sqlite3.SQLITE_OK
        return sqlite3.SQLITE_DENY
    if action == sqlite3.SQLITE_PRAGMA:
        if arg1 in _ALLOWED_PRAGMAS:
            return sqlite3.SQLITE_OK
        return sqlite3.SQLITE_DENY
    if action in (
        sqlite3.SQLITE_INSERT,
        sqlite3.SQLITE_UPDATE,
        sqlite3.SQLITE_DELETE,
        sqlite3.SQLITE_CREATE_TABLE,
        sqlite3.SQLITE_DROP_TABLE,
        sqlite3.SQLITE_ALTER_TABLE,
        sqlite3.SQLITE_CREATE_INDEX,
        sqlite3.SQLITE_DROP_INDEX,
        sqlite3.SQLITE_CREATE_VIEW,
        sqlite3.SQLITE_DROP_VIEW,
        sqlite3.SQLITE_CREATE_TRIGGER,
        sqlite3.SQLITE_DROP_TRIGGER,
        sqlite3.SQLITE_TRANSACTION,
        sqlite3.SQLITE_ATTACH,
        sqlite3.SQLITE_DETACH,
    ):
        return sqlite3.SQLITE_DENY
    return sqlite3.SQLITE_DENY


def _make_progress_handler(state: _ReadState, deadline: float):
    def _handler() -> int:
        if time.monotonic() >= deadline:
            state.deadline_hit = True
            return 1
        return 0

    return _handler


def _connect_readonly(path: Path, *, timeout: float, state: _ReadState, deadline: float):
    conn = sqlite3.connect(
        _sqlite_uri(path),
        uri=True,
        timeout=max(0.0, min(timeout, BUSY_TIMEOUT_MAX_SECONDS)),
    )
    conn.set_progress_handler(_make_progress_handler(state, deadline), PROGRESS_OPCODE_INTERVAL)
    conn.execute("PRAGMA query_only=ON")
    conn.execute("PRAGMA trusted_schema=OFF")
    conn.execute("BEGIN")
    conn.set_authorizer(_sqlite_authorizer)
    return conn


def _reject_shadow_rowid(conn: sqlite3.Connection) -> bool:
    rows = conn.execute("PRAGMA table_info(messages)").fetchall()
    for row in rows:
        name = row[1]
        if isinstance(name, str) and name.casefold() in _SHADOW_ID_COLUMNS:
            return True
    return False


def _extract_text_parts(parts_raw: Any) -> tuple[str | None, str | None]:
    """Return (content, row_error) where row_error is malformed_row or oversized_row."""
    if parts_raw is None:
        return None, None
    if isinstance(parts_raw, bytes):
        if len(parts_raw) > MAX_PARTS_BYTES:
            return None, "oversized_row"
        parts_raw = parts_raw.decode("utf-8", errors="replace")
    elif isinstance(parts_raw, str):
        if len(parts_raw.encode("utf-8")) > MAX_PARTS_BYTES:
            return None, "oversized_row"
    else:
        return None, "malformed_row"

    try:
        parts = json.loads(parts_raw)
    except (json.JSONDecodeError, TypeError, RecursionError):
        return None, "malformed_row"
    if not isinstance(parts, list):
        return None, "malformed_row"

    texts: list[str] = []
    for part in parts:
        if not isinstance(part, dict):
            continue
        ptype = part.get("type")
        data = part.get("data")
        if not isinstance(data, dict):
            continue
        if ptype == "text":
            text = data.get("text")
            if isinstance(text, str) and text.strip():
                texts.append(text.strip())
    if not texts:
        return None, None
    return "\n\n".join(texts), None


def _bound_excerpt(
    text: str,
    max_chars: int,
    *,
    match_span: tuple[int, int],
) -> tuple[str, bool, bool] | None:
    """Return (excerpt, cut_leading, cut_trailing), or None if no candidate
    window fits `max_chars` while preserving the full match span intact.

    Candidates are tried in order (see the excerpt algorithm addendum on
    issue #263): whole text; left-anchored prefix + trailing marker;
    right-anchored leading marker + suffix; centered window with both
    markers. Never returns a marker-only or partial-query excerpt.
    """
    match_start, match_end = match_span
    if not 0 <= match_start < match_end <= len(text):
        raise ValueError(f"invalid match_span {match_span!r} for text of length {len(text)}")

    # Candidate 1: whole text, no markers.
    if len(text) <= max_chars:
        return text, False, False

    query_len = match_end - match_start
    if query_len > max_chars:
        return None

    marker_len = len(TRUNCATION_MARKER)

    # Candidate 2: left-anchored prefix, one trailing marker.
    if marker_len <= max_chars and match_end <= max_chars - marker_len:
        end = max_chars - marker_len
        return text[:end] + TRUNCATION_MARKER, False, True

    # Candidate 3: right-anchored suffix, one leading marker.
    if marker_len <= max_chars and (len(text) - match_start) <= max_chars - marker_len:
        start = len(text) - (max_chars - marker_len)
        return TRUNCATION_MARKER + text[start:], True, False

    # Candidate 4: centered window, both markers. Falling through here means
    # neither a prefix-only nor a suffix-only window fit, so this candidate
    # always cuts both sides.
    if 2 * marker_len > max_chars:
        return None
    content_budget = max_chars - 2 * marker_len
    if query_len > content_budget:
        return None

    slack = content_budget - query_len
    start = match_start - slack // 2
    end = start + content_budget
    if start < 0:
        end -= start
        start = 0
    if end > len(text):
        start -= end - len(text)
        end = len(text)
    start = max(start, 0)

    assert start > 0 and end < len(text), "candidate 4 must cut both sides"
    return TRUNCATION_MARKER + text[start:end] + TRUNCATION_MARKER, True, True


def _prevalidate_locator(
    locator: EvidenceLocator,
    query_text: str,
    *,
    max_scan_rows: int,
    max_candidate_messages: int,
    max_result_messages: int,
    max_excerpt_chars: int,
) -> EvidenceResult | None:
    if _validate_budgets(
        max_scan_rows=max_scan_rows,
        max_candidate_messages=max_candidate_messages,
        max_result_messages=max_result_messages,
        max_excerpt_chars=max_excerpt_chars,
    ):
        return EvidenceResult(
            status=EvidenceStatus.INVALID_LOCATOR,
            reason="invalid_budget",
        )

    for field_name, value in (
        ("source_path", locator.source_path),
        ("session_id", locator.session_id),
        ("conversation_id", locator.conversation_id),
    ):
        if value is not None and not isinstance(value, str):
            return EvidenceResult(
                status=EvidenceStatus.INVALID_LOCATOR,
                reason="invalid_locator_field",
            )

    for field_name, value in (("start_offset", locator.start_offset), ("end_offset", locator.end_offset)):
        if value is not None and (isinstance(value, bool) or not isinstance(value, int)):
            return EvidenceResult(
                status=EvidenceStatus.INVALID_LOCATOR,
                reason="invalid_locator_field",
            )

    source = (locator.source_path or "").strip()
    if not source:
        return EvidenceResult(
            status=EvidenceStatus.INVALID_LOCATOR,
            reason="missing_source_path",
        )

    path = Path(source).expanduser()
    if not path.is_absolute():
        return EvidenceResult(
            status=EvidenceStatus.INVALID_LOCATOR,
            source_path=source,
            reason="relative_source_path",
        )

    if len(normalize_evidence_text(query_text or "")) > MAX_QUERY_CHARS:
        return EvidenceResult(
            status=EvidenceStatus.INVALID_LOCATOR,
            source_path=source,
            reason="query_too_long",
        )

    normalized_query = normalize_evidence_text(query_text or "")
    if not normalized_query.strip():
        return EvidenceResult(
            status=EvidenceStatus.INVALID_LOCATOR,
            source_path=source,
            reason="empty_query",
        )

    session_hint = _session_key(locator)
    has_offsets = _has_offsets(locator)

    if has_offsets and not session_hint:
        return EvidenceResult(
            status=EvidenceStatus.INVALID_LOCATOR,
            source_path=source,
            adapter_kind=ADAPTER_KIND_CRUSH,
            reason="offset_retrieval_unavailable",
        )

    has_session = isinstance(locator.session_id, str) and bool(locator.session_id.strip())
    has_conversation = isinstance(locator.conversation_id, str) and bool(
        locator.conversation_id.strip()
    )

    if has_conversation and not has_session:
        return EvidenceResult(
            status=EvidenceStatus.INVALID_LOCATOR,
            source_path=source,
            adapter_kind=ADAPTER_KIND_CRUSH,
            reason="conversation_only_locator",
        )

    if not session_hint:
        return EvidenceResult(
            status=EvidenceStatus.INVALID_LOCATOR,
            source_path=source,
            adapter_kind=ADAPTER_KIND_CRUSH,
            reason="missing_session_conversation_or_offsets",
        )

    if has_session and has_conversation and locator.session_id.strip() != locator.conversation_id.strip():
        return EvidenceResult(
            status=EvidenceStatus.INVALID_LOCATOR,
            source_path=source,
            adapter_kind=ADAPTER_KIND_CRUSH,
            reason="conflicting_session_and_conversation",
        )

    return None


def retrieve_crush_evidence(
    locator: EvidenceLocator,
    query_text: str,
    *,
    max_scan_rows: int = DEFAULT_MAX_SCAN_ROWS,
    max_candidate_messages: int = DEFAULT_MAX_CANDIDATE_MESSAGES,
    max_result_messages: int = DEFAULT_MAX_RESULT_MESSAGES,
    max_excerpt_chars: int = DEFAULT_MAX_EXCERPT_CHARS,
) -> EvidenceResult:
    """Look up bounded Crush session evidence for ``query_text``.

    Session-only slice: offset-only locators are rejected before open. Locators
    with both offsets and a session key ignore offsets and search the session.
    """
    pre = _prevalidate_locator(
        locator,
        query_text,
        max_scan_rows=max_scan_rows,
        max_candidate_messages=max_candidate_messages,
        max_result_messages=max_result_messages,
        max_excerpt_chars=max_excerpt_chars,
    )
    if pre is not None:
        return pre

    source = (locator.source_path or "").strip()
    path = Path(source).expanduser()
    session_hint = _session_key(locator)
    assert session_hint is not None
    offsets_ignored = _has_offsets(locator)

    snapshot_before = _source_snapshot(path)
    if snapshot_before is None:
        return EvidenceResult(
            status=EvidenceStatus.UNAVAILABLE_SOURCE,
            source_path=source,
            adapter_kind=ADAPTER_KIND_CRUSH,
            reason="source_missing",
        )

    if not snapshot_before.resolved.is_file():
        return EvidenceResult(
            status=EvidenceStatus.UNAVAILABLE_SOURCE,
            source_path=str(snapshot_before.resolved),
            adapter_kind=ADAPTER_KIND_CRUSH,
            reason="source_missing",
        )

    deadline = time.monotonic() + TOTAL_READ_DEADLINE_SECONDS
    state = _ReadState()
    normalized_query = normalize_evidence_text(query_text or "")

    conn: sqlite3.Connection | None = None
    try:
        remaining = max(0.0, deadline - time.monotonic())
        conn = _connect_readonly(
            snapshot_before.resolved,
            timeout=remaining,
            state=state,
            deadline=deadline,
        )

        if not is_sqlite_crush_schema(conn):
            return EvidenceResult(
                status=EvidenceStatus.UNAVAILABLE_SOURCE,
                source_path=str(snapshot_before.resolved),
                adapter_kind=ADAPTER_KIND_CRUSH,
                reason="unsupported_source",
            )

        if _reject_shadow_rowid(conn):
            return EvidenceResult(
                status=EvidenceStatus.UNAVAILABLE_SOURCE,
                source_path=str(snapshot_before.resolved),
                adapter_kind=ADAPTER_KIND_CRUSH,
                reason="unsupported_source",
            )

        result = _scan_session(
            conn,
            session_key=session_hint,
            normalized_query=normalized_query,
            query_text=query_text or "",
            resolved_path=str(snapshot_before.resolved),
            max_scan_rows=min(max_scan_rows, max_candidate_messages),
            max_result_messages=max_result_messages,
            max_excerpt_chars=max_excerpt_chars,
            state=state,
            deadline=deadline,
            offsets_ignored=offsets_ignored,
        )
    except sqlite3.OperationalError as exc:
        if state.deadline_hit:
            return EvidenceResult(
                status=EvidenceStatus.UNAVAILABLE_SOURCE,
                source_path=str(snapshot_before.resolved),
                adapter_kind=ADAPTER_KIND_CRUSH,
                reason="deadline",
            )
        if exc.sqlite_errorcode == sqlite3.SQLITE_BUSY:
            return EvidenceResult(
                status=EvidenceStatus.UNAVAILABLE_SOURCE,
                source_path=str(snapshot_before.resolved),
                adapter_kind=ADAPTER_KIND_CRUSH,
                reason="source_busy",
            )
        return EvidenceResult(
            status=EvidenceStatus.UNAVAILABLE_SOURCE,
            source_path=str(snapshot_before.resolved),
            adapter_kind=ADAPTER_KIND_CRUSH,
            reason="source_unreadable",
        )
    except sqlite3.Error:
        if state.deadline_hit:
            return EvidenceResult(
                status=EvidenceStatus.UNAVAILABLE_SOURCE,
                source_path=str(snapshot_before.resolved),
                adapter_kind=ADAPTER_KIND_CRUSH,
                reason="deadline",
            )
        return EvidenceResult(
            status=EvidenceStatus.UNAVAILABLE_SOURCE,
            source_path=str(snapshot_before.resolved),
            adapter_kind=ADAPTER_KIND_CRUSH,
            reason="source_unreadable",
        )
    finally:
        if conn is not None:
            conn.close()

    if not _snapshot_unchanged(snapshot_before):
        return EvidenceResult(
            status=EvidenceStatus.UNAVAILABLE_SOURCE,
            source_path=str(snapshot_before.resolved),
            adapter_kind=ADAPTER_KIND_CRUSH,
            reason="source_identity_changed",
        )

    return result


def _scan_session(
    conn: sqlite3.Connection,
    *,
    session_key: str,
    normalized_query: str,
    query_text: str,
    resolved_path: str,
    max_scan_rows: int,
    max_result_messages: int,
    max_excerpt_chars: int,
    state: _ReadState,
    deadline: float,
    offsets_ignored: bool,
) -> EvidenceResult:
    if len(normalized_query.strip()) > max_excerpt_chars:
        return EvidenceResult(
            status=EvidenceStatus.UNAVAILABLE_MATCH,
            source_path=resolved_path,
            adapter_kind=ADAPTER_KIND_CRUSH,
            reason="query_exceeds_excerpt_budget",
            scope=EvidenceScope.SESSION,
        )

    matches: list[EvidenceExcerpt] = []
    seen_keys: set[tuple[str, str]] = set()
    session_ordinal = 0
    bytes_scanned = 0
    partial_reason: str | None = None
    scan_capped = False
    result_capped = False
    at_result_limit = False
    any_dropped_excerpt = False

    stage1_rows = conn.execute(_STAGE1_SQL, (session_key, max_scan_rows + 1)).fetchall()
    if len(stage1_rows) > max_scan_rows:
        scan_capped = True
        stage1_rows = stage1_rows[:max_scan_rows]

    for message_id, row_session_id, role, created_at, parts_len in stage1_rows:
        if time.monotonic() >= deadline:
            state.deadline_hit = True
            raise sqlite3.OperationalError("deadline")

        bytes_scanned += int(parts_len or 0)
        if bytes_scanned > MAX_SCAN_BYTES:
            scan_capped = True
            break

        if not isinstance(message_id, str) or not isinstance(row_session_id, str):
            partial_reason = partial_reason or "malformed_row"
            continue
        key = (message_id, row_session_id)
        if key in seen_keys:
            return EvidenceResult(
                status=EvidenceStatus.UNAVAILABLE_SOURCE,
                source_path=resolved_path,
                adapter_kind=ADAPTER_KIND_CRUSH,
                reason="duplicate_row_identity",
            )
        seen_keys.add(key)

        if int(parts_len or 0) > MAX_PARTS_BYTES:
            partial_reason = partial_reason or "oversized_row"
            continue

        row = conn.execute(_STAGE2_SQL, key).fetchone()
        if row is None:
            partial_reason = partial_reason or "malformed_row"
            continue
        _, verified_session, verified_role, parts_raw, verified_created_at = row
        if verified_session != session_key:
            partial_reason = partial_reason or "malformed_row"
            continue
        if verified_role not in ("user", "assistant"):
            continue

        content, row_error = _extract_text_parts(parts_raw)
        if row_error:
            partial_reason = partial_reason or row_error
            continue
        if not content:
            continue

        normalized_content = normalize_evidence_text(content)
        current_ordinal = session_ordinal
        session_ordinal += 1

        if not message_matches(normalized_content, normalized_query):
            continue

        match_span = find_match_span(normalized_content, normalized_query)
        bound = _bound_excerpt(
            normalized_content,
            max_excerpt_chars,
            match_span=match_span,
        )
        if bound is None:
            # Dropped match: does not count as evidence, is not terminal,
            # and does not consume a result slot. Scanning continues.
            any_dropped_excerpt = True
            continue

        if at_result_limit:
            # A usable extra excerpt is the only condition that proves
            # result_limit; it is not itself appended.
            result_capped = True
            break

        excerpt_text, cut_leading, cut_trailing = bound
        matches.append(
            EvidenceExcerpt(
                source_path=resolved_path,
                adapter_kind=ADAPTER_KIND_CRUSH,
                session_id=verified_session,
                message_id=message_id,
                role=verified_role if isinstance(verified_role, str) else "",
                timestamp=_crush_timestamp_to_iso(verified_created_at),
                message_ordinal=current_ordinal,
                excerpt=excerpt_text,
                truncated=cut_leading or cut_trailing,
                content_digest_sha256=digest_excerpt(excerpt_text),
                cut_leading=cut_leading,
                cut_trailing=cut_trailing,
                scope=EvidenceScope.SESSION,
            )
        )
        if len(matches) >= max_result_messages:
            at_result_limit = True

    if not matches:
        if scan_capped:
            return EvidenceResult(
                status=EvidenceStatus.UNAVAILABLE_MATCH,
                source_path=resolved_path,
                adapter_kind=ADAPTER_KIND_CRUSH,
                reason="scan_limit",
                scope=EvidenceScope.SESSION,
            )
        if state.deadline_hit:
            return EvidenceResult(
                status=EvidenceStatus.UNAVAILABLE_SOURCE,
                source_path=resolved_path,
                adapter_kind=ADAPTER_KIND_CRUSH,
                reason="deadline",
                scope=EvidenceScope.SESSION,
            )
        if any_dropped_excerpt:
            return EvidenceResult(
                status=EvidenceStatus.UNAVAILABLE_MATCH,
                source_path=resolved_path,
                adapter_kind=ADAPTER_KIND_CRUSH,
                reason="query_exceeds_excerpt_budget",
                scope=EvidenceScope.SESSION,
            )
        return EvidenceResult(
            status=EvidenceStatus.UNAVAILABLE_MATCH,
            source_path=resolved_path,
            adapter_kind=ADAPTER_KIND_CRUSH,
            reason="no_message_match",
            scope=EvidenceScope.SESSION,
        )

    partial = bool(partial_reason or scan_capped or result_capped or any_dropped_excerpt)
    if scan_capped:
        partial_reason = "scan_limit"
    elif result_capped:
        partial_reason = "result_limit"
    elif not partial_reason:
        partial_reason = "excerpt_budget" if any_dropped_excerpt else None

    status = EvidenceStatus.AVAILABLE
    reason = "offsets_ignored_session_scope" if offsets_ignored else None

    return EvidenceResult(
        status=status,
        excerpts=tuple(matches),
        source_path=resolved_path,
        adapter_kind=ADAPTER_KIND_CRUSH,
        reason=reason,
        scope=EvidenceScope.SESSION,
        partial=partial,
        partial_reason=partial_reason,
    )

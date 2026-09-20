"""Read-only Crush SQLite adapter for bounded verbatim evidence."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from adapters.sqlite_chat import (
    _crush_parts_to_content,
    _crush_timestamp_to_iso,
    is_sqlite_crush_schema,
)
from verbatim_evidence.normalize import digest_excerpt, normalize_evidence_text
from verbatim_evidence.types import (
    EvidenceExcerpt,
    EvidenceLocator,
    EvidenceResult,
    EvidenceStatus,
)

ADAPTER_KIND_CRUSH = "sqlite_crush"

# API-contract budgets (not live config). Keep first slice conservative.
DEFAULT_MAX_CANDIDATE_MESSAGES = 64
DEFAULT_MAX_RESULT_MESSAGES = 3
DEFAULT_MAX_EXCERPT_CHARS = 2000
TRUNCATION_MARKER = "…[truncated]"

_MSG_SELECT = (
    "SELECT id, session_id, role, parts, created_at "
    "FROM messages "
    "WHERE role IN ('user', 'assistant') "
    "ORDER BY session_id, created_at, id"
)

_MSG_SELECT_SESSION = (
    "SELECT id, session_id, role, parts, created_at "
    "FROM messages "
    "WHERE session_id = ? AND role IN ('user', 'assistant') "
    "ORDER BY created_at, id"
)


def _connect_readonly(path: Path) -> sqlite3.Connection:
    """Open SQLite URI mode=ro; never creates WAL/SHM or mutates the file."""
    uri = f"file:{path.resolve().as_posix()}?mode=ro"
    return sqlite3.connect(uri, uri=True)


def _locator_usable(locator: EvidenceLocator) -> bool:
    has_offsets = locator.start_offset is not None and locator.end_offset is not None
    has_session = bool((locator.session_id or "").strip())
    has_conversation = bool((locator.conversation_id or "").strip())
    return has_offsets or has_session or has_conversation


def _resolve_session_key(locator: EvidenceLocator) -> str | None:
    session = (locator.session_id or "").strip() or None
    conversation = (locator.conversation_id or "").strip() or None
    if session and conversation and session != conversation:
        # Crush has no separate conversation_id column; conflicting ids are
        # unsafe to widen over — refuse rather than scan both.
        return None
    return session or conversation


def _message_matches(normalized_message: str, normalized_query: str) -> bool:
    query = normalized_query.strip()
    if not query:
        return False
    if query in normalized_message:
        return True
    return query.casefold() in normalized_message.casefold()


def _bound_excerpt(text: str, max_chars: int) -> tuple[str, bool]:
    if max_chars <= 0:
        return TRUNCATION_MARKER, True
    if len(text) <= max_chars:
        return text, False
    keep = max(0, max_chars - len(TRUNCATION_MARKER))
    return text[:keep] + TRUNCATION_MARKER, True


def _load_ordered_messages(
    conn: sqlite3.Connection,
    *,
    session_key: str | None,
    max_candidate_messages: int,
) -> list[dict]:
    if session_key:
        rows = conn.execute(_MSG_SELECT_SESSION, (session_key,)).fetchall()
    else:
        rows = conn.execute(_MSG_SELECT).fetchall()

    messages: list[dict] = []
    for row in rows:
        message_id, session_id, role, parts_raw, created_at = row
        content = _crush_parts_to_content(parts_raw)
        if not content:
            continue
        messages.append(
            {
                "id": message_id if isinstance(message_id, str) else None,
                "session_id": session_id if isinstance(session_id, str) else None,
                "role": role if isinstance(role, str) else "",
                "content": content,
                "timestamp": _crush_timestamp_to_iso(created_at),
            }
        )
        if len(messages) >= max_candidate_messages:
            break
    return messages


def _apply_offset_window(
    messages: list[dict],
    locator: EvidenceLocator,
    *,
    max_candidate_messages: int,
) -> list[dict]:
    start = locator.start_offset
    end = locator.end_offset
    assert start is not None and end is not None
    if start < 0 or end < start:
        return []
    window = messages[start : end + 1]
    if len(window) > max_candidate_messages:
        return window[:max_candidate_messages]
    return window


def _select_candidates(
    messages: list[dict],
    locator: EvidenceLocator,
    *,
    max_candidate_messages: int,
) -> list[dict] | None:
    """Return the bounded candidate window, or None for invalid_locator."""
    has_offsets = locator.start_offset is not None and locator.end_offset is not None
    session_key = _resolve_session_key(locator)

    if has_offsets:
        # Offsets are untrusted hints over the ordered message list already
        # constrained by session when a session key is present.
        return _apply_offset_window(
            messages, locator, max_candidate_messages=max_candidate_messages
        )

    if session_key:
        # Session (and optional conversation alias) already applied in SQL.
        if len(messages) > max_candidate_messages:
            return messages[:max_candidate_messages]
        return messages

    return None


def retrieve_crush_evidence(
    locator: EvidenceLocator,
    query_text: str,
    *,
    max_candidate_messages: int = DEFAULT_MAX_CANDIDATE_MESSAGES,
    max_result_messages: int = DEFAULT_MAX_RESULT_MESSAGES,
    max_excerpt_chars: int = DEFAULT_MAX_EXCERPT_CHARS,
) -> EvidenceResult:
    """Look up bounded Crush message evidence for ``query_text``.

    Never writes to the source database. Never scans an entire source when the
    locator is missing or ambiguous.
    """
    source = (locator.source_path or "").strip()
    if not source:
        return EvidenceResult(
            status=EvidenceStatus.INVALID_LOCATOR,
            reason="missing_source_path",
        )
    if not _locator_usable(locator):
        return EvidenceResult(
            status=EvidenceStatus.INVALID_LOCATOR,
            source_path=source,
            reason="missing_session_conversation_or_offsets",
        )

    session_key = _resolve_session_key(locator)
    has_offsets = locator.start_offset is not None and locator.end_offset is not None
    raw_session = (locator.session_id or "").strip()
    raw_conversation = (locator.conversation_id or "").strip()
    if raw_session and raw_conversation and raw_session != raw_conversation:
        return EvidenceResult(
            status=EvidenceStatus.INVALID_LOCATOR,
            source_path=source,
            adapter_kind=ADAPTER_KIND_CRUSH,
            reason="conflicting_session_and_conversation",
        )

    path = Path(source).expanduser()
    if not path.is_file():
        return EvidenceResult(
            status=EvidenceStatus.UNAVAILABLE_SOURCE,
            source_path=source,
            adapter_kind=ADAPTER_KIND_CRUSH,
            reason="source_missing",
        )

    try:
        conn = _connect_readonly(path)
    except sqlite3.Error:
        return EvidenceResult(
            status=EvidenceStatus.UNAVAILABLE_SOURCE,
            source_path=source,
            adapter_kind=ADAPTER_KIND_CRUSH,
            reason="source_unreadable",
        )

    try:
        if not is_sqlite_crush_schema(conn):
            return EvidenceResult(
                status=EvidenceStatus.UNAVAILABLE_SOURCE,
                source_path=source,
                adapter_kind=ADAPTER_KIND_CRUSH,
                reason="unsupported_source",
            )

        # Without offsets, Crush requires a session/conversation identity so
        # we never fall through to a source-wide scan.
        if not has_offsets and not session_key:
            return EvidenceResult(
                status=EvidenceStatus.INVALID_LOCATOR,
                source_path=source,
                adapter_kind=ADAPTER_KIND_CRUSH,
                reason="missing_session_conversation_or_offsets",
            )

        ordered = _load_ordered_messages(
            conn,
            session_key=session_key,
            max_candidate_messages=max(
                max_candidate_messages,
                (locator.end_offset or 0) + 1 if has_offsets else max_candidate_messages,
            ),
        )
        candidates = _select_candidates(
            ordered,
            locator,
            max_candidate_messages=max_candidate_messages,
        )
        if candidates is None:
            return EvidenceResult(
                status=EvidenceStatus.INVALID_LOCATOR,
                source_path=source,
                adapter_kind=ADAPTER_KIND_CRUSH,
                reason="ambiguous_locator",
            )

        normalized_query = normalize_evidence_text(query_text or "")
        matches: list[EvidenceExcerpt] = []
        for ordinal, message in enumerate(candidates):
            if len(matches) >= max_result_messages:
                break
            normalized_content = normalize_evidence_text(message["content"])
            if not _message_matches(normalized_content, normalized_query):
                continue
            excerpt_text, truncated = _bound_excerpt(
                normalized_content, max_excerpt_chars
            )
            matches.append(
                EvidenceExcerpt(
                    source_path=str(path),
                    adapter_kind=ADAPTER_KIND_CRUSH,
                    session_id=message["session_id"],
                    message_id=message["id"],
                    role=message["role"],
                    timestamp=message["timestamp"],
                    message_ordinal=ordinal,
                    excerpt=excerpt_text,
                    truncated=truncated,
                    content_digest_sha256=digest_excerpt(excerpt_text),
                )
            )

        if not matches:
            return EvidenceResult(
                status=EvidenceStatus.UNAVAILABLE_MATCH,
                source_path=str(path),
                adapter_kind=ADAPTER_KIND_CRUSH,
                reason="no_message_match",
            )

        return EvidenceResult(
            status=EvidenceStatus.AVAILABLE,
            excerpts=tuple(matches),
            source_path=str(path),
            adapter_kind=ADAPTER_KIND_CRUSH,
            reason=None,
        )
    except sqlite3.Error:
        return EvidenceResult(
            status=EvidenceStatus.UNAVAILABLE_SOURCE,
            source_path=source,
            adapter_kind=ADAPTER_KIND_CRUSH,
            reason="source_unreadable",
        )
    finally:
        conn.close()

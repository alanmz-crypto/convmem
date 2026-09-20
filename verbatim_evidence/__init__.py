"""Bounded read-only verbatim evidence retrieval (issue #263).

Chroma remains a summary/serving projection. Source databases stay read-only
authority. The first adapter covers Crush SQLite session retrieval only.
"""

from verbatim_evidence.context import (
    LABEL_SUMMARY,
    LABEL_UNAVAILABLE,
    LABEL_VERBATIM_SOURCE,
    format_labeled_context,
)
from verbatim_evidence.crush import (
    ADAPTER_KIND_CRUSH,
    DEFAULT_MAX_CANDIDATE_MESSAGES,
    DEFAULT_MAX_EXCERPT_CHARS,
    DEFAULT_MAX_RESULT_MESSAGES,
    DEFAULT_MAX_SCAN_ROWS,
    retrieve_crush_evidence,
)
from verbatim_evidence.normalize import digest_excerpt, message_matches, normalize_evidence_text
from verbatim_evidence.types import (
    EvidenceExcerpt,
    EvidenceLocator,
    EvidenceResult,
    EvidenceScope,
    EvidenceStatus,
)

__all__ = [
    "ADAPTER_KIND_CRUSH",
    "DEFAULT_MAX_CANDIDATE_MESSAGES",
    "DEFAULT_MAX_EXCERPT_CHARS",
    "DEFAULT_MAX_RESULT_MESSAGES",
    "DEFAULT_MAX_SCAN_ROWS",
    "EvidenceExcerpt",
    "EvidenceLocator",
    "EvidenceResult",
    "EvidenceScope",
    "EvidenceStatus",
    "LABEL_SUMMARY",
    "LABEL_UNAVAILABLE",
    "LABEL_VERBATIM_SOURCE",
    "digest_excerpt",
    "format_labeled_context",
    "message_matches",
    "normalize_evidence_text",
    "retrieve_crush_evidence",
    "retrieve_verbatim_evidence",
]


def retrieve_verbatim_evidence(
    locator: EvidenceLocator,
    query_text: str,
    *,
    max_scan_rows: int = DEFAULT_MAX_SCAN_ROWS,
    max_candidate_messages: int = DEFAULT_MAX_CANDIDATE_MESSAGES,
    max_result_messages: int = DEFAULT_MAX_RESULT_MESSAGES,
    max_excerpt_chars: int = DEFAULT_MAX_EXCERPT_CHARS,
) -> EvidenceResult:
    """Dispatch to a supported read-only source adapter.

    Unsupported or unreadable sources return ``unavailable_source`` without
    raising. Offset-only locators return ``offset_retrieval_unavailable`` before
    opening the database. Session retrieval ignores summary offsets when a
    session key is present.
    """
    return retrieve_crush_evidence(
        locator,
        query_text,
        max_scan_rows=max_scan_rows,
        max_candidate_messages=max_candidate_messages,
        max_result_messages=max_result_messages,
        max_excerpt_chars=max_excerpt_chars,
    )

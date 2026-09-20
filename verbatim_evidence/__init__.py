"""Bounded read-only verbatim evidence retrieval (issue #263).

Chroma remains a summary/serving projection. Source databases stay read-only
authority. The first adapter covers Crush SQLite only.
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
    retrieve_crush_evidence,
)
from verbatim_evidence.normalize import digest_excerpt, normalize_evidence_text
from verbatim_evidence.types import (
    EvidenceExcerpt,
    EvidenceLocator,
    EvidenceResult,
    EvidenceStatus,
)

__all__ = [
    "ADAPTER_KIND_CRUSH",
    "DEFAULT_MAX_CANDIDATE_MESSAGES",
    "DEFAULT_MAX_EXCERPT_CHARS",
    "DEFAULT_MAX_RESULT_MESSAGES",
    "EvidenceExcerpt",
    "EvidenceLocator",
    "EvidenceResult",
    "EvidenceStatus",
    "LABEL_SUMMARY",
    "LABEL_UNAVAILABLE",
    "LABEL_VERBATIM_SOURCE",
    "digest_excerpt",
    "format_labeled_context",
    "normalize_evidence_text",
    "retrieve_crush_evidence",
    "retrieve_verbatim_evidence",
]


def retrieve_verbatim_evidence(
    locator: EvidenceLocator,
    query_text: str,
    *,
    max_candidate_messages: int = DEFAULT_MAX_CANDIDATE_MESSAGES,
    max_result_messages: int = DEFAULT_MAX_RESULT_MESSAGES,
    max_excerpt_chars: int = DEFAULT_MAX_EXCERPT_CHARS,
) -> EvidenceResult:
    """Dispatch to a supported read-only source adapter.

    Unsupported or unreadable sources return ``unavailable_source`` without
    raising. Ambiguous locators return ``invalid_locator`` (never a source-wide
    scan).
    """
    return retrieve_crush_evidence(
        locator,
        query_text,
        max_candidate_messages=max_candidate_messages,
        max_result_messages=max_result_messages,
        max_excerpt_chars=max_excerpt_chars,
    )

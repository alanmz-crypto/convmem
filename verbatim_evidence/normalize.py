"""Unicode NFC + LF normalization shared by matching and digests."""

from __future__ import annotations

import hashlib
import re
import unicodedata


def normalize_evidence_text(text: str) -> str:
    """Normalize text for both message matching and SHA-256 digesting.

    Rules (pinned by architecture tip 3a49408):
    - Unicode NFC
    - LF line endings (CRLF/CR → LF)
    """
    if not isinstance(text, str):
        return ""
    normalized = unicodedata.normalize("NFC", text)
    return normalized.replace("\r\n", "\n").replace("\r", "\n")


def find_match_span(
    normalized_message: str, normalized_query: str
) -> tuple[int, int] | None:
    """Return the first match span using the same rules as ``message_matches``."""
    query = normalized_query.strip()
    if not query:
        return None
    idx = normalized_message.find(query)
    if idx >= 0:
        return idx, idx + len(query)
    regex = re.search(re.escape(query), normalized_message, flags=re.IGNORECASE)
    if regex is not None:
        return regex.start(), regex.end()
    return None


def message_matches(normalized_message: str, normalized_query: str) -> bool:
    """Conservative exact match with length-preserving IGNORECASE fallback."""
    return find_match_span(normalized_message, normalized_query) is not None


def digest_excerpt(excerpt: str) -> str:
    """SHA-256 hex digest of the post-truncation excerpt after NFC+LF.

    Digests the returned excerpt bytes (UTF-8), never the pre-truncation
    source text.
    """
    payload = normalize_evidence_text(excerpt).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()

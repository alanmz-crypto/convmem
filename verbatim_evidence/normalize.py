"""Unicode NFC + LF normalization shared by matching and digests."""

from __future__ import annotations

import hashlib
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


def digest_excerpt(excerpt: str) -> str:
    """SHA-256 hex digest of the post-truncation excerpt after NFC+LF.

    Digests the returned excerpt bytes (UTF-8), never the pre-truncation
    source text.
    """
    payload = normalize_evidence_text(excerpt).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()

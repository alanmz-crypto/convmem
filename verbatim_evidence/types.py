"""Typed contracts for bounded verbatim evidence retrieval."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class EvidenceStatus(str, Enum):
    """Honest availability states for source evidence."""

    AVAILABLE = "available"
    UNAVAILABLE_SOURCE = "unavailable_source"
    UNAVAILABLE_MATCH = "unavailable_match"
    INVALID_LOCATOR = "invalid_locator"
    SCAN_LIMIT = "scan_limit"


class EvidenceScope(str, Enum):
    """How the adapter bounded the lookup."""

    SESSION = "session"


@dataclass(frozen=True)
class EvidenceLocator:
    """Untrusted summary metadata used to bound a source lookup."""

    source_path: str
    session_id: str | None = None
    conversation_id: str | None = None
    start_offset: int | None = None
    end_offset: int | None = None


@dataclass(frozen=True)
class EvidenceExcerpt:
    """One bounded, provenance-bearing source excerpt."""

    source_path: str
    adapter_kind: str
    session_id: str | None
    message_id: str | None
    role: str
    timestamp: str | None
    message_ordinal: int
    excerpt: str
    truncated: bool
    content_digest_sha256: str
    scope: EvidenceScope = EvidenceScope.SESSION


@dataclass(frozen=True)
class EvidenceResult:
    """Adapter return value: status plus zero or more excerpts."""

    status: EvidenceStatus
    excerpts: tuple[EvidenceExcerpt, ...] = field(default_factory=tuple)
    adapter_kind: str | None = None
    source_path: str | None = None
    reason: str | None = None
    scope: EvidenceScope | None = None
    partial: bool = False
    partial_reason: str | None = None

    @property
    def available(self) -> bool:
        return self.status is EvidenceStatus.AVAILABLE and bool(self.excerpts)

"""Shared complete-prefix types for incremental JSONL adapters."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass


@dataclass(frozen=True)
class RawLineOutcome:
    """Auditable outcome for one complete raw line before the prefix boundary."""

    start: int
    end: int
    outcome: str
    message_index: int | None = None


@dataclass(frozen=True)
class CompletePrefixView:
    """Canonical messages plus byte commitment for one selected prefix."""

    messages: list[dict]
    byte_ranges: list[tuple[int, int]]
    line_outcomes: list[RawLineOutcome]
    complete_boundary: int
    prefix_sha256: str
    device: int
    inode: int
    raw_prefix: bytes
    session_meta: dict | None = None
    session_meta_digest: str | None = None


def prefix_boundary(raw: bytes) -> int:
    """Byte offset after the last complete newline, or zero when absent."""
    return raw.rfind(b"\n") + 1


def prefix_sha256(prefix: bytes) -> str:
    return hashlib.sha256(prefix).hexdigest()


def complete_line_outcomes_cover_prefix(
    outcomes: list[RawLineOutcome], complete_boundary: int
) -> bool:
    """True when every complete line byte range is accounted for once."""
    if complete_boundary <= 0:
        return not outcomes
    covered = 0
    expected = 0
    for item in outcomes:
        if item.start != expected or item.end <= item.start:
            return False
        expected = item.end
        covered += item.end - item.start
    return expected == complete_boundary and covered == complete_boundary

"""Secure source-byte observation for CG-2 promotion and reconciliation.

Reads canonical source paths with the same SHA-256 definition used by candidate
build (`hashlib.sha256` over full file bytes).  Identity normalization uses
``file_generation_contract.canonical_source_path``; this module does not claim
``openat2`` TOCTOU defense — callers must hold the owner ``source_flock`` when
observation must align with promotion.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from file_generation_contract import canonical_source_path


class SourceObservationError(OSError):
    """A canonical source cannot be observed."""


@dataclass(frozen=True)
class SourceObservation:
    canonical_path: str
    source_hash: str
    byte_length: int
    observed_at: str

    @property
    def exists(self) -> bool:
        return self.byte_length >= 0


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def read_source_bytes(canonical_path: str | Path) -> bytes:
    """Read the full current bytes of a canonical source path."""

    path = Path(canonical_source_path(canonical_path))
    if not path.is_file():
        raise SourceObservationError(f"source is not a readable file: {path}")
    try:
        return path.read_bytes()
    except OSError as exc:
        raise SourceObservationError(f"cannot read source {path}: {exc}") from exc


def source_content_hash(source_bytes: bytes) -> str:
    return hashlib.sha256(source_bytes).hexdigest()


def observe_source_bytes(canonical_path: str | Path) -> SourceObservation:
    """Return a private snapshot observation of the current source bytes."""

    canonical = canonical_source_path(canonical_path)
    payload = read_source_bytes(canonical)
    return SourceObservation(
        canonical_path=canonical,
        source_hash=source_content_hash(payload),
        byte_length=len(payload),
        observed_at=_utc_now(),
    )


def observe_source_hash(canonical_path: str | Path) -> str:
    """Return the current SHA-256 content hash for a canonical source path."""

    return observe_source_bytes(canonical_path).source_hash


def observation_matches_manifest(
    observation: SourceObservation, manifest_source_hash: str
) -> bool:
    return observation.source_hash == manifest_source_hash

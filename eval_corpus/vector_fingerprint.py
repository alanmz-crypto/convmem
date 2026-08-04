"""Canonical vector validation and fingerprints for embedding evidence."""

from __future__ import annotations

import hashlib
import math
import struct
from collections.abc import Iterable, Sequence
from typing import Any


class VectorIntegrityError(ValueError):
    """A vector cannot be used as evaluation evidence."""


SERIALIZATION_VERSION = "matrix_fingerprint_v1"


def _float32_bytes(value: float) -> bytes:
    numeric = float(value)
    if not math.isfinite(numeric):
        raise VectorIntegrityError("vector contains NaN or infinity")
    # Signed zero is numerically equivalent and may be normalized by a storage
    # round-trip.  Canonical evidence therefore hashes both signs as +0.0.
    if numeric == 0.0:
        numeric = 0.0
    try:
        return struct.pack("<f", numeric)
    except (OverflowError, struct.error) as exc:
        raise VectorIntegrityError(f"value cannot be represented as float32: {value!r}") from exc


def canonical_float32(value: float) -> float:
    """Return the exact finite float32 value used by persistence."""
    return struct.unpack("<f", _float32_bytes(value))[0]


def validate_vector(
    vector: Sequence[float] | Iterable[float],
    *,
    expected_dimension: int | None = None,
    require_nonzero_norm: bool = True,
) -> dict[str, Any]:
    """Validate and describe the actual float32 vector representation."""
    values = [canonical_float32(float(value)) for value in vector]
    if expected_dimension is not None and len(values) != int(expected_dimension):
        raise VectorIntegrityError(
            f"vector dimension {len(values)} != expected {expected_dimension}"
        )
    norm_sq = sum(float(value) * float(value) for value in values)
    norm = math.sqrt(norm_sq)
    if require_nonzero_norm and norm == 0.0:
        raise VectorIntegrityError("zero-norm vector is not valid retrieval evidence")
    return {
        "dimension": len(values),
        "finite": True,
        "norm": norm,
        "values": values,
    }


def vector_fingerprint_v1(vector: Sequence[float] | Iterable[float]) -> str:
    """Hash one canonical float32 vector, without embedding its semantic ID."""
    values = validate_vector(vector)["values"]
    digest = hashlib.sha256()
    digest.update(struct.pack(">I", len(values)))
    for value in values:
        digest.update(_float32_bytes(value))
    return digest.hexdigest()


def matrix_fingerprint_v1(rows: Iterable[tuple[str, Sequence[float]]]) -> str:
    """Hash sorted UTF-8 unit IDs and the exact float32 vectors they carry."""
    normalized: list[tuple[str, list[float]]] = []
    seen: set[str] = set()
    for unit_id, vector in rows:
        uid = str(unit_id)
        if uid in seen:
            raise VectorIntegrityError(f"duplicate unit id in vector matrix: {uid}")
        seen.add(uid)
        normalized.append((uid, validate_vector(vector)["values"]))

    digest = hashlib.sha256()
    for unit_id, values in sorted(normalized, key=lambda row: row[0].encode("utf-8")):
        raw_id = unit_id.encode("utf-8")
        digest.update(struct.pack(">I", len(raw_id)))
        digest.update(raw_id)
        digest.update(struct.pack(">I", len(values)))
        for value in values:
            digest.update(_float32_bytes(value))
    return digest.hexdigest()


__all__ = [
    "SERIALIZATION_VERSION",
    "VectorIntegrityError",
    "canonical_float32",
    "matrix_fingerprint_v1",
    "validate_vector",
    "vector_fingerprint_v1",
]

"""Metadata-complete corpus fingerprint (Architecture Rev 1 / Exec Rev 2)."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from eval_corpus.io_atomic import sha256_bytes


def canonical_unit_json_bytes(unit: dict[str, Any]) -> bytes:
    """UTF-8 JSON with sorted keys, no trailing whitespace (no trailing newline)."""
    return json.dumps(unit, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )


def unit_hash_hex(unit: dict[str, Any]) -> str:
    return sha256_bytes(canonical_unit_json_bytes(unit))


def unit_hash_digest(unit: dict[str, Any]) -> bytes:
    return hashlib.sha256(canonical_unit_json_bytes(unit)).digest()


def corpus_fingerprint_hex(units: list[dict[str, Any]]) -> str:
    """SHA-256 of concatenated raw 32-byte unit digests in id-sorted order."""
    ordered = sorted(units, key=lambda u: str(u.get("id") or "").encode("utf-8"))
    concat = b"".join(unit_hash_digest(u) for u in ordered)
    return hashlib.sha256(concat).hexdigest()


def package_jsonl_bytes(units: list[dict[str, Any]]) -> bytes:
    """\\n-delimited canonical JSON lines in id order, with trailing newline per line."""
    ordered = sorted(units, key=lambda u: str(u.get("id") or "").encode("utf-8"))
    parts = [canonical_unit_json_bytes(u) + b"\n" for u in ordered]
    return b"".join(parts)


def package_sha256_hex(units: list[dict[str, Any]]) -> str:
    return sha256_bytes(package_jsonl_bytes(units))

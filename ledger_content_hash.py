"""Canonical semantic hashes for governed ledger units (schema v1)."""

from __future__ import annotations

import hashlib
import json
import unicodedata

HASH_SCHEMA_VERSION = 1
SEMANTIC_FIELDS = (
    "ledger_id", "kind", "status", "title", "summary", "rationale",
    "relates_to", "confidence", "domain", "site", "notes", "result",
    "alternatives_rejected", "constraints",
)


def _text(value: object) -> object:
    return unicodedata.normalize("NFC", value) if isinstance(value, str) else value


def canonical_semantic_record(record: dict) -> dict:
    """Return the v1 semantic projection; operational fields never enter it."""
    out = {"hash_schema_version": HASH_SCHEMA_VERSION}
    for field in SEMANTIC_FIELDS:
        value = record.get(field)
        if field == "ledger_id":
            value = record.get("ledger_id", record.get("id"))
        elif field == "kind":
            value = record.get("kind", record.get("ledger_kind", record.get("type")))
        elif field in ("alternatives_rejected", "constraints"):
            value = list(value or [])
        out[field] = _text(value)
    return out


def ledger_content_hash(record: dict) -> str:
    """SHA-256 lowercase hex of the stable semantic representation."""
    raw = json.dumps(
        canonical_semantic_record(record), sort_keys=True,
        separators=(",", ":"), ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()

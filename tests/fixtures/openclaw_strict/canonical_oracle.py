"""Independent canonical JSON oracle A (fixture-owned; T0b).

Strict raw parse requires input bytes already equal the canonical serialization.
Reordered keys or insignificant whitespace are rejected — not repaired by sorting
on output. Fixture-only algorithm digests are never source-component hashes.
Does not import production canonical_json.
"""
# pylint: disable=R0801  # independent oracle specimen; sharing would couple oracle A to peers

from __future__ import annotations

import hashlib
import json
import math
import re
from typing import Any


class CanonicalOracleError(ValueError):
    """Independent oracle A rejection."""


_SURROGATE = re.compile(r"[\ud800-\udfff]")


def _reject_surrogates(value: Any, path: str = "$") -> None:
    if isinstance(value, str):
        if _SURROGATE.search(value):
            raise CanonicalOracleError(f"surrogate:{path}")
    elif isinstance(value, list):
        for i, item in enumerate(value):
            _reject_surrogates(item, f"{path}[{i}]")
    elif isinstance(value, dict):
        for key, item in value.items():
            _reject_surrogates(key, f"{path}.key")
            _reject_surrogates(item, f"{path}.{key}")


def _reject_nonfinite(value: Any, path: str = "$") -> None:
    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            raise CanonicalOracleError(f"nonfinite:{path}")
    elif isinstance(value, list):
        for i, item in enumerate(value):
            _reject_nonfinite(item, f"{path}[{i}]")
    elif isinstance(value, dict):
        for key, item in value.items():
            _reject_nonfinite(item, f"{path}.{key}")


def _reject_constant(token: str) -> None:
    raise CanonicalOracleError(f"constant:{token}")


def _object_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    seen: set[str] = set()
    out: dict[str, Any] = {}
    for key, value in pairs:
        if key in seen:
            raise CanonicalOracleError(f"duplicate_key:{key}")
        seen.add(key)
        out[key] = value
    return out


def encode_canonical_bytes(value: Any) -> bytes:
    """Encode with UTF-8, sorted keys, compact separators, no NaN."""
    _reject_surrogates(value)
    _reject_nonfinite(value)
    try:
        return json.dumps(
            value,
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    except (TypeError, ValueError, UnicodeEncodeError) as exc:
        raise CanonicalOracleError(f"encode:{exc}") from exc


def parse_strict_raw(payload: bytes | str) -> Any:
    """Parse only when raw input bytes already equal the canonical serialization."""
    if isinstance(payload, str):
        raw = payload.encode("utf-8")
    else:
        raw = payload
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise CanonicalOracleError("utf8") from exc
    try:
        value = json.loads(
            text, object_pairs_hook=_object_pairs, parse_constant=_reject_constant
        )
    except json.JSONDecodeError as exc:
        raise CanonicalOracleError(f"json:{exc}") from exc
    _reject_surrogates(value)
    _reject_nonfinite(value)
    canonical = encode_canonical_bytes(value)
    if raw != canonical:
        raise CanonicalOracleError("noncanonical_raw_bytes")
    return value


# Back-compat name used by older call sites — identical to strict raw parse.
parse_canonical_json = parse_strict_raw


def digest_sha256(value: Any) -> str:
    """Fixture-only algorithm digest over a value — never a source component hash."""
    return f"sha256:{hashlib.sha256(encode_canonical_bytes(value)).hexdigest()}"


def reject_unknown_fields(obj: dict[str, Any], allowed: set[str]) -> None:
    extra = set(obj) - allowed
    if extra:
        raise CanonicalOracleError(f"unknown_fields:{sorted(extra)}")


def reject_missing_fields(obj: dict[str, Any], required: set[str]) -> None:
    missing = required - set(obj)
    if missing:
        raise CanonicalOracleError(f"missing_fields:{sorted(missing)}")

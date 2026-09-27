"""Independent canonical JSON oracle B (fixture-owned; T0b).

Genuinely independent of oracle A: hand-builds canonical UTF-8 without
json.dumps(sort_keys=True). Strict raw parse still requires raw == canonical.
Does not import production canonical_json or canonical_oracle.
"""
# pylint: disable=R0801  # independent oracle specimen; sharing would couple oracle B to peers

from __future__ import annotations

import hashlib
import json
import math
import re
from typing import Any


class CanonicalOracleBError(ValueError):
    """Independent oracle B rejection."""


_SURROGATE = re.compile(r"[\ud800-\udfff]")


def _reject_surrogates(value: Any, path: str = "$") -> None:
    if isinstance(value, str):
        if _SURROGATE.search(value):
            raise CanonicalOracleBError(f"surrogate:{path}")
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
            raise CanonicalOracleBError(f"nonfinite:{path}")
    elif isinstance(value, list):
        for i, item in enumerate(value):
            _reject_nonfinite(item, f"{path}[{i}]")
    elif isinstance(value, dict):
        for key, item in value.items():
            _reject_nonfinite(item, f"{path}.{key}")


def _escape_string(s: str) -> str:
    # Use json.dumps only for string escaping of a scalar — not for object key order.
    return json.dumps(s, ensure_ascii=False)


def _encode_node(value: Any) -> str:
    if value is None:
        return "null"
    if value is True:
        return "true"
    if value is False:
        return "false"
    if isinstance(value, int) and not isinstance(value, bool):
        return str(value)
    if isinstance(value, float):
        raise CanonicalOracleBError("float_forbidden_in_strict_fields")
    if isinstance(value, str):
        return _escape_string(value)
    if isinstance(value, list):
        return "[" + ",".join(_encode_node(item) for item in value) + "]"
    if isinstance(value, dict):
        parts: list[str] = []
        for key in sorted(value.keys()):
            if not isinstance(key, str):
                raise CanonicalOracleBError("non_string_key")
            parts.append(_escape_string(key) + ":" + _encode_node(value[key]))
        return "{" + ",".join(parts) + "}"
    raise CanonicalOracleBError(f"unsupported_type:{type(value)!r}")


def encode_canonical_bytes(value: Any) -> bytes:
    _reject_surrogates(value)
    _reject_nonfinite(value)
    return _encode_node(value).encode("utf-8")


def _object_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    seen: set[str] = set()
    out: dict[str, Any] = {}
    for key, value in pairs:
        if key in seen:
            raise CanonicalOracleBError(f"duplicate_key:{key}")
        seen.add(key)
        out[key] = value
    return out


def _reject_constant(token: str) -> None:
    raise CanonicalOracleBError(f"constant:{token}")


def parse_strict_raw(payload: bytes | str) -> Any:
    """Parse only when raw input bytes already equal oracle-B canonical bytes."""
    if isinstance(payload, str):
        raw = payload.encode("utf-8")
    else:
        raw = payload
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise CanonicalOracleBError("utf8") from exc
    try:
        value = json.loads(
            text, object_pairs_hook=_object_pairs, parse_constant=_reject_constant
        )
    except json.JSONDecodeError as exc:
        raise CanonicalOracleBError(f"json:{exc}") from exc
    _reject_surrogates(value)
    _reject_nonfinite(value)
    canonical = encode_canonical_bytes(value)
    if raw != canonical:
        raise CanonicalOracleBError("noncanonical_raw_bytes")
    return value


def digest_sha256(value: Any) -> str:
    """Fixture-only algorithm digest — never a source component hash."""
    return f"sha256:{hashlib.sha256(encode_canonical_bytes(value)).hexdigest()}"

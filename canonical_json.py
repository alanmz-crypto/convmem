"""Shared deterministic JSON byte encoding primitive."""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any


def canonical_json_bytes(
    value: Any,
    *,
    validate: Callable[[Any], None],
    error_type: type[ValueError],
) -> bytes:
    """Validate a value and encode it with ConvMem's stable JSON profile."""

    validate(value)
    try:
        return json.dumps(
            value,
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    except (TypeError, UnicodeEncodeError, ValueError) as exc:
        raise error_type(f"value is not canonical JSON: {exc}") from exc

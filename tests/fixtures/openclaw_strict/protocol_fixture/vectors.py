"""Known-answer vectors for independent canonical parsers (fixture-only).

ACCEPT payloads are already-canonical raw UTF-8 bytes. REJECT payloads include
reordered keys and whitespace variants that must fail strict raw parse.
These algorithm self-checks are never source-component or authority hashes.
"""

from __future__ import annotations

from typing import Any

# value + already-canonical raw bytes (must parse under strict raw equality).
KNOWN_ANSWER_OBJECTS: list[dict[str, Any]] = [
    {
        "name": "empty_object",
        "value": {},
        "canonical_utf8": b"{}",
    },
    {
        "name": "sorted_keys",
        "value": {"a": 1, "b": 2},
        "canonical_utf8": b'{"a":1,"b":2}',
    },
    {
        "name": "nested_null",
        "value": {"schema": "convmem.error.v1", "x": None},
        "canonical_utf8": b'{"schema":"convmem.error.v1","x":null}',
    },
    {
        "name": "array_stable",
        "value": {"items": [1, "two", False]},
        "canonical_utf8": b'{"items":[1,"two",false]}',
    },
]

REJECT_PAYLOADS: list[dict[str, Any]] = [
    {"name": "duplicate_key", "payload": b'{"a":1,"a":2}'},
    {"name": "trailing_garbage", "payload": b'{"a":1}x'},
    {"name": "nan_literal", "payload": b'{"a":NaN}'},
    {"name": "surrogate", "payload": b'{"a":"\\ud800"}'},
    {"name": "reordered_keys", "payload": b'{"b":2,"a":1}'},
    {"name": "whitespace_variant", "payload": b'{ "a": 1}'},
    {"name": "pretty_printed", "payload": b'{\n  "a": 1\n}'},
]

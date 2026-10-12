"""Streaming complete-prefix digest must match the canonical prefix hash."""

from __future__ import annotations

from pathlib import Path

import pytest

from adapters.jsonl_prefix import (
    prefix_boundary,
    prefix_sha256,
    streaming_complete_prefix_digest_for_path,
)


@pytest.mark.parametrize("bufsize", range(1, 17))
@pytest.mark.parametrize(
    "payload",
    [
        b"\n",
        b'{"a":1}\n\n{"b":2}\n',
        b'{"type":"session_meta"}\n{"type":"item"}\n',
        b"partial",
        b"partial\n",
    ],
    ids=["blank_line", "double_jsonl", "two_lines", "no_newline", "one_line"],
)
def test_streaming_digest_matches_prefix_sha256(
    tmp_path: Path, bufsize: int, payload: bytes
) -> None:
    path = tmp_path / "sample.jsonl"
    path.write_bytes(payload)
    boundary = prefix_boundary(payload)
    expected = prefix_sha256(payload[:boundary])
    actual = streaming_complete_prefix_digest_for_path(path, bufsize=bufsize)
    assert actual == expected


def test_streaming_digest_double_jsonl_at_bufsize_eight(tmp_path: Path) -> None:
    payload = b'{"a":1}\n\n{"b":2}\n'
    path = tmp_path / "rollout.jsonl"
    path.write_bytes(payload)
    expected = prefix_sha256(payload[: prefix_boundary(payload)])
    assert streaming_complete_prefix_digest_for_path(path, bufsize=8) == expected

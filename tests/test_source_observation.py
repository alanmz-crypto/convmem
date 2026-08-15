"""Tests for secure source observation."""

from __future__ import annotations

from pathlib import Path

import pytest

from source_observation import (
    SourceObservationError,
    observe_source_bytes,
    observe_source_hash,
    source_content_hash,
)


def test_source_content_hash_is_sha256() -> None:
    payload = b"hello"
    assert source_content_hash(payload) == observe_source_hash_from_bytes(payload)


def observe_source_hash_from_bytes(payload: bytes) -> str:
    return source_content_hash(payload)


def test_observe_source_hash_reads_file(tmp_path: Path) -> None:
    source = tmp_path / "note.jsonl"
    source.write_bytes(b"line-one\n")
    observed = observe_source_bytes(source)
    assert observed.canonical_path == str(source.resolve())
    assert observed.source_hash == observe_source_hash(source)
    assert observed.byte_length == len(b"line-one\n")


def test_missing_source_raises(tmp_path: Path) -> None:
    missing = tmp_path / "gone.jsonl"
    with pytest.raises(SourceObservationError):
        observe_source_hash(missing)

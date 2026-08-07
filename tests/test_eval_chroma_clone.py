"""Adversarial tests for disposable Chroma-root cloning."""

from __future__ import annotations

import os

import pytest

from eval_corpus.chroma_clone import clone_chroma_root
from eval_corpus.secure_fs import (
    FilesystemAuthorizationError,
    assert_regular_evidence_tree,
)


def _source_tree(root):
    (root / "index").mkdir(parents=True)
    (root / "chroma.sqlite3").write_bytes(b"sqlite fixture\n")
    (root / "index" / "data.bin").write_bytes(b"vector fixture\0\1\n")


def test_clone_is_fresh_regular_file_only_and_content_identical(tmp_path):
    source = tmp_path / "authoritative"
    parent = tmp_path / "attempts"
    source.mkdir()
    parent.mkdir()
    _source_tree(source)

    receipt = clone_chroma_root(
        source,
        parent / "clone-0",
        approved_source_root=tmp_path,
        approved_destination_parent=parent,
    )

    assert receipt["schema_version"] == "chroma_disposable_clone_v1"
    assert receipt["source_content_fingerprint"] == receipt["clone_content_fingerprint"]
    assert receipt["source_entry_count"] == receipt["clone_entry_count"]
    assert (parent / "clone-0" / "index" / "data.bin").read_bytes() == b"vector fixture\0\1\n"
    assert_regular_evidence_tree(parent / "clone-0")


def test_clone_rejects_symlink_and_hardlink_sources(tmp_path):
    source = tmp_path / "authoritative"
    parent = tmp_path / "attempts"
    source.mkdir()
    parent.mkdir()
    _source_tree(source)
    outside = tmp_path / "outside.txt"
    outside.write_text("outside", encoding="utf-8")
    (source / "link").symlink_to(outside)
    with pytest.raises(FilesystemAuthorizationError, match="symlink"):
        clone_chroma_root(
            source,
            parent / "symlink-clone",
            approved_source_root=tmp_path,
            approved_destination_parent=parent,
        )

    (source / "link").unlink()
    os.link(source / "chroma.sqlite3", source / "alias.sqlite3")
    with pytest.raises(FilesystemAuthorizationError, match="singly-linked"):
        clone_chroma_root(
            source,
            parent / "hardlink-clone",
            approved_source_root=tmp_path,
            approved_destination_parent=parent,
        )


def test_clone_rejects_existing_destination_and_overlap(tmp_path):
    source = tmp_path / "authoritative"
    parent = tmp_path / "attempts"
    source.mkdir()
    parent.mkdir()
    _source_tree(source)
    existing = parent / "existing"
    existing.mkdir()
    with pytest.raises(FilesystemAuthorizationError, match="absent"):
        clone_chroma_root(
            source,
            existing,
            approved_source_root=tmp_path,
            approved_destination_parent=parent,
        )
    with pytest.raises(FilesystemAuthorizationError, match="overlap"):
        clone_chroma_root(
            source,
            source / "nested",
            approved_source_root=tmp_path,
            approved_destination_parent=source,
        )

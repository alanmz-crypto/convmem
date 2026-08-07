"""Adversarial tests for the evaluation attempt filesystem boundary."""

from __future__ import annotations

import json
import os

import pytest

from eval_corpus.secure_fs import (
    FilesystemAuthorizationError,
    assert_contained_no_symlink,
    assert_nonoverlapping_roots,
    assert_regular_evidence_tree,
    copy_immutable_input,
    create_absent_attempt_root,
    write_absent_json,
)


def test_attempt_roots_are_absent_direct_children_and_nonoverlapping(tmp_path):
    parent = tmp_path / "attempts"
    parent.mkdir()
    baseline = parent / "baseline"
    challenger = parent / "challenger"
    assert create_absent_attempt_root(baseline, parent)["kind"] == "directory"
    assert create_absent_attempt_root(challenger, parent)["kind"] == "directory"
    assert_nonoverlapping_roots(baseline, challenger)
    with pytest.raises(FilesystemAuthorizationError, match="absent"):
        create_absent_attempt_root(baseline, parent)
    with pytest.raises(FilesystemAuthorizationError, match="overlap"):
        assert_nonoverlapping_roots(baseline, baseline / "nested")


def test_component_containment_rejects_prefix_and_symlink(tmp_path):
    root = tmp_path / "attempts"
    root.mkdir()
    with pytest.raises(FilesystemAuthorizationError, match="escapes"):
        assert_contained_no_symlink(tmp_path / "attempts-old" / "x", root)
    outside = tmp_path / "outside"
    outside.mkdir()
    (root / "redirect").symlink_to(outside, target_is_directory=True)
    with pytest.raises(FilesystemAuthorizationError, match="symlink"):
        assert_contained_no_symlink(root / "redirect" / "x", root)


def test_immutable_input_rejects_hardlink_and_copies_exact_bytes(tmp_path):
    root = tmp_path / "attempt"
    root.mkdir()
    source = root / "source.jsonl"
    source.write_bytes(b'{"id":"one"}\n')
    (root / "inputs").mkdir()
    copy = root / "inputs" / "package.jsonl"
    copied = copy_immutable_input(source, copy, approved_root=root)
    assert copy.read_bytes() == source.read_bytes()
    assert copied["source"]["link_count"] == 1
    assert copied["destination"]["link_count"] == 1
    alias = root / "alias.jsonl"
    os.link(source, alias)
    with pytest.raises(FilesystemAuthorizationError, match="hard-linked"):
        copy_immutable_input(alias, root / "inputs" / "alias.jsonl", approved_root=root)


def test_evidence_tree_rejects_links(tmp_path):
    root = tmp_path / "evidence"
    root.mkdir()
    (root / "report.json").write_text("{}\n", encoding="utf-8")
    assert_regular_evidence_tree(root)
    (root / "report-link.json").symlink_to(root / "report.json")
    with pytest.raises(FilesystemAuthorizationError, match="symlink"):
        assert_regular_evidence_tree(root)


def test_absent_json_publisher_creates_one_regular_file(tmp_path):
    root = tmp_path / "attempt"
    root.mkdir()
    output = root / "report.json"
    receipt = write_absent_json(output, {"status": "OK"}, approved_root=root)
    assert json.loads(output.read_text(encoding="utf-8")) == {"status": "OK"}
    assert receipt["kind"] == "regular"
    assert receipt["link_count"] == 1
    assert not list(root.glob(".report.json.*.tmp"))


def test_absent_json_publisher_rejects_preexisting_file_and_symlink(tmp_path):
    root = tmp_path / "attempt"
    root.mkdir()
    existing = root / "existing.json"
    existing.write_text("sentinel\n", encoding="utf-8")
    with pytest.raises(FilesystemAuthorizationError, match="absent"):
        write_absent_json(existing, {"status": "MUTATE"}, approved_root=root)
    assert existing.read_text(encoding="utf-8") == "sentinel\n"

    target = root / "target.json"
    outside = tmp_path / "outside.json"
    outside.write_text("outside\n", encoding="utf-8")
    target.symlink_to(outside)
    with pytest.raises(FilesystemAuthorizationError, match="absent"):
        write_absent_json(target, {"status": "FOLLOW"}, approved_root=root)
    assert target.is_symlink()
    assert outside.read_text(encoding="utf-8") == "outside\n"

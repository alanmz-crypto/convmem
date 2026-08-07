"""Gate 2 marker/archive/release receipts are deterministic and fail closed."""

from __future__ import annotations

import json

import pytest

from eval_corpus.evidence_release import (
    EVIDENCE_MARKER_NAME,
    create_deterministic_archive,
    inventory_evidence_directory,
    write_gate2_marker,
    write_release_receipt,
)
from eval_corpus.secure_fs import FilesystemAuthorizationError


def _make_evidence(root):
    root.mkdir()
    (root / "raw").mkdir()
    (root / "raw" / "stdout.txt").write_bytes(b"ok\n")
    (root / "report.json").write_text('{"ok":true}\n', encoding="utf-8")


def test_inventory_root_is_stable_and_marker_is_last(tmp_path):
    root = tmp_path / "evidence"
    _make_evidence(root)
    before = inventory_evidence_directory(root)
    result = write_gate2_marker(
        root,
        {
            "technical_status": "VALID",
            "evidence_verdict": "INCONCLUSIVE",
            "run_ids": ["r1"],
        },
    )
    assert result["body"]["inventory_root_sha256"] == before["inventory_root_sha256"]
    assert (root / EVIDENCE_MARKER_NAME).is_file()
    with pytest.raises(FilesystemAuthorizationError):
        write_gate2_marker(root, {"technical_status": "VALID", "evidence_verdict": "NOT_ISSUED"})


def test_marker_rejects_quality_verdict_for_invalid_run(tmp_path):
    root = tmp_path / "evidence"
    _make_evidence(root)
    with pytest.raises(ValueError, match="NOT_ISSUED"):
        write_gate2_marker(
            root,
            {"technical_status": "INVALID", "evidence_verdict": "INCONCLUSIVE"},
        )


def test_archive_and_receipt_are_reproducible(tmp_path):
    root = tmp_path / "evidence"
    _make_evidence(root)
    marker = write_gate2_marker(
        root,
        {"technical_status": "VALID", "evidence_verdict": "BETTER"},
    )
    archive_one = create_deterministic_archive(root, tmp_path / "one.tar.gz")
    archive_two = create_deterministic_archive(root, tmp_path / "two.tar.gz")
    assert archive_one["archive_sha256"] == archive_two["archive_sha256"]
    receipt = write_release_receipt(
        tmp_path / "release-receipt.json",
        marker_sha256=marker["marker_sha256"],
        inventory_root_sha256=marker["body"]["inventory_root_sha256"],
        archive=archive_one,
        approved_source_git_oid="a" * 40,
        run_ids=["r1"],
        kiro_review={"identity": "kiro", "timestamp": "2026-08-07T00:00:00Z"},
    )
    loaded = json.loads((tmp_path / "release-receipt.json").read_text())
    assert loaded["archive_sha256"] == archive_one["archive_sha256"]
    assert receipt["receipt_sha256"]


def test_evidence_tree_rejects_symlink(tmp_path):
    root = tmp_path / "evidence"
    _make_evidence(root)
    (root / "bad").symlink_to(root / "report.json")
    with pytest.raises(FilesystemAuthorizationError):
        inventory_evidence_directory(root)

"""Evidence release wrappers require operation-bound authorization."""

from __future__ import annotations

import json

import pytest

from eval_corpus.evidence_release import (
    create_authorized_archive,
    write_authorized_gate2_marker,
    write_authorized_release_receipt,
)
from eval_corpus.run_manifest import AuthContext, bind_evidence_release
from eval_corpus.secure_fs import FilesystemAuthorizationError


def _auth(root, operation):
    paths = {
        "evidence_root": root / "evidence",
        "archive_path": root / "evidence.tar.gz",
        "receipt_path": root / "release.json",
    }
    auth = bind_evidence_release(
        operation=operation,
        authorize_fixture=True,
        run_manifest_path=None,
        runtime=paths,
    )
    return paths, auth


def test_marker_archive_and_receipt_wrappers_require_matching_operation(tmp_path):
    paths, marker_auth = _auth(tmp_path, "evidence_assembly")
    paths["evidence_root"].mkdir()
    (paths["evidence_root"] / "report.json").write_text('{"ok":true}\n', encoding="utf-8")
    marker = write_authorized_gate2_marker(
        paths["evidence_root"],
        {"technical_status": "VALID", "evidence_verdict": "INCONCLUSIVE"},
        auth=marker_auth,
    )

    _, archive_auth = _auth(tmp_path, "archive_creation")
    archive = create_authorized_archive(
        paths["evidence_root"], paths["archive_path"], auth=archive_auth
    )
    _, receipt_auth = _auth(tmp_path, "release_receipt")
    result = write_authorized_release_receipt(
        paths["receipt_path"],
        auth=receipt_auth,
        marker_sha256=marker["marker_sha256"],
        inventory_root_sha256=marker["body"]["inventory_root_sha256"],
        archive=archive,
        approved_source_git_oid="a" * 40,
        run_ids=["r1"],
        kiro_review={"identity": "fixture"},
    )
    assert result["receipt_sha256"]
    assert json.loads(paths["receipt_path"].read_text())["archive_sha256"] == archive["archive_sha256"]

    with pytest.raises(PermissionError):
        create_authorized_archive(
            paths["evidence_root"], tmp_path / "other.tar.gz", auth=marker_auth
        )


def test_release_capability_binds_paths_and_is_single_use(tmp_path):
    paths, auth = _auth(tmp_path, "evidence_assembly")
    paths["evidence_root"].mkdir()
    with pytest.raises(PermissionError, match="release path mismatch"):
        write_authorized_gate2_marker(tmp_path / "other", {}, auth=auth)
    write_authorized_gate2_marker(
        paths["evidence_root"],
        {"technical_status": "VALID", "evidence_verdict": "INCONCLUSIVE"},
        auth=auth,
    )
    with pytest.raises(PermissionError, match="already been consumed"):
        write_authorized_gate2_marker(
            paths["evidence_root"],
            {"technical_status": "VALID", "evidence_verdict": "INCONCLUSIVE"},
            auth=auth,
        )


def test_release_wrappers_reject_forged_context(tmp_path):
    root = tmp_path / "evidence"
    root.mkdir()
    forged = AuthContext(
        execution_mode="fixture",
        require_corpus_acceptance=False,
        manifest={"execution_mode": "fixture", "status": "approved"},
        operation="evidence_assembly",
    )
    with pytest.raises(PermissionError, match="not issued"):
        write_authorized_gate2_marker(
            root,
            {"technical_status": "VALID", "evidence_verdict": "INCONCLUSIVE"},
            auth=forged,
        )


def test_receipt_requires_matching_marker_and_archive_bytes(tmp_path):
    paths, marker_auth = _auth(tmp_path, "evidence_assembly")
    paths["evidence_root"].mkdir()
    (paths["evidence_root"] / "report.json").write_text("{}\n", encoding="utf-8")
    marker = write_authorized_gate2_marker(
        paths["evidence_root"],
        {"technical_status": "VALID", "evidence_verdict": "INCONCLUSIVE"},
        auth=marker_auth,
    )
    _, archive_auth = _auth(tmp_path, "archive_creation")
    archive = create_authorized_archive(
        paths["evidence_root"], paths["archive_path"], auth=archive_auth
    )
    _, receipt_auth = _auth(tmp_path, "release_receipt")
    with pytest.raises(FilesystemAuthorizationError, match="marker hash"):
        write_authorized_release_receipt(
            paths["receipt_path"],
            auth=receipt_auth,
            marker_sha256="0" * 64,
            inventory_root_sha256=marker["body"]["inventory_root_sha256"],
            archive=archive,
            approved_source_git_oid="a" * 40,
            run_ids=["r1"],
            kiro_review={"identity": "fixture"},
        )

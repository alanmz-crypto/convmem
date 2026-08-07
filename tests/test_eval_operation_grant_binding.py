"""Manifest-bound operation grants reject replay and binding drift."""

from __future__ import annotations

import copy
import json
from datetime import datetime, timezone

import pytest

from eval_corpus.run_manifest import (
    canonical_manifest_body_sha256,
    consume_operation_grant,
    make_fixture_run_manifest,
)


def _fixture(root):
    capture_dir = root / "capture"
    manifest = make_fixture_run_manifest(
        operations=["capture"],
        paths={"capture_dir": str(capture_dir)},
    )
    manifest_path = root / "run-manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    paths = {"capture_dir": str(capture_dir)}
    grant = {
        "schema_version": "single_use_grant_v1",
        "grant_id": "grant-1",
        "attempt_id": "attempt-1",
        "run_id": "run-1",
        "operation": "capture",
        "manifest_body_sha256": canonical_manifest_body_sha256(manifest),
        "approved_paths": paths,
        "approved_git_oid": "b" * 40,
        "not_before": "2026-08-01T00:00:00Z",
        "expires_at": None,
        "max_invocations": 1,
    }
    grant_path = root / "grant.json"
    grant_path.write_text(json.dumps(grant), encoding="utf-8")
    return manifest, manifest_path, grant_path, paths


def _kwargs(manifest, manifest_path, grant_path, paths):
    return {
        "grant_path": grant_path,
        "operation": "capture",
        "manifest_path": manifest_path,
        "grant_id": "grant-1",
        "approved_paths": paths,
        "approved_git_oid": "b" * 40,
        "attempt_id": "attempt-1",
        "run_id": "run-1",
        "manifest": manifest,
        "now": datetime(2026, 8, 7, tzinfo=timezone.utc),
    }


def test_operation_grant_binds_manifest_paths_and_consumes_once(tmp_path):
    manifest, manifest_path, grant_path, paths = _fixture(tmp_path)
    result = consume_operation_grant(**_kwargs(manifest, manifest_path, grant_path, paths))
    assert result["grant"]["grant_id"] == "grant-1"
    assert not grant_path.exists()

    with pytest.raises(FileNotFoundError):
        consume_operation_grant(**_kwargs(manifest, manifest_path, grant_path, paths))


def test_operation_grant_rejects_manifest_or_path_drift_before_consumption(tmp_path):
    manifest, manifest_path, grant_path, _paths = _fixture(tmp_path)
    changed = copy.deepcopy(manifest)
    changed["paths"] = {"capture_dir": str(tmp_path / "other")}
    with pytest.raises(PermissionError, match="supplied manifest differs"):
        consume_operation_grant(
            **_kwargs(changed, manifest_path, grant_path, {"capture_dir": str(tmp_path / "other")})
        )
    assert grant_path.exists()

    with pytest.raises(PermissionError, match="approved path mismatch"):
        consume_operation_grant(
            **_kwargs(manifest, manifest_path, grant_path, {"capture_dir": str(tmp_path / "other")})
        )
    assert grant_path.exists()

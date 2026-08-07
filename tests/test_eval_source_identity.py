"""Tests for exact source/interpreter identity receipts."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from eval_corpus.source_identity import (
    SourceIdentityError,
    canonical_identity_sha256,
    collect_source_identity,
    verify_manifest_path_source_identity,
    verify_source_identity,
)


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True)


def _fixture_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init")
    _git(repo, "config", "user.email", "test@example.invalid")
    _git(repo, "config", "user.name", "Test")
    (repo / "requirements.txt").write_text("example==1\n", encoding="utf-8")
    (repo / "tracked.txt").write_text("initial\n", encoding="utf-8")
    _git(repo, "add", "requirements.txt", "tracked.txt")
    _git(repo, "commit", "-m", "fixture")
    return repo


def test_collect_and_verify_source_identity(tmp_path):
    repo = _fixture_repo(tmp_path)
    identity = collect_source_identity(repo, critical_modules=("json",))
    assert identity["clean_tracked_worktree"] is True
    assert len(identity["approved_source_git_oid"]) == 40
    assert identity["tracked_source_tree_sha256"]
    assert identity["dependency_lock_sha256"]
    assert identity["identity_sha256"] == canonical_identity_sha256(identity)
    verify_source_identity(identity, dict(identity))


def test_tracked_change_is_rejected(tmp_path):
    repo = _fixture_repo(tmp_path)
    (repo / "tracked.txt").write_text("changed\n", encoding="utf-8")
    with pytest.raises(SourceIdentityError, match="dirty"):
        collect_source_identity(repo, critical_modules=("json",))


def test_exact_import_or_lock_identity_mismatch_is_rejected(tmp_path):
    repo = _fixture_repo(tmp_path)
    approved = collect_source_identity(repo, critical_modules=("json",))
    observed = json.loads(json.dumps(approved))
    observed["dependency_lock_sha256"] = "0" * 64
    observed["identity_sha256"] = canonical_identity_sha256(observed)
    with pytest.raises(SourceIdentityError, match="dependency_lock_sha256"):
        verify_source_identity(approved, observed)
    observed = json.loads(json.dumps(approved))
    observed["critical_modules"][0]["sha256"] = "f" * 64
    observed["identity_sha256"] = canonical_identity_sha256(observed)
    with pytest.raises(SourceIdentityError, match="critical_modules"):
        verify_source_identity(approved, observed)


def test_untracked_inventory_is_observed_not_hidden(tmp_path):
    repo = _fixture_repo(tmp_path)
    (repo / "notes.txt").write_text("untracked\n", encoding="utf-8")
    identity = collect_source_identity(repo, critical_modules=("json",))
    assert identity["untracked_inventory"] == ["notes.txt"]


def test_import_shadowing_file_is_rejected(tmp_path):
    repo = _fixture_repo(tmp_path)
    (repo / "query.py").write_text("shadow\n", encoding="utf-8")
    with pytest.raises(SourceIdentityError, match="import-shadowing"):
        collect_source_identity(repo, critical_modules=("json",))


def test_symlinked_identity_input_is_rejected(tmp_path):
    target = tmp_path / "requirements.txt"
    target.write_text("example==1\n", encoding="utf-8")
    link = tmp_path / "requirements-link.txt"
    link.symlink_to(target)
    with pytest.raises(SourceIdentityError, match="symlinked"):
        from eval_corpus.source_identity import sha256_file

        sha256_file(link)


def test_manifest_path_preflight_is_fixture_noop_and_real_fail_closed(tmp_path):
    fixture = tmp_path / "fixture.json"
    fixture.write_text('{"execution_mode": "fixture"}\n', encoding="utf-8")
    assert verify_manifest_path_source_identity(fixture, repo_root=tmp_path) is None

    real = tmp_path / "real.json"
    real.write_text('{"execution_mode": "real"}\n', encoding="utf-8")
    with pytest.raises(SourceIdentityError, match="source_identity"):
        verify_manifest_path_source_identity(real, repo_root=tmp_path)

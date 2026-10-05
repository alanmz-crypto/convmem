"""A one-shot bootstrap needs a narrow, owned, reviewable grant file."""

from __future__ import annotations

import json
import runpy
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "bootstrap-incremental-jsonl.py"


def _read_grant():
    return runpy.run_path(str(SCRIPT), run_name="bootstrap_test")["_read_grant"]


def test_grant_file_binds_exact_source_and_budget(tmp_path: Path) -> None:
    source = tmp_path / "session" / "messages.jsonl"
    grant = {
        "source": str(source),
        "prefix_sha256": "a" * 64,
        "complete_boundary": 42,
        "max_chunks": 3,
        "embed_dimension": 8,
        "backup_snapshot": "verified-snapshot-id",
    }
    grant_path = tmp_path / "grant.json"
    grant_path.write_text(json.dumps(grant), encoding="utf-8")
    grant_path.chmod(0o600)
    assert _read_grant()(grant_path) == grant
    grant_path.chmod(0o644)
    with pytest.raises(ValueError, match="0600"):
        _read_grant()(grant_path)


def test_grant_rejects_missing_budget_and_symlink(tmp_path: Path) -> None:
    grant_path = tmp_path / "grant.json"
    grant_path.write_text("{}", encoding="utf-8")
    grant_path.chmod(0o600)
    with pytest.raises(ValueError, match="exactly"):
        _read_grant()(grant_path)
    alias = tmp_path / "alias.json"
    alias.symlink_to(grant_path)
    with pytest.raises(ValueError, match="symlink"):
        _read_grant()(alias)

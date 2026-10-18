"""T2 V3 crash matrix with process barriers and parent oracle."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from bootstrap_codex_v2_authority import (
    CRASH_POINT_ENV,
    claim_initial_authority,
    claim_recovery_authority,
    load_authority,
    mirror_invocation_start,
)
from tests.test_issue_286_codex_bootstrap_v2_t1 import _rollout_fixture, _v2_grant


def _run_child(state_dir: Path, grant: dict, *, crash_point: str, action: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env[CRASH_POINT_ENV] = crash_point
    payload = {"state_dir": str(state_dir), "grant": grant, "action": action}
    script = (
        "import json, os, sys\n"
        "from pathlib import Path\n"
        "payload = json.loads(sys.argv[1])\n"
        "sys.path.insert(0, os.getcwd())\n"
        "from bootstrap_codex_v2_authority import claim_initial_authority, claim_recovery_authority, mirror_invocation_start, load_authority\n"
        "state_dir = Path(payload['state_dir'])\n"
        "grant = payload['grant']\n"
        "action = payload['action']\n"
        "if action == 'initial':\n"
        "    claim_initial_authority(state_dir, grant)\n"
        "elif action == 'mirror':\n"
        "    mirror_invocation_start(state_dir, grant)\n"
        "elif action == 'recovery':\n"
        "    claim_recovery_authority(state_dir, grant)\n"
        "print(json.dumps({'ordinal': load_authority(state_dir).invocation_ordinal if load_authority(state_dir) else None}))\n"
    )
    return subprocess.run(
        [sys.executable, "-c", script, json.dumps(payload)],
        cwd=str(Path(__file__).resolve().parents[1]),
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


def _fixture(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    source, cfg, prefix, boundary = _rollout_fixture(tmp_path, monkeypatch)
    grant = _v2_grant(source, cfg, prefix_sha256=prefix, complete_boundary=boundary)
    state_root = Path(cfg["index"]["incremental_jsonl"]["state_dir"])
    from bootstrap_codex_v2 import v2_source_state_directory

    return v2_source_state_directory(state_root, grant), grant


def test_crash_after_authority_leaves_ordinal1_for_recovery(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    state_dir, grant = _fixture(tmp_path, monkeypatch)
    result = _run_child(state_dir, grant, crash_point="after_authority_fsync", action="initial")
    assert result.returncode == 91
    view = load_authority(state_dir)
    assert view is not None
    assert view.invocation_ordinal == 1
    claim_recovery_authority(state_dir, grant)
    assert load_authority(state_dir).invocation_ordinal == 2


def test_reservation_without_transaction_recovery(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    state_dir, grant = _fixture(tmp_path, monkeypatch)
    claim_initial_authority(state_dir, grant)
    assert not (state_dir / "transaction.json").exists()
    claim_recovery_authority(state_dir, grant)
    mirror_invocation_start(state_dir, grant)
    assert load_authority(state_dir).invocation_ordinal == 2


def test_journal_mirror_idempotent(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    state_dir, grant = _fixture(tmp_path, monkeypatch)
    claim_initial_authority(state_dir, grant)
    mirror_invocation_start(state_dir, grant)
    mirror_invocation_start(state_dir, grant)
    from bootstrap_codex_v2_authority import operation_root
    from bootstrap_safety import _read_jsonl

    rows = _read_jsonl(operation_root(state_dir, grant) / "invocations.jsonl")
    assert len([r for r in rows if r.get("record_type") == "start"]) == 1

def test_crash_after_journal_mirror_still_authority_ordinal1(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    state_dir, grant = _fixture(tmp_path, monkeypatch)
    claim_initial_authority(state_dir, grant)
    result = _run_child(state_dir, grant, crash_point="after_journal_mirror_fsync", action="mirror")
    assert result.returncode == 91
    assert load_authority(state_dir).invocation_ordinal == 1

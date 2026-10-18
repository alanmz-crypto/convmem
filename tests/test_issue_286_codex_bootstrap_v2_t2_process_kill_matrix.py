"""T2 V3 parent SIGKILL matrix with byte oracle (not os._exit alone)."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

from bootstrap_codex_v2_authority import (
    authority_path,
    claim_initial_authority,
    claim_recovery_authority,
    load_authority,
    mirror_invocation_start,
    publish_terminal_authority,
)
from bootstrap_codex_v2_publication import PublicationFailure
from bootstrap_codex_v2_authority import CodexBootstrapV2AuthorityError
from tests.fixtures.issue_286_t2_parent_oracle import snapshot_tree
from tests.test_issue_286_codex_bootstrap_v2_t1 import _rollout_fixture, _v2_grant

REPO = Path(__file__).resolve().parents[1]
CHILD = Path(__file__).with_name("issue_286_codex_bootstrap_t2_child.py")

KILL_STAGES = [
    "initial_authority.before_tmp_fsync",
    "initial_authority.before_dir_fsync",
    "initial_authority.after_dir_fsync",
    "journal_mirror.before_file_fsync",
    "journal_mirror.after_dir_fsync",
    "recovery_authority.after_dir_fsync",
    "terminal_receipt.after_dir_fsync",
    "terminal_authority.after_dir_fsync",
]


def _fixture(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    source, cfg, prefix, boundary = _rollout_fixture(tmp_path, monkeypatch)
    grant = _v2_grant(source, cfg, prefix_sha256=prefix, complete_boundary=boundary)
    state_root = Path(cfg["index"]["incremental_jsonl"]["state_dir"])
    from bootstrap_codex_v2 import v2_source_state_directory

    state_dir = v2_source_state_directory(state_root, grant)
    chroma = Path(cfg["index"]["chroma_dir"])
    return state_dir, grant, chroma


def _parent_kill(
    tmp_path: Path,
    state_dir: Path,
    grant: dict,
    *,
    action: str,
    kill_stage: str,
    setup: callable | None = None,
    wait_barrier: bool = False,
) -> tuple[bool, int, dict[str, str]]:
    barrier = tmp_path / f"barrier-{kill_stage}"
    grant_file = tmp_path / "grant.json"
    grant_file.write_text(json.dumps(grant), encoding="utf-8")
    if setup:
        setup()
    env = os.environ.copy()
    env["CONVMEM_BOOTSTRAP_V2_BARRIER_PREFIX"] = str(barrier)
    if wait_barrier:
        env["CONVMEM_BOOTSTRAP_V2_BARRIER_WAIT"] = "1"
    proc = subprocess.Popen(
        [sys.executable, str(CHILD), action, str(state_dir), str(grant_file)],
        cwd=str(REPO),
        env=env,
    )
    killed = False
    for _ in range(800):
        if (barrier / f"stage.{kill_stage}").exists():
            proc.kill()
            killed = True
            break
        if proc.poll() is not None:
            break
        time.sleep(0.01)
    try:
        rc = proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        proc.kill()
        rc = proc.wait()
    return killed, rc, snapshot_tree(state_dir)


@pytest.mark.parametrize("kill_stage", KILL_STAGES)
def test_parent_sigkill_at_publication_stage(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, kill_stage: str
) -> None:
    state_dir, grant, _ = _fixture(tmp_path, monkeypatch)

    def setup() -> None:
        if kill_stage.startswith("journal_mirror") or kill_stage.startswith("recovery"):
            claim_initial_authority(state_dir, grant)

    if kill_stage.startswith("journal_mirror"):
        action = "mirror"
    elif kill_stage.startswith("recovery"):
        action = "recovery"
    elif kill_stage.startswith("terminal"):
        action = "terminal"
    else:
        action = "initial"

    killed, rc, snap = _parent_kill(tmp_path, state_dir, grant, action=action, kill_stage=kill_stage, setup=setup)
    assert killed is True
    assert rc != 0
    if kill_stage.endswith("after_dir_fsync") and action == "initial":
        assert authority_path(state_dir).is_file()
        assert load_authority(state_dir).invocation_ordinal == 1


def test_injected_replace_fail_leaves_no_durable_authority(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    state_dir, grant, _ = _fixture(tmp_path, monkeypatch)
    monkeypatch.setenv("CONVMEM_BOOTSTRAP_V2_INJECT_REPLACE_FAIL", "initial_authority.replace")
    with pytest.raises(PublicationFailure):
        claim_initial_authority(state_dir, grant)
    assert load_authority(state_dir) is None


def test_injected_fsync_fail_before_authority_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    state_dir, grant, _ = _fixture(tmp_path, monkeypatch)
    monkeypatch.setenv("CONVMEM_BOOTSTRAP_V2_INJECT_FSYNC_FAIL", "initial_authority.dir_fsync")
    with pytest.raises(PublicationFailure):
        claim_initial_authority(state_dir, grant)
    assert authority_path(state_dir).is_file() or authority_path(state_dir).with_suffix(".json.tmp").exists()


def test_ambiguous_authority_temp_blocks_initial(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    state_dir, grant, _ = _fixture(tmp_path, monkeypatch)
    state_dir.mkdir(parents=True, exist_ok=True)
    authority_path(state_dir).with_name(authority_path(state_dir).name + ".tmp").write_text("{}", encoding="utf-8")
    with pytest.raises(CodexBootstrapV2AuthorityError, match="initial_claim_refused:.*ambiguous_authority_temp"):
        claim_initial_authority(state_dir, grant)


def test_parent_kill_ordinal3_child_exits_nonzero(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    state_dir, grant, _ = _fixture(tmp_path, monkeypatch)
    grant_file = tmp_path / "grant.json"
    grant_file.write_text(json.dumps(grant), encoding="utf-8")
    proc = subprocess.run(
        [sys.executable, str(CHILD), "ordinal3", str(state_dir), str(grant_file)],
        cwd=str(REPO),
        capture_output=True,
        check=False,
    )
    assert proc.returncode != 0
    assert load_authority(state_dir).invocation_ordinal == 2


def test_terminal_receipt_before_release_parent_kill_preserves_active_reservation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    state_dir, grant, _ = _fixture(tmp_path, monkeypatch)
    claim_initial_authority(state_dir, grant)
    killed, rc, _ = _parent_kill(
        tmp_path,
        state_dir,
        grant,
        action="terminal",
        kill_stage="terminal_receipt.before_dir_fsync",
        wait_barrier=True,
    )
    assert killed
    view = load_authority(state_dir)
    assert view is not None
    assert view.reservation_active is True
    assert not view.terminal


def test_authority_claim_does_not_mutate_chroma(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    state_dir, grant, chroma = _fixture(tmp_path, monkeypatch)
    chroma.mkdir(parents=True, exist_ok=True)
    before = snapshot_tree(chroma)
    claim_initial_authority(state_dir, grant)
    after = snapshot_tree(chroma)
    assert before == after

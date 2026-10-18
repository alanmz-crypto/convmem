"""T2 V3 parent SIGKILL matrix with byte oracle (not os._exit alone)."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

from tests.fixtures.issue_286_t2_owner_context import t2_owner_context

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

from bootstrap_codex_v2_publication_catalog import all_barrier_stage_names, PUBLICATION_SITES

KILL_STAGES = all_barrier_stage_names()



def _initial(state_dir, grant):
    with t2_owner_context(state_dir):
        return claim_initial_authority(state_dir, grant)


def _recovery(state_dir, grant):
    with t2_owner_context(state_dir):
        return claim_recovery_authority(state_dir, grant)


def _mirror(state_dir, grant):
    with t2_owner_context(state_dir):
        mirror_invocation_start(state_dir, grant)


def _terminal(state_dir, grant, **kwargs):
    with t2_owner_context(state_dir):
        return publish_terminal_authority(state_dir, grant, **kwargs)


SITE_ACTION = {
    "initial_authority": "initial",
    "recovery_authority": "recovery",
    "progress_authority": "progress",
    "terminal_receipt": "terminal",
    "terminal_authority": "terminal",
    "journal_mirror": "mirror",
    "v2_permit": "permit",
}


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
    for _ in range(2000):
        if barrier.exists():
            for stage_marker in sorted(barrier.glob("stage.*")):
                stage_name = stage_marker.name.removeprefix("stage.")
                if stage_name == kill_stage:
                    proc.kill()
                    killed = True
                    break
                ack_path = barrier / f"ack.{stage_name}"
                if not ack_path.exists():
                    ack_path.write_text("1", encoding="ascii")
        if killed or proc.poll() is not None:
            break
        time.sleep(0.01)
    try:
        rc = proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        proc.kill()
        rc = proc.wait()
    return killed, rc, snapshot_tree(state_dir)


    with t2_owner_context(state_dir):
        return publish_terminal_authority(state_dir, grant, **kwargs)

@pytest.mark.parametrize("kill_stage", KILL_STAGES)
def test_parent_sigkill_at_publication_stage(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, kill_stage: str
) -> None:
    state_dir, grant, _ = _fixture(tmp_path, monkeypatch)

    def setup() -> None:
        site, _stage = kill_stage.split(".", 1)
        if site in {"journal_mirror", "recovery_authority", "progress_authority", "terminal_receipt", "terminal_authority", "v2_permit"}:
            _initial(state_dir, grant)
        if site == "recovery_authority":
            return

    site, stage = kill_stage.split(".", 1)
    action = SITE_ACTION[site]

    killed, rc, snap = _parent_kill(
        tmp_path, state_dir, grant, action=action, kill_stage=kill_stage, setup=setup, wait_barrier=True
    )
    assert killed is True
    assert rc != 0
    from bootstrap_codex_v2_authority import operation_root
    from tests.fixtures.issue_286_t2_parent_oracle import count_oracle_rows

    if site in {"initial_authority", "recovery_authority", "progress_authority", "terminal_authority"}:
        durable = stage in {"after_dir_fsync", "after_replace"}
        if durable:
            assert load_authority(state_dir) is not None
        elif site == "initial_authority" and stage in {"before_tmp_write", "before_tmp_fsync", "before_replace"}:
            assert load_authority(state_dir) is None
    if site == "recovery_authority" and stage == "after_dir_fsync":
        assert load_authority(state_dir).invocation_ordinal == 2
    if site == "v2_permit" and stage == "after_dir_fsync":
        assert count_oracle_rows(operation_root(state_dir, grant) / "v2_provider_permits.jsonl") == 1
    if site == "journal_mirror" and stage == "after_dir_fsync":
        assert count_oracle_rows(operation_root(state_dir, grant) / "invocations.jsonl") == 1


def test_injected_replace_fail_leaves_no_durable_authority(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    state_dir, grant, _ = _fixture(tmp_path, monkeypatch)
    monkeypatch.setenv("CONVMEM_BOOTSTRAP_V2_INJECT_REPLACE_FAIL", "initial_authority.replace")
    with pytest.raises(PublicationFailure):
        _initial(state_dir, grant)
    assert load_authority(state_dir) is None


def test_injected_fsync_fail_before_authority_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    state_dir, grant, _ = _fixture(tmp_path, monkeypatch)
    monkeypatch.setenv("CONVMEM_BOOTSTRAP_V2_INJECT_FSYNC_FAIL", "initial_authority.dir_fsync")
    with pytest.raises(PublicationFailure):
        _initial(state_dir, grant)
    assert authority_path(state_dir).is_file() or authority_path(state_dir).with_suffix(".json.tmp").exists()


def test_ambiguous_authority_temp_blocks_initial(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    state_dir, grant, _ = _fixture(tmp_path, monkeypatch)
    state_dir.mkdir(parents=True, exist_ok=True)
    authority_path(state_dir).with_name(authority_path(state_dir).name + ".tmp").write_text("{}", encoding="utf-8")
    with pytest.raises(CodexBootstrapV2AuthorityError, match="initial_claim_refused:.*ambiguous_authority_temp"):
        _initial(state_dir, grant)


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
    _initial(state_dir, grant)
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
    _initial(state_dir, grant)
    after = snapshot_tree(chroma)
    assert before == after


INJECT_CASES = [
    ("initial_authority.before_tmp_fsync", "initial", "ambiguous_authority_temp"),
    ("initial_authority.before_replace", "initial", "no_authority"),
    ("journal_mirror.before_file_fsync", "mirror", "mirror_row_present"),
    ("v2_permit.before_file_fsync", "permit", "permit_row_present"),
]


@pytest.mark.parametrize("inject_stage,action,expect", INJECT_CASES)
def test_injected_publication_failure_matrix(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, inject_stage: str, action: str, expect: str
) -> None:
    from bootstrap_codex_v2_authority import operation_root
    from tests.fixtures.issue_286_t2_parent_oracle import count_oracle_rows

    state_dir, grant, _ = _fixture(tmp_path, monkeypatch)
    if action != "initial":
        _initial(state_dir, grant)
    site, barrier = inject_stage.split(".", 1)
    if barrier == "before_replace":
        monkeypatch.setenv("CONVMEM_BOOTSTRAP_V2_INJECT_REPLACE_FAIL", f"{site}.replace")
        monkeypatch.delenv("CONVMEM_BOOTSTRAP_V2_INJECT_FSYNC_FAIL", raising=False)
    elif barrier == "before_tmp_fsync":
        monkeypatch.setenv("CONVMEM_BOOTSTRAP_V2_INJECT_FSYNC_FAIL", f"{site}.tmp_fsync")
        monkeypatch.delenv("CONVMEM_BOOTSTRAP_V2_INJECT_REPLACE_FAIL", raising=False)
    elif barrier == "before_file_fsync":
        monkeypatch.setenv("CONVMEM_BOOTSTRAP_V2_INJECT_FSYNC_FAIL", f"{site}.file_fsync")
        monkeypatch.delenv("CONVMEM_BOOTSTRAP_V2_INJECT_REPLACE_FAIL", raising=False)
    from bootstrap_codex_v2_publication import PublicationFailure

    with pytest.raises(PublicationFailure):
        with t2_owner_context(state_dir):
            if action == "initial":
                claim_initial_authority(state_dir, grant)
            elif action == "mirror":
                mirror_invocation_start(state_dir, grant)
            else:
                from bootstrap_codex_v2_permits import CodexV2PaidLedger

                CodexV2PaidLedger(state_dir, grant).consume_provider_http_attempt(
                    {
                        "provider": "deepseek",
                        "operation": "generate",
                        "model": grant["distill_model"],
                        "base_url": grant["distill_base_url"],
                    }
                )
    if expect == "no_authority":
        assert load_authority(state_dir) is None
    elif expect == "no_mirror_rows":
        assert count_oracle_rows(operation_root(state_dir, grant) / "invocations.jsonl") == 0
    elif expect == "no_permit_rows":
        assert count_oracle_rows(operation_root(state_dir, grant) / "v2_provider_permits.jsonl") == 0
    elif expect == "mirror_row_present":
        assert count_oracle_rows(operation_root(state_dir, grant) / "invocations.jsonl") == 1
    elif expect == "permit_row_present":
        assert count_oracle_rows(operation_root(state_dir, grant) / "v2_provider_permits.jsonl") == 1

# pylint: disable=wrong-import-position
# Project imports follow the mandatory isolation check.
# pylint: disable=redefined-outer-name
"""Real subprocess concurrency: recovery vs forget/refine at native flock boundaries."""

from __future__ import annotations

import json
import os
import subprocess
import select

import pytest
from tests._safe_harbor_bootstrap import require_t3_bootstrap

require_t3_bootstrap()

pytest_plugins = ("tests.test_safe_harbor_t2",)

from tests._safe_harbor_t4_concurrency import (  # noqa: E402
    BARRIER_TIMEOUT_SECONDS,
    CHILD_TIMEOUT_SECONDS,
    assert_child_isolation,
    close_fds,
    corpus_triplet,
    lock_path_for_cli,
    parse_worker_stdout,
    read_event,
    seed_canonical_id,
    spawn_worker,
    spawn_worker_popen,
    terminate_worker,
    unit_by_id,
    unit_for_proposal,
    worker_env,
    write_go,
)
from tests._safe_harbor_t4_harness import assert_cli_confined  # noqa: E402
from tests.test_safe_harbor_t2 import (  # noqa: E402
    NOW_ENV_KEY,
    _current,
    _event_only_state,
    local_noon,
)


def _events_for_pid(cli, proposal_id: str) -> list[dict]:
    path = cli.s.data / "pending_decision_events.jsonl"
    rows = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    return [row for row in rows if row.get("proposal_id") == proposal_id]


def _ledger_id(cli, proposal_id: str) -> str:
    path = cli.s.data / "decisions-approved.jsonl"
    for line in reversed(path.read_text().splitlines()):
        if not line.strip():
            continue
        row = json.loads(line)
        if row.get("id") == proposal_id or row.get("proposal_id") == proposal_id:
            return str(row.get("id") or row.get("ledger_id") or proposal_id)
    raise AssertionError(f"no approved ledger row for {proposal_id}")


def _export_lines(cli, ledger_id: str) -> list[dict]:
    path = cli.s.data / "knowledge_units.jsonl"
    if not path.is_file():
        return []
    return [
        json.loads(line)
        for line in path.read_text().splitlines()
        if line.strip() and json.loads(line).get("ledger_id") == ledger_id
    ]


def _assert_no_approved(cli, proposal_id: str) -> None:
    assert not any(
        e.get("event_type") == "APPROVED" for e in _events_for_pid(cli, proposal_id)
    )


def _run_recovery_first_race(cli, *, competitor: str) -> None:  # pylint: disable=too-many-locals
    assert_cli_confined(cli)
    env_base = {**_current(cli), NOW_ENV_KEY: local_noon().isoformat()}
    assert_child_isolation(cli, extra_env=env_base)

    pid = _event_only_state(cli)
    before = cli.dump()
    before_unit = unit_for_proposal(before, pid)
    unit_id = before_unit["id"]
    lock_path = lock_path_for_cli(cli)
    canonical_id = seed_canonical_id(cli) if competitor == "refine" else ""

    rec_sig_r, rec_sig_w = os.pipe()
    rec_cont_r, rec_cont_w = os.pipe()
    comp_sig_r, comp_sig_w = os.pipe()
    comp_cont_r, comp_cont_w = os.pipe()
    open_fds = [rec_sig_r, rec_sig_w, rec_cont_r, rec_cont_w, comp_sig_r, comp_sig_w, comp_cont_r, comp_cont_w]

    rec_proc: subprocess.Popen[str] | None = None
    comp_proc: subprocess.Popen[str] | None = None
    try:
        rec_env = worker_env(
            cli,
            extra={
                **env_base,
                "SAFE_HARBOR_T4_LOCK_PATH": lock_path,
                "SAFE_HARBOR_T4_SIGNAL_WRITE_FD": str(rec_sig_w),
                "SAFE_HARBOR_T4_CONTINUE_READ_FD": str(rec_cont_r),
            },
        )
        comp_env = worker_env(
            cli,
            extra={
                **env_base,
                "SAFE_HARBOR_T4_LOCK_PATH": lock_path,
                "SAFE_HARBOR_T4_COMPETE_SIGNAL_WRITE_FD": str(comp_sig_w),
                "SAFE_HARBOR_T4_COMPETE_CONTINUE_READ_FD": str(comp_cont_r),
            },
        )
        if competitor == "refine":
            comp_env["SAFE_HARBOR_T4_TOMBSTONE_ID"] = unit_id
            comp_env["SAFE_HARBOR_T4_CANONICAL_ID"] = canonical_id
            comp_mode = "refine-apply"
            comp_args: tuple[str, ...] = ()
        else:
            comp_mode = "forget-cli"
            comp_args = (unit_id,)

        rec_proc = spawn_worker_popen(
            cli,
            "recover-held",
            (pid,),
            extra_env=rec_env,
            pass_fds=(rec_sig_w, rec_cont_r),
        )
        os.close(rec_sig_w)
        os.close(rec_cont_r)

        assert read_event(rec_sig_r, timeout=BARRIER_TIMEOUT_SECONDS) == "INSPECTED"

        comp_proc = spawn_worker_popen(
            cli,
            comp_mode,
            comp_args,
            extra_env=comp_env,
            pass_fds=(comp_sig_w, comp_cont_r),
        )
        os.close(comp_sig_w)
        os.close(comp_cont_r)

        assert read_event(comp_sig_r, timeout=BARRIER_TIMEOUT_SECONDS) == "PRE_FLOCK"
        assert read_event(comp_sig_r, timeout=BARRIER_TIMEOUT_SECONDS) == "NB_BLOCKED"

        _, probe_payload = spawn_worker(
            cli,
            "probe-lock-nb",
            extra_env={**env_base, "SAFE_HARBOR_T4_LOCK_PATH": lock_path},
            timeout=CHILD_TIMEOUT_SECONDS,
        )
        assert probe_payload.get("acquired") is False

        assert not select.select([comp_sig_r], [], [], 0)[0], "competitor acquired before recovery release"
        write_go(rec_cont_w)
        os.close(rec_cont_w)
        rec_payload = parse_worker_stdout(rec_proc, timeout=CHILD_TIMEOUT_SECONDS)
        assert rec_payload.get("verdict") == "OK"
        assert rec_payload.get("action") == "approve"
        assert rec_payload.get("captured_under_lock") is True

        os.close(comp_cont_w)
        assert read_event(comp_sig_r, timeout=BARRIER_TIMEOUT_SECONDS) == "ACQUIRED"
        comp_payload = parse_worker_stdout(comp_proc, timeout=CHILD_TIMEOUT_SECONDS)
        assert comp_payload.get("verdict") == "OK"

        after_unit = unit_for_proposal(rec_payload["state"], pid)
        assert corpus_triplet(before_unit) == corpus_triplet(after_unit)
        ledger = _ledger_id(cli, pid)
        exports = _export_lines(cli, ledger)
        assert len(exports) == 1
        assert exports[0]["id"] == after_unit["id"]
        assert any(e.get("event_type") == "APPROVED" for e in _events_for_pid(cli, pid))

        final_unit = unit_by_id(comp_payload["state"], unit_id)
        assert (final_unit.get("metadata") or {}).get("superseded") is True
    finally:
        terminate_worker(rec_proc)
        terminate_worker(comp_proc)
        close_fds(open_fds)


def _run_competitor_first_refuse(cli, *, competitor: str) -> None:
    env_base = {**_current(cli), NOW_ENV_KEY: local_noon().isoformat()}
    assert_child_isolation(cli, extra_env=env_base)

    pid = _event_only_state(cli)
    before = cli.dump()
    before_unit = unit_for_proposal(before, pid)
    unit_id = before_unit["id"]
    lock_path = lock_path_for_cli(cli)
    before_triplet = corpus_triplet(before_unit)

    comp_extra = {
        **env_base,
        "SAFE_HARBOR_T4_LOCK_PATH": lock_path,
        "SAFE_HARBOR_T4_PRE_FLOCK": "0",
    }
    if competitor == "refine":
        comp_extra["SAFE_HARBOR_T4_TOMBSTONE_ID"] = unit_id
        comp_extra["SAFE_HARBOR_T4_CANONICAL_ID"] = seed_canonical_id(cli)
        comp_mode = "refine-apply"
        comp_args: tuple[str, ...] = ()
    else:
        comp_mode = "forget-cli"
        comp_args = (unit_id,)

    comp_proc, comp_payload = spawn_worker(
        cli,
        comp_mode,
        comp_args,
        extra_env=comp_extra,
        timeout=CHILD_TIMEOUT_SECONDS,
    )
    assert comp_proc.returncode == 0, comp_proc.stdout + comp_proc.stderr
    assert comp_payload.get("verdict") == "OK"
    tombstoned = unit_by_id(comp_payload["state"], unit_id)
    assert (tombstoned.get("metadata") or {}).get("superseded") is True
    assert corpus_triplet(tombstoned)["metadata"] != before_triplet["metadata"]

    export_before_recovery = cli.export.read_bytes() if cli.export.exists() else None
    events_before_recovery = (cli.s.data / "pending_decision_events.jsonl").read_bytes()
    rec_proc, rec_payload = spawn_worker(
        cli,
        "recover-refused",
        (pid,),
        extra_env=env_base,
        timeout=CHILD_TIMEOUT_SECONDS,
    )
    assert rec_proc.returncode == 0, rec_proc.stdout + rec_proc.stderr
    assert rec_payload.get("verdict") == "REFUSED"
    assert "target_tombstoned" in rec_payload.get("error", "")
    _assert_no_approved(cli, pid)
    after_unit = unit_for_proposal(rec_payload["state"], pid)
    assert (after_unit.get("metadata") or {}).get("superseded") is True
    assert corpus_triplet(after_unit)["document"] == before_triplet["document"]
    assert corpus_triplet(after_unit)["embedding_sha"] == before_triplet["embedding_sha"]
    assert (cli.export.read_bytes() if cli.export.exists() else None) == export_before_recovery
    assert (cli.s.data / "pending_decision_events.jsonl").read_bytes() == events_before_recovery


def test_t4_real_recovery_holds_lock_forget_cannot_acquire(cli):
    _run_recovery_first_race(cli, competitor="forget")


def test_t4_real_recovery_holds_lock_refine_cannot_acquire(cli):
    _run_recovery_first_race(cli, competitor="refine")


def test_t4_real_forget_before_recovery_refuses(cli):
    _run_competitor_first_refuse(cli, competitor="forget")


def test_t4_real_refine_before_recovery_refuses(cli):
    _run_competitor_first_refuse(cli, competitor="refine")


def test_t4_faulty_out_of_lock_recheck_negative_control(cli):
    env_base = {**_current(cli), NOW_ENV_KEY: local_noon().isoformat()}
    assert_child_isolation(cli, extra_env=env_base)

    pid = _event_only_state(cli)
    unit_id = unit_for_proposal(cli.dump(), pid)["id"]
    lock_path = lock_path_for_cli(cli)

    rec_sig_r, rec_sig_w = os.pipe()
    gap_r, gap_w = os.pipe()
    open_fds = [rec_sig_r, rec_sig_w, gap_r, gap_w]
    rec_proc: subprocess.Popen[str] | None = None

    try:
        rec_env = worker_env(
            cli,
            extra={
                **env_base,
                "SAFE_HARBOR_T4_LOCK_PATH": lock_path,
                "SAFE_HARBOR_T4_SIGNAL_WRITE_FD": str(rec_sig_w),
                "SAFE_HARBOR_T4_GAP_READ_FD": str(gap_r),
            },
        )
        rec_proc = spawn_worker_popen(
            cli,
            "recover-faulty-oool",
            (pid,),
            extra_env=rec_env,
            pass_fds=(rec_sig_w, gap_r),
        )
        os.close(rec_sig_w)
        os.close(gap_r)

        assert read_event(rec_sig_r, timeout=BARRIER_TIMEOUT_SECONDS) == "INSPECTED"
        write_go(gap_w)
        assert read_event(rec_sig_r, timeout=BARRIER_TIMEOUT_SECONDS) == "GAP"

        forget_proc, forget_payload = spawn_worker(
            cli,
            "forget-cli",
            (unit_id,),
            extra_env={
                **env_base,
                "SAFE_HARBOR_T4_LOCK_PATH": lock_path,
                "SAFE_HARBOR_T4_PRE_FLOCK": "0",
            },
            timeout=CHILD_TIMEOUT_SECONDS,
        )
        assert forget_proc.returncode == 0, forget_proc.stdout + forget_proc.stderr
        assert (unit_by_id(forget_payload["state"], unit_id).get("metadata") or {}).get("superseded")

        write_go(gap_w)
        faulty = parse_worker_stdout(rec_proc, timeout=CHILD_TIMEOUT_SECONDS)
        assert faulty.get("faulty") is True
        assert faulty.get("stale_classify") is True

        tombstoned = (unit_by_id(forget_payload["state"], unit_id).get("metadata") or {}).get(
            "superseded"
        ) is True
        approved = any(e.get("event_type") == "APPROVED" for e in _events_for_pid(cli, pid))
        refused_like_production = faulty.get("verdict") == "REFUSED" and not approved

        assert tombstoned
        assert not refused_like_production, "out-of-lock negative control is insensitive"

        def production_must_refuse() -> None:
            assert faulty.get("verdict") == "REFUSED"
            assert "target_tombstoned" in faulty.get("error", "")
            _assert_no_approved(cli, pid)

        with pytest.raises(AssertionError):
            production_must_refuse()
    finally:
        terminate_worker(rec_proc)
        close_fds(open_fds)

def test_t4_rechecks_config_after_native_lock_wait(cli):
    """A real blocked recovery cannot use its now-replaced config after admission."""
    import fcntl
    from pathlib import Path
    pid = _event_only_state(cli)
    before = cli.dump()
    lock_path = lock_path_for_cli(cli)
    lock_fd = os.open(lock_path, os.O_CREAT | os.O_RDWR, 0o600)
    signal_r, signal_w = os.pipe()
    proc = None
    try:
        fcntl.flock(lock_fd, fcntl.LOCK_EX)
        proc = spawn_worker_popen(
            cli, "recover-wait-config", (pid,),
            extra_env={**_current(cli), NOW_ENV_KEY: local_noon().isoformat(),
                       "SAFE_HARBOR_T4_LOCK_PATH": lock_path,
                       "SAFE_HARBOR_T4_SIGNAL_WRITE_FD": str(signal_w)},
            pass_fds=(signal_w,),
        )
        os.close(signal_w)
        assert read_event(signal_r, timeout=BARRIER_TIMEOUT_SECONDS) == "PRE_FLOCK"
        assert read_event(signal_r, timeout=BARRIER_TIMEOUT_SECONDS) == "NB_BLOCKED"
        replacement = Path(str(cli.config) + ".replacement")
        replacement.write_bytes(cli.config.read_bytes() + b"\n# replaced after admission\n")
        os.replace(replacement, cli.config)
        fcntl.flock(lock_fd, fcntl.LOCK_UN)
        payload = parse_worker_stdout(proc, timeout=CHILD_TIMEOUT_SECONDS)
        assert payload["cli_rc"] == 24, payload
        assert "operation_config_changed" in payload["output"], payload
        assert cli.dump() == before, "post-wait refusal changed corpus or governed effects"
        _assert_no_approved(cli, pid)
    finally:
        terminate_worker(proc)
        close_fds([lock_fd, signal_r, signal_w])

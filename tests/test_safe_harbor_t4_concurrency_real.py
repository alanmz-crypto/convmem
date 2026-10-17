# pylint: disable=wrong-import-position
# Project imports follow the mandatory isolation check.
# pylint: disable=redefined-outer-name
"""Real subprocess concurrency: recovery vs forget/refine at native flock boundaries."""

from __future__ import annotations

import json
import os
import subprocess
import select
import sys
import time
from unittest import mock

import pytest
from tests._safe_harbor_bootstrap import require_t3_bootstrap

require_t3_bootstrap()
# Register only for this module; each child gets refusal before project imports.
from tests._safe_harbor_t4_pytest import isolated_t4_child_network  # pylint: disable=unused-import
from tests.test_safe_harbor_t2 import cli, isolated, scratch  # pylint: disable=unused-import

from tests import _safe_harbor_t4_concurrency as t4_concurrency  # noqa: E402
from tests._safe_harbor_t4_concurrency import (  # noqa: E402
    CHILD_TIMEOUT_SECONDS,
    RaceTrace,
    assert_child_isolation,
    assert_holder_live,
    attach_worker_diagnostic,
    cleanup_race_workers,
    close_fds,
    corpus_triplet,
    finish_race_run,
    lock_path_for_cli,
    parse_worker_stdout,
    pipe_read_fragment_delivery,
    read_event,
    read_event_lossy,
    read_tracked_event,
    seed_canonical_id,
    spawn_worker,
    spawn_worker_popen,
    terminate_worker,
    unit_by_id,
    unit_for_proposal,
    worker_env,
    write_go,
    write_race_diagnostic,
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
    rec_diag = attach_worker_diagnostic(None, "recovery")
    comp_diag = attach_worker_diagnostic(None, "competitor")
    trace = RaceTrace()
    race_exc: BaseException | None = None

    try:
        trace.stage("fixture_ready")
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
        rec_diag.proc = rec_proc
        os.close(rec_sig_w)
        os.close(rec_cont_r)
        trace.stage("recovery_spawned")
        assert_holder_live(rec_proc, stage="post_spawn", trace=trace)

        trace.stage("await_INSPECTED")
        assert (
            read_tracked_event(rec_sig_r, trace, "recovery_INSPECTED")
            == "INSPECTED"
        )
        assert_holder_live(rec_proc, stage="post_INSPECTED", trace=trace)

        comp_proc = spawn_worker_popen(
            cli,
            comp_mode,
            comp_args,
            extra_env=comp_env,
            pass_fds=(comp_sig_w, comp_cont_r),
        )
        comp_diag.proc = comp_proc
        os.close(comp_sig_w)
        os.close(comp_cont_r)
        trace.stage("competitor_spawned")

        trace.stage("await_PRE_FLOCK")
        assert (
            read_tracked_event(comp_sig_r, trace, "competitor_PRE_FLOCK")
            == "PRE_FLOCK"
        )
        assert_holder_live(rec_proc, stage="post_PRE_FLOCK", trace=trace)

        trace.stage("await_NB_BLOCKED")
        assert (
            read_tracked_event(comp_sig_r, trace, "competitor_NB_BLOCKED")
            == "NB_BLOCKED"
        )
        assert_holder_live(rec_proc, stage="post_NB_BLOCKED", trace=trace)

        trace.stage("probe_lock_nb")
        _, probe_payload = spawn_worker(
            cli,
            "probe-lock-nb",
            extra_env={**env_base, "SAFE_HARBOR_T4_LOCK_PATH": lock_path},
            timeout=CHILD_TIMEOUT_SECONDS,
        )
        assert probe_payload.get("acquired") is False
        assert_holder_live(rec_proc, stage="post_probe", trace=trace)

        trace.stage("pre_release_select")
        assert not select.select([comp_sig_r], [], [], 0)[0], "competitor acquired before recovery release"
        assert_holder_live(rec_proc, stage="pre_GO", trace=trace)
        trace.stage("release_GO")
        write_go(rec_cont_w)
        os.close(rec_cont_w)
        rec_payload = parse_worker_stdout(
            rec_proc, timeout=CHILD_TIMEOUT_SECONDS, diagnostic=rec_diag
        )
        assert rec_payload.get("verdict") == "OK"
        assert rec_payload.get("action") == "approve"
        assert rec_payload.get("captured_under_lock") is True

        os.close(comp_cont_w)
        trace.stage("await_ACQUIRED")
        assert (
            read_tracked_event(comp_sig_r, trace, "competitor_ACQUIRED")
            == "ACQUIRED"
        )
        comp_payload = parse_worker_stdout(
            comp_proc, timeout=CHILD_TIMEOUT_SECONDS, diagnostic=comp_diag
        )
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
        trace.stage("race_complete")
    except BaseException as exc:  # pylint: disable=broad-exception-caught
        # Preserve child diagnostics before re-raising even an interrupted test.
        race_exc = exc
    finally:
        cleanup_race_workers(
            rec_proc=rec_proc,
            comp_proc=comp_proc,
            rec_diag=rec_diag,
            comp_diag=comp_diag,
            open_fds=open_fds,
            trace=trace,
        )

    finish_race_run(
        cli,
        f"recovery_first_{competitor}_{pid}",
        trace,
        race="recovery_first",
        competitor=competitor,
        proposal_id=pid,
        children={"recovery": rec_diag, "competitor": comp_diag},
        race_exc=race_exc,
    )


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
    rec_diag = attach_worker_diagnostic(None, "faulty_recovery")
    comp_diag = attach_worker_diagnostic(None, "forget")
    trace = RaceTrace()
    race_exc = None

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
        rec_diag.proc = rec_proc
        os.close(rec_sig_w)
        os.close(gap_r)

        assert read_tracked_event(rec_sig_r, trace, "recovery_signal") == "INSPECTED"
        write_go(gap_w)
        assert read_tracked_event(rec_sig_r, trace, "recovery_signal") == "GAP"

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
        comp_diag.proc = forget_proc
        comp_diag.finalize()
        assert forget_proc.returncode == 0, forget_proc.stdout + forget_proc.stderr
        assert (unit_by_id(forget_payload["state"], unit_id).get("metadata") or {}).get("superseded")

        write_go(gap_w)
        faulty = parse_worker_stdout(
            rec_proc, timeout=CHILD_TIMEOUT_SECONDS, diagnostic=rec_diag
        )
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
    except BaseException as exc:  # pylint: disable=broad-exception-caught
        race_exc = exc
    finally:
        cleanup_race_workers(
            rec_proc=rec_proc, comp_proc=None, rec_diag=rec_diag, comp_diag=comp_diag,
            open_fds=open_fds, trace=trace,
        )
    finish_race_run(
        cli, "faulty_ool", trace, race="faulty_ool", competitor="forget",
        proposal_id=pid, children={"recovery": rec_diag, "competitor": comp_diag},
        race_exc=race_exc,
    )


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
    wait_diag = attach_worker_diagnostic(None, "recover_wait_config")
    trace = RaceTrace()
    race_exc = None
    try:
        fcntl.flock(lock_fd, fcntl.LOCK_EX)
        proc = spawn_worker_popen(
            cli, "recover-wait-config", (pid,),
            extra_env={**_current(cli), NOW_ENV_KEY: local_noon().isoformat(),
                       "SAFE_HARBOR_T4_LOCK_PATH": lock_path,
                       "SAFE_HARBOR_T4_SIGNAL_WRITE_FD": str(signal_w)},
            pass_fds=(signal_w,),
        )
        wait_diag.proc = proc
        os.close(signal_w)
        assert read_tracked_event(signal_r, trace, "waiting_recovery") == "PRE_FLOCK"
        assert read_tracked_event(signal_r, trace, "waiting_recovery") == "NB_BLOCKED"
        replacement = Path(str(cli.config) + ".replacement")
        replacement.write_bytes(cli.config.read_bytes() + b"\n# replaced after admission\n")
        os.replace(replacement, cli.config)
        fcntl.flock(lock_fd, fcntl.LOCK_UN)
        payload = parse_worker_stdout(
            proc, timeout=CHILD_TIMEOUT_SECONDS, diagnostic=wait_diag
        )
        assert payload["cli_rc"] == 20, payload
        assert "operation_config_changed" in payload["output"], payload
        assert cli.dump() == before, "post-wait refusal changed corpus or governed effects"
        _assert_no_approved(cli, pid)
    except BaseException as exc:  # pylint: disable=broad-exception-caught
        race_exc = exc
    finally:
        cleanup_race_workers(
            rec_proc=proc, comp_proc=None, rec_diag=wait_diag,
            comp_diag=attach_worker_diagnostic(None, "parent_lock"),
            open_fds=[lock_fd, signal_r, signal_w], trace=trace,
        )
    finish_race_run(
        cli, "config_wait", trace, race="config_wait", competitor="parent_lock",
        proposal_id=pid, children={"recovery": wait_diag}, race_exc=race_exc,
    )


def test_t4_pipe_protocol_coalesced_competitor_signals():
    """Lossless reader must deliver both lines when the kernel coalesces them."""
    read_fd, write_fd = os.pipe()
    try:
        os.write(write_fd, b"PRE_FLOCK\nNB_BLOCKED\n")
        assert read_event(read_fd) == "PRE_FLOCK"
        assert read_event(read_fd) == "NB_BLOCKED"
    finally:
        close_fds([read_fd, write_fd])


def test_t4_pipe_protocol_fragmented_competitor_signals():
    read_fd, write_fd = os.pipe()
    try:
        fragments = [b"PRE_", b"FLOCK\nNB_", b"BLOCKED", b"\n"]
        with pipe_read_fragment_delivery(read_fd, write_fd, fragments):
            assert read_event(read_fd) == "PRE_FLOCK"
            assert read_event(read_fd) == "NB_BLOCKED"
    finally:
        close_fds([read_fd, write_fd])


def test_t4_pipe_protocol_lossy_reader_drops_coalesced_second_line():
    read_fd, write_fd = os.pipe()
    try:
        os.write(write_fd, b"PRE_FLOCK\nNB_BLOCKED\n")
        assert read_event_lossy(read_fd) == "PRE_FLOCK"
        close_fds([write_fd])
        write_fd = -1
        with pytest.raises(EOFError):
            read_event_lossy(read_fd)
    finally:
        if write_fd >= 0:
            close_fds([write_fd])
        close_fds([read_fd])


def test_t4_pipe_protocol_lossless_reader_keeps_second_line_selectable():
    read_fd, write_fd = os.pipe()
    try:
        os.write(write_fd, b"PRE_FLOCK\nNB_BLOCKED\n")
        assert read_event(read_fd) == "PRE_FLOCK"
        assert select.select([read_fd], [], [], 0)[0], "second line must stay kernel-ready"
        assert read_event(read_fd) == "NB_BLOCKED"
    finally:
        close_fds([read_fd, write_fd])


def _spawn_blocking_diagnostic_child() -> tuple[subprocess.Popen[str], int]:
    block_r, block_w = os.pipe()
    ready_r, ready_w = os.pipe()
    script = (
        "import os,sys;"
        "sys.stdout.write('{\"verdict\":\"OK\",\"sentinel\":\"stdout-sentinel\"}\\n');sys.stdout.flush();"
        "sys.stderr.write('stderr-sentinel\\n');sys.stderr.flush();"
        f"os.write({ready_w}, b'READY\\n');"
        f"os.read({block_r}, 1)"
    )
    # The caller owns this live barrier child through diagnostic cleanup.
    proc = subprocess.Popen(  # pylint: disable=consider-using-with
        [sys.executable, "-s", "-B", "-c", script],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        pass_fds=(block_r, ready_w),
    )
    os.close(block_r)
    os.close(ready_w)
    try:
        assert read_event(ready_r) == "READY"
    except BaseException:
        proc.kill()
        proc.communicate(timeout=5)
        os.close(block_w)
        raise
    finally:
        os.close(ready_r)
    return proc, block_w


def test_t4_write_go_short_write_control():
    read_fd, write_fd = os.pipe()
    real_write = os.write
    state = {"first": True}

    def short_write(fd: int, data: bytes) -> int:
        if fd == write_fd and state["first"]:
            state["first"] = False
            return real_write(fd, data[:1])
        return real_write(fd, data)

    try:
        with mock.patch.object(t4_concurrency.os, "write", short_write):
            write_go(write_fd, "GO")
        assert read_event(read_fd) == "GO"
    finally:
        close_fds([write_fd, read_fd])


def test_t4_write_go_zero_progress_raises():
    read_fd, write_fd = os.pipe()
    real_write = t4_concurrency.os.write

    def zero_write(fd: int, data: bytes) -> int:
        if fd == write_fd:
            return 0
        return real_write(fd, data)

    try:
        with mock.patch.object(t4_concurrency.os, "write", zero_write):
            with pytest.raises(OSError):
                write_go(write_fd, "GO")
    finally:
        close_fds([write_fd, read_fd])


def test_t4_worker_diagnostic_capture_success(cli):
    env_base = {**_current(cli), NOW_ENV_KEY: local_noon().isoformat()}
    proc, payload = spawn_worker(cli, "snapshot", extra_env=env_base, timeout=CHILD_TIMEOUT_SECONDS)
    diag = attach_worker_diagnostic(proc, "snapshot")
    diag.finalize()
    assert proc.returncode == 0
    assert payload.get("verdict") == "PASS"
    assert diag.returncode == 0
    assert diag.stdout
    assert diag.stderr == ""


def test_t4_worker_diagnostic_capture_exited_failure(cli):
    env_base = {**_current(cli), NOW_ENV_KEY: local_noon().isoformat()}
    proc, payload = spawn_worker(
        cli,
        "unknown-mode",
        (),
        extra_env=env_base,
        timeout=CHILD_TIMEOUT_SECONDS,
    )
    diag = attach_worker_diagnostic(proc, "unknown_mode")
    diag.finalize()
    assert proc.returncode != 0
    assert payload.get("verdict") == "FAIL"
    assert diag.returncode == proc.returncode
    assert diag.stdout or diag.stderr


def test_t4_worker_diagnostic_capture_killed():
    proc, block_w = _spawn_blocking_diagnostic_child()
    diag = attach_worker_diagnostic(proc, "killed_blocking")
    try:
        proc.kill()
        diag.finalize()
        assert diag.returncode is not None and diag.returncode < 0
        assert "stdout-sentinel" in diag.stdout
        assert "stderr-sentinel" in diag.stderr
    finally:
        close_fds([block_w])
        terminate_worker(proc, diagnostic=diag)


def test_t4_worker_diagnostic_parse_timeout_retains_partial():
    proc, block_w = _spawn_blocking_diagnostic_child()
    diag = attach_worker_diagnostic(proc, "parse_timeout")
    try:
        with pytest.raises(subprocess.TimeoutExpired):
            parse_worker_stdout(proc, timeout=0.01, diagnostic=diag)
        assert diag.returncode is not None
        assert "stdout-sentinel" in diag.stdout
        assert "stderr-sentinel" in diag.stderr
        assert diag.annotations.get("communicate_timeout") is True
        assert diag.annotations.get("killed_after_timeout") is True
        assert diag.returncode is not None and diag.returncode < 0
        diag.finalize()
        assert "stdout-sentinel" in diag.stdout
    finally:
        close_fds([block_w])
        terminate_worker(proc, diagnostic=diag)


def test_t4_worker_diagnostic_malformed_json_then_cleanup():
    proc = subprocess.run(
        [sys.executable, "-s", "-B", "-c", "print('not-json-line')"],
        capture_output=True,
        text=True,
        check=False,
    )
    diag = attach_worker_diagnostic(proc, "malformed_json")
    with pytest.raises(RuntimeError):
        parse_worker_stdout(proc, diagnostic=diag)
    assert diag.annotations.get("parse_error")
    assert "not-json-line" in diag.stdout
    diag.finalize()
    assert diag.stdout == proc.stdout


def test_t4_worker_diagnostic_already_exited_nonzero():
    # Test finalization after an independently observed process exit.
    proc = subprocess.Popen(  # pylint: disable=consider-using-with
        [sys.executable, "-s", "-B", "-c",
         "import sys; print('bye'); print('failure-detail', file=sys.stderr); sys.exit(7)"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    diag = attach_worker_diagnostic(proc, "exited_nonzero")
    try:
        assert proc.wait(timeout=CHILD_TIMEOUT_SECONDS) == 7
        diag.finalize()
        assert diag.returncode == 7
        assert diag.annotations["returncode_before_gather"] == 7
        assert "bye" in diag.stdout
        assert "failure-detail" in diag.stderr
    finally:
        terminate_worker(proc, diagnostic=diag)


def test_t4_worker_diagnostic_idempotent_after_parse(cli):
    env_base = {**_current(cli), NOW_ENV_KEY: local_noon().isoformat()}
    proc = spawn_worker_popen(cli, "snapshot", extra_env=env_base)
    diag = attach_worker_diagnostic(proc, "snapshot_parse")
    payload = parse_worker_stdout(proc, timeout=CHILD_TIMEOUT_SECONDS, diagnostic=diag)
    assert payload.get("verdict") == "PASS"
    before = (diag.stdout, diag.stderr, diag.returncode)
    diag.finalize()
    assert (diag.stdout, diag.stderr, diag.returncode) == before


def test_t4_race_diagnostic_writes_under_fixture_root(cli):
    payload = {
        "race": "diagnostic_control",
        "competitor": "control",
        "parent_stages": {"control": time.monotonic()},
        "children": {},
    }
    path = write_race_diagnostic(cli, "diagnostic_control", payload)
    assert_cli_confined(cli)
    root = cli.s.root.resolve()
    assert path.resolve().is_relative_to(root)
    loaded = json.loads(path.read_text(encoding="utf-8"))
    assert loaded["race"] == "diagnostic_control"


def test_t4_race_diagnostic_preserves_both_children_on_early_assertion(cli):
    """Exercise the real cleanup/persistence path before either worker is parsed."""
    recovery, recovery_go = _spawn_blocking_diagnostic_child()
    rec_diag = attach_worker_diagnostic(recovery, "recovery")
    comp_diag = attach_worker_diagnostic(None, "competitor")
    competitor = None
    descriptors = [recovery_go]
    trace = RaceTrace()
    failure = AssertionError("controlled failure before child parsing")
    try:
        competitor, competitor_go = _spawn_blocking_diagnostic_child()
        descriptors.append(competitor_go)
        comp_diag.proc = competitor
        assert_holder_live(recovery, stage="controlled_failure", trace=trace)
        trace.record_signal("control", "READY")
    finally:
        cleanup_race_workers(
            rec_proc=recovery, comp_proc=competitor, rec_diag=rec_diag,
            comp_diag=comp_diag, open_fds=descriptors, trace=trace,
        )
    with pytest.raises(AssertionError) as caught:
        finish_race_run(
            cli, "early_assertion", trace, race="control", competitor="control",
            proposal_id="fixture", children={"recovery": rec_diag, "competitor": comp_diag},
            race_exc=failure,
        )
    assert caught.value is failure
    packet = json.loads(t4_concurrency.race_diagnostic_path(cli, "early_assertion").read_text())
    assert packet["outcome"] == "failure"
    assert packet["cleanup_errors"] == []
    assert packet["holder_polls"][0]["returncode"] is None
    assert packet["signals"][0]["value"] == "READY"
    for child in packet["children"].values():
        assert child["returncode"] < 0
        assert "stdout-sentinel" in child["stdout"]
        assert "stderr-sentinel" in child["stderr"]
        assert child["annotations"]["killed_before_gather"] is True


def test_t4_race_diagnostic_write_failure_keeps_original_failure(cli, monkeypatch, capsys):
    def fail_write(*_args, **_kwargs):
        raise OSError("controlled diagnostic write failure")

    monkeypatch.setattr(t4_concurrency, "write_race_diagnostic", fail_write)
    original = AssertionError("original lock assertion")
    with pytest.raises(AssertionError) as caught:
        finish_race_run(
            cli, "failed_log", RaceTrace(), race="control", competitor="control",
            proposal_id="fixture", children={}, race_exc=original,
        )
    assert caught.value is original
    assert "controlled diagnostic write failure" in capsys.readouterr().err
    with pytest.raises(OSError, match="controlled diagnostic write failure"):
        finish_race_run(
            cli, "failed_success_log", RaceTrace(), race="control", competitor="control",
            proposal_id="fixture", children={}, race_exc=None,
        )

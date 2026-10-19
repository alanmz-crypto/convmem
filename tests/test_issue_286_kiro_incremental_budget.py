"""Issue #286 paid cohort enforcement, transport retries and C-KI6 durability."""

# These tests exercise the coordinator's private transport/lock boundaries.
# pylint: disable=protected-access

from __future__ import annotations

import fcntl
import json
import multiprocessing
import os
import signal
import stat
from pathlib import Path

import pytest
import requests

import chroma_write_store
import config
import incremental_jsonl
import incremental_jsonl_cohort_budget as budget
import llm
from incremental_jsonl_production import ProductionBoundary
from purge_locks import index_write_flock
from tests.incremental_jsonl_helpers import write_source


PAID_EVENT = {"provider": "deepseek", "operation": "generate"}
OPENAI_PAID_EVENT = {"provider": "openai", "operation": "generate"}
COHORT_FIELDS = (
    "cohort_ledger_path", "cohort_max_paid_http_attempts", "cohort_operation_id",
)


def _coordinator(root: Path, *, name="sess_budget", cap=5, missing=()):
    source = write_source(root, 2, name=name)
    data = root / "data"
    policy = dict(zip(COHORT_FIELDS, (str(data / "cohort.json"), cap, "budget-test")))
    for key in missing:
        policy.pop(key)
    incremental = {
        "kiro_session": policy,
        "live_sources": [str(source.resolve())],
        "state_dir": str(data / "incremental"),
        "embed_dimension": 8,
        "enabled": True,
    }
    cfg = {"index": {
        "incremental_jsonl": incremental,
        "chroma_dir": str(data / "chroma"),
        "processed_log": str(data / "processed.json"),
        "units_export": str(data / "units.jsonl"),
    }}
    boundary = ProductionBoundary(cfg, source, config_path=root / "config.toml")
    return incremental_jsonl.IncrementalJsonlCoordinator(boundary, source, cfg=cfg, enabled=True)


def _ledger(root: Path, cap=2):
    return budget.CohortBudgetLedger(budget.CohortBudgetSettings(root / "cohort.json", cap, "test"))


def _payload(ledger):
    return json.loads(ledger.settings.ledger_path.read_text(encoding="utf-8"))


def _response():
    response = requests.Response()
    response.status_code = 200
    # Deliberately no usage: successful transport still consumes the attempt.
    response._content = b'{"choices":[{"message":{"content":"done"}}]}'
    return response


def _generate():
    return llm._deepseek_generate("test", "deepseek-v4", "https://provider.invalid", retry_backoff=0)


def _frontier(*_args, **_kwargs):
    assert _generate() == "done"
    return [], 0


def _run_frontier(coordinator, monkeypatch):
    monkeypatch.setattr(coordinator, "_build_frontier", _frontier)
    coordinator._acquire_source_lock()
    try:
        return coordinator._build_frontier_with_accounting([], 0)
    finally:
        coordinator._release_source_lock()


@pytest.fixture(autouse=True)
def _deny_real_transport(monkeypatch):
    def denied(*_args, **_kwargs):
        pytest.fail("real network forbidden in cohort tests")

    monkeypatch.setattr(requests.sessions.Session, "request", denied)
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-only-not-a-credential")


def test_coordinator_wires_cohort_ledger_for_admitted_kiro(tmp_path):
    coordinator = _coordinator(tmp_path)
    assert coordinator.kiro_admitted_live
    assert coordinator.cohort_budget_enabled


@pytest.mark.parametrize("mask", range(1, 8))
def test_missing_cohort_fields_refuse_before_paid_transport(tmp_path, monkeypatch, mask):
    missing = tuple(field for index, field in enumerate(COHORT_FIELDS) if mask & (1 << index))
    dispatched = []
    monkeypatch.setattr(requests, "post", lambda *_a, **_k: dispatched.append(True))
    with pytest.raises(
        (config.IncrementalJsonlConfigError, incremental_jsonl.IncrementalJsonlError),
        match="cohort",
    ) as caught:
        coordinator = _coordinator(tmp_path, missing=missing)
        _run_frontier(coordinator, monkeypatch)
    if mask == 7:
        assert caught.value.code == "cohort_budget_required"
    assert not dispatched


@pytest.mark.parametrize("failure", [requests.Timeout, requests.ConnectionError])
@pytest.mark.parametrize("cap", [1, 2])
def test_real_deepseek_retry_settles_failure_before_next_permit(tmp_path, monkeypatch, failure, cap):
    coordinator = _coordinator(tmp_path, cap=cap)
    ledger = coordinator._cohort_ledger
    calls = []

    def post(*_args, **_kwargs):
        calls.append(_payload(ledger))
        if len(calls) == 1:
            raise failure("stubbed first attempt")
        return _response()

    monkeypatch.setattr(requests, "post", post)
    if cap == 1:
        with pytest.raises(llm.ProviderAttemptBudgetExceeded):
            _run_frontier(coordinator, monkeypatch)
    else:
        assert _run_frontier(coordinator, monkeypatch) == ([], 0)
        assert calls[1]["consumed"] == 1
        assert calls[1]["reserved"] == 1
    assert len(calls) == cap
    assert _payload(ledger)["consumed"] == cap
    assert _payload(ledger)["reserved"] == 0




def test_openai_attempt_reserves_paid_cap(tmp_path):
    ledger = _ledger(tmp_path)
    ledger.consume_provider_http_attempt(OPENAI_PAID_EVENT)
    assert _payload(ledger)["reserved"] == 1


def test_ollama_provider_event_does_not_reserve_paid_cap(tmp_path):
    ledger = _ledger(tmp_path)
    ledger.consume_provider_http_attempt({"provider": "ollama", "operation": "generate"})
    assert not ledger.settings.ledger_path.exists()

def test_unfinished_attempt_is_not_forgiven_by_usage_or_another_permit(tmp_path):
    ledger = _ledger(tmp_path)
    ledger.consume_provider_http_attempt(PAID_EVENT)
    ledger.report_provider_usage(PAID_EVENT, {})
    with pytest.raises(budget.CohortBudgetError, match="cohort_reservation_in_flight"):
        ledger.consume_provider_http_attempt(PAID_EVENT)
    assert _payload(ledger)["reserved"] == 1


@pytest.mark.parametrize("missing_budget", [False, True])
def test_local_ollama_embed_and_generate_do_not_spend_paid_cap(tmp_path, monkeypatch, missing_budget):
    coordinator = _coordinator(tmp_path, cap=1, missing=COHORT_FIELDS if missing_budget else ())
    calls = []

    def local_post(url, **_kwargs):
        calls.append(url)
        response = _response()
        response._content = b'{"embedding":[0.1,0.2],"response":"local","eval_count":1}'
        return response

    def local_frontier(*_args, **_kwargs):
        assert llm.ollama_embed("test", "local-embed", "http://local.invalid") == [0.1, 0.2]
        assert llm._ollama_generate("test", "local-model", "http://local.invalid") == "local"
        return [], 0

    monkeypatch.setattr(requests, "post", local_post)
    monkeypatch.setattr(coordinator, "_build_frontier", local_frontier)
    coordinator._acquire_source_lock()
    try:
        coordinator._build_frontier_with_accounting([], 0)
    finally:
        coordinator._release_source_lock()
    assert len(calls) == 2
    assert not (tmp_path / "data/cohort.json").exists()
    if not missing_budget:
        monkeypatch.setattr(requests, "post", lambda *_a, **_k: _response())
        _run_frontier(coordinator, monkeypatch)
        assert _payload(coordinator._cohort_ledger)["consumed"] == 1


def test_atomic_reservation_fsyncs_file_before_replace_and_parent_after(tmp_path, monkeypatch):
    ledger = _ledger(tmp_path / "new-directory")
    steps = []
    real_fsync, real_replace = os.fsync, os.replace

    def fsync(fd):
        steps.append("dir" if stat.S_ISDIR(os.fstat(fd).st_mode) else "file")
        real_fsync(fd)

    def replace(source, target):
        assert steps == ["file"]
        steps.append("replace")
        real_replace(source, target)

    monkeypatch.setattr(budget.os, "fsync", fsync)
    monkeypatch.setattr(budget.os, "replace", replace)
    ledger.consume_provider_http_attempt(PAID_EVENT)
    assert steps == ["file", "replace", "dir"]
    assert stat.S_IMODE(ledger.settings.ledger_path.stat().st_mode) == 0o600


@pytest.mark.parametrize("fail_directory", [False, True])
def test_fsync_failure_prevents_dispatch(tmp_path, monkeypatch, fail_directory):
    coordinator = _coordinator(tmp_path)
    calls = []
    real_fsync = os.fsync

    def fsync(fd):
        if stat.S_ISDIR(os.fstat(fd).st_mode) == fail_directory:
            raise OSError("injected durability failure")
        real_fsync(fd)

    monkeypatch.setattr(budget.os, "fsync", fsync)
    monkeypatch.setattr(requests, "post", lambda *_a, **_k: calls.append(True))
    with pytest.raises(OSError, match="durability failure"):
        _run_frontier(coordinator, monkeypatch)
    assert not calls


@pytest.mark.parametrize("scope", ["index", "chroma"])
def test_write_scope_refuses_before_budget_lock_or_reservation(tmp_path, monkeypatch, scope):
    coordinator = _coordinator(tmp_path)
    ledger = coordinator._cohort_ledger
    acquired = []
    monkeypatch.setattr(ledger, "_acquire_budget_lock", lambda: acquired.append(True))
    if scope == "index":
        with index_write_flock(coordinator.cfg):
            with pytest.raises(RuntimeError, match="provider calls are forbidden"):
                _run_frontier(coordinator, monkeypatch)
    else:
        chroma_write_store._enter_chroma_store_session()
        try:
            with pytest.raises(RuntimeError, match="provider calls are forbidden"):
                _run_frontier(coordinator, monkeypatch)
        finally:
            chroma_write_store._exit_chroma_store_session()
    assert not acquired
    assert not ledger.settings.ledger_path.exists()



@pytest.mark.parametrize("configured", [False, True])
def test_real_run_holds_source_lock_and_unchanged_run_does_not_pay(tmp_path, monkeypatch, configured):
    import tomllib
    import ingest
    from tests.incremental_jsonl_helpers import (
        apply_env, enable_incremental, install_fakes, isolated_env,
    )

    isolated, env = isolated_env(tmp_path)
    apply_env(monkeypatch, env)
    monkeypatch.delenv("CONVMEM_INCREMENTAL_ROOT", raising=False)
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-only")
    monkeypatch.setattr(ingest, "_SYNTHESIS_FAIL_LOG", isolated.root / "failures.jsonl")
    install_fakes(monkeypatch)
    enable_incremental(isolated)
    source = write_source(isolated.root, 2)
    cfg = tomllib.loads(isolated.layout["user_config"].read_text(encoding="utf-8"))
    policy = dict(zip(COHORT_FIELDS, (str(isolated.root / "cohort.json"), 1, "run-test")))
    cfg["index"]["incremental_jsonl"].update(
        live_sources=[str(source)], embed_dimension=8, kiro_session=policy if configured else {},
    )
    boundary = ProductionBoundary(cfg, source, config_path=isolated.layout["user_config"])
    coordinator = incremental_jsonl.IncrementalJsonlCoordinator(boundary, source, cfg=cfg)
    calls = []

    def post(*_args, **_kwargs):
        _assert_dispatch_locks(coordinator)
        assert chroma_write_store.production_chroma_store_session_depth() == 0
        calls.append(True)
        return _response()

    monkeypatch.setattr(requests, "post", post)
    monkeypatch.setattr(ingest, "summarize", lambda *_a, **_k: _generate())
    first = coordinator.run()
    if not configured:
        assert first.outcome == "cohort_budget_required"
        assert not calls
        return
    assert first.outcome == "committed"
    assert len(calls) == 1
    # A fresh invocation reuses the checkpoint even with the entire cap spent.
    coordinator = incremental_jsonl.IncrementalJsonlCoordinator(boundary, source, cfg=cfg)
    assert coordinator.run().outcome == "unchanged"
    assert len(calls) == 1
    assert _payload(coordinator._cohort_ledger)["consumed"] == 1


def _assert_dispatch_locks(coordinator):
    # Independent file descriptions prove source flock is held and budget flock is free.
    paths = (coordinator.paths["lock"], coordinator._cohort_ledger._lock_path)
    for index, path in enumerate(paths):
        fd = os.open(path, os.O_RDWR)
        try:
            if index == 0:
                with pytest.raises(BlockingIOError):
                    fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            else:
                # A peer may briefly own this lock; our own unreleased lock
                # would deadlock and fail the parent's bounded join.
                fcntl.flock(fd, fcntl.LOCK_EX)
                fcntl.flock(fd, fcntl.LOCK_UN)
        finally:
            os.close(fd)


def _process_worker(root, name, barrier, messages, crash):
    """Spawned process: real permits/transport wrapper, fake HTTP and private files."""
    with pytest.MonkeyPatch.context() as patch:
        patch.setenv("DEEPSEEK_API_KEY", "process-test-only")
        coordinator = _coordinator(Path(root), name=name, cap=2 if crash else 7)
        reservations = []

        def post(*_args, **_kwargs):
            _assert_dispatch_locks(coordinator)
            reservations.append(coordinator._cohort_ledger._open_reservation)
            if crash:
                messages.put(("reserved", os.getpid()))
                # Parent kills us only after observing the durable reservation.
                signal.pause()
                raise AssertionError("crash child unexpectedly resumed")
            if len(reservations) == 1:
                barrier.wait(timeout=20)
            return _response()

        patch.setattr(requests, "post", post)
        patch.setattr(coordinator, "_build_frontier", _frontier)
        coordinator._acquire_source_lock()
        try:
            for _ in range(8):
                try:
                    coordinator._build_frontier_with_accounting([], 0)
                except llm.ProviderAttemptBudgetExceeded:
                    break
        finally:
            coordinator._release_source_lock()
        messages.put((str(coordinator.paths["lock"]), reservations))


def _join_or_kill(processes):
    for process in processes:
        process.join(timeout=20)
    for process in processes:
        if process.is_alive():
            process.kill()
            process.join(timeout=10)


def test_two_process_sources_share_cap_without_duplicate_reservations(tmp_path):
    context = multiprocessing.get_context("spawn")
    messages = context.Queue()
    barrier = context.Barrier(2)
    processes = [context.Process(
        target=_process_worker, args=(str(tmp_path), f"sess_{index}", barrier, messages, False),
    ) for index in range(2)]
    try:
        for process in processes:
            process.start()
        results = [messages.get(timeout=30) for _ in processes]
    finally:
        _join_or_kill(processes)
    assert [process.exitcode for process in processes] == [0, 0]
    assert len({result[0] for result in results}) == 2
    reservations = [item for _, items in results for item in items]
    assert len(reservations) == len(set(reservations)) == 7
    payload = json.loads((tmp_path / "data/cohort.json").read_text())
    assert payload["consumed"] == 7
    assert payload["reserved"] == 0


def test_sigkill_after_reserve_still_counts_and_next_run_proceeds(tmp_path, monkeypatch):
    context = multiprocessing.get_context("spawn")
    messages = context.Queue()
    child = context.Process(target=_process_worker, args=(str(tmp_path), "sess_killed", None, messages, True))
    child.start()
    try:
        assert messages.get(timeout=30) == ("reserved", child.pid)
        os.kill(child.pid, signal.SIGKILL)
    finally:
        _join_or_kill([child])
    assert child.exitcode == -signal.SIGKILL
    coordinator = _coordinator(tmp_path, name="sess_killed", cap=2)
    ledger = coordinator._cohort_ledger
    assert (_payload(ledger)["reserved"], _payload(ledger)["consumed"]) == (1, 0)
    monkeypatch.setattr(requests, "post", lambda *_a, **_k: _response())
    assert _run_frontier(coordinator, monkeypatch) == ([], 0)
    assert (_payload(ledger)["reserved"], _payload(ledger)["consumed"]) == (1, 1)
    with pytest.raises(llm.ProviderAttemptBudgetExceeded):
        _run_frontier(coordinator, monkeypatch)


# ref: ../incremental_jsonl_cohort_budget.py, ../llm.py — paid attempt durability and retry lifecycle
# ref: ../incremental_jsonl.py — admitted Kiro accounting under per-source locks

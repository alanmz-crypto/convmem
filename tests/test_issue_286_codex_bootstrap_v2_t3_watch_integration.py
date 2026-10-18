"""T3 watcher subprocess deferral integration (Arc #286)."""

from __future__ import annotations

from tests.fixtures.issue_286_host_isolation import enforce_issue_286_import_guard

enforce_issue_286_import_guard()

from pathlib import Path

import pytest

import watch
from bootstrap_codex_v3_writer_coordination import COORDINATION_DEFERRAL_EXIT, CoordinationDeferralSignal
from incremental_jsonl import LIVE_ROUTE_REFUSED_EXIT

EMPTY = "{}" + chr(10)


def test_subprocess_exit93_requeues_without_breaker_side_effects(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from bootstrap_codex_v2_authority import load_authority
    from tests.fixtures.issue_286_t3_fixture import claim_active_reservation, t3_bundle

    source, cfg, grant, state_dir = t3_bundle(tmp_path, monkeypatch)
    claim_active_reservation(state_dir, grant)
    path = str(source.resolve())
    authority = load_authority(state_dir)
    assert authority is not None
    breaker = watch.CircuitBreakerState(tmp_path / "cb.json")
    signal = CoordinationDeferralSignal(path, grant["operation_id"], authority.revision)
    err = watch.IndexSubprocessError(
        signal.to_stderr_line(),
        returncode=COORDINATION_DEFERRAL_EXIT,
        stderr=signal.to_stderr_line() + "\n",
    )
    forget = watch._record_ready_path_failure(path, err, breaker=breaker, verbose=False, cfg=cfg)
    assert forget is False
    assert not breaker.has_refusal_quarantine_for_path(path)
    assert breaker._data["paths"] == {}


def test_exit93_disjoint_from_timeout_and_native_parsing() -> None:
    assert COORDINATION_DEFERRAL_EXIT not in {0, 1, LIVE_ROUTE_REFUSED_EXIT}
    assert watch.parse_native_fault_returncode("index subprocess exit 93") == 93
    assert watch.parse_native_fault_returncode("index subprocess timed out") is None


def test_broken_exit91_mapping_control_would_quarantine(tmp_path: Path) -> None:
    path = str(tmp_path / "x.jsonl")
    Path(path).write_text(EMPTY, encoding="utf-8")
    breaker = watch.CircuitBreakerState(tmp_path / "cb.json")
    marker = "live_route_refused:bootstrap_required:" + "e" * 64
    err = watch.IndexSubprocessError(marker, returncode=LIVE_ROUTE_REFUSED_EXIT, stderr=marker + chr(10))
    forget = watch._record_ready_path_failure(path, err, breaker=breaker, verbose=False)
    assert forget is True
    assert breaker.has_refusal_quarantine_for_path(path)


def test_malformed_deferral_is_failure_not_requeue(tmp_path: Path) -> None:
    path = str(tmp_path / "bad.jsonl")
    breaker = watch.CircuitBreakerState(tmp_path / "cb.json")
    err = watch.IndexSubprocessError("garbage", returncode=COORDINATION_DEFERRAL_EXIT, stderr="not-a-valid-marker" + chr(10))
    forget = watch._record_ready_path_failure(path, err, breaker=breaker, verbose=False)
    assert forget is True


def test_process_ready_path_defer_does_not_forget_scheduler(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from tests.fixtures.issue_286_t3_fixture import claim_active_reservation, t3_bundle

    source, cfg, grant, state_dir = t3_bundle(tmp_path, monkeypatch)
    claim_active_reservation(state_dir, grant)
    path = str(source.resolve())
    breaker = watch.CircuitBreakerState(tmp_path / "cb.json")
    scheduler = watch.DebounceScheduler(debounce_seconds=5.0)
    scheduler.note(path)
    from bootstrap_codex_v2_authority import load_authority

    authority = load_authority(state_dir)
    assert authority is not None
    signal = CoordinationDeferralSignal(path, grant["operation_id"], authority.revision)

    def boom(*_a, **_k):
        raise watch.IndexSubprocessError(
            signal.to_stderr_line(),
            returncode=COORDINATION_DEFERRAL_EXIT,
            stderr=signal.to_stderr_line(),
        )

    monkeypatch.setattr(watch, "flush_path", boom)
    forget = watch._process_ready_path(path, cfg=cfg, breaker=breaker, verbose=False)
    assert forget is False


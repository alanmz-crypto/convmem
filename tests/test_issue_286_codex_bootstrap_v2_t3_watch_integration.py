"""T3 watcher subprocess deferral integration (Arc #286)."""

from __future__ import annotations

from pathlib import Path

import pytest

import watch
from bootstrap_codex_v3_writer_coordination import COORDINATION_DEFERRAL_EXIT, CoordinationDeferralSignal
from incremental_jsonl import LIVE_ROUTE_REFUSED_EXIT

EMPTY = "{}" + chr(10)


def test_subprocess_exit93_requeues_without_breaker_side_effects(tmp_path: Path) -> None:
    path = str(tmp_path / "rollout.jsonl")
    Path(path).write_text(EMPTY, encoding="utf-8")
    breaker = watch.CircuitBreakerState(tmp_path / "cb.json")
    signal = CoordinationDeferralSignal(path, "d" * 64, 4)
    err = watch.IndexSubprocessError(
        "coordination",
        returncode=COORDINATION_DEFERRAL_EXIT,
        stderr=signal.to_stderr_line() + chr(10),
    )
    forget = watch._record_ready_path_failure(path, err, breaker=breaker, verbose=False)
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
    path = str(tmp_path / "defer.jsonl")
    Path(path).write_text(EMPTY, encoding="utf-8")
    breaker = watch.CircuitBreakerState(tmp_path / "cb.json")
    scheduler = watch.DebounceScheduler(debounce_seconds=5.0)
    scheduler.note(path)
    signal = CoordinationDeferralSignal(path, "f" * 64, 1)

    def boom(*_a, **_k):
        raise watch.IndexSubprocessError(
            signal.to_stderr_line(),
            returncode=COORDINATION_DEFERRAL_EXIT,
            stderr=signal.to_stderr_line(),
        )

    monkeypatch.setattr(watch, "flush_path", boom)
    forget = watch._process_ready_path(path, cfg={}, breaker=breaker, verbose=False)
    assert forget is False

def test_flush_path_subprocess_exit93_maps_to_requeue(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import config
    from tests.test_issue_286_codex_bootstrap_v2_t1 import _rollout_fixture

    source, cfg, _prefix, _boundary = _rollout_fixture(tmp_path, monkeypatch)
    path = str(source.resolve())
    toml_path = tmp_path / "config.toml"
    monkeypatch.setattr(config, "CONFIG_PATH", toml_path)
    signal = CoordinationDeferralSignal(path, "a" * 64, 2)
    stderr = signal.to_stderr_line() + chr(10)

    class _Proc:
        returncode = COORDINATION_DEFERRAL_EXIT
        pid = 4242

        def communicate(self, timeout=None):  # noqa: ARG002
            return ("", stderr)

        def __enter__(self):
            return self

        def __exit__(self, *_a):
            return False

    import subprocess

    monkeypatch.setattr(subprocess, "Popen", lambda *a, **k: _Proc())
    breaker = watch.CircuitBreakerState(tmp_path / "cb.json")
    with pytest.raises(watch.IndexSubprocessError) as raised:
        watch._flush_path_subprocess(path, verbose=False)
    forget = watch._record_ready_path_failure(path, raised.value, breaker=breaker, verbose=False)
    assert forget is False
    assert not breaker.has_refusal_quarantine_for_path(path)

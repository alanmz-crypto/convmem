"""Watch refusal quarantine corrective tests for Codex rollout admission."""

# pylint: disable=duplicate-code

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest

import watch
from tests.incremental_jsonl_helpers import codex_rollout_record
from tests.test_incremental_jsonl_codex_rollout_route import (
    _admitted_rollout,
    _sessions_root,
)
from watch import CircuitBreakerState


def test_watch_unadmitted_path_skips_prefix_digest(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    sessions = _sessions_root(tmp_path)
    sessions.mkdir(parents=True)
    admitted = datetime(2026, 6, 1, tzinfo=timezone.utc)
    source = _admitted_rollout(sessions, admitted)
    breaker = CircuitBreakerState(tmp_path / "breaker.json")

    def boom(*_args, **_kwargs):
        raise AssertionError("prefix digest read")

    monkeypatch.setattr(
        "adapters.jsonl_prefix.streaming_complete_prefix_digest_for_path",
        boom,
    )
    calls: list[str] = []
    monkeypatch.setattr(
        watch,
        "flush_path",
        lambda path, **kwargs: calls.append(path),
    )
    watch._process_ready_path(str(source), cfg={}, breaker=breaker, verbose=False)
    assert calls == [str(source)]


def test_record_refusal_prefers_child_marker_digest(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    path = str(tmp_path / "rollout.jsonl")
    Path(path).write_text("{}\n", encoding="utf-8")
    breaker = CircuitBreakerState(tmp_path / "breaker.json")
    marker_digest = "a" * 64

    def boom(*_args, **_kwargs):
        raise AssertionError("streaming digest should not run when marker carries digest")

    monkeypatch.setattr(
        "adapters.jsonl_prefix.streaming_complete_prefix_digest_for_path",
        boom,
    )
    watch._record_ready_path_failure(
        path,
        RuntimeError(f"live_route_refused:bootstrap_required:{marker_digest}"),
        breaker=breaker,
        verbose=False,
    )
    assert breaker.is_refusal_quarantined(path, marker_digest)


def test_refusal_quarantine_terminal_path_skips_digest_after_appends(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """§13 c3/c4: one refusal quarantines the path; later digest changes do not respawn."""
    monkeypatch.setenv("HOME", str(tmp_path))
    sessions = _sessions_root(tmp_path)
    sessions.mkdir(parents=True)
    admitted = datetime(2026, 6, 1, tzinfo=timezone.utc)
    source = _admitted_rollout(sessions, admitted)
    breaker = CircuitBreakerState(tmp_path / "breaker.json")
    breaker.record_refusal(
        str(source),
        outcome="bootstrap_required",
        prefix_digest="deadbeef" * 8,
    )
    flush_calls: list[str] = []

    def track_flush(path: str, **kwargs):  # noqa: ANN003
        flush_calls.append(path)

    def boom(*_args, **_kwargs):
        raise AssertionError("prefix digest must not be computed for terminal quarantine")

    monkeypatch.setattr(watch, "flush_path", track_flush)
    monkeypatch.setattr(
        "adapters.jsonl_prefix.streaming_complete_prefix_digest_for_path",
        boom,
    )
    for index in range(3):
        with source.open("ab") as handle:
            handle.write(codex_rollout_record(40 + index))
        watch._process_ready_path(str(source), cfg={}, breaker=breaker, verbose=False)
    assert flush_calls == []

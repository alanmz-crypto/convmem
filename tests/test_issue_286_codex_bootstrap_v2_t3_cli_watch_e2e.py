"""T3 real CLI child + watch parent chain (Arc #286)."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

import watch
from bootstrap_codex_v2_authority import load_authority, publish_terminal_authority
from bootstrap_codex_v3_writer_coordination import COORDINATION_DEFERRAL_EXIT, CoordinationDeferralSignal
from incremental_jsonl import LIVE_ROUTE_REFUSED_EXIT
from repository_knowledge_sync import watcher_child_index_argv
from tests.fixtures.issue_286_t3_fixture import claim_active_reservation, t3_bundle
from tests.test_incremental_jsonl_codex_rollout_route import _admitted_rollout, _sessions_root
from watch import CircuitBreakerState, DebounceScheduler

REPO_ROOT = Path(__file__).resolve().parents[1]
CONVMEM = REPO_ROOT / "convmem.py"


def _run_index_child(path: str, *, env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    cmd = watcher_child_index_argv(path)
    env = watch._sanitize_index_child_env(env)
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        env=env,
        cwd=str(REPO_ROOT),
        timeout=60,
    )


def test_real_cli_child_coordination_deferral_exit93(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    source, cfg, grant, state_dir = t3_bundle(tmp_path, monkeypatch)
    claim_active_reservation(state_dir, grant)
    path = str(source.resolve())
    env = os.environ.copy()
    env["CONVMEM_CONFIG"] = str(tmp_path / "config.toml")
    proc = _run_index_child(path, env=env)
    assert proc.returncode == COORDINATION_DEFERRAL_EXIT
    assert "coordination_deferral:" in (proc.stderr or "")


def test_flush_path_subprocess_real_child_then_parent_requeue(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import config

    source, cfg, grant, state_dir = t3_bundle(tmp_path, monkeypatch)
    claim_active_reservation(state_dir, grant)
    path = str(source.resolve())
    toml = tmp_path / "config.toml"
    monkeypatch.setattr(config, "CONFIG_PATH", toml)
    breaker = CircuitBreakerState(tmp_path / "cb.json")
    breaker_path = tmp_path / "cb.json"
    breaker_path.write_text(json.dumps({"paths": {}, "global": {}}), encoding="utf-8")
    before = breaker_path.read_bytes()
    with pytest.raises(watch.IndexSubprocessError) as exc_info:
        watch._flush_path_subprocess(path, verbose=False)
    assert exc_info.value.returncode == COORDINATION_DEFERRAL_EXIT
    forget = watch._record_ready_path_failure(path, exc_info.value, breaker=breaker, verbose=False, cfg=cfg)
    assert forget is False
    assert breaker_path.read_bytes() == before
    assert not breaker.has_refusal_quarantine_for_path(path)


def test_process_ready_path_real_subprocess_defer_scheduler_backoff(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import config

    source, cfg, grant, state_dir = t3_bundle(tmp_path, monkeypatch)
    claim_active_reservation(state_dir, grant)
    path = str(source.resolve())
    monkeypatch.setattr(config, "CONFIG_PATH", tmp_path / "config.toml")
    breaker = CircuitBreakerState(tmp_path / "cb.json")
    scheduler = DebounceScheduler(debounce_seconds=30.0)
    scheduler.note(path)
    forget = watch._process_ready_path(path, cfg=cfg, breaker=breaker, verbose=False)
    assert forget is False
    assert scheduler.pending_count() == 1
    assert path not in scheduler.ready()


def test_fabricated_deferral_revision_mismatch_after_terminal_refuses_requeue(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import config
    from tests.fixtures.issue_286_t2_owner_context import t2_owner_context

    source, cfg, grant, state_dir = t3_bundle(tmp_path, monkeypatch)
    claim_active_reservation(state_dir, grant)
    path = str(source.resolve())
    monkeypatch.setattr(config, "CONFIG_PATH", tmp_path / "config.toml")
    with t2_owner_context(state_dir):
        publish_terminal_authority(state_dir, grant, receipt_digest="a" * 64)
    authority = load_authority(state_dir)
    assert authority is not None and authority.terminal
    fabricated_revision = int(authority.revision) + 1
    signal = CoordinationDeferralSignal(path, grant["operation_id"], fabricated_revision)
    err = watch.IndexSubprocessError(
        signal.to_stderr_line(),
        returncode=COORDINATION_DEFERRAL_EXIT,
        stderr=signal.to_stderr_line() + "\n",
    )
    breaker = CircuitBreakerState(tmp_path / "cb.json")
    breaker_path = tmp_path / "cb.json"
    breaker_path.write_text(json.dumps({"paths": {}, "global": {}}), encoding="utf-8")
    before = breaker_path.read_bytes()
    forget = watch._record_ready_path_failure(path, err, breaker=breaker, verbose=False, cfg=cfg)
    assert forget is True
    assert breaker_path.read_bytes() == before


def test_real_child_deferral_after_terminal_authority_still_requeues(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import config
    from tests.fixtures.issue_286_t2_owner_context import t2_owner_context

    source, cfg, grant, state_dir = t3_bundle(tmp_path, monkeypatch)
    claim_active_reservation(state_dir, grant)
    path = str(source.resolve())
    monkeypatch.setattr(config, "CONFIG_PATH", tmp_path / "config.toml")
    env = os.environ.copy()
    env["CONVMEM_CONFIG"] = str(config.CONFIG_PATH)
    proc = _run_index_child(path, env=env)
    assert proc.returncode == COORDINATION_DEFERRAL_EXIT
    authority = load_authority(state_dir)
    assert authority is not None
    with t2_owner_context(state_dir):
        publish_terminal_authority(state_dir, grant, receipt_digest="b" * 64)
    err = watch.IndexSubprocessError(
        (proc.stderr or "").strip(),
        returncode=proc.returncode,
        stderr=proc.stderr or "",
    )
    breaker = CircuitBreakerState(tmp_path / "cb-term-race.json")
    breaker_path = tmp_path / "cb-term-race.json"
    breaker_path.write_text(json.dumps({"paths": {}, "global": {}}), encoding="utf-8")
    before = breaker_path.read_bytes()
    scheduler = DebounceScheduler(debounce_seconds=30.0)
    scheduler.note(path)
    forget = watch._record_ready_path_failure(
        path, err, breaker=breaker, verbose=False, cfg=cfg
    )
    assert forget is False
    assert breaker_path.read_bytes() == before
    assert not breaker.has_refusal_quarantine_for_path(path)
    assert scheduler.pending_count() == 1
    assert path not in scheduler.ready()


def test_real_child_deferral_after_multi_progress_terminal_still_requeues(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import config
    from bootstrap_codex_v2_authority import publish_authority_progress
    from tests.fixtures.issue_286_t2_owner_context import t2_owner_context

    source, cfg, grant, state_dir = t3_bundle(tmp_path, monkeypatch)
    claim_active_reservation(state_dir, grant)
    path = str(source.resolve())
    monkeypatch.setattr(config, "CONFIG_PATH", tmp_path / "config.toml")
    env = os.environ.copy()
    env["CONVMEM_CONFIG"] = str(config.CONFIG_PATH)
    proc = _run_index_child(path, env=env)
    assert proc.returncode == COORDINATION_DEFERRAL_EXIT
    authority = load_authority(state_dir)
    assert authority is not None
    deferral_revision = int(authority.revision)
    with t2_owner_context(state_dir):
        publish_authority_progress(
            state_dir, grant, progress={"checkpoint_digest": "c" * 64}
        )
        publish_authority_progress(
            state_dir, grant, progress={"prepared_lineage_digest": "d" * 64}
        )
        publish_terminal_authority(state_dir, grant, receipt_digest="e" * 64)
    terminal = load_authority(state_dir)
    assert terminal is not None and terminal.terminal
    assert int(terminal.revision) >= deferral_revision + 3
    err = watch.IndexSubprocessError(
        (proc.stderr or "").strip(),
        returncode=proc.returncode,
        stderr=proc.stderr or "",
    )
    breaker = CircuitBreakerState(tmp_path / "cb-multi-progress.json")
    breaker_path = tmp_path / "cb-multi-progress.json"
    breaker_path.write_text(json.dumps({"paths": {}, "global": {}}), encoding="utf-8")
    before = breaker_path.read_bytes()
    scheduler = DebounceScheduler(debounce_seconds=30.0)
    scheduler.note(path)
    forget = watch._record_ready_path_failure(
        path, err, breaker=breaker, verbose=False, cfg=cfg
    )
    assert forget is False
    assert breaker_path.read_bytes() == before
    assert not breaker.has_refusal_quarantine_for_path(path)
    assert scheduler.pending_count() == 1
    assert path not in scheduler.ready()


def test_preexisting_refusal_quarantine_skips_real_spawn(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    source, cfg, grant, state_dir = t3_bundle(tmp_path, monkeypatch)
    path = str(source.resolve())
    breaker = CircuitBreakerState(tmp_path / "cb.json")
    breaker.record_refusal(path, outcome="bootstrap_required", prefix_digest="b" * 64)
    calls = 0

    def track(*_a, **_k):
        nonlocal calls
        calls += 1
        raise AssertionError("spawn")

    monkeypatch.setattr(watch, "flush_path", track)
    watch._process_ready_path(path, cfg=cfg, breaker=breaker, verbose=False)
    assert calls == 0


def test_real_cli_bootstrap_required_exit91_unreserved_route(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import config
    import shutil
    from datetime import datetime, timezone

    from incremental_jsonl import source_state_id
    from tests.fixtures.issue_286_t3_fixture import worker_config_path

    sessions = _sessions_root(Path(os.environ["HOME"]))
    sessions.mkdir(parents=True, exist_ok=True)
    admitted = datetime(2026, 6, 1, tzinfo=timezone.utc)
    source = _admitted_rollout(sessions, admitted)
    from tests.test_incremental_jsonl_codex_rollout_route import _production_cfg, _write_user_config

    cfg = _production_cfg(tmp_path, sessions, admitted)
    path_key = str(source.resolve())
    table = dict(cfg["index"].get("incremental_jsonl") or {})
    table.update(enabled=True)
    cfg["index"]["incremental_jsonl"] = table
    toml = worker_config_path()
    toml.parent.mkdir(parents=True, exist_ok=True)
    _write_user_config(toml, cfg)
    models = cfg["models"]
    with toml.open("a", encoding="utf-8") as handle:
        handle.write(
            "\n[models]\n"
            f'summarize_model = "{models["summarize_model"]}"\n'
            f'distill_model = "{models["distill_model"]}"\n'
            f'embed_model = "{models["embed_model"]}"\n'
            f'ollama_host = "{models["ollama_host"]}"\n'
        )
    monkeypatch.setattr(config, "CONFIG_PATH", toml)
    processed_path = Path(cfg["index"]["processed_log"])
    processed_path.parent.mkdir(parents=True, exist_ok=True)
    processed_path.write_text(
        json.dumps({"legacy_processed": {"path": path_key, "chunks": 1, "units": 1}}),
        encoding="utf-8",
    )
    source_state = Path(cfg["index"]["incremental_jsonl"]["state_dir"]) / source_state_id(
        path_key, format_id="jsonl_codex_rollout"
    )
    if source_state.exists():
        shutil.rmtree(source_state)
    env = os.environ.copy()
    env.pop("CONVMEM_INCREMENTAL_ROOT", None)
    proc = _run_index_child(path_key, env=env)
    assert proc.returncode == LIVE_ROUTE_REFUSED_EXIT
    assert "live_route_refused" in (proc.stderr or "")
    breaker = CircuitBreakerState(tmp_path / "cb-br.json")
    err = watch.IndexSubprocessError(
        proc.stderr.strip() or "live_route_refused",
        returncode=proc.returncode,
        stderr=proc.stderr or "",
    )
    forget = watch._record_ready_path_failure(path_key, err, breaker=breaker, verbose=False, cfg=cfg)
    assert forget is True
    assert breaker.has_refusal_quarantine_for_path(path_key)

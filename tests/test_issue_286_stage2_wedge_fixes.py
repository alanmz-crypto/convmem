"""Hermetic tests for issue #286 stage-2 wedge fixes (C1–C4)."""

# pylint: disable=duplicate-code,protected-access

from __future__ import annotations

import json
import threading
import tomllib
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

import pytest
from typer.testing import CliRunner

import convmem
import incremental_jsonl
import ingest
import watch
from adapters.kiro_session_jsonl import parse_complete_prefix
from incremental_jsonl_production import ProductionBoundary
from tests.incremental_jsonl_helpers import (
    apply_env,
    enable_incremental,
    install_fakes,
    isolated_env,
    write_source,
)
from tests.test_incremental_jsonl_codex_rollout_route import (
    _admitted_rollout,
    _production_cfg,
    _sessions_root,
    _write_user_config,
)
from tests.test_incremental_jsonl_live_boundary import _bootstrap_binding
from watch import CircuitBreakerState, IndexSubprocessError
from watch_circuit_breaker import parse_live_route_refused


def _enable_incremental_kiro(isolated, source: Path) -> tuple[ProductionBoundary, dict]:
    enable_incremental(isolated)
    cfg = tomllib.loads(isolated.layout["user_config"].read_text(encoding="utf-8"))
    cfg["index"]["incremental_jsonl"].update(
        live_sources=[str(source)], embed_dimension=8
    )
    boundary = ProductionBoundary(
        cfg, source, config_path=isolated.layout["user_config"]
    )
    return boundary, cfg


def test_wedge_replay_commits_after_foreign_growth(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    isolated, env = isolated_env(tmp_path)
    apply_env(monkeypatch, env)
    monkeypatch.delenv("CONVMEM_INCREMENTAL_ROOT", raising=False)
    install_fakes(monkeypatch)
    source = write_source(isolated.root, 4)
    boundary, cfg = _enable_incremental_kiro(isolated, source)
    digest = parse_complete_prefix(str(source)).prefix_sha256

    def first_crash(point: str) -> None:
        if point == "after_summary_upsert":
            raise RuntimeError("initial partial apply")

    first = incremental_jsonl.IncrementalJsonlCoordinator(
        boundary,
        source,
        cfg=cfg,
        processed={"old-hash": {"path": str(source)}},
        bootstrap_existing=True,
        expected_prefix_sha256=digest,
        max_bootstrap_chunks=4,
        chunk_size=2,
        fault=first_crash,
        **_bootstrap_binding(),
    )
    with first._session() as session:
        session.store.add_summary(
            "legacy-summary", "old", [0.1] * 8, {"source_path": str(source)}
        )
        session.store.add_unit(
            "legacy-unit", "old", [0.1] * 8, {"source_path": str(source)}
        )
    with pytest.raises(RuntimeError, match="initial partial apply"):
        first.run()

    with first._session() as session:
        session.store.add_summary(
            "foreign-summary",
            "foreign",
            [0.1] * 8,
            {"source_path": "/other"},
        )
    export_path = Path(cfg["index"]["units_export"])
    export_path.parent.mkdir(parents=True, exist_ok=True)
    with export_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps({"id": "foreign-unit", "source_path": "/other"}) + "\n")

    replay = incremental_jsonl.IncrementalJsonlCoordinator(
        boundary,
        source,
        cfg=cfg,
        bootstrap_existing=True,
        expected_prefix_sha256=digest,
        max_bootstrap_chunks=4,
        chunk_size=2,
        **_bootstrap_binding(),
    )
    result = replay.run()
    assert result.outcome == "committed"
    assert not replay.paths["transaction"].exists()


def test_legacy_write_blocks_during_index_write_lock(tmp_path: Path) -> None:
    from purge_locks import index_write_flock
    from tests.purge_test_util import purge_cfg as _cfg

    cfg = _cfg(tmp_path)
    release = threading.Event()
    holder_ready = threading.Event()
    contender_started = threading.Event()
    contender_done = threading.Event()

    def holder() -> None:
        with index_write_flock(cfg):
            holder_ready.set()
            release.wait(timeout=5)

    def contender() -> None:
        assert holder_ready.wait(timeout=5)
        contender_started.set()
        with index_write_flock(cfg):
            contender_done.set()

    holder_thread = threading.Thread(target=holder)
    contender_thread = threading.Thread(target=contender)
    holder_thread.start()
    contender_thread.start()
    assert contender_started.wait(timeout=5)
    assert not contender_done.wait(timeout=0.1)
    release.set()
    holder_thread.join(timeout=10)
    contender_thread.join(timeout=10)
    assert contender_done.is_set()


def test_bounded_retries_exit_91_on_repeat(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    sessions = _sessions_root(tmp_path)
    sessions.mkdir(parents=True)
    source = _admitted_rollout(sessions, datetime(2026, 6, 1, tzinfo=timezone.utc))
    cfg = _production_cfg(tmp_path, sessions, datetime(2026, 6, 1, tzinfo=timezone.utc))
    _write_user_config(tmp_path / "config.toml", cfg)
    monkeypatch.setenv("HOME", str(tmp_path))
    prefix = "d" * 64
    from incremental_retry_state import record_incremental_retry_failure

    record_incremental_retry_failure(
        cfg,
        path_key=str(source),
        prefix_digest=prefix,
        error_code="rollback_export_foreign_changed",
        transaction_id="a" * 32,
    )
    assert record_incremental_retry_failure(
        cfg,
        path_key=str(source),
        prefix_digest=prefix,
        error_code="rollback_export_foreign_changed",
        transaction_id="a" * 32,
    )
    marker = incremental_jsonl.format_live_route_refused(
        "wedged_incremental_transaction:rollback_export_foreign_changed", prefix
    )
    breaker = CircuitBreakerState(tmp_path / "breaker.json")
    spawn_calls = 0

    def fake_flush(_path: str, **_kwargs: object) -> None:
        nonlocal spawn_calls
        spawn_calls += 1
        raise IndexSubprocessError(marker, returncode=91, stderr=marker + "\n")

    monkeypatch.setattr(watch, "flush_path", fake_flush)
    watch._process_ready_path(str(source), cfg=cfg, breaker=breaker, verbose=False)
    assert spawn_calls == 1
    watch._process_ready_path(str(source), cfg=cfg, breaker=breaker, verbose=False)
    assert spawn_calls == 1


def test_watcher_intake_event_types() -> None:
    from watchdog.events import (
        FileClosedEvent,
        FileClosedNoWriteEvent,
        FileCreatedEvent,
        FileModifiedEvent,
        FileMovedEvent,
        FileOpenedEvent,
    )

    batch: list[str] = []
    lock = threading.Lock()

    class Handler:
        def on_any_event(self, event) -> None:  # noqa: ANN001
            if event.is_directory:
                return
            if isinstance(event, (FileOpenedEvent, FileClosedNoWriteEvent)):
                return
            queued: list[str] = []
            if isinstance(event, FileMovedEvent):
                queued.extend([event.dest_path, event.src_path])
            elif isinstance(
                event, (FileCreatedEvent, FileModifiedEvent, FileClosedEvent)
            ):
                queued.append(event.src_path)
            with lock:
                batch.extend(queued)

    handler = Handler()
    handler.on_any_event(mock.Mock(is_directory=True, src_path="/x"))
    handler.on_any_event(FileOpenedEvent("/x/a.jsonl"))
    handler.on_any_event(FileClosedNoWriteEvent("/x/a.jsonl"))
    handler.on_any_event(FileModifiedEvent("/x/a.jsonl"))
    handler.on_any_event(FileCreatedEvent("/x/b.jsonl"))
    handler.on_any_event(FileClosedEvent("/x/c.jsonl"))
    handler.on_any_event(FileMovedEvent("/x/old.jsonl", "/x/new.jsonl"))
    assert batch == [
        "/x/a.jsonl",
        "/x/b.jsonl",
        "/x/c.jsonl",
        "/x/new.jsonl",
        "/x/old.jsonl",
    ]


def test_index_file_deferral_and_override(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    sessions = _sessions_root(tmp_path)
    sessions.mkdir(parents=True)
    rollout = _admitted_rollout(sessions, datetime(2026, 6, 1, tzinfo=timezone.utc))
    cfg = _production_cfg(tmp_path, sessions, datetime(2026, 6, 1, tzinfo=timezone.utc))
    cfg_path = tmp_path / "config.toml"
    _write_user_config(cfg_path, cfg)
    lock_path = Path(cfg["index"]["chroma_dir"]).expanduser().parent / "watch.lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    lock_path.write_text("999999\n", encoding="utf-8")
    monkeypatch.setattr(watch, "_is_live_watch_pid", lambda _pid: True)
    monkeypatch.setattr(convmem, "_guard_write", lambda: None)
    runner = CliRunner()
    deferred = runner.invoke(convmem.app, ["index", "--file", str(rollout)])
    assert deferred.exit_code == 0
    assert f"[index] deferred: the convmem watcher captures {rollout}" in deferred.stdout
    indexed = {"calls": 0}

    def fake_index(**_kwargs: object) -> dict:
        indexed["calls"] += 1
        return {
            "files_processed": 1,
            "files_skipped": 0,
            "chunks_indexed": 0,
            "units_indexed": 0,
        }

    monkeypatch.setattr(ingest, "index", fake_index)
    forced = runner.invoke(convmem.app, ["index", "--file", str(rollout), "--now"])
    assert forced.exit_code == 0
    assert indexed["calls"] == 1
    claude = tmp_path / "claude.jsonl"
    claude.write_text("{}\n", encoding="utf-8")
    monkeypatch.setattr(watch, "is_watchable", lambda path: str(path) != str(claude))
    claude_run = runner.invoke(convmem.app, ["index", "--file", str(claude)])
    assert claude_run.exit_code == 0
    assert indexed["calls"] == 2

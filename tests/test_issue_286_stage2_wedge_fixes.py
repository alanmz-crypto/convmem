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

import config
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
from watch import CircuitBreakerState, IndexSubprocessError, queue_paths_from_fs_event
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


def test_replay_error_after_foreign_growth_rolls_back(
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

    def replay_fail(point: str) -> None:
        if point == "before_summary_upsert":
            raise incremental_jsonl.IncrementalJsonlError("dedupe_prefix_changed")

    replay = incremental_jsonl.IncrementalJsonlCoordinator(
        boundary,
        source,
        cfg=cfg,
        bootstrap_existing=True,
        expected_prefix_sha256=digest,
        max_bootstrap_chunks=4,
        chunk_size=2,
        fault=replay_fail,
        **_bootstrap_binding(),
    )
    result = replay.run()
    assert result.outcome == "rolled_back"


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
    paths = {
        "transaction": tmp_path / "incremental-jsonl" / "tx" / "transaction.json",
    }
    paths["transaction"].parent.mkdir(parents=True, exist_ok=True)
    from incremental_retry_state import record_incremental_retry_failure

    record_incremental_retry_failure(
        paths,
        path_key=str(source),
        prefix_digest=prefix,
        error_code="rollback_export_foreign_changed",
        transaction_id="a" * 32,
    )
    assert record_incremental_retry_failure(
        paths,
        path_key=str(source),
        prefix_digest=prefix,
        error_code="rollback_export_foreign_changed",
        transaction_id="a" * 32,
    )
    outcome = incremental_jsonl.wedged_incremental_outcome(
        "rollback_export_foreign_changed"
    )
    marker = incremental_jsonl.format_live_route_refused(outcome, prefix)
    assert parse_live_route_refused(marker) == (outcome, prefix)
    breaker = CircuitBreakerState(tmp_path / "breaker.json")
    spawn_calls = 0

    def fake_flush(_path: str, **_kwargs: object) -> None:
        nonlocal spawn_calls
        spawn_calls += 1
        raise IndexSubprocessError(marker, returncode=91, stderr=marker + "\n")

    monkeypatch.setattr(watch, "flush_path", fake_flush)
    monkeypatch.setattr(
        watch,
        "source_prefix_digest_for_watch",
        lambda _path: prefix,
    )
    watch._process_ready_path(str(source), cfg=cfg, breaker=breaker, verbose=False)
    assert spawn_calls == 1
    watch._process_ready_path(str(source), cfg=cfg, breaker=breaker, verbose=False)
    assert spawn_calls == 1
    monkeypatch.setattr(
        watch,
        "source_prefix_digest_for_watch",
        lambda _path: "e" * 64,
    )
    watch._process_ready_path(str(source), cfg=cfg, breaker=breaker, verbose=False)
    assert spawn_calls == 2


def test_watcher_intake_event_types() -> None:
    pytest.importorskip("watchdog")
    from watchdog.events import (
        FileClosedEvent,
        FileClosedNoWriteEvent,
        FileCreatedEvent,
        FileDeletedEvent,
        FileModifiedEvent,
        FileMovedEvent,
        FileOpenedEvent,
    )

    batch: list[str] = []
    for event in (
        mock.Mock(is_directory=True, src_path="/x"),
        FileOpenedEvent("/x/a.jsonl"),
        FileClosedNoWriteEvent("/x/a.jsonl"),
        FileModifiedEvent("/x/a.jsonl"),
        FileCreatedEvent("/x/b.jsonl"),
        FileClosedEvent("/x/c.jsonl"),
        FileDeletedEvent("/x/removed.jsonl"),
        FileMovedEvent("/x/old.jsonl", "/x/new.jsonl"),
    ):
        batch.extend(queue_paths_from_fs_event(event))
    assert batch == [
        "/x/a.jsonl",
        "/x/b.jsonl",
        "/x/c.jsonl",
        "/x/removed.jsonl",
        "/x/new.jsonl",
        "/x/old.jsonl",
    ]


def test_index_file_deferral_and_override(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    sessions = _sessions_root(tmp_path)
    sessions.mkdir(parents=True)
    rollout = _admitted_rollout(sessions, datetime(2026, 6, 1, tzinfo=timezone.utc))
    cfg = _production_cfg(tmp_path, sessions, datetime(2026, 6, 1, tzinfo=timezone.utc))
    cfg["watch"] = {"paths": [str(sessions)]}
    cfg_path = tmp_path / "config.toml"
    _write_user_config(cfg_path, cfg)
    watch_paths = cfg.get("watch", {}).get("paths") or []
    if watch_paths:
        quoted = ", ".join(f'"{p}"' for p in watch_paths)
        cfg_path.write_text(
            cfg_path.read_text(encoding="utf-8")
            + f"\n[watch]\npaths = [{quoted}]\n",
            encoding="utf-8",
        )
    monkeypatch.setenv("CONVMEM_CONFIG", str(cfg_path))
    monkeypatch.setattr(config, "CONFIG_PATH", cfg_path)
    _real_is_watchable = watch.is_watchable

    def _watchable_for_defer(path: Path | str) -> bool:
        candidate = Path(path)
        if candidate == rollout:
            return True
        if candidate.name == "claude.jsonl":
            return False
        return _real_is_watchable(candidate)

    monkeypatch.setattr(watch, "is_watchable", _watchable_for_defer)
    lock_path = Path(cfg["index"]["chroma_dir"]).expanduser().parent / "watch.lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    lock_path.write_text("999999\n", encoding="utf-8")
    monkeypatch.setattr(watch, "_is_live_watch_pid", lambda _pid: True)
    monkeypatch.setattr(convmem, "_guard_write", lambda: None)
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
    runner = CliRunner()
    deferred = runner.invoke(convmem.app, ["index", "--file", str(rollout)])
    assert deferred.exit_code == 0
    assert f"[index] deferred: the convmem watcher captures {rollout}" in deferred.stdout
    assert indexed["calls"] == 0
    forced = runner.invoke(convmem.app, ["index", "--file", str(rollout), "--now"])
    assert forced.exit_code == 0
    assert indexed["calls"] == 1
    claude = tmp_path / "claude.jsonl"
    claude.write_text("{}\n", encoding="utf-8")
    claude_run = runner.invoke(convmem.app, ["index", "--file", str(claude)])
    assert claude_run.exit_code == 0
    assert indexed["calls"] == 2


def test_export_tamper_still_refused(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    isolated, env = isolated_env(tmp_path)
    apply_env(monkeypatch, env)
    monkeypatch.delenv("CONVMEM_INCREMENTAL_ROOT", raising=False)
    install_fakes(monkeypatch)
    source = write_source(isolated.root, 2)
    boundary, cfg = _enable_incremental_kiro(isolated, source)
    coord = incremental_jsonl.IncrementalJsonlCoordinator(
        boundary,
        source,
        cfg=cfg,
        chunk_size=2,
        **_bootstrap_binding(),
    )
    export_path = Path(cfg["index"]["units_export"])
    export_path.parent.mkdir(parents=True, exist_ok=True)
    good = (
        json.dumps(
            {"source_path": str(source), "id": "owned-a"},
            separators=(",", ":"),
        )
        + "\n"
    ).encode("utf-8")
    bad = json.dumps({"id": "owned-a", "source_path": str(source), "x": 1}).encode() + b"\n"
    export_path.write_bytes(bad)
    preimage = {
        "version": 1,
        "existed": True,
        "source_lines": [
            {
                "foreign_lines_before": 0,
                "payload_base64": __import__("base64").b64encode(good).decode("ascii"),
            }
        ],
        "foreign_lines": 0,
    }
    coord._restore_export(preimage)
    assert export_path.read_bytes() == good

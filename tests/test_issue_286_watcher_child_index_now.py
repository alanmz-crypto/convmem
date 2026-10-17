"""Regression: watcher index children must pass --now so they do not self-defer."""

# pylint: disable=duplicate-code,protected-access

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest
from typer.testing import CliRunner

import config
import convmem
import ingest
import watch
from repository_knowledge_sync import public_index_argv
from tests.test_incremental_jsonl_codex_rollout_route import (
    _admitted_rollout,
    _production_cfg,
    _sessions_root,
    _write_user_config,
)


def _deferral_fixture(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> tuple[Path, dict]:
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
        return _real_is_watchable(candidate)

    monkeypatch.setattr(watch, "is_watchable", _watchable_for_defer)
    lock_path = Path(cfg["index"]["chroma_dir"]).expanduser().parent / "watch.lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    lock_path.write_text("999999\n", encoding="utf-8")
    monkeypatch.setattr(watch, "_is_live_watch_pid", lambda _pid: True)
    assert watch.should_defer_index_file(cfg, str(rollout))
    return rollout, cfg


def test_watcher_child_argv_indexes_under_live_watch_lock(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    rollout, _cfg = _deferral_fixture(tmp_path, monkeypatch)
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
    argv = public_index_argv(str(rollout))
    assert argv[-4:] == ["index", "--file", str(rollout), "--now"]
    runner = CliRunner()
    result = runner.invoke(convmem.app, argv[2:])
    assert result.exit_code == 0
    assert "deferred" not in (result.stdout + result.stderr).lower()
    assert indexed["calls"] == 1

    manual = runner.invoke(convmem.app, ["index", "--file", str(rollout)])
    assert manual.exit_code == 0
    assert f"[index] deferred: the convmem watcher captures {rollout}" in manual.stdout
    assert indexed["calls"] == 1

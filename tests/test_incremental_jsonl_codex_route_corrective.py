"""Production-route corrective tests for Codex rollout admission."""

# pylint: disable=duplicate-code,protected-access

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

import pytest

import incremental_jsonl
from incremental_jsonl_production import ProductionBoundary
from tests.incremental_jsonl_helpers import codex_rollout_record, install_fakes
from tests.test_incremental_jsonl_codex_rollout_route import (
    _admitted_rollout,
    _production_cfg,
    _sessions_root,
    _write_user_config,
)


def _coordinator(boundary, source, cfg, **kwargs):
    defaults = {
        "cfg": cfg,
        "enabled": True,
        "chunk_size": 4,
        "overlap": 0,
        "min_confidence": 0.6,
        "embed_dimension": 8,
        "processed": {},
    }
    defaults.update(kwargs)
    return incremental_jsonl.IncrementalJsonlCoordinator(boundary, source, **defaults)


def test_source_too_large_refuses_before_full_read(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    sessions = _sessions_root(tmp_path)
    sessions.mkdir(parents=True)
    admitted = datetime(2026, 6, 1, tzinfo=timezone.utc)
    source = _admitted_rollout(sessions, admitted)
    cfg = _production_cfg(tmp_path, sessions, admitted)
    cfg["index"]["incremental_jsonl"]["codex_rollout_admission"]["max_source_bytes"] = 64
    cfg_path = tmp_path / "config.toml"
    _write_user_config(cfg_path, cfg)
    monkeypatch.delenv("CONVMEM_INCREMENTAL_ROOT", raising=False)
    install_fakes(monkeypatch)
    reads: list[int] = []
    real_read = os.read

    def track_read(fd, size):  # noqa: ANN001
        reads.append(size)
        return real_read(fd, size)

    monkeypatch.setattr(os, "read", track_read)
    boundary = ProductionBoundary(cfg, source, config_path=cfg_path)
    result = _coordinator(boundary, source, cfg).run()
    assert result.outcome == "source_too_large"
    assert reads == []
    assert result.counters.total == 0


def test_frontier_violation_refuses_without_provider_calls(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    sessions = _sessions_root(tmp_path)
    sessions.mkdir(parents=True)
    admitted = datetime(2026, 6, 1, tzinfo=timezone.utc)
    source = _admitted_rollout(sessions, admitted)
    cfg = _production_cfg(tmp_path, sessions, admitted)
    cfg_path = tmp_path / "config.toml"
    _write_user_config(cfg_path, cfg)
    monkeypatch.delenv("CONVMEM_INCREMENTAL_ROOT", raising=False)
    install_fakes(monkeypatch)
    boundary = ProductionBoundary(cfg, source, config_path=cfg_path)
    monkeypatch.setattr(
        incremental_jsonl.IncrementalJsonlCoordinator,
        "_allowed_transform_starts",
        lambda self, messages, prior: frozenset({0}),
    )
    monkeypatch.setattr(
        incremental_jsonl.IncrementalJsonlCoordinator,
        "_planned_transform_starts",
        lambda self, messages, *, cache_required_before: {999},
    )
    result = _coordinator(boundary, source, cfg).run()
    assert result.outcome == "frontier_violation"
    assert result.counters.total == 0


def test_compacted_record_mid_session_keeps_continuity(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    sessions = _sessions_root(tmp_path)
    sessions.mkdir(parents=True)
    admitted = datetime(2026, 6, 1, tzinfo=timezone.utc)
    source = _admitted_rollout(sessions, admitted)
    cfg = _production_cfg(tmp_path, sessions, admitted)
    cfg_path = tmp_path / "config.toml"
    _write_user_config(cfg_path, cfg)
    monkeypatch.delenv("CONVMEM_INCREMENTAL_ROOT", raising=False)
    install_fakes(monkeypatch)
    boundary = ProductionBoundary(cfg, source, config_path=cfg_path)
    assert _coordinator(boundary, source, cfg).run().outcome == "committed"
    with source.open("ab") as handle:
        handle.write(json.dumps({"type": "compacted", "payload": {}}).encode("utf-8") + b"\n")
        handle.write(codex_rollout_record(20))
    second = _coordinator(boundary, source, cfg).run()
    assert second.outcome == "committed"
    assert second.counters.total > 0


def test_admitted_truncation_refuses(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    sessions = _sessions_root(tmp_path)
    sessions.mkdir(parents=True)
    admitted = datetime(2026, 6, 1, tzinfo=timezone.utc)
    source = _admitted_rollout(sessions, admitted)
    cfg = _production_cfg(tmp_path, sessions, admitted)
    cfg_path = tmp_path / "config.toml"
    _write_user_config(cfg_path, cfg)
    monkeypatch.delenv("CONVMEM_INCREMENTAL_ROOT", raising=False)
    install_fakes(monkeypatch)
    boundary = ProductionBoundary(cfg, source, config_path=cfg_path)
    _coordinator(boundary, source, cfg).run()
    raw = source.read_bytes()
    source.write_bytes(raw[: max(1, len(raw) // 2)])
    result = _coordinator(boundary, source, cfg).run()
    assert result.outcome.startswith("rebuild_required:")
    assert result.counters.total == 0


def test_admitted_interior_rewrite_refuses(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    sessions = _sessions_root(tmp_path)
    sessions.mkdir(parents=True)
    admitted = datetime(2026, 6, 1, tzinfo=timezone.utc)
    source = _admitted_rollout(sessions, admitted)
    cfg = _production_cfg(tmp_path, sessions, admitted)
    cfg_path = tmp_path / "config.toml"
    _write_user_config(cfg_path, cfg)
    monkeypatch.delenv("CONVMEM_INCREMENTAL_ROOT", raising=False)
    install_fakes(monkeypatch)
    boundary = ProductionBoundary(cfg, source, config_path=cfg_path)
    _coordinator(boundary, source, cfg).run()
    raw = source.read_bytes()
    first_nl = raw.find(b"\n")
    second_nl = raw.find(b"\n", first_nl + 1)
    source.write_bytes(raw[: second_nl + 1] + b'{"type":"response_item"}\n' + raw[second_nl + 1 :])
    result = _coordinator(boundary, source, cfg).run()
    assert result.outcome.startswith("rebuild_required:")
    assert result.counters.total == 0


def test_rollback_reenable_refuses_visible(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    sessions = _sessions_root(tmp_path)
    sessions.mkdir(parents=True)
    admitted = datetime(2026, 6, 1, tzinfo=timezone.utc)
    source = _admitted_rollout(sessions, admitted)
    cfg = _production_cfg(tmp_path, sessions, admitted)
    cfg_path = tmp_path / "config.toml"
    _write_user_config(cfg_path, cfg)
    monkeypatch.delenv("CONVMEM_INCREMENTAL_ROOT", raising=False)
    install_fakes(monkeypatch)
    boundary = ProductionBoundary(cfg, source, config_path=cfg_path)
    assert _coordinator(boundary, source, cfg).run().outcome == "committed"
    # D8 rollback: legacy re-index leaves a stale incremental checkpoint (table re-enabled).
    state_dir = Path(cfg["index"]["incremental_jsonl"]["state_dir"])
    checkpoint_path = next(state_dir.rglob("checkpoint.json"))
    checkpoint = json.loads(checkpoint_path.read_text(encoding="utf-8"))
    checkpoint["transform_fingerprint"] = "legacy-route-stale"
    checkpoint_path.write_text(json.dumps(checkpoint), encoding="utf-8")
    _write_user_config(cfg_path, cfg)
    result = _coordinator(boundary, source, cfg).run()
    assert result.outcome == "rebuild_required:transform_fingerprint_changed"
    assert result.counters.total == 0
    with pytest.raises(incremental_jsonl.IncrementalJsonlError, match="live_route_refused"):
        incremental_jsonl.maybe_route_incremental(
            cfg=cfg,
            idx=cfg["index"],
            path=str(source),
            path_key=str(source),
            file_hash="post-rollback-hash",
            processed={},
            models=cfg["models"],
            tool="codex",
            units_export=None,
            chunk_size=4,
            overlap=0,
            min_confidence=0.6,
            force_reindex=False,
            supersede_on_reindex=False,
            verbose=False,
            detected_format="jsonl_codex_rollout",
        )

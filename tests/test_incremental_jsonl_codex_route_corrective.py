"""Production-route corrective tests for Codex rollout admission."""

# pylint: disable=duplicate-code,protected-access

from __future__ import annotations

import copy
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

import pytest

import incremental_jsonl
import ingest
from adapters.detect import get_parser
from incremental_jsonl_production import ProductionBoundary
from tests.incremental_jsonl_helpers import codex_rollout_record, install_fakes
from tests.purge_test_util import patch_live_config
from tests.test_incremental_jsonl_codex_rollout_route import (
    _admitted_rollout,
    _production_cfg,
    _sessions_root,
    _write_user_config,
)


def _write_config_without_admission(path: Path, cfg: dict) -> None:
    index = cfg["index"]
    incremental = index["incremental_jsonl"]
    path.write_text(
        "\n".join(
            [
                "[index]",
                f'chroma_dir = "{index["chroma_dir"]}"',
                f'processed_log = "{index["processed_log"]}"',
                f'units_export = "{index["units_export"]}"',
                f"chunk_size = {index.get('chunk_size', 4)}",
                f"chunk_overlap = {index.get('chunk_overlap', 0)}",
                "",
                "[index.incremental_jsonl]",
                "enabled = true",
                f'state_dir = "{incremental["state_dir"]}"',
                f"embed_dimension = {incremental['embed_dimension']}",
                "live_sources = []",
                "",
            ]
        ),
        encoding="utf-8",
    )


def _legacy_reindex(
    cfg: dict,
    source: Path,
    *,
    force_reindex: bool = True,
) -> None:
    idx = cfg["index"]
    processed = ingest.load_processed(idx["processed_log"])
    real_write_session = ingest.production_chroma_write_session
    root = Path(idx["chroma_dir"]).parent

    def hermetic_write_session(*, entrypoint: str, **kwargs):
        return real_write_session(
            entrypoint=entrypoint,
            lock_path=root / "writer.lock",
            attest_dir=root / "attest",
            census_dir=root / "census",
            **kwargs,
        )

    with patch_live_config(cfg), mock.patch(
        "ingest.production_chroma_write_session",
        side_effect=hermetic_write_session,
    ), mock.patch(
        "inter_model_index.production_chroma_write_session",
        side_effect=hermetic_write_session,
    ):
        ingest._index_one_file(  # pylint: disable=protected-access
            cfg=cfg,
            idx=idx,
            path=str(source),
            parser=get_parser(str(source)),
            processed=processed,
            models=cfg["models"],
            units_export=Path(idx["units_export"]),
            chunk_size=idx.get("chunk_size", 4),
            overlap=idx.get("chunk_overlap", 0),
            min_confidence=0.6,
            force_file=str(source),
            force_reindex=force_reindex,
            supersede_on_reindex=False,
            verbose=False,
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
    assert not reads
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
    cfg_rollback = copy.deepcopy(cfg)
    del cfg_rollback["index"]["incremental_jsonl"]["codex_rollout_admission"]
    _write_config_without_admission(cfg_path, cfg_rollback)
    _legacy_reindex(cfg_rollback, source)
    with source.open("ab") as handle:
        handle.write(codex_rollout_record(9))
    _write_user_config(cfg_path, cfg)
    processed = ingest.load_processed(cfg["index"]["processed_log"])
    with pytest.raises(incremental_jsonl.IncrementalJsonlError, match="live_route_refused"):
        incremental_jsonl.maybe_route_incremental(
            cfg=cfg,
            idx=cfg["index"],
            path=str(source),
            path_key=str(source),
            file_hash="post-rollback-hash",
            processed=processed,
            models=cfg["models"],
            tool="codex",
            units_export=Path(cfg["index"]["units_export"]),
            chunk_size=4,
            overlap=0,
            min_confidence=0.6,
            force_reindex=False,
            supersede_on_reindex=False,
            verbose=False,
            detected_format="jsonl_codex_rollout",
        )
    result = _coordinator(
        ProductionBoundary(cfg, source, config_path=cfg_path),
        source,
        cfg,
        processed=processed,
    ).run()
    assert result.outcome == "rebuild_required:projection_checkpoint_mismatch"
    assert result.counters.total == 0

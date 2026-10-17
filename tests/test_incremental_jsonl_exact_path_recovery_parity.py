"""Hermetic tests for Kiro exact-path production recovery parity (R1–R3)."""

# pylint: disable=duplicate-code,protected-access

from __future__ import annotations

import copy
from pathlib import Path

import pytest
import tomllib

import incremental_jsonl
import ingest
from adapters.kiro_session_jsonl import parse_complete_prefix
from incremental_jsonl_isolation import IsolationBoundary
from incremental_jsonl_production import ProductionBoundary
from tests.incremental_jsonl_helpers import (
    apply_env,
    enable_incremental,
    install_fakes,
    isolated_env,
    kiro_record,
    write_source,
)
from tests.test_incremental_jsonl_codex_route_corrective import (
    _coordinator,
    _legacy_reindex,
)
from tests.test_incremental_jsonl_live_boundary import _bootstrap_binding


def _kiro_production_setup(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, *, records: int = 4
) -> tuple[Path, dict, Path, ProductionBoundary]:
    isolated, env = isolated_env(tmp_path)
    apply_env(monkeypatch, env)
    monkeypatch.delenv("CONVMEM_INCREMENTAL_ROOT", raising=False)
    install_fakes(monkeypatch)
    enable_incremental(isolated)
    source = write_source(isolated.root, records)
    cfg = tomllib.loads(isolated.layout["user_config"].read_text(encoding="utf-8"))
    cfg["index"]["incremental_jsonl"].update(
        live_sources=[str(source)], embed_dimension=8
    )
    cfg_path = isolated.layout["user_config"]
    boundary = ProductionBoundary(cfg, source, config_path=cfg_path)
    return source, cfg, cfg_path, boundary


def _projection_state(coord: incremental_jsonl.IncrementalJsonlCoordinator, cfg: dict):
    processed = Path(cfg["index"]["processed_log"])
    return (
        coord._projection_fingerprint(),
        processed.read_bytes() if processed.exists() else None,
    )


def _kiro_legacy_reindex(cfg: dict, source: Path) -> None:
    cfg_off_route = copy.deepcopy(cfg)
    cfg_off_route["index"]["incremental_jsonl"]["live_sources"] = []
    _legacy_reindex(cfg_off_route, source)


def _leave_preparing_kiro_transaction(
    boundary: ProductionBoundary,
    source: Path,
    cfg: dict,
    cfg_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> incremental_jsonl.IncrementalJsonlCoordinator:
    real_build = incremental_jsonl.IncrementalJsonlCoordinator._build_frontier

    def halt_build(self, *args, **kwargs):  # noqa: ANN001, ARG002
        raise RuntimeError("halt")

    monkeypatch.setattr(
        incremental_jsonl.IncrementalJsonlCoordinator,
        "_build_frontier",
        halt_build,
    )
    coord = _coordinator(
        ProductionBoundary(cfg, source, config_path=cfg_path),
        source,
        cfg,
        chunk_size=2,
        overlap=0,
    )
    with pytest.raises(RuntimeError, match="halt"):
        coord.run()
    assert incremental_jsonl._read_json(coord.paths["transaction"])["phase"] == "PREPARING"
    monkeypatch.setattr(
        incremental_jsonl.IncrementalJsonlCoordinator,
        "_build_frontier",
        real_build,
    )
    return coord


def _crash_first_kiro_run(
    boundary: ProductionBoundary,
    source: Path,
    cfg: dict,
    *,
    point: str,
    phase: str,
) -> incremental_jsonl.IncrementalJsonlCoordinator:
    def crash(current: str) -> None:
        if current == point:
            raise RuntimeError(f"crash at {point}")

    coord = _coordinator(boundary, source, cfg, fault=crash, chunk_size=2, overlap=0)
    with pytest.raises(RuntimeError, match="crash at"):
        coord.run()
    assert coord.checkpoint() is None
    pending = incremental_jsonl._read_json(coord.paths["transaction"])
    assert pending["phase"] == phase
    return coord


def test_kiro_fresh_run_after_legacy_reindex_refuses_projection_mismatch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source, cfg, cfg_path, boundary = _kiro_production_setup(tmp_path, monkeypatch)
    assert _coordinator(boundary, source, cfg, chunk_size=2, overlap=0).run().outcome == "committed"
    _kiro_legacy_reindex(cfg, source)
    with source.open("ab") as handle:
        handle.write(kiro_record(10))
    coord = _coordinator(ProductionBoundary(cfg, source, config_path=cfg_path), source, cfg)
    before = _projection_state(coord, cfg)
    result = coord.run()
    assert result.outcome == "rebuild_required:projection_checkpoint_mismatch"
    assert result.counters.total == 0
    assert _projection_state(coord, cfg) == before


def test_kiro_recovery_after_legacy_reindex_refuses_projection_mismatch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source, cfg, cfg_path, boundary = _kiro_production_setup(tmp_path, monkeypatch)
    assert _coordinator(boundary, source, cfg, chunk_size=2, overlap=0).run().outcome == "committed"
    with source.open("ab") as handle:
        handle.write(kiro_record(8))
    _leave_preparing_kiro_transaction(boundary, source, cfg, cfg_path, monkeypatch)
    _kiro_legacy_reindex(cfg, source)
    with source.open("ab") as handle:
        handle.write(kiro_record(9))
    coord = _coordinator(ProductionBoundary(cfg, source, config_path=cfg_path), source, cfg)
    before = _projection_state(coord, cfg)
    result = coord.run()
    assert result.outcome == "rebuild_required:projection_checkpoint_mismatch"
    assert result.counters.total == 0
    assert _projection_state(coord, cfg) == before


def test_kiro_checkpointless_recovery_after_legacy_refuses_bootstrap_required(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source, cfg, cfg_path, boundary = _kiro_production_setup(tmp_path, monkeypatch)
    _crash_first_kiro_run(
        boundary, source, cfg, point="before_rollback_prepare", phase="PREPARING"
    )
    _kiro_legacy_reindex(cfg, source)
    with source.open("ab") as handle:
        handle.write(kiro_record(4))
    coord = _coordinator(ProductionBoundary(cfg, source, config_path=cfg_path), source, cfg)
    before = _projection_state(coord, cfg)
    result = coord.run()
    assert result.outcome == "bootstrap_required"
    assert result.counters.total == 0
    assert _projection_state(coord, cfg) == before


def test_kiro_preparing_recovery_without_legacy_still_commits(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source, cfg, cfg_path, boundary = _kiro_production_setup(tmp_path, monkeypatch)
    _crash_first_kiro_run(
        boundary, source, cfg, point="before_rollback_prepare", phase="PREPARING"
    )
    result = _coordinator(
        ProductionBoundary(cfg, source, config_path=cfg_path), source, cfg, chunk_size=2, overlap=0
    ).run()
    assert result.outcome == "committed"
    assert result.mode == "preparing_recovery"


def test_kiro_append_after_commit_still_commits(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source, cfg, cfg_path, boundary = _kiro_production_setup(tmp_path, monkeypatch)
    first = _coordinator(boundary, source, cfg, chunk_size=2, overlap=0).run()
    assert first.outcome == "committed"
    checkpoint = incremental_jsonl.IncrementalJsonlCoordinator(
        boundary, source, cfg=cfg, chunk_size=2, overlap=0
    ).checkpoint()
    assert checkpoint is not None
    assert checkpoint.get("processed_lineage_digest")
    processed = ingest.load_processed(cfg["index"]["processed_log"])
    path_key = str(source.resolve())
    entry = next(row for row in processed.values() if row.get("path") == path_key)
    assert entry.get("incremental_jsonl_lineage") == checkpoint["processed_lineage_digest"]
    with source.open("ab") as handle:
        handle.write(kiro_record(6))
    second = _coordinator(
        ProductionBoundary(cfg, source, config_path=cfg_path), source, cfg, chunk_size=2, overlap=0
    ).run()
    assert second.outcome == "committed"
    assert second.mode == "incremental"


def test_isolation_boundary_skips_production_projection_guards(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    isolated, env = isolated_env(tmp_path)
    apply_env(monkeypatch, env)
    install_fakes(monkeypatch)
    source = write_source(isolated.root, 4)
    cfg = tomllib.loads(isolated.layout["user_config"].read_text(encoding="utf-8"))
    cfg["index"]["incremental_jsonl"].update(enabled=True, embed_dimension=8)
    boundary = IsolationBoundary.from_environment()
    coord = incremental_jsonl.IncrementalJsonlCoordinator(
        boundary, source, cfg=cfg, chunk_size=2, overlap=0
    )
    assert coord.production_boundary_live is False
    assert coord.run().outcome == "committed"
    cfg_off = copy.deepcopy(cfg)
    cfg_off["index"]["incremental_jsonl"]["live_sources"] = []
    _legacy_reindex(cfg_off, source)
    with source.open("ab") as handle:
        handle.write(kiro_record(8))
    result = incremental_jsonl.IncrementalJsonlCoordinator(
        boundary, source, cfg=cfg, chunk_size=2, overlap=0
    ).run()
    assert result.outcome != "rebuild_required:projection_checkpoint_mismatch"


def test_bootstrap_commit_records_production_lineage(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    isolated, env = isolated_env(tmp_path)
    apply_env(monkeypatch, env)
    monkeypatch.delenv("CONVMEM_INCREMENTAL_ROOT", raising=False)
    install_fakes(monkeypatch)
    enable_incremental(isolated)
    source = write_source(isolated.root, 4)
    cfg = tomllib.loads(isolated.layout["user_config"].read_text(encoding="utf-8"))
    cfg["index"]["incremental_jsonl"].update(
        live_sources=[str(source)], embed_dimension=8
    )
    boundary = ProductionBoundary(
        cfg, source, config_path=isolated.layout["user_config"]
    )
    view = parse_complete_prefix(str(source))
    coordinator = incremental_jsonl.IncrementalJsonlCoordinator(
        boundary,
        source,
        cfg=cfg,
        processed={"old-hash": {"path": str(source)}},
        bootstrap_existing=True,
        expected_prefix_sha256=view.prefix_sha256,
        max_bootstrap_chunks=4,
        **_bootstrap_binding(),
        chunk_size=2,
        overlap=0,
    )
    assert coordinator.run().outcome == "committed"
    checkpoint = coordinator.checkpoint()
    assert checkpoint is not None
    assert checkpoint.get("processed_lineage_digest")
    processed = ingest.load_processed(cfg["index"]["processed_log"])
    entry = next(row for row in processed.values() if row.get("path") == str(source))
    assert entry.get("incremental_jsonl_lineage") == checkpoint["processed_lineage_digest"]

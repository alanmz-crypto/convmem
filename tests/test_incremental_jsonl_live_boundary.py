"""Production route must distinguish legacy files from explicit live grants."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

import incremental_jsonl
from config import IncrementalJsonlConfigError, incremental_jsonl_settings
from incremental_jsonl_isolation import IsolationBoundary, IsolationViolation
from incremental_jsonl_production import ProductionBoundary
from tests.incremental_jsonl_helpers import write_source


def _fixture(tmp_path: Path) -> tuple[dict, Path]:
    source = tmp_path / "source" / "messages.jsonl"
    source.parent.mkdir()
    source.write_text('{"role":"user","message":"hello"}\n', encoding="utf-8")
    data = tmp_path / "data"
    cfg = {
        "index": {
            "chroma_dir": str(data / "chroma"),
            "processed_log": str(data / "processed.json"),
            "units_export": str(data / "knowledge_units.jsonl"),
            "incremental_jsonl": {
                "enabled": True,
                "state_dir": str(data / "incremental-jsonl"),
                "live_sources": [str(source)],
            },
        }
    }
    return cfg, source


def _route(cfg: dict, source: Path) -> tuple | None:
    return incremental_jsonl.maybe_route_incremental(
        cfg=cfg,
        idx=cfg["index"],
        path=str(source),
        path_key=str(source),
        file_hash="changed",
        processed={},
        models={},
        tool="kiro",
        units_export=None,
        chunk_size=4,
        overlap=0,
        min_confidence=0.6,
        force_reindex=False,
        supersede_on_reindex=False,
        verbose=False,
        detected_format="jsonl_kiro_session",
    )


def test_exact_grants_exclude_source_from_mutable_roles(tmp_path: Path) -> None:
    cfg, source = _fixture(tmp_path)
    boundary = ProductionBoundary(cfg, source, config_path=tmp_path / "config.toml")
    assert boundary.resolve_source(source, label="source") == source
    assert boundary.resolve_mutable(
        Path(cfg["index"]["incremental_jsonl"]["state_dir"]) / "cursor.json",
        label="cursor",
    ).name == "cursor.json"
    with pytest.raises(IsolationViolation):
        boundary.resolve_mutable(source, label="source write")
    with pytest.raises(IsolationViolation):
        boundary.resolve_mutable(tmp_path / "unrelated", label="unrelated")


def test_live_boundary_rejects_symlink_and_role_overlap(tmp_path: Path) -> None:
    cfg, source = _fixture(tmp_path)
    alias = tmp_path / "alias.jsonl"
    alias.symlink_to(source)
    cfg["index"]["incremental_jsonl"]["live_sources"] = [str(alias)]
    with pytest.raises(IsolationViolation, match="symlink"):
        ProductionBoundary(cfg, alias)
    cfg["index"]["incremental_jsonl"]["live_sources"] = [str(source)]
    cfg["index"]["incremental_jsonl"]["state_dir"] = cfg["index"]["chroma_dir"]
    with pytest.raises(IsolationViolation, match="overlaps Chroma"):
        ProductionBoundary(cfg, source)


@pytest.mark.parametrize("bad", ["/tmp/*", "relative.jsonl", 3, ""])
def test_live_source_configuration_requires_exact_paths(tmp_path: Path, bad) -> None:
    cfg, _source = _fixture(tmp_path)
    cfg["index"]["incremental_jsonl"]["live_sources"] = [bad]
    with pytest.raises(IncrementalJsonlConfigError):
        incremental_jsonl_settings(cfg)


def test_unselected_source_uses_legacy_without_constructing_state(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cfg, source = _fixture(tmp_path)
    cfg["index"]["incremental_jsonl"]["live_sources"] = []
    monkeypatch.delenv("CONVMEM_INCREMENTAL_ROOT", raising=False)
    assert _route(cfg, source) is None
    assert not (tmp_path / "data").exists()
    with pytest.raises(IsolationViolation):
        IsolationBoundary.from_environment()


def test_selected_refusal_is_visible_without_legacy_fallback(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cfg, source = _fixture(tmp_path)
    monkeypatch.delenv("CONVMEM_INCREMENTAL_ROOT", raising=False)

    class RefusingCoordinator:
        def __init__(self, *_args, **_kwargs):
            pass

        def run(self):
            return SimpleNamespace(outcome="bootstrap_required")

    monkeypatch.setattr(incremental_jsonl, "IncrementalJsonlCoordinator", RefusingCoordinator)
    with pytest.raises(incremental_jsonl.IncrementalJsonlError, match="bootstrap_required"):
        _route(cfg, source)
    assert not (tmp_path / "data").exists()


def test_isolation_env_does_not_create_a_production_grant(tmp_path: Path) -> None:
    cfg, source = _fixture(tmp_path)
    cfg["index"]["incremental_jsonl"]["live_sources"] = []
    with pytest.raises(IsolationViolation, match="exact live grant"):
        ProductionBoundary(cfg, source)


def test_existing_source_refuses_before_provider_or_checkpoint(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cfg, _source = _fixture(tmp_path)
    source = write_source(tmp_path, 3)
    cfg["index"]["incremental_jsonl"]["live_sources"] = [str(source)]
    monkeypatch.delenv("CONVMEM_INCREMENTAL_ROOT", raising=False)
    processed = {"old-hash": {"path": str(source)}}
    with pytest.raises(incremental_jsonl.IncrementalJsonlError, match="bootstrap_required"):
        incremental_jsonl.maybe_route_incremental(
            cfg=cfg,
            idx=cfg["index"],
            path=str(source),
            path_key=str(source),
            file_hash="new-hash",
            processed=processed,
            models={},
            tool="kiro",
            units_export=None,
            chunk_size=2,
            overlap=0,
            min_confidence=0.6,
            force_reindex=False,
            supersede_on_reindex=False,
            verbose=False,
            detected_format="jsonl_kiro_session",
        )
    assert processed == {"old-hash": {"path": str(source)}}
    state = Path(cfg["index"]["incremental_jsonl"]["state_dir"])
    assert not list(state.glob("*/checkpoint.json"))

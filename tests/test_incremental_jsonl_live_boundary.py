"""Production route must distinguish legacy files from explicit live grants."""

# Ruff targets the repo Python version where tomllib is third-party to this
# import sorter; Pylint uses the host stdlib classification.
# pylint: disable=wrong-import-order,protected-access

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest
import tomllib

import incremental_jsonl
from adapters.kiro_session_jsonl import parse_complete_prefix
from chroma_store import SUMMARIES, UNITS
from config import IncrementalJsonlConfigError, incremental_jsonl_settings
from incremental_jsonl_isolation import IsolationBoundary, IsolationViolation
from incremental_jsonl_production import ProductionBoundary
from tests.incremental_jsonl_helpers import (
    apply_env,
    enable_incremental,
    install_fakes,
    isolated_env,
    kiro_record,
    write_source,
)


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
                "embed_dimension": 8,
            },
        }
    }
    return cfg, source


def _route(cfg: dict, source: Path) -> tuple | None:
    return incremental_jsonl.maybe_route_incremental(
        cfg=cfg,
        idx=cfg["index"],
        path=str(source),
        path_key=str(source.expanduser().resolve()),
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
    with pytest.raises(IncrementalJsonlConfigError, match="canonical"):
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


def test_live_source_configuration_rejects_duplicate_grants(tmp_path: Path) -> None:
    cfg, source = _fixture(tmp_path)
    cfg["index"]["incremental_jsonl"]["live_sources"] = [str(source), str(source)]
    with pytest.raises(IncrementalJsonlConfigError, match="duplicate"):
        incremental_jsonl_settings(cfg)


def test_live_source_configuration_rejects_noncanonical_grants(tmp_path: Path) -> None:
    cfg, source = _fixture(tmp_path)
    alias = tmp_path / "alias.jsonl"
    alias.symlink_to(source)
    for invalid in (str(alias), str(source.parent / ".." / "source" / source.name)):
        cfg["index"]["incremental_jsonl"]["live_sources"] = [invalid]
        with pytest.raises(IncrementalJsonlConfigError, match="canonical"):
            _route(cfg, alias)


def test_symlinked_input_cannot_bypass_selected_live_boundary(tmp_path: Path) -> None:
    cfg, source = _fixture(tmp_path)
    alias = tmp_path / "alias.jsonl"
    alias.symlink_to(source)
    with pytest.raises(IsolationViolation, match="symlink"):
        _route(cfg, alias)


@pytest.mark.parametrize("bad", [0, -1, True, "768"])
def test_live_embedding_dimension_must_be_positive_integer(tmp_path: Path, bad) -> None:
    cfg, _source = _fixture(tmp_path)
    cfg["index"]["incremental_jsonl"]["embed_dimension"] = bad
    with pytest.raises(IncrementalJsonlConfigError, match="embed_dimension"):
        incremental_jsonl_settings(cfg)


def test_selected_source_needs_explicit_embedding_dimension(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cfg, source = _fixture(tmp_path)
    del cfg["index"]["incremental_jsonl"]["embed_dimension"]
    monkeypatch.delenv("CONVMEM_INCREMENTAL_ROOT", raising=False)
    with pytest.raises(IncrementalJsonlConfigError, match="embed_dimension"):
        _route(cfg, source)
    assert not (tmp_path / "data").exists()


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


def test_one_shot_bootstrap_then_append_reuses_historical_transforms(
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
    old = {"old-hash": {"path": str(source)}}
    coordinator = incremental_jsonl.IncrementalJsonlCoordinator(
        boundary,
        source,
        cfg=cfg,
        processed=old,
        bootstrap_existing=True,
        expected_prefix_sha256=view.prefix_sha256,
        max_bootstrap_chunks=4,
        chunk_size=2,
        overlap=0,
    )
    with coordinator._session() as session:
        session.store.add_summary(
            "legacy-summary", "old", [0.1] * 8, {"source_path": str(source)}
        )
        session.store.add_unit(
            "legacy-unit", "old", [0.1] * 8, {"source_path": str(source)}
        )
        session.store.add_summary(
            "other-summary", "other", [0.1] * 8, {"source_path": "/other"}
        )
    first = coordinator.run()
    assert first.outcome == "committed"
    assert first.mode == "bootstrap_existing"
    assert first.counters.summarize > 0
    with coordinator._session() as session:
        assert "legacy-summary" not in session.store.ids_for_source(SUMMARIES, str(source))
        assert "legacy-unit" not in session.store.ids_for_source(UNITS, str(source))
        assert "other-summary" in session.store.ids_for_source(SUMMARIES, "/other")
    with source.open("ab") as handle:
        handle.write(kiro_record(4))
    second = incremental_jsonl.IncrementalJsonlCoordinator(
        boundary, source, cfg=cfg, chunk_size=2, overlap=0
    ).run()
    assert second.outcome == "committed"
    assert second.mode == "incremental"
    assert second.counters.summarize < first.counters.summarize


def test_bootstrap_requires_exact_digest_and_chunk_limit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    isolated, env = isolated_env(tmp_path)
    apply_env(monkeypatch, env)
    monkeypatch.delenv("CONVMEM_INCREMENTAL_ROOT", raising=False)
    source = write_source(isolated.root, 4)
    cfg = tomllib.loads(isolated.layout["user_config"].read_text(encoding="utf-8"))
    cfg["index"]["incremental_jsonl"].update(
        enabled=True, live_sources=[str(source)], embed_dimension=8
    )
    boundary = ProductionBoundary(
        cfg, source, config_path=isolated.layout["user_config"]
    )
    old = {"old-hash": {"path": str(source)}}
    mismatch = incremental_jsonl.IncrementalJsonlCoordinator(
        boundary,
        source,
        cfg=cfg,
        processed=old,
        bootstrap_existing=True,
        expected_prefix_sha256="0" * 64,
        max_bootstrap_chunks=4,
        chunk_size=2,
    ).run()
    assert mismatch.outcome == "bootstrap_source_digest_mismatch"
    view = parse_complete_prefix(str(source))
    over_budget = incremental_jsonl.IncrementalJsonlCoordinator(
        boundary,
        source,
        cfg=cfg,
        processed=old,
        bootstrap_existing=True,
        expected_prefix_sha256=view.prefix_sha256,
        max_bootstrap_chunks=1,
        chunk_size=2,
    ).run()
    assert over_budget.outcome == "bootstrap_chunk_limit_exceeded"
    assert not list(Path(cfg["index"]["incremental_jsonl"]["state_dir"]).glob("*/checkpoint.json"))


def test_watcher_route_cannot_resume_one_shot_bootstrap(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    isolated, env = isolated_env(tmp_path)
    apply_env(monkeypatch, env)
    monkeypatch.delenv("CONVMEM_INCREMENTAL_ROOT", raising=False)
    source = write_source(isolated.root, 4)
    cfg = tomllib.loads(isolated.layout["user_config"].read_text(encoding="utf-8"))
    cfg["index"]["incremental_jsonl"].update(
        enabled=True, live_sources=[str(source)], embed_dimension=8
    )
    boundary = ProductionBoundary(
        cfg, source, config_path=isolated.layout["user_config"]
    )
    view = parse_complete_prefix(str(source))

    def interrupt(point: str) -> None:
        if point == "after_transaction_phase_publish":
            raise RuntimeError("simulated crash")

    with pytest.raises(RuntimeError, match="simulated crash"):
        incremental_jsonl.IncrementalJsonlCoordinator(
            boundary,
            source,
            cfg=cfg,
            processed={"old-hash": {"path": str(source)}},
            bootstrap_existing=True,
            expected_prefix_sha256=view.prefix_sha256,
            max_bootstrap_chunks=4,
            chunk_size=2,
            fault=interrupt,
        ).run()
    watcher = incremental_jsonl.IncrementalJsonlCoordinator(
        boundary, source, cfg=cfg, chunk_size=2
    ).run()
    assert watcher.outcome == "bootstrap_requires_one_shot"
    wrong_grant = incremental_jsonl.IncrementalJsonlCoordinator(
        boundary,
        source,
        cfg=cfg,
        bootstrap_existing=True,
        expected_prefix_sha256="0" * 64,
        max_bootstrap_chunks=4,
        chunk_size=2,
    ).run()
    assert wrong_grant.outcome == "bootstrap_replay_grant_mismatch"
    assert not list(Path(cfg["index"]["incremental_jsonl"]["state_dir"]).glob("*/checkpoint.json"))


@pytest.mark.parametrize("mutate_source", [False, True])
def test_bootstrap_crash_replays_or_restores_exact_before_images(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mutate_source: bool
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
    digest = parse_complete_prefix(str(source)).prefix_sha256
    old = {"old-hash": {"path": str(source)}}

    def interrupt(point: str) -> None:
        if point == "after_summary_upsert":
            raise RuntimeError("simulated crash after first Chroma write")

    first = incremental_jsonl.IncrementalJsonlCoordinator(
        boundary,
        source,
        cfg=cfg,
        processed=old,
        bootstrap_existing=True,
        expected_prefix_sha256=digest,
        max_bootstrap_chunks=4,
        chunk_size=2,
        fault=interrupt,
    )
    with first._session() as session:
        session.store.add_summary(
            "legacy-summary", "old", [0.1] * 8, {"source_path": str(source)}
        )
        session.store.add_summary(
            "other-summary", "other", [0.1] * 8, {"source_path": "/other"}
        )
    with pytest.raises(RuntimeError, match="simulated crash"):
        first.run()
    assert first.counters.summarize > 0
    watcher = incremental_jsonl.IncrementalJsonlCoordinator(
        boundary, source, cfg=cfg, chunk_size=2
    ).run()
    assert watcher.outcome == "bootstrap_requires_one_shot"
    if mutate_source:
        source.write_bytes(source.read_bytes().replace(b"message-00000", b"changed-00000"))
    replay = incremental_jsonl.IncrementalJsonlCoordinator(
        boundary,
        source,
        cfg=cfg,
        bootstrap_existing=True,
        expected_prefix_sha256=digest,
        max_bootstrap_chunks=4,
        chunk_size=2,
    )
    result = replay.run()
    assert result.outcome == ("rolled_back" if mutate_source else "committed")
    if not mutate_source:
        assert result.mode == "replay_forward"
    assert result.counters.total == 0
    with replay._session() as session:
        source_ids = session.store.ids_for_source(SUMMARIES, str(source))
        assert ("legacy-summary" in source_ids) is mutate_source
        assert "other-summary" in session.store.ids_for_source(SUMMARIES, "/other")

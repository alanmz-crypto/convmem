"""Hermetic tests for transform contract v2 (Arc Codex #286, design section 6)."""

# pylint: disable=protected-access

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

import incremental_jsonl
from incremental_jsonl import CHECKPOINT_VERSION, TRANSACTION_VERSION
from incremental_checkpoint_migration import (
    MIGRATION_PUBLISH_FAULT_POINTS,
    MigrationError,
    MigrationPlan,
    MigrationPublishContext,
    assert_quiescent_for_migration,
    dry_run_migration,
    publish_migration,
)
from incremental_jsonl_production import ProductionBoundary
from incremental_transform_contract import (
    CHECKPOINT_VERSION_V1,
    CHECKPOINT_VERSION_V2,
    RECOVERY_PROTOCOL_VERSION,
    TRANSACTION_VERSION_V2,
    build_transform_descriptor,
    compute_legacy_v1_transform_fingerprint,
    generation_id_v1,
    generation_id_v2,
)
from tests.incremental_jsonl_helpers import (
    codex_rollout_record,
    install_build_chunk_tracker,
    install_fakes,
    isolated_env,
    write_codex_rollout_source,
)
from tests.test_incremental_jsonl_codex_rollout_route import (
    _admitted_rollout,
    _production_cfg,
    _sessions_root,
    _write_user_config,
)


def _downgrade_checkpoint_to_legacy_v1(
    coord: incremental_jsonl.IncrementalJsonlCoordinator,
    *,
    legacy_producer_revision: str,
) -> None:
    ckpt_path = coord.paths["checkpoint"]
    payload = json.loads(ckpt_path.read_text(encoding="utf-8"))
    payload["version"] = CHECKPOINT_VERSION
    for field in (
        "transform_descriptor",
        "fingerprint_scheme",
        "transform_contract_version",
        "prepared_namespace",
        "migration_receipt_digest",
        "coordinator_implementation_revision",
        "generation_scheme",
    ):
        payload.pop(field, None)
    payload["transform_fingerprint"] = compute_legacy_v1_transform_fingerprint(
        chunk_size=coord.chunk_size,
        overlap=coord.overlap,
        min_confidence=coord.min_confidence,
        models=coord.models,
        embed_dimension=coord.embed_dimension,
        implementation_revision=legacy_producer_revision,
        adapter_format=coord.format_spec.format_id,
        adapter_contract_version=coord.format_spec.adapter_contract_version,
    )
    ckpt_path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")


def _migration_plan(
    coord: incremental_jsonl.IncrementalJsonlCoordinator,
    *,
    legacy_producer_revision: str,
) -> MigrationPlan:
    return MigrationPlan(
        state_dir=coord.state_dir,
        source_path=str(coord.source),
        source_identity=coord.source_id,
        chunk_size=coord.chunk_size,
        overlap=coord.overlap,
        min_confidence=coord.min_confidence,
        models=coord.models,
        embed_dimension=coord.embed_dimension,
        adapter_format=coord.format_spec.format_id,
        adapter_contract_version=coord.format_spec.adapter_contract_version,
        legacy_producer_implementation_revision=legacy_producer_revision,
    )


def _publish_context(
    coord: incremental_jsonl.IncrementalJsonlCoordinator,
    *,
    legacy_producer_revision: str,
    coordinator_revision: str = "converter-runtime",
    dry_run_report: dict | None = None,
) -> MigrationPublishContext:
    return MigrationPublishContext(
        plan=_migration_plan(coord, legacy_producer_revision=legacy_producer_revision),
        cfg=coord.cfg,
        path_key=coord.path_key,
        coordinator_implementation_revision=coordinator_revision,
        dry_run_report=dry_run_report,
    )


def _checkpoint_version(state_dir: Path) -> int:
    payload = json.loads((state_dir / "checkpoint.json").read_text(encoding="utf-8"))
    return int(payload.get("version") or 0)


def test_version_constants_are_distinct_c8() -> None:
    from incremental_transform_contract import FINGERPRINT_SCHEME

    assert CHECKPOINT_VERSION != CHECKPOINT_VERSION_V2
    assert TRANSACTION_VERSION != TRANSACTION_VERSION_V2
    assert RECOVERY_PROTOCOL_VERSION == 1
    assert FINGERPRINT_SCHEME != str(CHECKPOINT_VERSION_V2)
    assert FINGERPRINT_SCHEME != str(TRANSACTION_VERSION_V2)


def test_v2_descriptor_ignores_implementation_revision() -> None:
    models = {"summarize_model": "s", "distill_model": "d", "embed_model": "e"}
    a = build_transform_descriptor(
        chunk_size=4,
        overlap=0,
        min_confidence=0.6,
        models=models,
        embed_dimension=8,
        adapter_format="jsonl_codex_rollout",
        adapter_contract_version="codex-rollout-complete-prefix-v1",
    )
    b = build_transform_descriptor(
        chunk_size=4,
        overlap=0,
        min_confidence=0.6,
        models=models,
        embed_dimension=8,
        adapter_format="jsonl_codex_rollout",
        adapter_contract_version="codex-rollout-complete-prefix-v1",
    )
    assert a.digest == b.digest
    legacy_a = compute_legacy_v1_transform_fingerprint(
        chunk_size=4,
        overlap=0,
        min_confidence=0.6,
        models=models,
        embed_dimension=8,
        implementation_revision="aaa",
        adapter_format="jsonl_codex_rollout",
        adapter_contract_version="codex-rollout-complete-prefix-v1",
    )
    legacy_b = compute_legacy_v1_transform_fingerprint(
        chunk_size=4,
        overlap=0,
        min_confidence=0.6,
        models=models,
        embed_dimension=8,
        implementation_revision="bbb",
        adapter_format="jsonl_codex_rollout",
        adapter_contract_version="codex-rollout-complete-prefix-v1",
    )
    assert legacy_a != legacy_b


def test_generation_ids_differ_by_scheme() -> None:
    args = {
        "source_id": "sid",
        "prefix_sha256": "a" * 64,
        "complete_boundary": 100,
        "transform_fingerprint": "f" * 64,
    }
    assert generation_id_v1(**args) != generation_id_v2(**args)


def test_deploy_identity_ab_unchanged_without_provider_calls(
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
    rev_a = "a" * 64
    rev_b = "b" * 64
    import chroma_write_store

    monkeypatch.setattr(
        chroma_write_store,
        "current_implementation_revision",
        lambda: rev_a,
        raising=False,
    )
    first = incremental_jsonl.IncrementalJsonlCoordinator(
        boundary,
        source,
        cfg=cfg,
        enabled=True,
        chunk_size=4,
        overlap=0,
        min_confidence=0.6,
        embed_dimension=8,
        processed={},
    )
    fp = first.transform_fingerprint
    assert first.run().outcome == "committed"
    monkeypatch.setattr(
        chroma_write_store,
        "current_implementation_revision",
        lambda: rev_b,
        raising=False,
    )
    second = incremental_jsonl.IncrementalJsonlCoordinator(
        boundary,
        source,
        cfg=cfg,
        enabled=True,
        chunk_size=4,
        overlap=0,
        min_confidence=0.6,
        embed_dimension=8,
        processed={},
    )
    assert second.transform_fingerprint == fp
    result = second.run()
    assert result.outcome == "unchanged"
    assert result.counters.total == 0


def test_legacy_v1_checkpoint_refuses_migration_required(
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
    coord = incremental_jsonl.IncrementalJsonlCoordinator(
        boundary,
        source,
        cfg=cfg,
        enabled=True,
        chunk_size=4,
        overlap=0,
        min_confidence=0.6,
        embed_dimension=8,
        processed={},
    )
    coord.run()
    _downgrade_checkpoint_to_legacy_v1(coord, legacy_producer_revision="a" * 64)
    result = incremental_jsonl.IncrementalJsonlCoordinator(
        boundary,
        source,
        cfg=cfg,
        enabled=True,
        chunk_size=4,
        overlap=0,
        min_confidence=0.6,
        embed_dimension=8,
        processed={},
    ).run()
    assert result.outcome == "migration_required"


def test_production_codex_v1_migrates_then_continues_without_rebuild(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("CONVMEM_INCREMENTAL_ROOT", str(tmp_path))
    sessions = _sessions_root(tmp_path)
    sessions.mkdir(parents=True)
    admitted = datetime(2026, 6, 1, tzinfo=timezone.utc)
    source = _admitted_rollout(sessions, admitted)
    cfg = _production_cfg(tmp_path, sessions, admitted)
    cfg_path = tmp_path / "config.toml"
    _write_user_config(cfg_path, cfg)
    install_fakes(monkeypatch)
    build_calls = install_build_chunk_tracker(monkeypatch)
    boundary = ProductionBoundary(cfg, source, config_path=cfg_path)
    legacy_rev = "a" * 64
    import chroma_write_store

    monkeypatch.setattr(
        chroma_write_store,
        "current_implementation_revision",
        lambda: legacy_rev,
        raising=False,
    )
    coord = incremental_jsonl.IncrementalJsonlCoordinator(
        boundary,
        source,
        cfg=cfg,
        enabled=True,
        chunk_size=4,
        overlap=0,
        min_confidence=0.6,
        embed_dimension=8,
        processed={},
    )
    assert coord.run().outcome == "committed"
    _downgrade_checkpoint_to_legacy_v1(coord, legacy_producer_revision=legacy_rev)
    refused = incremental_jsonl.IncrementalJsonlCoordinator(
        boundary,
        source,
        cfg=cfg,
        enabled=True,
        chunk_size=4,
        overlap=0,
        min_confidence=0.6,
        embed_dimension=8,
        processed={},
    ).run()
    assert refused.outcome == "migration_required"
    report = dry_run_migration(_migration_plan(coord, legacy_producer_revision=legacy_rev))
    publish_migration(
        _publish_context(coord, legacy_producer_revision=legacy_rev, dry_run_report=report)
    )
    unchanged = incremental_jsonl.IncrementalJsonlCoordinator(
        boundary,
        source,
        cfg=cfg,
        enabled=True,
        chunk_size=4,
        overlap=0,
        min_confidence=0.6,
        embed_dimension=8,
        processed={},
    ).run()
    assert unchanged.outcome == "unchanged"
    assert unchanged.counters.total == 0
    prior_count = int(
        json.loads((coord.state_dir / "checkpoint.json").read_text(encoding="utf-8"))["record_count"]
    )
    with source.open("ab") as handle:
        for index in range(prior_count, prior_count + 4):
            handle.write(codex_rollout_record(index))
    build_calls.clear()
    appended = incremental_jsonl.IncrementalJsonlCoordinator(
        boundary,
        source,
        cfg=cfg,
        enabled=True,
        chunk_size=4,
        overlap=0,
        min_confidence=0.6,
        embed_dimension=8,
        processed={},
    ).run()
    assert appended.outcome == "committed"
    assert appended.counters.total > 0
    assert build_calls


def test_recovery_protocol_refused_c6(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    boundary, _env = isolated_env(tmp_path)
    monkeypatch.setenv("CONVMEM_INCREMENTAL_ROOT", str(boundary.root))
    source = write_codex_rollout_source(boundary.root, 6)
    install_fakes(monkeypatch)
    coord = incremental_jsonl.IncrementalJsonlCoordinator.from_isolated_boundary(
        boundary, source, enabled=True, embed_dimension=8
    )
    state = coord.state_dir
    (state / "transaction.json").write_text(
        json.dumps(
            {
                "version": TRANSACTION_VERSION_V2,
                "transaction_id": "0" * 32,
                "phase": "PREPARING",
                "recovery_protocol_version": 999,
                "source_path": str(source),
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(incremental_jsonl.IncrementalJsonlError, match="unsupported recovery protocol"):
        coord._roll_forward(json.loads((state / "transaction.json").read_text(encoding="utf-8")))


def test_quiescence_blocks_migration_c4(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    boundary, _env = isolated_env(tmp_path)
    monkeypatch.setenv("CONVMEM_INCREMENTAL_ROOT", str(boundary.root))
    source = write_codex_rollout_source(boundary.root, 4)
    state = boundary.layout["state"] / incremental_jsonl.source_state_id(
        str(source), format_id="jsonl_codex_rollout"
    )
    state.mkdir(parents=True)
    (state / "checkpoint.json").write_text('{"version":1}', encoding="utf-8")
    (state / "transaction.json").write_text('{"phase":"PREPARING"}', encoding="utf-8")
    with pytest.raises(MigrationError, match="pending_transaction"):
        assert_quiescent_for_migration(
            checkpoint_path=state / "checkpoint.json",
            transaction_path=state / "transaction.json",
            rollback_path=state / "rollback.json",
        )


def test_publish_refuses_when_transaction_appears_after_dry_run_c4(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    boundary, env = isolated_env(tmp_path)
    from tests.incremental_jsonl_helpers import apply_env

    apply_env(monkeypatch, env)
    source = write_codex_rollout_source(boundary.root, 8)
    install_fakes(monkeypatch)
    coord = incremental_jsonl.IncrementalJsonlCoordinator.from_isolated_boundary(
        boundary, source, enabled=True, embed_dimension=8, chunk_size=4, overlap=0
    )
    coord.run()
    _downgrade_checkpoint_to_legacy_v1(coord, legacy_producer_revision="legacy-producer")
    report = dry_run_migration(_migration_plan(coord, legacy_producer_revision="legacy-producer"))
    (coord.state_dir / "transaction.json").write_text('{"phase":"PREPARING"}', encoding="utf-8")
    with pytest.raises(MigrationError, match="pending_transaction"):
        publish_migration(
            _publish_context(
                coord,
                legacy_producer_revision="legacy-producer",
                dry_run_report=report,
            )
        )
    assert _checkpoint_version(coord.state_dir) == CHECKPOINT_VERSION_V1


@pytest.mark.parametrize("point", MIGRATION_PUBLISH_FAULT_POINTS)
def test_migration_publish_crash_fault_matrix_is_safe_and_idempotent(
    tmp_path: Path, point: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    boundary, env = isolated_env(tmp_path)
    from tests.incremental_jsonl_helpers import apply_env

    apply_env(monkeypatch, env)
    source = write_codex_rollout_source(boundary.root, 8)
    install_fakes(monkeypatch)
    coord = incremental_jsonl.IncrementalJsonlCoordinator.from_isolated_boundary(
        boundary, source, enabled=True, embed_dimension=8, chunk_size=4, overlap=0
    )
    coord.run()
    _downgrade_checkpoint_to_legacy_v1(coord, legacy_producer_revision="legacy-producer")
    report = dry_run_migration(_migration_plan(coord, legacy_producer_revision="legacy-producer"))

    def fault(name: str) -> None:
        if name == point:
            raise RuntimeError(f"injected fault at {name}")

    with pytest.raises(RuntimeError, match="injected fault"):
        publish_migration(
            _publish_context(
                coord,
                legacy_producer_revision="legacy-producer",
                dry_run_report=report,
            ),
            fault=fault,
        )
    version = _checkpoint_version(coord.state_dir)
    assert version in {CHECKPOINT_VERSION_V1, CHECKPOINT_VERSION_V2}
    if version == CHECKPOINT_VERSION_V2:
        payload = json.loads((coord.state_dir / "checkpoint.json").read_text(encoding="utf-8"))
        receipt_digest = str(payload.get("migration_receipt_digest") or "")
        assert (coord.state_dir / f"migration_receipt_{receipt_digest}.json").is_file()

    publish_migration(
        _publish_context(
            coord,
            legacy_producer_revision="legacy-producer",
            dry_run_report=report,
        )
    )
    assert _checkpoint_version(coord.state_dir) == CHECKPOINT_VERSION_V2

"""Hermetic tests for transform contract v2 (Arc Codex #286, design section 6)."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

import pytest

import incremental_jsonl
from incremental_jsonl import CHECKPOINT_VERSION, TRANSACTION_VERSION
from incremental_checkpoint_migration import (
    MigrationError,
    assert_quiescent_for_migration,
    dry_run_migration,
    publish_migration,
)
from incremental_jsonl_production import ProductionBoundary
from incremental_transform_contract import (
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
    enable_incremental,
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
    import chroma_write_store

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
    ckpt_path = coord.paths["checkpoint"]
    payload = json.loads(ckpt_path.read_text(encoding="utf-8"))
    payload["version"] = CHECKPOINT_VERSION
    payload.pop("transform_descriptor", None)
    payload.pop("fingerprint_scheme", None)
    payload.pop("transform_contract_version", None)
    payload["transform_fingerprint"] = compute_legacy_v1_transform_fingerprint(
        chunk_size=4,
        overlap=0,
        min_confidence=0.6,
        models=cfg["models"],
        embed_dimension=8,
        implementation_revision=coord.coordinator_implementation_revision,
        adapter_format="jsonl_codex_rollout",
        adapter_contract_version="codex-rollout-complete-prefix-v1",
    )
    ckpt_path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
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


def test_migration_converter_dry_run_and_publish(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    boundary, env = isolated_env(tmp_path)
    from tests.incremental_jsonl_helpers import apply_env
    apply_env(monkeypatch, env)
    source = write_codex_rollout_source(boundary.root, 8)
    install_fakes(monkeypatch)
    enable_incremental(boundary)
    coord = incremental_jsonl.IncrementalJsonlCoordinator.from_isolated_boundary(
        boundary, source, enabled=True, embed_dimension=8, chunk_size=4, overlap=0
    )
    outcome = coord.run()
    assert outcome.outcome == "committed"
    state = coord.state_dir
    ckpt = json.loads((state / "checkpoint.json").read_text(encoding="utf-8"))
    ckpt["version"] = CHECKPOINT_VERSION
    legacy_fp = compute_legacy_v1_transform_fingerprint(
        chunk_size=4,
        overlap=0,
        min_confidence=0.6,
        models=coord.models,
        embed_dimension=8,
        implementation_revision="legacy-producer",
        adapter_format=coord.format_spec.format_id,
        adapter_contract_version=coord.format_spec.adapter_contract_version,
    )
    ckpt["transform_fingerprint"] = legacy_fp
    (state / "checkpoint.json").write_text(json.dumps(ckpt, sort_keys=True), encoding="utf-8")
    report = dry_run_migration(
        state_dir=state,
        source_path=str(source),
        source_identity=coord.source_id,
        chunk_size=4,
        overlap=0,
        min_confidence=0.6,
        models=coord.models,
        embed_dimension=8,
        adapter_format=coord.format_spec.format_id,
        adapter_contract_version=coord.format_spec.adapter_contract_version,
        legacy_producer_implementation_revision="legacy-producer",
    )
    assert report["dry_run"] is True
    published = publish_migration(
        state_dir=state,
        source_path=str(source),
        source_identity=coord.source_id,
        chunk_size=4,
        overlap=0,
        min_confidence=0.6,
        models=coord.models,
        embed_dimension=8,
        adapter_format=coord.format_spec.format_id,
        adapter_contract_version=coord.format_spec.adapter_contract_version,
        legacy_producer_implementation_revision="legacy-producer",
        coordinator_implementation_revision="converter-runtime",
    )
    assert published["checkpoint_version"] == CHECKPOINT_VERSION_V2
    new_ckpt = json.loads((state / "checkpoint.json").read_text(encoding="utf-8"))
    assert new_ckpt["version"] == CHECKPOINT_VERSION_V2


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
            state,
            checkpoint_path=state / "checkpoint.json",
            transaction_path=state / "transaction.json",
            rollback_path=state / "rollback.json",
        )

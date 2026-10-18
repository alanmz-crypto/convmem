"""T3 Chroma/processed/export oracles with parent observation (Arc #286)."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from bootstrap_codex_v2_owner import OwnerLockRequired
from bootstrap_codex_v3_writer_coordination import BootstrapWriterCoordinationError
from chroma_write_store import production_chroma_write_session
from ingest import _commit_chunk_to_stores, commit_processed_index_entry, load_processed
from tests.fixtures.issue_286_t3_fixture import claim_active_reservation, idx_dict, t3_bundle
from tests.incremental_jsonl_helpers import install_fakes


def _minimal_commit_kwargs(cfg, idx, source, file_hash: str):
    path_key = str(source.resolve())
    dim = int(cfg.get("models", {}).get("embed_dimension") or 8)
    emb = [0.01] * dim
    doc_id = hashlib.sha256(file_hash.encode()).hexdigest()[:32]
    return {
        "cfg": cfg,
        "idx": idx,
        "path_key": path_key,
        "path": str(source),
        "file_hash": file_hash,
        "chroma_dir": idx["chroma_dir"],
        "units_export": Path(idx.get("units_export") or idx["chroma_dir"]).parent / "units.jsonl",
        "doc_id": doc_id,
        "summary": "s",
        "summary_embedding": emb,
        "metadata": {"source_path": path_key, "tool": "codex"},
        "units_to_add": [],
        "verbose": False,
    }


def test_stale_legacy_commit_chunk_to_stores_refused(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    install_fakes(monkeypatch)
    source, cfg, grant, state_dir = t3_bundle(tmp_path, monkeypatch)
    claim_active_reservation(state_dir, grant)
    idx = idx_dict(cfg)
    kwargs = _minimal_commit_kwargs(cfg, idx, source, "c" * 64)
    with pytest.raises(BootstrapWriterCoordinationError):
        _commit_chunk_to_stores(**kwargs)


def test_broken_recheck_control_allows_stale_chroma_write(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    install_fakes(monkeypatch)
    source, cfg, grant, state_dir = t3_bundle(tmp_path, monkeypatch)
    claim_active_reservation(state_dir, grant)
    idx = idx_dict(cfg)
    monkeypatch.setattr(
        "bootstrap_codex_v3_writer_coordination.recheck_reservation_before_commit",
        lambda *a, **k: None,
    )
    monkeypatch.setattr(
        "bootstrap_codex_v3_writer_coordination.enforce_writer_scope",
        lambda *a, **k: None,
    )
    kwargs = _minimal_commit_kwargs(cfg, idx, source, "d" * 64)
    ok, *_rest = _commit_chunk_to_stores(**kwargs)
    assert ok is True
    with production_chroma_write_session(
        entrypoint="oracle.count", affected_sources=(kwargs["path_key"],)
    ) as session:
        assert session.store.count_summaries() >= 1 is not None


def test_disjoint_source_chroma_and_processed_while_reservation_active(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    install_fakes(monkeypatch)
    source_a, cfg, grant, state_dir = t3_bundle(tmp_path, monkeypatch)
    claim_active_reservation(state_dir, grant)
    source_b = tmp_path / "sessions" / "other.jsonl"
    source_b.parent.mkdir(parents=True, exist_ok=True)
    source_b.write_text("{}\n", encoding="utf-8")
    idx = idx_dict(cfg)
    kwargs = _minimal_commit_kwargs(cfg, idx, source_b, "e" * 64)
    ok, *_ = _commit_chunk_to_stores(**kwargs)
    assert ok is True
    with production_chroma_write_session(
        entrypoint="oracle.disjoint", affected_sources=(str(source_b.resolve()),)
    ) as session:
        assert session.store.count_summaries() >= 1


def test_chroma_no_source_mutation_defers_under_reservation(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    source, cfg, grant, state_dir = t3_bundle(tmp_path, monkeypatch)
    claim_active_reservation(state_dir, grant)
    with pytest.raises(BootstrapWriterCoordinationError, match="maintenance_deferred"):
        with production_chroma_write_session(
            entrypoint="oracle.unscoped", maintenance_unscoped=True
        ) as session:
            session.store.add_summary(
                "x", "y", [0.0] * 8, {"source_path": str(source.resolve())}
            )


def test_install_owner_without_lock_refused(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from bootstrap_codex_v2_authority import load_authority
    from bootstrap_codex_v3_writer_coordination import install_owner_operation_identity

    _source, _cfg, grant, state_dir = t3_bundle(tmp_path, monkeypatch)
    claim_active_reservation(state_dir, grant)
    authority = load_authority(state_dir)
    assert authority is not None
    with pytest.raises(OwnerLockRequired):
        install_owner_operation_identity(authority)


def test_owner_bound_identity_allows_same_source_processed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from bootstrap_codex_v2_authority import load_authority
    from bootstrap_codex_v3_writer_coordination import (
        clear_owner_operation_identity,
        install_owner_operation_identity,
        recheck_reservation_before_commit,
    )
    from tests.fixtures.issue_286_t2_owner_context import t2_owner_context

    source, cfg, grant, state_dir = t3_bundle(tmp_path, monkeypatch)
    claim_active_reservation(state_dir, grant)
    authority = load_authority(state_dir)
    with t2_owner_context(state_dir):
        token = install_owner_operation_identity(authority)
        try:
            recheck_reservation_before_commit(cfg, str(source))
            ok = commit_processed_index_entry(
                cfg["index"]["processed_log"],
                file_hash="f" * 64,
                path_key=str(source.resolve()),
                chunks=1,
                units=1,
            )
            assert ok is True
        finally:
            clear_owner_operation_identity(token)


def test_raw_save_processed_refused_outside_mutate(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from ingest import save_processed

    _source, cfg, _grant, _state_dir = t3_bundle(tmp_path, monkeypatch)
    path = cfg["index"]["processed_log"]
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with pytest.raises(RuntimeError, match="mutate_processed"):
        save_processed(path, {})

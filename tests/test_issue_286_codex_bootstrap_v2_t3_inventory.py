"""T3 §5 inventory: shared-guard equivalence classes (Arc #286)."""

from __future__ import annotations

from tests.fixtures.issue_286_host_isolation import enforce_issue_286_import_guard

enforce_issue_286_import_guard()

import json
from pathlib import Path

import pytest

from bootstrap_codex_v3_writer_coordination import BootstrapWriterCoordinationError
from chroma_write_store import production_chroma_write_session
from ingest import (
    _compact_units_export_after_index,
    _deduplicate_units_export,
    commit_processed_index_entry,
    exclude_processed_path,
    load_processed,
    mutate_processed,
    undo_exclude_processed_path,
)
from ingest_dedupe import IngestDedupeResult, persist_ingest_dedupe
from incremental_retry_state import (
    clear_all_incremental_retry_states,
    clear_incremental_retry_states_for_source,
)
from tests.fixtures.issue_286_t3_fixture import claim_active_reservation, idx_dict, t3_bundle
from tests.incremental_jsonl_helpers import install_fakes
from incremental_jsonl import IncrementalJsonlError
from purge_locks import index_write_flock


def _chroma_under_lock(cfg, fn):
    with index_write_flock(cfg):
        fn()


def test_export_compaction_defers_under_active_reservation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source, cfg, grant, state_dir = t3_bundle(tmp_path, monkeypatch)
    claim_active_reservation(state_dir, grant)
    export = Path(cfg["index"]["units_export"])
    export.parent.mkdir(parents=True, exist_ok=True)
    foreign = json.dumps({"id": "foreign-unit", "title": "keep"}) + "\n"
    export.write_text(foreign, encoding="utf-8")
    before = export.read_bytes()
    with pytest.raises(BootstrapWriterCoordinationError, match="maintenance_deferred"):
        _deduplicate_units_export(export)
    assert export.read_bytes() == before


def test_disjoint_export_append_and_compaction_after_owner_commit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    install_fakes(monkeypatch)
    source_a, cfg, grant, state_dir = t3_bundle(tmp_path, monkeypatch)
    claim_active_reservation(state_dir, grant)
    source_b = tmp_path / "other.jsonl"
    source_b.write_text("{}\n", encoding="utf-8")
    export = Path(cfg["index"]["units_export"])
    export.parent.mkdir(parents=True, exist_ok=True)
    foreign = json.dumps({"id": "foreign-unit", "title": "keep"}) + "\n"
    export.write_text(foreign, encoding="utf-8")
    from ingest import _commit_chunk_to_stores
    import hashlib

    idx = idx_dict(cfg)
    path_key = str(source_b.resolve())
    fh = "a" * 64
    dim = 8
    ok, *_ = _commit_chunk_to_stores(
        cfg=cfg,
        idx=idx,
        path_key=path_key,
        path=str(source_b),
        file_hash=fh,
        chroma_dir=idx["chroma_dir"],
        units_export=export,
        doc_id=hashlib.sha256(fh.encode()).hexdigest()[:32],
        summary="s",
        summary_embedding=[0.01] * dim,
        metadata={"source_path": path_key, "tool": "codex"},
        units_to_add=[],
        verbose=False,
    )
    assert ok is True
    stats = {"files_processed": 1, "chunks_indexed": 1}
    _compact_units_export_after_index(export, stats)
    assert stats.get("export_compaction_deferred") is True
    assert foreign.strip() in export.read_text(encoding="utf-8")
    assert stats.get("export_duplicates_removed", 0) >= 0


def test_persist_ingest_dedupe_defers_under_reservation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source, cfg, grant, state_dir = t3_bundle(tmp_path, monkeypatch)
    claim_active_reservation(state_dir, grant)
    result = IngestDedupeResult(
        exact_suppressions=[{"event_id": "e1", "unit_id": "u1"}],
    )
    with pytest.raises(BootstrapWriterCoordinationError, match="maintenance_deferred"):
        persist_ingest_dedupe(cfg, result)


def test_persist_ingest_dedupe_disjoint_append_without_reservation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _source, cfg, _grant, _state_dir = t3_bundle(tmp_path, monkeypatch)
    data_dir = Path(cfg["index"]["chroma_dir"]).parent
    data_dir.mkdir(parents=True, exist_ok=True)
    result = IngestDedupeResult(
        exact_suppressions=[{"event_id": "e2", "unit_id": "u2", "reason": "exact"}],
    )
    stats = persist_ingest_dedupe(cfg, result)
    assert stats["exact_suppressed"] == 1
    sink = data_dir / "ingest_duplicate_suppressions.jsonl"
    assert sink.is_file()
    assert "e2" in sink.read_text(encoding="utf-8")


def test_clear_retry_state_for_source_defers_under_reservation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source, cfg, grant, state_dir = t3_bundle(tmp_path, monkeypatch)
    claim_active_reservation(state_dir, grant)
    path_key = str(source.resolve())
    state_root = Path(cfg["index"]["incremental_jsonl"]["state_dir"])
    retry = state_root / "retry_state.json"
    retry.parent.mkdir(parents=True, exist_ok=True)
    retry.write_text(json.dumps({"source_path": path_key}) + "\n", encoding="utf-8")
    with pytest.raises(BootstrapWriterCoordinationError, match="coordination_deferral"):
        clear_incremental_retry_states_for_source(cfg, path_key)


def test_clear_all_retry_states_defers_when_reservation_active(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source, cfg, grant, state_dir = t3_bundle(tmp_path, monkeypatch)
    claim_active_reservation(state_dir, grant)
    with pytest.raises(BootstrapWriterCoordinationError, match="maintenance_deferred"):
        clear_all_incremental_retry_states(cfg)


def test_exclude_processed_on_reserved_source_defers(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source, cfg, grant, state_dir = t3_bundle(tmp_path, monkeypatch)
    claim_active_reservation(state_dir, grant)
    path_key = str(source.resolve())
    processed = cfg["index"]["processed_log"]
    Path(processed).parent.mkdir(parents=True, exist_ok=True)
    with pytest.raises((BootstrapWriterCoordinationError, IncrementalJsonlError), match="coordination_deferral"):
        exclude_processed_path(processed, path_key, "b" * 64, reason="purge")


def test_undo_exclude_on_reserved_source_defers(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source, cfg, grant, state_dir = t3_bundle(tmp_path, monkeypatch)
    claim_active_reservation(state_dir, grant)
    path_key = str(source.resolve())
    processed = cfg["index"]["processed_log"]
    Path(processed).parent.mkdir(parents=True, exist_ok=True)
    Path(processed).write_text(
        json.dumps({("c" * 64): {"path": path_key, "excluded": True}}),
        encoding="utf-8",
    )
    with pytest.raises((BootstrapWriterCoordinationError, IncrementalJsonlError), match="coordination_deferral"):
        undo_exclude_processed_path(processed, path_key)


def test_processed_preimage_restore_on_reserved_source_defers(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from ingest import mutate_processed

    source, cfg, grant, state_dir = t3_bundle(tmp_path, monkeypatch)
    claim_active_reservation(state_dir, grant)
    path_key = str(source.resolve())
    processed = cfg["index"]["processed_log"]
    Path(processed).parent.mkdir(parents=True, exist_ok=True)

    def mutator(data: dict) -> None:
        for key, value in list(data.items()):
            if isinstance(value, dict) and value.get("path") == path_key:
                del data[key]
        data.update({"stale": {"path": path_key, "chunks": 9}})

    with pytest.raises((BootstrapWriterCoordinationError, IncrementalJsonlError), match="coordination_deferral"):
        mutate_processed(processed, mutator, affected_sources=(path_key,))


def test_chroma_mutation_without_source_defers_under_reservation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source, cfg, grant, state_dir = t3_bundle(tmp_path, monkeypatch)
    claim_active_reservation(state_dir, grant)
    with pytest.raises(BootstrapWriterCoordinationError, match="maintenance_deferred"):
        with index_write_flock(cfg):
            with production_chroma_write_session(entrypoint="convmem.add") as session:
                session.store.add_summary("doc", "text", [0.0] * 8, {})


def test_chroma_scoped_disjoint_mutation_while_other_reserved(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source, cfg, grant, state_dir = t3_bundle(tmp_path, monkeypatch)
    claim_active_reservation(state_dir, grant)
    other = tmp_path / "disjoint.jsonl"
    other.write_text("{}\n", encoding="utf-8")
    path_key = str(other.resolve())
    with index_write_flock(cfg):
        with production_chroma_write_session(
            entrypoint="inter_model_index", affected_sources=(path_key,)
        ) as session:
            session.store.add_unit(
                "unit-disjoint",
                "body",
                [0.01] * 8,
                {"source_path": path_key, "tool": "inter_model"},
            )
    with index_write_flock(cfg):
        with production_chroma_write_session(
            entrypoint="oracle.count", affected_sources=(path_key,)
        ) as session:
            assert session.store.count_units() >= 1



def test_repository_knowledge_scoped_session_defers_on_reserved_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    source, cfg, grant, state_dir = t3_bundle(tmp_path, monkeypatch)
    claim_active_reservation(state_dir, grant)
    path_key = str(source.resolve())
    with pytest.raises(BootstrapWriterCoordinationError, match="coordination_deferral"):
        with index_write_flock(cfg):
            with production_chroma_write_session(
                entrypoint="repository_knowledge_index",
                affected_sources=(path_key,),
            ) as session:
                session.store.add_unit(
                    "rk-unit",
                    "doc",
                    [0.0] * 8,
                    {"source_path": path_key},
                )


def test_nested_chroma_sessions_reenter_safely(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    _source, cfg, _grant, _state_dir = t3_bundle(tmp_path, monkeypatch)
    a = tmp_path / "a.jsonl"
    b = tmp_path / "b.jsonl"
    a.write_text("{}\n", encoding="utf-8")
    b.write_text("{}\n", encoding="utf-8")
    key_a, key_b = str(a.resolve()), str(b.resolve())
    with index_write_flock(cfg):
        with production_chroma_write_session(
            entrypoint="refine.write", affected_sources=(key_a,)
        ) as outer:
            outer.store.add_summary(
                "outer",
                "o",
                [0.0] * 8,
                {"source_path": key_a},
            )
            with production_chroma_write_session(
                entrypoint="refine.write", affected_sources=(key_b,)
            ) as inner:
                inner.store.add_summary(
                    "inner",
                    "i",
                    [0.0] * 8,
                    {"source_path": key_b},
                )


def test_propose_decision_entrypoint_unscoped_chroma_defers(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    source, cfg, grant, state_dir = t3_bundle(tmp_path, monkeypatch)
    claim_active_reservation(state_dir, grant)
    with pytest.raises(BootstrapWriterCoordinationError, match="maintenance_deferred"):
        with index_write_flock(cfg):
            with production_chroma_write_session(entrypoint="propose_decision.write") as session:
                session.store.add_summary("p", "t", [0.0] * 8, {})


def test_monitor_entrypoint_unscoped_chroma_defers(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    source, cfg, grant, state_dir = t3_bundle(tmp_path, monkeypatch)
    claim_active_reservation(state_dir, grant)
    with pytest.raises(BootstrapWriterCoordinationError, match="maintenance_deferred"):
        with index_write_flock(cfg):
            with production_chroma_write_session(entrypoint="convmem.monitor") as session:
                session.store.add_summary("m", "t", [0.0] * 8, {})


def test_disjoint_processed_merge_while_other_reserved(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    source, cfg, grant, state_dir = t3_bundle(tmp_path, monkeypatch)
    claim_active_reservation(state_dir, grant)
    other = tmp_path / "disjoint.jsonl"
    other.write_text("{}\n", encoding="utf-8")
    path_key = str(other.resolve())
    ok = commit_processed_index_entry(
        cfg["index"]["processed_log"],
        file_hash="d" * 64,
        path_key=path_key,
        chunks=1,
        units=0,
    )
    assert ok is True
    data = load_processed(cfg["index"]["processed_log"])
    assert data["d" * 64]["path"] == path_key


def test_source_purge_defers_at_processed_exclusion_before_chroma(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    from source_purge import execute_purge

    source, cfg, grant, state_dir = t3_bundle(tmp_path, monkeypatch)
    claim_active_reservation(state_dir, grant)
    path_key = str(source.resolve())
    chroma_entered = {"value": False}

    def after_exclusion() -> None:
        chroma_entered["value"] = True
        raise AssertionError("chroma boundary should not run when exclusion defers")

    with pytest.raises((BootstrapWriterCoordinationError, IncrementalJsonlError), match="coordination_deferral"):
        execute_purge(
            cfg,
            path_key,
            reason="test",
            _hooks={"after_exclusion": after_exclusion},
        )
    assert chroma_entered["value"] is False


def test_incremental_cleanup_preserves_v2_authority_artifact(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    from bootstrap_codex_v2_authority import authority_path
    from incremental_jsonl import DURABLE_TRANSITIONS, IncrementalJsonlCoordinator, IncrementalJsonlError

    source, cfg, grant, state_dir = t3_bundle(tmp_path, monkeypatch)
    claim_active_reservation(state_dir, grant)
    auth_path = authority_path(state_dir)
    assert auth_path.is_file()
    before_auth = auth_path.read_bytes()
    tx_path = state_dir / "transaction.json"
    tx_path.write_text('{"transaction_id": "t1"}\n', encoding="utf-8")
    rb_path = state_dir / "rollback.json"
    rb_path.write_text("{}", encoding="utf-8")
    snap_dir = state_dir / "snap-test"
    snap_dir.mkdir(parents=True)
    (snap_dir / "piece.json").write_text("{}", encoding="utf-8")

    class _CleanupProbe:
        paths = {"transaction": tx_path, "rollback": rb_path}

        def fault(self, _name: str) -> None:
            return None

        def _transition(self, name: str, action) -> None:
            if name not in DURABLE_TRANSITIONS:
                raise IncrementalJsonlError("undeclared_transition", name)
            action()

    IncrementalJsonlCoordinator._cleanup(_CleanupProbe(), snap_dir)
    assert auth_path.read_bytes() == before_auth
    assert not tx_path.exists()
    assert not rb_path.exists()
    assert not snap_dir.exists()


def test_enforce_incremental_retry_gates_check_before_reserve(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    from incremental_retry_state import enforce_incremental_retry_gates

    order: list[str] = []

    def track_check(*_a, **_k):
        order.append("check")

    def track_reserve(*_a, **_k):
        order.append("reserve")

    monkeypatch.setattr(
        "incremental_retry_state.check_incremental_retry_gates",
        track_check,
    )
    monkeypatch.setattr(
        "incremental_retry_state.reserve_incremental_retry_attempt",
        track_reserve,
    )
    paths = {"transaction": str(tmp_path / "state" / "transaction.json")}
    Path(paths["transaction"]).parent.mkdir(parents=True)
    enforce_incremental_retry_gates(
        paths,
        path_key=str(tmp_path / "x.jsonl"),
        prefix_digest="f" * 64,
        transaction_id="tx-1",
    )
    assert order == ["check", "reserve"]

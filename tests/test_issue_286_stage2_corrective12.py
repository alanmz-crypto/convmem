"""Safe-behavior tests for issue #286 stage-2 corrective 12 (R2-F1..F4)."""

# pylint: disable=protected-access

from __future__ import annotations

import inspect
import json
import threading
from pathlib import Path
from unittest.mock import Mock

import pytest

from chroma_store import ChromaStore


def observation():
    return {
        "id": "obs_audit_r2",
        "title": "Audit observation",
        "summary": "A valid observation from the scratch audit.",
        "keywords": ["audit", "scratch", "safety"],
        "author_model": "audit",
        "type": "observation",
        "domain": "coding.tooling",
        "confidence": 0.9,
    }


def test_readonly_retry_file_refuses_before_more_paid_work(tmp_path, monkeypatch):
    import incremental_jsonl as inc
    from tests.test_zz_claude_verify8b import _count_summaries, _retry_state_path
    from tests.test_zz_codex_audit import _route_fixture

    source, cfg, route = _route_fixture(tmp_path, monkeypatch)
    calls = _count_summaries(monkeypatch)

    def fail(*_a, **_k):
        raise OSError("prepared write failed")

    monkeypatch.setattr(inc.IncrementalJsonlCoordinator, "_write_prepared", fail)
    with pytest.raises(inc.IncrementalJsonlError):
        route()
    state = _retry_state_path(tmp_path)
    original = state.read_bytes()
    state.chmod(0o400)
    try:
        with pytest.raises(inc.IncrementalJsonlError) as caught:
            route()
        assert caught.value.code == "retry_state_unavailable"
    finally:
        state.chmod(0o600)
    assert len(calls) == 1
    assert state.read_bytes() == original


def test_alternating_failures_bound_by_prefix_attempts(tmp_path, monkeypatch):
    import incremental_jsonl as inc
    from tests.test_zz_claude_verify8b import _count_summaries
    from tests.test_zz_codex_audit import _route_fixture

    source, cfg, route = _route_fixture(tmp_path, monkeypatch)
    calls = _count_summaries(monkeypatch)

    def fail(*_a, **_k):
        if len(calls) % 2:
            raise OSError("prepared write failed")
        raise ValueError("artifact serialization failure")

    monkeypatch.setattr(inc.IncrementalJsonlCoordinator, "_write_prepared", fail)
    codes: list[str] = []
    for _ in range(6):
        try:
            route()
        except inc.IncrementalJsonlError as exc:
            codes.append(exc.code)
    assert len(calls) == 3
    assert codes[-1] == "live_route_refused"


def test_reservation_survives_exit_before_failure_record(tmp_path):
    from incremental_retry_state import enforce_incremental_retry_gates, load_incremental_retry_state

    paths = {"transaction": tmp_path / "tx" / "transaction.json"}
    paths["transaction"].parent.mkdir(parents=True, exist_ok=True)
    enforce_incremental_retry_gates(
        paths,
        path_key="/tmp/source.jsonl",
        prefix_digest="a" * 64,
        transaction_id="t" * 32,
    )
    state = load_incremental_retry_state(paths)
    assert state is not None
    assert int(state.get("attempts_on_prefix") or 0) == 1


def test_unchanged_preparation_drift_reprepares_outside_c1(tmp_path, monkeypatch):
    import llm
    from chroma_write_store import production_chroma_store_session_depth
    from observe import (
        ObservationIngestDriftError,
        commit_observation_ingest,
        ingest_observation,
        prepare_observation_file_rows,
    )
    from purge_locks import index_write_flock, index_write_lock_depth
    from tests.test_zz_claude_verify9 import _real_session_env

    cfg = _real_session_env(tmp_path, monkeypatch)
    record = observation()
    seed = ChromaStore(cfg["index"]["chroma_dir"])
    unit = ingest_observation(
        record,
        store=seed,
        embed_model="fake",
        ollama_host="offline",
        upsert=True,
        precomputed_embedding=[0.1, 0.2, 0.3],
    )
    seed.close()
    path = tmp_path / "observations.jsonl"
    path.write_text(json.dumps(record) + "\n")
    from chroma_readonly import open_readonly_unit_store
    from chroma_write_store import production_chroma_write_session
    from ledger import invalidate_ledger_index_cache

    invalidate_ledger_index_cache(cfg["index"]["chroma_dir"])
    reader = open_readonly_unit_store(cfg["index"]["chroma_dir"])
    rows, _ = prepare_observation_file_rows(
        str(path),
        embed_store=reader,
        embed_model="fake",
        ollama_host="offline",
        upsert=True,
    )
    assert rows[0][1] is not None and rows[0][1].skipped_unchanged
    with index_write_flock(cfg):
        with production_chroma_write_session(entrypoint="audit.drift") as session:
            fresh = session.store.get_unit(unit["id"])
            session.store.update_unit(
                unit["id"],
                "changed after preparation",
                [0.1, 0.2, 0.3],
                fresh["metadata"],
            )
    depths: list[tuple[int, int]] = []

    def embed(*_a, **_k):
        depths.append(
            (index_write_lock_depth(), production_chroma_store_session_depth())
        )
        return [0.1, 0.2, 0.3]

    monkeypatch.setattr(llm, "ollama_embed", embed)
    with index_write_flock(cfg):
        with production_chroma_write_session(entrypoint="audit.commit") as session:
            with pytest.raises(ObservationIngestDriftError):
                commit_observation_ingest(rows[0][1], store=session.store)
    assert depths == []


def test_commit_rechecks_missing_monitor_target(tmp_path, monkeypatch):
    from observe import commit_observation_ingest, prepare_observation_ingest

    reader = Mock()
    reader.get_unit.return_value = {"id": "old", "metadata": {}, "document": "old text"}
    prepared = prepare_observation_ingest(
        observation(),
        store=reader,
        embed_model="fake",
        ollama_host="offline",
        upsert=True,
        by_ledger_id={"obs_audit_r2": {"id": "old"}},
        precomputed_embedding=[0.1, 0.2, 0.3],
    )
    assert prepared is not None
    writer = Mock()
    writer.get_unit.return_value = None
    writer.units_metadata.return_value = [
        {"ledger_id": "obs_audit_r2", "id": "old"},
    ]

    from observe import ObservationIngestDriftError

    with pytest.raises(ObservationIngestDriftError):
        commit_observation_ingest(prepared, store=writer)
    writer.update_unit.assert_not_called()


def test_refine_queue_append_survives_locked_rollback(tmp_path, monkeypatch):
    import refine
    from purge_locks import index_write_flock
    from tests.test_issue_286_stage2_wedge_probes import _wedge_then_replay

    replay, _, _, _ = _wedge_then_replay(tmp_path, monkeypatch, "before_summary_upsert")
    queue = replay._dedupe_restore_paths()["dedupe_queue.jsonl"]
    queue.parent.mkdir(parents=True, exist_ok=True)
    queue.write_text(
        json.dumps({"event_id": "keep", "transaction_id": "foreign"})
        + "\n"
        + json.dumps({"event_id": "remove", "transaction_id": "mine"})
        + "\n"
    )
    vectors = Mock()
    vectors.get_units_with_embeddings.return_value = [
        {"id": "a", "metadata": {"domain": "general"}, "embedding": [1.0, 0.0]},
        {"id": "b", "metadata": {"domain": "general"}, "embedding": [1.0, 0.0]},
    ]
    monkeypatch.setattr(refine, "ChromaStore", lambda *a, **k: vectors)
    with index_write_flock(replay.cfg):
        result = refine.job_semantic_dedupe(None, replay.cfg, verbose=False)
    assert result["queued"] == 1
    assert '"id_a": "a"' in queue.read_text()
    with index_write_flock(replay.cfg):
        replay._restore_dedupe_files("mine")
    assert '"id_a": "a"' in queue.read_text()
    assert '"event_id": "keep"' in queue.read_text()


def test_approved_single_ledger_prepares_outside_c1(tmp_path, monkeypatch):
    import llm
    import propose_decision
    from chroma_write_store import production_chroma_store_session_depth
    from purge_locks import index_write_lock_depth
    from tests.test_zz_claude_verify9 import _real_session_env

    cfg = _real_session_env(tmp_path, monkeypatch)
    depths: list[tuple[int, int]] = []

    def embed(*_a, **_k):
        depths.append(
            (index_write_lock_depth(), production_chroma_store_session_depth())
        )
        return [0.1, 0.2, 0.3]

    monkeypatch.setattr(llm, "ollama_embed", embed)
    result = propose_decision.ingest_approved_ledger(cfg, observation())
    assert result["accepted"] == 1
    assert depths == [(0, 0)]


def test_monitor_deleted_target_does_not_export_upsert(tmp_path, monkeypatch):
    from chroma_write_store import production_chroma_write_session
    from ledger import invalidate_ledger_index_cache
    from observe import (
        ObservationIngestDriftError,
        commit_observation_ingest,
        ingest_observation,
        prepare_observation_ingest,
    )
    from purge_locks import index_write_flock
    from tests.test_zz_claude_verify9 import _real_session_env

    cfg = _real_session_env(tmp_path, monkeypatch)
    record = observation()
    seed = ChromaStore(cfg["index"]["chroma_dir"])
    unit = ingest_observation(
        record,
        store=seed,
        embed_model="fake",
        ollama_host="offline",
        upsert=True,
        precomputed_embedding=[0.1, 0.2, 0.3],
    )
    seed.close()
    invalidate_ledger_index_cache(cfg["index"]["chroma_dir"])
    from chroma_readonly import open_readonly_unit_store

    reader = open_readonly_unit_store(cfg["index"]["chroma_dir"])
    prepared = prepare_observation_ingest(
        {**record, "summary": "New monitor result"},
        store=reader,
        embed_model="fake",
        ollama_host="offline",
        upsert=True,
        precomputed_embedding=[0.1, 0.2, 0.3],
    )
    assert prepared is not None
    export = tmp_path / "monitor-export.jsonl"
    with index_write_flock(cfg):
        with production_chroma_write_session(entrypoint="audit.delete") as session:
            session.store.delete_units_for_source(unit["source_path"])
            assert session.store.get_unit(unit["id"]) is None
    with index_write_flock(cfg):
        with production_chroma_write_session(entrypoint="audit.commit") as session:
            with pytest.raises(ObservationIngestDriftError):
                commit_observation_ingest(
                    prepared, store=session.store, units_export=export
                )
    assert not export.exists()


def test_index_write_guarded_store_read_allow_list_complete():
    from chroma_store import ChromaStore
    from chroma_write_store import _IndexWriteGuardedChromaStore

    public = {
        name
        for name, member in inspect.getmembers(ChromaStore)
        if not name.startswith("_") and callable(member)
    }
    reads = set(_IndexWriteGuardedChromaStore._READS)
    inner = Mock()
    guarded = _IndexWriteGuardedChromaStore(inner)
    for name in sorted(public):
        if name in reads or name == "client":
            continue
        with pytest.raises(RuntimeError, match="index write lock"):
            getattr(guarded, name)("x", "y", [0.0], {})


def test_add_file_upsert_drift_allows_second_admission_round(tmp_path, monkeypatch) -> None:
    """N4: a fresh admission context per commit round survives drift retry (no RuntimeError)."""
    import json
    from contextlib import contextmanager

    import llm

    monkeypatch.setattr(llm, "ollama_embed", lambda *_a, **_k: [0.1, 0.2, 0.3])
    from chroma_readonly import open_readonly_unit_store
    from chroma_write_store import production_chroma_write_session
    from observe import ingest_observation_file_with_drift_retry
    from purge_locks import index_write_flock
    from tests.test_zz_claude_verify15 import _foreign_update, _obs, _seed
    from tests.test_zz_claude_verify9 import _real_session_env

    cfg = _real_session_env(tmp_path, monkeypatch)
    rec = _obs("obs_c13_add_upsert", "Original.")
    unit, = _seed(cfg, rec)
    path = tmp_path / "upsert.jsonl"
    path.write_text(json.dumps({**rec, "summary": "Updated from file."}) + "\n")
    admission_opens: list[int] = []
    commit_rounds = {"n": 0}

    @contextmanager
    def _admission_once_per_round():
        admission_opens.append(1)
        yield None

    def open_write_commit(commit_fn):
        commit_rounds["n"] += 1
        if commit_rounds["n"] == 1:
            _foreign_update(cfg, unit["id"], "foreign drift")
        with _admission_once_per_round():
            with index_write_flock(cfg):
                with production_chroma_write_session(entrypoint="convmem.add") as session:
                    return commit_fn(session.store, None)

    result = ingest_observation_file_with_drift_retry(
        str(path),
        embed_store=open_readonly_unit_store(cfg["index"]["chroma_dir"]),
        open_write_commit=open_write_commit,
        embed_model="fake",
        ollama_host="offline",
        upsert=True,
        verbose=False,
    )
    assert commit_rounds["n"] == 2, commit_rounds
    assert len(admission_opens) == 2, admission_opens
    assert result["updated"] == 1, result

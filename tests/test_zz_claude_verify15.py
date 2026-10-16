"""Claude verify probes, round 15 (8d6ee76): corrective 12's drift retry, insert race, limiter, guard.

Scratch only: real production store sessions against a scratch config; fake providers; no network.
"""

# pylint: disable=protected-access,duplicate-code

from __future__ import annotations

import json
from pathlib import Path  # pylint: disable=unused-import
from unittest.mock import Mock

import pytest

from tests.test_zz_claude_verify9 import _real_session_env


def _obs(lid: str, summary: str) -> dict:
    return {"id": lid, "title": f"Probe {lid}", "summary": summary,
            "keywords": ["probe", "scratch", "verify"], "author_model": "claude-verify",
            "type": "observation", "domain": "coding.tooling", "confidence": 0.9}


def _seed(cfg, *records):
    from chroma_store import ChromaStore
    from ledger import invalidate_ledger_index_cache  # pylint: disable=no-name-in-module  # stale docs/chatgpt-pack observe/ledger names
    from observe import ingest_observation

    seed = ChromaStore(cfg["index"]["chroma_dir"])
    try:
        units = [ingest_observation(r, store=seed, embed_model="fake", ollama_host="offline",  # pylint: disable=unexpected-keyword-arg
                                    upsert=True, precomputed_embedding=[0.1, 0.2, 0.3]) for r in records]
    finally:
        seed.close()
    invalidate_ledger_index_cache(cfg["index"]["chroma_dir"])
    return units


def _foreign_update(cfg, unit_id: str, text: str) -> None:
    from chroma_write_store import production_chroma_write_session
    from purge_locks import index_write_flock

    with index_write_flock(cfg):
        with production_chroma_write_session(entrypoint="claude_verify15.foreign") as session:
            fresh = session.store.get_unit(unit_id)
            session.store.update_unit(unit_id, text, [0.1, 0.2, 0.3], fresh["metadata"])


def _depth_embed(monkeypatch, depths):
    import llm
    from chroma_write_store import production_chroma_store_session_depth
    from purge_locks import index_write_lock_depth

    def embed(*_a, **_k):
        depths.append((index_write_lock_depth(), production_chroma_store_session_depth()))
        return [0.1, 0.2, 0.3]

    monkeypatch.setattr(llm, "ollama_embed", embed)


def _commit_fn(cfg, foreign=None):
    """Like convmem.add's open_write_commit; runs `foreign` once, before the first commit."""
    from chroma_write_store import production_chroma_write_session
    from purge_locks import index_write_flock

    calls = {"n": 0}

    def open_write_commit(commit):
        calls["n"] += 1
        if foreign and calls["n"] == 1:
            foreign()
        with index_write_flock(cfg):
            with production_chroma_write_session(entrypoint="claude_verify15.commit") as session:
                return commit(session.store, None)

    return open_write_commit, calls


class _FreshReader:
    """A readonly reader reopened on every call, to separate snapshot staleness from other effects."""

    def __init__(self, chroma_dir):
        self.chroma_dir = str(chroma_dir)

    def __getattr__(self, name):
        from chroma_readonly import open_readonly_unit_store
        from ledger import invalidate_ledger_index_cache  # pylint: disable=no-name-in-module  # stale docs/chatgpt-pack observe/ledger names

        invalidate_ledger_index_cache(self.chroma_dir)
        return getattr(open_readonly_unit_store(self.chroma_dir), name)


def test_c0_unchanged_and_changed_rows_commit_without_false_drift(tmp_path, monkeypatch) -> None:
    """Control: prepared from the readonly reader, committed to the write store, nothing foreign in between."""
    from chroma_readonly import open_readonly_unit_store
    from chroma_write_store import production_chroma_write_session
    from observe import commit_observation_ingest, prepare_observation_ingest  # pylint: disable=line-too-long, no-name-in-module# stale docs/chatgpt-pack observe/ledger names
    from purge_locks import index_write_flock

    cfg = _real_session_env(tmp_path, monkeypatch)
    same, changed = _obs("obs_v15_same", "Stays the same."), _obs("obs_v15_chg", "Old text.")
    _seed(cfg, same, changed)
    _depth_embed(monkeypatch, [])
    reader = open_readonly_unit_store(cfg["index"]["chroma_dir"])
    p_same = prepare_observation_ingest(same, store=reader, embed_model="fake", ollama_host="offline", upsert=True)
    p_chg = prepare_observation_ingest({**changed, "summary": "New text."}, store=reader, embed_model="fake",
                                       ollama_host="offline", upsert=True)
    assert p_same.skipped_unchanged and p_chg.upsert_update
    with index_write_flock(cfg):
        with production_chroma_write_session(entrypoint="claude_verify15.c0") as session:
            a = commit_observation_ingest(p_same, store=session.store)
            b = commit_observation_ingest(p_chg, store=session.store)
    assert a.get("_skipped") and b.get("_upserted")


def test_d1_single_row_drift_retry_recovers(tmp_path, monkeypatch) -> None:
    """Spec C2: on drift, release, re-prepare outside C1, commit again. Uses the caller's real reader."""
    from chroma_readonly import open_readonly_unit_store
    from observe import ingest_observation_file_with_drift_retry  # pylint: disable=no-name-in-module  # stale docs/chatgpt-pack observe/ledger names

    cfg = _real_session_env(tmp_path, monkeypatch)
    rec = _obs("obs_v15_d1", "Old text.")
    unit, = _seed(cfg, rec)
    path = tmp_path / "obs.jsonl"
    path.write_text(json.dumps({**rec, "summary": "New text from the file."}) + "\n")
    depths = []
    _depth_embed(monkeypatch, depths)
    owc, calls = _commit_fn(cfg, lambda: _foreign_update(cfg, unit["id"], "foreign change"))
    try:
        result, err = ingest_observation_file_with_drift_retry(
            str(path), embed_store=open_readonly_unit_store(cfg["index"]["chroma_dir"]),
            open_write_commit=owc, embed_model="fake", ollama_host="offline", upsert=True, verbose=False), None
    except Exception as exc:  # noqa: BLE001  # pylint: disable=broad-exception-caught
        result, err = None, repr(exc)[:160]
    assert all(d == (0, 0) for d in depths), depths
    assert err is None, ("commit rounds:", calls["n"], err)
    assert result["updated"] == 1, result


def test_d2_single_row_drift_retry_with_a_fresh_reader(tmp_path, monkeypatch) -> None:
    """Same as d1 but the reader is reopened on each call: isolates snapshot staleness."""
    from observe import ingest_observation_file_with_drift_retry  # pylint: disable=no-name-in-module  # stale docs/chatgpt-pack observe/ledger names

    cfg = _real_session_env(tmp_path, monkeypatch)
    rec = _obs("obs_v15_d2", "Old text.")
    unit, = _seed(cfg, rec)
    path = tmp_path / "obs.jsonl"
    path.write_text(json.dumps({**rec, "summary": "New text from the file."}) + "\n")
    _depth_embed(monkeypatch, [])
    owc, calls = _commit_fn(cfg, lambda: _foreign_update(cfg, unit["id"], "foreign change"))
    result = ingest_observation_file_with_drift_retry(
        str(path), embed_store=_FreshReader(cfg["index"]["chroma_dir"]), open_write_commit=owc,
        embed_model="fake", ollama_host="offline", upsert=True, verbose=False)
    assert result["updated"] == 1 and calls["n"] == 2, (result, calls)


def test_d3_batch_drift_on_a_later_row_recovers(tmp_path, monkeypatch) -> None:
    """Two changed rows; only row 2 drifts. Row 1 is committed in round 1; round 2 must not trip on it."""
    from observe import ingest_observation_file_with_drift_retry  # pylint: disable=no-name-in-module  # stale docs/chatgpt-pack observe/ledger names

    cfg = _real_session_env(tmp_path, monkeypatch)
    r1, r2 = _obs("obs_v15_b1", "Old one."), _obs("obs_v15_b2", "Old two.")
    _u1, u2 = _seed(cfg, r1, r2)
    path = tmp_path / "obs.jsonl"
    path.write_text(json.dumps({**r1, "summary": "New one."}) + "\n" + json.dumps({**r2, "summary": "New two."}) + "\n")
    _depth_embed(monkeypatch, [])
    owc, calls = _commit_fn(cfg, lambda: _foreign_update(cfg, u2["id"], "foreign change"))
    try:
        result, err = ingest_observation_file_with_drift_retry(
            str(path), embed_store=_FreshReader(cfg["index"]["chroma_dir"]), open_write_commit=owc,
            embed_model="fake", ollama_host="offline", upsert=True, verbose=False), None
    except Exception as exc:  # noqa: BLE001  # pylint: disable=broad-exception-caught
        result, err = None, repr(exc)[:160]
    assert err is None, ("commit rounds:", calls["n"], err)
    assert result["updated"] == 2, result


def test_i1_insert_race_is_revalidated(tmp_path, monkeypatch) -> None:
    """Spec D: a row prepared against 'no target' must not commit over a target that appeared since."""
    from chroma_readonly import open_readonly_unit_store
    from chroma_write_store import production_chroma_write_session
    from ledger import invalidate_ledger_index_cache  # pylint: disable=no-name-in-module  # stale docs/chatgpt-pack observe/ledger names
    from observe import (ObservationIngestDriftError, commit_observation_ingest, ingest_observation,  # pylint: disable=line-too-long, no-name-in-module# stale docs/chatgpt-pack observe/ledger names
                         prepare_observation_ingest)
    from purge_locks import index_write_flock

    cfg = _real_session_env(tmp_path, monkeypatch)
    _depth_embed(monkeypatch, [])
    rec = _obs("obs_v15_ins", "Mine, prepared first.")
    reader = open_readonly_unit_store(cfg["index"]["chroma_dir"])
    prepared = prepare_observation_ingest(rec, store=reader, embed_model="fake", ollama_host="offline", upsert=True)
    assert not prepared.upsert_update and not prepared.skipped_unchanged
    with index_write_flock(cfg):
        with production_chroma_write_session(entrypoint="claude_verify15.foreign") as session:
            ingest_observation({**rec, "summary": "Foreign, inserted after my prepare."}, store=session.store,  # pylint: disable=unexpected-keyword-arg
                               embed_model="fake", ollama_host="offline", upsert=True,
                               precomputed_embedding=[0.1, 0.2, 0.3])
    invalidate_ledger_index_cache(cfg["index"]["chroma_dir"])
    outcome = "committed"
    with index_write_flock(cfg):
        with production_chroma_write_session(entrypoint="claude_verify15.commit") as session:
            try:
                commit_observation_ingest(prepared, store=session.store)
            except ObservationIngestDriftError:
                outcome = "drift"
            rows = [m for m in session.store.units_metadata() if m.get("ledger_id") == "obs_v15_ins"]
    assert outcome == "drift", (outcome, len(rows))


def test_l1_semantic_dedupe_limiter_keeps_what_it_counted(tmp_path, monkeypatch) -> None:
    """The batched append must not drop candidates found before the hourly cap stops the job."""
    import refine

    cfg = _real_session_env(tmp_path, monkeypatch)
    vectors = Mock()
    vectors.get_units_with_embeddings.return_value = [
        {"id": x, "metadata": {"domain": "general"}, "embedding": [1.0, 0.0]} for x in ("a", "b", "c")]
    monkeypatch.setattr(refine, "ChromaStore", lambda *a, **k: vectors)
    limiter = Mock()
    limiter.allow.side_effect = [True, False, False, False]
    stats = refine.job_semantic_dedupe(None, cfg, verbose=False, limiter=limiter)
    queue = refine.dedupe_queue_path(cfg)
    lines = queue.read_text().splitlines() if queue.exists() else []
    assert stats["queued"] == len(lines), (stats, len(lines))


@pytest.mark.parametrize("call", ["embed", "summarize", "distill"])
def test_g1_real_provider_entry_refuses_under_c1(tmp_path, monkeypatch, call) -> None:
    """The runtime guard fires before any HTTP (hosts point at a closed port)."""
    import distill
    import llm
    from purge_locks import index_write_flock

    cfg = _real_session_env(tmp_path, monkeypatch)
    fn = {"embed": lambda: llm.ollama_embed("x", model="fake", host="http://127.0.0.1:9"),
          "summarize": lambda: llm.summarize("x", model="fake", ollama_host="http://127.0.0.1:9",
                                             deepseek_base_url="http://127.0.0.1:9"),
          "distill": lambda: distill.distill_with_response("x", model="fake", ollama_host="http://127.0.0.1:9",
                                                           deepseek_base_url="http://127.0.0.1:9")}[call]
    with index_write_flock(cfg):
        with pytest.raises(RuntimeError, match="provider calls are forbidden"):
            fn()

"""Codex audit round-3 probes (issue #286 corrective 16) — safe-behavior assertions."""

# pylint: disable=protected-access,duplicate-code

from __future__ import annotations

import json
import threading
from concurrent.futures import ThreadPoolExecutor

import pytest

from tests.test_zz_claude_verify9 import _real_session_env
from tests.test_zz_claude_verify15 import _depth_embed, _foreign_update, _obs, _seed


def test_repair_real_drift_completes_with_document_accurate_retry(tmp_path, monkeypatch):
    import llm
    import observe
    from chroma_write_store import production_chroma_store_session_depth
    from ledger import invalidate_ledger_index_cache  # pylint: disable=no-name-in-module  # stale docs/chatgpt-pack observe/ledger names
    from purge_locks import index_write_lock_depth
    from tests.test_ledger_document import _DECISION

    cfg = _real_session_env(tmp_path, monkeypatch)
    record = {**_DECISION, "_governed_protocol": True, "proposal_id": "audit-repair"}
    unit, = _seed(cfg, record)
    _foreign_update(cfg, unit["id"], "")
    invalidate_ledger_index_cache(cfg["index"]["chroma_dir"])
    monkeypatch.setattr("ledger_recent.load_approved_decision_by_id", lambda *a: record)
    depths: list[tuple[int, int]] = []

    def embed(*a, **kw):  # pylint: disable=unused-argument
        depths.append((index_write_lock_depth(), production_chroma_store_session_depth()))
        _foreign_update(cfg, unit["id"], "A cooperating writer repaired the text.")
        return [0.1, 0.2, 0.3]

    monkeypatch.setattr(llm, "ollama_embed", embed)
    stats = observe.repair_empty_ledger_documents(cfg, verbose=False)  # pylint: disable=no-member  # stale docs/chatgpt-pack observe/ledger names
    assert depths and all(depth == (0, 0) for depth in depths)
    assert stats["repaired"] + stats["skipped"] >= 1


def test_concurrent_real_routes_bound_prefix_attempts(tmp_path, monkeypatch):
    import incremental_jsonl as inc
    import incremental_retry_state as retry  # pylint: disable=unused-import
    from tests.test_zz_claude_verify8b import _count_summaries
    from tests.test_zz_codex_audit import _route_fixture

    source, cfg, route = _route_fixture(tmp_path, monkeypatch)
    calls = _count_summaries(monkeypatch)
    state_dir = inc.source_state_id(str(source.resolve()), format_id="jsonl_codex_rollout")
    from pathlib import Path

    state = Path(cfg["index"]["incremental_jsonl"]["state_dir"]) / state_dir / "retry_state.json"
    state.parent.mkdir(parents=True, exist_ok=True)
    state.write_text("{}\n")

    def fail(*a, **kw):
        raise OSError("scratch prepared artifact failure")

    monkeypatch.setattr(inc.IncrementalJsonlCoordinator, "_write_prepared", fail)

    def invoke():  # pylint: disable=inconsistent-return-statements
        try:
            route()
        except inc.IncrementalJsonlError as exc:
            return exc.code

    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(lambda _: invoke(), range(4)))
    saved = json.loads(state.read_text())
    assert len(calls) <= 3
    assert int(saved.get("attempts_on_prefix") or 0) == len(calls)
    assert len(results) == 4


def test_monitor_unchanged_row_drift_completes_or_refuses_cleanly(tmp_path, monkeypatch):
    import monitor
    import observe

    cfg = _real_session_env(tmp_path, monkeypatch)
    monkeypatch.setattr(monitor, "fetch_https_headers", lambda *a, **kw: ({}, "offline"))
    monkeypatch.setattr(monitor, "check_tls_redirect", lambda *a, **kw: False)
    monkeypatch.setattr(monitor, "_now_iso", lambda: "2026-10-15T00:00:00Z")
    depths: list[tuple[int, int]] = []
    _depth_embed(monkeypatch, depths)

    def run():
        return monitor.run_monitor(
            site="example.test",
            embed_model="fake",
            ollama_host="offline",
            live_cfg=cfg,
            verbose=False,
        )

    run()
    run()
    depths.clear()
    real_prepare = observe.prepare_observation_ingest  # pylint: disable=no-member  # stale docs/chatgpt-pack observe/ledger names
    changed: list[str] = []

    def prepare(*a, **kw):
        prepared = real_prepare(*a, **kw)
        if prepared and prepared.skipped_unchanged and not changed:
            assert prepared.embedding == []
            changed.append(prepared.existing_chroma_id or "")
            _foreign_update(cfg, prepared.existing_chroma_id, "Foreign monitor row change.")
        return prepared

    monkeypatch.setattr(observe, "prepare_observation_ingest", prepare)
    stats = run()
    assert len(changed) == 1
    assert stats["errors"] == 0 or stats.get("drift_refused", 0) >= 1
    assert depths == [(0, 0)] or depths == []  # pylint: disable=consider-using-in, use-implicit-booleaness-not-comparison


def test_post_admission_failure_record_error_still_bounds_work(tmp_path, monkeypatch):
    import incremental_jsonl as inc
    import incremental_retry_state as retry
    from tests.test_zz_claude_verify8b import _count_summaries
    from tests.test_zz_codex_audit import _route_fixture

    source, cfg, route = _route_fixture(tmp_path, monkeypatch)  # pylint: disable=unused-variable
    calls = _count_summaries(monkeypatch)
    original_write = retry._write

    def write(path, payload):
        if "transaction_id" in payload:
            raise OSError("failure recording unavailable after reservation")
        return original_write(path, payload)

    monkeypatch.setattr(retry, "_write", write)

    def fail(*a, **kw):
        raise OSError("partial artifact failed")

    monkeypatch.setattr(inc.IncrementalJsonlCoordinator, "_write_prepared", fail)
    codes: list[str] = []
    for _ in range(6):
        with pytest.raises(inc.IncrementalJsonlError) as caught:
            route()
        codes.append(caught.value.code)
    assert len(calls) == 3
    assert codes == ["retry_state_unavailable"] * 3 + ["live_route_refused"] * 3


def test_refine_append_waits_then_survives_real_rollback(tmp_path, monkeypatch):
    import refine
    from unittest.mock import Mock

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
    real_temp = replay._export_temp
    started, finished = threading.Event(), threading.Event()
    errors: list[BaseException] = []
    workers: list[threading.Thread] = []

    def temp(path):
        if path == queue:

            def append():
                started.set()
                try:
                    assert refine.job_semantic_dedupe(None, replay.cfg, verbose=False)["queued"] == 1
                except BaseException as exc:  # pylint: disable=broad-exception-caught
                    errors.append(exc)
                finally:
                    finished.set()

            thread = threading.Thread(target=append)
            workers.append(thread)
            thread.start()
            assert started.wait(2)
            assert not finished.wait(0.1)
        return real_temp(path)

    monkeypatch.setattr(replay, "_export_temp", temp)
    with index_write_flock(replay.cfg):
        replay._restore_dedupe_files("mine")
    for thread in workers:
        thread.join(5)
        assert not thread.is_alive()
    assert not errors, errors
    assert '"id_a": "a"' in queue.read_text()
    assert '"event_id": "keep"' in queue.read_text()
    assert '"event_id": "remove"' not in queue.read_text()


def test_export_failure_still_clears_post_write_ledger_cache(tmp_path, monkeypatch):
    import observe
    from chroma_readonly import open_readonly_unit_store
    from chroma_write_store import production_chroma_write_session
    from ledger import build_ledger_index, invalidate_ledger_index_cache  # pylint: disable=no-name-in-module  # stale docs/chatgpt-pack observe/ledger names
    from purge_locks import index_write_flock
    cfg = _real_session_env(tmp_path, monkeypatch)
    rec = _obs("obs_cache_failure", "Scratch cache failure observation.")
    reader = open_readonly_unit_store(cfg["index"]["chroma_dir"])
    prepared = observe.prepare_observation_ingest(  # pylint: disable=no-member  # stale docs/chatgpt-pack observe/ledger names
        rec,
        store=reader,
        embed_model="fake",
        ollama_host="offline",
        upsert=True,
        precomputed_embedding=[0.1, 0.2, 0.3],
    )
    assert build_ledger_index(reader)[0] == {}  # pylint: disable=use-implicit-booleaness-not-comparison

    def fail(*a, **kw):
        raise OSError("scratch export publication failure")

    monkeypatch.setattr(observe, "_upsert_jsonl_line", fail)
    with index_write_flock(cfg):
        with production_chroma_write_session(entrypoint="audit.cache") as session:
            with pytest.raises(OSError, match="scratch export"):
                observe.commit_observation_ingest(  # pylint: disable=no-member  # stale docs/chatgpt-pack observe/ledger names
                    prepared,
                    store=session.store,
                    units_export=tmp_path / "export.jsonl",
                )
            assert len(session.store.active_units_for_ledger_id(rec["id"])) == 1
            invalidate_ledger_index_cache(cfg["index"]["chroma_dir"])
            assert rec["id"] in build_ledger_index(session.store)[0]
    fresh_reader = open_readonly_unit_store(cfg["index"]["chroma_dir"])
    next_prepared = observe.prepare_observation_ingest(  # pylint: disable=no-member  # stale docs/chatgpt-pack observe/ledger names
        rec,
        store=fresh_reader,
        embed_model="fake",
        ollama_host="offline",
        upsert=True,
        precomputed_embedding=[0.1, 0.2, 0.3],
    )
    assert next_prepared.target_digest != "missing"
    with index_write_flock(cfg):
        with production_chroma_write_session(entrypoint="audit.cache.recheck") as session:
            unit = observe.commit_observation_ingest(next_prepared, store=session.store)  # pylint: disable=line-too-long, no-member# stale docs/chatgpt-pack observe/ledger names
            assert unit is not None
            assert rec["id"] in build_ledger_index(session.store)[0]


def test_tracked_artifact_writer_is_included_in_inventory(tmp_path, monkeypatch):
    import subprocess

    from eval_corpus.r2b_v2.coverage import inventory

    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    body = 'from chroma_store import ChromaStore\nstore = ChromaStore("/scratch/chroma")\n'
    for folder in ("review-bundles", "artifacts"):
        path = tmp_path / folder / "tracked_writer.py"
        path.parent.mkdir()
        path.write_text(body)
        subprocess.run(["git", "-C", str(tmp_path), "add", str(path)], check=True)
    manifest = tmp_path / "shadow.json"
    manifest.write_text('{"allowlisted_direct_sites": []}')
    monkeypatch.setattr(inventory, "ROOT", tmp_path)
    monkeypatch.setattr(inventory, "SHADOW_INVENTORY", manifest)
    hits = inventory._scan_chroma_ctor_uncached()
    assert "review-bundles/tracked_writer.py:2" in hits
    assert "artifacts/tracked_writer.py:2" in hits
    assert not inventory._skip_repo_scan_path("artifacts/tracked_writer.py")

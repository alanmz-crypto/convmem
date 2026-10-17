"""Codex audit round-4 probes (issue #286 corrective 17)."""

# pylint: disable=protected-access,duplicate-code

from __future__ import annotations

import fcntl
import json
import os
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest


def _state_root(source, cfg):
    import incremental_jsonl as inc

    return Path(cfg["index"]["incremental_jsonl"]["state_dir"]) / inc.source_state_id(
        str(source.resolve()), format_id="jsonl_codex_rollout"
    )


def _lock_held(path):
    fd = os.open(path, os.O_RDWR)
    try:
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return True
        fcntl.flock(fd, fcntl.LOCK_UN)
        return False
    finally:
        os.close(fd)


def _snapshot_metrics(root: Path) -> tuple[int, int]:
    snapshots = list((root / "snapshots").glob("*/*"))
    return len(snapshots), sum(p.stat().st_size for p in snapshots)


def test_lock_covers_admission_run_accounting_and_release(tmp_path, monkeypatch):
    import incremental_jsonl as inc
    import incremental_retry_state as retry
    from purge_locks import index_write_lock_depth
    from chroma_write_store import production_chroma_store_session_depth
    from tests.test_zz_claude_verify8b import _count_summaries
    from tests.test_zz_codex_audit import _route_fixture

    source, cfg, route = _route_fixture(tmp_path, monkeypatch)  # pylint: disable=unused-variable
    calls = _count_summaries(monkeypatch)
    seen = []
    lock_path = []
    original_gate = retry.enforce_incremental_retry_gates
    original_record = retry.record_incremental_retry_failure

    def gate(paths, **kw):
        lock_path[:] = [paths["lock"]]
        assert _lock_held(paths["lock"])
        seen.append("admission")
        return original_gate(paths, **kw)

    def fail(self, *args, **kw):  # pylint: disable=unused-argument
        assert _lock_held(self.paths["lock"])
        assert (index_write_lock_depth(), production_chroma_store_session_depth()) == (0, 0)
        seen.append("run")
        raise OSError("scratch prepared failure")

    def record(paths, **kw):
        assert _lock_held(paths["lock"])
        seen.append("accounting")
        return original_record(paths, **kw)

    monkeypatch.setattr(retry, "enforce_incremental_retry_gates", gate)
    monkeypatch.setattr(retry, "record_incremental_retry_failure", record)
    monkeypatch.setattr(inc.IncrementalJsonlCoordinator, "_write_prepared", fail)
    for _ in range(4):
        with pytest.raises(inc.IncrementalJsonlError):
            route()
        assert not _lock_held(lock_path[0])
    assert len(calls) == 2
    assert seen == ["admission", "run", "accounting"] * 2 + ["admission"] * 2


def test_competitor_cannot_enter_during_failure_accounting(tmp_path, monkeypatch):
    import incremental_jsonl as inc
    import incremental_retry_state as retry
    from tests.test_zz_claude_verify8b import _count_summaries
    from tests.test_zz_codex_audit import _route_fixture

    source, cfg, route = _route_fixture(tmp_path, monkeypatch)
    calls = _count_summaries(monkeypatch)
    original = retry.record_incremental_retry_failure
    paused, release = threading.Event(), threading.Event()
    records = []

    def record(paths, **kw):
        records.append(1)
        if len(records) == 1:
            paused.set()
            assert release.wait(5)
        return original(paths, **kw)

    def fail(*args, **kw):
        raise OSError("scratch prepared failure")

    def invoke():  # pylint: disable=inconsistent-return-statements
        try:
            route()
        except inc.IncrementalJsonlError as exc:
            return exc.code

    monkeypatch.setattr(retry, "record_incremental_retry_failure", record)
    monkeypatch.setattr(inc.IncrementalJsonlCoordinator, "_write_prepared", fail)
    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(invoke)
        assert paused.wait(5)
        second = pool.submit(invoke)
        try:
            assert not second.done()
            assert not threading.Event().wait(0.2)
            assert len(calls) == 1
            assert len(records) == 1
            assert not second.done()
        finally:
            release.set()
        results = [first.result(5), second.result(5)]
    saved = json.loads((_state_root(source, cfg) / "retry_state.json").read_text())
    assert len(calls) == saved["attempts_on_prefix"] == saved["consecutive"] == 2
    assert results


def test_concurrent_failed_accounting_still_caps_at_three(tmp_path, monkeypatch):
    import incremental_jsonl as inc
    import incremental_retry_state as retry
    from tests.test_zz_claude_verify8b import _count_summaries
    from tests.test_zz_codex_audit import _route_fixture

    source, cfg, route = _route_fixture(tmp_path, monkeypatch)
    calls = _count_summaries(monkeypatch)
    original = retry._write

    def write(path, payload):
        if "transaction_id" in payload:
            raise OSError("failure accounting unavailable")
        return original(path, payload)

    def fail(*args, **kw):
        raise OSError("scratch prepared failure")

    def invoke(_):  # pylint: disable=inconsistent-return-statements
        try:
            route()
        except inc.IncrementalJsonlError as exc:
            return exc.code

    monkeypatch.setattr(retry, "_write", write)
    monkeypatch.setattr(inc.IncrementalJsonlCoordinator, "_write_prepared", fail)
    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(invoke, range(8)))
    saved = json.loads((_state_root(source, cfg) / "retry_state.json").read_text())
    assert len(calls) == saved["attempts_on_prefix"] == 3
    assert results.count("retry_state_unavailable") == 3
    assert results.count("live_route_refused") == 5


def test_success_clear_and_unchanged_stay_locked_without_reservation(tmp_path, monkeypatch):
    import incremental_retry_state as retry
    from tests.test_zz_codex_audit import _route_fixture

    source, cfg, route = _route_fixture(tmp_path, monkeypatch)
    seen = []
    original = retry.clear_incremental_retry_state

    def clear(paths):
        assert _lock_held(paths["lock"])
        seen.append("clear")
        return original(paths)

    monkeypatch.setattr(retry, "clear_incremental_retry_state", clear)
    result = route()
    root = _state_root(source, cfg)
    assert not (root / "retry_state.json").exists()

    def forbidden(*a, **kw):
        raise AssertionError("unchanged source tried to reserve work")

    monkeypatch.setattr(retry, "enforce_incremental_retry_gates", forbidden)
    result2 = route()
    assert len(seen) == 2
    assert result2[0] == "skipped"
    assert not (root / "retry_state.json").exists()
    assert result


def test_refusal_snapshot_growth_differential(tmp_path, monkeypatch):
    import incremental_jsonl as inc
    import ingest
    from tests.test_zz_claude_verify8b import _count_summaries
    from tests.test_zz_codex_audit import _route_fixture

    source, cfg, route = _route_fixture(tmp_path, monkeypatch)
    calls = _count_summaries(monkeypatch)

    def fail(*args, **kw):
        raise RuntimeError("scratch distill unavailable")

    monkeypatch.setattr(ingest, "distill", fail)
    monkeypatch.setattr(ingest, "_SYNTHESIS_FAIL_LOG", tmp_path / "synthesis_failures.jsonl")
    root = _state_root(source, cfg)
    rows = []
    for _ in range(6):
        with pytest.raises(inc.IncrementalJsonlError) as caught:
            route()
        files, nbytes = _snapshot_metrics(root)
        rows.append(
            {
                "calls": len(calls),
                "code": caught.value.code,
                "files": files,
                "bytes": nbytes,
                "transaction": (root / "transaction.json").exists(),
            }
        )
    assert len(calls) == 2
    assert all(not r["transaction"] for r in rows)
    assert all(r["files"] == 0 for r in rows)


def test_export_failure_clears_cache_without_test_invalidation(tmp_path, monkeypatch):
    import observe
    from chroma_readonly import open_readonly_unit_store
    from chroma_write_store import production_chroma_write_session
    from purge_locks import index_write_flock
    from ledger import build_ledger_index
    from tests.test_zz_claude_verify9 import _real_session_env
    from tests.test_zz_claude_verify15 import _obs

    cfg = _real_session_env(tmp_path, monkeypatch)
    rec = _obs("obs_cache_r4", "Original scratch observation.")
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
        raise OSError("export unavailable")

    monkeypatch.setattr(observe, "_upsert_jsonl_line", fail)
    for stage in ("insert", "update"):  # pylint: disable=unused-variable
        with index_write_flock(cfg):
            with production_chroma_write_session(entrypoint="audit.r4.cache") as session:
                with pytest.raises(OSError, match="export unavailable"):
                    observe.commit_observation_ingest(  # pylint: disable=no-member  # stale docs/chatgpt-pack observe/ledger names
                        prepared,
                        store=session.store,
                        units_export=tmp_path / "export.jsonl",
                    )
                assert rec["id"] in build_ledger_index(session.store)[0]
                doc = session.store.get_unit(prepared.existing_chroma_id or prepared.unit["id"])["document"]
                assert prepared.doc == doc
        reader = open_readonly_unit_store(cfg["index"]["chroma_dir"])
        prepared = observe.prepare_observation_ingest(  # pylint: disable=no-member  # stale docs/chatgpt-pack observe/ledger names
            {**rec, "summary": "Changed scratch observation."},
            store=reader,
            embed_model="fake",
            ollama_host="offline",
            upsert=True,
            precomputed_embedding=[0.1, 0.2, 0.3],
        )
        assert prepared.target_digest != "missing"


def test_corrupt_retry_admission_differential(tmp_path, monkeypatch):
    import incremental_jsonl as inc
    from tests.test_zz_claude_verify8b import _count_summaries
    from tests.test_zz_codex_audit import _route_fixture

    source, cfg, route = _route_fixture(tmp_path, monkeypatch)
    calls = _count_summaries(monkeypatch)

    def fail(*a, **kw):
        raise OSError("scratch prepared failure")

    monkeypatch.setattr(inc.IncrementalJsonlCoordinator, "_write_prepared", fail)
    for _ in range(3):
        with pytest.raises(inc.IncrementalJsonlError):
            route()
    assert len(calls) == 2
    state = _state_root(source, cfg) / "retry_state.json"
    corrupt = "{truncated retry evidence\n"
    state.write_text(corrupt)
    files_before, bytes_before = _snapshot_metrics(_state_root(source, cfg))
    results = []
    for _ in range(3):
        with pytest.raises(inc.IncrementalJsonlError) as caught:
            route()
        files, nbytes = _snapshot_metrics(_state_root(source, cfg))
        results.append(
            {
                "calls": len(calls),
                "code": caught.value.code,
                "state": state.read_text(),
                "files": files,
                "bytes": nbytes,
            }
        )
    assert all(r["calls"] == 2 for r in results)
    assert all(r["code"] == "retry_state_unavailable" for r in results)
    assert state.read_text() == corrupt
    assert all(r["files"] == files_before and r["bytes"] == bytes_before for r in results)


def test_repeated_calls_unavailable_state_hold_bytes_and_snapshots(tmp_path, monkeypatch):
    import incremental_jsonl as inc
    from tests.test_zz_claude_verify8b import _count_summaries, _retry_state_path
    from tests.test_zz_codex_audit import _route_fixture

    source, cfg, route = _route_fixture(tmp_path, monkeypatch)
    calls = _count_summaries(monkeypatch)

    def fail(*_a, **_k):
        raise OSError("scratch prepared failure")

    monkeypatch.setattr(inc.IncrementalJsonlCoordinator, "_write_prepared", fail)
    with pytest.raises(inc.IncrementalJsonlError):
        route()
    state = _retry_state_path(tmp_path)
    original = state.read_bytes()
    files_before, bytes_before = _snapshot_metrics(_state_root(source, cfg))
    state.chmod(0o400)
    try:
        for _ in range(3):
            before_calls = len(calls)
            with pytest.raises(inc.IncrementalJsonlError) as caught:
                route()
            assert caught.value.code == "retry_state_unavailable"
            assert len(calls) == before_calls
            assert state.read_bytes() == original
            files, nbytes = _snapshot_metrics(_state_root(source, cfg))
            assert files == files_before and nbytes == bytes_before
    finally:
        state.chmod(0o600)


def test_repeated_calls_prefix_cap_refusal_stable(tmp_path, monkeypatch):
    import incremental_jsonl as inc
    from tests.test_zz_claude_verify8b import _count_summaries
    from tests.test_zz_codex_audit import _route_fixture

    source, cfg, route = _route_fixture(tmp_path, monkeypatch)
    calls = _count_summaries(monkeypatch)
    root = _state_root(source, cfg)

    def fail(*_a, **_k):
        raise OSError("scratch prepared failure")

    monkeypatch.setattr(inc.IncrementalJsonlCoordinator, "_write_prepared", fail)
    rows = []
    for _ in range(6):
        with pytest.raises(inc.IncrementalJsonlError) as caught:
            route()
        files, nbytes = _snapshot_metrics(root)
        rows.append({"calls": len(calls), "code": caught.value.code, "files": files, "bytes": nbytes})
    assert rows[0]["calls"] <= 3
    assert all(r["calls"] == rows[2]["calls"] for r in rows[2:])
    assert all(r["code"] == "live_route_refused" for r in rows[3:])
    cap_files, cap_bytes = rows[2]["files"], rows[2]["bytes"]
    assert all(r["files"] == cap_files and r["bytes"] == cap_bytes for r in rows[3:])


def test_repeated_calls_same_code_hold_refusal_stable(tmp_path, monkeypatch):
    import incremental_jsonl as inc
    import ingest
    from tests.test_zz_claude_verify8b import _count_summaries
    from tests.test_zz_codex_audit import _route_fixture

    source, cfg, route = _route_fixture(tmp_path, monkeypatch)
    calls = _count_summaries(monkeypatch)
    root = _state_root(source, cfg)

    def fail(*_a, **_k):
        raise RuntimeError("scratch distill unavailable")

    monkeypatch.setattr(ingest, "distill", fail)
    monkeypatch.setattr(ingest, "_SYNTHESIS_FAIL_LOG", tmp_path / "synthesis_failures.jsonl")
    rows = []
    for _ in range(6):
        with pytest.raises(inc.IncrementalJsonlError) as caught:
            route()
        files, nbytes = _snapshot_metrics(root)
        rows.append({"calls": len(calls), "code": caught.value.code, "files": files, "bytes": nbytes})
    assert len(calls) == 2
    assert all(r["files"] == 0 for r in rows)
    assert all(r["code"] == "live_route_refused" for r in rows[2:])

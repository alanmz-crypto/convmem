"""Codex audit probes flipped to assert corrective-6 safe behavior (issue #286)."""

# pylint: disable=duplicate-code,protected-access

from __future__ import annotations

import json
import threading
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest


def test_add_embeds_before_index_lock(tmp_path, monkeypatch):
    import chroma_write_store as cs
    import convmem
    import llm
    from purge_locks import index_write_flock, index_write_lock_depth
    from tests.purge_test_util import purge_cfg
    from typer.testing import CliRunner

    cfg = purge_cfg(tmp_path)
    cfg["models"] = {"embed_model": "fake", "ollama_host": "http://127.0.0.1:9"}
    cfg["index"]["units_export"] = None
    depths = []
    write_store = Mock()
    write_store.chroma_dir = cfg["index"]["chroma_dir"]
    write_store.active_units_for_ledger_id.return_value = []
    write_store.get_unit.return_value = None

    @contextmanager
    def session(**kwargs):
        depths.append(("session_enter", index_write_lock_depth()))
        from tests.fake_production_write_session import counting_fake_production_write_session

        with counting_fake_production_write_session(write_store, cfg):
            yield SimpleNamespace(store=write_store, live_cfg=cfg)

    def embed(*args, **kwargs):
        depths.append(("embed", index_write_lock_depth()))
        return [0.1] * 8

    import config

    monkeypatch.setattr(convmem, "_guard_write", lambda: None)
    monkeypatch.setattr(config, "load_config", lambda *a, **k: cfg)
    monkeypatch.setattr(cs, "production_chroma_write_session", session)
    monkeypatch.setattr(llm, "ollama_embed", embed)
    result = CliRunner().invoke(
        convmem.app,
        [
            "add",
            "--title",
            "Audit example",
            "--summary",
            "A valid observation from a hermetic audit.",
            "--author",
            "audit",
            "--keyword",
            "one",
            "--keyword",
            "two",
            "--keyword",
            "three",
        ],
    )
    assert result.exit_code == 0, (result.output, result.exception)
    assert depths == [("embed", 0), ("session_enter", 1)]


def test_refine_tombstone_waits_for_index_lock(tmp_path, monkeypatch):
    import refine
    from purge_locks import index_write_flock, index_write_lock_depth
    from tests.purge_test_util import purge_cfg

    cfg = purge_cfg(tmp_path)
    import config

    monkeypatch.setattr(config, "CONFIG_PATH", tmp_path / "config.toml")
    monkeypatch.setattr(config, "load_config", lambda *a, **k: cfg)
    store = Mock()
    store.chroma_dir = cfg["index"]["chroma_dir"]
    store.get_unit.side_effect = lambda uid: {"id": uid, "metadata": {"id": uid}}
    writes = []
    store.update_unit_metadata.side_effect = lambda *args: writes.append(
        index_write_lock_depth()
    )
    monkeypatch.setattr(refine, "write_undo_snapshot", lambda *args: None)
    monkeypatch.setattr(refine, "invalidate_superseded_cache", lambda *args: None)

    @contextmanager
    def _scope(_cfg):
        with index_write_flock(cfg):
            yield store, cfg

    monkeypatch.setattr(refine, "_refine_write_scope", _scope)
    done = threading.Event()
    errors = []

    def contender():
        try:
            refine._tombstone_semantic_duplicate(
                store, cfg, tombstone_id="a", canonical_id="b", verbose=False
            )
        except BaseException as exc:
            errors.append(exc)
        finally:
            done.set()

    worker = threading.Thread(target=contender)
    with index_write_flock(cfg):
        worker.start()
        completed_while_locked = done.wait(0.05)
        assert not completed_while_locked
    worker.join(2)
    assert not errors, errors
    assert writes == [1]


def test_claude_is_not_deferred_under_broad_watch_root(tmp_path, monkeypatch):
    import watch
    from adapters.detect import detect_format

    monkeypatch.setenv("HOME", str(tmp_path))
    source = tmp_path / ".claude/projects/project/session.jsonl"
    source.parent.mkdir(parents=True)
    source.write_text(
        json.dumps(
            {
                "sessionId": "audit-session",
                "type": "user",
                "message": {"role": "user", "content": "test"},
            }
        )
        + "\n"
    )
    monkeypatch.setattr(watch, "_processed_cache", {})
    monkeypatch.setattr(watch, "_is_live_watch_pid", lambda pid: True)
    lock = tmp_path / "watch.lock"
    lock.write_text("999999\n")
    cfg = {"watch": {"paths": [str(tmp_path)], "lock_file": str(lock)}}
    assert detect_format(str(source)) == "jsonl_claude_session"
    assert watch.is_watchable(source)
    assert not watch.should_defer_index_file(cfg, str(source))


def test_tracked_review_bundle_writer_is_scanned(tmp_path, monkeypatch):
    from eval_corpus.r2b_v2.coverage import inventory

    bundle = tmp_path / "review-bundles/production_writer.py"
    bundle.parent.mkdir(parents=True)
    bundle.write_text(
        "from chroma_store import ChromaStore\n"
        'store = ChromaStore("~/.local/share/convmem/chroma")\n'
    )
    manifest = tmp_path / "shadow.json"
    manifest.write_text('{"allowlisted_direct_sites": []}')
    monkeypatch.setattr(inventory, "ROOT", tmp_path)
    monkeypatch.setattr(inventory, "SHADOW_INVENTORY", manifest)
    monkeypatch.setattr(
        inventory,
        "_skip_repo_scan_path",
        lambda rel: rel.startswith("tests/"),
    )
    assert inventory._scan_chroma_ctor_uncached() == [
        "review-bundles/production_writer.py:2"
    ]


def test_lock_guard_rejects_index_then_source(tmp_path):
    from purge_locks import index_write_flock, source_flock
    from tests.purge_test_util import purge_cfg

    cfg = purge_cfg(tmp_path)
    with pytest.raises(RuntimeError, match="index write lock"):
        with index_write_flock(cfg):
            with source_flock(cfg, "/audit/source"):
                pass


def test_rollback_preserves_foreign_dedupe(tmp_path, monkeypatch):
    from ingest_dedupe import IngestDedupeResult, persist_ingest_dedupe
    from tests.test_issue_286_stage2_wedge_probes import _wedge_then_replay

    replay, export, foreign, source = _wedge_then_replay(
        tmp_path, monkeypatch, "before_summary_upsert"
    )
    persist_ingest_dedupe(
        replay.cfg,
        IngestDedupeResult(
            exact_suppressions=[
                {
                    "event_id": "foreign-event",
                    "source_path": "/other",
                    "suppressed_id": "foreign-a",
                    "matched_id": "foreign-b",
                }
            ],
            semantic_candidates=[
                {"id_a": "foreign-a", "id_b": "foreign-b", "status": "pending"}
            ],
        ),
    )
    paths = replay._dedupe_restore_paths()
    assert all(p.exists() and p.read_bytes() for p in paths.values())
    result = replay.run()
    assert result.outcome == "rolled_back"
    assert all(p.exists() and p.read_bytes() for p in paths.values())
    assert foreign.encode() in export.read_bytes()


def test_wedge_digest_failure_keeps_hold(tmp_path):
    from watch_circuit_breaker import CircuitBreakerState

    breaker = CircuitBreakerState(tmp_path / "breaker.json")
    breaker.record_refusal(
        "/audit/source",
        outcome="wedged_incremental_transaction_recovery_unproven",
        prefix_digest="a" * 64,
    )
    assert breaker.should_skip_refusal_quarantine("/audit/source", "")
    assert not breaker.should_skip_refusal_quarantine("/audit/source", "b" * 64)

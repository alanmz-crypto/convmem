"""Claude verify probes for issue #286 corrective 6 (e1914f5). Scratch only.

Each test asserts the round-7 spec; a failure at e1914f5 is a finding.
"""

# pylint: disable=protected-access

from __future__ import annotations

import unittest
from contextlib import contextmanager
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
import requests


def test_guard_refuses_unlocked_supersede() -> None:
    """Q3: every production Chroma mutator raises without C1, including supersede."""
    from chroma_write_store import _IndexWriteGuardedChromaStore

    inner = Mock()
    guarded = _IndexWriteGuardedChromaStore(inner)
    with pytest.raises(RuntimeError, match="index write lock"):
        guarded.supersede_units_for_source("/audit/source", superseded_by="audit")
    inner.supersede_units_for_source.assert_not_called()


def test_repository_knowledge_retirement_holds_index_write_lock(monkeypatch) -> None:
    """Q3: the watcher's repository-knowledge retirement supersedes units under C1."""
    from chroma_store import ChromaStore
    from purge_locks import index_write_lock_depth
    from tests.test_repository_knowledge_sync import SyncRoutingTests

    depths: list[int] = []
    real = ChromaStore.supersede_units_for_source

    def spy(self, *args, **kwargs):
        depths.append(index_write_lock_depth())
        return real(self, *args, **kwargs)

    monkeypatch.setattr(ChromaStore, "supersede_units_for_source", spy)
    result = unittest.TestResult()
    SyncRoutingTests("test_retirement_requires_prior_state_and_row_manifest_identity").run(result)
    assert result.wasSuccessful(), result.errors + result.failures
    assert depths, "retirement never superseded"
    assert all(depth >= 1 for depth in depths), depths


class _Offline:
    def get(self, *args, **kwargs):
        raise requests.ConnectionError("offline")


def test_monitor_embeds_the_document_it_stores(tmp_path, monkeypatch) -> None:
    """Q4 side effect: the precomputed embedding must be of the stored document text."""
    import llm
    from chroma_store import ChromaStore
    from monitor import run_monitor

    embedded: list[str] = []

    def embed(text, model=None, host=None):
        embedded.append(text)
        return [0.1, 0.2, 0.3]

    monkeypatch.setattr(llm, "ollama_embed", embed)
    store = ChromaStore(str(tmp_path / "chroma"))
    try:
        stats = run_monitor(
            store, site="example.test", embed_model="fake", ollama_host="http://127.0.0.1:9",
            units_export=None, dry_run=False, verbose=False, session=_Offline(),
        )
        assert stats["observations"] > 0, stats
        docs = [store.get_unit(m["id"])["document"] for m in store.units_metadata()]
    finally:
        store.close()
    mismatched = [doc for doc in docs if doc not in embedded]
    assert not mismatched, {"stored": mismatched[:2], "embedded": embedded[:2]}


def test_monitor_http_probes_run_outside_index_write_lock(tmp_path, monkeypatch) -> None:
    """Q4: nothing slow under C1. The CLI must not hold C1 across monitor's HTTP probes."""
    import chroma_write_store as cs
    import config
    import convmem
    import llm
    import monitor
    from chroma_store import ChromaStore
    from purge_locks import index_write_lock_depth
    from tests.purge_test_util import purge_cfg
    from typer.testing import CliRunner

    cfg = purge_cfg(tmp_path)
    cfg["models"] = {"embed_model": "fake", "ollama_host": "http://127.0.0.1:9"}
    cfg["index"]["units_export"] = None
    depths: list[tuple[str, int]] = []

    def headers(site, *, session=None, timeout=20.0):
        depths.append(("https_fetch", index_write_lock_depth()))
        return {}, "offline"

    def tls(site, *, session=None, timeout=20.0):
        depths.append(("tls_fetch", index_write_lock_depth()))
        return False

    from tests.fake_production_write_session import counting_fake_production_write_session

    @contextmanager
    def session(**kwargs):
        store = ChromaStore(str(tmp_path / "chroma"))
        try:
            with counting_fake_production_write_session(store, cfg) as session_obj:
                yield session_obj
        finally:
            store.close()

    monkeypatch.setattr(convmem, "_guard_write", lambda: None)
    monkeypatch.setattr(config, "load_config", lambda *a, **k: cfg)
    monkeypatch.setattr(cs, "production_chroma_write_session", session)
    monkeypatch.setattr(monitor, "fetch_https_headers", headers)
    monkeypatch.setattr(monitor, "check_tls_redirect", tls)
    monkeypatch.setattr(llm, "ollama_embed", lambda *a, **k: [0.1, 0.2, 0.3])
    monkeypatch.setattr("brief.refresh_brief_after_change", lambda *a, **k: None, raising=False)
    result = CliRunner().invoke(convmem.app, ["monitor", "--site", "example.test"])
    assert depths, (result.output, result.exception)
    assert all(depth == 0 for _, depth in depths), depths

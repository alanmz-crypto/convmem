"""Claude verify probe, round 8: the incremental route through the real index() entrypoint. Scratch only."""

from __future__ import annotations

import traceback
from unittest import mock

from tests.test_zz_codex_audit import _route_fixture


def test_index_file_routes_codex_rollout_and_commits(tmp_path, monkeypatch) -> None:
    import ingest
    from tests.incremental_jsonl_helpers import fake_summarize

    import chroma_write_store
    import incremental_jsonl as inc

    source, cfg, _route = _route_fixture(tmp_path, monkeypatch)
    # Production shape: the outer index() lease and the coordinator use one writer lock.
    layout = inc.ProductionBoundary(cfg, str(source)).layout
    monkeypatch.setattr(chroma_write_store, "DEFAULT_WRITER_LOCK", layout["locks"] / "chroma_writer_gate.lock")
    calls = []

    def summarize(*args, **kwargs):
        calls.append(1)
        return fake_summarize(*args, **kwargs)

    monkeypatch.setattr(ingest, "summarize", summarize)
    err = None
    with mock.patch("ingest.load_config", return_value=cfg), mock.patch("config.load_config", return_value=cfg), \
            mock.patch("brief.refresh_brief_after_change", lambda *_a, **_k: None):
        try:
            stats = ingest.index(verbose=False, force_file=str(source))
        except Exception as exc:
            stats = None
            err = (repr(exc)[:200], [f"{f.filename.split('/')[-1]}:{f.lineno}" for f in traceback.extract_tb(exc.__traceback__)][-8:])
    assert err is None, ("summaries paid:", len(calls), err)
    assert stats["files_processed"] == 1, stats

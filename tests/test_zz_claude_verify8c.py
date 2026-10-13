"""Claude verify probe, round 8: legacy index paths through the real index() entrypoint. Scratch only."""

from __future__ import annotations

import tempfile
from pathlib import Path
from unittest import mock

import tests.test_index_limit_skip_stats as limit_stats


def _run(force_file: bool):
    calls: list[int] = []
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / "chroma").mkdir()
        (root / "processed.json").write_text("{}", encoding="utf-8")
        (root / "knowledge_units.jsonl").write_text("", encoding="utf-8")
        src = root / "agent-transcripts" / "s" / "chat.jsonl"
        src.parent.mkdir(parents=True)
        src.write_text(limit_stats._cursor_line() + "\n", encoding="utf-8")
        inv = root / "inventory.jsonl"
        limit_stats._write_inventory(inv, [str(src)])
        cfg = limit_stats.IndexLimitSkipStatsTests()._cfg(root, inv)
        unit = {"type": "explanation", "title": "T", "summary": "S", "keywords": ["k"],
                "confidence": 0.9, "domain": "coding.tooling"}
        with mock.patch("ingest.load_config", return_value=cfg), \
                mock.patch("config.load_config", return_value=cfg), \
                mock.patch("ingest.summarize", side_effect=lambda *a, **k: calls.append(1) or "summary"), \
                mock.patch("ingest.distill", return_value=[unit]), \
                mock.patch("ingest.ollama_embed", return_value=[0.1, 0.2]), \
                mock.patch("brief.refresh_brief_after_change", lambda *_a, **_k: None):
            from ingest import index

            try:
                return len(calls), index(verbose=False, force_file=str(src) if force_file else None), None
            except Exception as exc:  # report how much was paid before the failure
                return len(calls), None, repr(exc)[:160]


def test_bulk_index_commits_without_lock_error() -> None:
    calls, stats, err = _run(False)
    assert err is None, (calls, err)
    assert stats["files_processed"] == 1, stats


def test_legacy_index_file_commits_without_lock_error() -> None:
    calls, stats, err = _run(True)
    assert err is None, (calls, err)
    assert stats["files_processed"] == 1, stats

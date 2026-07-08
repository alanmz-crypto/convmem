"""Tests for convmem brief generation."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from brief import (
    _brief_row_matches_project,
    _format_age,
    _latest_handoff_info,
    _recent_inter_model_titles,
    gather_brief_data,
    render_brief_markdown,
    write_brief,
)


class BriefTests(unittest.TestCase):
    def test_render_includes_core_sections(self):
        data = {
            "generated_at": "2026-06-22T10:00:00Z",
            "units": 1028,
            "summaries": 263,
            "inventory": {"total": 122, "indexed": 121, "pending": 1, "deferred": 0},
            "tests": 72,
            "rerank": False,
            "services": {
                "watch": "disabled/inactive",
                "refine": "enabled/active",
                "monitor_timer": "enabled/active",
            },
            "kiro_db_excluded": False,
            "mcp": {
                "cursor": "registered",
                "crush": "registered",
                "crush_live": "unverified",
                "stdio": "verified",
            },
            "recent_decisions": [
                {
                    "ledger_id": "dec_test",
                    "title": "Single writer",
                    "rationale": "Concurrent writes corrupt HNSW",
                }
            ],
            "recent_monitor": [],
            "pending_decision_files": [],
            "inter_model_inbox": Path("docs/inter-model"),
            "latest_handoff": {
                "path": "docs/inter-model/LATEST.md",
                "mtime_iso": "2026-06-23T10:00:00Z",
                "age_label": "2h ago",
                "age_seconds": 7200,
                "date_label": "2026-06-23",
                "author": "Codex",
            },
            "recent_inter_model_titles": [
                "DEEPSEEK-CODEX-2026-06-23-aligned.md",
                "CODEX-2026-06-15-plot-the-course.md",
            ],
        }
        text = render_brief_markdown(data)
        self.assertIn("# CONVMEM BRIEF", text)
        self.assertIn("1028", text)
        self.assertIn("LATEST.md: updated **2h ago**", text)
        self.assertIn("Recent inter-model:", text)
        self.assertIn("DEEPSEEK-CODEX-2026-06-23-aligned.md", text)
        self.assertIn("## Active P0", text)
        self.assertIn("Kiro sqlite exclude", text)
        self.assertIn("dec_test", text)
        self.assertIn("## Before Working", text)
        self.assertIn("AGENT-ROLES", text)

    def _min_data(self) -> dict:
        return {
            "generated_at": "2026-07-07T10:00:00Z",
            "units": 10,
            "summaries": 5,
            "inventory": {"total": 1, "indexed": 1, "pending": 0, "deferred": 0},
            "tests": 47,
            "rerank": False,
            "services": {"watch": "enabled/active", "refine": "enabled/active",
                         "monitor_timer": "enabled/active"},
            "kiro_db_excluded": True,
            "mcp": {"cursor": "registered", "crush": "registered",
                    "crush_live": "verified", "stdio": "verified"},
        }

    def test_standing_due_silent_when_none(self):
        data = self._min_data()
        data["standing_due"] = {"open": 12, "due": []}
        text = render_brief_markdown(data)
        self.assertNotIn("STANDING CHECKS DUE", text)

    def test_standing_due_absent_is_silent(self):
        text = render_brief_markdown(self._min_data())
        self.assertNotIn("STANDING CHECKS DUE", text)

    def test_standing_due_renders_when_due(self):
        data = self._min_data()
        data["standing_due"] = {"open": 12, "due": [
            {"id": "ksweep-sunset", "detail": "manual: 120d since verified (limit 90d)"},
        ]}
        text = render_brief_markdown(data)
        self.assertIn("STANDING CHECKS DUE (1)", text)
        self.assertIn("ksweep-sunset", text)
        self.assertIn("convmem doctor", text)

    def test_write_brief_creates_file(self):
        with tempfile.TemporaryDirectory() as td:
            cfg = {
                "index": {"chroma_dir": td, "processed_log": str(Path(td) / "processed.json")},
                "sources": {"inventory": str(Path(td) / "inventory.jsonl")},
                "query": {"rerank": False},
            }
            Path(cfg["index"]["processed_log"]).write_text("{}")
            Path(cfg["sources"]["inventory"]).write_text("")
            out = Path(td) / "brief.md"
            with patch("brief.collection_count", side_effect=[10, 5]), patch(
                "brief.collection_metadata_rows", return_value=[]
            ):
                write_brief(cfg, out_path=out, quiet=True)
            self.assertTrue(out.is_file())
            self.assertIn("CONVMEM BRIEF", out.read_text(encoding="utf-8"))

    def test_kiro_excluded_detected(self):
        with tempfile.TemporaryDirectory() as td:
            kiro = Path(td) / "data.sqlite3"
            kiro.write_text("x")
            proc = Path(td) / "processed.json"
            proc.write_text(
                json.dumps(
                    {
                        "abc": {
                            "path": str(kiro.resolve()),
                            "excluded": True,
                            "exclude_reason": "live db",
                        }
                    }
                )
            )
            cfg = {
                "index": {"chroma_dir": td, "processed_log": str(proc)},
                "sources": {"inventory": str(Path(td) / "inventory.jsonl")},
                "query": {},
            }
            Path(cfg["sources"]["inventory"]).write_text("")
            with patch("brief.KIRO_DB", kiro), patch(
                "brief.collection_count", side_effect=[1, 1]
            ), patch("brief.collection_metadata_rows", return_value=[]):
                data = gather_brief_data(cfg)
            self.assertTrue(data["kiro_db_excluded"])

    def test_format_age(self):
        self.assertEqual(_format_age(30), "just now")
        self.assertEqual(_format_age(120), "2m ago")
        self.assertEqual(_format_age(7200), "2h ago")
        self.assertEqual(_format_age(90000), "1d ago")

    def test_latest_handoff_parses_updated_line(self):
        with tempfile.TemporaryDirectory() as td:
            inbox = Path(td)
            latest = inbox / "LATEST.md"
            latest.write_text(
                "# Latest\n\n**Updated:** 2026-06-23 by Codex\n",
                encoding="utf-8",
            )
            info = _latest_handoff_info(inbox)
            self.assertIsNotNone(info)
            assert info is not None
            self.assertEqual(info["author"], "Codex")
            self.assertEqual(info["date_label"], "2026-06-23")
            self.assertTrue(info["age_label"])

    def test_recent_inter_model_titles_skips_pointer(self):
        with tempfile.TemporaryDirectory() as td:
            inbox = Path(td)
            (inbox / "README.md").write_text("x", encoding="utf-8")
            (inbox / "LATEST.md").write_text("x", encoding="utf-8")
            (inbox / "A-note.md").write_text("x", encoding="utf-8")
            (inbox / "B-note.md").write_text("x", encoding="utf-8")
            titles = _recent_inter_model_titles(inbox, limit=2)
            self.assertEqual(len(titles), 2)
            self.assertNotIn("LATEST.md", titles)
            self.assertNotIn("README.md", titles)

    def test_handoff_staleness_when_newer_file_exists(self):
        from brief import _handoff_staleness
        import os
        import time

        with tempfile.TemporaryDirectory() as td:
            inbox = Path(td)
            latest = inbox / "LATEST.md"
            latest.write_text("# LATEST\n", encoding="utf-8")
            newer = inbox / "NEWER.md"
            newer.write_text("# newer\n", encoding="utf-8")
            os.utime(latest, (time.time() - 10, time.time() - 10))
            os.utime(newer, (time.time(), time.time()))
            stale = _handoff_staleness(inbox)
            self.assertIsNotNone(stale)
            assert stale is not None
            self.assertTrue(stale["stale"])
            self.assertEqual(stale["newest_file"], "NEWER.md")

    def test_render_stale_handoff_warning(self):
        data = {
            "generated_at": "2026-06-23T10:00:00Z",
            "units": 1,
            "summaries": 1,
            "inventory": {"total": 1, "indexed": 1, "pending": 0, "deferred": 0},
            "tests": None,
            "rerank": False,
            "services": {"watch": "enabled/active", "refine": "enabled/active", "monitor_timer": "enabled/active"},
            "kiro_db_excluded": True,
            "mcp": {"cursor": "registered", "crush": "registered", "crush_live": "unverified", "stdio": "x"},
            "watch_memory_kb": None,
            "latest_handoff": None,
            "handoff_staleness": {"stale": True, "newest_file": "X.md", "newest_age_label": "5m ago"},
            "recent_inter_model_titles": [],
            "recent_decisions": [],
            "recent_monitor": [],
            "pending_decision_files": [],
            "inter_model_inbox": Path("docs/inter-model"),
        }
        text = render_brief_markdown(data)
        self.assertIn("STALE HANDOFF", text)
        self.assertIn("brief @", text)

    def test_brief_row_matches_project_by_slug(self):
        row = {"title": "pavlomassage-practice stack on :8082", "document": ""}
        self.assertTrue(_brief_row_matches_project(row, "pavlomassage-practice"))
        self.assertFalse(_brief_row_matches_project(row, "willowyhollow-dev"))

    def test_brief_row_matches_project_rejects_unrelated(self):
        row = {
            "title": "Arch Linux system health prompt matrix",
            "document": "pacman configuration boot entries",
        }
        self.assertFalse(_brief_row_matches_project(row, "pavlomassage-practice"))

    @patch("brief._kiro_excluded", return_value=True)
    @patch("brief._mcp_registration", return_value={})
    @patch("brief._watch_process_memory", return_value=None)
    @patch("brief._systemd_state", return_value="enabled/active")
    @patch("brief._recent_decisions")
    @patch("brief._recent_monitor_units")
    @patch("brief.gather_project_activity", return_value=[{"slug": "pavlomassage-practice"}])
    @patch("brief.collection_count", return_value=1)
    @patch("brief._coverage_counts", return_value=(1, 1, 0, 0))
    @patch("brief.load_config")
    def test_gather_brief_data_filters_decisions_when_project_set(
        self,
        mock_load,
        _cov,
        _count,
        _proj,
        mock_monitor,
        mock_decisions,
        _sysd,
        _watch,
        _mcp,
        _kiro,
    ):
        mock_load.return_value = {
            "index": {"chroma_dir": "/tmp/x", "processed_log": "/tmp/p.json"},
            "query": {},
        }
        mock_decisions.return_value = [
            {"title": "Arch Linux runbook", "document": "pacman"},
            {"title": "pavlomassage-practice docker stack", "document": "8082"},
        ]
        mock_monitor.return_value = [
            {"site": "staging2.willowyhollow.com", "title": "TLS check"},
        ]
        data = gather_brief_data(project="pavlomassage-practice")
        self.assertEqual(data["brief_scope"], "project")
        self.assertEqual(len(data["recent_decisions"]), 1)
        self.assertIn("pavlomassage", data["recent_decisions"][0]["title"])
        self.assertEqual(data["recent_monitor"], [])
        self.assertIn("answer_from", data)


if __name__ == "__main__":
    unittest.main()

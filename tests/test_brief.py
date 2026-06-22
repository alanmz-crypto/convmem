"""Tests for convmem brief generation."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from brief import gather_brief_data, render_brief_markdown, write_brief


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
        }
        text = render_brief_markdown(data)
        self.assertIn("# CONVMEM BRIEF", text)
        self.assertIn("1028", text)
        self.assertIn("## Active P0", text)
        self.assertIn("Kiro sqlite exclude", text)
        self.assertIn("dec_test", text)
        self.assertIn("## Before Working", text)
        self.assertIn("AGENT-ROLES", text)

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


if __name__ == "__main__":
    unittest.main()

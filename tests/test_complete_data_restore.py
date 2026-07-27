"""Tests for complete_data_restore.py — inventory, classification, and reports."""

from __future__ import annotations

import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

import sys
REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from complete_data_restore import (  # noqa: E402
    EXIT_BLOCKED,
    EXIT_INTERNAL_FAILURE,
    EXIT_REPAIRABLE_DRIFT,
    EXIT_VALID,
    RestoreReport,
    StateClassification,
    inventory_restored_state,
)


class TestRestoreReport(unittest.TestCase):
    def test_report_written_and_finalized(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "reports" / "restore-test.json"
            report = RestoreReport(path)
            report.step("resolve_snapshot", "PASS", "id=abc")
            report.step("classify:chroma", "VALID", "ok")
            report.finalize("VALID", "all good", exit_code=0)
            data = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(data["meta"]["status"], "VALID")
            self.assertEqual(data["meta"]["exit_code"], 0)
            self.assertTrue(path.with_suffix(".md").is_file())

    def test_md_report_contains_steps(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "reports" / "test.json"
            report = RestoreReport(path)
            report.step("step1", "PASS", "detail here")
            report.finalize("BLOCKED", "bad", exit_code=31)
            md = path.with_suffix(".md").read_text(encoding="utf-8")
            self.assertIn("step1", md)
            self.assertIn("BLOCKED", md)


class TestStateClassification(unittest.TestCase):
    def test_dataclass_fields(self):
        c = StateClassification("chroma/", "authoritative", "VALID", "ok")
        self.assertEqual(c.path_hint, "chroma/")
        self.assertEqual(c.authority, "authoritative")
        self.assertEqual(c.classification, "VALID")


class TestInventoryRestoredState(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.root = Path(self.td.name)

    def tearDown(self):
        self.td.cleanup()

    def _make_chroma_db(self, root: Path) -> Path:
        chroma = root / "chroma"
        chroma.mkdir()
        db = chroma / "chroma.sqlite3"
        conn = sqlite3.connect(str(db))
        conn.execute("CREATE TABLE collections (id TEXT PRIMARY KEY, name TEXT)")
        conn.execute("CREATE TABLE embeddings (id TEXT, segment_id TEXT, embedding_id TEXT)")
        conn.execute("CREATE TABLE segments (id TEXT, collection TEXT, scope TEXT)")
        conn.execute("CREATE TABLE embedding_queue (seq_id INTEGER)")
        conn.execute("CREATE TABLE embedding_metadata (key TEXT, value TEXT)")
        conn.execute("CREATE TABLE tenants (id TEXT)")
        conn.execute("CREATE TABLE databases (id TEXT, name TEXT)")
        conn.execute("INSERT INTO collections VALUES ('c1', 'knowledge_units')")
        conn.execute("INSERT INTO embeddings VALUES ('e1', 's1', 'emb1')")
        conn.commit()
        conn.close()
        return db

    def _make_approved_decisions(self, root: Path):
        rec = {
            "ledger_id": "dec_test_001",
            "ledger_kind": "decision",
            "title": "Test decision",
            "rationale": "test",
            "domain": "testing",
            "confidence": 1.0,
        }
        (root / "decisions-approved.jsonl").write_text(json.dumps(rec) + "\n", encoding="utf-8")

    def test_valid_restored_state(self):
        self._make_chroma_db(self.root)
        self._make_approved_decisions(self.root)
        (self.root / "pending_decisions.jsonl").write_text("", encoding="utf-8")

        result = inventory_restored_state(self.root, self.root)
        self.assertIn(result.overall, ("VALID", "VALID_WITH_REPAIRABLE_DERIVED_DRIFT"))
        self.assertIn(result.exit_code, (EXIT_VALID, EXIT_REPAIRABLE_DRIFT))

    def test_missing_chroma_blocks(self):
        self._make_approved_decisions(self.root)
        result = inventory_restored_state(self.root, self.root)
        self.assertEqual(result.overall, "BLOCKED")
        self.assertEqual(result.exit_code, EXIT_BLOCKED)

    def test_missing_approved_decisions_blocks(self):
        self._make_chroma_db(self.root)
        result = inventory_restored_state(self.root, self.root)
        self.assertEqual(result.overall, "BLOCKED")
        self.assertEqual(result.exit_code, EXIT_BLOCKED)

    def test_unknown_top_level_state_blocks(self):
        self._make_chroma_db(self.root)
        self._make_approved_decisions(self.root)
        (self.root / "unknown_state_dir").mkdir()
        result = inventory_restored_state(self.root, self.root)
        self.assertEqual(result.overall, "BLOCKED")
        self.assertEqual(result.exit_code, EXIT_BLOCKED)

    def test_scratch_dirs_are_valid(self):
        self._make_chroma_db(self.root)
        self._make_approved_decisions(self.root)
        (self.root / "worktrees").mkdir()
        (self.root / "locks").mkdir()
        result = inventory_restored_state(self.root, self.root)
        self.assertNotEqual(result.overall, "BLOCKED")

    def test_shadow_disabled_is_valid(self):
        self._make_chroma_db(self.root)
        self._make_approved_decisions(self.root)
        # No shadow files at all
        result = inventory_restored_state(self.root, self.root)
        self.assertNotEqual(result.overall, "BLOCKED")
        has_shadow = any("shadow" in c.path_hint.lower() for c in result.classifications)
        self.assertTrue(has_shadow)

    def test_shadow_inactive_is_advisory(self):
        self._make_chroma_db(self.root)
        self._make_approved_decisions(self.root)
        manifest = {"active": False, "identity": "test"}
        (self.root / "shadow_activation_manifest.json").write_text(json.dumps(manifest))
        (self.root / "shadow_ledger.jsonl").write_text("{}", encoding="utf-8")
        result = inventory_restored_state(self.root, self.root)
        self.assertNotEqual(result.overall, "BLOCKED")

    def test_broken_chroma_db_is_blocked(self):
        self._make_approved_decisions(self.root)
        chroma = self.root / "chroma"
        chroma.mkdir()
        (chroma / "chroma.sqlite3").write_text("not a database", encoding="utf-8")
        result = inventory_restored_state(self.root, self.root)
        self.assertEqual(result.overall, "BLOCKED")

    def test_malformed_approved_jsonl_is_blocked(self):
        self._make_chroma_db(self.root)
        (self.root / "decisions-approved.jsonl").write_text("not json", encoding="utf-8")
        result = inventory_restored_state(self.root, self.root)
        self.assertEqual(result.overall, "BLOCKED")

    def test_empty_restored_root_is_blocked(self):
        result = inventory_restored_state(self.root, self.root)
        self.assertEqual(result.overall, "BLOCKED")

    def test_repairable_drift_detected(self):
        self._make_chroma_db(self.root)
        self._make_approved_decisions(self.root)
        # knowledge_units.jsonl missing -> REPAIRABLE
        result = inventory_restored_state(self.root, self.root)
        has_repairable = any(c.classification == "REPAIRABLE" for c in result.classifications)
        self.assertTrue(has_repairable)


if __name__ == "__main__":
    unittest.main()

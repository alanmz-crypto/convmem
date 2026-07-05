"""Tests for ledger_recent and ask recent-decision injection."""

from __future__ import annotations

import unittest

from ask import _prepend_recent_decisions
from ledger_recent import decision_record_to_unit, load_recent_decisions


class LedgerRecentTests(unittest.TestCase):
    def test_load_recent_decisions_filters_by_age(self):
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "decisions-approved.jsonl"
            path.write_text(
                '{"id":"dec_prop_old","timestamp":"2020-01-01T00:00:00Z","summary":"old"}\n'
                '{"id":"dec_prop_new","timestamp":"2099-06-01T12:00:00Z","summary":"new"}\n',
                encoding="utf-8",
            )
            rows = load_recent_decisions(path, days=7, limit=10)
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["id"], "dec_prop_new")

    def test_decision_record_to_unit_shape(self):
        unit = decision_record_to_unit(
            {
                "id": "dec_prop_test",
                "summary": "Ship feature",
                "rationale": "Because tests",
                "timestamp": "2026-07-01T00:00:00Z",
                "author": "ryan",
            }
        )
        self.assertEqual(unit["metadata"]["ledger_id"], "dec_prop_test")
        self.assertIn("Ship feature", unit["document"])


class AskRecentPrependTests(unittest.TestCase):
    def test_prepend_recent_before_semantic(self):
        semantic = [
            {"metadata": {"ledger_id": "obs_a"}, "score": 0.9},
            {"metadata": {"ledger_id": "obs_b"}, "score": 0.8},
        ]
        recent = [{"id": "dec_prop_new", "summary": "fresh", "timestamp": "2099-01-01T00:00:00Z"}]
        out = _prepend_recent_decisions(semantic, recent, total_limit=3)
        self.assertEqual(out[0]["metadata"]["ledger_id"], "dec_prop_new")
        self.assertEqual(len(out), 3)

    def test_prepend_dedupes_semantic_duplicate(self):
        semantic = [
            {"metadata": {"ledger_id": "dec_prop_new"}, "score": 0.5},
            {"metadata": {"ledger_id": "obs_b"}, "score": 0.8},
        ]
        recent = [{"id": "dec_prop_new", "summary": "fresh"}]
        out = _prepend_recent_decisions(semantic, recent, total_limit=2)
        ids = [(u.get("metadata") or {}).get("ledger_id") for u in out]
        self.assertEqual(ids.count("dec_prop_new"), 1)


if __name__ == "__main__":
    unittest.main()

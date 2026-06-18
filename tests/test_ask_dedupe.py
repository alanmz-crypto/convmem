"""Tests for ask-layer deduplication."""

from __future__ import annotations

import unittest

from ask import _dedupe_results_by_ledger_id


class AskDedupeTests(unittest.TestCase):
    def test_dedupe_twins_same_ledger_id(self):
        results = [
            {"id": "a", "rank_score": 0.76, "metadata": {"ledger_id": "obs001"}},
            {"id": "b", "rank_score": 0.70, "metadata": {"ledger_id": "obs001"}},
            {"id": "c", "score": 0.55, "metadata": {"ledger_id": "obs002"}},
        ]
        out = _dedupe_results_by_ledger_id(results)
        self.assertEqual([r["id"] for r in out], ["a", "c"])

    def test_legacy_units_without_ledger_id_kept(self):
        results = [
            {"id": "x", "metadata": {"title": "chat chunk"}},
            {"id": "y", "metadata": {"title": "other chunk"}},
        ]
        self.assertEqual(len(_dedupe_results_by_ledger_id(results)), 2)


if __name__ == "__main__":
    unittest.main()

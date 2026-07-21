"""Tests for ask-layer deduplication."""

from __future__ import annotations

import unittest

from ask import _dedupe_results_by_ledger_id, _filter_superseded_decisions
from query_result_filters import dedupe_results_by_ledger_id, filter_superseded_decisions


class AskDedupeTests(unittest.TestCase):
    def test_query_and_ask_helpers_match(self):
        """Ask wrappers must stay thin aliases of the shared query helpers."""
        results = [
            {
                "id": "child",
                "metadata": {
                    "ledger_id": "dec_child",
                    "ledger_kind": "decision",
                    "relates_to": "dec_parent",
                },
            },
            {
                "id": "parent",
                "metadata": {
                    "ledger_id": "dec_parent",
                    "ledger_kind": "decision",
                    "relates_to": "obs_x",
                },
            },
        ]
        self.assertEqual(
            [r["id"] for r in _filter_superseded_decisions(results)],
            [r["id"] for r in filter_superseded_decisions(results)],
        )
        twins = [
            {"id": "a", "metadata": {"ledger_id": "obs001"}},
            {"id": "b", "metadata": {"ledger_id": "obs001"}},
        ]
        self.assertEqual(
            [r["id"] for r in _dedupe_results_by_ledger_id(twins)],
            [r["id"] for r in dedupe_results_by_ledger_id(twins)],
        )

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

    def test_filter_superseded_parent_decision(self):
        child = {
            "id": "child",
            "metadata": {
                "ledger_id": "dec_prop_20260623_153615_a66c",
                "ledger_kind": "decision",
                "relates_to": "dec_prop_20260622_234011_d1ba",
            },
        }
        parent = {
            "id": "parent",
            "metadata": {
                "ledger_id": "dec_prop_20260622_234011_d1ba",
                "ledger_kind": "decision",
                "relates_to": "obs_staging2_monitor_csp-missing",
            },
        }
        out = _filter_superseded_decisions([child, parent])
        self.assertEqual([r["id"] for r in out], ["child"])

    def test_filter_keeps_unrelated_decisions(self):
        results = [
            {
                "id": "a",
                "metadata": {
                    "ledger_id": "dec_a",
                    "ledger_kind": "decision",
                    "relates_to": "obs_x",
                },
            },
            {
                "id": "b",
                "metadata": {
                    "ledger_id": "dec_b",
                    "ledger_kind": "decision",
                    "relates_to": "obs_y",
                },
            },
        ]
        self.assertEqual(len(_filter_superseded_decisions(results)), 2)


if __name__ == "__main__":
    unittest.main()

"""P1.1: search path applies decision-supersede + ledger dedupe (ask parity)."""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from query import query_units
from query_result_filters import (
    dedupe_results_by_ledger_id,
    filter_superseded_decisions,
)


class SearchPathFilterHelpersTests(unittest.TestCase):
    def test_filter_and_dedupe_helpers(self):
        child = {
            "id": "child",
            "metadata": {
                "ledger_id": "dec_child",
                "ledger_kind": "decision",
                "relates_to": "dec_parent",
            },
        }
        parent = {
            "id": "parent",
            "metadata": {
                "ledger_id": "dec_parent",
                "ledger_kind": "decision",
                "relates_to": "obs_x",
            },
        }
        twin = {
            "id": "twin",
            "metadata": {"ledger_id": "dec_child", "ledger_kind": "decision"},
        }
        filtered = filter_superseded_decisions([child, parent, twin])
        self.assertEqual([r["id"] for r in filtered], ["child", "twin"])
        deduped = dedupe_results_by_ledger_id(filtered)
        self.assertEqual([r["id"] for r in deduped], ["child"])


class QueryUnitsSearchHardenTests(unittest.TestCase):
    @patch("query._ledger_lookup_hits", return_value=[])
    @patch("query.open_chroma_for_read")
    @patch("query.ollama_embed", return_value=[0.1, 0.2])
    @patch("query.load_config")
    @patch(
        "rerank.rerank",
        side_effect=lambda _query, candidates, _model, top_k: candidates[:top_k],
    )
    def test_query_units_drops_superseded_parent_decision(
        self, _rerank, mock_cfg, _embed, mock_open, _lookup
    ):
        mock_cfg.return_value = {
            "models": {
                "embed_model": "nomic-embed-text",
                "ollama_host": "http://x",
                "rerank_model": "x",
            },
            "index": {"chroma_dir": "/tmp/chroma"},
            "query": {"rerank": False, "recency_weight": 0.0, "top_k_candidates": 20},
        }
        store = MagicMock()
        store.query_units.return_value = [
            {
                "id": "child",
                "distance": 0.1,
                "metadata": {
                    "ledger_id": "dec_child",
                    "ledger_kind": "decision",
                    "relates_to": "dec_parent",
                    "title": "child decision",
                },
                "document": "child",
            },
            {
                "id": "parent",
                "distance": 0.15,
                "metadata": {
                    "ledger_id": "dec_parent",
                    "ledger_kind": "decision",
                    "relates_to": "obs_x",
                    "title": "parent decision",
                },
                "document": "parent",
            },
            {
                "id": "chat",
                "distance": 0.2,
                "metadata": {"title": "chat chunk"},
                "document": "chat",
            },
        ]
        mock_open.return_value = store

        out = query_units("decision about parent", top_k=5)
        ids = [r["id"] for r in out]
        self.assertIn("child", ids)
        self.assertIn("chat", ids)
        self.assertNotIn("parent", ids)


if __name__ == "__main__":
    unittest.main()

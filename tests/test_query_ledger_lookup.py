"""Ledger id lookup + protocol anchor injection in query_units."""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from ledger_recent import (
    PROTOCOL_FALLBACK_LEDGER_ID,
    is_protocol_anchor_query,
    load_approved_decision_by_id,
)
from query import (
    _extract_ledger_ids,
    _merge_priority_hits,
    query_units,
)


class LedgerLookupHelpersTests(unittest.TestCase):
    def test_extract_ledger_ids(self):
        ids = _extract_ledger_ids(
            "see dec_prop_20260623_161428_c311 and obs_staging2_monitor_csp-missing"
        )
        self.assertEqual(
            ids,
            ["dec_prop_20260623_161428_c311", "obs_staging2_monitor_csp-missing"],
        )

    def test_protocol_anchor_query(self):
        self.assertTrue(is_protocol_anchor_query("convmem record relates-to fallback root"))
        self.assertTrue(is_protocol_anchor_query("convmem protocol root fallback relates-to"))
        self.assertFalse(is_protocol_anchor_query("staging2 nginx config"))

    def test_merge_priority_prepends_extras(self):
        primary = [{"id": "a", "metadata": {}, "score": 0.9}]
        extra = [
            {
                "id": "b",
                "metadata": {"ledger_id": PROTOCOL_FALLBACK_LEDGER_ID},
                "score": 0.99,
            }
        ]
        merged = _merge_priority_hits(primary, extra)
        self.assertEqual(merged[0]["metadata"]["ledger_id"], PROTOCOL_FALLBACK_LEDGER_ID)


class QueryUnitsLedgerLookupTests(unittest.TestCase):
    @patch("query._ledger_lookup_hits")
    @patch("query.open_chroma_for_read")
    @patch("query.ollama_embed", return_value=[0.1, 0.2])
    @patch("query.load_config")
    @patch(
        "rerank.rerank",
        side_effect=lambda _query, candidates, _model, top_k: candidates[:top_k],
    )
    def test_protocol_anchor_query_returns_c311(
        self, _rerank, mock_cfg, _embed, mock_open, mock_lookup
    ):
        mock_cfg.return_value = {
            "models": {"embed_model": "nomic-embed-text", "ollama_host": "http://x"},
            "index": {"chroma_dir": "/tmp/chroma"},
            "query": {"rerank": False, "recency_weight": 0.0},
        }
        store = MagicMock()
        store.query_units.return_value = [
            {
                "id": "chat1",
                "distance": 0.2,
                "metadata": {"title": "relates-to must be ledger id"},
                "document": "chat chunk",
            }
        ]
        mock_open.return_value = store
        mock_lookup.return_value = [
            {
                "id": "anchor",
                "metadata": {"ledger_id": PROTOCOL_FALLBACK_LEDGER_ID},
                "document": "protocol",
                "score": 0.98,
                "ledger_lookup": True,
            }
        ]

        results = query_units("convmem record relates-to fallback root", top_k=5)

        self.assertEqual(
            results[0]["metadata"]["ledger_id"],
            PROTOCOL_FALLBACK_LEDGER_ID,
        )
        self.assertTrue(results[0].get("ledger_lookup"))

    @patch("ledger.find_unit_by_ledger_id")
    @patch("query.open_chroma_for_read")
    @patch("query.ollama_embed", return_value=[0.1, 0.2])
    @patch("query.load_config")
    def test_explicit_ledger_id_in_query(
        self, mock_cfg, _embed, mock_open, mock_find
    ):
        mock_cfg.return_value = {
            "models": {"embed_model": "nomic-embed-text", "ollama_host": "http://x"},
            "index": {"chroma_dir": "/tmp/chroma"},
            "query": {"rerank": False, "recency_weight": 0.0},
        }
        store = MagicMock()
        store.query_units.return_value = []
        mock_open.return_value = store
        mock_find.return_value = {
            "id": "u1",
            "document": "coordination protocol steps",
            "metadata": {"ledger_id": PROTOCOL_FALLBACK_LEDGER_ID, "title": "proto"},
        }

        results = query_units(f"details for {PROTOCOL_FALLBACK_LEDGER_ID}", top_k=3)

        self.assertEqual(results[0]["metadata"]["ledger_id"], PROTOCOL_FALLBACK_LEDGER_ID)


class ApprovedDecisionLoadTests(unittest.TestCase):
    def test_load_c311_from_approved_if_present(self):
        from config import load_config

        cfg = load_config()
        rec = load_approved_decision_by_id(cfg, PROTOCOL_FALLBACK_LEDGER_ID)
        if rec is None:
            self.skipTest("c311 not in local decisions-approved.jsonl")
        self.assertEqual(rec.get("id"), PROTOCOL_FALLBACK_LEDGER_ID)
        self.assertIn("protocol", (rec.get("summary") or "").lower())


if __name__ == "__main__":
    unittest.main()

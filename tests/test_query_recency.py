"""query_units recency rerank wiring (Manning P1a)."""

from __future__ import annotations

import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

from query import query_units


class QueryRecencyTests(unittest.TestCase):
    @patch("query.open_chroma_for_read")
    @patch("query.ollama_embed", return_value=[0.1, 0.2])
    @patch("query.load_config")
    @patch(
        "rerank.rerank",
        side_effect=lambda _query, candidates, _model, top_k: candidates[:top_k],
    )
    def test_query_units_applies_recency_when_configured(
        self, _rerank, mock_cfg, _embed, mock_open
    ):
        recent_ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        old_ts = (datetime.now(timezone.utc) - timedelta(days=365)).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        )
        mock_cfg.return_value = {
            "models": {"embed_model": "nomic-embed-text", "ollama_host": "http://x"},
            "index": {"chroma_dir": "/tmp/chroma"},
            "query": {"rerank": False, "recency_weight": 0.2, "recency_half_life_days": 30},
        }
        store = MagicMock()
        store.query_units.return_value = [
            {"id": "old", "distance": 0.15, "metadata": {"timestamp": old_ts}, "document": "old"},
            {"id": "new", "distance": 0.15, "metadata": {"timestamp": recent_ts}, "document": "new"},
        ]
        mock_open.return_value = store

        results = query_units("test query", top_k=2)

        self.assertEqual(results[0]["id"], "new")
        self.assertGreater(results[0]["recency_boost"], 0)


if __name__ == "__main__":
    unittest.main()

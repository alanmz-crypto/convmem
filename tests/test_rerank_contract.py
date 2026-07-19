"""Mandatory CrossEncoder reranking and score contract."""

import unittest
from unittest.mock import MagicMock, patch

from query import QueryUnitTrace, query_units
from rerank import rerank


class RerankScoreTests(unittest.TestCase):
    @patch("rerank.get_model")
    def test_rerank_attaches_scores_and_ranks(self, mock_get_model):
        model = MagicMock()
        model.predict.return_value = [-1.0, 2.0]
        mock_get_model.return_value = model
        candidates = [
            {"id": "a", "document": "A", "score": 0.9},
            {"id": "b", "document": "B", "score": 0.8},
        ]

        results = rerank("query", candidates, "model", top_k=2)

        self.assertEqual([row["id"] for row in results], ["b", "a"])
        self.assertEqual([row["rerank_rank"] for row in results], [1, 2])
        self.assertGreater(results[0]["rerank_score"], results[1]["rerank_score"])
        self.assertGreater(
            results[0]["rerank_score_norm"], results[1]["rerank_score_norm"]
        )
        self.assertEqual(results[0]["rank_score"], results[0]["rerank_score_norm"])
        self.assertNotIn("rerank_score", candidates[0])


class MandatoryRerankQueryTests(unittest.TestCase):
    @patch("rerank.rerank")
    @patch("query.open_chroma_for_read")
    @patch("query.ollama_embed", return_value=[0.1, 0.2])
    def test_query_units_reranks_even_when_legacy_flag_is_false(
        self, _embed, mock_open, mock_rerank
    ):
        store = MagicMock()
        store.query_units.return_value = [
            {
                "id": "semantic-first",
                "distance": 0.1,
                "document": "first",
                "metadata": {},
            },
            {
                "id": "rerank-first",
                "distance": 0.2,
                "document": "second",
                "metadata": {},
            },
        ]
        mock_open.return_value = store

        def _rerank(_query, candidates, _model, _top_k):
            out = [dict(candidates[1]), dict(candidates[0])]
            for rank, row in enumerate(out, 1):
                row["rerank_score"] = float(3 - rank)
                row["rerank_score_norm"] = float(3 - rank) / 3
                row["rerank_rank"] = rank
                row["rank_score"] = row["rerank_score_norm"]
            return out

        mock_rerank.side_effect = _rerank
        trace = QueryUnitTrace()
        cfg = {
            "models": {
                "embed_model": "embed",
                "ollama_host": "http://ollama",
                "rerank_model": "reranker",
            },
            "index": {"chroma_dir": "/tmp/chroma"},
            "query": {"rerank": False, "top_k_candidates": 20},
        }

        results = query_units("query", top_k=2, cfg=cfg, retrieval_trace=trace)

        self.assertEqual([row["id"] for row in results], ["rerank-first", "semantic-first"])
        self.assertEqual(
            [row["id"] for row in trace.candidates],
            ["semantic-first", "rerank-first"],
        )
        self.assertEqual(
            [row["id"] for row in trace.reranked],
            ["rerank-first", "semantic-first"],
        )
        mock_rerank.assert_called_once()


if __name__ == "__main__":
    unittest.main()

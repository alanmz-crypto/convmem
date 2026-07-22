"""MCP search payload exposes retrieval-stage scores."""

import json
import unittest

from mcp_server import _search_payload


class McpRerankScoreTests(unittest.TestCase):
    def test_search_payload_includes_semantic_and_reranker_scores(self):
        payload = json.loads(
            _search_payload(
                [
                    {
                        "id": "u1",
                        "score": 0.81,
                        "semantic_rank": 4,
                        "rerank_score": 2.4,
                        "rerank_score_norm": 0.916827,
                        "rerank_rank": 1,
                        "rank_fusion_score": 0.049,
                        "retrieval_rank": 1,
                        "rank_score": 0.9168,
                        "source_trust_boost": 0.15,
                        "metadata": {"title": "Unit"},
                        "document": "body",
                    },
                    {
                        "id": "u2",
                        "score": 0.8,
                        "metadata": {"title": "Chat"},
                        "document": "body",
                    },
                ]
            )
        )

        self.assertEqual(payload[0]["score"], 0.81)
        self.assertEqual(payload[0]["semantic_rank"], 4)
        self.assertEqual(payload[0]["rerank_score"], 2.4)
        self.assertEqual(payload[0]["rerank_score_norm"], 0.916827)
        self.assertEqual(payload[0]["rerank_rank"], 1)
        self.assertEqual(payload[0]["rank_fusion_score"], 0.049)
        self.assertEqual(payload[0]["retrieval_rank"], 1)
        self.assertEqual(payload[0]["source_trust_boost"], 0.15)
        self.assertNotIn("source_trust_boost", payload[1])


if __name__ == "__main__":
    unittest.main()

"""Unit tests for eval-retrieval helpers (no live Chroma)."""

from __future__ import annotations

import unittest


class EvalRetrievalLogicTests(unittest.TestCase):
    def test_rank_detection(self):
        hits = [
            {"metadata": {"ledger_id": ""}},
            {"metadata": {"ledger_id": "dec_prop_target"}},
        ]
        acceptable = ["dec_prop_target"]
        ids = [((h.get("metadata") or {}).get("ledger_id") or "").strip() for h in hits]
        rank = next((i for i, lid in enumerate(ids, 1) if lid in acceptable), None)
        self.assertEqual(rank, 2)


if __name__ == "__main__":
    unittest.main()

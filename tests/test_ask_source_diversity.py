"""Source-path diversification — Round 3 hermetic acceptance."""

from __future__ import annotations

import unittest
from collections import Counter
from unittest.mock import patch

from ask import (
    MAX_PER_SOURCE,
    _diversify_by_source,
    _source_diversity_block,
    ask,
)


def _cfg() -> dict:
    return {
        "models": {
            "distill_model": "deepseek-v4-flash",
            "ollama_host": "http://127.0.0.1:11434",
            "deepseek_base_url": "https://api.deepseek.com",
        }
    }


def _hit(uid: str, source: str, score: float = 0.9) -> dict:
    return {
        "id": uid,
        "document": f"body-{uid}",
        "score": score,
        "metadata": {
            "title": uid,
            "type": "fact",
            "tool": "cursor",
            "source_path": source,
            "domain": "coding.tooling",
        },
    }


class TestDiversifyBySource(unittest.TestCase):
    def test_crowding_fixture_refill(self):
        # pool A,A,A,B,C,D limit 5 → A,A,B,C,D; one A dropped
        pool = [
            _hit("a1", "A", 0.99),
            _hit("a2", "A", 0.98),
            _hit("a3", "A", 0.97),
            _hit("b1", "B", 0.96),
            _hit("c1", "C", 0.95),
            _hit("d1", "D", 0.94),
        ]
        kept, dropped = _diversify_by_source(pool, limit=5)
        self.assertEqual([r["id"] for r in kept], ["a1", "a2", "b1", "c1", "d1"])
        self.assertEqual([r["id"] for r in dropped], ["a3"])
        counts = Counter(
            (r.get("metadata") or {}).get("source_path") for r in kept
        )
        self.assertLessEqual(counts["A"], MAX_PER_SOURCE)

    def test_noop_already_diverse(self):
        pool = [_hit(f"x{i}", f"S{i}") for i in range(5)]
        kept, dropped = _diversify_by_source(pool, limit=5)
        self.assertEqual([r["id"] for r in kept], [f"x{i}" for i in range(5)])
        self.assertEqual(dropped, [])

    def test_empty_source_path_always_admissible(self):
        pool = [
            _hit("e1", "", 0.99),
            _hit("e2", "", 0.98),
            _hit("e3", "", 0.97),
            _hit("a1", "A", 0.96),
            _hit("a2", "A", 0.95),
            _hit("a3", "A", 0.94),
            _hit("b1", "B", 0.93),
        ]
        kept, dropped = _diversify_by_source(pool, limit=6)
        # Empties never share a bucket — all three kept; third A skipped for B refill
        self.assertEqual(
            [r["id"] for r in kept], ["e1", "e2", "e3", "a1", "a2", "b1"]
        )
        self.assertEqual([r["id"] for r in dropped], ["a3"])


class TestSourceDiversityViaAsk(unittest.TestCase):
    @patch("ask.generate_stream", return_value=iter(["ok"]))
    @patch("ask.load_config", return_value=_cfg())
    @patch("ask.query_raw", return_value=[])
    def test_results_pre_diversity_citations_may_refill(
        self, _raw, _cfg_mock, _stream
    ):
        # ranks 1-5 are A,A,A,B,C — diversify to top_k=5 pulls D from rank 6
        units = [
            _hit("a1", "ledger:decisions-approved.jsonl", 0.99),
            _hit("a2", "ledger:decisions-approved.jsonl", 0.98),
            _hit("a3", "ledger:decisions-approved.jsonl", 0.97),
            _hit("b1", "/tmp/b.md", 0.96),
            _hit("c1", "/tmp/c.md", 0.95),
            _hit("d1", "/tmp/d.md", 0.94),
        ]
        with patch("ask.query_units", return_value=units):
            out = ask("q", top_k=5, evidence=False, trace=True)

        result_ids = [r["id"] for r in out["results"]]
        cite_ids = [c.get("id") for c in out["citations"]]
        self.assertEqual(result_ids, ["a1", "a2", "a3", "b1", "c1"])
        self.assertIn("d1", cite_ids)
        self.assertNotIn("d1", result_ids)
        self.assertNotIn("a3", cite_ids)

        fc = out["trace"]["stages"]["final_context"]
        diversity = fc["source_diversity"]
        self.assertEqual(diversity["max_per_source"], 2)
        self.assertEqual(diversity["dropped_items_total"], 1)
        self.assertFalse(diversity["truncated"])
        self.assertFalse(fc["truncated"])
        dropped = diversity["dropped_items"]
        self.assertEqual(len(dropped), 1)
        self.assertEqual(dropped[0]["drop_reason"], "source_cap")
        self.assertEqual(dropped[0]["id"], "a3")
        self.assertNotIn("document", dropped[0])
        for key in dropped[0]:
            self.assertNotEqual(key, "document")

    @patch("ask.generate_stream", return_value=iter(["ok"]))
    @patch("ask.load_config", return_value=_cfg())
    @patch("ask.query_raw", return_value=[])
    def test_source_diversity_truncation_sets_envelope_not_stage_items(
        self, _raw, _cfg_mock, _stream
    ):
        # Many same-source skips while refilling → dropped_items_total > trace_limit
        # Keep selection size == trace_limit so final_context.items is not truncated.
        units = [_hit(f"a{i}", "A", 1.0 - i * 0.001) for i in range(20)]
        units += [
            _hit("b1", "B", 0.5),
            _hit("c1", "C", 0.49),
            _hit("d1", "D", 0.48),
        ]
        with patch("ask.query_units", return_value=units):
            with patch("ask.TRACE_LIMIT_DEFAULT", 5):
                out = ask("q", top_k=5, evidence=False, trace=True)

        trace = out["trace"]
        fc = trace["stages"]["final_context"]
        diversity = fc["source_diversity"]
        self.assertGreater(diversity["dropped_items_total"], 5)
        self.assertTrue(diversity["truncated"])
        self.assertLessEqual(len(diversity["dropped_items"]), 5)
        self.assertTrue(trace["truncated"])
        # items list itself is a full prefix of size <= trace_limit
        self.assertEqual(len(fc["items"]), fc["items_total"])
        self.assertFalse(fc["truncated"])
        for row in diversity["dropped_items"]:
            self.assertEqual(row["drop_reason"], "source_cap")
            self.assertNotIn("document", row)

    def test_source_diversity_block_shape(self):
        dropped = [_hit("x", "A"), _hit("y", "A"), _hit("z", "A")]
        block = _source_diversity_block(dropped, trace_limit=2)
        self.assertEqual(block["dropped_items_total"], 3)
        self.assertTrue(block["truncated"])
        self.assertEqual(len(block["dropped_items"]), 2)
        self.assertEqual(block["dropped_items"][0]["drop_reason"], "source_cap")


if __name__ == "__main__":
    unittest.main()

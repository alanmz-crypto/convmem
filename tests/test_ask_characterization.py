"""Characterization locks for current ask() — Round 4 extract must not change these.

Commit 1 of fix/2026-07-16-retrieve-for-ask: expected values only, no extraction yet.
"""

from __future__ import annotations

import unittest
from unittest.mock import patch

from ask import (
    TRACE_SCHEMA,
    _ASK_TOP_K,
    _LOW_CONFIDENCE,
    _MAX_CONTEXT_CHARS,
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


def _unit(uid: str, score: float, source: str | None = None) -> dict:
    return {
        "id": uid,
        "document": f"body-{uid}",
        "score": score,
        "metadata": {
            "title": uid,
            "type": "fact",
            "tool": "cursor",
            "source_path": source if source is not None else f"/tmp/{uid}.md",
            "domain": "coding.tooling",
            "author_model": "test",
        },
    }


def _raw(uid: str, score: float) -> dict:
    return {
        "id": uid,
        "document": f"raw-{uid}",
        "score": score,
        "metadata": {
            "tool": "cursor",
            "source_path": f"/tmp/{uid}.jsonl",
            "start_offset": 0,
            "end_offset": 1,
        },
    }


class TestAskCharacterizationEmpty(unittest.TestCase):
    """Empty-result contract (architecture lock 5)."""

    @patch("ask.generate_stream")
    @patch("ask.load_config", return_value=_cfg())
    @patch("ask.query_raw", return_value=[])
    @patch("ask.query_units", return_value=[])
    def test_empty_keys_warning_and_no_synthesis(
        self, _units, _raw_q, mock_cfg, mock_stream
    ):
        out = ask("q", trace=False)
        self.assertEqual(
            set(out.keys()),
            {"answer", "citations", "results", "confidence", "warning"},
        )
        self.assertEqual(out["warning"], "No matches in index.")
        self.assertEqual(
            out["answer"],
            "No relevant excerpts found in the index for that question.",
        )
        self.assertEqual(out["citations"], [])
        self.assertEqual(out["results"], [])
        self.assertIsNone(out["confidence"])
        mock_stream.assert_not_called()

    @patch("ask.generate_stream")
    @patch("ask.load_config", return_value=_cfg())
    @patch("ask.query_raw", return_value=[])
    @patch("ask.query_units", return_value=[])
    def test_empty_trace_zero_delivery_and_stages(
        self, _units, _raw_q, mock_cfg, mock_stream
    ):
        out = ask("q", trace=True)
        self.assertEqual(out["warning"], "No matches in index.")
        mock_stream.assert_not_called()
        tr = out["trace"]
        self.assertEqual(tr["schema"], TRACE_SCHEMA)
        delivery = tr["context_delivery"]
        self.assertEqual(
            delivery,
            {
                "max_chars": _MAX_CONTEXT_CHARS,
                "truncated": False,
                "chars_before": 0,
                "chars_after": 0,
                "last_fully_included_id": None,
                "partial_id": None,
            },
        )
        # Stages are constructed even on empty (hybrid attempt + final_context)
        stages = tr["stages"]
        self.assertIn("candidates", stages)
        self.assertIn("final_context", stages)
        self.assertIn("source_diversity", stages["final_context"])


class TestAskCharacterizationHybridWarning(unittest.TestCase):
    """Hybrid warning may use weak unit score while confidence reflects merged hits."""

    @patch("ask.generate_stream", return_value=iter(["ok"]))
    @patch("ask.load_config", return_value=_cfg())
    def test_hybrid_warning_uses_unit_score_not_merged_confidence(
        self, _cfg_mock, _stream
    ):
        weak = 0.40
        self.assertLess(weak, _LOW_CONFIDENCE)
        units = [_unit("u1", weak)]
        raw_hits = [_raw("r1", 0.95)]
        with patch("ask.query_units", return_value=units):
            with patch("ask.query_raw", return_value=raw_hits):
                out = ask("q", top_k=5, evidence=False, trace=False)

        self.assertAlmostEqual(out["confidence"], 0.95)
        self.assertIsNotNone(out["warning"])
        self.assertIn(f"{weak:.3f}", out["warning"])
        self.assertIn("Low retrieval confidence", out["warning"])


class TestAskCharacterizationCardinality(unittest.TestCase):
    """External ask() slices vs internal fetch_k pools."""

    @patch("ask.generate_stream", return_value=iter(["ok"]))
    @patch("ask.load_config", return_value=_cfg())
    @patch("ask.query_raw", return_value=[])
    def test_normal_path_returns_at_most_top_k(self, _raw_q, _cfg_mock, _stream):
        top_k = 3
        units = [_unit(f"u{i}", 0.99 - i * 0.01) for i in range(10)]
        with patch("ask.query_units", return_value=units) as mock_units:
            out = ask("q", top_k=top_k, evidence=False)
        # Over-fetch for diversify pool
        self.assertEqual(mock_units.call_args.kwargs.get("top_k"), max(top_k, _ASK_TOP_K))
        self.assertLessEqual(len(out["results"]), top_k)
        self.assertLessEqual(len(out["citations"]), top_k)
        self.assertEqual(len(out["results"]), top_k)
        self.assertEqual(len(out["citations"]), top_k)

    @patch("ask.generate_stream", return_value=iter(["ok"]))
    @patch("ask.load_config", return_value=_cfg())
    def test_raw_path_external_slice_top_k_despite_fetch_k_pool(
        self, _cfg_mock, _stream
    ):
        top_k = 3
        fetch_k = max(top_k, _ASK_TOP_K)
        raw_hits = [_raw(f"r{i}", 0.9 - i * 0.01) for i in range(fetch_k)]
        with patch("ask.query_raw", return_value=raw_hits) as mock_raw:
            out = ask("q", top_k=top_k, raw=True, trace=True)
        self.assertEqual(mock_raw.call_args.kwargs.get("top_k"), fetch_k)
        self.assertEqual(len(out["results"]), top_k)
        self.assertEqual(len(out["citations"]), top_k)
        # Internal selection may be wider; trace final_context items_total reflects selection
        fc = out["trace"]["stages"]["final_context"]
        self.assertGreaterEqual(fc["items_total"], top_k)
        self.assertLessEqual(fc["items_total"], fetch_k)


class TestAskCharacterizationConfig(unittest.TestCase):
    """ask() loads config once per call (lock 2 baseline)."""

    @patch("ask.generate_stream", return_value=iter(["ok"]))
    @patch("ask.query_raw", return_value=[])
    @patch("ask.query_units", return_value=[_unit("a", 0.9)])
    @patch("ask.load_config", return_value=_cfg())
    def test_ask_calls_load_config_exactly_once(
        self, mock_cfg, _units, _raw_q, _stream
    ):
        ask("q", top_k=1)
        self.assertEqual(mock_cfg.call_count, 1)


class TestAskCharacterizationTraceEnvelope(unittest.TestCase):
    @patch("ask.generate_stream", return_value=iter(["ok"]))
    @patch("ask.load_config", return_value=_cfg())
    @patch("ask.query_raw", return_value=[])
    @patch("ask.query_units", return_value=[_unit("a", 0.9), _unit("b", 0.8)])
    def test_success_trace_has_schema_stages_delivery(
        self, _units, _raw_q, _cfg_mock, _stream
    ):
        out = ask("q", top_k=2, trace=True)
        tr = out["trace"]
        self.assertEqual(tr["schema"], TRACE_SCHEMA)
        self.assertIn("stages", tr)
        self.assertIn("context_delivery", tr)
        self.assertIn("request", tr)
        self.assertIn("final_context", tr["stages"])
        self.assertIn("source_diversity", tr["stages"]["final_context"])
        self.assertIn("retrieval_query", out)
        self.assertIn("evidence", out)


if __name__ == "__main__":
    unittest.main()

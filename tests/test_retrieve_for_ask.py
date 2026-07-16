"""Direct retrieve_for_ask() contracts — no LLM (Round 4 commit 3)."""

# pylint: disable=duplicate-code

from __future__ import annotations

import unittest
from unittest.mock import patch

from ask import TRACE_SCHEMA, retrieve_for_ask


def _cfg() -> dict:
    return {
        "models": {
            "distill_model": "deepseek-v4-flash",
            "ollama_host": "http://127.0.0.1:11434",
            "deepseek_base_url": "https://api.deepseek.com",
        }
    }


def _unit(uid: str, score: float) -> dict:
    return {
        "id": uid,
        "document": f"body-{uid}",
        "score": score,
        "metadata": {
            "title": uid,
            "type": "fact",
            "tool": "cursor",
            "source_path": f"/tmp/{uid}.md",
            "domain": "coding.tooling",
            "author_model": "test",
        },
    }


class TestRetrieveForAskNoLLM(unittest.TestCase):
    @patch("ask.generate_stream")
    @patch("ask.load_config", return_value=_cfg())
    @patch("ask.query_raw", return_value=[])
    @patch("ask.query_units", return_value=[_unit("a", 0.9), _unit("b", 0.8)])
    def test_retrieve_never_calls_generate_stream(
        self, _units, _raw, _cfg_mock, mock_stream
    ):
        bundle = retrieve_for_ask("q", top_k=2, trace=True)
        mock_stream.assert_not_called()
        self.assertEqual(len(bundle.results), 2)
        self.assertIsNotNone(bundle.trace)
        self.assertEqual(bundle.trace["schema"], TRACE_SCHEMA)

    @patch("ask.generate_stream")
    @patch("ask.load_config")
    @patch("ask.query_raw", return_value=[])
    @patch("ask.query_units", return_value=[])
    def test_cfg_supplied_skips_load_config(
        self, _units, _raw, mock_cfg, mock_stream
    ):
        bundle = retrieve_for_ask("q", cfg=_cfg(), trace=False)
        mock_cfg.assert_not_called()
        mock_stream.assert_not_called()
        self.assertEqual(bundle.warning, "No matches in index.")
        self.assertIsNone(bundle.trace)

    @patch("ask.generate_stream")
    @patch("ask.load_config", return_value=_cfg())
    @patch("ask.query_raw", return_value=[])
    @patch("ask.query_units", return_value=[_unit("a", 0.9)])
    def test_cfg_none_loads_once(self, _units, _raw, mock_cfg, mock_stream):
        retrieve_for_ask("q", top_k=1, cfg=None)
        self.assertEqual(mock_cfg.call_count, 1)
        mock_stream.assert_not_called()


if __name__ == "__main__":
    unittest.main()

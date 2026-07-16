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


class TestRetrieveForAskIntegrationGaps(unittest.TestCase):
    """Round 5 option B: close supersession + site seams through retrieve_for_ask."""

    def _decision_unit(
        self,
        uid: str,
        ledger_id: str,
        score: float,
        *,
        relates_to: str | None = None,
    ) -> dict:
        meta = {
            "title": uid,
            "type": "decision",
            "tool": "cursor",
            "source_path": f"/tmp/{uid}.md",
            "domain": "web_stack.security",
            "author_model": "test",
            "ledger_id": ledger_id,
            "ledger_kind": "decision",
        }
        if relates_to:
            meta["relates_to"] = relates_to
        return {
            "id": uid,
            "document": f"body-{uid}",
            "score": score,
            "metadata": meta,
        }

    @patch("ask.query_raw", return_value=[])
    @patch("ask.query_units")
    @patch("ask.load_config", return_value=_cfg())
    def test_superseded_parent_dropped_through_retrieve(
        self, _cfg_mock, mock_units, _raw
    ):
        child = self._decision_unit(
            "child",
            "dec_prop_20260623_153615_a66c",
            0.9,
            relates_to="dec_prop_20260622_234011_d1ba",
        )
        parent = self._decision_unit(
            "parent",
            "dec_prop_20260622_234011_d1ba",
            0.85,
            relates_to="obs_staging2_monitor_csp-missing",
        )
        mock_units.return_value = [child, parent]
        bundle = retrieve_for_ask("csp decision supersession", top_k=5)
        result_ids = [r["id"] for r in bundle.results]
        selection_ids = [r["id"] for r in bundle.selection]
        self.assertIn("child", result_ids)
        self.assertNotIn("parent", result_ids)
        self.assertNotIn("parent", selection_ids)

    @patch("ask.query_raw", return_value=[])
    @patch("ask.query_units")
    @patch("ask.load_config", return_value=_cfg())
    def test_site_forwarded_through_retrieve_paths(
        self, _cfg_mock, mock_units, mock_raw
    ):
        site = "staging2.willowyhollow.com"
        mock_units.return_value = [_unit("a", 0.9)]

        retrieve_for_ask("csp status", site=site, raw=False)
        self.assertEqual(mock_units.call_args.kwargs.get("site"), site)

        retrieve_for_ask("csp status", site=site, raw=True)
        self.assertEqual(mock_raw.call_args.kwargs.get("site"), site)


class TestQueryCfgThreading(unittest.TestCase):
    """Lock 2: supplied cfg must not trigger query.load_config (or fallback reload)."""

    def _full_cfg(self) -> dict:
        return {
            "models": {
                "embed_model": "nomic-embed-text",
                "ollama_host": "http://127.0.0.1:11434",
                "distill_model": "deepseek-v4-flash",
                "deepseek_base_url": "https://api.deepseek.com",
                "rerank_model": "rerank",
            },
            "index": {"chroma_dir": "/tmp/convmem-test-chroma"},
            "query": {},
        }

    @patch("query.collection_metadata_rows", return_value=[])
    @patch("query.open_chroma_for_read", side_effect=RuntimeError("force fallback"))
    @patch("query.ollama_embed", return_value=[0.1, 0.2, 0.3])
    @patch("query.load_config")
    def test_query_units_cfg_skips_load_config(
        self, mock_qcfg, _embed, _open, _rows
    ):
        from query import query_units

        cfg = self._full_cfg()
        query_units("hello", top_k=1, cfg=cfg)
        mock_qcfg.assert_not_called()

    @patch("query.collection_metadata_rows", return_value=[])
    @patch("query.open_chroma_for_read", side_effect=RuntimeError("force fallback"))
    @patch("query.ollama_embed", return_value=[0.1, 0.2, 0.3])
    @patch("query.load_config")
    def test_query_raw_cfg_skips_load_config(
        self, mock_qcfg, _embed, _open, _rows
    ):
        from query import query_raw

        cfg = self._full_cfg()
        query_raw("hello", top_k=1, cfg=cfg)
        mock_qcfg.assert_not_called()

    @patch("query.collection_metadata_rows", return_value=[])
    @patch("query.open_chroma_for_read", side_effect=RuntimeError("force fallback"))
    @patch("query.ollama_embed", return_value=[0.1, 0.2, 0.3])
    @patch("query.load_config")
    @patch("ask.load_config")
    @patch("ask.generate_stream")
    def test_retrieve_for_ask_threads_cfg_no_query_reload(
        self, mock_stream, mock_ask_cfg, mock_qcfg, _embed, _open, _rows
    ):
        cfg = self._full_cfg()
        retrieve_for_ask("q", top_k=1, cfg=cfg, raw=False)
        retrieve_for_ask("q", top_k=1, cfg=cfg, raw=True)
        mock_qcfg.assert_not_called()
        mock_ask_cfg.assert_not_called()
        mock_stream.assert_not_called()


if __name__ == "__main__":
    unittest.main()

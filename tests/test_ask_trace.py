"""ask() retrieval trace — convmem.ask.trace.v1 contract."""

from __future__ import annotations

import json
import unittest
from unittest.mock import patch

from ask import (
    TRACE_SCHEMA,
    _apply_context_char_limit,
    _compact_trace_row,
    ask,
)


def _unit(uid: str, score: float, title: str = "T", **extra) -> dict:
    meta = {
        "title": title,
        "type": "fact",
        "tool": "cursor",
        "source_path": f"/tmp/{uid}.md",
        "ledger_id": extra.pop("ledger_id", ""),
        "ledger_kind": extra.pop("ledger_kind", None),
        "domain": "coding.tooling",
        "author_model": "test",
    }
    row = {
        "id": uid,
        "document": f"body-{uid}",
        "score": score,
        "metadata": meta,
    }
    row.update(extra)
    return row


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


class TestAskTrace(unittest.TestCase):
    def test_compact_row_no_document_body(self):
        row = _compact_trace_row(_unit("a", 0.9, "Alpha"), origin="unit")
        self.assertEqual(row["id"], "a")
        self.assertEqual(row["origin"], "unit")
        self.assertNotIn("document", row)
        self.assertNotIn("body", json.dumps(row))

    def test_context_delivery_char_truncation(self):
        selection = [
            _unit("a", 0.9, document="AAAA"),
            _unit("b", 0.8, document="BBBB"),
        ]
        # Force known block texts
        blocks = ["BLOCK-A", "BLOCK-B-LONG"]
        context = "\n\n".join(blocks)
        delivered, meta = _apply_context_char_limit(
            context, selection, blocks, max_chars=10
        )
        self.assertTrue(meta["truncated"])
        self.assertEqual(meta["max_chars"], 10)
        self.assertEqual(meta["chars_before"], len(context))
        self.assertGreater(meta["chars_after"], 10)  # includes marker
        self.assertIn("[… context truncated …]", delivered)
        self.assertEqual(meta["last_fully_included_id"], "a")
        self.assertEqual(meta["partial_id"], "b")

    @patch("ask.query_units")
    @patch("ask.load_config")
    @patch("ask.generate_stream")
    def test_trace_absent_by_default(self, mock_stream, mock_cfg, mock_units):
        mock_units.return_value = [_unit("a", 0.95), _unit("b", 0.9)]
        mock_cfg.return_value = {
            "models": {
                "distill_model": "deepseek-v4-flash",
                "ollama_host": "http://127.0.0.1:11434",
                "deepseek_base_url": "https://api.deepseek.com",
            }
        }
        mock_stream.side_effect = lambda *a, **k: iter(["ok"])
        plain = ask("q", top_k=2)
        self.assertNotIn("trace", plain)

    @patch("ask.query_units")
    @patch("ask.load_config")
    @patch("ask.generate_stream")
    def test_normal_path_final_context_and_schema(
        self, mock_stream, mock_cfg, mock_units
    ):
        units = [_unit("a", 0.95), _unit("b", 0.9), _unit("c", 0.85)]
        mock_units.return_value = units
        mock_cfg.return_value = {
            "models": {
                "distill_model": "deepseek-v4-flash",
                "ollama_host": "http://127.0.0.1:11434",
                "deepseek_base_url": "https://api.deepseek.com",
            }
        }
        mock_stream.side_effect = lambda *a, **k: iter(["ok"])

        traced = ask("q", top_k=2, trace=True)
        tr = traced["trace"]
        self.assertEqual(tr["schema"], TRACE_SCHEMA)
        self.assertEqual(tr["request"]["retrieval_query"], "q")
        self.assertFalse(tr["request"]["evidence"])
        self.assertFalse(tr["request"]["raw"])
        self.assertIn("context_delivery", tr)
        self.assertFalse(tr["context_delivery"]["truncated"])

        stages = tr["stages"]
        for name in (
            "candidates",
            "evidence_reranked",
            "ledger_deduped",
            "recent_injected",
            "final_context",
        ):
            self.assertIn(name, stages)

        self.assertEqual(stages["evidence_reranked"]["status"], "skipped")
        self.assertEqual(stages["evidence_reranked"]["reason"], "evidence_disabled")
        self.assertEqual(stages["ledger_deduped"]["status"], "skipped")
        self.assertEqual(stages["recent_injected"]["status"], "skipped")

        final_ids = [r["id"] for r in stages["final_context"]["items"]]
        self.assertEqual(final_ids, ["a", "b"])
        self.assertFalse(stages["final_context"]["truncated"])
        self.assertEqual(stages["final_context"]["items_total"], 2)
        # No document bodies in any compact row
        blob = json.dumps(tr)
        self.assertNotIn("body-a", blob)

    @patch("ask.query_raw")
    @patch("ask.load_config")
    @patch("ask.generate_stream")
    def test_raw_path_final_context(self, mock_stream, mock_cfg, mock_raw):
        hits = [_raw("r1", 0.9), _raw("r2", 0.8), _raw("r3", 0.7)]
        mock_raw.return_value = hits
        mock_cfg.return_value = {
            "models": {
                "distill_model": "deepseek-v4-flash",
                "ollama_host": "http://127.0.0.1:11434",
                "deepseek_base_url": "https://api.deepseek.com",
            }
        }
        mock_stream.side_effect = lambda *a, **k: iter(["ok"])
        traced = ask("q", top_k=2, raw=True, trace=True)
        stages = traced["trace"]["stages"]
        self.assertEqual(stages["evidence_reranked"]["reason"], "raw_mode")
        self.assertEqual(stages["ledger_deduped"]["reason"], "raw_mode")
        self.assertEqual(stages["recent_injected"]["reason"], "raw_mode")
        final_ids = [r["id"] for r in stages["final_context"]["items"]]
        # raw formats all fetch_k hits (max(top_k, 8) => 8 but only 3 available)
        self.assertEqual(final_ids, ["r1", "r2", "r3"])
        self.assertTrue(
            all(r.get("origin") == "raw_summary" for r in stages["final_context"]["items"])
        )

    @patch("ask.query_raw")
    @patch("ask.query_units")
    @patch("ask.load_config")
    @patch("ask.generate_stream")
    def test_hybrid_path_final_context_origins(
        self, mock_stream, mock_cfg, mock_units, mock_raw
    ):
        # Low scores force hybrid when evidence=False
        mock_units.return_value = [_unit("u1", 0.2)]
        mock_raw.return_value = [_raw("r1", 0.9), _raw("r2", 0.8)]
        mock_cfg.return_value = {
            "models": {
                "distill_model": "deepseek-v4-flash",
                "ollama_host": "http://127.0.0.1:11434",
                "deepseek_base_url": "https://api.deepseek.com",
            }
        }
        mock_stream.side_effect = lambda *a, **k: iter(["ok"])
        traced = ask("q", top_k=5, trace=True)
        items = traced["trace"]["stages"]["final_context"]["items"]
        origins = {r["id"]: r.get("origin") for r in items}
        self.assertIn("u1", origins)
        self.assertEqual(origins["u1"], "unit")
        self.assertTrue(any(o == "raw_summary" for o in origins.values()))

    @patch("ask.recent_decisions_for_cfg")
    @patch("ask.apply_evidence_rerank", create=True)
    @patch("ask.ChromaStore", create=True)
    @patch("ask.query_units")
    @patch("ask.load_config")
    @patch("ask.generate_stream")
    def test_evidence_stages_separated_and_admitted_recent(
        self,
        mock_stream,
        mock_cfg,
        mock_units,
        mock_store_cls,
        mock_rerank,
        mock_recent,
    ):
        # Import path uses chroma_store.ChromaStore and evidence.apply_evidence_rerank
        units = [_unit("a", 0.95, ledger_id="dec_a"), _unit("b", 0.9, ledger_id="dec_b")]
        mock_units.return_value = units
        mock_cfg.return_value = {
            "models": {
                "distill_model": "deepseek-v4-flash",
                "ollama_host": "http://127.0.0.1:11434",
                "deepseek_base_url": "https://api.deepseek.com",
            },
            "index": {"chroma_dir": "/tmp/chroma"},
            "query": {"recency_weight": 0.0, "recency_half_life_days": 30.0},
        }
        mock_stream.side_effect = lambda *a, **k: iter(["ok"])

        store = mock_store_cls.return_value
        store.__enter__.return_value = store
        store.__exit__.return_value = False

        def _rerank(u, *a, **k):
            out = []
            for row in u:
                c = dict(row)
                c["evidence_status"] = "resolved"
                c["evidence_boost"] = 0.1
                out.append(c)
            return out

        with patch("evidence.apply_evidence_rerank", side_effect=_rerank), patch(
            "chroma_store.ChromaStore", mock_store_cls
        ):
            mock_recent.return_value = [
                {
                    "id": "dec_recent",
                    "timestamp": "2026-07-15T00:00:00+00:00",
                    "summary": "recent",
                    "rationale": "r",
                    "author_model": "test",
                    "domain": "coding.tooling",
                    "site": "",
                    "relates_to": "",
                    "status": "proposed",
                }
            ]
            traced = ask("q", top_k=5, evidence=True, trace=True)

        stages = traced["trace"]["stages"]
        self.assertEqual(stages["evidence_reranked"]["status"], "ok")
        self.assertEqual(stages["ledger_deduped"]["status"], "ok")
        self.assertIsNot(stages["evidence_reranked"], stages["ledger_deduped"])
        admitted = stages["recent_injected"]["items"]
        self.assertTrue(admitted)
        self.assertTrue(
            all(r.get("evidence_status") == "recent_decision" for r in admitted)
        )

    @patch("ask.query_units")
    @patch("ask.load_config")
    @patch("ask.generate_stream")
    def test_trace_limit_truncation_flag(self, mock_stream, mock_cfg, mock_units):
        units = [_unit(f"u{i}", 0.9 - i * 0.01) for i in range(25)]
        mock_units.return_value = units
        mock_cfg.return_value = {
            "models": {
                "distill_model": "deepseek-v4-flash",
                "ollama_host": "http://127.0.0.1:11434",
                "deepseek_base_url": "https://api.deepseek.com",
            }
        }
        mock_stream.side_effect = lambda *a, **k: iter(["ok"])
        traced = ask("q", top_k=5, trace=True, trace_limit=20)
        tr = traced["trace"]
        self.assertTrue(tr["truncated"])
        self.assertEqual(tr["stages"]["candidates"]["items_total"], 25)
        self.assertEqual(len(tr["stages"]["candidates"]["items"]), 20)
        self.assertTrue(tr["stages"]["candidates"]["truncated"])

    def test_mcp_omit_trace_key_and_piggyback_fields(self):
        import mcp_server

        with patch.object(mcp_server, "_blocked_until_brief_json", return_value=None):
            with patch("ask.ask") as run_ask:
                run_ask.return_value = {
                    "answer": "a",
                    "confidence": 0.9,
                    "warning": None,
                    "citations": [
                        {
                            "n": 1,
                            "title": "T",
                            "type": "fact",
                            "tool": "cursor",
                            "source_path": "/t",
                            "domain": "coding.tooling",
                            "when": "",
                            "score": 0.9,
                            "evidence_status": "resolved",
                            "ledger_id": "dec_x",
                        }
                    ],
                }
                payload = json.loads(mcp_server.ask("q", trace=False))
                self.assertNotIn("trace", payload)
                self.assertEqual(payload["citations"][0]["evidence_status"], "resolved")
                self.assertEqual(payload["citations"][0]["ledger_id"], "dec_x")

                run_ask.return_value["trace"] = {"schema": TRACE_SCHEMA}
                payload2 = json.loads(mcp_server.ask("q", trace=True))
                self.assertEqual(payload2["trace"]["schema"], TRACE_SCHEMA)


if __name__ == "__main__":
    unittest.main()

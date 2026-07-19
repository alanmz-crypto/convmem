"""ask() retrieval trace — convmem.ask.trace.v1 contract."""

from __future__ import annotations

import json
import unittest
from unittest import mock
from unittest.mock import patch

from ask import (
    TRACE_SCHEMA,
    _apply_context_char_limit,
    _compact_trace_row,
    ask,
)


def _cfg(**extra) -> dict:
    base = {
        "models": {
            "distill_model": "deepseek-v4-flash",
            "ollama_host": "http://127.0.0.1:11434",
            "deepseek_base_url": "https://api.deepseek.com",
        }
    }
    base.update(extra)
    return base


def _unit(uid: str, score: float, title: str = "T", **extra) -> dict:
    meta = {
        "title": title,
        "type": "fact",
        "tool": "cursor",
        "source_path": f"/tmp/{uid}.md",
        "ledger_id": extra.pop("ledger_id", ""),
        "ledger_kind": extra.pop("ledger_kind", None),
        "domain": extra.pop("domain", "coding.tooling"),
        "author_model": "test",
    }
    if "site" in extra:
        meta["site"] = extra.pop("site")
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


def _recent_rec(
    rid: str,
    *,
    domain: str = "coding.tooling",
    site: str = "",
) -> dict:
    return {
        "id": rid,
        "timestamp": "2026-07-15T00:00:00+00:00",
        "summary": f"summary-{rid}",
        "rationale": "r",
        "author_model": "test",
        "domain": domain,
        "site": site,
        "relates_to": "",
        "status": "proposed",
    }


class TestAskTrace(unittest.TestCase):
    def test_compact_row_no_document_body(self):
        row = _compact_trace_row(
            _unit(
                "a",
                0.9,
                "Alpha",
                semantic_rank=2,
                rerank_score=3.5,
                rerank_score_norm=0.97,
                rerank_rank=1,
            ),
            origin="unit",
        )
        self.assertEqual(row["id"], "a")
        self.assertEqual(row["origin"], "unit")
        self.assertEqual(row["semantic_rank"], 2)
        self.assertEqual(row["rerank_score"], 3.5)
        self.assertEqual(row["rerank_score_norm"], 0.97)
        self.assertEqual(row["rerank_rank"], 1)
        self.assertNotIn("document", row)
        self.assertNotIn("body", json.dumps(row))

    def test_context_delivery_char_truncation(self):
        selection = [_unit("a", 0.9), _unit("b", 0.8)]
        blocks = ["BLOCK-A", "BLOCK-B-LONG"]
        context = "\n\n".join(blocks)
        delivered, meta = _apply_context_char_limit(
            context, selection, blocks, max_chars=10
        )
        self.assertTrue(meta["truncated"])
        self.assertEqual(meta["max_chars"], 10)
        self.assertEqual(meta["chars_before"], len(context))
        self.assertGreater(meta["chars_after"], 10)
        self.assertIn("[… context truncated …]", delivered)
        self.assertEqual(meta["last_fully_included_id"], "a")
        self.assertEqual(meta["partial_id"], "b")

    @patch("ask.query_units")
    @patch("ask.load_config")
    @patch("ask.generate_stream")
    def test_prompt_parity_and_numbering(self, mock_stream, mock_cfg, mock_units):
        mock_units.return_value = [
            _unit("a", 0.95),
            _unit("b", 0.9),
            _unit("c", 0.85),
        ]
        mock_cfg.return_value = _cfg()
        prompts: list[str] = []

        def _stream(*_a, **kwargs):
            prompts.append(kwargs.get("prompt") or (_a[0] if _a else ""))
            return iter(["ok"])

        # generate_stream(prompt, model=..., ...) — first positional is prompt
        def _stream2(prompt, **_kwargs):
            prompts.append(prompt)
            return iter(["ok"])

        mock_stream.side_effect = _stream2

        plain = ask("q", top_k=3, trace=False)
        traced = ask("q", top_k=3, trace=True)
        self.assertEqual(len(prompts), 2)
        self.assertEqual(prompts[0], prompts[1])
        self.assertIn("[1]", prompts[0])
        self.assertIn("[2]", prompts[0])
        self.assertIn("[3]", prompts[0])
        # Excerpt headers (not the prompt template's "[1], [2], etc.")
        self.assertEqual(prompts[0].count("[1] ("), 1)
        self.assertEqual(prompts[0].count("[2] ("), 1)
        self.assertEqual(prompts[0].count("[3] ("), 1)

        plain_keys = set(plain) - {"trace"}
        traced_keys = set(traced) - {"trace"}
        self.assertEqual(plain_keys, traced_keys)
        for k in plain_keys:
            self.assertEqual(plain[k], traced[k], msg=k)
        self.assertNotIn("trace", plain)
        self.assertIn("trace", traced)

    @patch("ask.query_raw")
    @patch("ask.query_units")
    @patch("ask.load_config")
    @patch("ask.generate_stream")
    def test_empty_shape_trace_false_and_true(
        self, mock_stream, mock_cfg, mock_units, mock_raw
    ):
        mock_units.return_value = []
        mock_raw.return_value = []
        mock_cfg.return_value = _cfg()
        mock_stream.side_effect = lambda *_a, **_k: iter(["ok"])

        plain = ask("q", trace=False)
        self.assertEqual(
            set(plain.keys()),
            {"answer", "citations", "results", "confidence", "warning"},
        )
        traced = ask("q", trace=True)
        self.assertEqual(
            set(traced.keys()),
            {"answer", "citations", "results", "confidence", "warning", "trace"},
        )
        self.assertEqual(traced["trace"]["schema"], TRACE_SCHEMA)

    @patch("ask.query_units")
    @patch("ask.load_config")
    @patch("ask.generate_stream")
    def test_trace_absent_by_default(self, mock_stream, mock_cfg, mock_units):
        mock_units.return_value = [_unit("a", 0.95), _unit("b", 0.9)]
        mock_cfg.return_value = _cfg()
        mock_stream.side_effect = lambda *_a, **_k: iter(["ok"])
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
        mock_cfg.return_value = _cfg()
        mock_stream.side_effect = lambda *_a, **_k: iter(["ok"])

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
            "semantic_reranked",
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
        blob = json.dumps(tr)
        self.assertNotIn("body-a", blob)

    @patch("ask.query_raw")
    @patch("ask.load_config")
    @patch("ask.generate_stream")
    def test_raw_path_final_context(self, mock_stream, mock_cfg, mock_raw):
        hits = [_raw("r1", 0.9), _raw("r2", 0.8), _raw("r3", 0.7)]
        mock_raw.return_value = hits
        mock_cfg.return_value = _cfg()
        mock_stream.side_effect = lambda *_a, **_k: iter(["ok"])
        traced = ask("q", top_k=2, raw=True, trace=True)
        stages = traced["trace"]["stages"]
        self.assertEqual(stages["semantic_reranked"]["reason"], "raw_mode")
        self.assertEqual(stages["evidence_reranked"]["reason"], "raw_mode")
        self.assertEqual(stages["ledger_deduped"]["reason"], "raw_mode")
        self.assertEqual(stages["recent_injected"]["reason"], "raw_mode")
        final_ids = [r["id"] for r in stages["final_context"]["items"]]
        self.assertEqual(final_ids, ["r1", "r2", "r3"])
        self.assertTrue(
            all(
                r.get("origin") == "raw_summary"
                for r in stages["final_context"]["items"]
            )
        )

    @patch("ask.query_raw")
    @patch("ask.query_units")
    @patch("ask.load_config")
    @patch("ask.generate_stream")
    def test_hybrid_path_final_context_origins(
        self, mock_stream, mock_cfg, mock_units, mock_raw
    ):
        mock_units.return_value = [_unit("u1", 0.2)]
        mock_raw.return_value = [_raw("r1", 0.9), _raw("r2", 0.8)]
        mock_cfg.return_value = _cfg()
        mock_stream.side_effect = lambda *_a, **_k: iter(["ok"])
        traced = ask("q", top_k=5, trace=True)
        items = traced["trace"]["stages"]["final_context"]["items"]
        origins = {r["id"]: r.get("origin") for r in items}
        self.assertIn("u1", origins)
        self.assertEqual(origins["u1"], "unit")
        self.assertTrue(any(o == "raw_summary" for o in origins.values()))

    @patch("ask.recent_decisions_for_cfg")
    @patch("ask.query_units")
    @patch("ask.load_config")
    @patch("ask.generate_stream")
    def test_evidence_dedupe_and_admitted_recent_edges(
        self,
        mock_stream,
        mock_cfg,
        mock_units,
        mock_recent,
    ):
        # Duplicate ledger_id so dedupe drops one; recent overlaps + over-cap + domain miss
        units = [
            _unit("a", 0.95, ledger_id="dec_a"),
            _unit("a_dup", 0.94, ledger_id="dec_a"),
            _unit("b", 0.9, ledger_id="dec_b"),
        ]
        mock_units.return_value = units
        mock_cfg.return_value = _cfg(
            index={"chroma_dir": "/tmp/chroma"},
            query={"recency_weight": 0.0, "recency_half_life_days": 30.0},
        )
        mock_stream.side_effect = lambda *_a, **_k: iter(["ok"])

        def _rerank(u, *_a, **_k):
            out = []
            for row in u:
                c = dict(row)
                c["evidence_status"] = "resolved"
                c["evidence_boost"] = 0.1
                out.append(c)
            return out

        mock_store = mock.MagicMock()
        mock_store.__enter__.return_value = mock_store
        mock_store.__exit__.return_value = False

        mock_recent.return_value = [
            _recent_rec("dec_a"),  # overlaps semantic — excluded
            _recent_rec("dec_r1"),
            _recent_rec("dec_r2"),
            _recent_rec("dec_r3"),
            _recent_rec("dec_r4"),
            _recent_rec("dec_r5"),
            _recent_rec("dec_r6"),
            _recent_rec("dec_r7"),
            _recent_rec("dec_r8"),
            _recent_rec("dec_other", domain="web_stack.security"),  # domain miss
        ]

        with patch("evidence.apply_evidence_rerank", side_effect=_rerank), patch(
            "chroma_store.ChromaStore", return_value=mock_store
        ):
            traced = ask(
                "q",
                top_k=5,
                evidence=True,
                trace=True,
                domain="coding.tooling",
            )

        stages = traced["trace"]["stages"]
        self.assertEqual(stages["evidence_reranked"]["status"], "ok")
        self.assertEqual(stages["ledger_deduped"]["status"], "ok")
        self.assertGreater(
            stages["evidence_reranked"]["items_total"],
            stages["ledger_deduped"]["items_total"],
        )
        admitted_ids = {
            (r.get("ledger_id") or "") for r in stages["recent_injected"]["items"]
        }
        self.assertNotIn("dec_a", admitted_ids)
        self.assertNotIn("dec_other", admitted_ids)
        self.assertTrue(
            all(
                r.get("evidence_status") == "recent_decision"
                for r in stages["recent_injected"]["items"]
            )
        )
        # Minority cap on fetch_k=8 → at most floor(8/3)=2 or max(1,...) = 2
        self.assertLessEqual(len(stages["recent_injected"]["items"]), 2)

    @patch("ask.query_raw")
    @patch("ask.load_config")
    @patch("ask.generate_stream")
    def test_final_context_trace_limit_prefix(self, mock_stream, mock_cfg, mock_raw):
        hits = [_raw(f"r{i}", 0.9 - i * 0.01) for i in range(12)]
        mock_raw.return_value = hits
        mock_cfg.return_value = _cfg()
        mock_stream.side_effect = lambda *_a, **_k: iter(["ok"])
        with patch("ask.TRACE_LIMIT_DEFAULT", 5):
            traced = ask("q", top_k=12, raw=True, trace=True)
        fc = traced["trace"]["stages"]["final_context"]
        self.assertTrue(fc["truncated"])
        self.assertEqual(fc["items_total"], 12)
        self.assertEqual(len(fc["items"]), 5)
        self.assertEqual(
            [r["id"] for r in fc["items"]],
            [f"r{i}" for i in range(5)],
        )

    @patch("ask.query_units")
    @patch("ask.load_config")
    @patch("ask.generate_stream")
    def test_a2_e2e_via_ask_max_chars(self, mock_stream, mock_cfg, mock_units):
        mock_units.return_value = [
            _unit("a", 0.95),
            _unit("b", 0.9),
            _unit("c", 0.85),
        ]
        mock_cfg.return_value = _cfg()
        mock_stream.side_effect = lambda *_a, **_k: iter(["ok"])
        with patch("ask._MAX_CONTEXT_CHARS", 40):
            traced = ask("q", top_k=3, trace=True)
        delivery = traced["trace"]["context_delivery"]
        self.assertTrue(delivery["truncated"])
        self.assertEqual(delivery["max_chars"], 40)
        self.assertGreater(delivery["chars_after"], 40)

    @patch("ask.query_units")
    @patch("ask.load_config")
    @patch("ask.generate_stream")
    def test_trace_limit_truncation_flag(self, mock_stream, mock_cfg, mock_units):
        units = [_unit(f"u{i}", 0.9 - i * 0.01) for i in range(25)]
        mock_units.return_value = units
        mock_cfg.return_value = _cfg()
        mock_stream.side_effect = lambda *_a, **_k: iter(["ok"])
        traced = ask("q", top_k=5, trace=True)
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

    @patch("ask.query_units")
    @patch("ask.load_config")
    @patch("ask.generate_stream")
    def test_cli_trace_writes_json_stderr(
        self, mock_stream, mock_cfg, mock_units
    ):
        from typer.testing import CliRunner

        import convmem

        mock_units.return_value = [_unit("a", 0.95), _unit("b", 0.9)]
        mock_cfg.return_value = _cfg()
        mock_stream.side_effect = lambda *_a, **_k: iter(["ok"])

        runner = CliRunner()
        result = runner.invoke(
            convmem.app, ["ask", "hello trace", "--trace"], catch_exceptions=False
        )
        self.assertEqual(result.exit_code, 0, msg=result.output)
        # stderr should contain trace JSON
        err = result.stderr or ""
        self.assertIn("convmem.ask.trace.v1", err)
        payload = json.loads(err[err.index("{") :])
        self.assertEqual(payload["schema"], TRACE_SCHEMA)


if __name__ == "__main__":
    unittest.main()

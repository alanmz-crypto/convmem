"""Tests for ledger_recent and ask recent-decision injection."""

from __future__ import annotations

import unittest
from unittest import mock

from ask import _prepend_recent_decisions
from ledger_recent import decision_record_to_unit, load_recent_decisions


class LedgerRecentTests(unittest.TestCase):
    def test_load_recent_decisions_filters_by_age(self):
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "decisions-approved.jsonl"
            path.write_text(
                '{"id":"dec_prop_old","timestamp":"2020-01-01T00:00:00Z","summary":"old"}\n'
                '{"id":"dec_prop_new","timestamp":"2099-06-01T12:00:00Z","summary":"new"}\n',
                encoding="utf-8",
            )
            rows = load_recent_decisions(path, days=7, limit=10)
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["id"], "dec_prop_new")

    def test_decision_record_to_unit_shape(self):
        unit = decision_record_to_unit(
            {
                "id": "dec_prop_test",
                "summary": "Ship feature",
                "rationale": "Because tests",
                "timestamp": "2026-07-01T00:00:00Z",
                "author": "ryan",
            }
        )
        self.assertEqual(unit["metadata"]["ledger_id"], "dec_prop_test")
        self.assertIn("Ship feature", unit["document"])
        self.assertEqual(unit["evidence_status"], "recent_decision")


class AskRecentPrependTests(unittest.TestCase):
    def test_prepend_recent_before_semantic(self):
        semantic = [
            {"metadata": {"ledger_id": "obs_a"}, "score": 0.9},
            {"metadata": {"ledger_id": "obs_b"}, "score": 0.8},
        ]
        recent = [{"id": "dec_prop_new", "summary": "fresh", "timestamp": "2099-01-01T00:00:00Z"}]
        out = _prepend_recent_decisions(semantic, recent, total_limit=3)
        self.assertEqual(out[0]["metadata"]["ledger_id"], "dec_prop_new")
        self.assertEqual(len(out), 3)

    def test_prepend_prefers_semantic_on_ledger_id_overlap(self):
        """Semantic wins identity; overlapping recent is dropped before cap."""
        semantic = [
            {"metadata": {"ledger_id": "dec_prop_new"}, "score": 0.5, "document": "sem"},
            {"metadata": {"ledger_id": "obs_b"}, "score": 0.8, "document": "b"},
        ]
        recent = [{"id": "dec_prop_new", "summary": "fresh"}]
        out = _prepend_recent_decisions(semantic, recent, total_limit=2)
        ids = [(u.get("metadata") or {}).get("ledger_id") for u in out]
        self.assertEqual(ids.count("dec_prop_new"), 1)
        # Surviving dec_prop_new is the semantic unit, not the inject.
        winner = next(u for u in out if (u.get("metadata") or {}).get("ledger_id") == "dec_prop_new")
        self.assertEqual(winner.get("document"), "sem")
        self.assertNotEqual(winner.get("evidence_status"), "recent_decision")

    def test_minority_cap_eight_plus_eight(self):
        semantic = [
            {"metadata": {"ledger_id": f"sem_{i}"}, "score": 0.9 - i * 0.01}
            for i in range(8)
        ]
        recent = [
            {
                "id": f"dec_prop_r{i}",
                "summary": f"recent {i}",
                "domain": "web_stack.wordpress",
            }
            for i in range(8)
        ]
        out = _prepend_recent_decisions(semantic, recent, total_limit=8)
        self.assertEqual(len(out), 8)
        recent_n = sum(1 for u in out if u.get("evidence_status") == "recent_decision")
        self.assertEqual(recent_n, 2)  # max(1, 8//3) = 2
        for u in out[:recent_n]:
            self.assertEqual(u.get("evidence_status"), "recent_decision")
        final5 = out[:5]
        sem_in_final = sum(
            1 for u in final5 if u.get("evidence_status") != "recent_decision"
        )
        self.assertGreaterEqual(sem_in_final, 3)

    def test_cap_after_dedupe_short_list(self):
        """5 recent, 3 overlap semantic → 2 remain; floor does not cut further."""
        semantic = [
            {"metadata": {"ledger_id": "dec_prop_a"}, "score": 0.9},
            {"metadata": {"ledger_id": "dec_prop_b"}, "score": 0.8},
            {"metadata": {"ledger_id": "dec_prop_c"}, "score": 0.7},
            {"metadata": {"ledger_id": "sem_x"}, "score": 0.6},
            {"metadata": {"ledger_id": "sem_y"}, "score": 0.5},
        ]
        recent = [
            {"id": "dec_prop_a", "summary": "a"},
            {"id": "dec_prop_b", "summary": "b"},
            {"id": "dec_prop_c", "summary": "c"},
            {"id": "dec_prop_d", "summary": "d"},
            {"id": "dec_prop_e", "summary": "e"},
        ]
        out = _prepend_recent_decisions(semantic, recent, total_limit=8)
        recent_ids = [
            (u.get("metadata") or {}).get("ledger_id")
            for u in out
            if u.get("evidence_status") == "recent_decision"
        ]
        self.assertEqual(set(recent_ids), {"dec_prop_d", "dec_prop_e"})
        # 2 recent + 5 semantic = 7 when both pools are short of total_limit
        self.assertEqual(len(out), 7)

    def test_small_total_limit_keeps_one_recent_slot(self):
        semantic = [{"metadata": {"ledger_id": f"sem_{i}"}, "score": 0.9} for i in range(4)]
        recent = [{"id": f"dec_prop_r{i}", "summary": f"r{i}"} for i in range(4)]
        out = _prepend_recent_decisions(semantic, recent, total_limit=2)
        recent_n = sum(1 for u in out if u.get("evidence_status") == "recent_decision")
        self.assertEqual(recent_n, 1)  # max(1, 2//3) = 1
        self.assertEqual(len(out), 2)

    def test_domain_filter_excludes_mismatched(self):
        semantic = [{"metadata": {"ledger_id": f"sem_{i}"}, "score": 0.9} for i in range(6)]
        recent = [
            {"id": "dec_prop_code", "summary": "code", "domain": "coding.tooling"},
            {"id": "dec_prop_wp", "summary": "wp", "domain": "web_stack.wordpress"},
        ]
        out = _prepend_recent_decisions(
            semantic, recent, total_limit=8, domain="coding"
        )
        recent_ids = [
            (u.get("metadata") or {}).get("ledger_id")
            for u in out
            if u.get("evidence_status") == "recent_decision"
        ]
        self.assertEqual(recent_ids, ["dec_prop_code"])

    def test_site_filter_exact(self):
        semantic = [{"metadata": {"ledger_id": "sem_1"}, "score": 0.9}]
        recent = [
            {"id": "dec_prop_a", "summary": "a", "site": "staging2.willowyhollow.com"},
            {"id": "dec_prop_b", "summary": "b", "site": "other.example.com"},
        ]
        out = _prepend_recent_decisions(
            semantic, recent, total_limit=8, site="staging2.willowyhollow.com"
        )
        recent_ids = [
            (u.get("metadata") or {}).get("ledger_id")
            for u in out
            if u.get("evidence_status") == "recent_decision"
        ]
        self.assertEqual(recent_ids, ["dec_prop_a"])


class EvidenceStoreCloseTests(unittest.TestCase):
    @mock.patch("ask.query_units")
    @mock.patch("ask.recent_decisions_for_cfg", return_value=[])
    @mock.patch("ask._dedupe_results_by_ledger_id", side_effect=lambda x: x)
    @mock.patch("ask.load_config")
    def test_chroma_store_closed_on_success(self, mock_cfg, _dedupe, _recent, mock_q):
        from ask import ask as ask_fn

        store = mock.MagicMock()
        store.__enter__.return_value = store
        store.__exit__.return_value = None
        mock_q.return_value = [{"metadata": {"ledger_id": "sem_1"}, "score": 0.9, "document": "x"}]
        mock_cfg.return_value = {
            "index": {"chroma_dir": "/tmp/chroma-test"},
            "models": {
                "distill_model": "deepseek-v4-flash",
                "ollama_host": "http://localhost:11434",
            },
            "query": {},
        }
        with mock.patch("chroma_store.ChromaStore", return_value=store), mock.patch(
            "evidence.apply_evidence_rerank", side_effect=lambda u, s, **k: u
        ), mock.patch("ask.generate_stream", return_value=iter(["ok"])):
            ask_fn("test question", evidence=True, top_k=5)
        store.__enter__.assert_called_once()
        store.__exit__.assert_called_once()

    @mock.patch("ask.query_units")
    @mock.patch("ask.load_config")
    def test_chroma_store_closed_on_rerank_error(self, mock_cfg, mock_q):
        from ask import ask as ask_fn

        store = mock.MagicMock()
        store.__enter__.return_value = store
        store.__exit__.return_value = None
        mock_q.return_value = [{"metadata": {"ledger_id": "sem_1"}, "score": 0.9, "document": "x"}]
        mock_cfg.return_value = {
            "index": {"chroma_dir": "/tmp/chroma-test"},
            "models": {
                "distill_model": "deepseek-v4-flash",
                "ollama_host": "http://localhost:11434",
            },
            "query": {},
        }

        def boom(*_a, **_k):
            raise RuntimeError("rerank failed")

        with mock.patch("chroma_store.ChromaStore", return_value=store), mock.patch(
            "evidence.apply_evidence_rerank", side_effect=boom
        ):
            with self.assertRaises(RuntimeError):
                ask_fn("test question", evidence=True, top_k=5)
        store.__exit__.assert_called_once()


if __name__ == "__main__":
    unittest.main()

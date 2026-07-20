"""Additional Phase A hermetic tests: validate, shadow lifecycle, config, metrics."""
# pylint: disable=duplicate-code


from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from eval_corpus.config_audit import config_diff_violations, query_time_data_dir_files
from eval_corpus.metrics import (
    expand_acceptable_ids,
    hit_at_k,
    mrr,
    ndcg_at_k,
    p_at_1,
    recall_at_k_complete,
)
from eval_corpus.reconstruct import RECIPE_ORDINARY, build_canonical_unit
from eval_corpus.shadow_build import (
    assert_complete_id_set,
    collection_metadata_from_manifest,
    plan_resume_adds,
    verify_collection_metadata_for_resume,
    write_build_manifest,
)
from eval_corpus.validate import historical_spot_check_plan, validate_overlap


class ValidateTests(unittest.TestCase):
    def test_overlap_pass_and_mismatch(self):
        units = [
            {
                "id": f"id{i}",
                "summary": f"s{i}",
                "keywords": ["k"],
                "tool": "t",
                "source_path": f"/tmp/{i}",
            }
            for i in range(45)
        ]
        live = {u["id"]: f"{u['summary']} k" for u in units}
        report = validate_overlap(units, live, capture_id="cap1")
        self.assertEqual(report["by_recipe"][RECIPE_ORDINARY]["status"], "PASS")

        live[units[0]["id"]] = "WRONG"
        report2 = validate_overlap(units, live, capture_id="cap1")
        # May be PASS if id0 not in sample — force mismatch on a sampled id
        sample = report2["by_recipe"][RECIPE_ORDINARY]["sample_ids"]
        if sample:
            live[sample[0]] = "WRONG"
            report3 = validate_overlap(units, live, capture_id="cap1")
            self.assertEqual(report3["by_recipe"][RECIPE_ORDINARY]["status"], "FAILED")

    def test_spot_check_deterministic(self):
        ids = [f"x{i}" for i in range(100)]
        a = historical_spot_check_plan(ids, capture_id="c", n=20)
        b = historical_spot_check_plan(ids, capture_id="c", n=20)
        self.assertEqual(a["sample_ids"], b["sample_ids"])
        self.assertEqual(len(a["sample_ids"]), 20)


class ShadowLifecycleTests(unittest.TestCase):
    def test_manifest_no_self_hash_and_collection_bind(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "build-manifest.json"
            manifest = {
                "embed_model": "nomic-embed-text",
                "embed_dimensions": 768,
                "unit_corpus_fingerprint": "abc",
                "unit_count": 2,
                "batch_size": 1,
                "schema_version": "1",
            }
            sha = write_build_manifest(path, manifest)
            self.assertNotIn("build_manifest_sha256", json.loads(path.read_text()))
            meta = collection_metadata_from_manifest(manifest, manifest_sha256=sha)
            self.assertEqual(meta["convmem:build_manifest_sha256"], sha)
            with self.assertRaises(ValueError):
                write_build_manifest(path, {**manifest, "build_manifest_sha256": "x"})

    def test_resume_row_safe(self):
        u1 = build_canonical_unit(
            {
                "id": "a",
                "summary": "s",
                "keywords": ["k"],
                "source_path": "/tmp/a",
                "tool": "t",
            }
        )
        u2 = build_canonical_unit(
            {
                "id": "b",
                "summary": "s2",
                "keywords": ["k"],
                "source_path": "/tmp/b",
                "tool": "t",
            }
        )
        pkg = {u1["id"]: u1, u2["id"]: u2}
        existing = {
            "a": {"document": u1["document"], "metadata": {"title": u1.get("title", ""), **{
                k: u1[k] for k in ("source_path", "tool", "keywords", "type") if k in u1
            }}},
        }
        # Fix metadata to exact normalized form
        from eval_corpus.reconstruct import normalized_shadow_metadata

        existing = {
            "a": {
                "document": u1["document"],
                "metadata": normalized_shadow_metadata(u1),
            }
        }
        skip, add, errors = plan_resume_adds(pkg, existing)
        self.assertEqual(errors, [])
        self.assertEqual(skip, ["a"])
        self.assertEqual(add, ["b"])

        bad = {
            "a": {"document": "nope", "metadata": normalized_shadow_metadata(u1)},
        }
        _, _, errors2 = plan_resume_adds(pkg, bad)
        self.assertTrue(errors2)

        assert_complete_id_set({"a", "b"}, {"a", "b"})
        with self.assertRaises(RuntimeError):
            assert_complete_id_set({"a", "b"}, {"a"})

    def test_metadata_resume_guard(self):
        errs = verify_collection_metadata_for_resume(
            {
                "convmem:embed_model": "nomic-embed-text",
                "convmem:unit_corpus_fingerprint": "fp",
                "convmem:embed_dimensions": 768,
                "convmem:build_manifest_sha256": "m",
                "convmem:package_sha256": "p",
                "convmem:batch_size": 1,
            },
            embed_model="nomic-embed-text",
            unit_corpus_fingerprint="fp",
            embed_dimensions=768,
            build_manifest_sha256="m",
            package_sha256="p",
            batch_size=1,
        )
        self.assertEqual(errs, [])
        errs2 = verify_collection_metadata_for_resume(
            {
                "convmem:embed_model": "other",
                "convmem:unit_corpus_fingerprint": "fp",
                "convmem:embed_dimensions": 768,
                "convmem:build_manifest_sha256": "m",
                "convmem:package_sha256": "p",
                "convmem:batch_size": 1,
            },
            embed_model="nomic-embed-text",
            unit_corpus_fingerprint="fp",
            embed_dimensions=768,
            build_manifest_sha256="m",
            package_sha256="p",
            batch_size=1,
        )
        self.assertTrue(errs2)


class ConfigAuditTests(unittest.TestCase):
    def test_allowlist(self):
        live = {"index": {"chroma_dir": "/live", "chunk_size": 60}, "models": {"embed_model": "nomic"}}
        shadow = {
            "index": {"chroma_dir": "/shadow", "chunk_size": 60},
            "models": {"embed_model": "qwen"},
        }
        self.assertEqual(config_diff_violations(live, shadow), [])
        shadow2 = {
            "index": {"chroma_dir": "/shadow", "chunk_size": 99},
            "models": {"embed_model": "qwen"},
        }
        self.assertTrue(config_diff_violations(live, shadow2))

    def test_pending_not_query_time(self):
        rows = query_time_data_dir_files()
        pending = next(r for r in rows if r["path_relative"] == "pending_decisions.jsonl")
        self.assertEqual(pending["query_time"], "no")
        approved = next(r for r in rows if r["path_relative"] == "decisions-approved.jsonl")
        self.assertEqual(approved["query_time"], "yes")


class MetricsTests(unittest.TestCase):
    def test_hit_mrr_recall_ndcg(self):
        relevant = [{"namespace": "ledger_id", "id": "dec_1", "grade": 3}]
        hits = [
            {"id": "u0", "metadata": {"ledger_id": "dec_other"}},
            {"id": "u1", "metadata": {"ledger_id": "dec_1"}},
        ]
        self.assertFalse(p_at_1(hits, relevant))
        self.assertTrue(hit_at_k(hits, relevant, 2))
        self.assertEqual(mrr(hits, relevant), 0.5)
        self.assertEqual(recall_at_k_complete(hits, relevant, 2), 1.0)
        self.assertGreater(ndcg_at_k(hits, relevant, 2), 0)
        row = {"acceptable_ids": ["dec_1"]}
        self.assertEqual(expand_acceptable_ids(row)[0]["namespace"], "ledger_id")


class QueryViewTests(unittest.TestCase):
    @patch("query.ollama_embed", return_value=[0.1, 0.2])
    @patch("query.open_chroma_for_read")
    @patch("query._ledger_lookup_hits")
    @patch("query._apply_keyword_rank", side_effect=lambda t, r: r)
    @patch("query._merge_priority_hits")
    def test_embedding_influenced_skips_ledger(
        self, merge, _kw, ledger_hits, open_chroma, _embed
    ):
        from query import query_units

        store = MagicMock()
        store.query_units.return_value = [
            {"id": "1", "distance": 0.1, "metadata": {"domain": "coding.tooling"}}
        ]
        open_chroma.return_value = store
        ledger_hits.return_value = [{"id": "ledger"}]
        merge.side_effect = lambda results, extras: results + extras

        cfg = {
            "models": {"embed_model": "nomic-embed-text", "ollama_host": "http://x", "rerank_model": "r"},
            "index": {"chroma_dir": "/tmp/chroma"},
            "query": {"rerank": False, "top_k_candidates": 5, "recency_weight": 0},
            "eval": {"retrieval_view": "embedding_influenced"},
        }
        with patch("rerank.rerank", side_effect=lambda _q, rows, _m, k: rows[:k]):
            out = query_units("q", top_k=5, cfg=cfg)
        ledger_hits.assert_not_called()
        merge.assert_not_called()
        self.assertEqual(len(out), 1)

    @patch("query.ollama_embed", return_value=[0.1, 0.2])
    @patch("query.open_chroma_for_read")
    @patch("query._ledger_lookup_hits")
    @patch("query._apply_keyword_rank", side_effect=lambda t, r: r)
    @patch("query._merge_priority_hits")
    def test_production_default_calls_ledger(
        self, merge, _kw, ledger_hits, open_chroma, _embed
    ):
        from query import query_units

        store = MagicMock()
        store.query_units.return_value = [
            {"id": "1", "distance": 0.1, "metadata": {}}
        ]
        open_chroma.return_value = store
        ledger_hits.return_value = []
        merge.side_effect = lambda results, extras: results

        cfg = {
            "models": {"embed_model": "nomic-embed-text", "ollama_host": "http://x", "rerank_model": "r"},
            "index": {"chroma_dir": "/tmp/chroma"},
            "query": {"rerank": False, "top_k_candidates": 5, "recency_weight": 0},
        }
        with patch("rerank.rerank", side_effect=lambda _q, rows, _m, k: rows[:k]):
            query_units("q", top_k=5, cfg=cfg)
        ledger_hits.assert_called()
        merge.assert_called()


class DoctorEmbedIdentityTests(unittest.TestCase):
    def test_legacy_warn(self):
        from doctor import DoctorCheck, _check_embed_collection_identity

        cfg = {
            "index": {"chroma_dir": "/tmp/missing-chroma-xyz"},
            "models": {"embed_model": "nomic-embed-text"},
        }
        check = _check_embed_collection_identity(cfg)
        self.assertIsInstance(check, DoctorCheck)
        self.assertEqual(check.effective_status(), "warn")

    def test_schema_incompatible_sqlite_warns_not_raises(self):
        """A chroma.sqlite3 without collection_metadata must WARN, not crash.

        Regression guard: sqlite3.OperationalError ('no such table:
        collection_metadata') must stay inside doctor's containment boundary.
        """
        import sqlite3

        from doctor import DoctorCheck, _check_embed_collection_identity

        with tempfile.TemporaryDirectory() as td:
            chroma_dir = Path(td)
            conn = sqlite3.connect(chroma_dir / "chroma.sqlite3")
            try:
                conn.execute("CREATE TABLE unrelated (x INTEGER)")
                conn.commit()
            finally:
                conn.close()
            cfg = {
                "index": {"chroma_dir": str(chroma_dir)},
                "models": {"embed_model": "nomic-embed-text"},
            }
            check = _check_embed_collection_identity(cfg)
            self.assertIsInstance(check, DoctorCheck)
            self.assertEqual(check.effective_status(), "warn")
            self.assertIn("cannot read collection metadata", check.detail)


class CaptureFixtureTests(unittest.TestCase):
    def test_capture_export_processed_hermetic(self):
        from eval_corpus.capture import capture_export_and_processed

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            export = root / "knowledge_units.jsonl"
            processed = root / "processed.json"
            export.write_text(
                json.dumps({"id": "a", "summary": "s"}) + "\n", encoding="utf-8"
            )
            processed.write_text("{}", encoding="utf-8")
            cap = root / "capture"
            report = capture_export_and_processed(
                export_src=export,
                processed_src=processed,
                capture_dir=cap,
            )
            self.assertEqual(report["status"], "OK")
            self.assertTrue((cap / "knowledge_units.jsonl").is_file())


if __name__ == "__main__":
    unittest.main()

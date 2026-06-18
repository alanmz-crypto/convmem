"""Tests for refine jobs (F1)."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from chroma_store import ChromaStore
from refine import (
    _pick_canonical,
    job_chroma_dedupe,
    job_confidence_audit,
    job_redistill,
    job_semantic_dedupe,
    load_stats,
    save_stats,
)


class RefineJobTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.chroma_dir = root / "chroma"
        self.chroma_dir.mkdir()
        self.store = ChromaStore(str(self.chroma_dir))
        self.cfg = {
            "index": {
                "chroma_dir": str(self.chroma_dir),
                "processed_log": str(root / "processed.json"),
            },
            "refine": {"batch_size": 10, "min_confidence_redistill": 0.6},
            "models": {
                "distill_model": "deepseek-v4-flash",
                "ollama_host": "http://localhost:11434",
                "deepseek_base_url": "https://api.deepseek.com",
            },
        }
        self.store.add_unit(
            "u1",
            "doc a",
            [1.0, 0.0],
            {
                "id": "u1",
                "ledger_id": "obs_dup",
                "confidence": 0.5,
                "timestamp": "2026-01-01T00:00:00Z",
                "title": "A",
            },
        )
        self.store.add_unit(
            "u2",
            "doc b",
            [1.0, 0.0],
            {
                "id": "u2",
                "ledger_id": "obs_dup",
                "confidence": 0.9,
                "timestamp": "2026-06-01T00:00:00Z",
                "title": "B",
            },
        )

    def tearDown(self):
        self.tmp.cleanup()

    def test_pick_canonical_prefers_confidence(self):
        group = [
            {"id": "u1", "confidence": 0.5, "timestamp": "2026-06-01"},
            {"id": "u2", "confidence": 0.9, "timestamp": "2026-01-01"},
        ]
        self.assertEqual(_pick_canonical(group)["id"], "u2")

    def test_chroma_dedupe_tombstones_orphan(self):
        stats = job_chroma_dedupe(self.store, self.cfg, verbose=False)
        self.assertEqual(stats["tombstoned"], 1)
        orphan = self.store.get_unit("u1")
        assert orphan is not None
        self.assertTrue(orphan["metadata"]["superseded"])
        self.assertEqual(orphan["metadata"]["superseded_by"], "u2")

    def test_chroma_dedupe_idempotent(self):
        job_chroma_dedupe(self.store, self.cfg, verbose=False)
        stats2 = job_chroma_dedupe(self.store, self.cfg, verbose=False)
        self.assertEqual(stats2["tombstoned"], 0)

    def test_confidence_audit_writes_stats(self):
        self.store.add_unit(
            "u3",
            "low",
            [0.0, 1.0],
            {"id": "u3", "confidence": 0.4, "title": "low"},
        )
        job_confidence_audit(self.store, self.cfg, verbose=False)
        stats = load_stats(self.cfg)
        self.assertIn("confidence_audit", stats)
        self.assertIn("histogram", stats["confidence_audit"])

    def test_redistill_exits_without_audit(self):
        stats_path = Path(self.cfg["index"]["chroma_dir"]).parent / "refine_stats.json"
        if stats_path.is_file():
            stats_path.unlink()
        with mock.patch.object(sys, "exit") as mock_exit:
            mock_exit.side_effect = SystemExit(1)
            with self.assertRaises(SystemExit):
                job_redistill(self.store, self.cfg, verbose=False)
            mock_exit.assert_called_once_with(1)

    def test_redistill_after_audit(self):
        save_stats(self.cfg, {"confidence_audit": {"histogram": {"0.5": 1}}})
        stats = job_redistill(self.store, self.cfg, limit=5, verbose=False)
        self.assertIn("processed", stats)


class SemanticDedupeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.chroma_dir = root / "chroma"
        self.chroma_dir.mkdir()
        self.store = ChromaStore(str(self.chroma_dir))
        self.cfg = {
            "index": {
                "chroma_dir": str(self.chroma_dir),
                "processed_log": str(root / "processed.json"),
            },
            "refine": {"batch_size": 10, "dedupe_similarity": 0.92},
            "models": {},
        }

    def tearDown(self):
        self.tmp.cleanup()

    def test_semantic_dedupe_uses_public_embedding_api(self):
        self.store.add_unit(
            "sim-a",
            "similar a",
            [1.0, 0.01],
            {"id": "sim-a", "domain": "coding.tooling", "title": "A"},
        )
        self.store.add_unit(
            "sim-b",
            "similar b",
            [1.0, 0.02],
            {"id": "sim-b", "domain": "coding.tooling", "title": "B"},
        )
        stats = job_semantic_dedupe(self.store, self.cfg, limit=1, verbose=False)
        self.assertGreaterEqual(stats["queued"], 1)
        queue_path = Path(self.cfg["index"]["chroma_dir"]).parent / "dedupe_queue.jsonl"
        self.assertTrue(queue_path.is_file())


class ChromaDedupeIdMismatchTests(unittest.TestCase):
    """Regression: metadata.id ≠ Chroma row id (legacy / upsert artifact)."""

    def test_chroma_dedupe_metadata_id_mismatch(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            chroma_dir = root / "chroma"
            chroma_dir.mkdir()
            store = ChromaStore(str(chroma_dir))
            cfg = {
                "index": {"chroma_dir": str(chroma_dir), "processed_log": str(root / "p.json")},
                "refine": {},
                "models": {},
            }
            store.add_unit(
                "real-chroma-uuid",
                "orphan doc",
                [1.0, 0.0],
                {
                    "id": "wrong-metadata-id",
                    "ledger_id": "obs_mismatch",
                    "confidence": 0.4,
                    "timestamp": "2026-01-01T00:00:00Z",
                    "title": "orphan",
                },
            )
            store.add_unit(
                "canonical-uuid",
                "canonical doc",
                [1.0, 0.0],
                {
                    "id": "also-wrong-id",
                    "ledger_id": "obs_mismatch",
                    "confidence": 0.95,
                    "timestamp": "2026-06-01T00:00:00Z",
                    "title": "canonical",
                },
            )
            stats = job_chroma_dedupe(store, cfg, verbose=False)
            self.assertEqual(stats["tombstoned"], 1)
            orphan = store.get_unit("real-chroma-uuid")
            assert orphan is not None
            self.assertTrue(orphan["metadata"]["superseded"])
            self.assertEqual(orphan["metadata"]["superseded_by"], "canonical-uuid")
            stats2 = job_chroma_dedupe(store, cfg, verbose=False)
            self.assertEqual(stats2["tombstoned"], 0)


if __name__ == "__main__":
    unittest.main()

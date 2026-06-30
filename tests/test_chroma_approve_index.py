"""Regression: approve-index upsert on non-empty PersistentClient corpus (live HNSW)."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from chroma_store import ChromaStore
from propose_decision import ingest_approved_ledger


def _fake_embed(text: str, model=None, host=None) -> list[float]:
    base = (sum(ord(c) for c in text) % 997) / 997.0
    return [base] * 768


class ChromaApproveIndexTests(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.chroma_dir = str(Path(self.td.name) / "chroma")
        self.cfg = {
            "index": {"chroma_dir": self.chroma_dir},
            "models": {
                "embed_model": "nomic-embed-text",
                "ollama_host": "http://localhost:11434",
            },
        }
        store = ChromaStore(self.chroma_dir)
        for i in range(3):
            store.add_unit(
                f"seed-{i}",
                f"seed document {i}",
                [0.1 * (i + 1)] * 768,
                {
                    "id": f"seed-{i}",
                    "title": f"Seed {i}",
                    "ledger_id": f"obs_seed_{i}",
                    "type": "observation",
                },
            )
        store.close()
        self.assertEqual(ChromaStore(self.chroma_dir).count_units(), 3)

    def tearDown(self):
        self.td.cleanup()

    @patch("llm.ollama_embed", side_effect=_fake_embed)
    def test_ingest_approved_ledger_upsert_nonempty_corpus(self, _mock_embed):
        ledger = {
            "id": "dec_test_nonempty_upsert",
            "kind": "decision",
            "ledger_id": "dec_test_nonempty_upsert",
            "status": "accepted",
            "relates_to": "obs_seed_0",
            "summary": "Approve path on seeded corpus",
            "rationale": "Regression for SegmentAPI upsert failure on live HNSW",
            "author_model": "ryan",
            "domain": "coding.tooling",
            "confidence": 0.8,
        }
        stats = ingest_approved_ledger(self.cfg, ledger)
        self.assertEqual(stats["accepted"], 1)
        store = ChromaStore(self.chroma_dir)
        try:
            self.assertEqual(store.count_units(), 4)
            found = [
                m
                for m in store.units_metadata()
                if m.get("ledger_id") == "dec_test_nonempty_upsert"
            ]
            self.assertEqual(len(found), 1)
        finally:
            store.close()

    @patch("llm.ollama_embed", side_effect=_fake_embed)
    def test_add_unit_upsert_after_seed(self, _mock_embed):
        store = ChromaStore(self.chroma_dir)
        try:
            store.add_unit(
                "dec_direct_upsert",
                "direct upsert after seed",
                [0.3] * 768,
                {
                    "id": "dec_direct_upsert",
                    "title": "Direct upsert",
                    "ledger_id": "dec_direct_upsert",
                    "type": "decision",
                },
            )
            self.assertEqual(store.count_units(), 4)
        finally:
            store.close()


if __name__ == "__main__":
    unittest.main()

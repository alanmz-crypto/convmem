"""Tests for convmem add --upsert (Milestone C2/C3)."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from chroma_store import ChromaStore
from observe import ingest_observation, ingest_observation_file


def _fake_embed(text: str, model=None, host=None) -> list[float]:
    base = (sum(ord(c) for c in text) % 997) / 997.0
    return [base] * 768


_RECORD = {
    "id": "obs_staging2_lh_csp-missing",
    "kind": "observation",
    "domain": "web_stack.security",
    "author_model": "lighthouse-ci",
    "site": "staging2.willowyhollow.com",
    "severity": "medium",
    "summary": "Missing CSP header",
}


class UpsertTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = ChromaStore(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    @patch("llm.ollama_embed", side_effect=_fake_embed)
    def test_upsert_keeps_unit_count(self, _mock):
        ingest_observation(
            _RECORD,
            store=self.store,
            embed_model="test",
            ollama_host="local",
        )
        self.assertEqual(self.store.count_units(), 1)

        updated = {**_RECORD, "summary": "Missing CSP and COOP headers"}
        ingest_observation(
            updated,
            store=self.store,
            embed_model="test",
            ollama_host="local",
            upsert=True,
        )
        self.assertEqual(self.store.count_units(), 1)

    @patch("llm.ollama_embed", side_effect=_fake_embed)
    def test_upsert_updates_document_and_embedding(self, mock_embed):
        ingest_observation(
            _RECORD,
            store=self.store,
            embed_model="test",
            ollama_host="local",
        )
        unit = self.store.get_unit(
            self.store.units_metadata()[0]["id"]
        )
        assert unit is not None
        first_doc = unit["document"]

        updated = {**_RECORD, "summary": "Missing CSP and COOP headers"}
        ingest_observation(
            updated,
            store=self.store,
            embed_model="test",
            ollama_host="local",
            upsert=True,
        )
        unit2 = self.store.get_unit(unit["id"])
        assert unit2 is not None
        self.assertIn("COOP", unit2["document"])
        self.assertNotEqual(unit2["document"], first_doc)
        self.assertEqual(mock_embed.call_count, 2)

    @patch("llm.ollama_embed", side_effect=_fake_embed)
    def test_file_ingest_twice_stats(self, _mock):
        path = Path(self.tmp.name) / "obs.jsonl"
        path.write_text(json.dumps(_RECORD) + "\n", encoding="utf-8")

        r1 = ingest_observation_file(
            str(path),
            store=self.store,
            embed_model="test",
            ollama_host="local",
            verbose=False,
        )
        self.assertEqual(r1["accepted"], 1)
        self.assertEqual(self.store.count_units(), 1)

        r2 = ingest_observation_file(
            str(path),
            store=self.store,
            embed_model="test",
            ollama_host="local",
            verbose=False,
            upsert=True,
        )
        self.assertEqual(r2["skipped"], 1)
        self.assertEqual(r2["accepted"], 0)
        self.assertEqual(r2["updated"], 0)
        self.assertEqual(self.store.count_units(), 1)

    @patch("llm.ollama_embed", side_effect=_fake_embed)
    def test_upsert_skips_unchanged_reembed(self, mock_embed):
        ingest_observation(
            _RECORD,
            store=self.store,
            embed_model="test",
            ollama_host="local",
        )
        ingest_observation(
            _RECORD,
            store=self.store,
            embed_model="test",
            ollama_host="local",
            upsert=True,
        )
        self.assertEqual(mock_embed.call_count, 1)


if __name__ == "__main__":
    unittest.main()

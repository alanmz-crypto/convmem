"""Ledger unit document text and empty-document repair."""

from __future__ import annotations

import tempfile
import unittest
from unittest.mock import patch

from chroma_store import ChromaStore
from ledger import ledger_unit_document, normalize_ledger_record
from observe import ingest_observation, repair_empty_ledger_documents


def _fake_embed(text: str, model=None, host=None) -> list[float]:
    base = (sum(ord(c) for c in text) % 997) / 997.0
    return [base] * 768


_DECISION = {
    "id": "dec_prop_test_empty_doc",
    "kind": "decision",
    "status": "accepted",
    "relates_to": "dec_prop_parent_001",
    "summary": "Protocol fallback root for session close relates-to",
    "rationale": "Anchor decision for convmem record blocks.",
    "author_model": "ryan",
    "domain": "coding.tooling",
    "confidence": 0.8,
    "timestamp": "2026-06-23T16:16:38Z",
    "tool": "ryan",
}


class LedgerUnitDocumentTests(unittest.TestCase):
    def test_document_includes_summary_and_rationale(self):
        unit = normalize_ledger_record(_DECISION, min_confidence=0.0)
        assert unit is not None
        doc = ledger_unit_document(unit)
        self.assertIn("Protocol fallback root", doc)
        self.assertIn("Rationale:", doc)
        self.assertIn("convmem record", doc)


class EmptyDocumentRepairTests(unittest.TestCase):
    @patch("llm.ollama_embed", side_effect=_fake_embed)
    def test_upsert_repairs_empty_document_when_metadata_unchanged(self, _mock):
        tmp = tempfile.TemporaryDirectory()
        store = ChromaStore(tmp.name)
        try:
            ingest_observation(
                _DECISION,
                store=store,
                embed_model="test",
                ollama_host="local",
            )
            chroma_id = store.units_metadata()[0]["id"]
            store.update_unit(chroma_id, "", [0.1] * 768, store.units_metadata()[0])

            unit = store.get_unit(chroma_id)
            assert unit is not None
            self.assertEqual(unit.get("document"), "")

            ingest_observation(
                {**_DECISION, "_governed_protocol": True, "proposal_id": "dec_prop_repair"},
                store=store,
                embed_model="test",
                ollama_host="local",
                upsert=True,
            )
            unit2 = store.get_unit(chroma_id)
            assert unit2 is not None
            self.assertIn("Protocol fallback root", unit2["document"])
        finally:
            store.close()
            tmp.cleanup()

    @patch("ledger_recent.load_approved_decision_by_id", return_value=_DECISION)
    @patch("llm.ollama_embed", side_effect=_fake_embed)
    def test_repair_empty_ledger_documents(self, _mock, _load):
        tmp = tempfile.TemporaryDirectory()
        store = ChromaStore(tmp.name)
        try:
            ingest_observation(
                _DECISION,
                store=store,
                embed_model="test",
                ollama_host="local",
            )
            chroma_id = store.units_metadata()[0]["id"]
            store.update_unit(chroma_id, "", [0.1] * 768, store.units_metadata()[0])

            cfg = {
                "models": {"embed_model": "test", "ollama_host": "local"},
                "index": {"chroma_dir": tmp.name},
            }
            stats = repair_empty_ledger_documents(cfg, verbose=False)
            self.assertEqual(stats["empty"], 1)
            self.assertEqual(stats["repaired"], 1)

            unit = store.get_unit(chroma_id)
            assert unit is not None
            self.assertIn("Protocol fallback root", unit["document"])
        finally:
            store.close()
            tmp.cleanup()


if __name__ == "__main__":
    unittest.main()

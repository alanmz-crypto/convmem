"""Tests for tombstone filtering in chroma_store (F1)."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from chroma_store import ChromaStore, is_superseded


class SupersededFilterTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        chroma = Path(self.tmp.name) / "chroma"
        chroma.mkdir()
        self.store = ChromaStore(str(chroma))
        self.store.add_unit(
            "canonical",
            "csp missing",
            [1.0, 0.0],
            {
                "id": "canonical",
                "title": "Missing CSP",
                "domain": "web_stack.security",
                "ledger_id": "obs001",
                "confidence": 0.9,
            },
        )
        self.store.add_unit(
            "twin",
            "csp missing duplicate",
            [1.0, 0.0],
            {
                "id": "twin",
                "title": "Missing CSP dup",
                "domain": "web_stack.security",
                "ledger_id": "obs001",
                "confidence": 0.5,
                "superseded": True,
                "superseded_by": "canonical",
            },
        )

    def tearDown(self):
        self.tmp.cleanup()

    def test_is_superseded(self):
        self.assertTrue(is_superseded({"superseded": True}))
        self.assertFalse(is_superseded({"superseded": False}))
        self.assertFalse(is_superseded({}))

    def test_delete_units_for_source(self):
        self.store.add_unit(
            "u1",
            "doc",
            [1.0, 0.0],
            {"id": "u1", "title": "a", "source_path": "/tmp/chat.jsonl"},
        )
        self.store.add_unit(
            "u2",
            "doc",
            [1.0, 0.0],
            {"id": "u2", "title": "b", "source_path": "/other.jsonl"},
        )
        n = self.store.delete_units_for_source("/tmp/chat.jsonl")
        self.assertEqual(n, 1)
        ids = {m["id"] for m in self.store.units_metadata(include_superseded=True)}
        self.assertNotIn("u1", ids)
        self.assertIn("u2", ids)

    def test_supersede_units_for_source(self):
        src = "/tmp/findings.md"
        self.store.add_unit(
            "f1",
            "finding one",
            [1.0, 0.0],
            {"id": "f1", "title": "1", "source_path": src},
        )
        self.store.add_unit(
            "f2",
            "finding two",
            [1.0, 0.0],
            {"id": "f2", "title": "2", "source_path": src},
        )
        n = self.store.supersede_units_for_source(src, superseded_by="findings@v2")
        self.assertEqual(n, 2)
        active = {m["id"] for m in self.store.units_metadata(include_superseded=False)}
        self.assertEqual(active, {"canonical"})
        twin = self.store.get_unit("f1")
        assert twin is not None
        self.assertTrue(twin["metadata"]["superseded"])
        self.assertEqual(twin["metadata"]["superseded_by"], "findings@v2")

        metas = self.store.units_metadata(include_superseded=False)
        ids = {m["id"] for m in metas}
        self.assertIn("canonical", ids)
        self.assertNotIn("twin", ids)

    def test_units_metadata_include_all(self):
        metas = self.store.units_metadata(include_superseded=True)
        self.assertEqual(len(metas), 2)

    def test_count_units_excludes_tombstone(self):
        self.assertEqual(self.store.count_units(include_superseded=False), 1)
        self.assertEqual(self.store.count_units(include_superseded=True), 2)

    def test_get_unit_returns_tombstone(self):
        hit = self.store.get_unit("twin")
        assert hit is not None
        self.assertTrue(hit["metadata"]["superseded"])

    def test_units_metadata_binds_chroma_id(self):
        self.store.add_unit(
            "chroma-abc",
            "doc",
            [1.0, 0.0],
            {"id": "stale-in-meta", "title": "x"},
        )
        metas = self.store.units_metadata(include_superseded=True)
        row = next(m for m in metas if m.get("title") == "x")
        self.assertEqual(row["id"], "chroma-abc")
        results = self.store.query_units([1.0, 0.0], top_k=5, include_superseded=False)
        ids = {r["id"] for r in results}
        self.assertIn("canonical", ids)
        self.assertNotIn("twin", ids)

    def test_get_units_with_embeddings_excludes_tombstone(self):
        rows = self.store.get_units_with_embeddings(include_superseded=False)
        ids = {r["id"] for r in rows}
        self.assertIn("canonical", ids)
        self.assertNotIn("twin", ids)
        for row in rows:
            self.assertEqual(row["metadata"]["id"], row["id"])
            self.assertIsInstance(row["embedding"], list)

    def test_get_units_with_embeddings_include_all(self):
        rows = self.store.get_units_with_embeddings(include_superseded=True)
        self.assertEqual(len(rows), 2)


if __name__ == "__main__":
    unittest.main()

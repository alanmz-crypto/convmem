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

    def test_preview_supersede_active_only_and_read_only(self):
        src = "/tmp/findings.md"
        self.store.add_unit(
            "p1",
            "finding one",
            [1.0, 0.0],
            {"id": "p1", "title": "One", "source_path": src, "created_at": "2026-06-01"},
        )
        self.store.add_unit(
            "p2",
            "finding two",
            [1.0, 0.0],
            {"id": "p2", "title": "Two", "source_path": src},  # no created_at — tolerated
        )
        self.store.add_unit(
            "p3",
            "already gone",
            [1.0, 0.0],
            {"id": "p3", "title": "Old", "source_path": src, "superseded": True},
        )
        preview = self.store.preview_supersede_for_source(src)
        self.assertEqual({u["id"] for u in preview}, {"p1", "p2"})  # p3 excluded
        by_id = {u["id"]: u for u in preview}
        self.assertEqual(by_id["p1"]["created_at"], "2026-06-01")
        self.assertEqual(by_id["p2"]["created_at"], "")  # missing field defaulted
        self.assertEqual(by_id["p1"]["title"], "One")
        # Read-only proof: nothing got tombstoned or removed by previewing.
        active = {m["id"] for m in self.store.units_metadata(include_superseded=False)}
        self.assertEqual(active, {"canonical", "p1", "p2"})

    def test_preview_matches_actual_tombstone_set(self):
        src = "/tmp/audit.md"
        for uid in ("a1", "a2", "a3"):
            self.store.add_unit(
                uid, "doc", [1.0, 0.0], {"id": uid, "title": uid, "source_path": src}
            )
        previewed = {u["id"] for u in self.store.preview_supersede_for_source(src)}
        n = self.store.supersede_units_for_source(src, superseded_by="audit@v2")
        self.assertEqual(n, len(previewed))
        tombstoned = {
            m["id"]
            for m in self.store.units_metadata(include_superseded=True)
            if is_superseded(m) and m.get("superseded_by") == "audit@v2"
        }
        self.assertEqual(tombstoned, previewed)

    def test_preview_empty_for_unknown_source(self):
        self.assertEqual(self.store.preview_supersede_for_source("/nope.md"), [])

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

    def test_forget_undo_clears_superseded_and_is_reversible(self):
        """Simulate the exact CLI forget --undo path."""
        from datetime import datetime, timezone

        from chroma_store import invalidate_superseded_cache

        # Verify twin starts superseded
        self.assertTrue(is_superseded(self.store.get_unit("twin")["metadata"]))
        self.assertEqual(self.store.count_units(include_superseded=False), 1)

        # Simulate forget --undo: full meta copy, overwrite keys
        meta = dict(self.store.get_unit("twin")["metadata"])
        now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        meta["superseded"] = False
        meta["superseded_by"] = ""
        meta["updated_at"] = now
        self.store.update_unit_metadata("twin", meta)
        invalidate_superseded_cache(self.store.chroma_dir)

        # Verify: is_superseded now False, unit is active in search
        restored = self.store.get_unit("twin")
        assert restored is not None
        self.assertFalse(is_superseded(restored["metadata"]))
        self.assertEqual(restored["metadata"]["superseded_by"], "")
        self.assertEqual(restored["metadata"]["updated_at"], now)

        # All original keys preserved? The unit had domain, title, ledger_id
        self.assertEqual(restored["metadata"].get("domain"), "web_stack.security")
        self.assertEqual(restored["metadata"].get("title"), "Missing CSP dup")
        self.assertEqual(restored["metadata"].get("ledger_id"), "obs001")

        # Unit should now appear in active search results
        active_ids = {m["id"] for m in self.store.units_metadata(include_superseded=False)}
        self.assertIn("twin", active_ids)
        self.assertEqual(self.store.count_units(include_superseded=False), 2)

        # Re-tombstone works (reversible cycle)
        meta2 = dict(self.store.get_unit("twin")["metadata"])
        meta2["superseded"] = True
        meta2["superseded_by"] = "forget-cli:test"
        meta2["updated_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        self.store.update_unit_metadata("twin", meta2)
        invalidate_superseded_cache(self.store.chroma_dir)
        self.assertTrue(is_superseded(self.store.get_unit("twin")["metadata"]))
        self.assertEqual(self.store.count_units(include_superseded=False), 1)


if __name__ == "__main__":
    unittest.main()

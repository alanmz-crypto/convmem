"""Tests for ChromaStore._flatten orphan-document guard (P0-A)."""

from __future__ import annotations

import unittest

from chroma_store import ChromaStore


class FlattenOrphanGuardTests(unittest.TestCase):
    def test_skips_none_document_rows(self):
        res = {
            "ids": [["good", "orphan", "also-good"]],
            "documents": [["valid text", None, "other"]],
            "metadatas": [[{"title": "a"}, None, {"title": "b"}]],
            "distances": [[0.1, 0.2, 0.3]],
        }
        out = ChromaStore._flatten(res)
        self.assertEqual([r["id"] for r in out], ["good", "also-good"])
        self.assertEqual(out[0]["document"], "valid text")
        self.assertEqual(out[1]["document"], "other")
        self.assertNotIn("orphan", [r["id"] for r in out])

    def test_does_not_coalesce_none_to_empty_string(self):
        res = {
            "ids": [["only-orphan"]],
            "documents": [[None]],
            "metadatas": [[None]],
            "distances": [[0.5]],
        }
        out = ChromaStore._flatten(res)
        self.assertEqual(out, [])

    def test_keeps_rows_with_empty_string_document(self):
        res = {
            "ids": [["empty-doc"]],
            "documents": [[""]],
            "metadatas": [[{"title": "t"}]],
            "distances": [[0.4]],
        }
        out = ChromaStore._flatten(res)
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0]["document"], "")

    def test_normalizes_none_metadata_to_empty_dict_for_kept_rows(self):
        res = {
            "ids": [["meta-none"]],
            "documents": [["body"]],
            "metadatas": [[None]],
            "distances": [[0.2]],
        }
        out = ChromaStore._flatten(res)
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0]["metadata"], {})


if __name__ == "__main__":
    unittest.main()

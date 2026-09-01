"""Tests for ChromaStore._flatten orphan-document guard (P0-A)."""

# pylint: disable=protected-access

from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

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

    def test_units_metadata_reads_in_pages(self):
        collection = MagicMock()
        collection.get.side_effect = [
            {
                "ids": ["u1", "u2"],
                "metadatas": [{"title": "one"}, {"title": "two"}],
            },
            {"ids": ["u3"], "metadatas": [{"title": "three"}]},
        ]
        store = ChromaStore.__new__(ChromaStore)
        store._collection = MagicMock(return_value=collection)

        with patch("chroma_store._METADATA_PAGE_SIZE", 2):
            rows = store.units_metadata()

        self.assertEqual([row["id"] for row in rows], ["u1", "u2", "u3"])
        self.assertEqual(
            [call.kwargs for call in collection.get.call_args_list],
            [
                {"include": ["metadatas"], "limit": 2, "offset": 0},
                {"include": ["metadatas"], "limit": 2, "offset": 2},
            ],
        )


if __name__ == "__main__":
    unittest.main()

"""Read-only Chroma facade for ledger commands (Codex sandbox safe)."""

from __future__ import annotations

import tempfile
import unittest

from chroma_readonly import ReadonlyUnitStore, collection_metadata_rows
from unresolved import list_unresolved


class TestReadonlyUnitStore(unittest.TestCase):
    def test_list_unresolved_on_live_corpus_if_present(self):
        import os
        from config import load_config

        chroma_dir = load_config()["index"]["chroma_dir"]
        if not os.path.isdir(chroma_dir):
            self.skipTest("no chroma dir")
        store = ReadonlyUnitStore(chroma_dir)
        metas = store.units_metadata()
        self.assertGreater(len(metas), 0)
        results = list_unresolved(store)
        self.assertIsInstance(results, list)

    def test_get_unit_by_ledger_id(self):
        store = ReadonlyUnitStore.__new__(ReadonlyUnitStore)
        store._metas = [
            {
                "id": "uuid-1",
                "ledger_id": "obs_test",
                "ledger_kind": "observation",
                "type": "observation",
                "title": "Test obs",
            }
        ]
        store._units = {
            "uuid-1": {
                "id": "uuid-1",
                "metadata": store._metas[0],
                "document": "Test obs",
            }
        }
        hit = store.get_unit("obs_test")
        self.assertIsNotNone(hit)
        self.assertEqual(hit["metadata"]["ledger_id"], "obs_test")


if __name__ == "__main__":
    unittest.main()

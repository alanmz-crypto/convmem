"""Tests for the doctor active-index/history diagnostic."""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from doctor import _check_index_drift


class IndexDriftTests(unittest.TestCase):
    @patch("doctor.collection_ids", return_value=["active-1", "active-2"])
    def test_export_history_does_not_reduce_active_coverage(self, _mock_ids):
        with tempfile.TemporaryDirectory() as d:
            export = Path(d) / "knowledge_units.jsonl"
            export.write_text(
                "\n".join(
                    json.dumps({"id": uid})
                    for uid in ("historical-1", "active-1", "active-2")
                )
                + "\n",
                encoding="utf-8",
            )
            check = _check_index_drift(
                {
                    "index": {
                        "chroma_dir": str(Path(d) / "chroma"),
                        "units_export": str(export),
                    }
                }
            )

        self.assertTrue(check.ok)
        self.assertEqual(check.effective_status(), "pass")
        self.assertIn("100% active coverage", check.detail)
        self.assertIn("1 historical-only", check.detail)

    @patch("doctor.collection_ids", return_value=[f"active-{i}" for i in range(600)])
    def test_collection_identity_mismatch_fails(self, _mock_ids):
        with tempfile.TemporaryDirectory() as d:
            export = Path(d) / "knowledge_units.jsonl"
            export.write_text(
                "\n".join(json.dumps({"id": f"history-{i}"}) for i in range(600)) + "\n",
                encoding="utf-8",
            )
            check = _check_index_drift(
                {
                    "index": {
                        "chroma_dir": str(Path(d) / "chroma"),
                        "units_export": str(export),
                    }
                }
            )

        self.assertFalse(check.ok)
        self.assertIn("identity mismatch", check.detail)


if __name__ == "__main__":
    unittest.main()

"""Tests for processed.json load behavior."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from ingest import load_processed


class LoadProcessedTests(unittest.TestCase):
    def test_missing_file_returns_empty(self):
        with tempfile.TemporaryDirectory() as td:
            self.assertEqual(load_processed(str(Path(td) / "missing.json")), {})

    def test_valid_file_loads(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "processed.json"
            p.write_text(json.dumps({"abc": {"path": "/tmp/x"}}))
            self.assertEqual(load_processed(str(p)), {"abc": {"path": "/tmp/x"}})

    def test_corrupt_file_raises(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "processed.json"
            p.write_text('{"truncated": ')
            with self.assertRaises(RuntimeError) as ctx:
                load_processed(str(p))
            self.assertIn("corrupt", str(ctx.exception).lower())


if __name__ == "__main__":
    unittest.main()

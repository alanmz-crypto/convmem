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

    def test_save_processed_atomic_replace(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "processed.json"
            from ingest import save_processed

            save_processed(str(p), {"a": {"path": "/x"}})
            self.assertEqual(json.loads(p.read_text()), {"a": {"path": "/x"}})
            save_processed(str(p), {"b": {"path": "/y"}})
            self.assertEqual(json.loads(p.read_text()), {"b": {"path": "/y"}})
            self.assertFalse(p.with_suffix(p.suffix + ".tmp").exists())

    def test_save_processed_does_not_follow_fixed_temp_symlink(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            p = root / "processed.json"
            target = root / "unrelated"
            target.write_text("keep", encoding="utf-8")
            p.with_suffix(p.suffix + ".tmp").symlink_to(target)

            from ingest import save_processed

            save_processed(str(p), {"safe": {"path": "/x"}})

            self.assertEqual(target.read_text(encoding="utf-8"), "keep")
            self.assertTrue(p.with_suffix(p.suffix + ".tmp").is_symlink())


if __name__ == "__main__":
    unittest.main()

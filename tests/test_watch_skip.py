"""Tests for watch skip preflight (hash compare when path known)."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from ingest import sha256_file, watch_skip_reason
from watch import flush_path


class WatchSkipReasonTests(unittest.TestCase):
    def test_path_known_same_hash_skips(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "sess.jsonl"
            path.write_text('{"role":"user","content":"x"}\n')
            path_str = str(path.resolve())
            file_hash = sha256_file(str(path))
            processed = {file_hash: {"path": path_str}}
            with mock.patch("ingest.sha256_file", wraps=sha256_file) as mock_hash:
                reason = watch_skip_reason(path, processed=processed)
                self.assertEqual(mock_hash.call_count, 1)
            self.assertEqual(reason, "unchanged")

    def test_path_known_hash_changed_allows(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "sess.jsonl"
            path.write_text('{"role":"user","content":"x"}\n')
            path_str = str(path.resolve())
            processed = {"oldhash": {"path": path_str}}
            reason = watch_skip_reason(path, processed=processed)
            self.assertIsNone(reason)

    def test_hash_only_entry_needs_one_hash(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "sess.jsonl"
            path.write_text('{"role":"user","content":"x"}\n')
            file_hash = sha256_file(str(path))
            processed = {file_hash: {}}
            with mock.patch("ingest.sha256_file", wraps=sha256_file) as mock_hash:
                reason = watch_skip_reason(path, processed=processed)
                self.assertEqual(mock_hash.call_count, 1)
            self.assertEqual(reason, "unchanged")

    def test_excluded_by_path_without_hash(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "skip.jsonl"
            path.write_text("data\n")
            path_str = str(path.resolve())
            processed = {"x": {"path": path_str, "excluded": True}}
            with mock.patch("ingest.sha256_file") as mock_hash:
                reason = watch_skip_reason(path, processed=processed)
                mock_hash.assert_not_called()
            self.assertEqual(reason, "excluded")


class FlushPathHashTests(unittest.TestCase):
    def test_flush_path_skips_known_path_same_hash(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "agent-transcripts" / "x.jsonl"
            path.parent.mkdir()
            path.write_text(
                '{"role":"user","message":{"content":[{"type":"text","text":"test"}]}}\n'
            )
            file_hash = sha256_file(str(path))
            processed = {file_hash: {"path": str(path.resolve())}}
            mock_index = mock.Mock()
            with mock.patch("ingest.load_processed", return_value=processed):
                with mock.patch("ingest.sha256_file", wraps=sha256_file):
                    self.assertIsNone(
                        flush_path(str(path), index_fn=mock_index, verbose=False)
                    )
            mock_index.assert_not_called()

    def test_flush_path_reindexes_when_hash_changed(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "agent-transcripts" / "x.jsonl"
            path.parent.mkdir()
            path.write_text(
                '{"role":"user","message":{"content":[{"type":"text","text":"test"}]}}\n'
            )
            processed = {"stalehash": {"path": str(path.resolve())}}
            mock_index = mock.Mock(return_value={"files_processed": 1})
            with mock.patch("ingest.load_processed", return_value=processed):
                result = flush_path(str(path), index_fn=mock_index, verbose=False)
            mock_index.assert_called_once()
            self.assertIsNotNone(result)


if __name__ == "__main__":
    unittest.main()

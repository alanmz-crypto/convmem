"""Tests for Milestone F0 filesystem watch."""

from __future__ import annotations

import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

from watch import (
    DebounceScheduler,
    _is_live_watch_pid,
    acquire_lock,
    flush_path,
    is_indexable,
    is_live_watch_db,
    is_watchable,
    watch_roots,
)


class DebounceSchedulerTests(unittest.TestCase):
    def test_ready_after_debounce(self):
        sched = DebounceScheduler(debounce_seconds=0.05)
        sched.note("/tmp/a.jsonl")
        self.assertEqual(sched.ready(), [])
        time.sleep(0.06)
        self.assertEqual(sched.ready(), ["/tmp/a.jsonl"])

    def test_reset_timer_on_repeat_event(self):
        sched = DebounceScheduler(debounce_seconds=0.1)
        sched.note("/tmp/b.jsonl")
        time.sleep(0.06)
        sched.note("/tmp/b.jsonl")
        self.assertEqual(sched.ready(), [])
        time.sleep(0.06)
        self.assertEqual(sched.ready(), [])
        time.sleep(0.05)
        self.assertEqual(sched.ready(), ["/tmp/b.jsonl"])

    def test_forget(self):
        sched = DebounceScheduler(debounce_seconds=0.01)
        sched.note("/tmp/c.jsonl")
        time.sleep(0.02)
        sched.forget("/tmp/c.jsonl")
        self.assertEqual(sched.ready(), [])


class WatchPathTests(unittest.TestCase):
    def test_watch_roots_file_uses_parent(self):
        with tempfile.TemporaryDirectory() as td:
            f = Path(td) / "data.sqlite3"
            f.touch()
            roots = watch_roots([str(f)])
            self.assertEqual(roots, [Path(td)])

    def test_watch_roots_directory(self):
        with tempfile.TemporaryDirectory() as td:
            roots = watch_roots([td])
            self.assertEqual(roots, [Path(td)])

    def test_is_indexable_cursor_jsonl(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "agent-transcripts" / "sess" / "t.jsonl"
            path.parent.mkdir(parents=True)
            path.write_text(
                '{"role":"user","message":{"content":[{"type":"text","text":"hi"}]}}\n'
            )
            self.assertTrue(is_indexable(path))

    def test_is_indexable_random_jsonl_false(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "metrics.jsonl"
            path.write_text("{}\n")
            self.assertFalse(is_indexable(path))

    def test_flush_path_calls_index(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "agent-transcripts" / "x.jsonl"
            path.parent.mkdir()
            path.write_text(
                '{"role":"user","message":{"content":[{"type":"text","text":"test"}]}}\n'
            )
            mock_index = mock.Mock(return_value={"files_processed": 1})
            stats = flush_path(str(path), index_fn=mock_index, verbose=False)
            mock_index.assert_called_once()
            self.assertEqual(stats["files_processed"], 1)

    def test_is_live_watch_db_kiro(self):
        self.assertTrue(
            is_live_watch_db("/home/lauer/.local/share/kiro-cli/data.sqlite3")
        )

    def test_is_live_watch_db_cursor_store(self):
        self.assertTrue(
            is_live_watch_db(
                "/home/lauer/.config/cursor/chats/abc123/session-1/store.db"
            )
        )

    def test_is_live_watch_db_other_store_db_not_live(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "store.db"
            path.touch()
            self.assertFalse(is_live_watch_db(path))

    def test_is_watchable_skips_live_db(self):
        self.assertFalse(
            is_watchable("/home/lauer/.local/share/kiro-cli/data.sqlite3")
        )

    def test_is_watchable_skips_cursor_store_db(self):
        self.assertFalse(
            is_watchable(
                "/home/lauer/.config/cursor/chats/abc123/session-1/store.db"
            )
        )

    def test_flush_path_skips_already_processed(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "agent-transcripts" / "x.jsonl"
            path.parent.mkdir()
            path.write_text(
                '{"role":"user","message":{"content":[{"type":"text","text":"test"}]}}\n'
            )
            mock_index = mock.Mock()
            with mock.patch("ingest.watch_skip_reason", return_value="unchanged"):
                self.assertIsNone(
                    flush_path(str(path), index_fn=mock_index, verbose=False)
                )
            mock_index.assert_not_called()

    def test_flush_path_skips_unsupported(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "nope.jsonl"
            path.write_text("{}\n")
            mock_index = mock.Mock()
            self.assertIsNone(flush_path(str(path), index_fn=mock_index, verbose=False))
            mock_index.assert_not_called()

    def test_flush_path_subprocess(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "agent-transcripts" / "x.jsonl"
            path.parent.mkdir()
            path.write_text(
                '{"role":"user","message":{"content":[{"type":"text","text":"test"}]}}\n'
            )
            with mock.patch("watch._flush_path_subprocess", return_value={"subprocess": True}) as sp:
                out = flush_path(str(path), verbose=False, use_subprocess=True)
            sp.assert_called_once()
            self.assertEqual(out, {"subprocess": True})

    def test_is_live_watch_pid_matches_cmdline(self):
        with mock.patch("watch.os.kill", return_value=None):
            with mock.patch(
                "watch._pid_cmdline",
                return_value="/usr/bin/python convmem.py watch",
            ):
                self.assertTrue(_is_live_watch_pid(12345))

    def test_is_live_watch_pid_rejects_pid_reuse(self):
        with mock.patch("watch.os.kill", return_value=None):
            with mock.patch(
                "watch._pid_cmdline",
                return_value="/usr/bin/bash",
            ):
                self.assertFalse(_is_live_watch_pid(12345))

    def test_acquire_lock_removes_stale_pid(self):
        with tempfile.TemporaryDirectory() as td:
            lock = Path(td) / "watch.lock"
            lock.write_text("99999", encoding="utf-8")
            with mock.patch("watch._is_live_watch_pid", return_value=False):
                with mock.patch("watch.os.getpid", return_value=4242):
                    acquire_lock(lock)
            self.assertEqual(lock.read_text().strip(), "4242")


if __name__ == "__main__":
    unittest.main()

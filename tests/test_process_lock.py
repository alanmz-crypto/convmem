"""Regression tests for symlink-safe PID locks."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from process_lock import acquire_lock
from watch import acquire_lock as acquire_watch_lock


class ProcessLockTests(unittest.TestCase):
    def test_lock_is_created_atomically_with_private_mode(self):
        with tempfile.TemporaryDirectory() as td:
            lock = Path(td) / "nested" / "process.lock"
            with mock.patch("process_lock.os.getpid", return_value=4242):
                acquire_lock(lock)
            self.assertEqual(lock.read_text(encoding="utf-8"), "4242")
            self.assertEqual(lock.stat().st_mode & 0o777, 0o600)

    def test_process_lock_refuses_leaf_symlink(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            target = root / "target"
            target.write_text("keep", encoding="utf-8")
            lock = root / "process.lock"
            lock.symlink_to(target)
            with mock.patch("process_lock.os.getpid", return_value=4242), self.assertRaisesRegex(
                RuntimeError, "symlink lock path"
            ):
                acquire_lock(lock)
            self.assertEqual(target.read_text(encoding="utf-8"), "keep")

    def test_process_lock_refuses_symlinked_parent(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            target_dir = root / "target-dir"
            target_dir.mkdir()
            link_dir = root / "link-dir"
            link_dir.symlink_to(target_dir, target_is_directory=True)
            lock = link_dir / "process.lock"
            with mock.patch("process_lock.os.getpid", return_value=4242):
                with self.assertRaisesRegex(RuntimeError, "unsafe lock directory"):
                    acquire_lock(lock)
            self.assertFalse((target_dir / "process.lock").exists())

    def test_watch_lock_refuses_leaf_symlink(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            target = root / "target"
            target.write_text("keep", encoding="utf-8")
            lock = root / "watch.lock"
            lock.symlink_to(target)
            with mock.patch("watch.os.getpid", return_value=4242), self.assertRaisesRegex(
                RuntimeError, "symlink lock path"
            ):
                acquire_watch_lock(lock)
            self.assertEqual(target.read_text(encoding="utf-8"), "keep")


if __name__ == "__main__":
    unittest.main()

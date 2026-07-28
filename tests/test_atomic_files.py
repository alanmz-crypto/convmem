"""V5 atomic publication fault injection + FD-leak proof (complete-data backup v2 T3)."""

# Fault-injection fixtures deliberately retain resources across setUp/tearDown
# and mirror os.fdopen's signature.
# pylint: disable=consider-using-with,keyword-arg-before-vararg,duplicate-code

from __future__ import annotations

import os
import stat
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from atomic_files import (
    PostPublicationDurabilityError,
    PrePublicationError,
    atomic_write_bytes,
    atomic_write_json,
    atomic_write_text,
)


def _fd_count() -> int:
    return len(os.listdir(f"/proc/{os.getpid()}/fd"))


def _is_dir_fd(fd: int) -> bool:
    return stat.S_ISDIR(os.fstat(fd).st_mode)


class AtomicFilesTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self._tmp.name)
        self.path = self.dir / "dest.txt"
        self.path.write_text("PRIOR\n", encoding="utf-8")
        os.chmod(self.path, 0o640)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_v5a_partial_write_preserves_destination(self) -> None:
        original = self.path.read_bytes()

        class BoomFile:
            def __init__(self, real):
                self._real = real

            def write(self, data):
                self._real.write(data[: max(1, len(data) // 2)])
                self._real.flush()
                raise OSError("injected partial write")

            def flush(self):
                return self._real.flush()

            def fileno(self):
                return self._real.fileno()

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return self._real.__exit__(*args)

        real_fdopen = os.fdopen

        def fdopen_wrap(fd, mode="r", *args, **kwargs):
            real = real_fdopen(fd, mode, *args, **kwargs)
            if "b" in mode:
                return BoomFile(real)
            return real

        with mock.patch("os.fdopen", side_effect=fdopen_wrap):
            with self.assertRaises(PrePublicationError):
                atomic_write_text(self.path, "NEW-COMPLETE\n")

        self.assertEqual(self.path.read_bytes(), original)

    def test_v5b_flush_failure_preserves_destination(self) -> None:
        original = self.path.read_bytes()
        real_fdopen = os.fdopen

        class BoomFlush:
            def __init__(self, real):
                self._real = real

            def write(self, data):
                return self._real.write(data)

            def flush(self):
                raise OSError("injected flush failure")

            def fileno(self):
                return self._real.fileno()

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return self._real.__exit__(*args)

        def fdopen_wrap(fd, mode="r", *args, **kwargs):
            real = real_fdopen(fd, mode, *args, **kwargs)
            if "b" in mode:
                return BoomFlush(real)
            return real

        with mock.patch("os.fdopen", side_effect=fdopen_wrap):
            with self.assertRaises(PrePublicationError):
                atomic_write_text(self.path, "NEW-COMPLETE\n")

        self.assertEqual(self.path.read_bytes(), original)

    def test_v5c_temp_fsync_failure_preserves_destination(self) -> None:
        original = self.path.read_bytes()
        real_fsync = os.fsync

        def boom(fd: int) -> None:
            if not _is_dir_fd(fd):
                raise OSError("injected temp fsync failure")
            return real_fsync(fd)

        with mock.patch("os.fsync", side_effect=boom):
            with self.assertRaises(PrePublicationError):
                atomic_write_text(self.path, "NEW-COMPLETE\n")

        self.assertEqual(self.path.read_bytes(), original)

    def test_v5d_pre_replace_interrupt_preserves_destination(self) -> None:
        original = self.path.read_bytes()

        def boom(src, dst):
            raise OSError("injected pre-replace interrupt")

        with mock.patch("os.replace", side_effect=boom):
            with self.assertRaises(PrePublicationError):
                atomic_write_text(self.path, "NEW-COMPLETE\n")

        self.assertEqual(self.path.read_bytes(), original)

    def test_v5e_replace_success_publishes_complete_file(self) -> None:
        atomic_write_text(self.path, "NEW-COMPLETE\n")
        self.assertEqual(self.path.read_text(encoding="utf-8"), "NEW-COMPLETE\n")

    def test_v5f_parent_dir_fsync_failure_after_replace(self) -> None:
        real_fsync = os.fsync

        def boom(fd: int) -> None:
            if _is_dir_fd(fd):
                raise OSError("injected parent-directory fsync failure")
            return real_fsync(fd)

        with mock.patch("os.fsync", side_effect=boom):
            with self.assertRaises(PostPublicationDurabilityError):
                atomic_write_text(self.path, "NEW-COMPLETE\n")

        self.assertEqual(self.path.read_text(encoding="utf-8"), "NEW-COMPLETE\n")

    def test_v5g_mode_preservation(self) -> None:
        self.assertEqual(stat.S_IMODE(self.path.stat().st_mode), 0o640)
        atomic_write_text(self.path, "MODE-OK\n", preserve_mode=True)
        self.assertEqual(stat.S_IMODE(self.path.stat().st_mode), 0o640)

        atomic_write_text(self.path, "MODE-NEW\n", preserve_mode=False)
        # Without preserve_mode, mode comes from mkstemp umask; just ensure write ok.
        self.assertEqual(self.path.read_text(encoding="utf-8"), "MODE-NEW\n")

    def test_v5h_cleanup_only_own_unpublished_temp(self) -> None:
        foreign = self.dir / f".{self.path.name}.foreign.tmp"
        foreign.write_text("leave-me\n", encoding="utf-8")
        original = self.path.read_bytes()

        with mock.patch("os.replace", side_effect=OSError("injected replace fail")):
            with self.assertRaises(PrePublicationError):
                atomic_write_text(self.path, "NEW-COMPLETE\n")

        self.assertEqual(self.path.read_bytes(), original)
        self.assertTrue(foreign.is_file())
        self.assertEqual(foreign.read_text(encoding="utf-8"), "leave-me\n")
        leftovers = list(self.dir.glob(f".{self.path.name}.*.tmp"))
        self.assertEqual(leftovers, [foreign])

    def test_v5i_repeated_write_zero_fd_growth(self) -> None:
        # Warm paths / caches so steady-state counting is stable.
        for i in range(5):
            atomic_write_text(self.path, f"warm-{i}\n")
        baseline = _fd_count()
        for i in range(50):
            atomic_write_text(self.path, f"steady-{i}\n")
            atomic_write_bytes(self.path, f"bytes-{i}\n".encode())
            atomic_write_json(self.path, {"i": i})
        self.assertEqual(_fd_count(), baseline)

    def test_new_file_without_prior(self) -> None:
        fresh = self.dir / "fresh.json"
        atomic_write_json(fresh, {"ok": True})
        self.assertTrue(fresh.is_file())
        self.assertIn('"ok": true', fresh.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()

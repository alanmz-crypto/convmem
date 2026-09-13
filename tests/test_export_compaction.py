"""Bounded export compaction: golden parity, fail-closed, crash, and lock tests."""

# Fault-injection fixtures retain resources across setUp/tearDown.
# pylint: disable=consider-using-with,keyword-arg-before-vararg,duplicate-code,protected-access

from __future__ import annotations

import errno
import os
import sqlite3
import stat
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest import mock

from atomic_files import PostPublicationDurabilityError, PrePublicationError
from export_compaction import (
    MAX_RECORD_BYTES,
    ExportIdentityChangedError,
    InvalidExportRecordError,
    OversizedExportRecordError,
    compact_units_export,
)
from purge_locks import export_flock_path


def _fd_count() -> int:
    return len(os.listdir(f"/proc/{os.getpid()}/fd"))


def _is_dir_fd(fd: int) -> bool:
    return stat.S_ISDIR(os.fstat(fd).st_mode)


def _write_export(path: Path, data: bytes | str, mode: int = 0o640) -> None:
    raw = data if isinstance(data, bytes) else data.encode("utf-8")
    path.write_bytes(raw)
    os.chmod(path, mode)


class ExportCompactionTests(unittest.TestCase):  # pylint: disable=too-many-public-methods
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self._tmp.name)
        self.path = self.dir / "knowledge_units.jsonl"

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_missing_file_returns_zero(self) -> None:
        missing = self.dir / "absent.jsonl"
        self.assertEqual(compact_units_export(missing), 0)
        self.assertFalse(missing.exists())

    def test_unique_valid_rows_are_byte_identical_noop(self) -> None:
        original = b'{"id":"a","v":1}\n{"id":"b","v":2}\n'
        _write_export(self.path, original)
        mtime = self.path.stat().st_mtime_ns
        self.assertEqual(compact_units_export(self.path), 0)
        self.assertEqual(self.path.read_bytes(), original)
        self.assertEqual(stat.S_IMODE(self.path.stat().st_mode), 0o640)
        self.assertEqual(self.path.stat().st_mtime_ns, mtime)

    def test_unique_final_record_without_newline_is_noop(self) -> None:
        original = b'{"id":"a","v":1}\n{"id":"b","v":2}'
        _write_export(self.path, original)
        self.assertEqual(compact_units_export(self.path), 0)
        self.assertEqual(self.path.read_bytes(), original)

    def test_duplicates_retain_last_value_in_first_id_order(self) -> None:
        _write_export(
            self.path,
            '{"id":"a","v":1}\n{"id":"b","v":2}\n{"id":"a","v":3}\n',
        )
        self.assertEqual(compact_units_export(self.path), 1)
        self.assertEqual(
            self.path.read_bytes(),
            b'{"id":"a","v":3}\n{"id":"b","v":2}\n',
        )
        self.assertEqual(stat.S_IMODE(self.path.stat().st_mode), 0o640)

    def test_final_unterminated_duplicate_is_retained(self) -> None:
        _write_export(self.path, '{"id":"a","v":1}\n{"id":"a","v":2}')
        self.assertEqual(compact_units_export(self.path), 1)
        self.assertEqual(self.path.read_bytes(), b'{"id":"a","v":2}\n')

    def test_blank_lines_ignored_and_whitespace_stripped_on_rewrite(self) -> None:
        _write_export(self.path, '\n  {"id":"a","v":1}  \n\n{"id":"a","v":2}\n')
        self.assertEqual(compact_units_export(self.path), 1)
        self.assertEqual(self.path.read_bytes(), b'{"id":"a","v":2}\n')

    def test_malformed_json_fails_closed(self) -> None:
        original = b'{"id":"a"}\nNOTJSON\n{"id":"b"}\n'
        _write_export(self.path, original)
        with self.assertRaises(InvalidExportRecordError):
            compact_units_export(self.path)
        self.assertEqual(self.path.read_bytes(), original)

    def test_non_object_missing_empty_and_nonstring_ids_fail_closed(self) -> None:
        cases = (
            b'{"id":"a"}\n[1,2]\n',
            b'{"id":"a"}\n{"v":1}\n',
            b'{"id":"a"}\n{"id":""}\n',
            b'{"id":"a"}\n{"id":null}\n',
            b'{"id":"a"}\n{"id":123}\n',
            b'{"id":"a"}\n"x"\n',
        )
        for original in cases:
            with self.subTest(original=original):
                _write_export(self.path, original)
                with self.assertRaises(InvalidExportRecordError):
                    compact_units_export(self.path)
                self.assertEqual(self.path.read_bytes(), original)

    def test_invalid_utf8_fails_closed(self) -> None:
        original = b'{"id":"a"}\n\xff\n{"id":"b"}\n'
        _write_export(self.path, original)
        with self.assertRaises(InvalidExportRecordError):
            compact_units_export(self.path)
        self.assertEqual(self.path.read_bytes(), original)

    def test_symlink_fails_closed(self) -> None:
        target = self.dir / "real.jsonl"
        _write_export(target, '{"id":"a"}\n{"id":"a"}\n')
        link = self.dir / "link.jsonl"
        os.symlink(target, link)
        original = target.read_bytes()
        with self.assertRaises(InvalidExportRecordError):
            compact_units_export(link)
        self.assertEqual(target.read_bytes(), original)

    def test_oversized_record_fails_closed_without_unbounded_readline(self) -> None:
        original = b'{"id":"a"}\n' + (b"x" * (MAX_RECORD_BYTES + 1)) + b"\n"
        _write_export(self.path, original)
        with mock.patch("export_compaction.os.read", wraps=os.read) as wrapped_read:
            with self.assertRaises(OversizedExportRecordError):
                compact_units_export(self.path)
        self.assertEqual(self.path.read_bytes(), original)
        for args in wrapped_read.call_args_list:
            self.assertLessEqual(args.args[1], MAX_RECORD_BYTES + 1)

    def test_sqlite_failure_leaves_original_and_removes_scratch(self) -> None:
        original = b'{"id":"a","v":1}\n{"id":"a","v":2}\n'
        _write_export(self.path, original)
        def boom(*_args, **_kwargs):
            raise sqlite3.OperationalError("injected sqlite failure")

        with mock.patch("export_compaction._index_row", side_effect=boom):
            with self.assertRaises(PrePublicationError):
                compact_units_export(self.path)
        self.assertEqual(self.path.read_bytes(), original)
        self.assertEqual(list(self.dir.glob(".*compact*")), [])

    def test_enospc_write_leaves_original(self) -> None:
        original = b'{"id":"a","v":1}\n{"id":"a","v":2}\n'
        _write_export(self.path, original)
        real_fdopen = os.fdopen

        class BoomFile:
            def __init__(self, real):
                self._real = real

            def write(self, data):
                raise OSError(errno.ENOSPC, "No space left on device")

            def flush(self):
                return self._real.flush()

            def fileno(self):
                return self._real.fileno()

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return self._real.__exit__(*args)

        def fdopen_wrap(fd, mode="r", *args, **kwargs):
            real = real_fdopen(fd, mode, *args, **kwargs)
            if "b" in mode:
                return BoomFile(real)
            return real

        with mock.patch("os.fdopen", side_effect=fdopen_wrap):
            with self.assertRaises(PrePublicationError):
                compact_units_export(self.path)
        self.assertEqual(self.path.read_bytes(), original)

    def test_replace_failure_leaves_original(self) -> None:
        original = b'{"id":"a","v":1}\n{"id":"a","v":2}\n'
        _write_export(self.path, original)
        with mock.patch("os.replace", side_effect=OSError("injected replace fail")):
            with self.assertRaises(PrePublicationError):
                compact_units_export(self.path)
        self.assertEqual(self.path.read_bytes(), original)

    def test_parent_dir_fsync_failure_publishes_complete_file(self) -> None:
        _write_export(self.path, '{"id":"a","v":1}\n{"id":"a","v":2}\n')
        real_fsync = os.fsync

        def boom(fd: int) -> None:
            if _is_dir_fd(fd):
                raise OSError("injected parent-directory fsync failure")
            return real_fsync(fd)

        with mock.patch("os.fsync", side_effect=boom):
            with self.assertRaises(PostPublicationDurabilityError):
                compact_units_export(self.path)
        self.assertEqual(self.path.read_bytes(), b'{"id":"a","v":2}\n')

    def test_path_replacement_during_output_refuses_publication(self) -> None:
        original = b'{"id":"a","v":1}\n{"id":"a","v":2}\n'
        _write_export(self.path, original)
        hijacked = b'{"id":"hijack"}\n'
        real_stream = __import__("atomic_files").atomic_write_stream

        def wrapped(path, writer, *, preserve_mode=True, validate_before_replace=None):
            def mutating_writer(handle) -> None:
                writer(handle)
                other = Path(path).with_name("other.jsonl")
                other.write_bytes(hijacked)
                os.replace(other, path)

            return real_stream(
                path,
                mutating_writer,
                preserve_mode=preserve_mode,
                validate_before_replace=validate_before_replace,
            )

        with mock.patch("export_compaction.atomic_write_stream", wrapped):
            with self.assertRaises(ExportIdentityChangedError):
                compact_units_export(self.path)
        self.assertEqual(self.path.read_bytes(), hijacked)

    def test_same_inode_mutation_during_output_refuses_publication(self) -> None:
        original = b'{"id":"a","v":1}\n{"id":"a","v":2}\n'
        _write_export(self.path, original)
        real_stream = __import__("atomic_files").atomic_write_stream

        def wrapped(path, writer, *, preserve_mode=True, validate_before_replace=None):
            def mutating_writer(handle) -> None:
                writer(handle)
                payload = b"Z" * len(original)
                fd = os.open(path, os.O_WRONLY)
                try:
                    os.write(fd, payload)
                    os.fsync(fd)
                finally:
                    os.close(fd)

            return real_stream(
                path,
                mutating_writer,
                preserve_mode=preserve_mode,
                validate_before_replace=validate_before_replace,
            )

        with mock.patch("export_compaction.atomic_write_stream", wrapped):
            with self.assertRaises(ExportIdentityChangedError):
                compact_units_export(self.path)
        self.assertEqual(self.path.read_bytes(), b"Z" * len(original))

    def test_lock_contention_blocks_append_writer(self) -> None:
        _write_export(self.path, '{"id":"a","v":1}\n{"id":"a","v":2}\n')
        held = threading.Event()
        release = threading.Event()
        compacting = threading.Event()
        done: list[float] = []

        def holder() -> None:
            with export_flock_path(self.path):
                held.set()
                self.assertTrue(release.wait(5))

        def runner() -> None:
            compacting.set()
            start = time.monotonic()
            compact_units_export(self.path)
            done.append(time.monotonic() - start)

        t_hold = threading.Thread(target=holder)
        t_run = threading.Thread(target=runner)
        t_hold.start()
        self.assertTrue(held.wait(5))
        t_run.start()
        self.assertTrue(compacting.wait(5))
        time.sleep(0.2)
        self.assertEqual(done, [])
        release.set()
        t_run.join(5)
        t_hold.join(5)
        self.assertTrue(done)
        self.assertEqual(self.path.read_bytes(), b'{"id":"a","v":2}\n')

    def test_handled_failure_removes_owned_scratch_not_foreign(self) -> None:
        original = b'{"id":"a","v":1}\n{"id":"a","v":2}\n'
        _write_export(self.path, original)
        foreign_dir = self.dir / f".{self.path.name}.compact.foreign"
        foreign_dir.mkdir()
        (foreign_dir / "keep").write_text("leave-me\n", encoding="utf-8")
        foreign_tmp = self.dir / f".{self.path.name}.foreign.tmp"
        foreign_tmp.write_text("leave-me\n", encoding="utf-8")
        with mock.patch("os.replace", side_effect=OSError("injected replace fail")):
            with self.assertRaises(PrePublicationError):
                compact_units_export(self.path)
        self.assertEqual(self.path.read_bytes(), original)
        self.assertTrue(foreign_dir.is_dir())
        self.assertEqual((foreign_dir / "keep").read_text(encoding="utf-8"), "leave-me\n")
        self.assertTrue(foreign_tmp.is_file())
        owned = [p for p in self.dir.glob(f".{self.path.name}.compact.*") if p != foreign_dir]
        self.assertEqual(owned, [])

    def test_noop_validates_identity_before_return(self) -> None:
        original = b'{"id":"a"}\n{"id":"b"}\n'
        _write_export(self.path, original)
        hijacked = b'{"id":"hijack"}\n'
        real_scan = __import__("export_compaction")._scan_into_index

        def scanning(fd, conn):
            result = real_scan(fd, conn)
            other = self.dir / "other.jsonl"
            other.write_bytes(hijacked)
            os.replace(other, self.path)
            return result

        with mock.patch("export_compaction._scan_into_index", scanning):
            with self.assertRaises(ExportIdentityChangedError):
                compact_units_export(self.path)
        self.assertEqual(self.path.read_bytes(), hijacked)

    def test_empty_noop_validates_identity_before_return(self) -> None:
        _write_export(self.path, b"\n\n")
        hijacked = b'{"id":"hijack"}\n'
        real_scan = __import__("export_compaction")._scan_into_index

        def scanning(fd, conn):
            result = real_scan(fd, conn)
            other = self.dir / "other.jsonl"
            other.write_bytes(hijacked)
            os.replace(other, self.path)
            return result

        with mock.patch("export_compaction._scan_into_index", scanning):
            with self.assertRaises(ExportIdentityChangedError):
                compact_units_export(self.path)
        self.assertEqual(self.path.read_bytes(), hijacked)

    def test_scratch_pathname_replacement_does_not_delete_foreign(self) -> None:
        original = b'{"id":"a","v":1}\n{"id":"a","v":2}\n'
        _write_export(self.path, original)
        victim = self.dir / "victim"
        victim.mkdir()
        canary = victim / "keep"
        canary.write_text("leave-me\n", encoding="utf-8")
        real_create = __import__("export_compaction")._create_scratch

        def wrapped(export_path):
            scratch = real_create(export_path)
            aside = export_path.parent / (scratch.path.name + ".aside")
            os.rename(scratch.path, aside)
            os.symlink(victim, scratch.path)
            return scratch

        with mock.patch("export_compaction._create_scratch", wrapped):
            self.assertEqual(compact_units_export(self.path), 1)
        self.assertTrue(canary.is_file())
        self.assertEqual(canary.read_text(encoding="utf-8"), "leave-me\n")
        self.assertEqual(self.path.read_bytes(), b'{"id":"a","v":2}\n')

    def test_scratch_replaced_before_dirfd_leaves_foreign_untouched(self) -> None:
        original = b'{"id":"a","v":1}\n{"id":"a","v":2}\n'
        _write_export(self.path, original)
        foreign = self.dir / "foreign-scratch"
        foreign.mkdir()
        db = foreign / "index.sqlite"
        payload = b"FOREIGN-DB-PAYLOAD-DO-NOT-TOUCH\n"
        db.write_bytes(payload)
        foreign_mode = stat.S_IMODE(foreign.stat().st_mode)
        db_mode = stat.S_IMODE(db.stat().st_mode)
        real_mkdtemp = tempfile.mkdtemp
        swapped: dict[str, Path] = {}

        def wrapped_mkdtemp(*args, **kwargs):
            created = Path(real_mkdtemp(*args, **kwargs))
            aside = created.parent / (created.name + ".aside")
            os.rename(created, aside)
            os.rename(foreign, created)
            swapped["path"] = created
            swapped["aside"] = aside
            return str(created)

        with mock.patch("export_compaction.tempfile.mkdtemp", wrapped_mkdtemp):
            with self.assertRaises(PrePublicationError):
                compact_units_export(self.path)
        target = swapped["path"]
        self.assertTrue(target.is_dir())
        self.assertFalse(target.is_symlink())
        self.assertEqual(sorted(p.name for p in target.iterdir()), ["index.sqlite"])
        self.assertEqual((target / "index.sqlite").read_bytes(), payload)
        self.assertEqual(stat.S_IMODE(target.stat().st_mode), foreign_mode)
        self.assertEqual(stat.S_IMODE((target / "index.sqlite").stat().st_mode), db_mode)
        self.assertEqual(self.path.read_bytes(), original)
        self.assertTrue(swapped["aside"].is_dir())
        self.assertEqual(list(swapped["aside"].iterdir()), [])

    def test_repeated_compact_zero_fd_growth(self) -> None:
        _write_export(self.path, '{"id":"a","v":1}\n{"id":"b","v":2}\n')
        for _ in range(3):
            compact_units_export(self.path)
        _write_export(self.path, '{"id":"a","v":1}\n{"id":"a","v":2}\n')
        compact_units_export(self.path)
        baseline = _fd_count()
        for i in range(20):
            _write_export(self.path, f'{{"id":"a","v":{i}}}\n{{"id":"a","v":{i+1}}}\n')
            compact_units_export(self.path)
            _write_export(self.path, '{"id":"a"}\n{"id":"b"}\n')
            compact_units_export(self.path)
        self.assertEqual(_fd_count(), baseline)


if __name__ == "__main__":
    unittest.main()

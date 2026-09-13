"""Bounded export compaction: golden parity, fail-closed, crash, and lock tests."""

# Fault-injection fixtures retain resources across setUp/tearDown.
# pylint: disable=consider-using-with,keyword-arg-before-vararg,duplicate-code,protected-access

from __future__ import annotations

import errno
import os
import signal
import sqlite3
import stat
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest import mock

import export_compaction as export_compaction_mod

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


def _fstype(path: str) -> str:
    raw = path.split(" (deleted)", 1)[0]
    probe = raw if os.path.exists(raw) else os.path.dirname(raw)
    probe = os.path.realpath(probe)
    best = ""
    best_len = -1
    with open("/proc/mounts", encoding="utf-8") as handle:
        for line in handle:
            parts = line.split()
            if len(parts) < 3:
                continue
            mount = parts[1].replace("\\040", " ")
            fstype = parts[2]
            if probe == mount or probe.startswith(mount.rstrip("/") + "/"):
                if len(mount) > best_len:
                    best = fstype
                    best_len = len(mount)
    return best


def _deleted_sqlite_fds(pid: int | None = None) -> list[str]:
    if pid is None:
        pid = os.getpid()
    found: list[str] = []
    fd_dir = Path(f"/proc/{pid}/fd")
    for entry in fd_dir.iterdir():
        try:
            target = os.readlink(entry)
        except OSError:
            continue
        if "etilqs_" in target:
            found.append(target)
    return found


def _non_tmpfs_parent() -> Path:
    for candidate in (Path("/var/tmp"), Path.home()):
        if candidate.is_dir() and _fstype(str(candidate)) not in {"tmpfs", "ramfs"}:
            return candidate
    raise AssertionError("no non-tmpfs directory available for SQLite temp evidence")


def _entry_snapshot(path: Path) -> dict:
    st = os.lstat(path)
    rec = {
        "mode": stat.S_IMODE(st.st_mode),
        "dev": st.st_dev,
        "ino": st.st_ino,
        "uid": st.st_uid,
        "gid": st.st_gid,
        "nlink": st.st_nlink,
        "size": st.st_size,
        "islnk": stat.S_ISLNK(st.st_mode),
        "isdir": stat.S_ISDIR(st.st_mode),
        "target": os.readlink(path) if stat.S_ISLNK(st.st_mode) else None,
        "data": path.read_bytes() if stat.S_ISREG(st.st_mode) else None,
    }
    return rec


def _tree_snapshot(paths: list[Path]) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for path in paths:
        out[str(path)] = _entry_snapshot(path)
        if path.is_dir() and not path.is_symlink():
            for child in sorted(path.rglob("*")):
                out[str(child)] = _entry_snapshot(child)
    return out


class ExportCompactionTests(unittest.TestCase):  # pylint: disable=too-many-public-methods
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self._tmp.name)
        self.path = self.dir / "knowledge_units.jsonl"

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _plant_foreign_export_dir_objects(self) -> tuple[list[Path], dict[str, dict]]:
        compact = self.dir / f".{self.path.name}.compact.adversary"
        compact.mkdir()
        canary = compact / "canary"
        canary.write_bytes(b"CANARY-BYTES\n")
        os.chmod(canary, 0o640)
        db = self.dir / "index.sqlite"
        db.write_bytes(b"FOREIGN-INDEX-SQLITE\n")
        os.chmod(db, 0o600)
        journal = self.dir / "index.sqlite-journal"
        journal.write_bytes(b"FOREIGN-JOURNAL\n")
        os.chmod(journal, 0o600)
        keep = self.dir / "keep-me"
        keep.write_bytes(b"KEEP-ME\n")
        os.chmod(keep, 0o644)
        paths = [compact, canary, db, journal, keep]
        return paths, _tree_snapshot(paths)

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

    def test_sqlite_failure_leaves_original_and_foreign_objects(self) -> None:
        original = b'{"id":"a","v":1}\n{"id":"a","v":2}\n'
        _write_export(self.path, original)
        _paths, before = self._plant_foreign_export_dir_objects()

        def boom(*_args, **_kwargs):
            raise sqlite3.OperationalError("injected sqlite failure")

        with mock.patch("export_compaction._index_row", side_effect=boom):
            with self.assertRaises(PrePublicationError):
                compact_units_export(self.path)
        self.assertEqual(self.path.read_bytes(), original)
        self.assertEqual(_tree_snapshot(_paths), before)

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

    def test_foreign_export_dir_objects_survive_noop_and_rewrite(self) -> None:
        paths, before = self._plant_foreign_export_dir_objects()
        unique = b'{"id":"a","v":1}\n{"id":"b","v":2}\n'
        _write_export(self.path, unique)
        self.assertEqual(compact_units_export(self.path), 0)
        self.assertEqual(self.path.read_bytes(), unique)
        self.assertEqual(_tree_snapshot(paths), before)
        _write_export(self.path, b'{"id":"a","v":1}\n{"id":"a","v":2}\n')
        self.assertEqual(compact_units_export(self.path), 1)
        self.assertEqual(self.path.read_bytes(), b'{"id":"a","v":2}\n')
        self.assertEqual(_tree_snapshot(paths), before)

    def test_large_index_uses_deleted_ondisk_sqlite_temp(self) -> None:
        rows = []
        for i in range(90000):
            # IDs must be large enough that the offset index exceeds the 8 MiB
            # SQLite page cache and spills to a deleted on-disk temp file.
            rows.append(f'{{"id":"id-{i:08d}-{"x"*40}","n":{i}}}\n')
        _write_export(self.path, "".join(rows))
        original = self.path.read_bytes()
        paths, before = self._plant_foreign_export_dir_objects()
        captured: dict[str, object] = {}
        real = export_compaction_mod._index_row
        seen = 0

        def wrapped(conn, uid, seq, offset, length):
            nonlocal seen
            real(conn, uid, seq, offset, length)
            seen += 1
            if seen >= 70000 and seen % 4096 == 0:
                captured["database_list"] = conn.execute("PRAGMA database_list").fetchall()
                captured["temp_store"] = conn.execute("PRAGMA temp_store").fetchone()[0]
                fds = _deleted_sqlite_fds()
                if fds:
                    captured["fds"] = fds

        sqlite_parent = _non_tmpfs_parent()
        with tempfile.TemporaryDirectory(
            prefix="convmem-sqlite-tmp.", dir=str(sqlite_parent)
        ) as sqlite_tmp:
            self.assertNotIn(_fstype(sqlite_tmp), {"tmpfs", "ramfs"})
            with mock.patch.dict(os.environ, {"SQLITE_TMPDIR": sqlite_tmp, "TMPDIR": sqlite_tmp}):
                with mock.patch("export_compaction._index_row", wrapped):
                    self.assertEqual(compact_units_export(self.path), 0)
        self.assertEqual(self.path.read_bytes(), original)
        self.assertEqual(_tree_snapshot(paths), before)
        db_list = captured["database_list"]
        self.assertTrue(db_list)
        self.assertEqual(db_list[0][1], "main")
        self.assertEqual(db_list[0][2], "")
        self.assertNotEqual(captured["temp_store"], 2)
        fds = captured["fds"]
        self.assertTrue(fds, captured)
        for target in fds:
            self.assertNotIn(_fstype(target), {"tmpfs", "ramfs"}, target)
            self.assertNotIn(str(self.dir), target)

    def test_sigkill_after_batches_leaves_export_dir_untouched(self) -> None:
        original = (b'{"id":"a","v":1}\n{"id":"a","v":2}\n') * 4000
        _write_export(self.path, original)
        paths, before = self._plant_foreign_export_dir_objects()
        sentinel = self.dir / "pause-ready"
        worker = Path(__file__).resolve().parent / "export_compaction_sigkill_worker.py"
        pause_after = export_compaction_mod._SQLITE_BATCH * 2 + 8
        proc = subprocess.Popen(
            [sys.executable, str(worker), str(self.path), str(sentinel), str(pause_after)],
            cwd=str(Path(__file__).resolve().parents[1]),
        )
        deadline = time.monotonic() + 20
        while time.monotonic() < deadline and not sentinel.is_file():
            if proc.poll() is not None:
                raise AssertionError(f"worker exited early with {proc.returncode}")
            time.sleep(0.05)
        self.assertTrue(sentinel.is_file(), "worker did not pause after batches")
        os.kill(proc.pid, signal.SIGKILL)
        proc.wait(5)
        self.assertEqual(self.path.read_bytes(), original)
        self.assertEqual(_tree_snapshot(paths), before)

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

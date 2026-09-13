"""Bounded-memory, crash-safe compaction for knowledge_units.jsonl.

Replaces whole-export Python materialization with a SQLite offset index and
streaming atomic publication. The public entry point preserves the ingest
caller contract: last value per non-empty string ID, first-occurrence order,
byte-identical no-op when every nonblank row is uniquely valid, and
fail-closed refusal on malformed or oversized records.
"""

from __future__ import annotations

import json
import os
import sqlite3
import stat
from dataclasses import dataclass
from pathlib import Path

from atomic_files import PrePublicationError, atomic_write_stream
from purge_locks import export_flock_path

MAX_RECORD_BYTES = 16 * 1024 * 1024
_READ_CHUNK_BYTES = 64 * 1024
_SQLITE_CACHE_KIB = 8192
_SQLITE_BATCH = 512


class InvalidExportRecordError(PrePublicationError):
    """A nonblank row is not a valid UTF-8 JSON object with a string ID."""


class OversizedExportRecordError(PrePublicationError):
    """A record exceeded the 16 MiB inclusive ceiling while scanning."""


class ExportIdentityChangedError(PrePublicationError):
    """The export path no longer identifies the file observed at scan start."""


@dataclass(frozen=True)
class _FileIdentity:  # pylint: disable=too-many-instance-attributes
    dev: int
    ino: int
    size: int
    mode: int
    uid: int
    gid: int
    mtime_ns: int
    ctime_ns: int


def compact_units_export(export_path: Path) -> int:
    """Compact *export_path* under the export flock. Return lines removed."""
    path = Path(export_path)
    try:
        st = os.lstat(path)
    except FileNotFoundError:
        return 0
    if stat.S_ISLNK(st.st_mode):
        raise InvalidExportRecordError(f"export path is a symlink: {path}")
    if not stat.S_ISREG(st.st_mode):
        return 0
    with export_flock_path(path):
        return _compact_locked(path)


def _identity_from_stat(st: os.stat_result) -> _FileIdentity:
    return _FileIdentity(
        dev=st.st_dev,
        ino=st.st_ino,
        size=st.st_size,
        mode=st.st_mode,
        uid=st.st_uid,
        gid=st.st_gid,
        mtime_ns=st.st_mtime_ns,
        ctime_ns=st.st_ctime_ns,
    )


def _assert_regular_identity(path: Path, expected: _FileIdentity) -> None:
    try:
        st = os.lstat(path)
    except OSError as exc:
        raise ExportIdentityChangedError(
            f"export path disappeared before publication: {path}: {exc}"
        ) from exc
    if not stat.S_ISREG(st.st_mode):
        raise ExportIdentityChangedError(f"export path is no longer a regular file: {path}")
    actual = _identity_from_stat(st)
    if actual != expected:
        raise ExportIdentityChangedError(
            f"export identity changed before publication: {path}"
        )


def _read_bounded_record(fd: int) -> bytes | None:
    """Read one binary record with an incremental 16 MiB ceiling.

    Each os.read is limited to remaining budget plus one detection byte.
    Returns None at EOF with no pending bytes. A final unterminated record
    at or below the ceiling is returned as-is.
    """
    chunks: list[bytes] = []
    consumed = 0
    while True:
        remaining = MAX_RECORD_BYTES - consumed
        buf = os.read(fd, min(remaining + 1, _READ_CHUNK_BYTES))
        if not buf:
            if not chunks:
                return None
            return b"".join(chunks)
        newline = buf.find(b"\n")
        if newline >= 0:
            record = b"".join(chunks) + buf[: newline + 1]
            unread = len(buf) - (newline + 1)
            if unread:
                os.lseek(fd, -unread, os.SEEK_CUR)
            if len(record) > MAX_RECORD_BYTES:
                raise OversizedExportRecordError(
                    "export record exceeds 16 MiB including terminator"
                )
            return record
        consumed += len(buf)
        if consumed > MAX_RECORD_BYTES:
            raise OversizedExportRecordError(
                "export record exceeds 16 MiB including terminator"
            )
        chunks.append(buf)


def _pread_exact(fd: int, offset: int, length: int) -> bytes:
    parts: list[bytes] = []
    remaining = length
    pos = offset
    while remaining:
        chunk = os.pread(fd, remaining, pos)
        if not chunk:
            raise PrePublicationError(
                f"short pread at offset {offset} length {length}"
            )
        parts.append(chunk)
        got = len(chunk)
        remaining -= got
        pos += got
    return b"".join(parts)


def _validate_record(raw: bytes) -> str:
    try:
        text = raw.strip().decode("utf-8")
    except UnicodeDecodeError as exc:
        raise InvalidExportRecordError("export record is not valid UTF-8") from exc
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as exc:
        raise InvalidExportRecordError("export record is not valid JSON") from exc
    if not isinstance(parsed, dict):
        raise InvalidExportRecordError("export record is not a JSON object")
    uid = parsed.get("id", "")
    if not isinstance(uid, str) or uid == "":
        raise InvalidExportRecordError("export record lacks a non-empty string id")
    return uid


def _connect_index() -> sqlite3.Connection:
    """Open SQLite's private deleted on-disk temp database for this scan.

    ``sqlite3.connect("")`` is disposable scratch, never publication
    authority, and is not a pathname in the export directory.
    """
    conn = sqlite3.connect("")
    try:
        conn.execute("PRAGMA journal_mode=OFF")
        conn.execute(f"PRAGMA cache_size=-{_SQLITE_CACHE_KIB}")
        conn.execute(
            "CREATE TABLE retained ("
            "id TEXT PRIMARY KEY NOT NULL,"
            "first_seq INTEGER NOT NULL,"
            "last_offset INTEGER NOT NULL,"
            "last_length INTEGER NOT NULL)"
        )
        conn.execute("CREATE INDEX retained_first_seq ON retained(first_seq)")
    except sqlite3.Error:
        try:
            conn.close()
        except sqlite3.Error:
            pass
        raise
    return conn


def _index_row(conn: sqlite3.Connection, uid: str, seq: int, offset: int, length: int) -> None:
    conn.execute(
        "INSERT INTO retained(id, first_seq, last_offset, last_length) "
        "VALUES (?, ?, ?, ?) "
        "ON CONFLICT(id) DO UPDATE SET "
        "last_offset=excluded.last_offset, last_length=excluded.last_length",
        (uid, seq, offset, length),
    )


def _open_export(path: Path) -> int:
    flags = os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW
    try:
        return os.open(str(path), flags)
    except OSError as exc:
        raise PrePublicationError(f"failed to open export for compaction: {path}: {exc}") from exc


def _scan_into_index(fd: int, conn: sqlite3.Connection) -> tuple[int, int]:
    nonblank = 0
    seq = 0
    offset = 0
    pending = 0
    while True:
        record = _read_bounded_record(fd)
        if record is None:
            break
        length = len(record)
        start = offset
        offset += length
        if not record.strip():
            continue
        nonblank += 1
        uid = _validate_record(record)
        seq += 1
        _index_row(conn, uid, seq, start, length)
        pending += 1
        if pending >= _SQLITE_BATCH:
            conn.commit()
            pending = 0
    if pending:
        conn.commit()
    retained = conn.execute("SELECT COUNT(*) FROM retained").fetchone()[0]
    return nonblank, int(retained)


def _publish_compacted(path: Path, fd: int, identity: _FileIdentity, conn: sqlite3.Connection) -> None:
    cursor = conn.execute(
        "SELECT last_offset, last_length FROM retained ORDER BY first_seq"
    )

    def _write(handle) -> None:
        for last_offset, last_length in cursor:
            raw = _pread_exact(fd, int(last_offset), int(last_length))
            handle.write(raw.strip() + b"\n")

    def _validate() -> None:
        _assert_regular_identity(path, identity)

    atomic_write_stream(
        path,
        _write,
        preserve_mode=True,
        validate_before_replace=_validate,
    )


def _compact_locked(path: Path) -> int:
    fd = _open_export(path)
    conn: sqlite3.Connection | None = None
    try:
        fd_st = os.fstat(fd)
        if not stat.S_ISREG(fd_st.st_mode):
            raise InvalidExportRecordError(f"export is not a regular file: {path}")
        identity = _identity_from_stat(fd_st)
        _assert_regular_identity(path, identity)
        try:
            conn = _connect_index()
            nonblank, retained = _scan_into_index(fd, conn)
        except sqlite3.Error as exc:
            if conn is not None:
                try:
                    conn.close()
                except sqlite3.Error:
                    pass
                conn = None
            raise PrePublicationError(
                f"compaction index failed for {path}: {exc}"
            ) from exc
        if nonblank == 0 or retained >= nonblank:
            _assert_regular_identity(path, identity)
            return 0
        _publish_compacted(path, fd, identity, conn)
        return nonblank - retained
    finally:
        if conn is not None:
            try:
                conn.close()
            except sqlite3.Error:
                pass
        try:
            os.close(fd)
        except OSError:
            pass

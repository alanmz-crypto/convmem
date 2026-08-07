"""Fail-closed, regular-file-only snapshots for disposable Chroma roots.

The authoritative build collection is never opened by an evaluation worker.
This module creates a fresh disposable copy while proving that the source did
not change during the copy and that the clone has the same file-content tree.
It does not authorize an operation; callers must bind the source and destination
to an approved manifest before calling it.
"""

from __future__ import annotations

import hashlib
import json
import os
import stat
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from eval_corpus.secure_fs import (
    FilesystemAuthorizationError,
    assert_contained_no_symlink,
    assert_nonoverlapping_roots,
    create_absent_attempt_root,
    receipt_for_path,
)

CLONE_SCHEMA_VERSION = "chroma_disposable_clone_v1"


class ChromaCloneError(FilesystemAuthorizationError):
    """The source or disposable clone failed an integrity invariant."""


def _regular_file_record(path: Path, relative: str) -> dict[str, Any]:
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    except OSError as exc:
        raise ChromaCloneError(f"cannot open clone source file {path}: {exc}") from exc
    try:
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1:
            raise ChromaCloneError(
                f"clone source requires a singly-linked regular file: {path}"
            )
        digest = hashlib.sha256()
        size = 0
        while True:
            chunk = os.read(fd, 1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
            size += len(chunk)
        after = os.fstat(fd)
    finally:
        os.close(fd)
    identity_fields = ("st_dev", "st_ino", "st_nlink", "st_size", "st_mtime_ns", "st_ctime_ns")
    if any(getattr(before, field) != getattr(after, field) for field in identity_fields):
        raise ChromaCloneError(f"clone source changed while hashing: {path}")
    if size != before.st_size:
        raise ChromaCloneError(f"clone source size changed while hashing: {path}")
    return {
        "path": relative,
        "kind": "file",
        "size": size,
        "sha256": digest.hexdigest(),
        "executable": bool(stat.S_IMODE(before.st_mode) & 0o111),
        "device": before.st_dev,
        "inode": before.st_ino,
        "link_count": before.st_nlink,
    }


def _walk_records(root: Path) -> list[dict[str, Any]]:
    root_info = root.lstat()
    if stat.S_ISLNK(root_info.st_mode) or not stat.S_ISDIR(root_info.st_mode):
        raise ChromaCloneError(f"clone root must be a real directory: {root}")
    records: list[dict[str, Any]] = [
        {
            "path": "",
            "kind": "directory",
            "device": root_info.st_dev,
            "inode": root_info.st_ino,
            "link_count": root_info.st_nlink,
            "executable": bool(stat.S_IMODE(root_info.st_mode) & 0o111),
        }
    ]
    pending = [root]
    while pending:
        current = pending.pop()
        try:
            entries = sorted(os.scandir(current), key=lambda entry: entry.name)
        except OSError as exc:
            raise ChromaCloneError(f"cannot enumerate clone root {current}: {exc}") from exc
        for entry in entries:
            path = Path(entry.path)
            relative = path.relative_to(root).as_posix()
            try:
                info = entry.stat(follow_symlinks=False)
            except OSError as exc:
                raise ChromaCloneError(f"cannot stat clone entry {path}: {exc}") from exc
            if stat.S_ISLNK(info.st_mode):
                raise ChromaCloneError(f"clone tree forbids symlink: {path}")
            if stat.S_ISDIR(info.st_mode):
                records.append(
                    {
                        "path": relative,
                        "kind": "directory",
                        "device": info.st_dev,
                        "inode": info.st_ino,
                        "link_count": info.st_nlink,
                        "executable": bool(stat.S_IMODE(info.st_mode) & 0o111),
                    }
                )
                pending.append(path)
            elif stat.S_ISREG(info.st_mode):
                records.append(_regular_file_record(path, relative))
            else:
                raise ChromaCloneError(f"clone tree allows regular files/directories only: {path}")
    return sorted(records, key=lambda item: (item["path"], item["kind"]))


def _content_records(records: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            key: record[key]
            for key in ("path", "kind", "size", "sha256", "executable")
            if key in record
        }
        for record in records
    ]


def _content_fingerprint(records: Iterable[dict[str, Any]]) -> str:
    payload = json.dumps(
        _content_records(records),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _open_relative(root_fd: int, parts: tuple[str, ...], *, flags: int) -> int:
    current_fd = os.dup(root_fd)
    try:
        for part in parts[:-1]:
            next_fd = os.open(
                part,
                os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                dir_fd=current_fd,
            )
            os.close(current_fd)
            current_fd = next_fd
        return os.open(parts[-1], flags | os.O_NOFOLLOW, dir_fd=current_fd)
    finally:
        os.close(current_fd)


def _ensure_relative_directory(root_fd: int, parts: tuple[str, ...]) -> int:
    current_fd = os.dup(root_fd)
    try:
        for part in parts:
            try:
                os.mkdir(part, mode=0o700, dir_fd=current_fd)
            except FileExistsError:
                pass
            next_fd = os.open(
                part,
                os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                dir_fd=current_fd,
            )
            os.close(current_fd)
            current_fd = next_fd
        return current_fd
    except Exception:
        os.close(current_fd)
        raise


def _copy_file(
    source_root_fd: int,
    destination_root_fd: int,
    record: dict[str, Any],
) -> None:
    parts = tuple(record["path"].split("/"))
    source_fd = _open_relative(
        source_root_fd,
        parts,
        flags=os.O_RDONLY,
    )
    try:
        source_info = os.fstat(source_fd)
        if (
            not stat.S_ISREG(source_info.st_mode)
            or source_info.st_nlink != 1
            or source_info.st_dev != record["device"]
            or source_info.st_ino != record["inode"]
        ):
            raise ChromaCloneError(f"clone source identity changed: {record['path']}")
        destination_parent_fd = _ensure_relative_directory(
            destination_root_fd,
            parts[:-1],
        )
        try:
            destination_fd = os.open(
                parts[-1],
                os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                0o600,
                dir_fd=destination_parent_fd,
            )
            try:
                while True:
                    chunk = os.read(source_fd, 1024 * 1024)
                    if not chunk:
                        break
                    view = memoryview(chunk)
                    while view:
                        written = os.write(destination_fd, view)
                        if written <= 0:
                            raise ChromaCloneError(
                                f"short write while cloning {record['path']}"
                            )
                        view = view[written:]
                os.fchmod(destination_fd, 0o700 if record["executable"] else 0o600)
                os.fsync(destination_fd)
            finally:
                os.close(destination_fd)
            os.fsync(destination_parent_fd)
        finally:
            os.close(destination_parent_fd)
    finally:
        after = os.fstat(source_fd)
        os.close(source_fd)
    if (
        after.st_dev != source_info.st_dev
        or after.st_ino != source_info.st_ino
        or after.st_nlink != source_info.st_nlink
        or after.st_size != source_info.st_size
        or after.st_mtime_ns != source_info.st_mtime_ns
        or after.st_ctime_ns != source_info.st_ctime_ns
    ):
        raise ChromaCloneError(f"clone source changed while copying: {record['path']}")


def clone_chroma_root(
    source: Path | str,
    destination: Path | str,
    *,
    approved_source_root: Path | str,
    approved_destination_parent: Path | str,
) -> dict[str, Any]:
    """Copy one authoritative Chroma root into a fresh disposable root.

    The destination is a direct absent child of ``approved_destination_parent``.
    A partial destination is intentionally left in place on failure so the
    caller can quarantine the failed attempt rather than repair or reuse it.
    """
    source_path = assert_contained_no_symlink(source, approved_source_root)
    source_info = receipt_for_path(source_path)
    if source_info["kind"] != "directory":
        raise ChromaCloneError(f"clone source must be a directory: {source_path}")
    destination_path = assert_contained_no_symlink(
        destination,
        approved_destination_parent,
    )
    assert_nonoverlapping_roots(source_path, destination_path)
    before = _walk_records(source_path)
    destination_receipt = create_absent_attempt_root(
        destination_path,
        approved_destination_parent,
    )
    source_fd = os.open(source_path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    destination_fd = os.open(
        destination_path,
        os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
    )
    try:
        for record in before:
            if record["kind"] == "directory" and record["path"]:
                directory_fd = _ensure_relative_directory(
                    destination_fd,
                    tuple(record["path"].split("/")),
                )
                os.close(directory_fd)
        for record in before:
            if record["kind"] == "file":
                _copy_file(source_fd, destination_fd, record)
        os.fsync(destination_fd)
    finally:
        os.close(source_fd)
        os.close(destination_fd)
    after = _walk_records(source_path)
    if before != after:
        raise ChromaCloneError("authoritative Chroma root changed during clone")
    clone_records = _walk_records(destination_path)
    if _content_fingerprint(before) != _content_fingerprint(clone_records):
        raise ChromaCloneError("disposable Chroma clone content does not match source")
    return {
        "schema_version": CLONE_SCHEMA_VERSION,
        "source": source_info,
        "destination": destination_receipt,
        "source_content_fingerprint": _content_fingerprint(before),
        "clone_content_fingerprint": _content_fingerprint(clone_records),
        "source_entry_count": len(before),
        "clone_entry_count": len(clone_records),
        "source_records": before,
        "clone_records": clone_records,
    }


__all__ = ["CLONE_SCHEMA_VERSION", "ChromaCloneError", "clone_chroma_root"]

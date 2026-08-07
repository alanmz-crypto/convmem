"""No-follow filesystem primitives for evaluation attempts and evidence.

The real-evaluation lane must not turn a manifest path comparison into a
time-of-check/time-of-use promise.  These helpers keep a directory descriptor
open for writes, reject links, and return inode/device receipts for later
evidence binding.  They do not authorize an operation; callers must still use
the run-manifest binder.
"""

from __future__ import annotations

import hashlib
import json
import os
import stat
import uuid
from pathlib import Path
from typing import Any


class FilesystemAuthorizationError(PermissionError):
    """A path, link, or attempt-root invariant is unsafe."""


def _absolute(path: Path | str) -> Path:
    return Path(path).expanduser().absolute()


def _lstat(path: Path) -> os.stat_result:
    try:
        return path.lstat()
    except OSError as exc:
        raise FilesystemAuthorizationError(f"cannot lstat {path}: {exc}") from exc


def _require_regular_single_link(path: Path) -> os.stat_result:
    info = _lstat(path)
    if stat.S_ISLNK(info.st_mode):
        raise FilesystemAuthorizationError(f"symlink is forbidden: {path}")
    if not stat.S_ISREG(info.st_mode):
        raise FilesystemAuthorizationError(f"regular file required: {path}")
    if info.st_nlink != 1:
        raise FilesystemAuthorizationError(
            f"hard-linked file is forbidden: {path} has link_count={info.st_nlink}"
        )
    return info


def _require_directory(path: Path) -> os.stat_result:
    info = _lstat(path)
    if stat.S_ISLNK(info.st_mode):
        raise FilesystemAuthorizationError(f"symlink is forbidden: {path}")
    if not stat.S_ISDIR(info.st_mode):
        raise FilesystemAuthorizationError(f"directory required: {path}")
    return info


def assert_contained_no_symlink(path: Path | str, approved_root: Path | str) -> Path:
    """Return absolute ``path`` only if it is inside a real, link-free root.

    Component comparison, rather than a string prefix, prevents ``root-old``
    from being accepted as a child of ``root``.  Existing components from the
    approved root through the target are lstat'd without following links.
    """
    root = _absolute(approved_root)
    target = _absolute(path)
    _require_directory(root)
    try:
        relative = target.relative_to(root)
    except ValueError as exc:
        raise FilesystemAuthorizationError(
            f"path escapes approved root: {target} not under {root}"
        ) from exc

    current = root
    for part in relative.parts:
        current = current / part
        if not current.exists() and not current.is_symlink():
            # Missing suffix is permitted for a leaf to be created.  No later
            # component can exist if its parent does not exist.
            break
        info = _lstat(current)
        if stat.S_ISLNK(info.st_mode):
            raise FilesystemAuthorizationError(f"symlink is forbidden: {current}")
        if current != target and not stat.S_ISDIR(info.st_mode):
            raise FilesystemAuthorizationError(f"non-directory parent: {current}")
    return target


def receipt_for_path(path: Path | str, *, require_regular: bool = False) -> dict[str, Any]:
    """Return a stable device/inode receipt; regular evidence files need nlink=1."""
    target = _absolute(path)
    info = _require_regular_single_link(target) if require_regular else _lstat(target)
    if stat.S_ISLNK(info.st_mode):
        raise FilesystemAuthorizationError(f"symlink is forbidden: {target}")
    kind = "regular" if stat.S_ISREG(info.st_mode) else "directory" if stat.S_ISDIR(info.st_mode) else "other"
    return {
        "path": str(target),
        "device": info.st_dev,
        "inode": info.st_ino,
        "mode": stat.S_IMODE(info.st_mode),
        "link_count": info.st_nlink,
        "kind": kind,
        "size": info.st_size,
    }


def create_absent_attempt_root(path: Path | str, approved_parent: Path | str) -> dict[str, Any]:
    """Create one fresh sibling attempt root and return its inode receipt."""
    parent = _absolute(approved_parent)
    target = assert_contained_no_symlink(path, parent)
    if target.parent != parent:
        raise FilesystemAuthorizationError(
            "attempt root must be a direct child of its approved parent"
        )
    if target.exists() or target.is_symlink():
        raise FilesystemAuthorizationError(f"attempt root must be absent: {target}")
    parent_fd = os.open(parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        os.mkdir(target.name, mode=0o700, dir_fd=parent_fd)
        os.fsync(parent_fd)
    except OSError as exc:
        raise FilesystemAuthorizationError(f"cannot create attempt root {target}: {exc}") from exc
    finally:
        os.close(parent_fd)
    return receipt_for_path(target)


def assert_nonoverlapping_roots(*roots: Path | str) -> None:
    """Refuse equal, nested, or overlapping arm/attempt roots."""
    normalized = [_absolute(root) for root in roots]
    if len(set(normalized)) != len(normalized):
        raise FilesystemAuthorizationError("attempt roots must be distinct")
    for index, left in enumerate(normalized):
        for right in normalized[index + 1 :]:
            try:
                right.relative_to(left)
            except ValueError:
                try:
                    left.relative_to(right)
                except ValueError:
                    continue
            raise FilesystemAuthorizationError(
                f"attempt roots must not overlap or nest: {left} and {right}"
            )


def _open_regular_no_follow(path: Path) -> tuple[int, os.stat_result]:
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode):
            raise FilesystemAuthorizationError(f"regular file required: {path}")
        if info.st_nlink != 1:
            raise FilesystemAuthorizationError(
                f"hard-linked file is forbidden: {path} has link_count={info.st_nlink}"
            )
        return fd, info
    except Exception:
        os.close(fd)
        raise


def copy_immutable_input(
    source: Path | str,
    destination: Path | str,
    *,
    approved_root: Path | str,
) -> dict[str, Any]:
    """Copy source bytes once into an absent, link-free destination.

    The returned digest is over the exact bytes parsed by callers.  Both source
    and destination receipts make path replacement visible to evidence review.
    """
    root = _absolute(approved_root)
    src = assert_contained_no_symlink(source, root)
    dest = assert_contained_no_symlink(destination, root)
    if dest.exists() or dest.is_symlink():
        raise FilesystemAuthorizationError(f"immutable destination must be absent: {dest}")
    _require_directory(dest.parent)
    source_fd, source_info = _open_regular_no_follow(src)
    parent_fd = os.open(dest.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    temp_name = f".{dest.name}.{uuid.uuid4().hex}.tmp"
    output_fd: int | None = None
    digest = hashlib.sha256()
    try:
        output_fd = os.open(
            temp_name,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
            0o600,
            dir_fd=parent_fd,
        )
        while True:
            chunk = os.read(source_fd, 1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
            offset = 0
            while offset < len(chunk):
                written = os.write(output_fd, chunk[offset:])
                if written <= 0:
                    raise FilesystemAuthorizationError(
                        f"short write while copying immutable input: {dest}"
                    )
                offset += written
        os.fsync(output_fd)
        os.close(output_fd)
        output_fd = None
        # A plain rename would replace a destination created after the initial
        # lstat. Linking the temp inode into the absent leaf is atomic and
        # fails with EEXIST instead of overwriting a racing file; removing the
        # temp name leaves the destination with one link.
        os.link(
            temp_name,
            dest.name,
            src_dir_fd=parent_fd,
            dst_dir_fd=parent_fd,
            follow_symlinks=False,
        )
        os.unlink(temp_name, dir_fd=parent_fd)
        os.fsync(parent_fd)
        source_after = os.fstat(source_fd)
        if (
            source_after.st_dev != source_info.st_dev
            or source_after.st_ino != source_info.st_ino
            or source_after.st_size != source_info.st_size
            or source_after.st_mtime_ns != source_info.st_mtime_ns
            or source_after.st_ctime_ns != source_info.st_ctime_ns
        ):
            raise FilesystemAuthorizationError(
                "source changed while immutable input was being copied"
            )
        source_path_info = _require_regular_single_link(src)
        if (
            source_path_info.st_dev != source_info.st_dev
            or source_path_info.st_ino != source_info.st_ino
        ):
            raise FilesystemAuthorizationError(
                "source path identity changed while immutable input was being copied"
            )
    except Exception:
        if output_fd is not None:
            os.close(output_fd)
        try:
            os.unlink(temp_name, dir_fd=parent_fd)
        except OSError:
            pass
        raise
    finally:
        os.close(source_fd)
        os.close(parent_fd)
    return {
        "sha256": digest.hexdigest(),
        "source": receipt_for_path(src, require_regular=True),
        "destination": receipt_for_path(dest, require_regular=True),
        "source_device": source_info.st_dev,
        "source_inode": source_info.st_ino,
    }


def write_absent_json(
    path: Path | str,
    obj: Any,
    *,
    approved_root: Path | str,
) -> dict[str, Any]:
    """Publish one JSON file without replacing an existing leaf.

    The final name is created with ``link`` only after the complete payload is
    fsynced.  A racing file or symlink therefore makes publication fail closed
    instead of being replaced or followed.
    """
    target = assert_contained_no_symlink(path, approved_root)
    parent = target.parent
    _require_directory(parent)
    payload = json.dumps(
        obj,
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
        allow_nan=False,
    ).encode("utf-8") + b"\n"
    parent_fd = os.open(parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    temp_name = f".{target.name}.{uuid.uuid4().hex}.tmp"
    temp_fd: int | None = None
    try:
        temp_fd = os.open(
            temp_name,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
            0o600,
            dir_fd=parent_fd,
        )
        offset = 0
        while offset < len(payload):
            written = os.write(temp_fd, payload[offset:])
            if written <= 0:
                raise FilesystemAuthorizationError(f"short JSON write: {target}")
            offset += written
        os.fsync(temp_fd)
        os.close(temp_fd)
        temp_fd = None
        os.link(
            temp_name,
            target.name,
            src_dir_fd=parent_fd,
            dst_dir_fd=parent_fd,
            follow_symlinks=False,
        )
        os.unlink(temp_name, dir_fd=parent_fd)
        os.fsync(parent_fd)
        return receipt_for_path(target, require_regular=True)
    except FileExistsError as exc:
        raise FilesystemAuthorizationError(
            f"JSON output must remain absent until publication: {target}"
        ) from exc
    finally:
        if temp_fd is not None:
            os.close(temp_fd)
        try:
            os.unlink(temp_name, dir_fd=parent_fd)
        except OSError:
            pass
        os.close(parent_fd)


def assert_regular_evidence_tree(root: Path | str) -> None:
    """Evidence directories may contain directories and singly linked regular files only."""
    base = _absolute(root)
    _require_directory(base)
    for candidate in sorted(base.rglob("*")):
        info = _lstat(candidate)
        if stat.S_ISLNK(info.st_mode):
            raise FilesystemAuthorizationError(f"evidence symlink forbidden: {candidate}")
        if stat.S_ISDIR(info.st_mode):
            continue
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
            raise FilesystemAuthorizationError(
                f"evidence must contain singly linked regular files only: {candidate}"
            )


__all__ = [
    "FilesystemAuthorizationError",
    "assert_contained_no_symlink",
    "assert_nonoverlapping_roots",
    "assert_regular_evidence_tree",
    "copy_immutable_input",
    "create_absent_attempt_root",
    "receipt_for_path",
    "write_absent_json",
]

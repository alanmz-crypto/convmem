"""PID lock helpers for long-running convmem daemons."""

from __future__ import annotations

import os
import sys
from collections.abc import Callable
from errno import ELOOP
from pathlib import Path

from shadow_authorization import AuthorizationRefused, open_directory_nofollow


def _open_lock_parent(lock_path: Path, *, create: bool) -> int | None:
    if create:
        lock_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        return open_directory_nofollow(lock_path.parent)
    except AuthorizationRefused as exc:
        if not create:
            return None
        raise RuntimeError(
            f"refusing unsafe lock directory: {lock_path.parent}"
        ) from exc


def _read_pid(lock_path: Path, parent_fd: int) -> int | None:
    """Read a PID without following a symlink at the lock path."""
    try:
        fd = os.open(
            lock_path.name,
            os.O_RDONLY | os.O_CLOEXEC | getattr(os, "O_NOFOLLOW", 0),
            dir_fd=parent_fd,
        )
    except FileNotFoundError:
        return None
    except OSError as exc:
        if exc.errno == ELOOP:
            raise RuntimeError(f"refusing symlink lock path: {lock_path}") from exc
        return None
    try:
        with os.fdopen(fd, "r", encoding="utf-8") as handle:
            fd = -1
            try:
                return int(handle.read().strip())
            except ValueError:
                return 0
    finally:
        if fd >= 0:
            os.close(fd)


def _create_pid_lock(lock_path: Path, pid: int, parent_fd: int) -> bool:
    """Create a PID lock atomically, refusing a symlink at the leaf path."""
    try:
        fd = os.open(
            lock_path.name,
            os.O_WRONLY
            | os.O_CREAT
            | os.O_EXCL
            | os.O_CLOEXEC
            | getattr(os, "O_NOFOLLOW", 0),
            0o600,
            dir_fd=parent_fd,
        )
    except FileExistsError:
        return False
    except OSError as exc:
        if exc.errno == ELOOP:
            raise RuntimeError(f"refusing symlink lock path: {lock_path}") from exc
        raise
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            fd = -1
            handle.write(str(pid))
            handle.flush()
            os.fsync(handle.fileno())
    finally:
        if fd >= 0:
            os.close(fd)
    return True


def acquire_pid_lock(
    lock_path: Path,
    *,
    pid: int,
    is_live_pid: Callable[[int], bool],
    label: str,
) -> None:
    """Acquire a PID lock without following attacker-controlled leaf symlinks."""
    parent_fd = _open_lock_parent(lock_path, create=True)
    assert parent_fd is not None
    try:
        while not _create_pid_lock(lock_path, pid, parent_fd):
            other_pid = _read_pid(lock_path, parent_fd) or 0
            if other_pid > 0 and is_live_pid(other_pid):
                print(
                    f"[{label}] another instance is running (pid {other_pid}). "
                    f"Lock: {lock_path}",
                    file=sys.stderr,
                )
                sys.exit(1)
            try:
                # unlink removes a symlink itself, never its target. A symlink
                # was already rejected by _read_pid, and O_NOFOLLOW closes the
                # create race if one is inserted before the next attempt.
                os.unlink(lock_path.name, dir_fd=parent_fd)
            except FileNotFoundError:
                continue
    finally:
        os.close(parent_fd)


def _pid_is_live(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def acquire_lock(lock_path: Path, *, label: str = "process") -> None:
    acquire_pid_lock(
        lock_path,
        pid=os.getpid(),
        is_live_pid=_pid_is_live,
        label=label,
    )


def release_lock(lock_path: Path) -> None:
    parent_fd = _open_lock_parent(lock_path, create=False)
    if parent_fd is None:
        return
    try:
        if _read_pid(lock_path, parent_fd) == os.getpid():
            try:
                os.unlink(lock_path.name, dir_fd=parent_fd)
            except FileNotFoundError:
                pass
    except (OSError, RuntimeError):
        # A lock replaced by a symlink or an unreadable path must not make the
        # daemon follow or remove an attacker-selected target during cleanup.
        pass
    finally:
        os.close(parent_fd)

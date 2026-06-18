"""PID lock helpers for long-running convmem daemons."""

from __future__ import annotations

import os
import sys
from pathlib import Path


def acquire_lock(lock_path: Path, *, label: str = "process") -> None:
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    if lock_path.exists():
        try:
            other_pid = int(lock_path.read_text().strip())
        except ValueError:
            other_pid = 0
        if other_pid > 0:
            try:
                os.kill(other_pid, 0)
            except OSError:
                pass
            else:
                print(
                    f"[{label}] another instance is running (pid {other_pid}). "
                    f"Lock: {lock_path}",
                    file=sys.stderr,
                )
                sys.exit(1)
        lock_path.unlink(missing_ok=True)
    lock_path.write_text(str(os.getpid()), encoding="utf-8")


def release_lock(lock_path: Path) -> None:
    if not lock_path.exists():
        return
    try:
        if int(lock_path.read_text().strip()) == os.getpid():
            lock_path.unlink(missing_ok=True)
    except (ValueError, OSError):
        lock_path.unlink(missing_ok=True)

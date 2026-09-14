"""Linux /proc helpers shared by hermetic RSS workers and fd tests."""

from __future__ import annotations

import os
import resource
from pathlib import Path

_PROC_STATUS = Path("/proc/self/status")
_PROC_FD = Path("/proc/self/fd")


def rss_bytes() -> int:
    """Current resident set size from /proc, or 0 if unavailable."""
    status = _PROC_STATUS.read_text(encoding="utf-8")
    for line in status.splitlines():
        if line.startswith("VmRSS:"):
            return int(line.split()[1]) * 1024
    return 0


def peak_rss_bytes() -> int:
    """Peak resident set size from /proc, with rusage fallback."""
    status = _PROC_STATUS.read_text(encoding="utf-8")
    for line in status.splitlines():
        if line.startswith("VmHWM:"):
            return int(line.split()[1]) * 1024
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024


def proc_fd_targets() -> list[str]:
    """Resolved /proc/self/fd symlink targets; skips unreadable entries."""
    found: list[str] = []
    for entry in _PROC_FD.iterdir():
        try:
            found.append(os.readlink(entry))
        except OSError:
            continue
    return found

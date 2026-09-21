"""Live suite deadline/output/tmp sampling with process-group reaping."""

from __future__ import annotations

import fcntl
import os
import select
import signal
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import List

from constants import (
    SUITE_OUTPUT_LIMIT_BYTES,
    SUITE_WALL_DEADLINE_SEC,
    TMP_SAMPLE_INTERVAL_SEC,
)


@dataclass
class SuiteRunResult:
    name: str
    returncode: int
    elapsed_sec: float
    combined_output_bytes: int
    max_tmp_bytes: int
    tmp_sample_interval_sec: float
    killed_reason: str | None
    stdout: str
    stderr: str


def _tmp_used_bytes(path: str = "/tmp") -> int:
    total = 0
    root = Path(path)
    if not root.exists():
        return 0
    for dirpath, _dirnames, filenames in os.walk(root, followlinks=False):
        for name in filenames:
            p = Path(dirpath) / name
            try:
                if p.is_file() and not p.is_symlink():
                    total += p.stat().st_size
            except OSError:
                continue
    return total


def _kill_process_group(proc: subprocess.Popen[bytes]) -> None:
    if proc.pid is None:
        return
    try:
        os.killpg(proc.pid, signal.SIGKILL)
    except ProcessLookupError:
        try:
            proc.kill()
        except ProcessLookupError:
            pass


def _set_nonblocking(fd: int) -> None:
    flags = fcntl.fcntl(fd, fcntl.F_GETFL)
    fcntl.fcntl(fd, fcntl.F_SETFL, flags | os.O_NONBLOCK)


def _bounded_drain(fd: int, limit_remaining: int) -> bytes:
    """Drain remaining bytes after kill without treating overflow as success."""
    chunks: list[bytes] = []
    total = 0
    while total < limit_remaining:
        try:
            chunk = os.read(fd, min(65536, limit_remaining - total))
        except BlockingIOError:
            break
        except OSError:
            break
        if not chunk:
            break
        chunks.append(chunk)
        total += len(chunk)
    return b"".join(chunks)


def run_suite_with_limits(
    name: str,
    argv: List[str],
    *,
    deadline_sec: float = SUITE_WALL_DEADLINE_SEC,
    output_limit: int = SUITE_OUTPUT_LIMIT_BYTES,
    sample_interval: float = TMP_SAMPLE_INTERVAL_SEC,
) -> SuiteRunResult:
    """Enforce deadline/output live with raw os.read; reap process group on violation."""
    started = time.monotonic()
    proc = subprocess.Popen(
        argv,
        cwd="/src",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=False,
        close_fds=True,
        start_new_session=True,
    )
    assert proc.stdout is not None and proc.stderr is not None
    stdout_fd = proc.stdout.fileno()
    stderr_fd = proc.stderr.fileno()
    _set_nonblocking(stdout_fd)
    _set_nonblocking(stderr_fd)

    out_buf = bytearray()
    err_buf = bytearray()
    combined = 0
    max_tmp = 0
    killed_reason = None
    next_sample = started
    open_fds = {stdout_fd, stderr_fd}

    while open_fds or proc.poll() is None:
        now = time.monotonic()
        if now - started > deadline_sec:
            killed_reason = "deadline"
            _kill_process_group(proc)
            break
        if now >= next_sample:
            max_tmp = max(max_tmp, _tmp_used_bytes("/tmp"))
            next_sample = now + sample_interval
        timeout = min(0.2, max(0.0, next_sample - now))
        ready, _, _ = select.select(list(open_fds), [], [], timeout)
        for fd in ready:
            try:
                chunk = os.read(fd, 65536)
            except BlockingIOError:
                continue
            except OSError:
                open_fds.discard(fd)
                continue
            if not chunk:
                open_fds.discard(fd)
                continue
            if fd == stdout_fd:
                out_buf.extend(chunk)
            else:
                err_buf.extend(chunk)
            combined += len(chunk)
            if combined > output_limit:
                killed_reason = "output_overflow"
                _kill_process_group(proc)
                open_fds.clear()
                break
        if killed_reason:
            break
        if proc.poll() is not None and not open_fds:
            break

    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        _kill_process_group(proc)
        proc.wait(timeout=5)

    # Bounded drain after termination; overflow stays a failure.
    remain = max(0, output_limit + 1 - combined)
    if proc.stdout is not None:
        drained = _bounded_drain(stdout_fd, remain)
        out_buf.extend(drained)
        combined += len(drained)
        remain = max(0, output_limit + 1 - combined)
    if proc.stderr is not None:
        drained = _bounded_drain(stderr_fd, remain)
        err_buf.extend(drained)
        combined += len(drained)
    if combined > output_limit and killed_reason is None:
        killed_reason = "output_overflow"

    max_tmp = max(max_tmp, _tmp_used_bytes("/tmp"))
    elapsed = time.monotonic() - started
    rc = proc.returncode if proc.returncode is not None else 1
    if killed_reason:
        rc = 1
    return SuiteRunResult(
        name=name,
        returncode=rc,
        elapsed_sec=elapsed,
        combined_output_bytes=combined,
        max_tmp_bytes=max_tmp,
        tmp_sample_interval_sec=sample_interval,
        killed_reason=killed_reason,
        stdout=bytes(out_buf).decode("utf-8", errors="replace"),
        stderr=bytes(err_buf).decode("utf-8", errors="replace"),
    )

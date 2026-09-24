"""Live suite deadline/output/tmp sampling with process-group reaping."""

from __future__ import annotations

import fcntl
import os
import select
import signal
import stat as stat_mod
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import List

from constants import (  # pylint: disable=E0401  # fixture path-injection import; module resolved via sys.path
    SUITE_OUTPUT_LIMIT_BYTES,
    SUITE_WALL_DEADLINE_SEC,
    TMP_SAMPLE_INTERVAL_SEC,
)


@dataclass
class SuiteRunResult:  # pylint: disable=R0902  # attributes mirror suite run result fields
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
    """Allocated bytes under path: sum(st_blocks * 512), each inode once."""
    total = 0
    seen: set[tuple[int, int]] = set()
    root = Path(path)
    if not root.exists():
        return 0
    for dirpath, _dirnames, filenames in os.walk(root, followlinks=False):
        for name in filenames:
            p = Path(dirpath) / name
            try:
                st = os.lstat(p)
            except OSError:
                continue
            if not stat_mod.S_ISREG(st.st_mode):
                continue
            key = (st.st_dev, st.st_ino)
            if key in seen:
                continue
            seen.add(key)
            total += st.st_blocks * 512
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
    """Drain at most limit_remaining bytes after kill."""
    if limit_remaining <= 0:
        return b""
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


def _take_into_cap(
    buf: bytearray,
    chunk: bytes,
    *,
    buffered: int,
    output_limit: int,
) -> tuple[int, bool]:
    """Append at most enough to reach the cap. Returns (new_buffered, overflow)."""
    room = output_limit - buffered
    if room <= 0:
        return buffered, True
    if len(chunk) <= room:
        buf.extend(chunk)
        return buffered + len(chunk), False
    buf.extend(chunk[:room])
    return output_limit, True


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
    buffered = 0
    overflow = False
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
            target = out_buf if fd == stdout_fd else err_buf
            buffered, saw_overflow = _take_into_cap(
                target, chunk, buffered=buffered, output_limit=output_limit
            )
            if saw_overflow:
                overflow = True
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

    # Bounded drain: retain at most the cap; one extra readable byte marks overflow.
    for fd, target in ((stdout_fd, out_buf), (stderr_fd, err_buf)):
        room = output_limit - buffered
        if room > 0:
            drained = _bounded_drain(fd, room)
            if drained:
                target.extend(drained)
                buffered += len(drained)
        if buffered >= output_limit and not overflow:
            extra = _bounded_drain(fd, 1)
            if extra:
                overflow = True
                if killed_reason is None:
                    killed_reason = "output_overflow"

    if overflow and killed_reason is None:
        killed_reason = "output_overflow"

    # Buffers never exceed the cap; overflow reports cap+1 as observed-at-least.
    assert len(out_buf) + len(err_buf) <= output_limit
    combined_report = output_limit + 1 if overflow else buffered

    max_tmp = max(max_tmp, _tmp_used_bytes("/tmp"))
    elapsed = time.monotonic() - started
    rc = proc.returncode if proc.returncode is not None else 1
    if killed_reason:
        rc = 1
    return SuiteRunResult(
        name=name,
        returncode=rc,
        elapsed_sec=elapsed,
        combined_output_bytes=combined_report,
        max_tmp_bytes=max_tmp,
        tmp_sample_interval_sec=sample_interval,
        killed_reason=killed_reason,
        stdout=bytes(out_buf).decode("utf-8", errors="replace"),
        stderr=bytes(err_buf).decode("utf-8", errors="replace"),
    )

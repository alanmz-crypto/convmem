"""Live suite deadline/output/tmp sampling enforcement."""

from __future__ import annotations

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


def run_suite_with_limits(
    name: str,
    argv: List[str],
    *,
    deadline_sec: float = SUITE_WALL_DEADLINE_SEC,
    output_limit: int = SUITE_OUTPUT_LIMIT_BYTES,
    sample_interval: float = TMP_SAMPLE_INTERVAL_SEC,
) -> SuiteRunResult:
    """Enforce deadline and output cap while the suite runs; reap on violation."""
    started = time.monotonic()
    proc = subprocess.Popen(
        argv,
        cwd="/src",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        close_fds=True,
    )
    assert proc.stdout is not None and proc.stderr is not None
    out_chunks: list[str] = []
    err_chunks: list[str] = []
    combined = 0
    max_tmp = 0
    killed_reason = None
    next_sample = started
    stdout_fd = proc.stdout.fileno()
    stderr_fd = proc.stderr.fileno()
    open_fds = {stdout_fd, stderr_fd}

    while open_fds or proc.poll() is None:
        now = time.monotonic()
        if now - started > deadline_sec:
            killed_reason = "deadline"
            proc.send_signal(signal.SIGKILL)
            break
        if now >= next_sample:
            max_tmp = max(max_tmp, _tmp_used_bytes("/tmp"))
            next_sample = now + sample_interval
        timeout = min(0.2, max(0.0, next_sample - now))
        ready, _, _ = select.select(list(open_fds), [], [], timeout)
        for fd in ready:
            if fd == stdout_fd:
                chunk = proc.stdout.read(65536)
                if chunk:
                    out_chunks.append(chunk)
                    combined += len(chunk.encode("utf-8", errors="replace"))
                else:
                    open_fds.discard(fd)
            elif fd == stderr_fd:
                chunk = proc.stderr.read(65536)
                if chunk:
                    err_chunks.append(chunk)
                    combined += len(chunk.encode("utf-8", errors="replace"))
                else:
                    open_fds.discard(fd)
            if combined > output_limit:
                killed_reason = "output_overflow"
                proc.send_signal(signal.SIGKILL)
                open_fds.clear()
                break
        if killed_reason:
            break
        if proc.poll() is not None and not open_fds:
            break

    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait(timeout=5)
    # Final drain
    rem_out = proc.stdout.read() if proc.stdout else ""
    rem_err = proc.stderr.read() if proc.stderr else ""
    if rem_out:
        out_chunks.append(rem_out)
        combined += len(rem_out.encode("utf-8", errors="replace"))
    if rem_err:
        err_chunks.append(rem_err)
        combined += len(rem_err.encode("utf-8", errors="replace"))
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
        stdout="".join(out_chunks),
        stderr="".join(err_chunks),
    )

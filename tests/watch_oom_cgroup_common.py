# pylint: disable=duplicate-code
"""Shared cgroup transient-service helpers for issue #268 D1 runners."""

from __future__ import annotations

import os
import selectors
import subprocess
import time
from pathlib import Path
from collections.abc import Callable
from typing import Any


def assert_fresh_cgroup_ready_path(ready_path: Path) -> Path:
    if ready_path.exists() or not ready_path.parent.is_dir():
        raise RuntimeError("cgroup-ready path must be fresh under an existing arm")
    temp_ready = ready_path.with_name(ready_path.name + ".tmp")
    if temp_ready.exists():
        raise RuntimeError("temporary cgroup-ready path already exists")
    return temp_ready


def systemd_run_memory_properties(*, expected_bytes: int, timeout: float) -> list[str]:
    return [
        "--property=MemoryAccounting=yes",
        f"--property=MemoryMax={expected_bytes}",
        "--property=MemorySwapMax=0",
        "--property=OOMPolicy=continue",
        f"--property=RuntimeMaxSec={int(timeout + 30)}s",
    ]


def register_popen_streams(
    selector: selectors.DefaultSelector, proc: subprocess.Popen[bytes]
) -> dict[Any, bytearray]:
    assert proc.stdout is not None and proc.stderr is not None
    selector.register(proc.stdout, selectors.EVENT_READ)
    selector.register(proc.stderr, selectors.EVENT_READ)
    return {proc.stdout: bytearray(), proc.stderr: bytearray()}


def drain_popen_streams(
    selector: selectors.DefaultSelector,
    output: dict[Any, bytearray],
    *,
    poll_timeout: float = 0.02,
) -> None:
    for key, _ in selector.select(timeout=poll_timeout):
        chunk = os.read(key.fd, 65536)
        if chunk:
            output[key.fileobj].extend(chunk)
        else:
            selector.unregister(key.fileobj)


def handle_popen_timeout(*, unit: str, proc: subprocess.Popen[Any], own_unit_action) -> None:
    if not own_unit_action("stop", unit):
        own_unit_action("kill", unit)
    proc.terminate()


def stop_unit_and_kill_proc(*, unit: str, proc: subprocess.Popen[Any], own_unit_action) -> None:
    if proc.poll() is None:
        if not own_unit_action("stop", unit):
            own_unit_action("kill", unit)
        try:
            proc.kill()
        except ProcessLookupError:
            pass
        proc.wait(timeout=5)


def drain_popen_until_exit_or_timeout(
    selector: selectors.DefaultSelector,
    proc: subprocess.Popen[Any],
    output: dict[Any, bytearray],
    deadline: float,
    *,
    unit: str,
    own_unit_action,
    between_polls: Callable[[], None] | None = None,
) -> bool:
    timed_out = False
    while selector.get_map() or proc.poll() is None:
        if time.monotonic() >= deadline:
            timed_out = True
            handle_popen_timeout(unit=unit, proc=proc, own_unit_action=own_unit_action)
            break
        if between_polls is not None:
            between_polls()
        drain_popen_streams(selector, output)
        if proc.poll() is not None and not selector.get_map():
            break
    return timed_out


def run_popen_supervised_drain(
    selector: selectors.DefaultSelector,
    proc: subprocess.Popen[Any],
    output: dict[Any, bytearray],
    deadline: float,
    *,
    unit: str,
    own_unit_action,
    between_polls: Callable[[], None] | None = None,
) -> bool:
    timed_out = drain_popen_until_exit_or_timeout(
        selector,
        proc,
        output,
        deadline,
        unit=unit,
        own_unit_action=own_unit_action,
        between_polls=between_polls,
    )
    wait_popen_after_loop(timed_out=timed_out, proc=proc, deadline=deadline)
    return timed_out


def wait_popen_after_loop(
    *,
    timed_out: bool,
    proc: subprocess.Popen[Any],
    deadline: float,
) -> None:
    if timed_out:
        proc.wait(timeout=5)
    else:
        proc.wait(timeout=max(1, deadline - time.monotonic()))

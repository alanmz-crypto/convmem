# pylint: disable=too-many-nested-blocks
"""Fail-closed transient user-service boundary for the gated §9.7a worker."""

from __future__ import annotations

import json
import os
import selectors
import subprocess
import sys
import time
import uuid
from pathlib import Path
from typing import Callable

CGROUP_ROOT = Path("/sys/fs/cgroup")
MEMORY_LIMIT_BYTES = 2 * 1024**3
PROBE_OOM_LIMIT_BYTES = 64 * 1024**2
TELEMETRY_MARKER = "CONVMEM_CGROUP_EXIT_TELEMETRY:"
DENIED_PATH_MARKER = "cgroup-probe-denied-path-marker"
NETWORK_DENIED_MARKER = "cgroup-probe-network-denied-marker"


def _limit_value(path: Path) -> int | None:
    value = path.read_text(encoding="ascii").strip()
    return None if value == "max" else int(value)


def _effective_limit(group: Path, root: Path, name: str) -> int | None:
    values: list[int] = []
    current = group
    while True:
        candidate = current / name
        if candidate.is_file():
            value = _limit_value(candidate)
            if value is not None:
                values.append(value)
        if current == root:
            break
        current = current.parent
    return min(values) if values else None


def _assert_limits(group: Path, *, expected_bytes: int, root: Path) -> dict:
    root = root.resolve(strict=True)
    group = group.resolve(strict=True)
    if not group.is_relative_to(root) or group == root:
        raise RuntimeError("worker is not in a private cgroup-v2 child")
    direct_memory = _limit_value(group / "memory.max")
    direct_swap = _limit_value(group / "memory.swap.max")
    effective_memory = _effective_limit(group, root, "memory.max")
    effective_swap = _effective_limit(group, root, "memory.swap.max")
    if (direct_memory, direct_swap, effective_memory, effective_swap) != (
        expected_bytes,
        0,
        expected_bytes,
        0,
    ):
        raise RuntimeError(
            "cgroup memory/swap bound differs from the reviewed cap: "
            f"direct=({direct_memory}, {direct_swap}) "
            f"effective=({effective_memory}, {effective_swap})"
        )
    return {
        "cgroup_path": str(group),
        "memory_max_bytes": effective_memory,
        "memory_swap_max_bytes": effective_swap,
    }


def worker_limit_claim(
    expected_bytes: int,
    *,
    proc_cgroup: Path = Path("/proc/self/cgroup"),
    root: Path = CGROUP_ROOT,
) -> dict:
    """Verify the worker's own effective limit, not launcher arguments."""
    entries = proc_cgroup.read_text(encoding="ascii").splitlines()
    unified = [line[3:] for line in entries if line.startswith("0::/")]
    if len(unified) != 1 or any(part == ".." for part in Path(unified[0]).parts):
        raise RuntimeError("worker has no unambiguous cgroup-v2 membership")
    group = root / unified[0].lstrip("/")
    return _assert_limits(group, expected_bytes=expected_bytes, root=root)


def wait_for_parent_ready(path: Path, *, timeout: float = 50) -> None:
    """Keep the worker idle until the parent has opened its telemetry files."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if path.is_file():
            if path.read_text(encoding="ascii") != "ready\n":
                raise RuntimeError("invalid cgroup-ready signal")
            return
        time.sleep(0.02)
    raise TimeoutError("parent did not verify cgroup telemetry before worker start")


def _unit_property(unit: str, name: str) -> str:
    result = subprocess.run(
        ["systemctl", "--user", "show", unit, "-p", name, "--value"],
        check=False,
        capture_output=True,
        text=True,
        timeout=3,
    )
    return result.stdout.strip() if result.returncode == 0 else ""


def _own_unit_action(action: str, unit: str) -> bool:
    if not unit.startswith("convmem-oom-measure-") or not unit.endswith(".service"):
        raise ValueError("refusing action on a non-measurement unit")
    try:
        result = subprocess.run(
            ["systemctl", "--user", action, unit],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=5,
        )
    except (OSError, subprocess.SubprocessError):
        return False
    return result.returncode == 0


class _Sampler:
    def __init__(self, group: Path):
        self._files = {}
        try:
            for name in ("memory.peak", "memory.events"):
                self._files[name] = (group / name).open("r", encoding="ascii")
        except OSError:
            self.close()
            raise
        self.samples = 0
        self.peak_bytes = 0
        self.events: dict[str, int] = {}

    def sample(self) -> None:
        try:
            for handle in self._files.values():
                handle.seek(0)
            peak = int(self._files["memory.peak"].read().strip())
            events = {
                key: int(value)
                for key, value in (
                    line.split() for line in self._files["memory.events"].read().splitlines()
                )
            }
        except (OSError, ValueError):
            return
        self.samples += 1
        self.peak_bytes = max(self.peak_bytes, peak)
        for key, value in events.items():
            self.events[key] = max(self.events.get(key, 0), value)

    def close(self) -> None:
        for handle in self._files.values():
            handle.close()


def _parse_exit_telemetry(stderr: str, limit_claim: dict | None) -> dict | None:
    lines = [
        line.removeprefix(TELEMETRY_MARKER)
        for line in stderr.splitlines()
        if line.startswith(TELEMETRY_MARKER)
    ]
    if len(lines) != 1:
        return None
    try:
        telemetry = json.loads(lines[0])
    except json.JSONDecodeError:
        return None
    if not isinstance(telemetry, dict) or telemetry.get("claim") != limit_claim:
        return None
    if not isinstance(telemetry.get("peak_bytes"), int) or telemetry["peak_bytes"] <= 0:
        return None
    events = telemetry.get("events")
    if not isinstance(events, dict) or not all(
        isinstance(events.get(key), int) and events[key] >= 0
        for key in ("max", "oom", "oom_kill")
    ):
        return None
    if not isinstance(telemetry.get("worker_returncode"), int):
        return None
    return telemetry


def run_capped_worker(
    worker_argv: list[str],
    *,
    ready_path: Path,
    cwd: Path,
    expected_bytes: int = MEMORY_LIMIT_BYTES,
    timeout: float = 90,
    cgroup_root: Path = CGROUP_ROOT,
    while_active: Callable[[], dict] | None = None,
) -> dict:
    """Run one worker under a checked cap; return evidence, never fall back."""
    if ready_path.exists() or not ready_path.parent.is_dir():
        raise RuntimeError("cgroup-ready path must be fresh under an existing arm")
    temp_ready = ready_path.with_name(ready_path.name + ".tmp")
    if temp_ready.exists():
        raise RuntimeError("temporary cgroup-ready path already exists")
    unit = f"convmem-oom-measure-{uuid.uuid4().hex}.service"
    supervisor = Path(__file__).with_name("watch_oom_cgroup_supervisor.py")
    command = [
        "systemd-run", "--user", "--service-type=exec", "--pipe", "--wait",
        "--quiet", "--same-dir", f"--unit={unit}",
        "--property=MemoryAccounting=yes",
        f"--property=MemoryMax={expected_bytes}",
        "--property=MemorySwapMax=0",
        "--property=OOMPolicy=continue",
        f"--property=RuntimeMaxSec={int(timeout + 30)}s",
        sys.executable, str(supervisor), str(expected_bytes), *worker_argv,
    ]
    proc = subprocess.Popen(  # pylint: disable=consider-using-with
        command,
        cwd=cwd,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    selector = selectors.DefaultSelector()
    assert proc.stdout is not None and proc.stderr is not None
    selector.register(proc.stdout, selectors.EVENT_READ)
    selector.register(proc.stderr, selectors.EVENT_READ)
    output = {proc.stdout: bytearray(), proc.stderr: bytearray()}
    deadline = time.monotonic() + timeout
    sampler: _Sampler | None = None
    group_path = ""
    limit_claim: dict | None = None
    oom_policy_verified = False
    active_host: dict | None = None
    timed_out = False
    try:
        while selector.get_map() or proc.poll() is None:
            if time.monotonic() >= deadline:
                timed_out = True
                if not _own_unit_action("stop", unit):
                    _own_unit_action("kill", unit)
                proc.terminate()
                break
            if sampler is None and proc.poll() is None:
                try:
                    group_path = _unit_property(unit, "ControlGroup")
                    if group_path:
                        if _unit_property(unit, "OOMPolicy") != "continue":
                            raise RuntimeError("transient service did not retain OOMPolicy=continue")
                        oom_policy_verified = True
                        group = cgroup_root / group_path.lstrip("/")
                        limit_claim = _assert_limits(
                            group, expected_bytes=expected_bytes, root=cgroup_root
                        )
                        sampler = _Sampler(group)
                        sampler.sample()
                        if sampler.samples == 0:
                            raise RuntimeError("cgroup telemetry unreadable before worker start")
                        if while_active is not None:
                            active_host = while_active()
                        temp_ready.write_text("ready\n", encoding="ascii")
                        temp_ready.replace(ready_path)
                except (OSError, subprocess.SubprocessError):
                    pass
            if sampler is not None:
                sampler.sample()
            for key, _ in selector.select(timeout=0.02):
                chunk = os.read(key.fd, 65536)
                if chunk:
                    output[key.fileobj].extend(chunk)
                else:
                    selector.unregister(key.fileobj)
            if proc.poll() is not None and not selector.get_map():
                break
        if timed_out:
            proc.wait(timeout=5)
        else:
            proc.wait(timeout=max(1, deadline - time.monotonic()))
        if sampler is not None:
            sampler.sample()
        stderr = bytes(output[proc.stderr]).decode("utf-8", errors="replace")
        exit_telemetry = _parse_exit_telemetry(stderr, limit_claim)
        return {
            "unit": unit,
            "control_group": group_path,
            "limit_claim": limit_claim,
            "oom_policy_verified": oom_policy_verified,
            "active_host": active_host,
            "returncode": proc.returncode,
            "stdout": bytes(output[proc.stdout]).decode("utf-8", errors="replace"),
            "stderr": stderr,
            "timed_out": timed_out,
            "cgroup_samples": sampler.samples if sampler else 0,
            "cgroup_peak_bytes": exit_telemetry["peak_bytes"] if exit_telemetry else None,
            "cgroup_events": exit_telemetry["events"] if exit_telemetry else None,
            "exit_telemetry": exit_telemetry,
            "sampled_peak_bytes": sampler.peak_bytes if sampler else None,
            "sampled_events": sampler.events if sampler else None,
        }
    finally:
        selector.close()
        temp_ready.unlink(missing_ok=True)
        if sampler is not None:
            sampler.close()
        try:
            if proc.poll() is None:
                if not _own_unit_action("stop", unit):
                    _own_unit_action("kill", unit)
                try:
                    proc.kill()
                except ProcessLookupError:
                    pass
                proc.wait(timeout=5)
        finally:
            _own_unit_action("reset-failed", unit)


def run_capability_probes(
    arm: Path, *, cwd: Path, while_active: Callable[[], dict]
) -> dict:
    """Prove stdout/exit, hard cap and telemetry before any index fixture."""
    probe = Path(__file__).with_name("watch_oom_cgroup_probe.py")
    observations = {}
    for mode, cap in (
        ("success", MEMORY_LIMIT_BYTES),
        ("exit", MEMORY_LIMIT_BYTES),
        ("oom", PROBE_OOM_LIMIT_BYTES),
    ):
        ready = arm / f"cgroup-{mode}-{uuid.uuid4().hex}.ready"
        try:
            result = run_capped_worker(
                [sys.executable, str(probe), "--mode", mode, "--ready", str(ready),
                 "--expected-bytes", str(cap)],
                ready_path=ready,
                cwd=cwd,
                expected_bytes=cap,
                timeout=60,
                while_active=while_active,
            )
        finally:
            ready.unlink(missing_ok=True)
        if any((
            result["timed_out"],
            not result["limit_claim"],
            not result["oom_policy_verified"],
            not result["active_host"],
            not result["cgroup_samples"],
            not result["cgroup_peak_bytes"],
            not result["cgroup_events"],
            not result["exit_telemetry"],
        )):
            raise RuntimeError(f"cgroup {mode} capability probe could not verify cap/telemetry")
        if mode == "success":
            payload = json.loads(result["stdout"])
            if (
                result["returncode"] != 0
                or payload.get("status") != "succeeded"
                or "cgroup probe stderr captured" not in result["stderr"]
                or result["exit_telemetry"]["worker_returncode"] != 0
            ):
                raise RuntimeError("cgroup service did not preserve success JSON and exit")
            if payload.get("claim", {}).get("memory_max_bytes") != cap:
                raise RuntimeError("worker did not attest its own cgroup cap")
            if payload.get("denied_paths") != [DENIED_PATH_MARKER] or payload.get(
                "network_denied"
            ) != [NETWORK_DENIED_MARKER]:
                raise RuntimeError("worker denial fields were lost in service stdout")
        elif mode == "exit":
            payload = json.loads(result["stdout"])
            if (
                result["returncode"] != 17
                or payload.get("status") != "exited"
                or result["exit_telemetry"]["worker_returncode"] != 17
            ):
                raise RuntimeError("cgroup service did not propagate nonzero worker exit")
            if payload.get("claim", {}).get("memory_max_bytes") != cap:
                raise RuntimeError("nonzero worker did not attest its cgroup cap")
            if payload.get("denied_paths") != [DENIED_PATH_MARKER] or payload.get(
                "network_denied"
            ) != [NETWORK_DENIED_MARKER]:
                raise RuntimeError("nonzero worker denial fields were lost")
        elif (
            result["returncode"] == 0
            or result["exit_telemetry"]["worker_returncode"] >= 0
            or result["cgroup_events"].get("oom_kill", 0) < 1
        ):
            raise RuntimeError("small-cap OOM was not captured and classified as blocked")
        observations[mode] = result
    return observations

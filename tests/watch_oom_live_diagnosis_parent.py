# pylint: disable=protected-access,too-many-locals,too-many-branches,too-many-statements
"""Parent-side cgroup/process sampler for issue #268 D1 (outside worker cgroup)."""

from __future__ import annotations

import json
import os
import selectors
import subprocess
import sys
import time
import uuid
from pathlib import Path
from typing import Any, Callable

from tests.watch_oom_cgroup_runner import (
    CGROUP_ROOT,
    _assert_limits,
    _own_unit_action,
    _parse_exit_telemetry,
    _unit_property,
)
from tests.watch_oom_live_diagnosis_dual_boundary import (
    INNER_SCOPE_UNVERIFIED,
    read_index_pid,
    read_inner_scope_unit,
    verify_inner_scope_unit,
    pid_in_cgroup,
    inner_scope_cgroup,
)
from tests.watch_oom_live_diagnosis_support import (
    SAMPLE_INTERVAL_SECONDS,
    bounded_telemetry_append,
)

D2_KERNEL_ISOLATION_BLOCKER = (
    "D2 requires cgroup v2 IPAddressDeny=any on the measurement unit; "
    "hermetic proof needs systemd user manager + CONVMEM_D1_CGROUP=1."
)


def _read_int(path: Path) -> int | None:
    try:
        return int(path.read_text(encoding="ascii").strip())
    except (OSError, ValueError):
        return None


def _read_events(path: Path) -> dict[str, int]:
    try:
        return {
            key: int(value)
            for key, value in (
                line.split() for line in path.read_text(encoding="ascii").splitlines()
            )
        }
    except (OSError, ValueError):
        return {}


def _cgroup_pids(group: Path) -> list[int]:
    procs = group / "cgroup.procs"
    if not procs.is_file():
        return []
    try:
        return [int(p) for p in procs.read_text(encoding="ascii").split() if p.strip()]
    except (OSError, ValueError):
        return []


def worker_rss_bytes(pid: int) -> int | None:
    status = Path(f"/proc/{pid}/status")
    if not status.is_file():
        return None
    try:
        text = status.read_text(encoding="utf-8")
    except OSError:
        return None
    for line in text.splitlines():
        if line.startswith("VmRSS:"):
            return int(line.split()[1]) * 1024
    return None


def _pick_worker_pid(group: Path, pid_hint: Path | None) -> int | None:
    if pid_hint and pid_hint.is_file():
        try:
            return int(pid_hint.read_text(encoding="ascii").strip())
        except (OSError, ValueError):
            pass
    pids = _cgroup_pids(group)
    if not pids:
        return None
    scored: list[tuple[int, int]] = []
    for pid in pids:
        rss = worker_rss_bytes(pid)
        scored.append((rss or 0, pid))
    scored.sort(reverse=True)
    return scored[0][1]


class PhaseTailWatcher:
    """Detect new phase markers written by the worker (parent reads scratch file)."""

    def __init__(self, phase_path: Path):
        self._path = phase_path
        self._offset = 0

    def poll_new_phases(self) -> list[str]:
        if not self._path.is_file():
            return []
        try:
            data = self._path.read_bytes()
        except OSError:
            return []
        chunk = data[self._offset :]
        self._offset = len(data)
        phases: list[str] = []
        for line in chunk.decode("utf-8", errors="replace").splitlines():
            if not line.strip():
                continue
            try:
                phases.append(json.loads(line)["phase"])
            except (json.JSONDecodeError, KeyError, TypeError):
                continue
        return phases


class LiveDiagnosisParentSampler:
    """Sample cgroup memory.current/peak/events and worker RSS at <=250 ms."""

    def __init__(
        self,
        group: Path,
        *,
        telemetry_path: Path,
        worker_pid: int | None = None,
        boundary: str = "outer",
    ):
        self._group = group
        self._telemetry_path = telemetry_path
        self._worker_pid = worker_pid
        self._boundary = boundary
        self._last_sample = 0.0
        self.samples = 0
        self.last_row: dict[str, Any] | None = None
        self.peak_current = 0
        self.peak_rss = 0

    def sample(self, *, reason: str = "interval", force: bool = False) -> None:
        now = time.monotonic()
        if not force and self.samples and now - self._last_sample < SAMPLE_INTERVAL_SECONDS:
            return
        self._last_sample = now
        current = _read_int(self._group / "memory.current")
        peak = _read_int(self._group / "memory.peak")
        events = _read_events(self._group / "memory.events")
        rss = worker_rss_bytes(self._worker_pid) if self._worker_pid else None
        if current is not None:
            self.peak_current = max(self.peak_current, current)
        if rss is not None:
            self.peak_rss = max(self.peak_rss, rss)
        row = {
            "ts": time.time(),
            "reason": reason,
            "boundary": self._boundary,
            "memory_current": current,
            "memory_peak": peak,
            "memory_events": events,
            "worker_rss_bytes": rss,
            "worker_pid": self._worker_pid,
        }
        if current is None and peak is None:
            return
        bounded_telemetry_append(self._telemetry_path, row)
        self.samples += 1
        self.last_row = row

    def set_worker_pid(self, pid: int | None) -> None:
        self._worker_pid = pid

    def final_pre_teardown(self) -> dict[str, Any]:
        """Persist cgroup counters before the transient unit is torn down."""
        self.sample(reason="final_pre_teardown", force=True)
        row = {
            "ts": time.time(),
            "reason": "cgroup_final_counters",
            "boundary": self._boundary,
            "memory_current": _read_int(self._group / "memory.current"),
            "memory_peak": _read_int(self._group / "memory.peak"),
            "memory_events": _read_events(self._group / "memory.events"),
            "worker_rss_bytes": worker_rss_bytes(self._worker_pid) if self._worker_pid else None,
            "samples_total": self.samples,
            "peak_current_observed": self.peak_current,
            "peak_rss_observed": self.peak_rss,
        }
        bounded_telemetry_append(self._telemetry_path, row)
        return row


def require_telemetry_after_kill(telemetry_path: Path, *, min_samples: int = 1) -> dict[str, Any]:
    if not telemetry_path.is_file():
        raise RuntimeError("telemetry_missing_after_kill")
    lines = [line for line in telemetry_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if len(lines) < min_samples:
        raise RuntimeError("telemetry_too_sparse")
    final_rows = [json.loads(line) for line in lines if "memory_peak" in line or "memory_current" in line]
    if not final_rows:
        raise RuntimeError("telemetry_missing_memory_peak")
    has_final = any(r.get("reason") == "cgroup_final_counters" for r in final_rows)
    if not has_final:
        raise RuntimeError("telemetry_missing_final_counters")
    return {"samples": len(lines), "last": final_rows[-1]}


class DualBoundaryController:
    """Track outer service cgroup + inner index scope with fail-closed verification."""

    def __init__(
        self,
        *,
        telemetry_path: Path,
        outer_group: Path,
        worker_pid_path: Path | None,
        inner_marker_path: Path,
        index_pid_path: Path,
        expected_inner_bytes: int,
        cgroup_root: Path,
    ):
        self._inner_marker_path = inner_marker_path
        self._index_pid_path = index_pid_path
        self._expected_inner_bytes = expected_inner_bytes
        self._cgroup_root = cgroup_root
        self._outer_group = outer_group
        self.outer = LiveDiagnosisParentSampler(
            outer_group,
            telemetry_path=telemetry_path,
            worker_pid=_pick_worker_pid(outer_group, worker_pid_path),
            boundary="outer",
        )
        self.inner: LiveDiagnosisParentSampler | None = None
        self.inner_verified = False
        self.inner_meta: dict | None = None
        self._worker_pid_path = worker_pid_path
        self._index_pid: int | None = None

    def _refresh_outer_pid(self) -> None:
        self.outer.set_worker_pid(_pick_worker_pid(self._outer_group, self._worker_pid_path))

    def try_verify_inner(self) -> bool:
        if self.inner_verified:
            return True
        unit = read_inner_scope_unit(self._inner_marker_path)
        if not unit:
            return False
        meta = verify_inner_scope_unit(
            unit,
            expected_memory_bytes=self._expected_inner_bytes,
            outer_group=self._outer_group.resolve(),
            cgroup_root=self._cgroup_root,
        )
        group = inner_scope_cgroup(unit, cgroup_root=self._cgroup_root)
        if group is None:
            raise RuntimeError(f"{INNER_SCOPE_UNVERIFIED}:inner_cgroup_missing")
        pid = read_index_pid(self._index_pid_path)
        if pid is None:
            return False
        if not pid_in_cgroup(pid, group):
            raise RuntimeError(f"{INNER_SCOPE_UNVERIFIED}:index_pid_not_in_inner")
        self._index_pid = pid
        self.inner = LiveDiagnosisParentSampler(
            group,
            telemetry_path=self.outer._telemetry_path,
            worker_pid=pid,
            boundary="inner",
        )
        self.inner_verified = True
        self.inner_meta = meta
        self.inner.sample(force=True, reason="inner_scope_verified")
        return True

    def sample(self, *, reason: str = "interval", force: bool = False) -> None:
        self._refresh_outer_pid()
        self.outer.sample(reason=reason, force=force)
        index_pid = read_index_pid(self._index_pid_path)
        if index_pid is not None:
            rss = worker_rss_bytes(index_pid)
            if rss is not None:
                bounded_telemetry_append(
                    self.outer._telemetry_path,
                    {
                        "ts": time.time(),
                        "reason": reason,
                        "boundary": "index_child_rss",
                        "index_pid": index_pid,
                        "index_rss_bytes": rss,
                    },
                )
        if self.inner_verified and self.inner is not None:
            self.inner.set_worker_pid(read_index_pid(self._index_pid_path))
            self.inner.sample(reason=reason, force=force)

    def final_pre_teardown(self) -> dict[str, Any]:
        self.sample(reason="final_pre_teardown", force=True)
        outer_final = self.outer.final_pre_teardown()
        inner_final = None
        if self.inner is not None:
            inner_final = self.inner.final_pre_teardown()
        return {"outer": outer_final, "inner": inner_final}


def _systemd_forward_env(env: dict[str, str] | None) -> list[str]:
    if not env:
        return []
    fragments: list[str] = []
    for key in sorted(env):
        if key == "CONVMEM_CONFIG" or key.startswith("CONVMEM_LIVE_DIAG_"):
            fragments.extend(["--setenv", f"{key}={env[key]}"])
    return fragments


def run_d1_capped_worker(
    worker_argv: list[str],
    *,
    ready_path: Path,
    cwd: Path,
    telemetry_path: Path,
    phase_path: Path,
    worker_pid_path: Path | None,
    expected_bytes: int,
    worker_env: dict[str, str] | None = None,
    inner_scope_marker_path: Path | None = None,
    index_pid_path: Path | None = None,
    expected_inner_bytes: int | None = None,
    require_dual_boundary: bool = True,
    timeout: float = 120,
    cgroup_root: Path = CGROUP_ROOT,
    kernel_network_deny: bool = True,
) -> dict:
    """Run worker under cap with parent sampler + phase-triggered samples (D1)."""
    if ready_path.exists() or not ready_path.parent.is_dir():
        raise RuntimeError("cgroup-ready path must be fresh under an existing arm")
    temp_ready = ready_path.with_name(ready_path.name + ".tmp")
    if temp_ready.exists():
        raise RuntimeError("temporary cgroup-ready path already exists")
    unit = f"convmem-oom-measure-{uuid.uuid4().hex}.service"
    supervisor = Path(__file__).resolve().parent / "watch_oom_cgroup_supervisor.py"
    command = [
        "systemd-run",
        "--user",
        "--service-type=exec",
        "--pipe",
        "--wait",
        "--quiet",
        "--same-dir",
        f"--unit={unit}",
        "--property=MemoryAccounting=yes",
        f"--property=MemoryMax={expected_bytes}",
        "--property=MemorySwapMax=0",
        "--property=OOMPolicy=continue",
        f"--property=RuntimeMaxSec={int(timeout + 30)}s",
    ]
    if kernel_network_deny:
        command.extend(
            [
                "--property=IPAddressDeny=any",
                "--property=RestrictAddressFamilies=AF_UNIX",
            ]
        )
    command.extend(_systemd_forward_env(worker_env))
    command.extend([sys.executable, str(supervisor), str(expected_bytes), *worker_argv])
    popen_env = None
    if worker_env is not None:
        popen_env = os.environ.copy()
        popen_env.update(worker_env)
    proc = subprocess.Popen(
        command,
        cwd=cwd,
        env=popen_env,
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
    dual: DualBoundaryController | None = None
    outer_sampler: LiveDiagnosisParentSampler | None = None
    phase_watch: PhaseTailWatcher | None = None
    group_path = ""
    group: Path | None = None
    limit_claim: dict | None = None
    oom_policy_verified = False
    kernel_isolation_requested = kernel_network_deny
    timed_out = False
    final_counters: dict[str, Any] | None = None
    dual_boundary_verified = False
    try:
        while selector.get_map() or proc.poll() is None:
            if time.monotonic() >= deadline:
                timed_out = True
                if not _own_unit_action("stop", unit):
                    _own_unit_action("kill", unit)
                proc.terminate()
                break
            if dual is None and proc.poll() is None:
                try:
                    group_path = _unit_property(unit, "ControlGroup")
                    if group_path:
                        oom_policy = _unit_property(unit, "OOMPolicy")
                        if oom_policy != "continue":
                            continue
                        oom_policy_verified = True
                        group = cgroup_root / group_path.lstrip("/")
                        limit_claim = _assert_limits(
                            group, expected_bytes=expected_bytes, root=cgroup_root
                        )
                        phase_watch = PhaseTailWatcher(phase_path)
                        if (
                            require_dual_boundary
                            and inner_scope_marker_path is not None
                            and index_pid_path is not None
                            and expected_inner_bytes is not None
                        ):
                            dual = DualBoundaryController(
                                telemetry_path=telemetry_path,
                                outer_group=group,
                                worker_pid_path=worker_pid_path,
                                inner_marker_path=inner_scope_marker_path,
                                index_pid_path=index_pid_path,
                                expected_inner_bytes=expected_inner_bytes,
                                cgroup_root=cgroup_root,
                            )
                            dual.sample(force=True, reason="cgroup_attached")
                        else:
                            outer_sampler = LiveDiagnosisParentSampler(
                                group,
                                telemetry_path=telemetry_path,
                                worker_pid=_pick_worker_pid(group, worker_pid_path),
                                boundary="outer",
                            )
                            outer_sampler.sample(force=True, reason="cgroup_attached")
                            if outer_sampler.samples == 0:
                                raise RuntimeError("parent telemetry unreadable before worker start")
                        if dual is not None:
                            if dual.outer.samples == 0:
                                raise RuntimeError("parent telemetry unreadable before worker start")
                        temp_ready.write_text("ready\n", encoding="ascii")
                        temp_ready.replace(ready_path)
                except (OSError, subprocess.SubprocessError):
                    pass
            if group is not None:
                if dual is not None:
                    dual.try_verify_inner()
                    dual_boundary_verified = dual.inner_verified
                    dual.sample()
                    if phase_watch is not None:
                        for phase in phase_watch.poll_new_phases():
                            dual.try_verify_inner()
                            dual_boundary_verified = dual.inner_verified
                            dual.sample(reason=f"phase:{phase}", force=True)
                elif outer_sampler is not None:
                    outer_sampler.set_worker_pid(_pick_worker_pid(group, worker_pid_path))
                    outer_sampler.sample()
                    if phase_watch is not None:
                        for phase in phase_watch.poll_new_phases():
                            outer_sampler.sample(reason=f"phase:{phase}", force=True)
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
        if dual is not None and group is not None:
            if phase_watch is not None:
                for phase in phase_watch.poll_new_phases():
                    dual.try_verify_inner()
                    dual_boundary_verified = dual.inner_verified
                    dual.sample(reason=f"phase:{phase}", force=True)
            final_counters = dual.final_pre_teardown()
            dual.sample(force=True, reason="post_worker_exit")
            dual_boundary_verified = dual.inner_verified
            parent_samples = dual.outer.samples + (dual.inner.samples if dual.inner else 0)
        elif outer_sampler is not None and group is not None:
            if phase_watch is not None:
                for phase in phase_watch.poll_new_phases():
                    outer_sampler.sample(reason=f"phase:{phase}", force=True)
            final_counters = outer_sampler.final_pre_teardown()
            outer_sampler.sample(force=True, reason="post_worker_exit")
            parent_samples = outer_sampler.samples
        else:
            parent_samples = 0
        stderr = bytes(output[proc.stderr]).decode("utf-8", errors="replace")
        exit_telemetry = _parse_exit_telemetry(stderr, limit_claim)
        if parent_samples == 0:
            raise RuntimeError("parent_sampler_no_samples")
        if final_counters is None:
            raise RuntimeError("parent_missing_final_counters")
        if require_dual_boundary and not dual_boundary_verified:
            raise RuntimeError(INNER_SCOPE_UNVERIFIED)
        if not oom_policy_verified:
            raise RuntimeError("transient service did not retain OOMPolicy=continue")
        return {
            "unit": unit,
            "control_group": group_path,
            "limit_claim": limit_claim,
            "inner_limit_claim": dual.inner_meta if dual else None,
            "oom_policy_verified": oom_policy_verified,
            "kernel_isolation_requested": kernel_isolation_requested,
            "dual_boundary_verified": dual_boundary_verified,
            "returncode": proc.returncode,
            "stdout": bytes(output[proc.stdout]).decode("utf-8", errors="replace"),
            "stderr": stderr,
            "timed_out": timed_out,
            "parent_telemetry_samples": parent_samples,
            "parent_final_counters": final_counters,
            "exit_telemetry": exit_telemetry,
            "cgroup_peak_bytes": exit_telemetry["peak_bytes"] if exit_telemetry else None,
            "cgroup_events": exit_telemetry["events"] if exit_telemetry else None,
        }
    finally:
        selector.close()
        temp_ready.unlink(missing_ok=True)
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


def run_d1_worker_subprocess(
    command: list[str],
    *,
    cwd: Path,
    env: dict[str, str],
    telemetry_path: Path,
    phase_path: Path,
    timeout: float = 120,
) -> dict[str, Any]:
    """Non-cgroup fallback: parent polls phase file only (no cgroup telemetry proof)."""
    phase_watch = PhaseTailWatcher(phase_path)
    proc = subprocess.Popen(
        command,
        cwd=cwd,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    deadline = time.monotonic() + timeout
    stdout = ""
    stderr = ""
    while proc.poll() is None and time.monotonic() < deadline:
        for phase in phase_watch.poll_new_phases():
            bounded_telemetry_append(
                telemetry_path,
                {"ts": time.time(), "reason": f"phase:{phase}", "memory_current": None},
            )
        time.sleep(min(SAMPLE_INTERVAL_SECONDS, max(0, deadline - time.monotonic())))
    try:
        stdout, stderr = proc.communicate(timeout=max(1, deadline - time.monotonic()))
    except subprocess.TimeoutExpired:
        proc.kill()
        stdout, stderr = proc.communicate()
    return {
        "returncode": proc.returncode,
        "stdout": stdout,
        "stderr": stderr,
        "parent_telemetry_samples": 0,
        "cgroup_unavailable": True,
    }

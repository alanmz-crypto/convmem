# pylint: disable=protected-access,too-many-locals,too-many-branches,too-many-statements,too-many-lines,too-many-instance-attributes,too-many-arguments,too-many-nested-blocks
"""Parent-side cgroup/process sampler for issue #268 D1 (outside worker cgroup)."""

from __future__ import annotations

import json
import os
import re
import selectors
import signal
import subprocess
import sys
import time
import uuid
from contextlib import ExitStack
from pathlib import Path
from typing import Any

from live_diagnosis import (
    GATE_INDEX_AT_GATE,
    GATE_RUN_GRANTED,
    GATE_SCOPE_READY,
    GATE_SPAWN_GRANTED,
)

from tests.watch_oom_cgroup_common import (
    assert_fresh_cgroup_ready_path,
    register_popen_streams,
    run_popen_supervised_drain,
    stop_unit_and_kill_proc,
    systemd_run_memory_properties,
)
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
    read_supervisor_pid,
    verify_inner_scope_unit,
    pid_in_cgroup,
    inner_scope_cgroup,
)
from tests.watch_oom_live_diagnosis_bwrap import (
    D1_PARENT_NETNS_ENV,
    build_bwrap_command,
    net_namespace_id,
)
from tests.watch_oom_live_diagnosis_net_probe import (
    NET_PROBE_INNER_PATH_ENV,
    NET_PROBE_OUTER_PATH_ENV,
    NET_PROBE_PORT_ENV,
    NetProbeVerificationError,
    parent_can_connect_loopback,
    parent_loopback_listener,
    parent_net_namespace_id,
    verify_dual_net_probe_artifacts,
)
from tests.watch_oom_live_diagnosis_support import (
    D1_BWRAP_ACTIVE_ENV,
    SAMPLE_INTERVAL_SECONDS,
    assert_denial_events_empty,
    bounded_telemetry_append,
)

D2_KERNEL_ISOLATION_BLOCKER = (
    "D2 adds cgroup v2 IPAddressDeny=any on the measurement unit (supplemental; "
    "enforcement is bwrap + child AF_INET probe artifacts). "
    "Hermetic proof needs systemd user manager + CONVMEM_D1_CGROUP=1."
)


def assert_inject_kill_index_at_gate_allowed(
    *,
    inject_kill_index_at_gate: bool,
    require_dual_boundary: bool,
    use_bwrap: bool,
    worker_env: dict[str, str] | None,
) -> None:
    """Test-only: parent SIGKILL of index child at index_at_gate (scratch hermetic only)."""
    if not inject_kill_index_at_gate:
        return
    if not require_dual_boundary or not use_bwrap:
        raise RuntimeError("inject_kill_index_at_gate_unavailable")
    if not worker_env:
        raise RuntimeError("inject_kill_index_at_gate_env_missing")
    if worker_env.get("CONVMEM_LIVE_DIAG_HERMETIC") != "1":
        raise RuntimeError("inject_kill_index_at_gate_hermetic_only")
    if not worker_env.get("CONVMEM_LIVE_DIAG_SCRATCH_ROOTS", "").strip():
        raise RuntimeError("inject_kill_index_at_gate_scratch_only")


def d1_systemd_network_properties(
    *,
    kernel_network_deny: bool,
    use_bwrap: bool,
    require_dual_boundary: bool,
) -> list[str]:
    """systemd-run network properties for D1 capped worker."""
    if not kernel_network_deny:
        return []
    # User IPAddressDeny=any is best-effort; bwrap unshare-net + scratch artifacts are enforcing.
    props = ["--property=IPAddressDeny=any"]
    # bwrap --unshare-net needs AF_NETLINK for loopback; AF_UNIX-only breaks before worker start.
    if not (use_bwrap and require_dual_boundary):
        props.append("--property=RestrictAddressFamilies=AF_UNIX")
    return props

_MAX_DIAG_STREAM_CHARS = 2048
_MAX_DIAG_LINE_CHARS = 400
_ENV_ASSIGN_RE = re.compile(
    r"(?i)(CONVMEM_[A-Z0-9_]+|DEEPSEEK_API_KEY|OPENAI_API_KEY|Authorization)=([^\s\\'\"]+)"
)
_SHA256_RE = re.compile(r"\b[a-f0-9]{64}\b", re.IGNORECASE)
_SECRET_JSON_RE = re.compile(
    r'"(api[_-]?key|token|authorization|password|secret)"\s*:\s*"[^"]*"',
    re.IGNORECASE,
)


def _scratch_roots_from_worker_env(worker_env: dict[str, str] | None) -> list[Path]:
    if not worker_env:
        return []
    raw = worker_env.get("CONVMEM_LIVE_DIAG_SCRATCH_ROOTS", "").strip()
    if not raw:
        return []
    try:
        items = json.loads(raw)
    except json.JSONDecodeError:
        return []
    if not isinstance(items, list):
        return []
    roots: list[Path] = []
    for item in items:
        if isinstance(item, str) and item.strip():
            roots.append(Path(item).expanduser())
    return roots


def _clip_path_for_diagnostic(path_text: str, *, allowed_roots: list[Path]) -> str:
    if not path_text or not allowed_roots:
        return path_text
    try:
        resolved = Path(path_text).expanduser().resolve()
    except (OSError, ValueError):
        return "<path>"
    for root in allowed_roots:
        try:
            root_res = root.expanduser().resolve()
            if resolved.is_relative_to(root_res):
                return str(resolved.relative_to(root_res))
        except (OSError, ValueError):
            continue
    return "<path-outside-scratch>"


def sanitize_d1_worker_stream(
    text: str,
    *,
    allowed_scratch_roots: list[Path] | None = None,
) -> str:
    """Bounded worker stream tail safe for logs (no secrets, no off-scratch paths)."""
    if not text:
        return ""
    roots = allowed_scratch_roots or []
    cleaned: list[str] = []
    for line in text.splitlines():
        line = _ENV_ASSIGN_RE.sub(r"\1=<redacted>", line)
        line = _SHA256_RE.sub("<sha256>", line)
        line = _SECRET_JSON_RE.sub(r'"\1": "<redacted>"', line)
        for match in re.finditer(r"(/[\w./-]+)", line):
            clipped = _clip_path_for_diagnostic(match.group(1), allowed_roots=roots)
            if clipped != match.group(1):
                line = line.replace(match.group(1), clipped, 1)
        if len(line) > _MAX_DIAG_LINE_CHARS:
            line = line[: _MAX_DIAG_LINE_CHARS - 1] + "…"
        cleaned.append(line)
    out = "\n".join(cleaned).strip()
    if len(out) > _MAX_DIAG_STREAM_CHARS:
        out = "…" + out[-_MAX_DIAG_STREAM_CHARS :]
    return out


def build_d1_worker_exit_diagnostic(
    *,
    reason: str,
    unit: str,
    returncode: int | None,
    stdout: str,
    stderr: str,
    control_group: str = "",
    oom_policy_verified: bool = False,
    allowed_scratch_roots: list[Path] | None = None,
) -> str:
    """Single-line failure summary for early worker exit (test-only diagnostic)."""
    parts = [
        reason,
        f"unit={unit}",
        f"returncode={returncode}",
    ]
    if control_group:
        parts.append(f"control_group={control_group}")
    if not oom_policy_verified:
        parts.append("parent_cgroup_unattached=true")
    stdout_tail = sanitize_d1_worker_stream(stdout, allowed_scratch_roots=allowed_scratch_roots)
    stderr_tail = sanitize_d1_worker_stream(stderr, allowed_scratch_roots=allowed_scratch_roots)
    if stdout_tail:
        parts.append(f"stdout_tail={stdout_tail!r}")
    if stderr_tail:
        parts.append(f"stderr_tail={stderr_tail!r}")
    return "; ".join(parts)


def _raise_d1_worker_run_failure(
    reason: str,
    *,
    unit: str,
    proc: subprocess.Popen[bytes],
    output: dict[Any, bytearray],
    control_group: str = "",
    oom_policy_verified: bool,
    worker_env: dict[str, str] | None,
) -> None:
    stdout = ""
    stderr = ""
    if proc.stdout in output:
        stdout = bytes(output[proc.stdout]).decode("utf-8", errors="replace")
    if proc.stderr in output:
        stderr = bytes(output[proc.stderr]).decode("utf-8", errors="replace")
    message = build_d1_worker_exit_diagnostic(
        reason=reason,
        unit=unit,
        returncode=proc.returncode,
        stdout=stdout,
        stderr=stderr,
        control_group=control_group,
        oom_policy_verified=oom_policy_verified,
        allowed_scratch_roots=_scratch_roots_from_worker_env(worker_env),
    )
    raise RuntimeError(message)


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


def assert_memory_headroom(*, outer_bytes: int, inner_bytes: int) -> None:
    meminfo = Path("/proc/meminfo")
    if not meminfo.is_file():
        raise RuntimeError("memory_headroom_unverified")
    available = None
    for line in meminfo.read_text(encoding="ascii").splitlines():
        if line.startswith("MemAvailable:"):
            available = int(line.split()[1]) * 1024
            break
    if available is None or available < outer_bytes + inner_bytes:
        raise RuntimeError("memory_headroom_insufficient")


def _validate_inner_final(path: Path) -> dict:
    if not path.is_file():
        raise RuntimeError("inner_final_counters_missing")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("memory_peak") is None or not payload.get("memory_events"):
        raise RuntimeError("inner_final_events_null")
    return payload


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
        index_gate_path: Path | None = None,
        scope_ready_path: Path | None = None,
        supervisor_pid_path: Path | None = None,
        verify_kernel_envelope: bool = False,
        net_probe_port: int | None = None,
        outer_probe_path: Path | None = None,
        inner_probe_path: Path | None = None,
        parent_netns: str | None = None,
        parent_positive_control: bool = False,
        inject_kill_index_at_gate: bool = False,
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
        self.stage1_done = False
        self.stage2_done = False
        self.inner_meta: dict | None = None
        self._worker_pid_path = worker_pid_path
        self._index_gate_path = index_gate_path
        self._scope_ready_path = scope_ready_path
        self._supervisor_pid_path = supervisor_pid_path
        self._verify_kernel_envelope = verify_kernel_envelope
        self._supervisor_pid: int | None = None
        self._net_probe_port = net_probe_port
        self._outer_probe_path = outer_probe_path
        self._inner_probe_path = inner_probe_path
        self._parent_netns = parent_netns
        self._parent_positive_control = parent_positive_control
        self._inject_kill_index_at_gate = inject_kill_index_at_gate
        self.index_killed_at_gate = False

    def _require_net_probe_artifacts(self) -> None:
        if not self._verify_kernel_envelope:
            return
        if (
            self._net_probe_port is None
            or self._outer_probe_path is None
            or self._inner_probe_path is None
        ):
            raise RuntimeError(f"{INNER_SCOPE_UNVERIFIED}:net_probe_config_missing")
        worker_pid = _pick_worker_pid(self._outer_group, self._worker_pid_path)
        supervisor_pid = self._supervisor_pid
        if supervisor_pid is None and self._supervisor_pid_path is not None:
            supervisor_pid = read_supervisor_pid(self._supervisor_pid_path)
        try:
            verify_dual_net_probe_artifacts(
                outer_path=self._outer_probe_path,
                inner_path=self._inner_probe_path,
                port=self._net_probe_port,
                parent_netns=self._parent_netns,
                parent_positive_control=self._parent_positive_control,
                outer_pid=worker_pid,
                inner_pid=supervisor_pid,
            )
        except NetProbeVerificationError as exc:
            raise RuntimeError(f"{INNER_SCOPE_UNVERIFIED}:net_probe_failed:{exc}") from exc

    def _refresh_outer_pid(self) -> None:
        self.outer.set_worker_pid(_pick_worker_pid(self._outer_group, self._worker_pid_path))

    def _gate_state(self) -> str | None:
        if self._index_gate_path is None:
            return None
        if not self._index_gate_path.is_file():
            return None
        return self._index_gate_path.read_text(encoding="ascii").strip()

    def _write_gate(self, state: str) -> None:
        if self._index_gate_path is None:
            return
        self._index_gate_path.write_text(f"{state}\n", encoding="ascii")

    def try_handshake(self) -> None:
        if self.inner_verified:
            return
        unit = read_inner_scope_unit(self._inner_marker_path)
        if not unit:
            return
        group = inner_scope_cgroup(unit, cgroup_root=self._cgroup_root)
        if group is None:
            return

        if not self.stage1_done:
            if self._scope_ready_path is not None and not self._scope_ready_path.is_file():
                return
            if self._gate_state() != GATE_SCOPE_READY:
                return
            if self._supervisor_pid_path is None:
                return
            supervisor_pid = read_supervisor_pid(self._supervisor_pid_path)
            if supervisor_pid is None:
                return
            meta = verify_inner_scope_unit(
                unit,
                expected_memory_bytes=self._expected_inner_bytes,
                outer_group=self._outer_group.resolve(),
                cgroup_root=self._cgroup_root,
            )
            if not pid_in_cgroup(supervisor_pid, group):
                raise RuntimeError(f"{INNER_SCOPE_UNVERIFIED}:supervisor_not_in_inner")
            worker_pid = _pick_worker_pid(self._outer_group, self._worker_pid_path)
            worker_net = net_namespace_id(worker_pid) if worker_pid else None
            supervisor_net = net_namespace_id(supervisor_pid)
            if not worker_net or not supervisor_net or worker_net != supervisor_net:
                raise RuntimeError(f"{INNER_SCOPE_UNVERIFIED}:net_namespace_mismatch")
            self._supervisor_pid = supervisor_pid
            self._require_net_probe_artifacts()
            self.inner = LiveDiagnosisParentSampler(
                group,
                telemetry_path=self.outer._telemetry_path,
                worker_pid=supervisor_pid,
                boundary="inner",
            )
            self.inner_meta = meta
            self._write_gate(GATE_SPAWN_GRANTED)
            self.stage1_done = True
            self.inner.sample(force=True, reason="handshake_stage1")

        if self.stage1_done and not self.stage2_done:
            if self._gate_state() != GATE_INDEX_AT_GATE:
                return
            index_pid = read_index_pid(self._index_pid_path)
            if index_pid is None:
                return
            if not pid_in_cgroup(index_pid, group):
                raise RuntimeError(f"{INNER_SCOPE_UNVERIFIED}:index_pid_not_in_inner")
            index_net = net_namespace_id(index_pid)
            supervisor_net = net_namespace_id(self._supervisor_pid) if self._supervisor_pid else None
            if not index_net or not supervisor_net or index_net != supervisor_net:
                raise RuntimeError(f"{INNER_SCOPE_UNVERIFIED}:index_net_namespace_mismatch")
            self._require_net_probe_artifacts()
            if self._inject_kill_index_at_gate:
                if not pid_in_cgroup(index_pid, group):
                    raise RuntimeError(f"{INNER_SCOPE_UNVERIFIED}:inject_kill_index_not_in_inner")
                try:
                    os.kill(index_pid, signal.SIGKILL)
                except ProcessLookupError as exc:
                    raise RuntimeError(
                        f"{INNER_SCOPE_UNVERIFIED}:inject_kill_index_missing"
                    ) from exc
                self.index_killed_at_gate = True
                self.stage2_done = True
                self.inner_verified = True
                if self.inner is not None:
                    self.inner.set_worker_pid(index_pid)
                    self.inner.sample(force=True, reason="handshake_stage2_injected_kill")
                return
            self._write_gate(GATE_RUN_GRANTED)
            if self.inner is not None:
                self.inner.set_worker_pid(index_pid)
            self.stage2_done = True
            self.inner_verified = True
            if self.inner is not None:
                self.inner.sample(force=True, reason="handshake_stage2")

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
    index_gate_path: Path | None = None,
    denial_path: Path | None = None,
    expected_inner_bytes: int | None = None,
    require_dual_boundary: bool = True,
    use_bwrap: bool = False,
    scratch_root: Path | None = None,
    source_path: Path | None = None,
    timeout: float = 120,
    cgroup_root: Path = CGROUP_ROOT,
    kernel_network_deny: bool = True,
    inject_kill_index_at_gate: bool = False,
) -> dict:
    """Run worker under cap with parent sampler + phase-triggered samples (D1)."""
    assert_inject_kill_index_at_gate_allowed(
        inject_kill_index_at_gate=inject_kill_index_at_gate,
        require_dual_boundary=require_dual_boundary,
        use_bwrap=use_bwrap,
        worker_env=worker_env,
    )
    if require_dual_boundary:
        if not use_bwrap:
            raise RuntimeError("dual_boundary_requires_bwrap")
        if scratch_root is None or source_path is None:
            raise RuntimeError("dual_boundary_requires_scratch_and_source")
    if require_dual_boundary and worker_env:
        if worker_env.get("CONVMEM_LIVE_DIAG_SYNTHETIC_FAST") == "1":
            raise RuntimeError("cgroup_route_refuses_synthetic_fast")
        if worker_env.get("CONVMEM_LIVE_DIAG_GATE_AUTO_GO") == "1":
            raise RuntimeError("cgroup_route_refuses_auto_go")
    inner_final_path = (
        Path(worker_env["CONVMEM_LIVE_DIAG_INNER_FINAL_PATH"])
        if worker_env and worker_env.get("CONVMEM_LIVE_DIAG_INNER_FINAL_PATH")
        else None
    )
    inner_ack_path = (
        Path(worker_env["CONVMEM_LIVE_DIAG_INNER_ACK_PATH"])
        if worker_env and worker_env.get("CONVMEM_LIVE_DIAG_INNER_ACK_PATH")
        else None
    )
    temp_ready = assert_fresh_cgroup_ready_path(ready_path)
    if expected_inner_bytes is not None:
        assert_memory_headroom(outer_bytes=expected_bytes, inner_bytes=expected_inner_bytes)
    worker_env_mutable = dict(worker_env) if worker_env else {}
    unit = f"convmem-oom-measure-{uuid.uuid4().hex}.service"
    supervisor = Path(__file__).resolve().parent / "watch_oom_cgroup_supervisor.py"
    net_probe_port: int | None = None
    parent_netns: str | None = None
    parent_positive_control = False
    outer_probe_path: Path | None = None
    inner_probe_path: Path | None = None
    if use_bwrap:
        outer_raw = worker_env_mutable.get(NET_PROBE_OUTER_PATH_ENV, "").strip()
        inner_raw = worker_env_mutable.get(NET_PROBE_INNER_PATH_ENV, "").strip()
        if not outer_raw or not inner_raw:
            raise RuntimeError("net_probe_paths_required_for_bwrap")
        outer_probe_path = Path(outer_raw)
        inner_probe_path = Path(inner_raw)
        parent_netns = parent_net_namespace_id()
    selector = selectors.DefaultSelector()
    proc: subprocess.Popen[bytes] | None = None
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
    inner_final_ack_done = False
    output: dict[Any, bytearray] = {}
    stack = ExitStack()
    try:
        if use_bwrap:
            net_probe_port = stack.enter_context(parent_loopback_listener())
            if not parent_can_connect_loopback(net_probe_port):
                raise RuntimeError("net_probe_parent_positive_control_failed")
            parent_positive_control = True
            worker_env_mutable[NET_PROBE_PORT_ENV] = str(net_probe_port)
            worker_env_mutable[D1_BWRAP_ACTIVE_ENV] = "1"
            if not worker_env_mutable.get(D1_PARENT_NETNS_ENV, "").strip():
                parent_ns = parent_net_namespace_id()
                if parent_ns:
                    worker_env_mutable[D1_PARENT_NETNS_ENV] = parent_ns
        command = [
            "systemd-run",
            "--user",
            "--service-type=exec",
            "--pipe",
            "--wait",
            "--quiet",
            "--same-dir",
            f"--unit={unit}",
            *systemd_run_memory_properties(expected_bytes=expected_bytes, timeout=timeout),
        ]
        command.extend(
            d1_systemd_network_properties(
                kernel_network_deny=kernel_network_deny,
                use_bwrap=use_bwrap,
                require_dual_boundary=require_dual_boundary,
            )
        )
        command.extend(_systemd_forward_env(worker_env_mutable))
        inner_exec = [sys.executable, str(supervisor), str(expected_bytes), *worker_argv]
        if use_bwrap:
            if scratch_root is None or source_path is None:
                raise RuntimeError("bwrap_requires_scratch_and_source")
            inner_exec = build_bwrap_command(
                inner_exec,
                scratch_root=scratch_root,
                source_path=source_path,
                repo_root=cwd,
            )
        command.extend(inner_exec)
        popen_env = os.environ.copy()
        popen_env.update(worker_env_mutable)
        proc = subprocess.Popen(
            command,
            cwd=cwd,
            env=popen_env,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        output = register_popen_streams(selector, proc)
        deadline = time.monotonic() + timeout

        def _between_polls() -> None:
            nonlocal dual, outer_sampler, group, group_path, limit_claim
            nonlocal oom_policy_verified, phase_watch, dual_boundary_verified
            nonlocal inner_final_ack_done
            if dual is None and proc.poll() is None:
                try:
                    group_path = _unit_property(unit, "ControlGroup")
                    if group_path:
                        oom_policy = _unit_property(unit, "OOMPolicy")
                        if oom_policy != "continue":
                            return
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
                            scope_ready = (
                                Path(worker_env_mutable["CONVMEM_LIVE_DIAG_SCOPE_READY_PATH"])
                                if worker_env_mutable.get("CONVMEM_LIVE_DIAG_SCOPE_READY_PATH")
                                else None
                            )
                            supervisor_pid_path = (
                                Path(worker_env_mutable["CONVMEM_LIVE_DIAG_SUPERVISOR_PID_PATH"])
                                if worker_env_mutable.get("CONVMEM_LIVE_DIAG_SUPERVISOR_PID_PATH")
                                else None
                            )
                            gate_path = index_gate_path
                            if gate_path is None:
                                raw_gate = worker_env_mutable.get(
                                    "CONVMEM_LIVE_DIAG_INDEX_GATE_PATH", ""
                                )
                                if raw_gate.strip():
                                    gate_path = Path(raw_gate)
                            dual = DualBoundaryController(
                                telemetry_path=telemetry_path,
                                outer_group=group,
                                worker_pid_path=worker_pid_path,
                                inner_marker_path=inner_scope_marker_path,
                                index_pid_path=index_pid_path,
                                expected_inner_bytes=expected_inner_bytes,
                                cgroup_root=cgroup_root,
                                index_gate_path=gate_path,
                                scope_ready_path=scope_ready,
                                supervisor_pid_path=supervisor_pid_path,
                                verify_kernel_envelope=use_bwrap,
                                net_probe_port=net_probe_port,
                                outer_probe_path=outer_probe_path,
                                inner_probe_path=inner_probe_path,
                                parent_netns=parent_netns,
                                parent_positive_control=parent_positive_control,
                                inject_kill_index_at_gate=inject_kill_index_at_gate,
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
                        if dual is not None and dual.outer.samples == 0:
                            raise RuntimeError("parent telemetry unreadable before worker start")
                        temp_ready.write_text("ready\n", encoding="ascii")
                        temp_ready.replace(ready_path)
                except (OSError, subprocess.SubprocessError):
                    pass
            if group is not None:
                if dual is not None:
                    dual.try_handshake()
                    dual_boundary_verified = dual.inner_verified
                    dual.sample()
                    if (
                        require_dual_boundary
                        and inner_final_path is not None
                        and inner_final_path.is_file()
                        and not inner_final_ack_done
                        and proc.poll() is None
                    ):
                        _validate_inner_final(inner_final_path)
                        dual.sample(force=True, reason="inner_final_pre_ack")
                        if inner_ack_path is not None:
                            inner_ack_path.write_text("ack\n", encoding="ascii")
                        inner_final_ack_done = True
                    if phase_watch is not None:
                        for phase in phase_watch.poll_new_phases():
                            dual.try_handshake()
                            dual_boundary_verified = dual.inner_verified
                            dual.sample(reason=f"phase:{phase}", force=True)
                elif outer_sampler is not None:
                    outer_sampler.set_worker_pid(_pick_worker_pid(group, worker_pid_path))
                    outer_sampler.sample()
                    if phase_watch is not None:
                        for phase in phase_watch.poll_new_phases():
                            outer_sampler.sample(reason=f"phase:{phase}", force=True)

        timed_out = run_popen_supervised_drain(
            selector,
            proc,
            output,
            deadline,
            unit=unit,
            own_unit_action=_own_unit_action,
            between_polls=_between_polls,
        )
        if dual is not None and group is not None:
            if phase_watch is not None:
                for phase in phase_watch.poll_new_phases():
                    dual.try_handshake()
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
            _raise_d1_worker_run_failure(
                "parent_sampler_no_samples",
                unit=unit,
                proc=proc,
                output=output,
                control_group=group_path,
                oom_policy_verified=oom_policy_verified,
                worker_env=worker_env_mutable,
            )
        if final_counters is None:
            _raise_d1_worker_run_failure(
                "parent_missing_final_counters",
                unit=unit,
                proc=proc,
                output=output,
                control_group=group_path,
                oom_policy_verified=oom_policy_verified,
                worker_env=worker_env_mutable,
            )
        if denial_path is not None:
            assert_denial_events_empty(denial_path)
        if require_dual_boundary and not dual_boundary_verified:
            _raise_d1_worker_run_failure(
                INNER_SCOPE_UNVERIFIED,
                unit=unit,
                proc=proc,
                output=output,
                control_group=group_path,
                oom_policy_verified=oom_policy_verified,
                worker_env=worker_env_mutable,
            )
        if not oom_policy_verified:
            _raise_d1_worker_run_failure(
                "oom_policy_not_verified",
                unit=unit,
                proc=proc,
                output=output,
                control_group=group_path,
                oom_policy_verified=False,
                worker_env=worker_env_mutable,
            )
        if require_dual_boundary and inner_final_path is not None:
            _validate_inner_final(inner_final_path)
            if inner_ack_path is not None and not inner_ack_path.is_file():
                raise RuntimeError("inner_ack_missing_after_exit")
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
            "index_killed_at_gate": bool(dual and dual.index_killed_at_gate),
        }
    finally:
        stack.close()
        selector.close()
        temp_ready.unlink(missing_ok=True)
        try:
            if proc is not None:
                stop_unit_and_kill_proc(unit=unit, proc=proc, own_unit_action=_own_unit_action)
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

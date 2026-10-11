"""Dual cgroup boundary verification for D1 (outer service + inner index scope)."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

from tests.watch_oom_cgroup_runner import CGROUP_ROOT, _assert_limits, _unit_property

INNER_SCOPE_PREFIX = "convmem-live-diag-index-"
INNER_SCOPE_UNVERIFIED = "inner_scope_unverified"


def _systemd_ip_deny_is_any(value: str | None) -> bool:
    if not value:
        return False
    if value.strip() == "any":
        return True
    parts = value.split()
    return "::/0" in parts and "0.0.0.0/0" in parts


def parse_systemd_memory(value: str) -> int:
    """Parse MemoryMax-style values (e.g. 2G, 1536M) to bytes."""
    raw = value.strip().upper()
    match = re.fullmatch(r"(\d+)([KMG]?)", raw)
    if not match:
        raise ValueError(f"unsupported_memory_limit:{value}")
    amount = int(match.group(1))
    suffix = match.group(2) or "B"
    scale = {"": 1, "K": 1024, "M": 1024**2, "G": 1024**3}[suffix]
    return amount * scale


def read_inner_scope_unit(marker_path: Path) -> str | None:
    if not marker_path.is_file():
        return None
    unit = marker_path.read_text(encoding="utf-8").strip()
    if not unit.startswith(INNER_SCOPE_PREFIX) or not unit.endswith(".scope"):
        return None
    return unit


def inner_scope_cgroup(unit: str, *, cgroup_root: Path = CGROUP_ROOT) -> Path | None:
    group_path = _unit_property(unit, "ControlGroup")
    if not group_path:
        return None
    return cgroup_root / group_path.lstrip("/")


def verify_inner_scope_unit(
    unit: str,
    *,
    expected_memory_bytes: int,
    outer_group: Path,
    cgroup_root: Path = CGROUP_ROOT,
) -> dict:
    """Fail closed unless the inner scope cgroup exists with expected limits."""
    if not unit.startswith(INNER_SCOPE_PREFIX):
        raise RuntimeError(f"{INNER_SCOPE_UNVERIFIED}:bad_unit_name")
    active = _unit_property(unit, "ActiveState")
    if active not in {"active", "running", "deactivating"}:
        raise RuntimeError(f"{INNER_SCOPE_UNVERIFIED}:inner_not_active:{active}")
    group = inner_scope_cgroup(unit, cgroup_root=cgroup_root)
    if group is None or not group.is_dir():
        raise RuntimeError(f"{INNER_SCOPE_UNVERIFIED}:inner_cgroup_missing")
    if group.resolve() == outer_group.resolve():
        raise RuntimeError(f"{INNER_SCOPE_UNVERIFIED}:inner_same_as_outer")
    claim = _assert_limits(group, expected_bytes=expected_memory_bytes, root=cgroup_root)
    swap = _unit_property(unit, "MemorySwapMax")
    if swap not in {"0", "0B"}:
        raise RuntimeError(f"{INNER_SCOPE_UNVERIFIED}:inner_swap_not_zero:{swap}")
    ip_deny = _unit_property(unit, "IPAddressDeny")
    if not _systemd_ip_deny_is_any(ip_deny):
        raise RuntimeError(f"{INNER_SCOPE_UNVERIFIED}:inner_ip_deny_not_any:{ip_deny}")
    families = _unit_property(unit, "RestrictAddressFamilies")
    if families and "AF_UNIX" not in families:
        raise RuntimeError(f"{INNER_SCOPE_UNVERIFIED}:inner_af_unix_not_restricted")
    return {
        "unit": unit,
        "control_group": str(group),
        "limit_claim": claim,
        "active_state": active,
    }


def pid_in_cgroup(pid: int, group: Path) -> bool:
    procs = group / "cgroup.procs"
    if not procs.is_file():
        return False
    try:
        members = {int(p) for p in procs.read_text(encoding="ascii").split() if p.strip()}
    except (OSError, ValueError):
        return False
    return pid in members


def read_index_pid(index_pid_path: Path) -> int | None:
    if not index_pid_path.is_file():
        return None
    try:
        return int(index_pid_path.read_text(encoding="ascii").strip())
    except (OSError, ValueError):
        return None


def probe_systemd_scope_accepts_network_deny() -> bool:
    """Read-only control: systemd-run scope accepts IPAddressDeny=any (no index run)."""
    try:
        result = subprocess.run(
            [
                "systemd-run",
                "--user",
                "--scope",
                "--quiet",
                "--unit=convmem-live-diag-probe-true.scope",
                "-p",
                "MemoryMax=64M",
                "-p",
                "MemorySwapMax=0",
                "-p",
                "IPAddressDeny=any",
                "--",
                "/usr/bin/true",
            ],
            check=False,
            capture_output=True,
            text=True,
            timeout=15,
        )
    except (OSError, subprocess.SubprocessError):
        return False
    if result.returncode != 0:
        return False
    deny = _unit_property("convmem-live-diag-probe-true.scope", "IPAddressDeny")
    subprocess.run(
        ["systemctl", "--user", "reset-failed", "convmem-live-diag-probe-true.scope"],
        check=False,
        capture_output=True,
        timeout=5,
    )
    return _systemd_ip_deny_is_any(deny)

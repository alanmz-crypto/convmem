"""Independent pre-import containment detectors (case 57 T0a).

Detectors have no mutant-name switches. Outer controls change mounts/env/FDs/
inventory views; these same checks reject deviations before integration imports.
"""

from __future__ import annotations

import errno
import hashlib
import json
import os
import socket
import sys
import unicodedata
from pathlib import Path
from typing import Any

from constants import (
    CANARY_PATHS_FILE,
    CHILD_ENV,
    FORBIDDEN_CHILD_ENV_PREFIXES,
    FROZEN_IDNA,
    FROZEN_INVENTORY_PATH,
    FROZEN_MCP,
    FROZEN_NODE,
    FROZEN_PYTHON,
    FROZEN_UNICODE,
    HOST_NETNS_FILE,
    HOST_SENTINEL_ENV,
    IMPORT_TRACE_PATH,
    INNER_ROLE_ENV,
    INNER_ROLE_VALUE,
    INTEGRATION_IMPORT_SENTINELS,
    PREFLIGHT_OK_PATH,
    PREFLIGHT_REPORT_PATH,
    TMPFS_SIZE_BYTES,
)


class PreflightFailure(Exception):
    """Independent preflight rejection before integration import."""


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        while True:
            chunk = fh.read(1024 * 1024)
            if not chunk:
                break
            h.update(chunk)
    return f"sha256:{h.hexdigest()}"


def _mode_octal(path: Path) -> str:
    return f"{path.stat().st_mode & 0o7777:04o}"


def inspect_inherited_fds() -> dict[str, Any]:
    """Inspect inherited FDs before closing anything. Only stdio may be present."""
    allowed = {0, 1, 2}
    found: list[int] = []
    dir_fd = os.open("/proc/self/fd", os.O_RDONLY | os.O_DIRECTORY)
    try:
        for name in os.listdir(dir_fd):
            try:
                fd = int(name)
            except ValueError:
                continue
            if fd == dir_fd:
                continue
            found.append(fd)
    finally:
        os.close(dir_fd)
    unexpected = sorted(fd for fd in found if fd not in allowed)
    if unexpected:
        raise PreflightFailure(f"unexpected_inherited_fds:{unexpected}")
    return {"fds": sorted(found), "unexpected": []}


def assert_no_integration_imports() -> list[str]:
    present = [name for name in INTEGRATION_IMPORT_SENTINELS if name in sys.modules]
    if present:
        raise PreflightFailure(f"pre_import_integration_loaded:{present}")
    return present


def check_environment() -> dict[str, Any]:
    for key in HOST_SENTINEL_ENV:
        if key in os.environ:
            raise PreflightFailure(f"sentinel_env_present:{key}")
    for key in os.environ:
        for prefix in FORBIDDEN_CHILD_ENV_PREFIXES:
            if key == prefix or key.startswith(prefix + "="):
                raise PreflightFailure(f"production_fake_selector:{key}")
            if key.startswith(prefix):
                raise PreflightFailure(f"production_fake_selector:{key}")
    for key, expected in CHILD_ENV.items():
        actual = os.environ.get(key)
        if actual != expected:
            raise PreflightFailure(f"env_mismatch:{key}={actual!r}")
    role = os.environ.get(INNER_ROLE_ENV)
    if role != INNER_ROLE_VALUE:
        raise PreflightFailure(f"inner_role_missing:{role!r}")
    # Exact empty child environment + PWD (bwrap) + role marker only.
    allowed = set(CHILD_ENV) | {INNER_ROLE_ENV, "PWD"}
    unexpected = sorted(k for k in os.environ if k not in allowed)
    if unexpected:
        raise PreflightFailure(f"unexpected_env:{unexpected}")
    return {"env_keys": sorted(os.environ)}


def check_canaries(canary_paths: list[str]) -> list[dict[str, Any]]:
    results = []
    for path in canary_paths:
        read_info: dict[str, Any]
        write_info: dict[str, Any]
        try:
            fd = os.open(path, os.O_RDONLY)
        except OSError as exc:
            read_info = {"ok": False, "errno": exc.errno, "strerror": exc.strerror}
        else:
            os.close(fd)
            read_info = {"ok": True, "errno": None, "strerror": None}
        try:
            fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        except OSError as exc:
            write_info = {"ok": False, "errno": exc.errno, "strerror": exc.strerror}
        else:
            os.close(fd)
            write_info = {"ok": True, "errno": None, "strerror": None}
        results.append({"path": path, "read": read_info, "write": write_info})
        if read_info["ok"] or write_info["ok"]:
            raise PreflightFailure(f"canary_exposed:{path}")
        # Require actual kernel denial (not success). ENOENT/EACCES/EPERM/EROFS acceptable.
        if read_info["errno"] is None or write_info["errno"] is None:
            raise PreflightFailure(f"canary_missing_kernel_denial:{path}")
    return results


def check_readonly_mounts() -> list[dict[str, Any]]:
    probes = []
    for path in ("/src/.write_probe", "/runtime/.write_probe", "/usr/.write_probe"):
        try:
            fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        except OSError as exc:
            info = {"path": path, "ok": False, "errno": exc.errno, "strerror": exc.strerror}
        else:
            os.close(fd)
            info = {"path": path, "ok": True, "errno": None, "strerror": None}
        probes.append(info)
        if info["ok"]:
            raise PreflightFailure(f"readonly_mount_writable:{path}")
        if info["errno"] not in {errno.EROFS, errno.EACCES, errno.EPERM, errno.ENOENT}:
            # Still a denial; record and continue if not ok.
            if info["ok"]:
                raise PreflightFailure(f"readonly_mount_writable:{path}")
    return probes


def check_network_namespace() -> dict[str, Any]:
    info: dict[str, Any] = {"connect_errno": None}
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(0.2)
        try:
            sock.connect(("1.1.1.1", 80))
        except OSError as exc:
            info["connect_errno"] = exc.errno
        else:
            sock.close()
            raise PreflightFailure("network_namespace_leaked")
        finally:
            try:
                sock.close()
            except OSError:
                pass
    except OSError as exc:
        info["connect_errno"] = exc.errno
    ns_path = Path("/proc/self/ns/net")
    if not ns_path.exists():
        raise PreflightFailure("netns_missing")
    child_ns = os.readlink("/proc/self/ns/net")
    info["net_ns"] = child_ns
    host_ns_file = Path(HOST_NETNS_FILE)
    if host_ns_file.is_file():
        host_ns = host_ns_file.read_text(encoding="utf-8").strip()
        info["host_net_ns"] = host_ns
        if host_ns and child_ns == host_ns:
            raise PreflightFailure("netns_not_isolated")
    return info


def _tmpfs_size_bytes(mount_point: str = "/tmp") -> int:
    for line in Path("/proc/mounts").read_text(encoding="utf-8").splitlines():
        parts = line.split()
        if len(parts) < 4:
            continue
        if parts[1] == mount_point and parts[2] == "tmpfs":
            for opt in parts[3].split(","):
                if opt.startswith("size="):
                    raw = opt.split("=", 1)[1]
                    if raw.endswith("k"):
                        return int(raw[:-1]) * 1024
                    if raw.endswith("m"):
                        return int(raw[:-1]) * 1024 * 1024
                    return int(raw)
    raise PreflightFailure("tmpfs_size_unreadable")


def check_mounted_runtime_against_inventory(frozen: list[dict[str, str]]) -> dict[str, Any]:
    """Full /runtime and /usr walk vs frozen inventory — no shallow sample."""
    by_path = {e["path"]: e for e in frozen}
    seen: set[str] = set()
    mismatches: list[str] = []
    extras: list[str] = []

    def consider(abs_path: Path, inventory_path: str) -> None:
        if not abs_path.is_file() or abs_path.is_symlink():
            if abs_path.is_symlink():
                extras.append(f"symlink:{inventory_path}")
                raise PreflightFailure(f"unlisted_or_host_usr:{extras[:5]}:count>={len(extras)}")
            return
        seen.add(inventory_path)
        expected = by_path.get(inventory_path)
        if expected is None:
            extras.append(inventory_path)
            raise PreflightFailure(
                f"unlisted_or_host_usr:{extras[:5]}:count>={len(extras)}"
            )
        actual_mode = _mode_octal(abs_path)
        actual_hash = _sha256_file(abs_path)
        if expected["mode"] != actual_mode or expected["sha256"] != actual_hash:
            mismatches.append(inventory_path)
            raise PreflightFailure(
                f"changed_dependency:{mismatches[:5]}:count>={len(mismatches)}"
            )

    runtime_root = Path("/runtime")
    for dirpath, dirnames, filenames in os.walk(runtime_root, followlinks=False):
        for name in list(dirnames) + list(filenames):
            p = Path(dirpath) / name
            if p.is_symlink():
                rel = p.relative_to(runtime_root).as_posix()
                extras.append(f"symlink:{rel}")
        for name in filenames:
            p = Path(dirpath) / name
            if not p.is_file() or p.is_symlink():
                continue
            rel = p.relative_to(runtime_root).as_posix()
            consider(p, rel)

    usr_root = Path("/usr")
    if usr_root.exists():
        for dirpath, dirnames, filenames in os.walk(usr_root, followlinks=False):
            for name in list(dirnames) + list(filenames):
                p = Path(dirpath) / name
                if p.is_symlink():
                    rel = p.relative_to(usr_root).as_posix()
                    extras.append(f"symlink:sysroot/usr/{rel}")
            for name in filenames:
                p = Path(dirpath) / name
                if not p.is_file() or p.is_symlink():
                    continue
                rel = p.relative_to(usr_root).as_posix()
                consider(p, f"sysroot/usr/{rel}")

    missing = sorted(p for p in by_path if p not in seen)
    # Overlay mutants may hide paths under /runtime; those register as missing.
    # Host /usr bind produces massive extras.
    if extras:
        raise PreflightFailure(f"unlisted_or_host_usr:{extras[:5]}:count={len(extras)}")
    if mismatches:
        raise PreflightFailure(f"changed_dependency:{mismatches[:5]}:count={len(mismatches)}")
    if missing:
        raise PreflightFailure(f"missing_dependency:{missing[:5]}:count={len(missing)}")
    return {
        "seen": len(seen),
        "inventory": len(by_path),
        "extras": 0,
        "mismatches": 0,
        "missing": 0,
    }


def check_runtime_versions() -> dict[str, Any]:
    import importlib.metadata
    import subprocess

    py_ver = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    if py_ver != FROZEN_PYTHON:
        raise PreflightFailure(f"python_version:{py_ver}")
    unicode_ver = unicodedata.unidata_version
    if unicode_ver != FROZEN_UNICODE:
        raise PreflightFailure(f"unicode_version:{unicode_ver}")
    try:
        mcp_ver = importlib.metadata.version("mcp")
    except importlib.metadata.PackageNotFoundError as exc:
        raise PreflightFailure("mcp_missing") from exc
    if mcp_ver != FROZEN_MCP:
        raise PreflightFailure(f"mcp_version:{mcp_ver}")
    try:
        idna_ver = importlib.metadata.version("idna")
    except importlib.metadata.PackageNotFoundError as exc:
        raise PreflightFailure("idna_missing") from exc
    if idna_ver != FROZEN_IDNA:
        raise PreflightFailure(f"idna_version:{idna_ver}")
    if not Path("/runtime/bin/node").is_file():
        raise PreflightFailure("node_binary_missing")
    node = subprocess.run(
        ["/runtime/bin/node", "--version"],
        check=True,
        capture_output=True,
        text=True,
        close_fds=True,
    )
    node_ver = node.stdout.strip()
    if node_ver != FROZEN_NODE:
        raise PreflightFailure(f"node_version:{node_ver}")
    return {
        "python": py_ver,
        "unicode": unicode_ver,
        "mcp": mcp_ver,
        "idna": idna_ver,
        "node": node_ver,
    }


def validate_suite_argv(argv: list[str], expected: list[str]) -> None:
    if argv != expected:
        raise PreflightFailure(f"arbitrary_suite_or_selector_drift:{argv[:8]}")


def run_preflight() -> dict[str, Any]:
    report: dict[str, Any] = {"status": "PENDING"}
    try:
        report["fds"] = inspect_inherited_fds()
        report["integration_imports_before"] = assert_no_integration_imports()
        report["environment"] = check_environment()
        canary_paths = json.loads(Path(CANARY_PATHS_FILE).read_text(encoding="utf-8"))
        report["canaries"] = check_canaries(canary_paths)
        report["readonly_mounts"] = check_readonly_mounts()
        report["network"] = check_network_namespace()
        size = _tmpfs_size_bytes("/tmp")
        if size != TMPFS_SIZE_BYTES:
            raise PreflightFailure(f"tmpfs_size:{size}")
        report["tmpfs_size_bytes"] = size
        frozen = json.loads(Path(FROZEN_INVENTORY_PATH).read_text(encoding="utf-8"))
        report["mount_inventory"] = check_mounted_runtime_against_inventory(frozen)
        report["versions"] = check_runtime_versions()
        assert_no_integration_imports()
        Path(PREFLIGHT_OK_PATH).write_text("ok\n", encoding="utf-8")
        Path(IMPORT_TRACE_PATH).write_text(
            json.dumps(
                {
                    "integration_modules_before_sentinel": [],
                    "preflight": "passed",
                },
                sort_keys=True,
            ),
            encoding="utf-8",
        )
        report["status"] = "PASS"
        report["import_sentinel"] = "written"
    except PreflightFailure as exc:
        report["status"] = "FAIL"
        report["error"] = str(exc)
        report["import_sentinel"] = "not_written"
        Path(PREFLIGHT_REPORT_PATH).write_text(
            json.dumps(report, sort_keys=True, indent=2) + "\n", encoding="utf-8"
        )
        # Ensure sentinel absent on failure.
        try:
            Path(PREFLIGHT_OK_PATH).unlink()
        except FileNotFoundError:
            pass
        raise
    Path(PREFLIGHT_REPORT_PATH).write_text(
        json.dumps(report, sort_keys=True, indent=2) + "\n", encoding="utf-8"
    )
    return report

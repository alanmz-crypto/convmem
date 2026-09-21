"""Independent pre-import containment detectors (case 57 T0a)."""

from __future__ import annotations

import errno
import fcntl
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
    FD_OBSERVATION_FILE,
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
    NODE_RESOLUTION_REPORT_PATH,
    NS_OBSERVATION_FILE,
    PREFLIGHT_OK_PATH,
    PREFLIGHT_REPORT_PATH,
    RESOLUTION_REPORT_PATH,
    SYNTHETIC_DEP_INVENTORY,
    SYNTHETIC_DEP_TREE,
    SYNTHETIC_HOST_USR_INVENTORY,
    SYNTHETIC_HOST_USR_TREE,
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
    """Prove no inherited FD beyond 0/1/2 using the complete /proc/self/fd set.

    If FD_OBSERVATION_FILE exists, use that substituted observation (parent §6.5.8).
    """
    obs_path = Path(FD_OBSERVATION_FILE)
    if obs_path.is_file():
        obs = json.loads(obs_path.read_text(encoding="utf-8"))
        found = [int(x) for x in obs["fds"]]
        source = "substituted_observation"
    else:
        proc_fd_dir = Path("/proc/self/fd")
        try:
            names = os.listdir(proc_fd_dir)
        except OSError as exc:
            raise PreflightFailure(
                f"proc_self_fd_unreadable:{getattr(exc, 'errno', None)}"
            ) from exc
        candidates: list[int] = []
        for name in names:
            try:
                candidates.append(int(name))
            except ValueError:
                continue
        found = []
        # F_GETFD after directory enumeration so the listdir FD is ignored once closed.
        for fd in sorted(set(candidates)):
            try:
                fcntl.fcntl(fd, fcntl.F_GETFD)
            except OSError:
                continue
            found.append(fd)
        source = "proc_self_fd_f_getfd"
    unexpected = sorted(fd for fd in found if fd not in (0, 1, 2))
    if unexpected:
        raise PreflightFailure(f"unexpected_inherited_fds:{unexpected}")
    # Success reports only stdin/stdout/stderr.
    reported = sorted(found)
    if reported != [0, 1, 2]:
        raise PreflightFailure(f"unexpected_inherited_fds:{reported}")
    return {"fds": reported, "unexpected": [], "source": source}


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
            if key == prefix or key.startswith(prefix):
                raise PreflightFailure(f"production_fake_selector:{key}")
    for key, expected in CHILD_ENV.items():
        actual = os.environ.get(key)
        if actual != expected:
            raise PreflightFailure(f"env_mismatch:{key}={actual!r}")
    role = os.environ.get(INNER_ROLE_ENV)
    if role != INNER_ROLE_VALUE:
        raise PreflightFailure(f"inner_role_missing:{role!r}")
    allowed = set(CHILD_ENV) | {INNER_ROLE_ENV, "PWD"}
    unexpected = sorted(k for k in os.environ if k not in allowed)
    if unexpected:
        raise PreflightFailure(f"unexpected_env:{unexpected}")
    return {"env_keys": sorted(os.environ)}


def check_canaries(canary_paths: list[str]) -> list[dict[str, Any]]:
    results = []
    for path in canary_paths:
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
    return probes


def check_network_namespace() -> dict[str, Any]:
    """Keep real unshare-net. Optional substituted ns observation (§6.5.8)."""
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

    obs_path = Path(NS_OBSERVATION_FILE)
    if obs_path.is_file():
        obs = json.loads(obs_path.read_text(encoding="utf-8"))
        child_ns = str(obs["child_net_ns"])
        host_ns = str(obs["host_net_ns"])
        info["source"] = "substituted_observation"
    else:
        if not Path("/proc/self/ns/net").exists():
            raise PreflightFailure("netns_missing")
        child_ns = os.readlink("/proc/self/ns/net")
        host_ns = Path(HOST_NETNS_FILE).read_text(encoding="utf-8").strip()
        info["source"] = "proc_ns"
    info["net_ns"] = child_ns
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


def check_tree_against_inventory(
    *,
    walk_roots: list[tuple[Path, str]],
    frozen: list[dict[str, str]],
    unlisted_prefix: str = "unlisted_or_host_usr:",
    missing_prefix: str = "missing_dependency:",
    changed_prefix: str = "changed_dependency:",
) -> dict[str, Any]:
    """Independent inventory oracle over one or more rooted trees."""
    by_path = {e["path"]: e for e in frozen}
    seen: set[str] = set()

    def consider(abs_path: Path, inventory_path: str) -> None:
        if abs_path.is_symlink():
            raise PreflightFailure(f"{unlisted_prefix}symlink:{inventory_path}")
        if not abs_path.is_file():
            return
        seen.add(inventory_path)
        expected = by_path.get(inventory_path)
        if expected is None:
            raise PreflightFailure(f"{unlisted_prefix}{inventory_path}")
        actual_mode = _mode_octal(abs_path)
        actual_hash = _sha256_file(abs_path)
        if expected["mode"] != actual_mode or expected["sha256"] != actual_hash:
            raise PreflightFailure(f"{changed_prefix}{inventory_path}")

    for root, prefix in walk_roots:
        if not root.exists():
            continue
        for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
            for name in list(dirnames) + list(filenames):
                p = Path(dirpath) / name
                if p.is_symlink():
                    rel = p.relative_to(root).as_posix()
                    inv = f"{prefix}{rel}" if prefix else rel
                    raise PreflightFailure(f"{unlisted_prefix}symlink:{inv}")
            for name in filenames:
                p = Path(dirpath) / name
                if not p.is_file() or p.is_symlink():
                    continue
                rel = p.relative_to(root).as_posix()
                inv = f"{prefix}{rel}" if prefix else rel
                consider(p, inv)

    missing = sorted(p for p in by_path if p not in seen)
    if missing:
        raise PreflightFailure(f"{missing_prefix}{missing[:5]}:count={len(missing)}")
    return {"seen": len(seen), "inventory": len(by_path)}


def check_mounted_runtime_against_inventory(frozen: list[dict[str, str]]) -> dict[str, Any]:
    return check_tree_against_inventory(
        walk_roots=[
            (Path("/runtime"), ""),
            (Path("/usr"), "sysroot/usr/"),
        ],
        frozen=frozen,
        unlisted_prefix="unlisted_or_host_usr:",
        missing_prefix="missing_dependency:",
        changed_prefix="changed_dependency:",
    )


def check_synthetic_dep_oracle() -> dict[str, Any] | None:
    """Optional synthetic disposable root under /fixture — same oracle."""
    inv_path = Path(SYNTHETIC_DEP_INVENTORY)
    tree = Path(SYNTHETIC_DEP_TREE)
    if not inv_path.is_file():
        return None
    frozen = json.loads(inv_path.read_text(encoding="utf-8"))
    return check_tree_against_inventory(
        walk_roots=[(tree, "")],
        frozen=frozen,
        unlisted_prefix="unlisted_dependency:",
        missing_prefix="missing_dependency:",
        changed_prefix="changed_dependency:",
    )


def check_synthetic_host_usr_oracle() -> dict[str, Any] | None:
    """Disposable synthetic host_usr root — same fail-closed inventory oracle."""
    inv_path = Path(SYNTHETIC_HOST_USR_INVENTORY)
    tree = Path(SYNTHETIC_HOST_USR_TREE)
    if not inv_path.is_file():
        return None
    frozen = json.loads(inv_path.read_text(encoding="utf-8"))
    return check_tree_against_inventory(
        walk_roots=[(tree, "")],
        frozen=frozen,
        unlisted_prefix="unlisted_or_host_usr:",
        missing_prefix="missing_dependency:",
        changed_prefix="changed_dependency:",
    )


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


def _map_abs_to_inventory(abs_path: str) -> str | None:
    if abs_path.startswith("/runtime/"):
        return abs_path[len("/runtime/") :]
    if abs_path.startswith("/usr/"):
        return "sysroot/usr/" + abs_path[len("/usr/") :]
    return None


def _parse_maps_regular_files(maps_text: str) -> list[str]:
    """Parse /proc/*/maps lines into distinct regular-file pathnames."""
    import stat as stat_mod

    seen: set[str] = set()
    out: list[str] = []
    for line in maps_text.splitlines():
        parts = line.split(None, 5)
        if len(parts) < 6:
            continue
        raw = parts[5]
        if " (deleted)" in raw:
            raw = raw[: raw.index(" (deleted)")]
        if not raw.startswith("/"):
            continue
        if raw in seen:
            continue
        seen.add(raw)
        try:
            st = os.lstat(raw)
        except OSError:
            continue
        if stat_mod.S_ISLNK(st.st_mode) or not stat_mod.S_ISREG(st.st_mode):
            continue
        out.append(raw)
    return out


def _validate_runtime_mappings(
    *,
    paths: list[str],
    frozen_paths: set[str],
    kind_for: dict[str, str] | None = None,
) -> tuple[list[dict[str, str]], list[str], list[dict[str, str]]]:
    """Represent all mapped regular files; inventory-validate every /runtime or /usr path.

    /src is source-only (skipped). Non-/runtime/non-/usr paths fail closed.
    """
    kind_for = kind_for or {}
    mapped_items: list[dict[str, str]] = []
    source_only: list[dict[str, str]] = []
    unlisted: list[str] = []
    seen_resolved: set[str] = set()
    for abs_path in paths:
        try:
            resolved = str(Path(abs_path).resolve())
        except OSError:
            resolved = abs_path
        if resolved in seen_resolved:
            continue
        seen_resolved.add(resolved)
        kind = kind_for.get(abs_path, kind_for.get(resolved, "maps_regular_file"))
        if resolved.startswith("/src/") or abs_path.startswith("/src/"):
            source_only.append({"kind": kind, "path": resolved, "inventory_path": ""})
            continue
        inv = _map_abs_to_inventory(resolved)
        if inv is None:
            inv = _map_abs_to_inventory(abs_path)
        item = {"kind": kind, "path": resolved, "inventory_path": inv or ""}
        if inv is None:
            unlisted.append(resolved)
            continue
        mapped_items.append(item)
        if inv not in frozen_paths:
            unlisted.append(resolved)
    return mapped_items, unlisted, source_only


def record_resolutions(frozen_paths: set[str]) -> dict[str, Any]:
    """Record actual process mappings; validate /runtime and /usr against inventory."""
    import subprocess

    maps_text = Path("/proc/self/maps").read_text(encoding="utf-8", errors="replace")
    maps_files = _parse_maps_regular_files(maps_text)

    kind_for: dict[str, str] = {}
    exe = str(Path(sys.executable).resolve())
    kind_for[exe] = "interpreter"
    try:
        proc_exe = str(Path("/proc/self/exe").resolve())
        kind_for[proc_exe] = "proc_exe"
    except OSError:
        proc_exe = None
    for mod in list(sys.modules.values()):
        f = getattr(mod, "__file__", None)
        if not f:
            continue
        try:
            mp = str(Path(f).resolve())
        except OSError:
            continue
        kind_for.setdefault(mp, "module")

    # Union maps regular files with interpreter/modules so classification is complete.
    all_paths: list[str] = []
    seen: set[str] = set()
    for p in [exe] + ([proc_exe] if proc_exe else []) + list(kind_for) + maps_files:
        if p and p not in seen:
            seen.add(p)
            all_paths.append(p)

    for p in maps_files:
        name = Path(p).name
        if name.startswith("ld-") or ".so" in name:
            kind_for.setdefault(p, "elf_loader_or_shared_lib")

    mapped_items, unlisted, source_only = _validate_runtime_mappings(
        paths=all_paths, frozen_paths=frozen_paths, kind_for=kind_for
    )
    if unlisted:
        raise PreflightFailure(f"unlisted_resolution:{unlisted[:5]}")
    # Every maps regular file under /runtime or /usr must appear in the report.
    maps_runtime_validated = {
        item["path"]
        for item in mapped_items
        if item["path"].startswith("/runtime/") or item["path"].startswith("/usr/")
    }
    for raw in maps_files:
        try:
            resolved = str(Path(raw).resolve())
        except OSError:
            resolved = raw
        if resolved.startswith("/src/"):
            continue
        if resolved.startswith("/runtime/") or resolved.startswith("/usr/"):
            if resolved not in maps_runtime_validated:
                raise PreflightFailure(f"unlisted_resolution:{resolved}")

    python_report = {
        "resolutions": mapped_items,
        "source_only": source_only,
        "maps_regular_files": maps_files,
        "maps_regular_file_count": len(maps_files),
        "mapped_count": len(mapped_items),
        "source": "python_/proc/self/maps",
    }
    Path(RESOLUTION_REPORT_PATH).write_text(
        json.dumps(python_report, sort_keys=True, indent=2) + "\n", encoding="utf-8"
    )

    # Fixed Node probe: execPath, exact version, own /proc/self/maps regular files.
    node_probe = (
        "const fs=require('fs');"
        "const maps=fs.readFileSync('/proc/self/maps','utf8');"
        "const seen=new Set();"
        "const files=[];"
        "for (const line of maps.split('\\n')) {"
        "  const parts=line.trim().split(/\\s+/);"
        "  if (parts.length<6) continue;"
        "  let p=parts.slice(5).join(' ');"
        "  const del=p.indexOf(' (deleted)');"
        "  if (del>=0) p=p.slice(0,del);"
        "  if (!p.startsWith('/')||seen.has(p)) continue;"
        "  seen.add(p);"
        "  try {"
        "    const st=fs.lstatSync(p);"
        "    if (st.isSymbolicLink()) continue;"
        "    if (st.isFile()) files.push(p);"
        "  } catch (e) {}"
        "}"
        "process.stdout.write(JSON.stringify({"
        "execPath:process.execPath,"
        "version:process.version,"
        "maps_regular_files:files"
        "}));"
    )
    node = subprocess.run(
        ["/runtime/bin/node", "-e", node_probe],
        check=True,
        capture_output=True,
        text=True,
        close_fds=True,
    )
    node_payload = json.loads(node.stdout)
    if node_payload.get("version") != FROZEN_NODE:
        raise PreflightFailure(f"node_version:{node_payload.get('version')}")
    node_paths = [str(node_payload["execPath"]), *list(node_payload["maps_regular_files"])]
    node_kind = {str(node_payload["execPath"]): "node_execPath"}
    for p in node_payload["maps_regular_files"]:
        name = Path(p).name
        if name.startswith("ld-") or ".so" in name:
            node_kind.setdefault(p, "elf_loader_or_shared_lib")
    node_mapped, node_unlisted, node_source_only = _validate_runtime_mappings(
        paths=node_paths, frozen_paths=frozen_paths, kind_for=node_kind
    )
    if node_unlisted:
        raise PreflightFailure(f"unlisted_resolution:{node_unlisted[:5]}")
    node_runtime_validated = {
        item["path"]
        for item in node_mapped
        if item["path"].startswith("/runtime/") or item["path"].startswith("/usr/")
    }
    for raw in node_payload["maps_regular_files"]:
        try:
            resolved = str(Path(raw).resolve())
        except OSError:
            resolved = raw
        if resolved.startswith("/src/"):
            continue
        if resolved.startswith("/runtime/") or resolved.startswith("/usr/"):
            if resolved not in node_runtime_validated:
                raise PreflightFailure(f"unlisted_resolution:{resolved}")
    node_report = {
        "execPath": node_payload["execPath"],
        "version": node_payload["version"],
        "maps_regular_files": node_payload["maps_regular_files"],
        "resolutions": node_mapped,
        "source_only": node_source_only,
        "mapped_count": len(node_mapped),
        "source": "node_/proc/self/maps",
    }
    Path(NODE_RESOLUTION_REPORT_PATH).write_text(
        json.dumps(node_report, sort_keys=True, indent=2) + "\n", encoding="utf-8"
    )
    return {"python": python_report, "node": node_report}


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
        synth = check_synthetic_dep_oracle()
        if synth is not None:
            report["synthetic_dep"] = synth
        host_usr = check_synthetic_host_usr_oracle()
        if host_usr is not None:
            report["synthetic_host_usr"] = host_usr
        report["versions"] = check_runtime_versions()
        report["resolutions"] = record_resolutions({e["path"] for e in frozen})
        assert_no_integration_imports()
        Path(PREFLIGHT_OK_PATH).write_text("ok\n", encoding="utf-8")
        Path(IMPORT_TRACE_PATH).write_text(
            json.dumps(
                {"integration_modules_before_sentinel": [], "preflight": "passed"},
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
        try:
            Path(PREFLIGHT_OK_PATH).unlink()
        except FileNotFoundError:
            pass
        raise
    Path(PREFLIGHT_REPORT_PATH).write_text(
        json.dumps(report, sort_keys=True, indent=2) + "\n", encoding="utf-8"
    )
    return report

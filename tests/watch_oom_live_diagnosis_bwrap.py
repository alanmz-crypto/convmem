"""Test-only bwrap envelope for D1 outer worker isolation."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path


def bwrap_available() -> bool:
    return shutil.which("bwrap") is not None


def build_bwrap_command(
    inner_argv: list[str],
    *,
    scratch_root: Path,
    source_path: Path,
    repo_root: Path,
) -> list[str]:
    """Wrap worker argv: RO root via /, scratch writable bind, source RO (no repo overlay)."""
    if not bwrap_available():
        raise RuntimeError("bwrap_unavailable")
    scratch_root = scratch_root.resolve()
    source_path = source_path.resolve()
    repo_root = repo_root.resolve()
    if scratch_root.is_relative_to(repo_root):
        pass  # scratch must stay a separate bind; never ro-bind repo_root on top
    cmd: list[str] = [
        "bwrap",
        "--unshare-user",
        "--unshare-net",
        "--die-with-parent",
        "--ro-bind",
        "/",
        "/",
        "--proc",
        "/proc",
        "--dev",
        "/dev",
        "--tmpfs",
        "/tmp",
        "--bind",
        str(scratch_root),
        str(scratch_root),
        "--ro-bind",
        str(source_path),
        str(source_path),
        "--chdir",
        str(repo_root),
        "--",
    ]
    cmd.extend(inner_argv)
    return cmd


def run_bwrap_capability_check(
    *,
    scratch_root: Path,
    source_path: Path,
    repo_root: Path,
    repo_probe_file: Path,
    timeout: float = 30.0,
) -> dict[str, bool]:
    """Synthetic FS capability proof inside bwrap (no production paths)."""
    script = (
        "import os, sys\n"
        f"scratch = {str(scratch_root)!r}\n"
        f"source = {str(source_path)!r}\n"
        f"repo_probe = {str(repo_probe_file)!r}\n"
        "out = {}\n"
        "p = os.path.join(scratch, 'bwrap_write_probe.txt')\n"
        "try:\n"
        "    open(p, 'w', encoding='utf-8').write('ok\\n')\n"
        "    out['scratch_writable'] = os.path.isfile(p)\n"
        "except OSError:\n"
        "    out['scratch_writable'] = False\n"
        "try:\n"
        "    open(source, 'a', encoding='utf-8').write('x')\n"
        "    out['source_readonly'] = False\n"
        "except OSError:\n"
        "    out['source_readonly'] = True\n"
        "try:\n"
        "    open(repo_probe, 'a', encoding='utf-8').write('x')\n"
        "    out['repo_readonly'] = False\n"
        "except OSError:\n"
        "    out['repo_readonly'] = True\n"
        "import json\n"
        "print(json.dumps(out))\n"
    )
    cmd = build_bwrap_command(
        [sys.executable, "-c", script],
        scratch_root=scratch_root,
        source_path=source_path,
        repo_root=repo_root,
    )
    result = subprocess.run(
        cmd,
        check=False,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    if result.returncode != 0:
        raise RuntimeError(f"bwrap_capability_check_failed:{result.stderr.strip()}")
    payload = json.loads(result.stdout.strip())
    return {
        "scratch_writable": bool(payload.get("scratch_writable")),
        "source_readonly": bool(payload.get("source_readonly")),
        "repo_readonly": bool(payload.get("repo_readonly")),
    }


D1_PARENT_NETNS_ENV = "CONVMEM_LIVE_DIAG_PARENT_NETNS"


def verify_d1_kernel_envelope(
    *,
    scratch_root: Path,
    source_path: Path,
    repo_root: Path,
) -> None:
    """Behavioral check: RO root, writable scratch, net ns distinct from parent hint."""
    scratch_root = scratch_root.resolve()
    source_path = source_path.resolve()
    repo_root = repo_root.resolve()
    probe = scratch_root / ".d1_envelope_write_probe"
    try:
        probe.write_text("1\n", encoding="utf-8")
        probe.unlink(missing_ok=True)
    except OSError as exc:
        raise RuntimeError("d1_envelope_scratch_not_writable") from exc
    repo_marker = repo_root / "tests" / "watch_oom_live_diagnosis_bwrap.py"
    try:
        with repo_marker.open("a", encoding="utf-8"):
            raise RuntimeError("d1_envelope_root_not_readonly")
    except OSError:
        pass
    try:
        with source_path.open("a", encoding="utf-8"):
            raise RuntimeError("d1_envelope_source_not_readonly")
    except OSError:
        pass
    parent_ns = os.environ.get(D1_PARENT_NETNS_ENV, "").strip()
    if not parent_ns:
        raise RuntimeError("d1_envelope_parent_netns_missing")
    self_ns = net_namespace_id(os.getpid())
    if not self_ns or self_ns == parent_ns:
        raise RuntimeError("d1_envelope_net_not_isolated")


def net_namespace_id(pid: int) -> str | None:
    link = Path(f"/proc/{pid}/ns/net")
    if not link.is_symlink():
        return None
    try:
        return os.readlink(link)
    except OSError:
        return None

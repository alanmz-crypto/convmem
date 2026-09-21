"""Fixed bubblewrap launch plan — no permissive fallback."""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Mapping, Sequence

from constants import (
    BWRAP_MANDATORY_FLAGS,
    CHILD_ENV,
    FORBIDDEN_BWRAP_FLAGS,
    HOST_SENTINEL_ENV,
    INNER_ROLE_ENV,
    INNER_ROLE_VALUE,
    TMPFS_SIZE_BYTES,
)


def require_bwrap() -> str:
    path = shutil.which("bwrap")
    if not path:
        raise SystemExit("bubblewrap_missing")
    return path


def create_fixture_root() -> Path:
    root = Path(tempfile.mkdtemp(prefix="convmem-openclaw-fixture.", dir="/tmp"))
    os.chmod(root, 0o700)
    for name in ("home", "tmp", "config", "cache", "data", "pytest-strict", "pytest-legacy"):
        (root / name).mkdir(mode=0o700)
    return root


def create_canary_root() -> Path:
    """Distinct mode0700 host temp root — never mounted on the success path."""
    root = Path(tempfile.mkdtemp(prefix="convmem-openclaw-canary.", dir="/tmp"))
    os.chmod(root, 0o700)
    for name in ("outside_a", "outside_b"):
        (root / name).write_text("synthetic-canary\n", encoding="utf-8")
    return root


def build_bwrap_argv(
    *,
    bwrap: str,
    source_root: Path,
    runtime_root: Path,
    fixture_root: Path,
    inner_argv: Sequence[str],
    usr_source: Path | None = None,
    extra_ro_binds: Sequence[tuple[str, str]] = (),
    extra_binds: Sequence[tuple[str, str]] = (),
    runtime_bin_overlay: Sequence[tuple[str, str]] | None = None,
    hide_runtime_bin: bool = False,
    unshare_net: bool = True,
    extra_env: Mapping[str, str] | None = None,
    omit_mandatory: Sequence[str] = (),
) -> list[str]:
    flags = list(BWRAP_MANDATORY_FLAGS)
    if not unshare_net:
        flags = [f for f in flags if f != "--unshare-net"]
    for omit in omit_mandatory:
        flags = [f for f in flags if f != omit]
    argv = [bwrap, *flags]
    for flag in FORBIDDEN_BWRAP_FLAGS:
        if flag in argv:
            raise SystemExit(f"forbidden_bwrap_flag:{flag}")
    argv += [
        "--proc", "/proc",
        "--dev", "/dev",
        "--size", str(TMPFS_SIZE_BYTES),
        "--tmpfs", "/tmp",
        "--ro-bind", str(source_root), "/src",
        "--ro-bind", str(runtime_root), "/runtime",
    ]
    if hide_runtime_bin:
        argv += ["--tmpfs", "/runtime/bin"]
        for host_path, sandbox_path in runtime_bin_overlay or ():
            argv += ["--ro-bind", host_path, sandbox_path]
    usr = usr_source if usr_source is not None else (runtime_root / "sysroot" / "usr")
    argv += ["--ro-bind", str(usr), "/usr"]
    argv += [
        "--symlink", "usr/bin", "/bin",
        "--symlink", "usr/lib", "/lib",
        "--symlink", "usr/lib64", "/lib64",
        "--bind", str(fixture_root), "/fixture",
        "--chdir", "/src",
        "--clearenv",
    ]
    for key, value in CHILD_ENV.items():
        argv += ["--setenv", key, value]
    argv += ["--setenv", INNER_ROLE_ENV, INNER_ROLE_VALUE]
    if extra_env:
        for key, value in extra_env.items():
            argv += ["--setenv", key, value]
    for host_path, sandbox_path in extra_ro_binds:
        argv += ["--ro-bind", host_path, sandbox_path]
    for host_path, sandbox_path in extra_binds:
        argv += ["--bind", host_path, sandbox_path]
    argv += list(inner_argv)
    return argv


def launch_contained(
    argv: list[str],
    *,
    timeout: int,
    pass_fds: Sequence[int] = (),
) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env.update(HOST_SENTINEL_ENV)
    # Success path: close_fds True and no pass_fds. FD mutant passes an extra FD.
    # close_fds=True always; pass_fds keeps only the listed descriptors besides stdio.
    return subprocess.run(
        argv,
        check=False,
        capture_output=True,
        text=True,
        timeout=timeout,
        env=env,
        close_fds=True,
        pass_fds=tuple(pass_fds),
    )


def host_net_ns() -> str:
    return os.readlink("/proc/self/ns/net")

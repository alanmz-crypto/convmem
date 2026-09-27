"""Fixed bubblewrap launch plan — no permissive fallback."""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Mapping, Sequence

from constants import (  # pylint: disable=E0401  # fixture path-injection import; module resolved via sys.path
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


def _mkdir_0700(path: Path) -> None:
    path.mkdir(parents=False, exist_ok=True)
    os.chmod(path, 0o700)


def create_fixture_root() -> Path:
    """Fresh disposable fixture — only synthetic identity config, never live paths."""
    root = Path(tempfile.mkdtemp(prefix="convmem-openclaw-fixture.", dir="/tmp"))
    os.chmod(root, 0o700)
    for name in ("home", "tmp", "config", "cache", "data", "pytest-strict", "pytest-legacy"):
        _mkdir_0700(root / name)
    # Parents mode 0700 before suites; only HOME identity config.toml (no live config/data).
    home_dot_config = root / "home" / ".config"
    _mkdir_0700(home_dot_config)
    home_convmem = home_dot_config / "convmem"
    _mkdir_0700(home_convmem)
    (home_convmem / "config.toml").write_text(
        '[index]\nchroma_dir = "/fixture/legacy-live-identity/chroma"\n',
        encoding="utf-8",
    )
    legacy_root = root / "legacy-live-identity"
    _mkdir_0700(legacy_root)
    _mkdir_0700(legacy_root / "chroma")
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
    extra_ro_binds: Sequence[tuple[str, str]] = (),
    extra_env: Mapping[str, str] | None = None,
) -> list[str]:
    argv = [bwrap, *BWRAP_MANDATORY_FLAGS]
    for flag in FORBIDDEN_BWRAP_FLAGS:
        if flag in argv:
            raise SystemExit(f"forbidden_bwrap_flag:{flag}")
    # Every mandatory flag from BWRAP_MANDATORY_FLAGS must remain present.
    missing_mandatory = [
        flag for flag in BWRAP_MANDATORY_FLAGS if flag != "ALL" and flag not in argv
    ]
    if missing_mandatory:
        raise SystemExit(f"missing_mandatory_flag:{missing_mandatory[0]}")
    # Real runtime sysroot always at /usr — never mount live host /usr.
    usr = runtime_root / "sysroot" / "usr"
    argv += [
        "--proc", "/proc",
        "--dev", "/dev",
        "--size", str(TMPFS_SIZE_BYTES),
        "--tmpfs", "/tmp",
        "--ro-bind", str(source_root), "/src",
        "--ro-bind", str(runtime_root), "/runtime",
        "--ro-bind", str(usr), "/usr",
    ]
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
    argv += list(inner_argv)
    return argv


def launch_contained(
    argv: list[str],
    *,
    timeout: int,
) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env.update(HOST_SENTINEL_ENV)
    return subprocess.run(
        argv,
        check=False,
        capture_output=True,
        text=True,
        timeout=timeout,
        env=env,
        close_fds=True,
    )


def host_net_ns() -> str:
    return os.readlink("/proc/self/ns/net")

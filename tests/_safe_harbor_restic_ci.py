"""Pinned Restic 0.19.0 identity for hosted full_ci (stdlib-only)."""

from __future__ import annotations

import hashlib
import os
import subprocess
from pathlib import Path

RESTIC_VERSION = "0.19.0"
RESTIC_LINUX_AMD64_BZ2_SHA256 = (
    "13176fe6d89d4357947a2cd107218ab2873a5f9d8e1ac2d4cd1c8e07e6839c21"
)
RESTIC_BINARY_SHA256 = (
    "ae7fe58ab3511f830fd31d157158620b209522ff1332b119199d2e938d72338c"
)
CI_RESTIC_ENV = "SAFE_HARBOR_CI_RESTIC_EXECUTABLE"


def verify_restic_binary(path: Path) -> None:
    if not path.is_file():
        raise RuntimeError(f"refusing missing restic executable {path}")
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if digest != RESTIC_BINARY_SHA256:
        raise RuntimeError(
            f"refusing restic identity drift {path}: sha256={digest} expected={RESTIC_BINARY_SHA256}"
        )
    proc = subprocess.run(
        [str(path), "version"],
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
        env={"LANG": "C.UTF-8"},
    )
    if proc.returncode != 0:
        raise RuntimeError(f"refusing restic version probe: {proc.stderr}")
    line = proc.stdout.strip().splitlines()[0]
    if RESTIC_VERSION not in line:
        raise RuntimeError(f"refusing unexpected restic version line: {line!r}")


def resolve_ci_restic_executable() -> Path:
    raw = os.environ.get(CI_RESTIC_ENV, "").strip()
    if not raw:
        raise RuntimeError(f"refusing full CI without {CI_RESTIC_ENV}")
    if not Path(raw).is_absolute():
        raise RuntimeError("refusing relative CI Restic path")
    path = Path(raw).resolve(strict=True)
    if not os.access(path, os.X_OK):
        raise RuntimeError(f"refusing non-executable {CI_RESTIC_ENV}={raw!r}")
    verify_restic_binary(path)
    return path


def bridge_restic_into_toolbin(fixture_root: Path, restic: Path) -> Path:
    toolbin = fixture_root / "toolbin"
    if toolbin.is_symlink():
        raise RuntimeError("refusing symlinked toolbin")
    toolbin.mkdir(parents=True, exist_ok=True)
    bridge = toolbin / "restic"
    if bridge.exists() or bridge.is_symlink():
        if not bridge.is_symlink():
            raise RuntimeError(f"refusing non-symlink toolbin restic at {bridge}")
        existing = bridge.resolve(strict=False)
        if existing != restic:
            raise RuntimeError(f"refusing toolbin restic identity drift {existing} != {restic}")
        return bridge
    bridge.symlink_to(restic)
    if bridge.resolve(strict=False) != restic:
        raise RuntimeError(f"refusing toolbin restic bridge outside selected executable {restic}")
    return bridge


def restic_fixture_meta(restic: Path, bridge: Path) -> dict[str, str]:
    verify_restic_binary(restic)
    return {
        "restic_executable": str(restic),
        "restic_executable_sha256": RESTIC_BINARY_SHA256,
        "restic_bridge": str(bridge),
        "restic_version": RESTIC_VERSION,
    }


def stage_ci_restic(fixture_root: Path) -> dict[str, str]:
    """Require the pinned tool for hosted CI or an explicitly supplied local tool."""
    if os.environ.get("GITHUB_ACTIONS") != "true" and not os.environ.get(CI_RESTIC_ENV):
        return {}
    restic = resolve_ci_restic_executable()
    bridge = bridge_restic_into_toolbin(fixture_root, restic)
    return restic_fixture_meta(restic, bridge)

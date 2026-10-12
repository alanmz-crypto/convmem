"""Prod vs lab write boundary — refuse cross-context writes unless explicitly confirmed."""

from __future__ import annotations

import os
import pwd
from pathlib import Path
from typing import Iterable

PROD_DATA_ROOT = Path("~/.local/share/convmem").expanduser()
LAB_DATA_ROOT = Path("~/.local/share/convmem-lab").expanduser()
PROD_CONFIG = Path("~/.config/convmem/config.toml").expanduser()
LAB_CONFIG = Path("~/.config/convmem-lab/config.toml").expanduser()

RESTIC_GATE_EXCEPTION_ENV = "CONVMEM_RESTIC_GATE_EXCEPTION"
RESTIC_GATE_EXCEPTION_CONTEXTS = frozenset({"isolated-test", "isolated-lab"})


def config_path() -> Path:
    return Path(os.environ.get("CONVMEM_CONFIG", str(PROD_CONFIG))).expanduser()


def data_profile(chroma_dir: str | Path) -> str:
    """Classify the configured data directory as prod, lab, or other."""
    p = Path(chroma_dir).expanduser().resolve()
    for root, label in ((LAB_DATA_ROOT, "lab"), (PROD_DATA_ROOT, "prod")):
        try:
            p.relative_to(root.resolve())
            return label
        except ValueError:
            continue
    s = str(p)
    if "convmem-lab" in s:
        return "lab"
    if "local/share/convmem" in s:
        return "prod"
    return "other"


def workspace_repo(cwd: Path | None = None) -> str | None:
    """Infer repo lane from cwd and CONVMEM_ROOT."""
    root = os.environ.get("CONVMEM_ROOT", "").strip()
    if root:
        name = Path(root).expanduser().name.lower()
        if name == "convmem-lab":
            return "lab"
        if name == "convmem":
            return "prod"

    cwd = (cwd or Path.cwd()).resolve()
    for p in [cwd, *cwd.parents]:
        name = p.name.lower()
        if name == "convmem-lab":
            return "lab"
        if name == "convmem":
            return "prod"
    return None


def write_boundary_message(chroma_dir: str | Path) -> str | None:
    """Return a refusal message when a write would cross prod/lab lanes."""
    profile = data_profile(chroma_dir)
    workspace = workspace_repo()
    cfg = config_path()

    if profile == "prod":
        lab_context = workspace == "lab" or "convmem-lab" in str(cfg)
        if lab_context and os.environ.get("CONVMEM_CONFIRM_PROD") != "1":
            return (
                "Refusing prod write from convmem-lab context.\n"
                f"  workspace: {workspace or Path.cwd()}\n"
                f"  config: {cfg}\n"
                f"  chroma: {Path(chroma_dir).expanduser()}\n"
                "Prod Tier 1 is backed up — lab work must stay on convmem-lab data.\n"
                "Set CONVMEM_CONFIRM_PROD=1 only when you intentionally mean prod."
            )

    if profile == "lab":
        prod_context = workspace == "prod" and os.environ.get("CONVMEM_CONFIRM_LAB") != "1"
        if prod_context:
            return (
                "Refusing lab write from prod convmem repo without lab intent.\n"
                f"  workspace: {workspace or Path.cwd()}\n"
                f"  config: {cfg}\n"
                f"  chroma: {Path(chroma_dir).expanduser()}\n"
                "Use scripts/convmem-lab.sh (sets CONVMEM_CONFIRM_LAB=1) or export it explicitly."
            )

    return None


def require_write_consent(chroma_dir: str | Path) -> None:
    msg = write_boundary_message(chroma_dir)
    if msg:
        raise RuntimeError(msg)


def _account_homes() -> list[Path]:
    """Current HOME plus the passwd home, so a redirected HOME cannot hide prod."""
    homes = [Path.home()]
    try:
        homes.append(Path(pwd.getpwuid(os.getuid()).pw_dir))
    except (KeyError, OSError):
        pass
    return homes


def _canonical_roots(relative: str) -> set[Path]:
    return {(home / relative).resolve(strict=False) for home in _account_homes()}


def _overlaps(path: Path, roots: Iterable[Path]) -> bool:
    for root in roots:
        if path == root or path.is_relative_to(root) or root.is_relative_to(path):
            return True
    return False


def restic_gate_exception(
    paths: Iterable[str | Path], *, config_file: str | Path | None = None
) -> tuple[bool, str]:
    """Classify a Restic-gate skip request for one bound operation.

    Allowed only with an explicit isolated context and canonical isolation of
    every affected path (and the config) from the production roots of both the
    current HOME and the account's passwd home. cwd, names, confirm variables
    and CONVMEM_ROOT play no part. Unknown or missing context refuses.
    """
    context = os.environ.get(RESTIC_GATE_EXCEPTION_ENV, "").strip()
    if context not in RESTIC_GATE_EXCEPTION_CONTEXTS:
        return False, (
            f"{RESTIC_GATE_EXCEPTION_ENV}={context!r} is not an explicit isolated "
            f"context ({', '.join(sorted(RESTIC_GATE_EXCEPTION_CONTEXTS))})"
        )
    prod_roots = _canonical_roots(".local/share/convmem") | _canonical_roots(
        ".config/convmem"
    )
    lab_roots = _canonical_roots(".local/share/convmem-lab")
    resolved = [Path(p).expanduser().resolve(strict=False) for p in paths]
    if config_file is not None:
        resolved.append(Path(config_file).expanduser().resolve(strict=False))
    if not resolved:
        return False, "no affected paths to classify"
    for path in resolved:
        if _overlaps(path, prod_roots):
            return False, f"path {path} overlaps a production root"
    if context == "isolated-lab":
        data_paths = resolved[:-1] if config_file is not None else resolved
        for path in data_paths:
            if not any(path.is_relative_to(root) for root in lab_roots):
                return False, f"isolated-lab path {path} is outside the lab data root"
    else:
        for path in resolved:
            if _overlaps(path, lab_roots):
                return False, f"isolated-test path {path} overlaps the lab data root"
    return True, f"{context}: all affected paths canonically isolated from production"


def runtime_summary(chroma_dir: str | Path) -> str:
    profile = data_profile(chroma_dir)
    workspace = workspace_repo() or "unknown"
    cfg = config_path()
    blocked = write_boundary_message(chroma_dir) is not None
    state = "BLOCKED (cross-lane)" if blocked else "OK"
    return (
        f"lane={profile} workspace={workspace} config={cfg.name} write_guard={state}"
    )

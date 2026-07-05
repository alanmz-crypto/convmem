"""Prod vs lab write boundary — refuse cross-context writes unless explicitly confirmed."""

from __future__ import annotations

import os
from pathlib import Path

PROD_DATA_ROOT = Path("~/.local/share/convmem").expanduser()
LAB_DATA_ROOT = Path("~/.local/share/convmem-lab").expanduser()
PROD_CONFIG = Path("~/.config/convmem/config.toml").expanduser()
LAB_CONFIG = Path("~/.config/convmem-lab/config.toml").expanduser()


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


def runtime_summary(chroma_dir: str | Path) -> str:
    profile = data_profile(chroma_dir)
    workspace = workspace_repo() or "unknown"
    cfg = config_path()
    blocked = write_boundary_message(chroma_dir) is not None
    state = "BLOCKED (cross-lane)" if blocked else "OK"
    return (
        f"lane={profile} workspace={workspace} config={cfg.name} write_guard={state}"
    )

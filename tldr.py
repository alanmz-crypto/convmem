"""Print lane-specific TLDR cheat sheets."""

from __future__ import annotations

import os
from pathlib import Path

_REPO = Path(os.environ.get("CONVMEM_ROOT", Path(__file__).resolve().parent))

_LANES: dict[str, Path] = {
    "willowyhollow-practice": _REPO / "docs/WILLOWYHOLLOW-TLDR.md",
    "willowyhollow-preview": _REPO / "docs/WILLOWYHOLLOW-TLDR.md",
    "convmem": _REPO / "docs/CONVMEM-TLDR.md",
}


def resolve_tldr_path(*, lane: str | None = None) -> Path:
    """Pick TLDR markdown for workspace lane or explicit --lane."""
    from next_steps import workspace_context

    if lane:
        key = lane.strip().lower()
    else:
        key = str(workspace_context().get("lane") or "general")

    if key in _LANES:
        return _LANES[key]
    if "willowyhollow" in key:
        return _LANES["willowyhollow-practice"]
    return _LANES["convmem"]


def read_tldr(*, lane: str | None = None) -> str:
    path = resolve_tldr_path(lane=lane)
    if not path.is_file():
        raise FileNotFoundError(f"TLDR not found: {path}")
    return path.read_text(encoding="utf-8")


def list_lanes() -> list[str]:
    return sorted(_LANES.keys())

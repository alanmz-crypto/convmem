"""Shared production-path guards for hermetic watch-OOM workers."""

from __future__ import annotations

import os
from pathlib import Path

PRODUCTION_PREFIXES = (
    str((Path.home() / ".local/share/convmem").resolve()),
    str((Path.home() / ".config/convmem").resolve()),
)
DEFAULT_BRIEF = str((Path.home() / ".local/share/convmem/brief.md").expanduser())


def share_convmem_worktree_path(path: Path) -> bool:
    """Git worktrees under ~/.local/share/convmem are dev checkouts, not corpus."""
    share = (Path.home() / ".local/share/convmem").resolve()
    try:
        resolved = path.resolve()
    except OSError:
        return False
    if not resolved.is_relative_to(share):
        return False
    return resolved.is_relative_to(share / "worktrees")


def production_path_denied(path: object) -> bool:
    try:
        raw = os.fspath(path)
    except TypeError:
        return False
    expanded = str(Path(raw).expanduser())
    try:
        resolved = str(Path(expanded).resolve())
    except OSError:
        resolved = expanded
    if DEFAULT_BRIEF in (expanded, resolved):
        return True
    try:
        resolved_path = Path(expanded).resolve()
    except OSError:
        resolved_path = None
    if resolved_path is not None and share_convmem_worktree_path(resolved_path):
        return False
    for prefix in PRODUCTION_PREFIXES:
        if resolved.startswith(prefix) or expanded.startswith(prefix):
            return True
    return False

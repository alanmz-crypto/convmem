"""Shared production-path guards for hermetic watch-OOM workers."""

from __future__ import annotations

import os
from pathlib import Path

PRODUCTION_PREFIXES = (
    str((Path.home() / ".local/share/convmem").resolve()),
    str((Path.home() / ".config/convmem").resolve()),
)
DEFAULT_BRIEF = str((Path.home() / ".local/share/convmem/brief.md").expanduser())


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
    for prefix in PRODUCTION_PREFIXES:
        if resolved.startswith(prefix) or expanded.startswith(prefix):
            return True
    return False

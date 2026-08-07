"""Exhaustive source_path classification (first-match; does not select recipe)."""

from __future__ import annotations

import re
from pathlib import Path

_SCHEME_RE = re.compile(r"^[a-zA-Z][a-zA-Z0-9+.-]*:")

CLASS_UNKNOWN = "unknown"
CLASS_LEDGER = "logical_ledger"
CLASS_OTHER_LOGICAL = "other_logical"
CLASS_KIRO_SNAPSHOT = "kiro_snapshot"
CLASS_FILESYSTEM = "filesystem"

ALL_CLASSES = (
    CLASS_UNKNOWN,
    CLASS_LEDGER,
    CLASS_OTHER_LOGICAL,
    CLASS_KIRO_SNAPSHOT,
    CLASS_FILESYSTEM,
)


def classify_source_path(source_path: str | None) -> str:
    """Return exactly one class. Does not select the document reconstruction recipe."""
    sp = (source_path or "").strip()
    if not sp:
        return CLASS_UNKNOWN

    if sp.startswith("ledger:"):
        return CLASS_LEDGER

    # Absolute filesystem paths (Unix). Expanduser first for ~/...
    expanded = str(Path(sp).expanduser()) if sp.startswith("~") else sp
    if expanded.startswith("/"):
        parts = Path(expanded).parts
        if "snapshots" in parts:
            return CLASS_KIRO_SNAPSHOT
        return CLASS_FILESYSTEM

    # Non-filesystem URI / logical schemes (site:, http(s):, observation:, …)
    if _SCHEME_RE.match(sp):
        return CLASS_OTHER_LOGICAL

    return CLASS_UNKNOWN

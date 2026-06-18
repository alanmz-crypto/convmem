"""Format metadata fields for CLI display."""

from __future__ import annotations

import os
from datetime import datetime, timezone


def when_from_meta(meta: dict) -> str | None:
    """Best-effort date/time for a indexed excerpt."""
    raw = meta.get("timestamp") or meta.get("date")
    if raw:
        s = str(raw).strip()
        if s:
            return s[:19].replace("T", " ")
    src = meta.get("source_path") or ""
    if src and os.path.isfile(src):
        mtime = os.path.getmtime(src)
        return datetime.fromtimestamp(mtime, tz=timezone.utc).strftime("%Y-%m-%d")
    return None


def when_label(meta: dict) -> str:
    """Human-readable when string; em dash if unknown."""
    return when_from_meta(meta) or "—"

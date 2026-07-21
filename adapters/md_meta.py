"""Shared markdown metadata helpers for document adapters."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path


def file_date(path: Path) -> str:
    """UTC YYYY-MM-DD from mtime, or empty string if unavailable."""
    try:
        mtime = path.stat().st_mtime
        return datetime.fromtimestamp(mtime, tz=timezone.utc).strftime("%Y-%m-%d")
    except OSError:
        return ""


def doc_title(text: str, fallback: str = "") -> str:
    """First AT1 heading, else ``fallback``."""
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("# ") and not stripped.startswith("##"):
            return stripped.lstrip("# ").strip()
    return fallback

"""Shared helpers for line-oriented JSONL adapters."""

from __future__ import annotations

import json
from collections.abc import Iterator
from pathlib import Path


def iter_jsonl_dicts(filepath: str) -> Iterator[dict]:
    """Yield dict records from a UTF-8 JSONL file; skip bad/non-dict lines."""
    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(record, dict):
                yield record


def nonempty_stripped(value: object) -> str | None:
    """Return stripped text, or None when missing/blank/non-string."""
    if not isinstance(value, str):
        return None
    text = value.strip()
    return text or None


def session_parse_context(
    filepath: str, read_meta
) -> tuple[str, str]:
    """Common session_id + workspace setup for sess_*/events.jsonl parsers."""
    meta = read_meta(filepath)
    session_id = meta.get("session_id") or Path(filepath).parent.name
    workspace = meta.get("workspace_directory") or ""
    return session_id, workspace

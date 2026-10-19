"""Leaf helpers for rendering canonical message chunks (shared by ingest and expand)."""

from __future__ import annotations

import json
from pathlib import Path


def load_processed(path: str) -> dict:
    p = Path(path)
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"processed.json corrupt at {p}: {exc}") from exc


def processed_path_str(entry_path: str) -> str:
    return str(Path(entry_path).expanduser().resolve())


def path_is_excluded(processed: dict, path_key: str) -> bool:
    for entry in processed.values():
        if not isinstance(entry, dict) or not entry.get("excluded"):
            continue
        ep = entry.get("path")
        if ep and processed_path_str(ep) == path_key:
            return True
    return False


def render_chunk_message_views(messages: list[dict], total_budget: int = 10000) -> list[str]:
    """Return each exact per-message view used by :func:`render_chunk`."""
    if not messages:
        return []
    per_msg = max(150, total_budget // len(messages))
    lines = []
    for message in messages:
        content = message["content"].strip()
        if len(content) > per_msg:
            content = content[:per_msg] + " […]"
        lines.append(f"{message['role']}: {content}")
    return lines


def render_chunk(messages: list[dict], total_budget: int = 10000) -> str:
    """Render a chunk for summarization within a bounded character budget."""
    if not messages:
        return ""
    return "\n".join(render_chunk_message_views(messages, total_budget=total_budget))


def chunk_date(messages: list[dict]) -> str:
    for message in messages:
        ts = message.get("timestamp")
        if ts:
            return str(ts)[:10]
    return ""

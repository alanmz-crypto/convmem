"""Adapter for kiro-cli 2.x session transcripts (jsonl_kiro_session).

kiro-cli stores full agent chats at:
    ~/.kiro/sessions/<hash>/sess_<uuid>/messages.jsonl

This is kiro-cli transcript storage — not a separate IDE product. Legacy chats
through ~April 2026 may still live in ~/.local/share/kiro-cli/data.sqlite3.

Thin prompt sidecars at ~/.kiro/sessions/cli/*.history are not indexed.
"""

import json
from pathlib import Path

from adapters.jsonl_io import (
    iter_jsonl_dicts,
    nonempty_stripped,
    session_parse_context,
)

_SKIP_PAYLOAD_TYPES = frozenset(
    {
        "turn_start",
        "turn_end",
        "tool_call",
        "tool_result",
        "session_metadata",
        "usage_summary",
        "pending_interaction",
        "interaction_resolved",
    }
)


def is_kiro_session_jsonl(path: Path | str) -> bool:
    """True for kiro-cli sess_*/messages.jsonl files (not cli/ or snapshots/)."""
    p = Path(path)
    if p.name != "messages.jsonl":
        return False
    if "snapshots" in p.parts:
        return False
    parent = p.parent.name
    return parent.startswith("sess_")


def read_session_meta(filepath: str) -> dict:
    """Read sibling session.json for title and workspace paths."""
    session_dir = Path(filepath).parent
    session_json = session_dir / "session.json"
    if not session_json.is_file():
        return {}
    try:
        with open(session_json, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(data, dict):
        return {}

    session_id = data.get("id")
    if not isinstance(session_id, str) or not session_id:
        session_id = session_dir.name

    title = data.get("title")
    workspaces = data.get("workspacePaths")
    workspace = ""
    if isinstance(workspaces, list) and workspaces:
        first = workspaces[0]
        if isinstance(first, str):
            workspace = first

    return {
        "session_id": session_id,
        "workspace_directory": workspace,
        "title": title if isinstance(title, str) else "",
    }


def parse(filepath: str) -> list[dict]:
    """Parse a kiro-cli messages.jsonl into canonical messages."""
    session_id, workspace = session_parse_context(filepath, read_session_meta)

    messages: list[dict] = []
    for record in iter_jsonl_dicts(filepath):
        payload = record.get("payload")
        if not isinstance(payload, dict):
            continue

        ptype = payload.get("type")
        if ptype in _SKIP_PAYLOAD_TYPES:
            continue
        if ptype not in ("user", "assistant"):
            continue

        content = nonempty_stripped(payload.get("content"))
        if content is None:
            continue

        timestamp = record.get("timestamp")
        ts = timestamp if isinstance(timestamp, str) else None

        messages.append(
            {
                "role": ptype,
                "content": content,
                "timestamp": ts,
                "session_id": session_id,
                "workspace_directory": workspace,
            }
        )

    return messages

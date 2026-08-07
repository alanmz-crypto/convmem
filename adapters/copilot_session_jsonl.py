"""Adapter for GitHub Copilot CLI session transcripts (jsonl_copilot_session).

Copilot CLI stores full agent chats at:
    ~/.copilot/session-state/<uuid>/events.jsonl

Sibling files (not indexed by this adapter):
    session.db          — live SQLite; do not watch
    workspace.yaml      — session metadata (title, cwd)
    ~/.copilot/session-store.db — global index DB; do not watch
"""

from __future__ import annotations

from pathlib import Path

from adapters.jsonl_io import (
    iter_jsonl_dicts,
    nonempty_stripped,
    session_parse_context,
)

_MESSAGE_TYPES = frozenset({"user.message", "assistant.message"})


def is_copilot_session_jsonl(path: Path | str) -> bool:
    """True for Copilot CLI session-state events.jsonl files."""
    p = Path(path)
    if p.name != "events.jsonl":
        return False
    try:
        p.resolve().relative_to((Path.home() / ".copilot" / "session-state").resolve())
    except (ValueError, OSError):
        return False
    # ~/.copilot/session-state/<uuid>/events.jsonl
    return p.parent.parent.name == "session-state"


def read_session_meta(filepath: str) -> dict:
    """Read sibling workspace.yaml and/or session.start event for metadata."""
    session_dir = Path(filepath).parent
    meta: dict = {
        "session_id": session_dir.name,
        "workspace_directory": "",
        "title": "",
    }

    workspace_yaml = session_dir / "workspace.yaml"
    if workspace_yaml.is_file():
        try:
            text = workspace_yaml.read_text(encoding="utf-8")
        except OSError:
            text = ""
        for line in text.splitlines():
            if ":" not in line:
                continue
            key, _, raw = line.partition(":")
            key = key.strip()
            val = raw.strip().strip('"').strip("'")
            if key == "cwd" and val:
                meta["workspace_directory"] = val
            elif key == "name" and val:
                meta["title"] = val
            elif key == "id" and val:
                meta["session_id"] = val

    # Prefer session.start for cwd when yaml missing/empty
    if not meta["workspace_directory"] or not meta["title"]:
        try:
            for record in iter_jsonl_dicts(filepath):
                if record.get("type") != "session.start":
                    continue
                data = record.get("data")
                if not isinstance(data, dict):
                    break
                sid = data.get("sessionId")
                if isinstance(sid, str) and sid:
                    meta["session_id"] = sid
                ctx = data.get("context")
                if isinstance(ctx, dict):
                    cwd = ctx.get("cwd")
                    if isinstance(cwd, str) and cwd and not meta["workspace_directory"]:
                        meta["workspace_directory"] = cwd
                break
        except OSError:
            pass

    return meta


def parse(filepath: str) -> list[dict]:
    """Parse a Copilot CLI events.jsonl into canonical messages."""
    session_id, workspace = session_parse_context(filepath, read_session_meta)

    messages: list[dict] = []
    for record in iter_jsonl_dicts(filepath):
        etype = record.get("type")
        if etype not in _MESSAGE_TYPES:
            continue

        data = record.get("data")
        if not isinstance(data, dict):
            continue

        content = nonempty_stripped(data.get("content"))
        if content is None:
            continue

        role = "user" if etype == "user.message" else "assistant"
        ts = record.get("timestamp")
        timestamp = ts if isinstance(ts, str) else None

        messages.append(
            {
                "role": role,
                "content": content,
                "timestamp": timestamp,
                "session_id": session_id,
                "workspace_directory": workspace,
                "source_type": "copilot_session",
            }
        )

    return messages

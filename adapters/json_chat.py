"""Adapter for Continue session files (json_continue_sessions).

Real format (observed on disk) — not the flat handoff sketch:
    {
      "sessionId": "...",
      "history": [
        {
          "message": {"role": "user"|"assistant"|"tool", "content": ...},
          "contextItems": [...],
          "promptLogs": [{"prompt": "<system>...<user>...", ...}]  # NOT used
        }
      ]
    }

`message.content` is either a plain string or a list of blocks like
[{"type": "text", "text": "..."}]. We extract text blocks only.

`promptLogs[].prompt` embeds the system prompt plus user text — we never
read it; `message.content` is the clean source. `tool` turns are skipped.
"""

import json
from pathlib import Path


def _extract_content(raw) -> str:
    if raw is None:
        return ""
    if isinstance(raw, str):
        return raw
    if isinstance(raw, list):
        parts: list[str] = []
        for block in raw:
            if not isinstance(block, dict):
                continue
            if block.get("type") != "text":
                continue
            text = block.get("text")
            if isinstance(text, str):
                parts.append(text)
        return "\n".join(parts)
    return ""


def read_session_meta(filepath: str) -> dict:
    """File-level Continue session fields (for open/index metadata)."""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(data, dict):
        return {}
    session_id = data.get("sessionId")
    workspace = data.get("workspaceDirectory")
    title = data.get("title")
    return {
        "session_id": session_id if isinstance(session_id, str) else Path(filepath).stem,
        "workspace_directory": workspace if isinstance(workspace, str) else "",
        "title": title if isinstance(title, str) else "",
    }


def parse(filepath: str) -> list[dict]:
    """Parse a Continue session JSON file into canonical messages.

    Returns:
        [{"role": "user"|"assistant", "content": str, "timestamp": str|None}, ...]
    """
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, dict):
        return []
    history = data.get("history")
    if not isinstance(history, list):
        return []

    meta = read_session_meta(filepath)
    session_id = meta.get("session_id")
    workspace = meta.get("workspace_directory") or ""

    messages: list[dict] = []
    for entry in history:
        if not isinstance(entry, dict):
            continue
        message = entry.get("message")
        if not isinstance(message, dict):
            continue

        role = message.get("role")
        if role not in ("user", "assistant"):
            continue

        content = _extract_content(message.get("content")).strip()
        if not content:
            continue

        messages.append(
            {
                "role": role,
                "content": content,
                "timestamp": None,
                "session_id": session_id,
                "workspace_directory": workspace,
            }
        )

    return messages

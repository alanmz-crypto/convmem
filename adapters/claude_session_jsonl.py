"""Adapter for Claude Code CLI session transcripts (jsonl_claude_session).

Claude Code stores full agent chats at:
    ~/.claude/projects/<project-slug>/<session-uuid>.jsonl
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from adapters.jsonl_io import (
    iter_jsonl_dicts,
    session_parse_context,
)

_MESSAGE_TYPES = frozenset({"user", "assistant"})
_SIGNAL_TYPES = frozenset({"user", "assistant", "system"})
_PROBE_LINES = 10

_STRIP_TAGS = (
    "system-reminder",
    "local-command-caveat",
    "command-name",
    "command-message",
    "command-args",
    "local-command-stdout",
)
_STRIP_RE = re.compile(
    r"<(" + "|".join(_STRIP_TAGS) + r")>.*?</\1>",
    re.DOTALL,
)


def _claude_projects_root() -> Path:
    return (Path.home() / ".claude" / "projects").resolve()


def is_claude_session_jsonl(path: Path | str) -> bool:
    """True for Claude Code project session *.jsonl files."""
    p = Path(path)
    if p.suffix != ".jsonl":
        return False
    try:
        p.resolve().relative_to(_claude_projects_root())
    except (ValueError, OSError):
        return False
    return _probe_claude_session(p)


def _probe_claude_session(path: Path) -> bool:
    """First N non-blank lines must carry sessionId and a signal type."""
    seen_session = False
    seen_type = False
    count = 0
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                count += 1
                if count > _PROBE_LINES:
                    break
                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if not isinstance(record, dict):
                    continue
                sid = record.get("sessionId") or record.get("session_id")
                if isinstance(sid, str) and sid:
                    seen_session = True
                rtype = record.get("type")
                if rtype in _SIGNAL_TYPES:
                    seen_type = True
                if seen_session and seen_type:
                    return True
    except OSError:
        return False
    return False


def read_session_meta(filepath: str) -> dict:
    """Read session id and cwd from the first substantive records."""
    meta: dict = {
        "session_id": "",
        "workspace_directory": "",
    }
    for record in iter_jsonl_dicts(filepath):
        sid = record.get("sessionId") or record.get("session_id")
        if isinstance(sid, str) and sid and not meta["session_id"]:
            meta["session_id"] = sid
        cwd = record.get("cwd")
        if isinstance(cwd, str) and cwd and not meta["workspace_directory"]:
            meta["workspace_directory"] = cwd
        if meta["session_id"] and meta["workspace_directory"]:
            break
    if not meta["session_id"]:
        meta["session_id"] = Path(filepath).stem
    return meta


def strip_injected_context(text: str) -> str:
    """Remove Claude Code injected wrappers and their contents."""
    return _STRIP_RE.sub("", text).strip()


def _text_from_content(raw: object) -> str | None:
    if isinstance(raw, str):
        text = strip_injected_context(raw)
        return text or None
    if isinstance(raw, list):
        parts: list[str] = []
        for block in raw:
            if not isinstance(block, dict):
                continue
            if block.get("type") != "text":
                continue
            t = block.get("text")
            if isinstance(t, str) and t.strip():
                parts.append(t.strip())
        joined = "\n".join(parts)
        return joined or None
    return None


def parse(filepath: str) -> list[dict]:
    """Parse a Claude Code session jsonl into canonical messages."""
    session_id, workspace = session_parse_context(filepath, read_session_meta)

    messages: list[dict] = []
    for record in iter_jsonl_dicts(filepath):
        rtype = record.get("type")
        if rtype not in _MESSAGE_TYPES:
            continue
        if record.get("isSidechain") is True:
            continue

        message = record.get("message")
        if not isinstance(message, dict):
            continue
        content = _text_from_content(message.get("content"))
        if content is None:
            continue

        ts = record.get("timestamp")
        timestamp = ts if isinstance(ts, str) else None
        cwd = record.get("cwd")
        workspace_dir = cwd if isinstance(cwd, str) and cwd else workspace
        sid = record.get("sessionId") or record.get("session_id")
        rec_session = sid if isinstance(sid, str) and sid else session_id

        messages.append(
            {
                "role": rtype,
                "content": content,
                "timestamp": timestamp,
                "session_id": rec_session,
                "workspace_directory": workspace_dir,
                "source_type": "claude_session",
            }
        )

    return messages

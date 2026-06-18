"""Adapter for SQLite-backed chat stores.

Branches:
  - Kiro: `conversations_v2.value` JSON blobs with nested history[]
  - Open WebUI: flat `chat_message` rows
  - Crush: `sessions` + `messages` with JSON `parts` arrays
  - Cursor store.db: deferred (blob DAG)
"""

import json
import sqlite3
from datetime import datetime, timezone


def _table_names(conn: sqlite3.Connection) -> set[str]:
    rows = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()
    return {r[0] for r in rows}


def _message_column_names(conn: sqlite3.Connection) -> set[str]:
    return {r[1] for r in conn.execute("PRAGMA table_info(messages)").fetchall()}


def is_sqlite_crush_schema(
    con: sqlite3.Connection, tables: set[str] | None = None
) -> bool:
    """Crush: goose_db_version + sessions/messages with a parts column.

    Explicitly excludes Kiro (conversations_v2) and Open WebUI (chat_message).
    """
    tables = tables or _table_names(con)
    if "conversations_v2" in tables or "chat_message" in tables:
        return False
    if "blobs" in tables and "meta" in tables:
        return False
    if "goose_db_version" not in tables:
        return False
    if "sessions" not in tables or "messages" not in tables:
        return False
    return "parts" in _message_column_names(con)


def _epoch_to_iso(value) -> str | None:
    """Convert a unix-epoch-seconds value to an ISO-8601 UTC string."""
    if value is None:
        return None
    try:
        return datetime.fromtimestamp(int(value), tz=timezone.utc).isoformat()
    except (ValueError, OSError, OverflowError):
        return None


def _kiro_user_text(user: dict) -> str:
    content = user.get("content")
    if not isinstance(content, dict):
        return ""
    prompt = content.get("Prompt")
    if not isinstance(prompt, dict):
        return ""
    text = prompt.get("prompt")
    return text.strip() if isinstance(text, str) else ""


def _kiro_assistant_text(assistant: dict) -> str:
    if not isinstance(assistant, dict):
        return ""
    response = assistant.get("Response")
    if isinstance(response, dict):
        text = response.get("content")
        if isinstance(text, str) and text.strip():
            return text.strip()
    tool_use = assistant.get("ToolUse")
    if isinstance(tool_use, dict):
        text = tool_use.get("content")
        if isinstance(text, str) and text.strip():
            return text.strip()
    return ""


def _parse_kiro(conn: sqlite3.Connection) -> list[dict]:
    """Kiro: conversations_v2 rows hold JSON with history[].user / .assistant."""
    messages: list[dict] = []
    for (raw,) in conn.execute("SELECT value FROM conversations_v2"):
        try:
            data = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            continue
        if not isinstance(data, dict):
            continue
        history = data.get("history")
        if not isinstance(history, list):
            continue

        for turn in history:
            if not isinstance(turn, dict):
                continue
            conv_id = data.get("conversation_id")
            user = turn.get("user")
            if isinstance(user, dict):
                text = _kiro_user_text(user)
                if text:
                    ts = user.get("timestamp")
                    messages.append(
                        {
                            "role": "user",
                            "content": text,
                            "timestamp": ts if isinstance(ts, str) else None,
                            "conversation_id": conv_id if isinstance(conv_id, str) else None,
                        }
                    )

            assistant = turn.get("assistant")
            text = _kiro_assistant_text(assistant if isinstance(assistant, dict) else {})
            if text:
                messages.append(
                    {
                        "role": "assistant",
                        "content": text,
                        "timestamp": None,
                        "conversation_id": conv_id if isinstance(conv_id, str) else None,
                    }
                )

    return messages


def _crush_timestamp_to_iso(value) -> str | None:
    """Crush created_at — schema says ms; observed DBs often use seconds (~1e9)."""
    if value is None:
        return None
    try:
        ts = int(value)
        if ts >= 10_000_000_000:
            ts = ts / 1000
        return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()
    except (ValueError, OSError, OverflowError):
        return None


def _crush_parts_to_content(parts_raw) -> str:
    try:
        parts = json.loads(parts_raw) if isinstance(parts_raw, str) else parts_raw
    except (json.JSONDecodeError, TypeError):
        return ""
    if not isinstance(parts, list):
        return ""

    texts: list[str] = []
    for part in parts:
        if not isinstance(part, dict):
            continue
        ptype = part.get("type")
        data = part.get("data")
        if not isinstance(data, dict):
            continue
        if ptype == "text":
            text = data.get("text")
            if isinstance(text, str) and text.strip():
                texts.append(text.strip())
        # v1: skip reasoning and finish (metadata-only) part types
    return "\n\n".join(texts)


def _parse_crush(conn: sqlite3.Connection, filepath: str) -> list[dict]:
    """Crush: messages ordered by created_at; parts JSON holds turn text."""
    from pathlib import Path

    workspace = ""
    p = Path(filepath)
    if p.name == "crush.db" and p.parent.name == ".crush":
        workspace = str(p.parent.parent)

    messages: list[dict] = []
    cursor = conn.execute(
        "SELECT session_id, role, parts, model, provider, created_at "
        "FROM messages ORDER BY session_id, created_at, id"
    )
    for session_id, role, parts_raw, model, provider, created_at in cursor:
        if role not in ("user", "assistant"):
            continue
        content = _crush_parts_to_content(parts_raw)
        if not content:
            continue
        msg: dict = {
            "role": role,
            "content": content,
            "timestamp": _crush_timestamp_to_iso(created_at),
            "session_id": session_id if isinstance(session_id, str) else None,
        }
        if workspace:
            msg["workspace_directory"] = workspace
        if role == "assistant":
            if isinstance(model, str) and model:
                msg["model"] = model
            if isinstance(provider, str) and provider:
                msg["provider"] = provider
        messages.append(msg)
    return messages


def _parse_openwebui(conn: sqlite3.Connection) -> list[dict]:
    messages: list[dict] = []
    # Order so each conversation's turns stay contiguous and chronological.
    cursor = conn.execute(
        "SELECT role, content, created_at FROM chat_message "
        "ORDER BY chat_id, created_at, id"
    )
    for role, raw_content, created_at in cursor:
        if role not in ("user", "assistant"):
            continue
        if raw_content is None:
            continue

        # Open WebUI stores content as a JSON string literal; unwrap it.
        try:
            content = json.loads(raw_content)
        except (json.JSONDecodeError, TypeError):
            content = raw_content
        if not isinstance(content, str):
            continue
        if not content.strip():
            continue

        messages.append(
            {
                "role": role,
                "content": content,
                "timestamp": _epoch_to_iso(created_at),
            }
        )
    return messages


def parse(filepath: str) -> list[dict]:
    """Parse a SQLite chat store into canonical messages.

    Returns:
        [{"role": "user"|"assistant", "content": str, "timestamp": str|None}, ...]
    """
    uri = f"file:{filepath}?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    try:
        tables = _table_names(conn)
        if "conversations_v2" in tables:
            return _parse_kiro(conn)
        if "chat_message" in tables:
            return _parse_openwebui(conn)
        if is_sqlite_crush_schema(conn, tables):
            return _parse_crush(conn, filepath)
        raise NotImplementedError(
            f"No SQLite adapter branch matches schema in {filepath} "
            f"(tables: {sorted(tables)[:10]}...)"
        )
    finally:
        conn.close()

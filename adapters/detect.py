"""Format detection and adapter routing.

Detection logic mirrors inventory.py exactly. Only the adapters that are
implemented and gate-passed are wired into `get_parser`; unimplemented
formats (Kiro, Continue, Aider, Crush, Cursor store.db) return None so the ingest
pipeline skips them cleanly until their adapters land.
"""

import json
import sqlite3
from pathlib import Path
from typing import Callable, Optional

from adapters import jsonl_chat, json_chat, markdown_chat, sqlite_chat
from adapters.sqlite_chat import is_sqlite_crush_schema

# Map detected format -> human-facing tool name (used in metadata).
TOOL_BY_FORMAT = {
    "jsonl_cursor": "cursor",
    "sqlite_openwebui": "openwebui",
    "sqlite_kiro": "kiro",
    "json_continue_sessions": "continue",
    "aider_markdown": "aider",
    "sqlite_crush": "crush",
    "sqlite_cursor_store": "cursor",
}

# Map detected format -> parse callable. None means "recognized but not yet
# implemented" — deliberately deferred per the build order.
_PARSERS: dict[str, Optional[Callable[[str], list[dict]]]] = {
    "jsonl_cursor": jsonl_chat.parse,
    "sqlite_openwebui": sqlite_chat.parse,
    "sqlite_kiro": sqlite_chat.parse,
    "json_continue_sessions": json_chat.parse,
    "aider_markdown": markdown_chat.parse,
    "sqlite_crush": sqlite_chat.parse,
    "sqlite_cursor_store": None,
}


def detect_format(path: Path | str) -> Optional[str]:
    """Classify a file by format, or return None if unrecognized."""
    path = Path(path)

    if path.name == ".aider.chat.history.md":
        return "aider_markdown"
    if path.suffix == ".md":
        return None

    if path.suffix == ".jsonl":
        if "agent-transcripts" in path.parts:
            return "jsonl_cursor"
        return None

    if path.suffix in (".sqlite3", ".db"):
        return _detect_sqlite(path)

    if path.suffix == ".json":
        return _detect_json_continue(path)

    return None


def _sqlite_tables(con: sqlite3.Connection) -> set[str]:
    return {
        r[0]
        for r in con.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    }


def _detect_sqlite(path: Path) -> Optional[str]:
    try:
        con = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
        tables = _sqlite_tables(con)
    except Exception:
        return None

    try:
        if "conversations_v2" in tables:
            return "sqlite_kiro"
        if "chat_message" in tables:
            return "sqlite_openwebui"
        if "blobs" in tables and "meta" in tables:
            return "sqlite_cursor_store"
        if is_sqlite_crush_schema(con, tables):
            return "sqlite_crush"
        return None
    finally:
        con.close()


def _detect_json_continue(path: Path) -> Optional[str]:
    try:
        sessions_dir = Path.home() / ".continue" / "sessions"
        path.relative_to(sessions_dir)
    except ValueError:
        return None
    try:
        with open(path) as f:
            data = json.load(f)
    except Exception:
        return None
    if isinstance(data, dict) and "history" in data:
        return "json_continue_sessions"
    return None


def get_parser(path: Path | str) -> Optional[Callable[[str], list[dict]]]:
    """Return the parse callable for a file, or None if unsupported/deferred."""
    fmt = detect_format(path)
    if fmt is None:
        return None
    return _PARSERS.get(fmt)

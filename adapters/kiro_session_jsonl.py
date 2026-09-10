"""Adapter for kiro-cli 2.x session transcripts (jsonl_kiro_session).

kiro-cli stores full agent chats at:
    ~/.kiro/sessions/<hash>/sess_<uuid>/messages.jsonl

This is kiro-cli transcript storage — not a separate IDE product. Legacy chats
through ~April 2026 may still live in ~/.local/share/kiro-cli/data.sqlite3.

Thin prompt sidecars at ~/.kiro/sessions/cli/*.history are not indexed.
"""

# Prefix scanning deliberately preserves the reviewed scratch parser contract.
# pylint: disable=duplicate-code

import hashlib
import json
from dataclasses import dataclass
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


@dataclass(frozen=True)
class CompletePrefixView:  # pylint: disable=too-many-instance-attributes
    """Canonical Kiro messages plus the byte-range commitment for one prefix."""

    messages: list[dict]
    byte_ranges: list[tuple[int, int]]
    complete_boundary: int
    prefix_sha256: str
    device: int
    inode: int
    session_meta: dict
    session_meta_digest: str | None
    raw_prefix: bytes


def _accepted_message(record: object, *, session_id: str, workspace: str) -> dict | None:
    if not isinstance(record, dict):
        return None
    payload = record.get("payload")
    if not isinstance(payload, dict):
        return None
    ptype = payload.get("type")
    if ptype in _SKIP_PAYLOAD_TYPES or ptype not in ("user", "assistant"):
        return None
    content = nonempty_stripped(payload.get("content"))
    if content is None:
        return None
    timestamp = record.get("timestamp")
    ts = timestamp if isinstance(timestamp, str) else None
    return {
        "role": ptype,
        "content": content,
        "timestamp": ts,
        "session_id": session_id,
        "workspace_directory": workspace,
    }


def _scan_prefix_records(raw: bytes, *, session_id: str, workspace: str) -> tuple[list[dict], list[tuple[int, int]]]:
    messages: list[dict] = []
    ranges: list[tuple[int, int]] = []
    offset = 0
    for line in raw.splitlines(keepends=True):
        end = offset + len(line)
        try:
            record = json.loads(line)
        except (json.JSONDecodeError, UnicodeDecodeError):
            record = None
        message = _accepted_message(record, session_id=session_id, workspace=workspace)
        if message is not None:
            messages.append(message)
            ranges.append((offset, end))
        offset = end
    return messages, ranges


def parse(filepath: str) -> list[dict]:
    """Parse a kiro-cli messages.jsonl into canonical messages."""
    session_id, workspace = session_parse_context(filepath, read_session_meta)
    messages: list[dict] = []
    for record in iter_jsonl_dicts(filepath):
        message = _accepted_message(record, session_id=session_id, workspace=workspace)
        if message is not None:
            messages.append(message)
    return messages


def parse_complete_prefix(filepath: str, *, raw: bytes | None = None) -> CompletePrefixView:
    """Return messages, accepted-record byte ranges, and prefix identity."""
    path = Path(filepath)
    session_id, workspace = session_parse_context(str(path), read_session_meta)
    if raw is None:
        data = path.read_bytes()
        stat_info = path.stat()
    else:
        data = raw
        stat_info = path.stat()
    boundary = data.rfind(b"\n") + 1
    prefix = data[:boundary]
    messages, ranges = _scan_prefix_records(
        prefix, session_id=session_id, workspace=workspace
    )
    session_json = path.parent / "session.json"
    session_meta = read_session_meta(str(path))
    meta_digest = None
    if session_json.is_file() and not session_json.is_symlink():
        meta_digest = hashlib.sha256(session_json.read_bytes()).hexdigest()
    return CompletePrefixView(
        messages=messages,
        byte_ranges=ranges,
        complete_boundary=boundary,
        prefix_sha256=hashlib.sha256(prefix).hexdigest(),
        device=int(stat_info.st_dev),
        inode=int(stat_info.st_ino),
        session_meta=session_meta,
        session_meta_digest=meta_digest,
        raw_prefix=prefix,
    )

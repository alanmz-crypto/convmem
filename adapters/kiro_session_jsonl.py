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
from pathlib import Path

from adapters.jsonl_io import (
    iter_jsonl_dicts,
    nonempty_stripped,
    session_parse_context,
)
from adapters.jsonl_prefix import (
    CompletePrefixView,
    RawLineOutcome,
    prefix_boundary,
    prefix_sha256,
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



SESSION_META_BYTE_CAP = 1024 * 1024
KIRO_SEMANTIC_META_VERSION = "kiro-complete-prefix-v2"


def _canonical_json(payload: dict) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def semantic_session_meta_digest(session_id: str, workspace_directory: str) -> str:
    body = {
        "version": KIRO_SEMANTIC_META_VERSION,
        "session_id": session_id,
        "workspace_directory": workspace_directory,
    }
    return hashlib.sha256(_canonical_json(body).encode("utf-8")).hexdigest()


def load_bounded_session_meta_bytes(session_dir: Path) -> bytes:
    session_json = session_dir / "session.json"
    if not session_json.is_file() or session_json.is_symlink():
        raise ValueError("session_meta_missing")
    raw = session_json.read_bytes()
    if len(raw) > SESSION_META_BYTE_CAP:
        raise ValueError("session_meta_too_large")
    return raw


def validated_kiro_session_identity(session_dir: Path, raw: bytes) -> tuple[str, str]:
    try:
        data = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("session_meta_malformed") from exc
    if not isinstance(data, dict):
        raise ValueError("session_meta_malformed")
    session_id = data.get("id")
    if not isinstance(session_id, str) or not session_id:
        raise ValueError("session_meta_identity_missing")
    if session_id != session_dir.name:
        raise ValueError("session_meta_identity_mismatch")
    workspaces = data.get("workspacePaths")
    workspace = ""
    if not isinstance(workspaces, list) or not workspaces:
        raise ValueError("session_meta_workspace_missing")
    first = workspaces[0]
    if not isinstance(first, str) or not first.strip():
        raise ValueError("session_meta_workspace_missing")
    workspace = first
    return session_id, workspace

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


def _scan_prefix_records(
    raw: bytes, *, session_id: str, workspace: str
) -> tuple[list[dict], list[tuple[int, int]], list[RawLineOutcome]]:
    messages: list[dict] = []
    ranges: list[tuple[int, int]] = []
    outcomes: list[RawLineOutcome] = []
    offset = 0
    for line in raw.splitlines(keepends=True):
        end = offset + len(line)
        stripped = line.strip()
        if not stripped:
            outcomes.append(RawLineOutcome(offset, end, "skipped_blank"))
            offset = end
            continue
        try:
            text = line.decode("utf-8")
        except UnicodeDecodeError:
            outcomes.append(RawLineOutcome(offset, end, "skipped_invalid_utf8"))
            offset = end
            continue
        try:
            record = json.loads(text.strip())
        except json.JSONDecodeError:
            outcomes.append(RawLineOutcome(offset, end, "skipped_malformed_json"))
            offset = end
            continue
        if not isinstance(record, dict):
            outcomes.append(RawLineOutcome(offset, end, "skipped_non_object"))
            offset = end
            continue
        message = _accepted_message(record, session_id=session_id, workspace=workspace)
        if message is None:
            outcomes.append(RawLineOutcome(offset, end, "skipped_no_message"))
            offset = end
            continue
        messages.append(message)
        ranges.append((offset, end))
        outcomes.append(
            RawLineOutcome(offset, end, "emitted", message_index=len(messages) - 1)
        )
        offset = end
    return messages, ranges, outcomes


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
    boundary = prefix_boundary(data)
    prefix = data[:boundary]
    messages, ranges, outcomes = _scan_prefix_records(
        prefix, session_id=session_id, workspace=workspace
    )
    session_dir = path.parent
    session_meta = read_session_meta(str(path))
    meta_digest = None
    meta_raw_digest = None
    try:
        raw_meta = load_bounded_session_meta_bytes(session_dir)
        session_id, workspace = validated_kiro_session_identity(session_dir, raw_meta)
        meta_raw_digest = hashlib.sha256(raw_meta).hexdigest()
        meta_digest = semantic_session_meta_digest(session_id, workspace)
        session_meta = {
            "session_id": session_id,
            "workspace_directory": workspace,
            "title": session_meta.get("title", ""),
        }
    except ValueError:
        meta_digest = None
        meta_raw_digest = None
    return CompletePrefixView(
        messages=messages,
        byte_ranges=ranges,
        line_outcomes=outcomes,
        complete_boundary=boundary,
        prefix_sha256=prefix_sha256(prefix),
        device=int(stat_info.st_dev),
        inode=int(stat_info.st_ino),
        session_meta=session_meta,
        session_meta_digest=meta_digest,
        session_meta_raw_digest=meta_raw_digest,
        raw_prefix=prefix,
    )

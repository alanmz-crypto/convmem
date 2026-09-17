"""Adapter for Codex CLI rollout transcripts (~/.codex/sessions/**/rollout-*.jsonl).

Full user/assistant turns — unlike ~/.codex/history.jsonl (prompts only).
"""

from __future__ import annotations

import json
from pathlib import Path

from adapters.jsonl_prefix import (
    CompletePrefixView,
    RawLineOutcome,
    prefix_boundary,
    prefix_sha256,
)


def is_codex_rollout_jsonl(path: Path | str) -> bool:
    p = Path(path).expanduser().resolve()
    if p.suffix != ".jsonl" or not p.name.startswith("rollout-"):
        return False
    try:
        p.relative_to((Path.home() / ".codex" / "sessions").resolve())
    except ValueError:
        return False
    return True


def _text_blocks(blocks: object) -> str:
    if not isinstance(blocks, list):
        return ""
    parts: list[str] = []
    for block in blocks:
        if not isinstance(block, dict):
            continue
        kind = block.get("type")
        if kind in ("input_text", "output_text", "text"):
            text = block.get("text")
            if isinstance(text, str) and text.strip():
                parts.append(text.strip())
    return "\n".join(parts)


def _message_from_payload(payload: dict) -> tuple[str, str] | None:
    ptype = payload.get("type")
    if ptype == "message":
        role = payload.get("role")
        if role not in ("user", "assistant"):
            return None
        content = _text_blocks(payload.get("content"))
        if content:
            return role, content
        return None
    if ptype in ("user_message", "agent_message"):
        role = "user" if ptype == "user_message" else "assistant"
        msg = payload.get("message")
        if isinstance(msg, str) and msg.strip():
            return role, msg.strip()
        return None
    return None


def _message_from_record(record: object) -> dict | None:
    if not isinstance(record, dict):
        return None
    ts = record.get("timestamp")
    timestamp = ts if isinstance(ts, str) else None
    rtype = record.get("type")
    payload = record.get("payload")
    if not isinstance(payload, dict):
        return None
    if rtype not in ("response_item", "event_msg"):
        return None
    pair = _message_from_payload(payload)
    if not pair:
        return None
    role, content = pair
    return {
        "role": role,
        "content": content,
        "timestamp": timestamp,
        "source_type": "codex_rollout",
    }


def _scan_complete_lines(
    prefix: bytes,
) -> tuple[list[dict], list[tuple[int, int]], list[RawLineOutcome]]:
    messages: list[dict] = []
    byte_ranges: list[tuple[int, int]] = []
    outcomes: list[RawLineOutcome] = []
    offset = 0
    for line in prefix.splitlines(keepends=True):
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
        message = _message_from_record(record)
        if message is None:
            outcomes.append(RawLineOutcome(offset, end, "skipped_no_message"))
            offset = end
            continue
        messages.append(message)
        byte_ranges.append((offset, end))
        outcomes.append(
            RawLineOutcome(offset, end, "emitted", message_index=len(messages) - 1)
        )
        offset = end
    return messages, byte_ranges, outcomes


def parse(filepath: str) -> list[dict]:
    """Parse a Codex rollout jsonl into canonical messages."""
    messages: list[dict] = []
    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            message = _message_from_record(record)
            if message is not None:
                messages.append(message)
    return messages


def parse_complete_prefix(filepath: str, *, raw: bytes | None = None) -> CompletePrefixView:
    """Return messages, line outcomes, and prefix identity for rollout JSONL."""
    path = Path(filepath)
    if raw is None:
        data = path.read_bytes()
        stat_info = path.stat()
    else:
        data = raw
        stat_info = path.stat()
    boundary = prefix_boundary(data)
    prefix = data[:boundary]
    messages, byte_ranges, outcomes = _scan_complete_lines(prefix)
    return CompletePrefixView(
        messages=messages,
        byte_ranges=byte_ranges,
        line_outcomes=outcomes,
        complete_boundary=boundary,
        prefix_sha256=prefix_sha256(prefix),
        device=int(stat_info.st_dev),
        inode=int(stat_info.st_ino),
        raw_prefix=prefix,
    )

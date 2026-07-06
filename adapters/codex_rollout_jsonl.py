"""Adapter for Codex CLI rollout transcripts (~/.codex/sessions/**/rollout-*.jsonl).

Full user/assistant turns — unlike ~/.codex/history.jsonl (prompts only).
"""

from __future__ import annotations

import json
from pathlib import Path


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
            if not isinstance(record, dict):
                continue

            ts = record.get("timestamp")
            timestamp = ts if isinstance(ts, str) else None
            rtype = record.get("type")
            payload = record.get("payload")
            if not isinstance(payload, dict):
                continue

            if rtype == "response_item":
                pair = _message_from_payload(payload)
                if pair:
                    role, content = pair
                    messages.append(
                        {
                            "role": role,
                            "content": content,
                            "timestamp": timestamp,
                            "source_type": "codex_rollout",
                        }
                    )
            elif rtype == "event_msg":
                pair = _message_from_payload(payload)
                if pair:
                    role, content = pair
                    messages.append(
                        {
                            "role": role,
                            "content": content,
                            "timestamp": timestamp,
                            "source_type": "codex_rollout",
                        }
                    )

    return messages

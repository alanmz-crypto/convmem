"""Adapter for Cursor agent-transcripts (jsonl_cursor format).

Source lines look like:
    {"role": "user",      "message": {"content": [{"type": "text", "text": "..."}, {"type": "tool_use", ...}]}}
    {"role": "assistant", "message": {"content": [{"type": "text", "text": "..."}]}}

Some lines carry no chat role (role is absent/None and the line holds
type/status/error fields). Those are status records, not conversation turns,
and are skipped.
"""

import json


def parse(filepath: str) -> list[dict]:
    """Parse a Cursor agent-transcript .jsonl file into canonical messages.

    Returns:
        [{"role": "user"|"assistant", "content": str, "timestamp": str|None}, ...]
    """
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

            role = record.get("role")
            if role not in ("user", "assistant"):
                continue

            message = record.get("message")
            if not isinstance(message, dict):
                continue

            blocks = message.get("content")
            if not isinstance(blocks, list):
                continue

            texts: list[str] = []
            for block in blocks:
                if not isinstance(block, dict):
                    continue
                if block.get("type") != "text":
                    continue
                text = block.get("text")
                if isinstance(text, str):
                    texts.append(text)

            content = "\n".join(texts)
            # Drop turns that contained only tool_use (no extractable text).
            if not content.strip():
                continue

            messages.append(
                {
                    "role": role,
                    "content": content,
                    "timestamp": None,
                }
            )

    return messages

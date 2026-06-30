"""Adapter for Codex CLI user prompt history (~/.codex/history.jsonl).

Each line is a user prompt only — assistant replies are NOT stored in this file.
Units indexed from here carry source_type=prompt_only so ask synthesis can treat
them differently later (v1: metadata only; ask wiring deferred).
"""

import json
from datetime import datetime, timezone
from pathlib import Path


def is_codex_history_jsonl(path: Path | str) -> bool:
    p = Path(path).expanduser().resolve()
    expected = (Path.home() / ".codex" / "history.jsonl").resolve()
    return p == expected


def parse(filepath: str) -> list[dict]:
    """Parse Codex history.jsonl into canonical user-only messages."""
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

            text = record.get("text")
            if not isinstance(text, str) or not text.strip():
                continue

            session_id = record.get("session_id")
            sid = session_id if isinstance(session_id, str) else ""

            ts_raw = record.get("ts")
            timestamp = None
            if isinstance(ts_raw, (int, float)):
                try:
                    timestamp = datetime.fromtimestamp(
                        float(ts_raw), tz=timezone.utc
                    ).isoformat()
                except (OSError, OverflowError, ValueError):
                    timestamp = None

            messages.append(
                {
                    "role": "user",
                    "content": text.strip(),
                    "timestamp": timestamp,
                    "session_id": sid,
                    "source_type": "prompt_only",
                }
            )

    return messages

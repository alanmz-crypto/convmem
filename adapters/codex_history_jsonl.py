"""Adapter for Codex CLI user prompt history (~/.codex/history.jsonl).

Each line is a user prompt only — assistant replies are NOT stored in this file.
Units indexed from here carry source_type=prompt_only so ask synthesis can treat
them differently later (v1: metadata only; ask wiring deferred).
"""

import json
from datetime import datetime, timezone
from pathlib import Path

from adapters.jsonl_prefix import (
    CompletePrefixView,
    RawLineOutcome,
    prefix_boundary,
    prefix_sha256,
)


def is_codex_history_jsonl(path: Path | str) -> bool:
    p = Path(path).expanduser().resolve()
    expected = (Path.home() / ".codex" / "history.jsonl").resolve()
    return p == expected


def _message_from_record(record: object) -> dict | None:
    if not isinstance(record, dict):
        return None
    text = record.get("text")
    if not isinstance(text, str) or not text.strip():
        return None
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
    return {
        "role": "user",
        "content": text.strip(),
        "timestamp": timestamp,
        "session_id": sid,
        "source_type": "prompt_only",
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
            message = _message_from_record(record)
            if message is not None:
                messages.append(message)
    return messages


def parse_complete_prefix(filepath: str, *, raw: bytes | None = None) -> CompletePrefixView:
    """Return messages, line outcomes, and prefix identity for history JSONL."""
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

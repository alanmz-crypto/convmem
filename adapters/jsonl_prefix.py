"""Shared complete-prefix types for incremental JSONL adapters."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class RawLineOutcome:
    """Auditable outcome for one complete raw line before the prefix boundary."""

    start: int
    end: int
    outcome: str
    message_index: int | None = None


@dataclass(frozen=True)
class CompletePrefixView:  # pylint: disable=too-many-instance-attributes
    """Canonical messages plus byte commitment for one selected prefix."""

    messages: list[dict]
    byte_ranges: list[tuple[int, int]]
    line_outcomes: list[RawLineOutcome]
    complete_boundary: int
    prefix_sha256: str
    device: int
    inode: int
    raw_prefix: bytes
    session_meta: dict | None = None
    session_meta_digest: str | None = None


def prefix_boundary(raw: bytes) -> int:
    """Byte offset after the last complete newline, or zero when absent."""
    return raw.rfind(b"\n") + 1


def prefix_sha256(prefix: bytes) -> str:
    return hashlib.sha256(prefix).hexdigest()


def scan_complete_jsonl_lines(
    prefix: bytes,
    message_from_record: Callable[[object], dict | None],
) -> tuple[list[dict], list[tuple[int, int]], list[RawLineOutcome]]:
    """Scan complete lines in a prefix and map records to emitted messages."""
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
        message = message_from_record(record)
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


def legacy_parse_jsonl_messages(  # pylint: disable=duplicate-code
    filepath: str,
    message_from_record: Callable[[object], dict | None],
) -> list[dict]:
    """Parse complete JSONL lines using legacy skip-on-error semantics."""
    messages: list[dict] = []
    with open(filepath, "r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            message = message_from_record(record)
            if message is not None:
                messages.append(message)
    return messages


def complete_prefix_view(
    filepath: str,
    *,
    raw: bytes | None,
    message_from_record: Callable[[object], dict | None],
) -> CompletePrefixView:
    """Build a complete-prefix view from on-disk bytes or an injected raw buffer."""
    path = Path(filepath)
    if raw is None:
        data = path.read_bytes()
        stat_info = path.stat()
    else:
        data = raw
        stat_info = path.stat()
    boundary = prefix_boundary(data)
    prefix = data[:boundary]
    messages, byte_ranges, outcomes = scan_complete_jsonl_lines(
        prefix, message_from_record
    )
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


def serialize_raw_line_coverage(
    outcomes: list[RawLineOutcome], prefix_hash: str
) -> dict:
    """Persist digest-bound complete-line outcomes for checkpoint audit."""
    serialized = [
        {
            "start": item.start,
            "end": item.end,
            "outcome": item.outcome,
            "message_index": item.message_index,
        }
        for item in outcomes
    ]
    digest_payload = {"prefix_sha256": prefix_hash, "outcomes": serialized}
    return {
        "prefix_sha256": prefix_hash,
        "outcomes": serialized,
        "coverage_digest": hashlib.sha256(
            json.dumps(digest_payload, sort_keys=True, separators=(",", ":")).encode(
                "utf-8"
            )
        ).hexdigest(),
    }


def complete_line_outcomes_cover_prefix(
    outcomes: list[RawLineOutcome], complete_boundary: int
) -> bool:
    """True when every complete line byte range is accounted for once."""
    if complete_boundary <= 0:
        return not outcomes
    covered = 0
    expected = 0
    for item in outcomes:
        if item.start != expected or item.end <= item.start:
            return False
        expected = item.end
        covered += item.end - item.start
    return expected == complete_boundary and covered == complete_boundary

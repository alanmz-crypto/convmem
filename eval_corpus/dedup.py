"""Last-occurrence-by-id deduplication for frozen export copies."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass
class DedupResult:
    rows: list[dict]
    input_lines: int
    unique_ids: int
    duplicates_removed: int
    after_dedup_count: int
    partial_line: bool
    malformed_line_numbers: list[int]


def dedup_export_lines(lines: list[str]) -> DedupResult:
    """Keep last occurrence of each unit id. Fail soft on mid-file malformed (collect).

    Trailing partial line: non-empty last line that fails JSON → partial_line=True.
    Callers treat partial_line as fail-closed for capture acceptance.
    """
    by_id: dict[str, dict] = {}
    order: list[str] = []
    input_lines = 0
    malformed: list[int] = []
    partial_line = False

    nonempty = list(enumerate(lines, 1))
    for idx, (lineno, raw) in enumerate(nonempty):
        line = raw.strip()
        if not line:
            continue
        input_lines += 1
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            # Trailing incomplete line is the capture failure mode.
            if idx == len(nonempty) - 1:
                partial_line = True
            else:
                malformed.append(lineno)
            continue
        if not isinstance(obj, dict):
            malformed.append(lineno)
            continue
        uid = str(obj.get("id") or "").strip()
        if not uid:
            malformed.append(lineno)
            continue
        if uid not in by_id:
            order.append(uid)
        by_id[uid] = obj

    rows = [by_id[i] for i in order]
    unique = len(rows)
    return DedupResult(
        rows=rows,
        input_lines=input_lines,
        unique_ids=unique,
        duplicates_removed=max(0, input_lines - unique),
        after_dedup_count=unique,
        partial_line=partial_line,
        malformed_line_numbers=malformed,
    )


def dedup_export_file(path: Path | str) -> DedupResult:
    text = Path(path).read_text(encoding="utf-8")
    return dedup_export_lines(text.splitlines())

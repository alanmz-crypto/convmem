"""Read-only Phase 0 inventory and readiness report helpers."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping


def build_inventory_stamp(
    *,
    code_commit: str,
    chroma_root: str | Path,
    active_count: int,
    total_count: int,
    chroma_only_ids: list[str],
    input_paths: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    """Runtime-stamped inventory — never hardcodes audit snapshot constants."""
    return {
        "utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "code_commit": code_commit,
        "chroma_root": str(Path(chroma_root).expanduser().resolve()),
        "active_unit_count": int(active_count),
        "total_unit_count": int(total_count),
        "chroma_only_count": len(chroma_only_ids),
        "chroma_only_ids": list(chroma_only_ids),
        "input_paths": dict(input_paths or {}),
        "comparison_rule_version": 1,
    }


def classify_legacy_decision_candidate(
    *,
    title: str,
    summary: str,
    approved_match: bool,
    normalized_match: bool,
    looks_like_observation: bool,
) -> str:
    if approved_match:
        return "matched governed decision"
    if normalized_match:
        return "matched governed decision"
    if looks_like_observation:
        return "likely observation"
    return "ambiguous"


def readiness_verdict(
    *,
    corruption: bool,
    unexplained_missing: bool,
    unsafe_replay: bool,
    covered_touched_reconcile: bool,
    unknown_provenance_only: bool,
) -> str:
    if corruption or unexplained_missing or unsafe_replay:
        return "FAIL"
    if covered_touched_reconcile and not unknown_provenance_only:
        return "PASS — delta capture"
    return "PARTIAL"


def write_report(path: Path, report: Mapping[str, Any]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(dict(report), ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

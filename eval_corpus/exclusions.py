"""Supersession + processed-state exclusion (Architecture Rev 1)."""

from __future__ import annotations

from pathlib import Path

from eval_corpus.classify import CLASS_FILESYSTEM, CLASS_KIRO_SNAPSHOT, classify_source_path


def _resolved(path: str) -> str:
    return str(Path(path).expanduser().resolve())


def active_excluded_paths(processed: dict) -> set[str]:
    """Paths with truthy excluded flag (ingest._path_is_excluded semantics)."""
    out: set[str] = set()
    for entry in processed.values():
        if not isinstance(entry, dict) or not entry.get("excluded"):
            continue
        ep = entry.get("path")
        if ep:
            out.add(_resolved(str(ep)))
    return out


def is_processed_excluded(unit: dict, processed: dict) -> bool:
    """Processed exclusion applies only to filesystem and kiro_snapshot units."""
    sp = str(unit.get("source_path") or "")
    cls = classify_source_path(sp)
    if cls not in (CLASS_FILESYSTEM, CLASS_KIRO_SNAPSHOT):
        return False
    if not sp:
        return False
    try:
        key = _resolved(sp)
    except OSError:
        return False
    return key in active_excluded_paths(processed)


def apply_exclusions(
    rows: list[dict],
    *,
    superseded_ids: set[str],
    processed: dict,
) -> tuple[list[dict], dict]:
    """Supersession first, then processed exclusion. Returns (kept, stats)."""
    kept: list[dict] = []
    super_n = 0
    proc_n = 0
    for row in rows:
        uid = str(row.get("id") or "")
        if uid in superseded_ids:
            super_n += 1
            continue
        if is_processed_excluded(row, processed):
            proc_n += 1
            continue
        kept.append(row)
    stats = {
        "superseded_exclusion_count": super_n,
        "source_exclusion_count": proc_n,
        "after_exclusion_count": len(kept),
    }
    return kept, stats

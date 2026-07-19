"""Immutable capture helpers (library only in R1 — do not invoke against live prod).

R2a creates directories/configs; R2b runs capture. This module is the implementation
surface for R2b, exercised hermetically in tests with temp fixtures.
"""

from __future__ import annotations

import json
import shutil
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from eval_corpus import CAPTURE_SCHEMA_VERSION
from eval_corpus.dedup import dedup_export_file
from eval_corpus.io_atomic import atomic_write_json, sha256_file
from purge_locks import export_flock_path


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def copy_under_export_lock(src: Path, dest: Path) -> str:
    """Acquire export_flock on src, copy bytes, release, return sha256 of dest."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    with export_flock_path(src):
        shutil.copy2(src, dest)
    return sha256_file(dest)


def copy_under_processed_lock(src: Path, dest: Path) -> str:
    """Acquire processed sidecar lock, copy, return sha256."""
    from ingest import _processed_lock  # local import — same lock as mutate_processed

    dest.parent.mkdir(parents=True, exist_ok=True)
    with _processed_lock(str(src)):
        if src.is_file():
            shutil.copy2(src, dest)
        else:
            atomic_write_json(dest, {})
    return sha256_file(dest)


def capture_export_and_processed(
    *,
    export_src: Path,
    processed_src: Path,
    capture_dir: Path,
    max_retries: int = 3,
) -> dict[str, Any]:
    """Copy export+processed with locks; recheck identity; retry on drift.

    Does not stop watch. Does not open live Chroma (SQLite extract is separate).
    """
    capture_dir.mkdir(parents=True, exist_ok=True)
    last_err = ""
    for attempt in range(1, max_retries + 1):
        t0 = time.perf_counter()
        export_dest = capture_dir / "knowledge_units.jsonl"
        processed_dest = capture_dir / "processed.json"
        h_export = copy_under_export_lock(export_src, export_dest)
        h_processed = (
            copy_under_processed_lock(processed_src, processed_dest)
            if processed_src.is_file()
            else ""
        )
        # Post-copy recheck of sources
        if sha256_file(export_src) != h_export:
            last_err = "export changed across copy"
            continue
        if processed_src.is_file() and sha256_file(processed_src) != h_processed:
            last_err = "processed changed across copy"
            continue
        dedup = dedup_export_file(export_dest)
        skew_ms = int((time.perf_counter() - t0) * 1000)
        report = {
            "capture_timestamp": _now(),
            "capture_schema_version": CAPTURE_SCHEMA_VERSION,
            "attempt": attempt,
            "capture_skew_ms": skew_ms,
            "input_export_path": str(export_src),
            "input_export_sha256": h_export,
            "input_processed_sha256": h_processed,
            "input_export_lines": dedup.input_lines,
            "input_export_unique_ids": dedup.unique_ids,
            "dedup_method": "last_occurrence_by_id",
            "after_dedup_count": dedup.after_dedup_count,
            "duplicates_removed": dedup.duplicates_removed,
            "partial_line": dedup.partial_line,
            "malformed_line_numbers": dedup.malformed_line_numbers,
            "status": "FAIL" if dedup.partial_line or dedup.malformed_line_numbers else "OK",
        }
        atomic_write_json(capture_dir / "capture_report.json", report)
        return report
    raise RuntimeError(f"capture failed after {max_retries} retries: {last_err}")


def load_processed_json(path: Path) -> dict:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))

"""Scratch-only capture execution for R2b v2 I6 (no production paths)."""

from __future__ import annotations

import shutil
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from eval_corpus.io_atomic import atomic_write_json, sha256_file
from eval_corpus.r2b_capture_auth import canonical_source_snapshot_sha256
from eval_corpus.r2b_v2.materialization import V2MaterializationResult
from eval_corpus.r2b_v2.scratch_isolation import assert_scratch_path, assert_scratch_source_paths


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def prepare_scratch_capture_artifacts(
    materialized: V2MaterializationResult,
) -> dict[str, Any]:
    """Copy sources into capture_dir — no completion marker yet."""
    bindings = materialized.bindings
    assert_scratch_source_paths(
        bindings.export,
        bindings.processed,
        bindings.chroma_dir,
    )
    assert_scratch_path(bindings.capture_dir, label="capture_dir")
    capture_dir = bindings.capture_dir
    capture_dir.mkdir(parents=True, exist_ok=False)

    export_dest = capture_dir / "knowledge_units.jsonl"
    shutil.copy2(bindings.export, export_dest)
    processed_state = str(bindings.source_snapshot.get("processed_state") or "absent")
    if processed_state == "present":
        shutil.copy2(bindings.processed, capture_dir / "processed.json")

    chroma_slice = {
        "collection_name": bindings.source_snapshot.get("chroma_collection_name"),
        "collection_id": bindings.source_snapshot.get("chroma_collection_id"),
        "extracted_unit_count": bindings.source_snapshot.get(
            "chroma_extracted_unit_count"
        ),
    }
    atomic_write_json(capture_dir / "chroma_extract.json", chroma_slice)

    report = {
        "capture_id": bindings.run_id,
        "capture_timestamp": _now(),
        "capture_schema_version": 1,
        "attempt": 1,
        "status": "PENDING_FINAL_SOURCE",
        "elapsed_seconds": time.perf_counter(),
    }
    atomic_write_json(capture_dir / "capture_report.json", report)
    return {"capture_report": report, "capture_dir": capture_dir}


def publish_scratch_completion_marker(
    materialized: V2MaterializationResult,
    *,
    capture_dir: Path,
) -> dict[str, Any]:
    """Write completion marker last — only after final source check passes."""
    bindings = materialized.bindings
    export_dest = capture_dir / "knowledge_units.jsonl"
    marker = {
        "marker_version": 1,
        "status": "CAPTURE_ARTIFACTS_COMPLETE",
        "capture_outcome": "COMPLETE",
        "run_id": bindings.run_id,
        "capture_id": bindings.run_id,
        "authorization_body_sha256": bindings.authorization_body_sha256,
        "source_snapshot_sha256": canonical_source_snapshot_sha256(
            bindings.source_snapshot
        ),
        "artifact_sha256": {
            "knowledge_units.jsonl": sha256_file(export_dest),
            "capture_report.json": sha256_file(capture_dir / "capture_report.json"),
        },
    }
    atomic_write_json(capture_dir / "corpus_package_manifest.json", marker)
    report_path = capture_dir / "capture_report.json"
    report = {
        "capture_id": bindings.run_id,
        "capture_timestamp": _now(),
        "capture_schema_version": 1,
        "attempt": 1,
        "status": "COMPLETE",
    }
    atomic_write_json(report_path, report)
    return {"completion_marker": marker, "capture_report": report}

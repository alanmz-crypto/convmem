"""Immutable capture helpers (library + CLI; live paths need approved run-manifest).

Capture artifacts under capture_dir are write-once completion products.
Human corpus acceptance is a separate adjudication step that never mutates
historical_spot_check.json.
"""

from __future__ import annotations

import json
import sqlite3
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from eval_corpus import CAPTURE_SCHEMA_VERSION, RECONSTRUCTION_SCHEMA_VERSION
from eval_corpus.dedup import dedup_export_file
from eval_corpus.exclusions import apply_exclusions
from eval_corpus.fingerprint import (
    corpus_fingerprint_hex,
    package_jsonl_bytes,
    package_sha256_hex,
)
from eval_corpus.io_atomic import (
    atomic_copy_file,
    atomic_write_bytes,
    atomic_write_json,
    sha256_file,
)
from eval_corpus.reconstruct import build_canonical_unit
from eval_corpus.validate import (
    OverlapPolicy,
    historical_spot_check_plan,
    validate_overlap,
)
from purge_locks import export_flock_path

UNITS_COLLECTION = "knowledge_units"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _connect_readonly(db: Path) -> sqlite3.Connection:
    if not db.is_file():
        raise FileNotFoundError(str(db))
    uri = f"file:{db.resolve().as_posix()}?mode=ro"
    return sqlite3.connect(uri, uri=True)


def extract_chroma_capture_slice(
    chroma_dir: Path | str,
    *,
    collection_name: str = UNITS_COLLECTION,
) -> dict[str, Any]:
    """One readonly SQLite transaction: superseded ids + id→document map."""
    chroma_dir = Path(chroma_dir).expanduser()
    db = chroma_dir / "chroma.sqlite3"
    conn = _connect_readonly(db)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("BEGIN")
        cur = conn.cursor()
        cur.execute(
            """
            SELECT
                e.embedding_id,
                em.key,
                em.string_value,
                em.bool_value
            FROM embeddings e
            JOIN segments s ON e.segment_id = s.id
            JOIN collections c ON s.collection = c.id
            JOIN embedding_metadata em ON em.id = e.id
            WHERE c.name = ? AND s.scope = 'METADATA'
              AND em.key IN ('chroma:document', 'superseded')
            ORDER BY e.embedding_id, em.key
            """,
            (collection_name,),
        )
        documents: dict[str, str] = {}
        superseded_ids: set[str] = set()
        seen_ids: set[str] = set()
        for row in cur.fetchall():
            eid = str(row["embedding_id"])
            seen_ids.add(eid)
            key = row["key"]
            if key == "chroma:document":
                documents[eid] = row["string_value"] or ""
            elif key == "superseded" and row["bool_value"]:
                superseded_ids.add(eid)
        conn.execute("COMMIT")
    finally:
        conn.close()

    return {
        "collection_name": collection_name,
        "ids": sorted(seen_ids),
        "count": len(seen_ids),
        "superseded_ids": sorted(superseded_ids),
        "documents": documents,
        "chroma_sqlite_sha256": sha256_file(db) if db.is_file() else "",
    }


def capture_export_and_processed(
    *,
    export_src: Path,
    processed_src: Path,
    capture_dir: Path,
    max_retries: int = 3,
) -> dict[str, Any]:
    """Legacy helper: atomic export+processed copy only (no Chroma). Prefer run_capture."""
    capture_dir = Path(capture_dir)
    capture_dir.mkdir(parents=True, exist_ok=True)
    last_err = ""
    for attempt in range(1, max_retries + 1):
        h_export = copy_under_export_lock(Path(export_src), capture_dir / "knowledge_units.jsonl")
        h_processed = (
            copy_under_processed_lock(Path(processed_src), capture_dir / "processed.json")
            if Path(processed_src).is_file()
            else ""
        )
        if sha256_file(export_src) != h_export:
            last_err = "export changed across copy"
            continue
        if Path(processed_src).is_file() and sha256_file(processed_src) != h_processed:
            last_err = "processed changed across copy"
            continue
        dedup = dedup_export_file(capture_dir / "knowledge_units.jsonl")
        report = {
            "capture_timestamp": _now(),
            "capture_schema_version": CAPTURE_SCHEMA_VERSION,
            "attempt": attempt,
            "input_export_sha256": h_export,
            "input_processed_sha256": h_processed,
            "partial_line": dedup.partial_line,
            "malformed_line_numbers": dedup.malformed_line_numbers,
            "status": "FAIL" if dedup.partial_line or dedup.malformed_line_numbers else "OK",
        }
        atomic_write_json(capture_dir / "capture_report.json", report)
        return report
    raise RuntimeError(f"capture failed after {max_retries} retries: {last_err}")


def copy_under_export_lock(src: Path, dest: Path) -> str:
    dest.parent.mkdir(parents=True, exist_ok=True)
    with export_flock_path(src):
        return atomic_copy_file(src, dest)


def copy_under_processed_lock(src: Path, dest: Path) -> str:
    from ingest import _processed_lock

    dest.parent.mkdir(parents=True, exist_ok=True)
    with _processed_lock(str(src)):
        if src.is_file():
            return atomic_copy_file(src, dest)
        atomic_write_json(dest, {})
        return sha256_file(dest)


def load_processed_json(path: Path) -> dict:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def build_corpus_package(
    *,
    capture_dir: Path,
    chroma_slice: dict[str, Any],
    package_name: str = "corpus_package.jsonl",
) -> dict[str, Any]:
    """Dedup → exclude → reconstruct → fingerprint; write package atomically."""
    capture_dir = Path(capture_dir)
    export_path = capture_dir / "knowledge_units.jsonl"
    processed_path = capture_dir / "processed.json"
    dedup = dedup_export_file(export_path)
    if dedup.partial_line or dedup.malformed_line_numbers:
        raise RuntimeError(
            "refusing package build: export has partial/malformed lines "
            f"(partial={dedup.partial_line} malformed={dedup.malformed_line_numbers})"
        )
    processed = load_processed_json(processed_path)
    superseded = set(chroma_slice.get("superseded_ids") or [])
    kept, excl_stats = apply_exclusions(
        dedup.rows, superseded_ids=superseded, processed=processed
    )
    units = [build_canonical_unit(row) for row in kept]
    fingerprint = corpus_fingerprint_hex(units)
    package_bytes = package_jsonl_bytes(units)
    package_path = capture_dir / package_name
    atomic_write_bytes(package_path, package_bytes)
    package_sha = package_sha256_hex(units)
    manifest = {
        "capture_schema_version": CAPTURE_SCHEMA_VERSION,
        "reconstruction_schema_version": RECONSTRUCTION_SCHEMA_VERSION,
        "unit_count": len(units),
        "unit_corpus_fingerprint": fingerprint,
        "package_sha256": package_sha,
        "package_path": package_name,
        "exclusion_stats": excl_stats,
        "chroma_superseded_count": len(superseded),
        "built_at": _now(),
    }
    atomic_write_json(capture_dir / "corpus_package_manifest.json", manifest)
    return {
        "units": units,
        "manifest": manifest,
        "package_path": str(package_path),
        "dedup": dedup,
    }


def run_capture(
    *,
    export_src: Path,
    processed_src: Path,
    capture_dir: Path,
    chroma_dir: Path,
    max_retries: int = 3,
    capture_id: str | None = None,
    overlap_policy: OverlapPolicy = "canonical",
) -> dict[str, Any]:
    """Capture: Chroma required; post-Chroma recheck; validation wired.

    Default overlap_policy=canonical (Architecture Rev 1 40/30/30).
    policy=fixture is for hermetic tests only — never exposed on the CLI.
    Status is CAPTURE_COMPLETE / FAILED / UNRESOLVED — never corpus-accepted.
    """
    export_src = Path(export_src)
    processed_src = Path(processed_src)
    capture_dir = Path(capture_dir)
    chroma_dir = Path(chroma_dir)
    if not (chroma_dir / "chroma.sqlite3").is_file():
        raise FileNotFoundError(
            f"chroma_dir required with chroma.sqlite3 present: {chroma_dir}"
        )

    capture_dir.mkdir(parents=True, exist_ok=True)
    capture_id = capture_id or f"cap_{uuid.uuid4().hex[:12]}"
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
        if sha256_file(export_src) != h_export:
            last_err = "export changed across copy"
            continue
        if processed_src.is_file() and sha256_file(processed_src) != h_processed:
            last_err = "processed changed across copy"
            continue

        chroma_slice = extract_chroma_capture_slice(chroma_dir)
        # Post-Chroma recheck — entire capture retries on drift
        if sha256_file(export_src) != h_export or sha256_file(export_dest) != h_export:
            last_err = "export drifted after chroma extract"
            continue
        if processed_src.is_file():
            if sha256_file(processed_src) != h_processed or sha256_file(processed_dest) != h_processed:
                last_err = "processed drifted after chroma extract"
                continue

        atomic_write_json(
            capture_dir / "chroma_extract.json",
            {
                "collection_name": chroma_slice["collection_name"],
                "count": chroma_slice["count"],
                "superseded_ids": chroma_slice["superseded_ids"],
                "ids": chroma_slice["ids"],
                "chroma_sqlite_sha256": chroma_slice["chroma_sqlite_sha256"],
            },
        )
        atomic_write_json(capture_dir / "chroma_documents.json", chroma_slice["documents"])

        try:
            package = build_corpus_package(
                capture_dir=capture_dir, chroma_slice=chroma_slice
            )
        except RuntimeError as exc:
            last_err = str(exc)
            report = {
                "capture_id": capture_id,
                "capture_timestamp": _now(),
                "capture_schema_version": CAPTURE_SCHEMA_VERSION,
                "attempt": attempt,
                "status": "FAILED",
                "error": last_err,
            }
            atomic_write_json(capture_dir / "capture_report.json", report)
            return {
                "capture_report": report,
                "chroma_slice": chroma_slice,
                "package_manifest": None,
                "units": [],
            }

        units = package["units"]
        overlap = validate_overlap(
            units,
            chroma_slice["documents"],
            capture_id=capture_id,
            policy=overlap_policy,
        )
        atomic_write_json(capture_dir / "overlap_validation.json", overlap)

        chroma_ids = set(chroma_slice["ids"])
        # Spot-check plan uses raw export IDs absent from Chroma.
        dedup = package["dedup"]
        raw_export_ids = [str(r.get("id") or "") for r in dedup.rows if r.get("id")]
        absent_from_chroma = sorted(set(raw_export_ids) - chroma_ids)
        spot = historical_spot_check_plan(
            absent_from_chroma, capture_id=capture_id, n=20
        )
        atomic_write_json(capture_dir / "historical_spot_check.json", spot)

        overall = overlap.get("overall")
        if overall == "FAILED":
            status = "FAILED"
        elif overall == "UNRESOLVED":
            status = "UNRESOLVED"
        elif package["dedup"].partial_line or package["dedup"].malformed_line_numbers:
            status = "FAILED"
        else:
            status = "CAPTURE_COMPLETE"

        skew_ms = int((time.perf_counter() - t0) * 1000)
        report = {
            "capture_id": capture_id,
            "capture_timestamp": _now(),
            "capture_schema_version": CAPTURE_SCHEMA_VERSION,
            "attempt": attempt,
            "capture_skew_ms": skew_ms,
            "input_export_path": str(export_src),
            "input_export_sha256": h_export,
            "input_processed_sha256": h_processed,
            "input_export_lines": package["dedup"].input_lines,
            "input_export_unique_ids": package["dedup"].unique_ids,
            "dedup_method": "last_occurrence_by_id",
            "after_dedup_count": package["dedup"].after_dedup_count,
            "duplicates_removed": package["dedup"].duplicates_removed,
            "partial_line": package["dedup"].partial_line,
            "malformed_line_numbers": package["dedup"].malformed_line_numbers,
            "unit_corpus_fingerprint": package["manifest"]["unit_corpus_fingerprint"],
            "package_sha256": package["manifest"]["package_sha256"],
            "unit_count": package["manifest"]["unit_count"],
            "chroma_extract": True,
            "overlap_overall": overall,
            "spot_check_sample_n": len(spot.get("sample_ids") or []),
            "status": status,
            "corpus_accepted": False,
        }
        atomic_write_json(capture_dir / "capture_report.json", report)
        return {
            "capture_report": report,
            "chroma_slice": chroma_slice,
            "package_manifest": package["manifest"],
            "units": units,
            "overlap": overlap,
            "spot_check": spot,
        }

    raise RuntimeError(f"capture failed after {max_retries} retries: {last_err}")

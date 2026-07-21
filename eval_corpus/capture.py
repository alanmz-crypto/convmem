"""Immutable capture helpers (library + CLI; live paths need approved run-manifest).

Capture artifacts under capture_dir are write-once completion products.
Human corpus acceptance is a separate adjudication step that never mutates
historical_spot_check.json.
"""

from __future__ import annotations

import hashlib
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
from eval_corpus.run_manifest import path_is_eval_root
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


def compute_chroma_capture_identity(
    chroma_dir: Path | str,
    *,
    collection_name: str = UNITS_COLLECTION,
) -> dict[str, Any]:
    """Canonical Chroma identity: sorted-ID hash + content-bound slice hash.

    Shares one read-only transaction and canonicalization with extract.
    Used for pre-approval snapshot, capture verification, and post-capture
    drift check.
    """
    chroma_dir = Path(chroma_dir).expanduser()
    db = chroma_dir / "chroma.sqlite3"
    conn = _connect_readonly(db)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("BEGIN")
        cur = conn.cursor()

        cur.execute("SELECT id FROM collections WHERE name = ?", (collection_name,))
        row = cur.fetchone()
        if row is None:
            raise ValueError(f"collection {collection_name!r} not found")
        collection_id = str(row["id"])

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

        records: dict[str, dict[str, Any]] = {}
        for row in cur.fetchall():
            eid = str(row["embedding_id"])
            if eid not in records:
                records[eid] = {
                    "id": eid,
                    "document_present": False,
                    "document": None,
                    "superseded": False,
                }
            key = row["key"]
            if key == "chroma:document":
                records[eid]["document_present"] = True
                records[eid]["document"] = (
                    row["string_value"] if row["string_value"] is not None else ""
                )
            elif key == "superseded" and row["bool_value"]:
                records[eid]["superseded"] = True

        conn.execute("COMMIT")
    finally:
        conn.close()

    for eid in records:
        if "\r" in eid or "\n" in eid:
            raise ValueError(f"Chroma ID contains CR/LF: {eid!r}")

    sorted_ids = sorted(records.keys(), key=lambda x: x.encode("utf-8"))

    id_hash_input = b"".join(
        eid.encode("utf-8") + b"\n" for eid in sorted_ids
    )
    sorted_id_hash = hashlib.sha256(id_hash_input).hexdigest()

    slice_records = []
    for eid in sorted_ids:
        r = records[eid]
        doc_hex = (
            r["document"].encode("utf-8").hex() if r["document_present"] else None
        )
        slice_records.append(
            {
                "document_present": r["document_present"],
                "document_utf8_hex": doc_hex,
                "id_utf8_hex": eid.encode("utf-8").hex(),
                "superseded": r["superseded"],
            }
        )

    slice_obj = {
        "collection_id": collection_id,
        "collection_name": collection_name,
        "records": slice_records,
    }
    slice_canonical = json.dumps(
        slice_obj, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )
    capture_slice_sha256 = hashlib.sha256(
        slice_canonical.encode("utf-8")
    ).hexdigest()

    return {
        "collection_name": collection_name,
        "collection_id": collection_id,
        "extracted_unit_count": len(records),
        "sorted_id_hash": sorted_id_hash,
        "capture_slice_sha256": capture_slice_sha256,
    }


def recompute_source_snapshot(
    *,
    export: Path,
    processed: Path,
    chroma_dir: Path,
    collection_name: str = UNITS_COLLECTION,
) -> dict[str, Any]:
    """Recompute a fresh source_snapshot from live sources."""
    export_sha = sha256_file(export)

    if Path(processed).is_file():
        processed_state = "present"
        processed_sha = sha256_file(processed)
    else:
        processed_state = "absent"
        processed_sha = None

    identity = compute_chroma_capture_identity(
        chroma_dir, collection_name=collection_name
    )

    return {
        "export_sha256": export_sha,
        "processed_state": processed_state,
        "processed_sha256": processed_sha,
        "chroma_collection_name": identity["collection_name"],
        "chroma_collection_id": identity["collection_id"],
        "chroma_extracted_unit_count": identity["extracted_unit_count"],
        "chroma_sorted_id_hash": identity["sorted_id_hash"],
        "chroma_capture_slice_sha256": identity["capture_slice_sha256"],
        "snapshot_timestamp": datetime.now(timezone.utc).isoformat(),
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
    write_legacy_manifest: bool = True,
) -> dict[str, Any]:
    """Dedup -> exclude -> reconstruct -> fingerprint; write package atomically.

    When write_legacy_manifest=False (R2b), the mid-pipeline
    corpus_package_manifest.json is not written — the expanded completion
    marker is written last by the R2b capture path instead.
    """
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
    if write_legacy_manifest:
        atomic_write_json(capture_dir / "corpus_package_manifest.json", manifest)
    return {
        "units": units,
        "manifest": manifest,
        "package_path": str(package_path),
        "dedup": dedup,
    }


def r2b_artifact_inventory(*, processed_state: str) -> list[str]:
    """Sorted artifact inventory for R2b completion marker (VERIFY / tests)."""
    base = [
        "capture_report.json",
        "chroma_documents.json",
        "chroma_extract.json",
        "corpus_package.jsonl",
        "corpus_package_manifest.json",
        "historical_spot_check.json",
        "knowledge_units.jsonl",
        "overlap_validation.json",
    ]
    if processed_state == "present":
        base.append("processed.json")
    return sorted(base)


def _r2b_artifact_inventory(*, processed_state: str) -> list[str]:
    return r2b_artifact_inventory(processed_state=processed_state)


def _r2b_artifact_sha256(capture_dir: Path, *, processed_state: str) -> dict[str, str]:
    """SHA-256 of every required non-marker artifact."""
    names = [
        "knowledge_units.jsonl",
        "chroma_extract.json",
        "chroma_documents.json",
        "corpus_package.jsonl",
        "overlap_validation.json",
        "historical_spot_check.json",
        "capture_report.json",
    ]
    if processed_state == "present":
        names.append("processed.json")
    return {name: sha256_file(capture_dir / name) for name in sorted(names)}


def _run_r2b_capture(  # pylint: disable=too-many-locals
    *,
    export_src: Path,
    processed_src: Path,
    capture_dir: Path,
    chroma_dir: Path,
    r2b_capability: Any,
) -> dict[str, Any]:
    """R2b capture path: single attempt, marker-last, capability-gated."""
    from eval_corpus.r2b_capture_auth import (
        canonical_source_snapshot_sha256,
        materialize_r2b_write_authorization,
    )

    bindings = materialize_r2b_write_authorization(
        r2b_capability,
        snapshot_recompute_fn=recompute_source_snapshot,
    )

    run_id = bindings.run_id
    capture_id = run_id
    overlap_policy: OverlapPolicy = "canonical"
    spot_check_n = 20

    capture_dir.mkdir(parents=True, exist_ok=False)

    t0 = time.perf_counter()
    export_dest = capture_dir / "knowledge_units.jsonl"
    processed_dest = capture_dir / "processed.json"

    h_export = copy_under_export_lock(export_src, export_dest)
    processed_state = "present" if processed_src.is_file() else "absent"
    h_processed = ""
    if processed_state == "present":
        h_processed = copy_under_processed_lock(processed_src, processed_dest)

    if sha256_file(export_src) != h_export:
        return _failed_r2b_result(capture_id, "export changed across copy")
    if processed_state == "present" and sha256_file(processed_src) != h_processed:
        return _failed_r2b_result(capture_id, "processed changed across copy")

    chroma_slice = extract_chroma_capture_slice(chroma_dir)
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
    atomic_write_json(
        capture_dir / "chroma_documents.json", chroma_slice["documents"]
    )

    if sha256_file(export_src) != h_export or sha256_file(export_dest) != h_export:
        return _failed_r2b_result(capture_id, "export drifted after chroma extract")
    if processed_state == "present":
        if (
            sha256_file(processed_src) != h_processed
            or sha256_file(processed_dest) != h_processed
        ):
            return _failed_r2b_result(
                capture_id, "processed drifted after chroma extract"
            )

    try:
        package = build_corpus_package(
            capture_dir=capture_dir,
            chroma_slice=chroma_slice,
            write_legacy_manifest=False,
        )
    except RuntimeError as exc:
        report = {
            "capture_id": capture_id,
            "capture_timestamp": _now(),
            "capture_schema_version": CAPTURE_SCHEMA_VERSION,
            "attempt": 1,
            "status": "FAILED",
            "error": str(exc),
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

    dedup = package["dedup"]
    raw_export_ids = [
        str(r.get("id") or "") for r in dedup.rows if r.get("id")
    ]
    absent_from_chroma = sorted(set(raw_export_ids) - set(chroma_slice["ids"]))
    spot = historical_spot_check_plan(
        absent_from_chroma, capture_id=capture_id, n=spot_check_n
    )
    atomic_write_json(capture_dir / "historical_spot_check.json", spot)

    overall = overlap.get("overall")
    if overall == "FAILED" or dedup.partial_line or dedup.malformed_line_numbers:
        status = "FAILED"
    elif overall == "UNRESOLVED":
        status = "UNRESOLVED"
    else:
        status = "CAPTURE_COMPLETE"

    skew_ms = int((time.perf_counter() - t0) * 1000)
    report = {
        "capture_id": capture_id,
        "capture_timestamp": _now(),
        "capture_schema_version": CAPTURE_SCHEMA_VERSION,
        "attempt": 1,
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

    if status == "FAILED":
        return {
            "capture_report": report,
            "chroma_slice": chroma_slice,
            "package_manifest": package["manifest"],
            "units": units,
            "overlap": overlap,
            "spot_check": spot,
        }

    if sha256_file(export_src) != h_export:
        report["status"] = "FAILED"
        report["error"] = "post_capture_source_drift: export"
        atomic_write_json(capture_dir / "capture_report.json", report)
        return {
            "capture_report": report,
            "chroma_slice": chroma_slice,
            "package_manifest": package["manifest"],
            "units": units,
            "overlap": overlap,
            "spot_check": spot,
        }
    if processed_state == "present" and sha256_file(processed_src) != h_processed:
        report["status"] = "FAILED"
        report["error"] = "post_capture_source_drift: processed"
        atomic_write_json(capture_dir / "capture_report.json", report)
        return {
            "capture_report": report,
            "chroma_slice": chroma_slice,
            "package_manifest": package["manifest"],
            "units": units,
            "overlap": overlap,
            "spot_check": spot,
        }

    marker = {
        "marker_version": 1,
        "status": "CAPTURE_ARTIFACTS_COMPLETE",
        "capture_outcome": status,
        "run_id": run_id,
        "capture_id": capture_id,
        "authorization_body_sha256": bindings.authorization_body_sha256,
        "source_snapshot_sha256": canonical_source_snapshot_sha256(
            bindings.source_snapshot
        ),
        "processed_state": processed_state,
        "package_sha256": package["manifest"]["package_sha256"],
        "unit_corpus_fingerprint": package["manifest"]["unit_corpus_fingerprint"],
        "unit_count": package["manifest"]["unit_count"],
        "artifact_inventory": _r2b_artifact_inventory(
            processed_state=processed_state
        ),
        "artifact_sha256": _r2b_artifact_sha256(
            capture_dir, processed_state=processed_state
        ),
    }
    atomic_write_json(capture_dir / "corpus_package_manifest.json", marker)

    return {
        "capture_report": report,
        "chroma_slice": chroma_slice,
        "package_manifest": package["manifest"],
        "units": units,
        "overlap": overlap,
        "spot_check": spot,
        "completion_marker": marker,
    }


def _failed_r2b_result(capture_id: str, error: str) -> dict[str, Any]:
    """Construct a FAILED R2b result without writing a marker."""
    return {
        "capture_report": {
            "capture_id": capture_id,
            "capture_timestamp": _now(),
            "capture_schema_version": CAPTURE_SCHEMA_VERSION,
            "attempt": 1,
            "status": "FAILED",
            "error": error,
        },
        "chroma_slice": None,
        "package_manifest": None,
        "units": [],
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
    r2b_capability: Any = None,
) -> dict[str, Any]:
    """Capture: Chroma required; post-Chroma recheck; validation wired.

    Default overlap_policy=canonical (Architecture Rev 1 40/30/30).
    policy=fixture is for hermetic tests only — never exposed on the CLI.
    Status is CAPTURE_COMPLETE / FAILED / UNRESOLVED — never corpus-accepted.

    When r2b_capability is provided (or capture_dir is under eval root),
    the R2b write path is used: single attempt, marker-last, capability-gated.
    """
    export_src = Path(export_src)
    processed_src = Path(processed_src)
    capture_dir = Path(capture_dir)
    chroma_dir = Path(chroma_dir)
    if not (chroma_dir / "chroma.sqlite3").is_file():
        raise FileNotFoundError(
            f"chroma_dir required with chroma.sqlite3 present: {chroma_dir}"
        )

    is_eval_root = path_is_eval_root(capture_dir)
    if r2b_capability is not None or is_eval_root:
        if r2b_capability is None:
            raise PermissionError(
                "eval-root capture requires R2b capability"
            )
        return _run_r2b_capture(
            export_src=export_src,
            processed_src=processed_src,
            capture_dir=capture_dir,
            chroma_dir=chroma_dir,
            r2b_capability=r2b_capability,
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
        if sha256_file(export_src) != h_export or sha256_file(export_dest) != h_export:
            last_err = "export drifted after chroma extract"
            continue
        if processed_src.is_file():
            if (
                sha256_file(processed_src) != h_processed
                or sha256_file(processed_dest) != h_processed
            ):
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
        atomic_write_json(
            capture_dir / "chroma_documents.json", chroma_slice["documents"]
        )

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
        dedup = package["dedup"]
        raw_export_ids = [
            str(r.get("id") or "") for r in dedup.rows if r.get("id")
        ]
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

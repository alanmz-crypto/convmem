"""R2b capability-gated capture write path (single attempt, marker-last)."""

from __future__ import annotations

import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from eval_corpus import CAPTURE_SCHEMA_VERSION
from eval_corpus import capture as capture_lib
from eval_corpus.io_atomic import atomic_write_json, sha256_file
from eval_corpus.r2b_capture_auth import (
    canonical_source_snapshot_sha256,
    compare_source_snapshots,
    materialize_r2b_write_authorization,
)


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _require_caller_paths_match_bindings(
    *,
    export_src: Path,
    processed_src: Path,
    capture_dir: Path,
    chroma_dir: Path,
    bindings: Any,
) -> None:
    """Refuse caller paths that are not byte-equal to the approved bindings."""
    pairs = (
        ("export", export_src, bindings.export),
        ("processed", processed_src, bindings.processed),
        ("capture_dir", capture_dir, bindings.capture_dir),
        ("chroma_dir", chroma_dir, bindings.chroma_dir),
    )
    for name, caller, approved in pairs:
        if str(Path(caller)) != str(Path(approved)):
            raise PermissionError(
                f"R2b caller {name} is not bound to approved path: "
                f"caller={caller!s}, approved={approved!s}"
            )


def _snapshot_mismatch(
    approved: dict[str, Any],
    *,
    export_sha: str,
    processed_state: str,
    processed_sha: str | None,
    chroma_identity: dict[str, Any],
) -> str | None:
    """Return an error string if captured state diverges from approved snapshot."""
    if export_sha != approved.get("export_sha256"):
        return "captured export_sha256 does not match approved source_snapshot"
    if processed_state != approved.get("processed_state"):
        return "captured processed_state does not match approved source_snapshot"
    if processed_state == "present":
        if processed_sha != approved.get("processed_sha256"):
            return (
                "captured processed_sha256 does not match approved source_snapshot"
            )
    elif processed_sha is not None:
        return "processed_sha256 must be null when processed_state is absent"
    checks = (
        ("chroma_collection_name", chroma_identity.get("collection_name")),
        ("chroma_collection_id", chroma_identity.get("collection_id")),
        ("chroma_extracted_unit_count", chroma_identity.get("extracted_unit_count")),
        ("chroma_sorted_id_hash", chroma_identity.get("sorted_id_hash")),
        (
            "chroma_capture_slice_sha256",
            chroma_identity.get("capture_slice_sha256"),
        ),
    )
    for key, actual in checks:
        if actual != approved.get(key):
            return f"captured {key} does not match approved source_snapshot"
    return None


def _failed_result(
    capture_id: str,
    error: str,
    *,
    capture_dir: Path | None = None,
) -> dict[str, Any]:
    """FAILED R2b result; persist capture_report.json when capture_dir exists."""
    report = {
        "capture_id": capture_id,
        "capture_timestamp": _now(),
        "capture_schema_version": CAPTURE_SCHEMA_VERSION,
        "attempt": 1,
        "status": "FAILED",
        "error": error,
    }
    if capture_dir is not None and Path(capture_dir).is_dir():
        atomic_write_json(Path(capture_dir) / "capture_report.json", report)
    return {
        "capture_report": report,
        "chroma_slice": None,
        "package_manifest": None,
        "units": [],
    }


def _artifact_sha256(capture_dir: Path, *, processed_state: str) -> dict[str, str]:
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


def _copy_verify_and_extract(  # pylint: disable=too-many-locals
    *,
    capture_id: str,
    capture_dir: Path,
    sources: tuple[Path, Path, Path],
    approved: dict[str, Any],
    collection_name: str,
    processed_state: str,
) -> dict[str, Any]:
    """Copy sources, verify against approved snapshot, write Chroma extract."""
    export_src, processed_src, chroma_dir = sources
    export_dest = capture_dir / "knowledge_units.jsonl"
    processed_dest = capture_dir / "processed.json"

    # Attribute access so hermetic tests can patch capture.copy_under_export_lock.
    h_export = capture_lib.copy_under_export_lock(export_src, export_dest)
    h_processed: str | None = None
    early_error: str | None = None
    if processed_state == "present":
        if not processed_src.is_file():
            early_error = (
                "approved processed_state is present but processed source missing"
            )
        else:
            h_processed = capture_lib.copy_under_processed_lock(
                processed_src, processed_dest
            )
    elif processed_src.is_file():
        early_error = (
            "approved processed_state is absent but processed source exists"
        )

    if early_error is None and sha256_file(export_src) != h_export:
        early_error = "export changed across copy"
    if (
        early_error is None
        and processed_state == "present"
        and sha256_file(processed_src) != h_processed
    ):
        early_error = "processed changed across copy"

    if early_error is None:
        chroma_identity = capture_lib.compute_chroma_capture_identity(
            chroma_dir, collection_name=collection_name
        )
        early_error = _snapshot_mismatch(
            approved,
            export_sha=h_export,
            processed_state=processed_state,
            processed_sha=h_processed,
            chroma_identity=chroma_identity,
        )

    if early_error is not None:
        return _failed_result(capture_id, early_error, capture_dir=capture_dir)

    chroma_slice = capture_lib.extract_chroma_capture_slice(
        chroma_dir, collection_name=collection_name
    )
    capture_lib.write_chroma_slice_artifacts(capture_dir, chroma_slice)

    if sha256_file(export_src) != h_export or sha256_file(export_dest) != h_export:
        early_error = "export drifted after chroma extract"
    elif processed_state == "present" and (
        sha256_file(processed_src) != h_processed
        or sha256_file(processed_dest) != h_processed
    ):
        early_error = "processed drifted after chroma extract"
    else:
        post_identity = capture_lib.compute_chroma_capture_identity(
            chroma_dir, collection_name=collection_name
        )
        mismatch = _snapshot_mismatch(
            approved,
            export_sha=h_export,
            processed_state=processed_state,
            processed_sha=h_processed,
            chroma_identity=post_identity,
        )
        if mismatch:
            early_error = f"post-extract {mismatch}"

    if early_error is not None:
        return _failed_result(capture_id, early_error, capture_dir=capture_dir)

    return {
        "h_export": h_export,
        "h_processed": h_processed,
        "chroma_slice": chroma_slice,
    }


def _post_package_drift_error(
    *,
    sources: tuple[Path, Path, Path],
    digests: tuple[str, str | None],
    processed_state: str,
    collection_name: str,
    approved: dict[str, Any],
) -> str | None:
    """Return a drift error string, or None if live sources still match approval."""
    export_src, processed_src, chroma_dir = sources
    h_export, h_processed = digests
    if sha256_file(export_src) != h_export:
        return "post_capture_source_drift: export"
    if processed_state == "present" and sha256_file(processed_src) != h_processed:
        return "post_capture_source_drift: processed"
    try:
        live = capture_lib.recompute_source_snapshot(
            export=export_src,
            processed=processed_src,
            chroma_dir=chroma_dir,
            collection_name=collection_name,
        )
        compare_source_snapshots(approved, live)
    except PermissionError as exc:
        return f"pre_marker_source_drift: {exc}"
    return None


def run_r2b_capture(  # pylint: disable=too-many-locals
    *,
    export_src: Path,
    processed_src: Path,
    capture_dir: Path,
    chroma_dir: Path,
    r2b_capability: Any,
) -> dict[str, Any]:
    """R2b capture path: single attempt, marker-last, capability-gated."""
    bindings = materialize_r2b_write_authorization(
        r2b_capability,
        snapshot_recompute_fn=capture_lib.recompute_source_snapshot,
    )
    _require_caller_paths_match_bindings(
        export_src=export_src,
        processed_src=processed_src,
        capture_dir=capture_dir,
        chroma_dir=chroma_dir,
        bindings=bindings,
    )

    export_src = Path(bindings.export)
    processed_src = Path(bindings.processed)
    capture_dir = Path(bindings.capture_dir)
    chroma_dir = Path(bindings.chroma_dir)
    approved = bindings.source_snapshot
    collection_name = str(approved["chroma_collection_name"])
    processed_state = str(approved["processed_state"])

    run_id = bindings.run_id
    capture_id = run_id

    capture_dir.mkdir(parents=True, exist_ok=False)

    t0 = time.perf_counter()
    prepared = _copy_verify_and_extract(
        capture_id=capture_id,
        capture_dir=capture_dir,
        sources=(export_src, processed_src, chroma_dir),
        approved=approved,
        collection_name=collection_name,
        processed_state=processed_state,
    )
    if prepared.get("chroma_slice") is None:
        return prepared
    h_export = prepared["h_export"]
    h_processed = prepared["h_processed"]
    chroma_slice = prepared["chroma_slice"]

    try:
        package = capture_lib.build_corpus_package(
            capture_dir=capture_dir,
            chroma_slice=chroma_slice,
            write_legacy_manifest=False,
        )
    except RuntimeError as exc:
        return capture_lib.package_build_failed_result(
            capture_dir=capture_dir,
            capture_id=capture_id,
            attempt=1,
            chroma_slice=chroma_slice,
            error=str(exc),
        )

    partial = capture_lib.complete_capture_validation(
        capture_dir=capture_dir,
        chroma_slice=chroma_slice,
        package=package,
        capture_id=capture_id,
        attempt=1,
        t0=t0,
        export_src=export_src,
        h_export=h_export,
        h_processed=h_processed or "",
        overlap_policy="canonical",
        spot_check_n=20,
    )
    report = partial["capture_report"]
    status = report["status"]
    if status == "FAILED":
        return partial

    drift_error = _post_package_drift_error(
        sources=(export_src, processed_src, chroma_dir),
        digests=(h_export, h_processed),
        processed_state=processed_state,
        collection_name=collection_name,
        approved=approved,
    )
    if drift_error is not None:
        report["status"] = "FAILED"
        report["error"] = drift_error
        atomic_write_json(capture_dir / "capture_report.json", report)
        return partial

    marker = {
        "marker_version": 1,
        "status": "CAPTURE_ARTIFACTS_COMPLETE",
        "capture_outcome": status,
        "run_id": run_id,
        "capture_id": capture_id,
        "authorization_body_sha256": bindings.authorization_body_sha256,
        "source_snapshot_sha256": canonical_source_snapshot_sha256(approved),
        "processed_state": processed_state,
        "package_sha256": package["manifest"]["package_sha256"],
        "unit_corpus_fingerprint": package["manifest"]["unit_corpus_fingerprint"],
        "unit_count": package["manifest"]["unit_count"],
        "artifact_inventory": capture_lib.r2b_artifact_inventory(
            processed_state=processed_state
        ),
        "artifact_sha256": _artifact_sha256(
            capture_dir, processed_state=processed_state
        ),
    }
    atomic_write_json(capture_dir / "corpus_package_manifest.json", marker)
    partial["completion_marker"] = marker
    return partial

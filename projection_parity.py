"""Read-only export-to-Chroma projection completeness accounting."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable, Iterable
from pathlib import Path

from chroma_store import is_superseded
from eval_corpus.classify import (
    CLASS_FILESYSTEM,
    CLASS_KIRO_SNAPSHOT,
    CLASS_OTHER_LOGICAL,
    classify_source_path,
)


def entity_key(row: dict) -> str:
    """Return the durable comparison key for an exported or active unit."""
    ledger_id = str(row.get("ledger_id") or "").strip()
    if ledger_id:
        return f"ledger:{ledger_id}"
    unit_id = str(row.get("id") or "").strip()
    return f"id:{unit_id}" if unit_id else ""


def _source_key(source_path: str) -> str:
    source_path = str(source_path or "").strip()
    source_class = classify_source_path(source_path)
    if source_class not in (CLASS_FILESYSTEM, CLASS_KIRO_SNAPSHOT):
        return source_path
    return str(Path(source_path).expanduser().resolve())


def _processed_by_source(processed: dict) -> dict[str, list[dict]]:
    by_source: dict[str, list[dict]] = defaultdict(list)
    for file_hash, entry in processed.items():
        if not isinstance(entry, dict) or not entry.get("path"):
            continue
        row = dict(entry)
        row["file_hash"] = file_hash
        by_source[_source_key(str(entry["path"]))].append(row)
    return by_source


def _safe_exists(path: str) -> bool:
    try:
        return Path(path).expanduser().exists()
    except OSError:
        return False


def _disposition(
    source_path: str,
    *,
    entries: list[dict],
    missing_keys: set[str],
    required_keys: set[str],
    path_exists: Callable[[str], bool],
) -> tuple[str, bool | None]:
    if any(entry.get("excluded") for entry in entries):
        return "processed_excluded", None
    if any(int(entry.get("units") or 0) > 0 for entry in entries):
        return "processed_nonzero_missing_active_projection", None
    if entries:
        return "processed_zero_units", None

    source_class = classify_source_path(source_path)
    if missing_keys & required_keys:
        return "required_ledger_projection_gap", None
    if source_class == CLASS_KIRO_SNAPSHOT:
        return "historical_snapshot_without_processed_claim", path_exists(source_path)
    if source_class == CLASS_FILESYSTEM:
        exists = path_exists(source_path)
        suffix = "existing" if exists else "missing"
        return f"historical_{suffix}_source_without_processed_claim", exists
    if source_class == CLASS_OTHER_LOGICAL or source_path.startswith("ledger:"):
        return "historical_logical_source_without_processed_claim", None
    if source_path:
        return "historical_relative_source_without_processed_claim", path_exists(source_path)
    return "unclassified", None


def build_projection_parity_report(
    export_rows: Iterable[dict],
    active_rows: Iterable[dict],
    processed: dict,
    *,
    required_ledger_ids: Iterable[str] = (),
    path_exists: Callable[[str], bool] = _safe_exists,
) -> dict:
    """Classify export-only entities without treating history as active loss.

    Ledger rows compare by durable ``ledger_id`` because a canonical upsert may
    change its Chroma UUID. Transcript-derived units compare by their stable
    Chroma ID. The historical export remains diagnostic authority; a positive
    processed entry is the active projection claim for filesystem sources.
    """
    export_by_key: dict[str, dict] = {}
    for row in export_rows:
        key = entity_key(row)
        if key:
            export_by_key[key] = dict(row)

    active_by_key: dict[str, dict] = {}
    active_source_counts: dict[str, int] = defaultdict(int)
    for row in active_rows:
        if is_superseded(row):
            continue
        key = entity_key(row)
        if key:
            active_by_key[key] = dict(row)
        active_source_counts[_source_key(str(row.get("source_path") or ""))] += 1

    missing_by_source: dict[str, set[str]] = defaultdict(set)
    for key, row in export_by_key.items():
        if key not in active_by_key:
            missing_by_source[str(row.get("source_path") or "")].add(key)

    processed_by_source = _processed_by_source(processed)
    required_ids = {str(item).strip() for item in required_ledger_ids if str(item).strip()}
    required_keys = {f"ledger:{item}" for item in required_ids}
    active_ledger_ids = {
        key.removeprefix("ledger:")
        for key in active_by_key
        if key.startswith("ledger:")
    }
    missing_required = sorted(required_ids - active_ledger_ids)

    paths: list[dict] = []
    for source_path, missing_keys in sorted(missing_by_source.items()):
        source_key = _source_key(source_path)
        active_count = active_source_counts.get(source_key, 0)
        if active_count:
            continue
        entries = processed_by_source.get(source_key, [])
        disposition, exists = _disposition(
            source_path,
            entries=entries,
            missing_keys=missing_keys,
            required_keys=required_keys,
            path_exists=path_exists,
        )
        expected_units = max(
            (int(entry.get("units") or 0) for entry in entries if not entry.get("excluded")),
            default=0,
        )
        paths.append(
            {
                "source_path": source_path,
                "source_class": classify_source_path(source_path),
                "export_only_entity_count": len(missing_keys),
                "export_only_entity_keys": sorted(missing_keys),
                "active_unit_count": 0,
                "processed_expected_units": expected_units,
                "processed_entries": entries,
                "path_exists": exists,
                "disposition": disposition,
            }
        )

    processed_gaps = [
        row
        for row in paths
        if row["disposition"] == "processed_nonzero_missing_active_projection"
    ]
    unclassified = [row for row in paths if row["disposition"] == "unclassified"]
    metrics = {
        "export_entity_count": len(export_by_key),
        "active_entity_count": len(active_by_key),
        "export_only_entity_count": len(set(export_by_key) - set(active_by_key)),
        "export_only_path_count": len(missing_by_source),
        "export_only_paths_without_active_units_count": len(paths),
        "export_only_entities_in_zero_active_paths_count": sum(
            int(row["export_only_entity_count"]) for row in paths
        ),
        "processed_nonzero_paths_without_active_units_count": len(processed_gaps),
        "processed_nonzero_expected_units_without_active_units_count": sum(
            int(row["processed_expected_units"]) for row in processed_gaps
        ),
        "required_ledger_ids_missing_count": len(missing_required),
        "unclassified_export_only_paths_count": len(unclassified),
    }
    gates = {
        key: metrics[key]
        for key in (
            "processed_nonzero_paths_without_active_units_count",
            "processed_nonzero_expected_units_without_active_units_count",
            "required_ledger_ids_missing_count",
            "unclassified_export_only_paths_count",
        )
    }
    return {
        "schema": "convmem/projection-parity-v1",
        "metrics": metrics,
        "gates": {**gates, "pass": all(value == 0 for value in gates.values())},
        "required_ledger_ids": sorted(required_ids),
        "missing_required_ledger_ids": missing_required,
        "paths_without_active_units": paths,
    }

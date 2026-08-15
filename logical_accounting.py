"""CG-2 namespaced logical identity and truthful health accounting.

Semantic comparison uses ``(owner_digest, collection_kind, logical_id)``.
Physical Chroma ids remain diagnostic provenance only.  Retained inactive
generations are inventory, not active drift.  Invalid pointer/manifest authority
is reported separately from membership percentages.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from enum import Enum
from typing import Any

from chroma_readonly import collection_metadata_rows
from chroma_store import SUMMARIES, UNITS, is_superseded
from file_generation_store import FILE_SCOPE, STABLE_SCOPE
from serving_authority import (
    FrozenAuthorityVector,
    OwnerAuthorityMode,
    generation_root_for_cfg,
    resolve_frozen_authority_vector,
)
from source_reconciler import (
    ReconciliationBudget,
    pending_owner_work,
    reconciliation_staleness_seconds,
    reconciliation_state_path,
)

STABLE_OWNER_SENTINEL = "stable-governed"
SCHEMA = "convmem/logical-accounting-v1"


class PhysicalRowClass(str, Enum):
    """Diagnostic classification for one persisted Chroma row."""

    SERVING_STABLE = "serving_stable"
    SERVING_ACTIVE_GENERATION = "serving_active_generation"
    SUPERSEDED = "superseded"
    RETAINED_INACTIVE = "retained_inactive"
    ABANDONED = "abandoned"
    WRONG_GENERATION = "wrong_generation"
    WRONG_OWNER = "wrong_owner"
    UNCLASSIFIED = "unclassified"


@dataclass(frozen=True)
class NamespacedLogicalKey:
    owner_digest: str
    collection_kind: str
    logical_id: str

    def encode(self) -> str:
        return f"{self.owner_digest}|{self.collection_kind}|{self.logical_id}"


def logical_id_from_metadata(meta: Mapping[str, Any]) -> str:
    ledger_id = str(meta.get("ledger_id") or "").strip()
    if ledger_id:
        return ledger_id
    logical_id = str(meta.get("logical_id") or "").strip()
    if logical_id:
        return logical_id
    return str(meta.get("id") or "").strip()


def namespaced_logical_key(
    meta: Mapping[str, Any], collection_kind: str
) -> NamespacedLogicalKey | None:
    logical_id = logical_id_from_metadata(meta)
    if not logical_id:
        return None
    scope = str(meta.get("generation_scope") or "")
    if scope == STABLE_SCOPE or not meta.get("owner_digest"):
        owner = STABLE_OWNER_SENTINEL
    else:
        owner = str(meta.get("owner_digest") or "")
    return NamespacedLogicalKey(owner, collection_kind, logical_id)


def membership_ratio(intersection: int, denominator: int) -> float | None:
    """Empty-set convention: ``None`` when the denominator is zero."""

    if denominator == 0:
        return None
    return intersection / denominator


def manifest_namespaced_keys(manifest: Mapping[str, Any]) -> set[NamespacedLogicalKey]:
    owner = str(manifest["owner_digest"])
    keys: set[NamespacedLogicalKey] = set()
    for collection_name, raw_spec in dict(manifest.get("collections") or {}).items():
        spec = dict(raw_spec)
        for row in dict(spec.get("rows") or {}).values():
            logical_id = str(dict(row).get("logical_id") or "")
            if logical_id:
                keys.add(NamespacedLogicalKey(owner, str(collection_name), logical_id))
    return keys


def projection_key_index(
    metas: Iterable[Mapping[str, Any]], collection_kind: str
) -> dict[NamespacedLogicalKey, list[str]]:
    index: dict[NamespacedLogicalKey, list[str]] = defaultdict(list)
    for meta in metas:
        key = namespaced_logical_key(meta, collection_kind)
        if key is None:
            continue
        physical_id = str(meta.get("id") or "")
        if physical_id:
            index[key].append(physical_id)
    return dict(index)


def build_membership_metrics(
    expected: set[NamespacedLogicalKey],
    observed: set[NamespacedLogicalKey],
) -> dict[str, Any]:
    intersection = expected & observed
    missing = sorted(key.encode() for key in (expected - observed))
    unexpected = sorted(key.encode() for key in (observed - expected))
    return {
        "expected_count": len(expected),
        "observed_count": len(observed),
        "intersection_count": len(intersection),
        "missing_keys": missing,
        "unexpected_keys": unexpected,
        "missing_count": len(missing),
        "unexpected_count": len(unexpected),
        "completeness": membership_ratio(len(intersection), len(expected)),
        "purity": membership_ratio(len(intersection), len(observed)),
    }


def discover_file_generations_by_owner(
    chroma_dir: str, collection_name: str = UNITS
) -> dict[str, set[str]]:
    by_owner: dict[str, set[str]] = defaultdict(set)
    for meta in collection_metadata_rows(chroma_dir, collection_name):
        if str(meta.get("generation_scope") or "") != FILE_SCOPE:
            continue
        owner = str(meta.get("owner_digest") or "")
        generation = str(meta.get("generation_id") or "")
        if owner and generation:
            by_owner[owner].add(generation)
    return dict(by_owner)


def classify_physical_row(
    meta: Mapping[str, Any],
    *,
    collection_kind: str,
    active_generations: Mapping[str, str],
    previous_generations: Mapping[str, str],
    known_generations_by_owner: Mapping[str, set[str]],
) -> PhysicalRowClass:
    if collection_kind == UNITS and is_superseded(meta):
        return PhysicalRowClass.SUPERSEDED
    scope = str(meta.get("generation_scope") or "")
    if scope in (STABLE_SCOPE, ""):
        return PhysicalRowClass.SERVING_STABLE
    if scope != FILE_SCOPE:
        return PhysicalRowClass.UNCLASSIFIED
    owner = str(meta.get("owner_digest") or "")
    generation = str(meta.get("generation_id") or "")
    if not owner or not generation:
        return PhysicalRowClass.UNCLASSIFIED
    active = active_generations.get(owner)
    previous = previous_generations.get(owner)
    protected = {value for value in (active, previous) if value}
    known = known_generations_by_owner.get(owner, set())
    abandoned = known - set(protected)
    if active == generation:
        return PhysicalRowClass.SERVING_ACTIVE_GENERATION
    if previous == generation:
        return PhysicalRowClass.RETAINED_INACTIVE
    if generation in abandoned:
        return PhysicalRowClass.ABANDONED
    if active and generation != active:
        return PhysicalRowClass.WRONG_GENERATION
    if owner not in active_generations and owner in known_generations_by_owner:
        return PhysicalRowClass.WRONG_OWNER
    return PhysicalRowClass.UNCLASSIFIED


def build_physical_inventory_report(
    chroma_dir: str,
    *,
    active_generations: Mapping[str, str] | None = None,
    previous_generations: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    active_generations = dict(active_generations or {})
    previous_generations = dict(previous_generations or {})
    known_by_owner = discover_file_generations_by_owner(chroma_dir, UNITS)
    counts: dict[str, int] = defaultdict(int)
    units_counts: dict[str, int] = defaultdict(int)
    summaries_counts: dict[str, int] = defaultdict(int)
    duplicate_keys: list[str] = []
    for collection_kind in (UNITS, SUMMARIES):
        bucket = units_counts if collection_kind == UNITS else summaries_counts
        index = projection_key_index(
            collection_metadata_rows(chroma_dir, collection_kind), collection_kind
        )
        for key, physical_ids in index.items():
            if len(physical_ids) > 1:
                duplicate_keys.append(key.encode())
        for meta in collection_metadata_rows(chroma_dir, collection_kind):
            classification = classify_physical_row(
                meta,
                collection_kind=collection_kind,
                active_generations=active_generations,
                previous_generations=previous_generations,
                known_generations_by_owner=known_by_owner,
            )
            counts[classification.value] += 1
            bucket[classification.value] += 1
    units_serving = (
        units_counts[PhysicalRowClass.SERVING_STABLE.value]
        + units_counts[PhysicalRowClass.SERVING_ACTIVE_GENERATION.value]
    )
    summaries_serving = (
        summaries_counts[PhysicalRowClass.SERVING_STABLE.value]
        + summaries_counts[PhysicalRowClass.SERVING_ACTIVE_GENERATION.value]
    )
    units_physical = sum(units_counts.values()) - units_counts[
        PhysicalRowClass.SUPERSEDED.value
    ]
    summaries_physical = sum(summaries_counts.values())
    amplification = None
    combined_serving = units_serving + summaries_serving
    combined_physical = units_physical + summaries_physical
    if combined_serving:
        amplification = combined_physical / combined_serving
    return {
        "counts_by_class": dict(counts),
        "duplicate_logical_keys": sorted(duplicate_keys),
        "duplicate_logical_count": len(duplicate_keys),
        "serving_units_count": units_serving,
        "serving_summaries_count": summaries_serving,
        "physical_units_count": units_physical,
        "physical_summaries_count": summaries_physical,
        "serving_row_count": combined_serving,
        "physical_row_count": combined_physical,
        "storage_amplification_ratio": amplification,
    }


def build_owner_logical_projection_report(
    manifest: Mapping[str, Any],
    chroma_dir: str,
) -> dict[str, Any]:
    owner = str(manifest["owner_digest"])
    generation = str(manifest["generation_id"])
    expected = manifest_namespaced_keys(manifest)
    observed_keys: set[NamespacedLogicalKey] = set()
    duplicate_keys: list[str] = []
    wrong_generation_keys: list[str] = []
    wrong_owner_keys: list[str] = []
    for collection_name in dict(manifest.get("collections") or {}):
        rows = collection_metadata_rows(chroma_dir, str(collection_name))
        active_rows = [
            meta
            for meta in rows
            if str(meta.get("generation_scope") or "") == FILE_SCOPE
            and str(meta.get("owner_digest") or "") == owner
            and str(meta.get("generation_id") or "") == generation
        ]
        index = projection_key_index(active_rows, str(collection_name))
        for key, physical_ids in index.items():
            if len(physical_ids) > 1:
                duplicate_keys.append(key.encode())
            observed_keys.add(key)
        for meta in rows:
            if str(meta.get("generation_scope") or "") != FILE_SCOPE:
                continue
            row_owner = str(meta.get("owner_digest") or "")
            row_generation = str(meta.get("generation_id") or "")
            key = namespaced_logical_key(meta, str(collection_name))
            if key is None:
                continue
            if row_owner == owner and row_generation != generation:
                wrong_generation_keys.append(key.encode())
            elif row_owner and row_owner != owner and key in expected:
                wrong_owner_keys.append(key.encode())
    membership = build_membership_metrics(expected, observed_keys)
    return {
        "owner_digest": owner,
        "generation_id": generation,
        "membership": membership,
        "duplicate_logical_keys": sorted(duplicate_keys),
        "wrong_generation_keys": sorted(set(wrong_generation_keys)),
        "wrong_owner_keys": sorted(set(wrong_owner_keys)),
        "gate_pass": (
            membership["missing_count"] == 0
            and membership["unexpected_count"] == 0
            and not duplicate_keys
            and not wrong_generation_keys
            and not wrong_owner_keys
        ),
    }


def build_authority_evidence(vector: FrozenAuthorityVector) -> dict[str, Any]:
    owners: list[dict[str, Any]] = []
    for digest, state in sorted(vector.by_owner.items()):
        owners.append(
            {
                "owner_digest": digest,
                "mode": state.mode.value,
                "generation_id": state.generation_id,
                "owner_key": state.owner_key,
                "servable": state.is_servable(),
            }
        )
    return {
        "legacy_global": vector.legacy_global,
        "resolution_attempts": vector.resolution_attempts,
        "owners": owners,
        "retired_count": sum(
            1 for state in vector.by_owner.values()
            if state.mode == OwnerAuthorityMode.RETIRED
        ),
        "quarantined_count": sum(
            1 for state in vector.by_owner.values()
            if state.mode == OwnerAuthorityMode.QUARANTINED
        ),
        "fenced_count": sum(
            1 for state in vector.by_owner.values()
            if state.mode == OwnerAuthorityMode.FENCED_NO_POINTER
        ),
    }


def build_reconciliation_diagnostics(cfg: Mapping[str, Any]) -> dict[str, Any]:
    budget = ReconciliationBudget()
    index = cfg.get("index") if isinstance(cfg.get("index"), dict) else {}
    processed_log = index.get("processed_log")
    if not processed_log:
        return {
            "pending_owner_count": 0,
            "dirty_scope_count": 0,
            "staleness_seconds": None,
            "max_reconciliation_staleness": budget.max_reconciliation_staleness,
            "fresh": True,
        }
    stale = reconciliation_staleness_seconds(cfg)
    pending = pending_owner_work(cfg)
    state_path = reconciliation_state_path(cfg)
    dirty_scopes: list[str] = []
    if state_path.exists():
        try:
            import json

            payload = json.loads(state_path.read_text(encoding="utf-8"))
            dirty_scopes = list(payload.get("dirty_scopes") or [])
        except (OSError, json.JSONDecodeError):
            dirty_scopes = []
    fresh = stale is not None and stale <= budget.max_reconciliation_staleness
    return {
        "pending_owner_count": len(pending),
        "dirty_scope_count": len(dirty_scopes),
        "staleness_seconds": stale,
        "max_reconciliation_staleness": budget.max_reconciliation_staleness,
        "fresh": fresh and not dirty_scopes,
    }


def build_corpus_view_stats(cfg: Mapping[str, Any]) -> dict[str, Any]:
    """Serving versus physical counts and CG-2 operational diagnostics."""

    chroma_dir = str((cfg.get("index") or {})["chroma_dir"])
    vector = resolve_frozen_authority_vector(cfg)
    physical = build_physical_inventory_report(
        chroma_dir,
        active_generations=vector.active_generations(),
        previous_generations=vector.previous_generations(),
    )
    owner_reports: list[dict[str, Any]] = []
    authority_failures: list[str] = []
    generation_root = generation_root_for_cfg(cfg)
    from file_generation_pointer import (
        GenerationQualificationError,
        load_manifest_reference,
        read_unqualified_pointer,
    )

    for digest, state in vector.by_owner.items():
        if state.mode != OwnerAuthorityMode.GENERATIONAL:
            continue
        pointer = read_unqualified_pointer(generation_root, digest)
        if pointer is None:
            authority_failures.append(f"{digest}: generational without pointer")
            continue
        try:
            ref = load_manifest_reference(
                generation_root,
                manifest_filename=str(pointer["manifest_filename"]),
                expected_sha256=str(pointer["manifest_file_hash"]),
            )
            owner_reports.append(
                build_owner_logical_projection_report(ref.manifest, chroma_dir)
            )
        except GenerationQualificationError as exc:
            authority_failures.append(f"{digest}: {exc}")

    return {
        "schema": SCHEMA,
        "view": {
            "serving_units": physical["serving_units_count"],
            "serving_summaries": physical["serving_summaries_count"],
            "physical_units": physical["physical_units_count"],
            "physical_summaries": physical["physical_summaries_count"],
        },
        "physical_inventory": physical,
        "authority": build_authority_evidence(vector),
        "reconciliation": build_reconciliation_diagnostics(cfg),
        "owner_projection_reports": owner_reports,
        "authority_failures": authority_failures,
        "logical_projection_gate_pass": (
            not authority_failures
            and all(report.get("gate_pass") for report in owner_reports)
        ),
    }

"""CG-2 mixed-mode backend characterization and proof gates.

Measures authority safety, authorized cardinality, and retrieval quality as
separate properties against an authority-clean control.  Physical deletion,
online GC, and internal queue surgery remain disabled in this slice.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from chroma_store import ChromaStore, UNITS
from file_generation_store import FileGenerationStore
from file_generation_validate import chroma_sequence_positions
from logical_accounting import build_physical_inventory_report
from mixed_mode_control import build_authority_clean_control
from mixed_mode_retrieval import (
    MixedModeCandidateBudget,
    assert_pinned_chroma_version,
    dedupe_namespaced_logical_rows,
    filter_authorized_rows,
    query_units_mixed_ann,
    verify_authority_safety,
)
from serving_authority import FrozenAuthorityVector

PROOF_SCHEMA = "convmem/mixed-mode-proof-v1"
PHYSICAL_DELETION_DISABLED = True


def characterize_chroma_storage(chroma_dir: str | Path) -> dict[str, Any]:
    chroma_path = Path(chroma_dir).expanduser()
    sqlite_path = chroma_path / "chroma.sqlite3"
    sequence = chroma_sequence_positions(chroma_path)
    sqlite_bytes = sqlite_path.stat().st_size if sqlite_path.is_file() else 0
    return {
        "chroma_version": assert_pinned_chroma_version(),
        "sqlite_bytes": sqlite_bytes,
        "sequence_positions": sequence,
        "physical_deletion_disabled": PHYSICAL_DELETION_DISABLED,
    }


def measure_authorized_cardinality(
    mixed_rows: list[dict[str, Any]],
    control_rows: list[dict[str, Any]],
    *,
    requested_k: int,
) -> dict[str, Any]:
    mixed_count = len(mixed_rows)
    control_count = len(control_rows)
    underfill = control_count >= requested_k and mixed_count < requested_k
    mismatch = control_count != mixed_count
    return {
        "requested_k": requested_k,
        "mixed_authorized_count": mixed_count,
        "control_count": control_count,
        "underfill": underfill,
        "count_mismatch": mismatch,
        "pass": not underfill and not mismatch,
    }


def measure_retrieval_quality(
    mixed_rows: list[dict[str, Any]],
    control_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    mixed_ids = [str(row.get("id")) for row in mixed_rows]
    control_ids = [str(row.get("id")) for row in control_rows]
    overlap = [row_id for row_id in mixed_ids if row_id in set(control_ids)]
    rank_divergence = [
        index
        for index, row_id in enumerate(mixed_ids)
        if index >= len(control_ids) or control_ids[index] != row_id
    ]
    return {
        "overlap_count": len(overlap),
        "mixed_ids": mixed_ids,
        "control_ids": control_ids,
        "rank_divergence_positions": rank_divergence,
        "exact_rank_match": not rank_divergence,
    }


def retention_inventory_report(
    chroma_dir: str | Path,
    vector: FrozenAuthorityVector,
) -> dict[str, Any]:
    physical = build_physical_inventory_report(
        str(chroma_dir),
        active_generations=vector.active_generations(),
        previous_generations=vector.previous_generations(),
    )
    counts = physical.get("counts_by_class") or {}
    return {
        "active_generations": vector.active_generations(),
        "previous_generations": vector.previous_generations(),
        "retained_inactive_count": int(counts.get("retained_inactive", 0)),
        "abandoned_count": int(counts.get("abandoned", 0)),
        "serving_units": int(physical.get("serving_units_count", 0)),
        "physical_units": int(physical.get("physical_units_count", 0)),
        "physical_deletion_disabled": PHYSICAL_DELETION_DISABLED,
    }


def run_mixed_mode_proof(
    chroma_dir: str | Path,
    control_chroma_dir: str | Path,
    embedding: list[float],
    top_k: int,
    *,
    vector: FrozenAuthorityVector,
    budget: MixedModeCandidateBudget | None = None,
) -> dict[str, Any]:
    """Compare mixed-mode ANN retrieval against an authority-clean control."""

    budget = budget or MixedModeCandidateBudget()
    source_path = Path(chroma_dir).expanduser()
    control_path = Path(control_chroma_dir).expanduser()

    control_info = build_authority_clean_control(
        source_path,
        control_path,
        active_generations=vector.active_generations,
        previous_generations=vector.previous_generations,
    )

    with FileGenerationStore(
        source_path,
        active_generations=vector.active_generations,
        previous_generations=vector.previous_generations,
    ) as mixed_store:
        mixed_rows = query_units_mixed_ann(
            mixed_store,
            embedding,
            top_k,
            vector=vector,
            budget=budget,
        )

    with ChromaStore(str(control_path), create_collections=False) as control_store:
        control_rows = control_store.query_units(embedding, top_k)

    safety = verify_authority_safety(mixed_rows, vector)
    cardinality = measure_authorized_cardinality(
        mixed_rows, control_rows, requested_k=top_k
    )
    quality = measure_retrieval_quality(mixed_rows, control_rows)
    storage = characterize_chroma_storage(source_path)
    retention = retention_inventory_report(source_path, vector)

    gates = {
        "authority_safety_pass": safety["pass"],
        "authorized_cardinality_pass": cardinality["pass"],
        "physical_deletion_disabled": PHYSICAL_DELETION_DISABLED,
    }

    return {
        "schema": PROOF_SCHEMA,
        "chroma_version": storage["chroma_version"],
        "control": control_info,
        "authority_safety": safety,
        "authorized_cardinality": cardinality,
        "retrieval_quality": quality,
        "storage": storage,
        "retention": retention,
        "gates": gates,
        "gate_pass": all(
            gates[key]
            for key in (
                "authority_safety_pass",
                "authorized_cardinality_pass",
                "physical_deletion_disabled",
            )
        ),
    }


def query_control_exact_cosine(
    store: FileGenerationStore,
    embedding: list[float],
    top_k: int,
    *,
    collection_name: str = UNITS,
) -> list[dict[str, Any]]:
    """Secondary diagnostic: exact cosine over the authority-filtered active set."""

    rows = store._get_rows(collection_name, include_embeddings=True)  # pylint: disable=protected-access
    query_vector = store._validated_embedding(embedding, label="query")  # pylint: disable=protected-access
    scored: list[dict[str, Any]] = []
    for row in rows:
        row_embedding = store._validated_embedding(  # pylint: disable=protected-access
            row.get("embedding"),
            label=str(row["id"]),
            expected_dimension=len(query_vector),
        )
        scored.append(
            {
                "id": row["id"],
                "metadata": row["metadata"],
                "document": row["document"],
                "distance": store._cosine_distance(  # pylint: disable=protected-access
                    query_vector, row_embedding, label=str(row["id"])
                ),
            }
        )
    scored.sort(key=lambda item: (float(item["distance"]), str(item["id"])))
    return scored[:top_k]

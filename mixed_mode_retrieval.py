"""CG-2 mixed-mode Chroma retrieval with bounded candidate expansion.

Queries the mixed physical collection through authority predicates derived from
the frozen vector, widens ANN candidate pools within a budget, and rejects
inactive rows after retrieval.  No raw top-k over the full collection.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from chroma_store import UNITS, is_superseded
from file_generation_store import FILE_SCOPE, STABLE_SCOPE, FileGenerationStore
from logical_accounting import namespaced_logical_key
from serving_authority import FrozenAuthorityVector, ServingAuthorityError

PINNED_CHROMA_VERSION = "1.5.9"


class MixedModeCardinalityError(ServingAuthorityError):
    """Mixed-mode retrieval could not return the authorized cardinality within budget."""


class MixedModeAuthorityError(ServingAuthorityError):
    """A mixed-mode result row violated the frozen authority vector."""


@dataclass(frozen=True)
class MixedModeCandidateBudget:
    expansion_factor: int = 4
    max_candidates: int = 256
    max_attempts: int = 6


def assert_pinned_chroma_version() -> str:
    import chromadb

    version = str(chromadb.__version__)
    if version != PINNED_CHROMA_VERSION:
        raise RuntimeError(
            f"mixed-mode proof requires chromadb=={PINNED_CHROMA_VERSION}, got {version}"
        )
    return version


def _flatten_query_result(result: Mapping[str, Any]) -> list[dict[str, Any]]:
    ids = list(result.get("ids") or [[]])[0]
    documents = list(result.get("documents") or [[]])[0]
    metadatas = list(result.get("metadatas") or [[]])[0]
    distances = list(result.get("distances") or [[]])[0]
    rows: list[dict[str, Any]] = []
    for index, physical_id in enumerate(ids):
        meta = dict(metadatas[index] if index < len(metadatas) else {})
        meta["id"] = physical_id
        row: dict[str, Any] = {
            "id": physical_id,
            "metadata": meta,
            "document": documents[index] if index < len(documents) else "",
        }
        if index < len(distances):
            row["distance"] = distances[index]
        rows.append(row)
    return rows


def _authority_where_filter(
    store: FileGenerationStore, active: Mapping[str, str]
) -> dict[str, Any]:
    clauses = store._active_where_clauses(dict(active))  # pylint: disable=protected-access
    group = clauses[0]
    if len(group) == 1:
        return group[0]
    return {"$or": group}


def _row_is_authorized(
    meta: Mapping[str, Any], vector: FrozenAuthorityVector
) -> bool:
    if is_superseded(meta):
        return False
    scope = str(meta.get("generation_scope") or "")
    if scope == STABLE_SCOPE or scope == "":
        return True
    if scope != FILE_SCOPE:
        return False
    owner = str(meta.get("owner_digest") or "")
    generation = str(meta.get("generation_id") or "")
    active = vector.active_generations()
    return bool(owner and generation and active.get(owner) == generation)


def filter_authorized_rows(
    rows: list[dict[str, Any]], vector: FrozenAuthorityVector
) -> list[dict[str, Any]]:
    authorized: list[dict[str, Any]] = []
    for row in rows:
        meta = row.get("metadata") or {}
        if _row_is_authorized(meta, vector):
            authorized.append(row)
    return authorized


def dedupe_namespaced_logical_rows(
    rows: list[dict[str, Any]], collection_kind: str = UNITS
) -> list[dict[str, Any]]:
    seen: set[str] = set()
    out: list[dict[str, Any]] = []
    for row in rows:
        meta = row.get("metadata") or {}
        key = namespaced_logical_key(meta, collection_kind)
        encoded = key.encode() if key is not None else str(row.get("id"))
        if encoded in seen:
            continue
        seen.add(encoded)
        out.append(row)
    return out


def verify_authority_safety(
    rows: list[dict[str, Any]], vector: FrozenAuthorityVector
) -> dict[str, Any]:
    violations = [
        str(row.get("id"))
        for row in rows
        if not _row_is_authorized(row.get("metadata") or {}, vector)
    ]
    return {
        "violation_ids": violations,
        "pass": not violations,
    }


def query_units_mixed_ann(
    store: FileGenerationStore,
    embedding: list[float],
    top_k: int,
    *,
    vector: FrozenAuthorityVector,
    budget: MixedModeCandidateBudget | None = None,
    collection_name: str = UNITS,
) -> list[dict[str, Any]]:
    """ANN query over a mixed physical collection under frozen authority."""

    assert_pinned_chroma_version()
    if top_k <= 0:
        return []
    budget = budget or MixedModeCandidateBudget()
    active = vector.active_generations()
    col = store._store._collection(collection_name)  # pylint: disable=protected-access
    where = _authority_where_filter(store, active)
    n_candidates = top_k
    authorized: list[dict[str, Any]] = []
    physical_total = col.count()
    attempts = 0
    while attempts < budget.max_attempts and n_candidates <= budget.max_candidates:
        attempts += 1
        n_fetch = min(max(n_candidates, top_k), max(physical_total, 1), budget.max_candidates)
        result = col.query(
            query_embeddings=[embedding],
            n_results=n_fetch,
            where=where,
            include=["metadatas", "documents", "distances"],
        )
        rows = filter_authorized_rows(_flatten_query_result(result), vector)
        authorized = dedupe_namespaced_logical_rows(rows, collection_name)
        if len(authorized) >= top_k:
            return authorized[:top_k]
        if n_fetch >= physical_total:
            break
        n_candidates = min(
            max(n_candidates * budget.expansion_factor, top_k),
            budget.max_candidates,
        )
    if len(authorized) < top_k:
        raise MixedModeCardinalityError(
            f"mixed-mode underfill: authorized={len(authorized)} requested={top_k} "
            f"after {attempts} expansion attempts (max_candidates={budget.max_candidates})"
        )
    return authorized[:top_k]

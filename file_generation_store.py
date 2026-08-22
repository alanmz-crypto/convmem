"""Hermetic copy-on-write storage facade for file generations.

This module is deliberately opt-in.  It does not change ``ChromaStore`` or any
production read path.  Rows staged with ``generation_scope == "file"`` become
visible only when the injected active-generation resolver selects their owner
and generation.  Stable/governed fixtures use ``generation_scope == "stable"``
and retain their existing physical ids.

The active predicate is passed to Chroma itself for every get operation.
Generation-aware vector reads then rerank the exact active rows in-process, so
inactive rows cannot consume vector top-k slots before filtering.
"""

from __future__ import annotations

import math
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Self

from chroma_readonly import collection_metadata_rows
from chroma_store import SUMMARIES, UNITS, ChromaStore, is_superseded
from file_generation_contract import (
    GenerationContractError,
    canonical_hash,
    validate_generation_manifest,
)

FILE_SCOPE = "file"
STABLE_SCOPE = "stable"


class GenerationValidationError(RuntimeError):
    """A staged generation does not exactly match its immutable manifest."""


# StagedRow is an explicit immutable schema, not mutable object state.
# pylint: disable=too-many-instance-attributes
@dataclass(frozen=True)
class StagedRow:
    """One hermetic Chroma row with explicit logical/physical identity."""

    collection_name: str
    physical_id: str
    logical_id: str
    document: str
    embedding: list[float]
    metadata: Mapping[str, Any] = field(default_factory=dict)
    generation_scope: str = FILE_SCOPE
    owner_digest: str | None = None
    generation_id: str | None = None


class GenerationBackpressureError(RuntimeError):
    """Staging is refused until CG-2 explicitly disposes abandoned state."""

    state = "DEGRADED-SAFE"


class GenerationReadError(RuntimeError):
    """An active generation row cannot be safely ranked for a vector read."""


def _and_where(*clauses: dict[str, Any] | None) -> dict[str, Any] | None:
    present = [clause for clause in clauses if clause]
    if not present:
        return None
    if len(present) == 1:
        return present[0]
    return {"$and": present}


# pylint: disable=too-many-instance-attributes,too-many-public-methods
class FileGenerationStore:
    """Temporary-Chroma generation staging and mediated read facade.

    ``active_generations`` returns an owner-digest -> generation-id snapshot.
    Pointer/manifest validation is intentionally owned by the pointer module;
    this class only consumes an already-qualified active view.
    """

    def __init__(
        self,
        chroma_dir: str | Path,
        *,
        active_generations: Callable[[], Mapping[str, str]],
        previous_generations: Callable[[], Mapping[str, str]] | None = None,
        retained_baselines: Callable[[], Mapping[str, set[str]]] | None = None,
    ) -> None:
        self.chroma_dir = str(Path(chroma_dir))
        self._active_generations = active_generations
        self._previous_generations = previous_generations or (dict)
        self._retained_baselines = retained_baselines or (dict)
        # No mutation sink: candidate staging must emit no authoritative Shadow
        # events.  The caller is responsible for providing temporary state.
        self._store = ChromaStore(self.chroma_dir, mutation_sink=None)

    def close(self) -> None:
        self._store.close()

    def __enter__(self) -> Self:
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    @property
    def raw_store(self) -> ChromaStore:
        """Hermetic diagnostic access; never use this for serving reads."""
        return self._store

    def stage_rows(self, rows: Iterable[StagedRow]) -> None:
        """Physically upsert candidate or stable fixture rows.

        This operation never changes the active resolver and therefore never
        promotes a generation.  File rows must use generation-scoped physical
        ids; stable/governed rows must retain stable physical identity.
        """

        grouped: dict[str, list[StagedRow]] = {}
        materialized = list(rows)
        proposed_by_owner: dict[str, set[str]] = {}
        for row in materialized:
            self._validate_staged_row(row)
            if row.generation_scope == FILE_SCOPE:
                proposed_by_owner.setdefault(str(row.owner_digest), set()).add(
                    str(row.generation_id)
                )
            grouped.setdefault(row.collection_name, []).append(row)
        for owner, proposed in proposed_by_owner.items():
            if len(proposed) != 1:
                raise ValueError(
                    "one staging call cannot mix generations for one owner"
                )
            self._assert_owner_budget(owner, next(iter(proposed)))
        for collection_name, batch in grouped.items():
            col = self._store._collection(collection_name)  # pylint: disable=protected-access
            ids: list[str] = []
            documents: list[str] = []
            embeddings: list[list[float]] = []
            metadatas: list[dict[str, Any]] = []
            for row in batch:
                meta = dict(row.metadata)
                meta.update(
                    {
                        "id": row.physical_id,
                        "physical_id": row.physical_id,
                        "logical_id": row.logical_id,
                        "generation_scope": row.generation_scope,
                    }
                )
                if row.generation_scope == FILE_SCOPE:
                    meta["owner_digest"] = str(row.owner_digest)
                    meta["generation_id"] = str(row.generation_id)
                ids.append(row.physical_id)
                documents.append(row.document)
                embeddings.append(list(row.embedding))
                metadatas.append(meta)
            col.upsert(
                ids=ids,
                documents=documents,
                embeddings=embeddings,
                metadatas=metadatas,
            )

    def _assert_owner_budget(self, owner_digest: str, proposed_generation: str) -> None:
        active = self._active_generations().get(owner_digest)
        previous = self._previous_generations().get(owner_digest)
        retained = {
            str(value)
            for value in (self._retained_baselines().get(owner_digest) or set())
            if value
        }
        known: set[str] = set()
        for collection_name in (UNITS, SUMMARIES):
            col = self._store._collection(collection_name)  # pylint: disable=protected-access
            result = col.get(
                where={
                    "$and": [
                        {"generation_scope": FILE_SCOPE},
                        {"owner_digest": owner_digest},
                    ]
                },
                include=["metadatas"],
            )
            for meta in result.get("metadatas") or []:
                generation = str((meta or {}).get("generation_id") or "")
                if generation:
                    known.add(generation)
        protected = {value for value in (active, previous) if value} | retained
        abandoned = known - protected
        if abandoned and proposed_generation not in abandoned:
            raise GenerationBackpressureError(
                "owner already has one unresolved abandoned generation; "
                "CG-2 disposition is required before another stage"
            )

    def collection_identity(self, collection_name: str) -> dict[str, Any]:
        """Return the Chroma identity fields enforced by generation manifests."""
        col = self._store._collection(collection_name)  # pylint: disable=protected-access
        return {
            "collection_uuid": str(col.id),
            "configuration": dict(col.configuration_json),
        }

    # The immutable-manifest schema deliberately exposes every validated field.
    # pylint: disable=too-many-locals
    def build_manifest_collection_spec(
        self,
        collection_name: str,
        *,
        owner_digest: str,
        generation_id: str,
        embedding_model: str,
        embedding_dimension: int,
        immutable_metadata_keys: Iterable[str] = (
            "source_path",
            "start_offset",
            "content_hash",
        ),
    ) -> dict[str, Any]:
        """Describe the persisted float32 generation for an immutable manifest.

        Chroma normalizes embeddings on write.  Hashing the cold-readable rows,
        rather than caller-side float64 lists, binds the manifest to the bytes
        that restart qualification will actually recover.
        """
        col = self._store._collection(collection_name)  # pylint: disable=protected-access
        result = col.get(
            where={
                "$and": [
                    {"generation_scope": FILE_SCOPE},
                    {"owner_digest": owner_digest},
                    {"generation_id": generation_id},
                ]
            },
            include=["metadatas", "documents", "embeddings"],
        )
        ids = list(result.get("ids") or [])
        documents = list(result.get("documents") or [])
        metadatas = list(result.get("metadatas") or [])
        embeddings = result.get("embeddings")
        if embeddings is None:
            embeddings = []
        logical_to_physical: dict[str, str] = {}
        rows: dict[str, dict[str, Any]] = {}
        dimension = int(embedding_dimension)
        if dimension < 1:
            raise ValueError("embedding_dimension must be positive")
        for index, physical_id in enumerate(ids):
            meta = dict(metadatas[index] if index < len(metadatas) else {})
            document = documents[index] if index < len(documents) else None
            embedding = embeddings[index] if index < len(embeddings) else None
            if embedding is not None and hasattr(embedding, "tolist"):
                embedding = embedding.tolist()
            if not isinstance(document, str) or embedding is None:
                raise GenerationValidationError(
                    f"cannot manifest incomplete row {collection_name}/{physical_id}"
                )
            embedding_list = list(embedding)
            if len(embedding_list) != dimension:
                raise GenerationValidationError(
                    f"mixed embedding dimensions in {collection_name}"
                )
            logical_id = str(meta.get("logical_id") or "")
            if not logical_id or logical_id in logical_to_physical:
                raise GenerationValidationError(
                    f"missing/duplicate logical id in {collection_name}: {logical_id!r}"
                )
            logical_to_physical[logical_id] = physical_id
            rows[physical_id] = {
                "logical_id": logical_id,
                "document_hash": canonical_hash(document),
                "embedding_hash": canonical_hash(embedding_list),
                "embedding_dimension": dimension,
                "embedding_model": embedding_model,
                "immutable_metadata": {
                    key: meta[key] for key in immutable_metadata_keys if key in meta
                },
            }
        identity = self.collection_identity(collection_name)
        return {
            **identity,
            "embedding_model": embedding_model,
            "embedding_dimension": dimension,
            "logical_to_physical": logical_to_physical,
            "rows": rows,
        }

    def validate_manifest_exact(self, manifest: Mapping[str, Any]) -> dict[str, Any]:
        """Validate the exact immutable row set for a staged generation.

        Mutable annotations are intentionally ignored: only the keys explicitly
        listed under each expected row's ``immutable_metadata`` participate.
        Every physical row tagged with this owner/generation must be named by the
        manifest, and every named row must exist with exact immutable content.
        """
        try:
            validate_generation_manifest(manifest)
        except GenerationContractError as exc:
            raise GenerationValidationError(str(exc)) from exc

        owner = str(manifest["owner_digest"])
        generation = str(manifest["generation_id"])
        collection_results: dict[str, Any] = {}
        for collection_name, raw_spec in dict(manifest["collections"]).items():
            spec = dict(raw_spec)
            col = self._store._collection(collection_name)  # pylint: disable=protected-access
            actual_uuid = str(col.id)
            actual_configuration = dict(col.configuration_json)
            if actual_uuid != spec["collection_uuid"]:
                raise GenerationValidationError(
                    f"{collection_name} collection UUID mismatch"
                )
            if actual_configuration != spec["configuration"]:
                raise GenerationValidationError(
                    f"{collection_name} collection configuration mismatch"
                )

            result = col.get(
                where={
                    "$and": [
                        {"generation_scope": FILE_SCOPE},
                        {"owner_digest": owner},
                        {"generation_id": generation},
                    ]
                },
                include=["metadatas", "documents", "embeddings"],
            )
            ids = list(result.get("ids") or [])
            expected_rows = dict(spec["rows"])
            if set(ids) != set(expected_rows):
                missing = sorted(set(expected_rows) - set(ids))
                unexpected = sorted(set(ids) - set(expected_rows))
                raise GenerationValidationError(
                    f"{collection_name} expected-set mismatch; "
                    f"missing={missing}, unexpected={unexpected}"
                )

            documents = result.get("documents") or []
            metadatas = result.get("metadatas") or []
            embeddings = result.get("embeddings")
            if embeddings is None:
                embeddings = []
            by_id = {physical_id: index for index, physical_id in enumerate(ids)}
            for physical_id, raw_expected in expected_rows.items():
                expected = dict(raw_expected)
                index = by_id[physical_id]
                meta = dict(metadatas[index] if index < len(metadatas) else {})
                document = documents[index] if index < len(documents) else None
                embedding = embeddings[index] if index < len(embeddings) else None
                if embedding is not None and hasattr(embedding, "tolist"):
                    embedding = embedding.tolist()
                if not isinstance(document, str) or embedding is None:
                    raise GenerationValidationError(
                        f"{collection_name}/{physical_id} lacks document/embedding"
                    )
                logical_id = str(expected["logical_id"])
                if (
                    meta.get("id") != physical_id
                    or meta.get("physical_id") != physical_id
                ):
                    raise GenerationValidationError(
                        f"{collection_name}/{physical_id} physical identity mismatch"
                    )
                if meta.get("logical_id") != logical_id:
                    raise GenerationValidationError(
                        f"{collection_name}/{physical_id} logical identity mismatch"
                    )
                if canonical_hash(document) != expected["document_hash"]:
                    raise GenerationValidationError(
                        f"{collection_name}/{physical_id} document hash mismatch"
                    )
                embedding_list = list(embedding)
                if canonical_hash(embedding_list) != expected["embedding_hash"]:
                    raise GenerationValidationError(
                        f"{collection_name}/{physical_id} embedding hash mismatch"
                    )
                expected_dimension = int(expected["embedding_dimension"])
                if len(embedding_list) != expected_dimension:
                    raise GenerationValidationError(
                        f"{collection_name}/{physical_id} embedding dimension mismatch"
                    )
                if expected_dimension != int(spec["embedding_dimension"]):
                    raise GenerationValidationError(
                        f"{collection_name}/{physical_id} manifest dimension mismatch"
                    )
                expected_model = str(expected["embedding_model"])
                if expected_model != str(spec["embedding_model"]):
                    raise GenerationValidationError(
                        f"{collection_name}/{physical_id} manifest model mismatch"
                    )
                if meta.get("embedding_model") != expected_model:
                    raise GenerationValidationError(
                        f"{collection_name}/{physical_id} embedding model mismatch"
                    )
                if meta.get("embedding_dimension") != expected_dimension:
                    raise GenerationValidationError(
                        f"{collection_name}/{physical_id} metadata dimension mismatch"
                    )
                for key, value in dict(expected["immutable_metadata"]).items():
                    if meta.get(key) != value:
                        raise GenerationValidationError(
                            f"{collection_name}/{physical_id} immutable metadata "
                            f"mismatch for {key}"
                        )
            collection_results[collection_name] = {
                "expected_count": len(expected_rows),
                "actual_count": len(ids),
                "collection_uuid": actual_uuid,
            }
        return {
            "state": "HEALTHY",
            "owner_digest": owner,
            "generation_id": generation,
            "manifest_payload_hash": manifest["manifest_payload_hash"],
            "collections": collection_results,
        }

    @staticmethod
    def _validate_staged_row(row: StagedRow) -> None:
        if row.collection_name not in {UNITS, SUMMARIES}:
            raise ValueError(f"unsupported collection: {row.collection_name}")
        if not row.physical_id or not row.logical_id:
            raise ValueError("physical_id and logical_id are required")
        if row.generation_scope == FILE_SCOPE:
            if not row.physical_id.startswith("fg1_"):
                raise ValueError("file-derived physical ids must start with fg1_")
            if not row.owner_digest or not row.generation_id:
                raise ValueError(
                    "file-derived rows require owner_digest and generation_id"
                )
        elif row.generation_scope == STABLE_SCOPE:
            if row.physical_id != row.logical_id:
                raise ValueError(
                    "stable/governed rows must retain stable physical identity"
                )
            if row.owner_digest is not None or row.generation_id is not None:
                raise ValueError("stable/governed rows cannot carry a file generation")
        else:
            raise ValueError(f"unsupported generation scope: {row.generation_scope}")

    def _active_where(
        self,
        active: Mapping[str, str],
        *,
        owner_digest: str | None = None,
    ) -> dict[str, Any]:
        if owner_digest is not None:
            generation_id = active.get(owner_digest)
            if generation_id is None:
                # A deliberately impossible conjunction.  Chroma has no
                # constant-false metadata predicate.
                return {
                    "$and": [
                        {"owner_digest": owner_digest},
                        {"generation_id": "__convmem_no_active_generation__"},
                    ]
                }
            return {
                "$and": [
                    {"generation_scope": FILE_SCOPE},
                    {"owner_digest": owner_digest},
                    {"generation_id": generation_id},
                ]
            }

        clauses: list[dict[str, Any]] = [{"generation_scope": STABLE_SCOPE}]
        for owner, generation_id in sorted(active.items()):
            clauses.append(
                {
                    "$and": [
                        {"generation_scope": FILE_SCOPE},
                        {"owner_digest": owner},
                        {"generation_id": generation_id},
                    ]
                }
            )
        if len(clauses) == 1:
            return clauses[0]
        return {"$or": clauses}

    def _active_where_clauses(
        self,
        active: Mapping[str, str],
        *,
        owner_digest: str | None = None,
    ) -> list[list[dict[str, Any]]]:
        """Return bounded predicates so large owner sets avoid SQLite expression limits."""
        if owner_digest is not None:
            return [[self._active_where(active, owner_digest=owner_digest)]]
        active_ids = sorted(set(active.values()))
        if not active_ids:
            return [[{"generation_scope": STABLE_SCOPE}]]
        # Well-formed generation IDs include owner_digest, so the active ID set
        # is a useful bounded backend prefilter that avoids a deep owner×gen OR
        # tree (SQLite rejects it around 1,000 expressions). It is not authority:
        # _get_rows defensively checks the exact owner→generation pair.
        return [
            [
                {
                    "$or": [
                        {"generation_scope": STABLE_SCOPE},
                        {
                            "$and": [
                                {"generation_scope": FILE_SCOPE},
                                {"generation_id": {"$in": active_ids}},
                            ]
                        },
                    ]
                }
            ]
        ]

    def _get_rows(
        self,
        collection_name: str,
        *,
        where: dict[str, Any] | None = None,
        include_embeddings: bool = False,
        owner_digest: str | None = None,
    ) -> list[dict[str, Any]]:
        include = ["metadatas", "documents"]
        if include_embeddings:
            include.append("embeddings")
        col = self._store._collection(collection_name)  # pylint: disable=protected-access
        # One immutable read snapshot drives both the broad in-Chroma filter
        # and the defensive owner+generation check below.  Calling the resolver
        # twice could mix two pointer states in one read.
        active = dict(self._active_generations())
        results = []
        for clause_group in self._active_where_clauses(
            active, owner_digest=owner_digest
        ):
            active_where = clause_group[0] if len(clause_group) == 1 else {"$or": clause_group}
            results.append(
                col.get(where=_and_where(active_where, where), include=include)
            )
        out: list[dict[str, Any]] = []
        for result in results:
            ids = result.get("ids") or []
            documents = result.get("documents") or []
            metadatas = result.get("metadatas") or []
            embeddings = result.get("embeddings") if include_embeddings else None
            for index, physical_id in enumerate(ids):
                meta = dict(metadatas[index] if index < len(metadatas) else {})
                scope = meta.get("generation_scope")
                if scope == FILE_SCOPE:
                    row_owner = str(meta.get("owner_digest") or "")
                    row_generation = str(meta.get("generation_id") or "")
                    if active.get(row_owner) != row_generation:
                        continue
                    if owner_digest is not None and row_owner != owner_digest:
                        continue
                elif scope == STABLE_SCOPE:
                    if owner_digest is not None:
                        continue
                else:
                    # Generation-mediated reads fail closed on unclassified
                    # rows even if a broad backend predicate returned them.
                    continue
                meta["id"] = physical_id
                row: dict[str, Any] = {
                    "id": physical_id,
                    "physical_id": physical_id,
                    "logical_id": meta.get("logical_id"),
                    "document": documents[index] if index < len(documents) else "",
                    "metadata": meta,
                }
                if include_embeddings:
                    embedding = None
                    if embeddings is not None and index < len(embeddings):
                        embedding = embeddings[index]
                        if embedding is not None and hasattr(embedding, "tolist"):
                            embedding = embedding.tolist()
                    row["embedding"] = embedding
                out.append(row)
        return out

    @staticmethod
    def _validated_embedding(
        value: Any, *, label: str, expected_dimension: int | None = None
    ) -> list[float]:
        """Convert one embedding to finite floats or fail closed."""
        if value is None or isinstance(value, (str, bytes)):
            raise GenerationReadError(f"missing embedding for active row {label}")
        if hasattr(value, "tolist"):
            value = value.tolist()
        try:
            components = list(value)
        except (TypeError, ValueError) as exc:
            raise GenerationReadError(
                f"malformed embedding for active row {label}"
            ) from exc
        if not components:
            raise GenerationReadError(f"empty embedding for active row {label}")
        converted: list[float] = []
        for component in components:
            if isinstance(component, bool):
                raise GenerationReadError(
                    f"malformed embedding for active row {label}"
                )
            try:
                number = float(component)
            except (TypeError, ValueError) as exc:
                raise GenerationReadError(
                    f"malformed embedding for active row {label}"
                ) from exc
            if not math.isfinite(number):
                raise GenerationReadError(
                    f"non-finite embedding for active row {label}"
                )
            converted.append(number)
        if expected_dimension is not None and len(converted) != expected_dimension:
            raise GenerationReadError(
                f"embedding dimension mismatch for active row {label}: "
                f"expected {expected_dimension}, got {len(converted)}"
            )
        return converted

    @staticmethod
    def _cosine_distance(query: list[float], row: list[float], *, label: str) -> float:
        query_norm = math.sqrt(math.fsum(value * value for value in query))
        row_norm = math.sqrt(math.fsum(value * value for value in row))
        if not math.isfinite(query_norm) or query_norm == 0.0:
            raise GenerationReadError("query embedding has no usable cosine norm")
        if not math.isfinite(row_norm) or row_norm == 0.0:
            raise GenerationReadError(f"zero-norm embedding for active row {label}")
        similarity = math.fsum(
            query_value * row_value
            for query_value, row_value in zip(query, row, strict=True)
        ) / (query_norm * row_norm)
        distance = 1.0 - similarity
        if not math.isfinite(distance):
            raise GenerationReadError(f"unusable cosine distance for active row {label}")
        return distance

    def _query(
        self,
        collection_name: str,
        embedding: list[float],
        top_k: int,
        *,
        include_superseded: bool,
        owner_digest: str | None = None,
    ) -> list[dict[str, Any]]:
        if top_k <= 0:
            return []
        query_vector = self._validated_embedding(embedding, label="query")
        active_rows = self._get_rows(
            collection_name,
            include_embeddings=True,
            owner_digest=owner_digest,
        )
        if not active_rows:
            return []

        fetch = top_k if include_superseded else max(top_k * 3, top_k)
        rows: list[dict[str, Any]] = []
        for row in active_rows:
            row_embedding = self._validated_embedding(
                row.get("embedding"),
                label=str(row["id"]),
                expected_dimension=len(query_vector),
            )
            rows.append(
                {
                    "id": row["id"],
                    "document": row["document"],
                    "metadata": row["metadata"],
                    "distance": self._cosine_distance(
                        query_vector, row_embedding, label=str(row["id"])
                    ),
                }
            )
        rows.sort(key=lambda row: (float(row["distance"]), str(row["id"])))
        rows = rows[: min(fetch, len(rows))]
        if not include_superseded:
            rows = [row for row in rows if not is_superseded(row.get("metadata") or {})]
        return rows[:top_k]

    def query_units(
        self,
        embedding: list[float],
        top_k: int,
        *,
        include_superseded: bool = False,
        owner_digest: str | None = None,
    ) -> list[dict[str, Any]]:
        return self._query(
            UNITS,
            embedding,
            top_k,
            include_superseded=include_superseded,
            owner_digest=owner_digest,
        )

    def dedupe_query(
        self, embedding: list[float], candidate_k: int
    ) -> list[dict[str, Any]]:
        """Return the corpus-wide committed view used by candidate dedupe."""
        return self.query_units(embedding, candidate_k, include_superseded=False)

    def query_summaries(
        self,
        embedding: list[float],
        top_k: int,
        *,
        owner_digest: str | None = None,
    ) -> list[dict[str, Any]]:
        return self._query(
            SUMMARIES,
            embedding,
            top_k,
            include_superseded=True,
            owner_digest=owner_digest,
        )

    def summary_keyword_fallback(self, query: str, top_k: int) -> list[dict[str, Any]]:
        """Small deterministic fallback over committed summary documents only."""
        if top_k <= 0:
            return []
        tokens = {token.casefold() for token in query.split() if token.strip()}
        rows = self._get_rows(SUMMARIES)

        def score(row: dict[str, Any]) -> tuple[int, str]:
            haystack = str(row.get("document") or "").casefold()
            matches = sum(1 for token in tokens if token in haystack)
            return (-matches, str(row["id"]))

        matched = [row for row in rows if not tokens or score(row)[0] < 0]
        return sorted(matched, key=score)[:top_k]

    def get_unit_by_logical_id(
        self,
        logical_id: str,
        *,
        include_embedding: bool = False,
        include_superseded: bool = False,
    ) -> dict[str, Any] | None:
        rows = self._get_rows(
            UNITS,
            where={"logical_id": logical_id},
            include_embeddings=include_embedding,
        )
        if not include_superseded:
            rows = [row for row in rows if not is_superseded(row["metadata"])]
        if len(rows) > 1:
            raise RuntimeError(f"multiple active rows for logical id {logical_id}")
        return rows[0] if rows else None

    def get_unit_by_physical_id(
        self,
        physical_id: str,
        *,
        include_embedding: bool = False,
    ) -> dict[str, Any] | None:
        rows = self._get_rows(
            UNITS,
            where={"physical_id": physical_id},
            include_embeddings=include_embedding,
        )
        return rows[0] if rows else None

    def get_unit(
        self, physical_id: str, *, include_embedding: bool = False
    ) -> dict[str, Any] | None:
        """Compatibility lookup for ledger/observe/refine physical-id callers."""
        return self.get_unit_by_physical_id(
            physical_id, include_embedding=include_embedding
        )

    def units_metadata(
        self, *, include_superseded: bool = False
    ) -> list[dict[str, Any]]:
        rows = self._get_rows(UNITS)
        return [
            row["metadata"]
            for row in rows
            if include_superseded or not is_superseded(row["metadata"])
        ]

    def get_units_with_embeddings(
        self, *, include_superseded: bool = False
    ) -> list[dict[str, Any]]:
        rows = self._get_rows(UNITS, include_embeddings=True)
        return [
            row
            for row in rows
            if row.get("embedding") is not None
            and (include_superseded or not is_superseded(row["metadata"]))
        ]

    def rows_for_source(
        self,
        collection_name: str,
        source_path: str,
        *,
        owner_digest: str | None = None,
        include_superseded: bool = False,
    ) -> list[dict[str, Any]]:
        rows = self._get_rows(
            collection_name,
            where={"source_path": source_path},
            owner_digest=owner_digest,
        )
        if collection_name == UNITS and not include_superseded:
            rows = [row for row in rows if not is_superseded(row["metadata"])]
        return rows

    def count_units(self, *, include_superseded: bool = False) -> int:
        return len(self.units_metadata(include_superseded=include_superseded))

    def count_summaries(self) -> int:
        return len(self._get_rows(SUMMARIES))

    def preview_supersede_for_source(
        self, source_path: str, *, owner_digest: str | None = None
    ) -> list[dict[str, Any]]:
        rows = self.rows_for_source(
            UNITS,
            source_path,
            owner_digest=owner_digest,
            include_superseded=False,
        )
        return [
            {
                "id": row["id"],
                "logical_id": row["logical_id"],
                "title": row["metadata"].get("title") or "",
            }
            for row in rows
        ]

    def preview_purge_for_source(
        self, source_path: str, *, owner_digest: str | None = None
    ) -> list[str]:
        return sorted(
            row["id"]
            for row in self.rows_for_source(
                UNITS,
                source_path,
                owner_digest=owner_digest,
                include_superseded=True,
            )
        )

    def all_physical_ids(self, collection_name: str) -> set[str]:
        """Diagnostic physical inventory, including inactive residue."""
        result = self._store._collection(collection_name).get(  # pylint: disable=protected-access
            include=[]
        )
        return set(result.get("ids") or [])

    def readonly_sqlite_rows(
        self, collection_name: str, *, owner_digest: str | None = None
    ) -> list[dict[str, Any]]:
        """Generation-mediated diagnostic fallback over read-only SQLite.

        This path has no vector top-k pool.  It is a correctness fallback for
        metadata inspection only; inactive rows are filtered before the caller
        receives counts or records.
        """
        active = dict(self._active_generations())
        rows: list[dict[str, Any]] = []
        for row in collection_metadata_rows(self.chroma_dir, collection_name):
            scope = row.get("generation_scope")
            if scope == STABLE_SCOPE:
                if owner_digest is None:
                    rows.append(row)
                continue
            if scope != FILE_SCOPE:
                continue
            owner = str(row.get("owner_digest") or "")
            if owner_digest is not None and owner != owner_digest:
                continue
            if active.get(owner) == row.get("generation_id"):
                rows.append(row)
        return rows

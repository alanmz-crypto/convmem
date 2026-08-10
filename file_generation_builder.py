"""Hermetic construction of file-derived candidate generations.

This module deliberately has no knowledge of production processed logs, exports,
writer sessions, or Shadow sinks.  Callers provide pure parsing/model/embedding
callbacks and a read-only committed-corpus view.  The returned bundle is inert
until a separate store stages it and the pointer layer promotes it.
"""

from __future__ import annotations

import hashlib
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from typing import Any

from distill import make_unit_id
from file_generation_contract import (
    candidate_bundle_hash,
    canonical_hash,
    canonical_source_path,
    make_generation_id,
    make_physical_id,
    owner_digest,
    ownership_key,
)
from ingest_dedupe import IngestDedupeResult, evaluate_ingest_batch, unit_content_hash
from vector_similarity import cosine_similarity


class CandidateBuildError(RuntimeError):
    """A candidate could not be completely built; no authority was changed."""


@dataclass(frozen=True)
class CandidateRow:
    collection_name: str
    logical_id: str
    physical_id: str
    document: str
    embedding: tuple[float, ...]
    metadata: dict[str, Any]

    def as_stage_row(self) -> dict[str, Any]:
        return {
            "collection_name": self.collection_name,
            "logical_id": self.logical_id,
            "physical_id": self.physical_id,
            "document": self.document,
            "embedding": list(self.embedding),
            "metadata": dict(self.metadata),
        }


@dataclass
class CandidateGeneration:  # pylint: disable=too-many-instance-attributes
    canonical_source_path: str
    ownership_key: str
    owner_digest: str
    source_hash: str
    pipeline_fingerprint: str
    candidate_bundle_hash: str
    generation_id: str
    unit_rows: list[CandidateRow] = field(default_factory=list)
    summary_rows: list[CandidateRow] = field(default_factory=list)
    exact_suppressions: list[dict] = field(default_factory=list)
    semantic_candidates: list[dict] = field(default_factory=list)
    self_source_cross_logical_suppression_count: int = 0
    known_projection_loss_risks: list[str] = field(default_factory=list)

    @property
    def all_rows(self) -> list[CandidateRow]:
        return [*self.unit_rows, *self.summary_rows]


class _ChunkOverlayStore:
    """Merge committed neighbors with earlier candidate chunks before top-k."""

    def __init__(self, committed_store: Any, prior_rows: list[CandidateRow]):
        self._committed = committed_store
        self._prior = prior_rows

    def query_units(self, embedding: list[float], top_k: int) -> list[dict]:
        committed = list(self._committed.query_units(embedding, top_k))
        overlay: list[dict] = []
        for row in self._prior:
            similarity = cosine_similarity(embedding, list(row.embedding))
            overlay.append(
                {
                    "id": row.physical_id,
                    "document": row.document,
                    "metadata": dict(row.metadata),
                    "distance": 1.0 - similarity,
                }
            )
        merged = [*committed, *overlay]
        merged.sort(key=lambda item: float(item.get("distance", float("inf"))))
        return merged[:top_k]


def _summary_logical_id(source: str, start_offset: int) -> str:
    return hashlib.sha256(f"{source}:{start_offset}".encode()).hexdigest()


def _unit_logical_id(
    source: str, start_offset: int, title: str, unit_index: int
) -> str:
    # Mirror production's call signature exactly.  The current implementation
    # deliberately excludes title from the hash, so title drift remains stable.
    return make_unit_id(source, start_offset, title, unit_index)


def _pre_dedupe_rows(
    *,
    source: str,
    chunks: Iterable[dict[str, Any]],
    extract_chunk: Callable[[dict[str, Any]], tuple[str, list[dict[str, Any]]]],
    embed: Callable[[str], list[float]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    units: list[dict[str, Any]] = []
    summaries: list[dict[str, Any]] = []
    for chunk in chunks:
        start = int(chunk["start_offset"])
        try:
            summary, raw_units = extract_chunk(chunk)
            if not isinstance(summary, str) or not isinstance(raw_units, list):
                raise TypeError("extractor must return (summary: str, units: list)")
            if any(not isinstance(raw, dict) for raw in raw_units):
                raise TypeError("every extracted unit must be an object")
            summary_embedding = embed(summary)
        except Exception as exc:  # callback boundary must fail the whole candidate
            raise CandidateBuildError(
                f"chunk {start} extraction failed: {exc}"
            ) from exc
        summaries.append(
            {
                "logical_id": _summary_logical_id(source, start),
                "document": summary,
                "embedding": list(summary_embedding),
                "metadata": {
                    "source_path": source,
                    "start_offset": start,
                    "end_offset": int(chunk.get("end_offset", start)),
                    "distill_status": "empty" if not raw_units else "done",
                },
                "chunk_index": len(summaries),
            }
        )
        for unit_index, raw in enumerate(raw_units):
            logical_id = _unit_logical_id(
                source, start, str(raw.get("title") or ""), unit_index
            )
            document = str(
                raw.get("document") or raw.get("summary") or raw.get("text") or ""
            )
            if not document:
                raise CandidateBuildError(
                    f"chunk {start} unit {unit_index} has no document"
                )
            try:
                embedding = embed(document)
            except Exception as exc:
                raise CandidateBuildError(
                    f"chunk {start} unit {unit_index} embedding failed: {exc}"
                ) from exc
            metadata = dict(raw.get("metadata") or {})
            metadata.update(
                {
                    "source_path": source,
                    "start_offset": start,
                    "logical_id": logical_id,
                    "content_hash": unit_content_hash(document),
                }
            )
            units.append(
                {
                    "logical_id": logical_id,
                    "document": document,
                    "embedding": list(embedding),
                    "metadata": metadata,
                    "chunk_index": len(summaries) - 1,
                    "unit_index": unit_index,
                }
            )
    return units, summaries


def build_candidate_generation(  # pylint: disable=too-many-arguments,too-many-locals
    *,
    source_path: str,
    source_bytes: bytes,
    parse: Callable[[bytes], Iterable[dict[str, Any]]],
    extract_chunk: Callable[[dict[str, Any]], tuple[str, list[dict[str, Any]]]],
    embed: Callable[[str], list[float]],
    committed_store: Any,
    dedupe_cfg: dict,
    pipeline_fingerprint: dict[str, Any] | str,
    embedding_model: str,
) -> CandidateGeneration:
    """Build a complete inert candidate or raise ``CandidateBuildError``.

    Physical ids are derived only after hashing the full pre-dedupe bundle.  The
    dedupe evaluator sees the committed corpus plus a distance-ranked overlay of
    accepted rows from earlier candidate chunks.  Nothing is persisted here.
    """
    source = canonical_source_path(source_path)
    key = ownership_key(source)
    digest = owner_digest(key)
    source_hash = hashlib.sha256(source_bytes).hexdigest()
    fingerprint = (
        pipeline_fingerprint
        if isinstance(pipeline_fingerprint, str)
        else canonical_hash(pipeline_fingerprint)
    )
    try:
        chunks = list(parse(source_bytes))
    except Exception as exc:
        raise CandidateBuildError(f"parse failed: {exc}") from exc
    units, summaries = _pre_dedupe_rows(
        source=source, chunks=chunks, extract_chunk=extract_chunk, embed=embed
    )
    bundle_hash = candidate_bundle_hash(units, summaries)
    gen_id = make_generation_id(
        owner_digest=digest,
        source_hash=source_hash,
        pipeline_fingerprint=fingerprint,
        candidate_bundle_hash=bundle_hash,
    )

    summary_rows: list[CandidateRow] = []
    for row in summaries:
        physical = make_physical_id("conversation_summaries", gen_id, row["logical_id"])
        meta = dict(row["metadata"])
        meta.update(
            {
                "id": physical,
                "physical_id": physical,
                "logical_id": row["logical_id"],
                "owner_digest": digest,
                "generation_id": gen_id,
                "generation_scope": "file",
                "embedding_model": embedding_model,
                "embedding_dimension": len(row["embedding"]),
            }
        )
        summary_rows.append(
            CandidateRow(
                "conversation_summaries",
                row["logical_id"],
                physical,
                row["document"],
                tuple(row["embedding"]),
                meta,
            )
        )

    accepted: list[CandidateRow] = []
    exact: list[dict] = []
    semantic: list[dict] = []
    by_chunk: dict[int, list[dict[str, Any]]] = {}
    for row in units:
        by_chunk.setdefault(int(row["chunk_index"]), []).append(row)
    for chunk_index in sorted(by_chunk):
        batch: list[tuple] = []
        candidates_by_physical: dict[str, dict[str, Any]] = {}
        for row in by_chunk[chunk_index]:
            physical = make_physical_id("knowledge_units", gen_id, row["logical_id"])
            meta = dict(row["metadata"])
            meta.update(
                {
                    "id": physical,
                    "physical_id": physical,
                    "logical_id": row["logical_id"],
                    "owner_digest": digest,
                    "generation_id": gen_id,
                    "generation_scope": "file",
                    "embedding_model": embedding_model,
                    "embedding_dimension": len(row["embedding"]),
                }
            )
            unit = {
                "id": physical,
                "physical_id": physical,
                "logical_id": row["logical_id"],
            }
            candidates_by_physical[physical] = row
            batch.append((unit, row["document"], row["embedding"], meta))
        view = _ChunkOverlayStore(committed_store, accepted)
        outcome: IngestDedupeResult = evaluate_ingest_batch(
            view,
            dedupe_cfg,
            batch,
            generation_identity_fields=True,
        )
        exact.extend(outcome.exact_suppressions)
        semantic.extend(outcome.semantic_candidates)
        for unit, document, embedding, metadata in outcome.accepted:
            accepted.append(
                CandidateRow(
                    "knowledge_units",
                    str(unit["logical_id"]),
                    str(unit["physical_id"]),
                    document,
                    tuple(embedding),
                    dict(metadata),
                )
            )

    cross_logical = 0
    for row in exact:
        if row.get("suppressed_logical_id") == row.get("matched_logical_id"):
            continue
        matched = committed_store.get_unit(row["matched_id"])
        if matched and (matched.get("metadata") or {}).get("source_path") == source:
            cross_logical += 1
    risks = ["self_source_cross_logical_exact_suppression"] if cross_logical else []
    return CandidateGeneration(
        canonical_source_path=source,
        ownership_key=key,
        owner_digest=digest,
        source_hash=source_hash,
        pipeline_fingerprint=fingerprint,
        candidate_bundle_hash=bundle_hash,
        generation_id=gen_id,
        unit_rows=accepted,
        summary_rows=summary_rows,
        exact_suppressions=exact,
        semantic_candidates=semantic,
        self_source_cross_logical_suppression_count=cross_logical,
        known_projection_loss_risks=risks,
    )

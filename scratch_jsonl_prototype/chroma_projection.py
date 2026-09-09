"""Scratch-only projection of incremental JSONL rows into real Chroma.

This adapter deliberately owns no production state machine.  It is a small
bridge used by the bounded scratch evidence pass: all paths are checked by
``ScratchBoundary`` before imports/resources are constructed, writes use the
existing writer session, and rows are selected/pruned by exact source identity.
"""
# pylint: disable=too-many-instance-attributes

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Callable, Iterable

from scratch_jsonl_prototype.isolation import ScratchBoundary

CHROMA_DURABLE_TRANSITIONS = (
    "summary_upsert", "unit_upsert", "summaries_prune", "units_prune",
)


def _embedding(value: str, dimension: int = 4) -> list[float]:
    """Return a deterministic, fixed-size local embedding."""
    digest = hashlib.sha256(value.encode("utf-8")).digest()
    return [((digest[index] / 255.0) * 2.0) - 1.0 for index in range(dimension)]


class ScratchChromaProjection:
    """Real-Chroma generation projection for isolated scratch evidence."""

    def __init__(self, boundary: ScratchBoundary, *, source_path: Path | str,
                 fault: Callable[[str], None] | None = None):
        # Importing this module is safe; the heavy Chroma/writer imports happen
        # only after every mutable path has been validated below.
        self.boundary = boundary
        self.source_path = boundary.resolve_mutable(source_path, label="source fixture")
        self.fault = fault or (lambda _point: None)
        self.chroma_dir = boundary.resolve_mutable("chroma/real-projection", label="chroma")
        self.config_path = boundary.resolve_mutable("config/scratch.toml", label="config")
        self.lock_path = boundary.resolve_mutable("locks/chroma-writer.lock", label="writer lock")
        self.attest_dir = boundary.resolve_mutable("attest", label="attestation directory")
        self.census_dir = boundary.resolve_mutable("census", label="census directory")
        self.chroma_dir.mkdir(parents=True, exist_ok=True)
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        self.config_path.write_text(
            "[index]\nchroma_dir = "
            + json.dumps(str(self.chroma_dir))
            + "\n",
            encoding="utf-8",
        )

    @property
    def source_identity(self) -> str:
        return hashlib.sha256(f"kiro-jsonl:{self.source_path}".encode()).hexdigest()

    def _session(self):
        # Local imports are intentional: callers establish the pre-import
        # boundary/network denial before constructing this adapter.
        from chroma_write_store import production_chroma_write_session

        return production_chroma_write_session(
            self.config_path,
            lock_path=self.lock_path,
            attest_dir=self.attest_dir,
            census_dir=self.census_dir,
            entrypoint="scratch_jsonl_chroma_projection",
        )

    def upsert(self, rows: Iterable[dict[str, Any]], generation: str) -> int:
        """Upsert deterministic summary and unit rows for one generation."""
        _ = generation  # authority remains in the engine checkpoint
        count = 0
        with self._session() as session:
            for row in rows:
                metadata = dict(row.get("metadata") or {})
                metadata.update(
                    {
                        "source_path": str(self.source_path),
                        "source_identity": self.source_identity,
                        "scratch_projection": True,
                    }
                )
                doc_id = str(row["id"])
                document = str(row.get("document") or "")
                embedding = _embedding(document)
                self.fault("before_summary_upsert")
                session.store.add_summary(doc_id, document, embedding, metadata)
                self.fault("after_summary_upsert")
                # Keep a matching unit so both real collection write paths are
                # exercised; metadata has no provenance fields and is therefore
                # explicitly treated as untrusted by the production validator.
                self.fault("before_unit_upsert")
                session.store.add_unit(doc_id, document, embedding, metadata)
                self.fault("after_unit_upsert")
                count += 1
        return count

    def reconcile(self, rows: Iterable[dict[str, Any]], generation: str) -> int:
        """Repair missing rows in either collection without transformation."""
        _ = generation
        expected = list(rows)
        with self._session() as session:
            from chroma_store import SUMMARIES, UNITS
            have_summary = session.store.ids_for_source(SUMMARIES, str(self.source_path))
            have_units = session.store.ids_for_source(UNITS, str(self.source_path))
            missing = [row for row in expected if row["id"] not in have_summary or row["id"] not in have_units]
            for row in missing:
                metadata = dict(row.get("metadata") or {})
                metadata.update({"source_path": str(self.source_path), "source_identity": self.source_identity,
                                 "scratch_projection": True})
                document = str(row.get("document") or "")
                embedding = _embedding(document)
                self.fault("before_summary_upsert")
                session.store.add_summary(row["id"], document, embedding, metadata)
                self.fault("after_summary_upsert")
                self.fault("before_unit_upsert")
                session.store.add_unit(row["id"], document, embedding, metadata)
                self.fault("after_unit_upsert")
        return len(missing)

    def _rows_for(self, collection_name: str) -> list[dict[str, Any]]:
        with self._session() as session:
            collection = session.store._collection(collection_name)  # pylint: disable=protected-access
            result = collection.get(where={"source_path": str(self.source_path)},
                                    include=["documents", "metadatas", "embeddings"])
        docs, metas, embeds = result.get("documents") or [], result.get("metadatas") or [], result.get("embeddings")
        return sorted([{"id": doc_id, "document": docs[i], "embedding": embeds[i] if embeds is not None else [],
                        "metadata": dict(metas[i] or {})} for i, doc_id in enumerate(result.get("ids") or [])],
                      key=lambda row: row["id"])

    def rows(self, generation: str | None = None) -> list[dict[str, Any]]:
        """Read authoritative scratch rows from the real Chroma collections."""
        _ = generation
        from chroma_store import SUMMARIES
        return self._rows_for(SUMMARIES)

    def prune(self, *, generation: str, keep_ids: set[str]) -> int:
        """Delete obsolete rows, constrained to this exact scratch source."""
        from chroma_store import SUMMARIES, UNITS
        _ = generation

        removed = 0
        with self._session() as session:
            # Restrict deletion to this exact source; historical rows from a
            # different source are never candidates.
            for collection_name, delete in ((SUMMARIES, session.store.delete_summaries_for_source),
                                             (UNITS, session.store.delete_units_for_source)):
                collection = session.store._collection(collection_name)  # pylint: disable=protected-access
                found = collection.get(where={"source_path": str(self.source_path)}, include=["metadatas"])
                obsolete = {
                    doc_id for doc_id, metadata in zip(found.get("ids") or [], found.get("metadatas") or [])
                    if doc_id not in keep_ids
                }
                if obsolete:
                    self.fault("before_" + collection_name + "_prune")
                    removed += delete(str(self.source_path), keep_ids=set(keep_ids), candidate_ids=obsolete)
                    self.fault("after_" + collection_name + "_prune")
        return removed

    def authority(self) -> dict[str, Any]:
        """Return exact persisted rows and the validated scratch config path."""
        from chroma_store import SUMMARIES, UNITS
        return {
            "chroma_dir": str(self.chroma_dir),
            "config_path": str(self.config_path),
            "summaries": self._rows_for(SUMMARIES),
            "units": self._rows_for(UNITS),
        }


__all__ = ["CHROMA_DURABLE_TRANSITIONS", "ScratchChromaProjection"]

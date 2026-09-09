"""Scratch-only projection of incremental JSONL rows into real Chroma.

This adapter deliberately owns no production state machine.  It is a small
bridge used by the bounded scratch evidence pass: all paths are checked by
``ScratchBoundary`` before imports/resources are constructed, writes use the
existing writer session, and rows are selected/pruned by exact source identity.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Iterable

from scratch_jsonl_prototype.isolation import ScratchBoundary


def _embedding(value: str, dimension: int = 4) -> list[float]:
    """Return a deterministic, fixed-size local embedding."""
    digest = hashlib.sha256(value.encode("utf-8")).digest()
    return [((digest[index] / 255.0) * 2.0) - 1.0 for index in range(dimension)]


class ScratchChromaProjection:
    """Real-Chroma generation projection for isolated scratch evidence."""

    def __init__(self, boundary: ScratchBoundary, *, source_path: Path | str):
        # Importing this module is safe; the heavy Chroma/writer imports happen
        # only after every mutable path has been validated below.
        self.boundary = boundary
        self.source_path = boundary.resolve_mutable(source_path, label="source fixture")
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
        count = 0
        with self._session() as session:
            for row in rows:
                metadata = dict(row.get("metadata") or {})
                metadata.update(
                    {
                        "source_path": str(self.source_path),
                        "source_identity": self.source_identity,
                        "generation": generation,
                        "scratch_projection": True,
                    }
                )
                doc_id = str(row["id"])
                document = str(row.get("document") or "")
                embedding = _embedding(document)
                session.store.add_summary(doc_id, document, embedding, metadata)
                # Keep a matching unit so both real collection write paths are
                # exercised; metadata has no provenance fields and is therefore
                # explicitly treated as untrusted by the production validator.
                session.store.add_unit(doc_id, document, embedding, metadata)
                count += 1
        return count

    def rows(self, generation: str | None = None) -> list[dict[str, Any]]:
        """Read authoritative scratch rows from the real Chroma collections."""
        from chroma_store import SUMMARIES

        with self._session() as session:
            collection = session.store._collection(SUMMARIES)  # pylint: disable=protected-access
            result = collection.get(
                where={"source_path": str(self.source_path)},
                include=["documents", "metadatas", "embeddings"],
            )
        rows = []
        documents = result.get("documents") or []
        metadatas = result.get("metadatas") or []
        embeddings = result.get("embeddings")
        for index, doc_id in enumerate(result.get("ids") or []):
            metadata = dict(metadatas[index] or {})
            if generation is not None and metadata.get("generation") != generation:
                continue
            rows.append(
                {
                    "id": doc_id,
                    "document": documents[index],
                    "embedding": embeddings[index] if embeddings is not None else [],
                    "metadata": metadata,
                }
            )
        return sorted(rows, key=lambda row: row["id"])

    def prune(self, *, generation: str, keep_ids: set[str]) -> int:
        """Delete obsolete rows, constrained to this exact scratch source."""
        from chroma_store import SUMMARIES

        removed = 0
        with self._session() as session:
            existing = session.store.ids_for_source(SUMMARIES, str(self.source_path))
            # Restrict deletion to rows belonging to this generation and this
            # exact source; historical generations from another source remain.
            collection = session.store._collection(SUMMARIES)  # pylint: disable=protected-access
            found = collection.get(
                where={"source_path": str(self.source_path)}, include=["metadatas"]
            )
            candidates = {
                doc_id
                for doc_id, metadata in zip(
                    found.get("ids") or [], found.get("metadatas") or []
                )
                if (metadata or {}).get("generation") == generation
            }
            obsolete = (existing & candidates) - set(keep_ids)
            if obsolete:
                removed = session.store.delete_summaries_for_source(
                    str(self.source_path), keep_ids=set(keep_ids), candidate_ids=obsolete
                )
        return removed

    def authority(self) -> dict[str, Any]:
        """Return exact persisted rows and the validated scratch config path."""
        return {
            "chroma_dir": str(self.chroma_dir),
            "config_path": str(self.config_path),
            "rows": self.rows(),
        }


__all__ = ["ScratchChromaProjection"]

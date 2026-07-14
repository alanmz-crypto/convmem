"""ChromaDB wrapper.

Two collections are defined per the design, but Step 4 only uses
`conversation_summaries` (the --raw fallback layer). `knowledge_units`
is created lazily in Step 5.
"""

from __future__ import annotations

import time
from pathlib import Path

import chromadb

SUMMARIES = "conversation_summaries"
UNITS = "knowledge_units"

# Cache for superseded count — avoids O(n) metadata scan on every stats/search call.
# Superseded status changes only during refine dedupe or forget, not in normal reads.
_superseded_cache: dict[str, tuple[int, float]] = {}  # chroma_dir -> (count, expiry_ts)
_SUPERSEDED_CACHE_TTL = 30.0  # seconds


def _get_superseded_count(collection, chroma_dir: str) -> int:
    """Return cached or fresh superseded count. Cache TTL = 30s."""
    now = time.monotonic()
    cached = _superseded_cache.get(chroma_dir)
    if cached is not None and now < cached[1]:
        return cached[0]
    try:
        res = collection.get(where={"superseded": True}, include=[])
        n = len(res.get("ids") or [])
    except Exception:
        n = 0
    _superseded_cache[chroma_dir] = (n, now + _SUPERSEDED_CACHE_TTL)
    return n


def invalidate_superseded_cache(chroma_dir: str) -> None:
    """Call after tombstoning or undoing a unit (refine dedupe, forget, approve)."""
    _superseded_cache.pop(chroma_dir, None)


def is_chroma_contention_error(exc: BaseException) -> bool:
    """True when another process holds the Chroma sqlite write lock."""
    msg = str(exc).lower()
    return (
        "readonly" in msg
        or "database is locked" in msg
        or "code: 8" in msg
    )


def open_chroma_for_read(chroma_dir: str, *, retries: int = 5) -> "ChromaStore":
    """Open Chroma for vector queries; retry briefly on writer contention."""
    last: Exception | None = None
    for attempt in range(retries):
        store: ChromaStore | None = None
        try:
            store = ChromaStore(chroma_dir)
            store._collection(UNITS).count()
            return store
        except Exception as e:
            last = e
            if store is not None:
                try:
                    store.close()
                except Exception:
                    pass
            if is_chroma_contention_error(e) and attempt + 1 < retries:
                time.sleep(0.15 * (attempt + 1))
                continue
            raise
    if last:
        raise last
    raise RuntimeError("open_chroma_for_read failed")


def open_chroma_for_verify(chroma_dir: str) -> "ChromaStore":
    """Open an existing Chroma root read-only for restore-drill verification.

    Uses ``get_collection`` only — never ``get_or_create_collection`` — so a
    missing collection fails instead of mutating the restored store.
    """
    store = ChromaStore(chroma_dir, create_collections=False)
    # Touch primary collection so open fails early if restore is incomplete.
    store._collection(UNITS)
    return store


def is_superseded(meta: dict) -> bool:
    """True when a unit was tombstoned by chroma_dedupe (F1)."""
    return meta.get("superseded") is True


class ChromaStore:
    def __init__(self, chroma_dir: str, *, create_collections: bool = True):
        self.chroma_dir = str(Path(chroma_dir).expanduser())
        # SegmentAPI + hnswlib compat shim can count() but fails upsert on
        # existing persistent HNSW ("Index seems to be corrupted or unsupported").
        self.client_mode = "PersistentClient"
        self.create_collections = create_collections
        self.client = chromadb.PersistentClient(path=self.chroma_dir)

    def close(self) -> None:
        """Release the PersistentClient so readers can open the corpus."""
        client = self.client
        self.client = None
        if client is not None:
            try:
                client.close()
            except Exception:
                pass

    def __enter__(self) -> "ChromaStore":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def _collection(self, name: str):
        if self.client is None:
            raise RuntimeError("ChromaStore is closed")
        if self.create_collections:
            return self.client.get_or_create_collection(
                name=name, metadata={"hnsw:space": "cosine"}
            )
        # Verification / restore-drill path: never create missing collections.
        return self.client.get_collection(name=name)

    def add_summary(
        self,
        doc_id: str,
        document: str,
        embedding: list[float],
        metadata: dict,
    ) -> None:
        self._collection(SUMMARIES).add(
            ids=[doc_id],
            documents=[document],
            embeddings=[embedding],
            metadatas=[metadata],
        )

    def query_summaries(
        self, embedding: list[float], top_k: int
    ) -> list[dict]:
        res = self._collection(SUMMARIES).query(
            query_embeddings=[embedding],
            n_results=top_k,
        )
        return self._flatten(res)

    def count_summaries(self) -> int:
        return self._collection(SUMMARIES).count()

    def summaries_metadata(self) -> list[dict]:
        col = self._collection(SUMMARIES)
        res = col.get(include=["metadatas"])
        return res.get("metadatas", []) or []

    def add_unit(
        self,
        unit_id: str,
        document: str,
        embedding: list[float],
        metadata: dict,
    ) -> None:
        meta = dict(metadata or {})
        # Block semantic *replace* of governed decisions outside the approval protocol.
        # First-time creates (and legacy seed/repair into empty ids) remain allowed;
        # observe._reject_governed_bypass covers upsert=True without proposal_id.
        existing = self.get_unit(unit_id)
        if existing is not None:
            existing_meta = existing.get("metadata") or {}
            existing_lid = str(
                existing_meta.get("ledger_id") or existing.get("id") or unit_id or ""
            ).strip()
            if existing_lid.startswith("dec_") and not str(meta.get("proposal_id") or "").strip():
                raise ValueError(
                    "governed decision replace requires proposal_id from approval protocol"
                )
        self._collection(UNITS).upsert(
            ids=[unit_id],
            documents=[document],
            embeddings=[embedding],
            metadatas=[meta],
        )

    def query_units(
        self,
        embedding: list[float],
        top_k: int,
        *,
        include_superseded: bool = False,
    ) -> list[dict]:
        if include_superseded:
            res = self._collection(UNITS).query(
                query_embeddings=[embedding],
                n_results=top_k,
            )
            return self._flatten(res)

        fetch = max(top_k * 3, top_k)
        total = self._collection(UNITS).count()
        fetch = min(fetch, total) if total else fetch
        res = self._collection(UNITS).query(
            query_embeddings=[embedding],
            n_results=max(fetch, 1),
        )
        results = self._flatten(res)
        filtered = [
            r
            for r in results
            if not is_superseded(r.get("metadata") or {})
        ]
        return filtered[:top_k]

    def count_units(self, *, include_superseded: bool = False) -> int:
        total = self._collection(UNITS).count()
        if include_superseded:
            return total
        n_superseded = _get_superseded_count(self._collection(UNITS), self.chroma_dir)
        return total - n_superseded

    def units_metadata(self, *, include_superseded: bool = False) -> list[dict]:
        col = self._collection(UNITS)
        res = col.get(include=["metadatas"])
        ids = res.get("ids") or []
        metas = res.get("metadatas") or []
        out: list[dict] = []
        for chroma_id, meta in zip(ids, metas):
            row = dict(meta or {})
            row["id"] = chroma_id
            if include_superseded or not is_superseded(row):
                out.append(row)
        return out

    def get_units_with_embeddings(
        self, *, include_superseded: bool = False
    ) -> list[dict]:
        """Return knowledge units with embeddings for refine jobs (F2a)."""
        col = self._collection(UNITS)
        res = col.get(include=["metadatas", "embeddings"])
        ids = res.get("ids") or []
        metas = res.get("metadatas") or []
        embs = res.get("embeddings")
        if embs is None:
            embs = []
        out: list[dict] = []
        for i, chroma_id in enumerate(ids):
            meta = dict(metas[i] if i < len(metas) else {})
            meta["id"] = chroma_id
            if not include_superseded and is_superseded(meta):
                continue
            if i >= len(embs):
                continue
            emb = embs[i]
            if emb is None:
                continue
            if hasattr(emb, "tolist"):
                emb = emb.tolist()
            out.append({"id": chroma_id, "metadata": meta, "embedding": emb})
        return out

    def get_unit(self, unit_id: str, *, include_embedding: bool = False) -> dict | None:
        """Fetch a single unit by id, or None if it doesn't exist."""
        include = ["metadatas", "documents"]
        if include_embedding:
            include.append("embeddings")
        res = self._collection(UNITS).get(ids=[unit_id], include=include)
        ids = res.get("ids") or []
        if not ids:
            return None
        metas = res.get("metadatas") or [{}]
        docs = res.get("documents") or [""]
        meta = dict(metas[0] or {})
        meta["id"] = ids[0]
        out: dict = {"id": ids[0], "metadata": meta, "document": docs[0]}
        if include_embedding:
            embs = res.get("embeddings")
            emb = None
            if embs is not None and len(embs) > 0:
                emb = embs[0]
                if emb is not None and hasattr(emb, "tolist"):
                    emb = emb.tolist()
            out["embedding"] = emb
        return out

    def update_unit_metadata(self, unit_id: str, metadata: dict) -> None:
        """Replace metadata for an existing unit."""
        meta = dict(metadata)
        meta["id"] = unit_id
        self._collection(UNITS).update(ids=[unit_id], metadatas=[meta])

    def update_unit(
        self,
        unit_id: str,
        document: str,
        embedding: list[float],
        metadata: dict,
    ) -> None:
        """Replace document, embedding, and metadata for an existing unit."""
        self._collection(UNITS).update(
            ids=[unit_id],
            documents=[document],
            embeddings=[embedding],
            metadatas=[metadata],
        )

    def count_for_source_path(self, collection_name: str, source_path: str) -> int:
        """Count rows in a collection with exact source_path metadata."""
        col = self._collection(collection_name)
        res = col.get(where={"source_path": source_path}, include=[])
        return len(res.get("ids") or [])

    def delete_units_for_source(self, source_path: str) -> int:
        """Remove all knowledge units indexed from ``source_path``."""
        col = self._collection(UNITS)
        res = col.get(where={"source_path": source_path}, include=[])
        ids = res.get("ids") or []
        if ids:
            col.delete(ids=ids)
        return len(ids)

    def preview_supersede_for_source(self, source_path: str) -> list[dict]:
        """Read-only provenance preview of what supersede_units_for_source would tombstone.

        Returns the active (not-yet-superseded) units for ``source_path`` with
        their identity/provenance fields. No writes — safe to call before a
        neutralize run to echo what is about to be tombstoned.
        """
        col = self._collection(UNITS)
        res = col.get(where={"source_path": source_path}, include=["metadatas"])
        ids = res.get("ids") or []
        metas = res.get("metadatas") or []
        preview: list[dict] = []
        for unit_id, meta in zip(ids, metas):
            row = dict(meta or {})
            if is_superseded(row):
                continue
            preview.append(
                {
                    "id": unit_id,
                    "title": row.get("title") or "",
                    "created_at": row.get("created_at") or "",
                    "updated_at": row.get("updated_at") or "",
                }
            )
        return preview

    def supersede_units_for_source(
        self,
        source_path: str,
        *,
        superseded_by: str,
    ) -> int:
        """Tombstone active units for ``source_path`` (refine-style; keeps history)."""
        col = self._collection(UNITS)
        res = col.get(where={"source_path": source_path}, include=["metadatas"])
        ids = res.get("ids") or []
        metas = res.get("metadatas") or []
        n = 0
        from datetime import datetime, timezone

        now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        for unit_id, meta in zip(ids, metas):
            row = dict(meta or {})
            if is_superseded(row):
                continue
            row["superseded"] = True
            row["superseded_by"] = superseded_by
            row["updated_at"] = now
            row["id"] = unit_id
            col.update(ids=[unit_id], metadatas=[row])
            n += 1
        if n:
            invalidate_superseded_cache(self.chroma_dir)
        return n

    def delete_summaries_for_source(self, source_path: str) -> int:
        """Remove all conversation summaries indexed from ``source_path``."""
        col = self._collection(SUMMARIES)
        res = col.get(where={"source_path": source_path}, include=[])
        ids = res.get("ids") or []
        if ids:
            col.delete(ids=ids)
        return len(ids)

    @staticmethod
    def _flatten(res: dict) -> list[dict]:
        out = []
        ids = res.get("ids", [[]])[0]
        docs = res.get("documents", [[]])[0]
        metas = res.get("metadatas", [[]])[0]
        dists = res.get("distances", [[]])[0]
        for i in range(len(ids)):
            out.append(
                {
                    "id": ids[i],
                    "document": docs[i] if i < len(docs) else "",
                    "metadata": metas[i] if i < len(metas) else {},
                    "distance": dists[i] if i < len(dists) else None,
                }
            )
        return out

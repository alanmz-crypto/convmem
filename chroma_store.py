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


def is_superseded(meta: dict) -> bool:
    """True when a unit was tombstoned by chroma_dedupe (F1)."""
    return meta.get("superseded") is True


class ChromaStore:
    def __init__(self, chroma_dir: str):
        self.chroma_dir = str(Path(chroma_dir).expanduser())
        # SegmentAPI + hnswlib compat shim can count() but fails upsert on
        # existing persistent HNSW ("Index seems to be corrupted or unsupported").
        self.client_mode = "PersistentClient"
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
        return self.client.get_or_create_collection(
            name=name, metadata={"hnsw:space": "cosine"}
        )

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
        self._collection(UNITS).upsert(
            ids=[unit_id],
            documents=[document],
            embeddings=[embedding],
            metadatas=[metadata],
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
        try:
            superseded = self._collection(UNITS).get(
                where={"superseded": True}, include=[]
            )
            n_superseded = len(superseded.get("ids") or [])
        except Exception:
            n_superseded = 0
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

    def get_unit(self, unit_id: str) -> dict | None:
        """Fetch a single unit by id, or None if it doesn't exist."""
        res = self._collection(UNITS).get(
            ids=[unit_id], include=["metadatas", "documents"]
        )
        ids = res.get("ids") or []
        if not ids:
            return None
        metas = res.get("metadatas") or [{}]
        docs = res.get("documents") or [""]
        meta = dict(metas[0] or {})
        meta["id"] = ids[0]
        return {"id": ids[0], "metadata": meta, "document": docs[0]}

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

    def delete_units_for_source(self, source_path: str) -> int:
        """Remove all knowledge units indexed from ``source_path``."""
        col = self._collection(UNITS)
        res = col.get(where={"source_path": source_path}, include=[])
        ids = res.get("ids") or []
        if ids:
            col.delete(ids=ids)
        return len(ids)

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

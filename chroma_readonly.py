"""Read-only access helpers for the Chroma on-disk SQLite store."""

from __future__ import annotations

import sqlite3
from collections import defaultdict
from pathlib import Path


def _db_path(chroma_dir: str | Path) -> Path:
    return Path(chroma_dir).expanduser() / "chroma.sqlite3"


def _connect_readonly(db: Path) -> sqlite3.Connection:
    """Open chroma.sqlite3 with URI mode=ro (never creates WAL/SHM or the DB)."""
    if not db.is_file():
        raise FileNotFoundError(str(db))
    uri = f"file:{db.resolve().as_posix()}?mode=ro"
    return sqlite3.connect(uri, uri=True)


def _coerce_value(string_value, int_value, float_value, bool_value):
    if bool_value is not None:
        return bool(bool_value)
    if int_value is not None:
        return int(int_value)
    if float_value is not None:
        return float(float_value)
    if string_value is not None:
        return string_value
    return None


def collection_metadata_rows(chroma_dir: str | Path, collection_name: str) -> list[dict]:
    """Return one dict per embedding_id from the metadata segment of a collection."""
    db = _db_path(chroma_dir)
    conn = _connect_readonly(db)
    conn.row_factory = sqlite3.Row
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT
                e.embedding_id,
                em.key,
                em.string_value,
                em.int_value,
                em.float_value,
                em.bool_value
            FROM embeddings e
            JOIN segments s ON e.segment_id = s.id
            JOIN collections c ON s.collection = c.id
            JOIN embedding_metadata em ON em.id = e.id
            WHERE c.name = ? AND s.scope = 'METADATA'
            ORDER BY e.embedding_id, em.key
            """,
            (collection_name,),
        )
        rows = cur.fetchall()
    finally:
        conn.close()

    grouped: dict[str, dict] = defaultdict(dict)
    for row in rows:
        row_id = row["embedding_id"]
        meta = grouped[row_id]
        meta["id"] = row_id
        key = row["key"]
        if key == "chroma:document":
            meta["document"] = row["string_value"] or ""
            continue
        meta[key] = _coerce_value(
            row["string_value"], row["int_value"], row["float_value"], row["bool_value"]
        )

    return list(grouped.values())


def collection_count(chroma_dir: str | Path, collection_name: str) -> int:
    """Count distinct embeddings in the metadata segment of a collection."""
    db = _db_path(chroma_dir)
    conn = _connect_readonly(db)
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT COUNT(DISTINCT e.embedding_id)
            FROM embeddings e
            JOIN segments s ON e.segment_id = s.id
            JOIN collections c ON s.collection = c.id
            WHERE c.name = ? AND s.scope = 'METADATA'
            """,
            (collection_name,),
        )
        row = cur.fetchone()
    finally:
        conn.close()
    return int(row[0]) if row and row[0] is not None else 0


class ReadonlyUnitStore:
    """ChromaStore-compatible read facade using sqlite only (no PersistentClient writes).

    Safe inside Codex/sandbox when the corpus directory is read-only or writers hold
    the Chroma lock — avoids get_or_create_collection touching the DB.
    """

    def __init__(self, chroma_dir: str | Path):
        from chroma_store import UNITS, is_superseded

        self.chroma_dir = str(Path(chroma_dir).expanduser())
        metas: list[dict] = []
        units: dict[str, dict] = {}
        for meta in collection_metadata_rows(self.chroma_dir, UNITS):
            if is_superseded(meta):
                continue
            chroma_id = (meta.get("id") or "").strip()
            if not chroma_id:
                continue
            row = dict(meta)
            row["id"] = chroma_id
            metas.append(row)
            units[chroma_id] = {
                "id": chroma_id,
                "metadata": row,
                "document": row.get("document") or row.get("title") or "",
            }
        self._metas = metas
        self._units = units

    def units_metadata(self, *, include_superseded: bool = False) -> list[dict]:
        if include_superseded:
            return [dict(m) for m in self._metas]
        from chroma_store import is_superseded

        return [dict(m) for m in self._metas if not is_superseded(m)]

    def get_unit(self, unit_id: str) -> dict | None:
        hit = self._units.get(unit_id.strip())
        if hit:
            return dict(hit)
        for meta in self._metas:
            if (meta.get("ledger_id") or "").strip() == unit_id.strip():
                cid = meta["id"]
                return {
                    "id": cid,
                    "metadata": meta,
                    "document": meta.get("document") or meta.get("title") or "",
                }
        return None


def open_readonly_unit_store(chroma_dir: str | Path) -> ReadonlyUnitStore:
    return ReadonlyUnitStore(chroma_dir)

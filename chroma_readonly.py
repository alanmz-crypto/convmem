"""Read-only access helpers for the Chroma on-disk SQLite store."""

from __future__ import annotations

import sqlite3
from collections import defaultdict
from pathlib import Path


def _db_path(chroma_dir: str | Path) -> Path:
    return Path(chroma_dir).expanduser() / "chroma.sqlite3"


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
    conn = sqlite3.connect(db)
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
    conn = sqlite3.connect(db)
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

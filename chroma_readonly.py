"""Read-only access helpers for the Chroma on-disk SQLite store."""

from __future__ import annotations

import sqlite3
from collections.abc import Collection, Iterator
from pathlib import Path


# ConvMem serves the collections of Chroma's default tenant and database. A collection
# of the same name in another database is a different collection and must never be read
# as the serving one, so identity reads are restricted to the database the client uses.
_SERVING_DATABASE = (
    "c.database_id IN (SELECT id FROM databases "
    "WHERE name = 'default_database' AND tenant_id = 'default_tenant')"
)


def _serving_database(conn: sqlite3.Connection) -> str:
    """SQL restricting alias ``c`` to the serving database.

    Three layouts exist. A modern Chroma catalog has ``databases`` and
    ``collections.database_id``: restrict to the default database. A legacy or hand-made
    schema has neither, so it cannot hold more than one database and needs no restriction.
    One without the other is a damaged catalog in which a same-named collection of another
    database cannot be told apart, so it is refused rather than guessed at.
    """
    has_databases = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'databases'"
    ).fetchone() is not None
    has_column = "database_id" in {row[1] for row in conn.execute("PRAGMA table_info(collections)")}
    if has_databases and has_column:
        return _SERVING_DATABASE
    if not has_databases and not has_column:
        return "1 = 1"
    raise sqlite3.DatabaseError(
        "inconsistent Chroma catalog: "
        f"{'databases table present' if has_databases else 'databases table missing'}, "
        f"{'collections.database_id present' if has_column else 'collections.database_id missing'}"
    )


def journal_mode_is_wal(chroma_dir: str | Path) -> bool:
    """True when ``chroma.sqlite3`` is in WAL mode, read from the file header (no SQLite open).

    Bytes 18 and 19 of the header are the write and read format versions: 2 means WAL.
    """
    try:
        with open(_db_path(chroma_dir), "rb") as handle:
            handle.seek(18)
            return handle.read(2) == b"\x02\x02"
    except OSError:
        return False


def _db_path(chroma_dir: str | Path) -> Path:
    return Path(chroma_dir).expanduser() / "chroma.sqlite3"


def _connect_readonly(db: Path) -> sqlite3.Connection:
    """Open chroma.sqlite3 with URI mode=ro: never creates or writes the DB itself.

    For a database in WAL mode SQLite may still create ``-wal``/``-shm`` beside it even
    when read-only; Chroma writes a rollback journal, so this applies only to a store that
    was switched to WAL (see :func:`journal_mode_is_wal`).
    """
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


def _apply_metadata_row(meta: dict, row: sqlite3.Row, *, include_document: bool) -> None:
    key = row["key"]
    if key == "chroma:document":
        if include_document:
            meta["document"] = row["string_value"] or ""
        return
    meta[key] = _coerce_value(
        row["string_value"], row["int_value"], row["float_value"], row["bool_value"]
    )


def iter_collection_metadata_rows(
    chroma_dir: str | Path,
    collection_name: str,
    *,
    metadata_keys: Collection[str] | None = None,
    include_document: bool = True,
) -> Iterator[dict]:
    """Yield one metadata dict per embedding without fetchall or full grouping.

    ``metadata_keys=None`` is full-mode parity with the historical list helper.
    When keys are provided, SQLite projects only those metadata keys (plus
    ``chroma:document`` when ``include_document`` is true). Cursor and
    connection close on exhaustion, exception, or generator close.
    """
    db = _db_path(chroma_dir)
    conn = _connect_readonly(db)
    conn.row_factory = sqlite3.Row
    cur = None
    try:
        cur = conn.cursor()
        sql_keys: list[str] | None = None
        if metadata_keys is not None:
            sql_keys = [
                key
                for key in metadata_keys
                if key not in {"id", "document", "chroma:document"}
            ]
            if include_document:
                sql_keys.append("chroma:document")
        if sql_keys is not None and not sql_keys:
            cur.execute(
                f"""
                SELECT DISTINCT e.embedding_id
                FROM embeddings e
                JOIN segments s ON e.segment_id = s.id
                JOIN collections c ON s.collection = c.id
                WHERE c.name = ? AND s.scope = 'METADATA' AND {_serving_database(conn)}
                ORDER BY e.embedding_id
                """,
                (collection_name,),
            )
            for row in cur:
                yield {"id": row[0]}
            return
        if sql_keys is None:
            cur.execute(
                f"""
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
                WHERE c.name = ? AND s.scope = 'METADATA' AND {_serving_database(conn)}
                ORDER BY e.embedding_id, em.key
                """,
                (collection_name,),
            )
        else:
            placeholders = ",".join("?" * len(sql_keys))
            cur.execute(
                f"""
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
                WHERE c.name = ? AND s.scope = 'METADATA' AND {_serving_database(conn)}
                  AND em.key IN ({placeholders})
                ORDER BY e.embedding_id, em.key
                """,
                (collection_name, *sql_keys),
            )
        current_id = None
        current_meta: dict = {}
        for row in cur:
            row_id = row["embedding_id"]
            if current_id is not None and row_id != current_id:
                yield current_meta
                current_meta = {}
            current_id = row_id
            current_meta["id"] = row_id
            _apply_metadata_row(current_meta, row, include_document=include_document)
        if current_id is not None:
            yield current_meta
    finally:
        if cur is not None:
            cur.close()
        conn.close()


def unit_document_text(chroma_dir: str | Path, chroma_id: str) -> str | None:
    """Return stored document text for one unit id, or None if missing."""
    from chroma_store import UNITS

    want = (chroma_id or "").strip()
    if not want:
        return None
    db = _db_path(chroma_dir)
    if not db.is_file():
        return None
    conn = _connect_readonly(db)
    try:
        cur = conn.cursor()
        cur.execute(
            f"""
            SELECT em.string_value
            FROM embeddings e
            JOIN segments s ON e.segment_id = s.id
            JOIN collections c ON s.collection = c.id
            JOIN embedding_metadata em ON em.id = e.id
            WHERE c.name = ? AND s.scope = 'METADATA' AND {_serving_database(conn)}
              AND e.embedding_id = ?
              AND em.key = 'chroma:document'
            LIMIT 1
            """,
            (UNITS, want),
        )
        row = cur.fetchone()
    finally:
        conn.close()
    if row is None:
        return None
    return row[0] or ""


def collection_metadata_rows(chroma_dir: str | Path, collection_name: str) -> list[dict]:
    """Return one dict per embedding_id from the metadata segment of a collection."""
    return list(iter_collection_metadata_rows(chroma_dir, collection_name))


def collection_config_metadata(
    chroma_dir: str | Path, collection_name: str
) -> dict:
    """Return collection-level metadata via SQLite mode=ro (no PersistentClient).

    Reads ``collection_metadata`` (column ``str_value``). Missing collection → {}.
    """
    db = _db_path(chroma_dir)
    conn = _connect_readonly(db)
    try:
        cur = conn.cursor()
        cur.execute(
            f"""
            SELECT cm.key, cm.str_value, cm.int_value, cm.float_value, cm.bool_value
            FROM collection_metadata cm
            JOIN collections c ON c.id = cm.collection_id
            WHERE c.name = ? AND {_serving_database(conn)}
            """,
            (collection_name,),
        )
        out: dict = {}
        for key, str_value, int_value, float_value, bool_value in cur.fetchall():
            out[key] = _coerce_value(str_value, int_value, float_value, bool_value)
        return out
    finally:
        conn.close()


def collection_ids(chroma_dir: str | Path, collection_name: str) -> list[str]:
    """Distinct embedding ids in the METADATA segment of a collection (mode=ro).

    Content-level provenance check without loading row metadata.
    """
    db = _db_path(chroma_dir)
    conn = _connect_readonly(db)
    try:
        cur = conn.cursor()
        cur.execute(
            f"""
            SELECT DISTINCT e.embedding_id
            FROM embeddings e
            JOIN segments s ON e.segment_id = s.id
            JOIN collections c ON s.collection = c.id
            WHERE c.name = ? AND s.scope = 'METADATA' AND {_serving_database(conn)}
            """,
            (collection_name,),
        )
        rows = cur.fetchall()
    finally:
        conn.close()
    return [str(r[0]) for r in rows if r[0] is not None]


def collection_row_evidence(chroma_dir: str | Path, collection_name: str) -> int:
    """Rows a collection has left a trace of, however its segments are labelled.

    Distinct embedding ids in *every* segment of the collection (not only the METADATA
    segment that :func:`collection_count` reads) plus any rows in the pending log. Used to
    decide a collection is empty, which must never be concluded from a damaged or relabelled
    segment: zero here means nothing was ever stored, not merely that one view found nothing.
    """
    db = _db_path(chroma_dir)
    if not db.is_file():
        return 0
    conn = _connect_readonly(db)
    try:
        serving = _serving_database(conn)
        row = conn.execute(
            f"SELECT c.id FROM collections c WHERE c.name = ? AND {serving} LIMIT 1",
            (collection_name,),
        ).fetchone()
        if row is None:
            return 0
        stored = conn.execute(
            """
            SELECT COUNT(DISTINCT e.embedding_id)
            FROM embeddings e JOIN segments s ON e.segment_id = s.id
            WHERE s.collection = ?
            """,
            (row[0],),
        ).fetchone()[0]
        logged = 0
        if conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'embeddings_queue'"
        ).fetchone():
            logged = conn.execute(
                "SELECT COUNT(*) FROM embeddings_queue WHERE topic LIKE ?", (f"%/{row[0]}",)
            ).fetchone()[0]
        return int(stored or 0) + int(logged or 0)
    finally:
        conn.close()


def collection_count(chroma_dir: str | Path, collection_name: str) -> int:
    """Count distinct embeddings in the metadata segment of a collection."""
    db = _db_path(chroma_dir)
    conn = _connect_readonly(db)
    try:
        cur = conn.cursor()
        cur.execute(
            f"""
            SELECT COUNT(DISTINCT e.embedding_id)
            FROM embeddings e
            JOIN segments s ON e.segment_id = s.id
            JOIN collections c ON s.collection = c.id
            WHERE c.name = ? AND s.scope = 'METADATA' AND {_serving_database(conn)}
            """,
            (collection_name,),
        )
        row = cur.fetchone()
    finally:
        conn.close()
    return int(row[0]) if row and row[0] is not None else 0


def collection_inventory_snapshot(
    chroma_dir: str | Path, collection_name: str
) -> dict[str, object]:
    """Return current active/historical counts from the readonly metadata view.

    This deliberately mirrors the product meaning of an active unit without
    importing a writable Chroma client: a current row is historical when its
    metadata marks it superseded or deleted.  IDs lacking either marker remain
    active.  The returned IDs are the complete current collection ID set, not
    merely the rows used for candidate classification.
    """
    ids = sorted(set(collection_ids(chroma_dir, collection_name)))
    metadata = {
        str(row.get("id")): row
        for row in collection_metadata_rows(chroma_dir, collection_name)
        if row.get("id") is not None
    }
    historical_ids = {
        entity_id
        for entity_id in ids
        if bool(metadata.get(entity_id, {}).get("superseded"))
        or bool(metadata.get(entity_id, {}).get("deleted"))
    }
    total = len(ids)
    historical = len(historical_ids)
    return {
        "ids": ids,
        "active_unit_count": total - historical,
        "historical_unit_count": historical,
        "total_unit_count": total,
    }


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
        if not _db_path(self.chroma_dir).is_file():
            self._metas = metas
            self._units = units
            return
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

    def active_units_for_ledger_id(self, ledger_id: str) -> list[dict]:
        from chroma_store import is_superseded

        lid = (ledger_id or "").strip()
        return [
            dict(m)
            for m in self._metas
            if (m.get("ledger_id") or "").strip() == lid and not is_superseded(m)
        ]

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


def count_for_source_path(
    chroma_dir: str | Path, collection_name: str, source_path: str
) -> int:
    """Count metadata rows with an exact source_path using SQLite mode=ro.

    Missing database or collection is zero. Never creates files or opens a
    writable Chroma client.
    """
    db = _db_path(chroma_dir)
    if not db.is_file():
        return 0
    return sum(
        1
        for row in collection_metadata_rows(chroma_dir, collection_name)
        if row.get("source_path") == source_path
    )


def ids_for_source_path(
    chroma_dir: str | Path, collection_name: str, source_path: str
) -> list[str]:
    """Return embedding ids whose metadata source_path matches exactly."""
    db = _db_path(chroma_dir)
    if not db.is_file():
        return []
    return sorted(
        {
            str(row.get("id"))
            for row in collection_metadata_rows(chroma_dir, collection_name)
            if row.get("source_path") == source_path and row.get("id") is not None
        }
    )


def collection_uuid(chroma_dir: str | Path, collection_name: str) -> str | None:
    """Return the immutable Chroma collection UUID (collections.id) via mode=ro.

    Missing collection or DB → None. Never creates files or opens PersistentClient.
    """
    db = _db_path(chroma_dir)
    if not db.is_file():
        return None
    conn = _connect_readonly(db)
    try:
        cur = conn.cursor()
        cur.execute(
            f"SELECT c.id FROM collections c WHERE c.name = ? AND {_serving_database(conn)} LIMIT 1",
            (collection_name,),
        )
        row = cur.fetchone()
    finally:
        conn.close()
    if not row or row[0] is None:
        return None
    return str(row[0])


def collection_dimension(chroma_dir: str | Path, collection_name: str) -> int | None:
    """Return the vector dimension Chroma itself recorded for a collection (mode=ro).

    Chroma sets ``collections.dimension`` when the first vector arrives, so an
    empty collection, a missing collection and a missing DB all return None.
    This is the store's own measurement, never a configured or guessed value.
    """
    db = _db_path(chroma_dir)
    if not db.is_file():
        return None
    conn = _connect_readonly(db)
    try:
        cur = conn.cursor()
        cur.execute(
            f"SELECT c.dimension FROM collections c WHERE c.name = ? AND {_serving_database(conn)} LIMIT 1",
            (collection_name,),
        )
        row = cur.fetchone()
    finally:
        conn.close()
    if not row or row[0] is None:
        return None
    return int(row[0])

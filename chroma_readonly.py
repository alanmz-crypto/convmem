"""Read-only access helpers for the Chroma on-disk SQLite store."""

from __future__ import annotations

import sqlite3
import subprocess
import sys
from dataclasses import dataclass
from collections.abc import Collection, Iterator, Sequence
from pathlib import Path


# ConvMem serves the collections of Chroma's default tenant and database. A collection
# of the same name in another database is a different collection and must never be read
# as the serving one, so identity reads are restricted to the database the client uses.
_SERVING_DATABASE = (
    "c.database_id IN (SELECT id FROM databases "
    "WHERE name = 'default_database' AND tenant_id = 'default_tenant')"
)


def _serving_database(conn: sqlite3.Connection, name: str) -> str:
    """SQL restricting alias ``c`` to the serving database.

    Three layouts exist. A modern Chroma catalog has ``databases`` and
    ``collections.database_id``: restrict to the default database. A legacy or hand-made
    schema has neither, so it cannot hold more than one database and needs no restriction.
    One without the other is a damaged catalog in which a same-named collection of another
    database cannot be told apart, so it is refused rather than guessed at. ``name`` is the
    collection about to be read: more than one match within the serving database is refused.
    """
    has_databases = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'databases'"
    ).fetchone() is not None
    has_column = "database_id" in {row[1] for row in conn.execute("PRAGMA table_info(collections)")}
    if has_databases and has_column:
        fragment = _SERVING_DATABASE
    elif not has_databases and not has_column:
        fragment = "1 = 1"
    else:
        fragment = None
    if fragment is not None:
        # A name that matches two collections cannot be read as one: uuid, dimension and
        # metadata would each pick a different one. Real Chroma enforces UNIQUE(name,
        # database_id); a hand-made or damaged schema may not.
        matches = conn.execute(
            f"SELECT COUNT(*) FROM collections c WHERE c.name = ? AND {fragment}", (name,)
        ).fetchone()[0]
        if matches > 1:
            raise sqlite3.DatabaseError(f"ambiguous catalog: {matches} collections are named {name!r}")
        return fragment
    raise sqlite3.DatabaseError(
        "inconsistent Chroma catalog: "
        f"{'databases table present' if has_databases else 'databases table missing'}, "
        f"{'collections.database_id present' if has_column else 'collections.database_id missing'}"
    )


_HEADER_PROBE = (
    "import sys\n"
    "try:\n"
    "    handle = open(sys.argv[1], 'rb')\n"
    "except FileNotFoundError:\n"
    "    print('missing'); raise SystemExit(0)\n"
    "print(handle.read(20).hex())\n"
)


class HeaderProbeError(OSError):
    """The database header could not be read, so nothing can be said about it (not "unsafe", not "safe")."""


def may_create_wal_files(chroma_dir: str | Path) -> bool:
    """True unless ``chroma.sqlite3`` is verifiably a plain rollback-journal SQLite file.

    A pre-flight for a command that promises to leave a directory untouched: SQLite may create
    ``-wal``/``-shm`` beside a WAL database even for a read-only open. Bytes 18 and 19 of the
    header are the write and read format versions: 1 is the rollback journal, 2 is WAL, and SQLite
    opens a file as WAL when *either* byte says so, so only ``01 01`` is safe. A missing file is not
    a risk (nothing is opened); an unreadable, short or non-SQLite header is, because it cannot be
    vouched for.

    The header is read by a child process. Reading it here would ``close()`` a descriptor on the
    database, and on POSIX that cancels every lock this process holds on the file through SQLite
    (see :func:`_connect_readonly`), so it is safe to call from a process that has the file open.

    Raises :class:`HeaderProbeError` when the probe itself fails (no child process allowed, a timeout,
    an unexpected answer): that is not evidence the file is safe or unsafe, and the cause is kept.
    """
    db = _db_path(chroma_dir)
    try:
        done = subprocess.run(
            [sys.executable, "-I", "-S", "-c", _HEADER_PROBE, str(db)],
            capture_output=True, text=True, timeout=30, check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise HeaderProbeError(
            f"could not run the header probe for {db.name}: {type(exc).__name__}: {exc}"
        ) from exc
    out = done.stdout.strip()
    if done.returncode != 0 or not out:
        raise HeaderProbeError(
            f"the header probe for {db.name} failed (exit {done.returncode}): "
            f"{done.stderr.strip()[:200] or 'no output'}"
        )
    if out == "missing":
        return False
    try:
        header = bytes.fromhex(out)
    except ValueError as exc:  # anything but the hex of the first bytes, e.g. a wrapper's banner
        raise HeaderProbeError(f"the header probe for {db.name} answered {out[:60]!r}, not a header") from exc
    return header[:16] != b"SQLite format 3\x00" or header[18:20] != b"\x01\x01"


def _db_path(chroma_dir: str | Path) -> Path:
    return Path(chroma_dir).expanduser() / "chroma.sqlite3"


def _connect_readonly(db: Path) -> sqlite3.Connection:
    """Open chroma.sqlite3 with URI mode=ro: never creates or writes the DB itself.

    Opens a read transaction before returning, so every query a reader makes on this connection,
    including the ambiguity check that guards it, sees one snapshot; closing the connection ends it.

    Nothing here opens the file with an ordinary ``open()``. On POSIX, closing *any* descriptor for a
    file cancels every lock the process holds on it, including those of SQLite connections in the
    same process (Chroma's own, in a process that serves queries), so a header probe on a path this
    process also has open through SQLite silently releases another transaction's lock.
    """
    if not db.is_file():
        raise FileNotFoundError(str(db))
    # as_uri() percent-encodes the path: a '#' or '?' in a directory name would otherwise end
    # the path early, drop "mode=ro" and open (and create) a different, writable file.
    conn = sqlite3.connect(db.resolve().as_uri() + "?mode=ro", uri=True)
    conn.execute("BEGIN")
    return conn


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
                WHERE c.name = ? AND s.scope = 'METADATA' AND {_serving_database(conn, collection_name)}
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
                WHERE c.name = ? AND s.scope = 'METADATA' AND {_serving_database(conn, collection_name)}
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
                WHERE c.name = ? AND s.scope = 'METADATA' AND {_serving_database(conn, collection_name)}
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
            WHERE c.name = ? AND s.scope = 'METADATA' AND {_serving_database(conn, UNITS)}
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


def _metadata_in(conn: sqlite3.Connection, collection_name: str) -> dict:
    out: dict = {}
    for key, str_value, int_value, float_value, bool_value in conn.execute(
        f"""
        SELECT cm.key, cm.str_value, cm.int_value, cm.float_value, cm.bool_value
        FROM collection_metadata cm
        JOIN collections c ON c.id = cm.collection_id
        WHERE c.name = ? AND {_serving_database(conn, collection_name)}
        """,
        (collection_name,),
    ).fetchall():
        out[key] = _coerce_value(str_value, int_value, float_value, bool_value)
    return out


def collection_config_metadata(
    chroma_dir: str | Path, collection_name: str
) -> dict:
    """Return collection-level metadata via SQLite mode=ro (no PersistentClient).

    Reads ``collection_metadata`` (column ``str_value``). Missing collection → {}.
    """
    conn = _connect_readonly(_db_path(chroma_dir))
    try:
        return _metadata_in(conn, collection_name)
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
            WHERE c.name = ? AND s.scope = 'METADATA' AND {_serving_database(conn, collection_name)}
            """,
            (collection_name,),
        )
        rows = cur.fetchall()
    finally:
        conn.close()
    return [str(r[0]) for r in rows if r[0] is not None]


def _evidence_in(conn: sqlite3.Connection, collection_name: str) -> int:
    uuid = _uuid_in(conn, collection_name)
    if uuid is None:
        return 0
    stored = conn.execute(
        """
        SELECT COUNT(DISTINCT e.embedding_id)
        FROM embeddings e JOIN segments s ON e.segment_id = s.id
        WHERE s.collection = ?
        """,
        (uuid,),
    ).fetchone()[0]
    # A Chroma collection has exactly two segments (vector and metadata). If they cannot both
    # be found, if a segment belongs to no collection, or if any stored row belongs to no
    # segment, rows may sit where this count cannot see them: that is evidence of rows, not of
    # emptiness.
    segments = conn.execute("SELECT COUNT(*) FROM segments WHERE collection = ?", (uuid,)).fetchone()[0]
    orphan_segments = conn.execute(
        "SELECT COUNT(*) FROM segments s WHERE NOT EXISTS (SELECT 1 FROM collections c WHERE c.id = s.collection)"
    ).fetchone()[0]
    orphan_rows = conn.execute(
        "SELECT COUNT(*) FROM embeddings e WHERE NOT EXISTS (SELECT 1 FROM segments s WHERE s.id = e.segment_id)"
    ).fetchone()[0]
    unaccounted = int(segments != 2) + int(orphan_segments > 0) + int(orphan_rows > 0)
    logged = 0
    if conn.execute("SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'embeddings_queue'").fetchone():
        logged = conn.execute(
            "SELECT COUNT(*) FROM embeddings_queue WHERE topic LIKE ?", (f"%/{uuid}",)
        ).fetchone()[0]
    return int(stored or 0) + int(logged or 0) + unaccounted


def collection_row_evidence(chroma_dir: str | Path, collection_name: str) -> int:
    """Rows a collection has left a trace of, however its segments are labelled.

    Distinct embedding ids in *every* segment of the collection (not only the METADATA
    segment that :func:`collection_count` reads) plus any rows in the pending log. Used to
    decide a collection is empty, which must never be concluded from a damaged or relabelled
    segment: zero here means nothing was ever stored, not merely that one view found nothing.
    A collection whose two segments cannot both be found, a segment that belongs to no
    collection, and a stored row that belongs to no segment each count as one unaccounted row.
    """
    db = _db_path(chroma_dir)
    if not db.is_file():
        return 0
    conn = _connect_readonly(db)
    try:
        return _evidence_in(conn, collection_name)
    finally:
        conn.close()


@dataclass(frozen=True)
class CollectionFacts:
    """What one read transaction found out about one collection."""

    uuid: str | None
    dimension: int | None
    metadata: dict
    row_evidence: int | None  # only read when no dimension is recorded


def collection_identity_facts_many(
    chroma_dir: str | Path, collection_names: Sequence[str]
) -> dict[str, CollectionFacts | Exception]:
    """Facts for several collections from one connection and one read transaction.

    A verdict about several collections must describe one moment: read one collection at a time and
    a catalog that swaps their stamps in between yields a combined PASS that no committed state
    deserves. A failure reading one collection (an ambiguous or inconsistent catalog, a malformed
    value) is returned for that collection so it cannot hide another's; an unreadable *database*
    raises. The read lock is held for as long as it takes to read these facts and no longer.
    """
    conn = _connect_readonly(_db_path(chroma_dir))  # a missing database is unreadable, not "empty"
    try:
        out: dict[str, CollectionFacts | Exception] = {}
        for name in collection_names:
            try:
                uuid = _uuid_in(conn, name)
                if uuid is None:
                    out[name] = CollectionFacts(None, None, {}, None)
                    continue
                dimension = _dimension_in(conn, name)
                out[name] = CollectionFacts(
                    uuid,
                    dimension,
                    _metadata_in(conn, name),
                    _evidence_in(conn, name) if dimension is None else None,
                )
            except (sqlite3.Error, ValueError, TypeError) as exc:
                out[name] = exc
        return out
    finally:
        conn.close()


def collection_identity_facts(chroma_dir: str | Path, collection_name: str) -> CollectionFacts:
    """:func:`collection_identity_facts_many` for one collection; its failure is raised."""
    fact = collection_identity_facts_many(chroma_dir, (collection_name,))[collection_name]
    if isinstance(fact, Exception):
        raise fact
    return fact


def _sequence(value: object) -> int:
    """A sequence id as an integer, whether stored as one or as a historical big-endian blob."""
    if isinstance(value, (bytes, bytearray)):
        return int.from_bytes(value, "big")
    return int(value or 0)  # type: ignore[call-overload]


def collection_change_fingerprint(chroma_dir: str | Path, collection_name: str) -> tuple[int, int, int, int]:
    """(rows, newest sequence, sum of sequences, newest log sequence) of a collection's stored rows.

    Every write Chroma accepts gives a row a new sequence number, so any change to a collection,
    including an in-place repair of one vector, changes this fingerprint. Comparing it before and
    after a long read says whether the collection stayed the same while it was being read.
    """
    conn = _connect_readonly(_db_path(chroma_dir))
    try:
        uuid = _uuid_in(conn, collection_name)
        # Sequence ids are read and decoded here, not aggregated in SQL: chromadb < 0.5 stored them
        # as big-endian blobs, which SQL's MAX and SUM treat as text and zero respectively.
        sequences = [
            _sequence(row[0])
            for row in conn.execute(
                "SELECT e.seq_id FROM embeddings e JOIN segments s ON e.segment_id = s.id WHERE s.collection = ?",
                (uuid,),
            )
        ]
        logged = 0
        if conn.execute("SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'embeddings_queue'").fetchone():
            logged = max(
                (
                    _sequence(row[0])
                    for row in conn.execute("SELECT seq_id FROM embeddings_queue WHERE topic LIKE ?", (f"%/{uuid}",))
                ),
                default=0,
            )
        return len(sequences), max(sequences, default=0), sum(sequences), logged
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
            WHERE c.name = ? AND s.scope = 'METADATA' AND {_serving_database(conn, collection_name)}
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


def _uuid_in(conn: sqlite3.Connection, collection_name: str) -> str | None:
    row = conn.execute(
        "SELECT c.id FROM collections c "
        f"WHERE c.name = ? AND {_serving_database(conn, collection_name)} LIMIT 1",
        (collection_name,),
    ).fetchone()
    return None if not row or row[0] is None else str(row[0])


def collection_uuid(chroma_dir: str | Path, collection_name: str) -> str | None:
    """Return the immutable Chroma collection UUID (collections.id) via mode=ro.

    Missing collection or DB → None. Never creates files or opens PersistentClient.
    """
    db = _db_path(chroma_dir)
    if not db.is_file():
        return None
    conn = _connect_readonly(db)
    try:
        return _uuid_in(conn, collection_name)
    finally:
        conn.close()


def _dimension_in(conn: sqlite3.Connection, collection_name: str) -> int | None:
    row = conn.execute(
        "SELECT c.dimension FROM collections c "
        f"WHERE c.name = ? AND {_serving_database(conn, collection_name)} LIMIT 1",
        (collection_name,),
    ).fetchone()
    if not row or row[0] is None:
        return None
    try:
        return int(row[0])
    except (TypeError, ValueError) as exc:
        raise sqlite3.DatabaseError(f"collection {collection_name!r} records the dimension {row[0]!r}") from exc


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
        return _dimension_in(conn, collection_name)
    finally:
        conn.close()

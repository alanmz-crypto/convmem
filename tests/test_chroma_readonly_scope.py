"""Reading collection identity safely: serving database, ambiguity, URI characters, emptiness evidence.

Split out of ``test_chroma_embed_identity`` (which is at the module-size limit). Hermetic: every
store lives in ``tmp_path``; the helpers under test only ever read, through SQLite ``mode=ro``.
"""

# pylint: disable=protected-access,too-many-arguments

from __future__ import annotations

import subprocess
import sqlite3
import sys
from pathlib import Path

import chromadb
import pytest

import chroma_readonly
from chroma_embed_identity import FAIL, WARN, check_embed_identity
from chroma_store import EMBED_MODEL_KEY, SUMMARIES, UNITS, ChromaStore
from tests.test_chroma_embed_identity import COSINE, MODEL, _store

def test_a_same_named_collection_in_another_database_cannot_pass_for_the_serving_one(
    tmp_path: Path,
) -> None:
    from chromadb import AdminClient
    from chromadb.config import Settings

    from chroma_readonly import collection_config_metadata, collection_uuid

    chroma = tmp_path / "chroma"
    serving = chromadb.PersistentClient(path=str(chroma))
    wrong = serving.get_or_create_collection(
        UNITS, metadata={**COSINE, EMBED_MODEL_KEY: "wrong-model"}
    )
    wrong.upsert(ids=["a"], embeddings=[[1.0, 0.0]], documents=["x"])
    AdminClient(Settings(is_persistent=True, persist_directory=str(chroma))).create_database("other")
    other = chromadb.PersistentClient(path=str(chroma), database="other")
    other.get_or_create_collection(
        UNITS, metadata={**COSINE, EMBED_MODEL_KEY: "wanted-model"}
    ).upsert(ids=["b"], embeddings=[[0.0, 1.0]], documents=["y"])

    assert collection_uuid(chroma, UNITS) == str(wrong.id)
    assert collection_config_metadata(chroma, UNITS)[EMBED_MODEL_KEY] == "wrong-model"
    verdict = check_embed_identity(chroma, "wanted-model", strict=True)
    assert verdict.status == FAIL and "wrong-model" in verdict.detail


def test_a_schema_without_databases_is_read_as_before(tmp_path: Path) -> None:
    """Hand-made or very old SQLite files have no databases table: nothing to restrict."""
    from chroma_readonly import collection_config_metadata, collection_dimension, collection_uuid

    db = tmp_path / "chroma"
    db.mkdir()
    with sqlite3.connect(db / "chroma.sqlite3") as con:
        con.executescript(
            """
            CREATE TABLE collections (id TEXT, name TEXT, dimension INTEGER);
            CREATE TABLE collection_metadata (collection_id TEXT, key TEXT, str_value TEXT,
                int_value INTEGER, float_value REAL, bool_value INTEGER);
            INSERT INTO collections VALUES ('uuid-1', 'knowledge_units', 8);
            INSERT INTO collection_metadata VALUES ('uuid-1', 'convmem:embed_model', 'm', NULL, NULL, NULL);
            """
        )

    assert collection_uuid(db, UNITS) == "uuid-1"
    assert collection_dimension(db, UNITS) == 8
    assert collection_config_metadata(db, UNITS)[EMBED_MODEL_KEY] == "m"


def _two_databases(chroma: Path, first_stamp: str, other_stamp: str, *, tenant: str | None = None):
    """The serving collection stamped ``first_stamp``; a same-named one elsewhere stamped ``other_stamp``."""
    from chromadb import AdminClient
    from chromadb.config import Settings

    serving = chromadb.PersistentClient(path=str(chroma))
    wrong = serving.get_or_create_collection(UNITS, metadata={**COSINE, EMBED_MODEL_KEY: first_stamp})
    wrong.upsert(ids=["a"], embeddings=[[1.0, 0.0]], documents=["x"])
    admin = AdminClient(Settings(is_persistent=True, persist_directory=str(chroma)))
    if tenant is None:
        admin.create_database("other")
        client = chromadb.PersistentClient(path=str(chroma), database="other")
    else:
        admin.create_tenant(tenant)
        admin.create_database("default_database", tenant=tenant)
        client = chromadb.PersistentClient(path=str(chroma), tenant=tenant, database="default_database")
    client.get_or_create_collection(UNITS, metadata={**COSINE, EMBED_MODEL_KEY: other_stamp}).upsert(
        ids=["b"], embeddings=[[0.0, 1.0]], documents=["y"]
    )
    return wrong


def test_a_same_named_collection_in_another_tenant_cannot_pass_for_the_serving_one(
    tmp_path: Path,
) -> None:
    """The other tenant has its own 'default_database': only the tenant tells them apart."""
    chroma = tmp_path / "chroma"
    _two_databases(chroma, "wrong-model", "wanted-model", tenant="other_tenant")

    verdict = check_embed_identity(chroma, "wanted-model", strict=True)

    assert verdict.status == FAIL and "wrong-model" in verdict.detail


@pytest.mark.parametrize("damage", ["databases-table-renamed", "database-id-column-dropped"])
def test_an_inconsistent_catalog_is_refused_not_read_as_a_single_database(
    tmp_path: Path, damage: str
) -> None:
    chroma = tmp_path / "chroma"
    _two_databases(chroma, "wrong-model", "wanted-model")
    with sqlite3.connect(chroma / "chroma.sqlite3") as con:  # a scratch store: simulate damage
        if damage == "databases-table-renamed":
            con.execute("ALTER TABLE databases RENAME TO databases_gone")
        else:
            con.execute("ALTER TABLE collections RENAME COLUMN database_id TO database_gone")

    default = check_embed_identity(chroma, "wanted-model")
    strict = check_embed_identity(chroma, "wanted-model", strict=True)

    assert default.status == WARN and strict.status == FAIL  # never PASS for the wrong database
    assert "inconsistent Chroma catalog" in strict.detail and "DatabaseError" in strict.detail


def test_sibling_read_helpers_do_not_mix_in_another_databases_rows(tmp_path: Path) -> None:
    from chromadb import AdminClient
    from chromadb.config import Settings

    from chroma_readonly import collection_inventory_snapshot, count_for_source_path, ids_for_source_path

    chroma = tmp_path / "chroma"
    serving = chromadb.PersistentClient(path=str(chroma))
    serving.get_or_create_collection(UNITS).upsert(
        ids=["u1"], embeddings=[[1.0, 0.0]], documents=["x"], metadatas=[{"source_path": "a.md"}]
    )
    AdminClient(Settings(is_persistent=True, persist_directory=str(chroma))).create_database("other")
    chromadb.PersistentClient(path=str(chroma), database="other").get_or_create_collection(UNITS).upsert(
        ids=["u1", "u2"],
        embeddings=[[0.0, 1.0]] * 2,
        documents=["y", "z"],
        metadatas=[{"source_path": "a.md", "superseded": True}, {"source_path": "only-other.md"}],
    )

    snapshot = collection_inventory_snapshot(chroma, UNITS)
    assert snapshot["active_unit_count"] == 1 and snapshot["historical_unit_count"] == 0
    assert ids_for_source_path(chroma, UNITS, "a.md") == ["u1"]
    assert ids_for_source_path(chroma, UNITS, "only-other.md") == []
    assert count_for_source_path(chroma, UNITS, "only-other.md") == 0


def _serving_and_other_database(chroma: Path) -> None:
    """u1 in both databases (the other's superseded); u2 and a document only in the other."""
    from chromadb import AdminClient
    from chromadb.config import Settings

    serving = chromadb.PersistentClient(path=str(chroma))
    serving.get_or_create_collection(UNITS).upsert(
        ids=["u1"], embeddings=[[1.0, 0.0]], documents=["serving document"],
        metadatas=[{"source_path": "a.md"}],
    )
    AdminClient(Settings(is_persistent=True, persist_directory=str(chroma))).create_database("other")
    chromadb.PersistentClient(path=str(chroma), database="other").get_or_create_collection(UNITS).upsert(
        ids=["u1", "u2", "u3"],
        embeddings=[[0.0, 1.0]] * 3,
        documents=["other document", "only other", "also only other"],
        metadatas=[{"source_path": "a.md"}, {"source_path": "b.md"}, {"source_path": "c.md"}],
    )


def test_every_read_variant_returns_only_the_serving_databases_rows(tmp_path: Path) -> None:
    from chroma_readonly import collection_count, iter_collection_metadata_rows, unit_document_text

    chroma = tmp_path / "chroma"
    _serving_and_other_database(chroma)

    ids_only = list(iter_collection_metadata_rows(chroma, UNITS, metadata_keys={"id"}, include_document=False))
    projected = list(iter_collection_metadata_rows(chroma, UNITS, metadata_keys={"source_path"}))
    everything = list(iter_collection_metadata_rows(chroma, UNITS))

    assert sorted(r["id"] for r in ids_only) == ["u1"]
    assert sorted(r["id"] for r in projected) == ["u1"]
    assert sorted(r["id"] for r in everything) == ["u1"]
    assert unit_document_text(chroma, "u1") == "serving document"
    assert unit_document_text(chroma, "u2") is None  # exists only in the other database
    assert collection_count(chroma, UNITS) == 1


def test_stored_rows_in_a_relabelled_segment_withhold_the_drop_advice_even_with_no_log(
    tmp_path: Path,
) -> None:
    """The log is a second trace; the stored rows must stand on their own as evidence."""
    chroma = tmp_path / "chroma"
    _store(chroma, UNITS)
    with sqlite3.connect(chroma / "chroma.sqlite3") as con:
        con.execute("DELETE FROM embeddings_queue")  # as after compaction: no log left
        con.execute("UPDATE collections SET dimension = NULL")
        con.execute("UPDATE segments SET scope = 'BROKEN'")

    from chroma_readonly import collection_row_evidence

    assert collection_row_evidence(chroma, UNITS) > 0
    assert "can be dropped" not in check_embed_identity(chroma, MODEL).detail


@pytest.mark.parametrize("name", ["restore#1", "a?b", "100%", "sp ace", "x#y?z%20"])
def test_a_directory_name_with_uri_characters_is_read_in_place_and_nothing_is_created(
    tmp_path: Path, name: str
) -> None:
    from chroma_readonly import collection_uuid

    chroma = tmp_path / name / "chroma"
    _store(chroma, UNITS)
    before = sorted(p.name for p in tmp_path.iterdir())

    assert collection_uuid(chroma, UNITS) is not None  # read the real file, with mode=ro
    assert sorted(p.name for p in tmp_path.iterdir()) == before  # no truncated-path sibling created


def _legacy_catalog_with_two_collections(chroma: Path, names: tuple[str, str]) -> None:
    chroma.mkdir(parents=True)
    with sqlite3.connect(chroma / "chroma.sqlite3") as con:
        con.executescript(
            """
            CREATE TABLE collections (id TEXT, name TEXT, dimension INTEGER);
            CREATE TABLE collection_metadata (collection_id TEXT, key TEXT, str_value TEXT,
                int_value INTEGER, float_value REAL, bool_value INTEGER);
            """
        )
        for ident, stamp in zip(("uuid-old", "uuid-new"), names):
            con.execute("INSERT INTO collections VALUES (?, 'knowledge_units', 8)", (ident,))
            con.execute(
                "INSERT INTO collection_metadata VALUES (?, 'convmem:embed_model', ?, NULL, NULL, NULL)",
                (ident, stamp),
            )


def test_a_legacy_catalog_with_two_collections_of_one_name_is_refused_not_combined(
    tmp_path: Path,
) -> None:
    """Reviewed: uuid picked one collection, the metadata another, and strict said PASS."""
    from chroma_readonly import collection_uuid

    chroma = tmp_path / "chroma"
    _legacy_catalog_with_two_collections(chroma, ("old-model", "new-model"))

    with pytest.raises(sqlite3.DatabaseError, match="ambiguous"):
        collection_uuid(chroma, UNITS)
    strict = check_embed_identity(chroma, "new-model", strict=True)
    assert strict.status == FAIL and "ambiguous" in strict.detail


def test_a_segment_that_points_at_no_collection_withholds_the_drop_advice(tmp_path: Path) -> None:
    from chroma_readonly import collection_row_evidence

    chroma = tmp_path / "chroma"
    _store(chroma, UNITS)
    with sqlite3.connect(chroma / "chroma.sqlite3") as con:  # scratch: keep the row, lose the link
        con.execute("DELETE FROM embeddings_queue")
        con.execute("UPDATE collections SET dimension = NULL")
        con.execute("UPDATE segments SET collection = 'no-such-collection' WHERE scope = 'METADATA'")

    assert collection_row_evidence(chroma, UNITS) > 0
    default = check_embed_identity(chroma, MODEL)
    assert "can be dropped" not in default.detail and default.status == WARN
    assert check_embed_identity(chroma, MODEL, strict=True).status == FAIL


def test_a_missing_segment_alone_withholds_the_drop_advice(tmp_path: Path) -> None:
    from chroma_readonly import collection_row_evidence

    chroma = tmp_path / "chroma"
    _store(chroma, UNITS)
    with sqlite3.connect(chroma / "chroma.sqlite3") as con:  # the metadata segment row is gone
        con.execute("DELETE FROM embeddings_queue")
        con.execute("UPDATE collections SET dimension = NULL")
        con.execute("DELETE FROM segments WHERE scope = 'METADATA'")
        assert con.execute("SELECT COUNT(*) FROM segments s WHERE NOT EXISTS "
                           "(SELECT 1 FROM collections c WHERE c.id = s.collection)").fetchone()[0] == 0

    assert collection_row_evidence(chroma, UNITS) > 0  # one segment short, and no orphan to blame
    assert "can be dropped" not in check_embed_identity(chroma, MODEL).detail


def test_an_orphan_segment_alone_withholds_the_drop_advice(tmp_path: Path) -> None:
    from chroma_readonly import collection_row_evidence

    chroma = tmp_path / "chroma"
    with ChromaStore(str(chroma)) as store:
        store._collection(UNITS)  # empty, with both of its own segments
    with sqlite3.connect(chroma / "chroma.sqlite3") as con:
        con.execute("INSERT INTO segments (id, type, scope, collection) VALUES ('s', 't', 'VECTOR', 'nowhere')")

    assert collection_row_evidence(chroma, UNITS) > 0  # its rows might be the orphan's
    assert "can be dropped" not in check_embed_identity(chroma, MODEL).detail


def test_a_genuinely_empty_unmarked_collection_still_gets_the_drop_advice(tmp_path: Path) -> None:
    """Positive control: the segment accounting must not turn every empty collection unsafe."""
    from chroma_readonly import collection_row_evidence

    chroma = tmp_path / "chroma"
    with ChromaStore(str(chroma)) as store:
        store._collection(UNITS)  # created by a read, never written

    assert collection_row_evidence(chroma, UNITS) == 0
    assert "can be dropped" in check_embed_identity(chroma, MODEL).detail


def test_a_trace_in_the_log_alone_is_enough_to_withhold_the_drop_advice(tmp_path: Path) -> None:
    from chroma_readonly import collection_row_evidence

    chroma = tmp_path / "chroma"
    _store(chroma, UNITS)
    with sqlite3.connect(chroma / "chroma.sqlite3") as con:  # scratch: no stored row, a log row remains
        con.execute("DELETE FROM embeddings")
        con.execute("UPDATE collections SET dimension = NULL")

    assert collection_row_evidence(chroma, UNITS) > 0  # only the pending log still shows it
    assert "can be dropped" not in check_embed_identity(chroma, MODEL).detail


def test_the_facts_for_a_verdict_come_from_one_read_transaction(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Reviewed: separate connections let a collection be replaced between the UUID and the
    stamp, giving a verdict about a collection that never existed. Here a writer tries to replace it
    after the first query; inside one read transaction it cannot commit."""
    chroma = tmp_path / "chroma"
    _store(chroma, UNITS)
    outcomes: list[str] = []
    real_connect = chroma_readonly._connect_readonly

    def connect(db: Path) -> sqlite3.Connection:
        conn = real_connect(db)
        seen: list[str] = []

        def trace(statement: str) -> None:
            seen.append(statement)
            if len(seen) == 3 and not outcomes:  # BEGIN and a first query are done: a read lock is held
                writer = sqlite3.connect(db, timeout=0)
                try:
                    writer.execute("UPDATE collections SET name = 'replaced'")
                    writer.commit()
                    outcomes.append("replaced")
                except sqlite3.OperationalError as exc:
                    outcomes.append(str(exc))
                finally:
                    writer.close()

        conn.set_trace_callback(trace)
        return conn

    monkeypatch.setattr(chroma_readonly, "_connect_readonly", connect)

    facts = chroma_readonly.collection_identity_facts(chroma, UNITS)

    assert outcomes == ["database is locked"]
    assert facts.uuid is not None and facts.dimension is not None and facts.metadata


def test_readers_still_read_a_wal_mode_store(tmp_path: Path) -> None:
    """Reviewed: a connector that refused WAL broke healthy readers (the keyword fallback).

    Refusing a WAL file is a promise only the attestation command makes, as a pre-flight in a
    process that holds no SQLite connection to it. Every other reader keeps reading such a store
    (and, as before this branch, SQLite may create -wal/-shm beside it)."""
    chroma = tmp_path / "chroma"
    _store(chroma, UNITS, embed_model=MODEL)
    with sqlite3.connect(chroma / "chroma.sqlite3") as con:
        con.execute("PRAGMA journal_mode=WAL")

    assert chroma_readonly.collection_uuid(chroma, UNITS) is not None
    assert chroma_readonly.may_create_wal_files(chroma) is True  # the pre-flight still says so
    assert check_embed_identity(chroma, MODEL).status == "pass"


def test_a_stored_row_that_belongs_to_no_segment_withholds_the_drop_advice(tmp_path: Path) -> None:
    chroma = tmp_path / "chroma"
    _store(chroma, UNITS)
    with sqlite3.connect(chroma / "chroma.sqlite3") as con:  # both segments stay; the row loses its own
        con.execute("DELETE FROM embeddings_queue")
        con.execute("UPDATE collections SET dimension = NULL")
        con.execute("UPDATE embeddings SET segment_id = 'no-such-segment'")

    assert chroma_readonly.collection_row_evidence(chroma, UNITS) > 0
    default = check_embed_identity(chroma, MODEL)
    assert "can be dropped" not in default.detail and default.status == WARN
    assert check_embed_identity(chroma, MODEL, strict=True).status == FAIL


# --------------------------------------------------------------------------------------
# A reader must never disturb another connection's lock (POSIX: closing a descriptor drops them all)
# --------------------------------------------------------------------------------------


# Run in a fresh process that has never loaded Chroma. Chroma's embedded SQLite and Python's sqlite3 are
# different libraries in one process and do not coordinate their POSIX locks, so any earlier Chroma
# activity in the test process can drop the holder's lock on its own and make this test meaningless.
_LOCK_CHILD = r"""
import sqlite3, subprocess, sys
root, chroma, reader = sys.argv[1:4]
sys.path.insert(0, root)
import chroma_readonly as R
from chroma_embed_identity import check_embed_identity
PROBE = (
    "import sqlite3, sys\n"
    "conn = sqlite3.connect(sys.argv[1], timeout=0)\n"
    "try:\n    conn.execute('BEGIN EXCLUSIVE'); print('GOT')\n"
    "except sqlite3.OperationalError:\n    print('BLOCKED')\n"
)
db = chroma + "/chroma.sqlite3"
def lock_is_free():
    done = subprocess.run([sys.executable, "-c", PROBE, db], capture_output=True, text=True, check=True)
    return "GOT" in done.stdout
READERS = {
    "may_create_wal_files": lambda c: R.may_create_wal_files(c),
    "collection_uuid": lambda c: R.collection_uuid(c, "knowledge_units"),
    "collection_dimension": lambda c: R.collection_dimension(c, "knowledge_units"),
    "collection_config_metadata": lambda c: R.collection_config_metadata(c, "knowledge_units"),
    "collection_ids": lambda c: R.collection_ids(c, "knowledge_units"),
    "collection_count": lambda c: R.collection_count(c, "knowledge_units"),
    "collection_row_evidence": lambda c: R.collection_row_evidence(c, "knowledge_units"),
    "collection_identity_facts": lambda c: R.collection_identity_facts(c, "knowledge_units"),
    "collection_identity_facts_many": lambda c: R.collection_identity_facts_many(c, ("knowledge_units",)),
    "collection_change_fingerprint": lambda c: R.collection_change_fingerprint(c, "knowledge_units"),
    "iter_collection_metadata_rows": lambda c: list(R.iter_collection_metadata_rows(c, "knowledge_units")),
    "unit_document_text": lambda c: R.unit_document_text(c, "knowledge_units-1"),
    "check_embed_identity": lambda c: check_embed_identity(c, "nomic-embed-text:latest"),
}
holder = sqlite3.connect(db)
holder.execute("BEGIN")
holder.execute("SELECT count(*) FROM collections").fetchall()
assert not lock_is_free(), "baseline: the holder must hold a read lock"
READERS[reader](chroma)
print("IN_TRANSACTION", holder.in_transaction, "LOCK_FREE_AFTER", lock_is_free())
"""

_READER_NAMES = [
    "may_create_wal_files", "collection_uuid", "collection_dimension", "collection_config_metadata",
    "collection_ids", "collection_count", "collection_row_evidence", "collection_identity_facts",
    "collection_identity_facts_many", "collection_change_fingerprint", "iter_collection_metadata_rows",
    "unit_document_text", "check_embed_identity",
]


@pytest.mark.parametrize("reader", _READER_NAMES)
def test_no_reader_releases_a_lock_another_connection_holds(tmp_path: Path, reader: str) -> None:
    """Reviewed: an ordinary read helper (through a raw header probe) let another process take the
    exclusive lock while this process's own connection still believed it held a read lock."""
    chroma = tmp_path / "chroma"
    _store(chroma, UNITS, SUMMARIES, embed_model=MODEL)
    root = Path(chroma_readonly.__file__).resolve().parent

    done = subprocess.run(
        [sys.executable, "-c", _LOCK_CHILD, str(root), str(chroma), reader],
        capture_output=True, text=True, check=False, timeout=120,
    )

    assert done.returncode == 0, done.stderr[-600:]
    assert done.stdout.strip().endswith("IN_TRANSACTION True LOCK_FREE_AFTER False"), done.stdout


@pytest.mark.parametrize("reader", ["collection_uuid", "collection_config_metadata", "collection_dimension"])
def test_a_single_collection_reader_holds_one_snapshot_for_its_check_and_its_query(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, reader: str
) -> None:
    """The ambiguity count and the query it guards used to be separate statements outside a
    transaction, so a duplicate inserted between them was read by one and refused by the next."""
    chroma = tmp_path / "chroma"
    _store(chroma, UNITS, embed_model=MODEL)
    outcomes: list[str] = []
    real_connect = chroma_readonly._connect_readonly

    def connect(db: Path) -> sqlite3.Connection:
        conn = real_connect(db)
        seen: list[str] = []

        def trace(statement: str) -> None:
            seen.append(statement)
            if len(seen) == 3 and not outcomes:
                writer = sqlite3.connect(db, timeout=0)
                try:
                    writer.execute("UPDATE collections SET dimension = 999")  # any commit
                    writer.commit()
                    outcomes.append("committed")
                except sqlite3.OperationalError as exc:
                    outcomes.append(str(exc))
                finally:
                    writer.close()

        conn.set_trace_callback(trace)
        return conn

    monkeypatch.setattr(chroma_readonly, "_connect_readonly", connect)

    getattr(chroma_readonly, reader)(chroma, UNITS)

    assert outcomes == ["database is locked"]


def test_both_collections_are_judged_from_one_snapshot(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Reviewed: units were read, a transaction swapped the two stamps, summaries were read, and
    strict doctor passed a pair no committed state ever had."""
    chroma = tmp_path / "chroma"
    _store(chroma, UNITS, SUMMARIES, embed_model=MODEL)
    opened: list[Path] = []
    outcomes: list[str] = []
    real_connect = chroma_readonly._connect_readonly

    def connect(db: Path) -> sqlite3.Connection:
        opened.append(db)
        conn = real_connect(db)
        seen: list[str] = []

        def trace(statement: str) -> None:
            seen.append(statement)
            if len(seen) == 3 and not outcomes:  # after the first query: the swap tries to commit
                writer = sqlite3.connect(db, timeout=0)
                try:
                    writer.execute(
                        "UPDATE collection_metadata SET str_value = 'swapped' WHERE key = 'convmem:embed_model'"
                    )
                    writer.commit()
                    outcomes.append("swapped")
                except sqlite3.OperationalError as exc:
                    outcomes.append(str(exc))
                finally:
                    writer.close()

        conn.set_trace_callback(trace)
        return conn

    monkeypatch.setattr(chroma_readonly, "_connect_readonly", connect)

    verdict = check_embed_identity(chroma, MODEL, strict=True)

    assert len(opened) == 1  # one connection, hence one snapshot, for both collections
    assert outcomes == ["database is locked"]
    assert verdict.status == "pass"  # the state that was read: both stamps matched


def test_a_collection_missing_its_vector_segment_is_not_called_empty(tmp_path: Path) -> None:
    """With no row stored, nothing else can account for a missing segment: only the count of the
    collection's segments stands between "empty" and "safe to drop"."""
    chroma = tmp_path / "chroma"
    with ChromaStore(str(chroma)) as store:
        store._collection(UNITS)  # created empty, with both of its segments
    with sqlite3.connect(chroma / "chroma.sqlite3") as con:
        con.execute("DELETE FROM segments WHERE scope = 'VECTOR'")
        assert con.execute("SELECT COUNT(*) FROM embeddings").fetchone()[0] == 0
        assert con.execute("SELECT COUNT(*) FROM segments s WHERE NOT EXISTS "
                           "(SELECT 1 FROM collections c WHERE c.id = s.collection)").fetchone()[0] == 0

    assert chroma_readonly.collection_row_evidence(chroma, UNITS) == 1  # the unaccounted segment, nothing else
    assert "can be dropped" not in check_embed_identity(chroma, MODEL).detail


def test_a_malformed_dimension_is_a_catalog_error(tmp_path: Path) -> None:
    chroma = tmp_path / "chroma"
    _store(chroma, UNITS)
    with sqlite3.connect(chroma / "chroma.sqlite3") as con:
        con.execute("UPDATE collections SET dimension = 'unknown'")

    with pytest.raises(sqlite3.DatabaseError, match="records the dimension"):
        chroma_readonly.collection_dimension(chroma, UNITS)
    assert check_embed_identity(chroma, MODEL, strict=True).status == "fail"

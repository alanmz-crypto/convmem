"""Reading collection identity safely: serving database, ambiguity, URI characters, emptiness evidence.

Split out of ``test_chroma_embed_identity`` (which is at the module-size limit). Hermetic: every
store lives in ``tmp_path``; the helpers under test only ever read, through SQLite ``mode=ro``.
"""

# pylint: disable=protected-access,too-many-arguments

from __future__ import annotations

import sqlite3
from pathlib import Path

import chromadb
import pytest

from chroma_embed_identity import FAIL, WARN, check_embed_identity
from chroma_store import EMBED_MODEL_KEY, UNITS, ChromaStore
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

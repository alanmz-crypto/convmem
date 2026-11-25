"""A collection created by ChromaStore records which embedding model it was made for.

Hermetic: every store lives in ``tmp_path``; vectors are written directly, so no
embedding service is involved and the live Chroma directory is never opened.

Identity is read back through ``chroma_readonly.collection_config_metadata``, the
same read-only SQLite path ``convmem doctor`` uses, so these tests prove what the
health check will actually see on disk.
"""

# pylint: disable=protected-access

from __future__ import annotations

import json
from pathlib import Path
from unittest import mock

import pytest
from chromadb.errors import NotFoundError

import llm
from chroma_readonly import collection_config_metadata, collection_uuid
from chroma_store import (
    EMBED_MODEL_KEY,
    SUMMARIES,
    UNITS,
    ChromaStore,
    EmbedIdentityError,
    normalize_embed_model,
)
from chroma_write_store import open_chroma_for_write

MODEL = "nomic-embed-text:latest"
COSINE_ONLY = {"hnsw:space": "cosine"}


def _create(chroma: Path, *collections: str, embed_model: str | None = None) -> None:
    """Create the named collections through the normal store path, then close it."""
    with ChromaStore(str(chroma), embed_model=embed_model) as store:
        for name in collections:
            store._collection(name)


def test_creation_records_the_model_on_both_collections(tmp_path: Path) -> None:
    chroma = tmp_path / "chroma"
    _create(chroma, UNITS, SUMMARIES, embed_model=MODEL)

    expected = {**COSINE_ONLY, EMBED_MODEL_KEY: MODEL}
    # Exact equality also proves nothing else was written: no guessed dimension.
    assert collection_config_metadata(chroma, UNITS) == expected
    assert collection_config_metadata(chroma, SUMMARIES) == expected


def test_recording_identity_keeps_the_cosine_index_and_adds_no_dimension(tmp_path: Path) -> None:
    chroma = tmp_path / "chroma"
    with ChromaStore(str(chroma), embed_model=MODEL) as store:
        col = store._collection(UNITS)
        # Cosine distance from a to b is 1.0; squared-L2 would be 10.0.
        col.upsert(
            ids=["a", "b"],
            embeddings=[[1.0, 0.0, 0.0], [0.0, 3.0, 0.0]],
            documents=["a", "b"],
        )
        res = col.query(query_embeddings=[[1.0, 0.0, 0.0]], n_results=2, include=["distances"])
        distances = dict(zip(res["ids"][0], res["distances"][0]))

    assert distances["a"] == pytest.approx(0.0, abs=1e-6)
    assert distances["b"] == pytest.approx(1.0, abs=1e-6)
    # Writing vectors does not make the store invent a dimension either.
    assert collection_config_metadata(chroma, UNITS) == {**COSINE_ONLY, EMBED_MODEL_KEY: MODEL}


def test_store_without_a_model_records_no_identity(tmp_path: Path) -> None:
    chroma = tmp_path / "chroma"
    _create(chroma, UNITS, SUMMARIES)

    for name in (UNITS, SUMMARIES):
        meta = collection_config_metadata(chroma, name)
        assert meta == COSINE_ONLY
        assert EMBED_MODEL_KEY not in meta  # missing identity stays distinguishable


@pytest.mark.parametrize("blank", [None, "", "   \t"])
def test_blank_model_is_not_recorded(tmp_path: Path, blank: str | None) -> None:
    chroma = tmp_path / "chroma"
    _create(chroma, UNITS, embed_model=blank)

    assert collection_config_metadata(chroma, UNITS) == COSINE_ONLY


def test_normalize_embed_model_only_accepts_a_real_name() -> None:
    assert normalize_embed_model("  nomic-embed-text:latest ") == MODEL
    for not_a_name in (None, "", "  ", 7, 0.5, ["m"], {"m": 1}, b"m"):
        assert normalize_embed_model(not_a_name) is None


def test_existing_collection_is_never_relabeled(tmp_path: Path) -> None:
    unmarked = tmp_path / "unmarked"
    _create(unmarked, UNITS)  # created before identity was recorded
    _create(unmarked, UNITS, embed_model=MODEL)  # reopened by a store that knows a model
    assert collection_config_metadata(unmarked, UNITS) == COSINE_ONLY

    marked = tmp_path / "marked"
    _create(marked, UNITS, embed_model="model-a")
    _create(marked, UNITS, embed_model="model-b")  # a changed configuration must not relabel
    assert collection_config_metadata(marked, UNITS)[EMBED_MODEL_KEY] == "model-a"


def test_second_collection_is_marked_when_it_is_created_later(tmp_path: Path) -> None:
    chroma = tmp_path / "chroma"
    _create(chroma, UNITS, embed_model=MODEL)
    assert collection_uuid(chroma, SUMMARIES) is None

    _create(chroma, SUMMARIES, embed_model=MODEL)  # created lazily, as in production

    assert collection_config_metadata(chroma, SUMMARIES)[EMBED_MODEL_KEY] == MODEL
    assert collection_config_metadata(chroma, UNITS)[EMBED_MODEL_KEY] == MODEL


def test_verify_open_creates_nothing_and_leaves_metadata_alone(tmp_path: Path) -> None:
    chroma = tmp_path / "chroma"
    _create(chroma, UNITS)  # unmarked UNITS only; SUMMARIES does not exist
    before = collection_config_metadata(chroma, UNITS)

    with ChromaStore(str(chroma), create_collections=False, embed_model="other-model") as verify:
        assert verify._collection(UNITS).name == UNITS  # existing collection opens
        with pytest.raises(NotFoundError):
            verify._collection(SUMMARIES)  # missing collection is refused, not created

    assert collection_uuid(chroma, SUMMARIES) is None
    assert collection_config_metadata(chroma, UNITS) == before == COSINE_ONLY


def test_identity_key_matches_the_shadow_builder_contract() -> None:
    from eval_corpus.shadow_build import collection_metadata_from_manifest

    shadow = collection_metadata_from_manifest(
        {
            "embed_model": MODEL,
            "embed_dimensions": 768,
            "unit_corpus_fingerprint": "f" * 64,
            "unit_count": 0,
        },
        manifest_sha256="s" * 64,
    )

    assert shadow[EMBED_MODEL_KEY] == MODEL


# --------------------------------------------------------------------------------------
# A vector made by one model cannot create a collection stamped for another
# --------------------------------------------------------------------------------------


def _vector(model: str | None, values: tuple[float, ...] = (1.0, 0.0, 0.0)) -> llm.EmbeddingVector:
    vector = llm.EmbeddingVector(values)
    vector.embed_model = model
    return vector


def _write(store: ChromaStore, how: str, vector: list[float]) -> None:
    meta = {"source_path": "unit.md"}
    if how == "add_unit":
        store.add_unit("u1", "a document", vector, meta)
    elif how == "update_unit":
        store.update_unit("u1", "a document", vector, meta)
    else:
        store.add_summary("s1", "a summary", vector, meta)


WRITES = [("add_unit", UNITS), ("update_unit", UNITS), ("add_summary", SUMMARIES)]


def test_ollama_embed_tags_the_vector_with_the_model_that_made_it() -> None:
    response = mock.Mock()
    response.json.return_value = {"embedding": [0.25, 0.5, 0.75]}
    with (
        mock.patch.object(llm.requests, "post", return_value=response),
        mock.patch.object(llm, "_permit_provider_http_attempt"),
        mock.patch.object(llm, "_report_provider_usage"),
        mock.patch("purge_locks.reject_provider_under_write_scope"),
    ):
        vector = llm.ollama_embed("hello", "model-a", "http://localhost:11434")

    assert vector == [0.25, 0.5, 0.75]
    assert vector.embed_model == "model-a"
    assert json.dumps(vector) == "[0.25, 0.5, 0.75]"  # still an ordinary list to everything else


def test_the_tag_survives_pickling_and_copying_but_not_slicing() -> None:
    """The watch service indexes in subprocesses; a lost tag fails open (it is never judged)."""
    import copy
    import pickle

    vector = _vector("model-a", (0.1, 0.2, 0.3))

    assert pickle.loads(pickle.dumps(vector)).embed_model == "model-a"
    assert copy.deepcopy(vector).embed_model == "model-a"
    assert getattr(list(vector), "embed_model", None) is None  # documented: a plain copy is untagged
    assert getattr(vector[:2], "embed_model", None) is None


@pytest.mark.parametrize("how,collection", WRITES, ids=[w[0] for w in WRITES])
def test_a_vector_from_another_model_cannot_create_a_collection_stamped_for_this_one(
    tmp_path: Path, how: str, collection: str
) -> None:
    chroma = tmp_path / "chroma"
    with ChromaStore(str(chroma), embed_model="model-b") as store:
        with pytest.raises(EmbedIdentityError, match="model-a"):
            _write(store, how, _vector("model-a"))

    # Refused before anything was created, so nothing carries the wrong stamp.
    assert collection_uuid(chroma, collection) is None


@pytest.mark.parametrize("how,collection", WRITES, ids=[w[0] for w in WRITES])
def test_a_vector_from_the_stamped_model_creates_the_collection(
    tmp_path: Path, how: str, collection: str
) -> None:
    chroma = tmp_path / "chroma"
    with ChromaStore(str(chroma), embed_model="model-b") as store:
        if how == "update_unit":
            _write(store, "add_unit", _vector("model-b"))
        else:
            _write(store, how, _vector("model-b"))

    assert collection_config_metadata(chroma, collection)[EMBED_MODEL_KEY] == "model-b"


def test_an_untagged_vector_is_not_judged(tmp_path: Path) -> None:
    chroma = tmp_path / "chroma"
    with ChromaStore(str(chroma), embed_model="model-b") as store:
        store.add_unit("u1", "a document", [1.0, 0.0, 0.0], {"source_path": "unit.md"})

    assert collection_config_metadata(chroma, UNITS)[EMBED_MODEL_KEY] == "model-b"


READS_BEFORE_A_WRITE = {
    "get_unit": lambda store: store.get_unit("u1"),
    "query_units": lambda store: store.query_units([1.0, 0.0, 0.0], 3),
    "count_units": lambda store: store.count_units(),
}


@pytest.mark.parametrize("read", sorted(READS_BEFORE_A_WRITE))
def test_a_read_that_creates_the_collection_first_does_not_let_a_foreign_vector_through(
    tmp_path: Path, read: str
) -> None:
    """Writers dedupe and replay-check before they write; those reads create the collection."""
    chroma = tmp_path / "chroma"
    with ChromaStore(str(chroma), embed_model="model-b") as store:
        READS_BEFORE_A_WRITE[read](store)
        assert collection_config_metadata(chroma, UNITS)[EMBED_MODEL_KEY] == "model-b"

        with pytest.raises(EmbedIdentityError, match="model-a"):
            store.add_unit("u1", "a document", _vector("model-a"), {"source_path": "unit.md"})

        assert store.count_units() == 0  # nothing was stored under the wrong stamp
        # The right model is still accepted into the same collection afterwards.
        store.add_unit("u1", "a document", _vector("model-b"), {"source_path": "unit.md"})
        assert store.count_units() == 1


def test_the_first_vector_must_come_from_the_model_an_empty_collection_records(
    tmp_path: Path,
) -> None:
    chroma = tmp_path / "chroma"
    _create(chroma, UNITS, embed_model="model-b")  # exists, stamped, holds no vectors

    with ChromaStore(str(chroma), embed_model="model-b") as store:
        with pytest.raises(EmbedIdentityError):
            store.add_unit("u1", "a document", _vector("model-a"), {"source_path": "unit.md"})


def test_the_first_vector_is_compared_with_the_collection_not_just_the_store(
    tmp_path: Path,
) -> None:
    chroma = tmp_path / "chroma"
    _create(chroma, UNITS, embed_model="model-b")  # recorded b, but this session is configured c

    with ChromaStore(str(chroma), embed_model="model-c") as store:
        with pytest.raises(EmbedIdentityError, match="records 'model-b'"):
            store.add_unit("u1", "a document", _vector("model-c"), {"source_path": "unit.md"})


def test_the_collection_is_looked_up_once_per_session_not_on_every_write(tmp_path: Path) -> None:
    chroma = tmp_path / "chroma"
    with ChromaStore(str(chroma), embed_model="model-b") as store:
        with mock.patch.object(
            store.client, "get_collection", wraps=store.client.get_collection
        ) as lookup:
            for index in range(3):
                store.add_unit(
                    f"u{index}", "a document", _vector("model-b"), {"source_path": "unit.md"}
                )

    assert lookup.call_count == 1


def test_an_empty_collection_that_records_nothing_is_not_judged(tmp_path: Path) -> None:
    chroma = tmp_path / "chroma"
    _create(chroma, UNITS)  # a legacy-style collection: cosine only, no model

    with ChromaStore(str(chroma), embed_model="model-b") as store:
        store.add_unit("u1", "a document", _vector("model-a"), {"source_path": "unit.md"})

    assert EMBED_MODEL_KEY not in collection_config_metadata(chroma, UNITS)


def test_once_a_collection_holds_vectors_a_mismatch_is_left_to_doctor(tmp_path: Path) -> None:
    chroma = tmp_path / "chroma"
    with ChromaStore(str(chroma), embed_model="model-b") as store:
        store.add_unit("u1", "a document", _vector("model-b"), {"source_path": "unit.md"})

    with ChromaStore(str(chroma), embed_model="model-b") as store:  # a later session
        store.add_unit("u2", "another", _vector("model-a"), {"source_path": "unit.md"})

    assert collection_config_metadata(chroma, UNITS)[EMBED_MODEL_KEY] == "model-b"


def test_a_store_that_records_no_model_does_not_judge_vectors(tmp_path: Path) -> None:
    chroma = tmp_path / "chroma"
    with ChromaStore(str(chroma)) as store:
        store.add_unit("u1", "a document", _vector("model-a"), {"source_path": "unit.md"})

    assert EMBED_MODEL_KEY not in collection_config_metadata(chroma, UNITS)


def test_a_config_change_between_embedding_and_opening_the_writer_is_refused(
    tmp_path: Path,
) -> None:
    """The reviewed scenario: embed under A, config becomes B, the writer then opens."""
    chroma = tmp_path / "chroma"
    embedded_under_a = _vector("model-a")
    config_now = {"models": {"embed_model": "model-b"}}

    store, _ = open_chroma_for_write(config_now, chroma, purpose="test")
    try:
        with pytest.raises(EmbedIdentityError):
            store.add_unit("u1", "a document", embedded_under_a, {"source_path": "unit.md"})
        assert collection_uuid(chroma, UNITS) is None  # refused before anything was created

        store.get_unit("u1")  # the dedupe and replay reads a real writer does first
        with pytest.raises(EmbedIdentityError):
            store.add_unit("u1", "a document", embedded_under_a, {"source_path": "unit.md"})
        assert store.count_units() == 0
    finally:
        store.close()


@pytest.mark.xfail(
    strict=True,
    reason=(
        "known gap: ingest.py:1130 copies the summary vector with list(), which drops the model "
        "tag; fixing it edits ingest.py, whose hash the incremental canary baseline tests pin, "
        "so it needs a reviewed re-pin. Remove this marker when that lands."
    ),
)
def test_the_summary_vector_keeps_its_model_tag_through_ingest(tmp_path: Path) -> None:
    """A copy such as list(vector) drops the tag, and an untagged vector is never judged."""
    import ingest

    tagged = _vector("nomic-embed-text:latest")
    models = {
        "summarize_model": "m",
        "distill_model": "m",
        "embed_model": "nomic-embed-text:latest",
        "ollama_host": "http://localhost:11434",
    }
    chunk = {
        "messages": [{"role": "user", "content": "hello", "timestamp": None}],
        "start_offset": 0,
        "end_offset": 0,
    }
    with (
        mock.patch("ingest._SYNTHESIS_FAIL_LOG", tmp_path / "synthesis_failures.jsonl"),
        mock.patch("ingest.summarize", return_value="a summary"),
        mock.patch("ingest.ollama_embed", return_value=tagged),
        mock.patch("ingest._distill_with_provenance", return_value=([], "")),
    ):
        artifact = ingest.build_chunk_artifact(
            chunk=chunk,
            path="/tmp/session.jsonl",
            path_key="/tmp/session.jsonl",
            models=models,
            tool="codex",
            chunk_size=60,
            overlap=10,
            min_confidence=0.6,
            verbose=False,
            retry_sleep=False,
        )

    assert artifact is not None
    assert getattr(artifact.summary_embedding, "embed_model", None) == "nomic-embed-text:latest"

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
from chroma_embed_model_names import same_embed_model
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


# --------------------------------------------------------------------------------------
# A check must not be waived by anything short of a vector actually being stored
# --------------------------------------------------------------------------------------


def _empty_collection_recording(chroma: Path, model: str) -> None:
    _create(chroma, UNITS, embed_model=model)


def test_a_no_op_update_does_not_waive_the_first_vector_check(tmp_path: Path) -> None:
    chroma = tmp_path / "chroma"
    _empty_collection_recording(chroma, "model-y")
    with ChromaStore(str(chroma), embed_model="model-y") as store:
        store.update_unit("absent", "a document", _vector("model-y"), {"source_path": "unit.md"})
        assert store.count_units() == 0  # nothing was stored

        with pytest.raises(EmbedIdentityError):
            store.add_unit("u1", "a document", _vector("model-x"), {"source_path": "unit.md"})
        assert store.count_units() == 0


def test_a_failed_first_write_does_not_waive_the_check_for_the_retry(tmp_path: Path) -> None:
    chroma = tmp_path / "chroma"
    _empty_collection_recording(chroma, "model-y")
    with ChromaStore(str(chroma), embed_model="model-y") as store:
        with mock.patch.object(store, "_native", side_effect=RuntimeError("write failed")):
            with pytest.raises(RuntimeError):
                store.add_unit("u1", "a document", _vector("model-y"), {"source_path": "unit.md"})

        with pytest.raises(EmbedIdentityError):
            store.add_unit("u1", "a document", _vector("model-x"), {"source_path": "unit.md"})


@pytest.mark.parametrize(
    "kwargs", [{"create_collections": False}, {"embed_model": None}], ids=["no-create", "no-model"]
)
def test_a_store_without_its_own_model_still_protects_an_empty_stamped_collection(
    tmp_path: Path, kwargs: dict
) -> None:
    chroma = tmp_path / "chroma"
    _empty_collection_recording(chroma, "model-y")

    with ChromaStore(str(chroma), **kwargs) as store:
        with pytest.raises(EmbedIdentityError):
            store.add_unit("u1", "a document", _vector("model-x"), {"source_path": "unit.md"})
        store.add_unit("u1", "a document", _vector("model-y"), {"source_path": "unit.md"})
        assert store.count_units() == 1


def test_emptying_a_collection_in_a_session_restores_the_first_vector_check(tmp_path: Path) -> None:
    chroma = tmp_path / "chroma"
    with ChromaStore(str(chroma), embed_model="model-y") as store:
        store.add_unit("u1", "a document", _vector("model-y"), {"source_path": "unit.md"})
        store.add_unit("u2", "a document", _vector("model-x"), {"source_path": "unit.md"})  # left to doctor
        store._native(UNITS, "delete", ids=["u1", "u2"])
        assert store.count_units() == 0

        with pytest.raises(EmbedIdentityError):
            store.add_unit("u3", "a document", _vector("model-x"), {"source_path": "unit.md"})


@pytest.mark.parametrize(
    "first,second,same",
    [
        ("nomic-embed-text", "nomic-embed-text:latest", True),
        ("nomic-embed-text:latest", "nomic-embed-text", True),
        (" nomic-embed-text ", "nomic-embed-text:latest", True),
        ("library/nomic-embed-text", "nomic-embed-text:latest", True),
        ("registry.ollama.ai/library/nomic-embed-text:latest", "nomic-embed-text", True),
        ("NOMIC-EMBED-TEXT", "nomic-embed-text:latest", True),
        ("nomic-embed-text:V1.5", "nomic-embed-text:v1.5", True),
        ("someone/nomic-embed-text", "nomic-embed-text", False),
        ("localhost:11434/nomic-embed-text", "nomic-embed-text", False),
        # the leading "library/" is a namespace only when it is the host's namespace slot:
        ("library/acme/model", "acme/model", False),  # host "library", not the default host
        ("library/acme/model", "library/acme/model:latest", True),
        ("acme/model", "registry.ollama.ai/acme/model:latest", True),
        ("a.b:5000/ns/m", "a.b:5001/ns/m", False),
        ("a.b:5000/ns/m", "A.B:5000/NS/M:latest", True),
        # malformed names equal only themselves, never a well-formed model
        ("x:", "x", False),
        ("/x", "x", False),
        ("x:", "x:", True),
        ("a/b/c/d", "b/c/d", False),
        ("a/b/c/d", "d", False),  # four parts must not collapse to the bare model "d"
        # the rest of Ollama's own grammar (types/model/name.go)
        ("\u212a", "k", False),  # the Kelvin sign is not ASCII, so it is never folded into "k"
        ("K", "k", True),
        ("_model", "_model:latest", True),  # a leading underscore is valid in every part
        ("m:_t", "registry.ollama.ai/library/m:_t", True),
        ("https://registry.ollama.ai/library/m", "m", True),  # the scheme is not part of the identity
        ("http://h.example/ns/m", "https://h.example/ns/m", True),
        # two parts: "registry.ollama.ai" is read as a namespace, and a namespace may not contain a dot
        ("registry.ollama.ai/llama3", "llama3", False),
        ("llama3@sha256:abc", "llama3", False),  # digests are not part of the grammar
        ("a:b:c", "a", False),
        ("a.b/m", "m", False),
        ("a.b/m", "registry.ollama.ai/a.b/m", False),  # a dotted namespace is invalid, so only equal to itself
        ("localhost:11434", "localhost:11434", True),  # this is model "localhost" with tag "11434"
        ("localhost:11434", "localhost", False),
        ("llama3.1", "llama3_1", False),  # '.', '-' and '_' are significant
        ("x" * 81, "x" * 81, True),  # over-long: outside the grammar, so only equal to itself
        ("x" * 81, "x", False),
        ("x" * 81, "registry.ollama.ai/library/" + "x" * 81 + ":latest", False),  # no 81-char model exists
        ("x" * 80, "registry.ollama.ai/library/" + "x" * 80 + ":latest", True),  # 80 is the limit
        ("h" * 351 + "/ns/m", "h" * 351 + "/ns/m:latest", False),  # a 351-char host is over its limit
        ("a_b.c-d/ns_1/M.1:T-1", "A_B.C-D/NS_1/m.1:t-1", True),
        ("a/b/c/d", "a/b/c/d", True),
        ("nomic-embed-text", "nomic-embed-text:v1.5", False),
        ("nomic-embed-text:v1", "nomic-embed-text:v2", False),
        ("nomic-embed-text", "other-model", False),
        ("nomic-embed-text", None, False),
        ("", "", False),
    ],
)
def test_a_bare_model_name_means_latest_and_nothing_else_is_merged(first, second, same) -> None:
    assert same_embed_model(first, second) is same


def test_an_alias_only_config_change_does_not_refuse_the_first_write(tmp_path: Path) -> None:
    """Embedded as the bare name, then the config spells it ':latest': one Ollama model."""
    chroma = tmp_path / "chroma"
    with ChromaStore(str(chroma), embed_model="nomic-embed-text:latest") as store:
        store.add_unit("u1", "a document", _vector("nomic-embed-text"), {"source_path": "unit.md"})
        assert store.count_units() == 1


def test_another_session_emptying_the_collection_cannot_leave_a_stale_waiver(tmp_path: Path) -> None:
    """Reviewed: store A published, store B removed the last row, A then accepted a foreign first vector."""
    chroma = tmp_path / "chroma"
    with ChromaStore(str(chroma), embed_model="model-y") as first, ChromaStore(
        str(chroma), embed_model="model-y"
    ) as second:
        first.add_unit("u1", "a document", _vector("model-y"), {"source_path": "unit.md"})
        second._native(UNITS, "delete", ids=["u1"])
        assert first.count_units() == 0

        with pytest.raises(EmbedIdentityError):
            first.add_unit("u2", "a document", _vector("model-x"), {"source_path": "unit.md"})


def test_a_write_that_reports_failure_after_committing_cannot_waive_the_check(tmp_path: Path) -> None:
    chroma = tmp_path / "chroma"
    with ChromaStore(str(chroma), embed_model="model-y") as store:
        store.add_unit("u1", "a document", _vector("model-y"), {"source_path": "unit.md"})
        real = store._native

        def commit_then_fail(collection, operation, **kwargs):
            real(collection, operation, **kwargs)
            if operation == "delete":
                raise RuntimeError("bookkeeping failed after the row was gone")

        with mock.patch.object(store, "_native", commit_then_fail):
            with pytest.raises(RuntimeError):
                store._native(UNITS, "delete", ids=["u1"])
        assert store.count_units() == 0

        with pytest.raises(EmbedIdentityError):
            store.add_unit("u2", "a document", _vector("model-x"), {"source_path": "unit.md"})


def test_a_direct_native_write_with_an_array_succeeds_and_reports_success(tmp_path: Path) -> None:
    import numpy as np

    chroma = tmp_path / "chroma"
    with ChromaStore(str(chroma), embed_model="model-y") as store:
        store._native(
            UNITS,
            "upsert",
            ids=["n1"],
            documents=["a document"],
            embeddings=np.array([[1.0, 0.0]], dtype=np.float32),
            metadatas=[{"source_path": "unit.md"}],
        )
        assert store.count_units() == 1  # and it did not raise after committing


def _recreate_collection(chroma: Path, model: str) -> None:
    """Another session drops the collection and creates it again, stamped for ``model``."""
    with ChromaStore(str(chroma), embed_model=model) as other:
        other.client.delete_collection(UNITS)
        other._collection(UNITS)


def test_a_collection_replaced_by_another_session_is_judged_by_its_new_stamp(tmp_path: Path) -> None:
    """Reviewed: A cached the old stamp, so it refused the right vector and accepted the wrong one."""
    chroma = tmp_path / "chroma"
    with ChromaStore(str(chroma), embed_model="model-y") as first:
        first.add_unit("u1", "a document", _vector("model-y"), {"source_path": "unit.md"})
        _recreate_collection(chroma, "model-z")  # now empty and stamped model-z

        with pytest.raises(EmbedIdentityError, match="records 'model-z'"):
            first.add_unit("u2", "a document", _vector("model-y"), {"source_path": "unit.md"})
        first.add_unit("u2", "a document", _vector("model-z"), {"source_path": "unit.md"})

    assert collection_config_metadata(chroma, UNITS)[EMBED_MODEL_KEY] == "model-z"


def test_a_stamp_changed_in_place_is_read_fresh(tmp_path: Path) -> None:
    chroma = tmp_path / "chroma"
    with ChromaStore(str(chroma), embed_model="model-y") as first:
        first.add_unit("u1", "a document", _vector("model-y"), {"source_path": "unit.md"})
        first._native(UNITS, "delete", ids=["u1"])
        with ChromaStore(str(chroma), embed_model="model-y") as other:  # same UUID, new stamp
            other.client.get_collection(UNITS).modify(metadata={EMBED_MODEL_KEY: "model-z"})

        with pytest.raises(EmbedIdentityError, match="records 'model-z'"):
            first.add_unit("u2", "a document", _vector("model-y"), {"source_path": "unit.md"})


def test_a_stamp_is_not_remembered_across_a_no_op_that_found_none(tmp_path: Path) -> None:
    chroma = tmp_path / "chroma"
    _create(chroma, UNITS)  # empty and unmarked
    with ChromaStore(str(chroma), embed_model="model-y") as first:
        first.update_unit("absent", "a document", _vector("model-y"), {"source_path": "unit.md"})
        _recreate_collection(chroma, "model-y")  # now it records model-y

        with pytest.raises(EmbedIdentityError):
            first.add_unit("u1", "a document", _vector("model-x"), {"source_path": "unit.md"})


def test_the_check_is_repeated_inside_the_write_guard(tmp_path: Path) -> None:
    """The guard may reload the client; the vector is judged against the handle then in use."""
    chroma = tmp_path / "chroma"
    _create(chroma, UNITS, embed_model="model-y")
    with ChromaStore(str(chroma), embed_model="model-y") as store:
        entered: list[bool] = []

        class _Guard:
            def native_write(self, **_kwargs):
                import contextlib

                @contextlib.contextmanager
                def context():
                    entered.append(True)
                    _recreate_collection(chroma, "model-z")  # replaced as the guard is entered
                    yield

                return context()

        store._write_guard = _Guard()
        with pytest.raises(EmbedIdentityError, match="records 'model-z'"):
            store._native(
                UNITS, "upsert", ids=["u1"], documents=["a document"],
                embeddings=[_vector("model-y")], metadatas=[{"source_path": "unit.md"}],
            )

    assert entered == [True]


def test_a_refusal_inside_the_write_guard_is_reported_to_the_session_as_a_failed_mutation(
    tmp_path: Path,
) -> None:
    """Reviewed: the session was told a mutation was about to happen and never that it failed."""
    chroma = tmp_path / "chroma"
    _create(chroma, UNITS, embed_model="model-y")
    events: list[object] = []

    class _Session:
        store = None

        def bind_store(self, store) -> None:
            self.store = store

        def on_native_before(self, *_args, **_kwargs) -> None:
            events.append("before")

        def on_native_after(self, **kwargs) -> None:
            events.append(("after", kwargs["succeeded"]))

    class _Guard:
        def native_write(self, **_kwargs):
            import contextlib

            @contextlib.contextmanager
            def context():
                _recreate_collection(chroma, "model-z")  # replaced as the guard is entered
                yield

            return context()

    with ChromaStore(str(chroma), embed_model="model-y") as store:
        store._write_guard = _Guard()
        with mock.patch("incremental_mutation_proof.active_session", return_value=_Session()):
            with pytest.raises(EmbedIdentityError):
                store._native(
                    UNITS, "upsert", ids=["u1"], documents=["a document"],
                    embeddings=[_vector("model-y")], metadatas=[{"source_path": "unit.md"}],
                )

    assert events == ["before", ("after", False)]

"""A collection created by ChromaStore records which embedding model it was made for.

Hermetic: every store lives in ``tmp_path``; vectors are written directly, so no
embedding service is involved and the live Chroma directory is never opened.

Identity is read back through ``chroma_readonly.collection_config_metadata``, the
same read-only SQLite path ``convmem doctor`` uses, so these tests prove what the
health check will actually see on disk.
"""

# pylint: disable=protected-access

from __future__ import annotations

from pathlib import Path

import pytest
from chromadb.errors import NotFoundError

from chroma_readonly import collection_config_metadata, collection_uuid
from chroma_store import (
    EMBED_MODEL_KEY,
    SUMMARIES,
    UNITS,
    ChromaStore,
    normalize_embed_model,
)

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

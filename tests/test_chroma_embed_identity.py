"""Doctor's view of embedding identity: recorded, attested, mismatched, unproven.

Hermetic: every store lives in ``tmp_path``. The verdict table is tested as a
pure function; the I/O wrapper and ``convmem doctor``'s check are then run
against real scratch stores, and shown to stay read-only (no Chroma client is
ever opened, the SQLite file is byte-identical afterwards).
"""

# pylint: disable=protected-access,too-many-arguments

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any
from unittest import mock

import chromadb
import pytest

from chroma_embed_identity import (
    ATTESTATION_SCHEMA,
    FAIL,
    PASS,
    WARN,
    AttestationError,
    CollectionAttestation,
    check_embed_identity,
    judge_collection,
    parse_attestations,
    read_attestations,
    sidecar_path,
)
from chroma_store import EMBED_MODEL_KEY, SUMMARIES, UNITS, ChromaStore
from doctor import _check_embed_collection_identity

MODEL = "nomic-embed-text:latest"
UUID = "11111111-1111-1111-1111-111111111111"
COSINE = {"hnsw:space": "cosine"}
RECORDED = {**COSINE, EMBED_MODEL_KEY: MODEL}


def _attestation(**over: Any) -> CollectionAttestation:
    fields: dict[str, Any] = {
        "name": UNITS,
        "collection_uuid": UUID,
        "dimension": 768,
        "embed_model": MODEL,
        "attested_at": "2026-11-24T00:00:00Z",
    }
    fields.update(over)
    return CollectionAttestation(**fields)


def _judge(**over: Any):
    args: dict[str, Any] = {
        "meta": COSINE,
        "uuid": UUID,
        "chroma_dimension": 768,
        "attestation": None,
        "attestation_error": None,
        "configured_model": MODEL,
        "strict": False,
    }
    args.update(over)
    return judge_collection(**args)


# --------------------------------------------------------------------------------------
# The sidecar file
# --------------------------------------------------------------------------------------


def test_sidecar_sits_beside_the_chroma_dir_never_inside_it(tmp_path: Path) -> None:
    chroma = tmp_path / "state" / "chroma"
    path = sidecar_path(chroma)

    assert path.parent == chroma.parent
    assert chroma not in path.parents
    assert path.name == "chroma.embed-attestation.json"
    # Two stores with different directory names never share one file.
    assert sidecar_path(tmp_path / "state" / "chroma-shadow") != path


def _doc(**entry: Any) -> dict[str, Any]:
    base = {"collection_uuid": UUID, "dimension": 768, "embed_model": MODEL, "evidence": {}}
    base.update(entry)
    return {"schema": ATTESTATION_SCHEMA, "collections": {UNITS: base}}


def test_read_attestations_without_a_sidecar_means_none(tmp_path: Path) -> None:
    assert not read_attestations(tmp_path / "chroma")


def test_a_valid_sidecar_round_trips(tmp_path: Path) -> None:
    chroma = tmp_path / "chroma"
    payload = _doc()
    payload["collections"][UNITS]["evidence"] = {"attested_at": "2026-11-24T00:00:00Z"}
    sidecar_path(chroma).write_text(json.dumps(payload), encoding="utf-8")

    assert read_attestations(chroma) == {UNITS: _attestation()}


@pytest.mark.parametrize(
    "payload",
    [
        [],
        {"schema": "something-else", "collections": {}},
        {"schema": ATTESTATION_SCHEMA},
        {"schema": ATTESTATION_SCHEMA, "collections": []},
        _doc(collection_uuid=""),
        _doc(collection_uuid=7),
        _doc(embed_model="  "),
        _doc(embed_model=None),
        _doc(dimension=0),
        _doc(dimension=True),
        _doc(dimension="many"),
        {"schema": ATTESTATION_SCHEMA, "collections": {UNITS: "yes"}},
    ],
    ids=repr,
)
def test_a_malformed_sidecar_is_refused_not_half_loaded(payload: object) -> None:
    with pytest.raises(AttestationError):
        parse_attestations(payload)


def test_unreadable_json_is_refused(tmp_path: Path) -> None:
    chroma = tmp_path / "chroma"
    sidecar_path(chroma).write_text("{not json", encoding="utf-8")

    with pytest.raises(AttestationError, match="not valid JSON"):
        read_attestations(chroma)


# --------------------------------------------------------------------------------------
# The verdict table (pure)
# --------------------------------------------------------------------------------------


def test_recorded_model_matching_the_configuration_passes() -> None:
    verdict = _judge(meta=RECORDED)

    assert verdict.status == PASS
    assert MODEL in verdict.detail


def test_recorded_model_that_differs_from_the_configuration_fails() -> None:
    verdict = _judge(meta={**COSINE, EMBED_MODEL_KEY: "model-a"}, configured_model="model-b")

    assert verdict.status == FAIL
    assert "embed model mismatch" in verdict.detail


def test_recorded_dimension_matching_chromas_own_passes() -> None:
    meta = {**RECORDED, "convmem:embed_dimensions": 768}
    verdict = _judge(meta=meta, chroma_dimension=768)

    assert verdict.status == PASS
    assert "dimensions=768" in verdict.detail


def test_recorded_dimension_that_chroma_contradicts_fails() -> None:
    meta = {**RECORDED, "convmem:embed_dimensions": 768}
    verdict = _judge(meta=meta, chroma_dimension=384)

    assert verdict.status == FAIL
    assert "embed dimension mismatch" in verdict.detail
    assert "768" in verdict.detail and "384" in verdict.detail


@pytest.mark.parametrize("bad", ["many", 0, -3, True, 1.5], ids=repr)
def test_recorded_dimension_that_is_not_a_positive_integer_fails(bad: object) -> None:
    verdict = _judge(meta={**RECORDED, "convmem:embed_dimensions": bad})

    assert verdict.status == FAIL


def test_a_recorded_dimension_is_not_checked_against_an_empty_collection() -> None:
    meta = {**RECORDED, "convmem:embed_dimensions": 768}

    assert _judge(meta=meta, chroma_dimension=None).status == PASS


def test_attested_legacy_collection_passes() -> None:
    verdict = _judge(attestation=_attestation())

    assert verdict.status == PASS
    assert "attested legacy" in verdict.detail
    assert MODEL in verdict.detail


def test_attestation_for_another_model_fails() -> None:
    verdict = _judge(attestation=_attestation(embed_model="other-model"))

    assert verdict.status == FAIL
    assert "attested embed model mismatch" in verdict.detail


def test_attestation_whose_dimension_no_longer_matches_fails() -> None:
    verdict = _judge(attestation=_attestation(dimension=384), chroma_dimension=768)

    assert verdict.status == FAIL
    assert "attested dimension 384" in verdict.detail


def test_an_attestation_for_a_replaced_collection_does_not_count() -> None:
    other = _attestation(collection_uuid="22222222-2222-2222-2222-222222222222")

    lenient = _judge(attestation=other)
    strict = _judge(attestation=other, strict=True)

    assert lenient.status == WARN and "another collection" in lenient.detail
    assert strict.status == FAIL


def test_unattested_unmarked_collection_warns_with_the_historic_wording() -> None:
    verdict = _judge()

    assert verdict.status == WARN
    assert "legacy collection metadata lacks convmem:embed_model" in verdict.detail
    assert "no attestation" in verdict.detail


def test_unattested_unmarked_collection_fails_only_when_strict() -> None:
    verdict = _judge(strict=True)

    assert verdict.status == FAIL
    assert "nothing attests it" in verdict.detail


def test_an_unreadable_attestation_fails_an_unmarked_collection() -> None:
    verdict = _judge(attestation_error="chroma.embed-attestation.json is not valid JSON")

    assert verdict.status == FAIL
    assert "attestation unusable" in verdict.detail


def test_a_recorded_collection_ignores_a_broken_attestation() -> None:
    verdict = _judge(meta=RECORDED, attestation_error="corrupt")

    assert verdict.status == PASS


def test_a_collection_without_any_metadata_warns() -> None:
    assert _judge(meta={}).status == WARN
    assert _judge(meta={}, strict=True).status == WARN  # not an identity problem


# --------------------------------------------------------------------------------------
# Real scratch stores through the I/O wrapper
# --------------------------------------------------------------------------------------


def _store(path: Path, *names: str, embed_model: str | None = None, dim: int = 8) -> None:
    with ChromaStore(str(path), embed_model=embed_model) as store:
        for name in names:
            store._collection(name).upsert(
                ids=[f"{name}-1"],
                documents=["doc"],
                embeddings=[[1.0] + [0.0] * (dim - 1)],
            )


def _fingerprint(chroma: Path) -> tuple[str, list[str]]:
    digest = hashlib.sha256((chroma / "chroma.sqlite3").read_bytes()).hexdigest()
    return digest, sorted(p.name for p in chroma.iterdir())


def test_a_store_the_production_writer_created_passes_for_both_collections(tmp_path: Path) -> None:
    chroma = tmp_path / "chroma"
    _store(chroma, UNITS, SUMMARIES, embed_model=MODEL)

    verdict = check_embed_identity(chroma, MODEL)

    assert verdict.status == PASS
    assert f"{SUMMARIES}: collection embed_model={MODEL!r}" in verdict.detail


def test_the_summaries_collection_is_judged_only_when_it_exists(tmp_path: Path) -> None:
    chroma = tmp_path / "chroma"
    _store(chroma, UNITS, embed_model=MODEL)

    verdict = check_embed_identity(chroma, MODEL)

    assert verdict.status == PASS
    assert SUMMARIES not in verdict.detail


def test_a_wrong_model_on_the_summaries_collection_alone_fails(tmp_path: Path) -> None:
    chroma = tmp_path / "chroma"
    _store(chroma, UNITS, embed_model=MODEL)
    _store(chroma, SUMMARIES, embed_model="model-a")  # reopened: SUMMARIES is created fresh

    verdict = check_embed_identity(chroma, MODEL)

    assert verdict.status == FAIL
    assert f"{SUMMARIES}: embed model mismatch" in verdict.detail


def test_legacy_store_warns_then_passes_once_attested_and_fails_when_strict_without_it(
    tmp_path: Path,
) -> None:
    chroma = tmp_path / "chroma"
    _store(chroma, UNITS, SUMMARIES)  # created without identity, as the live store was
    assert check_embed_identity(chroma, MODEL).status == WARN
    assert check_embed_identity(chroma, MODEL, strict=True).status == FAIL

    from chroma_readonly import collection_dimension, collection_uuid

    sidecar_path(chroma).write_text(
        json.dumps(
            {
                "schema": ATTESTATION_SCHEMA,
                "collections": {
                    name: {
                        "collection_uuid": collection_uuid(chroma, name),
                        "dimension": collection_dimension(chroma, name),
                        "embed_model": MODEL,
                        "evidence": {},
                    }
                    for name in (UNITS, SUMMARIES)
                },
            }
        ),
        encoding="utf-8",
    )

    assert check_embed_identity(chroma, MODEL).status == PASS
    assert check_embed_identity(chroma, MODEL, strict=True).status == PASS
    # The configuration moving to another model breaks the attestation.
    assert check_embed_identity(chroma, "model-b").status == FAIL


def test_a_corrupt_sidecar_fails_a_legacy_store(tmp_path: Path) -> None:
    chroma = tmp_path / "chroma"
    _store(chroma, UNITS)
    sidecar_path(chroma).write_text("{broken", encoding="utf-8")

    verdict = check_embed_identity(chroma, MODEL)

    assert verdict.status == FAIL
    assert "attestation unusable" in verdict.detail


def test_chroma_contradicting_a_recorded_dimension_fails_on_a_real_store(tmp_path: Path) -> None:
    chroma = tmp_path / "chroma"
    client = chromadb.PersistentClient(path=str(chroma))
    col = client.get_or_create_collection(
        UNITS,
        metadata={**RECORDED, "convmem:embed_dimensions": 768, "hnsw:space": "cosine"},
    )
    col.upsert(ids=["a"], documents=["a"], embeddings=[[1.0, 0.0, 0.0, 0.0]])  # 4, not 768
    del col, client

    verdict = check_embed_identity(chroma, MODEL)

    assert verdict.status == FAIL
    assert "embed dimension mismatch" in verdict.detail


def test_checking_identity_opens_no_client_and_leaves_the_store_untouched(tmp_path: Path) -> None:
    chroma = tmp_path / "chroma"
    _store(chroma, UNITS, SUMMARIES)
    before = _fingerprint(chroma)

    with mock.patch.object(chromadb, "PersistentClient", side_effect=AssertionError("client")):
        check_embed_identity(chroma, MODEL)
        check_embed_identity(chroma, MODEL, strict=True)

    assert _fingerprint(chroma) == before


# --------------------------------------------------------------------------------------
# convmem doctor
# --------------------------------------------------------------------------------------


def _cfg(chroma: Path, **index: Any) -> dict[str, Any]:
    return {
        "index": {"chroma_dir": str(chroma), **index},
        "models": {"embed_model": MODEL},
    }


def test_doctor_reports_each_state_with_the_right_status(tmp_path: Path) -> None:
    created = tmp_path / "created"
    _store(created, UNITS, SUMMARIES, embed_model=MODEL)
    legacy = tmp_path / "legacy"
    _store(legacy, UNITS, SUMMARIES)

    assert _check_embed_collection_identity(_cfg(created)).effective_status() == "pass"
    assert _check_embed_collection_identity(_cfg(legacy)).effective_status() == "warn"
    strict = _check_embed_collection_identity(_cfg(legacy, require_embed_identity=True))
    assert strict.effective_status() == "fail"
    assert strict.ok is False


@pytest.mark.parametrize("value", ["true", 1, "yes", None, False], ids=repr)
def test_only_a_real_true_turns_the_strict_switch_on(tmp_path: Path, value: object) -> None:
    legacy = tmp_path / "legacy"
    _store(legacy, UNITS)

    check = _check_embed_collection_identity(_cfg(legacy, require_embed_identity=value))

    assert check.effective_status() == "warn"


def test_doctor_still_contains_unreadable_stores_as_a_warning(tmp_path: Path) -> None:
    empty = tmp_path / "nothing-here"

    check = _check_embed_collection_identity(_cfg(empty))

    assert check.effective_status() == "warn"
    assert "cannot read collection metadata" in check.detail

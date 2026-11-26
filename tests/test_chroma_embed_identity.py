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
import sqlite3
from pathlib import Path
from typing import Any
from unittest import mock

import chromadb
import pytest

import chroma_embed_identity
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


def _evidence(**over: Any) -> dict[str, Any]:
    """Evidence shaped like what the attestation tool writes."""
    evidence: dict[str, Any] = {
        "method": "reembed-spot-check-v1",
        "attested_at": "2026-11-24T00:00:00Z",
        "population": 100,
        "sample_size": 100,
        "seed": 7,
        "threshold": 0.99,
        "min_cosine": 0.999,
        "mean_cosine": 0.9995,
        "note": "",
    }
    evidence.update(over)
    return evidence


def _attestation(**over: Any) -> CollectionAttestation:
    fields: dict[str, Any] = {
        "name": UNITS,
        "collection_uuid": UUID,
        "dimension": 768,
        "embed_model": MODEL,
        "attested_at": "2026-11-24T00:00:00Z",
        "sample_size": 100,
        "population": 100,
        "min_cosine": 0.999,
        "threshold": 0.99,
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
    base = {
        "collection_uuid": UUID,
        "dimension": 768,
        "embed_model": MODEL,
        "evidence": _evidence(),
    }
    base.update(entry)
    return {"schema": ATTESTATION_SCHEMA, "collections": {UNITS: base}}


def test_read_attestations_without_a_sidecar_means_none(tmp_path: Path) -> None:
    assert not read_attestations(tmp_path / "chroma")


def test_a_valid_sidecar_round_trips(tmp_path: Path) -> None:
    chroma = tmp_path / "chroma"
    sidecar_path(chroma).write_text(json.dumps(_doc()), encoding="utf-8")

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
        # Evidence is part of the claim: a hand-written entry without it is not an attestation.
        _doc(evidence=None),
        _doc(evidence={}),
        _doc(evidence=_evidence(method="hand-written")),
        _doc(evidence=_evidence(attested_at="yesterday")),
        _doc(evidence=_evidence(attested_at=None)),
        _doc(evidence=_evidence(population=0)),
        _doc(evidence=_evidence(population=True)),
        _doc(evidence=_evidence(sample_size=51, population=50)),
        _doc(evidence=_evidence(threshold=0.0)),
        _doc(evidence=_evidence(threshold=float("nan"))),
        _doc(evidence=_evidence(min_cosine=float("nan"))),
        _doc(evidence=_evidence(min_cosine=float("inf"))),
        _doc(evidence=_evidence(min_cosine=0.5)),  # below its own threshold
        _doc(evidence=_evidence(mean_cosine="high")),
    ],
    ids=repr,
)
def test_a_malformed_sidecar_is_refused_not_half_loaded(payload: object) -> None:
    with pytest.raises(AttestationError):
        parse_attestations(payload)


@pytest.mark.parametrize("token", ["NaN", "Infinity", "-Infinity"])
def test_a_non_finite_literal_in_the_file_is_refused(tmp_path: Path, token: str) -> None:
    chroma = tmp_path / "chroma"
    text = json.dumps(_doc()).replace("0.999", token, 1)
    sidecar_path(chroma).write_text(text, encoding="utf-8")

    with pytest.raises(AttestationError, match="not valid JSON"):
        read_attestations(chroma)


def test_a_sidecar_that_is_not_utf8_is_an_attestation_error(tmp_path: Path) -> None:
    chroma = tmp_path / "chroma"
    sidecar_path(chroma).write_bytes(b"\xff\xfe{\x80")

    with pytest.raises(AttestationError, match="cannot read"):
        read_attestations(chroma)


def test_a_relative_chroma_dir_still_gets_its_sidecar_beside_it(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    chroma = tmp_path / "state" / "chroma"
    chroma.mkdir(parents=True)
    monkeypatch.chdir(chroma)

    for spelling in (".", "", "../chroma", "./"):
        path = sidecar_path(spelling or ".")
        assert path == chroma.parent / "chroma.embed-attestation.json", spelling
        assert chroma not in path.parents, spelling


def test_the_filesystem_root_has_no_place_for_a_sidecar() -> None:
    with pytest.raises(AttestationError, match="root"):
        sidecar_path("/")


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


def test_an_empty_collection_without_metadata_warns_even_when_strict() -> None:
    nothing = {"meta": {}, "chroma_dimension": None}
    assert _judge(**nothing).status == WARN
    assert _judge(**nothing, strict=True).status == WARN  # nothing to judge yet


def test_a_collection_with_vectors_and_no_metadata_is_unproven_not_ignored() -> None:
    assert _judge(meta={}).status == WARN
    assert _judge(meta={}, strict=True).status == FAIL
    # ...and an attestation can still vouch for it.
    assert _judge(meta={}, attestation=_attestation(), strict=True).status == PASS


def test_an_empty_unmarked_collection_says_how_to_get_it_stamped() -> None:
    for strict in (False, True):
        verdict = _judge(chroma_dimension=None, row_count=0, strict=strict)
        assert "can be dropped" in verdict.detail
    assert "can be dropped" not in _judge().detail  # one that holds vectors must not be dropped
    # A missing dimension alone is not proof of emptiness: unknown or non-zero counts get no advice.
    assert "can be dropped" not in _judge(chroma_dimension=None).detail
    assert "can be dropped" not in _judge(chroma_dimension=None, row_count=3).detail


def test_an_attestation_needs_a_known_collection_dimension_to_bind_to() -> None:
    unknown = _judge(attestation=_attestation(), chroma_dimension=None)
    assert unknown.status == WARN
    assert _judge(attestation=_attestation(), chroma_dimension=None, strict=True).status == FAIL


def test_strict_accepts_only_an_attestation_that_checked_every_row() -> None:
    sampled = _attestation(sample_size=50, population=1000)
    unknown = _attestation(sample_size=None, population=None)

    # The default mode still takes a sampled attestation and says how much was checked.
    assert _judge(attestation=sampled).status == PASS
    for partial in (sampled, unknown):
        verdict = _judge(attestation=partial, strict=True)
        assert verdict.status == FAIL and "--sample-size all" in verdict.detail
    assert _judge(attestation=_attestation(), strict=True).status == PASS


def test_an_attested_detail_says_how_much_was_sampled() -> None:
    verdict = _judge(attestation=_attestation(sample_size=50, population=1000))
    assert verdict.status == PASS and "sampled 50 of 1000" in verdict.detail


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
                        "evidence": _evidence(),
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


def test_a_sidecar_that_is_not_utf8_fails_a_legacy_store(tmp_path: Path) -> None:
    chroma = tmp_path / "chroma"
    _store(chroma, UNITS)
    sidecar_path(chroma).write_bytes(b"\xff\xfe{\x80")

    verdict = check_embed_identity(chroma, MODEL)

    assert verdict.status == FAIL and "attestation unusable" in verdict.detail


def test_one_collection_that_cannot_be_read_does_not_hide_anothers_failure(
    tmp_path: Path,
) -> None:
    chroma = tmp_path / "chroma"
    _store(chroma, UNITS, SUMMARIES, embed_model="model-a")  # units: a definite mismatch
    real = chroma_embed_identity.collection_identity_facts_many

    def flaky(directory: Any, names: Any) -> Any:
        facts = dict(real(directory, names))
        facts[SUMMARIES] = sqlite3.OperationalError("database disk image is malformed")
        return facts

    with mock.patch.object(chroma_embed_identity, "collection_identity_facts_many", flaky):
        default = check_embed_identity(chroma, "model-b")
        strict = check_embed_identity(chroma, "model-b", strict=True)

    for verdict in (default, strict):
        assert verdict.status == FAIL  # the mismatch survives the unreadable collection
        assert "embed model mismatch" in verdict.detail
        assert "cannot read collection metadata" in verdict.detail


def test_a_sidecar_nested_deeply_enough_to_overflow_the_parser_fails_a_legacy_store(
    tmp_path: Path,
) -> None:
    chroma = tmp_path / "chroma"
    _store(chroma, UNITS)
    sidecar_path(chroma).write_text("[" * 200_000, encoding="utf-8")

    verdict = check_embed_identity(chroma, MODEL)  # must not raise

    assert verdict.status == FAIL and "attestation unusable" in verdict.detail


def test_an_unexpected_error_in_one_collection_does_not_hide_anothers_failure(
    tmp_path: Path,
) -> None:
    chroma = tmp_path / "chroma"
    _store(chroma, UNITS, SUMMARIES, embed_model="model-a")  # units: a definite mismatch
    real = chroma_embed_identity.collection_identity_facts_many

    def surprising(directory: Any, names: Any) -> Any:
        facts = dict(real(directory, names))
        facts[SUMMARIES] = TypeError("something nobody planned for")
        return facts

    with mock.patch.object(chroma_embed_identity, "collection_identity_facts_many", surprising):
        verdict = check_embed_identity(chroma, "model-b")

    assert verdict.status == FAIL
    assert "embed model mismatch" in verdict.detail and "cannot read" in verdict.detail


def test_an_unreadable_collection_is_a_warn_and_a_strict_fail(tmp_path: Path) -> None:
    chroma = tmp_path / "chroma"
    _store(chroma, UNITS, embed_model=MODEL)

    with mock.patch.object(
        chroma_embed_identity, "collection_identity_facts_many", side_effect=sqlite3.OperationalError("locked")
    ):
        assert check_embed_identity(chroma, MODEL).status == WARN
        assert check_embed_identity(chroma, MODEL, strict=True).status == FAIL


@pytest.mark.parametrize("configured", ["", "   ", None])
def test_no_configured_model_cannot_pass_anything(tmp_path: Path, configured: str | None) -> None:
    chroma = tmp_path / "chroma"
    _store(chroma, UNITS, SUMMARIES, embed_model=MODEL)

    default = check_embed_identity(chroma, configured)  # type: ignore[arg-type]
    strict = check_embed_identity(chroma, configured, strict=True)  # type: ignore[arg-type]

    assert default.status == WARN and "no [models] embed_model is configured" in default.detail
    assert strict.status == FAIL


def test_a_model_name_is_compared_the_way_it_is_stamped(tmp_path: Path) -> None:
    chroma = tmp_path / "chroma"
    _store(chroma, UNITS, SUMMARIES, embed_model=" model ")  # recorded as 'model'

    assert check_embed_identity(chroma, " model ", strict=True).status == PASS
    assert check_embed_identity(chroma, "model", strict=True).status == PASS
    assert check_embed_identity(chroma, "model-b", strict=True).status == FAIL


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
    assert check.detail.count("cannot read collection metadata") == 1  # knowledge_units only


# --------------------------------------------------------------------------------------
# Reads must describe the collection the client serves, and survive hostile sidecars
# --------------------------------------------------------------------------------------


def test_populated_storage_is_never_called_empty_when_its_labels_are_damaged(tmp_path: Path) -> None:
    chroma = tmp_path / "chroma"
    _store(chroma, UNITS)
    with sqlite3.connect(chroma / "chroma.sqlite3") as con:  # scratch: damage the labels, keep the row
        con.execute("UPDATE collections SET dimension = NULL")
        con.execute("UPDATE segments SET scope = 'BROKEN'")

    default = check_embed_identity(chroma, MODEL)
    strict = check_embed_identity(chroma, MODEL, strict=True)

    assert "can be dropped" not in default.detail and "can be dropped" not in strict.detail
    assert default.status == WARN and strict.status == FAIL


def test_rows_without_any_metadata_are_unproven_under_strict_not_waved_through(tmp_path: Path) -> None:
    chroma = tmp_path / "chroma"
    _store(chroma, UNITS)
    with sqlite3.connect(chroma / "chroma.sqlite3") as con:
        con.execute("DELETE FROM collection_metadata")
        con.execute("UPDATE collections SET dimension = NULL")

    assert check_embed_identity(chroma, MODEL).status == WARN
    assert check_embed_identity(chroma, MODEL, strict=True).status == FAIL


@pytest.mark.parametrize(
    "evidence",
    [
        {"sample_size": 1, "population": 1, "min_cosine": 1.0, "mean_cosine": 0.0},  # one row: they must agree
        {"sample_size": 1, "population": 1, "min_cosine": 0.995, "mean_cosine": 1.0},
        {"sample_size": 5, "population": 5, "min_cosine": 1.0, "mean_cosine": 0.5},  # mean below the minimum
    ],
    ids=["one-row-mean-zero", "one-row-mean-above-min", "mean-below-min"],
)
def test_contradictory_census_numbers_are_not_an_attestation(evidence: dict) -> None:
    with pytest.raises(AttestationError, match="mean_cosine"):
        parse_attestations(_doc(evidence=_evidence(**evidence)))


_HOSTILE = [None, True, "x", [], {}, 10**400, -(10**400), 2**63, -1, 0, 1.5, "NaN"]


def test_no_sidecar_content_can_make_the_check_raise_or_hide_a_definite_failure(
    tmp_path: Path,
) -> None:
    chroma = tmp_path / "chroma"
    _store(chroma, UNITS)  # legacy: the sidecar is the only thing that can vouch for it
    from chroma_readonly import collection_dimension, collection_uuid

    good = _doc(
        collection_uuid=collection_uuid(chroma, UNITS),
        dimension=collection_dimension(chroma, UNITS),
    )
    entry = good["collections"][UNITS]
    paths = [(k,) for k in ("collection_uuid", "dimension", "embed_model", "evidence")]
    paths += [("evidence", k) for k in entry["evidence"]]
    for path in paths:
        for bad in _HOSTILE:
            doc = json.loads(json.dumps(good))
            target = doc["collections"][UNITS]
            for key in path[:-1]:
                target = target[key]
            target[path[-1]] = bad
            sidecar_path(chroma).write_text(json.dumps(doc), encoding="utf-8")

            verdict = check_embed_identity(chroma, MODEL, strict=True)  # must not raise

            assert verdict.status in (PASS, FAIL), (path, bad, verdict)
            if verdict.status == PASS:  # only a mutation that does not change the claim may pass
                assert path in (("evidence", "note"), ("evidence", "seed"), ("evidence", "mean_cosine")), (path, bad)


def test_a_missing_dimension_alone_is_not_proof_a_collection_is_empty(tmp_path: Path) -> None:
    chroma = tmp_path / "chroma"
    _store(chroma, UNITS)
    with sqlite3.connect(chroma / "chroma.sqlite3") as con:  # a scratch store: simulate damage
        con.execute("UPDATE collections SET dimension = NULL")

    verdict = check_embed_identity(chroma, MODEL)

    assert verdict.status == WARN and "can be dropped" not in verdict.detail


def test_a_bare_model_name_and_its_latest_tag_are_one_model_for_doctor(tmp_path: Path) -> None:
    chroma = tmp_path / "chroma"
    _store(chroma, UNITS, SUMMARIES, embed_model="nomic-embed-text")

    assert check_embed_identity(chroma, "nomic-embed-text:latest", strict=True).status == PASS
    assert check_embed_identity(chroma, "nomic-embed-text:v1.5", strict=True).status == FAIL

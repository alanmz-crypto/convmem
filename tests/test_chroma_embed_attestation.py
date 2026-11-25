"""Attesting the embedding model of collections that predate identity recording.

Hermetic: a "live" store and its "restore copy" live in ``tmp_path`` and vectors
come from a deterministic fake embedder, so no embedding service runs. The live
store is never opened with a Chroma client by the code under test; these tests
prove that by hashing its SQLite file and listing its directory before and after.
"""

# pylint: disable=protected-access,too-many-arguments

from __future__ import annotations

import hashlib
import json
import math
import os
import shutil
from pathlib import Path
from unittest import mock

import pytest

import chroma_embed_attestation as attestation_mod
from chroma_embed_attestation import (
    AttestationError,
    attest_collections,
    cosine,
    main,
    spot_check,
)
from chroma_embed_identity import (
    PASS,
    WARN,
    check_embed_identity,
    read_attestations,
    sidecar_path,
)
from chroma_readonly import collection_config_metadata, collection_dimension, collection_uuid
from chroma_store import EMBED_MODEL_KEY, SUMMARIES, UNITS, ChromaStore

MODEL = "nomic-embed-text:latest"
DIM = 16
POPULATION = 12


def fake_embed(model: str, text: str, dim: int = DIM) -> list[float]:
    """Deterministic, model-specific vector: same model and text, same vector."""
    digest = hashlib.sha256(f"{model}\x00{text}".encode()).digest()
    return [digest[i % len(digest)] / 255.0 - 0.5 for i in range(dim)]


def embedder(model: str, dim: int = DIM):
    return lambda text: fake_embed(model, text, dim)


def build(
    path: Path,
    *names: str,
    vectors_from: str = MODEL,
    n: int = POPULATION,
    embed_model: str | None = None,
) -> None:
    """A store whose vectors were made by ``vectors_from``; identity only if asked."""
    with ChromaStore(str(path), embed_model=embed_model) as store:
        for name in names:
            docs = [f"{name} document number {i}" for i in range(n)]
            store._collection(name).upsert(
                ids=[f"{name}-{i}" for i in range(n)],
                documents=docs,
                embeddings=[fake_embed(vectors_from, d) for d in docs],
            )


@pytest.fixture(name="stores")
def fixture_stores(tmp_path: Path) -> tuple[Path, Path]:
    """A legacy (unmarked) live store with both collections, and a restore copy."""
    live = tmp_path / "live" / "chroma"
    build(live, UNITS, SUMMARIES)
    copy = tmp_path / "restored" / "chroma"
    shutil.copytree(live, copy)
    return live, copy


def fingerprint(chroma: Path) -> tuple[str, list[str]]:
    digest = hashlib.sha256((chroma / "chroma.sqlite3").read_bytes()).hexdigest()
    return digest, sorted(p.name for p in chroma.iterdir())


# --------------------------------------------------------------------------------------
# The measurement
# --------------------------------------------------------------------------------------


def test_cosine_scores_identical_orthogonal_and_opposite_vectors() -> None:
    assert cosine([1.0, 2.0], [2.0, 4.0]) == pytest.approx(1.0)
    assert cosine([1.0, 0.0], [0.0, 1.0]) == pytest.approx(0.0)
    assert cosine([1.0, 0.0], [-1.0, 0.0]) == pytest.approx(-1.0)


@pytest.mark.parametrize(
    "left,right,match",
    [
        ([0.0, 0.0], [1.0, 1.0], "all zeros"),
        ([1.0, 1.0], [0.0, 0.0], "all zeros"),
        ([1.0, math.nan], [1.0, 1.0], "non-finite"),
        ([1.0, 1.0], [math.inf, 1.0], "non-finite"),
        ([1.0, 1.0], [-math.inf, 1.0], "non-finite"),
    ],
)
def test_a_vector_that_measures_nothing_is_an_error_not_a_score(left, right, match) -> None:
    with pytest.raises(AttestationError, match=match):
        cosine(left, right)


def test_vectors_of_different_length_are_an_error_not_a_score() -> None:
    with pytest.raises(AttestationError, match="dimensions"):
        cosine([1.0, 0.0], [1.0, 0.0, 0.0])


def test_the_right_model_reproduces_stored_vectors_and_another_does_not(
    stores: tuple[Path, Path],
) -> None:
    _, copy = stores

    right = spot_check(copy, UNITS, embedder(MODEL))
    wrong = spot_check(copy, UNITS, embedder("some-other-model"))

    assert right.min_cosine == pytest.approx(1.0)
    assert right.sample_size == right.population == POPULATION
    assert right.dimension == DIM
    assert wrong.min_cosine < 0.9


def test_the_sample_is_reproducible_and_bounded(tmp_path: Path) -> None:
    copy = tmp_path / "chroma"
    build(copy, UNITS, n=40)

    first = spot_check(copy, UNITS, embedder(MODEL), sample_size=15, seed=3)
    again = spot_check(copy, UNITS, embedder(MODEL), sample_size=15, seed=3)

    assert first == again
    assert first.sample_size == 15 and first.population == 40


def test_a_sample_below_the_minimum_is_refused(tmp_path: Path) -> None:
    copy = tmp_path / "chroma"
    build(copy, UNITS, n=40)

    with pytest.raises(AttestationError, match="below the minimum"):
        spot_check(copy, UNITS, embedder(MODEL), sample_size=3)


def test_an_embedder_of_another_dimension_is_an_error(stores: tuple[Path, Path]) -> None:
    _, copy = stores

    with pytest.raises(AttestationError, match="dimensions"):
        spot_check(copy, UNITS, embedder(MODEL, dim=DIM + 4))


def test_spot_check_never_creates_a_missing_collection(tmp_path: Path) -> None:
    copy = tmp_path / "chroma"
    build(copy, UNITS)

    with pytest.raises(AttestationError):
        spot_check(copy, SUMMARIES, embedder(MODEL))

    assert collection_uuid(copy, SUMMARIES) is None


def test_a_restore_copy_missing_knowledge_units_is_reported_as_incomplete(tmp_path: Path) -> None:
    copy = tmp_path / "chroma"
    build(copy, SUMMARIES)  # the verify opener insists on knowledge_units existing

    with pytest.raises(AttestationError, match="restore copy is incomplete"):
        spot_check(copy, SUMMARIES, embedder(MODEL))

    assert collection_uuid(copy, UNITS) is None  # and it was not created to satisfy the opener


# --------------------------------------------------------------------------------------
# Attesting
# --------------------------------------------------------------------------------------


def test_a_dry_run_checks_everything_and_writes_nothing(stores: tuple[Path, Path]) -> None:
    live, copy = stores
    before = fingerprint(live)

    report = attest_collections(live, copy, model=MODEL, embed=embedder(MODEL))

    assert sorted(report.attested) == sorted([UNITS, SUMMARIES])
    assert report.written is False
    assert not sidecar_path(live).exists()
    assert fingerprint(live) == before


def test_writing_records_an_attestation_doctor_accepts_and_never_touches_live(
    stores: tuple[Path, Path],
) -> None:
    live, copy = stores
    before = fingerprint(live)
    metadata_before = {n: collection_config_metadata(live, n) for n in (UNITS, SUMMARIES)}
    assert check_embed_identity(live, MODEL).status == WARN

    report = attest_collections(live, copy, model=MODEL, embed=embedder(MODEL), write=True)

    assert report.written is True and report.path == sidecar_path(live)
    assert fingerprint(live) == before  # the Chroma directory is byte-identical
    assert {n: collection_config_metadata(live, n) for n in (UNITS, SUMMARIES)} == metadata_before
    stored = read_attestations(live)
    assert stored[UNITS].collection_uuid == collection_uuid(live, UNITS)
    assert stored[UNITS].dimension == collection_dimension(live, UNITS) == DIM
    assert stored[UNITS].embed_model == MODEL
    verdict = check_embed_identity(live, MODEL, strict=True)
    assert verdict.status == PASS and "attested legacy" in verdict.detail
    # The evidence is recorded for a human reader.
    evidence = json.loads(sidecar_path(live).read_text(encoding="utf-8"))["collections"][UNITS]
    assert evidence["evidence"]["method"] == "reembed-spot-check-v1"
    assert evidence["evidence"]["min_cosine"] == pytest.approx(1.0)
    assert not [p for p in sidecar_path(live).parent.iterdir() if p.suffix == ".tmp"]


def test_a_claimed_model_that_did_not_make_the_vectors_is_refused(
    stores: tuple[Path, Path],
) -> None:
    live, copy = stores

    with pytest.raises(AttestationError, match="does not reproduce"):
        attest_collections(live, copy, model="some-other-model", embed=embedder("some-other-model"), write=True)

    assert not sidecar_path(live).exists()


def test_one_collection_failing_writes_nothing_for_either(stores: tuple[Path, Path]) -> None:
    live, _ = stores
    # SUMMARIES vectors in the copy were made by a different model than UNITS.
    copy = live.parent.parent / "mixed" / "chroma"
    build(copy, UNITS, vectors_from=MODEL)
    build(copy, SUMMARIES, vectors_from="some-other-model")
    mixed_live = live.parent.parent / "mixed-live" / "chroma"
    shutil.copytree(copy, mixed_live)

    with pytest.raises(AttestationError):
        attest_collections(mixed_live, copy, model=MODEL, embed=embedder(MODEL), write=True)

    assert not sidecar_path(mixed_live).exists()


@pytest.mark.parametrize("where", ["same", "inside-live", "contains-live"])
def test_a_restore_copy_that_overlaps_the_live_directory_is_refused(
    stores: tuple[Path, Path], where: str
) -> None:
    live, _ = stores
    before = fingerprint(live)
    target = {
        "same": live,
        "inside-live": live / "nested-copy",
        "contains-live": live.parent,
    }[where]

    with mock.patch.object(
        attestation_mod, "open_chroma_for_verify", side_effect=AssertionError("client")
    ):
        with pytest.raises(AttestationError, match="separate directory"):
            attest_collections(live, target, model=MODEL, embed=embedder(MODEL), write=True)

    assert fingerprint(live) == before
    assert not sidecar_path(live).exists()


@pytest.mark.parametrize(
    "link,message",
    [(os.link, "own files"), (os.symlink, "symlink")],
    ids=["hardlinks", "symlinks"],
)
def test_a_copy_that_shares_files_with_the_live_store_is_refused(
    stores: tuple[Path, Path], tmp_path: Path, link, message: str
) -> None:
    live, _ = stores
    before = fingerprint(live)
    clone = tmp_path / "linked" / "chroma"
    clone.mkdir(parents=True)
    for entry in live.iterdir():
        if entry.is_file():
            link(entry, clone / entry.name)  # same inode (hardlink) or a path alias (symlink)
        else:
            shutil.copytree(entry, clone / entry.name)

    with mock.patch.object(
        attestation_mod, "open_chroma_for_verify", side_effect=AssertionError("client")
    ):
        with pytest.raises(AttestationError, match=message):
            attest_collections(live, clone, model=MODEL, embed=embedder(MODEL), write=True)

    assert fingerprint(live) == before
    assert not sidecar_path(live).exists()


def test_a_copy_of_some_other_store_is_refused(tmp_path: Path, stores: tuple[Path, Path]) -> None:
    live, _ = stores
    stranger = tmp_path / "stranger" / "chroma"
    build(stranger, UNITS, SUMMARIES)  # same documents, same vectors, different collection UUIDs

    with pytest.raises(AttestationError, match="not a copy of this collection"):
        attest_collections(live, stranger, model=MODEL, embed=embedder(MODEL), write=True)

    assert not sidecar_path(live).exists()


def test_a_collection_that_already_records_its_model_is_never_relabelled(tmp_path: Path) -> None:
    live = tmp_path / "live" / "chroma"
    build(live, UNITS, embed_model="model-a")
    copy = tmp_path / "restored" / "chroma"
    shutil.copytree(live, copy)

    with pytest.raises(AttestationError, match="nothing to attest"):
        attest_collections(live, copy, model=MODEL, embed=embedder(MODEL), names=(UNITS,), write=True)

    assert collection_config_metadata(live, UNITS)[EMBED_MODEL_KEY] == "model-a"
    assert not sidecar_path(live).exists()


def test_a_missing_summaries_collection_is_skipped_not_created(tmp_path: Path) -> None:
    live = tmp_path / "live" / "chroma"
    build(live, UNITS)
    copy = tmp_path / "restored" / "chroma"
    shutil.copytree(live, copy)

    report = attest_collections(live, copy, model=MODEL, embed=embedder(MODEL), write=True)

    assert list(report.attested) == [UNITS]
    assert SUMMARIES in report.skipped
    assert collection_uuid(live, SUMMARIES) is None and collection_uuid(copy, SUMMARIES) is None


def test_a_later_run_adds_entries_without_losing_earlier_evidence(
    stores: tuple[Path, Path],
) -> None:
    live, copy = stores
    attest_collections(
        live, copy, model=MODEL, embed=embedder(MODEL), names=(UNITS,), note="first", write=True
    )
    attest_collections(
        live, copy, model=MODEL, embed=embedder(MODEL), names=(SUMMARIES,), note="second", write=True
    )

    document = json.loads(sidecar_path(live).read_text(encoding="utf-8"))["collections"]
    assert sorted(document) == sorted([UNITS, SUMMARIES])
    assert document[UNITS]["evidence"]["note"] == "first"
    assert document[SUMMARIES]["evidence"]["note"] == "second"


def test_a_corrupt_existing_sidecar_is_not_overwritten(stores: tuple[Path, Path]) -> None:
    live, copy = stores
    sidecar_path(live).write_text("{broken", encoding="utf-8")

    with pytest.raises(AttestationError):
        attest_collections(live, copy, model=MODEL, embed=embedder(MODEL), write=True)

    assert sidecar_path(live).read_text(encoding="utf-8") == "{broken"


@pytest.mark.parametrize("model", ["", "   ", None])
def test_an_empty_model_is_refused(stores: tuple[Path, Path], model: str | None) -> None:
    live, copy = stores

    with pytest.raises(AttestationError, match="embed model is required"):
        attest_collections(live, copy, model=model or "", embed=embedder(MODEL), write=True)


def test_an_empty_live_collection_cannot_be_attested(tmp_path: Path) -> None:
    live = tmp_path / "live" / "chroma"
    with ChromaStore(str(live)) as store:
        store._collection(UNITS)  # exists, holds no vectors
    copy = tmp_path / "restored" / "chroma"
    shutil.copytree(live, copy)

    with pytest.raises(AttestationError, match="same non-empty vector dimension"):
        attest_collections(live, copy, model=MODEL, embed=embedder(MODEL), names=(UNITS,), write=True)


# --------------------------------------------------------------------------------------
# What a run must refuse to publish
# --------------------------------------------------------------------------------------


@pytest.mark.parametrize("bad", [math.nan, math.inf, -math.inf], ids=["nan", "inf", "-inf"])
def test_a_provider_that_returns_non_finite_vectors_publishes_nothing(
    stores: tuple[Path, Path], bad: float
) -> None:
    live, copy = stores

    with pytest.raises(AttestationError, match="non-finite"):
        attest_collections(live, copy, model=MODEL, embed=lambda _text: [bad] * DIM, write=True)

    assert not sidecar_path(live).exists()


def test_a_provider_that_returns_zero_vectors_publishes_nothing(stores: tuple[Path, Path]) -> None:
    live, copy = stores

    with pytest.raises(AttestationError, match="all zeros"):
        attest_collections(live, copy, model=MODEL, embed=lambda _text: [0.0] * DIM, write=True)

    assert not sidecar_path(live).exists()


@pytest.mark.parametrize("threshold", [math.nan, math.inf, 0.0, -0.5, 1.5])
def test_a_threshold_that_cannot_reject_anything_is_refused(
    stores: tuple[Path, Path], threshold: float
) -> None:
    live, copy = stores

    with pytest.raises(AttestationError, match="threshold"):
        attest_collections(
            live, copy, model=MODEL, embed=embedder(MODEL), threshold=threshold, write=True
        )

    assert not sidecar_path(live).exists()


def test_a_short_read_of_the_sampled_vectors_is_refused(stores: tuple[Path, Path]) -> None:
    """The copy must return every sampled id; a partial answer is not a passing sample."""
    _, copy = stores

    class _Short:
        def get(self, ids, include):  # pylint: disable=unused-argument
            kept = list(ids)[:-1]
            return {
                "ids": kept,
                "documents": [f"doc {i}" for i in kept],
                "embeddings": [[1.0] * DIM for _ in kept],
            }

    class _Store:
        def _collection(self, _name):
            return _Short()

        def close(self) -> None:
            pass

    with mock.patch.object(attestation_mod, "open_chroma_for_verify", return_value=_Store()):
        with pytest.raises(AttestationError, match="could not read every sampled vector"):
            spot_check(copy, UNITS, embedder(MODEL))


def test_a_full_check_catches_foreign_vectors_a_sample_can_miss(tmp_path: Path) -> None:
    """The sampling limit, pinned: foreign rows outside the sample pass; a census refuses."""
    live = tmp_path / "live" / "chroma"
    n = 100
    docs = {f"u-{i:03d}": f"unit document {i}" for i in range(n)}
    sampled = set(attestation_mod._sample_ids(sorted(docs), 20, 5))
    with ChromaStore(str(live)) as store:
        store._collection(UNITS).upsert(
            ids=sorted(docs),
            documents=[docs[i] for i in sorted(docs)],
            embeddings=[
                fake_embed(MODEL if i in sampled else "another-model", docs[i])
                for i in sorted(docs)
            ],
        )
    copy = tmp_path / "restored" / "chroma"
    shutil.copytree(live, copy)

    passed = attest_collections(
        live, copy, model=MODEL, embed=embedder(MODEL), names=(UNITS,), sample_size=20, seed=5
    )
    assert passed.evidence[UNITS]["sample_size"] == 20  # the sample alone cannot tell

    with pytest.raises(AttestationError, match="does not reproduce"):
        attest_collections(
            live, copy, model=MODEL, embed=embedder(MODEL), names=(UNITS,), sample_size=None
        )


def test_checking_every_row_records_a_full_census(tmp_path: Path) -> None:
    live = tmp_path / "live" / "chroma"
    build(live, UNITS, n=60)
    copy = tmp_path / "restored" / "chroma"
    shutil.copytree(live, copy)

    report = attest_collections(
        live, copy, model=MODEL, embed=embedder(MODEL), sample_size=None, write=True
    )

    assert report.evidence[UNITS]["sample_size"] == report.evidence[UNITS]["population"] == 60
    assert "sampled 60 of 60" in check_embed_identity(live, MODEL).detail


def test_the_seed_is_random_unless_given_and_always_recorded(stores: tuple[Path, Path]) -> None:
    live, copy = stores

    drawn = attest_collections(live, copy, model=MODEL, embed=embedder(MODEL))
    fixed = attest_collections(live, copy, model=MODEL, embed=embedder(MODEL), seed=41)

    assert isinstance(drawn.evidence[UNITS]["seed"], int)
    assert fixed.evidence[UNITS]["seed"] == 41


def test_a_collection_asked_for_by_name_must_exist(tmp_path: Path) -> None:
    live = tmp_path / "live" / "chroma"
    build(live, UNITS)
    copy = tmp_path / "restored" / "chroma"
    shutil.copytree(live, copy)

    with pytest.raises(AttestationError, match="no such collection"):
        attest_collections(
            live, copy, model=MODEL, embed=embedder(MODEL), names=(UNITS, SUMMARIES), write=True
        )

    assert not sidecar_path(live).exists()  # units passed, but nothing is half-published


def test_two_attestations_finishing_out_of_order_keep_both_entries(
    stores: tuple[Path, Path],
) -> None:
    live, copy = stores
    nested: list[bool] = []

    def embed_then_let_another_run_finish(text: str) -> list[float]:
        if not nested:
            nested.append(True)
            attest_collections(
                live, copy, model=MODEL, embed=embedder(MODEL), names=(SUMMARIES,), write=True
            )
        return fake_embed(MODEL, text)

    attest_collections(
        live, copy, model=MODEL, embed=embed_then_let_another_run_finish, names=(UNITS,), write=True
    )

    assert sorted(read_attestations(live)) == sorted([UNITS, SUMMARIES])


def test_a_relative_live_path_never_writes_inside_the_live_directory(
    stores: tuple[Path, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    live, copy = stores
    monkeypatch.chdir(live)

    report = attest_collections(".", copy, model=MODEL, embed=embedder(MODEL), write=True)

    assert report.path == live.parent / "chroma.embed-attestation.json"
    assert not [p for p in live.iterdir() if "attestation" in p.name]


def test_a_copy_sharing_only_a_segment_file_with_the_live_store_is_refused(
    stores: tuple[Path, Path],
) -> None:
    live, copy = stores
    before = fingerprint(live)
    shared = next(p for p in live.rglob("*") if p.is_file() and p.parent != live)
    twin = copy / shared.relative_to(live)
    twin.unlink()
    os.link(shared, twin)  # chroma.sqlite3 stays separate; one segment file is the live inode

    with mock.patch.object(
        attestation_mod, "open_chroma_for_verify", side_effect=AssertionError("client")
    ):
        with pytest.raises(AttestationError, match="own files"):
            attest_collections(live, copy, model=MODEL, embed=embedder(MODEL), write=True)

    assert fingerprint(live) == before and not sidecar_path(live).exists()


def test_the_copy_is_checked_again_before_each_collection_is_opened(
    stores: tuple[Path, Path],
) -> None:
    """A copy that becomes a hardlink after the first check must not reach a client."""
    live, copy = stores
    shared = next(p for p in live.rglob("*") if p.is_file() and p.parent != live)
    swapped: list[bool] = []

    def embed_and_swap(text: str) -> list[float]:
        if not swapped:
            swapped.append(True)
            twin = copy / shared.relative_to(live)
            twin.unlink()
            os.link(shared, twin)
        return fake_embed(MODEL, text)

    with pytest.raises(AttestationError, match="own files"):
        attest_collections(
            live, copy, model=MODEL, embed=embed_and_swap, names=(UNITS, SUMMARIES), write=True
        )

    assert not sidecar_path(live).exists()


def test_a_copy_whose_segment_directory_is_a_link_into_live_is_refused(
    stores: tuple[Path, Path],
) -> None:
    live, copy = stores
    segment = next(p for p in live.iterdir() if p.is_dir())
    shutil.rmtree(copy / segment.name)
    os.symlink(segment, copy / segment.name)

    with mock.patch.object(
        attestation_mod, "open_chroma_for_verify", side_effect=AssertionError("client")
    ):
        with pytest.raises(AttestationError, match="symlink"):
            attest_collections(live, copy, model=MODEL, embed=embedder(MODEL), write=True)


def test_a_directory_that_cannot_be_inspected_refuses_the_copy(stores: tuple[Path, Path]) -> None:
    live, copy = stores
    real_walk = os.walk

    def failing_walk(top, **kwargs):
        if Path(top) == copy.resolve():
            kwargs["onerror"](PermissionError(13, "denied", str(top)))
            return iter(())
        return real_walk(top, **kwargs)

    with mock.patch.object(attestation_mod.os, "walk", failing_walk):
        with pytest.raises(AttestationError, match="cannot inspect"):
            attest_collections(live, copy, model=MODEL, embed=embedder(MODEL), write=True)


# --------------------------------------------------------------------------------------
# The command line
# --------------------------------------------------------------------------------------


def _config(path: Path, live: Path) -> Path:
    path.write_text(
        f'[index]\nchroma_dir = "{live}"\n'
        f'[models]\nembed_model = "{MODEL}"\nollama_host = "http://127.0.0.1:1"\n',
        encoding="utf-8",
    )
    return path


def test_the_command_is_a_dry_run_unless_asked_to_write(
    tmp_path: Path, stores: tuple[Path, Path], capsys: pytest.CaptureFixture[str]
) -> None:
    live, copy = stores
    cfg = _config(tmp_path / "config.toml", live)
    fake = mock.patch.object(attestation_mod, "_ollama_embedder", return_value=embedder(MODEL))

    with fake:
        assert main(["--config", str(cfg), "--restore-copy", str(copy)]) == 0
    assert "dry run" in capsys.readouterr().out
    assert not sidecar_path(live).exists()

    with fake:
        assert main(["--config", str(cfg), "--restore-copy", str(copy), "--write"]) == 0
    assert "wrote" in capsys.readouterr().out
    assert sidecar_path(live).is_file()


def test_the_command_reports_a_refusal_and_exits_nonzero(
    tmp_path: Path, stores: tuple[Path, Path], capsys: pytest.CaptureFixture[str]
) -> None:
    live, _ = stores
    cfg = _config(tmp_path / "config.toml", live)

    with mock.patch.object(attestation_mod, "_ollama_embedder", return_value=embedder(MODEL)):
        code = main(["--config", str(cfg), "--restore-copy", str(live), "--write"])

    assert code == 2
    assert "attestation refused" in capsys.readouterr().err
    assert not sidecar_path(live).exists()


@pytest.mark.parametrize("value", ["nan", "0", "1.5", "-1", "inf", "high"])
def test_the_command_rejects_a_threshold_that_cannot_reject(
    tmp_path: Path, stores: tuple[Path, Path], value: str
) -> None:
    live, copy = stores
    cfg = _config(tmp_path / "config.toml", live)

    with pytest.raises(SystemExit) as raised:
        main(["--config", str(cfg), "--restore-copy", str(copy), "--threshold", value])

    assert raised.value.code == 2


@pytest.mark.parametrize("value", ["0", "-3", "some"])
def test_the_command_rejects_a_sample_size_that_is_not_a_count_or_all(
    tmp_path: Path, stores: tuple[Path, Path], value: str
) -> None:
    live, copy = stores
    cfg = _config(tmp_path / "config.toml", live)

    with pytest.raises(SystemExit) as raised:
        main(["--config", str(cfg), "--restore-copy", str(copy), "--sample-size", value])

    assert raised.value.code == 2


def test_the_command_can_check_every_row_and_says_when_it_did_not(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    live = tmp_path / "live" / "chroma"
    build(live, UNITS, n=60)
    copy = tmp_path / "restored" / "chroma"
    shutil.copytree(live, copy)
    cfg = _config(tmp_path / "config.toml", live)

    with mock.patch.object(attestation_mod, "_ollama_embedder", return_value=embedder(MODEL)):
        assert main(["--config", str(cfg), "--restore-copy", str(copy)]) == 0
        sampled = capsys.readouterr().out
        assert main(["--config", str(cfg), "--restore-copy", str(copy), "--sample-size", "all"]) == 0
        full = capsys.readouterr().out

    assert "sample=50/60" in sampled and "cannot rule out a minority" in sampled
    assert "sample=60/60" in full and "cannot rule out" not in full

"""Attesting at scale: row-level failures, retries, progress, subnormal arithmetic, WAL, locks.

Split out of ``test_chroma_embed_attestation`` (which is at the module-size limit). Hermetic in
the same way: a "live" store and its "restore copy" live in ``tmp_path``, vectors come from a
deterministic fake embedder, and the live store is only ever read through SQLite ``mode=ro``.
"""

# pylint: disable=protected-access,too-many-arguments

from __future__ import annotations

import math
import shutil
import sqlite3
from pathlib import Path
from unittest import mock

import pytest

import chroma_embed_attestation as attestation_mod
from chroma_embed_attestation import AttestationError, attest_collections, cosine, main, spot_check
from chroma_embed_identity import sidecar_path
from chroma_store import SUMMARIES, UNITS
# Helpers and the ``stores`` fixture only (importing the fixture registers it); no test_* names.
from tests.test_chroma_embed_attestation import (  # pylint: disable=unused-import
    MODEL,
    POPULATION,
    _config,
    build,
    embedder,
    fake_embed,
    fixture_stores,
)


def test_cosine_of_subnormal_vectors_is_the_true_angle() -> None:
    assert cosine([1.0, 0.0], [5e-324, 5e-324]) == pytest.approx(math.sqrt(0.5))  # was 1.0
    assert cosine([5e-324, 5e-324], [5e-324, 5e-324]) == pytest.approx(1.0)
    assert cosine([1e-300, 0.0], [1e-300, 1e-300]) == pytest.approx(math.sqrt(0.5))


def test_a_provider_failure_names_the_collection_and_row_and_keeps_the_old_sidecar(
    stores: tuple[Path, Path],
) -> None:
    live, copy = stores
    attest_collections(live, copy, model=MODEL, embed=embedder(MODEL), names=(UNITS,), write=True)
    before = sidecar_path(live).read_bytes()

    def failing(text: str) -> list[float]:
        if text.endswith("number 7"):
            raise ConnectionError("provider went away")
        return fake_embed(MODEL, text)

    with mock.patch.object(attestation_mod.time, "sleep"):
        with pytest.raises(
            AttestationError, match=r"conversation_summaries.*conversation_summaries-7.*ConnectionError"
        ):
            attest_collections(live, copy, model=MODEL, embed=failing, names=(SUMMARIES,), write=True)

    assert sidecar_path(live).read_bytes() == before


def test_a_transient_provider_error_is_retried_a_permanent_one_gives_up(stores: tuple[Path, Path]) -> None:
    live, copy = stores
    flaky_calls: list[str] = []

    def flaky(text: str) -> list[float]:
        flaky_calls.append(text)
        if len(flaky_calls) == 3:
            raise TimeoutError("one slow call")
        return fake_embed(MODEL, text)

    with mock.patch.object(attestation_mod.time, "sleep") as slept:
        report = attest_collections(live, copy, model=MODEL, embed=flaky, names=(UNITS,))
    assert report.attested[UNITS].population == POPULATION and slept.call_count == 1

    always: list[str] = []

    def never(text: str) -> list[float]:
        always.append(text)
        raise OSError("down")

    with mock.patch.object(attestation_mod.time, "sleep"):
        with pytest.raises(AttestationError, match="failed after 3 attempts"):
            attest_collections(live, copy, model=MODEL, embed=never, names=(UNITS,))
    assert len(always) == attestation_mod.EMBED_RETRIES + 1


def test_a_census_reads_embeds_and_scores_one_batch_before_reading_the_next(tmp_path: Path) -> None:
    copy = tmp_path / "chroma"
    build(copy, UNITS, n=20)
    events: list[str] = []
    original = attestation_mod.open_chroma_for_verify

    def tracing_open(path):
        store = original(path)
        collection = store._collection(UNITS)
        real_get = collection.get

        def get(ids, include):
            events.append("get")
            return real_get(ids=ids, include=include)

        collection.get = get  # type: ignore[method-assign]
        store._collection = lambda _name: collection  # type: ignore[method-assign]
        return store

    def tracing_embed(text: str) -> list[float]:
        events.append("embed")
        return fake_embed(MODEL, text)

    seen: list[tuple[str, int, int]] = []
    with mock.patch.object(attestation_mod, "READ_BATCH", 8), mock.patch.object(
        attestation_mod, "open_chroma_for_verify", tracing_open
    ):
        spot_check(copy, UNITS, tracing_embed, sample_size=None, progress=lambda *a: seen.append(a))

    # three batches (8, 8, 4): each batch's rows are embedded before the next get
    assert events == ["get"] + ["embed"] * 8 + ["get"] + ["embed"] * 8 + ["get"] + ["embed"] * 4
    assert seen == [(UNITS, 8, 20), (UNITS, 16, 20), (UNITS, 20, 20)]


def test_the_command_reports_progress_on_stderr(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    live = tmp_path / "live" / "chroma"
    build(live, UNITS, n=30)
    copy = tmp_path / "restored" / "chroma"
    shutil.copytree(live, copy)
    cfg = _config(tmp_path / "config.toml", live)

    with mock.patch.object(attestation_mod, "_ollama_embedder", return_value=embedder(MODEL)):
        assert main(["--config", str(cfg), "--restore-copy", str(copy), "--sample-size", "all"]) == 0

    assert "knowledge_units: 30/30 rows checked" in capsys.readouterr().err


def test_an_existing_lock_file_is_narrowed_to_owner_only(stores: tuple[Path, Path]) -> None:
    live, copy = stores
    lock = sidecar_path(live).with_name(sidecar_path(live).name + ".lock")
    lock.write_text("")
    lock.chmod(0o644)

    attest_collections(live, copy, model=MODEL, embed=embedder(MODEL), write=True)

    assert (lock.stat().st_mode & 0o777) == 0o600
    assert (sidecar_path(live).stat().st_mode & 0o777) == 0o600


def test_directories_count_as_shared_storage_not_only_files(tmp_path: Path) -> None:
    root = tmp_path / "tree"
    (root / "empty-segment").mkdir(parents=True)

    identities = attestation_mod._file_identities(root, forbid_symlinks=True)

    for directory in (root, root / "empty-segment"):
        info = directory.stat()
        assert (info.st_dev, info.st_ino) in identities


def test_a_live_database_in_wal_mode_is_not_read_so_nothing_is_created_beside_it(
    stores: tuple[Path, Path],
) -> None:
    live, copy = stores
    with sqlite3.connect(live / "chroma.sqlite3") as con:  # a scratch store switched to WAL
        con.execute("PRAGMA journal_mode=WAL")
    before = sorted(p.name for p in live.iterdir())

    with pytest.raises(AttestationError, match="WAL mode"):
        attest_collections(live, copy, model=MODEL, embed=embedder(MODEL), write=True)

    assert sorted(p.name for p in live.iterdir()) == before  # no -wal/-shm created by the refusal

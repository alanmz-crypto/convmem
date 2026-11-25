"""Attesting at scale: row-level failures, retries, progress, subnormal arithmetic, WAL, locks.

Split out of ``test_chroma_embed_attestation`` (which is at the module-size limit). Hermetic in
the same way: a "live" store and its "restore copy" live in ``tmp_path``, vectors come from a
deterministic fake embedder, and the live store is only ever read through SQLite ``mode=ro``.
"""

# pylint: disable=protected-access,too-many-arguments

from __future__ import annotations

import math
import os
import shutil
import sqlite3
import struct
from pathlib import Path
from unittest import mock

import pytest

import chroma_embed_attestation as attestation_mod
from chroma_embed_attestation import AttestationError, attest_collections, cosine, main, spot_check
from chroma_embed_identity import sidecar_path
from chroma_store import SUMMARIES, UNITS, ChromaStore
# Helpers and the ``stores`` fixture only (importing the fixture registers it); no test_* names.
from tests.test_chroma_embed_attestation import (  # pylint: disable=unused-import
    DIM,
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

        def get(ids=None, include=None):
            if ids is not None:  # reading a batch; the one-off listing of every id is not a batch
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


# --------------------------------------------------------------------------------------
# Round 4: pending log records, scoring failures, error boundary, descriptor, header bytes
# --------------------------------------------------------------------------------------


def _append_pending_row(chroma: Path, name: str, doc_id: str, document: str, vector: list[float]) -> None:
    """A genuine Chroma upsert log record that the client only replays when it opens the collection."""
    from chroma_readonly import collection_uuid

    uuid = collection_uuid(chroma, name)
    with sqlite3.connect(chroma / "chroma.sqlite3") as con:
        newest = con.execute("SELECT COALESCE(MAX(seq_id), 0) FROM embeddings_queue").fetchone()[0]
        con.execute(
            "INSERT INTO embeddings_queue (seq_id, operation, topic, id, vector, encoding, metadata) "
            "VALUES (?, 2, ?, ?, ?, 'FLOAT32', ?)",
            (
                newest + 1,
                f"persistent://default/default/{uuid}",
                doc_id,
                struct.pack(f"<{len(vector)}f", *vector),
                '{"chroma:document":"%s"}' % document,
            ),
        )


def test_a_row_pending_in_the_log_is_part_of_the_census_and_a_foreign_one_is_refused(
    stores: tuple[Path, Path],
) -> None:
    """Reviewed: the ids were read from SQLite before the client replayed the log, so a thirteenth,
    nonmatching row was never scored and a 12/12 census was published."""
    live, copy = stores
    foreign = [-x for x in fake_embed(MODEL, "pending document")]
    _append_pending_row(copy, UNITS, "pending-row", "pending document", foreign)

    with pytest.raises(AttestationError, match=r"does not reproduce the stored vector of row 'pending-row'"):
        attest_collections(live, copy, model=MODEL, embed=embedder(MODEL), names=(UNITS,), write=True)

    assert not sidecar_path(live).exists()


def test_a_matching_pending_row_is_counted_in_the_population(stores: tuple[Path, Path]) -> None:
    live, copy = stores
    _append_pending_row(copy, UNITS, "pending-row", "pending document", fake_embed(MODEL, "pending document"))

    report = attest_collections(
        live, copy, model=MODEL, embed=embedder(MODEL), names=(UNITS,), sample_size=None
    )

    assert report.evidence[UNITS]["population"] == POPULATION + 1
    assert report.evidence[UNITS]["sample_size"] == POPULATION + 1


def test_a_census_stops_at_the_first_failing_row_and_names_it(stores: tuple[Path, Path]) -> None:
    live, copy = stores
    calls: list[str] = []

    def orthogonal_on_the_third(text: str) -> list[float]:
        calls.append(text)
        vector = fake_embed(MODEL, text)
        return [-x for x in vector] if len(calls) == 3 else vector

    with pytest.raises(AttestationError, match=r"knowledge_units.*row 'knowledge_units-\d+'.*cosine"):
        attest_collections(
            live, copy, model=MODEL, embed=orthogonal_on_the_third, names=(UNITS,), sample_size=None
        )

    assert len(calls) == 3  # it did not score the rest and report only a minimum


def test_a_wrong_sized_vector_names_the_row(stores: tuple[Path, Path]) -> None:
    live, copy = stores

    with pytest.raises(AttestationError, match=r"knowledge_units: row 'knowledge_units-\d+'.*dimensions"):
        attest_collections(
            live, copy, model=MODEL, embed=embedder(MODEL, dim=DIM + 1), names=(UNITS,)
        )


def test_the_command_turns_a_damaged_store_into_a_refusal_not_a_traceback(
    tmp_path: Path, stores: tuple[Path, Path], capsys: pytest.CaptureFixture[str]
) -> None:
    live, copy = stores
    (copy / "chroma.sqlite3").write_bytes(b"this is not a database" * 100)
    cfg = _config(tmp_path / "config.toml", live)

    with mock.patch.object(attestation_mod, "_ollama_embedder", return_value=embedder(MODEL)):
        code = main(["--config", str(cfg), "--restore-copy", str(copy)])

    assert code == 2
    assert "attestation refused" in capsys.readouterr().err


def _open_descriptors_for(name_suffix: str) -> list[str]:
    """Descriptors of this process that point at a file whose name ends with ``name_suffix``."""
    found = []
    for entry in os.listdir("/proc/self/fd"):
        try:
            target = os.readlink(f"/proc/self/fd/{entry}")
        except OSError:
            continue  # closed between listing and reading
        if target.endswith(name_suffix):
            found.append(target)
    return found


def test_a_lock_that_cannot_be_narrowed_leaks_no_descriptor(stores: tuple[Path, Path]) -> None:
    live, copy = stores

    with mock.patch.object(attestation_mod.os, "fchmod", side_effect=PermissionError("no")):
        for _ in range(3):
            with pytest.raises(AttestationError, match="lock"):
                attest_collections(live, copy, model=MODEL, embed=embedder(MODEL), write=True)

    # Counting every descriptor is flaky (Chroma keeps threads that open and close files);
    # what must not survive is a descriptor on the lock file itself.
    assert not _open_descriptors_for(".embed-attestation.json.lock")


def test_any_exception_from_the_provider_is_retried_and_the_delay_doubles(
    stores: tuple[Path, Path],
) -> None:
    live, copy = stores
    attempts: list[int] = []

    def flaky(text: str) -> list[float]:
        attempts.append(1)
        if len(attempts) == 1:
            raise RuntimeError("not an OSError")  # retried like any other failure
        return fake_embed(MODEL, text)

    with mock.patch.object(attestation_mod.time, "sleep") as slept:
        attest_collections(live, copy, model=MODEL, embed=flaky, names=(UNITS,))
    assert slept.call_args_list == [mock.call(attestation_mod.EMBED_BACKOFF)]

    def never(_text: str) -> list[float]:
        raise ValueError("down")

    with mock.patch.object(attestation_mod.time, "sleep") as slept:
        with pytest.raises(AttestationError):
            attest_collections(live, copy, model=MODEL, embed=never, names=(UNITS,))
    assert [c.args[0] for c in slept.call_args_list] == [0.5, 1.0]


@pytest.mark.parametrize(
    "header,safe",
    [(b"\x01\x01", True), (b"\x02\x02", False), (b"\x01\x02", False), (b"\x02\x01", False), (b"\x00\x00", False)],
)
def test_only_a_plain_rollback_journal_header_is_read(
    stores: tuple[Path, Path], header: bytes, safe: bool
) -> None:
    from chroma_readonly import may_create_wal_files

    live, _ = stores
    data = bytearray((live / "chroma.sqlite3").read_bytes()[:100])
    data[18:20] = header
    with open(live / "chroma.sqlite3", "r+b") as handle:  # a scratch store: set the format bytes
        handle.write(bytes(data))

    assert may_create_wal_files(live) is (not safe)


def test_a_header_that_is_not_sqlite_is_not_read(stores: tuple[Path, Path]) -> None:
    from chroma_readonly import may_create_wal_files

    live, _ = stores
    (live / "chroma.sqlite3").write_bytes(b"not sqlite at all")
    assert may_create_wal_files(live) is True
    # long enough, with plausible version bytes, but not an SQLite header at all
    (live / "chroma.sqlite3").write_bytes(b"X" * 18 + b"\x01\x01" + b"\x00" * 80)
    assert may_create_wal_files(live) is True
    assert may_create_wal_files(live.parent / "nowhere") is False  # nothing to open, nothing to create


def test_a_copy_whose_listing_and_count_disagree_is_refused(tmp_path: Path) -> None:
    class _Inconsistent:
        def count(self) -> int:
            return 13

        def get(self, ids=None, include=None):  # pylint: disable=unused-argument
            return {"ids": [f"row-{i:02d}" for i in range(12)]}

    class _Store:
        def _collection(self, _name):
            return _Inconsistent()

        def close(self) -> None:
            pass

    with mock.patch.object(attestation_mod, "open_chroma_for_verify", return_value=_Store()):
        with pytest.raises(AttestationError, match="lists 12 rows but counts 13"):
            spot_check(tmp_path, UNITS, embedder(MODEL), sample_size=None)


def test_a_restore_that_changes_after_its_uuid_was_checked_is_not_scored_under_the_old_uuid(
    tmp_path: Path,
) -> None:
    """Reviewed: restore A (nonmatching rows) was checked by UUID, the path was rotated to restore
    B (a different collection, ten matching rows), B was scored, and A's UUID was published."""
    live = tmp_path / "live" / "chroma"
    build(live, UNITS, vectors_from="some-other-model", n=12)  # these rows do NOT match MODEL
    copy = tmp_path / "restored" / "chroma"
    shutil.copytree(live, copy)
    other = tmp_path / "other" / "chroma"
    build(other, UNITS, vectors_from=MODEL, n=10)  # a different collection whose rows DO match
    calls: list[int] = []
    real_check = attestation_mod._require_separate_copy

    def rotate_on_the_second_call(live_dir: Path, copy_dir: Path) -> None:
        real_check(live_dir, copy_dir)
        calls.append(1)
        if len(calls) == 2:  # the guard that runs just before the client opens the copy
            shutil.rmtree(copy_dir)
            shutil.copytree(other, copy_dir)

    with mock.patch.object(attestation_mod, "_require_separate_copy", rotate_on_the_second_call):
        with pytest.raises(AttestationError, match="changed after it was checked"):
            attest_collections(
                live, copy, model=MODEL, embed=embedder(MODEL), names=(UNITS,),
                sample_size=None, write=True,
            )

    assert not sidecar_path(live).exists()


def test_the_command_refuses_a_missing_or_malformed_configuration(
    tmp_path: Path, stores: tuple[Path, Path], capsys: pytest.CaptureFixture[str]
) -> None:
    _, copy = stores

    assert main(["--config", str(tmp_path / "absent.toml"), "--restore-copy", str(copy)]) == 2
    broken = tmp_path / "broken.toml"
    broken.write_text("[index\nchroma_dir = ", encoding="utf-8")
    assert main(["--config", str(broken), "--restore-copy", str(copy)]) == 2
    err = capsys.readouterr().err
    assert err.count("attestation refused: cannot use the configuration") == 2


def test_a_restore_whose_collection_configuration_chroma_cannot_read_is_a_refusal(
    tmp_path: Path, stores: tuple[Path, Path], capsys: pytest.CaptureFixture[str]
) -> None:
    live, copy = stores
    with sqlite3.connect(copy / "chroma.sqlite3") as con:  # SQLite stays readable; Chroma's config is not
        con.execute("UPDATE collections SET config_json_str = '{not json'")
    cfg = _config(tmp_path / "config.toml", live)

    with mock.patch.object(attestation_mod, "_ollama_embedder", return_value=embedder(MODEL)):
        code = main(["--config", str(cfg), "--restore-copy", str(copy)])

    assert code == 2
    assert "attestation refused" in capsys.readouterr().err


def test_a_copy_chroma_cannot_read_is_an_attestation_error_at_the_library_level(
    stores: tuple[Path, Path],
) -> None:
    """The inner layer: spot_check translates Chroma's own errors, so library callers get one type."""
    live, copy = stores
    with sqlite3.connect(copy / "chroma.sqlite3") as con:
        con.execute("UPDATE collections SET config_json_str = '{not json'")

    with pytest.raises(AttestationError, match="cannot be read by Chroma"):
        attest_collections(live, copy, model=MODEL, embed=embedder(MODEL), names=(UNITS,))


def test_the_command_refuses_a_chroma_error_raised_outside_the_census(
    tmp_path: Path, stores: tuple[Path, Path], capsys: pytest.CaptureFixture[str]
) -> None:
    """The outer layer: any Chroma error that reaches main() is a refusal, not a traceback."""
    from chromadb.errors import InternalError

    live, copy = stores
    cfg = _config(tmp_path / "config.toml", live)

    with mock.patch.object(attestation_mod, "attest_collections", side_effect=InternalError("boom")):
        code = main(["--config", str(cfg), "--restore-copy", str(copy)])

    assert code == 2 and "attestation refused: cannot read a store: InternalError" in capsys.readouterr().err


def _ids_and_documents(n: int) -> tuple[list[str], dict[str, str]]:
    ids = sorted(f"{UNITS}-{i}" for i in range(n))
    return ids, {doc_id: f"{UNITS} document number {doc_id.rsplit('-', 1)[1]}" for doc_id in ids}


def test_a_second_writer_changing_the_restore_during_the_census_is_refused(tmp_path: Path) -> None:
    """Reviewed: the UUID, count and id set stayed the same while one writer repaired a row not yet
    read and broke one already scored, and a 501/501 census with minimum 1.0 was published."""
    live = tmp_path / "live" / "chroma"
    build(live, UNITS, n=501)
    copy = tmp_path / "restored" / "chroma"
    shutil.copytree(live, copy)
    ids, docs = _ids_and_documents(501)
    first, last = ids[0], ids[-1]
    writer = ChromaStore(str(copy))  # another process in real life; here a second client on the copy

    def vector(doc_id: str, *, broken: bool) -> list[float]:
        good = fake_embed(MODEL, docs[doc_id])
        return [-x for x in good] if broken else good

    def put(doc_id: str, *, broken: bool) -> None:
        writer._collection(UNITS).upsert(
            ids=[doc_id], documents=[docs[doc_id]], embeddings=[vector(doc_id, broken=broken)]
        )

    put(last, broken=True)  # the last row starts out wrong, so an honest census would refuse it
    calls: list[int] = []

    def embed_and_interfere(text: str) -> list[float]:
        calls.append(1)
        if len(calls) == attestation_mod.READ_BATCH:  # the first batch is scored; the second not yet read
            put(last, broken=False)  # repair the row that would have failed...
            put(first, broken=True)  # ...and break one that was already scored
        return fake_embed(MODEL, text)

    try:
        with pytest.raises(AttestationError, match="changed while it was being checked"):
            attest_collections(
                live, copy, model=MODEL, embed=embed_and_interfere, names=(UNITS,),
                sample_size=None, write=True,
            )
    finally:
        writer.close()

    assert not sidecar_path(live).exists()


def test_a_census_of_a_copy_nobody_else_writes_is_accepted(tmp_path: Path) -> None:
    live = tmp_path / "live" / "chroma"
    build(live, UNITS, n=501)
    copy = tmp_path / "restored" / "chroma"
    shutil.copytree(live, copy)

    report = attest_collections(live, copy, model=MODEL, embed=embedder(MODEL), names=(UNITS,), sample_size=None)

    assert report.evidence[UNITS]["sample_size"] == report.evidence[UNITS]["population"] == 501


def test_the_default_batch_works_on_a_34000_row_collection(tmp_path: Path) -> None:
    """SQLite caps the variables of one query; a batch that grows with the collection fails here."""
    live = tmp_path / "live" / "chroma"

    def vec(i: int) -> list[float]:
        return [1.0, (i % 97 + 1) / 100.0]

    with ChromaStore(str(live)) as store:
        collection = store._collection(UNITS)
        for start in range(0, 34_000, 2_000):  # 17 batches of 2,000: exactly 34,000 rows
            span = range(start, start + 2_000)
            collection.upsert(
                ids=[f"u{i:06d}" for i in span], documents=[f"doc {i}" for i in span],
                embeddings=[vec(i) for i in span],
            )
    copy = tmp_path / "restored" / "chroma"
    shutil.copytree(live, copy)

    check = spot_check(copy, UNITS, lambda text: vec(int(text.split()[1])), sample_size=None)

    assert check.sample_size == check.population == 34_000
    assert attestation_mod.READ_BATCH <= 1_000


def test_a_census_that_scored_fewer_rows_than_the_copy_holds_is_refused(stores: tuple[Path, Path]) -> None:
    live, copy = stores

    with mock.patch.object(attestation_mod, "_sample_ids", lambda ids, size, seed: sorted(ids)[:-1]):
        with pytest.raises(AttestationError, match="did not cover every row"):
            attest_collections(live, copy, model=MODEL, embed=embedder(MODEL), names=(UNITS,), sample_size=None)


def test_a_provider_that_exits_is_a_failed_row_not_a_successful_run(stores: tuple[Path, Path]) -> None:
    live, copy = stores

    def exits(_text: str) -> list[float]:
        raise SystemExit(0)

    with mock.patch.object(attestation_mod.time, "sleep"):
        with pytest.raises(AttestationError, match="embedding row"):
            attest_collections(live, copy, model=MODEL, embed=exits, names=(UNITS,))


def test_a_native_panic_from_chroma_is_a_refusal(tmp_path: Path) -> None:
    panic = type("PanicException", (BaseException,), {})

    class _Collection:
        id = "whatever"

        def count(self) -> int:
            raise panic("a Rust panic")

        def get(self, ids=None, include=None):  # pylint: disable=unused-argument
            raise panic("a Rust panic")

    class _Store:
        def _collection(self, _name):
            return _Collection()

        def close(self) -> None:
            pass

    with mock.patch.object(attestation_mod, "open_chroma_for_verify", return_value=_Store()):
        with pytest.raises(AttestationError, match="native layer"):
            spot_check(tmp_path, UNITS, embedder(MODEL), sample_size=None)


def test_a_lock_that_cannot_be_taken_leaks_no_descriptor(stores: tuple[Path, Path]) -> None:
    live, copy = stores

    with mock.patch.object(attestation_mod.fcntl, "flock", side_effect=OSError("no lock")):
        with pytest.raises(OSError):
            attest_collections(live, copy, model=MODEL, embed=embedder(MODEL), write=True)

    assert not _open_descriptors_for(".embed-attestation.json.lock")


def test_the_command_refuses_a_configuration_whose_models_is_not_a_table(
    tmp_path: Path, stores: tuple[Path, Path], capsys: pytest.CaptureFixture[str]
) -> None:
    live, copy = stores
    cfg = tmp_path / "config.toml"
    cfg.write_text(f'models = ["k"]\n[index]\nchroma_dir = "{live}"\n', encoding="utf-8")

    assert main(["--config", str(cfg), "--restore-copy", str(copy)]) == 2
    assert "[models] must be a table" in capsys.readouterr().err  # said by the check, not by a crash


def test_the_command_refuses_a_restore_whose_catalog_has_a_malformed_dimension(
    tmp_path: Path, stores: tuple[Path, Path], capsys: pytest.CaptureFixture[str]
) -> None:
    live, copy = stores
    with sqlite3.connect(copy / "chroma.sqlite3") as con:
        con.execute("UPDATE collections SET dimension = 'unknown'")
    cfg = _config(tmp_path / "config.toml", live)

    with mock.patch.object(attestation_mod, "_ollama_embedder", return_value=embedder(MODEL)):
        code = main(["--config", str(cfg), "--restore-copy", str(copy)])

    assert code == 2
    assert "attestation refused" in capsys.readouterr().err


def test_a_changed_id_listing_is_refused_even_if_the_fingerprint_did_not_move(
    stores: tuple[Path, Path],
) -> None:
    """The listing and the fingerprint are separate evidence; each must be able to refuse alone."""
    live, copy = stores
    original = attestation_mod.open_chroma_for_verify

    def listing_changes(path):
        store = original(path)
        collection = store._collection(UNITS)
        real_get = collection.get
        listings: list[int] = []

        def get(ids=None, include=None):
            result = real_get(ids=ids, include=include)
            if ids is None:
                listings.append(1)
                if len(listings) == 2:  # the re-listing after the census
                    return {"ids": [*result["ids"], "appeared-meanwhile"]}
            return result

        collection.get = get  # type: ignore[method-assign]
        store._collection = lambda _name: collection  # type: ignore[method-assign]
        return store

    with mock.patch.object(attestation_mod, "open_chroma_for_verify", listing_changes), mock.patch.object(
        attestation_mod, "collection_change_fingerprint", return_value=(1, 1, 1, 1)
    ):
        with pytest.raises(AttestationError, match="changed while it was being checked"):
            attest_collections(live, copy, model=MODEL, embed=embedder(MODEL), names=(UNITS,), sample_size=None)

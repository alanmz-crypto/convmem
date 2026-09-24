# pylint: disable=protected-access,redefined-outer-name
"""Crash containment for native Chroma writes (chroma_write_guard, Arc Poison Pill Part B).

Every test builds its own scratch store with a small HNSW sync threshold so real
Chroma saves happen within a few hundred records. Writers that must be killed or
must hold a stale in-memory index run as subprocesses (tests/_chroma_write_guard_worker.py).
Kills use SIGKILL: on disk it is indistinguishable from a native segfault, and it
leaves no core dump behind.
"""

from __future__ import annotations

import json
import pickle
import struct
import subprocess
import sys
import time
from pathlib import Path

import chromadb
import pytest

from chroma_store import SUMMARIES, UNITS, ChromaStore
from chroma_write_guard import (
    ChromaStaleSystemError,
    ChromaWriteGuard,
    ChromaWriteQuarantinedError,
    load_segment_id_map,
    recover,
    segment_dirs,
    segment_signature,
    validate_segment,
    vector_census,
    write_guard_enabled,
)
from tests._chroma_write_guard_worker import embedding

ROOT = Path(__file__).resolve().parents[1]
WORKER = ROOT / "tests" / "_chroma_write_guard_worker.py"


def _make_store(tmp_path: Path, *, sync_threshold: int = 100) -> Path:
    chroma = tmp_path / "chroma"
    client = chromadb.PersistentClient(path=str(chroma))
    for name in (SUMMARIES, UNITS):
        client.get_or_create_collection(
            name,
            configuration={"hnsw": {"space": "cosine", "sync_threshold": sync_threshold, "batch_size": 10}},
        )
    client.close()
    return chroma


def _worker(*args: object, timeout: float = 180) -> str:
    done = subprocess.run(
        [sys.executable, str(WORKER), *map(str, args)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )
    assert done.returncode == 0, done.stderr[-2000:]
    return done.stdout


def _segment(chroma: Path) -> tuple[str, Path]:
    (item,) = segment_dirs(chroma).items()  # only the summaries collection is written
    return item


def _events(chroma: Path) -> list[dict]:
    path = ChromaWriteGuard(chroma).events_path
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def _assert_every_record_has_its_vector(chroma: Path) -> int:
    census = vector_census(chroma)["conversation_summaries"]
    assert census["lost"] == 0, census
    store = ChromaStore(str(chroma))
    try:
        col = store._collection(SUMMARIES)
        ids = col.get(include=[])["ids"]
        # Chroma raises "Error finding id" for a listed record whose vector is gone.
        got = col.get(ids=ids, include=["embeddings"])
        assert len(got["embeddings"]) == len(ids)
        return len(ids)
    finally:
        store.close()


def _set_header_count(header: Path, delta: int) -> None:
    raw = bytearray(header.read_bytes())
    count = struct.unpack_from("<Q", raw, 20)[0]
    struct.pack_into("<Q", raw, 20, count + delta)
    header.write_bytes(bytes(raw))


# --------------------------------------------------------------------------------------
# Validator
# --------------------------------------------------------------------------------------


def test_validator_accepts_a_saved_segment_and_rejects_torn_copies(tmp_path: Path) -> None:
    chroma = _make_store(tmp_path)
    _worker("write", chroma, 0, 250)
    _, seg = _segment(chroma)
    assert validate_segment(seg).ok, validate_segment(seg).failures

    def torn(name: str, damage) -> list[str]:
        copy = tmp_path / f"copy-{name}"
        copy.mkdir()
        for path in seg.iterdir():
            (copy / path.name).write_bytes(path.read_bytes())
        damage(copy)
        report = validate_segment(copy)
        assert not report.ok, name
        return list(report.failures)

    def truncate(path: Path, keep: int) -> None:
        path.write_bytes(path.read_bytes()[:keep])

    def bad_neighbour(copy: Path) -> None:
        raw = bytearray((copy / "data_level0.bin").read_bytes())
        struct.pack_into("<I", raw, 4, 0x00FFFFFF)  # element 0, first level-0 neighbour
        (copy / "data_level0.bin").write_bytes(bytes(raw))

    def drop_id(copy: Path) -> None:
        id_map = load_segment_id_map(copy)
        victim = next(iter(id_map["id_to_label"]))
        label = id_map["id_to_label"].pop(victim)
        id_map["label_to_id"].pop(label, None)
        (copy / "index_metadata.pickle").write_bytes(pickle.dumps(id_map))

    assert torn("header", lambda c: truncate(c / "header.bin", 60))
    assert torn("data", lambda c: truncate(c / "data_level0.bin", 1000))
    assert torn("count", lambda c: _set_header_count(c / "header.bin", 7))
    assert torn("neighbour", bad_neighbour)
    assert torn("id-map", drop_id)
    if (seg / "link_lists.bin").stat().st_size:
        assert torn("links", lambda c: truncate(c / "link_lists.bin", (c / "link_lists.bin").stat().st_size - 1))


def test_id_map_loader_refuses_pickled_globals(tmp_path: Path) -> None:
    seg = tmp_path / "seg"
    seg.mkdir()
    (seg / "index_metadata.pickle").write_bytes(pickle.dumps({"id_to_label": {"a": Path("x")}}))
    with pytest.raises(pickle.UnpicklingError):
        load_segment_id_map(seg)


# --------------------------------------------------------------------------------------
# Snapshots and crash recovery
# --------------------------------------------------------------------------------------


def test_guarded_saves_keep_a_validated_copy_of_the_last_save(tmp_path: Path) -> None:
    chroma = _make_store(tmp_path)
    _worker("write", chroma, 0, 250, "--guard")
    seg_id, seg = _segment(chroma)
    guard = ChromaWriteGuard(chroma)
    snap_dir, meta = guard.current_snapshot(seg_id)
    assert meta["live_signature"] == segment_signature(seg)
    assert validate_segment(snap_dir).ok
    assert guard.quarantine_state() is None
    assert [e["event"] for e in _events(chroma)] == ["snapshot_created"]


def test_torn_save_is_restored_before_the_next_write_without_losing_records(tmp_path: Path) -> None:
    chroma = _make_store(tmp_path)
    _worker("write", chroma, 0, 200, "--guard")  # saves at 100 and 200; copy of the 200 save
    _worker("write", chroma, 200, 50, "--guard")  # below the threshold: only Chroma's log has these
    _, seg = _segment(chroma)
    # What a crash mid-save leaves behind: the header already counts the next save's
    # elements while data_level0.bin still holds the previous one.
    _set_header_count(seg / "header.bin", 50)
    assert not validate_segment(seg).ok

    _worker("write", chroma, 250, 1, "--guard")  # reconciles before writing

    assert validate_segment(seg).ok
    restored = [e for e in _events(chroma) if e["event"] == "segment_restored"]
    assert len(restored) == 1 and restored[0]["census"]["lost"] == 0
    assert _assert_every_record_has_its_vector(chroma) == 251


def test_native_crash_mid_write_leaves_the_shared_index_clean(tmp_path: Path) -> None:
    """Kill a guarded writer the moment a save touches the segment, three times over."""
    chroma = _make_store(tmp_path)
    _worker("write", chroma, 0, 100, "--guard")
    _, seg = _segment(chroma)
    start = 100
    for _ in range(3):
        before = segment_signature(seg)
        proc = subprocess.Popen(  # pylint: disable=consider-using-with
            [sys.executable, str(WORKER), "loop", str(chroma), str(start), "0", "--guard"],
            cwd=ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
        )
        deadline = time.monotonic() + 60
        while proc.poll() is None and time.monotonic() < deadline:
            if segment_signature(seg) != before:
                break
            time.sleep(0.0005)
        proc.kill()
        out, _ = proc.communicate()
        written = [int(tok) for tok in out.split() if tok.isdigit()]
        # After a restore, the first write replays Chroma's log and can save before any
        # record of this run is acknowledged, so an empty ``written`` is legitimate.
        start = max(written) + 2 if written else start + 1

        recover(chroma)

        assert validate_segment(seg).ok
        assert ChromaWriteGuard(chroma).quarantine_state() is None
        assert vector_census(chroma)["conversation_summaries"]["lost"] == 0

    _worker("write", chroma, start, 5, "--guard")
    _assert_every_record_has_its_vector(chroma)


def test_torn_segment_with_no_validated_save_quarantines(tmp_path: Path) -> None:
    chroma = _make_store(tmp_path)
    _worker("write", chroma, 0, 150)  # unguarded: no copy exists
    _, seg = _segment(chroma)
    _set_header_count(seg / "header.bin", 3)
    with pytest.raises(ChromaWriteQuarantinedError):
        recover(chroma)
    state = ChromaWriteGuard(chroma).quarantine_state()
    assert state["reason"].startswith("live segment failed validation")


def test_quarantine_stops_guarded_writes_but_not_reads(tmp_path: Path) -> None:
    chroma = _make_store(tmp_path)
    _worker("write", chroma, 0, 120, "--guard")
    guard = ChromaWriteGuard(chroma)
    guard.quarantine_path.write_text(json.dumps({"reason": "test", "segment": "x"}), encoding="utf-8")
    store = ChromaStore(str(chroma), write_guard=guard)
    try:
        with pytest.raises(ChromaWriteQuarantinedError):
            store.add_summary("s-new", "doc", embedding("s-new"), {"source_path": "/fixture"})
        assert store.count_summaries() == 120
    finally:
        store.close()


def test_invalid_own_save_quarantines_instead_of_restoring(tmp_path: Path, monkeypatch) -> None:
    import chroma_write_guard

    chroma = _make_store(tmp_path)
    _worker("write", chroma, 0, 199, "--guard")  # copy of the 100 save; 99 more in the log
    _, seg = _segment(chroma)
    real = chroma_write_guard.validate_segment
    monkeypatch.setattr(
        chroma_write_guard,
        "validate_segment",
        lambda path: real(path) if Path(path) != seg else chroma_write_guard.SegmentReport("x", False, ("forced",), ()),
    )
    inode = (seg / "data_level0.bin").stat().st_ino  # Chroma saves in place; a restore replaces it
    snapshot_sig = ChromaWriteGuard(chroma).current_snapshot(_segment(chroma)[0])[1]["live_signature"]
    store = ChromaStore(str(chroma), write_guard=ChromaWriteGuard(chroma))
    try:
        with pytest.raises(ChromaWriteQuarantinedError):
            store.add_summary("s199", "doc", embedding("s199"), {"source_path": "/fixture"})  # 200th: saves
    finally:
        store.close()
    assert ChromaWriteGuard(chroma).quarantine_state()["reason"].startswith("this process's own save")
    # Restoring the older copy here would silently drop records 100..199: it must not happen.
    assert (seg / "data_level0.bin").stat().st_ino == inode
    assert segment_signature(seg) != snapshot_sig
    monkeypatch.undo()
    assert validate_segment(seg).ok


def test_first_load_rewrite_of_an_unsynced_segment_is_not_a_save(tmp_path: Path) -> None:
    """Chroma rewrites a never-synced segment's files, unchanged, whenever a new client
    loads it. That must not read as another process's save (no adoption, no reload)."""
    chroma = _make_store(tmp_path)
    _worker("write", chroma, 0, 5, "--guard")  # created, not yet synced (threshold 100)
    _, seg = _segment(chroma)
    before = segment_signature(seg)
    reader = ChromaStore(str(chroma))
    try:
        assert reader.count_summaries() == 5  # the first load rewrites the files
    finally:
        reader.close()
    assert segment_signature(seg) == before
    _worker("write", chroma, 5, 1, "--guard")
    assert [e["event"] for e in _events(chroma)] == ["snapshot_created"]


# --------------------------------------------------------------------------------------
# Stale in-process systems (a second writer overwriting a newer save)
# --------------------------------------------------------------------------------------


@pytest.mark.parametrize("guarded", [True, False], ids=["guarded", "unguarded-control"])
def test_stale_writer_and_a_newer_save_from_another_process(tmp_path: Path, guarded: bool) -> None:
    chroma = _make_store(tmp_path)
    flag = ["--guard"] if guarded else []
    _worker("write", chroma, 0, 300, *flag)
    gate = tmp_path / "gate"
    holder = subprocess.Popen(  # pylint: disable=consider-using-with
        [sys.executable, str(WORKER), "hold", str(chroma), "450", "150", str(gate), *flag],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        assert holder.stdout.readline().strip() == "holding"
        _worker("write", chroma, 300, 150, *flag)  # another process saves at 400
        gate.touch()
        _, err = holder.communicate(timeout=180)
        assert holder.returncode == 0, err[-2000:]
    finally:
        if holder.poll() is None:
            holder.kill()
    lost = vector_census(chroma)["conversation_summaries"]["lost"]
    if guarded:
        assert lost == 0
        _assert_every_record_has_its_vector(chroma)
    else:
        # chromadb 1.5.9 without the guard: the stale writer's save drops the other
        # process's saved records. If this starts passing, re-verify the guard's premise.
        assert lost > 0


def test_write_is_refused_when_another_client_pins_a_stale_system(tmp_path: Path) -> None:
    chroma = _make_store(tmp_path)
    _worker("write", chroma, 0, 150, "--guard")
    reader = ChromaStore(str(chroma))
    reader.query_summaries(embedding("s0"), 1)  # this process's system loads the 100 save
    writer = ChromaStore(str(chroma), write_guard=ChromaWriteGuard(chroma))  # shares that system
    try:
        _worker("write", chroma, 150, 100, "--guard")  # another process saves at 200
        with pytest.raises(ChromaStaleSystemError):
            writer.add_summary("s-late", "doc", embedding("s-late"), {"source_path": "/fixture"})
    finally:
        writer.close()
        reader.close()
    fresh = ChromaStore(str(chroma), write_guard=ChromaWriteGuard(chroma))
    try:
        fresh.add_summary("s-late", "doc", embedding("s-late"), {"source_path": "/fixture"})
    finally:
        fresh.close()
    assert _assert_every_record_has_its_vector(chroma) == 251


def test_own_unguarded_saves_do_not_make_this_process_look_stale(tmp_path: Path) -> None:
    """A plain store and a guarded store in one process share one Chroma system; saves
    made through the plain one are this system's own, not a stranger's."""
    chroma = _make_store(tmp_path)
    plain = ChromaStore(str(chroma))
    try:
        for i in range(150):  # creates the segment and syncs it at 100, all in this process
            plain.add_summary(f"s{i}", "doc", embedding(f"s{i}"), {"source_path": "/fixture"})
        guarded = ChromaStore(str(chroma), write_guard=ChromaWriteGuard(chroma))
        try:
            guarded.add_summary("s150", "doc", embedding("s150"), {"source_path": "/fixture"})
        finally:
            guarded.close()
    finally:
        plain.close()
    assert _assert_every_record_has_its_vector(chroma) == 151


def test_another_process_creating_an_unsynced_segment_is_not_staleness(tmp_path: Path) -> None:
    """Nothing is purged before a segment's first sync, so a system that loaded earlier
    replays those records; refusing the write here would be a false alarm."""
    chroma = _make_store(tmp_path)
    reader = ChromaStore(str(chroma))
    reader.count_summaries()  # this process's system exists before any segment files do
    writer = ChromaStore(str(chroma), write_guard=ChromaWriteGuard(chroma))  # shares it
    try:
        _worker("write", chroma, 0, 30, "--guard")  # another process creates it, unsynced
        writer.add_summary("s30", "doc", embedding("s30"), {"source_path": "/fixture"})
    finally:
        writer.close()
        reader.close()
    assert _assert_every_record_has_its_vector(chroma) == 31


# --------------------------------------------------------------------------------------
# Wiring
# --------------------------------------------------------------------------------------


def test_production_write_stores_carry_the_guard(tmp_path: Path) -> None:
    from chroma_write_store import open_chroma_for_write

    chroma = tmp_path / "chroma"
    cfg = {"index": {"chroma_dir": str(chroma)}, "shadow_ledger": {"enabled": False}}
    off = {**cfg, "index": {**cfg["index"], "chroma_write_guard": False}}
    for config, purpose, expected in ((cfg, "production", True), (off, "production", False), (cfg, "test", False)):
        store, _ = open_chroma_for_write(config, chroma, purpose=purpose)
        try:
            assert (store._write_guard is not None) is expected, (purpose, config["index"])
        finally:
            store.close()
    assert write_guard_enabled(None) and write_guard_enabled({"index": {}})


def test_abrupt_index_child_exits_trigger_guard_recovery(tmp_path: Path, monkeypatch) -> None:
    import watch

    calls: list[int] = []
    monkeypatch.setattr(watch, "recover_chroma_after_abrupt_exit", lambda cfg=None: calls.append(1) or [])
    monkeypatch.setattr(watch, "log_native_crash", lambda *args, **kwargs: None)
    breaker = watch.CircuitBreakerState(tmp_path / "breaker.json")
    for message, expected in (
        ("index subprocess exit -11", 1),
        ("index subprocess exit -9", 1),
        ("index subprocess timed out after 900 seconds", 1),
        ("index subprocess exit 1", 0),
        ("provider dropped the request", 0),
    ):
        calls.clear()
        watch._record_ready_path_failure("/x/a.jsonl", RuntimeError(message), breaker=breaker, verbose=False)
        assert len(calls) == expected, message


def test_watch_recovery_restores_and_never_raises(tmp_path: Path) -> None:
    import watch

    chroma = _make_store(tmp_path)
    _worker("write", chroma, 0, 150, "--guard")
    _, seg = _segment(chroma)
    _set_header_count(seg / "header.bin", 9)
    events = watch.recover_chroma_after_abrupt_exit({"index": {"chroma_dir": str(chroma)}})
    assert [e["event"] for e in events] == ["segment_restored"]
    assert validate_segment(seg).ok
    ChromaWriteGuard(chroma).quarantine_path.write_text("{}", encoding="utf-8")
    assert not watch.recover_chroma_after_abrupt_exit({"index": {"chroma_dir": str(chroma)}})


def test_chromadb_internals_the_guard_depends_on() -> None:
    """The guard encodes chromadb 1.5.9 behaviour; a bump must re-run this file first."""
    from chromadb.api.shared_system_client import SharedSystemClient

    assert isinstance(SharedSystemClient._identifier_to_system, dict)
    assert chromadb.__version__ == "1.5.9", "re-verify chroma_write_guard before changing chromadb"


def test_doctor_reports_quarantine_restores_and_off_switch(tmp_path: Path) -> None:
    from doctor import _check_chroma_write_guard

    chroma = tmp_path / "chroma"
    cfg = {"index": {"chroma_dir": str(chroma)}}
    guard = ChromaWriteGuard(chroma)
    assert _check_chroma_write_guard(cfg).effective_status() == "pass"
    guard._event("segment_restored", segment="seg")
    assert _check_chroma_write_guard(cfg).effective_status() == "warn"
    guard.quarantine_path.write_text(json.dumps({"reason": "test", "segment": "seg"}), encoding="utf-8")
    assert _check_chroma_write_guard(cfg).effective_status() == "fail"
    assert guard.clear_quarantine() and not guard.clear_quarantine()
    off = {"index": {"chroma_dir": str(chroma), "chroma_write_guard": False}}
    assert _check_chroma_write_guard(off).effective_status() == "warn"

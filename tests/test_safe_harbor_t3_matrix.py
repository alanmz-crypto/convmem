"""Runtime preservation/release fault matrix; synthetic data only."""
# pylint: disable=protected-access,redefined-outer-name,wrong-import-position,wrong-import-order,ungrouped-imports
from __future__ import annotations

import copy
import errno
import json
import shutil
import sqlite3

from tests._safe_harbor_bootstrap import require_t3_bootstrap
require_t3_bootstrap()
import chromadb
import pytest
import chroma_write_guard as cwg
from chroma_store import SUMMARIES, UNITS
from tests._safe_harbor_t3_backend_worker import (
    cosine_vectors_equal, embedding_from_seed, read_persisted_embedding_vector,
)
from tests.safe_harbor_t3_fixtures import (
    kill_worker_at_barrier, segment_file_bytes_snapshot, tear_and_trigger_restore,
)
from tests.test_chroma_write_guard import _make_store, _segment, _set_header_count, _worker

PRESERVE_PHASES = (
    "before_preservation_io", "after_first_copy", "after_manifest_before_bind",
    "after_preservation_bind", "after_first_replacement",
)
RELEASE_PHASES = ("after_disposition_before_marker_removal", "after_marker_removal")


def release(guard):
    view = guard.read_authority()
    assert view.document is not None
    return guard.release_quarantine(
        disposition_ref="fixture-owner", authority_digest=cwg.authority_submission_digest(view.document)
    )


def torn_store(tmp_path):
    chroma = _make_store(tmp_path)
    _worker("write", chroma, 0, 200, "--guard")
    _, seg = _segment(chroma)
    _set_header_count(seg / "header.bin", 50)
    return chroma, seg


def resume(guard):
    view = guard.read_authority()
    assert view.document is not None
    with pytest.raises(cwg.ChromaWriteQuarantinedError):
        guard.resume_bounded_restore(incident_id=view.document["incidents"][0]["id"],
                                     authority_digest=cwg.authority_submission_digest(view.document))


@pytest.mark.parametrize("phase", PRESERVE_PHASES)
def test_preservation_kill_and_resume_keeps_originals(tmp_path, phase):
    chroma, seg = torn_store(tmp_path)
    originals = segment_file_bytes_snapshot(seg)
    kill_worker_at_barrier(chroma, phase=phase, ready=tmp_path / "ready", release=tmp_path / "continue")
    guard = cwg.ChromaWriteGuard(chroma)
    incident = guard.quarantine_state()["incidents"][0]
    base = guard._preservation_dir(incident["id"], incident)
    manifest = base / "MANIFEST.json"
    completed = manifest.read_bytes() if manifest.exists() else None
    if phase != "after_first_replacement":
        assert segment_file_bytes_snapshot(seg) == originals
    resume(guard)
    if completed is not None:
        assert manifest.read_bytes() == completed
    assert segment_file_bytes_snapshot(base / "originals") == originals
    assert guard.quarantine_state()["incidents"][0]["repair"]["status"] == "complete"
    with pytest.raises(cwg.ChromaWriteQuarantinedError):
        guard.require_not_quarantined()
    release(guard)
    assert not guard.quarantine_path.exists()


@pytest.mark.parametrize("phase", RELEASE_PHASES)
def test_release_kill_has_unambiguous_observed_state(tmp_path, phase):
    chroma, guard = tear_and_trigger_restore(tmp_path)
    kill_worker_at_barrier(chroma, phase=phase, ready=tmp_path / "ready", release=tmp_path / "continue")
    fresh = cwg.ChromaWriteGuard(chroma)
    records = [json.loads(line) for line in guard.events_path.read_text().splitlines()]
    assert any(row["event"] == "release_disposition" for row in records)
    if phase == "after_disposition_before_marker_removal":
        assert fresh.read_authority().blocking
        release(fresh)  # prior event does not itself authorize removal
    else:
        assert fresh.read_authority().state == "absent"
    assert not fresh.quarantine_path.exists()


def test_partial_preservation_refuses_changed_originals(tmp_path):
    chroma, seg = torn_store(tmp_path)
    kill_worker_at_barrier(chroma, phase="after_first_copy", ready=tmp_path / "ready", release=tmp_path / "continue")
    guard = cwg.ChromaWriteGuard(chroma)
    before = guard.quarantine_path.read_bytes()
    path = seg / "length.bin"
    path.write_bytes(path.read_bytes() + b"changed")
    with pytest.raises(cwg.ChromaWriteGuardError, match="original|source|identity|facts"):
        resume(guard)
    assert guard.quarantine_path.read_bytes() == before


@pytest.mark.parametrize("fault", ["shortwrite", "filefsync", "dirfsync", "enospc"])
def test_preservation_io_failure_cannot_replace_live_originals(tmp_path, fault, monkeypatch):
    chroma, seg = torn_store(tmp_path)
    before = segment_file_bytes_snapshot(seg)
    real_copy, real_fsync = cwg._copy_durable, cwg._fsync
    hit = []

    def copy_file(src, dst):
        if dst.parent.name == "originals" and fault in {"shortwrite", "enospc"}:
            hit.append(fault)
            if fault == "enospc":
                raise OSError(errno.ENOSPC, "injected full preservation volume")
            dst.write_bytes(b"short")
            real_fsync(dst)
            return
        real_copy(src, dst)

    def sync(path, *, directory=False):
        file_fault = fault == "filefsync" and path.parent.name == "originals" and not directory
        dir_fault = fault == "dirfsync" and directory and "preservation" in path.parts
        if file_fault or dir_fault:
            hit.append(fault)
            raise OSError("injected preservation fsync failure")
        real_fsync(path, directory=directory)

    monkeypatch.setattr(cwg, "_copy_durable", copy_file)
    monkeypatch.setattr(cwg, "_fsync", sync)
    guard = cwg.ChromaWriteGuard(chroma)
    with pytest.raises((cwg.ChromaWriteGuardError, OSError)):
        cwg.recover(chroma)
    assert hit, "fault must reach the real preservation operation"
    assert segment_file_bytes_snapshot(seg) == before
    assert guard.read_authority().blocking


def test_copy_over_original_negative_control_detects_evidence_loss(tmp_path, monkeypatch):
    _, guard = tear_and_trigger_restore(tmp_path)
    incident = guard.quarantine_state()["incidents"][0]
    original_dir = guard._preservation_dir(incident["id"], incident) / "originals"
    original_bytes = segment_file_bytes_snapshot(original_dir)
    view = guard.read_authority()
    args = {"incident_id": incident["id"], "authority_digest": cwg.authority_submission_digest(view.document)}
    guard.resume_bounded_restore(**args)
    assert segment_file_bytes_snapshot(original_dir) == original_bytes
    real_ensure = guard._ensure_preservation_complete

    def faulty(document, incident_id, segment, seg_dir):
        for name in original_bytes:
            shutil.copyfile(seg_dir / name, original_dir / name)
        return real_ensure(document, incident_id, segment, seg_dir)

    monkeypatch.setattr(guard, "_ensure_preservation_complete", faulty)
    with pytest.raises(cwg.ChromaWriteGuardError):
        guard.resume_bounded_restore(**args)
    with pytest.raises(AssertionError, match="original evidence"):
        assert segment_file_bytes_snapshot(original_dir) == original_bytes, "original evidence was overwritten"
    assert guard.read_authority().blocking


def test_two_incidents_release_is_all_or_nothing(tmp_path):
    chroma = _make_store(tmp_path)
    _worker("write", chroma, 0, 200, "--guard")
    client = chromadb.PersistentClient(path=str(chroma))
    client.get_collection(UNITS).add(ids=[f"u{i}" for i in range(200)],
        embeddings=[embedding_from_seed(i) for i in range(200)])
    client.close()
    guard = cwg.ChromaWriteGuard(chroma)
    cwg.recover(chroma)
    for seg in cwg.segment_dirs(chroma).values():
        _set_header_count(seg / "header.bin", 50)
    with pytest.raises(cwg.ChromaWriteQuarantinedError):
        cwg.recover(chroma)
    incidents = guard.quarantine_state()["incidents"]
    assert len(incidents) == 2
    before = guard.quarantine_path.read_bytes()
    bad = guard._preservation_dir(incidents[1]["id"], incidents[1]) / "MANIFEST.json"
    raw = bad.read_bytes()
    bad.write_bytes(raw + b" ")
    with pytest.raises(cwg.ChromaWriteGuardError, match="preservation"):
        release(guard)
    assert guard.quarantine_path.read_bytes() == before
    bad.write_bytes(raw)
    release(guard)
    assert not guard.quarantine_path.exists()


@pytest.mark.parametrize("persistent", [False, True])
def test_actual_census_retry_preserves_containment(tmp_path, persistent, monkeypatch):
    chroma, _ = torn_store(tmp_path)
    real = cwg.vector_census
    calls = []

    def census(path):
        calls.append(1)
        if persistent or len(calls) == 1:
            raise sqlite3.OperationalError("injected census read failure")
        return real(path)

    monkeypatch.setattr(cwg, "vector_census", census)
    guard = cwg.ChromaWriteGuard(chroma)
    with pytest.raises(cwg.ChromaWriteQuarantinedError):
        cwg.recover(chroma)
    assert len(calls) == 2
    assert guard.read_authority().blocking
    if persistent:
        with pytest.raises(cwg.ChromaWriteGuardError, match="census"):
            release(guard)
    else:
        release(guard)


@pytest.mark.parametrize("invalid", ["traversal", "missing", "symlink", "wrong_segment"])
def test_current_snapshot_refuses_unknown_source(tmp_path, invalid):
    chroma = _make_store(tmp_path)
    _worker("write", chroma, 0, 200, "--guard")
    guard = cwg.ChromaWriteGuard(chroma)
    segment, _ = _segment(chroma)
    snap, _ = guard.current_snapshot(segment)
    pointer = guard.snapshots / segment / "CURRENT"
    if invalid == "traversal":
        pointer.write_text("../evil")
    elif invalid == "missing":
        pointer.write_text("g-does-not-exist")
    elif invalid == "symlink":
        saved = snap / "original-metadata"
        (snap / "SNAPSHOT.json").rename(saved)
        (snap / "SNAPSHOT.json").symlink_to(saved)
    else:
        meta = json.loads((snap / "SNAPSHOT.json").read_text())
        meta["segment"] = "different"
        (snap / "SNAPSHOT.json").write_text(json.dumps(meta))
    with pytest.raises(cwg.ChromaWriteGuardError):
        guard.current_snapshot(segment)


def stale_vector_incident(tmp_path):
    chroma = tmp_path / "chroma"
    client = chromadb.PersistentClient(path=str(chroma))
    col = client.create_collection(SUMMARIES,
        configuration={"hnsw": {"space": "cosine", "sync_threshold": 2, "batch_size": 1}})
    col.add(ids=["a", "b"] + [f"pad{i}" for i in range(98)],
        embeddings=[embedding_from_seed(i) for i in range(100)])
    client.close()
    guard = cwg.ChromaWriteGuard(chroma)
    cwg.recover(chroma)  # capture the real old vector generation
    client = chromadb.PersistentClient(path=str(chroma))
    col = client.get_collection(SUMMARIES)
    col.update(ids=["a"], embeddings=[embedding_from_seed(999)])
    col.upsert(ids=["b"], embeddings=[embedding_from_seed(1)])
    client.close()
    _, seg = _segment(chroma)
    assert cosine_vectors_equal(read_persisted_embedding_vector(seg, "a"), embedding_from_seed(999))
    _set_header_count(seg / "header.bin", 50)
    with pytest.raises(cwg.ChromaWriteQuarantinedError):
        cwg.recover(chroma)
    assert cwg.vector_census(chroma)[SUMMARIES]["lost"] == 0
    assert cosine_vectors_equal(read_persisted_embedding_vector(seg, "a"), embedding_from_seed(0))
    return guard, seg


def test_strict_release_and_actual_census_only_negative_control(tmp_path, monkeypatch):
    guard, seg = stale_vector_incident(tmp_path)
    before = guard.quarantine_path.read_bytes()
    with pytest.raises(cwg.ChromaWriteGuardError, match="watermark_drift"):
        release(guard)
    assert guard.quarantine_path.read_bytes() == before
    called = []

    def census_only(root, evidence, **_kwargs):
        row = cwg.vector_census(root)[evidence["collection_name"]]
        called.append(row)
        return row["lost"] == 0 and row["extra"] == 0, "faulty census-only policy"

    monkeypatch.setattr(cwg, "evaluate_release_evidence", census_only)
    release(guard)
    assert called and not guard.quarantine_path.exists()
    with pytest.raises(AssertionError, match="stale persisted vector"):
        actual = read_persisted_embedding_vector(seg, "a")
        assert cosine_vectors_equal(actual, embedding_from_seed(999)), "stale persisted vector was admitted"


@pytest.mark.parametrize("field,value", [
    ("vector_watermark", None), ("vector_watermark", 999999),
    ("vector_segment_id", "different"), ("backend_identity", {}), ("segment_digests", {}),
])
def test_release_oracle_refuses_missing_or_mismatched_evidence(tmp_path, field, value):
    _, guard = tear_and_trigger_restore(tmp_path)
    incident = guard.quarantine_state()["incidents"][0]
    evidence = copy.deepcopy(guard._release_evidence_for_incident(incident))
    evidence[field] = value
    ok, reason = cwg.evaluate_release_evidence(guard.chroma_dir, evidence)
    assert not ok and reason
    assert guard.read_authority().blocking

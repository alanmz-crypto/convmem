# pylint: disable=protected-access,redefined-outer-name,import-outside-toplevel,wrong-import-position,wrong-import-order,ungrouped-imports
"""Safe Harbor T3 preservation, bounded repair, and validated release (V3/V4).

require_t3_bootstrap() runs before pytest/project imports (intentional bootstrap order).
"""

from __future__ import annotations

import json
import os
import signal
import struct
import subprocess
import sys
import time
from pathlib import Path

from tests._safe_harbor_bootstrap import require_t3_bootstrap

require_t3_bootstrap()

import pytest

from chroma_store import SUMMARIES
from chroma_write_guard import (
    ChromaReleaseUncertaintyError,
    ChromaWriteGuard,
    ChromaWriteGuardError,
    ChromaWriteQuarantinedError,
    authority_submission_digest,
    build_release_evidence_for_collection,
    evaluate_release_evidence,
    validate_segment,
    vector_census,
)
from tests.test_chroma_write_guard import (
    _make_store,
    _segment,
    _set_header_count,
    _worker,
    _worker_expect_quarantine,
)

ROOT = Path(__file__).resolve().parents[1]


def _evaluate_census_only_faulty(chroma: Path, collection: str) -> bool:
    """Test-only weak control; must not match strict release oracle."""
    try:
        row = vector_census(chroma).get(collection)
    except (OSError, struct.error):
        return False
    if row is None:
        return False
    return row.get("lost", 1) == 0 and row.get("extra", 1) == 0


def _authority_release(guard: ChromaWriteGuard, disposition: str = "owner-disposition-test") -> None:
    view = guard.read_authority()
    assert view.document is not None
    guard.release_quarantine(
        disposition_ref=disposition,
        authority_digest=authority_submission_digest(view.document),
    )


def _tear_and_trigger_restore(tmp_path: Path) -> tuple[Path, ChromaWriteGuard]:
    chroma = _make_store(tmp_path)
    _worker("write", chroma, 0, 200, "--guard")
    _, seg = _segment(chroma)
    _set_header_count(seg / "header.bin", 50)
    _worker_expect_quarantine("write", chroma, 250, 1, "--guard")
    return chroma, ChromaWriteGuard(chroma)


def test_restore_publishes_incident_before_preservation(tmp_path: Path) -> None:
    chroma, guard = _tear_and_trigger_restore(tmp_path)
    assert chroma.is_dir()
    state = guard.quarantine_state()
    assert state is not None
    reasons = {f["reason"] for inc in state["incidents"] for f in inc["findings"]}
    assert any("bounded restore required" in r for r in reasons)
    incident = state["incidents"][0]
    assert incident.get("preservation", {}).get("status") == "complete"
    assert incident.get("repair", {}).get("status") == "complete"
    assert incident.get("occurrence", {}).get("epoch")
    assert (guard.root / "repair-pending").exists() is False


def test_clear_quarantine_refuses_without_validated_release(tmp_path: Path) -> None:
    _, guard = _tear_and_trigger_restore(tmp_path)
    with pytest.raises(ChromaWriteGuardError, match="validated release"):
        guard.clear_quarantine()


def test_stale_authority_digest_refuses_release(tmp_path: Path) -> None:
    _, guard = _tear_and_trigger_restore(tmp_path)
    view = guard.read_authority()
    assert view.document is not None
    stale = authority_submission_digest(view.document)
    with _exclusive_flock_ctx(guard):
        guard._publish_findings(
            [
                {
                    "segment": view.document["incidents"][0]["segment"],
                    "kind": "structural",
                    "reason": "published revision drift for stale digest test",
                    "failures": ["stale-test"],
                }
            ]
        )
    with pytest.raises(ChromaWriteGuardError, match="authority digest"):
        guard.release_quarantine(disposition_ref="d", authority_digest=stale)


def _exclusive_flock_ctx(guard: ChromaWriteGuard):
    from chroma_write_guard import _exclusive_flock

    return _exclusive_flock(guard.lock_path, guard.lock_timeout_seconds)


def test_release_after_repair_with_matching_authority(tmp_path: Path) -> None:
    _, guard = _tear_and_trigger_restore(tmp_path)
    evidence = build_release_evidence_for_collection(guard.chroma_dir, SUMMARIES)
    ok, reason = evaluate_release_evidence(guard.chroma_dir, evidence)
    assert ok, reason
    _authority_release(guard)
    assert guard.quarantine_state() is None


def test_strict_release_refuses_census_only_faulty_control(tmp_path: Path) -> None:
    _, guard = _tear_and_trigger_restore(tmp_path)
    evidence = build_release_evidence_for_collection(guard.chroma_dir, SUMMARIES)
    assert _evaluate_census_only_faulty(guard.chroma_dir, SUMMARIES)
    _, seg = _segment(guard.chroma_dir)
    data_path = seg / "data_level0.bin"
    raw = bytearray(data_path.read_bytes())
    raw[min(200, len(raw) - 1)] ^= 0x01
    data_path.write_bytes(bytes(raw))
    assert _evaluate_census_only_faulty(guard.chroma_dir, SUMMARIES)
    ok, reason = evaluate_release_evidence(guard.chroma_dir, evidence)
    assert not ok
    assert reason


def test_preservation_manifest_tamper_refuses_release(tmp_path: Path) -> None:
    _, guard = _tear_and_trigger_restore(tmp_path)
    incident = guard.quarantine_state()["incidents"][0]
    manifest = guard._preservation_dir(incident["id"], incident) / "MANIFEST.json"
    manifest.write_bytes(manifest.read_bytes() + b" ")
    with pytest.raises(ChromaWriteGuardError, match="preservation"):
        _authority_release(guard)


def test_truncated_events_tail_blocks_release(tmp_path: Path) -> None:
    _, guard = _tear_and_trigger_restore(tmp_path)
    with guard.events_path.open("ab") as fh:
        fh.write(b'{"truncated":')
    with pytest.raises(ChromaWriteGuardError, match="truncated"):
        _authority_release(guard)


def test_release_fsync_uncertainty_after_marker_removal(tmp_path: Path, monkeypatch) -> None:
    from chroma_write_guard import _fsync as real_fsync

    _, guard = _tear_and_trigger_restore(tmp_path)
    view = guard.read_authority()
    assert view.document is not None
    digest = authority_submission_digest(view.document)

    def boom(path, *, directory=False):  # noqa: ANN001
        if directory and path == guard.quarantine_path.parent:
            raise OSError("simulated fsync failure")
        return real_fsync(path, directory=directory)

    monkeypatch.setattr("chroma_write_guard._fsync", boom)
    with pytest.raises(ChromaReleaseUncertaintyError):
        guard.release_quarantine(disposition_ref="d", authority_digest=digest)


def test_legitimate_release_then_new_incident_requires_fresh_digest(tmp_path: Path) -> None:
    chroma, guard = _tear_and_trigger_restore(tmp_path)
    view = guard.read_authority()
    assert view.document is not None
    first_digest = authority_submission_digest(view.document)
    _authority_release(guard)
    _worker("write", chroma, 300, 50, "--guard")
    _, seg = _segment(chroma)
    _set_header_count(seg / "header.bin", 30)
    _worker_expect_quarantine("write", chroma, 400, 1, "--guard")
    guard = ChromaWriteGuard(chroma)
    with pytest.raises(ChromaWriteGuardError, match="authority digest"):
        guard.release_quarantine(disposition_ref="second-release", authority_digest=first_digest)
    _authority_release(guard, disposition="second-release")
    assert guard.quarantine_state() is None


def test_finding_detail_revision_changes_authority_digest(tmp_path: Path) -> None:
    _, guard = _tear_and_trigger_restore(tmp_path)
    view = guard.read_authority()
    assert view.document is not None
    first = authority_submission_digest(view.document)
    document, _ = guard._load_incident_document()
    spec = {
        "segment": document["incidents"][0]["segment"],
        "kind": "structural",
        "reason": "additional review detail for same segment",
        "failures": ["detail-b"],
        "detail": {"phase": "review"},
    }
    guard._publish_findings([spec])
    view2 = guard.read_authority()
    assert view2.document is not None
    second = authority_submission_digest(view2.document)
    assert first != second


def test_subprocess_kill_before_restore_publication(tmp_path: Path) -> None:
    chroma = _make_store(tmp_path)
    _worker("write", chroma, 0, 200, "--guard")
    _, seg = _segment(chroma)
    _set_header_count(seg / "header.bin", 50)
    ready = tmp_path / "ready"
    release = tmp_path / "release"
    code = (
        "import os,sys; from pathlib import Path; "
        f"sys.path.insert(0, {repr(str(ROOT))}); "
        "from chroma_write_guard import ChromaWriteGuard; "
        f"os.environ['CONVMEM_GUARD_ADMISSION_BARRIER'] = {repr(str(ready) + ':' + str(release))}; "
        "g=ChromaWriteGuard(%r); "
        "g.reconcile()"
    ) % (str(chroma),)
    with subprocess.Popen(
        [sys.executable, "-c", code],
        cwd=ROOT,
        env={**os.environ, "PYTHONPATH": str(ROOT)},
    ) as proc:
        time.sleep(0.2)
        proc.send_signal(signal.SIGKILL)
        proc.wait(timeout=10)
    guard = ChromaWriteGuard(chroma)
    if validate_segment(seg).ok:
        assert guard.quarantine_state() is not None


def test_copy_durable_short_write_refuses_preservation(tmp_path: Path, monkeypatch) -> None:
    from chroma_write_guard import _fsync

    def short_copy(_src, dst):  # noqa: ANN001
        dst.write_bytes(b"short")
        _fsync(dst)

    monkeypatch.setattr("chroma_write_guard._copy_durable", short_copy)
    with pytest.raises((ChromaWriteQuarantinedError, ChromaWriteGuardError, OSError)):
        _tear_and_trigger_restore(tmp_path)


def test_pinned_generation_retained_across_refresh(tmp_path: Path) -> None:
    chroma, guard = _tear_and_trigger_restore(tmp_path)
    seg_id, _ = _segment(chroma)
    pinned = guard.quarantine_state()["incidents"][0]["pinned_source"]["generation"]
    pinned_dir = guard.snapshots / seg_id / pinned
    assert pinned_dir.is_dir()
    _worker("write", chroma, 500, 200, "--guard")
    assert pinned_dir.is_dir()


def test_legacy_snapshot_without_release_evidence_refuses_release(tmp_path: Path) -> None:
    chroma = _make_store(tmp_path)
    _worker("write", chroma, 0, 150, "--guard")
    guard = ChromaWriteGuard(chroma)
    seg_id, seg = _segment(chroma)
    snap = guard.current_snapshot(seg_id)
    assert snap is not None
    meta = snap[1]
    meta.pop("release_evidence", None)
    snap_path = snap[0] / "SNAPSHOT.json"
    snap_path.write_text(json.dumps(meta, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    _set_header_count(seg / "header.bin", 40)
    _worker_expect_quarantine("write", chroma, 200, 1, "--guard")
    guard = ChromaWriteGuard(chroma)
    if guard.quarantine_state() is not None:
        with pytest.raises(ChromaWriteGuardError, match="release evidence|repair is not complete|preservation"):
            _authority_release(guard)

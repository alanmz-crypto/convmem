# pylint: disable=protected-access,redefined-outer-name,import-outside-toplevel
"""Safe Harbor T3 preservation, bounded repair, and validated release (V3/V4)."""

from __future__ import annotations

import hashlib
import json
import os
import struct
import subprocess
import sys
from pathlib import Path

import chromadb
import pytest

if os.environ.get("SAFE_HARBOR_T3_BOOTSTRAPPED") != "1":
    pytest.skip(
        "refusing import without launcher isolation: run "
        "/home/lauer/miniforge3/bin/python -I -S -B tests/_safe_harbor_t3_worker.py run-t3",
        allow_module_level=True,
    )

from chroma_store import SUMMARIES, ChromaStore
from chroma_write_guard import (
    ChromaReleaseUncertaintyError,
    ChromaWriteGuard,
    ChromaWriteGuardError,
    ChromaWriteQuarantinedError,
    build_release_evidence_for_collection,
    evaluate_census_only_release,
    evaluate_release_evidence,
    recover,
    segment_dirs,
    segment_file_digests,
    validate_segment,
)
from tests.test_chroma_write_guard import _events, _make_store, _segment, _set_header_count, _worker

ROOT = Path(__file__).resolve().parents[1]
WORKER = ROOT / "tests" / "_chroma_write_guard_worker.py"


def _finding_digests(guard: ChromaWriteGuard) -> dict[str, str]:
    state = guard.quarantine_state()
    assert state is not None
    out: dict[str, str] = {}
    for incident in state["incidents"]:
        for finding in incident["findings"]:
            out[finding["id"]] = finding["digest"]
    return out


def _release_after_repair(guard: ChromaWriteGuard, disposition: str = "owner-disposition-test") -> None:
    digests = _finding_digests(guard)
    assert guard.release_quarantine(disposition_ref=disposition, finding_digests=digests)


def test_automatic_restore_quarantines_even_when_census_clean(tmp_path: Path) -> None:
    chroma = _make_store(tmp_path)
    _worker("write", chroma, 0, 200, "--guard")
    _, seg = _segment(chroma)
    _set_header_count(seg / "header.bin", 50)
    with pytest.raises(ChromaWriteQuarantinedError):
        _worker("write", chroma, 250, 1, "--guard")
    guard = ChromaWriteGuard(chroma)
    state = guard.quarantine_state()
    assert state is not None and state["blocking"]
    kinds = {f["kind"] for inc in state["incidents"] for f in inc["findings"]}
    assert "segment_restored" in kinds
    manifest = guard._preservation_dir(state["incidents"][0]["id"]) / "MANIFEST.json"
    assert manifest.is_file()


def test_clear_quarantine_refuses_without_validated_release(tmp_path: Path) -> None:
    chroma = _make_store(tmp_path)
    _worker("write", chroma, 0, 200, "--guard")
    _, seg = _segment(chroma)
    _set_header_count(seg / "header.bin", 50)
    with pytest.raises(ChromaWriteQuarantinedError):
        _worker("write", chroma, 250, 1, "--guard")
    guard = ChromaWriteGuard(chroma)
    with pytest.raises(ChromaWriteGuardError, match="validated release"):
        guard.clear_quarantine()


def test_release_requires_exact_finding_digests(tmp_path: Path) -> None:
    chroma = _make_store(tmp_path)
    _worker("write", chroma, 0, 200, "--guard")
    _, seg = _segment(chroma)
    _set_header_count(seg / "header.bin", 50)
    with pytest.raises(ChromaWriteQuarantinedError):
        _worker("write", chroma, 250, 1, "--guard")
    guard = ChromaWriteGuard(chroma)
    digests = _finding_digests(guard)
    stale = dict(digests)
    stale[next(iter(stale))] = "0" * 64
    with pytest.raises(ChromaWriteGuardError, match="do not match"):
        guard.release_quarantine(disposition_ref="disp-1", finding_digests=stale)


def test_release_admits_after_repair_when_evidence_matches(tmp_path: Path) -> None:
    chroma = _make_store(tmp_path)
    _worker("write", chroma, 0, 200, "--guard")
    _, seg = _segment(chroma)
    _set_header_count(seg / "header.bin", 50)
    with pytest.raises(ChromaWriteQuarantinedError):
        _worker("write", chroma, 250, 1, "--guard")
    guard = ChromaWriteGuard(chroma)
    evidence = build_release_evidence_for_collection(chroma, SUMMARIES)
    ok, reason = evaluate_release_evidence(chroma, evidence)
    assert ok, reason
    _release_after_repair(guard)
    assert guard.quarantine_state() is None


def test_evaluate_release_refuses_census_only_control(tmp_path: Path) -> None:
    chroma = _make_store(tmp_path)
    _worker("write", chroma, 0, 200, "--guard")
    evidence = build_release_evidence_for_collection(chroma, SUMMARIES)
    assert evaluate_census_only_release(chroma, SUMMARIES)
    _, seg = _segment(chroma)
    id_map_path = seg / "index_metadata.pickle"
    id_map_path.write_bytes(id_map_path.read_bytes())  # touch
    # Census-only stays green while strict oracle may still pass if digests unchanged;
    # corrupt a vector byte to create stale persisted state vs metadata.
    data_path = seg / "data_level0.bin"
    raw = bytearray(data_path.read_bytes())
    if raw:
        raw[min(200, len(raw) - 1)] ^= 0x01
        data_path.write_bytes(bytes(raw))
    assert evaluate_census_only_release(chroma, SUMMARIES)
    ok, reason = evaluate_release_evidence(chroma, evidence)
    assert not ok
    assert "digest" in reason or "structural" in reason or "census" in reason


def test_pinned_snapshot_generation_survives_refresh(tmp_path: Path) -> None:
    chroma = _make_store(tmp_path)
    _worker("write", chroma, 0, 200, "--guard")
    guard = ChromaWriteGuard(chroma)
    seg_id, _ = _segment(chroma)
    snap_before = guard.current_snapshot(seg_id)
    assert snap_before is not None
    generation = snap_before[0].name
    _, seg = _segment(chroma)
    _set_header_count(seg / "header.bin", 50)
    with pytest.raises(ChromaWriteQuarantinedError):
        _worker("write", chroma, 250, 1, "--guard")
    pinned_dir = guard.snapshots / seg_id / generation
    assert pinned_dir.is_dir()
    _worker("write", chroma, 300, 200, "--guard")
    assert pinned_dir.is_dir()


def test_preservation_originals_are_write_once(tmp_path: Path) -> None:
    chroma = _make_store(tmp_path)
    _worker("write", chroma, 0, 200, "--guard")
    _, seg = _segment(chroma)
    _set_header_count(seg / "header.bin", 50)
    with pytest.raises(ChromaWriteQuarantinedError):
        _worker("write", chroma, 250, 1, "--guard")
    guard = ChromaWriteGuard(chroma)
    incident = guard.quarantine_state()["incidents"][0]
    incident_id = incident["id"]
    digest = incident["preservation"]["manifest_digest"]
    originals = guard._preservation_dir(incident_id) / "originals"
    header = originals / "header.bin"
    header.write_bytes(header.read_bytes() + b"x")
    assert not guard._verify_preservation_manifest(incident_id, digest)
    with pytest.raises(ChromaWriteGuardError, match="source evidence"):
        guard.release_quarantine(disposition_ref="d", finding_digests=_finding_digests(guard))


def test_truncated_events_tail_blocks_release(tmp_path: Path) -> None:
    chroma = _make_store(tmp_path)
    _worker("write", chroma, 0, 200, "--guard")
    _, seg = _segment(chroma)
    _set_header_count(seg / "header.bin", 50)
    with pytest.raises(ChromaWriteQuarantinedError):
        _worker("write", chroma, 250, 1, "--guard")
    guard = ChromaWriteGuard(chroma)
    with guard.events_path.open("ab") as fh:
        fh.write(b'{"truncated":')
    with pytest.raises(ChromaWriteGuardError, match="truncated"):
        guard.release_quarantine(disposition_ref="d", finding_digests=_finding_digests(guard))


def test_release_fsync_failure_reports_uncertainty(tmp_path: Path, monkeypatch) -> None:
    chroma = _make_store(tmp_path)
    _worker("write", chroma, 0, 200, "--guard")
    _, seg = _segment(chroma)
    _set_header_count(seg / "header.bin", 50)
    with pytest.raises(ChromaWriteQuarantinedError):
        _worker("write", chroma, 250, 1, "--guard")
    guard = ChromaWriteGuard(chroma)

    def boom(path, *, directory=False):  # noqa: ANN001
        if directory and path == guard.quarantine_path.parent:
            raise OSError("simulated fsync failure")
        from chroma_write_guard import _fsync as real

        return real(path, directory=directory)

    monkeypatch.setattr("chroma_write_guard._fsync", boom)
    with pytest.raises(ChromaReleaseUncertaintyError):
        guard.release_quarantine(disposition_ref="d", finding_digests=_finding_digests(guard))


def test_recover_subprocess_restarts_barrier(tmp_path: Path) -> None:
    chroma = _make_store(tmp_path)
    _worker("write", chroma, 0, 150, "--guard")
    code = (
        "import os,sys; from pathlib import Path; "
        "sys.path.insert(0, %r); from chroma_write_guard import recover; "
        "os.environ['CONVMEM_GUARD_ADMISSION_BARRIER'] = %r; "
        "recover(%r); print('done')"
    )
    ready = tmp_path / "ready"
    release = tmp_path / "release"
    ready.unlink(missing_ok=True)
    release.unlink(missing_ok=True)
    env = os.environ.copy()
    env["CONVMEM_GUARD_ADMISSION_BARRIER"] = f"{ready}:{release}"
    proc = subprocess.Popen(
        [sys.executable, "-c", code % (str(ROOT), f"{ready}:{release}", str(chroma))],
        cwd=ROOT,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    for _ in range(200):
        if ready.is_file():
            break
        if proc.poll() is not None:
            break
        import time

        time.sleep(0.02)
    assert ready.is_file()
    release.write_text("go", encoding="utf-8")
    out, err = proc.communicate(timeout=30)
    assert proc.returncode == 0, err[-1000:] + out[-1000:]

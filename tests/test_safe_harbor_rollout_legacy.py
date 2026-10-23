"""Synthetic legacy saves only; private refresh access is not a deployment command."""
# pylint: disable=wrong-import-position,protected-access,redefined-outer-name,wrong-import-order,ungrouped-imports,use-implicit-booleaness-not-comparison
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil

from tests._safe_harbor_bootstrap import require_t3_bootstrap

require_t3_bootstrap()

import pytest

import chroma_write_guard as guard_module
from chroma_write_guard import (
    ChromaWriteGuard, ChromaWriteGuardError, ChromaWriteQuarantinedError,
    authority_submission_digest, evaluate_release_evidence, recover,
    segment_signature, validate_segment,
)
from tests.test_chroma_write_guard import _make_store, _segment, _set_header_count, _worker


def _digests(root: Path) -> dict[str, str]:
    return {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(root.rglob('*')) if p.is_file()}


def _legacy(tmp_path: Path, *, count: int = 200):
    chroma = _make_store(tmp_path)
    _worker('write', chroma, 0, count, '--guard')
    segment_id, segment = _segment(chroma)
    guard = ChromaWriteGuard(chroma)
    generation, metadata = guard.current_snapshot(segment_id)
    assert 'release_evidence' in metadata
    metadata.pop('release_evidence')
    assert set(metadata) == {'segment', 'live_signature', 'created_at', 'pid'}
    (generation / 'SNAPSHOT.json').write_text(json.dumps(metadata), encoding='utf-8')
    assert metadata['live_signature'] == segment_signature(segment)
    assert validate_segment(segment).ok
    return chroma, guard, segment_id, segment, generation


def test_unchanged_legacy_reconcile_is_not_initialization(tmp_path):
    chroma, guard, segment_id, _, generation = _legacy(tmp_path)
    saved = _digests(generation)
    pointer = (generation.parent / 'CURRENT').read_bytes()
    assert recover(chroma) == []
    current, metadata = guard.current_snapshot(segment_id)
    assert current == generation
    assert 'release_evidence' not in metadata
    assert _digests(generation) == saved
    assert (generation.parent / 'CURRENT').read_bytes() == pointer
    assert guard.quarantine_state() is None


def test_legacy_restore_refuses_before_replacement_and_release(tmp_path):
    chroma, guard, _, segment, generation = _legacy(tmp_path)
    saved = _digests(generation)
    _set_header_count(segment / 'header.bin', 50)
    torn = _digests(segment)
    with pytest.raises(ChromaWriteQuarantinedError):
        recover(chroma)
    document = guard.read_authority().document
    assert document and document['incidents']
    assert 'lacks release evidence' in json.dumps(document)
    assert _digests(segment) == torn
    assert _digests(generation) == saved
    marker = guard.quarantine_path.read_bytes()
    with pytest.raises(ChromaWriteGuardError, match='repair is not complete'):
        guard.release_quarantine(
            disposition_ref='synthetic-legacy-refusal',
            authority_digest=authority_submission_digest(document),
        )
    assert guard.quarantine_path.read_bytes() == marker
    with pytest.raises(ChromaWriteQuarantinedError):
        recover(chroma)


def _archived_refresh(tmp_path, *, fault=False, monkeypatch=None):
    chroma, guard, segment_id, segment, generation = _legacy(tmp_path)
    # Outside the guard's prune tree, within the disposable fixture. This copy
    # proves byte retention only; it is not an operational archival protocol.
    archive = tmp_path / 'original-generation'
    shutil.copytree(generation, archive)
    saved = _digests(generation)
    pointer_path = generation.parent / 'CURRENT'
    pointer = pointer_path.read_bytes()
    (tmp_path / 'original-CURRENT').write_bytes(pointer)
    live = _digests(chroma)
    if fault:
        real = guard_module._write_json_durable

        def fail_manifest(path, data):
            if path.name == 'SNAPSHOT.json':
                raise OSError('injected before snapshot manifest publication')
            return real(path, data)

        monkeypatch.setattr(guard_module, '_write_json_durable', fail_manifest)
        with pytest.raises(OSError, match='injected before snapshot'):
            with guard_module._exclusive_flock(guard.lock_path, guard.lock_timeout_seconds):
                guard._refresh_snapshot(segment_id, segment, segment_signature(segment))
        assert pointer_path.read_bytes() == pointer
        assert _digests(generation) == saved
        assert not list(generation.parent.glob('.*.partial'))
    else:
        with guard_module._exclusive_flock(guard.lock_path, guard.lock_timeout_seconds):
            guard._refresh_snapshot(segment_id, segment, segment_signature(segment))
        current, metadata = guard.current_snapshot(segment_id)
        assert current != generation
        # The real refresh prunes the unpinned old save. Archival is load-bearing.
        assert not generation.exists()
        ok, reason = evaluate_release_evidence(chroma, metadata['release_evidence'])
        assert ok, reason
        assert metadata['live_signature'] == segment_signature(segment)
        assert recover(chroma) == []
    assert _digests(archive) == saved
    assert (tmp_path / 'original-CURRENT').read_bytes() == pointer
    assert _digests(chroma) == live
    return chroma, guard, segment


def test_explicit_scratch_refresh_preserves_archive_and_enables_release(tmp_path):
    chroma, guard, segment = _archived_refresh(tmp_path)
    _set_header_count(segment / 'header.bin', 50)
    with pytest.raises(ChromaWriteQuarantinedError):
        recover(chroma)
    document = guard.read_authority().document
    assert document['incidents'][0]['repair']['status'] == 'complete'
    guard.release_quarantine(
        disposition_ref='synthetic-post-refresh-release',
        authority_digest=authority_submission_digest(document),
    )
    assert guard.quarantine_state() is None
    assert validate_segment(segment).ok


def test_refresh_manifest_failure_keeps_old_pointer_and_archive(tmp_path, monkeypatch):
    _archived_refresh(tmp_path, fault=True, monkeypatch=monkeypatch)


def test_refresh_with_pending_work_cannot_manufacture_releasability(tmp_path):
    chroma, guard, segment_id, segment, generation = _legacy(tmp_path, count=250)
    archive = tmp_path / 'original-pending-generation'
    shutil.copytree(generation, archive)
    saved = _digests(generation)
    live = _digests(chroma)
    with guard_module._exclusive_flock(guard.lock_path, guard.lock_timeout_seconds):
        guard._refresh_snapshot(segment_id, segment, segment_signature(segment))
    current, metadata = guard.current_snapshot(segment_id)
    assert current != generation
    assert not generation.exists()
    assert _digests(archive) == saved
    assert _digests(chroma) == live
    ok, reason = evaluate_release_evidence(chroma, metadata['release_evidence'])
    assert not ok
    assert 'watermark_drift' in reason
    _set_header_count(segment / 'header.bin', 50)
    with pytest.raises(ChromaWriteQuarantinedError):
        recover(chroma)
    document = guard.read_authority().document
    assert document['incidents'][0]['repair']['status'] == 'complete'
    marker = guard.quarantine_path.read_bytes()
    with pytest.raises(ChromaWriteGuardError, match='watermark_drift'):
        guard.release_quarantine(
            disposition_ref='synthetic-pending-work-refusal',
            authority_digest=authority_submission_digest(document),
        )
    assert guard.quarantine_path.read_bytes() == marker
    assert _digests(archive) == saved

# ref: ../docs/plans/ROLLOUT-safe-harbor.md — legacy readiness, not live initialization authority
# src: ./test_safe_harbor_t3.py, ../chroma_write_guard.py — real guard and release mechanics

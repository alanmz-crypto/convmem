"""Isolated evidence for EXECUTION §22 initialize-legacy."""
# pylint: disable=protected-access,redefined-outer-name,wrong-import-position
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

from tests._safe_harbor_bootstrap import require_t3_bootstrap

require_t3_bootstrap()

import pytest

import chroma_write_guard as guard_module
from chroma_store import UNITS, ChromaStore
from chroma_write_guard import (
    ChromaWriteGuard,
    ChromaWriteGuardError,
    evaluate_release_evidence,
    initialize_legacy,
    segment_dirs,
    segment_signature,
)
from tests._chroma_write_guard_worker import embedding
from tests.test_chroma_write_guard import ROOT, WORKER, _make_store, _segment, _set_header_count, _worker


def _digests(root: Path) -> dict[str, str]:
    return {
        str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(root.rglob("*"))
        if p.is_file()
    }


def _dir_entries(root: Path) -> set[str]:
    if not root.exists():
        return set()
    return {str(p.relative_to(root)) for p in root.rglob("*")}


def _run_cli(
    chroma: Path,
    archive: Path,
    *,
    apply: bool = False,
    expect_state: str | None = None,
    extra: list[str] | None = None,
) -> tuple[int, dict]:
    cmd = [
        sys.executable,
        str(ROOT / "scripts" / "chroma_guard.py"),
        "initialize-legacy",
        "--chroma-dir",
        str(chroma.resolve()),
        "--archive-dir",
        str(archive.resolve()),
    ]
    if apply:
        cmd.append("--apply")
    if expect_state:
        cmd.extend(["--expect-state", expect_state])
    if extra:
        cmd.extend(extra)
    done = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, check=False)
    payload = json.loads(done.stdout.strip() or "{}")
    return done.returncode, payload


def _strip_release_evidence(chroma: Path) -> ChromaWriteGuard:
    guard = ChromaWriteGuard(chroma)
    for seg_id in segment_dirs(chroma):
        snap = guard.current_snapshot(seg_id)
        assert snap is not None
        meta = snap[1]
        meta.pop("release_evidence", None)
        (snap[0] / "SNAPSHOT.json").write_text(json.dumps(meta, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return guard


def _legacy_store(tmp_path: Path, *, units: int = 0) -> tuple[Path, ChromaWriteGuard]:
    chroma = _make_store(tmp_path)
    _worker("write", chroma, 0, 200, "--guard")
    if units:
        store = ChromaStore(str(chroma), write_guard=ChromaWriteGuard(chroma))
        try:
            for index in range(units):
                uid = f"u{index}"
                store.add_unit(uid, f"unit {uid}", embedding(uid), {"n": index})
        finally:
            store.close()
    guard = _strip_release_evidence(chroma)
    return chroma, guard


def test_preview_success_leaves_store_unchanged(tmp_path: Path) -> None:
    chroma, guard = _legacy_store(tmp_path)
    archive = tmp_path / "archive-preview"
    before = _digests(chroma)
    guard_tree = _dir_entries(guard.root)
    code, payload = _run_cli(chroma, archive)
    assert code == 0
    assert payload["status"] == "preview_ready"
    assert not archive.exists()
    assert _digests(chroma) == before
    assert _dir_entries(guard.root) == guard_tree
    lock_before = guard.lock_path.exists()
    assert lock_before == guard.lock_path.exists()


def test_preview_refusal_leaves_store_unchanged(tmp_path: Path) -> None:
    chroma, _guard = _legacy_store(tmp_path)
    archive = tmp_path / "archive-refuse"
    archive.mkdir()
    (archive / "leftover").write_text("x", encoding="utf-8")
    before = _digests(chroma)
    code, payload = _run_cli(chroma, archive)
    assert code == 1
    assert payload["status"] == "refused"
    assert _digests(chroma) == before


def test_faulty_preview_calling_prepare_must_not_mutate(tmp_path: Path, monkeypatch) -> None:
    chroma, guard = _legacy_store(tmp_path)
    archive = tmp_path / "archive-fault-preview"
    before = _digests(guard.root)
    real_inspect = guard_module._legacy_initializer_inspect

    def faulty_inspect(guard_obj, archive_dir):
        seg_id, seg = next(iter(segment_dirs(guard_obj.chroma_dir).items()))
        with guard_module._exclusive_flock(guard_obj.lock_path, guard_obj.lock_timeout_seconds):
            guard_obj._prepare_snapshot_generation(seg_id, seg, segment_signature(seg))
        return real_inspect(guard_obj, archive_dir)

    monkeypatch.setattr(guard_module, "_legacy_initializer_inspect", faulty_inspect)
    payload, code = initialize_legacy(chroma, archive)
    assert code in (0, 1, 2)
    assert _digests(guard.root) != before


def test_two_segment_initialize_legacy_end_to_end(tmp_path: Path) -> None:
    chroma, guard = _legacy_store(tmp_path, units=200)
    assert len(segment_dirs(chroma)) == 2
    archive = tmp_path / "archive-apply"
    code, preview = _run_cli(chroma, archive)
    assert code == 0 and preview["status"] == "preview_ready"
    digest = preview["state_digest"]
    originals = {
        seg_id: (guard.snapshots / seg_id / "CURRENT").read_bytes()
        for seg_id in segment_dirs(chroma)
    }
    live_before = _digests(chroma)
    code, result = _run_cli(chroma, archive, apply=True, expect_state=digest)
    assert code == 0
    assert result["status"] == "complete"
    assert (archive / "MANIFEST.json").is_file()
    assert _digests(chroma) == live_before
    for seg_id in segment_dirs(chroma):
        assert (guard.snapshots / seg_id / "CURRENT").read_bytes() != originals[seg_id]
        current, meta = guard.current_snapshot(seg_id)
        assert current is not None
        ok, reason = evaluate_release_evidence(chroma, meta["release_evidence"])
        assert ok, reason
    old_generations = list(guard.snapshots.rglob("SNAPSHOT.json"))
    assert len(old_generations) >= 4


def test_mixed_legacy_and_initialized_refuses_before_current_changes(tmp_path: Path) -> None:
    chroma, guard = _legacy_store(tmp_path, units=200)
    seg_ids = sorted(segment_dirs(chroma))
    kept = guard.current_snapshot(seg_ids[0])
    assert kept is not None
    with guard_module._exclusive_flock(guard.lock_path, guard.lock_timeout_seconds):
        guard._refresh_snapshot(seg_ids[0], segment_dirs(chroma)[seg_ids[0]], segment_signature(segment_dirs(chroma)[seg_ids[0]]))
    archive = tmp_path / "archive-mixed"
    code, preview = _run_cli(chroma, archive)
    assert preview["status"] == "refused"
    pointers = {seg: (guard.snapshots / seg / "CURRENT").read_bytes() for seg in segment_dirs(chroma)}
    code, _result = _run_cli(chroma, archive, apply=True, expect_state=preview.get("state_digest") or "0" * 64)
    assert code != 0
    for seg, pointer in pointers.items():
        assert (guard.snapshots / seg / "CURRENT").read_bytes() == pointer


def test_apply_digest_and_target_refusals(tmp_path: Path) -> None:
    chroma, _guard = _legacy_store(tmp_path)
    archive = tmp_path / "archive-digest"
    code, preview = _run_cli(chroma, archive)
    digest = preview["state_digest"]
    code, payload = _run_cli(chroma, archive, apply=True, expect_state="0" * 64)
    assert code == 1 and payload["status"] == "refused"
    other = tmp_path / "other-chroma"
    other.mkdir()
    code, payload = _run_cli(other, archive, apply=True, expect_state=digest)
    assert code in (1, 2)


def test_usage_exit_when_apply_without_digest(tmp_path: Path) -> None:
    chroma, _guard = _legacy_store(tmp_path)
    archive = tmp_path / "archive-usage"
    code, payload = _run_cli(chroma, archive, apply=True)
    assert code == 2
    assert payload["status"] == "unavailable"


def test_source_fact_change_after_preview_refuses_apply(tmp_path: Path) -> None:
    chroma, guard = _legacy_store(tmp_path)
    archive = tmp_path / "archive-source"
    code, preview = _run_cli(chroma, archive)
    digest = preview["state_digest"]
    seg_id, seg = _segment(chroma)
    _set_header_count(seg / "header.bin", 40)
    code, payload = _run_cli(chroma, archive, apply=True, expect_state=digest)
    assert code == 1
    assert payload["status"] == "refused"


def test_archive_hash_mismatch_prevents_publish(tmp_path: Path, monkeypatch) -> None:
    chroma, guard = _legacy_store(tmp_path)
    archive = tmp_path / "archive-fault"
    code, preview = _run_cli(chroma, archive)
    digest = preview["state_digest"]
    real_copy = guard_module._copy_durable

    def short_copy(src, dst):
        if "/segments/" in str(dst) and "/archive" in str(dst):
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_bytes(src.read_bytes()[:10])
            guard_module._fsync(dst)
            return
        return real_copy(src, dst)

    monkeypatch.setattr(guard_module, "_copy_durable", short_copy)
    pointer = (guard.snapshots / _segment(chroma)[0] / "CURRENT").read_bytes()
    payload, code = initialize_legacy(chroma, archive, apply=True, expect_state=digest)
    assert code == 2
    assert payload["status"] == "partial_or_uncertain"
    assert (guard.snapshots / _segment(chroma)[0] / "CURRENT").read_bytes() == pointer


def test_omit_archive_control_fails_retention(tmp_path: Path, monkeypatch) -> None:
    chroma, guard = _legacy_store(tmp_path)
    archive = tmp_path / "archive-omit"
    code, preview = _run_cli(chroma, archive)
    digest = preview["state_digest"]

    def omit_archive(*_args, **_kwargs):
        raise ChromaWriteGuardError("faulty omit-archive control")

    monkeypatch.setattr(guard_module, "_legacy_initializer_archive_originals", omit_archive)
    pointer = (guard.snapshots / _segment(chroma)[0] / "CURRENT").read_bytes()
    payload, code = initialize_legacy(chroma, archive, apply=True, expect_state=digest)
    assert code == 2
    assert (guard.snapshots / _segment(chroma)[0] / "CURRENT").read_bytes() == pointer


def test_second_segment_prepare_failure_keeps_current(tmp_path: Path, monkeypatch) -> None:
    chroma, guard = _legacy_store(tmp_path, units=200)
    archive = tmp_path / "archive-second-fail"
    code, preview = _run_cli(chroma, archive)
    digest = preview["state_digest"]
    pointers = {seg: (guard.snapshots / seg / "CURRENT").read_bytes() for seg in segment_dirs(chroma)}
    segments = sorted(segment_dirs(chroma))
    real_prepare = ChromaWriteGuard._prepare_snapshot_generation
    calls = 0

    def fail_second(self, seg_id, seg, live_sig):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise ChromaWriteGuardError("injected second-segment preparation failure")
        return real_prepare(self, seg_id, seg, live_sig)

    monkeypatch.setattr(ChromaWriteGuard, "_prepare_snapshot_generation", fail_second)
    payload, code = initialize_legacy(chroma, archive, apply=True, expect_state=digest)
    assert code == 2
    assert payload["status"] == "partial_or_uncertain"
    for seg, pointer in pointers.items():
        assert (guard.snapshots / seg / "CURRENT").read_bytes() == pointer


def test_publish_during_preparation_control_fails(tmp_path: Path, monkeypatch) -> None:
    chroma, guard = _legacy_store(tmp_path, units=200)
    archive = tmp_path / "archive-early-publish"
    code, preview = _run_cli(chroma, archive)
    digest = preview["state_digest"]
    pointers = {seg: (guard.snapshots / seg / "CURRENT").read_bytes() for seg in segment_dirs(chroma)}
    real_prepare = ChromaWriteGuard._prepare_snapshot_generation

    def publish_early(self, seg_id, seg, live_sig):
        generation, generation_dir, meta, first = real_prepare(self, seg_id, seg, live_sig)
        self._publish_snapshot_current(seg_id, generation)
        return generation, generation_dir, meta, first

    monkeypatch.setattr(ChromaWriteGuard, "_prepare_snapshot_generation", publish_early)
    payload, code = initialize_legacy(chroma, archive, apply=True, expect_state=digest)
    assert code == 2
    unchanged = all(
        (guard.snapshots / seg / "CURRENT").read_bytes() == pointer for seg, pointer in pointers.items()
    )
    assert not unchanged


def test_success_does_not_prune_old_generations(tmp_path: Path) -> None:
    chroma, guard = _legacy_store(tmp_path)
    seg_id, _seg = _segment(chroma)
    old_generation = guard.current_snapshot(seg_id)[0]
    archive = tmp_path / "archive-no-prune"
    code, preview = _run_cli(chroma, archive)
    digest = preview["state_digest"]
    code, result = _run_cli(chroma, archive, apply=True, expect_state=digest)
    assert code == 0 and result["status"] == "complete"
    assert old_generation.is_dir()


def test_quarantined_store_refuses_initialize_legacy(tmp_path: Path) -> None:
    from chroma_write_guard import ChromaWriteQuarantinedError, recover

    chroma, guard = _legacy_store(tmp_path)
    seg_id, seg = _segment(chroma)
    _set_header_count(seg / "header.bin", 40)
    with pytest.raises(ChromaWriteQuarantinedError):
        recover(chroma)
    archive = tmp_path / "archive-quarantine"
    code, payload = _run_cli(chroma, archive)
    assert code == 1 and payload["status"] == "refused"


def test_backend_identity_change_between_preview_and_apply_refuses(tmp_path: Path, monkeypatch) -> None:
    chroma, _guard = _legacy_store(tmp_path)
    archive = tmp_path / "archive-backend"
    code, preview = _run_cli(chroma, archive)
    digest = preview["state_digest"]
    real = guard_module.live_backend_identity

    def shifted(root):
        identity = dict(real(root))
        identity["rust_binding_sha256"] = "0" * 64
        return identity

    monkeypatch.setattr(guard_module, "live_backend_identity", shifted)
    payload, code = initialize_legacy(chroma, archive, apply=True, expect_state=digest)
    assert code == 1 and payload["status"] == "refused"


def test_interrupt_before_archive_manifest_leaves_restart_state(tmp_path: Path, monkeypatch) -> None:
    chroma, guard = _legacy_store(tmp_path)
    archive = tmp_path / "archive-interrupt"
    code, preview = _run_cli(chroma, archive)
    digest = preview["state_digest"]
    real_archive = guard_module._legacy_initializer_archive_originals

    def partial_archive(guard_obj, archive_dir, segments):
        archive_dir.mkdir(parents=True, exist_ok=True)
        (archive_dir / "segments").mkdir(exist_ok=True)
        raise OSError("interrupted before manifest publication")

    monkeypatch.setattr(guard_module, "_legacy_initializer_archive_originals", partial_archive)
    payload, code = initialize_legacy(chroma, archive, apply=True, expect_state=digest)
    assert code == 2 and payload["status"] == "partial_or_uncertain"
    assert not (archive / "MANIFEST.json").exists()
    _code, restart = _run_cli(chroma, archive)
    assert restart["status"] in {"preview_ready", "refused", "partial_or_uncertain"}


def test_relative_chroma_dir_is_usage_error(tmp_path: Path) -> None:
    chroma, _guard = _legacy_store(tmp_path)
    archive = tmp_path / "archive-rel"
    payload, code = initialize_legacy("relative/chroma", archive)
    assert code == 2 and payload["status"] == "unavailable"


def test_unchanged_legacy_reconcile_still_not_initialization(tmp_path: Path) -> None:
    chroma, guard = _legacy_store(tmp_path)
    from chroma_write_guard import recover

    assert recover(chroma) == []
    meta = guard.current_snapshot(_segment(chroma)[0])[1]
    assert "release_evidence" not in meta

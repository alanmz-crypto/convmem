"""Tests for bounded CG-2 source reconciliation."""

from __future__ import annotations

from pathlib import Path

import pytest

from ingest import save_processed, sha256_file
from source_reconciler import (
    ReconciliationAdmissionError,
    ReconciliationBudget,
    discover_legacy_source_drift,
    enqueue_owner_work,
    mark_reconciliation_dirty,
    pending_owner_work,
    reconciliation_state_path,
    run_reconciliation_sweep,
    run_startup_reconciliation,
)


def _cfg(tmp_path: Path, source_path: Path) -> dict:
    processed = tmp_path / "processed.json"
    return {
        "sources": {"paths": [str(source_path)]},
        "watch": {"paths": [str(source_path)]},
        "index": {
            "processed_log": str(processed),
            "chroma_dir": str(tmp_path / "chroma"),
            "generation_root": str(tmp_path / "file_generations"),
        },
    }


def test_discover_legacy_drift_when_source_changes(tmp_path: Path) -> None:
    source = tmp_path / "transcript.jsonl"
    source.write_text("v1", encoding="utf-8")
    cfg = _cfg(tmp_path, source)
    old_hash = sha256_file(str(source))
    save_processed(
        str(cfg["index"]["processed_log"]),
        {old_hash: {"path": str(source.resolve()), "chunks": 1}},
    )
    source.write_text("v2", encoding="utf-8")
    findings = discover_legacy_source_drift(cfg)
    assert len(findings) == 1
    assert findings[0].reason == "source_hash_mismatch"
    assert findings[0].recorded_hash == old_hash
    assert findings[0].observed_hash == sha256_file(str(source))


def test_sweep_queues_owner_work_and_clears_dirty(tmp_path: Path) -> None:
    source = tmp_path / "transcript.jsonl"
    source.write_text("v1", encoding="utf-8")
    cfg = _cfg(tmp_path, source)
    old_hash = sha256_file(str(source))
    save_processed(
        str(cfg["index"]["processed_log"]),
        {old_hash: {"path": str(source.resolve()), "chunks": 1}},
    )
    mark_reconciliation_dirty(cfg, "watch-root", reason="overflow_uncertainty")
    source.write_text("v2", encoding="utf-8")
    report = run_reconciliation_sweep(cfg, reason="periodic")
    assert report.findings
    assert report.queued_owner_keys
    assert pending_owner_work(cfg)
    state = reconciliation_state_path(cfg)
    assert state.exists()
    data = __import__("json").loads(state.read_text(encoding="utf-8"))
    assert data["dirty_scopes"] == []
    assert data["last_successful_sweep_at"]


def test_owner_queue_coalesces_to_latest_desired_state(tmp_path: Path) -> None:
    source = tmp_path / "transcript.jsonl"
    source.write_text("v1", encoding="utf-8")
    cfg = _cfg(tmp_path, source)
    from file_generation_contract import ownership_key
    from source_reconciler import SourceDriftFinding

    owner_key = ownership_key(str(source.resolve()))
    enqueue_owner_work(
        cfg,
        SourceDriftFinding(
            canonical_path=str(source.resolve()),
            owner_key=owner_key,
            reason="source_hash_mismatch",
            recorded_hash="old",
            observed_hash="new",
        ),
    )
    enqueue_owner_work(
        cfg,
        SourceDriftFinding(
            canonical_path=str(source.resolve()),
            owner_key=owner_key,
            reason="new_eligible_source",
            recorded_hash=None,
            observed_hash="latest",
        ),
    )
    pending = pending_owner_work(cfg)
    assert len(pending) == 1
    assert pending[0].reason == "new_eligible_source"


def test_queue_capacity_is_bounded(tmp_path: Path) -> None:
    source = tmp_path / "transcript.jsonl"
    source.write_text("v1", encoding="utf-8")
    cfg = _cfg(tmp_path, source)
    budget = ReconciliationBudget(max_pending_owners=1)
    finding = discover_legacy_source_drift(cfg)[0]
    enqueue_owner_work(cfg, finding, budget=budget)
    other = finding.__class__(
        canonical_path="/tmp/other.jsonl",
        owner_key="source:/tmp/other.jsonl",
        reason="new_eligible_source",
        recorded_hash=None,
        observed_hash="deadbeef",
    )
    with pytest.raises(ReconciliationAdmissionError):
        enqueue_owner_work(cfg, other, budget=budget)


def test_startup_reconciliation_runs_sweep(tmp_path: Path) -> None:
    source = tmp_path / "transcript.jsonl"
    source.write_text("stable", encoding="utf-8")
    cfg = _cfg(tmp_path, source)
    report = run_startup_reconciliation(cfg)
    assert report.reason == "startup"

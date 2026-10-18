"""C1-a..C1-e digest reuse and commit phase timing for issue #286 slice 1."""

# pylint: disable=protected-access,duplicate-code

from __future__ import annotations

import hashlib
import json
import time
from contextlib import contextmanager
from pathlib import Path

import pytest

from chroma_store import SUMMARIES, UNITS, ChromaStore
from incremental_jsonl import IncrementalJsonlCoordinator
from purge_locks import index_write_flock, index_write_lock_depth
from tests.incremental_jsonl_helpers import (
    apply_env,
    enable_incremental,
    install_fakes,
    isolated_env,
    write_source,
)


C1_INNER_PHASES = frozenset(
    {
        "non_source_digest",
        "before_images",
        "journal",
        "apply",
        "verify_non_source",
        "projection_fingerprint",
        "checkpoint",
        "export_reconcile",
        "dedupe",
    }
)
POST_C1_PHASES = frozenset({"processed", "cleanup"})
ALLOWED_PHASES = C1_INNER_PHASES | POST_C1_PHASES
FORBIDDEN_EVENT_KEYS = frozenset(
    {
        "path",
        "source_path",
        "transaction_id",
        "generation",
        "id",
        "ids",
        "content",
        "document",
        "prefix_sha256",
        "elapsed_seconds",
        "total_seconds",
        "setup",
        "transform",
        "provider",
    }
)


def _prepare(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, count: int = 2):
    boundary, env = isolated_env(tmp_path)
    apply_env(monkeypatch, env)
    install_fakes(monkeypatch)
    enable_incremental(boundary)
    source = write_source(boundary.root, count)
    return boundary, source


def _timing_events(stderr: str) -> list[dict]:
    events = []
    for line in stderr.splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict) and payload.get("event") == "incremental_commit_phase_timing":
            events.append(payload)
    return events


def _install_digest_counter(monkeypatch: pytest.MonkeyPatch) -> dict[str, int]:
    counts = {SUMMARIES: 0, UNITS: 0}
    original = ChromaStore.non_source_inventory_digest

    def counting(self, collection_name, source_path, **kwargs):
        counts[collection_name] = counts.get(collection_name, 0) + 1
        return original(self, collection_name, source_path, **kwargs)

    monkeypatch.setattr(ChromaStore, "non_source_inventory_digest", counting)
    return counts


def test_c1_a_no_lock_release_or_chroma_write_between_capture_and_reuse(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    boundary, source = _prepare(tmp_path, monkeypatch)
    gap = {"active": False, "writes": [], "lock_releases": [], "reuse": None, "depths": []}

    original_digest = IncrementalJsonlCoordinator._non_source_collection_digest
    original_snapshot = IncrementalJsonlCoordinator._snapshot_before_images
    original_native = ChromaStore._native
    original_flock = index_write_flock

    def wrapped_digest(self):
        result = original_digest(self)
        if not gap["depths"]:
            gap["active"] = True
        gap["depths"].append(index_write_lock_depth())
        return result

    def wrapped_snapshot(self, non_source_collections=None):
        gap["reuse"] = non_source_collections is not None
        gap["snapshot_depth"] = index_write_lock_depth()
        gap["active"] = False
        return original_snapshot(self, non_source_collections=non_source_collections)

    def wrapped_native(self, collection, operation, **kwargs):
        if gap["active"]:
            gap["writes"].append(operation)
        return original_native(self, collection, operation, **kwargs)

    @contextmanager
    def wrapped_flock(*args, **kwargs):
        with original_flock(*args, **kwargs) as lock:
            yield lock
        if gap["active"] and index_write_lock_depth() == 0:
            gap["lock_releases"].append(True)

    monkeypatch.setattr(
        IncrementalJsonlCoordinator, "_non_source_collection_digest", wrapped_digest
    )
    monkeypatch.setattr(
        IncrementalJsonlCoordinator, "_snapshot_before_images", wrapped_snapshot
    )
    monkeypatch.setattr(ChromaStore, "_native", wrapped_native)
    monkeypatch.setattr("purge_locks.index_write_flock", wrapped_flock)

    result = IncrementalJsonlCoordinator.from_isolated_boundary(
        boundary, source, enabled=True
    ).run()
    assert result.outcome == "committed"
    assert result.chunks == 1
    assert gap["reuse"] is True
    assert gap["snapshot_depth"] > 0
    assert gap["depths"]
    assert gap["depths"][0] > 0
    assert not gap["writes"]
    assert not gap["lock_releases"]


def test_c1_b_later_mutation_does_not_change_recorded_baseline(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    boundary, source = _prepare(tmp_path, monkeypatch)
    held: dict = {}

    original_snapshot = IncrementalJsonlCoordinator._snapshot_before_images

    def wrapped_snapshot(self, non_source_collections=None):
        held["arg"] = non_source_collections
        rollback = original_snapshot(
            self, non_source_collections=non_source_collections
        )
        held["rollback"] = rollback
        if non_source_collections is not None:
            non_source_collections[SUMMARIES] = {"digest": "poisoned-alias"}
        return rollback

    def crash(point: str) -> None:
        if point == "after_rollback_publish":
            raise RuntimeError("captured-baseline")

    monkeypatch.setattr(
        IncrementalJsonlCoordinator, "_snapshot_before_images", wrapped_snapshot
    )
    coordinator = IncrementalJsonlCoordinator.from_isolated_boundary(
        boundary, source, enabled=True, fault=crash
    )
    with pytest.raises(RuntimeError, match="captured-baseline"):
        coordinator.run()

    recorded = json.loads(coordinator.paths["rollback"].read_text(encoding="utf-8"))
    original = IncrementalJsonlCoordinator._copy_non_source_digest(held["rollback"]["non_source_collections"])
    assert recorded["non_source_collections"] == original
    assert recorded["non_source_collections"][SUMMARIES]["digest"] != "poisoned-alias"
    assert held["arg"][SUMMARIES]["digest"] == "poisoned-alias"
    assert held["rollback"]["non_source_collections"] is not held["arg"]

    with coordinator._session() as session:
        session.store.add_summary(
            "foreign-after-capture",
            "mutated-foreign",
            [0.1] * 8,
            {"source_path": "/other"},
        )
    live = coordinator._non_source_collection_digest()
    assert recorded["non_source_collections"] != live
    assert recorded["non_source_collections"] == original


def test_c1_c_replay_computes_fresh_digest_and_keeps_journal_sha(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    boundary, source = _prepare(tmp_path, monkeypatch)
    order: list[str] = []
    checked: list[str] = []
    snapshot_calls: list[bool] = []

    def crash(point: str) -> None:
        if point == "after_summary_upsert":
            raise RuntimeError("stop-after-journal")

    first = IncrementalJsonlCoordinator.from_isolated_boundary(
        boundary, source, enabled=True, fault=crash
    )
    with pytest.raises(RuntimeError, match="stop-after-journal"):
        first.run()
    journal_sha = hashlib.sha256(first.paths["rollback"].read_bytes()).hexdigest()
    journal_payload = json.loads(first.paths["rollback"].read_text(encoding="utf-8"))

    original_digest = IncrementalJsonlCoordinator._non_source_collection_digest
    original_snapshot = IncrementalJsonlCoordinator._snapshot_before_images
    original_apply = IncrementalJsonlCoordinator._apply_prepared
    original_require = IncrementalJsonlCoordinator._require_rollback_authority

    def wrapped_digest(self):
        order.append("digest")
        return original_digest(self)

    def wrapped_snapshot(self, non_source_collections=None):
        snapshot_calls.append(non_source_collections is not None)
        return original_snapshot(self, non_source_collections=non_source_collections)

    def wrapped_apply(self, prepared):
        order.append("apply")
        return original_apply(self, prepared)

    def wrapped_require(self, expected_sha256: str):
        checked.append(expected_sha256)
        assert hashlib.sha256(self.paths["rollback"].read_bytes()).hexdigest() == journal_sha
        return original_require(self, expected_sha256)

    monkeypatch.setattr(
        IncrementalJsonlCoordinator, "_non_source_collection_digest", wrapped_digest
    )
    monkeypatch.setattr(
        IncrementalJsonlCoordinator, "_snapshot_before_images", wrapped_snapshot
    )
    monkeypatch.setattr(IncrementalJsonlCoordinator, "_apply_prepared", wrapped_apply)
    monkeypatch.setattr(
        IncrementalJsonlCoordinator, "_require_rollback_authority", wrapped_require
    )

    replay = IncrementalJsonlCoordinator.from_isolated_boundary(
        boundary, source, enabled=True
    )
    result = replay.run()
    assert result.outcome == "committed"
    assert "digest" in order
    assert order.index("digest") < order.index("apply")
    assert not snapshot_calls
    assert journal_sha in checked
    assert journal_payload["version"] == 2


def test_c1_d_fresh_one_chunk_commit_has_exactly_two_inventory_passes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    boundary, source = _prepare(tmp_path, monkeypatch)
    counts = _install_digest_counter(monkeypatch)
    result = IncrementalJsonlCoordinator.from_isolated_boundary(
        boundary, source, enabled=True
    ).run()
    assert result.outcome == "committed"
    assert result.chunks == 1
    assert counts[SUMMARIES] == 2
    assert counts[UNITS] == 2
    events = _timing_events(capsys.readouterr().err)
    assert len(events) == 1
    assert events[0]["full_inventory_passes"] == {
        SUMMARIES: 2,
        UNITS: 2,
    }


def test_c1_d_negative_control_third_scan_fails_two_pass_budget(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    boundary, source = _prepare(tmp_path, monkeypatch)
    counts = _install_digest_counter(monkeypatch)
    original_snapshot = IncrementalJsonlCoordinator._snapshot_before_images

    def recompute(self, non_source_collections=None):
        del non_source_collections
        return original_snapshot(self, non_source_collections=None)

    monkeypatch.setattr(IncrementalJsonlCoordinator, "_snapshot_before_images", recompute)
    result = IncrementalJsonlCoordinator.from_isolated_boundary(
        boundary, source, enabled=True
    ).run()
    assert result.outcome == "committed"
    with pytest.raises(AssertionError):
        assert counts[SUMMARIES] == 2
        assert counts[UNITS] == 2
    assert counts[SUMMARIES] == 3
    assert counts[UNITS] == 3


def test_c1_e_timing_event_excludes_setup_and_does_not_double_count(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    boundary, source = _prepare(tmp_path, monkeypatch)
    import ingest

    original_summarize = ingest.summarize

    def slow_summarize(text, **kwargs):
        time.sleep(0.05)
        return original_summarize(text, **kwargs)

    monkeypatch.setattr(ingest, "summarize", slow_summarize)
    started = time.monotonic()
    result = IncrementalJsonlCoordinator.from_isolated_boundary(
        boundary, source, enabled=True
    ).run()
    elapsed = time.monotonic() - started
    assert result.outcome == "committed"
    events = _timing_events(capsys.readouterr().err)
    assert len(events) == 1
    event = events[0]
    assert event["event"] == "incremental_commit_phase_timing"
    assert FORBIDDEN_EVENT_KEYS.isdisjoint(event)
    phases = event["phases"]
    assert set(phases) <= ALLOWED_PHASES
    assert "c1_hold_seconds" not in phases
    assert "setup" not in phases
    assert "transform" not in phases
    assert "summarize" not in phases
    inner = sum(value for name, value in phases.items() if name in C1_INNER_PHASES)
    assert inner <= event["c1_hold_seconds"] + 1e-4
    assert elapsed >= 0.05
    assert event["c1_hold_seconds"] < elapsed
    assert event["full_inventory_passes"][SUMMARIES] == 2
    assert event["full_inventory_passes"][UNITS] == 2

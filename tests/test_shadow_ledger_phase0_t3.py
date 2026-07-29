"""T3: durability, lock timeout, fail-closed corruption, health visibility."""

from __future__ import annotations

import fcntl
import inspect
import json
import os
import threading
import time
from pathlib import Path
import pytest

from shadow_ledger import SHADOW_DIR_MODE, create_shadow_ledger_header
from shadow_replay import compare_touched
from shadow_sink import (
    FSYNC_DEGRADED_LATENCY_MS,
    JsonlUnitMutationSink,
    assess_shadow_status,
    ledger_has_corruption,
)


def _private_paths(tmp_path: Path) -> tuple[Path, Path]:
    shadow = tmp_path / "shadow"
    shadow.mkdir(parents=True, exist_ok=True)
    os.chmod(shadow, SHADOW_DIR_MODE)
    ledger = shadow / "ledger.jsonl"
    health = shadow / "health.json"
    create_shadow_ledger_header(
        ledger,
        activation_id="act-t3",
        ledger_identity="ledger-t3",
        starting_sequence=0,
    )
    return ledger, health


def _event_lines(ledger: Path) -> list[dict]:
    out = []
    for line in ledger.read_text().splitlines():
        if not line.strip():
            continue
        obj = json.loads(line)
        if obj.get("record_type") == "ledger_header":
            continue
        out.append(obj)
    return out


def test_two_writers_serialize_sequences(tmp_path: Path) -> None:
    ledger, health = _private_paths(tmp_path)
    errors: list[BaseException] = []

    def worker(prefix: str) -> None:
        try:
            sink = JsonlUnitMutationSink(ledger_path=ledger, health_path=health)
            for i in range(5):
                eid = sink.prepare_event_id()
                sink.observe(
                    event_id=eid,
                    operation="create",
                    stable_entity_id=f"{prefix}-{i}",
                    document=f"doc-{prefix}-{i}",
                    metadata={"source_path": "/t"},
                    deleted=False,
                )
        except Exception as exc:  # pylint: disable=broad-exception-caught
            errors.append(exc)

    threads = [
        threading.Thread(target=worker, args=("a",)),
        threading.Thread(target=worker, args=("b",)),
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert not errors
    lines = _event_lines(ledger)
    assert len(lines) == 10
    seqs = [e["sequence"] for e in lines]
    assert seqs == sorted(seqs)
    assert seqs == list(range(1, 11))
    assert len(set(seqs)) == 10


def test_truncated_tail_refuses_append(tmp_path: Path) -> None:
    ledger, health = _private_paths(tmp_path)
    sink = JsonlUnitMutationSink(ledger_path=ledger, health_path=health)
    sink.observe(
        event_id=sink.prepare_event_id(),
        operation="create",
        stable_entity_id="u1",
        document="ok",
        metadata={},
        deleted=False,
    )
    raw = ledger.read_bytes()
    ledger.write_bytes(raw[:-5])
    assert ledger_has_corruption(ledger)
    sink.observe(
        event_id=sink.prepare_event_id(),
        operation="create",
        stable_entity_id="u2",
        document="nope",
        metadata={},
        deleted=False,
    )
    health_obj = json.loads(health.read_text())
    assert health_obj.get("last_failure_class") == "truncated_tail"
    assert health_obj.get("consecutive_failures", 0) >= 1
    assert health_obj.get("status") == "corrupt"


def test_invalid_tail_refuses_append(tmp_path: Path) -> None:
    """Bounded-tail append refuses an invalid final record (no O(N) middle scan)."""
    ledger, health = _private_paths(tmp_path)
    # Append a valid event then an invalid final line.
    sink = JsonlUnitMutationSink(ledger_path=ledger, health_path=health)
    sink.observe(
        event_id="e1",
        operation="create",
        stable_entity_id="u1",
        document="ok",
        metadata={},
        deleted=False,
    )
    with open(ledger, "ab") as handle:
        handle.write(b"NOT-JSON\n")
    assert ledger_has_corruption(ledger)
    sink.observe(
        event_id=sink.prepare_event_id(),
        operation="create",
        stable_entity_id="u2",
        document="x",
        metadata={},
        deleted=False,
    )
    health_obj = json.loads(health.read_text())
    assert health_obj.get("last_failure_class") in {"invalid_tail", "invalid_middle"}
    assert health_obj.get("status") == "corrupt"
    assert "u2" not in ledger.read_text()


def test_lock_timeout_does_not_block_caller(tmp_path: Path) -> None:
    ledger, health = _private_paths(tmp_path)
    sink = JsonlUnitMutationSink(
        ledger_path=ledger,
        health_path=health,
        lock_timeout_ms=50,
        lock_timeout_warn_n=3,
    )
    held = threading.Event()
    release = threading.Event()

    def holder() -> None:
        with open(ledger, "rb+") as handle:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
            held.set()
            release.wait(2.0)
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)

    t = threading.Thread(target=holder)
    t.start()
    assert held.wait(1.0)
    start = time.monotonic()
    sink.observe(
        event_id=sink.prepare_event_id(),
        operation="create",
        stable_entity_id="miss",
        document="x",
        metadata={},
        deleted=False,
    )
    elapsed_ms = (time.monotonic() - start) * 1000
    release.set()
    t.join()
    assert elapsed_ms < 500
    health_obj = json.loads(health.read_text())
    assert health_obj.get("last_failure_class") == "lock_timeout"
    assert health_obj.get("lock_timeout_warn_threshold_n") == 3
    assert assess_shadow_status(enabled=True, health=health_obj) == "degraded"


def test_fsync_failure_uncertain_ack_retry_appends_duplicate_id(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    ledger, health = _private_paths(tmp_path)
    sink = JsonlUnitMutationSink(ledger_path=ledger, health_path=health)
    calls = {"n": 0}
    real_fsync = os.fsync

    def boom(fd: int) -> None:
        calls["n"] += 1
        # Fail only the first ledger event fsync (not parent/health).
        if calls["n"] == 1:
            raise OSError("fsync failed")
        return real_fsync(fd)

    monkeypatch.setattr(os, "fsync", boom)
    eid = sink.prepare_event_id()
    sink.observe(
        event_id=eid,
        operation="create",
        stable_entity_id="u1",
        document="x",
        metadata={},
        deleted=False,
    )
    health_obj = json.loads(health.read_text())
    assert health_obj.get("last_failure_class") == "uncertain_ack"
    # Retry with same event_id appends another complete event / next sequence.
    sink.observe(
        event_id=eid,
        operation="create",
        stable_entity_id="u1",
        document="x",
        metadata={},
        deleted=False,
    )
    lines = _event_lines(ledger)
    matching = [e for e in lines if e.get("event_id") == eid]
    assert len(matching) == 2
    assert matching[0]["sequence"] != matching[1]["sequence"]
    assert matching[1]["sequence"] == matching[0]["sequence"] + 1


def test_first_create_mode_0600(tmp_path: Path) -> None:
    ledger, health = _private_paths(tmp_path)
    assert (ledger.stat().st_mode & 0o777) == 0o600
    sink = JsonlUnitMutationSink(ledger_path=ledger, health_path=health)
    sink.observe(
        event_id=sink.prepare_event_id(),
        operation="create",
        stable_entity_id="u1",
        document="x",
        metadata={},
        deleted=False,
    )
    assert (ledger.stat().st_mode & 0o777) == 0o600
    assert (health.stat().st_mode & 0o777) == 0o600


def test_append_latency_marked_degraded(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    ledger, health = _private_paths(tmp_path)
    sink = JsonlUnitMutationSink(
        ledger_path=ledger,
        health_path=health,
        degraded_latency_ms=FSYNC_DEGRADED_LATENCY_MS,
    )
    clock = {"t": 1000.0}

    def mono() -> float:
        clock["t"] += 0.6
        return clock["t"]

    monkeypatch.setattr(time, "monotonic", mono)
    sink.observe(
        event_id=sink.prepare_event_id(),
        operation="create",
        stable_entity_id="u1",
        document="x",
        metadata={},
        deleted=False,
    )
    health_obj = json.loads(health.read_text())
    assert health_obj.get("append_degraded") is True
    assert health_obj.get("last_append_latency_ms", 0) > FSYNC_DEGRADED_LATENCY_MS
    assert assess_shadow_status(enabled=True, health=health_obj) == "degraded"


def test_emit_order_after_chroma_no_chroma_lock_while_shadow() -> None:
    """V4a: ChromaStore emits shadow only after upsert; sink never touches Chroma locks."""
    from chroma_store import ChromaStore

    src = inspect.getsource(ChromaStore.add_unit)
    upsert_at = src.index("upsert")
    emit_at = src.index("_emit_shadow")
    assert upsert_at < emit_at
    sink_src = inspect.getsource(JsonlUnitMutationSink._append_event)  # pylint: disable=protected-access
    assert "chromadb" not in sink_src
    assert "PersistentClient" not in sink_src


def test_post_chroma_pre_shadow_gap_via_comparison() -> None:
    """V4j: missing shadow event is visible as missing-in-shadow; no auto-heal claim."""
    findings = compare_touched(
        shadow_final={},
        chroma_units={"u1": {"document": "live", "metadata": {"k": 1}}},
        touched_ids={"u1"},
    )
    assert any(f["category"] == "missing-in-shadow" for f in findings)


def test_assess_shadow_status_vocabulary() -> None:
    assert assess_shadow_status(enabled=False) == "disabled"
    assert assess_shadow_status(enabled=True, health={}) == "healthy"
    assert (
        assess_shadow_status(
            enabled=True, health={"append_degraded": True}
        )
        == "degraded"
    )
    assert (
        assess_shadow_status(enabled=True, ledger_corrupt=True) == "corrupt"
    )
    assert (
        assess_shadow_status(enabled=True, baseline_mismatch=True)
        == "baseline_mismatch"
    )


def test_doctor_shadow_disabled_by_default() -> None:
    from doctor import _check_shadow_ledger

    check = _check_shadow_ledger({"index": {"chroma_dir": "/tmp/x"}})
    assert check.ok
    assert "disabled" in check.detail


def test_checkpoint_does_not_advance_past_corruption(tmp_path: Path) -> None:
    """V4i bridge: replay projector stops; checkpoint last good event only."""
    from shadow_replay import run_disposable_replay
    from shadow_ledger import projection_state_hash, sha256_canonical

    prod = tmp_path / "prod"
    prod.mkdir()
    meta = {"source_path": "/t"}
    ev = {
        "event_id": "e1",
        "sequence": 1,
        "stable_entity_id": "u1",
        "post_state": {"document": "ok", "metadata": meta, "deleted": False},
        "document_hash": sha256_canonical("ok"),
        "state_hash": projection_state_hash(
            stable_entity_id="u1", deleted=False, document="ok", metadata=meta
        ),
        "embed_model": "unknown",
        "embed_dims": 8,
    }
    ledger = tmp_path / "ledger.jsonl"
    ledger.write_text(json.dumps(ev) + "\n{bad\n", encoding="utf-8")
    result = run_disposable_replay(
        ledger_path=ledger,
        replay_root=tmp_path / "replay",
        production_chroma_root=prod,
        mode="stub",
        production_units={},
        touched_ids={"u1"},
    )
    assert result.corrupt_at_line == 2
    assert result.checkpoint.get("last_event_id") == "e1"
    assert result.checkpoint.get("status") == "stopped_corrupt"

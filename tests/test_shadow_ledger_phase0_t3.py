"""T3: durability, lock timeout, fail-closed corruption."""

from __future__ import annotations

import fcntl
import json
import os
import threading
import time
from pathlib import Path

import pytest

from shadow_sink import JsonlUnitMutationSink


def test_two_writers_serialize_sequences(tmp_path: Path) -> None:
    ledger = tmp_path / "ledger.jsonl"
    health = tmp_path / "health.json"
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
        except BaseException as exc:
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
    lines = [json.loads(l) for l in ledger.read_text().splitlines() if l.strip()]
    assert len(lines) == 10
    seqs = [e["sequence"] for e in lines]
    assert seqs == sorted(seqs)
    assert len(set(seqs)) == 10


def test_truncated_tail_refuses_append(tmp_path: Path) -> None:
    ledger = tmp_path / "ledger.jsonl"
    health = tmp_path / "health.json"
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
    sink.observe(
        event_id=sink.prepare_event_id(),
        operation="create",
        stable_entity_id="u2",
        document="nope",
        metadata={},
        deleted=False,
    )
    health_obj = json.loads(health.read_text())
    assert health_obj.get("last_failure_class")
    assert health_obj.get("consecutive_failures", 0) >= 1


def test_lock_timeout_does_not_block_caller(tmp_path: Path) -> None:
    ledger = tmp_path / "ledger.jsonl"
    health = tmp_path / "health.json"
    sink = JsonlUnitMutationSink(
        ledger_path=ledger,
        health_path=health,
        lock_timeout_ms=50,
        lock_timeout_warn_n=3,
    )
    held = threading.Event()
    release = threading.Event()

    def holder() -> None:
        ledger.parent.mkdir(parents=True, exist_ok=True)
        with open(ledger, "a+", encoding="utf-8") as handle:
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


def test_fsync_failure_does_not_raise_to_caller(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    ledger = tmp_path / "ledger.jsonl"
    health = tmp_path / "health.json"
    sink = JsonlUnitMutationSink(ledger_path=ledger, health_path=health)
    calls = {"n": 0}
    real_fsync = os.fsync

    def boom(fd: int) -> None:
        calls["n"] += 1
        # Fail the ledger file fsync; allow later health persist fsync.
        if calls["n"] == 1:
            raise OSError("fsync failed")
        return real_fsync(fd)

    monkeypatch.setattr(os, "fsync", boom)
    # Must not raise — Chroma caller would already have succeeded.
    sink.observe(
        event_id=sink.prepare_event_id(),
        operation="create",
        stable_entity_id="u1",
        document="x",
        metadata={},
        deleted=False,
    )
    assert calls["n"] >= 1
    if health.is_file():
        health_obj = json.loads(health.read_text())
        assert health_obj.get("consecutive_failures", 0) >= 1
        assert health_obj.get("last_failure_class")
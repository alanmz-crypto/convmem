"""Replay-safe incremental JSONL state machine for scratch evidence only.

This is deliberately not wired into production ingest or the watcher. It
projects one supported Kiro JSONL source into a scratch-local durable JSON
store so fault windows can be exercised without production resources.
"""

# pylint: disable=too-many-instance-attributes

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable

from adapters.detect import detect_format, get_parser
from scratch_jsonl_prototype.isolation import (
    IsolationViolation,
    ScratchBoundary,
    ScratchPidLock,
)


class SourceMoved(RuntimeError):
    """The selected source prefix changed before publication."""


class InjectedCrash(RuntimeError):
    """In-process stand-in for an abrupt subprocess exit."""


FaultHook = Callable[[str], None]

DURABLE_TRANSITIONS = (
    "fallback_marker",
    "generation_prepare",
    "upsert",
    "publish",
    "prune",
    "checkpoint_prepare",
    "checkpoint_publish",
    "fallback_cleanup",
    "snapshot_cleanup",
    "lock_acquire",
    "lock_release",
)


@dataclass
class RunEvidence:
    mode: str
    fallback_reason: str | None
    adapter_format: str
    selected_boundary: int
    records: int
    frontier_record: int
    transform_calls: int
    reused_rows: int
    max_units_in_flight: int
    active_generation: str
    recovered_stale_lock: bool


@dataclass
class _Snapshot:
    raw: bytes
    boundary: int
    prefix_sha256: str
    stat_identity: dict[str, int]
    messages: list[dict]
    byte_ranges: list[tuple[int, int]]


def _sha(value: bytes | str) -> str:
    if isinstance(value, str):
        value = value.encode("utf-8")
    return hashlib.sha256(value).hexdigest()


def _read_json(path: Path, default: dict) -> dict:
    if not path.is_file():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def _fsync_dir(path: Path) -> None:
    fd = os.open(path, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _atomic_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    with tmp.open("w", encoding="utf-8") as handle:
        json.dump(value, handle, sort_keys=True, separators=(",", ":"))
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(tmp, path)
    _fsync_dir(path.parent)


class ScratchIncrementalJsonl:
    """One-adapter, one-source scratch projection with explicit commit state."""

    def __init__(
        self,
        boundary: ScratchBoundary,
        source: Path | str,
        *,
        transform_fingerprint: str = "deterministic-transform-v1",
        chunk_records: int = 2,
        fault: FaultHook | None = None,
        projection: Any | None = None,
    ):
        ScratchBoundary.require_fake_provider("deterministic-fake")
        if chunk_records <= 0:
            raise ValueError("chunk_records must be positive")
        self.boundary = boundary
        self.source = boundary.resolve_mutable(source, label="source fixture")
        self.transform_fingerprint = transform_fingerprint
        self.chunk_records = chunk_records
        self.fault = fault or (lambda _point: None)
        # Optional scratch projection.  Production callers cannot reach this
        # prototype; the adapter is used only by the real-Chroma evidence pass.
        self.projection = projection

        candidates = {
            "projection": "chroma/prototype-projection.json",
            "checkpoint": "checkpoints/jsonl-checkpoint.json",
            "fallback": "checkpoints/fallback-in-progress.json",
            "snapshot": "runtime/sess_snapshot/messages.jsonl",
            "export": "exports/knowledge_units.jsonl",
            "inventory": "inventory/source.json",
            "lock": "locks/jsonl-prototype.lock",
        }
        # All mutable resource paths are checked before any construction.
        self.paths = {
            name: boundary.resolve_mutable(path, label=name)
            for name, path in candidates.items()
        }

    def _transition(self, name: str, action: Callable[[], None]) -> None:
        self.fault(f"before_{name}")
        action()
        self.fault(f"after_{name}")

    def _source_identity(self) -> str:
        return _sha(f"kiro-jsonl:{self.source}")

    def _select_snapshot(self) -> _Snapshot:
        if detect_format(self.source) != "jsonl_kiro_session":
            raise IsolationViolation("prototype supports only jsonl_kiro_session")
        parser = get_parser(self.source)
        if parser is None or parser.__module__ != "adapters.kiro_session_jsonl":
            raise IsolationViolation("normal adapter dispatch did not select Kiro JSONL")

        with self.source.open("rb") as handle:
            before = os.fstat(handle.fileno())
            raw = handle.read(before.st_size)
            after = os.fstat(handle.fileno())
        if (before.st_dev, before.st_ino) != (after.st_dev, after.st_ino):
            raise SourceMoved("source identity changed while selecting high-water point")
        boundary = raw.rfind(b"\n") + 1
        complete = raw[:boundary]

        snapshot_path = self.paths["snapshot"]
        snapshot_path.parent.mkdir(parents=True, exist_ok=True)
        snapshot_path.write_bytes(complete)
        sibling_meta = self.source.parent / "session.json"
        if sibling_meta.is_file():
            (snapshot_path.parent / "session.json").write_bytes(sibling_meta.read_bytes())
        messages = parser(str(snapshot_path))

        ranges: list[tuple[int, int]] = []
        offset = 0
        for line in complete.splitlines(keepends=True):
            end = offset + len(line)
            try:
                record = json.loads(line)
            except (json.JSONDecodeError, UnicodeDecodeError):
                record = None
            payload = record.get("payload") if isinstance(record, dict) else None
            if (
                isinstance(payload, dict)
                and payload.get("type") in ("user", "assistant")
                and isinstance(payload.get("content"), str)
                and payload["content"].strip()
            ):
                ranges.append((offset, end))
            offset = end
        if len(ranges) != len(messages):
            raise RuntimeError("adapter output and byte-boundary scan disagree")
        return _Snapshot(
            raw=complete,
            boundary=boundary,
            prefix_sha256=_sha(complete),
            stat_identity={"device": before.st_dev, "inode": before.st_ino},
            messages=messages,
            byte_ranges=ranges,
        )

    def _continuity_reason(self, checkpoint: dict, snapshot: _Snapshot) -> str | None:
        if not checkpoint:
            return "initial_full"
        if checkpoint.get("source_identity") != self._source_identity():
            return "source_identity_changed"
        if checkpoint.get("transform_fingerprint") != self.transform_fingerprint:
            return "transform_fingerprint_changed"
        if (checkpoint.get("generation_identity") or {}) != snapshot.stat_identity:
            return "source_replaced_or_rotated"
        prior_boundary = int(checkpoint.get("complete_boundary", 0))
        if snapshot.boundary < prior_boundary:
            return "source_truncated"
        with self.source.open("rb") as handle:
            prior_prefix = handle.read(prior_boundary)
        if _sha(prior_prefix) != checkpoint.get("prefix_sha256"):
            return "validated_prefix_mutated"
        return None

    def _validate_selected_prefix(self, snapshot: _Snapshot) -> None:
        current = self.source.stat()
        if (current.st_dev, current.st_ino) != (
            snapshot.stat_identity["device"],
            snapshot.stat_identity["inode"],
        ):
            raise SourceMoved("source replaced before publication")
        if current.st_size < snapshot.boundary:
            raise SourceMoved("source truncated before publication")
        with self.source.open("rb") as handle:
            selected = handle.read(snapshot.boundary)
        if _sha(selected) != snapshot.prefix_sha256:
            raise SourceMoved("selected source prefix changed before publication")

    def _frontier(self, checkpoint: dict, fallback: str | None) -> int:
        if fallback is not None:
            return 0
        old_count = int(checkpoint.get("record_count", 0))
        return (old_count // self.chunk_records) * self.chunk_records

    def _row(self, snapshot: _Snapshot, start: int, stop: int) -> dict:
        byte_start = snapshot.byte_ranges[start][0]
        byte_end = snapshot.byte_ranges[stop - 1][1]
        rendered = "\n".join(
            f"{item['role']}: {item['content'].strip()}"
            for item in snapshot.messages[start:stop]
        )
        unit_id = _sha(
            f"scratch-unit-v1:{self._source_identity()}:{byte_start}:"
            f"{self.transform_fingerprint}"
        )
        return {
            "id": unit_id,
            "document": f"deterministic-summary:{_sha(rendered)[:24]}",
            "metadata": {
                "source_path": str(self.source),
                "source_identity": self._source_identity(),
                "adapter_format": "jsonl_kiro_session",
                "transform_fingerprint": self.transform_fingerprint,
                "record_start": start,
                "record_end": stop,
                "byte_start": byte_start,
                "byte_end": byte_end,
                "input_sha256": _sha(snapshot.raw[byte_start:byte_end]),
                "deterministic_fake": True,
            },
        }

    def _checkpoint_value(
        self, snapshot: _Snapshot, generation: str, fallback_reason: str | None
    ) -> dict:
        return {
            "version": 1,
            "commit_state": "complete",
            "adapter_format": "jsonl_kiro_session",
            "source_identity": self._source_identity(),
            "generation_identity": snapshot.stat_identity,
            "complete_boundary": snapshot.boundary,
            "prefix_sha256": snapshot.prefix_sha256,
            "transform_fingerprint": self.transform_fingerprint,
            "record_count": len(snapshot.messages),
            "active_generation": generation,
            "fallback_reason": fallback_reason,
        }

    def active_projection(self) -> dict:
        state = _read_json(
            self.paths["projection"], {"active_generation": "", "generations": {}}
        )
        active = state.get("active_generation", "")
        generation = (state.get("generations") or {}).get(active, {})
        rows = generation.get("rows") or {}
        return {
            "active_generation": active,
            "rows": [rows[key] for key in sorted(rows)],
        }

    def checkpoint(self) -> dict:
        return _read_json(self.paths["checkpoint"], {})

    def run(self) -> RunEvidence:
        self.fault("before_lock_acquire")
        lock = ScratchPidLock(self.boundary, self.paths["lock"])
        recovered = lock.acquire()
        self.fault("after_lock_acquire")
        try:
            return self._run_locked(recovered)
        finally:
            self.fault("before_lock_release")
            lock.release()
            self.fault("after_lock_release")

    def _run_locked(self, recovered: bool) -> RunEvidence:
        snapshot = self._select_snapshot()
        checkpoint = self.checkpoint()
        fallback_reason = self._continuity_reason(checkpoint, snapshot)
        if (
            fallback_reason is None
            and snapshot.boundary == int(checkpoint.get("complete_boundary", -1))
            and len(snapshot.messages) == int(checkpoint.get("record_count", -1))
        ):
            if self.projection is not None:
                # Repair a torn projection without recomputing transforms.
                rows = []
                for start in range(0, len(snapshot.messages), self.chunk_records):
                    rows.append(self._row(snapshot, start, min(start + self.chunk_records, len(snapshot.messages))))
                self.fault("before_chroma_repair")
                self.projection.reconcile(rows, checkpoint["active_generation"])
                self.fault("after_chroma_repair")
            if self.paths["fallback"].exists():
                self._transition(
                    "fallback_cleanup",
                    lambda: self.paths["fallback"].unlink(missing_ok=True),
                )
            self._transition(
                "snapshot_cleanup", lambda: self.paths["snapshot"].unlink(missing_ok=True)
            )
            return RunEvidence(
                mode="unchanged",
                fallback_reason=None,
                adapter_format="jsonl_kiro_session",
                selected_boundary=snapshot.boundary,
                records=len(snapshot.messages),
                frontier_record=len(snapshot.messages),
                transform_calls=0,
                reused_rows=len(self.active_projection()["rows"]),
                max_units_in_flight=0,
                active_generation=checkpoint["active_generation"],
                recovered_stale_lock=recovered,
            )

        mode = "full_rebuild_fallback" if fallback_reason else "incremental"
        if fallback_reason:
            marker = {
                "reason": fallback_reason,
                "source_identity": self._source_identity(),
                "selected_boundary": snapshot.boundary,
            }
            self._transition(
                "fallback_marker", lambda: _atomic_json(self.paths["fallback"], marker)
            )
        frontier = self._frontier(checkpoint, fallback_reason)
        state = _read_json(
            self.paths["projection"], {"active_generation": "", "generations": {}}
        )
        old_projection = self.active_projection()
        reused = {
            row["id"]: row
            for row in old_projection["rows"]
            if int(row["metadata"]["record_start"]) < frontier
        }
        generation = _sha(
            f"scratch-generation-v1:{self._source_identity()}:"
            f"{snapshot.prefix_sha256}:{snapshot.boundary}:"
            f"{self.transform_fingerprint}"
        )
        existing_generation = (state.get("generations") or {}).get(generation, {})
        already_published = (
            state.get("active_generation") == generation
            and existing_generation.get("status") == "active"
        )

        def prepare() -> None:
            state.setdefault("generations", {})[generation] = {
                "status": "staging",
                "rows": dict(reused),
            }
            _atomic_json(self.paths["projection"], state)

        transform_calls = 0
        max_units = 0
        if not already_published:
            self._transition("generation_prepare", prepare)
            start = frontier
            while start < len(snapshot.messages):
                stop = min(start + self.chunk_records, len(snapshot.messages))
                row = self._row(snapshot, start, stop)
                transform_calls += 1
                max_units = max(max_units, 1)

                def upsert(row_value=row) -> None:  # pylint: disable=dangerous-default-value
                    state["generations"][generation]["rows"][row_value["id"]] = row_value
                    _atomic_json(self.paths["projection"], state)
                    if self.projection is not None:
                        self.fault("before_chroma_upsert")
                        self.projection.upsert([row_value], generation)
                        self.fault("after_chroma_upsert")

                self._transition(f"upsert_{start}", upsert)
                start = stop

            self._validate_selected_prefix(snapshot)

            def publish() -> None:
                # Revalidate after before_publish and immediately before authority.
                self._validate_selected_prefix(snapshot)
                state["generations"][generation]["status"] = "active"
                state["active_generation"] = generation
                _atomic_json(self.paths["projection"], state)

            self._transition("publish", publish)

        def prune() -> None:
            state["generations"] = {generation: state["generations"][generation]}
            _atomic_json(self.paths["projection"], state)
            if self.projection is not None:
                authoritative_rows = list(state["generations"][generation]["rows"].values())
                self.projection.reconcile(authoritative_rows, generation)
                self.fault("before_chroma_prune")
                self.projection.prune(
                    generation=generation,
                    keep_ids=set(state["generations"][generation]["rows"]),
                )
                self.fault("after_chroma_prune")

        self._transition("prune", prune)
        checkpoint_value = self._checkpoint_value(snapshot, generation, fallback_reason)
        prepared = self.paths["checkpoint"].with_name(
            self.paths["checkpoint"].name + ".next"
        )
        self._transition(
            "checkpoint_prepare", lambda: _atomic_json(prepared, checkpoint_value)
        )

        def publish_checkpoint() -> None:
            os.replace(prepared, self.paths["checkpoint"])
            _fsync_dir(self.paths["checkpoint"].parent)

        self._transition("checkpoint_publish", publish_checkpoint)
        if fallback_reason:
            self._transition(
                "fallback_cleanup", lambda: self.paths["fallback"].unlink(missing_ok=True)
            )
        self._transition(
            "snapshot_cleanup", lambda: self.paths["snapshot"].unlink(missing_ok=True)
        )
        return RunEvidence(
            mode=mode,
            fallback_reason=fallback_reason,
            adapter_format="jsonl_kiro_session",
            selected_boundary=snapshot.boundary,
            records=len(snapshot.messages),
            frontier_record=frontier,
            transform_calls=transform_calls,
            reused_rows=len(reused),
            max_units_in_flight=max_units,
            active_generation=generation,
            recovered_stale_lock=recovered,
        )


def crash_at(point: str) -> FaultHook:
    """Return an in-process fault hook useful for focused unit checks."""
    def inject(observed: str) -> None:
        if observed == point:
            raise InjectedCrash(point)

    return inject


def evidence_dict(value: RunEvidence) -> dict:
    return asdict(value)

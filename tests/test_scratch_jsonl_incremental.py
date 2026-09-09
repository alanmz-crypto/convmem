"""Fault/replay matrix for the bounded scratch JSONL prototype."""

# pylint: disable=duplicate-code

from __future__ import annotations

import json
import os
import subprocess
import sys
import tracemalloc
from pathlib import Path

import pytest

from scratch_jsonl_prototype.engine import (
    DURABLE_TRANSITIONS,
    SourceMoved,
    ScratchIncrementalJsonl,
)
from scratch_jsonl_prototype.isolation import (
    ScratchBoundary,
    create_fresh_root,
    sanitized_worker_env,
)


WORKER = Path(__file__).with_name("scratch_jsonl_isolation_worker.py")
FP1 = "deterministic-transform-v1"


def _record(index: int, *, content: str | None = None) -> bytes:
    row = {
        "timestamp": f"2026-09-09T00:00:{index % 60:02d}Z",
        "payload": {
            "type": "user" if index % 2 == 0 else "assistant",
            "content": content or f"message-{index:05d}",
        },
    }
    return (json.dumps(row, sort_keys=True) + "\n").encode()


def _case(tmp_path: Path, count: int = 2) -> tuple[ScratchBoundary, Path, str]:
    root, token = create_fresh_root(tmp_path)
    source = root / "sources" / "hash" / "sess_scratch" / "messages.jsonl"
    source.parent.mkdir(parents=True)
    source.write_bytes(b"".join(_record(i) for i in range(count)))
    (source.parent / "session.json").write_text(
        json.dumps(
            {
                "id": "sess_scratch",
                "workspacePaths": [str(root / "workspace")],
                "title": "scratch",
            }
        ),
        encoding="utf-8",
    )
    return ScratchBoundary(root, token), source, token


def _append(source: Path, *indices: int) -> None:
    with source.open("ab") as handle:
        for index in indices:
            handle.write(_record(index))


def _worker(
    boundary: ScratchBoundary,
    token: str,
    source: Path,
    *,
    fingerprint: str = FP1,
    fault: str = "",
) -> subprocess.CompletedProcess[str]:
    args = [sys.executable, "-I", str(WORKER), "run", str(source), fingerprint]
    if fault:
        args.append(fault)
    return subprocess.run(
        args,
        cwd=boundary.root,
        env=sanitized_worker_env(boundary.root, token),
        close_fds=True,
        start_new_session=True,
        capture_output=True,
        text=True,
        check=False,
    )


def _worker_json(*args, **kwargs) -> dict:
    result = _worker(*args, **kwargs)
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


def _authority(payload: dict) -> dict:
    checkpoint = payload["checkpoint"]
    return {
        "rows": payload["projection"]["rows"],
        "checkpoint": {
            key: checkpoint[key]
            for key in (
                "version",
                "commit_state",
                "adapter_format",
                "source_identity",
                "generation_identity",
                "complete_boundary",
                "prefix_sha256",
                "transform_fingerprint",
                "record_count",
                "active_generation",
            )
        },
    }


def test_initial_append_partial_completion_and_exact_chunk_boundary(
    tmp_path: Path,
) -> None:
    boundary, source, _token = _case(tmp_path, 3)
    engine = ScratchIncrementalJsonl(boundary, source)
    initial = engine.run()
    assert initial.mode == "full_rebuild_fallback"
    assert initial.fallback_reason == "initial_full"
    assert initial.adapter_format == "jsonl_kiro_session"
    assert initial.transform_calls == 2

    _append(source, 3)
    single = engine.run()
    assert (single.mode, single.frontier_record, single.transform_calls) == (
        "incremental",
        2,
        1,
    )
    _append(source, 4, 5, 6, 7)
    multiple = engine.run()
    assert (multiple.frontier_record, multiple.transform_calls) == (4, 2)

    partial = _record(8).rstrip(b"\n")[:-5]
    with source.open("ab") as handle:
        handle.write(partial)
    deferred = engine.run()
    assert deferred.mode == "unchanged"
    assert deferred.transform_calls == 0
    with source.open("ab") as handle:
        handle.write(_record(8).rstrip(b"\n")[-5:] + b"\n")
    completed = engine.run()
    assert completed.records == 9
    assert completed.transform_calls == 1

    boundary2, source2, _ = _case(tmp_path, 2)
    exact = ScratchIncrementalJsonl(boundary2, source2)
    exact.run()
    _append(source2, 2, 3)
    exact_append = exact.run()
    assert (exact_append.frontier_record, exact_append.transform_calls) == (2, 1)


@pytest.mark.parametrize(
    ("mutation", "fingerprint", "reason"),
    [
        ("prefix", FP1, "validated_prefix_mutated"),
        ("truncate", FP1, "source_truncated"),
        ("rotation", FP1, "source_replaced_or_rotated"),
        ("replacement", FP1, "source_replaced_or_rotated"),
        ("none", "deterministic-transform-v2", "transform_fingerprint_changed"),
    ],
)
def test_continuity_failures_take_explicit_full_rebuild_fallback(
    tmp_path: Path, mutation: str, fingerprint: str, reason: str
) -> None:
    boundary, source, _token = _case(tmp_path, 4)
    ScratchIncrementalJsonl(boundary, source).run()
    original = source.read_bytes()
    if mutation == "prefix":
        source.write_bytes(original.replace(b"message-00000", b"changed-00000", 1))
    elif mutation == "truncate":
        source.write_bytes(b"".join(_record(i) for i in range(2)))
    elif mutation == "rotation":
        rotated = source.with_name("rotated.jsonl")
        rotated.write_bytes(original + _record(4))
        os.replace(rotated, source)
    elif mutation == "replacement":
        source.unlink()
        source.write_bytes(original)

    run = ScratchIncrementalJsonl(
        boundary, source, transform_fingerprint=fingerprint
    ).run()
    assert run.mode == "full_rebuild_fallback"
    assert run.fallback_reason == reason
    assert run.frontier_record == 0
    assert not ScratchIncrementalJsonl(
        boundary, source, transform_fingerprint=fingerprint
    ).paths["fallback"].exists()


def test_source_growth_after_highwater_is_deferred_and_prefix_mutation_fails_closed(
    tmp_path: Path,
) -> None:
    boundary, source, _token = _case(tmp_path, 2)
    appended = {"done": False}

    def append_before_publish(point: str) -> None:
        if point == "before_publish" and not appended["done"]:
            appended["done"] = True
            _append(source, 2)

    first = ScratchIncrementalJsonl(boundary, source, fault=append_before_publish)
    run = first.run()
    assert run.records == 2
    assert first.checkpoint()["record_count"] == 2
    catchup = ScratchIncrementalJsonl(boundary, source).run()
    assert catchup.records == 3

    old_projection = first.active_projection()
    old_checkpoint = first.checkpoint()
    _append(source, 3)
    changed = {"done": False}

    def mutate_prefix(point: str) -> None:
        if point == "before_publish" and not changed["done"]:
            changed["done"] = True
            data = source.read_bytes()
            source.write_bytes(data.replace(b"message-00000", b"changed-00000", 1))

    with pytest.raises(SourceMoved):
        ScratchIncrementalJsonl(boundary, source, fault=mutate_prefix).run()
    assert first.active_projection() == old_projection
    assert first.checkpoint() == old_checkpoint
    recovered = ScratchIncrementalJsonl(boundary, source).run()
    assert recovered.fallback_reason == "validated_prefix_mutated"


def test_incremental_matches_clean_full_rebuild_without_normalising_authority(
    tmp_path: Path,
) -> None:
    boundary, source, token = _case(tmp_path, 3)
    _worker_json(boundary, token, source)
    _append(source, 3, 4, 5, 6)
    incremental = _worker_json(boundary, token, source)
    authority_incremental = _authority(incremental)
    assert len({row["id"] for row in authority_incremental["rows"]}) == len(
        authority_incremental["rows"]
    )

    engine = ScratchIncrementalJsonl(boundary, source)
    engine.paths["projection"].unlink()
    engine.paths["checkpoint"].unlink()
    clean = _worker_json(boundary, token, source)
    assert _authority(clean) == authority_incremental


def test_frontier_counters_and_units_in_flight_memory_evidence(tmp_path: Path) -> None:
    boundary, source, _token = _case(tmp_path, 1000)
    tracemalloc.start()
    engine = ScratchIncrementalJsonl(boundary, source, chunk_records=20)
    initial = engine.run()
    _current, peak_initial = tracemalloc.get_traced_memory()
    tracemalloc.reset_peak()
    _append(source, 1000)
    incremental = engine.run()
    _current, peak_incremental = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    assert initial.transform_calls == 50
    assert incremental.frontier_record == 1000
    assert incremental.transform_calls == 1
    assert incremental.max_units_in_flight == 1
    assert incremental.reused_rows == 50
    assert peak_incremental <= peak_initial * 2
    assert engine.run().transform_calls == 0


INCREMENTAL_CRASH_POINTS = (
    "before_lock_acquire",
    "after_lock_acquire",
    "before_generation_prepare",
    "after_generation_prepare",
    "before_upsert_2",
    "after_upsert_2",
    "before_upsert_4",
    "after_upsert_4",
    "before_publish",
    "after_publish",
    "before_prune",
    "after_prune",
    "before_checkpoint_prepare",
    "after_checkpoint_prepare",
    "before_checkpoint_publish",
    "after_checkpoint_publish",
    "before_snapshot_cleanup",
    "after_snapshot_cleanup",
    "before_lock_release",
    "after_lock_release",
)


@pytest.mark.parametrize("point", INCREMENTAL_CRASH_POINTS)
def test_subprocess_crash_replay_converges_at_every_incremental_transition(
    tmp_path: Path, point: str
) -> None:
    boundary, source, token = _case(tmp_path, 2)
    _worker_json(boundary, token, source)
    _append(source, 2, 3, 4, 5)
    crashed = _worker(boundary, token, source, fault=point)
    assert crashed.returncode == 86
    retry = _worker_json(boundary, token, source)
    assert retry["checkpoint"]["commit_state"] == "complete"
    assert retry["checkpoint"]["record_count"] == 6
    assert len(retry["projection"]["rows"]) == 3
    assert len({row["id"] for row in retry["projection"]["rows"]}) == 3


FALLBACK_CRASH_POINTS = (
    "before_fallback_marker",
    "after_fallback_marker",
    "before_generation_prepare",
    "after_generation_prepare",
    "before_upsert_0",
    "after_upsert_0",
    "before_publish",
    "after_publish",
    "before_prune",
    "after_prune",
    "before_checkpoint_prepare",
    "after_checkpoint_prepare",
    "before_checkpoint_publish",
    "after_checkpoint_publish",
    "before_fallback_cleanup",
    "after_fallback_cleanup",
)


def test_fault_matrix_covers_both_sides_of_every_durable_transition() -> None:
    covered = set(INCREMENTAL_CRASH_POINTS) | set(FALLBACK_CRASH_POINTS)
    for transition in DURABLE_TRANSITIONS:
        if transition == "upsert":
            assert any(point.startswith("before_upsert_") for point in covered)
            assert any(point.startswith("after_upsert_") for point in covered)
        else:
            assert f"before_{transition}" in covered
            assert f"after_{transition}" in covered


@pytest.mark.parametrize("point", FALLBACK_CRASH_POINTS)
def test_subprocess_crash_replay_converges_during_full_rebuild_fallback(
    tmp_path: Path, point: str
) -> None:
    boundary, source, token = _case(tmp_path, 4)
    _worker_json(boundary, token, source)
    source.write_bytes(
        source.read_bytes().replace(b"message-00000", b"changed-00000", 1)
    )
    crashed = _worker(boundary, token, source, fault=point)
    assert crashed.returncode == 86
    retry = _worker_json(boundary, token, source)
    assert retry["checkpoint"]["record_count"] == 4
    assert retry["checkpoint"]["fallback_reason"] == "validated_prefix_mutated"
    assert len(retry["projection"]["rows"]) == 2
    assert not ScratchIncrementalJsonl(boundary, source).paths["fallback"].exists()


def test_repeated_crash_after_publish_never_demotes_active_generation(
    tmp_path: Path,
) -> None:
    boundary, source, token = _case(tmp_path, 2)
    initial = _worker_json(boundary, token, source)
    _append(source, 2, 3, 4, 5)
    assert _worker(
        boundary, token, source, fault="after_publish"
    ).returncode == 86
    # Replay recognizes the already-published deterministic generation and
    # cannot hit/demote it through generation preparation a second time.
    second = _worker(
        boundary, token, source, fault="after_generation_prepare"
    )
    assert second.returncode == 0
    published = json.loads(second.stdout)
    assert published["checkpoint"]["record_count"] == 6
    assert published["projection"]["active_generation"] != (
        initial["projection"]["active_generation"]
    )


def test_torn_checkpoint_candidate_is_ignored_and_stale_lock_recovers(
    tmp_path: Path,
) -> None:
    boundary, source, token = _case(tmp_path, 2)
    _worker_json(boundary, token, source)
    _append(source, 2, 3)
    crashed = _worker(
        boundary, token, source, fault="after_checkpoint_prepare"
    )
    assert crashed.returncode == 86
    engine = ScratchIncrementalJsonl(boundary, source)
    candidate = engine.paths["checkpoint"].with_name(
        engine.paths["checkpoint"].name + ".next"
    )
    candidate.write_text("{", encoding="utf-8")
    retry = _worker_json(boundary, token, source)
    assert retry["run"]["recovered_stale_lock"] is True
    assert retry["checkpoint"]["record_count"] == 4
    assert not candidate.exists()

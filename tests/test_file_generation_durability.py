from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

from chroma_store import UNITS
from file_generation_store import FileGenerationStore, StagedRow
from file_generation_validate import BAR_P_DURABILITY, chroma_sequence_positions


def _rows(start: int, stop: int, owner: str = "replay-owner") -> list[StagedRow]:
    return [
        StagedRow(
            UNITS,
            f"fg1_replay_{index}",
            f"L-replay-{index}",
            f"document {index}",
            [1.0, float(index % 7) / 10.0],
            {"source_path": "/tmp/replay.jsonl"},
            "file",
            owner,
            "N",
        )
        for index in range(start, stop)
    ]


def _vector_position(positions: dict) -> int | None:
    return positions["segment_max_seq_ids"].get("knowledge_units:VECTOR")


def test_process_crash_recovery_and_bar_p_claims_are_separate(tmp_path: Path) -> None:
    assert "full power-loss durability" in BAR_P_DURABILITY["residual_power_loss_risk"]
    assert "process" in BAR_P_DURABILITY["process_crash"]

    chroma = tmp_path / "chroma"
    active = {"replay-owner": "N"}
    with FileGenerationStore(chroma, active_generations=lambda: active) as store:
        store.stage_rows(_rows(0, 1))

    script = r"""
import os, sys
from chroma_store import UNITS
from file_generation_store import FileGenerationStore, StagedRow
root = sys.argv[1]
active = {"replay-owner": "N"}
store = FileGenerationStore(root, active_generations=lambda: active)
store.stage_rows([StagedRow(UNITS,"fg1_crash_tail","L-crash-tail","tail",[1.0,0.0],
 {"source_path":"/tmp/replay.jsonl"},"file","replay-owner","N")])
os._exit(41)
"""
    child = subprocess.run(
        [sys.executable, "-c", script, str(chroma)],
        cwd=Path(__file__).resolve().parents[1],
        check=False,
    )
    assert child.returncode == 41
    with FileGenerationStore(chroma, active_generations=lambda: active) as reopened:
        assert reopened.get_unit_by_logical_id("L-crash-tail") is not None


def test_known_queue_vector_replay_tail_recovers_exact_expected_set(
    tmp_path: Path,
) -> None:
    """SIGKILL proves process-crash replay, not storage power-loss durability."""
    chroma = tmp_path / "chroma"
    owner = "replay-owner"
    active = {owner: "N"}
    initial_count = 1200
    tail_count = 800
    with FileGenerationStore(chroma, active_generations=lambda: active) as store:
        store.stage_rows(_rows(0, initial_count, owner))
        assert len(store.query_units([1.0, 0.0], 5)) == 5

    deadline = time.monotonic() + 10
    before = chroma_sequence_positions(chroma)
    while _vector_position(before) is None and time.monotonic() < deadline:
        time.sleep(0.05)
        before = chroma_sequence_positions(chroma)
    assert _vector_position(before) is not None

    # A child appends a substantial tail and dies without graceful close.  The
    # parent records positions before opening Chroma again.
    script = r"""
import os, sys
from chroma_store import UNITS
from file_generation_store import FileGenerationStore, StagedRow
root, start, stop = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
active = {"replay-owner": "N"}
store = FileGenerationStore(root, active_generations=lambda: active)
rows = [StagedRow(UNITS,f"fg1_replay_{i}",f"L-replay-{i}",f"document {i}",
 [0.0,1.0],{"source_path":"/tmp/replay.jsonl"},"file","replay-owner","N")
 for i in range(start, stop)]
store.stage_rows(rows)
os._exit(42)
"""
    child = subprocess.run(
        [
            sys.executable,
            "-c",
            script,
            str(chroma),
            str(initial_count),
            str(initial_count + tail_count),
        ],
        cwd=Path(__file__).resolve().parents[1],
        check=False,
    )
    assert child.returncode == 42
    tail = chroma_sequence_positions(chroma)
    assert tail["queue_max_seq_id"] is not None
    assert _vector_position(tail) is not None
    assert tail["queue_max_seq_id"] > _vector_position(tail), json.dumps(tail)

    expected = {f"fg1_replay_{index}" for index in range(initial_count + tail_count)}
    with FileGenerationStore(chroma, active_generations=lambda: active) as reopened:
        # Metadata exact set survives immediately; vector read triggers/reuses
        # the Rust queue replay and must return only the active generation.
        assert reopened.all_physical_ids(UNITS) == expected
        hits = reopened.query_units([1.0, 0.0], 20)
        assert len(hits) == 20
        assert all(hit["metadata"]["generation_id"] == "N" for hit in hits)
        assert len(reopened.get_units_with_embeddings(include_superseded=True)) == len(
            expected
        )
        tail_hits = reopened.query_units([0.0, 1.0], 20)
        assert tail_hits
        assert all(
            int(hit["id"].rsplit("_", 1)[-1]) >= initial_count for hit in tail_hits
        )

    # The Rust queue itself is the durable replay tail.  Qualification does not
    # require the persisted HNSW segment to catch up synchronously; it requires
    # exact cold-readable rows/embeddings and generation-filtered vector reads.
    after = chroma_sequence_positions(chroma)
    assert after["queue_max_seq_id"] >= tail["queue_max_seq_id"]
    print(
        json.dumps(
            {"after": after, "before": before, "tail": tail}, sort_keys=True
        )
    )

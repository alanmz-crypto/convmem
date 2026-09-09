"""Focused real-Chroma evidence for the isolated JSONL projection seam."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from scratch_jsonl_prototype.chroma_projection import CHROMA_DURABLE_TRANSITIONS, ScratchChromaProjection
from scratch_jsonl_prototype.engine import ScratchIncrementalJsonl
from scratch_jsonl_prototype.isolation import ScratchBoundary, create_fresh_root
from scratch_jsonl_prototype.isolation import sanitized_worker_env

WORKER = Path(__file__).with_name("scratch_jsonl_isolation_worker.py")

CHROMA_CRASH_POINTS = tuple(
    f"{side}_{op}"
    for op in ("summary_upsert", "unit_upsert")
    for side in ("before", "after")
)


def _record(index: int) -> bytes:
    return (
        json.dumps(
            {"payload": {"type": "user", "content": f"message-{index}"}},
            sort_keys=True,
        )
        + "\n"
    ).encode()


def test_incremental_engine_projects_real_chroma_and_prunes_source_scope(tmp_path: Path) -> None:
    root, token = create_fresh_root(tmp_path)
    boundary = ScratchBoundary(root, token)
    source = root / "sources" / "sess_scratch" / "messages.jsonl"
    source.parent.mkdir(parents=True)
    source.write_bytes(_record(0) + _record(1))
    projection = ScratchChromaProjection(boundary, source_path=source)

    first = ScratchIncrementalJsonl(boundary, source, projection=projection).run()
    assert first.transform_calls == 1
    assert len(projection.rows()) == 1
    assert projection.authority()["chroma_dir"].startswith(str(root))

    with source.open("ab") as handle:
        handle.write(_record(2))
    second = ScratchIncrementalJsonl(boundary, source, projection=projection).run()
    assert second.transform_calls == 1
    rows = projection.rows()
    assert len(rows) == 2
    assert {row["metadata"]["source_identity"] for row in rows} == {
        projection.source_identity
    }
    assert projection.prune(generation=second.active_generation, keep_ids={rows[0]["id"]}) == 2
    assert len(projection.rows()) == 1


def test_real_chroma_worker_isolated_and_persistent(tmp_path: Path) -> None:
    root, token = create_fresh_root(tmp_path)
    source = root / "sources" / "sess_worker" / "messages.jsonl"
    source.parent.mkdir(parents=True)
    source.write_bytes(_record(0))
    result = subprocess.run(
        [sys.executable, "-I", str(WORKER), "chroma-run", str(source)],
        cwd=root,
        env=sanitized_worker_env(root, token),
        close_fds=True,
        start_new_session=True,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    authority = json.loads(result.stdout)
    assert Path(authority["chroma_dir"]).resolve().is_relative_to(root.resolve())
    assert authority["summaries"][0]["id"] == "worker-row"
    assert authority["units"][0]["id"] == "worker-row"
    assert "CONVMEM_CONFIG" not in os.environ


def test_chroma_transition_inventory_has_both_sides() -> None:
    covered = set(CHROMA_CRASH_POINTS)
    for transition in CHROMA_DURABLE_TRANSITIONS[:2]:
        assert f"before_{transition}" in covered
        assert f"after_{transition}" in covered


def test_subprocess_chroma_upsert_crashes_replay_to_both_collections(tmp_path: Path) -> None:
    for point in CHROMA_CRASH_POINTS:
        root, token = create_fresh_root(tmp_path)
        source = root / "sources" / "sess_worker" / "messages.jsonl"
        source.parent.mkdir(parents=True)
        source.write_bytes(_record(0) + _record(1))
        crashed = subprocess.run(
            [sys.executable, "-I", str(WORKER), "chroma-incremental", str(source), point],
            cwd=root, env=sanitized_worker_env(root, token), close_fds=True,
            start_new_session=True, capture_output=True, text=True, check=False,
        )
        assert crashed.returncode == 86, (point, crashed.stderr)
        replay = subprocess.run(
            [sys.executable, "-I", str(WORKER), "chroma-incremental", str(source)],
            cwd=root, env=sanitized_worker_env(root, token), close_fds=True,
            start_new_session=True, capture_output=True, text=True, check=False,
        )
        assert replay.returncode == 0, (point, replay.stderr)
        authority = json.loads(replay.stdout)["authority"]
        assert [row["id"] for row in authority["summaries"]] == [row["id"] for row in authority["units"]]

"""Focused real-Chroma evidence for the isolated JSONL projection seam."""
# pylint: disable=line-too-long,multiple-statements,subprocess-run-check,protected-access

from __future__ import annotations

import json
import subprocess
import sys
import shutil
from pathlib import Path

from scratch_jsonl_prototype.chroma_projection import CHROMA_DURABLE_TRANSITIONS, ScratchChromaProjection
from scratch_jsonl_prototype.engine import ScratchIncrementalJsonl
from scratch_jsonl_prototype.isolation import IsolationViolation, ScratchBoundary, create_fresh_root
from scratch_jsonl_prototype.isolation import sanitized_worker_env

WORKER = Path(__file__).with_name("scratch_jsonl_isolation_worker.py")

CHROMA_CRASH_POINTS = tuple(
    f"{side}_{op}"
    for op in ("summary_upsert", "unit_upsert")
    for side in ("before", "after")
)
CHROMA_PRUNE_CRASH_POINTS = tuple(
    f"{side}_{op}" for op in ("summaries_prune", "units_prune") for side in ("before", "after")
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
    assert authority["isolation"]["credential_names"] == []
    assert authority["isolation"]["production_override_names"] == []
    assert authority["isolation"]["network"] == "IsolationViolation"


def test_chroma_transition_inventory_has_both_sides() -> None:
    covered = set(CHROMA_CRASH_POINTS) | set(CHROMA_PRUNE_CRASH_POINTS)
    for transition in CHROMA_DURABLE_TRANSITIONS:
        assert f"before_{transition}" in covered
        assert f"after_{transition}" in covered


def test_subprocess_chroma_prune_crashes_retain_other_source(tmp_path: Path) -> None:
    for point in CHROMA_PRUNE_CRASH_POINTS:
        root, token = create_fresh_root(tmp_path)
        source = root / "sources" / "sess_worker" / "messages.jsonl"
        other = root / "sources" / "sess_other" / "messages.jsonl"
        source.parent.mkdir(parents=True); other.parent.mkdir(parents=True)
        source.write_bytes(_record(0)); other.write_bytes(_record(1))
        args = [sys.executable, "-I", str(WORKER), "chroma-prune", str(source), point]
        crashed = subprocess.run(args, cwd=root, env=sanitized_worker_env(root, token), close_fds=True, start_new_session=True, capture_output=True, text=True)
        assert crashed.returncode == 86, (point, crashed.stderr)
        replay = subprocess.run(args[:5], cwd=root, env=sanitized_worker_env(root, token), close_fds=True, start_new_session=True, capture_output=True, text=True)
        assert replay.returncode == 0, replay.stderr
        authority = json.loads(replay.stdout)
        assert all(row["id"] == "keep" for row in authority["summaries"] + authority["units"])
        other_projection = ScratchChromaProjection(
            ScratchBoundary(root, token), source_path=other,
            chroma_dir=Path(authority["chroma_dir"]),
        )
        other_authority = other_projection.authority()
        assert {row["id"] for row in other_authority["summaries"]} == {"other"}
        assert {row["id"] for row in other_authority["units"]} == {"other"}


def test_constructor_receives_validated_path_and_rejects_outside(tmp_path: Path, monkeypatch) -> None:
    root, token = create_fresh_root(tmp_path)
    boundary = ScratchBoundary(root, token)
    source = root / "sources" / "sess_scratch" / "messages.jsonl"
    source.parent.mkdir(parents=True); source.write_bytes(_record(0))
    projection = ScratchChromaProjection(boundary, source_path=source)
    import chromadb
    captured = []
    original = chromadb.PersistentClient
    monkeypatch.setattr(chromadb, "PersistentClient", lambda **kwargs: (captured.append(kwargs["path"]) or original(**kwargs)))
    projection.upsert([{"id": "path", "document": "path", "metadata": {}}], "g")
    assert Path(captured[0]).resolve() == projection.chroma_dir.resolve()
    outside = tmp_path / "outside"
    before = len(captured)
    try:
        ScratchChromaProjection(boundary, source_path=source, chroma_dir=outside)
    except IsolationViolation:
        pass
    else:
        raise AssertionError("outside Chroma path was accepted")
    assert len(captured) == before
    link = root / "link"
    link.symlink_to(tmp_path)
    try:
        ScratchChromaProjection(boundary, source_path=source, chroma_dir=link / "chroma")
    except IsolationViolation:
        pass
    else:
        raise AssertionError("symlinked Chroma path was accepted")
    assert len(captured) == before


def test_exact_rebuild_and_zero_transform_storage_repair(tmp_path: Path) -> None:
    root, token = create_fresh_root(tmp_path)
    boundary = ScratchBoundary(root, token)
    source = root / "sources" / "sess_equal" / "messages.jsonl"
    source.parent.mkdir(parents=True); source.write_bytes(_record(0) + _record(1) + _record(2))
    projection = ScratchChromaProjection(boundary, source_path=source)
    engine = ScratchIncrementalJsonl(boundary, source, projection=projection)
    first = engine.run()
    assert first.mode == "full_rebuild_fallback"
    expected = projection.authority()
    with projection._session() as session:  # scratch-only deliberate torn row
        session.store.delete_summaries_for_source(str(source), keep_ids={expected["summaries"][0]["id"]})
    repaired = ScratchIncrementalJsonl(boundary, source, projection=projection).run()
    assert repaired.transform_calls == 0
    assert projection.authority() == expected
    with projection._session() as session:
        session.store.delete_units_for_source(str(source), keep_ids={expected["units"][0]["id"]})
    repaired = ScratchIncrementalJsonl(boundary, source, projection=projection).run()
    assert repaired.transform_calls == 0
    assert projection.authority() == expected
    with source.open("ab") as handle:
        handle.write(_record(3) + _record(4))
    incremental = ScratchIncrementalJsonl(boundary, source, projection=projection).run()
    assert incremental.transform_calls == 2
    incremental_checkpoint = engine.checkpoint()
    expected = {
        "chroma": projection.authority(),
        "checkpoint_authority": {
            key: value
            for key, value in incremental_checkpoint.items()
            if key != "fallback_reason"
        },
        "projection": engine.active_projection(),
    }
    for path in (engine.paths["projection"], engine.paths["checkpoint"]):
        path.unlink(missing_ok=True)
    shutil.rmtree(projection.chroma_dir)
    clean = ScratchChromaProjection(boundary, source_path=source)
    clean_engine = ScratchIncrementalJsonl(boundary, source, projection=clean)
    rebuilt = clean_engine.run()
    assert rebuilt.transform_calls > 0
    clean_checkpoint = clean_engine.checkpoint()
    assert {
        "chroma": clean.authority(),
        "checkpoint_authority": {
            key: value
            for key, value in clean_checkpoint.items()
            if key != "fallback_reason"
        },
        "projection": clean_engine.active_projection(),
    } == expected
    assert incremental_checkpoint["fallback_reason"] is None
    assert clean_checkpoint["fallback_reason"] == "initial_full"


def test_subprocess_chroma_upsert_crashes_replay_to_both_collections(tmp_path: Path) -> None:
    for point in CHROMA_CRASH_POINTS:
        root, token = create_fresh_root(tmp_path)
        source = root / "sources" / "sess_worker" / "messages.jsonl"
        source.parent.mkdir(parents=True)
        source.write_bytes(_record(0) + _record(1) + _record(2) + _record(3))
        crashed = subprocess.run(
            [sys.executable, "-I", str(WORKER), "chroma-incremental", str(source), point],
            cwd=root, env=sanitized_worker_env(root, token), close_fds=True,
            start_new_session=True, capture_output=True, text=True, check=False,
        )
        assert crashed.returncode == 86, (point, crashed.stderr)
        partial = ScratchChromaProjection(
            ScratchBoundary(root, token), source_path=source
        ).authority()
        partial_counts = {
            "before_summary_upsert": (0, 0),
            "after_summary_upsert": (1, 0),
            "before_unit_upsert": (1, 0),
            "after_unit_upsert": (1, 1),
        }
        assert (
            len(partial["summaries"]),
            len(partial["units"]),
        ) == partial_counts[point]
        replay = subprocess.run(
            [sys.executable, "-I", str(WORKER), "chroma-incremental", str(source)],
            cwd=root, env=sanitized_worker_env(root, token), close_fds=True,
            start_new_session=True, capture_output=True, text=True, check=False,
        )
        assert replay.returncode == 0, (point, replay.stderr)
        payload = json.loads(replay.stdout)
        authority = payload["authority"]
        assert payload["checkpoint"]["commit_state"] == "complete"
        assert payload["checkpoint"]["record_count"] == 4
        assert len(authority["summaries"]) == 2
        assert len(authority["units"]) == 2
        assert [row["id"] for row in authority["summaries"]] == [row["id"] for row in authority["units"]]

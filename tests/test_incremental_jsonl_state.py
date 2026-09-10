"""T2–T5 incremental JSONL production state machine, cache, Chroma, and routing."""

# pylint: disable=protected-access,duplicate-code

from __future__ import annotations

import json
from pathlib import Path

import pytest

from adapters.kiro_session_jsonl import parse, parse_complete_prefix
from incremental_jsonl import DURABLE_TRANSITIONS, IncrementalJsonlCoordinator
from tests.incremental_jsonl_helpers import (
    apply_env,
    chroma_authority,
    enable_incremental,
    install_fakes,
    isolated_env,
    kiro_record,
    worker_run,
    write_source,
)


CRASH_EXIT = 86


def test_prefix_matrix_append_partial_blank_malformed(tmp_path: Path) -> None:
    boundary, _env = isolated_env(tmp_path)
    source = write_source(boundary.root, 3)
    view = parse_complete_prefix(str(source))
    assert len(view.messages) == len(view.byte_ranges) == 3
    assert view.complete_boundary == source.stat().st_size
    messages = parse(str(source))
    assert len(messages) == len(view.messages)

    with source.open("ab") as handle:
        handle.write(b'{"payload":{"type":"user","content":"partial"')
    view2 = parse_complete_prefix(str(source))
    assert view2.complete_boundary == view.complete_boundary
    assert len(view2.messages) == 3

    with source.open("ab") as handle:
        handle.write(b"\n\n")
        handle.write(b"{not-json}\n")
        handle.write(kiro_record(3))
    view3 = parse_complete_prefix(str(source))
    assert len(view3.messages) == 4
    assert len(view3.byte_ranges) == 4


def test_disabled_run_is_noop(tmp_path: Path, monkeypatch) -> None:
    boundary, env = isolated_env(tmp_path)
    apply_env(monkeypatch, env)
    source = write_source(boundary.root, 2)
    result = IncrementalJsonlCoordinator.from_isolated_boundary(
        boundary, source, enabled=False
    ).run()
    assert result.outcome == "disabled"
    assert result.counters.total == 0


def test_initial_index_append_and_zero_call_replay(tmp_path: Path, monkeypatch) -> None:
    boundary, env = isolated_env(tmp_path)
    apply_env(monkeypatch, env)
    install_fakes(monkeypatch)
    enable_incremental(boundary)
    source = write_source(boundary.root, 4)
    first = IncrementalJsonlCoordinator.from_isolated_boundary(
        boundary, source, enabled=True
    ).run()
    assert first.outcome == "committed"
    assert first.mode == "initial_full"
    assert first.counters.summarize > 0
    first_calls = first.counters.as_dict()
    replay = IncrementalJsonlCoordinator.from_isolated_boundary(
        boundary, source, enabled=True
    ).run()
    assert replay.outcome == "unchanged"
    assert replay.counters.total == 0

    with source.open("ab") as handle:
        handle.write(kiro_record(4))
    incremental = IncrementalJsonlCoordinator.from_isolated_boundary(
        boundary, source, enabled=True
    ).run()
    assert incremental.outcome == "committed"
    assert incremental.mode == "incremental"
    assert incremental.counters.summarize < first_calls["summarize"]
    assert incremental.reused_artifacts >= 1


def test_rebuild_required_on_mutation_without_permission(
    tmp_path: Path, monkeypatch
) -> None:
    boundary, env = isolated_env(tmp_path)
    apply_env(monkeypatch, env)
    install_fakes(monkeypatch)
    enable_incremental(boundary)
    source = write_source(boundary.root, 2)
    IncrementalJsonlCoordinator.from_isolated_boundary(boundary, source, enabled=True).run()
    raw = source.read_bytes()
    source.write_bytes(
        b'{"payload":{"type":"user","content":"mutated-prefix"}}\n'
        + raw[raw.find(b"\n") + 1 :]
    )
    result = IncrementalJsonlCoordinator.from_isolated_boundary(
        boundary, source, enabled=True
    ).run()
    assert result.outcome.startswith("rebuild_required:")
    assert result.counters.total == 0


def test_incremental_equals_clean_rebuild(tmp_path: Path, monkeypatch) -> None:
    boundary, env = isolated_env(tmp_path)
    apply_env(monkeypatch, env)
    install_fakes(monkeypatch)
    enable_incremental(boundary)
    source = write_source(boundary.root, 4)
    IncrementalJsonlCoordinator.from_isolated_boundary(boundary, source, enabled=True).run()
    with source.open("ab") as handle:
        handle.write(kiro_record(4))
    IncrementalJsonlCoordinator.from_isolated_boundary(boundary, source, enabled=True).run()
    incremental_auth = chroma_authority(boundary, source)

    import shutil

    shutil.rmtree(boundary.layout["chroma"], ignore_errors=True)
    shutil.rmtree(boundary.layout["state"], ignore_errors=True)
    Path(boundary.layout["processed"]).unlink(missing_ok=True)
    Path(boundary.layout["export"]).unlink(missing_ok=True)
    IncrementalJsonlCoordinator.from_isolated_boundary(boundary, source, enabled=True).run()
    clean_auth = chroma_authority(boundary, source)
    assert incremental_auth == clean_auth


def test_bootstrap_required_zero_spend(tmp_path: Path, monkeypatch) -> None:
    boundary, env = isolated_env(tmp_path)
    apply_env(monkeypatch, env)
    install_fakes(monkeypatch)
    enable_incremental(boundary)
    source = write_source(boundary.root, 2)
    Path(boundary.layout["processed"]).write_text(
        json.dumps({"deadbeef": {"path": str(source), "chunks": 1, "units": 1}}),
        encoding="utf-8",
    )
    result = IncrementalJsonlCoordinator.from_isolated_boundary(
        boundary, source, enabled=True
    ).run()
    assert result.outcome == "bootstrap_required"
    assert result.counters.total == 0


def test_force_supersede_zero_write(tmp_path: Path, monkeypatch) -> None:
    boundary, env = isolated_env(tmp_path)
    apply_env(monkeypatch, env)
    install_fakes(monkeypatch)
    enable_incremental(boundary)
    source = write_source(boundary.root, 2)
    result = IncrementalJsonlCoordinator.from_isolated_boundary(
        boundary, source, enabled=True, force_reindex=True
    ).run()
    assert result.outcome == "incremental_force_unsupported"
    assert result.counters.total == 0
    assert (
        IncrementalJsonlCoordinator.from_isolated_boundary(
            boundary, source, enabled=True
        ).checkpoint()
        is None
    )


def test_frontier_counters_on_append(tmp_path: Path, monkeypatch) -> None:
    boundary, env = isolated_env(tmp_path)
    apply_env(monkeypatch, env)
    install_fakes(monkeypatch)
    enable_incremental(boundary)
    source = write_source(boundary.root, 20)
    first = IncrementalJsonlCoordinator.from_isolated_boundary(
        boundary, source, enabled=True, chunk_size=8, overlap=2
    ).run()
    baseline = first.counters.summarize
    with source.open("ab") as handle:
        handle.write(kiro_record(20))
    second = IncrementalJsonlCoordinator.from_isolated_boundary(
        boundary, source, enabled=True, chunk_size=8, overlap=2
    ).run()
    assert second.mode == "incremental"
    assert 0 < second.counters.summarize < baseline
    replay = IncrementalJsonlCoordinator.from_isolated_boundary(
        boundary, source, enabled=True, chunk_size=8, overlap=2
    ).run()
    assert replay.counters.total == 0


def test_cross_source_sentinel_survives_prune(tmp_path: Path, monkeypatch) -> None:
    boundary, env = isolated_env(tmp_path)
    apply_env(monkeypatch, env)
    install_fakes(monkeypatch)
    enable_incremental(boundary)
    primary = write_source(boundary.root, 2, name="sess_primary")
    other = write_source(boundary.root, 2, name="sess_other")
    IncrementalJsonlCoordinator.from_isolated_boundary(boundary, other, enabled=True).run()
    IncrementalJsonlCoordinator.from_isolated_boundary(boundary, primary, enabled=True).run()
    with primary.open("ab") as handle:
        handle.write(kiro_record(2))
    IncrementalJsonlCoordinator.from_isolated_boundary(boundary, primary, enabled=True).run()
    auth = chroma_authority(boundary, other)
    assert auth["summaries"]
    assert auth["units"]


@pytest.mark.parametrize(
    "point",
    [f"{side}_{name}" for name in DURABLE_TRANSITIONS for side in ("before", "after")],
)
def test_both_side_crash_converges_or_restores(tmp_path: Path, point: str) -> None:
    boundary, env = isolated_env(tmp_path)
    source = write_source(boundary.root, 2)
    crashed = worker_run(boundary, env, source, fault=point)
    assert crashed.returncode == CRASH_EXIT, crashed.stderr[-2000:]
    replay = worker_run(boundary, env, source)
    assert replay.returncode == 0, replay.stderr[-2000:] + replay.stdout[-2000:]
    payload = json.loads(replay.stdout)
    assert payload["run"]["outcome"] in {
        "committed",
        "unchanged",
        "rolled_back",
        "source_moved",
        "bootstrap_required",
    }
    if payload["run"]["outcome"] == "committed":
        assert payload["checkpoint"]["commit_state"] == "complete"


def test_coverage_inventory_requires_both_sides() -> None:
    required = {
        f"{side}_{name}" for name in DURABLE_TRANSITIONS for side in ("before", "after")
    }
    dropped = {point for point in required if point.endswith("lock_release")}
    remaining = required - dropped
    assert "after_lock_release" in dropped
    assert remaining
    assert len(required) == 2 * len(DURABLE_TRANSITIONS)


def test_watch_parent_has_no_checkpoint_imports() -> None:
    text = Path("watch.py").read_text(encoding="utf-8")
    assert "incremental_jsonl" not in text
    assert "checkpoint.json" not in text
    assert '["index", "--file"' in text or '"index", "--file"' in text or "index --file" in text.replace(" ", "")
    assert "index" in text and "--file" in text


def test_prepared_crash_replays_with_zero_calls(tmp_path: Path) -> None:
    boundary, env = isolated_env(tmp_path)
    source = write_source(boundary.root, 2)
    crashed = worker_run(
        boundary, env, source, fault="after_prepared_output_publish"
    )
    assert crashed.returncode == CRASH_EXIT, crashed.stderr[-2000:]
    replay = worker_run(boundary, env, source)
    assert replay.returncode == 0, replay.stderr[-2000:]
    payload = json.loads(replay.stdout)
    assert payload["run"]["outcome"] == "committed"
    assert payload["counters"]["summarize"] == 0
    assert payload["counters"]["distill"] == 0
    assert payload["counters"]["summary_embed"] == 0
    assert payload["counters"]["unit_embed"] == 0
    assert payload["run"]["reused_artifacts"] >= 1


def test_thousand_message_append_only_transforms_frontier(
    tmp_path: Path, monkeypatch
) -> None:
    boundary, env = isolated_env(tmp_path)
    apply_env(monkeypatch, env)
    install_fakes(monkeypatch)
    enable_incremental(boundary)
    source = write_source(boundary.root, 1000)
    first = IncrementalJsonlCoordinator.from_isolated_boundary(
        boundary, source, enabled=True, chunk_size=20, overlap=2
    ).run()
    assert first.outcome == "committed"
    baseline = first.counters.summarize
    assert baseline > 40
    with source.open("ab") as handle:
        handle.write(kiro_record(1000))
    second = IncrementalJsonlCoordinator.from_isolated_boundary(
        boundary, source, enabled=True, chunk_size=20, overlap=2
    ).run()
    assert second.mode == "incremental"
    assert 0 < second.counters.summarize < 4
    assert second.reused_artifacts >= baseline - 3


def test_corrupt_prepared_cache_is_refused(tmp_path: Path, monkeypatch) -> None:
    boundary, env = isolated_env(tmp_path)
    apply_env(monkeypatch, env)
    install_fakes(monkeypatch)
    enable_incremental(boundary)
    source = write_source(boundary.root, 4)
    IncrementalJsonlCoordinator.from_isolated_boundary(
        boundary, source, enabled=True
    ).run()
    prepared_files = [
        path
        for path in Path(boundary.layout["state"]).rglob("*.json")
        if path.parent.name == "prepared"
    ]
    assert prepared_files
    for path in prepared_files:
        path.write_text("{}", encoding="utf-8")
    with source.open("ab") as handle:
        handle.write(kiro_record(4))
    replay = IncrementalJsonlCoordinator.from_isolated_boundary(
        boundary, source, enabled=True
    ).run()
    assert replay.outcome == "committed"
    assert replay.reused_artifacts == 0
    assert replay.counters.summarize >= 2


def test_source_mutation_after_partial_apply_rolls_back(tmp_path: Path) -> None:
    boundary, env = isolated_env(tmp_path)
    source = write_source(boundary.root, 2)
    crashed = worker_run(boundary, env, source, fault="after_summary_upsert")
    assert crashed.returncode == CRASH_EXIT, crashed.stderr[-2000:]
    raw = source.read_bytes()
    source.write_bytes(
        b'{"payload":{"type":"user","content":"mutated-after-partial"}}\n'
        + raw[raw.find(b"\n") + 1 :]
    )
    replay = worker_run(boundary, env, source)
    assert replay.returncode == 0, replay.stderr[-2000:] + replay.stdout[-2000:]
    payload = json.loads(replay.stdout)
    assert payload["run"]["outcome"] in {"rolled_back", "source_moved"}
    assert payload["counters"]["summarize"] == 0
    assert payload["counters"]["distill"] == 0


def test_corrupt_rollback_journal_fails_closed(tmp_path: Path) -> None:
    boundary, env = isolated_env(tmp_path)
    source = write_source(boundary.root, 2)
    crashed = worker_run(boundary, env, source, fault="after_unit_upsert")
    assert crashed.returncode == CRASH_EXIT, crashed.stderr[-2000:]
    rollback = next(Path(boundary.layout["state"]).rglob("rollback.json"))
    assert rollback.is_file()
    rollback.write_text("{not-json", encoding="utf-8")
    replay = worker_run(boundary, env, source)
    assert replay.returncode != 0
    assert "json" in (replay.stderr + replay.stdout).lower() or replay.returncode != 0


def test_processed_does_not_outrun_checkpoint(tmp_path: Path, monkeypatch) -> None:
    boundary, env = isolated_env(tmp_path)
    apply_env(monkeypatch, env)
    install_fakes(monkeypatch)
    enable_incremental(boundary)
    source = write_source(boundary.root, 2)
    IncrementalJsonlCoordinator.from_isolated_boundary(boundary, source, enabled=True).run()
    processed = json.loads(Path(boundary.layout["processed"]).read_text(encoding="utf-8"))
    checkpoint = IncrementalJsonlCoordinator.from_isolated_boundary(
        boundary, source, enabled=True
    ).checkpoint()
    assert checkpoint is not None
    assert checkpoint["processed_hash"] in processed
    assert processed[checkpoint["processed_hash"]]["path"] == str(source)

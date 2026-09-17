"""Copilot-FAIL corrective adversarial tests for issue #286 S0–S3."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from incremental_jsonl import IncrementalJsonlCoordinator
from tests.incremental_jsonl_helpers import (
    apply_env,
    chroma_authority,
    enable_incremental,
    install_build_chunk_tracker,
    install_fakes,
    isolated_env,
    kiro_record,
    worker_run,
    write_codex_history_source,
    write_source,
)

CRASH_EXIT = 86


def _duplicate_distill(_text, **_kwargs):
    return [
        {
            "type": "explanation",
            "title": "shared",
            "summary": "shared canonical distill body",
            "keywords": ["shared"],
            "confidence": 0.95,
            "domain": "general",
        }
    ]


def test_cross_source_dedupe_never_claims_foreign_matched_id(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    boundary, env = isolated_env(tmp_path)
    apply_env(monkeypatch, env)
    install_fakes(monkeypatch)
    import ingest

    enable_incremental(boundary)
    foreign = write_source(boundary.root, 4, name="sess_foreign")
    primary = write_source(boundary.root, 2, name="sess_primary")
    IncrementalJsonlCoordinator.from_isolated_boundary(
        boundary, foreign, enabled=True, chunk_size=2, overlap=0
    ).run()
    monkeypatch.setattr(ingest, "distill", _duplicate_distill)
    foreign_auth = chroma_authority(boundary, foreign)
    foreign_unit_ids = {row["id"] for row in foreign_auth["units"]}
    assert foreign_unit_ids
    second = IncrementalJsonlCoordinator.from_isolated_boundary(
        boundary, primary, enabled=True, chunk_size=2, overlap=0
    ).run()
    assert second.outcome == "committed"
    primary_cp = IncrementalJsonlCoordinator.from_isolated_boundary(
        boundary, primary, enabled=True, chunk_size=2, overlap=0
    ).checkpoint()
    assert primary_cp is not None
    assert not set(primary_cp["unit_ids"]).intersection(foreign_unit_ids)
    foreign_coordinator = IncrementalJsonlCoordinator.from_isolated_boundary(
        boundary, foreign, enabled=True, chunk_size=2, overlap=0
    )
    with foreign_coordinator._session() as session:  # pylint: disable=protected-access
        session.store.delete_units_for_source(
            str(foreign),
            candidate_ids=foreign_unit_ids,
            keep_ids=set(),
        )
    unchanged = IncrementalJsonlCoordinator.from_isolated_boundary(
        boundary, primary, enabled=True, chunk_size=2, overlap=0
    ).run()
    assert unchanged.outcome == "unchanged"
    assert unchanged.counters.total == 0


def test_historical_cache_loss_refuses_without_provider_calls(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    boundary, env = isolated_env(tmp_path)
    apply_env(monkeypatch, env)
    install_fakes(monkeypatch)
    enable_incremental(boundary)
    source = write_source(boundary.root, 8)
    build_calls = install_build_chunk_tracker(monkeypatch)
    first = IncrementalJsonlCoordinator.from_isolated_boundary(
        boundary, source, enabled=True, chunk_size=4, overlap=0
    ).run()
    assert first.outcome == "committed"
    assert build_calls == [0, 4]
    historical = [
        path
        for path in Path(boundary.layout["state"]).rglob("*.json")
        if path.parent.name == "prepared"
        and json.loads(path.read_text(encoding="utf-8")).get("chunk_start") == 0
    ]
    assert len(historical) == 1
    historical[0].write_text("{}", encoding="utf-8")
    build_calls.clear()
    with source.open("ab") as handle:
        handle.write(kiro_record(8))
    second = IncrementalJsonlCoordinator.from_isolated_boundary(
        boundary, source, enabled=True, chunk_size=4, overlap=0
    ).run()
    assert second.outcome == "historical_cache_unavailable"
    assert second.counters.total == 0
    assert not build_calls


def test_invalid_utf8_complete_line_refuses_incremental_route(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    boundary, env = isolated_env(tmp_path)
    apply_env(monkeypatch, env)
    install_fakes(monkeypatch)
    enable_incremental(boundary)
    source = write_source(boundary.root, 2)
    raw = source.read_bytes()
    source.write_bytes(raw + bytes.fromhex("c3") + b"\n")
    result = IncrementalJsonlCoordinator.from_isolated_boundary(
        boundary, source, enabled=True
    ).run()
    assert result.outcome == "invalid_prefix_encoding"
    assert result.counters.total == 0


def test_checkpoint_retains_raw_line_coverage_after_snapshot_cleanup(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    boundary, env = isolated_env(tmp_path)
    apply_env(monkeypatch, env)
    install_fakes(monkeypatch)
    enable_incremental(boundary)
    source = write_source(boundary.root, 2)
    IncrementalJsonlCoordinator.from_isolated_boundary(boundary, source, enabled=True).run()
    checkpoint = IncrementalJsonlCoordinator.from_isolated_boundary(
        boundary, source, enabled=True
    ).checkpoint()
    assert checkpoint is not None
    coverage = checkpoint["raw_line_coverage"]
    assert coverage["prefix_sha256"] == checkpoint["prefix_sha256"]
    assert coverage["outcomes"]
    assert not list(Path(boundary.layout["state"]).rglob("snapshots/*"))


def test_export_matches_physical_chroma_after_cross_source_dedupe(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    boundary, env = isolated_env(tmp_path)
    apply_env(monkeypatch, env)
    install_fakes(monkeypatch)
    import ingest

    enable_incremental(boundary)
    foreign = write_source(boundary.root, 4, name="sess_foreign")
    primary = write_source(boundary.root, 2, name="sess_primary")
    IncrementalJsonlCoordinator.from_isolated_boundary(
        boundary, foreign, enabled=True, chunk_size=2, overlap=0
    ).run()
    monkeypatch.setattr(ingest, "distill", _duplicate_distill)
    IncrementalJsonlCoordinator.from_isolated_boundary(
        boundary, primary, enabled=True, chunk_size=2, overlap=0
    ).run()
    export_path = Path(boundary.layout["export"])
    export_ids = set()
    for line in export_path.read_text(encoding="utf-8").splitlines():
        row = json.loads(line)
        if row.get("source_path") == str(primary):
            export_ids.add(row["id"])
    auth = chroma_authority(boundary, primary)
    chroma_ids = {row["id"] for row in auth["units"]}
    checkpoint_ids = set(auth["checkpoint"]["unit_ids"])
    assert export_ids == chroma_ids == checkpoint_ids


def test_codex_append_traces_build_calls_to_seam_only(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    boundary, env = isolated_env(tmp_path)
    apply_env(monkeypatch, env)
    install_fakes(monkeypatch)
    enable_incremental(boundary)
    source = write_codex_history_source(boundary.root, 8)
    build_calls = install_build_chunk_tracker(monkeypatch)
    IncrementalJsonlCoordinator.from_isolated_boundary(
        boundary, source, enabled=True, chunk_size=4, overlap=0
    ).run()
    assert build_calls == [0, 4]
    build_calls.clear()
    with source.open("ab") as handle:
        handle.write(
            json.dumps(
                {
                    "text": "codex-history-00008",
                    "session_id": "sess-codex",
                    "ts": 1_700_000_008,
                }
            ).encode()
            + b"\n"
        )
    append = IncrementalJsonlCoordinator.from_isolated_boundary(
        boundary, source, enabled=True, chunk_size=4, overlap=0
    ).run()
    assert append.outcome == "committed"
    assert append.mode == "incremental"
    assert 0 not in build_calls
    assert all(offset >= 4 for offset in build_calls)
    assert append.counters.summarize == len(build_calls)
    assert append.reused_artifacts >= 1


def test_corrupt_prepared_crash_replay_refuses_without_publish(tmp_path: Path) -> None:
    boundary, env = isolated_env(tmp_path)
    source = write_source(boundary.root, 2)
    crashed = worker_run(
        boundary, env, source, fault="after_prepared_output_publish"
    )
    assert crashed.returncode == CRASH_EXIT, crashed.stderr[-2000:]
    prepared_files = [
        path
        for path in Path(boundary.layout["state"]).rglob("*.json")
        if path.parent.name == "prepared"
    ]
    assert prepared_files
    artifact = json.loads(prepared_files[0].read_text(encoding="utf-8"))
    artifact["summary"] = "tampered-summary-without-digest-refresh"
    prepared_files[0].write_text(json.dumps(artifact), encoding="utf-8")
    replay = worker_run(boundary, env, source)
    assert replay.returncode == 0, replay.stderr[-2000:]
    payload = json.loads(replay.stdout)
    assert payload["run"]["outcome"] == "prepared_artifact_corrupt"
    assert payload["counters"]["summarize"] == 0
    assert payload["counters"]["distill"] == 0


def test_tampered_checkpoint_coverage_refuses_before_unchanged(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    boundary, env = isolated_env(tmp_path)
    apply_env(monkeypatch, env)
    install_fakes(monkeypatch)
    enable_incremental(boundary)
    source = write_source(boundary.root, 2)
    coordinator = IncrementalJsonlCoordinator.from_isolated_boundary(
        boundary, source, enabled=True
    )
    assert coordinator.run().outcome == "committed"
    checkpoint_paths = list(Path(boundary.layout["state"]).rglob("checkpoint.json"))
    assert checkpoint_paths
    checkpoint = json.loads(checkpoint_paths[0].read_text(encoding="utf-8"))
    checkpoint["raw_line_coverage"]["coverage_digest"] = "0" * 64
    checkpoint_paths[0].write_text(json.dumps(checkpoint), encoding="utf-8")
    second = IncrementalJsonlCoordinator.from_isolated_boundary(
        boundary, source, enabled=True
    ).run()
    assert second.outcome == "invalid_state"
    assert second.counters.total == 0

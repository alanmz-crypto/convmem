"""Gate 2 — isolated Claude incremental route and adversarial oracles."""

# pylint: disable=duplicate-code,redefined-outer-name

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from incremental_jsonl import IncrementalJsonlCoordinator, maybe_route_incremental
from incremental_jsonl_formats import (
    ALL_ISOLATED_FORMATS,
    ISOLATED_CLAUDE_FORMATS,
    ISOLATED_CODEX_FORMATS,
    KIRO_ROUTE_FORMATS,
    get_format_spec,
    routed_formats,
)
from tests.incremental_jsonl_helpers import (
    apply_env,
    chroma_authority,
    claude_record,
    enable_incremental,
    install_fakes,
    isolated_env,
    worker_run,
    write_claude_source,
)


CRASH_EXIT = 86


@pytest.fixture
def claude_source(tmp_path: Path) -> tuple:
    boundary, env = isolated_env(tmp_path)
    source = write_claude_source(boundary.root, 8)
    return boundary, env, source


def test_claude_format_spec_and_default_routing() -> None:
    spec = get_format_spec("jsonl_claude_session")
    assert spec is not None
    assert spec.adapter_contract_version == "claude-complete-prefix-v1"
    assert spec.tool == "claude"
    assert routed_formats() == KIRO_ROUTE_FORMATS
    assert "jsonl_claude_session" not in routed_formats()
    assert ISOLATED_CLAUDE_FORMATS == frozenset({"jsonl_claude_session"})
    assert ISOLATED_CODEX_FORMATS <= ALL_ISOLATED_FORMATS
    assert ISOLATED_CLAUDE_FORMATS <= ALL_ISOLATED_FORMATS
    assert routed_formats(isolated_codex=True) == ALL_ISOLATED_FORMATS
    assert "jsonl_kiro_session" in ALL_ISOLATED_FORMATS
    assert "jsonl_codex_history" in ALL_ISOLATED_FORMATS
    assert "jsonl_claude_session" in ALL_ISOLATED_FORMATS


def test_claude_append_reuses_historical_transforms(
    claude_source, monkeypatch: pytest.MonkeyPatch
) -> None:
    boundary, env, source = claude_source
    apply_env(monkeypatch, env)
    install_fakes(monkeypatch)
    enable_incremental(boundary)
    first = IncrementalJsonlCoordinator.from_isolated_boundary(
        boundary, source, enabled=True, chunk_size=4, overlap=0
    ).run()
    assert first.outcome == "committed"
    assert first.counters.summarize > 0
    baseline = first.counters.as_dict()
    with source.open("ab") as handle:
        handle.write(claude_record(8))
    second = IncrementalJsonlCoordinator.from_isolated_boundary(
        boundary, source, enabled=True, chunk_size=4, overlap=0
    ).run()
    assert second.outcome == "committed"
    assert second.mode == "incremental"
    assert second.counters.summarize < baseline["summarize"]
    assert second.reused_artifacts >= 1
    third = IncrementalJsonlCoordinator.from_isolated_boundary(
        boundary, source, enabled=True, chunk_size=4, overlap=0
    ).run()
    assert third.outcome == "unchanged"
    assert third.counters.total == 0


def test_claude_incremental_matches_clean_rebuild(
    claude_source, monkeypatch: pytest.MonkeyPatch
) -> None:
    boundary, env, source = claude_source
    apply_env(monkeypatch, env)
    install_fakes(monkeypatch)
    enable_incremental(boundary)
    IncrementalJsonlCoordinator.from_isolated_boundary(
        boundary, source, enabled=True, chunk_size=4, overlap=0
    ).run()
    with source.open("ab") as handle:
        handle.write(claude_record(8))
    IncrementalJsonlCoordinator.from_isolated_boundary(
        boundary, source, enabled=True, chunk_size=4, overlap=0
    ).run()
    incremental_auth = chroma_authority(boundary, source)
    shutil.rmtree(boundary.layout["chroma"], ignore_errors=True)
    shutil.rmtree(boundary.layout["state"], ignore_errors=True)
    Path(boundary.layout["processed"]).unlink(missing_ok=True)
    Path(boundary.layout["export"]).unlink(missing_ok=True)
    IncrementalJsonlCoordinator.from_isolated_boundary(
        boundary, source, enabled=True, chunk_size=4, overlap=0
    ).run()
    clean_auth = chroma_authority(boundary, source)
    assert incremental_auth == clean_auth


def test_claude_partial_line_never_advances_boundary(
    claude_source, monkeypatch: pytest.MonkeyPatch
) -> None:
    boundary, env, source = claude_source
    apply_env(monkeypatch, env)
    install_fakes(monkeypatch)
    enable_incremental(boundary)
    IncrementalJsonlCoordinator.from_isolated_boundary(
        boundary, source, enabled=True
    ).run()
    first = IncrementalJsonlCoordinator.from_isolated_boundary(
        boundary, source, enabled=True
    ).checkpoint()
    with source.open("ab") as handle:
        handle.write(b'{"type":"user","message":{"role":"user","content":"partial"')
    second = IncrementalJsonlCoordinator.from_isolated_boundary(
        boundary, source, enabled=True
    ).run()
    assert second.outcome == "unchanged"
    checkpoint = IncrementalJsonlCoordinator.from_isolated_boundary(
        boundary, source, enabled=True
    ).checkpoint()
    assert checkpoint["complete_boundary"] == first["complete_boundary"]


def test_claude_interior_rewrite_requires_rebuild(
    claude_source, monkeypatch: pytest.MonkeyPatch
) -> None:
    boundary, env, source = claude_source
    apply_env(monkeypatch, env)
    install_fakes(monkeypatch)
    enable_incremental(boundary)
    IncrementalJsonlCoordinator.from_isolated_boundary(
        boundary, source, enabled=True
    ).run()
    raw = source.read_bytes()
    source.write_bytes(
        json.dumps(
            {
                "type": "user",
                "sessionId": "sess-claude-hermetic",
                "message": {"role": "user", "content": "mutated"},
            }
        ).encode()
        + b"\n"
        + raw[raw.find(b"\n") + 1 :]
    )
    result = IncrementalJsonlCoordinator.from_isolated_boundary(
        boundary, source, enabled=True
    ).run()
    assert result.outcome.startswith("rebuild_required:")
    assert result.counters.total == 0


def test_claude_bootstrap_required_for_processed_entry(
    claude_source, monkeypatch: pytest.MonkeyPatch
) -> None:
    boundary, env, source = claude_source
    apply_env(monkeypatch, env)
    install_fakes(monkeypatch)
    enable_incremental(boundary)
    Path(boundary.layout["processed"]).write_text(
        json.dumps({"deadbeef": {"path": str(source), "chunks": 1, "units": 1}}),
        encoding="utf-8",
    )
    result = IncrementalJsonlCoordinator.from_isolated_boundary(
        boundary, source, enabled=True
    ).run()
    assert result.outcome == "bootstrap_required"
    assert result.counters.total == 0


def test_claude_format_eligible_only_under_isolation(
    claude_source, monkeypatch: pytest.MonkeyPatch
) -> None:
    boundary, env, source = claude_source
    assert "jsonl_claude_session" in ISOLATED_CLAUDE_FORMATS
    apply_env(monkeypatch, env)
    install_fakes(monkeypatch)
    enable_incremental(boundary)
    monkeypatch.delenv("CONVMEM_INCREMENTAL_ROOT", raising=False)
    result = IncrementalJsonlCoordinator.from_isolated_boundary(
        boundary, source, enabled=True
    ).run()
    assert result.outcome == "ineligible_format"


def test_maybe_route_skips_claude_without_isolated_root(
    claude_source, monkeypatch: pytest.MonkeyPatch
) -> None:
    boundary, env, source = claude_source
    apply_env(monkeypatch, env)
    monkeypatch.delenv("CONVMEM_INCREMENTAL_ROOT", raising=False)
    import tomllib

    cfg = tomllib.loads(
        boundary.layout["user_config"]
        .read_text(encoding="utf-8")
        .replace("enabled = false", "enabled = true", 1)
    )
    routed = maybe_route_incremental(
        cfg=cfg,
        idx=cfg.get("index", {}),
        path=str(source),
        path_key=str(source),
        file_hash="abc",
        processed={},
        models=cfg.get("models", {}),
        tool="claude",
        units_export=None,
        chunk_size=4,
        overlap=0,
        min_confidence=0.6,
        force_reindex=False,
        supersede_on_reindex=False,
        verbose=False,
        detected_format="jsonl_claude_session",
    )
    assert routed is None


def test_claude_unrelated_source_survives_prune(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    boundary, env = isolated_env(tmp_path)
    apply_env(monkeypatch, env)
    install_fakes(monkeypatch)
    enable_incremental(boundary)
    primary = write_claude_source(boundary.root, 4, name="primary-session")
    other = write_claude_source(boundary.root, 4, name="other-session")
    IncrementalJsonlCoordinator.from_isolated_boundary(boundary, other, enabled=True).run()
    IncrementalJsonlCoordinator.from_isolated_boundary(boundary, primary, enabled=True).run()
    with primary.open("ab") as handle:
        handle.write(claude_record(4))
    IncrementalJsonlCoordinator.from_isolated_boundary(boundary, primary, enabled=True).run()
    assert chroma_authority(boundary, other)["summaries"]


def test_kiro_and_codex_routing_unchanged() -> None:
    assert routed_formats() == frozenset({"jsonl_kiro_session"})
    assert "jsonl_codex_history" not in routed_formats()
    assert "jsonl_claude_session" not in routed_formats()
    isolated = routed_formats(isolated_codex=True)
    assert "jsonl_kiro_session" in isolated
    assert "jsonl_codex_history" in isolated
    assert "jsonl_claude_session" not in KIRO_ROUTE_FORMATS


def test_claude_prepared_crash_replays_with_zero_calls(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    boundary, env = isolated_env(tmp_path)
    source = write_claude_source(boundary.root, 2)
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

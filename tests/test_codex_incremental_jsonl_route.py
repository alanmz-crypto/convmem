"""S3 — isolated fresh-source Codex incremental route and adversarial oracles."""

# pylint: disable=duplicate-code,redefined-outer-name

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from incremental_jsonl import (
    IncrementalJsonlCoordinator,
    compute_transform_fingerprint,
    maybe_route_incremental,
)
from incremental_jsonl_formats import ISOLATED_CODEX_FORMATS
from tests.incremental_jsonl_helpers import (
    apply_env,
    chroma_authority,
    codex_history_record,
    codex_rollout_record,
    enable_incremental,
    install_fakes,
    isolated_env,
    worker_run,
    write_codex_history_source,
    write_codex_rollout_source,
)


CRASH_EXIT = 86


@pytest.fixture(params=["history", "rollout"])
def codex_source(request: pytest.FixtureRequest, tmp_path: Path):
    boundary, env = isolated_env(tmp_path)
    if request.param == "history":
        source = write_codex_history_source(boundary.root, 8)
        record_fn = codex_history_record
        fmt = "jsonl_codex_history"
    else:
        source = write_codex_rollout_source(boundary.root, 8)
        record_fn = codex_rollout_record
        fmt = "jsonl_codex_rollout"
    return boundary, env, source, record_fn, fmt


def _run_append_zero_calls(
    boundary,
    env,
    source: Path,
    record_fn,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
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
        handle.write(record_fn(8))
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


def test_codex_append_reuses_historical_transforms(
    codex_source, monkeypatch: pytest.MonkeyPatch
) -> None:
    boundary, env, source, record_fn, _fmt = codex_source
    _run_append_zero_calls(boundary, env, source, record_fn, monkeypatch)


def test_codex_incremental_matches_clean_rebuild(
    codex_source, monkeypatch: pytest.MonkeyPatch
) -> None:
    boundary, env, source, record_fn, _fmt = codex_source
    apply_env(monkeypatch, env)
    install_fakes(monkeypatch)
    enable_incremental(boundary)
    IncrementalJsonlCoordinator.from_isolated_boundary(
        boundary, source, enabled=True, chunk_size=4, overlap=0
    ).run()
    with source.open("ab") as handle:
        handle.write(record_fn(8))
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


def test_codex_partial_line_never_advances_boundary(
    codex_source, monkeypatch: pytest.MonkeyPatch
) -> None:
    boundary, env, source, _record_fn, _fmt = codex_source
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
        handle.write(b'{"text":"partial"')
    second = IncrementalJsonlCoordinator.from_isolated_boundary(
        boundary, source, enabled=True
    ).run()
    assert second.outcome == "unchanged"
    checkpoint = IncrementalJsonlCoordinator.from_isolated_boundary(
        boundary, source, enabled=True
    ).checkpoint()
    assert checkpoint["complete_boundary"] == first["complete_boundary"]


def test_codex_interior_rewrite_requires_rebuild(
    codex_source, monkeypatch: pytest.MonkeyPatch
) -> None:
    boundary, env, source, _record_fn, _fmt = codex_source
    apply_env(monkeypatch, env)
    install_fakes(monkeypatch)
    enable_incremental(boundary)
    IncrementalJsonlCoordinator.from_isolated_boundary(
        boundary, source, enabled=True
    ).run()
    raw = source.read_bytes()
    source.write_bytes(b'{"text":"mutated"}\n' + raw[raw.find(b"\n") + 1 :])
    result = IncrementalJsonlCoordinator.from_isolated_boundary(
        boundary, source, enabled=True
    ).run()
    assert result.outcome.startswith("rebuild_required:")
    assert result.counters.total == 0


def test_codex_bootstrap_required_for_processed_entry(
    codex_source, monkeypatch: pytest.MonkeyPatch
) -> None:
    boundary, env, source, _record_fn, _fmt = codex_source
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


def test_codex_formats_are_eligible_only_under_isolation(
    codex_source, monkeypatch: pytest.MonkeyPatch
) -> None:
    boundary, env, source, _record_fn, fmt = codex_source
    assert fmt in ISOLATED_CODEX_FORMATS
    apply_env(monkeypatch, env)
    install_fakes(monkeypatch)
    enable_incremental(boundary)
    monkeypatch.delenv("CONVMEM_INCREMENTAL_ROOT", raising=False)
    result = IncrementalJsonlCoordinator.from_isolated_boundary(
        boundary, source, enabled=True
    ).run()
    assert result.outcome == "ineligible_format"


def test_maybe_route_skips_codex_without_isolated_root(
    codex_source, monkeypatch: pytest.MonkeyPatch
) -> None:
    boundary, env, source, _record_fn, fmt = codex_source
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
        tool="codex",
        units_export=None,
        chunk_size=4,
        overlap=0,
        min_confidence=0.6,
        force_reindex=False,
        supersede_on_reindex=False,
        verbose=False,
        detected_format=fmt,
    )
    assert routed is None


def test_codex_unrelated_source_survives_prune(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    boundary, env = isolated_env(tmp_path)
    apply_env(monkeypatch, env)
    install_fakes(monkeypatch)
    enable_incremental(boundary)
    primary = write_codex_history_source(boundary.root, 4)
    other = write_codex_rollout_source(boundary.root, 4, name="rollout-other")
    IncrementalJsonlCoordinator.from_isolated_boundary(boundary, other, enabled=True).run()
    IncrementalJsonlCoordinator.from_isolated_boundary(boundary, primary, enabled=True).run()
    with primary.open("ab") as handle:
        handle.write(codex_history_record(4))
    IncrementalJsonlCoordinator.from_isolated_boundary(boundary, primary, enabled=True).run()
    assert chroma_authority(boundary, other)["summaries"]


def test_codex_fingerprint_change_refuses_stale_cache(
    codex_source, monkeypatch: pytest.MonkeyPatch
) -> None:
    boundary, env, source, record_fn, _fmt = codex_source
    apply_env(monkeypatch, env)
    install_fakes(monkeypatch)
    enable_incremental(boundary)
    coordinator = IncrementalJsonlCoordinator.from_isolated_boundary(
        boundary,
        source,
        enabled=True,
        transform_fingerprint="stale-fingerprint",
    )
    coordinator.run()
    with source.open("ab") as handle:
        handle.write(record_fn(8))
    result = IncrementalJsonlCoordinator.from_isolated_boundary(
        boundary,
        source,
        enabled=True,
        transform_fingerprint=compute_transform_fingerprint(
            chunk_size=2,
            overlap=0,
            min_confidence=0.6,
            models=coordinator.models,
            embed_dimension=8,
            implementation_revision="hermetic-test",
            adapter_format=coordinator.format_spec.format_id,
            adapter_contract_version=coordinator.format_spec.adapter_contract_version,
        ),
    ).run()
    assert result.outcome.startswith("rebuild_required:transform_fingerprint_changed")


@pytest.mark.parametrize(
    "writer",
    [write_codex_history_source, write_codex_rollout_source],
)
def test_codex_prepared_crash_replays_with_zero_calls(
    tmp_path: Path, writer
) -> None:
    boundary, env = isolated_env(tmp_path)
    if writer is write_codex_rollout_source:
        source = writer(boundary.root, 2, name="rollout-crash")
    else:
        source = writer(boundary.root, 2)
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

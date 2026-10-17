"""Gate-3 corrective 5 tests for Codex rollout admission (C5b, C1b, C6b)."""

# pylint: disable=duplicate-code,protected-access

from __future__ import annotations

import copy
from datetime import datetime, timezone
from pathlib import Path

import pytest
from typer.testing import CliRunner

import config
import convmem
import incremental_jsonl
import ingest
import watch
from incremental_jsonl_production import ProductionBoundary
from tests.incremental_jsonl_helpers import codex_rollout_record, install_fakes
from tests.test_incremental_jsonl_codex_route_corrective import (
    _coordinator,
    _legacy_reindex,
    _write_config_without_admission,
)
from tests.test_incremental_jsonl_codex_rollout_route import (
    _admitted_rollout,
    _production_cfg,
    _sessions_root,
    _write_user_config,
)
from watch import CircuitBreakerState, IndexSubprocessError
from watch_circuit_breaker import parse_live_route_refused

_DIGEST = "c" * 64
_CONTINUITY_REASONS = (
    "source_identity_changed",
    "transform_fingerprint_changed",
    "source_replaced_or_rotated",
    "source_truncated",
    "validated_prefix_mutated",
)
_ROUTE_OUTCOMES = (
    "bootstrap_required",
    "invalid_state",
    "source_too_large",
    "frontier_violation",
    "transform_chunk_cap",
    "codex_session_identity_mismatch",
    "rolled_back",
    "rebuild_required:projection_checkpoint_mismatch",
    *(f"rebuild_required:{reason}" for reason in _CONTINUITY_REASONS),
)


def _cli_refusal_stderr(
    monkeypatch: pytest.MonkeyPatch, outcome: str, digest: str
) -> tuple[int, str]:
    detail = f"{outcome}:{digest}" if digest else outcome

    def refuse(**_kwargs: object) -> dict:
        raise incremental_jsonl.IncrementalJsonlError("live_route_refused", detail)

    monkeypatch.setattr(convmem, "_guard_write", lambda: None)
    monkeypatch.setattr(ingest, "index", refuse)
    result = CliRunner().invoke(convmem.app, ["index", "--file", "/x/rollout.jsonl"])
    return result.exit_code, result.stderr


@pytest.mark.parametrize("digest", [_DIGEST, ""], ids=["digest", "no_digest"])
@pytest.mark.parametrize("outcome", _ROUTE_OUTCOMES)
def test_c5b_every_route_outcome_round_trips_through_cli(
    monkeypatch: pytest.MonkeyPatch, outcome: str, digest: str
) -> None:
    formatted = incremental_jsonl.format_live_route_refused(outcome, digest)
    assert parse_live_route_refused(formatted) == (outcome, digest)
    exit_code, stderr = _cli_refusal_stderr(monkeypatch, outcome, digest)
    assert exit_code == incremental_jsonl.LIVE_ROUTE_REFUSED_EXIT
    assert parse_live_route_refused(stderr) == (outcome, digest)


@pytest.mark.parametrize("verbose", [True, False], ids=["verbose", "quiet"])
def test_c5b_d8_marker_quarantines_first_event_without_respawn(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, verbose: bool
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    sessions = _sessions_root(tmp_path)
    sessions.mkdir(parents=True)
    source = _admitted_rollout(sessions, datetime(2026, 6, 1, tzinfo=timezone.utc))
    breaker = CircuitBreakerState(tmp_path / "breaker.json")
    marker = incremental_jsonl.format_live_route_refused(
        "rebuild_required:projection_checkpoint_mismatch", _DIGEST
    )
    spawn_calls = 0

    def fake_flush(_path: str, **_kwargs: object) -> None:
        nonlocal spawn_calls
        spawn_calls += 1
        raise IndexSubprocessError(marker, returncode=91, stderr=marker + "\n")

    monkeypatch.setattr(watch, "flush_path", fake_flush)
    watch._process_ready_path(str(source), cfg={}, breaker=breaker, verbose=verbose)
    assert spawn_calls == 1
    assert breaker.is_refusal_quarantined(str(source), _DIGEST)
    for index in range(3):
        with source.open("ab") as handle:
            handle.write(codex_rollout_record(60 + index))
        watch._process_ready_path(str(source), cfg={}, breaker=breaker, verbose=verbose)
    assert spawn_calls == 1


@pytest.mark.parametrize(
    "returncode,stderr",
    [
        (1, f"error: live_route_refused:rebuild_required:projection_checkpoint_mismatch:{_DIGEST}"),
        (91, "index subprocess exit 91 without marker"),
    ],
    ids=["exit_1_quoted_marker", "exit_91_no_whole_line_marker"],
)
def test_c5b_negative_cases_still_do_not_quarantine(
    tmp_path: Path, returncode: int, stderr: str
) -> None:
    path = str(tmp_path / "other.jsonl")
    Path(path).write_text("{}\n", encoding="utf-8")
    breaker = CircuitBreakerState(tmp_path / "breaker.json")
    watch._record_ready_path_failure(
        path,
        IndexSubprocessError(stderr, returncode=returncode, stderr=stderr),
        breaker=breaker,
        verbose=False,
    )
    assert not breaker.has_refusal_quarantine_for_path(path)


def _admitted_setup(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    sessions = _sessions_root(tmp_path)
    sessions.mkdir(parents=True)
    admitted = datetime(2026, 6, 1, tzinfo=timezone.utc)
    source = _admitted_rollout(sessions, admitted)
    cfg = _production_cfg(tmp_path, sessions, admitted)
    cfg_path = tmp_path / "config.toml"
    _write_user_config(cfg_path, cfg)
    monkeypatch.delenv("CONVMEM_INCREMENTAL_ROOT", raising=False)
    install_fakes(monkeypatch)
    return source, cfg, cfg_path


def _projection_state(coord: incremental_jsonl.IncrementalJsonlCoordinator, cfg: dict):
    processed = Path(cfg["index"]["processed_log"])
    return (
        coord._projection_fingerprint(),
        processed.read_bytes() if processed.exists() else None,
    )


def _crash_first_run(
    source: Path, cfg: dict, cfg_path: Path, *, point: str, phase: str
) -> incremental_jsonl.IncrementalJsonlCoordinator:
    def crash(current: str) -> None:
        if current == point:
            raise RuntimeError(f"crash at {point}")

    crashing = _coordinator(
        ProductionBoundary(cfg, source, config_path=cfg_path),
        source,
        cfg,
        fault=crash,
    )
    with pytest.raises(RuntimeError, match="crash at"):
        crashing.run()
    assert crashing.checkpoint() is None
    pending = incremental_jsonl._read_json(crashing.paths["transaction"])
    assert pending["phase"] == phase
    return crashing


def test_c1b_crashed_first_run_then_legacy_index_refuses_bootstrap_required(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source, cfg, cfg_path = _admitted_setup(tmp_path, monkeypatch)
    _crash_first_run(
        source, cfg, cfg_path, point="before_rollback_prepare", phase="PREPARING"
    )
    cfg_no_admission = copy.deepcopy(cfg)
    del cfg_no_admission["index"]["incremental_jsonl"]["codex_rollout_admission"]
    _write_config_without_admission(cfg_path, cfg_no_admission)
    _legacy_reindex(cfg_no_admission, source)
    _write_user_config(cfg_path, cfg)
    with source.open("ab") as handle:
        handle.write(codex_rollout_record(25))
    coord = _coordinator(ProductionBoundary(cfg, source, config_path=cfg_path), source, cfg)
    before = _projection_state(coord, cfg)
    assert before[0] and before[1]
    result = coord.run()
    assert result.outcome == "bootstrap_required"
    assert result.counters.total == 0
    assert _projection_state(coord, cfg) == before


def test_c1b_first_run_preparing_recovery_without_legacy_still_commits(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source, cfg, cfg_path = _admitted_setup(tmp_path, monkeypatch)
    _crash_first_run(
        source, cfg, cfg_path, point="before_rollback_prepare", phase="PREPARING"
    )
    result = _coordinator(ProductionBoundary(cfg, source, config_path=cfg_path), source, cfg).run()
    assert result.outcome == "committed"
    assert result.mode == "preparing_recovery"


def test_c1b_first_run_applying_recovery_without_legacy_still_commits(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source, cfg, cfg_path = _admitted_setup(tmp_path, monkeypatch)
    crashing = _crash_first_run(
        source, cfg, cfg_path, point="before_checkpoint_prepare", phase="APPLYING"
    )
    assert crashing._chroma_row_count() > 0
    result = _coordinator(ProductionBoundary(cfg, source, config_path=cfg_path), source, cfg).run()
    assert result.outcome == "committed"
    assert result.mode == "replay_forward"


@pytest.mark.parametrize("root", ["~/.codex/sessions", "~lauer/.codex/sessions"])
def test_c6b_tilde_admission_root_rejected_before_expansion(root: str) -> None:
    cfg = {
        "index": {
            "incremental_jsonl": {
                "enabled": True,
                "embed_dimension": 8,
                "live_sources": [],
                "codex_rollout_admission": {
                    "root": root,
                    "admitted_after": "2026-01-01T00:00:00Z",
                },
            }
        }
    }
    with pytest.raises(config.IncrementalJsonlConfigError) as excinfo:
        config.incremental_jsonl_settings(cfg)
    assert excinfo.value.code == "noncanonical_path"


def test_c6b_absolute_canonical_root_still_accepted(tmp_path: Path) -> None:
    root = (tmp_path / "sessions").resolve()
    root.mkdir()
    cfg = {
        "index": {
            "incremental_jsonl": {
                "enabled": True,
                "embed_dimension": 8,
                "live_sources": [],
                "codex_rollout_admission": {
                    "root": str(root),
                    "admitted_after": "2026-01-01T00:00:00Z",
                },
            }
        }
    }
    settings = config.incremental_jsonl_settings(cfg)
    assert settings.codex_rollout_admission is not None
    assert settings.codex_rollout_admission.root == root

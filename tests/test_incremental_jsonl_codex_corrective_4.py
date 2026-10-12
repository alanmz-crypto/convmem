"""Gate-3 corrective 4 tests for Codex rollout admission (C1–C6)."""

# pylint: disable=duplicate-code,protected-access

from __future__ import annotations

import copy
from datetime import datetime, timezone
from pathlib import Path

import pytest

import config
import incremental_jsonl
import watch
from incremental_jsonl_production import ProductionBoundary
from tests.incremental_jsonl_helpers import codex_rollout_record, install_fakes
from tests.test_incremental_jsonl_codex_route_corrective import _coordinator
from tests.test_incremental_jsonl_codex_rollout_route import (
    _admitted_rollout,
    _production_cfg,
    _sessions_root,
    _write_user_config,
)
from watch import CircuitBreakerState, IndexSubprocessError


def _leave_preparing_transaction(
    boundary: ProductionBoundary,
    source: Path,
    cfg: dict,
    monkeypatch: pytest.MonkeyPatch,
) -> incremental_jsonl.IncrementalJsonlCoordinator:
    real_build = incremental_jsonl.IncrementalJsonlCoordinator._build_frontier

    def halt_build(self, *args, **kwargs):  # noqa: ANN001, ARG002
        raise RuntimeError("halt")

    monkeypatch.setattr(
        incremental_jsonl.IncrementalJsonlCoordinator,
        "_build_frontier",
        halt_build,
    )
    coord = _coordinator(boundary, source, cfg)
    with pytest.raises(RuntimeError, match="halt"):
        coord.run()
    assert incremental_jsonl._read_json(coord.paths["transaction"])["phase"] == "PREPARING"
    monkeypatch.setattr(
        incremental_jsonl.IncrementalJsonlCoordinator,
        "_build_frontier",
        real_build,
    )
    return coord


def test_c1_preparing_roll_forward_refuses_lower_chunk_cap(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
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
    boundary = ProductionBoundary(cfg, source, config_path=cfg_path)
    assert _coordinator(boundary, source, cfg).run().outcome == "committed"
    with source.open("ab") as handle:
        for index in range(12):
            handle.write(codex_rollout_record(30 + index))
    _leave_preparing_transaction(boundary, source, cfg, monkeypatch)
    cfg["index"]["incremental_jsonl"]["codex_rollout_admission"][
        "max_transform_chunks_per_run"
    ] = 1
    _write_user_config(cfg_path, cfg)
    result = _coordinator(ProductionBoundary(cfg, source, config_path=cfg_path), source, cfg).run()
    assert result.outcome == "transform_chunk_cap"
    assert result.counters.total == 0


def test_c1_preparing_roll_forward_still_commits_when_guards_pass(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
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
    boundary = ProductionBoundary(cfg, source, config_path=cfg_path)
    assert _coordinator(boundary, source, cfg).run().outcome == "committed"
    with source.open("ab") as handle:
        handle.write(codex_rollout_record(25))
    _leave_preparing_transaction(boundary, source, cfg, monkeypatch)
    result = _coordinator(ProductionBoundary(cfg, source, config_path=cfg_path), source, cfg).run()
    assert result.outcome == "committed"
    assert result.counters.total >= 0


def test_c1_rollback_reenable_pending_tx_refuses_projection_mismatch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
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
    boundary = ProductionBoundary(cfg, source, config_path=cfg_path)
    assert _coordinator(boundary, source, cfg).run().outcome == "committed"
    with source.open("ab") as handle:
        handle.write(codex_rollout_record(25))
    _leave_preparing_transaction(boundary, source, cfg, monkeypatch)
    from tests.test_incremental_jsonl_codex_route_corrective import (
        _legacy_reindex,
        _write_config_without_admission,
    )

    cfg_no_admission = copy.deepcopy(cfg)
    del cfg_no_admission["index"]["incremental_jsonl"]["codex_rollout_admission"]
    _write_config_without_admission(cfg_path, cfg_no_admission)
    _legacy_reindex(cfg_no_admission, source)
    _write_user_config(cfg_path, cfg)
    result = _coordinator(ProductionBoundary(cfg, source, config_path=cfg_path), source, cfg).run()
    assert result.outcome == "rebuild_required:projection_checkpoint_mismatch"
    assert result.counters.total == 0


def test_c2_verbose_mode_quarantines_refusal_without_respawn(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    sessions = _sessions_root(tmp_path)
    sessions.mkdir(parents=True)
    admitted = datetime(2026, 6, 1, tzinfo=timezone.utc)
    source = _admitted_rollout(sessions, admitted)
    breaker = CircuitBreakerState(tmp_path / "breaker.json")
    marker = f"live_route_refused:bootstrap_required:{'a' * 64}"
    spawn_calls = 0

    def fake_flush(_path: str, **_kwargs: object) -> None:
        nonlocal spawn_calls
        spawn_calls += 1
        raise IndexSubprocessError(marker, returncode=91, stderr=marker + "\n")

    monkeypatch.setattr(watch, "flush_path", fake_flush)
    for _ in range(3):
        watch._process_ready_path(str(source), cfg={}, breaker=breaker, verbose=True)
    assert spawn_calls == 1
    assert breaker.has_refusal_quarantine_for_path(str(source))


def test_c3_parent_never_computes_refusal_digest(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    path = str(tmp_path / "rollout.jsonl")
    Path(path).write_text("{}\n", encoding="utf-8")
    breaker = CircuitBreakerState(tmp_path / "breaker.json")

    def boom(*_args, **_kwargs):
        raise AssertionError("parent must not hash source on refusal")

    monkeypatch.setattr(
        "adapters.jsonl_prefix.streaming_complete_prefix_digest_for_path",
        boom,
    )
    watch._record_ready_path_failure(
        path,
        IndexSubprocessError(
            "live_route_refused:bootstrap_required",
            returncode=91,
            stderr="live_route_refused:bootstrap_required\n",
        ),
        breaker=breaker,
        verbose=False,
    )
    assert breaker.is_refusal_quarantined(path, "")


def test_c3_streaming_digest_bounded_memory_for_long_line(tmp_path: Path) -> None:
    import tracemalloc

    from adapters.jsonl_prefix import streaming_complete_prefix_digest_for_path

    path = tmp_path / "huge.jsonl"
    bufsize = 65536
    path.write_bytes(b"x" * (8 * 1024 * 1024))
    tracemalloc.start()
    streaming_complete_prefix_digest_for_path(path, bufsize=bufsize)
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    assert peak < 4 * bufsize


def test_c4_source_growth_before_revalidation_refuses(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    sessions = _sessions_root(tmp_path)
    sessions.mkdir(parents=True)
    admitted = datetime(2026, 6, 1, tzinfo=timezone.utc)
    source = _admitted_rollout(sessions, admitted)
    cfg = _production_cfg(tmp_path, sessions, admitted)
    ceiling = source.stat().st_size + 500
    cfg["index"]["incremental_jsonl"]["codex_rollout_admission"]["max_source_bytes"] = ceiling
    cfg_path = tmp_path / "config.toml"
    _write_user_config(cfg_path, cfg)
    monkeypatch.delenv("CONVMEM_INCREMENTAL_ROOT", raising=False)
    install_fakes(monkeypatch)
    boundary = ProductionBoundary(cfg, source, config_path=cfg_path)
    assert _coordinator(boundary, source, cfg).run().outcome == "committed"
    with source.open("ab") as handle:
        handle.write(codex_rollout_record(40))
    real_revalidate = incremental_jsonl.IncrementalJsonlCoordinator._revalidate_live_prefix
    calls = 0

    def grow_on_revalidate(self, snapshot: dict) -> None:  # noqa: ANN001
        nonlocal calls
        calls += 1
        if calls == 1:
            with source.open("ab") as handle:
                for _ in range(3):
                    handle.write(codex_rollout_record(99))
        real_revalidate(self, snapshot)

    monkeypatch.setattr(
        incremental_jsonl.IncrementalJsonlCoordinator,
        "_revalidate_live_prefix",
        grow_on_revalidate,
    )
    result = _coordinator(ProductionBoundary(cfg, source, config_path=cfg_path), source, cfg).run()
    assert result.outcome == "source_too_large"
    assert result.counters.total == 0


def test_c5_exit_one_with_marker_in_text_does_not_quarantine(
    tmp_path: Path,
) -> None:
    path = str(tmp_path / "other.jsonl")
    Path(path).write_text("{}\n", encoding="utf-8")
    breaker = CircuitBreakerState(tmp_path / "breaker.json")
    quoted = "live_route_refused:bootstrap_required:" + ("a" * 64)
    watch._record_ready_path_failure(
        path,
        IndexSubprocessError(f"error: {quoted}", returncode=1, stderr=f"error: {quoted}"),
        breaker=breaker,
        verbose=False,
    )
    assert not breaker.has_refusal_quarantine_for_path(path)


def test_c5_exit_91_without_whole_line_marker_does_not_quarantine(
    tmp_path: Path,
) -> None:
    path = str(tmp_path / "other.jsonl")
    Path(path).write_text("{}\n", encoding="utf-8")
    breaker = CircuitBreakerState(tmp_path / "breaker.json")
    watch._record_ready_path_failure(
        path,
        IndexSubprocessError("index subprocess exit 91", returncode=91, stderr="no marker"),
        breaker=breaker,
        verbose=False,
    )
    assert not breaker.has_refusal_quarantine_for_path(path)


def test_c5_exit_91_with_whole_line_marker_quarantines(tmp_path: Path) -> None:
    path = str(tmp_path / "rollout.jsonl")
    Path(path).write_text("{}\n", encoding="utf-8")
    breaker = CircuitBreakerState(tmp_path / "breaker.json")
    marker = f"live_route_refused:source_too_large:{'b' * 64}"
    watch._record_ready_path_failure(
        path,
        IndexSubprocessError(marker, returncode=91, stderr=marker + "\n"),
        breaker=breaker,
        verbose=False,
    )
    assert breaker.is_refusal_quarantined(path, "b" * 64)


@pytest.mark.parametrize(
    "root,match",
    [
        ("/tmp/../etc", r"\.\."),
        ("/tmp/./sessions", "canonical"),
        ("/tmp/x/..", r"\.\."),
    ],
)
def test_c6_noncanonical_admission_root_rejected(
    root: str, match: str,
) -> None:
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
    with pytest.raises(config.IncrementalJsonlConfigError, match=match):
        config.incremental_jsonl_settings(cfg)


def test_c6_canonical_admission_root_accepted(tmp_path: Path) -> None:
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

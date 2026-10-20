"""Verifier appendix probes for issue #286 stage-2 wedge fixes (corrective 2)."""

# pylint: disable=duplicate-code,protected-access

from __future__ import annotations

import json
import os
import tomllib
from datetime import datetime, timezone
from pathlib import Path

import pytest
from typer.testing import CliRunner

import convmem
import incremental_jsonl
import ingest
import watch
from adapters.kiro_session_jsonl import parse_complete_prefix
from incremental_jsonl_production import ProductionBoundary
from tests.incremental_jsonl_helpers import (
    apply_env,
    codex_rollout_record,
    enable_incremental,
    install_fakes,
    isolated_env,
    write_source,
)
from tests.test_incremental_jsonl_codex_rollout_route import (
    _admitted_rollout,
    _production_cfg,
    _sessions_root,
    _write_user_config,
)
from tests.test_incremental_jsonl_live_boundary import _bootstrap_binding
from watch import CircuitBreakerState, IndexSubprocessError
from watch_circuit_breaker import parse_live_route_refused


def _enable(isolated, source: Path):
    enable_incremental(isolated)
    cfg = tomllib.loads(isolated.layout["user_config"].read_text(encoding="utf-8"))
    cfg["index"]["incremental_jsonl"].update(live_sources=[str(source)], embed_dimension=8)
    return ProductionBoundary(cfg, source, config_path=isolated.layout["user_config"]), cfg


def _wedge_then_replay(tmp_path, monkeypatch, replay_point: str):
    isolated, env = isolated_env(tmp_path)
    apply_env(monkeypatch, env)
    monkeypatch.delenv("CONVMEM_INCREMENTAL_ROOT", raising=False)
    install_fakes(monkeypatch)
    source = write_source(isolated.root, 4)
    boundary, cfg = _enable(isolated, source)
    digest = parse_complete_prefix(str(source)).prefix_sha256
    common = dict(  # pylint: disable=use-dict-literal
        cfg=cfg,
        bootstrap_existing=True,
        expected_prefix_sha256=digest,
        max_bootstrap_chunks=4,
        chunk_size=2,
        **_bootstrap_binding(),
    )

    def first_crash(point: str) -> None:
        if point == "after_summary_upsert":
            raise RuntimeError("initial partial apply")

    first = incremental_jsonl.IncrementalJsonlCoordinator(
        boundary,
        source,
        processed={"old-hash": {"path": str(source)}},
        fault=first_crash,
        **common,
    )
    with first._session() as session:
        session.store.add_summary(
            "legacy-summary", "old", [0.1] * 8, {"source_path": str(source)}
        )
        session.store.add_unit(
            "legacy-unit", "old", [0.1] * 8, {"source_path": str(source)}
        )
    with pytest.raises(RuntimeError, match="initial partial apply"):
        first.run()
    with first._session() as session:
        session.store.add_summary(
            "foreign-summary", "foreign", [0.1] * 8, {"source_path": "/other"}
        )
    export_path = Path(cfg["index"]["units_export"])
    export_path.parent.mkdir(parents=True, exist_ok=True)
    foreign_line = json.dumps({"id": "foreign-unit", "source_path": "/other"}) + "\n"
    with export_path.open("a", encoding="utf-8") as handle:
        handle.write(foreign_line)

    def replay_fault(point: str) -> None:
        if point == replay_point:
            raise incremental_jsonl.IncrementalJsonlError("synthetic_replay_fault", "forced")

    replay = incremental_jsonl.IncrementalJsonlCoordinator(
        boundary, source, fault=replay_fault, **common
    )
    return replay, export_path, foreign_line, source


def _tamper_export_line(export_path: Path, source: Path) -> None:
    line = (
        json.dumps({"id": "tampered-unit", "source_path": str(source), "text": "x"})
        + "\n"
    )
    export_path.parent.mkdir(parents=True, exist_ok=True)
    with export_path.open("a", encoding="utf-8") as handle:
        handle.write(line)


def test_s1_real_rollback_path_reports_tamper(
    tmp_path, monkeypatch, capsys: pytest.CaptureFixture[str]
) -> None:
    replay, export_path, _foreign, source = _wedge_then_replay(
        tmp_path, monkeypatch, "after_summary_upsert"
    )
    _tamper_export_line(export_path, source)
    tampered = export_path.read_bytes()
    with pytest.raises(incremental_jsonl.IncrementalJsonlError, match="unowned export"):
        replay.run()
    assert export_path.read_bytes() == tampered
    assert replay.paths["rollback"].is_file()


@pytest.mark.parametrize("point", ["after_summary_upsert", "before_dedupe_reconcile"])
def test_s2_clean_rollback_reports_no_dropped_lines(
    tmp_path, monkeypatch, capsys: pytest.CaptureFixture[str], point: str
) -> None:
    replay, _export, _foreign, _src = _wedge_then_replay(tmp_path, monkeypatch, point)
    result = replay.run()
    assert result.outcome == "rolled_back", result.outcome
    assert "rollback dropped" not in capsys.readouterr().err


def _owned_export_lines(export: Path, source: Path) -> list[bytes]:
    owned: list[bytes] = []
    for raw in export.read_bytes().splitlines(keepends=True):
        row = json.loads(raw)
        if row.get("source_path") == str(source):
            owned.append(raw)
    return owned


def _commit_then_grow_codex_rollout(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    crash_point: str | None,
):
    source, cfg = _codex_env(tmp_path, monkeypatch)
    install_fakes(monkeypatch)
    cfg_path = tmp_path / "config.toml"
    _write_user_config(cfg_path, cfg)
    boundary = ProductionBoundary(cfg, source, config_path=cfg_path)
    common = dict(  # pylint: disable=use-dict-literal
        cfg=cfg,
        enabled=True,
        chunk_size=4,
        overlap=0,
        min_confidence=0.6,
        embed_dimension=8,
    )
    first = incremental_jsonl.IncrementalJsonlCoordinator(boundary, source, **common)
    assert first.run().outcome == "committed"
    export = Path(cfg["index"]["units_export"])
    before = export.read_bytes()
    assert _owned_export_lines(export, source), "first commit wrote no export lines"
    with source.open("ab") as handle:
        for index in range(8, 16):
            handle.write(codex_rollout_record(index))
    if crash_point:

        def crash(point: str) -> None:
            if point == crash_point:
                raise RuntimeError("partial apply")

        second = incremental_jsonl.IncrementalJsonlCoordinator(
            boundary, source, fault=crash, **common
        )
        with pytest.raises(RuntimeError, match="partial apply"):
            second.run()
    replay = incremental_jsonl.IncrementalJsonlCoordinator(boundary, source, **common)
    return replay, export, before, source


@pytest.mark.parametrize("crash", ["after_export_reconcile", "before_dedupe_reconcile"])
def test_s3_grown_session_clean_rollback_is_silent(
    tmp_path,
    monkeypatch,
    capsys: pytest.CaptureFixture[str],
    crash: str,
) -> None:
    replay, export, before, _source = _commit_then_grow_codex_rollout(
        tmp_path, monkeypatch, crash
    )
    assert export.read_bytes() != before
    result = replay.run()
    assert result.outcome == "rolled_back", result.outcome
    assert export.read_bytes() == before
    assert "rollback dropped" not in capsys.readouterr().err


def test_s5_preimage_line_edited_while_wedged_is_reported(
    tmp_path, monkeypatch, capsys: pytest.CaptureFixture[str]
) -> None:
    replay, export, before, source = _commit_then_grow_codex_rollout(
        tmp_path, monkeypatch, "after_export_reconcile"
    )
    target_id = json.loads(_owned_export_lines(export, source)[0])["id"]
    data = export.read_bytes()
    target = [
        row
        for row in data.splitlines(keepends=True)
        if json.loads(row).get("id") == target_id
    ][0]
    edited = dict(json.loads(target), text_tampered=True)
    export.write_bytes(data.replace(target, (json.dumps(edited) + "\n").encode()))
    result = replay.run()
    assert result.outcome == "rolled_back", result.outcome
    assert export.read_bytes() == before
    err = capsys.readouterr().err
    assert "rollback dropped 1 unexpected export lines" in err, err


def test_p1_rollback_after_foreign_growth(
    tmp_path, monkeypatch, capsys: pytest.CaptureFixture[str]
) -> None:
    replay, export_path, foreign_line, _src = _wedge_then_replay(
        tmp_path, monkeypatch, "after_summary_upsert"
    )
    result = replay.run()
    assert result.outcome == "rolled_back", result.outcome
    assert not replay.paths["transaction"].exists()
    assert foreign_line.encode() in export_path.read_bytes()
    assert "rollback dropped" not in capsys.readouterr().err


def test_p2_rollback_after_export_already_rewritten(
    tmp_path, monkeypatch, capsys: pytest.CaptureFixture[str]
) -> None:
    replay, export_path, foreign_line, _src = _wedge_then_replay(
        tmp_path, monkeypatch, "before_dedupe_reconcile"
    )
    result = replay.run()
    assert result.outcome == "rolled_back", result.outcome
    assert foreign_line.encode() in export_path.read_bytes()
    assert "rollback dropped" not in capsys.readouterr().err


def _codex_env(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.delenv("CONVMEM_INCREMENTAL_ROOT", raising=False)
    sessions = _sessions_root(tmp_path)
    sessions.mkdir(parents=True)
    admitted = datetime(2026, 6, 1, tzinfo=timezone.utc)
    source = _admitted_rollout(sessions, admitted)
    cfg = _production_cfg(tmp_path, sessions, admitted)
    return source, cfg


def _route(cfg, source):
    return incremental_jsonl.maybe_route_incremental(
        cfg=cfg,
        idx=cfg["index"],
        path=str(source),
        path_key=str(source),
        file_hash="h",
        processed={},
        models=cfg["models"],
        tool="codex",
        units_export=Path(cfg["index"]["units_export"]),
        chunk_size=4,
        overlap=0,
        min_confidence=0.0,
        force_reindex=False,
        supersede_on_reindex=False,
        verbose=False,
        detected_format="jsonl_codex_rollout",
    )


def test_p3_real_wedge_marker_through_cli_parses(tmp_path, monkeypatch) -> None:
    from adapters.codex_rollout_jsonl import parse_complete_prefix  # pylint: disable=redefined-outer-name, reimported

    source, cfg = _codex_env(tmp_path, monkeypatch)
    digest = parse_complete_prefix(str(source)).prefix_sha256

    def failing_run(self):
        self.last_failure_code = "rollback_export_foreign_changed"
        self.last_evidence["prefix_sha256"] = digest
        tx = self.paths["transaction"]
        tx.parent.mkdir(parents=True, exist_ok=True)
        tx.write_text(json.dumps({"transaction_id": "a" * 32}), encoding="utf-8")
        return self._refusal("rolled_back")

    monkeypatch.setattr(incremental_jsonl.IncrementalJsonlCoordinator, "run", failing_run)
    with pytest.raises(incremental_jsonl.IncrementalJsonlError):
        _route(cfg, source)
    with pytest.raises(incremental_jsonl.IncrementalJsonlError) as second:
        _route(cfg, source)
    assert second.value.code == "live_route_refused"

    def raising_index(**_kwargs):
        raise second.value

    monkeypatch.setattr(ingest, "index", raising_index)
    monkeypatch.setattr(convmem, "_guard_write", lambda: None)
    result = CliRunner().invoke(convmem.app, ["index", "--file", str(source), "--now"])
    stderr = getattr(result, "stderr", "") or result.output
    assert result.exit_code == 91, (result.exit_code, stderr)
    parsed = parse_live_route_refused(stderr)
    assert parsed == (
        "wedged_incremental_transaction_rollback_export_foreign_changed",
        digest,
    ), stderr
    assert "a" * 32 in stderr and str(source) in stderr


def test_p4_raised_rollback_error_is_counted(tmp_path, monkeypatch) -> None:
    source, cfg = _codex_env(tmp_path, monkeypatch)

    def raising_run(self):
        raise incremental_jsonl.IncrementalJsonlError("recovery_unproven", "rollback failed")

    monkeypatch.setattr(incremental_jsonl.IncrementalJsonlCoordinator, "run", raising_run)
    codes = []
    for _ in range(3):
        with pytest.raises(incremental_jsonl.IncrementalJsonlError) as exc:
            _route(cfg, source)
        codes.append(exc.value.code)
    assert codes[1] == "live_route_refused", codes


def test_p4b_watcher_retries_plain_errors_forever(tmp_path, monkeypatch) -> None:
    breaker = CircuitBreakerState(tmp_path / "breaker.json")
    spawns = 0

    def fake_flush(_path, **_kwargs):
        nonlocal spawns
        spawns += 1
        raise IndexSubprocessError(
            "recovery_unproven", returncode=1, stderr="Error: recovery_unproven\n"
        )

    monkeypatch.setattr(watch, "flush_path", fake_flush)
    monkeypatch.setattr(watch, "source_prefix_digest_for_watch", lambda _p: "f" * 64)
    for _ in range(5):
        watch._process_ready_path("/x/rollout.jsonl", cfg={}, breaker=breaker, verbose=False)
    assert spawns == 5


def test_p5_doctor_wedge_check_with_default_state_dir(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    from config import DEFAULT_INCREMENTAL_JSONL_STATE_DIR
    from doctor import _check_wedged_incremental_transactions
    from incremental_retry_state import record_incremental_retry_failure

    state_root = Path(os.path.expanduser(DEFAULT_INCREMENTAL_JSONL_STATE_DIR))
    tx_dir = state_root / "src1"
    tx_dir.mkdir(parents=True)
    paths = {"transaction": tx_dir / "transaction.json"}
    digest = "d" * 64
    record_incremental_retry_failure(
        paths,
        path_key="/s",
        prefix_digest=digest,
        error_code="recovery_unproven",
        transaction_id="t",
    )
    record_incremental_retry_failure(
        paths,
        path_key="/s",
        prefix_digest=digest,
        error_code="recovery_unproven",
        transaction_id="t",
    )
    cfg = {"index": {"incremental_jsonl": {"enabled": True, "embed_dimension": 8}}}
    check = _check_wedged_incremental_transactions(cfg)
    assert check.status == "warn"


def test_doctor_warns_after_two_incremental_raises_through_route(
    tmp_path, monkeypatch
) -> None:
    from doctor import _check_wedged_incremental_transactions

    source, cfg = _codex_env(tmp_path, monkeypatch)

    def raising_run(self):
        raise incremental_jsonl.IncrementalJsonlError("recovery_unproven", "rollback failed")

    monkeypatch.setattr(incremental_jsonl.IncrementalJsonlCoordinator, "run", raising_run)
    for _ in range(2):
        with pytest.raises(incremental_jsonl.IncrementalJsonlError):
            _route(cfg, source)
    check = _check_wedged_incremental_transactions(cfg)
    assert check.status == "warn"


def test_p6_rolled_back_refusal_holds_forever(tmp_path) -> None:
    breaker = CircuitBreakerState(tmp_path / "breaker.json")
    breaker.record_refusal("/x/r.jsonl", outcome="rolled_back", prefix_digest="a" * 64)
    assert breaker.should_skip_refusal_quarantine("/x/r.jsonl", "b" * 64)


def test_p7_watcher_digest_matches_coordinator_digest(tmp_path, monkeypatch) -> None:
    from adapters.detect import detect_format

    source, cfg = _codex_env(tmp_path, monkeypatch)
    cfg_path = tmp_path / "config.toml"
    _write_user_config(cfg_path, cfg)
    install_fakes(monkeypatch)
    assert detect_format(str(source)) == "jsonl_codex_rollout"
    boundary = ProductionBoundary(cfg, source, config_path=cfg_path)
    coord = incremental_jsonl.IncrementalJsonlCoordinator(
        boundary,
        source,
        cfg=cfg,
        enabled=True,
        chunk_size=4,
        overlap=0,
        min_confidence=0.6,
        embed_dimension=8,
        processed={},
    )
    result = coord.run()
    assert result.outcome == "committed"
    coordinator_digest = coord.last_evidence.get("prefix_sha256")
    watcher_digest = watch.source_prefix_digest_for_watch(str(source))
    assert coordinator_digest and watcher_digest == coordinator_digest, (
        watcher_digest,
        coordinator_digest,
    )


def test_lazy_prefix_digest_only_when_wedge_quarantine_held(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    digest_calls: list[str] = []
    monkeypatch.setattr(
        watch,
        "source_prefix_digest_for_watch",
        lambda path: digest_calls.append(path) or ("a" * 64),
    )
    monkeypatch.setattr(watch, "flush_path", lambda *_a, **_k: None)
    breaker = CircuitBreakerState(tmp_path / "breaker.json")
    watch._process_ready_path("/x/rollout.jsonl", cfg={}, breaker=breaker, verbose=False)
    assert digest_calls == []  # pylint: disable=use-implicit-booleaness-not-comparison
    breaker.record_refusal(
        "/x/rollout.jsonl",
        outcome="wedged_incremental_transaction_recovery_unproven",
        prefix_digest="a" * 64,
    )
    watch._process_ready_path("/x/rollout.jsonl", cfg={}, breaker=breaker, verbose=False)
    assert digest_calls == ["/x/rollout.jsonl"]

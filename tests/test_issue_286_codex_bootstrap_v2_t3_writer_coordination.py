"""T3 writer mediation and coordination deferral (Arc #286)."""

from __future__ import annotations

import fcntl
import json
from pathlib import Path

import pytest

from bootstrap_codex_v2_authority import claim_initial_authority, load_authority
from bootstrap_codex_v3_preparation_lease import (
    SOURCE_WRITER_BUSY_CODE,
    bootstrap_exclusive_preparation_lease,
    legacy_shared_preparation_lease,
    preparation_lease_path,
)
from bootstrap_codex_v3_writer_coordination import (
    COORDINATION_DEFERRAL_EXIT,
    CoordinationDeferralSignal,
    format_coordination_deferral,
    parse_coordination_deferral,
    should_defer_ordinary_writer,
    validate_child_deferral_signal,
)
from incremental_jsonl import LIVE_ROUTE_REFUSED_EXIT
from tests.fixtures.issue_286_t2_owner_context import t2_owner_context


def test_exit_code_disjoint_from_91_and_native() -> None:
    assert COORDINATION_DEFERRAL_EXIT not in {0, 1, LIVE_ROUTE_REFUSED_EXIT}
    assert COORDINATION_DEFERRAL_EXIT == 93


def test_coordination_marker_roundtrip() -> None:
    signal = CoordinationDeferralSignal(
        canonical_source="/tmp/a.jsonl",
        operation_id="a" * 64,
        authority_revision=3,
    )
    line = format_coordination_deferral(signal)
    parsed = parse_coordination_deferral(line)
    assert parsed == signal


def test_path_mismatch_refused() -> None:
    signal = CoordinationDeferralSignal("/tmp/a.jsonl", "b" * 64, 1)
    with pytest.raises(Exception):
        validate_child_deferral_signal(signal, launched_path="/tmp/other.jsonl")


def _state_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    from tests.test_issue_286_codex_bootstrap_v2_t1 import _rollout_fixture, _v2_grant
    from bootstrap_codex_v2 import v2_source_state_directory

    source, cfg, prefix, boundary = _rollout_fixture(tmp_path, monkeypatch)
    grant = _v2_grant(source, cfg, prefix_sha256=prefix, complete_boundary=boundary)
    state_root = Path(cfg["index"]["incremental_jsonl"]["state_dir"])
    return source, v2_source_state_directory(state_root, grant), grant, cfg


def _write_rollout(path: Path) -> None:
    path.write_text("{}" + chr(10), encoding="utf-8")


def test_exclusive_prep_lease_busy_once(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _source, state_dir, _grant, _cfg = _state_dir(tmp_path, monkeypatch)
    state_dir.mkdir(parents=True, exist_ok=True)
    path = preparation_lease_path(state_dir)
    held = path.open("a+")
    fcntl.flock(held.fileno(), fcntl.LOCK_SH)
    try:
        with t2_owner_context(state_dir):
            with pytest.raises(Exception) as exc:
                with bootstrap_exclusive_preparation_lease(state_dir):
                    pass
            assert SOURCE_WRITER_BUSY_CODE in str(exc.value)
    finally:
        fcntl.flock(held.fileno(), fcntl.LOCK_UN)
        held.close()


def test_initial_claim_under_prep_lease(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    source, state_dir, grant, _cfg = _state_dir(tmp_path, monkeypatch)
    with t2_owner_context(state_dir):
        view = claim_initial_authority(state_dir, grant)
    assert view.reservation_active
    assert load_authority(state_dir) is not None


def test_race_legacy_prep_blocks_exclusive_claim(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _source, state_dir, grant, _cfg = _state_dir(tmp_path, monkeypatch)
    with legacy_shared_preparation_lease(state_dir):
        with t2_owner_context(state_dir):
            with pytest.raises(Exception) as exc:
                claim_initial_authority(state_dir, grant)
            assert SOURCE_WRITER_BUSY_CODE in str(exc.value)


def test_active_reservation_defers_ordinary_writer(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    source, state_dir, grant, cfg = _state_dir(tmp_path, monkeypatch)
    with t2_owner_context(state_dir):
        claim_initial_authority(state_dir, grant)
    assert should_defer_ordinary_writer(cfg, str(source)) is True


def test_watch_coordination_deferral_requeues_without_refusal(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import watch
    from bootstrap_codex_v2_authority import load_authority
    from tests.fixtures.issue_286_t3_fixture import claim_active_reservation, t3_bundle

    source, cfg, grant, state_dir = t3_bundle(tmp_path, monkeypatch)
    claim_active_reservation(state_dir, grant)
    path = str(source.resolve())
    authority = load_authority(state_dir)
    assert authority is not None
    breaker = watch.CircuitBreakerState(tmp_path / "cb.json")
    signal = CoordinationDeferralSignal(path, grant["operation_id"], authority.revision)
    err = watch.IndexSubprocessError(
        signal.to_stderr_line(),
        returncode=COORDINATION_DEFERRAL_EXIT,
        stderr=signal.to_stderr_line() + "\n",
    )
    forget = watch._record_ready_path_failure(path, err, breaker=breaker, verbose=False, cfg=cfg)
    assert forget is False
    assert not breaker.has_refusal_quarantine_for_path(path)


def test_resolve_incremental_state_root_from_config_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import config
    from tests.test_issue_286_codex_bootstrap_v2_t1 import _production_cfg, _write_user_config

    sessions = tmp_path / "sessions"
    sessions.mkdir()
    admitted = __import__("datetime").datetime(2026, 6, 1, tzinfo=__import__("datetime").timezone.utc)
    cfg = _production_cfg(tmp_path, sessions, admitted)
    toml_path = tmp_path / "config.toml"
    _write_user_config(toml_path, cfg)
    monkeypatch.delenv("CONVMEM_INCREMENTAL_ROOT", raising=False)
    monkeypatch.delenv("CONVMEM_INCREMENTAL_TOKEN", raising=False)
    monkeypatch.setenv("CONVMEM_CONFIG", str(toml_path))
    monkeypatch.setattr(config, "CONFIG_PATH", toml_path)
    from bootstrap_codex_v3_writer_coordination import resolve_incremental_state_root

    expected = Path(cfg["index"]["incremental_jsonl"]["state_dir"]).expanduser().resolve()
    assert resolve_incremental_state_root(cfg) == expected




def test_terminal_after_valid_deferral_revision_bump_accepted(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from bootstrap_codex_v2_authority import publish_terminal_authority
    from tests.fixtures.issue_286_t2_owner_context import t2_owner_context
    from tests.fixtures.issue_286_t3_fixture import claim_active_reservation, t3_bundle

    source, cfg, grant, state_dir = t3_bundle(tmp_path, monkeypatch)
    claim_active_reservation(state_dir, grant)
    path = str(source.resolve())
    authority = load_authority(state_dir)
    assert authority is not None
    child_revision = authority.revision
    with t2_owner_context(state_dir):
        publish_terminal_authority(state_dir, grant, receipt_digest="c" * 64)
    signal = CoordinationDeferralSignal(path, grant["operation_id"], child_revision)
    validate_child_deferral_signal(signal, launched_path=path, cfg=cfg)


def test_fabricated_revision_after_terminal_refused(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from bootstrap_codex_v2_authority import publish_terminal_authority
    from tests.fixtures.issue_286_t2_owner_context import t2_owner_context
    from tests.fixtures.issue_286_t3_fixture import claim_active_reservation, t3_bundle

    source, cfg, grant, state_dir = t3_bundle(tmp_path, monkeypatch)
    claim_active_reservation(state_dir, grant)
    path = str(source.resolve())
    with t2_owner_context(state_dir):
        publish_terminal_authority(state_dir, grant, receipt_digest="d" * 64)
    authority = load_authority(state_dir)
    assert authority is not None
    signal = CoordinationDeferralSignal(path, grant["operation_id"], int(authority.revision) + 1)
    with pytest.raises(Exception, match="revision_mismatch"):
        validate_child_deferral_signal(signal, launched_path=path, cfg=cfg)


def test_terminal_accepts_deferral_revision_behind_multi_progress(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from bootstrap_codex_v2_authority import publish_authority_progress, publish_terminal_authority
    from tests.fixtures.issue_286_t2_owner_context import t2_owner_context
    from tests.fixtures.issue_286_t3_fixture import claim_active_reservation, t3_bundle

    source, cfg, grant, state_dir = t3_bundle(tmp_path, monkeypatch)
    claim_active_reservation(state_dir, grant)
    path = str(source.resolve())
    authority = load_authority(state_dir)
    assert authority is not None
    child_revision = int(authority.revision)
    with t2_owner_context(state_dir):
        publish_authority_progress(state_dir, grant, progress={"checkpoint_digest": "f" * 64})
        publish_authority_progress(state_dir, grant, progress={"rollback_digest": "0" * 64})
        publish_terminal_authority(state_dir, grant, receipt_digest="1" * 64)
    terminal = load_authority(state_dir)
    assert terminal is not None and int(terminal.revision) > child_revision + 1
    signal = CoordinationDeferralSignal(path, grant["operation_id"], child_revision)
    validate_child_deferral_signal(signal, launched_path=path, cfg=cfg)

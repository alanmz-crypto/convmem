"""T1 gate proofs: admission checks, validation, audit oracle, state convergence."""

from __future__ import annotations

import copy
import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from bootstrap_codex_v2 import (
    coordinator_source_state_id_for_path,
    dry_run_preflight,
    validate_grant_v2,
    v2_source_state_directory,
)
from bootstrap_safety import BootstrapGrantError
from incremental_jsonl_codex_admission import (
    CodexRolloutAdmissionSettings,
    admits_path_checks_1_4,
    make_uuid7,
    parse_rollout_basename,
)
from incremental_transform_contract import build_transform_descriptor
from tests.test_incremental_jsonl_codex_admission import _meta_for, _settings, _write_rollout
from tests.test_issue_286_codex_bootstrap_v2_t1 import _rollout_fixture, _v2_grant
from tests.test_issue_286_codex_bootstrap_v2_t1_contract import _rebind_grant
from tests.test_incremental_jsonl_codex_rollout_route import _production_cfg, _sessions_root, _write_user_config


def _admission_settings(cfg: dict) -> CodexRolloutAdmissionSettings:
    raw = cfg["index"]["incremental_jsonl"]["codex_rollout_admission"]
    return CodexRolloutAdmissionSettings(
        root=Path(raw["root"]).resolve(),
        admitted_after=datetime(2026, 6, 1, tzinfo=timezone.utc),
        max_transform_chunks_per_run=raw.get("max_transform_chunks_per_run", 20),
        max_source_bytes=raw["max_source_bytes"],
    )


def test_admission_check_1_rejects_wrong_detected_format(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    source, cfg, *_ = _rollout_fixture(tmp_path, monkeypatch)
    settings = _admission_settings(cfg)
    assert not admits_path_checks_1_4(settings, str(source), "jsonl_kiro_session")


def test_admission_check_3_rejects_invalid_rollout_basename(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    sessions = _sessions_root(tmp_path)
    sessions.mkdir(parents=True, exist_ok=True)
    bad = sessions / "2026" / "09" / "not-a-valid-rollout-name.jsonl"
    bad.parent.mkdir(parents=True, exist_ok=True)
    bad.write_text("{}\n", encoding="utf-8")
    settings = _admission_settings(_production_cfg(tmp_path, sessions, datetime(2026, 6, 1, tzinfo=timezone.utc)))
    assert not admits_path_checks_1_4(settings, str(bad.resolve()), "jsonl_codex_rollout")
    with pytest.raises(ValueError):
        parse_rollout_basename(bad)


def test_admission_check_4_rejects_before_admitted_after(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    sessions = _sessions_root(tmp_path)
    admitted = datetime(2026, 6, 1, tzinfo=timezone.utc)
    early_uid = make_uuid7(int((admitted - timedelta(days=30)).timestamp() * 1000))
    uid = str(early_uid)
    local = datetime.fromtimestamp((early_uid.int >> 80) / 1000.0)
    source = _write_rollout(
        sessions,
        uid,
        filename_local=local,
        session_meta=_meta_for(uid, datetime.fromtimestamp((early_uid.int >> 80) / 1000.0, tz=timezone.utc)),
    )
    cfg = _production_cfg(tmp_path, sessions, admitted)
    settings = _admission_settings(cfg)
    assert not admits_path_checks_1_4(settings, str(source), "jsonl_codex_rollout")


def test_admission_rejects_duplicate_session_prefix_alias(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    sessions = _sessions_root(tmp_path)
    admitted = datetime(2026, 6, 1, tzinfo=timezone.utc)
    settings = _admission_settings(_production_cfg(tmp_path, sessions, admitted))
    uid_obj = make_uuid7(int(admitted.timestamp() * 1000) + 5_000)
    uid = str(uid_obj)
    uuid_dt = datetime.fromtimestamp((uid_obj.int >> 80) / 1000.0, tz=timezone.utc)
    local = datetime.fromtimestamp((uid_obj.int >> 80) / 1000.0)
    original = _write_rollout(sessions, uid, filename_local=local, session_meta=_meta_for(uid, uuid_dt))
    assert admits_path_checks_1_4(settings, str(original), "jsonl_codex_rollout")
    copy = _write_rollout(
        sessions,
        uid,
        filename_local=local + timedelta(hours=1),
        session_meta=_meta_for(uid, uuid_dt),
        extra_lines=1,
    )
    assert not admits_path_checks_1_4(settings, str(copy), "jsonl_codex_rollout")


def test_v2_validate_rejects_cross_format_kiro_source(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    source, cfg, prefix, boundary = _rollout_fixture(tmp_path, monkeypatch)
    kiro_path = source.parent / "kiro-session.jsonl"
    kiro_path.write_text('{"type":"session_meta"}\n', encoding="utf-8")
    grant = _rebind_grant(_v2_grant(source, cfg, prefix_sha256=prefix, complete_boundary=boundary), source=str(kiro_path.resolve()))
    with pytest.raises(BootstrapGrantError, match="grant source"):
        validate_grant_v2(grant)


def test_v2_preflight_rejects_invalid_checkpoint_history(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    packet, grant, cfg, source, state_root = _preflight_bundle(tmp_path, monkeypatch)
    state_dir = state_root / packet["source_state_id"]
    state_dir.mkdir(parents=True, exist_ok=True)
    (state_dir / "checkpoint.json").write_text(json.dumps({"incomplete": True}), encoding="utf-8")
    packet = dry_run_preflight(grant, cfg=cfg, state_root=state_root)
    assert "checkpoint_present" in packet["blockers"] or any(
        b.startswith("ineligible:") for b in packet["blockers"]
    )


def test_validate_rejects_bool_masquerading_as_int(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _, grant, *_ = _preflight_bundle(tmp_path, monkeypatch)
    grant = _rebind_grant(grant, max_chunks=True)
    with pytest.raises(BootstrapGrantError, match="positive integer"):
        validate_grant_v2(grant)


def test_validate_rejects_grant_version_bool(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _, grant, *_ = _preflight_bundle(tmp_path, monkeypatch)
    grant = copy.deepcopy(grant)
    grant["grant_version"] = True
    with pytest.raises(BootstrapGrantError, match="grant_version"):
        validate_grant_v2(grant)


def test_validate_rejects_descriptor_digest_mismatch(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _, grant, *_ = _preflight_bundle(tmp_path, monkeypatch)
    grant = _rebind_grant(grant, transform_fingerprint="0" * 64)
    with pytest.raises(BootstrapGrantError, match="digest"):
        validate_grant_v2(grant)


def test_validate_rejects_symlink_source(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from incremental_jsonl_isolation import SourceCaptureError

    source, cfg, prefix, boundary = _rollout_fixture(tmp_path, monkeypatch)
    link = source.parent / "alias.jsonl"
    link.symlink_to(source)
    grant = _rebind_grant(_v2_grant(source, cfg, prefix_sha256=prefix, complete_boundary=boundary), source=str(link))
    with pytest.raises((BootstrapGrantError, SourceCaptureError)):
        validate_grant_v2(grant)


def test_state_directory_matches_coordinator_derivation(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    source, cfg, prefix, boundary = _rollout_fixture(tmp_path, monkeypatch)
    grant = _v2_grant(source, cfg, prefix_sha256=prefix, complete_boundary=boundary)
    state_root = Path(cfg["index"]["incremental_jsonl"]["state_dir"])
    expected = v2_source_state_directory(state_root, grant)
    coordinator_id = coordinator_source_state_id_for_path(str(source))
    assert expected == state_root / coordinator_id
    packet = dry_run_preflight(grant, cfg=cfg, state_root=state_root)
    assert packet["coordinator_state_dir"] == str(expected)


def _preflight_bundle(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    source, cfg, prefix, boundary = _rollout_fixture(tmp_path, monkeypatch)
    grant = _v2_grant(source, cfg, prefix_sha256=prefix, complete_boundary=boundary)
    state_root = Path(cfg["index"]["incremental_jsonl"]["state_dir"])
    packet = dry_run_preflight(grant, cfg=cfg, state_root=state_root)
    return packet, grant, cfg, source, state_root


def test_dry_run_audit_ready_path_zero_calls_and_no_mutations(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CONVMEM_BOOTSTRAP_V2_DRY_RUN_AUDIT", "1")
    packet, grant, cfg, _, state_root = _preflight_bundle(tmp_path, monkeypatch)
    audit = packet["dry_run_audit"]
    assert audit["provider_permit_attempts"] == 0
    assert audit["coordinator_constructions"] == 0
    assert audit["journal_constructions"] == 0
    assert audit["mkdir_attempts"] == 0
    assert audit["surface_unchanged"] is True
    assert packet["ready"] is True


def test_dry_run_audit_refusal_path_still_immutable(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CONVMEM_BOOTSTRAP_V2_DRY_RUN_AUDIT", "1")
    packet, grant, cfg, _, state_root = _preflight_bundle(tmp_path, monkeypatch)
    state_dir = state_root / packet["source_state_id"]
    state_dir.mkdir(parents=True, exist_ok=True)
    (state_dir / "checkpoint.json").write_text("{}", encoding="utf-8")
    packet = dry_run_preflight(grant, cfg=cfg, state_root=state_root)
    assert packet["ready"] is False
    audit = packet["dry_run_audit"]
    assert audit["surface_unchanged"] is True
    assert audit["provider_permit_attempts"] == 0

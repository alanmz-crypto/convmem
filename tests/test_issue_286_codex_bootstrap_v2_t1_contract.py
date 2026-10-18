"""T1 contract proofs: admission, refusals, strict grant shape, dry-run preflight."""

from __future__ import annotations

import copy
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from bootstrap_codex_v2 import (
    dry_run_preflight,
    parse_v2_grant_document,
    validate_grant_v2,
)
from bootstrap_safety import BootstrapGrantError
from bootstrap_supersession import SUPERSESSION_DOCUMENT_KEY
from incremental_jsonl_codex_admission import make_uuid7
from tests.test_incremental_jsonl_codex_admission import _meta_for, _write_rollout
from tests.test_issue_286_codex_bootstrap_v2_t1 import (
    _rollout_fixture,
    _v2_grant,
)



def _rebind_grant(grant: dict, **updates) -> dict:
    import copy

    from bootstrap_codex_v2 import operation_identity_v2
    from incremental_jsonl import source_state_id

    body = copy.deepcopy(grant)
    body.update(updates)
    if "source" in updates:
        source = Path(body["source"])
        body["source_state_id"] = source_state_id(str(source), format_id="jsonl_codex_rollout")
        stat = source.stat()
        body["source_device"] = stat.st_dev
        body["source_inode"] = stat.st_ino
    body.pop("operation_id", None)
    body["operation_id"] = operation_identity_v2(body)
    return body



def _preflight(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, **grant_overrides):
    source, cfg, prefix, boundary = _rollout_fixture(tmp_path, monkeypatch)
    grant = _v2_grant(source, cfg, prefix_sha256=prefix, complete_boundary=boundary)
    grant.update(grant_overrides)
    state_root = Path(cfg["index"]["incremental_jsonl"]["state_dir"])
    return dry_run_preflight(grant, cfg=cfg, state_root=state_root), grant, cfg, source, state_root


def test_preflight_ready_for_bootstrap_required(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    packet, *_ = _preflight(tmp_path, monkeypatch)
    assert packet["blockers"] == []
    assert packet["ready"] is True
    assert packet["proposed_chunk_count"] >= 1


def test_preflight_prefix_mismatch(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import copy

    packet, grant, cfg, _, state_root = _preflight(tmp_path, monkeypatch)
    grant = _rebind_grant(grant, prefix_sha256="0" * 64)
    packet = dry_run_preflight(grant, cfg=cfg, state_root=state_root)
    assert "prefix_mismatch" in packet["blockers"]


def test_preflight_chunk_cap_exceeded(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from tests.incremental_jsonl_helpers import codex_rollout_record
    from incremental_jsonl_formats import get_format_spec

    packet, grant, cfg, source, state_root = _preflight(tmp_path, monkeypatch)
    extra = "".join(codex_rollout_record(i).decode("utf-8") for i in range(8))
    source.write_text(source.read_text() + extra, encoding="utf-8")
    spec = get_format_spec("jsonl_codex_rollout")
    view = spec.parse_complete_prefix(str(source))
    grant = _rebind_grant(
        grant,
        prefix_sha256=view.prefix_sha256,
        complete_boundary=view.complete_boundary,
        max_chunks=1,
    )
    packet = dry_run_preflight(grant, cfg=cfg, state_root=state_root)
    assert packet["proposed_chunk_count"] > grant["max_chunks"]
    assert "chunk_cap_exceeded" in packet["blockers"]



def test_preflight_session_identity_check_5(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import copy

    packet, grant, cfg, source, state_root = _preflight(tmp_path, monkeypatch)
    lines = source.read_text(encoding="utf-8").splitlines()
    meta = json.loads(lines[0])
    meta["payload"]["id"] = "00000000-0000-7000-8000-000000000001"
    lines[0] = json.dumps(meta, sort_keys=True)
    source.write_text("\n".join(lines) + "\n", encoding="utf-8")
    from incremental_jsonl_formats import get_format_spec

    spec = get_format_spec("jsonl_codex_rollout")
    view = spec.parse_complete_prefix(str(source))
    grant = _rebind_grant(grant, prefix_sha256=view.prefix_sha256, complete_boundary=view.complete_boundary)
    packet = dry_run_preflight(grant, cfg=cfg, state_root=state_root)
    assert "codex_session_identity_mismatch" in packet["blockers"]


def test_preflight_admission_rejected_outside_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    packet, grant, cfg, _, state_root = _preflight(tmp_path, monkeypatch)
    outside = tmp_path / "outside-rollout.jsonl"
    outside.write_text("{}\n", encoding="utf-8")
    grant["source"] = str(outside.resolve())
    with pytest.raises(BootstrapGrantError):
        validate_grant_v2(grant)


def test_admission_predicate_rejects_outside_sessions_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from incremental_jsonl_codex_admission import CodexRolloutAdmissionSettings, admits_path_checks_1_4

    packet, grant, cfg, source, _state_root = _preflight(tmp_path, monkeypatch)
    settings = cfg["index"]["incremental_jsonl"]["codex_rollout_admission"]
    admitted = datetime(2026, 6, 1, tzinfo=timezone.utc)
    admission = CodexRolloutAdmissionSettings(
        root=Path(settings["root"]).resolve(),
        admitted_after=admitted,
        max_transform_chunks_per_run=settings.get("max_transform_chunks_per_run", 20),
        max_source_bytes=settings["max_source_bytes"],
    )
    outside = tmp_path / "outside-sessions" / source.name
    outside.parent.mkdir(parents=True)
    outside.write_bytes(source.read_bytes())
    assert not admits_path_checks_1_4(admission, str(outside.resolve()), "jsonl_codex_rollout")
    packet = dry_run_preflight(grant, cfg=cfg, state_root=_state_root)
    assert packet["ready"] is True




def test_preflight_checkpoint_and_transaction_refused(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    packet, grant, cfg, _, state_root = _preflight(tmp_path, monkeypatch)
    sid = packet["source_state_id"]
    state_dir = state_root / sid
    state_dir.mkdir(parents=True, exist_ok=True)
    (state_dir / "checkpoint.json").write_text("{}", encoding="utf-8")
    packet = dry_run_preflight(grant, cfg=cfg, state_root=state_root)
    assert "checkpoint_present" in packet["blockers"]
    (state_dir / "checkpoint.json").unlink()
    (state_dir / "transaction.json").write_text("{}", encoding="utf-8")
    packet = dry_run_preflight(grant, cfg=cfg, state_root=state_root)
    assert "transaction_present" in packet["blockers"]


def test_preflight_retry_state_refused(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    packet, grant, cfg, _, state_root = _preflight(tmp_path, monkeypatch)
    state_dir = state_root / packet["source_state_id"]
    state_dir.mkdir(parents=True, exist_ok=True)
    (state_dir / "retry_state.json").write_text(
        json.dumps({"outcome": "transform_failed"}), encoding="utf-8"
    )
    packet = dry_run_preflight(grant, cfg=cfg, state_root=state_root)
    assert any(b.startswith("retry_state:") for b in packet["blockers"])


def test_preflight_supersession_evidence_refused(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    packet, grant, cfg, _, state_root = _preflight(tmp_path, monkeypatch)
    state_dir = state_root / packet["source_state_id"]
    state_dir.mkdir(parents=True, exist_ok=True)
    lineage = state_dir / "bootstrap_supersession_lineage"
    lineage.mkdir(parents=True, exist_ok=True)
    (lineage / "pred-tx.json").write_text(
        json.dumps({"predecessor_transaction_id": "pred-tx", "successor_operation_id": "x"}),
        encoding="utf-8",
    )
    packet = dry_run_preflight(grant, cfg=cfg, state_root=state_root)
    assert "supersession_evidence_present" in packet["blockers"]


def test_validate_rejects_extra_field(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _, grant, *_ = _preflight(tmp_path, monkeypatch)
    grant = dict(grant)
    grant["unexpected"] = True
    with pytest.raises(BootstrapGrantError, match="exactly"):
        validate_grant_v2(grant)


def test_validate_rejects_wrong_grant_version(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _, grant, *_ = _preflight(tmp_path, monkeypatch)
    grant = copy.deepcopy(grant)
    grant["grant_version"] = 1
    with pytest.raises(BootstrapGrantError, match="grant_version"):
        validate_grant_v2(grant)


def test_validate_rejects_v2_supersession_document(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _, grant, *_ = _preflight(tmp_path, monkeypatch)
    document = dict(grant)
    document[SUPERSESSION_DOCUMENT_KEY] = {}
    with pytest.raises(BootstrapGrantError, match="supersession"):
        parse_v2_grant_document(document)


def test_validate_rejects_inode_mismatch(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _, grant, *_ = _preflight(tmp_path, monkeypatch)
    grant = copy.deepcopy(grant)
    grant["source_inode"] = grant["source_inode"] + 1
    with pytest.raises(BootstrapGrantError, match="inode"):
        validate_grant_v2(grant)


def test_validate_rejects_source_over_max_bytes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _, grant, cfg, source, state_root = _preflight(tmp_path, monkeypatch)
    grant = copy.deepcopy(grant)
    grant["max_source_bytes"] = 1
    with pytest.raises(BootstrapGrantError, match="max_source_bytes"):
        validate_grant_v2(grant)


def test_preflight_codex_admission_rejected_blocker(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import copy

    packet, grant, cfg, _, state_root = _preflight(tmp_path, monkeypatch)
    cfg = copy.deepcopy(cfg)
    narrow = tmp_path / "narrow-admission-root"
    narrow.mkdir()
    cfg["index"]["incremental_jsonl"]["codex_rollout_admission"]["root"] = str(narrow)
    packet = dry_run_preflight(grant, cfg=cfg, state_root=state_root)
    assert "codex_admission_rejected" in packet["blockers"]

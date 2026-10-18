"""T1 hermetic evidence: v2 grant shape, hashes, dry-run immutability, v1 compatibility."""

from __future__ import annotations

import copy
import json
import os
from datetime import datetime, timezone
from pathlib import Path

import pytest

from bootstrap_codex_v2 import (
    GRANT_FIELDS_V2,
    grant_fingerprint_v2,
    operation_identity_v2,
    parse_v2_grant_document,
    validate_grant_v2,
)
from bootstrap_safety import GRANT_FIELDS, operation_identity, validate_grant
from bootstrap_supersession import parse_grant_document
from incremental_jsonl import source_state_id
from incremental_jsonl_formats import get_format_spec
from incremental_transform_contract import build_transform_descriptor
from tests.test_incremental_jsonl_bootstrap_command import _binding, _grant
from tests.test_incremental_jsonl_codex_admission import _meta_for, _write_rollout
from tests.test_incremental_jsonl_codex_rollout_route import (
    _production_cfg,
    _sessions_root,
    _write_user_config,
)


def _descriptor_digest(cfg: dict) -> tuple[dict, str]:
    models = cfg["models"]
    spec = get_format_spec("jsonl_codex_rollout")
    assert spec is not None
    descriptor = build_transform_descriptor(
        chunk_size=cfg["index"].get("chunk_size", 4),
        overlap=cfg["index"].get("chunk_overlap", 0),
        min_confidence=0.6,
        models=models,
        embed_dimension=cfg["index"]["incremental_jsonl"]["embed_dimension"],
        adapter_format=spec.format_id,
        adapter_contract_version=spec.adapter_contract_version,
    )
    return descriptor.body, descriptor.digest


def _v2_grant_body(
    source: Path,
    cfg: dict,
    *,
    prefix_sha256: str,
    complete_boundary: int,
    max_chunks: int = 3,
) -> dict:
    path_key = str(source.resolve())
    spec = get_format_spec("jsonl_codex_rollout")
    assert spec is not None
    view = spec.parse_complete_prefix(path_key)
    assert view.prefix_sha256 == prefix_sha256
    assert view.complete_boundary == complete_boundary
    descriptor_body, digest = _descriptor_digest(cfg)
    st = source.stat()
    uid, _ = __import__(
        "incremental_jsonl_codex_admission", fromlist=["parse_rollout_basename"]
    ).parse_rollout_basename(source)
    body = {
        "grant_version": 2,
        "adapter_format": "jsonl_codex_rollout",
        "adapter_contract_version": spec.adapter_contract_version,
        "coordination_protocol_version": 1,
        "source_state_id": source_state_id(path_key, format_id="jsonl_codex_rollout"),
        "session_id": str(uid),
        "source_device": st.st_dev,
        "source_inode": st.st_ino,
        "max_source_bytes": cfg["index"]["incremental_jsonl"]["codex_rollout_admission"][
            "max_source_bytes"
        ],
        "lock_wait_seconds": 30,
        "transform_descriptor": descriptor_body,
        "recovery_protocol_version": 1,
        "outer_budget_authority_sha256": "f" * 64,
        "source": path_key,
        "prefix_sha256": prefix_sha256,
        "complete_boundary": complete_boundary,
        "max_chunks": max_chunks,
        "embed_dimension": cfg["index"]["incremental_jsonl"]["embed_dimension"],
        "backup_snapshot": "e" * 64,
        "runtime_revision": "b" * 40,
        "config_sha256": "c" * 64,
        "transform_fingerprint": digest,
        "chunk_size": cfg["index"].get("chunk_size", 4),
        "chunk_overlap": cfg["index"].get("chunk_overlap", 0),
        "min_confidence": 0.6,
        "summarize_provider": "ollama",
        "summarize_model": "summary-model",
        "summarize_base_url": "http://provider.invalid",
        "distill_provider": "deepseek",
        "distill_model": "deepseek-v4-test",
        "distill_base_url": "https://provider.invalid",
        "embedding_provider": "ollama",
        "embedding_model": "embed-model",
        "embedding_base_url": "http://provider.invalid",
        "max_provider_http_attempts": 12,
        "max_recovery_invocations": 1,
    }
    return body


def _v2_grant(source: Path, cfg: dict, **kwargs) -> dict:
    body = _v2_grant_body(source, cfg, **kwargs)
    return {"operation_id": operation_identity_v2(body), **body}


def _rollout_fixture(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    sessions = _sessions_root(tmp_path)
    sessions.mkdir(parents=True)
    admitted = datetime(2026, 6, 1, tzinfo=timezone.utc)
    from incremental_jsonl_codex_admission import make_uuid7

    uid_obj = make_uuid7(int(admitted.timestamp() * 1000) + 5)
    uid = str(uid_obj)
    local = datetime.fromtimestamp((uid_obj.int >> 80) / 1000.0)
    source = _write_rollout(
        sessions,
        uid,
        filename_local=local,
        session_meta=_meta_for(
            uid,
            datetime.fromtimestamp((uid_obj.int >> 80) / 1000.0, tz=timezone.utc),
        ),
    )
    cfg = _production_cfg(tmp_path, sessions, admitted)
    cfg_path = tmp_path / "config.toml"
    _write_user_config(cfg_path, cfg)
    monkeypatch.setenv("CONVMEM_CONFIG", str(cfg_path))
    spec = get_format_spec("jsonl_codex_rollout")
    view = spec.parse_complete_prefix(str(source))
    return source, cfg, view.prefix_sha256, view.complete_boundary


def test_v1_grant_parse_unchanged(tmp_path: Path) -> None:
    grant = _grant(tmp_path / "source.jsonl")
    document = dict(grant)
    parsed, supersession = parse_grant_document(document)
    assert supersession is None
    assert parsed == validate_grant(grant)
    assert set(parsed) == GRANT_FIELDS


def test_v2_hash_vectors_independent_oracle(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    source, cfg, prefix, boundary = _rollout_fixture(tmp_path, monkeypatch)
    grant = _v2_grant(source, cfg, prefix_sha256=prefix, complete_boundary=boundary)
    assert set(grant) == GRANT_FIELDS_V2
    expected_op = operation_identity_v2({k: v for k, v in grant.items() if k != "operation_id"})
    assert grant["operation_id"] == expected_op
    assert grant_fingerprint_v2(grant) != operation_identity(grant)
    validate_grant_v2(grant)
    parsed, supersession = parse_grant_document(grant)
    assert supersession is None
    assert parsed["operation_id"] == expected_op


def test_v2_rejects_kiro_default_state_id(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    source, cfg, prefix, boundary = _rollout_fixture(tmp_path, monkeypatch)
    grant = _v2_grant(source, cfg, prefix_sha256=prefix, complete_boundary=boundary)
    grant["source_state_id"] = source_state_id(str(source))
    with pytest.raises(Exception, match="source_state_id"):
        validate_grant_v2(grant)


def test_dry_run_no_writes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import runpy

    source, cfg, prefix, boundary = _rollout_fixture(tmp_path, monkeypatch)
    cfg_path = tmp_path / "config.toml"
    grant = _v2_grant(source, cfg, prefix_sha256=prefix, complete_boundary=boundary)
    grant_path = tmp_path / "grant.json"
    grant_path.write_text(json.dumps(grant), encoding="utf-8")
    grant_path.chmod(0o600)
    state_root = Path(cfg["index"]["incremental_jsonl"]["state_dir"])
    before = {
        p: p.stat().st_mtime_ns if p.exists() else None
        for p in (
            state_root,
            Path(cfg["index"]["processed_log"]),
            Path(cfg["index"]["chroma_dir"]),
        )
    }
    import config

    monkeypatch.setenv("CONVMEM_CONFIG", str(cfg_path))
    monkeypatch.setattr(config, "CONFIG_PATH", cfg_path)
    script = Path(__file__).resolve().parents[1] / "scripts" / "bootstrap-incremental-jsonl.py"
    ns = runpy.run_path(str(script), run_name="dry_run_test")
    packet = ns["dry_run_v2"](grant_path)
    after = {
        p: p.stat().st_mtime_ns if p.exists() else None
        for p in before
    }
    assert before == after
    assert packet["source_state_id"] != packet["kiro_default_state_id"]
    assert packet["grant_fingerprint_v2"] == grant_fingerprint_v2(grant)

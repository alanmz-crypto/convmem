# pylint: disable=duplicate-code
"""T1 gates: shadow config, activation manifest, no-sink defaults."""

from __future__ import annotations

import json
import os
import stat
import tomllib
from pathlib import Path

import pytest

from chroma_write_store import open_chroma_for_write
from shadow_ledger import (
    atomic_write_json_private,
    decide_sink_injection,
    finalize_manifest,
    load_manifest,
    manifest_is_complete,
    new_incomplete_manifest,
    projection_state_hash,
    resolve_shadow_settings,
    runtime_stamp,
    sha256_canonical,
)


def _write_cfg(path: Path, body: str) -> Path:
    path.write_text(body, encoding="utf-8")
    return path


def test_absent_table_equals_enabled_false(tmp_path: Path) -> None:
    cfg_a = {"index": {"chroma_dir": str(tmp_path / "chroma")}}
    cfg_b = {
        "index": {"chroma_dir": str(tmp_path / "chroma")},
        "shadow_ledger": {
            "enabled": False,
            "ledger_path": str(tmp_path / "ledger.jsonl"),
            "activation_manifest_path": str(tmp_path / "act.json"),
            "health_path": str(tmp_path / "health.json"),
        },
    }
    sa = resolve_shadow_settings(cfg_a)
    sb = resolve_shadow_settings(cfg_b)
    assert sa.enabled is False and sb.enabled is False
    da = decide_sink_injection(cfg_a, chroma_dir=tmp_path / "chroma")
    db = decide_sink_injection(cfg_b, chroma_dir=tmp_path / "chroma")
    assert da.inject is False and db.inject is False
    assert "enabled=false" in da.reason or "absent" in da.reason


def test_enabled_true_without_manifest_refuses(tmp_path: Path) -> None:
    chroma = tmp_path / "chroma"
    chroma.mkdir()
    cfg = {
        "index": {"chroma_dir": str(chroma)},
        "shadow_ledger": {
            "enabled": True,
            "ledger_path": str(tmp_path / "ledger.jsonl"),
            "activation_manifest_path": str(tmp_path / "missing.json"),
            "health_path": str(tmp_path / "health.json"),
        },
    }
    decision = decide_sink_injection(cfg, chroma_dir=chroma)
    assert decision.inject is False
    assert "incomplete" in decision.reason or "missing" in decision.reason


def test_incomplete_manifest_cannot_enable(tmp_path: Path) -> None:
    chroma = tmp_path / "chroma"
    chroma.mkdir()
    manifest_path = tmp_path / "act.json"
    incomplete = new_incomplete_manifest(
        code_commit="abc123",
        chroma_root=chroma,
        configured_embed_model="nomic-embed-text",
    )
    atomic_write_json_private(manifest_path, incomplete)
    assert manifest_is_complete(load_manifest(manifest_path)) is False
    mode = stat.S_IMODE(manifest_path.stat().st_mode)
    assert mode == 0o600
    cfg = {
        "index": {"chroma_dir": str(chroma)},
        "shadow_ledger": {
            "enabled": True,
            "ledger_path": str(tmp_path / "ledger.jsonl"),
            "activation_manifest_path": str(manifest_path),
            "health_path": str(tmp_path / "health.json"),
        },
    }
    assert decide_sink_injection(cfg, chroma_dir=chroma).inject is False


def test_complete_manifest_root_mismatch_refuses(tmp_path: Path) -> None:
    chroma_a = tmp_path / "chroma_a"
    chroma_b = tmp_path / "chroma_b"
    chroma_a.mkdir()
    chroma_b.mkdir()
    manifest_path = tmp_path / "act.json"
    base = new_incomplete_manifest(
        code_commit="abc123",
        chroma_root=chroma_a,
        configured_embed_model="nomic-embed-text",
    )
    complete = finalize_manifest(
        base,
        entity_baselines={
            "u1": {
                "document_hash": sha256_canonical("doc"),
                "metadata_hash": sha256_canonical({"k": "v"}),
                "state_hash": projection_state_hash(
                    stable_entity_id="u1",
                    deleted=False,
                    document="doc",
                    metadata={"k": "v"},
                ),
            }
        },
        active_unit_count=1,
        total_unit_count=1,
        observed_embed_model="unknown",
        observed_embed_dimensions=None,
        shadow_ledger_identity="ledger-id-1",
    )
    atomic_write_json_private(manifest_path, complete)
    assert manifest_is_complete(complete)
    cfg = {
        "index": {"chroma_dir": str(chroma_b)},
        "shadow_ledger": {
            "enabled": True,
            "ledger_path": str(tmp_path / "ledger.jsonl"),
            "activation_manifest_path": str(manifest_path),
            "health_path": str(tmp_path / "health.json"),
        },
    }
    decision = decide_sink_injection(cfg, chroma_dir=chroma_b)
    assert decision.inject is False
    assert "mismatch" in decision.reason


def test_complete_matching_manifest_eligible(tmp_path: Path) -> None:
    chroma = tmp_path / "chroma"
    chroma.mkdir()
    manifest_path = tmp_path / "act.json"
    base = new_incomplete_manifest(
        code_commit="abc123",
        chroma_root=chroma,
        configured_embed_model="nomic-embed-text",
    )
    complete = finalize_manifest(
        base,
        entity_baselines={},
        active_unit_count=0,
        total_unit_count=0,
        observed_embed_model="unknown",
        observed_embed_dimensions=None,
        shadow_ledger_identity="ledger-id-1",
    )
    atomic_write_json_private(manifest_path, complete)
    cfg = {
        "index": {"chroma_dir": str(chroma)},
        "shadow_ledger": {
            "enabled": True,
            "ledger_path": str(tmp_path / "ledger.jsonl"),
            "activation_manifest_path": str(manifest_path),
            "health_path": str(tmp_path / "health.json"),
        },
    }
    decision = decide_sink_injection(cfg, chroma_dir=chroma)
    assert decision.inject is True


def test_config_example_shadow_ledger_disabled() -> None:
    root = Path(__file__).resolve().parents[1]
    example = root / "config.example.toml"
    with open(example, "rb") as handle:
        data = tomllib.load(handle)
    section = data.get("shadow_ledger")
    assert isinstance(section, dict)
    assert section.get("enabled") is False


def test_load_config_expands_shadow_paths(tmp_path: Path, monkeypatch) -> None:  # pylint: disable=unused-argument
    from config import load_config

    cfg_path = tmp_path / "config.toml"
    _write_cfg(
        cfg_path,
        """
[index]
chroma_dir = "~/chroma-test"

[shadow_ledger]
enabled = false
ledger_path = "~/shadow/ledger.jsonl"
activation_manifest_path = "~/shadow/act.json"
health_path = "~/shadow/health.json"
""",
    )
    cfg = load_config(cfg_path)
    assert cfg["shadow_ledger"]["ledger_path"].startswith(str(Path.home()))
    assert "~" not in cfg["shadow_ledger"]["ledger_path"]


def test_runtime_stamp_has_no_hardcoded_audit_counts() -> None:
    stamp = runtime_stamp(
        code_commit="deadbeef",
        chroma_root="/tmp/chroma",
        active_count=7,
        total_count=9,
    )
    blob = json.dumps(stamp)
    assert "192" not in blob
    assert "3448" not in blob
    assert stamp["active_unit_count"] == 7


def test_atomic_write_fsyncs_file_and_parent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """V2g: baseline write uses file fsync + parent-directory fsync."""
    calls: list[str] = []
    real_fsync = os.fsync

    def spy(fd: int) -> None:
        calls.append("fsync")
        return real_fsync(fd)

    monkeypatch.setattr(os, "fsync", spy)
    path = tmp_path / "act.json"
    atomic_write_json_private(path, {"ok": True, "status": "complete"})
    assert path.is_file()
    assert stat.S_IMODE(path.stat().st_mode) == 0o600
    assert len(calls) >= 2  # file + parent dir


def test_purpose_test_forces_no_sink(tmp_path: Path) -> None:
    pytest.importorskip("chromadb")
    chroma = tmp_path / "chroma"
    chroma.mkdir()
    cfg = {
        "index": {"chroma_dir": str(chroma)},
        "shadow_ledger": {"enabled": True},
    }
    store, decision = open_chroma_for_write(cfg, chroma, purpose="test")
    try:
        assert decision.inject is False
        assert store.mutation_sink is None
    finally:
        store.close()


def test_open_chroma_for_write_no_sink_when_disabled(
    tmp_path: Path, monkeypatch  # pylint: disable=unused-argument
) -> None:
    chroma = tmp_path / "chroma"
    # Avoid needing a real chromadb if import fails in minimal envs — skip.
    pytest.importorskip("chromadb")
    cfg = {
        "index": {"chroma_dir": str(chroma)},
        "shadow_ledger": {"enabled": False},
    }
    store, decision = open_chroma_for_write(cfg, chroma, purpose="production")
    try:
        assert decision.inject is False
        assert getattr(store, "mutation_sink", None) in (None, False)
    finally:
        store.close()


def test_phase0_contract_doc_exists() -> None:
    root = Path(__file__).resolve().parents[1]
    path = root / "docs/plans/PHASE0-SHADOW-CONTRACT.md"
    text = path.read_text(encoding="utf-8")
    assert "Tier-1" in text
    assert "post-activation delta" in text
    assert (
        "canonical observation-schema" in text.lower()
        or "not** a canonical" in text.lower()
        or "not a canonical" in text.lower()
    )

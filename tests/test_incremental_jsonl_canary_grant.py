"""Hermetic grant, boundary, and Gate 0 tests for the JSONL production canary."""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

import pytest

from incremental_jsonl_canary import (
    CanaryGrant,
    CanaryRefused,
    decode_grant,
    gate0_watcher_probe,
    prove_cli_watcher_unreachable,
    validate_grant,
    write_canary_overlay,
)
from incremental_jsonl_isolation import IsolationBoundary
from tests.incremental_jsonl_canary_helpers import (
    build_grant,
    hermetic_root,
    write_grant_file,
    write_kiro_source,
)


def test_p1_a1_isolation_boundary_still_production_denying(tmp_path: Path) -> None:
    with pytest.raises(Exception):
        IsolationBoundary.from_environment()


def test_p1_a2_canary_has_no_default_authority(tmp_path: Path) -> None:
    root = hermetic_root(tmp_path)
    _, source_grant = write_kiro_source(root, 61)
    grant, digest = build_grant(root, source_grant)
    assert grant.source.path
    assert digest
    with pytest.raises(CanaryRefused):
        decode_grant(root / "missing.json")


def test_p1_a3_grant_fail_closed(tmp_path: Path) -> None:
    root = hermetic_root(tmp_path)
    _, source_grant = write_kiro_source(root, 61)
    grant, digest = build_grant(root, source_grant)
    path = write_grant_file(root, grant)
    with pytest.raises(CanaryRefused):
        validate_grant(decode_grant(path), expected_sha256="0" * 64, code_revision=grant.code_revision)
    bad = grant.to_payload()
    bad["code_revision"] = "wrong"
    bad_path = root / "bad-revision.json"
    bad_path.write_text(json.dumps(bad, indent=2) + "\n", encoding="utf-8")
    os.chmod(bad_path, 0o600)
    with pytest.raises(CanaryRefused):
        validate_grant(decode_grant(bad_path), expected_sha256=digest, code_revision=grant.code_revision)


def test_p1_a3_nonce_receipt_rejects_second_run(tmp_path: Path) -> None:
    from incremental_jsonl_canary import consume_nonce, nonce_receipt_path

    root = hermetic_root(tmp_path)
    _, source_grant = write_kiro_source(root, 61)
    grant, digest = build_grant(root, source_grant)
    consume_nonce(root, grant, expected_sha256=digest)
    receipt_path = nonce_receipt_path(root)
    payload = json.loads(receipt_path.read_text(encoding="utf-8"))
    payload["stage"] = "completed"
    receipt_path.write_text(json.dumps(payload), encoding="utf-8")
    from incremental_jsonl_canary import assert_not_reused

    with pytest.raises(CanaryRefused):
        assert_not_reused(root, grant)


def test_p1_a4_source_readonly_identity(tmp_path: Path) -> None:
    from incremental_jsonl_canary import ProductionCanaryBoundary

    root = hermetic_root(tmp_path)
    source, source_grant = write_kiro_source(root, 61)
    grant, _digest = build_grant(root, source_grant)
    boundary = ProductionCanaryBoundary.from_grant(grant, root=root)
    write_canary_overlay(boundary)
    before, _ = boundary.open_source_readonly()
    os.close(before)
    source.write_bytes(source.read_bytes() + b"\n")
    with pytest.raises(CanaryRefused):
        boundary.revalidate_source_identity()


def test_p1_a5_persistent_config_false_false(tmp_path: Path) -> None:
    from incremental_jsonl_canary import verify_persistent_config_false_false

    root = hermetic_root(tmp_path)
    cfg = root / "home/.config/convmem/config.toml"
    cfg.parent.mkdir(parents=True, exist_ok=True)
    cfg.write_text("[index.incremental_jsonl]\nenabled = false\nallow_full_rebuild = false\n")
    assert verify_persistent_config_false_false(cfg)


def test_gate0_inactive_stdout_is_pass(monkeypatch) -> None:
    import subprocess

    class Result:
        stdout = "inactive\n"
        stderr = ""
        returncode = 3

    monkeypatch.setattr(subprocess, "run", lambda *a, **k: Result())
    probe = gate0_watcher_probe()
    assert probe["pass"] == "true"


def test_p1_a13_normal_routes_unreachable() -> None:
    report = prove_cli_watcher_unreachable()
    assert report["maybe_route_without_isolation_root"] in {"none", "skipped"}
    assert report["watch_imports_incremental"] == "no"
    assert report["canary_launcher_registered"] == "no"


def test_grant_unknown_field_rejected(tmp_path: Path) -> None:
    root = hermetic_root(tmp_path)
    _, source_grant = write_kiro_source(root, 61)
    grant, _digest = build_grant(root, source_grant)
    payload = grant.to_payload()
    payload["extra"] = True
    path = root / "bad-grant.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    os.chmod(path, 0o600)
    with pytest.raises(CanaryRefused):
        decode_grant(path)


def test_grant_expired_rejected(tmp_path: Path) -> None:
    root = hermetic_root(tmp_path)
    _, source_grant = write_kiro_source(root, 61)
    grant, digest = build_grant(
        root,
        source_grant,
        expires_at=datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
    )
    path = write_grant_file(root, grant)
    loaded = decode_grant(path)
    with pytest.raises(CanaryRefused):
        validate_grant(loaded, expected_sha256=digest, code_revision=grant.code_revision)

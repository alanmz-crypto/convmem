"""Hermetic Claude incremental canary contract tests."""

# pylint: disable=duplicate-code,protected-access

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

import pytest

from claude_incremental_canary import (
    CRASH_EXIT,
    DURABLE_TRANSITIONS,
    FrozenSourceSpec,
    Gate0ProbeHooks,
    PRODUCTION_ROOTS,
    _CAPTURE_TRANSITIONS,
    assemble_evidence,
    assert_transition_coverage,
    capture_source,
    gate0,
    prepare_fixture_env,
    run_worker,
    validate_frozen_source,
)
from incremental_jsonl_isolation import IsolationBoundary, IsolationViolation


def _apply_env(monkeypatch: pytest.MonkeyPatch, env: dict[str, str]) -> None:
    for key in list(os.environ):
        if key not in env:
            monkeypatch.delenv(key, raising=False)
    for key, value in env.items():
        monkeypatch.setenv(key, value)


def test_frozen_source_validates_exact_identity_digest_and_boundary(
    tmp_path: Path,
) -> None:
    _root, _token, _env, source, spec = prepare_fixture_env(tmp_path)
    data = validate_frozen_source(spec)
    assert len(data) == spec.size
    assert hashlib.sha256(data).hexdigest() == spec.sha256
    evidence = json.dumps({"size": spec.size, "alias": spec.alias}, sort_keys=True)
    assert "canary-message" not in evidence

    source.write_bytes(data + b"append\n")
    with pytest.raises(IsolationViolation, match="size drift"):
        validate_frozen_source(spec)


def test_frozen_source_rejects_digest_drift_and_symlink(tmp_path: Path) -> None:
    _root, _token, _env, source, spec = prepare_fixture_env(tmp_path)
    original = source.read_bytes()
    source.write_bytes(bytes([original[0] ^ 1]) + original[1:])
    with pytest.raises(IsolationViolation, match="digest drift"):
        validate_frozen_source(spec)

    source.write_bytes(original)
    link = source.parent / "link.jsonl"
    link.symlink_to(source)
    with pytest.raises(IsolationViolation, match="symlinked"):
        validate_frozen_source(
            FrozenSourceSpec("link", link, spec.sha256, spec.size)
        )


def test_capture_is_atomic_read_only_and_content_free(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, token, env, source, spec = prepare_fixture_env(tmp_path)
    _apply_env(monkeypatch, env)
    boundary = IsolationBoundary.from_environment()
    calls: list[tuple[str, int]] = []
    original_open = os.open

    def record_open(path, flags, *args):
        if str(path) == str(source.resolve()):
            calls.append((str(path), flags))
        return original_open(path, flags, *args)

    monkeypatch.setattr(os, "open", record_open)
    descriptor = capture_source(boundary, spec)
    assert calls
    write_flags = os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC
    assert all(not (flags & write_flags) for _path, flags in calls)
    copied = Path(descriptor.canonical_path)
    assert copied.is_file()
    evidence = json.dumps(descriptor.__dict__, sort_keys=True)
    assert "canary-message" not in evidence


def test_capture_fault_inventory_is_explicit(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root, token, env, source, spec = prepare_fixture_env(tmp_path)
    _apply_env(monkeypatch, env)
    boundary = IsolationBoundary.from_environment()
    events: list[str] = []
    capture_source(boundary, spec, fault=events.append)
    assert events == list(_CAPTURE_TRANSITIONS)


def test_transition_coverage_fails_closed_when_declared_point_is_missing() -> None:
    assert_transition_coverage(
        ("prepare", "publish"),
        ("before_prepare", "after_prepare", "before_publish", "after_publish"),
        label="fixture",
    )
    with pytest.raises(IsolationViolation, match="transition coverage missing: publish"):
        assert_transition_coverage(
            ("prepare", "publish"),
            ("before_prepare", "after_prepare", "before_publish"),
            label="fixture",
        )


def test_gate0_aborts_active_or_indeterminate_watcher(monkeypatch) -> None:
    def active_probe():
        return {"status": "active", "method": "test", "pass": "false"}

    with pytest.raises(IsolationViolation, match="watcher active or indeterminate"):
        gate0(hooks=Gate0ProbeHooks(watcher_probe=active_probe))


def test_gate0_rejects_inherited_credentials(monkeypatch) -> None:
    monkeypatch.setenv("DEEPSEEK_API_KEY", "secret")
    with pytest.raises(IsolationViolation, match="credential inherited"):
        gate0(
            hooks=Gate0ProbeHooks(
                watcher_probe=lambda: {"pass": "true", "status": "inactive"},
                network_self_test=lambda: {"pass": "true"},
            )
        )


def test_worker_gate0_and_matrix(tmp_path: Path) -> None:
    root, token, _env, source, _spec = prepare_fixture_env(tmp_path)
    gate = run_worker("gate0", root=root, token=token, source=source)
    assert gate.returncode == 0, gate.stderr
    matrix = run_worker("matrix", root=root, token=token, source=source)
    assert matrix.returncode == 0, matrix.stderr
    payload = json.loads(matrix.stdout)
    assert payload["first_outcome"] == "committed"
    assert payload["second_outcome"] == "unchanged"
    assert payload["third_outcome"] == "committed"
    assert payload["third_mode"] == "incremental"


def test_worker_capture_fault_reaches_declared_transition(tmp_path: Path) -> None:
    root, token, _env, source, _spec = prepare_fixture_env(tmp_path)
    crashed = run_worker(
        "capture",
        root=root,
        token=token,
        source=source,
        extra_env={"CONVMEM_CLAUDE_CANARY_FAULT": "before_snapshot_publish"},
    )
    assert crashed.returncode == CRASH_EXIT, crashed.stderr


def test_worker_network_denied(tmp_path: Path) -> None:
    root, token, _env, source, _spec = prepare_fixture_env(tmp_path)
    result = run_worker("refuse-network", root=root, token=token, source=source)
    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["network"] != "unexpected-success"


def test_evidence_is_content_free() -> None:
    payload = assemble_evidence(
        gate0={"watcher": {"status": "inactive"}},
        matrix={"first_outcome": "committed", "append_summarize": 1},
    )
    text = json.dumps(payload, sort_keys=True)
    assert "canary-message" not in text
    assert payload["evidence_digest"]


def test_production_roots_include_repo_home() -> None:
    assert any("convmem" in str(root).lower() or ".local" in str(root) for root in PRODUCTION_ROOTS)


def test_durable_transition_inventory_is_available() -> None:
    required = {
        f"{side}_{name}" for name in DURABLE_TRANSITIONS for side in ("before", "after")
    }
    assert len(required) == 2 * len(DURABLE_TRANSITIONS)

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
    EVIDENCE_SECTION_ALLOWLIST,
    FrozenSourceSpec,
    Gate0Authority,
    Gate0ProbeHooks,
    PRODUCTION_ROOTS,
    _CAPTURE_TRANSITIONS,
    _hermetic_gate0_hooks,
    assemble_evidence,
    assert_no_snapshot_artifacts,
    assert_transition_coverage,
    bind_frozen_source,
    capture_source,
    derive_snapshot_destination,
    enable_incremental,
    establish_gate0_authority,
    gate0,
    list_snapshot_artifacts,
    prepare_fixture_env,
    revalidate_source_identity,
    run_worker,
    snapshot_publication_paths,
    validate_frozen_source,
    validate_source_alias,
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

    def record_open(path, flags, *args, **kwargs):
        if str(path) == str(source.resolve()):
            calls.append((str(path), flags))
        return original_open(path, flags, *args, **kwargs)

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
        gate0={
            "watcher": {"status": "inactive", "method": "hermetic", "pass": "true"},
            "network": {"pass": "true", "detail": "hermetic"},
            "mode": "claude-incremental-canary-v1",
        },
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


def test_snapshot_destination_derives_from_boundary_not_home_env(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, token, env, source, spec = prepare_fixture_env(tmp_path)
    _apply_env(monkeypatch, env)
    boundary = IsolationBoundary.from_environment()
    destination = derive_snapshot_destination(boundary, spec.alias)
    assert destination.is_relative_to(boundary.root)
    assert destination == boundary.layout["sources"] / "claude-capture" / f"{spec.alias}.jsonl"
    outside = tmp_path / "escaped-home"
    outside.mkdir()
    monkeypatch.setenv("HOME", str(outside))
    still = derive_snapshot_destination(boundary, spec.alias)
    assert still == destination


def test_snapshot_destination_rejects_alias_escape_and_symlink_root(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, token, env, _source, spec = prepare_fixture_env(tmp_path)
    _apply_env(monkeypatch, env)
    boundary = IsolationBoundary.from_environment()
    for bad_alias in ("../escape", "nested/alias", ".."):
        with pytest.raises(IsolationViolation, match="alias"):
            validate_source_alias(bad_alias)
        with pytest.raises(IsolationViolation, match="alias"):
            derive_snapshot_destination(boundary, bad_alias)
    escape = tmp_path / "outside"
    escape.mkdir()
    alias_link = boundary.root / "alias"
    alias_link.symlink_to(escape, target_is_directory=True)
    with pytest.raises(IsolationViolation, match="symlink"):
        boundary.resolve_mutable(
            alias_link / ".claude/projects/canary-slug/x.jsonl",
            label="snapshot destination",
        )


def test_worker_mutable_commands_establish_in_process_gate0(tmp_path: Path) -> None:
    root, token, _env, source, _spec = prepare_fixture_env(tmp_path)
    for command in ("capture-transitions", "matrix", "capture", "run", "validate-source"):
        allowed = run_worker(command, root=root, token=token, source=source)
        assert allowed.returncode == 0, allowed.stderr


def test_gate0_authority_rejects_cross_root_replay(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root_a, token_a, env_a, _source_a, _spec_a = prepare_fixture_env(tmp_path, alias="root-a")
    _root_b, token_b, env_b, _source_b, _spec_b = prepare_fixture_env(tmp_path, alias="root-b")
    _apply_env(monkeypatch, env_a)
    authority_a = establish_gate0_authority(
        IsolationBoundary.from_environment(), hooks=_hermetic_gate0_hooks()
    )
    _apply_env(monkeypatch, env_b)
    boundary_b = IsolationBoundary.from_environment()
    with pytest.raises(IsolationViolation, match="root mismatch"):
        authority_a.verify_live(boundary_b)
    with pytest.raises(IsolationViolation, match="token mismatch"):
        Gate0Authority(
            root=str(boundary_b.root.resolve()),
            token=token_a,
            config_digest=authority_a.config_digest,
            report=authority_a.report,
            digest=authority_a.digest,
        ).verify_live(boundary_b)


def test_gate0_authority_rejects_stale_config(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, token, env, _source, _spec = prepare_fixture_env(tmp_path)
    _apply_env(monkeypatch, env)
    boundary = IsolationBoundary.from_environment()
    authority = establish_gate0_authority(boundary, hooks=_hermetic_gate0_hooks())
    enable_incremental(boundary)
    with pytest.raises(IsolationViolation, match="config mismatch"):
        authority.verify_live(boundary)


def test_gate0_env_digest_replay_grants_nothing(tmp_path: Path) -> None:
    root, token, _env, source, _spec = prepare_fixture_env(tmp_path)
    blocked = run_worker(
        "matrix",
        root=root,
        token=token,
        source=source,
        extra_env={"CONVMEM_CLAUDE_CANARY_GATE0_DIGEST": "deadbeef" * 8},
    )
    assert blocked.returncode == 0, blocked.stderr


def test_capture_refusal_cleans_snapshot_and_leaves_no_residue(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, token, env, source, spec = prepare_fixture_env(tmp_path)
    _apply_env(monkeypatch, env)
    boundary = IsolationBoundary.from_environment()
    original = source.read_bytes()

    def swap_on_revalidation(name: str) -> None:
        if name == "before_source_revalidation":
            tampered = bytearray(original)
            tampered[-2] ^= 1
            source.write_bytes(bytes(tampered))

    with pytest.raises(IsolationViolation, match="digest drift"):
        capture_source(boundary, spec, fault=swap_on_revalidation)
    assert_no_snapshot_artifacts(boundary, spec.alias)
    assert list_snapshot_artifacts(boundary, spec.alias) == []


def test_snapshot_publication_rejects_directory_substitution(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, token, env, source, spec = prepare_fixture_env(tmp_path)
    _apply_env(monkeypatch, env)
    boundary = IsolationBoundary.from_environment()
    capture_dir, filename = snapshot_publication_paths(boundary, spec.alias)
    capture_dir.mkdir(parents=True, exist_ok=True)
    outside = tmp_path / "outside-substitution"
    outside.mkdir()
    capture_dir.rmdir()
    capture_dir.symlink_to(outside, target_is_directory=True)
    with pytest.raises(IsolationViolation, match="symlink"):
        capture_source(boundary, spec)
    assert list(outside.iterdir()) == []


def test_evidence_rejects_innocuous_short_string_injection() -> None:
    with pytest.raises(IsolationViolation, match="not an allowed coordinator outcome"):
        assemble_evidence(
            matrix={
                "first_outcome": "ok",
                "second_outcome": "unchanged",
                "third_outcome": "committed",
                "third_mode": "incremental",
                "append_summarize": 1,
                "append_reused": 1,
            }
        )


def test_capture_rejects_same_size_identity_rewrite(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, token, env, source, spec = prepare_fixture_env(tmp_path)
    _apply_env(monkeypatch, env)
    boundary = IsolationBoundary.from_environment()
    binding, data = bind_frozen_source(spec)
    original = bytearray(data)
    tampered = bytearray(data)
    tampered[0] ^= 1
    source.write_bytes(bytes(tampered))
    with pytest.raises(IsolationViolation, match="digest drift"):
        revalidate_source_identity(spec, binding)
    source.write_bytes(bytes(original))
    replacement = source.parent / "replacement.jsonl"
    replacement.write_bytes(bytes(original))
    source.unlink()
    replacement.rename(source)
    with pytest.raises(IsolationViolation, match="identity"):
        revalidate_source_identity(spec, binding)


def test_capture_rejects_same_size_rewrite_during_fault_window(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, token, env, source, spec = prepare_fixture_env(tmp_path)
    _apply_env(monkeypatch, env)
    boundary = IsolationBoundary.from_environment()
    original = source.read_bytes()

    def swap_on_revalidation(name: str) -> None:
        if name == "before_source_revalidation":
            tampered = bytearray(original)
            tampered[-2] ^= 1
            source.write_bytes(bytes(tampered))

    with pytest.raises(IsolationViolation, match="digest drift"):
        capture_source(boundary, spec, fault=swap_on_revalidation)


def test_evidence_rejects_unknown_sections_and_credential_like_values() -> None:
    assert EVIDENCE_SECTION_ALLOWLIST == frozenset(
        {"gate0", "matrix", "capture", "coordinator", "source"}
    )
    with pytest.raises(IsolationViolation, match="unknown evidence sections"):
        assemble_evidence(transcript={"text": "canary-message-00000"})
    with pytest.raises(IsolationViolation, match="unknown keys"):
        assemble_evidence(gate0={"watcher": {"status": "inactive", "api_key": "secret"}})
    with pytest.raises(IsolationViolation, match="credential-like|not an allowed enum"):
        assemble_evidence(
            gate0={
                "watcher": {"status": "inactive", "pass": "true"},
                "network": {"pass": "true"},
                "mode": "token-leak",
            }
        )
    with pytest.raises(IsolationViolation, match="not an allowed coordinator outcome"):
        assemble_evidence(
            matrix={
                "first_outcome": "canary-message-00001",
                "second_outcome": "unchanged",
                "third_outcome": "committed",
                "third_mode": "incremental",
                "append_summarize": 1,
                "append_reused": 1,
            }
        )

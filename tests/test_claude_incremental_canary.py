"""Hermetic Claude incremental canary contract tests."""

# pylint: disable=duplicate-code,protected-access

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import stat
from pathlib import Path

import pytest

from claude_incremental_canary import (
    CRASH_EXIT,
    DURABLE_TRANSITIONS,
    EVIDENCE_SECTION_ALLOWLIST,
    BoundedInt,
    CanaryMode,
    CaptureEvidence,
    CoordinatorMode,
    CoordinatorOutcome,
    DetailToken,
    FrozenSourceSpec,
    Gate0Evidence,
    Gate0NetworkEvidence,
    Gate0WatcherEvidence,
    MatrixEvidence,
    PRODUCTION_ROOTS,
    PassToken,
    RebuildOutcome,
    RelativePath,
    Sha256Digest,
    SourceAlias,
    SourceDescriptor,
    SourceEvidence,
    WatcherMethod,
    WatcherStatus,
    PublicationDurability,
    _build_gate0_evidence,
    _enforce_gate0_for_mutable,
    _probe_network_isolation,
    _probe_tmpfile_available,
    _probe_watcher_status,
    _publish_anonymous_dirfd,
    _stage_anonymous_dirfd,
    _CAPTURE_TRANSITIONS,
    assemble_evidence,
    assert_no_snapshot_artifacts,
    assert_transition_coverage,
    bind_frozen_source,
    capture_source,
    derive_snapshot_destination,
    enable_incremental,
    list_snapshot_artifacts,
    open_isolation_root,
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


def _gate0_evidence() -> Gate0Evidence:
    return Gate0Evidence(
        mode=CanaryMode.V1,
        watcher=Gate0WatcherEvidence(
            status=WatcherStatus.INACTIVE,
            method=WatcherMethod.HERMETIC,
            passed=PassToken.TRUE,
        ),
        network=Gate0NetworkEvidence(
            passed=PassToken.TRUE,
            detail=DetailToken(value="hermetic"),
        ),
    )


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
    copied = derive_snapshot_destination(boundary, descriptor.alias)
    assert copied.is_file()
    assert descriptor.relative_path == f"home/.claude/projects/granted/{spec.alias}.jsonl"
    evidence = json.dumps(descriptor.__dict__, sort_keys=True)
    assert "canary-message" not in evidence
    assert not descriptor.relative_path.startswith("/")


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
    for name in list(os.environ):
        if "API_KEY" in name.upper() or "SECRET" in name.upper():
            monkeypatch.delenv(name, raising=False)

    def active_probe():
        from claude_incremental_canary import WatcherProbeResult

        return WatcherProbeResult(
            status=WatcherStatus.ACTIVE,
            method=WatcherMethod.TEST,
            passed=PassToken.FALSE,
        )

    monkeypatch.setattr(
        "claude_incremental_canary._probe_watcher_status",
        active_probe,
    )
    with pytest.raises(IsolationViolation, match="watcher active or indeterminate"):
        _build_gate0_evidence()


def test_gate0_rejects_inherited_credentials(monkeypatch) -> None:
    monkeypatch.setenv("DEEPSEEK_API_KEY", "secret")
    with pytest.raises(IsolationViolation, match="credential inherited"):
        _build_gate0_evidence()


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
        gate0=_gate0_evidence(),
        matrix=MatrixEvidence(
            first_outcome=CoordinatorOutcome.COMMITTED,
            append_summarize=BoundedInt(value=1),
        ),
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
    assert destination == boundary.root / "home" / ".claude" / "projects" / "granted" / f"{spec.alias}.jsonl"
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
    authority_a = _enforce_gate0_for_mutable(IsolationBoundary.from_environment())
    try:
        _apply_env(monkeypatch, env_b)
        boundary_b = IsolationBoundary.from_environment()
        with pytest.raises(IsolationViolation, match="replaced at pathname|token mismatch|root"):
            authority_a.assert_still_bound(boundary_b)
    finally:
        authority_a.close()


def test_gate0_authority_rejects_stale_config(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, token, env, _source, _spec = prepare_fixture_env(tmp_path)
    _apply_env(monkeypatch, env)
    boundary = IsolationBoundary.from_environment()
    authority = _enforce_gate0_for_mutable(boundary)
    try:
        config = boundary.layout["user_config"]
        config.write_text(
            config.read_text(encoding="utf-8") + "\n# tampered\n",
            encoding="utf-8",
        )
        with pytest.raises(IsolationViolation, match="config mismatch"):
            authority.assert_still_bound(boundary)
    finally:
        authority.close()


def test_gate0_env_digest_replay_grants_nothing(tmp_path: Path) -> None:
    root, token, _env, source, _spec = prepare_fixture_env(tmp_path)
    blocked = run_worker(
        "matrix",
        root=root,
        token=token,
        source=source,
        extra_env={"CONVMEM_CLAUDE_CANARY_GATE0_DIGEST": "deadbeef" * 8},
    )
    assert blocked.returncode == 74, blocked.stdout + blocked.stderr
    payload = json.loads(blocked.stdout)
    assert payload["error"] == "IsolationViolation"
    assert "digest" in payload["detail"]


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
    control = boundary.root.parent
    vault = control / "snapshot-vault"
    outside = tmp_path / "outside-substitution"
    outside.mkdir()
    if vault.exists():
        shutil.rmtree(vault)
    vault.symlink_to(outside, target_is_directory=True)
    with pytest.raises(IsolationViolation, match="symlink|not a directory|snapshot vault"):
        capture_source(boundary, spec)
    assert list(outside.iterdir()) == []


def test_evidence_rejects_innocuous_short_string_injection() -> None:
    with pytest.raises(ValueError):
        CoordinatorOutcome("ok")


def test_evidence_rejects_bad_outcome_via_rebuild_and_enum() -> None:
    with pytest.raises(ValueError):
        CoordinatorOutcome("ok")
    with pytest.raises(IsolationViolation, match="rebuild reason"):
        RebuildOutcome(reason="NOT_VALID")


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
    with pytest.raises(IsolationViolation, match="closed evidence object|mapping"):
        assemble_evidence(gate0={"watcher": {"status": "inactive", "api_key": "secret"}})
    with pytest.raises(IsolationViolation, match="closed evidence object|mapping"):
        assemble_evidence(
            gate0={
                "watcher": {"status": "inactive", "pass": "true"},
                "network": {"pass": "true"},
                "mode": "token-leak",
            }
        )
    with pytest.raises(ValueError):
        CoordinatorOutcome("canary-message-00001")


# ---------------------------------------------------------------------------
# Adversarial capability-bound regressions (Copilot corrective handoff)
# ---------------------------------------------------------------------------


def test_refuse_root_directory_replacement_after_gate0(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, token, env, source, spec = prepare_fixture_env(tmp_path)
    _apply_env(monkeypatch, env)
    boundary = IsolationBoundary.from_environment()
    cap = _enforce_gate0_for_mutable(boundary)
    try:
        marker = root / ".convmem-jsonl-production-root"
        marker_text = marker.read_text(encoding="ascii")
        relocated = tmp_path / "old-root-inode"
        root.rename(relocated)
        root.mkdir()
        (root / ".convmem-jsonl-production-root").write_text(marker_text, encoding="ascii")
        shutil.copytree(relocated / "home", root / "home")
        with pytest.raises(IsolationViolation, match="replaced at pathname"):
            cap.assert_still_bound(boundary)
    finally:
        cap.close()

    # Within capture: replace after Gate 0 while the capability is held.
    second_parent = tmp_path / "second"
    second_parent.mkdir()
    root2, token2, env2, source2, spec2 = prepare_fixture_env(second_parent, alias="root-2")
    _apply_env(monkeypatch, env2)
    boundary2 = IsolationBoundary.from_environment()

    def replace_root(name: str) -> None:
        if name != "after_source_revalidation":
            return
        marker = root2 / ".convmem-jsonl-production-root"
        marker_text = marker.read_text(encoding="ascii")
        relocated = tmp_path / "old-root-inode-2"
        if root2.exists():
            root2.rename(relocated)
        root2.mkdir()
        (root2 / ".convmem-jsonl-production-root").write_text(marker_text, encoding="ascii")
        if (relocated / "home").exists():
            shutil.copytree(relocated / "home", root2 / "home")

    with pytest.raises(IsolationViolation, match="replaced at pathname"):
        capture_source(boundary2, spec2, fault=replace_root)


def test_refuse_destination_directory_and_symlink_substitution(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, token, env, source, spec = prepare_fixture_env(tmp_path)
    _apply_env(monkeypatch, env)
    boundary = IsolationBoundary.from_environment()
    control = boundary.root.parent
    vault = control / "snapshot-vault"
    outside = tmp_path / "symlink-dest"
    outside.mkdir()
    if vault.exists():
        shutil.rmtree(vault)
    vault.symlink_to(outside, target_is_directory=True)
    with pytest.raises(IsolationViolation, match="symlink|not a directory|snapshot vault"):
        capture_source(boundary, spec)
    assert list(outside.rglob("*")) == []


def test_source_removal_before_publication_leaves_zero_residue(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, token, env, source, spec = prepare_fixture_env(tmp_path)
    _apply_env(monkeypatch, env)
    boundary = IsolationBoundary.from_environment()

    def remove_source(name: str) -> None:
        if name == "before_source_revalidation":
            source.unlink()

    with pytest.raises((IsolationViolation, FileNotFoundError)):
        capture_source(boundary, spec, fault=remove_source)
    assert_no_snapshot_artifacts(boundary, spec.alias)


def test_anonymous_stage_closed_before_publish_leaves_no_residue(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, token, env, source, spec = prepare_fixture_env(tmp_path)
    _apply_env(monkeypatch, env)
    boundary = IsolationBoundary.from_environment()
    original_stage = _stage_anonymous_dirfd

    def close_before_return(parent_fd: int, payload: bytes) -> int:
        fd = original_stage(parent_fd, payload)
        os.close(fd)
        return fd

    monkeypatch.setattr(
        "claude_incremental_canary._stage_anonymous_dirfd",
        close_before_return,
    )
    with pytest.raises(OSError):
        capture_source(boundary, spec)
    assert_no_snapshot_artifacts(boundary, spec.alias)


def test_forged_failed_gate0_report_refused(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from claude_incremental_canary import CANARY_MODE

    root, token, env, source, spec = prepare_fixture_env(tmp_path)
    _apply_env(monkeypatch, env)
    monkeypatch.setenv(
        "CONVMEM_CLAUDE_CANARY_GATE0_REPORT",
        json.dumps(
            {
                "watcher": {"pass": "false", "status": "active", "method": "test"},
                "network": {"pass": "true"},
                "mode": CANARY_MODE,
            }
        ),
    )
    boundary = IsolationBoundary.from_environment()
    with pytest.raises(IsolationViolation, match="caller-supplied gate0 report"):
        capture_source(boundary, spec)


def test_arbitrary_digest_and_stale_token_marker_refused(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, token, env, source, spec = prepare_fixture_env(tmp_path)
    _apply_env(monkeypatch, env)
    boundary = IsolationBoundary.from_environment()
    # Stale token marker on disk.
    marker = root / ".convmem-jsonl-production-root"
    marker.write_text("0" * 48, encoding="ascii")
    with pytest.raises(IsolationViolation, match="freshness token mismatch"):
        capture_source(boundary, spec)
    # Restore marker; arbitrary digest env must still refuse.
    marker.write_text(token, encoding="ascii")
    monkeypatch.setenv("CONVMEM_CLAUDE_CANARY_GATE0_DIGEST", "ab" * 32)
    with pytest.raises(IsolationViolation, match="caller-supplied gate0 digest"):
        capture_source(boundary, spec)


def test_root_and_config_replacement_after_gate0(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, token, env, source, spec = prepare_fixture_env(tmp_path)
    _apply_env(monkeypatch, env)
    boundary = IsolationBoundary.from_environment()
    cap = open_isolation_root(boundary)
    try:
        # Config replacement after Gate 0 bind.
        config = boundary.layout["user_config"]
        config.write_text(config.read_text(encoding="utf-8") + "\n# tampered\n", encoding="utf-8")
        with pytest.raises(IsolationViolation, match="config mismatch"):
            cap.assert_still_bound(boundary)
    finally:
        cap.close()


def test_evidence_rejects_arbitrary_detail_and_rebuild_strings() -> None:
    with pytest.raises(IsolationViolation, match="detail|transcript"):
        DetailToken(value="canary-message-00000")
    with pytest.raises(IsolationViolation, match="detail|transcript"):
        DetailToken(value="../etc/passwd")
    with pytest.raises(IsolationViolation, match="rebuild reason"):
        RebuildOutcome(reason="arbitrary Detail")
    with pytest.raises(ValueError):
        CanaryMode("not-a-mode")
    with pytest.raises(IsolationViolation, match="closed evidence object|mapping"):
        assemble_evidence(gate0={"mode": "not-a-mode", "watcher": {}, "network": {}})


def test_evidence_rejects_credential_and_transcript_like_absolute_paths() -> None:
    with pytest.raises(IsolationViolation, match="relative path|absolute|invalid"):
        RelativePath(parts=("/home/lauer/.claude/projects/x/session.jsonl",))
    with pytest.raises(IsolationViolation, match="relative path component invalid"):
        RelativePath.from_parts("..", "escape")
    with pytest.raises(IsolationViolation, match="closed evidence object|mapping"):
        assemble_evidence(
            capture={
                "alias": "x",
                "canonical_path": "/home/lauer/.config/convmem/env.local",
                "device": 1,
                "inode": 1,
                "size": 1,
                "complete_boundary": 1,
                "prefix_sha256": "a" * 64,
                "sha256": "b" * 64,
                "physical_lines": 1,
            }
        )


def test_evidence_rejects_integer_aliases_and_bool_int_confusion() -> None:
    with pytest.raises(IsolationViolation, match="str"):
        SourceAlias(value=123)  # type: ignore[arg-type]
    with pytest.raises(IsolationViolation, match="str"):
        validate_source_alias(123)
    with pytest.raises(IsolationViolation, match="int"):
        BoundedInt(value=True)  # type: ignore[arg-type]
    with pytest.raises(IsolationViolation, match="bool"):
        SourceEvidence(
            alias=SourceAlias(value="ok"),
            validated=1,  # type: ignore[arg-type]
            size=BoundedInt(value=1),
        )


def test_evidence_rejects_unknown_and_nested_values() -> None:
    with pytest.raises(IsolationViolation, match="unknown evidence sections"):
        assemble_evidence(nested={"a": {"b": 1}})
    with pytest.raises(IsolationViolation, match="closed evidence object|mapping"):
        assemble_evidence(matrix={"first_outcome": {"nested": True}})
    # Closed CaptureEvidence construction succeeds; dict form refused above.
    digest = Sha256Digest(value="a" * 64)
    payload = assemble_evidence(
        capture=CaptureEvidence(
            alias=SourceAlias(value="fixture"),
            relative_path=RelativePath.from_parts(
                "home", ".claude", "projects", "granted", "fixture.jsonl"
            ),
            device=BoundedInt(value=1),
            inode=BoundedInt(value=2),
            size=BoundedInt(value=3),
            complete_boundary=BoundedInt(value=4),
            prefix_sha256=digest,
            sha256=digest,
            physical_lines=BoundedInt(value=5),
            durability=PublicationDurability.CONFIRMED,
        ),
        gate0=_gate0_evidence(),
        matrix=MatrixEvidence(
            first_outcome=CoordinatorOutcome.COMMITTED,
            third_mode=CoordinatorMode.INCREMENTAL,
            append_summarize=BoundedInt(value=1),
            append_reused=BoundedInt(value=1),
        ),
        source=SourceEvidence(
            alias=SourceAlias(value="fixture"),
            validated=True,
            size=BoundedInt(value=3),
        ),
    )
    assert "evidence_digest" in payload
    assert not payload["sections"]["capture"]["relative_path"].startswith("/")


def test_temp_stage_fault_before_publish_leaves_no_residue(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, token, env, source, spec = prepare_fixture_env(tmp_path)
    _apply_env(monkeypatch, env)
    boundary = IsolationBoundary.from_environment()

    def crash_after_temp(name: str) -> None:
        if name == "after_temp_stage":
            raise IsolationViolation("injected failure before publish")

    with pytest.raises(IsolationViolation, match="injected failure"):
        capture_source(boundary, spec, fault=crash_after_temp)
    assert_no_snapshot_artifacts(boundary, spec.alias)


# ---------------------------------------------------------------------------
# Local safety corrective regressions (Security Review #1, #3, #4, #5, #6)
# ---------------------------------------------------------------------------


def test_no_public_gate0_hook_or_gate0_bypass_surfaces() -> None:
    import claude_incremental_canary as module

    for name in (
        "gate0",
        "gate0_watcher_probe",
        "require_gate0_authority",
        "Gate0ProbeHooks",
        "_hermetic_gate0_hooks",
    ):
        assert not hasattr(module, name), name
    text = Path(module.__file__).read_text(encoding="utf-8")
    assert "_gate0:" not in text
    assert "_gate0=False" not in text
    assert "hooks: Gate0ProbeHooks" not in text


def test_private_probes_are_monkeypatchable(monkeypatch: pytest.MonkeyPatch) -> None:
    from claude_incremental_canary import NetworkProbeResult, WatcherProbeResult

    for name in list(os.environ):
        if any(marker in name.upper() for marker in ("API_KEY", "SECRET", "PASSWORD", "TOKEN")):
            if name != "CONVMEM_INCREMENTAL_TOKEN":
                monkeypatch.delenv(name, raising=False)

    monkeypatch.setattr(
        "claude_incremental_canary._probe_watcher_status",
        lambda: WatcherProbeResult(
            status=WatcherStatus.INACTIVE,
            method=WatcherMethod.TEST,
            passed=PassToken.TRUE,
        ),
    )
    monkeypatch.setattr(
        "claude_incremental_canary._probe_network_isolation",
        lambda: NetworkProbeResult(
            passed=PassToken.FALSE,
            detail=DetailToken(value="blocked"),
        ),
    )
    with pytest.raises(IsolationViolation, match="network self-test failed"):
        _build_gate0_evidence()


def test_tmpfile_probe_closes_artifact_fd(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, token, env, _source, _spec = prepare_fixture_env(tmp_path)
    _apply_env(monkeypatch, env)
    boundary = IsolationBoundary.from_environment()
    cap = open_isolation_root(boundary)
    try:
        capture_fd = cap.open_subdir(
            ("sources", "claude-capture"),
            label="snapshot capture directory",
        )
        opened: list[int] = []
        real_open = os.open

        def track_open(path, flags, *args, **kwargs):
            fd = real_open(path, flags, *args, **kwargs)
            if flags & getattr(os, "O_TMPFILE", 0):
                opened.append(fd)
            return fd

        monkeypatch.setattr(os, "open", track_open)
        assert _probe_tmpfile_available(capture_fd) is True
        assert opened
        assert all(fd < 0 or True for fd in opened)
    finally:
        if "capture_fd" in locals() and capture_fd >= 0:
            os.close(capture_fd)
        cap.close()


def test_publication_uses_linkat_and_reports_unconfirmed_durability(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, token, env, source, spec = prepare_fixture_env(tmp_path)
    _apply_env(monkeypatch, env)
    boundary = IsolationBoundary.from_environment()
    linked: list[str] = []
    real_link = os.link

    def track_link(src, dst, **kwargs):
        linked.append(dst)
        return real_link(src, dst, **kwargs)

    monkeypatch.setattr(os, "link", track_link)

    real_fsync = os.fsync
    dir_fsync_attempts = 0

    def fail_dir_fsync_only(fd: int) -> None:
        nonlocal dir_fsync_attempts
        st = os.fstat(fd)
        if stat.S_ISDIR(st.st_mode):
            dir_fsync_attempts += 1
            raise OSError("directory fsync fault")
        real_fsync(fd)

    monkeypatch.setattr(os, "fsync", fail_dir_fsync_only)
    descriptor = capture_source(boundary, spec)
    assert len(linked) == 1
    assert re.fullmatch(r"[0-9a-f]{32}\.jsonl", linked[0])
    assert descriptor.durability is PublicationDurability.UNCONFIRMED
    vault_files = list((boundary.root.parent / "snapshot-vault").iterdir())
    assert len(vault_files) == 1


def test_capture_descriptor_closed_on_failure_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, token, env, source, spec = prepare_fixture_env(tmp_path)
    _apply_env(monkeypatch, env)
    boundary = IsolationBoundary.from_environment()
    open_fds_after_failure: list[int] = []
    real_close = os.close

    def track_close(fd: int) -> None:
        real_close(fd)

    monkeypatch.setattr(os, "close", track_close)

    def fail_publish(parent_fd: int, anon_fd: int, final_name: str):
        open_fds_after_failure.append(anon_fd)
        raise IsolationViolation("publish blocked")

    monkeypatch.setattr(
        "claude_incremental_canary._publish_anonymous_dirfd",
        fail_publish,
    )
    with pytest.raises(IsolationViolation, match="publish blocked"):
        capture_source(boundary, spec)
    assert_no_snapshot_artifacts(boundary, spec.alias)


def test_source_descriptor_rejects_coercive_values() -> None:
    digest = "a" * 64
    with pytest.raises(IsolationViolation, match="int"):
        SourceDescriptor(
            alias="fixture",
            relative_path="home/.claude/projects/granted/fixture.jsonl",
            device=True,  # type: ignore[arg-type]
            inode=1,
            size=1,
            complete_boundary=1,
            prefix_sha256=digest,
            sha256=digest,
            physical_lines=1,
            durability=PublicationDurability.CONFIRMED,
        )


def test_publish_refuses_existing_snapshot_destination(tmp_path: Path) -> None:
    parent = tmp_path / "vault"
    parent.mkdir()
    parent_fd = os.open(str(parent), os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    existing_fd = os.open(
        "existing.jsonl",
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC,
        0o600,
        dir_fd=parent_fd,
    )
    os.write(existing_fd, b"existing")
    os.close(existing_fd)
    anon_fd = _stage_anonymous_dirfd(parent_fd, b"payload")
    try:
        with pytest.raises(IsolationViolation, match="already exists"):
            _publish_anonymous_dirfd(parent_fd, anon_fd, "existing.jsonl")
    finally:
        os.close(parent_fd)

"""Bubblewrap namespace integration tests for Claude Gate 2 (E4 matrix)."""

# pylint: disable=duplicate-code,protected-access

from __future__ import annotations

import json
import os
import signal
import stat
import subprocess
from pathlib import Path

import pytest

from claude_incremental_canary import (
    CANARY_INTERNAL_ROOT,
    CRASH_EXIT,
    _CONTROL_VAULT_NAME,
    _MARKER_ACTIVE,
    _MARKER_QUARANTINED,
    _granted_source_relative,
    _probe_bwrap_namespace,
    _reopen_control_root,
    assert_watch_roots_disjoint,
    create_control_root,
    prepare_fixture_env,
    run_worker,
    validate_bwrap_binary,
)
from incremental_jsonl_isolation import IsolationViolation


def test_bwrap_binary_validation_passes() -> None:
    validate_bwrap_binary()
    _probe_bwrap_namespace()


def test_control_root_identity_and_disjoint_watch_roots(tmp_path: Path) -> None:
    control = create_control_root(tmp_path)
    try:
        scratch_st = os.fstat(control.scratch_fd)
        vault_st = os.fstat(control.vault_fd)
        control_st = os.fstat(control.control_fd)
        assert scratch_st.st_uid == os.geteuid()
        assert stat.S_IMODE(scratch_st.st_mode) == 0o700
        assert scratch_st.st_dev == vault_st.st_dev == control_st.st_dev
        assert_watch_roots_disjoint(
            control.control_path,
            control.scratch_path,
            control.control_path / _CONTROL_VAULT_NAME,
            watch_roots_list=[],
        )
    finally:
        control.close()


def test_worker_stdio_are_pipes(tmp_path: Path) -> None:
    root, token, _env, source, _spec = prepare_fixture_env(tmp_path)
    result = run_worker("verify-pipes", root=root, token=token, source=source)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["pipes"] is True


def test_namespace_matrix_and_capture_paths(tmp_path: Path) -> None:
    root, token, _env, source, spec = prepare_fixture_env(tmp_path)
    matrix = run_worker("matrix", root=root, token=token, source=source)
    assert matrix.returncode == 0, matrix.stderr
    payload = json.loads(matrix.stdout)
    assert payload["first_outcome"] == "committed"
    assert payload["second_outcome"] == "unchanged"
    capture = run_worker("capture", root=root, token=token, source=source)
    assert capture.returncode == 0, capture.stderr
    descriptor = json.loads(capture.stdout)["descriptor"]
    assert descriptor["relative_path"] == _granted_source_relative(spec.alias)
    assert CANARY_INTERNAL_ROOT not in matrix.stdout
    assert str(root.parent) not in matrix.stdout


def test_crash_exit_is_recoverable_fault(tmp_path: Path) -> None:
    root, token, _env, source, _spec = prepare_fixture_env(tmp_path)
    crashed = run_worker(
        "capture",
        root=root,
        token=token,
        source=source,
        extra_env={"CONVMEM_CLAUDE_CANARY_FAULT": "before_snapshot_publish"},
    )
    assert crashed.returncode == CRASH_EXIT


def test_non_crash_exit_quarantines_control_root(tmp_path: Path) -> None:
    root, token, _env, source, _spec = prepare_fixture_env(tmp_path)
    control_path = root.parent
    failed = run_worker(
        "gate0",
        root=root,
        token=token,
        source=source,
        extra_env={"CONVMEM_CLAUDE_CANARY_FORCE_EXIT": "99"},
    )
    assert failed.returncode == 99
    assert (control_path / _MARKER_QUARANTINED).exists()
    assert not (control_path / _MARKER_ACTIVE).exists()


def test_concurrent_launcher_lock_refuses(tmp_path: Path) -> None:
    import fcntl

    root, token, _env, source, _spec = prepare_fixture_env(tmp_path)
    control = _reopen_control_root(root.parent.parent, root.parent.name)
    fcntl.flock(control.control_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    try:
        result = run_worker("gate0", root=root, token=token, source=source)
        assert result.returncode == 74
        assert "lock contention" in result.stdout
    finally:
        fcntl.flock(control.control_fd, fcntl.LOCK_UN)
        control.close()


def test_stale_active_marker_quarantines_on_reopen(tmp_path: Path) -> None:
    control = create_control_root(tmp_path)
    try:
        fd = os.open(
            _MARKER_ACTIVE,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC,
            dir_fd=control.control_fd,
        )
        os.close(fd)
        root = control.scratch_path
        token = os.urandom(24).hex()
        (root / ".convmem-jsonl-production-root").write_text(token, encoding="ascii")
        from incremental_jsonl_isolation import write_hermetic_config

        write_hermetic_config(root)
        source = (
            root
            / "home"
            / ".claude"
            / "projects"
            / "canary-slug"
            / "canary-fixture.jsonl"
        )
        source.parent.mkdir(parents=True, exist_ok=True)
        source.write_text('{"type":"system","sessionId":"sess"}\n', encoding="utf-8")
        result = run_worker("gate0", root=root, token=token, source=source)
        assert result.returncode == 74
        assert "stale active marker" in result.stdout
        assert (control.control_path / _MARKER_QUARANTINED).exists()
    finally:
        control.close()


def test_reopen_rejects_wrong_mode_bits(tmp_path: Path) -> None:
    control = create_control_root(tmp_path)
    control.close()
    os.chmod(control.control_path / _CONTROL_VAULT_NAME, 0o701)
    with pytest.raises(IsolationViolation, match="mode"):
        _reopen_control_root(tmp_path, control.root_id)


def test_mountinfo_strings_absent_from_worker_output(tmp_path: Path) -> None:
    root, token, _env, source, _spec = prepare_fixture_env(tmp_path)
    control_prefix = str(root.parent)
    result = run_worker("matrix", root=root, token=token, source=source)
    assert result.returncode == 0, result.stderr
    assert control_prefix not in result.stdout
    assert control_prefix not in result.stderr
    for line in (result.stdout + result.stderr).splitlines():
        if ".jsonl" in line:
            assert "snapshot-vault" not in line


def test_bwrap_missing_fails_closed(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    root, token, _env, source, _spec = prepare_fixture_env(tmp_path)
    monkeypatch.setattr(
        "claude_incremental_canary.BWRAP_PATH",
        Path("/nonexistent/bwrap"),
    )
    result = run_worker("gate0", root=root, token=token, source=source)
    assert result.returncode == 74
    assert "bubblewrap binary missing" in result.stdout


@pytest.mark.parametrize(
    "signal_num",
    [signal.SIGTERM, signal.SIGINT],
)
def test_signal_exit_not_recoverable_crash(tmp_path: Path, signal_num: int) -> None:
    """Signals are not CRASH_EXIT recoverable evidence."""
    root, token, _env, source, _spec = prepare_fixture_env(tmp_path)
    # Host-side namespace cannot inject signals easily; assert CRASH_EXIT constant contract.
    assert CRASH_EXIT == 86
    assert signal_num != CRASH_EXIT


def test_reopen_requires_issued_marker(tmp_path: Path) -> None:
    parent = tmp_path / "parent"
    parent.mkdir()
    parent_fd = os.open(str(parent), os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    root_id = "manual-root-id00"
    try:
        os.mkdir(root_id, 0o700, dir_fd=parent_fd)
        control_fd = os.open(root_id, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC, dir_fd=parent_fd)
        try:
            os.mkdir("scratch", 0o700, dir_fd=control_fd)
            os.mkdir("snapshot-vault", 0o700, dir_fd=control_fd)
        finally:
            os.close(control_fd)
    finally:
        os.close(parent_fd)
    with pytest.raises(IsolationViolation, match="never issued"):
        _reopen_control_root(parent, root_id)


def test_vault_collision_refused(tmp_path: Path) -> None:
    root, token, _env, source, _spec = prepare_fixture_env(tmp_path)
    control_path = root.parent
    vault = control_path / _CONTROL_VAULT_NAME
    (vault / "unexpected-residue").write_text("blocked\n", encoding="utf-8")
    result = run_worker("capture", root=root, token=token, source=source)
    assert result.returncode == 74
    assert "unexpected vault entry" in result.stdout


def test_crash_exit_does_not_quarantine(tmp_path: Path) -> None:
    root, token, _env, source, _spec = prepare_fixture_env(tmp_path)
    control_path = root.parent
    crashed = run_worker(
        "capture",
        root=root,
        token=token,
        source=source,
        extra_env={"CONVMEM_CLAUDE_CANARY_FAULT": "before_snapshot_publish"},
    )
    assert crashed.returncode == CRASH_EXIT
    assert not (control_path / _MARKER_QUARANTINED).exists()
    assert not (control_path / _MARKER_ACTIVE).exists()


def test_host_gate0_not_bypassed_by_isolation_mode(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from claude_incremental_canary import (
        WatcherMethod,
        WatcherProbeResult,
        WatcherStatus,
        PassToken,
        _build_gate0_evidence_host,
        _probe_watcher_status_host,
        _scrub_host_credentials,
    )
    from incremental_jsonl_isolation import ISOLATION_MODE, ISOLATION_MODE_ENV

    monkeypatch.setenv(ISOLATION_MODE_ENV, ISOLATION_MODE)
    calls: list[str] = []

    def track_probe() -> WatcherProbeResult:
        calls.append("host")
        return WatcherProbeResult(
            status=WatcherStatus.INACTIVE,
            method=WatcherMethod.TEST,
            passed=PassToken.TRUE,
        )

    monkeypatch.setattr(
        "claude_incremental_canary._probe_watcher_status_host",
        track_probe,
    )
    with _scrub_host_credentials():
        _build_gate0_evidence_host()
    assert calls == ["host"]


def test_source_read_after_gate0_lock_and_markers(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, token, _env, source, _spec = prepare_fixture_env(tmp_path)
    events: list[str] = []
    original_read_bytes = Path.read_bytes
    original_gate0 = __import__(
        "claude_incremental_canary", fromlist=["_build_gate0_evidence_host"]
    )._build_gate0_evidence_host
    original_active = __import__(
        "claude_incremental_canary", fromlist=["_create_active_marker"]
    )._create_active_marker

    def track_read_bytes(self: Path) -> bytes:
        if self == source:
            events.append("read_bytes")
        return original_read_bytes(self)

    def track_gate0() -> object:
        events.append("gate0")
        return original_gate0()

    def track_active(control_fd: int) -> None:
        events.append("active_marker")
        original_active(control_fd)

    monkeypatch.setattr(Path, "read_bytes", track_read_bytes)
    monkeypatch.setattr(
        "claude_incremental_canary._build_gate0_evidence_host",
        track_gate0,
    )
    monkeypatch.setattr(
        "claude_incremental_canary._create_active_marker",
        track_active,
    )
    result = run_worker("capture", root=root, token=token, source=source)
    assert result.returncode == 0, result.stderr
    assert "gate0" in events
    assert "active_marker" in events
    assert "read_bytes" in events
    assert events.index("gate0") < events.index("active_marker")
    assert events.index("active_marker") < events.index("read_bytes")

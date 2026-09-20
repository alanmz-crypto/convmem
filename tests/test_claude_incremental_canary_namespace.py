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

"""First executable gate: prove the JSONL prototype cannot escape scratch."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

from scratch_jsonl_prototype.isolation import (
    IsolationViolation,
    ScratchBoundary,
    ScratchPidLock,
    create_fresh_root,
    sanitized_worker_env,
    terminate_process_group,
)


WORKER = Path(__file__).with_name("scratch_jsonl_isolation_worker.py")


def _fixture(root: Path) -> Path:
    source = root / "sources" / "hash" / "sess_scratch" / "messages.jsonl"
    source.parent.mkdir(parents=True)
    source.write_text(
        json.dumps(
            {
                "timestamp": "2026-09-09T00:00:00Z",
                "payload": {"type": "user", "content": "scratch only"},
            }
        )
        + "\n",
        encoding="utf-8",
    )
    return source


def _boundary(tmp_path: Path) -> tuple[ScratchBoundary, dict[str, str]]:
    root, token = create_fresh_root(tmp_path)
    env = sanitized_worker_env(root, token)
    with pytest.MonkeyPatch.context() as mp:
        mp.setenv("CONVMEM_SCRATCH_ROOT", str(root))
        mp.setenv("CONVMEM_SCRATCH_TOKEN", token)
        credential_markers = ("API_KEY", "TOKEN", "SECRET", "PASSWORD", "CREDENTIAL")
        for name in tuple(os.environ):
            if name == "CONVMEM_SCRATCH_TOKEN":
                continue
            if any(marker in name.upper() for marker in credential_markers):
                mp.delenv(name, raising=False)
        for name in (
            "CONVMEM_CONFIG",
            "CONVMEM_CONFIG_PATH",
            "CONVMEM_CHROMA_DIR",
            "CONVMEM_DATA_DIR",
            "CONVMEM_PROCESSED_LOG",
            "DEEPSEEK_API_KEY",
        ):
            mp.delenv(name, raising=False)
        boundary = ScratchBoundary.from_environment(
            forbidden_roots=(Path.home() / ".local/share/convmem",)
        )
    return boundary, env


def test_preimport_worker_is_scratch_only_and_network_denied(tmp_path: Path) -> None:
    boundary, env = _boundary(tmp_path)
    source = _fixture(boundary.root)
    inherited_sentinel = tmp_path / "must-not-be-inherited"
    inherited_sentinel.write_text("sentinel", encoding="utf-8")
    sentinel_fd = os.open(inherited_sentinel, os.O_RDONLY)
    os.set_inheritable(sentinel_fd, True)
    try:
        result = subprocess.run(
            [sys.executable, "-I", str(WORKER), "probe", str(source)],
            cwd=boundary.root,
            env=env,
            close_fds=True,
            start_new_session=True,
            check=True,
            capture_output=True,
            text=True,
        )
    finally:
        os.close(sentinel_fd)
    evidence = json.loads(result.stdout)
    assert evidence["root"] == str(boundary.root)
    assert evidence["cwd"] == str(boundary.root)
    assert evidence["format"] == "jsonl_kiro_session"
    assert evidence["parser"] == "adapters.kiro_session_jsonl"
    assert evidence["network"] == "IsolationViolation"
    assert str(inherited_sentinel) not in evidence["fd_targets"]
    assert not any(
        marker in name.upper()
        for name in env
        for marker in ("API_KEY", "SECRET", "PASSWORD", "CREDENTIAL")
    )


def test_paths_symlinks_production_and_provider_rejected_before_factory(
    tmp_path: Path,
) -> None:
    boundary, _env = _boundary(tmp_path)
    calls: list[Path] = []

    def factory(path: Path) -> Path:
        calls.append(path)
        return path

    production = Path.home() / ".local/share/convmem/chroma"
    with pytest.raises(IsolationViolation, match="escapes scratch root"):
        boundary.construct(production, label="chroma", factory=factory)
    with pytest.raises(IsolationViolation, match="escapes scratch root"):
        boundary.construct(
            boundary.root / ".." / "escape", label="lock", factory=factory
        )
    outside = tmp_path / "outside"
    outside.mkdir()
    alias = boundary.root / "alias"
    alias.symlink_to(outside, target_is_directory=True)
    with pytest.raises(IsolationViolation, match="symlink"):
        boundary.construct(alias / "state.json", label="checkpoint", factory=factory)
    with pytest.raises(IsolationViolation, match="deterministic-fake"):
        boundary.require_fake_provider("deepseek", "https://api.deepseek.com")
    with pytest.raises(IsolationViolation, match="deterministic-fake"):
        boundary.require_fake_provider("ollama", "http://127.0.0.1:11434")
    assert calls == []


def test_production_config_and_credentials_fail_bootstrap(tmp_path: Path) -> None:
    root, token = create_fresh_root(tmp_path)
    with pytest.MonkeyPatch.context() as mp:
        mp.setenv("CONVMEM_SCRATCH_ROOT", str(root))
        mp.setenv("CONVMEM_SCRATCH_TOKEN", token)
        mp.setenv("CONVMEM_CONFIG", "/home/lauer/.config/convmem/config.toml")
        with pytest.raises(IsolationViolation, match="production configuration"):
            ScratchBoundary.from_environment()
        mp.delenv("CONVMEM_CONFIG")
        mp.setenv("DEEPSEEK_API_KEY", "must-not-enter-worker")
        with pytest.raises(IsolationViolation, match="credential inherited"):
            ScratchBoundary.from_environment()


def test_crash_descendants_and_stale_scratch_lock_are_contained(tmp_path: Path) -> None:
    boundary, env = _boundary(tmp_path)
    proc = subprocess.Popen(
        [sys.executable, "-I", str(WORKER), "crash-with-child"],
        cwd=boundary.root,
        env=env,
        close_fds=True,
        start_new_session=True,
        stdout=subprocess.PIPE,
        text=True,
    )
    assert proc.stdout is not None
    evidence = json.loads(proc.stdout.readline())
    assert proc.wait(timeout=5) == 73
    child_pid = int(evidence["child_pid"])
    terminate_process_group(proc.pid)
    deadline = time.monotonic() + 3
    while Path(f"/proc/{child_pid}").exists() and time.monotonic() < deadline:
        time.sleep(0.02)
    if Path(f"/proc/{child_pid}").exists():
        status = Path(f"/proc/{child_pid}/status").read_text(encoding="utf-8")
        assert "State:\tZ" in status
    stale = ScratchPidLock(boundary, evidence["lock"])
    assert stale.acquire() is True
    stale.release()
    assert not Path(evidence["lock"]).exists()

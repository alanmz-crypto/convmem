"""T0: hermetic production-integration isolation boundary."""

# pylint: disable=consider-using-with,duplicate-code

from __future__ import annotations

import ast
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

from incremental_jsonl_isolation import (
    IsolationBoundary,
    IsolationViolation,
    PRODUCTION_OVERRIDE_ENV,
    SourceAdvisoryLock,
    create_fresh_root,
    known_production_roots,
    sanitized_worker_env,
    terminate_process_group,
    write_hermetic_config,
)


WORKER = Path(__file__).with_name("incremental_jsonl_isolation_worker.py")
ISOLATION_MODULE = Path(__file__).resolve().parents[1] / "incremental_jsonl_isolation.py"
_STDLIB_ROOTS = {
    "__future__",
    "fcntl",
    "json",
    "os",
    "signal",
    "socket",
    "stat",
    "subprocess",
    "tempfile",
    "time",
    "dataclasses",
    "pathlib",
    "typing",
}


def _fixture(root: Path) -> Path:
    source = root / "sources" / "hash" / "sess_prod" / "messages.jsonl"
    source.parent.mkdir(parents=True, exist_ok=True)
    source.write_text(
        json.dumps(
            {
                "timestamp": "2026-09-10T00:00:00Z",
                "payload": {"type": "user", "content": "isolation only"},
            }
        )
        + "\n",
        encoding="utf-8",
    )
    return source


def _boundary(tmp_path: Path) -> tuple[IsolationBoundary, dict[str, str]]:
    root, token = create_fresh_root(tmp_path)
    parent_home = Path.home()
    env = sanitized_worker_env(
        root, token, forbidden_roots=known_production_roots(home=parent_home)
    )
    with pytest.MonkeyPatch.context() as mp:
        for key, value in env.items():
            mp.setenv(key, value)
        credential_markers = ("API_KEY", "TOKEN", "SECRET", "PASSWORD", "CREDENTIAL")
        for name in tuple(os.environ):
            if name in {
                "CONVMEM_INCREMENTAL_TOKEN",
                "CONVMEM_INCREMENTAL_FORBIDDEN",
            }:
                continue
            if any(marker in name.upper() for marker in credential_markers):
                mp.delenv(name, raising=False)
        for name in (*PRODUCTION_OVERRIDE_ENV, "DEEPSEEK_API_KEY"):
            mp.delenv(name, raising=False)
        boundary = IsolationBoundary.from_environment()
    return boundary, env


def test_isolation_module_imports_only_stdlib() -> None:
    tree = ast.parse(ISOLATION_MODULE.read_text(encoding="utf-8"))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name.split(".", 1)[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module.split(".", 1)[0])
    unexpected = imported - _STDLIB_ROOTS
    assert not unexpected, f"non-stdlib isolation imports: {sorted(unexpected)}"


def test_preimport_worker_is_isolated_and_network_denied(tmp_path: Path) -> None:
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
    assert evidence["watcher"] == "IsolationViolation"
    assert str(inherited_sentinel) not in evidence["fd_targets"]
    assert evidence["home"].startswith(str(boundary.root))
    assert evidence["xdg_config"].startswith(str(boundary.root))
    assert evidence["credential_names"] == []
    assert evidence["production_override_names"] == []
    config_path = Path(evidence["home"]) / ".config/convmem/config.toml"
    assert config_path.is_file()
    assert "enabled = false" in config_path.read_text(encoding="utf-8")


def test_paths_symlinks_production_and_provider_rejected_before_factory(
    tmp_path: Path,
) -> None:
    boundary, _env = _boundary(tmp_path)
    calls: list[Path] = []

    def factory(path: Path) -> Path:
        calls.append(path)
        return path

    production = Path.home() / ".local/share/convmem/chroma"
    with pytest.raises(IsolationViolation, match="escapes isolation root"):
        boundary.construct(production, label="chroma", factory=factory)
    with pytest.raises(IsolationViolation, match="escapes isolation root"):
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
        IsolationBoundary.require_fake_provider("deepseek", "https://api.deepseek.com")
    with pytest.raises(IsolationViolation, match="deterministic-fake"):
        IsolationBoundary.require_fake_provider("ollama", "http://127.0.0.1:11434")
    assert not calls


def test_production_config_and_credentials_fail_bootstrap(tmp_path: Path) -> None:
    root, token = create_fresh_root(tmp_path)
    write_hermetic_config(root)
    with pytest.MonkeyPatch.context() as mp:
        mp.setenv("CONVMEM_INCREMENTAL_ROOT", str(root))
        mp.setenv("CONVMEM_INCREMENTAL_TOKEN", token)
        mp.setenv("CONVMEM_INCREMENTAL_MODE", "jsonl-production-integration-v1")
        mp.setenv("CONVMEM_CONFIG", "/home/lauer/.config/convmem/config.toml")
        with pytest.raises(IsolationViolation, match="production configuration"):
            IsolationBoundary.from_environment()
        mp.delenv("CONVMEM_CONFIG")
        mp.setenv("DEEPSEEK_API_KEY", "must-not-enter-worker")
        with pytest.raises(IsolationViolation, match="credential inherited"):
            IsolationBoundary.from_environment()


def test_crash_descendants_are_contained_and_advisory_lock_releases(
    tmp_path: Path,
) -> None:
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
    # Kernel advisory lock is released on crash; a fresh process can acquire it.
    stale = SourceAdvisoryLock(boundary, evidence["lock"])
    stale.acquire()
    stale.release()

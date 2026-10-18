"""Bwrap envelope for Arc Codex #286 T1 hermetic verification."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from tests.watch_oom_live_diagnosis_bwrap import (
    BWRAP_RO_ROOT_ARGS,
    bwrap_available,
    d1_bwrap_integration_available,
    production_convmem_dirs,
    write_denied_without_mutation,
)

ISSUE_286_BWRAP_ACTIVE_ENV = "CONVMEM_ISSUE_286_BWRAP_ACTIVE"
REPO_ROOT = Path(__file__).resolve().parents[1]


def issue_286_bwrap_integration_available() -> bool:
    return d1_bwrap_integration_available()


def _narrow_production_mask_binds(scratch_root: Path) -> list[tuple[str, str]]:
    """Mask default production data paths without hiding git worktrees under share."""
    mask_root = scratch_root.resolve() / ".bwrap-production-mask"
    share, config = production_convmem_dirs()
    binds: list[tuple[str, str]] = []
    config_empty = mask_root / "empty-config-convmem"
    config_empty.mkdir(parents=True, exist_ok=True)
    binds.append((str(config_empty), str(config)))
    targets = [
        ("chroma", True),
        ("processed.json", False),
        ("knowledge_units.jsonl", False),
        ("incremental-jsonl", True),
        ("synthesis_failures.jsonl", False),
    ]
    for rel, is_dir in targets:
        target = share / rel
        if not target.exists():
            continue
        empty = mask_root / f"empty-{rel.replace('/', '-')}"
        if is_dir:
            empty.mkdir(parents=True, exist_ok=True)
        else:
            empty.parent.mkdir(parents=True, exist_ok=True)
            empty.write_bytes(b"")
        binds.append((str(empty), str(target)))
    return binds


def build_issue_286_bwrap_command(
    inner_argv: list[str],
    *,
    scratch_root: Path,
    source_path: Path,
    repo_root: Path,
) -> list[str]:
    if not bwrap_available():
        raise RuntimeError("bwrap_unavailable")
    scratch_root = scratch_root.resolve()
    source_path = source_path.resolve()
    repo_root = repo_root.resolve()
    cmd: list[str] = [
        "bwrap",
        "--unshare-user",
        "--unshare-net",
        "--die-with-parent",
        *BWRAP_RO_ROOT_ARGS,
        "--tmpfs",
        "/tmp",
    ]
    for empty, target in _narrow_production_mask_binds(scratch_root):
        cmd.extend(["--ro-bind", empty, target])
    cmd.extend(
        [
            "--bind",
            str(scratch_root),
            str(scratch_root),
            "--ro-bind",
            str(source_path),
            str(source_path),
            "--chdir",
            str(repo_root),
            "--",
            *inner_argv,
        ]
    )
    return cmd


def ensure_probe_source(scratch_root: Path) -> Path:
    source = scratch_root / "sources" / "probe.jsonl"
    source.parent.mkdir(parents=True, exist_ok=True)
    if not source.is_file():
        source.write_bytes(b"{}" + bytes([10]))
    return source


def run_bwrap(
    inner_argv: list[str],
    *,
    scratch_root: Path,
    timeout: float = 180.0,
    extra_env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    if not issue_286_bwrap_integration_available():
        raise RuntimeError("issue_286_bwrap_unavailable")
    scratch_root = scratch_root.resolve()
    source = ensure_probe_source(scratch_root)
    cmd = build_issue_286_bwrap_command(
        inner_argv,
        scratch_root=scratch_root,
        source_path=source,
        repo_root=REPO_ROOT,
    )
    env = dict(extra_env or {})
    env.setdefault("PATH", os.environ.get("PATH", os.defpath))
    env[ISSUE_286_BWRAP_ACTIVE_ENV] = "1"
    return subprocess.run(
        cmd,
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )


def _production_dirs_hidden_narrow() -> bool:
    share, _config = production_convmem_dirs()
    for rel in ("chroma", "processed.json", "knowledge_units.jsonl"):
        path = share / rel
        try:
            if path.exists() and any(path.iterdir() if path.is_dir() else [path]):
                if path.is_dir() and list(path.iterdir()):
                    return False
                if path.is_file() and path.stat().st_size > 0:
                    return False
        except OSError:
            return False
    return True


def run_bwrap_capability_check(
    *,
    scratch_root: Path,
    source_path: Path,
    repo_probe_file: Path,
    timeout: float = 30.0,
) -> dict[str, bool]:
    script = (
        "import json, os, sys\n"
        "from pathlib import Path\n"
        f"sys.path.insert(0, {str(REPO_ROOT.resolve())!r})\n"
        "from tests.issue_286_codex_bootstrap_bwrap import (\n"
        "    _production_dirs_hidden_narrow,\n"
        ")\n"
        "from tests.watch_oom_live_diagnosis_bwrap import write_denied_without_mutation\n"
        f"scratch = {str(scratch_root)!r}\n"
        f"source = Path({str(source_path)!r})\n"
        f"repo_probe = Path({str(repo_probe_file)!r})\n"
        "out = {}\n"
        "p = os.path.join(scratch, 'bwrap_write_probe.txt')\n"
        "try:\n"
        "    with open(p, 'w', encoding='utf-8') as handle:\n"
        "        handle.write('ok\\n')\n"
        "    out['scratch_writable'] = os.path.isfile(p)\n"
        "except OSError:\n"
        "    out['scratch_writable'] = False\n"
        "out['source_readonly'] = write_denied_without_mutation(source)\n"
        "out['repo_readonly'] = write_denied_without_mutation(repo_probe)\n"
        "out['production_share_read_blocked'] = _production_dirs_hidden_narrow()\n"
        "out['production_share_write_blocked'] = write_denied_without_mutation(Path.home() / '.local/share/convmem/chroma')\n"
        "print(json.dumps(out))\n"
    )
    cmd = build_issue_286_bwrap_command(
        [sys.executable, "-c", script],
        scratch_root=scratch_root,
        source_path=source_path,
        repo_root=REPO_ROOT,
    )
    result = subprocess.run(
        cmd,
        check=False,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    if result.returncode != 0:
        raise RuntimeError(f"bwrap_capability_check_failed:{result.stderr.strip()}")
    return json.loads(result.stdout.strip())

"""Clean tracked git export of the candidate source commit."""

from __future__ import annotations

import os
import subprocess
import tempfile
from pathlib import Path


def export_source_commit(repo: Path, source_commit: str) -> Path:
    subprocess.run(
        ["git", "-C", str(repo), "cat-file", "-e", f"{source_commit}^{{commit}}"],
        check=True,
        capture_output=True,
        close_fds=True,
    )
    status = subprocess.run(
        ["git", "-C", str(repo), "status", "--porcelain"],
        check=True,
        capture_output=True,
        text=True,
        close_fds=True,
    )
    if status.stdout.strip():
        raise SystemExit("dirty_worktree_forbidden_before_export")
    dest = Path(tempfile.mkdtemp(prefix="convmem-openclaw-src.", dir="/tmp"))
    archive = subprocess.run(
        ["git", "-C", str(repo), "archive", "--format=tar", source_commit],
        check=True,
        capture_output=True,
        close_fds=True,
    )
    subprocess.run(
        ["tar", "-xf", "-", "-C", str(dest)],
        input=archive.stdout,
        check=True,
        close_fds=True,
    )
    if (dest / ".git").exists():
        raise SystemExit("export_contains_git")
    os.chmod(dest, 0o755)
    return dest

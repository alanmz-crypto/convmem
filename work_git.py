"""convmem work start / resume — Always-Available GitHub Fallback helpers."""

from __future__ import annotations

import subprocess
import sys
from datetime import date
from pathlib import Path

from git_hooks import valid_task_branch

WORKTREE_ROOT = Path("~/.local/share/convmem/worktrees").expanduser()
ALLOWED_TYPES = ("feat", "fix", "docs", "plan", "wip")


class WorkError(RuntimeError):
    """Fail-closed work helper error."""


def _run(repo: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    proc = subprocess.run(
        ["git", *args],
        cwd=repo,
        capture_output=True,
        text=True,
    )
    if check and proc.returncode != 0:
        msg = (proc.stderr or proc.stdout or "git failed").strip()
        raise WorkError(msg)
    return proc


def _validate_branch(name: str) -> None:
    if not valid_task_branch(name):
        raise WorkError(
            f"invalid task branch: {name!r} "
            f"(expected feat|fix|docs|plan|wip/YYYY-MM-DD-slug)"
        )


def _explicit_push(repo: Path, branch: str, *, set_upstream: bool = False) -> None:
    _validate_branch(branch)
    refspec = f"{branch}:refs/heads/{branch}"
    args = ["push"]
    if set_upstream:
        args.append("-u")
    args.extend(["origin", refspec])
    _run(repo, *args)


def _repo_root(start: Path | None = None) -> Path:
    base = start or Path.cwd()
    proc = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        cwd=base,
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        raise WorkError("not a git repository")
    return Path(proc.stdout.strip())


def _local_worktree_conflict(repo: Path, branch: str) -> str | None:
    """MVP: detect branch checked out in another worktree of this gitdir."""
    proc = _run(repo, "worktree", "list", "--porcelain", check=False)
    if proc.returncode != 0:
        return None
    current = None
    branch_ref = f"refs/heads/{branch}"
    for ln in proc.stdout.splitlines():
        if ln.startswith("worktree "):
            current = ln[len("worktree ") :]
        elif ln.startswith("branch ") and ln[len("branch ") :] == branch_ref:
            # Compare to primary checkout path
            primary = str(repo.resolve())
            if current and Path(current).resolve() != Path(primary).resolve():
                return current
    return None


def build_branch_name(kind: str, slug: str, *, when: date | None = None) -> str:
    kind = kind.strip().lower()
    if kind not in ALLOWED_TYPES:
        raise WorkError(f"type must be one of {ALLOWED_TYPES}, got {kind!r}")
    slug = slug.strip().strip("/")
    if not slug or "/" in slug or " " in slug:
        raise WorkError(f"slug must be a single path segment, got {slug!r}")
    day = (when or date.today()).isoformat()
    name = f"{kind}/{day}-{slug}"
    _validate_branch(name)
    return name


def work_start(
    kind: str,
    slug: str,
    *,
    repo: Path | None = None,
    worktree: bool = False,
) -> str:
    """Create branch from origin/main, push explicit refspec, fail closed."""
    root = _repo_root(repo)
    branch = build_branch_name(kind, slug)
    _validate_branch(branch)
    conflict = _local_worktree_conflict(root, branch)
    if conflict:
        raise WorkError(f"branch {branch} already checked out in worktree {conflict}")

    _run(root, "fetch", "origin")
    if worktree:
        WORKTREE_ROOT.mkdir(parents=True, exist_ok=True)
        dest = WORKTREE_ROOT / branch.replace("/", "-")
        if dest.exists():
            raise WorkError(f"worktree path exists: {dest}")
        _run(
            root,
            "worktree",
            "add",
            str(dest),
            "-b",
            branch,
            "origin/main",
        )
        cwd = dest
    else:
        cur = _run(root, "branch", "--show-current").stdout.strip()
        if cur == "main" or cur == "master":
            dirty = _run(root, "status", "--porcelain").stdout.strip()
            # Allow untracked noise; block tracked dirt switching away carelessly
            tracked = [
                ln
                for ln in dirty.splitlines()
                if ln and not ln.startswith("??") and not ln.startswith("!!")
            ]
            if tracked:
                raise WorkError(
                    "shared checkout on main has tracked dirty files; "
                    "use --worktree or clean/stash authorized paths first"
                )
        _run(root, "switch", "-c", branch, "origin/main")
        cwd = root

    _explicit_push(cwd, branch, set_upstream=True)
    return branch


def work_resume(branch: str, *, repo: Path | None = None, worktree: bool = False) -> str:
    """Resume existing remote (or local) task branch; fail closed."""
    root = _repo_root(repo)
    branch = branch.strip()
    _validate_branch(branch)
    conflict = _local_worktree_conflict(root, branch)
    if conflict:
        raise WorkError(f"branch {branch} already checked out in worktree {conflict}")

    _run(root, "fetch", "origin")

    if worktree:
        WORKTREE_ROOT.mkdir(parents=True, exist_ok=True)
        dest = WORKTREE_ROOT / branch.replace("/", "-")
        if dest.exists():
            raise WorkError(f"worktree path exists: {dest}")
        local = _run(root, "show-ref", "--verify", "--quiet", f"refs/heads/{branch}", check=False)
        if local.returncode == 0:
            _run(root, "worktree", "add", str(dest), branch)
        else:
            _run(
                root,
                "worktree",
                "add",
                str(dest),
                "-b",
                branch,
                f"origin/{branch}",
            )
        cwd = dest
    else:
        local = _run(root, "show-ref", "--verify", "--quiet", f"refs/heads/{branch}", check=False)
        if local.returncode == 0:
            _run(root, "switch", branch)
        else:
            _run(root, "switch", "--track", "-c", branch, f"origin/{branch}")
        cwd = root

    # Ensure upstream + push any unpushed commits
    up = _run(cwd, "rev-parse", "--abbrev-ref", "@{u}", check=False)
    if up.returncode != 0:
        _explicit_push(cwd, branch, set_upstream=True)
    else:
        ahead = _run(cwd, "log", "@{u}..HEAD", "--oneline", check=False)
        if ahead.stdout.strip():
            _explicit_push(cwd, branch, set_upstream=False)
    return branch

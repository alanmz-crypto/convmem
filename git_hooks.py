"""Shared git guards for pre-commit / pre-push hooks and doctor checks."""

from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

# WIP subjects: WIP:, wip:, WIP , wip(scope):, WIP!:
WIP_SUBJECT_RE = re.compile(r"^[Ww][Ii][Pp][:(! ]")

# Conventional feat:/fix: (optional scope) — used by tests / historical helpers
CONVENTIONAL_SUBJECT_RE = re.compile(r"^(feat|fix)(\(.+\))?:")

TASK_BRANCH_RE = re.compile(
    r"^(feat|fix|docs|plan|wip)/[0-9]{4}-[0-9]{2}-[0-9]{2}-.+$"
)

REJECTION_PUSH_MAIN = """\
Push rejected: agents must not push to main.
Create or resume a task branch, then push that branch:
  convmem work start feat short-slug
  # or: git switch -c feat/YYYY-MM-DD-slug origin/main
  #     git push -u origin "feat/YYYY-MM-DD-slug:refs/heads/feat/YYYY-MM-DD-slug"
Local hook bypass (NOT authorization — anyone can set this env):
  CONVMEM_SKIP_MAIN_HOOK=1 git push
GitHub branch protection is the real authz boundary (Ryan).
"""

REJECTION_COMMIT_MAIN = """\
Commit rejected: agents must not commit on main.
Create or resume a task branch first:
  convmem work start feat short-slug
Local hook bypass (NOT authorization — anyone can set this env):
  CONVMEM_SKIP_MAIN_HOOK=1 git commit ...
"""

# Legacy alias still honored as hook skip only (same caveats as CONVMEM_SKIP_MAIN_HOOK)
_BYPASS_ENVS = ("CONVMEM_SKIP_MAIN_HOOK", "CONVMEM_SKIP_WIP_HOOK")


def main_hook_bypass_enabled() -> bool:
    for name in _BYPASS_ENVS:
        if os.environ.get(name, "").strip().lower() in ("1", "true", "yes"):
            return True
    return False


def wip_commit_blocked(subject: str) -> bool:
    """True when commit subject matches WIP-pattern."""
    return bool(WIP_SUBJECT_RE.match(subject.strip()))


def conventional_feat_fix_subject(subject: str) -> bool:
    """True when subject is feat:/fix: (optional scope)."""
    return bool(CONVENTIONAL_SUBJECT_RE.match(subject.strip()))


def valid_task_branch(name: str) -> bool:
    """True when branch matches feat|fix|docs|plan|wip/YYYY-MM-DD-slug."""
    return bool(TASK_BRANCH_RE.match(name.strip()))


def _git(repo: Path, *args: str, timeout: int = 15) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=repo,
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def repo_root(start: Path | None = None) -> Path | None:
    base = start or Path(__file__).resolve().parent
    proc = _git(base, "rev-parse", "--show-toplevel")
    if proc.returncode != 0:
        return None
    return Path(proc.stdout.strip())


def current_branch(repo: Path) -> str:
    proc = _git(repo, "branch", "--show-current")
    if proc.returncode != 0:
        return ""
    return proc.stdout.strip()


def hooks_path_ok(repo: Path) -> tuple[bool, str]:
    """Return (ok, detail) for core.hooksPath + pre-push (+ pre-commit) executable."""
    proc = _git(repo, "config", "--get", "core.hooksPath")
    if proc.returncode != 0 or not proc.stdout.strip():
        return False, "core.hooksPath unset — run scripts/install-git-hooks.sh"
    configured = proc.stdout.strip()
    hooks_dir = Path(configured)
    if not hooks_dir.is_absolute():
        hooks_dir = (repo / configured).resolve()
    expected = (repo / "scripts" / "git-hooks").resolve()
    if hooks_dir != expected:
        return False, f"core.hooksPath={configured!r} (expected scripts/git-hooks)"
    for name in ("pre-push", "pre-commit"):
        hook = hooks_dir / name
        if not hook.is_file():
            return False, f"missing {hook}"
        if not os.access(hook, os.X_OK):
            return False, f"not executable: {hook}"
    return True, "hooksPath=scripts/git-hooks (pre-push+pre-commit ok)"


def wip_subjects_on_main(repo: Path, *, limit: int = 50) -> list[str]:
    """Commit subjects on main (last N) that match WIP pattern."""
    proc = _git(repo, "log", "main", f"-n{limit}", "--format=%s")
    if proc.returncode != 0:
        return []
    return [ln for ln in proc.stdout.splitlines() if wip_commit_blocked(ln)]


def direct_feat_fix_via_reflog(repo: Path, *, limit: int = 50) -> tuple[str | None, list[str]]:
    """Historical helper — no longer used by doctor (hard hooks supersede)."""
    proc = _git(repo, "reflog", "show", "main", f"-n{limit}", "--format=%gs")
    if proc.returncode != 0:
        return "no main reflog; unable to measure", []
    lines = [ln.strip() for ln in proc.stdout.splitlines() if ln.strip()]
    if not lines:
        return "no main reflog; unable to measure", []
    flagged: list[str] = []
    for gs in lines:
        if not gs.startswith("commit: "):
            continue
        subject = gs[len("commit: ") :]
        if conventional_feat_fix_subject(subject):
            flagged.append(gs)
    return None, flagged


def dirty_tracked_on_main(repo: Path) -> tuple[bool, str]:
    """True when HEAD is main/master and the index/worktree has tracked changes."""
    branch = current_branch(repo)
    if branch not in ("main", "master"):
        return False, f"on {branch or 'detached'}"
    proc = _git(repo, "status", "--porcelain")
    if proc.returncode != 0:
        return False, "git status failed"
    dirty = []
    for ln in proc.stdout.splitlines():
        if not ln or len(ln) < 3:
            continue
        # Skip untracked-only noise for "tracked dirty" signal; XY with M/A/D/R/C
        code = ln[:2]
        if "M" in code or "A" in code or "D" in code or "R" in code or "C" in code:
            dirty.append(ln[3:].strip())
        elif code.strip() and not code.startswith("?"):
            dirty.append(ln[3:].strip())
    if not dirty:
        return False, "main clean (tracked)"
    return True, f"tracked dirty on main: {', '.join(dirty[:5])}"


def unpushed_commits(repo: Path) -> tuple[str | None, list[str]]:
    """Return (error_or_none, subjects) for commits ahead of @{u}."""
    up = _git(repo, "rev-parse", "--abbrev-ref", "@{u}")
    if up.returncode != 0:
        return "no upstream configured", []
    proc = _git(repo, "log", "@{u}..HEAD", "--format=%s")
    if proc.returncode != 0:
        return "git log failed", []
    return None, [ln for ln in proc.stdout.splitlines() if ln.strip()]


def commits_in_range(repo: Path, old_sha: str, new_sha: str) -> list[tuple[str, str]]:
    """Return (sha, subject) for commits reachable from new_sha not in old_sha."""
    if re.fullmatch(r"0+", new_sha or ""):
        return []
    if re.fullmatch(r"0+", old_sha or ""):
        rev_range = new_sha
    else:
        rev_range = f"{old_sha}..{new_sha}"
    proc = _git(repo, "log", rev_range, "--format=%H %s")
    if proc.returncode != 0:
        return []
    out: list[tuple[str, str]] = []
    for ln in proc.stdout.splitlines():
        parts = ln.split(" ", 1)
        if len(parts) == 2:
            out.append((parts[0], parts[1]))
    return out


def evaluate_pre_commit(repo: Path) -> int:
    """Reject commits when HEAD is main/master unless bypass env set."""
    if main_hook_bypass_enabled():
        print(
            "WARNING: CONVMEM_SKIP_MAIN_HOOK (or legacy WIP skip) set — "
            "bypassing main commit guard (hook skip only; not GitHub authz)",
            file=sys.stderr,
        )
        return 0
    branch = current_branch(repo)
    if branch in ("main", "master"):
        sys.stderr.write(REJECTION_COMMIT_MAIN)
        return 1
    return 0


def evaluate_pre_push_stdin(repo: Path, stdin_text: str) -> int:
    """Reject any push whose remote ref is main/master unless bypass env set."""
    if main_hook_bypass_enabled():
        print(
            "WARNING: CONVMEM_SKIP_MAIN_HOOK (or legacy WIP skip) set — "
            "bypassing main push guard (hook skip only; not GitHub authz)",
            file=sys.stderr,
        )
        return 0

    for line in stdin_text.splitlines():
        parts = line.split()
        if len(parts) < 4:
            continue
        _local_ref, local_sha, remote_ref, _remote_sha = (
            parts[0],
            parts[1],
            parts[2],
            parts[3],
        )
        if remote_ref not in ("refs/heads/main", "refs/heads/master"):
            continue
        if re.fullmatch(r"0+", local_sha):
            continue  # delete
        sys.stderr.write(REJECTION_PUSH_MAIN)
        return 1
    return 0


def main() -> int:
    """CLI entry for shell hooks. argv: pre-commit | pre-push (default pre-push)."""
    repo = repo_root()
    if repo is None:
        print("git hook: not a git repo", file=sys.stderr)
        return 0
    mode = "pre-push"
    if len(sys.argv) > 1 and sys.argv[1] in ("pre-commit", "pre-push"):
        mode = sys.argv[1]
    if mode == "pre-commit":
        return evaluate_pre_commit(repo)
    return evaluate_pre_push_stdin(repo, sys.stdin.read())


if __name__ == "__main__":
    raise SystemExit(main())

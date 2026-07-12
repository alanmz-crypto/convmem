"""Shared git commit classification for pre-push hook and doctor checks."""

from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path

# WIP subjects: WIP:, wip:, WIP , wip(scope):, WIP!:
WIP_SUBJECT_RE = re.compile(r"^[Ww][Ii][Pp][:(! ]")

# Conventional feat:/fix: (optional scope)
CONVENTIONAL_SUBJECT_RE = re.compile(r"^(feat|fix)(\(.+\))?:")

REJECTION_STDERR = """\
Push rejected: WIP commits on main. Create a branch first:
  git checkout -b feat/YYYY-MM-DD-slug
  git push -u origin feat/YYYY-MM-DD-slug
To bypass (Ryan only): CONVMEM_SKIP_WIP_HOOK=1 git push
"""


def wip_commit_blocked(subject: str) -> bool:
    """True when commit subject matches WIP-pattern (blocked on push to main)."""
    return bool(WIP_SUBJECT_RE.match(subject.strip()))


def conventional_feat_fix_subject(subject: str) -> bool:
    """True when subject is feat:/fix: (optional scope)."""
    return bool(CONVENTIONAL_SUBJECT_RE.match(subject.strip()))


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


def hooks_path_ok(repo: Path) -> tuple[bool, str]:
    """Return (ok, detail) for core.hooksPath + pre-push executable."""
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
    pre_push = hooks_dir / "pre-push"
    if not pre_push.is_file():
        return False, f"missing {pre_push}"
    if not os.access(pre_push, os.X_OK):
        return False, f"not executable: {pre_push}"
    return True, f"hooksPath=scripts/git-hooks (pre-push ok)"


def wip_subjects_on_main(repo: Path, *, limit: int = 50) -> list[str]:
    """Commit subjects on main (last N) that match WIP pattern."""
    proc = _git(repo, "log", "main", f"-n{limit}", "--format=%s")
    if proc.returncode != 0:
        return []
    return [ln for ln in proc.stdout.splitlines() if wip_commit_blocked(ln)]


def direct_feat_fix_via_reflog(repo: Path, *, limit: int = 50) -> tuple[str | None, list[str]]:
    """Heuristic: main reflog ``commit:`` entries with feat:/fix: subjects.

    Returns (error_or_none, flagged_one_liners).
    error ``no main reflog; unable to measure`` when reflog unavailable.
    """
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


def commits_in_range(repo: Path, old_sha: str, new_sha: str) -> list[tuple[str, str]]:
    """Return (sha, subject) for commits reachable from new_sha not in old_sha."""
    if re.fullmatch(r"0+", new_sha or ""):
        return []  # branch delete
    if re.fullmatch(r"0+", old_sha or ""):
        rev_range = new_sha  # new branch
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


def evaluate_pre_push_stdin(repo: Path, stdin_text: str) -> int:
    """Process pre-push stdin. Return 0 allow, 1 reject."""
    if os.environ.get("CONVMEM_SKIP_WIP_HOOK", "").strip() in ("1", "true", "yes"):
        print(
            "WARNING: CONVMEM_SKIP_WIP_HOOK set — bypassing WIP-on-main check (Ryan only)",
            file=__import__("sys").stderr,
        )
        return 0

    for line in stdin_text.splitlines():
        parts = line.split()
        if len(parts) < 4:
            continue
        _local_ref, local_sha, remote_ref, remote_sha = parts[0], parts[1], parts[2], parts[3]
        if remote_ref not in ("refs/heads/main", "refs/heads/master"):
            continue
        if re.fullmatch(r"0+", local_sha):
            continue  # delete
        commits = commits_in_range(repo, remote_sha, local_sha)
        blocked = [(sha, subj) for sha, subj in commits if wip_commit_blocked(subj)]
        if blocked:
            import sys

            sys.stderr.write(REJECTION_STDERR)
            for sha, subj in blocked[:5]:
                sys.stderr.write(f"  {sha[:8]} {subj}\n")
            return 1
    return 0


def main() -> int:
    """CLI entry for the shell pre-push wrapper."""
    import sys

    repo = repo_root()
    if repo is None:
        print("pre-push: not a git repo", file=sys.stderr)
        return 0
    return evaluate_pre_push_stdin(repo, sys.stdin.read())


if __name__ == "__main__":
    raise SystemExit(main())

"""Hermetic tests for work_git start/resume (temp bare remote — no GitHub)."""

from __future__ import annotations

import os
import subprocess
import tempfile
import unittest
from datetime import date
from pathlib import Path

from work_git import WorkError, build_branch_name, work_resume, work_start


def _git(repo: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    env = {
        **os.environ,
        "GIT_AUTHOR_NAME": "t",
        "GIT_AUTHOR_EMAIL": "t@t",
        "GIT_COMMITTER_NAME": "t",
        "GIT_COMMITTER_EMAIL": "t@t",
    }
    return subprocess.run(
        ["git", *args],
        cwd=repo,
        check=check,
        capture_output=True,
        text=True,
        env=env,
    )


def _refs_heads(remote: Path, branch: str) -> bool:
    proc = _git(remote, "show-ref", "--verify", "--quiet", f"refs/heads/{branch}", check=False)
    return proc.returncode == 0


class WorkGitHermeticTests(unittest.TestCase):
    def _bare_and_clone(self, td: Path) -> tuple[Path, Path]:
        bare = td / "remote.git"
        clone = td / "clone"
        _git(td, "init", "--bare", "-b", "main", str(bare))
        _git(td, "clone", str(bare), str(clone))
        (clone / "README").write_text("init\n", encoding="utf-8")
        _git(clone, "add", "README")
        _git(clone, "commit", "-m", "chore: init")
        _git(clone, "push", "-u", "origin", "main:refs/heads/main")
        return bare, clone

    def test_start_creates_branch_from_origin_main_explicit_push_upstream(self):
        with tempfile.TemporaryDirectory() as tmp:
            td = Path(tmp)
            bare, clone = self._bare_and_clone(td)
            main_sha = _git(clone, "rev-parse", "origin/main").stdout.strip()
            slug = "hermetic-start"
            expected = f"feat/{date.today().isoformat()}-{slug}"

            got = work_start("feat", slug, repo=clone)
            self.assertEqual(got, expected)
            self.assertEqual(_git(clone, "branch", "--show-current").stdout.strip(), expected)
            # Branched from origin/main tip
            self.assertEqual(_git(clone, "rev-parse", "HEAD").stdout.strip(), main_sha)
            # Explicit destination on remote
            self.assertTrue(_refs_heads(bare, expected), f"missing refs/heads/{expected} on bare")
            # Upstream set
            up = _git(clone, "rev-parse", "--abbrev-ref", "@{u}")
            self.assertEqual(up.returncode, 0)
            self.assertEqual(up.stdout.strip(), f"origin/{expected}")

    def test_resume_origin_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            td = Path(tmp)
            bare, clone = self._bare_and_clone(td)
            slug = "hermetic-resume"
            branch = work_start("feat", slug, repo=clone)

            # Second clone: branch exists only on origin
            other = td / "other"
            _git(td, "clone", str(bare), str(other))
            self.assertNotEqual(
                _git(other, "show-ref", "--verify", "--quiet", f"refs/heads/{branch}", check=False).returncode,
                0,
            )
            self.assertTrue(_refs_heads(bare, branch))

            got = work_resume(branch, repo=other)
            self.assertEqual(got, branch)
            self.assertEqual(_git(other, "branch", "--show-current").stdout.strip(), branch)
            up = _git(other, "rev-parse", "--abbrev-ref", "@{u}")
            self.assertEqual(up.returncode, 0)
            self.assertEqual(up.stdout.strip(), f"origin/{branch}")

    def test_invalid_taxonomy_fails_before_git_mutation(self):
        with tempfile.TemporaryDirectory() as tmp:
            td = Path(tmp)
            bare, clone = self._bare_and_clone(td)
            before_local = _git(clone, "for-each-ref", "--format=%(refname)", "refs/heads").stdout
            before_remote = _git(bare, "for-each-ref", "--format=%(refname)", "refs/heads").stdout
            head_before = _git(clone, "rev-parse", "HEAD").stdout.strip()
            branch_before = _git(clone, "branch", "--show-current").stdout.strip()

            with self.assertRaises(WorkError):
                work_start("feat", "bad/slug", repo=clone)
            with self.assertRaises(WorkError):
                work_start("feature", "ok-slug", repo=clone)
            with self.assertRaises(WorkError):
                build_branch_name("feat", "has space")

            self.assertEqual(
                _git(clone, "for-each-ref", "--format=%(refname)", "refs/heads").stdout,
                before_local,
            )
            self.assertEqual(
                _git(bare, "for-each-ref", "--format=%(refname)", "refs/heads").stdout,
                before_remote,
            )
            self.assertEqual(_git(clone, "rev-parse", "HEAD").stdout.strip(), head_before)
            self.assertEqual(_git(clone, "branch", "--show-current").stdout.strip(), branch_before)

    def test_fetch_failure_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            td = Path(tmp)
            _bare, clone = self._bare_and_clone(td)
            _git(clone, "remote", "set-url", "origin", str(td / "missing-remote.git"))
            with self.assertRaises(WorkError):
                work_start("feat", "fetch-fail", repo=clone)
            # Must not leave success-path branch checked out as ready
            cur = _git(clone, "branch", "--show-current").stdout.strip()
            self.assertEqual(cur, "main")
            self.assertFalse(
                any(
                    ln.endswith(f"feat/{date.today().isoformat()}-fetch-fail")
                    for ln in _git(clone, "branch", "--list").stdout.splitlines()
                )
            )

    def test_push_failure_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            td = Path(tmp)
            bare, clone = self._bare_and_clone(td)
            expected = f"feat/{date.today().isoformat()}-push-fail"
            # Fetch still works; make bare unwritable so push fails closed.
            for root, dirs, files in os.walk(bare):
                os.chmod(root, 0o555)
                for name in files:
                    os.chmod(Path(root) / name, 0o444)
            try:
                with self.assertRaises(WorkError):
                    work_start("feat", "push-fail", repo=clone)
            finally:
                for root, dirs, files in os.walk(bare):
                    os.chmod(root, 0o755)
                    for name in files:
                        os.chmod(Path(root) / name, 0o644)
            self.assertFalse(_refs_heads(bare, expected))


if __name__ == "__main__":
    unittest.main()

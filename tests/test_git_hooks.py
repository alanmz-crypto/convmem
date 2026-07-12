"""Tests for git_hooks classification and pre-push evaluation."""

from __future__ import annotations

import os
import subprocess
import tempfile
import unittest
from pathlib import Path

from git_hooks import (
    REJECTION_STDERR,
    conventional_feat_fix_subject,
    evaluate_pre_push_stdin,
    wip_commit_blocked,
)


def _git(repo: Path, *args: str, env: dict | None = None) -> None:
    subprocess.run(
        ["git", *args],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
        env=env,
    )


class WipSubjectTests(unittest.TestCase):
    def test_blocked(self):
        for s in (
            "WIP: preserve progress",
            "wip: something",
            "WIP still going",
            "wip(scope): x",
            "WIP!: breaking",
        ):
            self.assertTrue(wip_commit_blocked(s), s)

    def test_allowed(self):
        for s in (
            "feat: add thing",
            "fix: bug",
            "docs: typo",
            "[WIP] not at start",
            "checkpoint: save",
            "save progress: x",
        ):
            self.assertFalse(wip_commit_blocked(s), s)


class ConventionalSubjectTests(unittest.TestCase):
    def test_feat_fix(self):
        self.assertTrue(conventional_feat_fix_subject("feat: x"))
        self.assertTrue(conventional_feat_fix_subject("fix: y"))
        self.assertTrue(conventional_feat_fix_subject("feat(hooks): z"))
        self.assertFalse(conventional_feat_fix_subject("docs: x"))
        self.assertFalse(conventional_feat_fix_subject("WIP: x"))


class PrePushIntegrationTests(unittest.TestCase):
    def _init_repo(self, d: Path) -> Path:
        repo = d / "repo"
        repo.mkdir()
        env = {**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t",
               "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"}
        _git(repo, "init", "-b", "main", env=env)
        (repo / "a.txt").write_text("a\n", encoding="utf-8")
        _git(repo, "add", "a.txt", env=env)
        _git(repo, "commit", "-m", "chore: init", env=env)
        return repo

    def test_rejects_wip_push_to_main(self):
        with tempfile.TemporaryDirectory() as td:
            repo = self._init_repo(Path(td))
            env = {**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t",
                   "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"}
            main_sha = subprocess.check_output(
                ["git", "rev-parse", "HEAD"], cwd=repo, text=True
            ).strip()
            (repo / "b.txt").write_text("b\n", encoding="utf-8")
            _git(repo, "add", "b.txt", env=env)
            _git(repo, "commit", "-m", "WIP: do not push", env=env)
            new_sha = subprocess.check_output(
                ["git", "rev-parse", "HEAD"], cwd=repo, text=True
            ).strip()
            zeros = "0" * 40
            # Simulate push of new commits to remote main (remote had main_sha)
            stdin = f"refs/heads/main {new_sha} refs/heads/main {main_sha}\n"
            # Clear bypass if set in environment
            old = os.environ.pop("CONVMEM_SKIP_WIP_HOOK", None)
            try:
                rc = evaluate_pre_push_stdin(repo, stdin)
            finally:
                if old is not None:
                    os.environ["CONVMEM_SKIP_WIP_HOOK"] = old
            self.assertEqual(rc, 1)

            # feat: commit allowed
            _git(repo, "reset", "--hard", main_sha, env=env)
            (repo / "c.txt").write_text("c\n", encoding="utf-8")
            _git(repo, "add", "c.txt", env=env)
            _git(repo, "commit", "-m", "feat: allowed on main", env=env)
            feat_sha = subprocess.check_output(
                ["git", "rev-parse", "HEAD"], cwd=repo, text=True
            ).strip()
            stdin2 = f"refs/heads/main {feat_sha} refs/heads/main {main_sha}\n"
            self.assertEqual(evaluate_pre_push_stdin(repo, stdin2), 0)

            # Feature branch push with WIP is OK (not targeting main)
            _git(repo, "checkout", "-b", "feat/x", env=env)
            (repo / "d.txt").write_text("d\n", encoding="utf-8")
            _git(repo, "add", "d.txt", env=env)
            _git(repo, "commit", "-m", "WIP: ok on feature branch", env=env)
            wip_feat = subprocess.check_output(
                ["git", "rev-parse", "HEAD"], cwd=repo, text=True
            ).strip()
            zeros = "0" * 40
            stdin3 = f"refs/heads/feat/x {wip_feat} refs/heads/feat/x {zeros}\n"
            self.assertEqual(evaluate_pre_push_stdin(repo, stdin3), 0)

    def test_skip_env_bypasses(self):
        with tempfile.TemporaryDirectory() as td:
            repo = self._init_repo(Path(td))
            env = {**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t",
                   "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"}
            main_sha = subprocess.check_output(
                ["git", "rev-parse", "HEAD"], cwd=repo, text=True
            ).strip()
            (repo / "b.txt").write_text("b\n", encoding="utf-8")
            _git(repo, "add", "b.txt", env=env)
            _git(repo, "commit", "-m", "WIP: bypass", env=env)
            new_sha = subprocess.check_output(
                ["git", "rev-parse", "HEAD"], cwd=repo, text=True
            ).strip()
            stdin = f"refs/heads/main {new_sha} refs/heads/main {main_sha}\n"
            os.environ["CONVMEM_SKIP_WIP_HOOK"] = "1"
            try:
                self.assertEqual(evaluate_pre_push_stdin(repo, stdin), 0)
            finally:
                del os.environ["CONVMEM_SKIP_WIP_HOOK"]

    def test_rejection_message_constant(self):
        self.assertIn("Push rejected: WIP commits on main", REJECTION_STDERR)
        self.assertIn("CONVMEM_SKIP_WIP_HOOK=1", REJECTION_STDERR)


if __name__ == "__main__":
    unittest.main()

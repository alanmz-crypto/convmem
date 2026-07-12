"""Tests for git_hooks classification and main-guard evaluation."""

from __future__ import annotations

import os
import subprocess
import tempfile
import unittest
from pathlib import Path

from git_hooks import (
    REJECTION_PUSH_MAIN,
    conventional_feat_fix_subject,
    evaluate_pre_commit,
    evaluate_pre_push_stdin,
    valid_task_branch,
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


class TaxonomyTests(unittest.TestCase):
    def test_valid(self):
        self.assertTrue(valid_task_branch("feat/2026-07-12-slug"))
        self.assertTrue(valid_task_branch("docs/2026-07-12-x"))
        self.assertFalse(valid_task_branch("main"))
        self.assertFalse(valid_task_branch("feat/no-date"))
        self.assertFalse(valid_task_branch("feature/2026-07-12-x"))


class PrePushIntegrationTests(unittest.TestCase):
    def _init_repo(self, d: Path) -> Path:
        repo = d / "repo"
        repo.mkdir()
        env = {
            **os.environ,
            "GIT_AUTHOR_NAME": "t",
            "GIT_AUTHOR_EMAIL": "t@t",
            "GIT_COMMITTER_NAME": "t",
            "GIT_COMMITTER_EMAIL": "t@t",
        }
        _git(repo, "init", "-b", "main", env=env)
        (repo / "a.txt").write_text("a\n", encoding="utf-8")
        _git(repo, "add", "a.txt", env=env)
        _git(repo, "commit", "-m", "chore: init", env=env)
        return repo

    def test_rejects_any_push_to_main(self):
        with tempfile.TemporaryDirectory() as td:
            repo = self._init_repo(Path(td))
            env = {
                **os.environ,
                "GIT_AUTHOR_NAME": "t",
                "GIT_AUTHOR_EMAIL": "t@t",
                "GIT_COMMITTER_NAME": "t",
                "GIT_COMMITTER_EMAIL": "t@t",
            }
            main_sha = subprocess.check_output(
                ["git", "rev-parse", "HEAD"], cwd=repo, text=True
            ).strip()
            (repo / "b.txt").write_text("b\n", encoding="utf-8")
            _git(repo, "add", "b.txt", env=env)
            _git(repo, "commit", "-m", "feat: should not push to main", env=env)
            new_sha = subprocess.check_output(
                ["git", "rev-parse", "HEAD"], cwd=repo, text=True
            ).strip()
            stdin = f"refs/heads/main {new_sha} refs/heads/main {main_sha}\n"
            for key in ("CONVMEM_SKIP_MAIN_HOOK", "CONVMEM_SKIP_WIP_HOOK"):
                os.environ.pop(key, None)
            self.assertEqual(evaluate_pre_push_stdin(repo, stdin), 1)
            self.assertIn("must not push to main", REJECTION_PUSH_MAIN)

            # Feature branch push OK
            _git(repo, "checkout", "-b", "feat/2026-07-12-x", env=env)
            feat_sha = subprocess.check_output(
                ["git", "rev-parse", "HEAD"], cwd=repo, text=True
            ).strip()
            zeros = "0" * 40
            stdin_feat = f"refs/heads/feat/2026-07-12-x {feat_sha} refs/heads/feat/2026-07-12-x {zeros}\n"
            self.assertEqual(evaluate_pre_push_stdin(repo, stdin_feat), 0)

            # Bypass env allows main push (hook skip only)
            os.environ["CONVMEM_SKIP_MAIN_HOOK"] = "1"
            try:
                self.assertEqual(evaluate_pre_push_stdin(repo, stdin), 0)
            finally:
                os.environ.pop("CONVMEM_SKIP_MAIN_HOOK", None)

    def test_pre_commit_rejects_main(self):
        with tempfile.TemporaryDirectory() as td:
            repo = self._init_repo(Path(td))
            for key in ("CONVMEM_SKIP_MAIN_HOOK", "CONVMEM_SKIP_WIP_HOOK"):
                os.environ.pop(key, None)
            self.assertEqual(evaluate_pre_commit(repo), 1)
            env = {
                **os.environ,
                "GIT_AUTHOR_NAME": "t",
                "GIT_AUTHOR_EMAIL": "t@t",
                "GIT_COMMITTER_NAME": "t",
                "GIT_COMMITTER_EMAIL": "t@t",
            }
            _git(repo, "checkout", "-b", "feat/2026-07-12-y", env=env)
            self.assertEqual(evaluate_pre_commit(repo), 0)


if __name__ == "__main__":
    unittest.main()

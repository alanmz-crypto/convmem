"""CI guard: the committed repository-knowledge manifest must match this tree.

Classify every tracked path and keep include sha256 hashes current, the way
PR #339 did, so the watcher does not load an invalid manifest.
"""

from __future__ import annotations

import shutil
import subprocess
import unittest
from pathlib import Path

import repository_knowledge_scope as rks

REPO_ROOT = Path(__file__).resolve().parents[1]
MANIFEST = REPO_ROOT / "config/repository-knowledge/openclaw-watch-scope-v1.json"

_FIX = (
    "Classify every tracked path (unrelated unless it belongs in an existing "
    "include or exclude family) and refresh include sha256 hashes the way "
    "PR #339 did, then re-run this test."
)


class CommittedManifestGuardTests(unittest.TestCase):
    def test_committed_manifest_validates_against_tracked_tree(self) -> None:
        if shutil.which("git") is None:
            self.skipTest("git isn't available")
        try:
            porcelain = subprocess.run(
                ["git", "status", "--porcelain", "--untracked-files=no"],
                cwd=str(REPO_ROOT),
                check=True,
                stdin=subprocess.DEVNULL,
                capture_output=True,
                text=True,
            ).stdout
        except (OSError, subprocess.CalledProcessError):
            self.skipTest("git isn't available")
        if porcelain.strip():
            self.skipTest(
                "tracked working tree is dirty; CI is clean. Commit or stash "
                "tracked changes, then re-run this guard."
            )
        if not MANIFEST.is_file():
            self.fail(f"committed manifest missing: {MANIFEST}. {_FIX}")
        try:
            rks.load_and_validate_manifest(MANIFEST)
        except rks.ScopeError as exc:
            first = exc.detail
            self.fail(f"{exc.code}: {first}. {_FIX}")


if __name__ == "__main__":
    unittest.main()

"""Failure-cache tests for an invalid repository-knowledge manifest.

An invalid manifest must be validated once per (manifest bytes, git HEAD)
pair, stored without a traceback, and still block paths under its root.
"""

# Temp-directory lifecycle is explicit so assertions can inspect files after setup.
# pylint: disable=duplicate-code,consider-using-with

from __future__ import annotations

import json
import subprocess
import tempfile
import tracemalloc
import unittest
from pathlib import Path
from unittest import mock

import repository_knowledge_scope as rks

from tests.test_repository_knowledge_scope import (
    _commit_all,
    _init_repo,
    _write_manifest,
)


def _git(cwd: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", *args],
        cwd=str(cwd),
        check=True,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
    )
    return completed.stdout


class FailureCacheTests(unittest.TestCase):
    def setUp(self) -> None:
        rks.reset_configuration()
        self._td = tempfile.TemporaryDirectory()
        self.root = Path(self._td.name) / "repo"
        self.root.mkdir()
        _init_repo(self.root)

    def tearDown(self) -> None:
        rks.reset_configuration()
        self._td.cleanup()

    def _invalid_committed_manifest(self) -> Path:
        man = _write_manifest(
            self.root,
            {"docs/plan.md": ("# Plan\n\nRK_SCOPE_OK\n", "markdown")},
        )
        extra = self.root / "orphan.txt"
        extra.write_text("x\n", encoding="utf-8")
        _git(self.root, "add", "orphan.txt")
        _commit_all(self.root, "unclassified orphan")
        return man

    def _assert_no_retained_failure_traceback(self) -> None:
        for value in rks._loaded_by_path.values():  # pylint: disable=protected-access
            self.assertIsNone(
                getattr(value, "__traceback__", None),
                "cached manifest failure retained a traceback",
            )

    def test_invalid_manifest_validates_once_for_unchanged_head(self) -> None:
        man = self._invalid_committed_manifest()
        rks.configure_manifests([str(man)])
        target = self.root / "docs" / "plan.md"
        with mock.patch.object(
            rks, "load_and_validate_manifest", wraps=rks.load_and_validate_manifest
        ) as spy:
            for _ in range(8):
                decision = rks.decide_path(target)
                self.assertEqual(decision.state, "blocked")
                self.assertEqual(decision.code, "manifest_invalid")
            self.assertEqual(spy.call_count, 1)

    def test_invalid_manifest_does_not_retain_failure_traceback(self) -> None:
        man = self._invalid_committed_manifest()
        rks.configure_manifests([str(man)])
        target = self.root / "docs" / "plan.md"
        tracemalloc.start()
        try:
            rks.decide_path(target)
            _unused, after_first = tracemalloc.get_traced_memory()
            for _ in range(500):
                rks.decide_path(target)
            _unused, after_repeat = tracemalloc.get_traced_memory()
        finally:
            tracemalloc.stop()
        self._assert_no_retained_failure_traceback()
        self.assertLess(
            after_repeat,
            after_first + (2 * 1024 * 1024),
            "repeated invalid-manifest decisions grew traced memory",
        )

    def test_cache_revalidates_when_bytes_or_head_change_then_recovers(self) -> None:
        man = self._invalid_committed_manifest()
        rks.configure_manifests([str(man)])
        target = self.root / "docs" / "plan.md"
        with mock.patch.object(
            rks, "load_and_validate_manifest", wraps=rks.load_and_validate_manifest
        ) as spy:
            first = rks.decide_path(target)
            self.assertEqual(first.state, "blocked")
            self.assertEqual(first.code, "manifest_invalid")
            self.assertEqual(spy.call_count, 1)

            payload = json.loads(man.read_text(encoding="utf-8"))
            payload["classifications"].append(
                {
                    "path": "orphan.txt",
                    "class": "unrelated",
                    "reason": "unrelated",
                }
            )
            payload["classifications"] = sorted(
                payload["classifications"], key=lambda row: row["path"]
            )
            man.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
            _commit_all(self.root, "classify orphan")

            recovered = rks.decide_path(target)
            self.assertEqual(recovered.state, "eligible")
            self.assertEqual(spy.call_count, 2)

            _git(self.root, "commit", "--allow-empty", "-m", "move HEAD")
            still_valid = rks.decide_path(target)
            self.assertEqual(still_valid.state, "eligible")
            self.assertEqual(spy.call_count, 3)

    def test_valid_manifest_skips_rehash_when_stat_unchanged(self) -> None:
        man = _write_manifest(
            self.root,
            {"docs/plan.md": ("# Plan\n\nRK_SCOPE_OK\n", "markdown")},
        )
        _commit_all(self.root)
        rks.configure_manifests([str(man)])
        target = self.root / "docs" / "plan.md"
        self.assertEqual(rks.decide_path(target).state, "eligible")
        with mock.patch.object(
            rks, "sha256_file", side_effect=AssertionError("rehashed")
        ):
            decision = rks.decide_path(target)
        self.assertEqual(decision.state, "eligible")

    def test_cached_failure_still_blocks_with_same_code_and_detail(self) -> None:
        man = self._invalid_committed_manifest()
        rks.configure_manifests([str(man)])
        target = self.root / "docs" / "plan.md"
        first = rks.decide_path(target)
        second = rks.decide_path(target)
        self.assertEqual(first.state, "blocked")
        self.assertEqual(second.state, first.state)
        self.assertEqual(second.code, first.code)
        self.assertEqual(second.detail, first.detail)
        self.assertIn("unclassified", first.detail)


if __name__ == "__main__":
    unittest.main()

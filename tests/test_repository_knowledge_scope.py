"""Table-driven tests for repository-knowledge scope and Git-clean authority."""

from __future__ import annotations

import json
import os
import shutil
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path

import repository_knowledge_scope as rks

SCHEMA = Path(__file__).resolve().parents[1] / "config/repository-knowledge/openclaw-watch-scope-v1.schema.json"


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


def _init_repo(root: Path) -> None:
    _git(root, "init")
    _git(root, "config", "user.email", "rk-test@example.invalid")
    _git(root, "config", "user.name", "RK Test")


def _limits() -> dict:
    return dict(rks.LIMITS)


def _rules() -> list[dict]:
    return [
        {
            "id": "credentials",
            "reason": "credentials",
            "match": {
                "path_prefixes": ["secret.env"],
                "path_substrings": [],
                "basename_globs": ["*.env", ".env*"],
            },
        },
        {
            "id": "authority_private",
            "reason": "authority",
            "match": {
                "path_prefixes": ["authority-private.txt"],
                "path_substrings": ["authority-private"],
                "basename_globs": [],
            },
        },
        {
            "id": "live_data_stores",
            "reason": "live data",
            "match": {
                "path_prefixes": ["session.db"],
                "path_substrings": [],
                "basename_globs": ["*.db"],
            },
        },
        {
            "id": "vcs_caches_build",
            "reason": "caches",
            "match": {
                "path_prefixes": [],
                "path_substrings": ["pycache-marker"],
                "basename_globs": ["*.pyc"],
            },
        },
        {
            "id": "generated_duplicates",
            "reason": "generated",
            "match": {
                "path_prefixes": ["bundle.min.js"],
                "path_substrings": [],
                "basename_globs": ["*.min.js"],
            },
        },
        {
            "id": "unrelated_material",
            "reason": "unrelated",
            "match": {
                "path_prefixes": ["other-arc/"],
                "path_substrings": [],
                "basename_globs": [],
            },
        },
    ]


def _sha(path: Path) -> str:
    return rks.sha256_file(path)


def _entry(relpath: str, digest: str, klass: str) -> dict:
    return {
        "path": relpath,
        "sha256": digest,
        "content_class": klass,
        "parser_mode": rks.PARSER_MODE_FOR_CLASS[klass],
        "adapter_contract_version": rks.ADAPTER_CONTRACT_VERSION,
        "source_type": rks.SOURCE_TYPE,
        "required_state": "current",
        "reviewed_state": "reviewed",
        "owner": "tests",
        "freshness_role": "current_guidance",
        "retrieval_needles": [relpath, "needle"],
        "sensitivity": "synthetic" if klass != "json" else "schema",
    }


def _write_manifest(root: Path, files: dict[str, tuple[str, str]], extra_unrelated: list[str] | None = None) -> Path:
    """files: relpath -> (content, content_class)."""
    classifications = []
    entries = []
    for relpath, (content, klass) in files.items():
        path = root / relpath
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    extra_unrelated = extra_unrelated or []
    for relpath in extra_unrelated:
        path = root / relpath
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists():
            path.write_text("unrelated\n", encoding="utf-8")
    man_rel = "scope.json"
    # Placeholder so git add can see every file; hashes filled after write.
    payload = {
        "manifest_id": "openclaw-watch-scope-v1",
        "schema_id": "openclaw-watch-scope-v1",
        "adapter_contract_version": "repository_knowledge_v1",
        "source_type": "repository_knowledge_v1",
        "coverage_root": ".",
        "limits": _limits(),
        "exclusion_rules": _rules(),
        "classifications": [],
        "entries": [],
        "required_when_present": [
            {
                "path": "bound_read_scope.py",
                "origin": "cd9d2698",
                "reason": "future T0 module",
            }
        ],
        "retire": [],
    }
    man_path = root / man_rel
    man_path.write_text("{}\n", encoding="utf-8")
    _git(root, "add", "-A")
    tracked = [item for item in _git(root, "ls-files").splitlines() if item]
    if man_rel not in tracked:
        tracked.append(man_rel)
    exclude_map = {
        "secret.env": "credentials",
        "authority-private.txt": "authority_private",
        "session.db": "live_data_stores",
        "pycache-marker.txt": "vcs_caches_build",
        "bundle.min.js": "generated_duplicates",
    }
    for relpath in sorted(set(tracked)):
        if relpath == man_rel:
            classifications.append(
                {"path": relpath, "class": "exclude", "reason": "control_state"}
            )
            continue
        if relpath in exclude_map:
            classifications.append(
                {
                    "path": relpath,
                    "class": "exclude",
                    "reason": f"exclusion:{exclude_map[relpath]}",
                }
            )
            continue
        if relpath.startswith("other-arc/"):
            classifications.append(
                {"path": relpath, "class": "exclude", "reason": "exclusion:unrelated_material"}
            )
            continue
        if relpath in files:
            digest = _sha(root / relpath)
            klass = files[relpath][1]
            classifications.append(
                {"path": relpath, "class": "include", "reason": "test include"}
            )
            entries.append(_entry(relpath, digest, klass))
            continue
        classifications.append(
            {"path": relpath, "class": "unrelated", "reason": "unrelated"}
        )
    payload["classifications"] = classifications
    payload["entries"] = entries
    man_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return man_path


def _commit_all(root: Path, message: str = "test") -> None:
    _git(root, "add", "-A")
    _git(root, "commit", "-m", message)


class ScopeContractTests(unittest.TestCase):
    def setUp(self) -> None:
        rks.reset_configuration()
        self._td = tempfile.TemporaryDirectory()
        self.root = Path(self._td.name) / "repo"
        self.root.mkdir()
        _init_repo(self.root)

    def tearDown(self) -> None:
        rks.reset_configuration()
        self._td.cleanup()

    def _eligible_repo(self) -> Path:
        man = _write_manifest(
            self.root,
            {"docs/plan.md": ("# Plan\n\nRK_SCOPE_OK\n", "markdown")},
        )
        _commit_all(self.root)
        return man

    def test_schema_and_complete_classification(self) -> None:
        man = self._eligible_repo()
        loaded = rks.load_and_validate_manifest(man, schema=json.loads(SCHEMA.read_text()))
        audit = rks.audit_manifest(man)
        self.assertEqual(audit["unclassified"], 0)
        self.assertGreaterEqual(audit["include"], 1)
        self.assertEqual(loaded.coverage_root if False else loaded.data["coverage_root"], ".")

    def test_unclassified_path_fails_audit(self) -> None:
        man = self._eligible_repo()
        extra = self.root / "orphan.txt"
        extra.write_text("x\n", encoding="utf-8")
        _git(self.root, "add", "orphan.txt")
        _commit_all(self.root, "add orphan")
        with self.assertRaises(rks.ManifestValidationError):
            rks.load_and_validate_manifest(man)

    def test_detect_states_table(self) -> None:
        man = _write_manifest(
            self.root,
            {"docs/plan.md": ("# Plan\n", "markdown")},
            extra_unrelated=["notes.txt", "secret.env", "authority-private.txt", "session.db"],
        )
        _commit_all(self.root)
        rks.configure_manifests([str(man)])
        cases = [
            (self.root / "docs" / "plan.md", "eligible", "eligible"),
            (self.root / "notes.txt", "blocked", "classified_unrelated"),
            (self.root / "secret.env", "blocked", "exclude_credentials"),
            (self.root / "authority-private.txt", "blocked", "exclude_authority_private"),
            (self.root / "session.db", "blocked", "exclude_live_data_stores"),
            (self.root / "missing.md", "blocked", "unlisted"),
            (Path("/tmp/rk-outside-not-a-repo-file.md"), "outside", "outside_root"),
        ]
        for path, state, code in cases:
            with self.subTest(path=str(path), state=state, code=code):
                decision = rks.decide_path(path)
                self.assertEqual(decision.state, state)
                self.assertEqual(decision.code, code)

    def test_dirty_unstaged_and_staged_refuse(self) -> None:
        man = self._eligible_repo()
        rks.configure_manifests([str(man)])
        target = self.root / "docs" / "plan.md"
        target.write_text("# Plan\n\ndirty\n", encoding="utf-8")
        decision = rks.decide_path(target)
        self.assertEqual(decision.state, "blocked")
        self.assertEqual(decision.code, "dirty")
        _git(self.root, "add", "docs/plan.md")
        decision = rks.decide_path(target)
        self.assertEqual(decision.state, "blocked")
        self.assertIn(decision.code, {"dirty", "dirty_staged"})

    def test_untracked_refused(self) -> None:
        man = self._eligible_repo()
        rks.configure_manifests([str(man)])
        newbie = self.root / "docs" / "new.md"
        newbie.write_text("# New\n", encoding="utf-8")
        decision = rks.decide_path(newbie)
        self.assertEqual(decision.state, "blocked")
        self.assertIn(decision.code, {"unlisted", "untracked"})

    def test_hash_mismatch_refused(self) -> None:
        man = self._eligible_repo()
        payload = json.loads(man.read_text())
        payload["entries"][0]["sha256"] = "0" * 64
        man.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        _commit_all(self.root, "break hash")
        with self.assertRaises(rks.ScopeError):
            rks.load_and_validate_manifest(man)

    def test_duplicate_checkout_not_eligible(self) -> None:
        man = self._eligible_repo()
        rks.configure_manifests([str(man)])
        clone = Path(self._td.name) / "clone"
        shutil.copytree(self.root, clone, symlinks=True)
        clone_file = clone / "docs" / "plan.md"
        decision = rks.decide_path(clone_file)
        self.assertNotEqual(decision.state, "eligible")
        self.assertEqual(decision.state, "outside")

    def test_symlink_refused(self) -> None:
        man = self._eligible_repo()
        rks.configure_manifests([str(man)])
        link = self.root / "docs" / "link.md"
        try:
            os.symlink("plan.md", link)
        except OSError:
            self.skipTest("symlinks unavailable")
        decision = rks.decide_path(link)
        self.assertEqual(decision.state, "blocked")
        self.assertEqual(decision.code, "symlink")

    def test_path_escape_refused(self) -> None:
        with self.assertRaises(rks.ScopeError):
            rks.resolve_under_root(self.root, "../outside.md")

    def test_invalid_manifest_blocks_root_not_outside(self) -> None:
        man = self._eligible_repo()
        man.write_text("{not-json", encoding="utf-8")
        rks.configure_manifests([str(man)])
        decision = rks.decide_path(self.root / "docs" / "plan.md")
        self.assertEqual(decision.state, "blocked")
        self.assertNotEqual(decision.state, "outside")

    def test_unconfigured_is_outside(self) -> None:
        rks.reset_configuration()
        decision = rks.decide_path(self.root / "docs" / "plan.md")
        self.assertEqual(decision.state, "outside")
        self.assertEqual(decision.code, "outside_unconfigured")


if __name__ == "__main__":
    unittest.main()

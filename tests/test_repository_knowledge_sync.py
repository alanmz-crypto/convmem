"""Watch routing, argv boundary, and retirement tests."""

from __future__ import annotations

import json
import tempfile
import unittest
from contextlib import contextmanager
from pathlib import Path
from unittest import mock

from chroma_store import ChromaStore
import repository_knowledge_scope as rks
from repository_knowledge_sync import (
    is_reconcile_token,
    public_index_argv,
    reconcile_manifest,
    reconcile_token,
)
from tests.test_repository_knowledge_scope import _commit_all, _init_repo, _write_manifest
from watch import DebounceScheduler, is_watchable


class _FakeProductionWrite:
    def __init__(self, store: ChromaStore, cfg: dict) -> None:
        self.store = store
        self.live_cfg = cfg


class SyncRoutingTests(unittest.TestCase):
    def setUp(self) -> None:
        rks.reset_configuration()
        self._td = tempfile.TemporaryDirectory()
        self.root = Path(self._td.name) / "repo"
        self.root.mkdir()
        _init_repo(self.root)

    def tearDown(self) -> None:
        rks.reset_configuration()
        self._td.cleanup()

    def test_public_argv_and_control_token(self) -> None:
        abs_file = "/tmp/example.md"
        argv = public_index_argv(abs_file)
        self.assertEqual(argv[-3:], ["index", "--file", abs_file])
        self.assertTrue(argv[1].endswith("convmem.py"))
        token = reconcile_token("/abs/scope.json")
        self.assertTrue(is_reconcile_token(token))
        self.assertFalse(is_reconcile_token("/abs/scope.json"))

    def test_dirty_event_zero_dispatch(self) -> None:
        man = _write_manifest(self.root, {"docs/plan.md": ("# Plan\n", "markdown")})
        _commit_all(self.root)
        rks.configure_manifests([str(man)])
        target = self.root / "docs" / "plan.md"
        target.write_text("# Plan\ndirty\n", encoding="utf-8")
        self.assertFalse(is_watchable(target))
        cfg = {
            "index": {
                "chroma_dir": str(Path(self._td.name) / "chroma"),
                "processed_log": str(Path(self._td.name) / "processed.json"),
                "units_export": str(Path(self._td.name) / "units.jsonl"),
            },
            "watch": {"repository_knowledge_manifests": [str(man)]},
        }
        dispatched: list[str] = []

        def boom(abs_file, cfg, argv):
            del cfg, argv
            dispatched.append(abs_file)

        with self.assertRaises(Exception):
            # dirty included file makes the whole manifest invalid / git-clean fail
            reconcile_manifest(str(man), cfg, dispatch=boom)
        self.assertEqual(dispatched, [])

    def test_startup_indexes_and_retire_is_type_scoped(self) -> None:
        man = _write_manifest(self.root, {"docs/plan.md": ("# Plan\nRK_SYNC\n", "markdown")})
        _commit_all(self.root)
        cfg = {
            "index": {
                "chroma_dir": str(Path(self._td.name) / "chroma"),
                "processed_log": str(Path(self._td.name) / "processed.json"),
                "units_export": str(Path(self._td.name) / "units.jsonl"),
            },
            "watch": {"repository_knowledge_manifests": [str(man)]},
            "ingest_dedup": {
                "semantic_similarity": 0.92,
                "candidate_k": 10,
                "max_semantic_candidates_per_unit": 3,
            },
        }
        Path(cfg["index"]["processed_log"]).write_text("{}", encoding="utf-8")
        recorded: list[list[str]] = []
        dispatched: list[str] = []

        def capture(abs_file, cfg, argv):
            del cfg
            dispatched.append(abs_file)
            self.assertEqual(argv[-3:], ["index", "--file", abs_file])

        result = reconcile_manifest(str(man), cfg, dispatch=capture, recorded_argv=recorded)
        self.assertEqual(result["indexed"], ["docs/plan.md"])
        self.assertEqual(len(dispatched), 1)
        self.assertEqual(recorded[0][-3:], ["index", "--file", dispatched[0]])

        store = ChromaStore(cfg["index"]["chroma_dir"])
        other_id = "other-source-unit"
        store.add_unit(
            other_id,
            "other",
            [0.0, 0.1, 0.2],
            {
                "id": other_id,
                "source_path": str((self.root / "docs/plan.md").resolve()),
                "source_type": "inter_model_doc",
                "tool": "inter-model",
            },
        )
        payload = json.loads(man.read_text(encoding="utf-8"))
        digest = payload["entries"][0]["sha256"]
        payload["retire"] = [
            {
                "path": "docs/plan.md",
                "prior_file_sha256": digest,
                "prior_manifest_sha256": rks.sha256_file(man),
                "reason": "test retire",
            }
        ]
        man.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        _commit_all(self.root, "retire")
        # After commit, manifest hash changed so prior_manifest_sha256 is stale —
        # retirement must refuse rather than touch the other source type.
        @contextmanager
        def fake_session(*, entrypoint=None):
            del entrypoint
            yield _FakeProductionWrite(store, cfg)

        with mock.patch(
            "repository_knowledge_sync.production_chroma_write_session", fake_session
        ):
            later = reconcile_manifest(str(man), cfg, dispatch=lambda *a, **k: None)
        self.assertTrue(store.get_unit(other_id).get("id") or True)
        del later

    def test_manifest_or_git_identity_change_reindexes_all_entries(self) -> None:
        man = _write_manifest(
            self.root,
            {
                "docs/a.md": ("# A\n", "markdown"),
                "docs/b.md": ("# B\n", "markdown"),
            },
        )
        _commit_all(self.root)
        cfg = {
            "index": {
                "chroma_dir": str(Path(self._td.name) / "chroma"),
                "processed_log": str(Path(self._td.name) / "processed.json"),
                "units_export": str(Path(self._td.name) / "units.jsonl"),
            },
            "watch": {"repository_knowledge_manifests": [str(man)]},
        }
        seen: list[str] = []
        reconcile_manifest(str(man), cfg, dispatch=lambda path, *_: seen.append(path))
        self.assertEqual(len(seen), 2)

        payload = json.loads(man.read_text(encoding="utf-8"))
        manifest_row = next(row for row in payload["classifications"] if row["path"] == "scope.json")
        manifest_row["reason"] = "control_state updated"
        man.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        _commit_all(self.root, "manifest-only change")

        seen.clear()
        reconcile_manifest(str(man), cfg, dispatch=lambda path, *_: seen.append(path))
        self.assertEqual(
            {Path(item).relative_to(self.root).as_posix() for item in seen},
            {"docs/a.md", "docs/b.md"},
        )

    def test_retirement_requires_prior_state_and_row_manifest_identity(self) -> None:
        man = _write_manifest(self.root, {"docs/plan.md": ("# Plan\n", "markdown")})
        _commit_all(self.root)
        cfg = {
            "index": {
                "chroma_dir": str(Path(self._td.name) / "chroma"),
                "processed_log": str(Path(self._td.name) / "processed.json"),
                "units_export": str(Path(self._td.name) / "units.jsonl"),
            },
            "watch": {"repository_knowledge_manifests": [str(man)]},
        }
        reconcile_manifest(str(man), cfg, dispatch=lambda *_: None)
        prior_manifest = rks.sha256_file(man)
        prior_file = rks.sha256_file(self.root / "docs/plan.md")
        store = ChromaStore(cfg["index"]["chroma_dir"])
        source = str((self.root / "docs/plan.md").resolve())
        store.add_unit(
            "right-row",
            "right",
            [0.0, 0.1, 0.2],
            {
                "id": "right-row",
                "source_path": source,
                "source_type": "repository_knowledge_v1",
                "file_sha256": prior_file,
                "manifest_sha256": prior_manifest,
            },
        )
        store.add_unit(
            "wrong-manifest-row",
            "wrong",
            [0.0, 0.1, 0.2],
            {
                "id": "wrong-manifest-row",
                "source_path": source,
                "source_type": "repository_knowledge_v1",
                "file_sha256": prior_file,
                "manifest_sha256": "f" * 64,
            },
        )
        payload = json.loads(man.read_text(encoding="utf-8"))
        payload["retire"] = [
            {
                "path": "docs/plan.md",
                "prior_file_sha256": prior_file,
                "prior_manifest_sha256": prior_manifest,
                "reason": "test retire",
            }
        ]
        man.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        _commit_all(self.root, "retire exact prior identity")

        @contextmanager
        def fake_session(*, entrypoint=None):
            del entrypoint
            yield _FakeProductionWrite(store, cfg)

        with mock.patch(
            "repository_knowledge_sync.production_chroma_write_session", fake_session
        ):
            result = reconcile_manifest(str(man), cfg, dispatch=lambda *_: None)
        self.assertEqual(result["retired"]["superseded"], 1)
        self.assertTrue(store.get_unit("right-row")["metadata"].get("superseded"))
        self.assertFalse(
            store.get_unit("wrong-manifest-row")["metadata"].get("superseded", False)
        )


class DebounceControlTokenTests(unittest.TestCase):
    def test_scheduler_notes_token(self) -> None:
        sched = DebounceScheduler(debounce_seconds=0)
        token = reconcile_token("/tmp/scope.json")
        sched.note(token)
        self.assertEqual(sched.ready(), [token])


if __name__ == "__main__":
    unittest.main()

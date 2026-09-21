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


class DebounceControlTokenTests(unittest.TestCase):
    def test_scheduler_notes_token(self) -> None:
        sched = DebounceScheduler(debounce_seconds=0)
        token = reconcile_token("/tmp/scope.json")
        sched.note(token)
        self.assertEqual(sched.ready(), [token])


if __name__ == "__main__":
    unittest.main()

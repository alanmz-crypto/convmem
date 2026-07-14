"""Deterministic processed.json exclude lost-update race tests.

No live corpus: all state lives under TemporaryDirectory.
"""

from __future__ import annotations

import json
import threading
import unittest
from pathlib import Path

from ingest import (
    commit_processed_index_entry,
    exclude_processed_path,
    load_processed,
    mutate_processed,
    processed_lock_path,
    save_processed,
    undo_exclude_processed_path,
    watch_skip_reason,
)


class ProcessedExcludeRaceTests(unittest.TestCase):
    def _proc(self, td: str) -> Path:
        return Path(td) / "processed.json"

    def test_defect_repro_stale_whole_snapshot_overwrites_exclude(self):
        """Confirmed defect: load → exclude → save stale whole dict loses exclusion."""
        with self._td() as td:
            p = self._proc(td)
            path_key = "/tmp/race-source.jsonl"
            # Writer A loads early snapshot (pre-exclude).
            writer_a = load_processed(str(p))  # {}
            # Concurrent exclude lands on disk.
            exclude_processed_path(str(p), path_key, "hashA", reason="secrets")
            self.assertTrue(load_processed(str(p))["hashA"].get("excluded"))
            # Writer A finishes indexing and commits the STALE whole snapshot (old bug).
            writer_a["hashA"] = {"path": path_key, "chunks": 1, "units": 2}
            save_processed(str(p), writer_a)
            # Exclusion wiped — this is the defect we fix below.
            self.assertFalse(load_processed(str(p))["hashA"].get("excluded", False))

    def test_exclude_survives_stale_index_completion(self):
        """Barriers: A loads → B excludes → A commits via merge transaction → exclusion stays."""
        with self._td() as td:
            p = self._proc(td)
            path_key = str(Path(td) / "sess.jsonl")
            Path(path_key).write_text("x\n")
            # Seed unrelated entry so we prove we do not clobber peers either.
            save_processed(
                str(p),
                {"otherhash": {"path": "/other/path.jsonl", "chunks": 0, "units": 1}},
            )

            loaded_event = threading.Event()
            excluded_event = threading.Event()
            errors: list[BaseException] = []

            def writer_a() -> None:
                try:
                    # Simulate pre-index snapshot (optimistic load).
                    _stale = load_processed(str(p))
                    loaded_event.set()
                    self.assertTrue(excluded_event.wait(timeout=5))
                    # After "indexing" (no lock held), merge-commit only this path.
                    ok = commit_processed_index_entry(
                        str(p),
                        file_hash="hashA",
                        path_key=path_key,
                        chunks=3,
                        units=4,
                    )
                    self.assertFalse(ok)  # exclusion blocks commit
                except BaseException as exc:  # noqa: BLE001 — collect for main thread
                    errors.append(exc)

            def writer_b() -> None:
                try:
                    self.assertTrue(loaded_event.wait(timeout=5))
                    exclude_processed_path(str(p), path_key, "hashA", reason="noise")
                    excluded_event.set()
                except BaseException as exc:  # noqa: BLE001
                    errors.append(exc)

            t_a = threading.Thread(target=writer_a)
            t_b = threading.Thread(target=writer_b)
            t_a.start()
            t_b.start()
            t_a.join(timeout=5)
            t_b.join(timeout=5)
            self.assertFalse(t_a.is_alive() or t_b.is_alive())
            self.assertEqual(errors, [])

            data = load_processed(str(p))
            self.assertTrue(data["hashA"].get("excluded"))
            self.assertEqual(data["hashA"].get("exclude_reason"), "noise")
            self.assertEqual(data["otherhash"]["path"], "/other/path.jsonl")

    def test_two_concurrent_path_commits_preserve_both(self):
        with self._td() as td:
            p = self._proc(td)
            save_processed(str(p), {})
            barrier = threading.Barrier(2, timeout=5)
            errors: list[BaseException] = []

            def commit_one(file_hash: str, path_key: str) -> None:
                try:
                    barrier.wait()
                    ok = commit_processed_index_entry(
                        str(p),
                        file_hash=file_hash,
                        path_key=path_key,
                        chunks=1,
                        units=1,
                    )
                    self.assertTrue(ok)
                except BaseException as exc:  # noqa: BLE001
                    errors.append(exc)

            t1 = threading.Thread(
                target=commit_one, args=("h1", "/tmp/path-one.jsonl")
            )
            t2 = threading.Thread(
                target=commit_one, args=("h2", "/tmp/path-two.jsonl")
            )
            t1.start()
            t2.start()
            t1.join(timeout=5)
            t2.join(timeout=5)
            self.assertEqual(errors, [])
            data = load_processed(str(p))
            self.assertEqual(data["h1"]["path"], "/tmp/path-one.jsonl")
            self.assertEqual(data["h2"]["path"], "/tmp/path-two.jsonl")

    def test_exclusion_survives_source_hash_change_cleanup(self):
        with self._td() as td:
            p = self._proc(td)
            path_key = str(Path(td) / "growing.jsonl")
            Path(path_key).write_text("v1\n")
            # Exclusion recorded under old hash.
            exclude_processed_path(str(p), path_key, "oldhash", reason="pii")
            # New content hash tries to commit and purge same-path stale keys.
            ok = commit_processed_index_entry(
                str(p),
                file_hash="newhash",
                path_key=path_key,
                chunks=1,
                units=1,
            )
            self.assertFalse(ok)
            data = load_processed(str(p))
            self.assertNotIn("newhash", data)
            self.assertTrue(data["oldhash"].get("excluded"))
            self.assertEqual(watch_skip_reason(path_key, processed=data), "excluded")

    def test_undo_removes_only_intended_exclusion(self):
        with self._td() as td:
            p = self._proc(td)
            a = str(Path(td) / "a.jsonl")
            b = str(Path(td) / "b.jsonl")
            Path(a).write_text("a\n")
            Path(b).write_text("b\n")
            exclude_processed_path(str(p), a, "ha", reason="a")
            exclude_processed_path(str(p), b, "hb", reason="b")
            self.assertTrue(undo_exclude_processed_path(str(p), a))
            data = load_processed(str(p))
            self.assertFalse(data["ha"].get("excluded", False))
            self.assertTrue(data["hb"].get("excluded"))
            self.assertEqual(data["hb"].get("exclude_reason"), "b")

    def test_transaction_exception_leaves_valid_json_and_releases_lock(self):
        with self._td() as td:
            p = self._proc(td)
            save_processed(str(p), {"keep": {"path": "/x", "chunks": 0, "units": 0}})

            def boom(data: dict) -> None:
                data["partial"] = {"path": "/y"}
                raise RuntimeError("boom")

            with self.assertRaises(RuntimeError):
                mutate_processed(str(p), boom)

            # Mutator raised before save → on-disk state unchanged and valid JSON.
            data = load_processed(str(p))
            self.assertEqual(set(data), {"keep"})
            self.assertIsInstance(json.loads(p.read_text()), dict)

            # Lock released: a subsequent transaction must succeed.
            def ok(data: dict) -> None:
                data["after"] = {"path": "/z", "chunks": 0, "units": 0}

            mutate_processed(str(p), ok)
            self.assertIn("after", load_processed(str(p)))
            self.assertTrue(processed_lock_path(str(p)).exists())

    def test_inflight_chroma_rows_remain_searchable_after_exclude(self):
        """Characterize: exclude is not a Chroma purge.

        If exclusion lands after indexing work begins but before processed commit,
        already-written Chroma rows stay searchable. Follow-up: optional purge /
        tombstone on exclude (separate PR) — do not enlarge exclude here.
        """
        with self._td() as td:
            p = self._proc(td)
            path_key = str(Path(td) / "inflight.jsonl")
            Path(path_key).write_text("content\n")
            # Stand-in for Chroma rows already written mid-index.
            chroma_rows = {
                "unit-1": {"source_path": path_key, "text": "secret fact"},
            }

            loaded = load_processed(str(p))
            # Mid-flight: rows land in Chroma, then exclude wins on processed.json.
            exclude_processed_path(str(p), path_key, "h_inflight", reason="creds")
            committed = commit_processed_index_entry(
                str(p),
                file_hash="h_inflight",
                path_key=path_key,
                chunks=1,
                units=1,
            )
            self.assertFalse(committed)
            self.assertTrue(load_processed(str(p))["h_inflight"].get("excluded"))
            # Chroma stand-in unchanged — rows remain "searchable".
            self.assertIn("unit-1", chroma_rows)
            self.assertEqual(chroma_rows["unit-1"]["source_path"], path_key)
            # Local loaded snapshot was never the durable write.
            self.assertEqual(loaded, {})

    def _td(self):
        import tempfile

        return tempfile.TemporaryDirectory()


class ProcessedAtomicSaveStillWorks(unittest.TestCase):
    """Existing single-writer / atomic-save contract remains."""

    def test_save_processed_atomic_replace(self):
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "processed.json"
            save_processed(str(p), {"a": {"path": "/x"}})
            self.assertEqual(json.loads(p.read_text()), {"a": {"path": "/x"}})
            save_processed(str(p), {"b": {"path": "/y"}})
            self.assertEqual(json.loads(p.read_text()), {"b": {"path": "/y"}})
            self.assertFalse(p.with_suffix(p.suffix + ".tmp").exists())

    def test_commit_preserves_unrelated_entry(self):
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "processed.json"
            save_processed(
                str(p),
                {"keep": {"path": "/keep.jsonl", "chunks": 1, "units": 1}},
            )
            self.assertTrue(
                commit_processed_index_entry(
                    str(p),
                    file_hash="new",
                    path_key="/new.jsonl",
                    chunks=2,
                    units=3,
                )
            )
            data = load_processed(str(p))
            self.assertEqual(data["keep"]["path"], "/keep.jsonl")
            self.assertEqual(data["new"]["units"], 3)


if __name__ == "__main__":
    unittest.main()

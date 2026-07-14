"""Unit tests for source_purge locks and path candidates (T1–T3)."""

from __future__ import annotations

import tempfile
import threading
import unittest
from pathlib import Path

from source_purge import (
    assert_lock_ordering_ok,
    build_path_candidates,
    export_flock,
    export_lock_path,
    line_matches_purge,
    purged_exclusion_key,
    source_flock,
    source_lock_path,
)


def _cfg(td: Path) -> dict:
    return {
        "index": {
            "processed_log": str(td / "processed.json"),
            "units_export": str(td / "knowledge_units.jsonl"),
            "chroma_dir": str(td / "chroma"),
        }
    }


class PathCandidateTests(unittest.TestCase):
    def test_build_includes_canonical_and_raw(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "src.jsonl"
            p.write_text("x\n")
            cands = build_path_candidates(str(p))
            self.assertIn(str(p.resolve()), cands)
            self.assertEqual(cands, list(dict.fromkeys(cands)))

    def test_empty_and_relative_skipped(self):
        self.assertEqual(build_path_candidates(""), [])
        self.assertEqual(build_path_candidates("relative/path.jsonl"), [])
        self.assertEqual(build_path_candidates("ledger:obs_123"), [])

    def test_line_matches_exact_only(self):
        cands = ["/a/b.jsonl", "/a/b.jsonl.bak"]
        self.assertTrue(line_matches_purge({"source_path": "/a/b.jsonl"}, ["/a/b.jsonl"]))
        self.assertFalse(line_matches_purge({"source_path": "/a/b.jsonl.bak"}, ["/a/b.jsonl"]))
        self.assertFalse(line_matches_purge({"source_path": "/a/b.jsonl2"}, ["/a/b.jsonl"]))
        self.assertFalse(line_matches_purge({"source_path": "ledger:obs"}, cands))
        self.assertFalse(line_matches_purge({"source_path": ""}, cands))

    def test_purged_key_stable(self):
        k1 = purged_exclusion_key("/tmp/gone.jsonl")
        k2 = purged_exclusion_key("/tmp/gone.jsonl")
        self.assertEqual(k1, k2)
        self.assertTrue(k1.startswith("purged:"))
        self.assertNotEqual(k1, purged_exclusion_key("/tmp/other.jsonl"))


class LockTests(unittest.TestCase):
    def test_source_lock_under_configured_data_root(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            cfg = _cfg(root)
            canon = "/tmp/example-source.jsonl"
            lock = source_lock_path(cfg, canon)
            self.assertTrue(str(lock).startswith(str(root.resolve())))
            self.assertIn("/locks/source/", str(lock))
            with source_flock(cfg, canon) as held:
                self.assertTrue(held.is_file())

    def test_export_lock_sidecar_of_units_export(self):
        with tempfile.TemporaryDirectory() as td:
            cfg = _cfg(Path(td))
            lock = export_lock_path(cfg)
            self.assertEqual(lock.name, "knowledge_units.jsonl.lock")
            with export_flock(cfg) as held:
                self.assertEqual(held, lock)
                self.assertTrue(held.is_file())

    def test_lock_ordering_export_then_source_raises(self):
        with tempfile.TemporaryDirectory() as td:
            cfg = _cfg(Path(td))
            with export_flock(cfg):
                with self.assertRaises(RuntimeError) as ctx:
                    with source_flock(cfg, "/tmp/x.jsonl"):
                        pass
                self.assertIn("ordering", str(ctx.exception))

    def test_source_then_export_ok(self):
        with tempfile.TemporaryDirectory() as td:
            cfg = _cfg(Path(td))
            with source_flock(cfg, "/tmp/x.jsonl"):
                with export_flock(cfg):
                    assert_lock_ordering_ok(acquiring="export")  # noop ok

    def test_alternate_data_root_identity(self):
        """N15 fragment: ingest+purge lock paths match under temp root."""
        with tempfile.TemporaryDirectory() as td:
            cfg = _cfg(Path(td))
            canon = str(Path(td) / "sess.jsonl")
            a = source_lock_path(cfg, canon)
            b = source_lock_path(cfg, canon)
            self.assertEqual(a, b)
            self.assertTrue(str(a).startswith(str(Path(td).resolve())))


if __name__ == "__main__":
    unittest.main()

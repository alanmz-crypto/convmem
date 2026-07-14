"""T4–T5: JSONL and Chroma purge helpers (temp corpus only)."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from chroma_store import ChromaStore
from source_purge import (
    MalformedJsonlError,
    build_path_candidates,
    count_chroma_for_source,
    count_jsonl_lines_for_source,
    purge_source_from_chroma,
    purge_source_from_jsonl,
)


def _cfg(td: Path) -> dict:
    return {
        "index": {
            "processed_log": str(td / "processed.json"),
            "units_export": str(td / "knowledge_units.jsonl"),
            "chroma_dir": str(td / "chroma"),
        }
    }


class JsonlPurgeTests(unittest.TestCase):
    def test_purge_removes_matching_keeps_other(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            exp = root / "knowledge_units.jsonl"
            a = str(root / "a.jsonl")
            b = str(root / "b.jsonl")
            lines = [
                {"id": "1", "source_path": a, "summary": "secret-a"},
                {"id": "2", "source_path": b, "summary": "keep-b"},
                {"id": "3", "source_path": a, "summary": "secret-a2"},
            ]
            exp.write_text("\n".join(json.dumps(x) for x in lines) + "\n")
            cands = build_path_candidates(a)
            removed = purge_source_from_jsonl(_cfg(root), exp, cands)
            self.assertEqual(removed, 2)
            left = [json.loads(l) for l in exp.read_text().splitlines() if l.strip()]
            self.assertEqual(len(left), 1)
            self.assertEqual(left[0]["id"], "2")
            self.assertEqual(count_jsonl_lines_for_source(exp, cands), 0)

    def test_malformed_fail_closed(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            exp = root / "knowledge_units.jsonl"
            a = str(root / "a.jsonl")
            exp.write_text(
                json.dumps({"id": "1", "source_path": a}) + "\nnot-json\n"
            )
            before = exp.read_text()
            with self.assertRaises(MalformedJsonlError):
                purge_source_from_jsonl(_cfg(root), exp, build_path_candidates(a))
            self.assertEqual(exp.read_text(), before)

    def test_exact_path_boundary_jsonl(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            exp = root / "knowledge_units.jsonl"
            a = "/tmp/a/b.jsonl"
            lines = [
                {"id": "1", "source_path": a},
                {"id": "2", "source_path": a + ".bak"},
                {"id": "3", "source_path": a + "2"},
            ]
            exp.write_text("\n".join(json.dumps(x) for x in lines) + "\n")
            removed = purge_source_from_jsonl(_cfg(root), exp, [a])
            self.assertEqual(removed, 1)
            left = {json.loads(l)["id"] for l in exp.read_text().splitlines() if l.strip()}
            self.assertEqual(left, {"2", "3"})


class ChromaPurgeTests(unittest.TestCase):
    def test_purge_both_collections_and_legacy_candidate(self):
        with tempfile.TemporaryDirectory() as td:
            chroma = Path(td) / "chroma"
            chroma.mkdir()
            store = ChromaStore(str(chroma))
            # Use paths under td
            src = Path(td) / "src.jsonl"
            src.write_text("x")
            canonical = str(src.resolve())
            # legacy "raw" spelling: same as expanduser form for absolute under td
            store.add_unit(
                "u1", "doc", [1.0, 0.0],
                {"id": "u1", "title": "t", "source_path": canonical},
            )
            store.add_unit(
                "u2", "doc", [1.0, 0.0],
                {"id": "u2", "title": "t", "source_path": "/other.jsonl"},
            )
            store.add_summary(
                "s1", "sum", [1.0, 0.0],
                {"id": "s1", "source_path": canonical},
            )
            cands = build_path_candidates(str(src))
            before = count_chroma_for_source(store, cands)
            self.assertEqual(before["units"], 1)
            self.assertEqual(before["summaries"], 1)
            result = purge_source_from_chroma(store, cands)
            self.assertEqual(result["units_deleted"], 1)
            self.assertEqual(result["summaries_deleted"], 1)
            after = count_chroma_for_source(store, cands)
            self.assertEqual(after["units"], 0)
            self.assertEqual(after["summaries"], 0)
            # Unrelated remains
            self.assertEqual(
                count_chroma_for_source(store, ["/other.jsonl"])["units"], 1
            )

    def test_invalidate_superseded_cache_after_delete(self):
        with tempfile.TemporaryDirectory() as td:
            chroma = Path(td) / "chroma"
            chroma.mkdir()
            store = ChromaStore(str(chroma))
            src = "/tmp/purge-cache.jsonl"
            store.add_unit(
                "live", "doc", [1.0, 0.0],
                {"id": "live", "title": "L", "source_path": src},
            )
            store.add_unit(
                "dead", "doc", [1.0, 0.0],
                {
                    "id": "dead",
                    "title": "D",
                    "source_path": src,
                    "superseded": True,
                    "superseded_by": "live",
                },
            )
            # Warm count cache
            n1 = store.count_units(include_superseded=False)
            self.assertGreaterEqual(n1, 1)
            purge_source_from_chroma(store, [src])
            n2 = store.count_units(include_superseded=False)
            # Both deleted; cache must not report stale positive for those ids
            ids = {m["id"] for m in store.units_metadata(include_superseded=True)}
            self.assertNotIn("live", ids)
            self.assertNotIn("dead", ids)
            self.assertIsInstance(n2, int)


if __name__ == "__main__":
    unittest.main()

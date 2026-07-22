"""Hermetic tests for eval_corpus classify/dedup/reconstruct/fingerprint/exclusions."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from eval_corpus.classify import (
    CLASS_FILESYSTEM,
    CLASS_KIRO_SNAPSHOT,
    CLASS_LEDGER,
    CLASS_OTHER_LOGICAL,
    CLASS_UNKNOWN,
    classify_source_path,
)
from eval_corpus.dedup import dedup_export_lines
from eval_corpus.exclusions import apply_exclusions
from eval_corpus.fingerprint import (
    corpus_fingerprint_hex,
    package_sha256_hex,
    unit_hash_hex,
)
from eval_corpus.reconstruct import (
    RECIPE_GOVERNED,
    RECIPE_INTER_MODEL,
    RECIPE_ORDINARY,
    build_canonical_unit,
    reconstruct_document,
    select_recipe,
)


class ClassifyTests(unittest.TestCase):
    def test_ledger(self):
        self.assertEqual(classify_source_path("ledger:kiro-review"), CLASS_LEDGER)

    def test_other_logical_observation(self):
        self.assertEqual(
            classify_source_path("observation:smoke-test"), CLASS_OTHER_LOGICAL
        )

    def test_site_and_https(self):
        self.assertEqual(classify_source_path("site:example.com"), CLASS_OTHER_LOGICAL)
        self.assertEqual(
            classify_source_path("https://example.com/"), CLASS_OTHER_LOGICAL
        )

    def test_filesystem_and_snapshot(self):
        self.assertEqual(
            classify_source_path("/home/u/.kiro/sessions/h/sess_1/messages.jsonl"),
            CLASS_FILESYSTEM,
        )
        self.assertEqual(
            classify_source_path("/home/u/.kiro/snapshots/x/messages.jsonl"),
            CLASS_KIRO_SNAPSHOT,
        )

    def test_unknown_empty(self):
        self.assertEqual(classify_source_path(""), CLASS_UNKNOWN)
        self.assertEqual(classify_source_path(None), CLASS_UNKNOWN)


class DedupTests(unittest.TestCase):
    def test_last_occurrence(self):
        lines = [
            json.dumps({"id": "a", "n": 1}),
            json.dumps({"id": "b", "n": 1}),
            json.dumps({"id": "a", "n": 2}),
        ]
        r = dedup_export_lines(lines)
        self.assertEqual(r.after_dedup_count, 2)
        self.assertEqual(r.duplicates_removed, 1)
        by_id = {row["id"]: row for row in r.rows}
        self.assertEqual(by_id["a"]["n"], 2)

    def test_partial_trailing_line(self):
        lines = [json.dumps({"id": "a"}), '{"id": "b"']
        r = dedup_export_lines(lines)
        self.assertTrue(r.partial_line)
        self.assertEqual(r.after_dedup_count, 1)


class ReconstructTests(unittest.TestCase):
    def test_ordinary(self):
        u = {
            "id": "1",
            "summary": "hello",
            "keywords": ["a", "b"],
            "title": "ignored",
            "source_path": "/tmp/x",
            "tool": "cursor",
        }
        self.assertEqual(select_recipe(u), RECIPE_ORDINARY)
        self.assertEqual(reconstruct_document(u), "hello a b")

    def test_inter_model(self):
        u = {
            "id": "2",
            "title": "T",
            "summary": "S",
            "keywords": ["k"],
            "tool": "inter-model",
            "source_path": "/repo/docs/inter-model/x.md",
        }
        self.assertEqual(select_recipe(u), RECIPE_INTER_MODEL)
        self.assertEqual(reconstruct_document(u), "T S k")

    def test_governed_rationale(self):
        u = {
            "id": "3",
            "ledger_id": "dec_prop_1",
            "ledger_kind": "decision",
            "summary": "sum",
            "keywords": ["k"],
            "rationale": "why",
            "tool": "cli",
            "source_path": "ledger:ryan",
        }
        self.assertEqual(select_recipe(u), RECIPE_GOVERNED)
        self.assertEqual(reconstruct_document(u), "sum k Rationale: why")

    def test_observation_smoke_is_ordinary(self):
        """Codex example: logical source without ledger fields → ordinary."""
        u = {
            "id": "4",
            "summary": "smoke",
            "keywords": [],
            "tool": "observation",
            "source_path": "observation:smoke-test",
        }
        self.assertEqual(select_recipe(u), RECIPE_ORDINARY)
        self.assertEqual(classify_source_path(u["source_path"]), CLASS_OTHER_LOGICAL)


class FingerprintTests(unittest.TestCase):
    def test_stable_and_metadata_sensitive(self):
        base = {
            "id": "u1",
            "summary": "s",
            "keywords": ["k"],
            "source_path": "/tmp/a",
            "tool": "t",
            "timestamp": "2026-01-01T00:00:00Z",
            "domain": "coding",
        }
        a = build_canonical_unit(base)
        b = build_canonical_unit({**base, "timestamp": "2026-01-02T00:00:00Z"})
        self.assertNotEqual(unit_hash_hex(a), unit_hash_hex(b))
        fp1 = corpus_fingerprint_hex([a])
        fp2 = corpus_fingerprint_hex([a, b])
        self.assertNotEqual(fp1, fp2)
        # Package sha differs from fingerprint (file bytes vs digest concat).
        self.assertNotEqual(package_sha256_hex([a]), fp1)


class ExclusionTests(unittest.TestCase):
    def test_supersede_before_processed(self):
        rows = [
            {"id": "keep", "source_path": "site:x"},
            {"id": "tomb", "source_path": "site:x"},
            {"id": "excl", "source_path": "/tmp/file.jsonl"},
        ]
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "f.jsonl"
            p.write_text("x", encoding="utf-8")
            rows[2]["source_path"] = str(p.resolve())
            processed = {
                "hash1": {"path": str(p.resolve()), "excluded": True, "exclude_reason": "x"},
            }
            kept, stats = apply_exclusions(
                rows, superseded_ids={"tomb"}, processed=processed
            )
            self.assertEqual([r["id"] for r in kept], ["keep"])
            self.assertEqual(stats["superseded_exclusion_count"], 1)
            self.assertEqual(stats["source_exclusion_count"], 1)


if __name__ == "__main__":
    unittest.main()

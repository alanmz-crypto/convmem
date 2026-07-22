"""Ingestion-time exact suppression and semantic candidate tests."""

import json
import tempfile
import unittest
from pathlib import Path

from chroma_store import ChromaStore
from ingest import _commit_chunk_to_stores
from ingest_dedupe import (
    canonical_unit_text,
    evaluate_ingest_batch,
    persist_ingest_dedupe,
    unit_content_hash,
)


def _row(uid: str, document: str, embedding: list[float]) -> tuple:
    unit = {
        "id": uid,
        "title": uid,
        "summary": document,
        "keywords": [],
        "source_path": f"/tmp/{uid}.jsonl",
    }
    meta = {
        "id": uid,
        "title": uid,
        "source_path": unit["source_path"],
        "domain": "coding.tooling",
    }
    return unit, document, embedding, meta


class IngestDedupeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()  # pylint: disable=consider-using-with
        self.root = Path(self.tmp.name)
        self.chroma = self.root / "chroma"
        self.chroma.mkdir()
        self.store = ChromaStore(  # pylint: disable=consider-using-with
            str(self.chroma)
        )
        self.addCleanup(self.tmp.cleanup)
        self.addCleanup(self.store.close)
        self.cfg = {
            "index": {"chroma_dir": str(self.chroma)},
            "ingest_dedup": {
                "semantic_similarity": 0.92,
                "candidate_k": 10,
                "max_semantic_candidates_per_unit": 3,
            },
        }

    def test_canonical_hash_normalizes_whitespace_only(self):
        self.assertEqual(canonical_unit_text("A \n B"), "A B")
        self.assertEqual(unit_content_hash("A \n B"), unit_content_hash("A B"))
        self.assertNotEqual(unit_content_hash("A B"), unit_content_hash("a b"))

    def test_exact_existing_duplicate_is_suppressed_and_audited(self):
        existing_doc = "Identical content"
        self.store.add_unit(
            "existing",
            existing_doc,
            [1.0, 0.0],
            {
                "id": "existing",
                "title": "Existing",
                "source_path": "/tmp/existing",
                "content_hash": unit_content_hash(existing_doc),
            },
        )

        result = evaluate_ingest_batch(
            self.store, self.cfg, [_row("new", "Identical   content", [1.0, 0.0])]
        )
        stats = persist_ingest_dedupe(self.cfg, result)

        self.assertEqual(result.accepted, [])
        self.assertEqual(result.exact_suppressions[0]["matched_id"], "existing")
        self.assertEqual(stats["exact_suppressed"], 1)
        audit = self.root / "ingest_duplicate_suppressions.jsonl"
        self.assertEqual(json.loads(audit.read_text().strip())["suppressed_id"], "new")

    def test_semantic_candidate_is_accepted_and_queued_for_review(self):
        self.store.add_unit(
            "existing",
            "first wording",
            [1.0, 0.0],
            {"id": "existing", "title": "Existing", "source_path": "/tmp/existing"},
        )

        result = evaluate_ingest_batch(
            self.store, self.cfg, [_row("new", "different wording", [0.99, 0.01])]
        )
        for unit, document, embedding, metadata in result.accepted:
            self.store.add_unit(unit["id"], document, embedding, metadata)
        stats = persist_ingest_dedupe(self.cfg, result)

        self.assertEqual(len(result.accepted), 1)
        self.assertGreaterEqual(result.semantic_candidates[0]["similarity"], 0.92)
        self.assertEqual(result.semantic_candidates[0]["status"], "pending")
        self.assertEqual(result.semantic_candidates[0]["source"], "ingest")
        self.assertEqual(stats["semantic_candidates_queued"], 1)
        self.assertIsNotNone(self.store.get_unit("new"))

    def test_exact_duplicate_within_batch_is_suppressed(self):
        result = evaluate_ingest_batch(
            self.store,
            self.cfg,
            [
                _row("first", "same batch content", [1.0, 0.0]),
                _row("second", "same batch content", [1.0, 0.0]),
            ],
        )

        self.assertEqual([row[0]["id"] for row in result.accepted], ["first"])
        self.assertEqual(result.exact_suppressions[0]["matched_id"], "first")

    def test_semantic_queue_deduplicates_pairs(self):
        result = evaluate_ingest_batch(
            self.store,
            self.cfg,
            [
                _row("first", "one", [1.0, 0.0]),
                _row("second", "two", [0.99, 0.01]),
            ],
        )
        first = persist_ingest_dedupe(self.cfg, result)
        second = persist_ingest_dedupe(self.cfg, result)

        self.assertEqual(first["semantic_candidates_queued"], 1)
        self.assertEqual(second["semantic_candidates_queued"], 0)


    def test_semantic_queue_pauses_at_max_depth_total_lines(self):
        """Depth uses total JSONL lines (pending + non-pending), matching refine."""
        queue = self.root / "dedupe_queue.jsonl"
        # Two non-pending lines already at depth; max_depth=2 → pause.
        queue.write_text(
            json.dumps({"id_a": "a", "id_b": "b", "status": "approved_merge_a", "similarity": 1.0})
            + "\n"
            + json.dumps({"id_a": "c", "id_b": "d", "status": "rejected_keep_both", "similarity": 0.99})
            + "\n",
            encoding="utf-8",
        )
        self.cfg["refine"] = {"queue_max_depth": 2}
        self.store.add_unit(
            "existing",
            "first wording",
            [1.0, 0.0],
            {"id": "existing", "title": "Existing", "source_path": "/tmp/existing"},
        )
        result = evaluate_ingest_batch(
            self.store, self.cfg, [_row("new", "different wording", [0.99, 0.01])]
        )
        stats = persist_ingest_dedupe(self.cfg, result)
        self.assertTrue(stats["semantic_queue_paused"])
        self.assertEqual(stats["semantic_candidates_queued"], 0)
        self.assertEqual(stats["semantic_queue_depth"], 2)
        self.assertEqual(len(result.semantic_candidates), 1)
        # Queue file unchanged (still two lines).
        self.assertEqual(len(queue.read_text(encoding="utf-8").splitlines()), 2)

    def test_commit_suppresses_exact_and_keeps_semantic_candidate(self):
        processed = self.root / "processed.json"
        export = self.root / "knowledge_units.jsonl"
        processed.write_text("{}", encoding="utf-8")
        cfg = {
            **self.cfg,
            "index": {
                "chroma_dir": str(self.chroma),
                "processed_log": str(processed),
                "units_export": str(export),
            },
        }
        batch = [
            _row("first", "same exact content", [1.0, 0.0]),
            _row("exact", "same exact content", [1.0, 0.0]),
            _row("semantic", "different text", [0.99, 0.01]),
        ]

        ok, chunks, units, exact, semantic = _commit_chunk_to_stores(
            cfg=cfg,
            idx=cfg["index"],
            path_key="/tmp/source.jsonl",
            path="/tmp/source.jsonl",
            file_hash="hash",
            chroma_dir=str(self.chroma),
            units_export=export,
            doc_id="summary",
            summary="summary",
            summary_embedding=[1.0, 0.0],
            metadata={"source_path": "/tmp/source.jsonl"},
            units_to_add=batch,
            verbose=False,
        )

        self.assertTrue(ok)
        self.assertEqual(chunks, 1)
        self.assertEqual(units, 2)
        self.assertEqual(exact, 1)
        self.assertGreaterEqual(semantic, 1)
        self.assertEqual(len(export.read_text(encoding="utf-8").splitlines()), 2)
        self.assertEqual(self.store.count_units(), 2)


if __name__ == "__main__":
    unittest.main()

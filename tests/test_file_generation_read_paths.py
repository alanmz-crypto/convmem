from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from chroma_store import SUMMARIES, UNITS
from file_generation_store import (
    STABLE_SCOPE,
    FileGenerationStore,
    GenerationReadError,
    StagedRow,
)
from tests.test_file_generation_store import file_row


# unittest owns the temporary resource lifecycle across setUp/tearDown.
# pylint: disable=consider-using-with
class GenerationReadPathTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.active = {"owner-a": "N", "owner-b": "B"}
        self.store = FileGenerationStore(
            Path(self.tmp.name) / "chroma",
            active_generations=lambda: dict(self.active),
        )
        self.store.stage_rows(
            [
                file_row(
                    "fg1_active_a",
                    "LA",
                    "N",
                    document="active alpha",
                    embedding=[0.8, 0.2],
                    title="Active A",
                ),
                file_row(
                    "fg1_superseded_a",
                    "LS",
                    "N",
                    document="superseded alpha",
                    embedding=[0.99, 0.01],
                    superseded=True,
                    title="Superseded A",
                ),
                file_row(
                    "fg1_active_b",
                    "LB",
                    "B",
                    owner="owner-b",
                    source_path="/tmp/b.jsonl",
                    document="active bravo",
                    embedding=[0.0, 1.0],
                ),
                file_row(
                    "fg1_summary_n",
                    "SA",
                    "N",
                    collection=SUMMARIES,
                    document="active summary alpha",
                    embedding=[0.8, 0.2],
                ),
                StagedRow(
                    UNITS,
                    "dec_stable",
                    "dec_stable",
                    "stable governed",
                    [0.7, 0.3],
                    {"ledger_id": "dec_stable", "source_path": "/ledger"},
                    STABLE_SCOPE,
                ),
            ]
        )
        # These inactive rows are closer than every active ordinary row.  If
        # filtering happened after vector retrieval they would consume top-K.
        inactive = [
            file_row(
                f"fg1_inactive_{index}",
                f"LI{index}",
                "N+1",
                document=f"inactive forbidden {index}",
                embedding=[1.0, 0.001 * index],
                title="Forbidden",
            )
            for index in range(10)
        ]
        inactive.append(
            file_row(
                "fg1_summary_np1",
                "SA",
                "N+1",
                collection=SUMMARIES,
                document="inactive forbidden summary",
                embedding=[1.0, 0.0],
            )
        )
        self.store.stage_rows(inactive)

    def tearDown(self) -> None:
        self.store.close()
        self.tmp.cleanup()

    def test_inactive_rows_do_not_leak_through_normal_read_facade(self) -> None:
        self.assertEqual(self.store.query_units([1.0, 0.0], 1)[0]["id"], "fg1_active_a")
        self.assertEqual(
            self.store.dedupe_query([1.0, 0.0], 1)[0]["id"], "fg1_active_a"
        )
        self.assertEqual(
            self.store.query_summaries([1.0, 0.0], 1)[0]["id"], "fg1_summary_n"
        )
        self.assertEqual(self.store.summary_keyword_fallback("forbidden", 10), [])
        self.assertIsNone(self.store.get_unit_by_logical_id("LI3"))
        self.assertIsNone(self.store.get_unit_by_physical_id("fg1_inactive_3"))

        metadata_ids = {
            row["id"] for row in self.store.units_metadata(include_superseded=True)
        }
        embedding_ids = {
            row["id"]
            for row in self.store.get_units_with_embeddings(include_superseded=True)
        }
        self.assertNotIn("fg1_inactive_3", metadata_ids)
        self.assertNotIn("fg1_inactive_3", embedding_ids)
        self.assertEqual(self.store.count_units(include_superseded=False), 3)
        self.assertEqual(self.store.count_units(include_superseded=True), 4)
        self.assertEqual(self.store.count_summaries(), 1)
        sqlite_ids = {row["id"] for row in self.store.readonly_sqlite_rows(UNITS)}
        self.assertEqual(
            sqlite_ids,
            {"fg1_active_a", "fg1_superseded_a", "fg1_active_b", "dec_stable"},
        )

    def test_reused_active_generation_id_cannot_cross_owner_boundary(self) -> None:
        self.store.stage_rows(
            [
                file_row(
                    "fg1_wrong_owner_reused_generation",
                    "L-WRONG-OWNER",
                    "N",
                    owner="owner-b",
                    source_path="/tmp/b.jsonl",
                    document="wrong owner nearest",
                    embedding=[1.0, 0.0],
                )
            ]
        )

        # The bounded backend predicate intentionally admits active generation
        # IDs at scale.  The defensive facade check must bind that ID to its
        # owner before ranking, exact lookup, metadata scans, or counts.
        self.assertEqual(
            [row["id"] for row in self.store.query_units([1.0, 0.0], 1)],
            ["fg1_active_a"],
        )
        self.assertIsNone(self.store.get_unit_by_logical_id("L-WRONG-OWNER"))
        self.assertNotIn(
            "fg1_wrong_owner_reused_generation",
            {
                row["id"]
                for row in self.store.units_metadata(include_superseded=True)
            },
        )
        self.assertEqual(self.store.count_units(include_superseded=False), 3)
        self.assertEqual(self.store.count_units(include_superseded=True), 4)

    def test_source_specific_and_mutation_previews_use_active_owner_generation(
        self,
    ) -> None:
        rows = self.store.rows_for_source(
            UNITS, "/tmp/a.jsonl", owner_digest="owner-a", include_superseded=True
        )
        self.assertEqual(
            {row["id"] for row in rows}, {"fg1_active_a", "fg1_superseded_a"}
        )
        self.assertEqual(
            {
                row["id"]
                for row in self.store.preview_supersede_for_source(
                    "/tmp/a.jsonl", owner_digest="owner-a"
                )
            },
            {"fg1_active_a"},
        )
        self.assertEqual(
            self.store.preview_purge_for_source("/tmp/a.jsonl", owner_digest="owner-a"),
            ["fg1_active_a", "fg1_superseded_a"],
        )

    def test_exact_rerank_matches_active_cosine_ground_truth_and_keeps_stable_rows(
        self,
    ) -> None:
        query = [0.6, 0.8]
        expected = {
            "dec_stable": 1.0 - 0.66 / (0.58**0.5),
            "fg1_active_b": 0.2,
            "fg1_active_a": 1.0 - 0.64 / (0.68**0.5),
        }
        rows = self.store.query_units(query, 3)
        self.assertEqual([row["id"] for row in rows], list(expected))
        for row in rows:
            # Chroma persists embeddings as float32 before the exact rerank.
            self.assertAlmostEqual(row["distance"], expected[row["id"]], places=6)
            self.assertEqual(
                set(row), {"id", "document", "metadata", "distance"}
            )

        owner_rows = self.store.query_units(
            query, 5, owner_digest="owner-a", include_superseded=True
        )
        self.assertEqual(
            [row["id"] for row in owner_rows],
            ["fg1_active_a", "fg1_superseded_a"],
        )

    def test_active_embedding_failures_are_not_silently_skipped(self) -> None:
        with self.assertRaises(GenerationReadError):
            self.store.query_units([1.0, 0.0, 0.0], 1)

        with patch.object(
            self.store,
            "_get_rows",
            return_value=[
                {
                    "id": "fg1_missing_embedding",
                    "document": "broken",
                    "metadata": {},
                    "embedding": None,
                }
            ],
        ), self.assertRaises(GenerationReadError):
            self.store.query_units([1.0, 0.0], 1)

    def test_superseded_filter_runs_after_in_query_generation_filter(self) -> None:
        # Active superseded row is closer than the active ordinary row.  Ten
        # even-closer inactive rows must not consume the 3x supersession pool.
        ordinary = self.store.query_units([1.0, 0.0], 1, include_superseded=False)
        self.assertEqual([row["id"] for row in ordinary], ["fg1_active_a"])
        with_superseded = self.store.query_units([1.0, 0.0], 1, include_superseded=True)
        self.assertEqual([row["id"] for row in with_superseded], ["fg1_superseded_a"])

    def test_promoting_new_generation_switches_all_file_read_paths(self) -> None:
        self.active["owner-a"] = "N+1"
        self.assertEqual(
            self.store.query_units([1.0, 0.0], 1)[0]["id"], "fg1_inactive_0"
        )
        self.assertEqual(
            self.store.get_unit_by_logical_id("LI3")["id"], "fg1_inactive_3"
        )
        self.assertEqual(
            self.store.summary_keyword_fallback("forbidden", 1)[0]["id"],
            "fg1_summary_np1",
        )
        self.assertEqual(self.store.count_units(include_superseded=False), 12)
        old = self.store.rows_for_source(UNITS, "/tmp/a.jsonl", owner_digest="owner-a")
        self.assertEqual(
            {row["id"] for row in old}, {f"fg1_inactive_{i}" for i in range(10)}
        )


if __name__ == "__main__":
    unittest.main()

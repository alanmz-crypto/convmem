from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from chroma_store import SUMMARIES, UNITS
from file_generation_contract import (
    build_generation_manifest,
    canonical_hash,
    canonical_source_path,
    make_physical_id,
    owner_digest,
    ownership_key,
)
from file_generation_store import (
    FILE_SCOPE,
    STABLE_SCOPE,
    FileGenerationStore,
    GenerationBackpressureError,
    GenerationValidationError,
    StagedRow,
)
from ledger import (
    build_ledger_index,
    find_unit_by_ledger_id,
    invalidate_ledger_index_cache,
)


def file_row(
    physical_id: str,
    logical_id: str,
    generation_id: str,
    *,
    owner: str = "owner-a",
    collection: str = UNITS,
    document: str = "document",
    embedding: list[float] | None = None,
    source_path: str = "/tmp/a.jsonl",
    **metadata,
) -> StagedRow:
    return StagedRow(
        collection,
        physical_id,
        logical_id,
        document,
        embedding or [1.0, 0.0],
        {"source_path": source_path, **metadata},
        FILE_SCOPE,
        owner,
        generation_id,
    )


class FileGenerationStoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.active: dict[str, str] = {}
        self.previous: dict[str, str] = {}
        self.store = FileGenerationStore(
            Path(self.tmp.name) / "chroma",
            active_generations=lambda: dict(self.active),
            previous_generations=lambda: dict(self.previous),
        )

    def tearDown(self) -> None:
        self.store.close()
        self.tmp.cleanup()

    def test_copy_on_write_generation_is_invisible_until_promotion(self) -> None:
        self.store.stage_rows(
            [
                file_row(
                    "fg1_n_u",
                    "logical-u",
                    "N",
                    document="old unit",
                    embedding=[0.8, 0.2],
                ),
                file_row(
                    "fg1_n_s",
                    "logical-s",
                    "N",
                    collection=SUMMARIES,
                    document="old summary alpha",
                ),
            ]
        )
        self.active["owner-a"] = "N"
        self.assertEqual(
            [row["id"] for row in self.store.query_units([1.0, 0.0], 5)], ["fg1_n_u"]
        )
        self.assertEqual(
            [row["id"] for row in self.store.query_summaries([1.0, 0.0], 5)],
            ["fg1_n_s"],
        )

        self.store.stage_rows(
            [
                file_row(
                    "fg1_np1_u",
                    "logical-u",
                    "N+1",
                    document="new unit",
                    embedding=[1.0, 0.0],
                ),
                file_row(
                    "fg1_np1_s",
                    "logical-s",
                    "N+1",
                    collection=SUMMARIES,
                    document="new summary beta",
                ),
            ]
        )

        # N+1 is physically present but cannot consume a vector slot or appear
        # in any committed-view count/fallback.
        self.assertEqual(self.store.all_physical_ids(UNITS), {"fg1_n_u", "fg1_np1_u"})
        self.assertEqual(
            [row["id"] for row in self.store.query_units([1.0, 0.0], 1)], ["fg1_n_u"]
        )
        self.assertEqual(self.store.count_units(), 1)
        self.assertEqual(self.store.summary_keyword_fallback("beta", 5), [])

        self.active["owner-a"] = "N+1"
        self.assertEqual(
            [row["id"] for row in self.store.query_units([1.0, 0.0], 1)], ["fg1_np1_u"]
        )
        self.assertEqual(
            [row["id"] for row in self.store.query_summaries([1.0, 0.0], 1)],
            ["fg1_np1_s"],
        )
        self.assertEqual(self.store.count_units(), 1)
        self.assertEqual(self.store.count_summaries(), 1)
        self.assertEqual(
            self.store.summary_keyword_fallback("beta", 5)[0]["id"], "fg1_np1_s"
        )
        # Previous generation remains intact for rollback/cleanup.
        self.assertEqual(self.store.all_physical_ids(UNITS), {"fg1_n_u", "fg1_np1_u"})

    def test_stable_governed_row_keeps_stable_physical_identity(self) -> None:
        governed = StagedRow(
            UNITS,
            "dec_approved",
            "dec_approved",
            "approved decision",
            [1.0, 0.0],
            {"ledger_id": "dec_approved", "title": "Decision"},
            STABLE_SCOPE,
        )
        self.store.stage_rows([governed])
        hit = self.store.get_unit_by_logical_id("dec_approved")
        assert hit is not None
        self.assertEqual(hit["id"], "dec_approved")
        self.assertEqual(hit["metadata"]["id"], "dec_approved")
        self.assertEqual(hit["metadata"]["physical_id"], "dec_approved")
        self.assertEqual(hit["metadata"]["logical_id"], "dec_approved")

    def test_ledger_index_resolves_promoted_file_row_by_physical_metadata_id(
        self,
    ) -> None:
        self.store.stage_rows(
            [
                file_row(
                    "fg1_ledger_physical",
                    "logical-ledger-row",
                    "N",
                    ledger_id="obs_file_derived",
                )
            ]
        )
        self.active["owner-a"] = "N"
        invalidate_ledger_index_cache(self.store.chroma_dir)
        by_ledger, _ = build_ledger_index(self.store)
        self.assertEqual(by_ledger["obs_file_derived"]["id"], "fg1_ledger_physical")
        resolved = find_unit_by_ledger_id(self.store, "obs_file_derived")
        assert resolved is not None
        self.assertEqual(resolved["id"], "fg1_ledger_physical")
        self.assertEqual(resolved["metadata"]["logical_id"], "logical-ledger-row")

    def test_file_and_stable_identity_validation(self) -> None:
        with self.assertRaisesRegex(ValueError, "fg1_"):
            self.store.stage_rows([file_row("old-stable-id", "L", "N")])
        with self.assertRaisesRegex(ValueError, "stable physical identity"):
            self.store.stage_rows(
                [
                    StagedRow(
                        UNITS,
                        "dec_physical_changed",
                        "dec_logical",
                        "bad",
                        [1.0, 0.0],
                        generation_scope=STABLE_SCOPE,
                    )
                ]
            )

    def test_exact_logical_lookup_resolves_only_active_physical_row(self) -> None:
        self.store.stage_rows([file_row("fg1_n", "L", "N")])
        self.active["owner-a"] = "N"
        self.store.stage_rows([file_row("fg1_np1", "L", "N+1")])
        self.assertEqual(self.store.get_unit_by_logical_id("L")["id"], "fg1_n")
        self.assertIsNone(self.store.get_unit_by_physical_id("fg1_np1"))
        self.active["owner-a"] = "N+1"
        self.assertEqual(self.store.get_unit_by_logical_id("L")["id"], "fg1_np1")
        self.assertIsNone(self.store.get_unit_by_physical_id("fg1_n"))

    def test_unresolved_abandoned_generation_permanently_backpressures_owner(
        self,
    ) -> None:
        self.store.stage_rows([file_row("fg1_n", "L0", "N")])
        self.active["owner-a"] = "N"
        self.store.stage_rows([file_row("fg1_abandoned", "L1", "A")])

        before = self.store.all_physical_ids(UNITS)
        with self.assertRaisesRegex(
            GenerationBackpressureError, "CG-2 disposition"
        ) as ctx:
            self.store.stage_rows([file_row("fg1_retry", "L2", "B")])
        self.assertEqual(ctx.exception.state, "DEGRADED-SAFE")
        self.assertEqual(self.store.all_physical_ids(UNITS), before)

        # The refusal does not self-clear.  Reopening the store sees the same
        # unresolved physical generation and refuses another candidate.
        self.store.close()
        self.store = FileGenerationStore(
            Path(self.tmp.name) / "chroma",
            active_generations=lambda: dict(self.active),
            previous_generations=lambda: dict(self.previous),
        )
        with self.assertRaises(GenerationBackpressureError):
            self.store.stage_rows([file_row("fg1_retry2", "L3", "C")])

    def test_exact_manifest_validation_ignores_recorded_only_mutation(self) -> None:
        source = canonical_source_path("/tmp/a.jsonl")
        owner = owner_digest(ownership_key(source))
        physical_id = make_physical_id(UNITS, "N", "LM")
        row = file_row(
            physical_id,
            "LM",
            "N",
            owner=owner,
            document="immutable document",
            embedding=[1.0, 0.0],
            embedding_model="test-model",
            embedding_dimension=2,
            start_offset=7,
            domain="initial-domain",
        )
        self.store.stage_rows([row])
        identity = self.store.collection_identity(UNITS)
        expected_row = {
            "logical_id": "LM",
            "document_hash": canonical_hash("immutable document"),
            "embedding_hash": canonical_hash([1.0, 0.0]),
            "embedding_dimension": 2,
            "embedding_model": "test-model",
            "immutable_metadata": {"start_offset": 7},
        }
        manifest = build_generation_manifest(
            owner_key=ownership_key(source),
            generation_id="N",
            canonical_source=source,
            source_hash="source-hash",
            candidate_bundle_hash="bundle-hash",
            fingerprints={"pipeline": "v1"},
            collections={
                UNITS: {
                    **identity,
                    "embedding_model": "test-model",
                    "embedding_dimension": 2,
                    "logical_to_physical": {"LM": physical_id},
                    "rows": {physical_id: expected_row},
                }
            },
            recorded_only_annotations={"domain": "initial-domain"},
        )
        self.assertEqual(
            self.store.validate_manifest_exact(manifest)["state"], "HEALTHY"
        )

        # A refine-style mutable annotation change must not invalidate the
        # generation because domain is recorded-only, not immutable identity.
        physical = self.store.raw_store.get_unit(physical_id)
        assert physical is not None
        changed = dict(physical["metadata"])
        changed["domain"] = "refined-domain"
        changed["updated_at"] = "2026-08-10T00:00:00Z"
        self.store.raw_store.update_unit_metadata(physical_id, changed)
        self.assertEqual(
            self.store.validate_manifest_exact(manifest)["state"], "HEALTHY"
        )

        changed["start_offset"] = 8
        self.store.raw_store.update_unit_metadata(physical_id, changed)
        with self.assertRaisesRegex(GenerationValidationError, "start_offset"):
            self.store.validate_manifest_exact(manifest)

    def test_manifest_validation_rejects_missing_and_unexpected_generation_rows(
        self,
    ) -> None:
        source = canonical_source_path("/tmp/a.jsonl")
        owner = owner_digest(ownership_key(source))
        expected_physical = make_physical_id(UNITS, "N", "LE")
        row = file_row(
            expected_physical,
            "LE",
            "N",
            owner=owner,
            embedding_model="test-model",
            embedding_dimension=2,
        )
        self.store.stage_rows([row])
        identity = self.store.collection_identity(UNITS)
        manifest = build_generation_manifest(
            owner_key=ownership_key(source),
            generation_id="N",
            canonical_source=source,
            source_hash="source-hash",
            candidate_bundle_hash="bundle-hash",
            fingerprints={"pipeline": "v1"},
            collections={
                UNITS: {
                    **identity,
                    "embedding_model": "test-model",
                    "embedding_dimension": 2,
                    "logical_to_physical": {"LE": expected_physical},
                    "rows": {
                        expected_physical: {
                            "logical_id": "LE",
                            "document_hash": canonical_hash("document"),
                            "embedding_hash": canonical_hash([1.0, 0.0]),
                            "embedding_dimension": 2,
                            "embedding_model": "test-model",
                            "immutable_metadata": {},
                        }
                    },
                }
            },
        )
        self.store.stage_rows(
            [
                file_row(
                    make_physical_id(UNITS, "N", "LU"),
                    "LU",
                    "N",
                    owner=owner,
                    embedding_model="test-model",
                    embedding_dimension=2,
                )
            ]
        )
        with self.assertRaisesRegex(GenerationValidationError, "unexpected"):
            self.store.validate_manifest_exact(manifest)


if __name__ == "__main__":
    unittest.main()

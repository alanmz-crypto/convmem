"""Hermetic mixed-mode proof tests against Chroma 1.5.9."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from file_generation_store import FileGenerationStore
from mixed_mode_proof import (
    PHYSICAL_DELETION_DISABLED,
    characterize_chroma_storage,
    run_mixed_mode_proof,
)
from mixed_mode_retrieval import (
    MixedModeCandidateBudget,
    MixedModeCardinalityError,
    query_units_mixed_ann,
)
from serving_authority import FrozenAuthorityVector, OwnerAuthorityMode, OwnerAuthorityState
from tests.generation_read_fixtures import (
    inactive_neighbor_rows,
    stage_dec_stable_row,
    stage_owner_a_active_alpha,
)
from tests.test_file_generation_store import file_row


def _frozen_vector(chroma_dir: Path, active: dict[str, str], previous: dict[str, str]):
    by_owner = {
        owner: OwnerAuthorityState(
            owner,
            OwnerAuthorityMode.GENERATIONAL,
            generation_id=generation,
        )
        for owner, generation in active.items()
    }
    return FrozenAuthorityVector(
        by_owner=by_owner,
        legacy_global=False,
        resolution_attempts=1,
        evidence_snapshots={},
        generation_root=str(chroma_dir.parent / "generations"),
        chroma_dir=str(chroma_dir),
        previous_by_owner=previous,
    )


# unittest owns the temporary resource lifecycle across setUp/tearDown.
# pylint: disable=consider-using-with
class MixedModeProofTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.chroma = self.root / "chroma"
        self.control = self.root / "control"
        self.active = {"owner-a": "N"}
        self.previous = {"owner-a": "N-1"}
        self.store = FileGenerationStore(
            self.chroma,
            active_generations=lambda: dict(self.active),
            previous_generations=lambda: dict(self.previous),
        )
        stage_owner_a_active_alpha(self.store)
        stage_dec_stable_row(self.store)
        self.store.stage_rows(
            [
                file_row(
                    "fg1_prev_a",
                    "LP",
                    "N-1",
                    document="previous alpha",
                    embedding=[0.7, 0.3],
                ),
            ]
        )
        self.store.stage_rows(inactive_neighbor_rows(8))

    def tearDown(self) -> None:
        self.store.close()
        self.tmp.cleanup()

    def test_mixed_ann_excludes_inactive_neighbors(self) -> None:
        vector = _frozen_vector(self.chroma, self.active, self.previous)
        hits = query_units_mixed_ann(
            self.store,
            [1.0, 0.0],
            2,
            vector=vector,
            budget=MixedModeCandidateBudget(max_candidates=64),
        )
        ids = {row["id"] for row in hits}
        self.assertIn("fg1_active_a", ids)
        self.assertNotIn("fg1_inactive_0", ids)

    def test_proof_gates_pass_against_control(self) -> None:
        vector = _frozen_vector(self.chroma, self.active, self.previous)
        report = run_mixed_mode_proof(
            self.chroma,
            self.control,
            [1.0, 0.0],
            2,
            vector=vector,
            budget=MixedModeCandidateBudget(max_candidates=64),
        )
        self.assertTrue(report["gate_pass"])
        self.assertTrue(report["authority_safety"]["pass"])
        self.assertTrue(report["authorized_cardinality"]["pass"])
        self.assertEqual(report["chroma_version"], "1.5.9")
        self.assertTrue(report["gates"]["physical_deletion_disabled"])

    def test_retention_survives_restart(self) -> None:
        vector = _frozen_vector(self.chroma, self.active, self.previous)
        before = run_mixed_mode_proof(
            self.chroma,
            self.root / "control-a",
            [1.0, 0.0],
            2,
            vector=vector,
            budget=MixedModeCandidateBudget(max_candidates=64),
        )
        self.store.close()
        with FileGenerationStore(
            self.chroma,
            active_generations=lambda: dict(self.active),
            previous_generations=lambda: dict(self.previous),
        ) as _reopened:
            after = run_mixed_mode_proof(
                self.chroma,
                self.root / "control-b",
                [1.0, 0.0],
                2,
                vector=vector,
                budget=MixedModeCandidateBudget(max_candidates=64),
            )
        self.assertEqual(
            before["retention"]["retained_inactive_count"],
            after["retention"]["retained_inactive_count"],
        )
        self.assertGreaterEqual(after["retention"]["retained_inactive_count"], 1)

    def test_underfill_raises_cardinality_error(self) -> None:
        vector = _frozen_vector(self.chroma, self.active, self.previous)
        with self.assertRaises(MixedModeCardinalityError):
            query_units_mixed_ann(
                self.store,
                [1.0, 0.0],
                50,
                vector=vector,
                budget=MixedModeCandidateBudget(max_candidates=16, max_attempts=2),
            )

    def test_storage_characterization_reports_pinned_chroma(self) -> None:
        storage = characterize_chroma_storage(self.chroma)
        self.assertEqual(storage["chroma_version"], "1.5.9")
        self.assertTrue(storage["physical_deletion_disabled"])
        self.assertEqual(PHYSICAL_DELETION_DISABLED, True)


if __name__ == "__main__":
    unittest.main()

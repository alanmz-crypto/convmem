"""T5 copied-corpus rehearsal and Execute evidence bundle tests."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from cg2_property_map import PROPERTY_TEST_MAP, build_property_map_report
from cg2_rehearsal import (
    ARCHITECTURE_SHA,
    collect_execute_evidence,
    failure_matrix_evidence,
    measured_budgets,
    run_legacy_gateway_rehearsal,
    shadow_comparison_status,
)
from mixed_mode_retrieval import PINNED_CHROMA_VERSION


class Cg2RehearsalTests(unittest.TestCase):
    def test_legacy_gateway_rehearsal_equivalence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            report = run_legacy_gateway_rehearsal(Path(tmp))
        self.assertTrue(report["equivalence_pass"])
        self.assertEqual(report["serving_units"], report["physical_units"])

    def test_property_map_covers_formal_properties(self) -> None:
        required = {
            "QualifiedPointerServes",
            "SingleCurrentAuthority",
            "PostFenceNeverLegacy",
            "FrozenLegacyProtected",
            "PromotionChecksRecorded",
            "LostDriftEventuallyHandled",
            "RecoveryUsesExactPointer",
            "GCRespectsProtection",
            "TentativePinWindowProtected",
            "RenameVectorExclusive",
            "RenameGroupStable",
            "FrozenGenerationStable",
            "RetryBudgetTerminates",
            "AuthorityFailuresNeverFallback",
            "FallbackIsMediated",
        }
        self.assertTrue(required <= set(PROPERTY_TEST_MAP))
        report = build_property_map_report()
        self.assertGreaterEqual(report["property_count"], 12)

    def test_execute_evidence_bundle(self) -> None:
        bundle = collect_execute_evidence(
            execution_plan_sha="6a808f1543f2c93270d9f0ed1ae88cad27f6556b"
        )
        self.assertEqual(bundle["architecture_sha"], ARCHITECTURE_SHA)
        self.assertEqual(
            bundle["execution_plan_sha"],
            "6a808f1543f2c93270d9f0ed1ae88cad27f6556b",
        )
        self.assertTrue(bundle["chroma_version_matches_pin"])
        self.assertFalse(bundle["production_activation_performed"])
        self.assertFalse(bundle["automatic_gc_performed"])
        self.assertIn("authority_races", failure_matrix_evidence())

    def test_measured_budgets_use_ratified_constants(self) -> None:
        budgets = measured_budgets()
        self.assertEqual(budgets["chroma_version"], PINNED_CHROMA_VERSION)
        self.assertTrue(budgets["physical_deletion_disabled"])
        self.assertEqual(budgets["authority_resolution_retry_budget"]["max_attempts"], 5)

    def test_shadow_comparison_deferred_while_disabled(self) -> None:
        shadow = shadow_comparison_status()
        self.assertEqual(shadow["shadow_ledger"], "disabled")
        self.assertFalse(shadow["comparison_run"])


if __name__ == "__main__":
    unittest.main()

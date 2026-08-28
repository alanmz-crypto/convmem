"""D5 isolated Design A rehearsal and Execute evidence bundle tests."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from cg2_property_map import PROPERTY_TEST_MAP, build_property_map_report
from cg2_rehearsal import (
    ARCHITECTURE_SHA,
    EXECUTION_PLAN_SHA,
    build_hermetic_design_a_environment,
    collect_execute_evidence,
    failure_matrix_evidence,
    install_hermetic_production_boundary_patches,
    measured_budgets,
    run_design_a_isolated_rehearsal,
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
        bundle = collect_execute_evidence()
        self.assertEqual(bundle["architecture_sha"], ARCHITECTURE_SHA)
        self.assertEqual(bundle["execution_plan_sha"], EXECUTION_PLAN_SHA)
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


def test_design_a_isolated_rehearsal(tmp_path: Path, monkeypatch) -> None:
    live_chroma, live_generations = install_hermetic_production_boundary_patches(
        monkeypatch, tmp_path
    )
    report = run_design_a_isolated_rehearsal(
        tmp_path / "rehearsal",
        production_chroma=live_chroma,
        production_generation_root=live_generations,
    )

    assert report["no_production_operations"] is True
    assert report["physical_deletion_disabled"] is True
    assert report["request_freeze"]["pass"] is True
    assert report["first_pointer_previous_is_grb"] is True
    assert report["first_pointer_active_is_canary"] is True
    assert report["one_lock_cutover_oracle"]["pass"] is True
    assert report["one_lock_rollback_oracle"]["pass"] is True
    assert report["reconciliation_pending_after_source_advance"] is True
    assert report["recovery_matches_rollback"] is True
    assert report["reconciliation_state_hash_before_restart"] == report[
        "reconciliation_state_hash_after_restart"
    ]
    assert report["retention_inventory"]["grb_protected"] is True
    assert report["retention_inventory"]["grb_gc_eligible"] is False
    assert report["guard_blocks_second_first_cutover"] is True
    assert report["ratified_query_context_digest"] == report["live_query_context_digest"]

    bundle = collect_execute_evidence(rehearsal_report=report)
    assert bundle["design_a_rehearsal"] is report
    assert bundle["no_production_operations"] is True


def test_hermetic_environment_builds_grb_and_canary(tmp_path: Path, monkeypatch) -> None:
    install_hermetic_production_boundary_patches(monkeypatch, tmp_path)
    env = build_hermetic_design_a_environment(tmp_path / "env")
    assert env["grb_result"].generation_id
    assert env["canary_ref"].manifest["generation_id"]


if __name__ == "__main__":
    unittest.main()

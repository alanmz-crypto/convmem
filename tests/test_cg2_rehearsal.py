"""D5 isolated Design A rehearsal and Execute evidence bundle tests."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import pytest

from cg2_property_map import PROPERTY_TEST_MAP, build_property_map_report
from cg2_rehearsal import (
    ARCHITECTURE_SHA,
    EXECUTION_PLAN_SHA,
    RehearsalProductionIsolationError,
    _verify_no_production_contact,
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
    assert report["request_freeze"]["fresh_open_resolves_disk_not_frozen"] is True
    assert report["request_freeze"]["fresh_open_grb_generation_id"] == report["grb_generation_id"]
    assert report["request_freeze"]["fresh_open_grb_subprocess_pid"] != __import__("os").getpid()
    assert report["first_pointer_cas_from_none"] is True
    assert report["first_pointer_pre_publication_absent"] is True
    assert report["first_pointer_previous_is_grb"] is True
    assert report["first_pointer_active_is_canary"] is True
    assert report["one_lock_cutover_oracle"]["pass"] is True
    assert report["one_lock_rollback_oracle"]["pass"] is True
    assert report["reconciliation_pending_after_source_advance"] is True
    assert report["reconciliation_pending_after_restart"] is True
    assert report["recovery_matches_rollback"] is True
    assert report["reconciliation_ordering_trace"] == [
        "source_advanced",
        "reconciliation_obligation_durable",
        "rollback_pointer_publication",
    ]
    assert report["restart_boundary"]["session_closed_before_recovery"] is True
    assert report["restart_boundary"]["subprocess_is_fresh_process"] is True
    assert report["restart_boundary"]["recovery_in_fresh_process"] is True
    assert report["restart_boundary"]["recovery_matches_expected_grb"] is True
    assert report["reconciliation_state_hash_before_restart"] == report[
        "reconciliation_state_hash_after_restart"
    ]
    assert report["fence_content_hash_before_restart"] == report[
        "fence_content_hash_after_restart"
    ]
    assert report["guard_content_hash_before_restart"] == report[
        "guard_content_hash_after_restart"
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


def test_production_isolation_fails_closed_on_resolution_error(
    tmp_path: Path, monkeypatch
) -> None:
    install_hermetic_production_boundary_patches(monkeypatch, tmp_path)
    env = build_hermetic_design_a_environment(tmp_path / "isolation")
    def _resolution_failure():
        raise OSError("simulated production path resolution failure")

    monkeypatch.setattr(
        "cg2_legacy_vector_attestation._resolve_live_production_paths",
        _resolution_failure,
    )
    with pytest.raises(RehearsalProductionIsolationError, match="resolution failed"):
        _verify_no_production_contact(env, production_chroma=None, production_generation_root=None)


def test_subprocess_public_open_resolves_active_generation(
    tmp_path: Path, monkeypatch
) -> None:
    from cg2_rehearsal import _make_cutover_grant, _publish_cutover
    from mixed_mode_proof import run_rehearsal_subprocess_public_open

    install_hermetic_production_boundary_patches(monkeypatch, tmp_path)
    env = build_hermetic_design_a_environment(tmp_path / "public-open")
    grant = _make_cutover_grant(env, grant_id="public-open-grant")
    _publish_cutover(env, grant)
    probe = run_rehearsal_subprocess_public_open(env["cfg"], env["owner_digest"])
    assert probe["via_public_serving_open"] is True
    assert probe["subprocess_is_fresh_process"] is True
    assert probe["active_generation_id"] == grant.canary_generation_id


if __name__ == "__main__":
    unittest.main()

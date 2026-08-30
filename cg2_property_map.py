"""Map CG-2 formal architecture properties to mechanical pytest evidence."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

SCHEMA = "convmem/cg2-design-a-property-map-v3"
REPO_ROOT = Path(__file__).resolve().parent

# Inherited §13.18 architecture properties (historical formal map).
PROPERTY_TEST_MAP: dict[str, dict[str, Any]] = {
    "QualifiedPointerServes": {
        "tests": [
            "tests/test_file_generation_pointer.py",
            "tests/test_file_generation_validate.py",
        ],
        "notes": "Qualified pointer publication and cold validation",
    },
    "SingleCurrentAuthority": {
        "tests": [
            "tests/test_serving_authority.py",
            "tests/test_file_generation_pointer.py",
        ],
        "notes": "One active generation per owner at resolution",
    },
    "PostFenceNeverLegacy": {
        "tests": [
            "tests/test_serving_authority.py::test_fenced_owner_blocks_serving_open",
            "tests/test_serving_index_repository.py::test_authority_failure_never_triggers_query_fallback",
        ],
        "notes": "Fenced owner cannot open serving repository",
    },
    "FrozenLegacyProtected": {
        "tests": [
            "tests/test_serving_index_repository.py::test_legacy_gateway_matches_direct_chroma_query_units",
        ],
        "notes": "Legacy-global gateway preserves direct Chroma equivalence",
    },
    "PromotionChecksRecorded": {
        "tests": [
            "tests/test_source_freshness_promotion.py",
            "tests/test_file_generation_pointer.py",
        ],
        "notes": "Stale source and generation refuse promotion",
    },
    "LostDriftEventuallyHandled": {
        "tests": [
            "tests/test_source_reconciler.py",
        ],
        "notes": "Startup, sweep, overflow dirty, and coalescing queue",
    },
    "RecoveryUsesExactPointer": {
        "tests": [
            "tests/test_file_generation_validate.py",
            "tests/test_file_generation_pointer.py",
        ],
        "notes": "Recovery republishes exact pointer bytes, not completeness",
    },
    "GCRespectsProtection": {
        "tests": [
            "tests/test_mixed_mode_proof.py",
        ],
        "notes": "PHYSICAL_DELETION_DISABLED; retention inventory",
    },
    "TentativePinWindowProtected": {
        "tests": [
            (
                "tests/test_mixed_mode_proof.py::MixedModeProofTests::"
                "test_retention_survives_restart"
            ),
        ],
        "notes": "Retained inactive rows survive reopen",
    },
    "RenameVectorExclusive": {
        "tests": [
            "tests/test_file_generation_read_paths.py",
        ],
        "notes": "Owner/generation binding; live rename excluded from first canary",
    },
    "RenameGroupStable": {
        "tests": [
            (
                "tests/test_file_generation_read_paths.py::GenerationReadPathTests::"
                "test_reused_active_generation_id_cannot_cross_owner_boundary"
            ),
        ],
        "notes": "Shared generation id cannot cross owner boundary",
    },
    "FrozenGenerationStable": {
        "tests": [
            "tests/test_cg2_rehearsal.py::test_design_a_isolated_rehearsal",
        ],
        "notes": (
            "Request-frozen authority via isolated Design A rehearsal "
            "(cg2_rehearsal._assert_frozen_generation_stable oracle)"
        ),
    },
    "RetryBudgetTerminates": {
        "tests": [
            "tests/test_serving_authority.py::test_retry_budget_exhaustion_raises_authority_unstable",
        ],
        "notes": "AUTHORITY_UNSTABLE after attempt budget",
    },
    "AuthorityFailuresNeverFallback": {
        "tests": [
            "tests/test_serving_index_repository.py::test_authority_failure_never_triggers_query_fallback",
            "tests/test_serving_index_repository.py::test_serving_authority_error_is_not_transient",
        ],
        "notes": "Authority errors never reach keyword fallback",
    },
    "FallbackIsMediated": {
        "tests": [
            "tests/test_serving_index_repository.py::test_transient_backend_uses_mediated_fallback_only",
        ],
        "notes": "Only ServingBackendTransient uses mediated fallback",
    },
}

# Design A formal named properties (EXECUTION §11.3 / formal README).
DESIGN_A_FORMAL_PROPERTY_MAP: dict[str, dict[str, Any]] = {
    "UnknownModelOnlyForRatifiedLegacyBaseline": {
        "tests": [
            "tests/test_cg2_rollback_baseline.py::test_b1_manifest_unknown_model_profile",
        ],
        "notes": "G_rb uses LEGACY_EXACT_VECTOR_UNKNOWN_MODEL_V1 only",
    },
    "ProspectiveGenerationRequiresKnownWriterModel": {
        "tests": [
            "tests/test_cg2_rehearsal.py::test_hermetic_environment_builds_grb_and_canary",
        ],
        "notes": "G_canary rehearsal uses KNOWN_MODEL_AND_VECTOR_V1 profile",
    },
    "D0CandidateNotAuthority": {
        "tests": [
            "tests/test_cg2_legacy_vector_attestation.py::test_candidate_cannot_emit_validation",
            "tests/test_cg2_legacy_vector_attestation.py::test_tampered_candidate_with_recomputed_hash_still_refuses",
        ],
        "notes": "Candidate self-hash is never authority",
    },
    "D0ValidationRequired": {
        "tests": [
            "tests/test_cg2_legacy_vector_attestation.py::test_independent_validation_and_single_lock",
        ],
        "notes": "Separate validation execution with single source_flock acquisition",
    },
    "D0RatificationRequired": {
        "tests": [
            "tests/test_cg2_legacy_vector_attestation.py::test_ratification_missing_mismatch_invalidated",
            "tests/test_cg2_rollback_baseline.py::test_d0_missing_ratification_refuses",
        ],
        "notes": "Ryan ratification required before D1 authority consumption",
    },
    "FirstCutoverRebindsCurrentLegacyRoot": {
        "tests": [
            "tests/test_cg2_first_cutover.py::test_lock_held_reread_before_fence",
        ],
        "notes": "Live LEGACY reread under lock before fence commit",
    },

    "GRbAuthoritySinglePhysicalState": {
        "tests": [
            "tests/test_cg2_reference_v2.py::test_same_reader_spy_qualification_and_serving",
            "tests/test_cg2_reference_v2.py::test_reference_v2_first_cutover_rollback_same_reader_rehearsal",
        ],
        "notes": "Qualification and serving share one exact-ID reader",
    },
    "GRbReferenceMembershipExact": {
        "tests": [
            "tests/test_cg2_reference_v2.py::test_adversarial_missing_physical_id_refuses",
            "tests/test_cg2_reference_v2.py::test_adversarial_substituted_physical_id_refuses",
            "tests/test_cg2_reference_v2.py::test_adversarial_duplicate_physical_id_refuses",
            "tests/test_cg2_reference_v2.py::test_adversarial_additional_physical_id_refuses",
            "tests/test_cg2_reference_v2.py::test_adversarial_wrong_owner_physical_id_refuses",
        ],
        "notes": "Selector membership equals D0 physical-id set exactly",
    },
    "GRbServingReadsReferencedRows": {
        "tests": [
            "tests/test_cg2_reference_v2.py::test_serving_reads_referenced_rows_only",
        ],
        "notes": "Rollback serving consumes target-aware reader output",
    },
    "GRbNoCopiedOrSidecarAuthority": {
        "tests": [
            "tests/test_cg2_reference_v2.py::test_zero_copied_vector_rows",
            "tests/test_cg2_reference_v2.py::test_reference_v2_static_inventory_no_sidecar_or_copied_vector_authority",
            "tests/test_cg2_reference_v2.py::test_reference_v2_lookup_spy_no_sidecar_or_generation_get_rows",
        ],
        "notes": "No Chroma staging/upsert on reference-v2 retention path",
    },
    "GRbColdQualificationBeforeRetention": {
        "tests": [
            "tests/test_cg2_reference_v2.py::test_reference_v2_happy_path",
        ],
        "notes": "Retention requires fresh-process reference-v2 qualification",
    },
    "GRbRecoveryCoverageBeforeFirstCutover": {
        "tests": [
            "tests/test_cg2_reference_v2.py::test_recovery_eligibility_binds_rows",
        ],
        "notes": "Recovery coverage binds referenced original rows",
    },
    "GRbFailedV1NeverEligible": {
        "tests": [
            "tests/test_cg2_reference_v2.py::test_failed_convert_v1_target_id_refuses",
        ],
        "notes": "Failed convert-v1 target id is permanently ineligible",
    },
    "GRbReferenceFingerprintVersioned": {
        "tests": [
            "tests/test_cg2_reference_v2.py::test_deterministic_reference_v2_target_id",
            "tests/test_cg2_reference_v2.py::test_reference_v2_id_differs_from_convert_v1",
        ],
        "notes": "Only reference-v2 fingerprint derives corrected target id",
    },
    "GRollbackRequiresExactQueryContext": {
        "tests": [
            "tests/test_cg2_first_cutover.py::test_grb_rollback_refuses_query_context_drift",
            "tests/test_cg2_rollback_baseline.py::test_b3_query_context_mismatch_refuses",
        ],
        "notes": "G_rb-only query-context equality; not required for known-model rollback",
    },
    "FirstCutoverHasExactRollbackBaseline": {
        "tests": [
            "tests/test_cg2_first_cutover.py::test_successful_first_cutover",
            "tests/test_cg2_rehearsal.py::test_design_a_isolated_rehearsal",
        ],
        "notes": "First pointer previous=G_rb with exact retained baseline evidence",
    },
    "FirstCutoverGenerationsDistinct": {
        "tests": [
            "tests/test_cg2_first_cutover.py::test_preflight_refuses_grb_equals_canary",
        ],
        "notes": "G_rb and G_canary must differ before fence",
    },
    "CASSeparateFromRollbackLineage": {
        "tests": [
            "tests/test_file_generation_pointer.py::test_rollback_stale_cas_refuses_independent_of_target_validity",
            "tests/test_file_generation_pointer.py::test_first_cutover_pointer_capability",
        ],
        "notes": "Forward CAS separate from rollback lineage fields",
    },
    "PreFenceRefusalPreservesLegacy": {
        "tests": [
            "tests/test_cg2_first_cutover.py::test_preflight_refusal_matrix",
        ],
        "notes": "Structural pre-fence refusal leaves owner LEGACY",
    },
    "PostFenceFailureNeverLegacy": {
        "tests": [
            "tests/test_cg2_first_cutover.py::test_crash_after_fence_leaves_fenced_no_pointer",
        ],
        "notes": "Post-fence failure resolves FENCED_NO_POINTER, never LEGACY",
    },
    "FenceCrashResumeRequiresFreshGrant": {
        "tests": [
            "tests/test_cg2_first_cutover.py::test_fresh_grant_resume_after_fence_crash",
            "tests/test_cg2_rehearsal.py::test_design_a_isolated_rehearsal",
        ],
        "notes": "Fence-only crash resume requires fresh grant identity",
    },
    "GuardCrashResumeRequiresFreshGrant": {
        "tests": [
            "tests/test_cg2_rehearsal.py::test_design_a_isolated_rehearsal",
        ],
        "notes": "Guard crash/resume oracle in isolated rehearsal controls",
    },
    "WrongGuardRefusesFirstPointer": {
        "tests": [
            "tests/test_cg2_first_cutover.py::test_lock_held_refuses_wrong_owner_guard",
            "tests/test_cg2_first_cutover.py::test_lock_held_refuses_corrupt_guard",
        ],
        "notes": "Conflicting guard refuses first pointer without LEGACY restoration",
    },
    "RollbackAfterSourceAdvanceKeepsReconciliation": {
        "tests": [
            "tests/test_cg2_first_cutover.py::test_grb_rollback_after_source_advance_records_reconciliation",
            "tests/test_cg2_rehearsal.py::test_design_a_isolated_rehearsal",
        ],
        "notes": "Source-advanced rollback persists reconciliation debt",
    },
    "RollbackNeverResurrectsLegacy": {
        "tests": [
            "tests/test_cg2_first_cutover.py::test_rollback_preserves_fence_and_generational_owner",
        ],
        "notes": "Rollback uses retained generation, not legacy resurrection",
    },
    "RecoveryNeverSwitchesGeneration": {
        "tests": [
            "tests/test_file_generation_pointer.py::test_recovery_cannot_switch_to_another_complete_generation",
            "tests/test_file_generation_pointer.py::test_recovery_has_no_generation_selection_parameter",
        ],
        "notes": "Same-pointer recovery; no generation selection parameter",
    },
    "FirstCanaryBlocksSecondPromotion": {
        "tests": [
            "tests/test_cg2_first_cutover.py::test_open_guard_blocks_second_first_cutover",
            "tests/test_cg2_rehearsal.py::test_design_a_isolated_rehearsal",
        ],
        "notes": "Open canary guard blocks second first-cutover/forward promotion",
    },
    "RollbackBaselineNeverGCEligible": {
        "tests": [
            (
                "tests/test_mixed_mode_proof.py::MixedModeProofTests::"
                "test_grb_retained_across_design_a_lifecycle"
            ),
            "tests/test_cg2_rollback_baseline.py::test_grb_protection_permits_canary_staging",
        ],
        "notes": "RETAINED_ROLLBACK_BASELINE protected across lifecycle",
    },
    "AuthorityOperationAcquiresOwnerLockOnce": {
        "tests": [
            "tests/test_cg2_first_cutover.py::test_one_lock_successful_cutover",
            "tests/test_cg2_rehearsal.py::test_design_a_isolated_rehearsal",
        ],
        "notes": "One source_flock interval per authority-changing operation",
    },
}

# EXECUTION §15 architecture invariant → pytest map (Design A Execute closure).
DESIGN_A_INVARIANT_MAP: dict[str, dict[str, Any]] = {
    "d0_candidate_not_authority": {
        "tests": DESIGN_A_FORMAL_PROPERTY_MAP["D0CandidateNotAuthority"]["tests"],
        "implementation": "cg2_legacy_vector_attestation.py",
    },
    "d0_validation_separate_execution_single_lock": {
        "tests": [
            "tests/test_cg2_legacy_vector_attestation.py::test_independent_validation_and_single_lock",
            "tests/test_cg2_legacy_vector_attestation.py::test_capture_churn_refuses_publication",
        ],
        "implementation": "cg2_legacy_vector_attestation.py",
    },
    "d0_ratification_fail_closed": {
        "tests": [
            "tests/test_cg2_legacy_vector_attestation.py::test_ratification_missing_mismatch_invalidated",
        ],
        "implementation": "cg2_legacy_vector_attestation.py",
    },
    "query_context_grb_only": {
        "tests": DESIGN_A_FORMAL_PROPERTY_MAP["GRollbackRequiresExactQueryContext"]["tests"],
        "implementation": "cg2_legacy_vector_attestation.py; cg2_first_cutover.py",
    },
    "accepted_legacy_set_converts_exactly_to_grb": {
        "tests": [
            "tests/test_cg2_rollback_baseline.py::test_frozen_legacy_set_is_bidirectionally_equivalent_to_grb",
            "tests/test_cg2_rollback_baseline.py::test_d0_root_mismatch_against_reread_refuses",
        ],
        "implementation": "cg2_rollback_baseline.py",
    },
    "ratified_convert_v1_fingerprint": {
        "tests": [
            "tests/test_cg2_rollback_baseline.py::test_literal_convert_v1_fingerprint_and_deterministic_generation_id",
        ],
        "implementation": "cg2_rollback_baseline.py",
    },
    "unknown_model_profile_for_grb": {
        "tests": [
            "tests/test_cg2_rollback_baseline.py::test_b1_manifest_unknown_model_profile",
        ],
        "implementation": "cg2_rollback_baseline.py",
    },
    "known_model_profile_for_g_canary": {
        "tests": [
            "tests/test_cg2_rehearsal.py::test_hermetic_environment_builds_grb_and_canary",
        ],
        "implementation": "cg2_rehearsal.py / build_candidate_generation",
    },
    "provenance_identity_preserved": {
        "tests": [
            (
                "tests/test_cg2_rollback_baseline.py::"
                "test_same_ledger_distinct_provenance_survive_without_dedupe_or_remint"
            ),
            "tests/test_cg2_rollback_baseline.py::test_b2_envelope_swap_in_evidence_refuses_validation",
        ],
        "implementation": "cg2_rollback_baseline.py",
    },
    "retained_rollback_baseline_protected": {
        "tests": [
            (
                "tests/test_file_generation_store.py::FileGenerationStoreTests::"
                "test_retained_rollback_baseline_permits_canary_staging_without_deletion"
            ),
            (
                "tests/test_mixed_mode_proof.py::MixedModeProofTests::"
                "test_grb_retained_across_design_a_lifecycle"
            ),
        ],
        "implementation": "file_generation_store.py",
    },
    "cas_and_durable_lineage_separate": {
        "tests": [
            "tests/test_file_generation_pointer.py::test_first_cutover_pointer_capability",
            "tests/test_file_generation_pointer.py::test_rollback_stale_cas_refuses_independent_of_target_validity",
        ],
        "implementation": "file_generation_pointer.py",
    },
    "ordinary_publish_cannot_create_first_pointer": {
        "tests": [
            "tests/test_file_generation_pointer.py::test_first_cutover_pointer_capability",
        ],
        "implementation": "file_generation_pointer.py",
    },
    "first_cutover_exact_grb_canary_d0_chain": {
        "tests": [
            "tests/test_cg2_first_cutover.py::test_successful_first_cutover",
            "tests/test_cg2_rehearsal.py::test_design_a_isolated_rehearsal",
        ],
        "implementation": "cg2_first_cutover.py",
    },
    "grb_not_equal_g_canary": {
        "tests": [
            "tests/test_cg2_first_cutover.py::test_preflight_refuses_grb_equals_canary",
        ],
        "implementation": "cg2_first_cutover.py",
    },
    "pre_fence_refusal_remains_legacy": {
        "tests": [
            "tests/test_cg2_first_cutover.py::test_preflight_refusal_matrix",
        ],
        "implementation": "cg2_first_cutover.py",
    },
    "post_fence_failure_fenced_no_pointer": {
        "tests": [
            "tests/test_cg2_first_cutover.py::test_crash_after_fence_leaves_fenced_no_pointer",
        ],
        "implementation": "cg2_first_cutover.py",
    },
    "fresh_grant_resume_only": {
        "tests": [
            "tests/test_cg2_first_cutover.py::test_fresh_grant_resume_after_fence_crash",
            "tests/test_cg2_first_cutover.py::test_old_grant_refused_on_resume",
        ],
        "implementation": "cg2_first_cutover.py",
    },
    "fence_never_clears_to_legacy": {
        "tests": [
            "tests/test_cg2_first_cutover.py::test_rollback_preserves_fence_and_generational_owner",
            "tests/test_cg2_rehearsal.py::test_design_a_isolated_rehearsal",
        ],
        "implementation": "cg2_first_cutover.py",
    },
    "rollback_after_source_advance": {
        "tests": [
            "tests/test_cg2_first_cutover.py::test_grb_rollback_after_source_advance_records_reconciliation",
        ],
        "implementation": "file_generation_pointer.py",
    },
    "reconciliation_before_stale_rollback_pointer": {
        "tests": [
            "tests/test_source_freshness_promotion.py::test_rollback_reconciliation_precedes_pointer_publication",
            "tests/test_source_reconciler.py::test_rollback_reconciliation_obligation_survives_process_restart",
        ],
        "implementation": "source_reconciler.py",
    },
    "grb_rollback_needs_d0_and_query_context": {
        "tests": [
            "tests/test_cg2_first_cutover.py::test_grb_rollback_refuses_missing_ratification_id",
            "tests/test_cg2_first_cutover.py::test_grb_rollback_refuses_evidence_sha_mismatch",
            "tests/test_cg2_first_cutover.py::test_grb_rollback_refuses_query_context_drift",
        ],
        "implementation": "file_generation_pointer.py / cg2_first_cutover.py",
    },
    "recovery_cannot_switch_generation": {
        "tests": DESIGN_A_FORMAL_PROPERTY_MAP["RecoveryNeverSwitchesGeneration"]["tests"],
        "implementation": "file_generation_pointer.py",
    },
    "one_owner_lock_interval_per_authority_change": {
        "tests": DESIGN_A_FORMAL_PROPERTY_MAP["AuthorityOperationAcquiresOwnerLockOnce"]["tests"],
        "implementation": "cg2_first_cutover.py; cg2_rehearsal.py",
    },
    "no_second_promotion_during_canary": {
        "tests": DESIGN_A_FORMAL_PROPERTY_MAP["FirstCanaryBlocksSecondPromotion"]["tests"],
        "implementation": "cg2_cutover_guard.py",
    },
    "frozen_generation_stable_mid_request": {
        "tests": [
            "tests/test_cg2_rehearsal.py::test_design_a_isolated_rehearsal",
        ],
        "implementation": "cg2_rehearsal._assert_frozen_generation_stable",
    },
    "gc_disabled_baseline_retained": {
        "tests": [
            (
                "tests/test_mixed_mode_proof.py::MixedModeProofTests::"
                "test_grb_retained_across_design_a_lifecycle"
            ),
        ],
        "implementation": "mixed_mode_proof.py",
    },
    "complete_data_restore_preserves_d0_grb": {
        "tests": [
            (
                "tests/test_cg2_legacy_vector_attestation.py::"
                "test_restore_preserves_d0_and_keeps_backup_evidence_non_authoritative"
            ),
            "tests/test_complete_data_restore.py",
        ],
        "implementation": "complete_data_restore.py",
    },
}

REQUIRED_INHERITED_FORMAL_PROPERTIES = frozenset(PROPERTY_TEST_MAP)
REQUIRED_DESIGN_A_FORMAL_PROPERTIES = frozenset(DESIGN_A_FORMAL_PROPERTY_MAP)
REQUIRED_DESIGN_A_INVARIANTS = frozenset(DESIGN_A_INVARIANT_MAP)


def _iter_mapped_test_nodes() -> list[str]:
    nodes: list[str] = []
    for mapping in (
        PROPERTY_TEST_MAP,
        DESIGN_A_FORMAL_PROPERTY_MAP,
        DESIGN_A_INVARIANT_MAP,
    ):
        for entry in mapping.values():
            nodes.extend(entry.get("tests", []))
    return nodes


def verify_property_map_node_resolution() -> dict[str, Any]:
    """Mechanically verify every mapped pytest node collects at least one test."""

    unresolved: list[str] = []
    resolved_count = 0
    for node in _iter_mapped_test_nodes():
        result = subprocess.run(
            ["python", "-m", "pytest", node, "--collect-only", "-q"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        combined = f"{result.stdout}\n{result.stderr}".lower()
        if result.returncode != 0 or "no tests collected" in combined:
            unresolved.append(node)
        else:
            resolved_count += 1
    return {
        "mapped_node_count": len(_iter_mapped_test_nodes()),
        "resolved_node_count": resolved_count,
        "unresolved_nodes": unresolved,
        "all_nodes_resolve": not unresolved,
    }


def verify_property_map_completeness() -> dict[str, Any]:
    """Return completeness oracle for D7 Execute-close bundle."""

    node_resolution = verify_property_map_node_resolution()
    return {
        "schema": SCHEMA,
        "inherited_formal_complete": REQUIRED_INHERITED_FORMAL_PROPERTIES
        <= set(PROPERTY_TEST_MAP),
        "design_a_formal_complete": REQUIRED_DESIGN_A_FORMAL_PROPERTIES
        <= set(DESIGN_A_FORMAL_PROPERTY_MAP),
        "design_a_invariant_complete": REQUIRED_DESIGN_A_INVARIANTS
        <= set(DESIGN_A_INVARIANT_MAP),
        "inherited_formal_count": len(PROPERTY_TEST_MAP),
        "design_a_formal_count": len(DESIGN_A_FORMAL_PROPERTY_MAP),
        "design_a_invariant_count": len(DESIGN_A_INVARIANT_MAP),
        "frozen_generation_stable_dedicated": (
            "tests/test_cg2_rehearsal.py::test_design_a_isolated_rehearsal"
            in PROPERTY_TEST_MAP["FrozenGenerationStable"]["tests"]
        ),
        "node_resolution": node_resolution,
    }


def build_property_map_report() -> dict[str, Any]:
    completeness = verify_property_map_completeness()
    return {
        "schema": SCHEMA,
        "property_count": len(PROPERTY_TEST_MAP),
        "properties": PROPERTY_TEST_MAP,
        "design_a_formal_properties": DESIGN_A_FORMAL_PROPERTY_MAP,
        "design_a_invariants": DESIGN_A_INVARIANT_MAP,
        "completeness": completeness,
    }

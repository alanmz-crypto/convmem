"""Map CG-2 formal architecture properties to mechanical pytest evidence."""

from __future__ import annotations

from typing import Any

SCHEMA = "convmem/cg2-property-map-v1"

# Keys match docs/plans/formal/cg2/README.md architecture-property table.
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
            "tests/test_mixed_mode_proof.py::test_retention_survives_restart",
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
            "tests/test_file_generation_read_paths.py::test_reused_active_generation_id_cannot_cross_owner_boundary",
        ],
        "notes": "Shared generation id cannot cross owner boundary",
    },
    "FrozenGenerationStable": {
        "tests": [
            (
                "tests/test_serving_index_repository.py::"
                "test_frozen_generation_stays_stable_when_pointer_changes_mid_request"
            ),
        ],
        "notes": (
            "Request-frozen authority vector ignores mid-request pointer changes"
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


def build_property_map_report() -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "property_count": len(PROPERTY_TEST_MAP),
        "properties": PROPERTY_TEST_MAP,
    }

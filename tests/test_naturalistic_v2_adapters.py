"""V2-02 — evidence adapter profiles and capability vector adversarial tests."""

# The test imports below follow the repository-local sys.path setup.
# pylint: disable=duplicate-code,too-many-public-methods,wrong-import-position

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from eval_naturalistic.base import StructuralContractError
from eval_naturalistic.v2.adapters.capability import (
    CAPABILITY_DIMENSIONS,
    CapabilityVectorV2,
    OccurrenceIdentityCapability,
)
from eval_naturalistic.v2.adapters.crush_sqlite import crush_sqlite_profile
from eval_naturalistic.v2.adapters.jsonl_derived import (
    jsonl_derived_profile,
    jsonl_derived_profile_invented_native,
)
from eval_naturalistic.v2.adapters.markdown_derived import markdown_derived_profile
from eval_naturalistic.v2.adapters.opencode_sqlite import (
    opencode_sqlite_profile,
    opencode_sqlite_profile_schema_drift,
)
from eval_naturalistic.v2.adapters.profile import (
    EvidenceAdapterProfileV2,
    NativeRecordIdentityMode,
)
from eval_naturalistic.v2.adapters.reduction import (
    CapabilityUseV2,
    evaluate_all_uses,
    evaluate_capability_for_use,
)
from eval_naturalistic.v2.adapters.registry import (
    parse_evidence_adapter_profile,
    profile_for_legacy_format,
    resolve_profile_or_fail,
)
from eval_naturalistic.v2.adapters.unsupported import unsupported_profile
from eval_naturalistic.v2.evidence import SourcePresenceV2, normalized_reported_presence
from tests.fixtures.naturalistic_v2_adapters import (
    crush_profile_with_attachment_loss,
    valid_profile_dict,
)


class NaturalisticV2AdapterTests(unittest.TestCase):
    def test_nine_capability_dimensions_present(self) -> None:
        profile = crush_sqlite_profile()
        payload = profile.capability_vector.to_dict()
        self.assertEqual(set(payload.keys()), set(CAPABILITY_DIMENSIONS))

    def test_unsupported_adapter_fails_closed(self) -> None:
        profile = unsupported_profile(reason="sqlite_kiro not profiled")
        decision = profile.capability_for_use(CapabilityUseV2.ADJUDICATION)
        self.assertFalse(decision.allowed)
        with self.assertRaises(StructuralContractError):
            resolve_profile_or_fail("sqlite_kiro")

    def test_malformed_profile_fails_closed(self) -> None:
        body = valid_profile_dict(crush_sqlite_profile())
        del body["semantics"]["ordering"]
        with self.assertRaises(StructuralContractError):
            EvidenceAdapterProfileV2.from_dict(body)

    def test_truncated_envelope_is_explicitly_partial(self) -> None:
        profile = jsonl_derived_profile("jsonl_cursor", truncated=True)
        self.assertEqual(profile.capability_vector.evidence_completeness.value, "PARTIAL_KNOWN")
        self.assertIn("Truncated", profile.semantics.omissions_truncation)

    def test_missing_stable_native_id_cannot_become_native_authority(self) -> None:
        profile = crush_sqlite_profile()
        self.assertEqual(profile.native_record_identity_mode, NativeRecordIdentityMode.UNKNOWN)
        self.assertNotEqual(
            profile.capability_vector.occurrence_identity,
            OccurrenceIdentityCapability.NATIVE_UNIQUE,
        )

    def test_invented_native_id_cannot_upgrade_capability(self) -> None:
        profile = jsonl_derived_profile_invented_native()
        with self.assertRaises(StructuralContractError):
            profile.validate()

    def test_attachment_loss_lowers_capability(self) -> None:
        profile = crush_profile_with_attachment_loss()
        decision = evaluate_capability_for_use(
            profile.capability_vector,
            CapabilityUseV2.PRIMARY_SCORING,
            target_material_span_policy_passes=False,
        )
        self.assertFalse(decision.allowed)
        self.assertIn("target_material_span_policy_passes==false", decision.failure_reasons)

    def test_unknown_extension_fields_declared(self) -> None:
        profile = opencode_sqlite_profile()
        self.assertIn("Extension JSON", profile.semantics.unknown_extension_fields)
        self.assertTrue(profile.declared_omissions)

    def test_schema_drift_bounds_capability(self) -> None:
        baseline = opencode_sqlite_profile()
        drift = opencode_sqlite_profile_schema_drift("opencode.message.part.v99")
        self.assertEqual(drift.schema_version, "opencode.message.part.v99")
        self.assertEqual(
            drift.capability_vector.evidence_completeness.value,
            "UNKNOWN",
        )
        self.assertNotEqual(
            baseline.capability_vector.to_dict(),
            drift.capability_vector.to_dict(),
        )

    def test_source_present_verbatim_unavailable_remains_present(self) -> None:
        profile = crush_sqlite_profile()
        reported = normalized_reported_presence(profile.default_availability)
        self.assertEqual(reported, SourcePresenceV2.PRESENT)
        unsupported = unsupported_profile(reason="test", source_present=True)
        self.assertEqual(
            normalized_reported_presence(unsupported.default_availability),
            SourcePresenceV2.PRESENT,
        )

    def test_duplicate_handling_declared_and_deterministic(self) -> None:
        left = profile_for_legacy_format("sqlite_crush")
        right = profile_for_legacy_format("sqlite_crush")
        self.assertEqual(left.semantics.duplicate_handling, right.semantics.duplicate_handling)
        self.assertIn("duplicate", left.semantics.duplicate_handling.lower())

    def test_ordering_not_silently_normalized(self) -> None:
        profile = jsonl_derived_profile("jsonl_codex_rollout")
        self.assertIn("line order", profile.semantics.ordering.lower())

    def test_jsonl_derived_not_labeled_provider_native(self) -> None:
        profile = jsonl_derived_profile("jsonl_cursor")
        self.assertEqual(profile.native_record_identity_mode, NativeRecordIdentityMode.DERIVED)
        self.assertEqual(profile.capability_vector.occurrence_identity.value, "DERIVED")

    def test_markdown_span_not_labeled_provider_native(self) -> None:
        profile = markdown_derived_profile("aider_markdown")
        self.assertEqual(profile.native_record_identity_mode, NativeRecordIdentityMode.DERIVED)
        self.assertIn("Byte/heading span", profile.semantics.native_record_identity)

    def test_unknown_capability_state_remains_unknown(self) -> None:
        profile = opencode_sqlite_profile()
        self.assertEqual(profile.capability_vector.revision_asof_binding.value, "UNKNOWN")
        self.assertEqual(profile.capability_vector.temporal_reproducibility.value, "UNKNOWN")

    def test_per_use_reduction_deterministic(self) -> None:
        vector = crush_sqlite_profile().capability_vector
        first = evaluate_all_uses(vector)
        second = evaluate_all_uses(vector)
        for use in CapabilityUseV2:
            self.assertEqual(first[use], second[use])

    def test_per_use_reduction_mixed_vectors(self) -> None:
        crush = crush_sqlite_profile().capability_vector
        jsonl = jsonl_derived_profile("jsonl_cursor").capability_vector
        crush_adj = evaluate_capability_for_use(crush, CapabilityUseV2.ADJUDICATION)
        jsonl_adj = evaluate_capability_for_use(jsonl, CapabilityUseV2.ADJUDICATION)
        self.assertTrue(crush_adj.allowed)
        self.assertTrue(jsonl_adj.allowed)
        crush_disc = evaluate_capability_for_use(crush, CapabilityUseV2.DISCOVERY_ELIGIBILITY)
        unsupported = unsupported_profile(reason="x").capability_vector
        uns_disc = evaluate_capability_for_use(unsupported, CapabilityUseV2.DISCOVERY_ELIGIBILITY)
        self.assertTrue(crush_disc.allowed)
        self.assertFalse(uns_disc.allowed)

    def test_primary_scoring_fail_closed_without_assurance_decision(self) -> None:
        vector = crush_sqlite_profile().capability_vector
        decision = evaluate_capability_for_use(vector, CapabilityUseV2.PRIMARY_SCORING)
        self.assertFalse(decision.allowed)
        self.assertIn("D_ASSURANCE_001 unselected", decision.failure_reasons[0])

    def test_profile_round_trip(self) -> None:
        profile = crush_sqlite_profile()
        parsed = parse_evidence_adapter_profile(valid_profile_dict(profile))
        self.assertEqual(parsed.profile_id, profile.profile_id)
        self.assertEqual(parsed.capability_vector.to_dict(), profile.capability_vector.to_dict())

    def test_registry_covers_jsonl_and_markdown_families(self) -> None:
        self.assertEqual(
            profile_for_legacy_format("jsonl_kiro_session").legacy_format,
            "jsonl_kiro_session",
        )
        self.assertEqual(
            profile_for_legacy_format("inter_model_doc").legacy_format,
            "inter_model_doc",
        )

    def test_capability_vector_rejects_unknown_fields(self) -> None:
        body = crush_sqlite_profile().capability_vector.to_dict()
        body["scalar_assurance"] = "HIGH"
        with self.assertRaises(StructuralContractError):
            CapabilityVectorV2.from_dict(body)

    def test_derived_human_ceiling_is_display_only(self) -> None:
        profile = crush_sqlite_profile()
        self.assertIsInstance(profile.capability_vector.derived_human_ceiling(), str)
        unsupported = unsupported_profile(reason="x")
        self.assertEqual(unsupported.capability_vector.derived_human_ceiling(), "unsupported")


if __name__ == "__main__":
    unittest.main()

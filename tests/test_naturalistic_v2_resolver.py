"""V2-03 — P2 opaque resolver and P1/P2 firewall adversarial tests."""

from __future__ import annotations

import copy
import hashlib
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from eval_naturalistic.base import StructuralContractError
from eval_naturalistic.digest import artifact_content_digest
from eval_naturalistic.v2.adapters.capability import EvidenceCompletenessCapability
from eval_naturalistic.v2.adapters.opencode_sqlite import opencode_sqlite_profile_schema_drift
from eval_naturalistic.v2.adapters.registry import profile_for_legacy_format
from eval_naturalistic.v2.evidence import (
    SourcePresenceV2,
    SummaryEvidenceAvailabilityV2,
    VerbatimEvidenceAvailabilityV2,
)
from eval_naturalistic.v2.firewall import (
    canonicalize_field_name,
    p1_payload_unchanged_by_p2_scan,
    reject_p2_fields_on_p1,
)
from eval_naturalistic.v2.resolver import (
    ResolverInputV2,
    compute_resolver_input_digest,
    compute_resolver_output_digest,
    resolve_opaque,
    resolver_implementation_digest,
    verify_opaque_resolver_manifest,
)
from eval_naturalistic.v2.resolver_contracts import ResolutionDetailV2, ResolverResultV2
from eval_naturalistic.v2.validators import parse_evidence_seal_manifest_v2
from tests.fixtures.naturalistic_v2_p1 import (
    ALT_DIGEST,
    FIXED_DIGEST,
    sample_availability,
    sample_availability_manifest,
    sample_occurrence,
    sample_seal_manifest,
)
from tests.fixtures.naturalistic_v2_resolver import (
    crush_resolver_input,
    summary_only_resolver_input,
    unsupported_resolver_input,
)


class NaturalisticV2ResolverTests(unittest.TestCase):
    def test_exact_resolution(self) -> None:
        manifest = resolve_opaque(crush_resolver_input())
        self.assertEqual(manifest.resolver_result, ResolverResultV2.EXACT_MATCH)

    def test_summary_only_resolution(self) -> None:
        resolver_input = crush_resolver_input(
            verbatim=VerbatimEvidenceAvailabilityV2.UNAVAILABLE,
            summary=SummaryEvidenceAvailabilityV2.AVAILABLE,
        )
        manifest = resolve_opaque(resolver_input)
        self.assertEqual(manifest.resolver_result, ResolverResultV2.SUMMARY_ONLY)

    def test_no_match(self) -> None:
        resolver_input = crush_resolver_input()
        other = sample_occurrence(physical_instance="other", namespace="other-ns")
        mutated = ResolverInputV2(
            construct_freeze_digest=resolver_input.construct_freeze_digest,
            evidence_seal=resolver_input.evidence_seal,
            evidence_availability=resolver_input.evidence_availability,
            adapter_profile=resolver_input.adapter_profile,
            legacy_format=resolver_input.legacy_format,
            query_occurrence_reference=other,
        )
        manifest = resolve_opaque(mutated)
        self.assertEqual(manifest.resolver_result, ResolverResultV2.NO_MATCH)

    def test_evidence_unavailable(self) -> None:
        resolver_input = crush_resolver_input(
            verbatim=VerbatimEvidenceAvailabilityV2.UNAVAILABLE,
            summary=SummaryEvidenceAvailabilityV2.UNAVAILABLE,
        )
        manifest = resolve_opaque(resolver_input)
        self.assertEqual(manifest.resolver_result, ResolverResultV2.EVIDENCE_UNAVAILABLE)

    def test_resolver_error_ambiguous(self) -> None:
        resolver_input = crush_resolver_input()
        ambiguous = ResolverInputV2(
            construct_freeze_digest=resolver_input.construct_freeze_digest,
            evidence_seal=resolver_input.evidence_seal,
            evidence_availability=resolver_input.evidence_availability,
            adapter_profile=resolver_input.adapter_profile,
            legacy_format=resolver_input.legacy_format,
            query_occurrence_reference=resolver_input.query_occurrence_reference,
            ambiguous_candidate_count=2,
        )
        manifest = resolve_opaque(ambiguous)
        self.assertEqual(manifest.resolver_result, ResolverResultV2.ERROR)
        self.assertEqual(manifest.resolution_detail, ResolutionDetailV2.AMBIGUOUS_MATCH)

    def test_unsupported_source_profile(self) -> None:
        manifest = resolve_opaque(unsupported_resolver_input())
        self.assertEqual(manifest.resolver_result, ResolverResultV2.ERROR)
        self.assertEqual(
            manifest.resolution_detail, ResolutionDetailV2.UNSUPPORTED_SOURCE_PROFILE
        )

    def test_wrong_source_instance(self) -> None:
        resolver_input = crush_resolver_input()
        mutated = ResolverInputV2(
            construct_freeze_digest=resolver_input.construct_freeze_digest,
            evidence_seal=resolver_input.evidence_seal,
            evidence_availability=resolver_input.evidence_availability,
            adapter_profile=resolver_input.adapter_profile,
            legacy_format=resolver_input.legacy_format,
            query_occurrence_reference=resolver_input.query_occurrence_reference,
            observed_physical_instance_id="wrong-instance",
        )
        manifest = resolve_opaque(mutated)
        self.assertEqual(manifest.resolution_detail, ResolutionDetailV2.WRONG_SOURCE_INSTANCE)

    def test_wrong_revision_asof(self) -> None:
        resolver_input = crush_resolver_input()
        mutated = ResolverInputV2(
            construct_freeze_digest=resolver_input.construct_freeze_digest,
            evidence_seal=resolver_input.evidence_seal,
            evidence_availability=resolver_input.evidence_availability,
            adapter_profile=resolver_input.adapter_profile,
            legacy_format=resolver_input.legacy_format,
            query_occurrence_reference=resolver_input.query_occurrence_reference,
            observed_revision_or_asof_id="rev-wrong",
        )
        manifest = resolve_opaque(mutated)
        self.assertEqual(manifest.resolution_detail, ResolutionDetailV2.WRONG_REVISION_ASOF)

    def test_hash_mismatch(self) -> None:
        resolver_input = crush_resolver_input()
        mutated = ResolverInputV2(
            construct_freeze_digest=resolver_input.construct_freeze_digest,
            evidence_seal=resolver_input.evidence_seal,
            evidence_availability=resolver_input.evidence_availability,
            adapter_profile=resolver_input.adapter_profile,
            legacy_format=resolver_input.legacy_format,
            query_occurrence_reference=resolver_input.query_occurrence_reference,
            observed_canonical_content_digest=ALT_DIGEST,
        )
        manifest = resolve_opaque(mutated)
        self.assertEqual(manifest.resolution_detail, ResolutionDetailV2.HASH_MISMATCH)

    def test_input_mutation_rejects_binding(self) -> None:
        resolver_input = crush_resolver_input()
        first = resolve_opaque(resolver_input)
        avail = copy.deepcopy(resolver_input.evidence_availability)
        avail_dict = avail.to_dict()
        avail_dict["evidence_seal_digest"] = ALT_DIGEST
        from eval_naturalistic.v2.contracts import EvidenceAvailabilityManifestV2

        mutated_avail = EvidenceAvailabilityManifestV2.from_dict(avail_dict)
        mutated_input = ResolverInputV2(
            construct_freeze_digest=resolver_input.construct_freeze_digest,
            evidence_seal=resolver_input.evidence_seal,
            evidence_availability=mutated_avail,
            adapter_profile=resolver_input.adapter_profile,
            legacy_format=resolver_input.legacy_format,
            query_occurrence_reference=resolver_input.query_occurrence_reference,
        )
        manifest = resolve_opaque(mutated_input)
        self.assertEqual(manifest.resolution_detail, ResolutionDetailV2.INPUT_MUTATION)
        self.assertNotEqual(first.resolver_input_digest, manifest.resolver_input_digest)

    def test_implementation_digest_mismatch(self) -> None:
        resolver_input = crush_resolver_input()
        manifest = resolve_opaque(resolver_input)
        with self.assertRaises(StructuralContractError):
            verify_opaque_resolver_manifest(
                manifest,
                resolver_input=resolver_input,
                expected_implementation_digest=ALT_DIGEST,
            )

    def test_output_digest_mismatch(self) -> None:
        resolver_input = crush_resolver_input()
        manifest = resolve_opaque(resolver_input)
        body = manifest.authority_body_for_digest()
        body["resolver_result"] = ResolverResultV2.NO_MATCH.value
        bad_digest = compute_resolver_output_digest(body)
        from eval_naturalistic.v2.resolver_contracts import OpaqueResolverManifestV2

        bad = OpaqueResolverManifestV2(
            header=manifest.header,
            evidence_seal_digest=manifest.evidence_seal_digest,
            resolver_implementation_digest=manifest.resolver_implementation_digest,
            resolver_input_digest=manifest.resolver_input_digest,
            resolver_result=manifest.resolver_result,
            capability_vector=manifest.capability_vector,
            resolver_output_digest=bad_digest,
            preserved_source_presence=manifest.preserved_source_presence,
            resolution_detail=manifest.resolution_detail,
        )
        with self.assertRaises(StructuralContractError):
            verify_opaque_resolver_manifest(bad, resolver_input=resolver_input)

    def test_deterministic_identical_output(self) -> None:
        resolver_input = crush_resolver_input()
        first = resolve_opaque(resolver_input)
        second = resolve_opaque(resolver_input)
        self.assertEqual(first.resolver_output_digest, second.resolver_output_digest)
        self.assertEqual(first.resolver_input_digest, second.resolver_input_digest)
        self.assertEqual(first.to_dict(), second.to_dict())

    def test_locator_hash_fallback_rejected(self) -> None:
        resolver_input = crush_resolver_input()
        mutated = ResolverInputV2(
            construct_freeze_digest=resolver_input.construct_freeze_digest,
            evidence_seal=resolver_input.evidence_seal,
            evidence_availability=resolver_input.evidence_availability,
            adapter_profile=resolver_input.adapter_profile,
            legacy_format=resolver_input.legacy_format,
            query_occurrence_reference=resolver_input.query_occurrence_reference,
            allow_hash_locator_fallback=True,
        )
        manifest = resolve_opaque(mutated)
        self.assertEqual(
            manifest.resolution_detail, ResolutionDetailV2.LOCATOR_HASH_FALLBACK_REJECTED
        )

    def test_resolver_cannot_create_target_authority(self) -> None:
        manifest = resolve_opaque(crush_resolver_input())
        payload = manifest.to_dict()
        for forbidden in (
            "registry_membership",
            "target_census",
            "discovered_targets",
        ):
            self.assertNotIn(forbidden, payload)

    def test_p1_rejects_resolver_result(self) -> None:
        body = sample_seal_manifest().to_dict()
        body["resolver_result"] = "EXACT_MATCH"
        with self.assertRaises(StructuralContractError):
            parse_evidence_seal_manifest_v2(body)

    def test_p1_rejects_capability_vector(self) -> None:
        body = sample_seal_manifest().to_dict()
        body["capability_vector"] = profile_for_legacy_format("sqlite_crush").capability_vector.to_dict()
        with self.assertRaises(StructuralContractError):
            parse_evidence_seal_manifest_v2(body)

    def test_p1_rejects_known_aliases(self) -> None:
        for alias in ("resolverResult", "resolver-result", "capabilityVector", "capability-vector"):
            body = sample_seal_manifest().to_dict()
            body[alias] = "x"
            with self.assertRaises(StructuralContractError):
                parse_evidence_seal_manifest_v2(body)
            self.assertIn(
                canonicalize_field_name(alias),
                {"resolver_result", "capability_vector"},
            )

    def test_unknown_alias_fails_closed(self) -> None:
        body = sample_seal_manifest().to_dict()
        body["custom_resolver_output"] = "x"
        with self.assertRaises(StructuralContractError):
            reject_p2_fields_on_p1(body, label="EvidenceSealManifestV2")

    def test_p1_unchanged_by_running_p2(self) -> None:
        seal = sample_seal_manifest()
        before = copy.deepcopy(seal.to_dict())
        resolve_opaque(crush_resolver_input())
        after = seal.to_dict()
        self.assertTrue(p1_payload_unchanged_by_p2_scan(before, after))

    def test_issue_263_preserved_on_resolver_failure(self) -> None:
        manifest = resolve_opaque(unsupported_resolver_input())
        self.assertEqual(manifest.preserved_source_presence, SourcePresenceV2.PRESENT)
        self.assertEqual(manifest.resolver_result, ResolverResultV2.ERROR)

    def test_issue_263_evidence_unavailable_not_absent(self) -> None:
        manifest = resolve_opaque(
            crush_resolver_input(
                verbatim=VerbatimEvidenceAvailabilityV2.UNAVAILABLE,
                summary=SummaryEvidenceAvailabilityV2.UNAVAILABLE,
            )
        )
        self.assertEqual(manifest.resolver_result, ResolverResultV2.EVIDENCE_UNAVAILABLE)
        self.assertEqual(manifest.preserved_source_presence, SourcePresenceV2.PRESENT)

    def test_input_digest_changes_with_mutation(self) -> None:
        base = crush_resolver_input()
        other = crush_resolver_input(
            verbatim=VerbatimEvidenceAvailabilityV2.UNAVAILABLE,
            summary=SummaryEvidenceAvailabilityV2.AVAILABLE,
        )
        self.assertNotEqual(
            compute_resolver_input_digest(base),
            compute_resolver_input_digest(other),
        )

    def test_implementation_digest_stable(self) -> None:
        self.assertEqual(len(resolver_implementation_digest()), 64)
        self.assertEqual(
            resolver_implementation_digest(),
            resolver_implementation_digest(),
        )


PRE_CORRECTIVE_RESOLVER_IMPLEMENTATION_ID = "v2/opaque-resolver/1"


def _pre_corrective_implementation_digest() -> str:
    payload = {
        "implementation_id": PRE_CORRECTIVE_RESOLVER_IMPLEMENTATION_ID,
        "read_only": True,
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()


class NaturalisticV2ResolverSummaryBindingCorrectiveTests(unittest.TestCase):
    def _profile_with_completeness(
        self, completeness: EvidenceCompletenessCapability
    ) -> EvidenceAdapterProfileV2:
        profile = profile_for_legacy_format("sqlite_crush")
        vector = profile.capability_vector.with_overrides(
            evidence_completeness=completeness.value
        )
        return profile.with_capability_vector(vector)

    def test_summary_only_complete_to_partial_known(self) -> None:
        manifest = resolve_opaque(
            summary_only_resolver_input(
                self._profile_with_completeness(EvidenceCompletenessCapability.COMPLETE)
            )
        )
        self.assertEqual(manifest.resolver_result, ResolverResultV2.SUMMARY_ONLY)
        self.assertEqual(
            manifest.capability_vector.evidence_completeness,
            EvidenceCompletenessCapability.PARTIAL_KNOWN,
        )

    def test_summary_only_partial_known_stays_partial_known(self) -> None:
        manifest = resolve_opaque(
            summary_only_resolver_input(
                self._profile_with_completeness(EvidenceCompletenessCapability.PARTIAL_KNOWN)
            )
        )
        self.assertEqual(
            manifest.capability_vector.evidence_completeness,
            EvidenceCompletenessCapability.PARTIAL_KNOWN,
        )

    def test_summary_only_unknown_stays_unknown(self) -> None:
        manifest = resolve_opaque(
            summary_only_resolver_input(
                self._profile_with_completeness(EvidenceCompletenessCapability.UNKNOWN)
            )
        )
        self.assertEqual(
            manifest.capability_vector.evidence_completeness,
            EvidenceCompletenessCapability.UNKNOWN,
        )

    def test_summary_only_missing_stays_missing(self) -> None:
        manifest = resolve_opaque(
            summary_only_resolver_input(
                self._profile_with_completeness(EvidenceCompletenessCapability.MISSING)
            )
        )
        self.assertEqual(
            manifest.capability_vector.evidence_completeness,
            EvidenceCompletenessCapability.MISSING,
        )

    def test_opencode_schema_drift_no_longer_promotes_unknown(self) -> None:
        drift = opencode_sqlite_profile_schema_drift("opencode.message.part.v99")
        manifest = resolve_opaque(summary_only_resolver_input(drift, legacy_format="sqlite_opencode"))
        self.assertEqual(manifest.resolver_result, ResolverResultV2.SUMMARY_ONLY)
        self.assertEqual(
            manifest.capability_vector.evidence_completeness,
            EvidenceCompletenessCapability.UNKNOWN,
        )

    def test_registered_profiles_non_regression(self) -> None:
        exact = resolve_opaque(crush_resolver_input(legacy_format="sqlite_crush"))
        self.assertEqual(exact.resolver_result, ResolverResultV2.EXACT_MATCH)

        summary_crush = resolve_opaque(
            summary_only_resolver_input(profile_for_legacy_format("sqlite_crush"))
        )
        self.assertEqual(summary_crush.resolver_result, ResolverResultV2.SUMMARY_ONLY)
        self.assertEqual(
            summary_crush.capability_vector.evidence_completeness,
            EvidenceCompletenessCapability.PARTIAL_KNOWN,
        )

        for legacy_format in ("sqlite_opencode", "jsonl_cursor", "aider_markdown"):
            manifest = resolve_opaque(
                summary_only_resolver_input(
                    profile_for_legacy_format(legacy_format),
                    legacy_format=legacy_format,
                )
            )
            self.assertEqual(manifest.resolver_result, ResolverResultV2.SUMMARY_ONLY)

    def test_implementation_digest_changed_from_pre_corrective(self) -> None:
        self.assertNotEqual(
            resolver_implementation_digest(),
            _pre_corrective_implementation_digest(),
        )

    def test_stale_implementation_digest_fails_closed(self) -> None:
        manifest = resolve_opaque(crush_resolver_input())
        with self.assertRaises(StructuralContractError):
            verify_opaque_resolver_manifest(
                manifest,
                resolver_input=crush_resolver_input(),
                expected_implementation_digest=_pre_corrective_implementation_digest(),
            )

    def test_summary_binding_deterministic(self) -> None:
        resolver_input = summary_only_resolver_input(
            self._profile_with_completeness(EvidenceCompletenessCapability.UNKNOWN)
        )
        first = resolve_opaque(resolver_input)
        second = resolve_opaque(resolver_input)
        self.assertEqual(first.resolver_output_digest, second.resolver_output_digest)


if __name__ == "__main__":
    unittest.main()

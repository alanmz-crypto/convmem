"""Adversarial tests for the V2-03C opaque resolver authority boundary."""

# The setup mirrors the preceding V2 authority tests so each attack remains
# independently readable at this boundary.
# pylint: disable=duplicate-code

from __future__ import annotations

import copy
import hashlib
import unittest
from dataclasses import replace

from eval_naturalistic.adjudication import build_evidence_adjudication_view
from eval_naturalistic.adjudication_fixtures import make_synthetic_adjudication_chain
from eval_naturalistic.base import StructuralContractError, strip_digest_metadata
from eval_naturalistic.digest import canonical_artifact_bytes
from eval_naturalistic.v2.adapters.capability_manifest import (
    SealedCapabilityManifestV2,
    derive_capability_manifest,
)
from eval_naturalistic.v2.authority_issuance import SealedP1AuthorityV2
from eval_naturalistic.v2.contracts import EvidenceSealManifestV2
from eval_naturalistic.v2.evidence import (
    SummaryEvidenceAvailabilityV2,
    VerbatimEvidenceAvailabilityV2,
)
from eval_naturalistic.v2.resolver import (
    RESOLVER_ARTIFACT_KIND,
    RESOLVER_IMPLEMENTATION_ID,
    ResolverResultV2,
    compute_resolver_implementation_digest,
    parse_opaque_resolver_manifest_v2,
    resolve_opaque_occurrence,
    trusted_resolver_implementation_identity,
    verify_opaque_resolver_manifest,
)
from eval_naturalistic.v2.adapters.registry import profile_for_legacy_format
from tests.fixtures.naturalistic_v2_p1 import (
    sample_availability,
    sample_sealed_authority_bundle,
)


class NaturalisticV2ResolverAuthorityTests(unittest.TestCase):
    def _bundle(self, **kwargs):
        kwargs.setdefault(
            "adapter_implementation_digest",
            profile_for_legacy_format("sqlite_crush").adapter_implementation_digest,
        )
        p1, p0, issuance = sample_sealed_authority_bundle(**kwargs)
        capability = derive_capability_manifest(
            p1,
            legacy_format="sqlite_crush",
            p0_repository=p0,
            issuance_repository=issuance,
        )
        resolver = resolve_opaque_occurrence(
            capability,
            p1_authority=p1,
            p0_repository=p0,
            issuance_repository=issuance,
        )
        return p1, p0, issuance, capability, resolver

    @staticmethod
    def _reseal_body(body: dict) -> bytes:
        body = copy.deepcopy(body)
        body["header"]["artifact_id"] = "pending"
        body["header"]["content_digest"] = None
        body["header"]["sealed"] = False
        digest = hashlib.sha256(
            canonical_artifact_bytes(strip_digest_metadata(body))
        ).hexdigest()
        body["header"]["artifact_id"] = f"nps2_{RESOLVER_ARTIFACT_KIND}_{digest}"
        body["header"]["content_digest"] = digest
        body["header"]["sealed"] = True
        return canonical_artifact_bytes(body)

    @staticmethod
    def _verify(resolver, p1, p0, issuance, capability):
        return verify_opaque_resolver_manifest(
            resolver,
            p1_authority=p1,
            capability_authority=capability,
            p0_repository=p0,
            issuance_repository=issuance,
        )

    def test_verified_p1_and_capability_produce_legitimate_resolver(self) -> None:
        p1, p0, issuance, capability, resolver = self._bundle()
        manifest = resolver.manifest
        self.assertEqual(manifest.p1_authority_digest, p1.manifest.header.content_digest)
        self.assertEqual(
            manifest.capability_manifest_digest,
            capability.manifest.header.content_digest,
        )
        self.assertEqual(
            manifest.occurrence_reference.to_dict(),
            capability.manifest.occurrence_reference.to_dict(),
        )
        self.assertEqual(manifest.resolver_result, ResolverResultV2.EXACT_MATCH)
        self.assertIs(self._verify(resolver, p1, p0, issuance, capability), resolver)

    def test_raw_or_fabricated_capability_cannot_issue_resolver(self) -> None:
        p1, p0, issuance, capability, _resolver = self._bundle()
        with self.assertRaises(TypeError):
            resolve_opaque_occurrence(  # type: ignore[arg-type]
                capability.to_dict(),
                p1_authority=p1,
                p0_repository=p0,
                issuance_repository=issuance,
            )

        forged = copy.deepcopy(capability.to_dict())
        forged["capability_vector"]["evidence_completeness"] = "UNKNOWN"
        forged_capability = SealedCapabilityManifestV2.from_canonical_bytes(
            canonical_artifact_bytes(forged)
        )
        with self.assertRaises(StructuralContractError):
            resolve_opaque_occurrence(
                forged_capability,
                p1_authority=p1,
                p0_repository=p0,
                issuance_repository=issuance,
            )

    def test_fabricated_p1_with_consistent_digest_cannot_issue_resolver(self) -> None:
        p1, p0, issuance, capability, _resolver = self._bundle()
        forged = copy.deepcopy(p1.to_dict())
        forged["occurrence_reference"]["physical_source_instance_id"] = "forged-instance"
        forged["occurrence_reference"]["native_record_id"] = "forged-record"
        forged["header"]["artifact_id"] = "pending"
        forged["header"]["content_digest"] = None
        forged["header"]["sealed"] = False
        digest = hashlib.sha256(
            canonical_artifact_bytes(strip_digest_metadata(forged))
        ).hexdigest()
        forged["header"]["artifact_id"] = f"nps2_evidence-seal-manifest-v2_{digest}"
        forged["header"]["content_digest"] = digest
        forged["header"]["sealed"] = True
        forged_manifest = EvidenceSealManifestV2.from_dict(forged)
        forged_p1 = SealedP1AuthorityV2(
            manifest=forged_manifest,
            canonical_bytes=canonical_artifact_bytes(forged_manifest.to_dict()),
            content_digest=digest,
        )
        with self.assertRaises(StructuralContractError):
            resolve_opaque_occurrence(
                capability,
                p1_authority=forged_p1,
                p0_repository=p0,
                issuance_repository=issuance,
            )

    def test_capability_and_resolver_are_bound_to_exact_occurrence(self) -> None:
        p1_a, p0_a, issuance_a, capability_a, resolver_a = self._bundle()
        occurrence_b = replace(
            p1_a.manifest.occurrence_reference,
            occurrence_namespace_id="ns-b",
            physical_source_instance_id="phys-b",
            native_record_id="msg-b",
        )
        p1_b, p0_b, issuance_b, capability_b, _resolver_b = self._bundle(
            occurrence=occurrence_b
        )
        with self.assertRaises(StructuralContractError):
            verify_opaque_resolver_manifest(
                resolver_a,
                p1_authority=p1_b,
                capability_authority=capability_b,
                p0_repository=p0_b,
                issuance_repository=issuance_b,
            )
        with self.assertRaises(StructuralContractError):
            resolve_opaque_occurrence(
                capability_a,
                p1_authority=p1_b,
                p0_repository=p0_b,
                issuance_repository=issuance_b,
            )
        self._verify(resolver_a, p1_a, p0_a, issuance_a, capability_a)

    def test_changed_authority_fields_with_stale_identity_fail_closed(self) -> None:
        p1, p0, issuance, capability, resolver = self._bundle()
        for field, value in (
            ("resolver_input_digest", "b" * 64),
            ("resolver_output_digest", "b" * 64),
            ("resolver_result", "NO_MATCH"),
        ):
            changed = resolver.to_dict()
            changed[field] = value
            with self.assertRaises(StructuralContractError):
                self._verify(changed, p1, p0, issuance, capability)

        changed_vector = resolver.to_dict()
        changed_vector["capability_vector"]["evidence_completeness"] = "UNKNOWN"
        with self.assertRaises(StructuralContractError):
            self._verify(changed_vector, p1, p0, issuance, capability)

    def test_caller_selected_digests_cannot_mint_authority(self) -> None:
        p1, p0, issuance, capability, resolver = self._bundle()
        changed_impl = resolver.to_dict()
        changed_impl["resolver_implementation_digest"] = "b" * 64
        with self.assertRaises(StructuralContractError):
            self._verify(
                self._reseal_body(changed_impl), p1, p0, issuance, capability
            )

        changed_input = resolver.to_dict()
        changed_input["resolver_input_digest"] = "b" * 64
        with self.assertRaises(StructuralContractError):
            self._verify(
                self._reseal_body(changed_input), p1, p0, issuance, capability
            )

        changed_output = resolver.to_dict()
        changed_output["resolver_output_digest"] = "b" * 64
        with self.assertRaises(StructuralContractError):
            self._verify(
                self._reseal_body(changed_output), p1, p0, issuance, capability
            )

    def test_handcrafted_self_consistent_manifest_still_requires_upstream_authority(self) -> None:
        p1, _p0, _issuance, capability, resolver = self._bundle()
        with self.assertRaises(StructuralContractError):
            parse_opaque_resolver_manifest_v2(resolver.canonical_bytes)
        with self.assertRaises(StructuralContractError):
            verify_opaque_resolver_manifest(
                resolver.canonical_bytes,
                p1_authority=p1,
                capability_authority=capability,
                p0_repository=None,
                issuance_repository=None,
            )

    def test_public_reload_rechecks_p1_capability_and_implementation(self) -> None:
        p1, p0, issuance, capability, resolver = self._bundle()
        reloaded = parse_opaque_resolver_manifest_v2(
            resolver.canonical_bytes,
            p1_authority=p1,
            capability_authority=capability,
            p0_repository=p0,
            issuance_repository=issuance,
        )
        self.assertEqual(reloaded.to_dict(), resolver.to_dict())
        self.assertEqual(reloaded.content_digest, resolver.content_digest)
        self.assertEqual(
            reloaded.manifest.resolver_implementation_digest,
            compute_resolver_implementation_digest(),
        )

    def test_unknown_result_and_unknown_nested_authority_fail_closed(self) -> None:
        p1, p0, issuance, capability, resolver = self._bundle()
        unknown_result = resolver.to_dict()
        unknown_result["resolver_output"]["resolver_result"] = "FUTURE_RESULT"
        with self.assertRaises(StructuralContractError):
            verify_opaque_resolver_manifest(
                self._reseal_body(unknown_result),
                p1_authority=p1,
                capability_authority=capability,
                p0_repository=p0,
                issuance_repository=issuance,
            )
        unknown_capability_state = resolver.to_dict()
        unknown_capability_state["capability_vector"]["lineage_assurance"] = "FUTURE"
        with self.assertRaises(StructuralContractError):
            verify_opaque_resolver_manifest(
                self._reseal_body(unknown_capability_state),
                p1_authority=p1,
                capability_authority=capability,
                p0_repository=p0,
                issuance_repository=issuance,
            )

    def test_issue_263_summary_only_preserves_source_presence(self) -> None:
        availability = sample_availability(
            verbatim=VerbatimEvidenceAvailabilityV2.UNAVAILABLE,
            summary=SummaryEvidenceAvailabilityV2.AVAILABLE,
        )
        p1, _p0, _issuance, capability, resolver = self._bundle(availability=availability)
        self.assertEqual(resolver.manifest.resolver_result, ResolverResultV2.SUMMARY_ONLY)
        self.assertEqual(resolver.manifest.resolver_output.source_presence.value, "PRESENT")
        self.assertEqual(
            resolver.manifest.resolver_output.verbatim_evidence_availability,
            VerbatimEvidenceAvailabilityV2.UNAVAILABLE,
        )
        self.assertEqual(
            resolver.manifest.condition_neutral_evidence_availability.source_presence,
            p1.manifest.condition_neutral_evidence_availability.source_presence,
        )
        self.assertEqual(
            capability.manifest.condition_neutral_evidence_availability.source_presence.value,
            "PRESENT",
        )

    def test_issue_263_source_present_verbatim_unavailable_never_becomes_absent(self) -> None:
        availability = sample_availability(
            verbatim=VerbatimEvidenceAvailabilityV2.UNAVAILABLE,
            summary=SummaryEvidenceAvailabilityV2.UNAVAILABLE,
        )
        _p1, _p0, _issuance, _capability, resolver = self._bundle(availability=availability)
        self.assertEqual(
            resolver.manifest.resolver_result,
            ResolverResultV2.EVIDENCE_UNAVAILABLE,
        )
        self.assertEqual(resolver.manifest.resolver_output.source_presence.value, "PRESENT")

    def test_resolver_output_has_no_p3_registry_or_ground_truth_fields(self) -> None:
        _p1, _p0, _issuance, _capability, resolver = self._bundle()
        forbidden = {
            "target_registry",
            "TargetRegistryV2",
            "registry_membership",
            "target_ground_truth",
            "target_census",
            "probe_keys",
            "sampling_membership",
            "adjudication_outcome",
            "duplicate_equivalence",
        }

        def keys(value):
            if isinstance(value, dict):
                for key, child in value.items():
                    yield key
                    yield from keys(child)
            elif isinstance(value, list):
                for child in value:
                    yield from keys(child)

        self.assertFalse(forbidden & set(keys(resolver.manifest.resolver_output.to_dict())))
        self.assertFalse(forbidden & set(keys(resolver.to_dict())))

    def test_adjudication_view_remains_resolver_blind(self) -> None:
        _frame, _episode, evidence, _workflow = make_synthetic_adjudication_chain()
        view = build_evidence_adjudication_view(evidence)
        forbidden = {
            "OpaqueResolverManifestV2",
            "resolver_status",
            "resolver_result",
            "capability_vector",
            "resolver_assurance",
            "resolver_failure_reason",
            "resolver_paths_and_locators",
            "resolver_retry_count_and_timing",
            "resolver_queue_order",
            "resolver_timestamps",
            "resolver_missing_file_signals",
            "resolver_completeness_labels",
            "resolver_derived_metadata",
        }
        self.assertFalse(forbidden & set(view))

    def test_trusted_implementation_is_closed_and_content_bound(self) -> None:
        identity = trusted_resolver_implementation_identity()
        self.assertEqual(identity["resolver_implementation_id"], RESOLVER_IMPLEMENTATION_ID)
        self.assertEqual(
            identity["resolver_implementation_digest"],
            compute_resolver_implementation_digest(),
        )
        self.assertNotEqual(identity["resolver_implementation_digest"], "b" * 64)


if __name__ == "__main__":
    unittest.main()

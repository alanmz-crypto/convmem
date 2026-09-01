"""V2-01 — P1 identity and evidence seal core adversarial tests."""

from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from eval_naturalistic.base import StructuralContractError
from eval_naturalistic.v2.contracts import EvidenceSealManifestV2
from eval_naturalistic.v2.evidence import (
    PostSealSourceStateV2,
    SourcePresenceV2,
    SummaryEvidenceAvailabilityV2,
    VerbatimEvidenceAvailabilityV2,
    normalized_reported_presence,
)
from eval_naturalistic.v2.identity import (
    LineageEdgeV2,
    LineageRelationKind,
    OccurrenceReferenceV2,
    reject_hash_or_locator_identity,
)
from eval_naturalistic.v2.validators import (
    evaluate_post_seal_source_state,
    parse_evidence_availability_manifest_v2,
    parse_evidence_seal_manifest_v2,
    validate_distinct_occurrences,
    validate_duplicate_content_distinct_occurrences,
    validate_lineage_preserves_physical_separation,
    validate_native_id_reuse_is_not_same_occurrence,
    validate_revision_binding,
    RevisionBindingObservationV2,
)
from eval_naturalistic.v2.authority_issuance import IssuanceAuthorityRepository
from eval_naturalistic.v2.lineage_attestation import LineageAttestationRepository
from tests.fixtures.naturalistic_v2_p1 import (
    ALT_DIGEST,
    clone_lineage_edge,
    sample_availability,
    sample_availability_manifest,
    sample_occurrence,
    sample_p0_repository,
    sample_seal_manifest,
    sample_sealed_authority_bundle,
)


class NaturalisticV2P1IdentityTests(unittest.TestCase):
    def test_clone_identity_separation(self) -> None:
        original = sample_occurrence(physical_instance="phys-original", namespace="ns-orig")
        clone = sample_occurrence(physical_instance="phys-clone", namespace="ns-clone")
        repo = LineageAttestationRepository()
        edge = clone_lineage_edge(
            child_occurrence=clone,
            parent_occurrence=original,
            from_instance="phys-original",
            to_instance="phys-clone",
            lineage_repository=repo,
        )
        validate_distinct_occurrences(original, clone, context="clone")
        validate_lineage_preserves_physical_separation([edge])
        self.assertNotEqual(original.identity_key(), clone.identity_key())

    def test_restore_identity_separation(self) -> None:
        backup = sample_occurrence(physical_instance="phys-live", revision="rev-live")
        restored = sample_occurrence(physical_instance="phys-restored", revision="rev-live")
        validate_distinct_occurrences(backup, restored, context="restore")
        self.assertEqual(
            backup.native_record_identity(), restored.native_record_identity()
        )

    def test_native_id_reuse_across_instances(self) -> None:
        first = sample_occurrence(physical_instance="inst-1", native_record="same-id")
        second = sample_occurrence(physical_instance="inst-2", native_record="same-id")
        validate_native_id_reuse_is_not_same_occurrence(first, second)
        validate_distinct_occurrences(first, second, context="native-id reuse")

    def test_duplicate_content_distinct_occurrences(self) -> None:
        left = sample_seal_manifest(
            occurrence=sample_occurrence(physical_instance="phys-1", namespace="ns-1")
        )
        right = sample_seal_manifest(
            occurrence=sample_occurrence(physical_instance="phys-2", namespace="ns-2")
        )
        validate_duplicate_content_distinct_occurrences(left, right)

    def test_provider_edit_vs_delete_recreate(self) -> None:
        edited = sample_occurrence(
            physical_instance="phys-live", native_record="msg-9", revision="rev-2"
        )
        prior = sample_occurrence(
            physical_instance="phys-live", native_record="msg-9", revision="rev-1"
        )
        self.assertFalse(edited.same_occurrence_as(prior))
        recreated = sample_occurrence(
            physical_instance="phys-new", native_record="msg-9", revision="rev-1"
        )
        validate_distinct_occurrences(prior, recreated, context="delete/recreate")

    def test_revision_asof_mismatch_fails_closed(self) -> None:
        manifest = sample_seal_manifest()
        with self.assertRaises(StructuralContractError):
            validate_revision_binding(
                manifest,
                RevisionBindingObservationV2(
                    revision_or_asof_id="rev-wrong",
                    physical_instance_id=manifest.physical_instance_id,
                ),
            )

    def test_source_mutation_after_evidence_seal(self) -> None:
        decision = evaluate_post_seal_source_state(
            capture_obligation_satisfied=True,
            capture_time_occurrence_revision_match=True,
            preserved_package_integrity=True,
            post_seal_source_state=PostSealSourceStateV2.MODIFIED,
        )
        self.assertEqual(
            decision.result,
            "VALID_ASOF_SEALED_EVIDENCE_WITH_SOURCE_DRIFT_DIAGNOSTIC",
        )

    def test_source_deletion_after_valid_seal(self) -> None:
        decision = evaluate_post_seal_source_state(
            capture_obligation_satisfied=True,
            capture_time_occurrence_revision_match=True,
            preserved_package_integrity=True,
            post_seal_source_state=PostSealSourceStateV2.DELETED,
        )
        self.assertEqual(
            decision.result,
            "VALID_ASOF_SEALED_EVIDENCE_WITH_SOURCE_DELETION_DIAGNOSTIC",
        )

    def test_hash_locator_only_identity_rejected(self) -> None:
        with self.assertRaises(StructuralContractError):
            reject_hash_or_locator_identity({"content_digest": "a" * 64, "locator": "/tmp/x"})
        with self.assertRaises(StructuralContractError):
            OccurrenceReferenceV2.from_dict(
                {
                    "content_digest": "a" * 64,
                    "source_system_id": "sys",
                    "tenant_or_realm_id": "t",
                    "authority_scope_id": "a",
                    "occurrence_namespace_id": "n",
                    "physical_source_instance_id": "p",
                    "native_id_namespace": "ns",
                    "native_record_id": "r",
                    "source_revision_or_asof_id": "rev",
                }
            )

    def test_source_present_verbatim_unavailable_not_absent(self) -> None:
        availability = sample_availability(
            presence=SourcePresenceV2.PRESENT,
            verbatim=VerbatimEvidenceAvailabilityV2.UNAVAILABLE,
            summary=SummaryEvidenceAvailabilityV2.UNAVAILABLE,
        )
        self.assertEqual(
            normalized_reported_presence(availability), SourcePresenceV2.PRESENT
        )

    def test_summary_available_verbatim_unavailable(self) -> None:
        availability = sample_availability(
            presence=SourcePresenceV2.PRESENT,
            verbatim=VerbatimEvidenceAvailabilityV2.UNAVAILABLE,
            summary=SummaryEvidenceAvailabilityV2.AVAILABLE,
        )
        availability.validate_issue_263()
        sealed, p0_repo, issuance_repo = sample_sealed_authority_bundle(availability=availability)
        parsed = parse_evidence_seal_manifest_v2(
            sealed.manifest.to_dict(),
            p0_repository=p0_repo,
            issuance_repository=issuance_repo,
        )
        self.assertEqual(
            parsed.condition_neutral_evidence_availability.summary_evidence_availability,
            SummaryEvidenceAvailabilityV2.AVAILABLE,
        )

    def test_malformed_incomplete_identity_tuple(self) -> None:
        sealed, p0_repo, issuance_repo = sample_sealed_authority_bundle()
        body = sealed.manifest.to_dict()
        del body["occurrence_reference"]["native_record_id"]
        with self.assertRaises(StructuralContractError):
            parse_evidence_seal_manifest_v2(
                body, p0_repository=p0_repo, issuance_repository=issuance_repo
            )

    def test_unknown_fields_fail_closed(self) -> None:
        sealed, p0_repo, issuance_repo = sample_sealed_authority_bundle()
        body = sealed.manifest.to_dict()
        body["resolver_result"] = "EXACT_MATCH"
        with self.assertRaises(StructuralContractError):
            parse_evidence_seal_manifest_v2(
                body, p0_repository=p0_repo, issuance_repository=issuance_repo
            )
        body = sealed.manifest.to_dict()
        body["unexpected_field"] = "x"
        with self.assertRaises(StructuralContractError):
            parse_evidence_seal_manifest_v2(
                body, p0_repository=p0_repo, issuance_repository=issuance_repo
            )

    def test_v1_schema_not_accepted_as_v2_seal(self) -> None:
        sealed, p0_repo, issuance_repo = sample_sealed_authority_bundle()
        body = sealed.manifest.to_dict()
        body["header"] = copy.deepcopy(body["header"])
        body["header"]["schema_version"] = "convmem/naturalistic/raw-evidence-manifest-v1"
        with self.assertRaises(StructuralContractError):
            parse_evidence_seal_manifest_v2(
                body, p0_repository=p0_repo, issuance_repository=issuance_repo
            )

    def test_availability_manifest_binds_to_seal(self) -> None:
        seal = sample_seal_manifest()
        avail = sample_availability_manifest(seal)
        parsed = parse_evidence_availability_manifest_v2(avail.to_dict(), seal=seal)
        self.assertTrue(
            parsed.occurrence_reference.same_occurrence_as(seal.occurrence_reference)
        )

    def test_lineage_cannot_collapse_physical_instances(self) -> None:
        original = sample_occurrence(physical_instance="same")
        clone = sample_occurrence(physical_instance="same", namespace="ns-clone")
        repo = LineageAttestationRepository()
        good_edge = clone_lineage_edge(
            child_occurrence=clone,
            parent_occurrence=original,
            from_instance="same",
            to_instance="same",
            lineage_repository=repo,
        )
        bad_edge = LineageEdgeV2(
            logical_lineage_id=good_edge.logical_lineage_id,
            from_physical_instance_id="same",
            to_physical_instance_id="same",
            relation_kind=LineageRelationKind.RESTORE,
            issuer_attested=True,
            child_occurrence_digest=ALT_DIGEST,
            parent_occurrence_digest=ALT_DIGEST,
            attestation_evidence_digest=ALT_DIGEST,
        )
        with self.assertRaises(StructuralContractError):
            validate_lineage_preserves_physical_separation([bad_edge])

    def test_duplicate_digest_different_occurrences_allowed(self) -> None:
        left = sample_seal_manifest(
            occurrence=sample_occurrence(physical_instance="p1"),
            canonical_content_digest=ALT_DIGEST,
        )
        right = sample_seal_manifest(
            occurrence=sample_occurrence(physical_instance="p2"),
            canonical_content_digest=ALT_DIGEST,
        )
        validate_duplicate_content_distinct_occurrences(left, right)


if __name__ == "__main__":
    unittest.main()

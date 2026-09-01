"""V2-01C second corrective — source-backed authority adversarial tests."""

from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from eval_naturalistic.base import StructuralContractError
from eval_naturalistic.v2.authority_issuance import (
    EvidenceSealManifestDraftV2,
    ImmediateParentBindingV2,
    IssuedOccurrenceReferenceV2,
    _ISSUED_REFERENCE_TOKEN,
    clear_p1_issuer_revision_cache,
    compute_p1_issuer_implementation_revision,
    issue_occurrence_reference,
    verify_sealed_p1_authority,
)
from eval_naturalistic.v2.contracts import EvidenceSealManifestV2, _ISSUANCE_TOKEN
from eval_naturalistic.v2.identity import LineageEdgeV2, LineageRelationKind, OccurrenceReferenceV2
from eval_naturalistic.v2.lineage_attestation import (
    LineageAttestationRepository,
    occurrence_commitment_digest,
    seal_lineage_attestation,
)
from eval_naturalistic.v2.p0_construct import (
    InMemoryConstructFreezeRepository,
    seal_construct_freeze_manifest,
)
from eval_naturalistic.v2.source_authority import (
    VerifiedSourceAuthorityV2,
    seal_source_capture_package,
    verify_source_capture_authority,
)
from tests.fixtures.naturalistic_v2_p1 import (
    ALT_DIGEST,
    CREATED_AT,
    FIXED_DIGEST,
    SEAL_TIME,
    build_source_capture_body,
    clone_lineage_edge,
    construct_freeze_content_digest,
    sample_availability,
    sample_construct_parent,
    sample_occurrence,
    sample_p0_repository,
    sample_sealed_authority,
    sample_verified_source_authority,
)


class SourceBackedAuthorityAdversarialTests(unittest.TestCase):
    def test_positive_verified_source_issues_occurrence_authority(self) -> None:
        authority = sample_verified_source_authority()
        issued = issue_occurrence_reference(authority)
        self.assertEqual(
            issued.occurrence_reference.physical_source_instance_id,
            "phys-a",
        )
        self.assertEqual(issued.source_authority_digest, authority.authority_record_digest)

    def test_positive_physical_incarnation_preserved(self) -> None:
        authority = sample_verified_source_authority(physical_instance="phys-unique")
        issued = issue_occurrence_reference(authority)
        self.assertEqual(
            issued.occurrence_reference.physical_source_instance_id,
            "phys-unique",
        )

    def test_positive_p0_parent_independently_verified(self) -> None:
        repo = sample_p0_repository()
        sealed = sample_sealed_authority(p0_repository=repo)
        verify_sealed_p1_authority(sealed, p0_repository=repo)

    def test_positive_lineage_attestation_resolves(self) -> None:
        child = sample_occurrence(physical_instance="child")
        parent = sample_occurrence(physical_instance="parent", namespace="ns-parent")
        lineage_repo = LineageAttestationRepository()
        edge = clone_lineage_edge(
            child_occurrence=child,
            parent_occurrence=parent,
            from_instance="parent",
            to_instance="child",
            lineage_repository=lineage_repo,
        )
        p0_repo = sample_p0_repository()
        sealed = sample_sealed_authority(
            p0_repository=p0_repo,
            lineage_edges=[edge],
            lineage_repository=lineage_repo,
            occurrence=child,
        )
        verify_sealed_p1_authority(
            sealed,
            p0_repository=p0_repo,
            lineage_repository=lineage_repo,
        )

    def test_positive_canonical_sealed_bytes_verify(self) -> None:
        sealed = sample_sealed_authority()
        reparsed = verify_sealed_p1_authority(sealed.to_dict())
        self.assertEqual(sealed.content_digest, reparsed.content_digest)

    def test_positive_expected_implementation_revision_enforced(self) -> None:
        sealed = sample_sealed_authority()
        self.assertEqual(
            sealed.manifest.issuer_implementation_revision,
            compute_p1_issuer_implementation_revision(),
        )

    def test_negative_arbitrary_strings_without_source_authority(self) -> None:
        with self.assertRaises(TypeError):
            issue_occurrence_reference("not-a-verified-authority")  # type: ignore[arg-type]

    def test_negative_fabricated_physical_instance(self) -> None:
        with self.assertRaises(TypeError):
            VerifiedSourceAuthorityV2(
                source_capture_digest=FIXED_DIGEST,
                occurrence_reference=sample_occurrence(physical_instance="fabricated"),
                evidence_snapshot_id="snap",
                issuer_capture_attestation="issuer",
                authority_record_digest=FIXED_DIGEST,
            )

    def test_negative_fabricated_revision(self) -> None:
        with self.assertRaises(TypeError):
            VerifiedSourceAuthorityV2(
                _token=object(),
                source_capture_digest=FIXED_DIGEST,
                occurrence_reference=sample_occurrence(revision="fabricated-rev"),
                evidence_snapshot_id="snap",
                issuer_capture_attestation="issuer",
                authority_record_digest=FIXED_DIGEST,
            )

    def test_negative_fabricated_snapshot_id(self) -> None:
        with self.assertRaises(TypeError):
            VerifiedSourceAuthorityV2(
                _token=object(),
                source_capture_digest=FIXED_DIGEST,
                occurrence_reference=sample_occurrence(),
                evidence_snapshot_id="fabricated-snap",
                issuer_capture_attestation="issuer",
                authority_record_digest=FIXED_DIGEST,
            )

    def test_negative_arbitrary_attestation_digest_without_artifact(self) -> None:
        child = sample_occurrence(physical_instance="child")
        parent = sample_occurrence(physical_instance="parent", namespace="ns-p")
        edge = LineageEdgeV2(
            logical_lineage_id="lineage-1",
            from_physical_instance_id="parent",
            to_physical_instance_id="child",
            relation_kind=LineageRelationKind.CLONE,
            issuer_attested=True,
            child_occurrence_digest=occurrence_commitment_digest(child),
            parent_occurrence_digest=occurrence_commitment_digest(parent),
            attestation_evidence_digest=ALT_DIGEST,
        )
        p0_repo = sample_p0_repository()
        construct_digest = construct_freeze_content_digest(p0_repo)
        issued = issue_occurrence_reference(sample_verified_source_authority())
        draft = EvidenceSealManifestDraftV2(
            construct_freeze_digest=construct_digest,
            episode_id="episode-1",
            issued_occurrence=issued,
            evidence_complete_envelope_digest=FIXED_DIGEST,
            canonical_content_digest=FIXED_DIGEST,
            canonicalization_profile_digest=FIXED_DIGEST,
            adapter_implementation_digest=FIXED_DIGEST,
            condition_neutral_evidence_availability=sample_availability(),
            immediate_parents=(sample_construct_parent(p0_repo),),
            responsible_role="evidence_capture",
            created_at=CREATED_AT,
            lineage_edges=[edge],
        )
        with self.assertRaises(StructuralContractError):
            draft.finalize_and_seal(
                seal_time=SEAL_TIME,
                p0_repository=p0_repo,
                lineage_repository=LineageAttestationRepository(),
            )

    def test_negative_direct_issued_reference_construction(self) -> None:
        with self.assertRaises(TypeError):
            IssuedOccurrenceReferenceV2(
                occurrence_reference=sample_occurrence(),
                issuance_digest=FIXED_DIGEST,
                issuer_implementation_revision="rev",
                evidence_snapshot_id="snap",
                source_authority_digest=FIXED_DIGEST,
            )

    def test_negative_imported_issuance_token_reuse(self) -> None:
        forged = IssuedOccurrenceReferenceV2(
            _token=_ISSUED_REFERENCE_TOKEN,
            occurrence_reference=sample_occurrence(),
            issuance_digest=FIXED_DIGEST,
            issuer_implementation_revision=compute_p1_issuer_implementation_revision(),
            evidence_snapshot_id="snap-1",
            source_authority_digest=FIXED_DIGEST,
        )
        p0_repo = sample_p0_repository()
        construct_digest = construct_freeze_content_digest(p0_repo)
        draft = EvidenceSealManifestDraftV2(
            construct_freeze_digest=construct_digest,
            episode_id="episode-1",
            issued_occurrence=forged,
            evidence_complete_envelope_digest=FIXED_DIGEST,
            canonical_content_digest=FIXED_DIGEST,
            canonicalization_profile_digest=FIXED_DIGEST,
            adapter_implementation_digest=FIXED_DIGEST,
            condition_neutral_evidence_availability=sample_availability(),
            immediate_parents=(sample_construct_parent(p0_repo),),
            responsible_role="evidence_capture",
            created_at=CREATED_AT,
        )
        with self.assertRaises(StructuralContractError):
            draft.finalize_and_seal(seal_time=SEAL_TIME, p0_repository=p0_repo)

    def test_negative_fabricated_self_consistent_p1_round_trip(self) -> None:
        p0_repo = sample_p0_repository()
        sealed = sample_sealed_authority(p0_repository=p0_repo)
        data = sealed.to_dict()
        data["episode_id"] = "forged-episode"
        with self.assertRaises(StructuralContractError):
            verify_sealed_p1_authority(data, p0_repository=p0_repo)

    def test_negative_nonexistent_parent_with_consistent_digest(self) -> None:
        p0_repo = InMemoryConstructFreezeRepository()
        issued = issue_occurrence_reference(sample_verified_source_authority())
        parent = ImmediateParentBindingV2(
            parent_kind="construct_freeze",
            parent_artifact_id=f"nps2_construct-freeze-manifest-v2_{FIXED_DIGEST}",
            parent_digest=FIXED_DIGEST,
        )
        draft = EvidenceSealManifestDraftV2(
            construct_freeze_digest=FIXED_DIGEST,
            episode_id="episode-1",
            issued_occurrence=issued,
            evidence_complete_envelope_digest=FIXED_DIGEST,
            canonical_content_digest=FIXED_DIGEST,
            canonicalization_profile_digest=FIXED_DIGEST,
            adapter_implementation_digest=FIXED_DIGEST,
            condition_neutral_evidence_availability=sample_availability(),
            immediate_parents=(parent,),
            responsible_role="evidence_capture",
            created_at=CREATED_AT,
        )
        with self.assertRaises(StructuralContractError):
            draft.finalize_and_seal(seal_time=SEAL_TIME, p0_repository=p0_repo)

    def test_negative_duplicate_construct_freeze_parents(self) -> None:
        p0_repo = sample_p0_repository()
        construct_digest = construct_freeze_content_digest(p0_repo)
        parent = sample_construct_parent(p0_repo)
        issued = issue_occurrence_reference(sample_verified_source_authority())
        draft = EvidenceSealManifestDraftV2(
            construct_freeze_digest=construct_digest,
            episode_id="episode-1",
            issued_occurrence=issued,
            evidence_complete_envelope_digest=FIXED_DIGEST,
            canonical_content_digest=FIXED_DIGEST,
            canonicalization_profile_digest=FIXED_DIGEST,
            adapter_implementation_digest=FIXED_DIGEST,
            condition_neutral_evidence_availability=sample_availability(),
            immediate_parents=(parent, parent),
            responsible_role="evidence_capture",
            created_at=CREATED_AT,
        )
        with self.assertRaises(StructuralContractError):
            draft.finalize_and_seal(seal_time=SEAL_TIME, p0_repository=p0_repo)

    def test_negative_unknown_extra_authority_parent(self) -> None:
        p0_repo = sample_p0_repository()
        construct_digest = construct_freeze_content_digest(p0_repo)
        issued = issue_occurrence_reference(sample_verified_source_authority())
        draft = EvidenceSealManifestDraftV2(
            construct_freeze_digest=construct_digest,
            episode_id="episode-1",
            issued_occurrence=issued,
            evidence_complete_envelope_digest=FIXED_DIGEST,
            canonical_content_digest=FIXED_DIGEST,
            canonicalization_profile_digest=FIXED_DIGEST,
            adapter_implementation_digest=FIXED_DIGEST,
            condition_neutral_evidence_availability=sample_availability(),
            immediate_parents=(
                sample_construct_parent(p0_repo),
                ImmediateParentBindingV2(
                    parent_kind="unknown_parent",
                    parent_artifact_id="nps2_unknown",
                    parent_digest=ALT_DIGEST,
                ),
            ),
            responsible_role="evidence_capture",
            created_at=CREATED_AT,
        )
        with self.assertRaises(StructuralContractError):
            draft.finalize_and_seal(seal_time=SEAL_TIME, p0_repository=p0_repo)

    def test_negative_parent_artifact_id_inconsistent_with_bytes(self) -> None:
        p0_repo = sample_p0_repository()
        construct_digest = construct_freeze_content_digest(p0_repo)
        manifest = seal_construct_freeze_manifest(
            construct_policy_digest=FIXED_DIGEST,
            study_id="study",
            responsible_role="study_owner",
            created_at=CREATED_AT,
            seal_time=SEAL_TIME,
        )
        p0_repo.register(manifest)
        bad_parent = ImmediateParentBindingV2(
            parent_kind="construct_freeze",
            parent_artifact_id="nps2_wrong_id",
            parent_digest=manifest.header.content_digest or FIXED_DIGEST,
        )
        issued = issue_occurrence_reference(sample_verified_source_authority())
        draft = EvidenceSealManifestDraftV2(
            construct_freeze_digest=construct_digest,
            episode_id="episode-1",
            issued_occurrence=issued,
            evidence_complete_envelope_digest=FIXED_DIGEST,
            canonical_content_digest=FIXED_DIGEST,
            canonicalization_profile_digest=FIXED_DIGEST,
            adapter_implementation_digest=FIXED_DIGEST,
            condition_neutral_evidence_availability=sample_availability(),
            immediate_parents=(bad_parent,),
            responsible_role="evidence_capture",
            created_at=CREATED_AT,
        )
        with self.assertRaises(StructuralContractError):
            draft.finalize_and_seal(seal_time=SEAL_TIME, p0_repository=p0_repo)

    def test_negative_wrong_parent_schema_kind(self) -> None:
        p0_repo = sample_p0_repository()
        issued = issue_occurrence_reference(sample_verified_source_authority())
        parent = ImmediateParentBindingV2(
            parent_kind="construct_freeze",
            parent_artifact_id="nps2_wrong-schema",
            parent_digest=ALT_DIGEST,
        )
        draft = EvidenceSealManifestDraftV2(
            construct_freeze_digest=ALT_DIGEST,
            episode_id="episode-1",
            issued_occurrence=issued,
            evidence_complete_envelope_digest=FIXED_DIGEST,
            canonical_content_digest=FIXED_DIGEST,
            canonicalization_profile_digest=FIXED_DIGEST,
            adapter_implementation_digest=FIXED_DIGEST,
            condition_neutral_evidence_availability=sample_availability(),
            immediate_parents=(parent,),
            responsible_role="evidence_capture",
            created_at=CREATED_AT,
        )
        with self.assertRaises(StructuralContractError):
            draft.finalize_and_seal(seal_time=SEAL_TIME, p0_repository=p0_repo)

    def test_negative_lineage_attestation_no_real_artifact(self) -> None:
        child = sample_occurrence(physical_instance="child")
        parent = sample_occurrence(physical_instance="parent", namespace="ns-p")
        edge = LineageEdgeV2(
            logical_lineage_id="lineage-1",
            from_physical_instance_id="parent",
            to_physical_instance_id="child",
            relation_kind=LineageRelationKind.CLONE,
            issuer_attested=True,
            child_occurrence_digest=occurrence_commitment_digest(child),
            parent_occurrence_digest=occurrence_commitment_digest(parent),
            attestation_evidence_digest=ALT_DIGEST,
        )
        p0_repo = sample_p0_repository()
        construct_digest = construct_freeze_content_digest(p0_repo)
        issued = issue_occurrence_reference(
            verify_source_capture_authority(
                seal_source_capture_package(
                    build_source_capture_body(
                        physical_instance="child",
                        namespace="ns-child",
                    )
                )
            )
        )
        draft = EvidenceSealManifestDraftV2(
            construct_freeze_digest=construct_digest,
            episode_id="episode-1",
            issued_occurrence=issued,
            evidence_complete_envelope_digest=FIXED_DIGEST,
            canonical_content_digest=FIXED_DIGEST,
            canonicalization_profile_digest=FIXED_DIGEST,
            adapter_implementation_digest=FIXED_DIGEST,
            condition_neutral_evidence_availability=sample_availability(),
            immediate_parents=(sample_construct_parent(p0_repo),),
            responsible_role="evidence_capture",
            created_at=CREATED_AT,
            lineage_edges=[edge],
        )
        with self.assertRaises(StructuralContractError):
            draft.finalize_and_seal(
                seal_time=SEAL_TIME,
                p0_repository=p0_repo,
                lineage_repository=LineageAttestationRepository(),
            )

    def test_negative_lineage_attestation_wrong_child_occurrence(self) -> None:
        child = sample_occurrence(physical_instance="child")
        parent = sample_occurrence(physical_instance="parent", namespace="ns-p")
        lineage_repo = LineageAttestationRepository()
        edge = clone_lineage_edge(
            child_occurrence=child,
            parent_occurrence=parent,
            from_instance="parent",
            to_instance="child",
            lineage_repository=lineage_repo,
        )
        wrong_child = sample_occurrence(physical_instance="wrong-child")
        p0_repo = sample_p0_repository()
        construct_digest = construct_freeze_content_digest(p0_repo)
        issued = issue_occurrence_reference(
            verify_source_capture_authority(
                seal_source_capture_package(
                    build_source_capture_body(
                        physical_instance="wrong-child",
                        namespace="ns-wrong",
                    )
                )
            )
        )
        draft = EvidenceSealManifestDraftV2(
            construct_freeze_digest=construct_digest,
            episode_id="episode-1",
            issued_occurrence=issued,
            evidence_complete_envelope_digest=FIXED_DIGEST,
            canonical_content_digest=FIXED_DIGEST,
            canonicalization_profile_digest=FIXED_DIGEST,
            adapter_implementation_digest=FIXED_DIGEST,
            condition_neutral_evidence_availability=sample_availability(),
            immediate_parents=(sample_construct_parent(p0_repo),),
            responsible_role="evidence_capture",
            created_at=CREATED_AT,
            lineage_edges=[edge],
        )
        with self.assertRaises(StructuralContractError):
            draft.finalize_and_seal(
                seal_time=SEAL_TIME,
                p0_repository=p0_repo,
                lineage_repository=lineage_repo,
            )

    def test_negative_lineage_attestation_wrong_parent_occurrence(self) -> None:
        child = sample_occurrence(physical_instance="child")
        parent = sample_occurrence(physical_instance="parent", namespace="ns-p")
        wrong_parent = sample_occurrence(physical_instance="wrong-parent", namespace="ns-wp")
        lineage_repo = LineageAttestationRepository()
        artifact = seal_lineage_attestation(
            logical_lineage_id="lineage-1",
            relation_kind=LineageRelationKind.CLONE,
            child_occurrence=child,
            parent_occurrence=wrong_parent,
            issuer_identity="issuer",
            responsible_role="lineage_issuer",
            created_at=CREATED_AT,
            seal_time=SEAL_TIME,
        )
        lineage_repo.register(artifact)
        edge = LineageEdgeV2(
            logical_lineage_id="lineage-1",
            from_physical_instance_id="parent",
            to_physical_instance_id="child",
            relation_kind=LineageRelationKind.CLONE,
            issuer_attested=True,
            child_occurrence_digest=occurrence_commitment_digest(child),
            parent_occurrence_digest=occurrence_commitment_digest(parent),
            attestation_evidence_digest=artifact.attestation_evidence_digest(),
        )
        p0_repo = sample_p0_repository()
        construct_digest = construct_freeze_content_digest(p0_repo)
        issued = issue_occurrence_reference(
            verify_source_capture_authority(
                seal_source_capture_package(
                    build_source_capture_body(
                        physical_instance="child",
                        namespace="ns-child",
                    )
                )
            )
        )
        draft = EvidenceSealManifestDraftV2(
            construct_freeze_digest=construct_digest,
            episode_id="episode-1",
            issued_occurrence=issued,
            evidence_complete_envelope_digest=FIXED_DIGEST,
            canonical_content_digest=FIXED_DIGEST,
            canonicalization_profile_digest=FIXED_DIGEST,
            adapter_implementation_digest=FIXED_DIGEST,
            condition_neutral_evidence_availability=sample_availability(),
            immediate_parents=(sample_construct_parent(p0_repo),),
            responsible_role="evidence_capture",
            created_at=CREATED_AT,
            lineage_edges=[edge],
        )
        with self.assertRaises(StructuralContractError):
            draft.finalize_and_seal(
                seal_time=SEAL_TIME,
                p0_repository=p0_repo,
                lineage_repository=lineage_repo,
            )

    def test_negative_behavior_relevant_code_change_invalidates_revision(self) -> None:
        import hashlib

        clear_p1_issuer_revision_cache()
        before = compute_p1_issuer_implementation_revision()
        with mock.patch(
            "eval_naturalistic.v2.authority_issuance._hash_file",
            return_value="c" * 64,
        ):
            clear_p1_issuer_revision_cache()
            after = compute_p1_issuer_implementation_revision()
        clear_p1_issuer_revision_cache()
        self.assertNotEqual(before, after)

    def test_negative_stale_cached_implementation_revision(self) -> None:
        clear_p1_issuer_revision_cache()
        cached = compute_p1_issuer_implementation_revision()
        clear_p1_issuer_revision_cache()
        fresh = compute_p1_issuer_implementation_revision()
        self.assertEqual(cached, fresh)

    def test_negative_arbitrary_issuer_revision_on_artifact(self) -> None:
        sealed = sample_sealed_authority()
        data = sealed.to_dict()
        data["issuer_implementation_revision"] = "arbitrary-revision"
        with self.assertRaises(StructuralContractError):
            verify_sealed_p1_authority(data)

    def test_negative_malformed_nested_authority_object(self) -> None:
        with self.assertRaises((StructuralContractError, KeyError, TypeError)):
            EvidenceSealManifestV2.from_dict({
                "header": {"artifact_id": "x", "schema_version": EvidenceSealManifestV2.SCHEMA},
                "construct_freeze_digest": FIXED_DIGEST,
            })


if __name__ == "__main__":
    unittest.main()

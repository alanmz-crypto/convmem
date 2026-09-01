"""V2-01C second corrective — source-backed authority adversarial tests."""

# pylint: disable=wrong-import-position,too-many-public-methods
from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from eval_naturalistic.base import StructuralContractError
from eval_naturalistic.v2.authority_issuance import (
    EvidenceSealManifestDraftV2,
    ImmediateParentBindingV2,
    IssuanceAuthorityRepository,
    IssuedOccurrenceReferenceV2,
    _ISSUED_REFERENCE_TOKEN,
    clear_p1_issuer_revision_cache,
    compute_p1_issuer_implementation_revision,
    issue_occurrence_reference,
    verify_sealed_p1_authority,
)
from eval_naturalistic.v2.contracts import EvidenceSealManifestV2
from eval_naturalistic.v2.evidence_commitments import bind_p1_evidence_commitments
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
from eval_naturalistic.v2.capture_attestation import CaptureAttestationRepository
from eval_naturalistic.v2.capture_attestation_issuance import issue_capture_attestation
from eval_naturalistic.v2.issuer_attestation_capability import (
    IssuerCaptureAttestationCapabilityRepository,
    mint_issuer_capture_attestation_capability,
)
from eval_naturalistic.v2.source_issuer_authority import (
    SourceIssuerGrantRepository,
    build_source_issuer_grant_record,
)
from eval_naturalistic.v2.source_authority import (
    SealedSourceCapturePackageV2,
    VerifiedSourceAuthorityV2,
    seal_source_capture_package,
    verify_source_capture_authority,
)
from tests.fixtures.naturalistic_v2_p1 import (
    ALT_DIGEST,
    CREATED_AT,
    FIXED_DIGEST,
    SEAL_TIME,
    build_p1_draft,
    build_source_capture_body,
    clone_lineage_edge,
    construct_freeze_content_digest,
    registered_construct_freeze,
    sample_availability,
    PLACEHOLDER_ATTESTATION_DIGEST,
    sample_capture_attestation_repository,
    sample_issuer_capability_repository,
    sample_construct_parent,
    sample_occurrence,
    sample_p0_repository,
    sample_sealed_authority,
    sample_sealed_authority_bundle,
    sample_verified_source_authority,
    seal_verified_source_capture,
)


class SourceBackedAuthorityAdversarialTests(unittest.TestCase):
    def test_positive_verified_source_issues_occurrence_authority(self) -> None:
        authority = sample_verified_source_authority()
        issuance_repo = IssuanceAuthorityRepository()
        issued = issue_occurrence_reference(authority, issuance_repository=issuance_repo)
        self.assertEqual(
            issued.occurrence_reference.physical_source_instance_id,
            "phys-a",
        )
        self.assertEqual(issued.source_authority_digest, authority.authority_record_digest)

    def test_positive_physical_incarnation_preserved(self) -> None:
        authority = sample_verified_source_authority(physical_instance="phys-unique")
        issuance_repo = IssuanceAuthorityRepository()
        issued = issue_occurrence_reference(authority, issuance_repository=issuance_repo)
        self.assertEqual(
            issued.occurrence_reference.physical_source_instance_id,
            "phys-unique",
        )

    def test_positive_p0_parent_independently_verified(self) -> None:
        sealed, repo, issuance_repo = sample_sealed_authority_bundle()
        verify_sealed_p1_authority(
            sealed, p0_repository=repo, issuance_repository=issuance_repo
        )

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
        issuance_repo = IssuanceAuthorityRepository()
        sealed = sample_sealed_authority(
            p0_repository=p0_repo,
            issuance_repository=issuance_repo,
            lineage_edges=[edge],
            lineage_repository=lineage_repo,
            occurrence=child,
        )
        verify_sealed_p1_authority(
            sealed,
            p0_repository=p0_repo,
            lineage_repository=lineage_repo,
            issuance_repository=issuance_repo,
        )

    def test_positive_canonical_sealed_bytes_verify(self) -> None:
        sealed, repo, issuance_repo = sample_sealed_authority_bundle()
        reparsed = verify_sealed_p1_authority(
            sealed.to_dict(), p0_repository=repo, issuance_repository=issuance_repo
        )
        self.assertEqual(sealed.content_digest, reparsed.content_digest)

    def test_positive_expected_implementation_revision_enforced(self) -> None:
        sealed, _, _ = sample_sealed_authority_bundle()
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
        issuance_repo = IssuanceAuthorityRepository()
        draft = build_p1_draft(
            p0_repository=p0_repo,
            issuance_repository=issuance_repo,
            lineage_edges=[edge],
        )
        with self.assertRaises(StructuralContractError):
            draft.finalize_and_seal(
                seal_time=SEAL_TIME,
                p0_repository=p0_repo,
                lineage_repository=LineageAttestationRepository(),
                issuance_repository=issuance_repo,
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
        issuance_repo = IssuanceAuthorityRepository()
        capture, att_repo, _, authority = seal_verified_source_capture(
            build_source_capture_body(),
            p0_repository=p0_repo,
        )
        capability_repo = sample_issuer_capability_repository(p0_repo)
        commitments = bind_p1_evidence_commitments(
            sealed_capture=capture,
            verified_authority=authority,
            attestation_repository=att_repo,
            issuer_capability_repository=capability_repo,
            p0_repository=p0_repo,
            construct_freeze_digest=construct_freeze_content_digest(p0_repo),
            construct_freeze_artifact_id=sample_construct_parent(p0_repo).parent_artifact_id,
            canonical_content_digest=FIXED_DIGEST,
            canonicalization_profile_digest=FIXED_DIGEST,
            adapter_implementation_digest=FIXED_DIGEST,
        )
        draft = build_p1_draft(
            p0_repository=p0_repo,
            issuance_repository=issuance_repo,
            issued=forged,
            evidence_commitments=commitments,
        )
        with self.assertRaises(StructuralContractError):
            draft.finalize_and_seal(
                seal_time=SEAL_TIME,
                p0_repository=p0_repo,
                issuance_repository=issuance_repo,
            )

    def test_negative_fabricated_self_consistent_p1_round_trip(self) -> None:
        sealed, p0_repo, issuance_repo = sample_sealed_authority_bundle()
        data = sealed.to_dict()
        data["episode_id"] = "forged-episode"
        with self.assertRaises(StructuralContractError):
            verify_sealed_p1_authority(
                data, p0_repository=p0_repo, issuance_repository=issuance_repo
            )

    def test_negative_nonexistent_parent_with_consistent_digest(self) -> None:
        p0_repo = InMemoryConstructFreezeRepository()
        issuance_repo = IssuanceAuthorityRepository()
        draft = build_p1_draft(
            p0_repository=sample_p0_repository(),
            issuance_repository=issuance_repo,
        )
        parent = ImmediateParentBindingV2(
            parent_kind="construct_freeze",
            parent_artifact_id=f"nps2_construct-freeze-manifest-v2_{FIXED_DIGEST}",
            parent_digest=FIXED_DIGEST,
        )
        draft = EvidenceSealManifestDraftV2(
            construct_freeze_digest=FIXED_DIGEST,
            episode_id=draft.episode_id,
            issued_occurrence=draft.issued_occurrence,
            evidence_commitments=draft.evidence_commitments,
            condition_neutral_evidence_availability=draft.condition_neutral_evidence_availability,
            immediate_parents=(parent,),
            responsible_role=draft.responsible_role,
            created_at=draft.created_at,
        )
        with self.assertRaises(StructuralContractError):
            draft.finalize_and_seal(
                seal_time=SEAL_TIME,
                p0_repository=p0_repo,
                issuance_repository=issuance_repo,
            )

    def test_negative_duplicate_construct_freeze_parents(self) -> None:
        p0_repo = sample_p0_repository()
        issuance_repo = IssuanceAuthorityRepository()
        parent = sample_construct_parent(p0_repo)
        draft = build_p1_draft(p0_repository=p0_repo, issuance_repository=issuance_repo)
        draft = EvidenceSealManifestDraftV2(
            construct_freeze_digest=draft.construct_freeze_digest,
            episode_id=draft.episode_id,
            issued_occurrence=draft.issued_occurrence,
            evidence_commitments=draft.evidence_commitments,
            condition_neutral_evidence_availability=draft.condition_neutral_evidence_availability,
            immediate_parents=(parent, parent),
            responsible_role=draft.responsible_role,
            created_at=draft.created_at,
        )
        with self.assertRaises(StructuralContractError):
            draft.finalize_and_seal(
                seal_time=SEAL_TIME,
                p0_repository=p0_repo,
                issuance_repository=issuance_repo,
            )

    def test_negative_unknown_extra_authority_parent(self) -> None:
        p0_repo = sample_p0_repository()
        issuance_repo = IssuanceAuthorityRepository()
        draft = build_p1_draft(p0_repository=p0_repo, issuance_repository=issuance_repo)
        draft = EvidenceSealManifestDraftV2(
            construct_freeze_digest=draft.construct_freeze_digest,
            episode_id=draft.episode_id,
            issued_occurrence=draft.issued_occurrence,
            evidence_commitments=draft.evidence_commitments,
            condition_neutral_evidence_availability=draft.condition_neutral_evidence_availability,
            immediate_parents=(
                sample_construct_parent(p0_repo),
                ImmediateParentBindingV2(
                    parent_kind="unknown_parent",
                    parent_artifact_id="nps2_unknown",
                    parent_digest=ALT_DIGEST,
                ),
            ),
            responsible_role=draft.responsible_role,
            created_at=draft.created_at,
        )
        with self.assertRaises(StructuralContractError):
            draft.finalize_and_seal(
                seal_time=SEAL_TIME,
                p0_repository=p0_repo,
                issuance_repository=issuance_repo,
            )

    def test_negative_parent_artifact_id_inconsistent_with_bytes(self) -> None:
        p0_repo = sample_p0_repository()
        issuance_repo = IssuanceAuthorityRepository()
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
        draft = build_p1_draft(p0_repository=p0_repo, issuance_repository=issuance_repo)
        draft = EvidenceSealManifestDraftV2(
            construct_freeze_digest=draft.construct_freeze_digest,
            episode_id=draft.episode_id,
            issued_occurrence=draft.issued_occurrence,
            evidence_commitments=draft.evidence_commitments,
            condition_neutral_evidence_availability=draft.condition_neutral_evidence_availability,
            immediate_parents=(bad_parent,),
            responsible_role=draft.responsible_role,
            created_at=draft.created_at,
        )
        with self.assertRaises(StructuralContractError):
            draft.finalize_and_seal(
                seal_time=SEAL_TIME,
                p0_repository=p0_repo,
                issuance_repository=issuance_repo,
            )

    def test_negative_wrong_parent_schema_kind(self) -> None:
        p0_repo = sample_p0_repository()
        issuance_repo = IssuanceAuthorityRepository()
        parent = ImmediateParentBindingV2(
            parent_kind="construct_freeze",
            parent_artifact_id="nps2_wrong-schema",
            parent_digest=ALT_DIGEST,
        )
        draft = build_p1_draft(p0_repository=p0_repo, issuance_repository=issuance_repo)
        draft = EvidenceSealManifestDraftV2(
            construct_freeze_digest=ALT_DIGEST,
            episode_id=draft.episode_id,
            issued_occurrence=draft.issued_occurrence,
            evidence_commitments=draft.evidence_commitments,
            condition_neutral_evidence_availability=draft.condition_neutral_evidence_availability,
            immediate_parents=(parent,),
            responsible_role=draft.responsible_role,
            created_at=draft.created_at,
        )
        with self.assertRaises(StructuralContractError):
            draft.finalize_and_seal(
                seal_time=SEAL_TIME,
                p0_repository=p0_repo,
                issuance_repository=issuance_repo,
            )

    def _draft_with_child_capture(
        self,
        *,
        physical_instance: str,
        namespace: str,
        lineage_edges: list[LineageEdgeV2] | None = None,
    ) -> tuple[EvidenceSealManifestDraftV2, InMemoryConstructFreezeRepository, IssuanceAuthorityRepository]:
        p0_repo = sample_p0_repository()
        issuance_repo = IssuanceAuthorityRepository()
        capture, att_repo, _, authority = seal_verified_source_capture(
            build_source_capture_body(physical_instance=physical_instance, namespace=namespace),
            p0_repository=p0_repo,
        )
        issued = issue_occurrence_reference(authority, issuance_repository=issuance_repo)
        capability_repo = sample_issuer_capability_repository(p0_repo)
        commitments = bind_p1_evidence_commitments(
            sealed_capture=capture,
            verified_authority=authority,
            attestation_repository=att_repo,
            issuer_capability_repository=capability_repo,
            p0_repository=p0_repo,
            construct_freeze_digest=construct_freeze_content_digest(p0_repo),
            construct_freeze_artifact_id=sample_construct_parent(p0_repo).parent_artifact_id,
            canonical_content_digest=FIXED_DIGEST,
            canonicalization_profile_digest=FIXED_DIGEST,
            adapter_implementation_digest=FIXED_DIGEST,
        )
        draft = EvidenceSealManifestDraftV2(
            construct_freeze_digest=construct_freeze_content_digest(p0_repo),
            episode_id="episode-1",
            issued_occurrence=issued,
            evidence_commitments=commitments,
            condition_neutral_evidence_availability=sample_availability(),
            immediate_parents=(sample_construct_parent(p0_repo),),
            responsible_role="evidence_capture",
            created_at=CREATED_AT,
            lineage_edges=lineage_edges or [],
        )
        return draft, p0_repo, issuance_repo

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
        draft, p0_repo, issuance_repo = self._draft_with_child_capture(
            physical_instance="child",
            namespace="ns-child",
            lineage_edges=[edge],
        )
        with self.assertRaises(StructuralContractError):
            draft.finalize_and_seal(
                seal_time=SEAL_TIME,
                p0_repository=p0_repo,
                lineage_repository=LineageAttestationRepository(),
                issuance_repository=issuance_repo,
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
        draft, p0_repo, issuance_repo = self._draft_with_child_capture(
            physical_instance="wrong-child",
            namespace="ns-wrong",
            lineage_edges=[edge],
        )
        with self.assertRaises(StructuralContractError):
            draft.finalize_and_seal(
                seal_time=SEAL_TIME,
                p0_repository=p0_repo,
                lineage_repository=lineage_repo,
                issuance_repository=issuance_repo,
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
        draft, p0_repo, issuance_repo = self._draft_with_child_capture(
            physical_instance="child",
            namespace="ns-child",
            lineage_edges=[edge],
        )
        with self.assertRaises(StructuralContractError):
            draft.finalize_and_seal(
                seal_time=SEAL_TIME,
                p0_repository=p0_repo,
                lineage_repository=lineage_repo,
                issuance_repository=issuance_repo,
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
        sealed, repo, issuance_repo = sample_sealed_authority_bundle()
        data = sealed.to_dict()
        data["issuer_implementation_revision"] = "arbitrary-revision"
        with self.assertRaises(StructuralContractError):
            verify_sealed_p1_authority(
                data, p0_repository=repo, issuance_repository=issuance_repo
            )

    def test_negative_verify_without_p0_repository_fails_closed(self) -> None:
        sealed, repo, issuance_repo = sample_sealed_authority_bundle()
        with self.assertRaises(StructuralContractError):
            verify_sealed_p1_authority(sealed.to_dict(), issuance_repository=issuance_repo)
        with self.assertRaises(StructuralContractError):
            verify_sealed_p1_authority(sealed.to_dict(), p0_repository=repo)

    def test_negative_fabricated_construct_freeze_parent_digest_only(self) -> None:
        p0_repo = InMemoryConstructFreezeRepository()
        issuance_repo = IssuanceAuthorityRepository()
        draft = build_p1_draft(
            p0_repository=sample_p0_repository(),
            issuance_repository=issuance_repo,
        )
        parent = ImmediateParentBindingV2(
            parent_kind="construct_freeze",
            parent_artifact_id=f"nps2_construct-freeze-manifest-v2_{FIXED_DIGEST}",
            parent_digest=FIXED_DIGEST,
        )
        draft = EvidenceSealManifestDraftV2(
            construct_freeze_digest=FIXED_DIGEST,
            episode_id=draft.episode_id,
            issued_occurrence=draft.issued_occurrence,
            evidence_commitments=draft.evidence_commitments,
            condition_neutral_evidence_availability=draft.condition_neutral_evidence_availability,
            immediate_parents=(parent,),
            responsible_role=draft.responsible_role,
            created_at=draft.created_at,
        )
        with self.assertRaises(StructuralContractError):
            draft.finalize_and_seal(
                seal_time=SEAL_TIME,
                p0_repository=p0_repo,
                issuance_repository=issuance_repo,
            )

    def test_negative_self_attested_source_capture_without_repository(self) -> None:
        body = build_source_capture_body()
        body["issuer_capture_attestation"] = ALT_DIGEST
        capture = seal_source_capture_package(body)
        with self.assertRaises(StructuralContractError):
            verify_source_capture_authority(capture)

    def test_negative_fabricated_capture_fields_with_arbitrary_attestation_digest(self) -> None:
        body = build_source_capture_body(
            physical_instance="fabricated-phys",
            native_record="fabricated-record",
            namespace="fabricated-ns",
            issuer_capture_attestation=ALT_DIGEST,
        )
        capture = seal_source_capture_package(body)
        with self.assertRaises(StructuralContractError):
            verify_source_capture_authority(
                capture,
                attestation_repository=CaptureAttestationRepository(),
            )

    def test_negative_self_consistent_capture_claim_graph_cannot_mint_p1(self) -> None:
        body = build_source_capture_body(
            physical_instance="forged-phys",
            issuer_capture_attestation=ALT_DIGEST,
        )
        capture = seal_source_capture_package(body)
        study_p0 = sample_p0_repository()
        study_manifest = registered_construct_freeze(study_p0)
        study_capability_repo = sample_issuer_capability_repository(study_p0)
        with self.assertRaises(StructuralContractError):
            authority = verify_source_capture_authority(
                capture,
                attestation_repository=CaptureAttestationRepository(),
                issuer_capability_repository=study_capability_repo,
                p0_repository=study_p0,
                construct_freeze_digest=study_manifest.header.content_digest or FIXED_DIGEST,
                construct_freeze_artifact_id=study_manifest.header.artifact_id,
            )
            issue_occurrence_reference(
                authority,
                issuance_repository=IssuanceAuthorityRepository(),
            )

    def test_negative_direct_capture_attestation_registration_rejected(self) -> None:
        p0_repo = sample_p0_repository()
        att_repo = sample_capture_attestation_repository(p0_repository=p0_repo)
        artifact = att_repo.artifacts()[0]
        fresh_repo = CaptureAttestationRepository()
        with self.assertRaises(AttributeError):
            fresh_repo.register(artifact)  # type: ignore[attr-defined]

    def test_negative_claimant_minted_attestation_chain_cannot_mint_p1(self) -> None:
        occurrence = OccurrenceReferenceV2(
            source_system_id="fabricated-sys",
            tenant_or_realm_id="fabricated-tenant",
            authority_scope_id="fabricated-scope",
            occurrence_namespace_id="fabricated-ns",
            physical_source_instance_id="fabricated-phys",
            native_id_namespace="fabricated.native",
            native_record_id="fabricated-record",
            source_revision_or_asof_id="fabricated-rev",
        )
        forged_grant = build_source_issuer_grant_record(
            issuer_identity="i-am-not-an-authorized-source-issuer",
            source_system_id=occurrence.source_system_id,
            authority_scope_id=occurrence.authority_scope_id,
        )
        attacker_p0 = InMemoryConstructFreezeRepository()
        forged_manifest = seal_construct_freeze_manifest(
            construct_policy_digest=ALT_DIGEST,
            study_id="forged-study",
            responsible_role="study_owner",
            created_at=CREATED_AT,
            seal_time=SEAL_TIME,
            authorized_capture_issuer_grants=(forged_grant,),
        )
        attacker_p0.register(forged_manifest)
        forged_digest = forged_manifest.header.content_digest or ALT_DIGEST
        forged_grant_repo = SourceIssuerGrantRepository.from_construct_freeze(forged_manifest)
        forged_grant_obj = forged_grant_repo.resolve(
            issuer_identity=forged_grant["issuer_identity"],
            source_system_id=occurrence.source_system_id,
            authority_scope_id=occurrence.authority_scope_id,
        )
        attacker_capability_repo = IssuerCaptureAttestationCapabilityRepository.from_capabilities(
            construct_freeze_digest=forged_digest,
            capabilities=(
                mint_issuer_capture_attestation_capability(
                    forged_grant_obj,
                    construct_freeze_digest=forged_digest,
                ),
            ),
        )
        body = build_source_capture_body(
            physical_instance=occurrence.physical_source_instance_id,
            native_record=occurrence.native_record_id,
            revision=occurrence.source_revision_or_asof_id,
            namespace=occurrence.occurrence_namespace_id,
            snapshot_id="fabricated-snap",
            issuer_capture_attestation=PLACEHOLDER_ATTESTATION_DIGEST,
        )
        body.update(
            {
                "source_system_id": occurrence.source_system_id,
                "tenant_or_realm_id": occurrence.tenant_or_realm_id,
                "authority_scope_id": occurrence.authority_scope_id,
                "native_id_namespace": occurrence.native_id_namespace,
            }
        )
        temp_capture = seal_source_capture_package(body)
        att_repo = CaptureAttestationRepository()
        issue_capture_attestation(
            temp_capture,
            attestation_repository=att_repo,
            p0_repository=attacker_p0,
            issuer_capability_repository=attacker_capability_repo,
            construct_freeze_digest=forged_digest,
            construct_freeze_artifact_id=forged_manifest.header.artifact_id,
            responsible_role="capture_issuer",
            created_at=CREATED_AT,
            seal_time=SEAL_TIME,
        )
        attestation_digest = att_repo.artifacts()[0].attestation_evidence_digest()
        body["issuer_capture_attestation"] = attestation_digest
        capture = seal_source_capture_package(body)
        study_p0 = sample_p0_repository()
        study_manifest = registered_construct_freeze(study_p0)
        study_capability_repo = sample_issuer_capability_repository(study_p0)
        with self.assertRaises(StructuralContractError):
            verify_source_capture_authority(
                capture,
                attestation_repository=att_repo,
                issuer_capability_repository=study_capability_repo,
                p0_repository=study_p0,
                construct_freeze_digest=study_manifest.header.content_digest or FIXED_DIGEST,
                construct_freeze_artifact_id=study_manifest.header.artifact_id,
            )
            issue_occurrence_reference(
                verify_source_capture_authority(
                    capture,
                    attestation_repository=att_repo,
                    issuer_capability_repository=study_capability_repo,
                    p0_repository=study_p0,
                    construct_freeze_digest=study_manifest.header.content_digest or FIXED_DIGEST,
                    construct_freeze_artifact_id=study_manifest.header.artifact_id,
                ),
                issuance_repository=IssuanceAuthorityRepository(),
            )

    def test_negative_legitimate_grant_replay_without_issuer_capability_cannot_mint_p1(self) -> None:
        study_p0 = sample_p0_repository()
        study_manifest = registered_construct_freeze(study_p0)
        construct_digest = study_manifest.header.content_digest or FIXED_DIGEST
        grant_repo = SourceIssuerGrantRepository.from_construct_freeze(study_manifest)
        occurrence = OccurrenceReferenceV2(
            source_system_id="sys-crush",
            tenant_or_realm_id="tenant-1",
            authority_scope_id="scope-1",
            occurrence_namespace_id="fabricated-ns",
            physical_source_instance_id="fabricated-phys",
            native_id_namespace="crush.message",
            native_record_id="fabricated-record",
            source_revision_or_asof_id="fabricated-rev",
        )
        grant_repo.resolve_for_occurrence(occurrence)
        body = build_source_capture_body(
            physical_instance=occurrence.physical_source_instance_id,
            native_record=occurrence.native_record_id,
            revision=occurrence.source_revision_or_asof_id,
            namespace=occurrence.occurrence_namespace_id,
            snapshot_id="fabricated-snap",
            issuer_capture_attestation=PLACEHOLDER_ATTESTATION_DIGEST,
        )
        temp_capture = seal_source_capture_package(body)
        empty_capability_repo = IssuerCaptureAttestationCapabilityRepository.from_capabilities(
            construct_freeze_digest=construct_digest,
            capabilities=(),
        )
        att_repo = CaptureAttestationRepository()
        with self.assertRaises(StructuralContractError):
            issue_capture_attestation(
                temp_capture,
                attestation_repository=att_repo,
                p0_repository=study_p0,
                issuer_capability_repository=empty_capability_repo,
                construct_freeze_digest=construct_digest,
                construct_freeze_artifact_id=study_manifest.header.artifact_id,
                responsible_role="capture_issuer",
                created_at=CREATED_AT,
                seal_time=SEAL_TIME,
            )
        study_capability_repo = sample_issuer_capability_repository(study_p0)
        with self.assertRaises(StructuralContractError):
            verify_source_capture_authority(
                temp_capture,
                attestation_repository=att_repo,
                issuer_capability_repository=study_capability_repo,
                p0_repository=study_p0,
                construct_freeze_digest=construct_digest,
                construct_freeze_artifact_id=study_manifest.header.artifact_id,
            )
            issue_occurrence_reference(
                verify_source_capture_authority(
                    temp_capture,
                    attestation_repository=att_repo,
                    issuer_capability_repository=study_capability_repo,
                    p0_repository=study_p0,
                    construct_freeze_digest=construct_digest,
                    construct_freeze_artifact_id=study_manifest.header.artifact_id,
                ),
                issuance_repository=IssuanceAuthorityRepository(),
            )

    def test_negative_malformed_nested_authority_object(self) -> None:
        with self.assertRaises((StructuralContractError, KeyError, TypeError)):
            EvidenceSealManifestV2.from_dict({
                "header": {"artifact_id": "x", "schema_version": EvidenceSealManifestV2.SCHEMA},
                "construct_freeze_digest": FIXED_DIGEST,
            })

    def test_negative_capture_without_raw_record_binding(self) -> None:
        body = build_source_capture_body()
        del body["raw_record_digest"]
        with self.assertRaises((StructuralContractError, KeyError)):
            seal_source_capture_package(body)

    def test_negative_instantiated_capture_with_tampered_canonical_bytes(self) -> None:
        p0_repo = sample_p0_repository()
        capture, att_repo, _, _ = seal_verified_source_capture(
            build_source_capture_body(),
            p0_repository=p0_repo,
        )
        manifest = registered_construct_freeze(p0_repo)
        tampered = SealedSourceCapturePackageV2(
            capture_body=dict(capture.capture_body),
            canonical_bytes=b"{\"schema_version\":\"tampered\"}",
            content_digest=capture.content_digest,
        )
        capability_repo = sample_issuer_capability_repository(p0_repo)
        with self.assertRaises(StructuralContractError):
            verify_source_capture_authority(
                tampered,
                attestation_repository=att_repo,
                issuer_capability_repository=capability_repo,
                p0_repository=p0_repo,
                construct_freeze_digest=construct_freeze_content_digest(p0_repo),
                construct_freeze_artifact_id=manifest.header.artifact_id,
            )

    def test_negative_token_built_source_authority_lacks_repository_evidence(self) -> None:
        from eval_naturalistic.v2.source_authority import _SOURCE_AUTHORITY_TOKEN

        forged = VerifiedSourceAuthorityV2(
            _token=_SOURCE_AUTHORITY_TOKEN,
            source_capture_digest=FIXED_DIGEST,
            occurrence_reference=sample_occurrence(),
            evidence_snapshot_id="snap-1",
            issuer_capture_attestation=ALT_DIGEST,
            authority_record_digest=FIXED_DIGEST,
        )
        with self.assertRaises(StructuralContractError):
            issue_occurrence_reference(
                forged,
                issuance_repository=IssuanceAuthorityRepository(),
            )

    def test_negative_direct_issuance_repository_registration_rejected(self) -> None:
        repo = IssuanceAuthorityRepository()
        forged = IssuedOccurrenceReferenceV2(
            _token=_ISSUED_REFERENCE_TOKEN,
            occurrence_reference=sample_occurrence(),
            issuance_digest=FIXED_DIGEST,
            issuer_implementation_revision=compute_p1_issuer_implementation_revision(),
            evidence_snapshot_id="snap-1",
            source_authority_digest=FIXED_DIGEST,
        )
        with self.assertRaises(AttributeError):
            repo.register(forged)  # type: ignore[attr-defined]

    def test_negative_altered_evidence_envelope_commitment_rejected(self) -> None:
        sealed, p0_repo, issuance_repo = sample_sealed_authority_bundle()
        data = sealed.to_dict()
        data["evidence_complete_envelope_digest"] = ALT_DIGEST
        with self.assertRaises(StructuralContractError):
            verify_sealed_p1_authority(
                data, p0_repository=p0_repo, issuance_repository=issuance_repo
            )

    def test_negative_altered_raw_record_commitment_rejected(self) -> None:
        sealed, p0_repo, issuance_repo = sample_sealed_authority_bundle()
        data = sealed.to_dict()
        data["raw_record_digest"] = ALT_DIGEST
        with self.assertRaises(StructuralContractError):
            verify_sealed_p1_authority(
                data, p0_repository=p0_repo, issuance_repository=issuance_repo
            )

    def test_negative_attested_lineage_without_repository(self) -> None:
        child = sample_occurrence(physical_instance="child", namespace="ns-child")
        parent = sample_occurrence(physical_instance="parent", namespace="ns-p")
        lineage_repo = LineageAttestationRepository()
        edge = clone_lineage_edge(
            child_occurrence=child,
            parent_occurrence=parent,
            from_instance="parent",
            to_instance="child",
            lineage_repository=lineage_repo,
        )
        sealed, p0_repo, issuance_repo = sample_sealed_authority_bundle(
            occurrence=child,
            lineage_edges=[edge],
            lineage_repository=lineage_repo,
        )
        with self.assertRaises(StructuralContractError):
            verify_sealed_p1_authority(
                sealed.to_dict(),
                p0_repository=p0_repo,
                issuance_repository=issuance_repo,
                lineage_repository=None,
            )

    def test_negative_lineage_physical_labels_inconsistent_with_occurrences(self) -> None:
        child = sample_occurrence(physical_instance="child")
        parent = sample_occurrence(physical_instance="parent", namespace="ns-p")
        lineage_repo = LineageAttestationRepository()
        edge = clone_lineage_edge(
            child_occurrence=child,
            parent_occurrence=parent,
            from_instance="wrong-parent",
            to_instance="child",
            lineage_repository=lineage_repo,
        )
        draft, p0_repo, issuance_repo = self._draft_with_child_capture(
            physical_instance="child",
            namespace="ns-child",
            lineage_edges=[edge],
        )
        with self.assertRaises(StructuralContractError):
            draft.finalize_and_seal(
                seal_time=SEAL_TIME,
                p0_repository=p0_repo,
                lineage_repository=lineage_repo,
                issuance_repository=issuance_repo,
            )

    def test_negative_header_parent_inconsistent_with_construct_binding(self) -> None:
        sealed, p0_repo, issuance_repo = sample_sealed_authority_bundle()
        data = sealed.to_dict()
        data["header"]["parent_artifact_id"] = "nps2_wrong_parent"
        with self.assertRaises(StructuralContractError):
            verify_sealed_p1_authority(
                data, p0_repository=p0_repo, issuance_repository=issuance_repo
            )

    def test_negative_implementation_revision_changes_without_manual_cache_clear(self) -> None:
        before = compute_p1_issuer_implementation_revision()
        with mock.patch(
            "eval_naturalistic.v2.authority_issuance._hash_file",
            return_value="d" * 64,
        ):
            after = compute_p1_issuer_implementation_revision()
        self.assertNotEqual(before, after)
        restored = compute_p1_issuer_implementation_revision()
        self.assertEqual(before, restored)

    def test_positive_fresh_repository_process_boundary_verification(self) -> None:
        sealed, p0_repo, issuance_repo = sample_sealed_authority_bundle()
        portable = IssuanceAuthorityRepository.from_records(issuance_repo.records())
        fresh_p0 = InMemoryConstructFreezeRepository()
        for manifest in p0_repo.manifests():
            fresh_p0.register(manifest)
        verify_sealed_p1_authority(
            sealed.to_dict(),
            p0_repository=fresh_p0,
            issuance_repository=portable,
        )


if __name__ == "__main__":
    unittest.main()

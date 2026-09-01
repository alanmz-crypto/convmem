"""Hermetic fixtures for Naturalistic V2 P1 identity and evidence seal tests."""

from __future__ import annotations

from eval_naturalistic.v2.authority_issuance import (
    EvidenceSealManifestDraftV2,
    ImmediateParentBindingV2,
    OccurrenceIssuanceEvidenceV2,
    SealedP1AuthorityV2,
    issue_occurrence_reference,
)
from eval_naturalistic.v2.contracts import (
    EvidenceAvailabilityManifestV2,
    EvidenceSealManifestV2,
)
from eval_naturalistic.v2.evidence import (
    ConditionNeutralEvidenceAvailabilityV2,
    SourcePresenceV2,
    SummaryEvidenceAvailabilityV2,
    VerbatimEvidenceAvailabilityV2,
)
from eval_naturalistic.v2.identity import LineageEdgeV2, LineageRelationKind

FIXED_DIGEST = "a" * 64
ALT_DIGEST = "b" * 64
CONSTRUCT_FREEZE_ARTIFACT_ID = "nps2_construct_freeze_test"
CREATED_AT = "2026-08-31T00:00:00Z"
SEAL_TIME = "2026-08-31T00:00:01Z"


def sample_issuance_evidence(
    *,
    physical_instance: str = "phys-a",
    native_record: str = "msg-1",
    revision: str = "rev-1",
    namespace: str = "ns-a",
    snapshot_id: str = "snap-1",
) -> OccurrenceIssuanceEvidenceV2:
    return OccurrenceIssuanceEvidenceV2(
        source_system_id="sys-crush",
        tenant_or_realm_id="tenant-1",
        authority_scope_id="scope-1",
        occurrence_namespace_id=namespace,
        physical_source_instance_id=physical_instance,
        native_id_namespace="crush.message",
        native_record_id=native_record,
        source_revision_or_asof_id=revision,
        evidence_snapshot_id=snapshot_id,
    )


def sample_occurrence(**kwargs):
    issued = issue_occurrence_reference(sample_issuance_evidence(**kwargs))
    return issued.occurrence_reference


def sample_availability(
    *,
    presence: SourcePresenceV2 = SourcePresenceV2.PRESENT,
    verbatim: VerbatimEvidenceAvailabilityV2 = VerbatimEvidenceAvailabilityV2.AVAILABLE,
    summary: SummaryEvidenceAvailabilityV2 = SummaryEvidenceAvailabilityV2.AVAILABLE,
) -> ConditionNeutralEvidenceAvailabilityV2:
    return ConditionNeutralEvidenceAvailabilityV2(
        source_presence=presence,
        verbatim_evidence_availability=verbatim,
        summary_evidence_availability=summary,
    )


def sample_construct_parent(*, digest: str = FIXED_DIGEST) -> ImmediateParentBindingV2:
    return ImmediateParentBindingV2(
        parent_kind="construct_freeze",
        parent_artifact_id=CONSTRUCT_FREEZE_ARTIFACT_ID,
        parent_digest=digest,
    )


def sample_seal_manifest(
    *,
    occurrence=None,
    availability: ConditionNeutralEvidenceAvailabilityV2 | None = None,
    canonical_digest: str = FIXED_DIGEST,
    lineage_edges: list[LineageEdgeV2] | None = None,
    construct_freeze_digest: str = FIXED_DIGEST,
) -> EvidenceSealManifestV2:
    if occurrence is None:
        issued = issue_occurrence_reference(sample_issuance_evidence())
    else:
        issued = issue_occurrence_reference(
            OccurrenceIssuanceEvidenceV2(
                source_system_id=occurrence.source_system_id,
                tenant_or_realm_id=occurrence.tenant_or_realm_id,
                authority_scope_id=occurrence.authority_scope_id,
                occurrence_namespace_id=occurrence.occurrence_namespace_id,
                physical_source_instance_id=occurrence.physical_source_instance_id,
                native_id_namespace=occurrence.native_id_namespace,
                native_record_id=occurrence.native_record_id,
                source_revision_or_asof_id=occurrence.source_revision_or_asof_id,
                evidence_snapshot_id="snap-1",
            )
        )
    draft = EvidenceSealManifestDraftV2(
        construct_freeze_digest=construct_freeze_digest,
        episode_id="episode-1",
        issued_occurrence=issued,
        evidence_complete_envelope_digest=FIXED_DIGEST,
        canonical_content_digest=canonical_digest,
        canonicalization_profile_digest=FIXED_DIGEST,
        adapter_implementation_digest=FIXED_DIGEST,
        condition_neutral_evidence_availability=availability or sample_availability(),
        immediate_parents=(sample_construct_parent(digest=construct_freeze_digest),),
        responsible_role="evidence_capture",
        created_at=CREATED_AT,
        lineage_edges=lineage_edges or [],
    )
    return draft.finalize_and_seal(seal_time=SEAL_TIME).manifest


def sample_sealed_authority(**kwargs) -> SealedP1AuthorityV2:
    manifest = sample_seal_manifest(**kwargs)
    from eval_naturalistic.v2.authority_issuance import verify_sealed_p1_authority
    return verify_sealed_p1_authority(manifest.to_dict())


def sample_availability_manifest(
    seal: EvidenceSealManifestV2,
    *,
    availability: ConditionNeutralEvidenceAvailabilityV2 | None = None,
) -> EvidenceAvailabilityManifestV2:
    from eval_naturalistic.base import ArtifactHeaderV1
    return EvidenceAvailabilityManifestV2(
        header=ArtifactHeaderV1(
            artifact_id="nps2_avail_test",
            schema_version=EvidenceAvailabilityManifestV2.SCHEMA,
            parent_artifact_id=seal.header.artifact_id,
            parent_digest=seal.header.content_digest,
            created_at=CREATED_AT,
            seal_time=SEAL_TIME,
            responsible_role="evidence_capture",
            content_digest=FIXED_DIGEST,
            sealed=True,
        ),
        evidence_seal_digest=seal.header.content_digest or FIXED_DIGEST,
        episode_id=seal.episode_id,
        occurrence_reference=seal.occurrence_reference,
        availability=availability or seal.condition_neutral_evidence_availability,
    )


def clone_lineage_edge(
    *,
    from_instance: str,
    to_instance: str,
    lineage_id: str = "lineage-1",
    child_digest: str = FIXED_DIGEST,
    parent_digest: str = ALT_DIGEST,
) -> LineageEdgeV2:
    return LineageEdgeV2(
        logical_lineage_id=lineage_id,
        from_physical_instance_id=from_instance,
        to_physical_instance_id=to_instance,
        relation_kind=LineageRelationKind.CLONE,
        issuer_attested=True,
        child_occurrence_digest=child_digest,
        parent_occurrence_digest=parent_digest,
        attestation_evidence_digest=FIXED_DIGEST,
    )

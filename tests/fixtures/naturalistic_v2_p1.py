"""Hermetic fixtures for Naturalistic V2 P1 identity and evidence seal tests."""

from __future__ import annotations

from eval_naturalistic.base import ArtifactHeaderV1
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
from eval_naturalistic.v2.identity import LineageEdgeV2, LineageRelationKind, OccurrenceReferenceV2

FIXED_DIGEST = "a" * 64
ALT_DIGEST = "b" * 64


def sample_header(*, schema: str, artifact_id: str = "nps2_test") -> ArtifactHeaderV1:
    return ArtifactHeaderV1(
        artifact_id=artifact_id,
        schema_version=schema,
        parent_artifact_id=None,
        parent_digest=None,
        created_at="2026-08-31T00:00:00Z",
        seal_time="2026-08-31T00:00:01Z",
        responsible_role="evidence_capture",
        content_digest=FIXED_DIGEST,
        sealed=True,
    )


def sample_occurrence(
    *,
    physical_instance: str = "phys-a",
    native_record: str = "msg-1",
    revision: str = "rev-1",
    namespace: str = "ns-a",
) -> OccurrenceReferenceV2:
    return OccurrenceReferenceV2(
        source_system_id="sys-crush",
        tenant_or_realm_id="tenant-1",
        authority_scope_id="scope-1",
        occurrence_namespace_id=namespace,
        physical_source_instance_id=physical_instance,
        native_id_namespace="crush.message",
        native_record_id=native_record,
        source_revision_or_asof_id=revision,
    )


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


def sample_seal_manifest(
    *,
    occurrence: OccurrenceReferenceV2 | None = None,
    availability: ConditionNeutralEvidenceAvailabilityV2 | None = None,
    canonical_digest: str = FIXED_DIGEST,
    lineage_edges: list[LineageEdgeV2] | None = None,
) -> EvidenceSealManifestV2:
    occ = occurrence or sample_occurrence()
    return EvidenceSealManifestV2(
        header=sample_header(schema=EvidenceSealManifestV2.SCHEMA),
        construct_freeze_digest=FIXED_DIGEST,
        episode_id="episode-1",
        occurrence_reference=occ,
        physical_instance_id=occ.physical_source_instance_id,
        revision_or_asof_id=occ.source_revision_or_asof_id,
        evidence_snapshot_id="snap-1",
        evidence_complete_envelope_digest=FIXED_DIGEST,
        canonical_content_digest=canonical_digest,
        canonicalization_profile_digest=FIXED_DIGEST,
        adapter_implementation_digest=FIXED_DIGEST,
        condition_neutral_evidence_availability=availability or sample_availability(),
        lineage_edges=lineage_edges or [],
    )


def sample_availability_manifest(
    seal: EvidenceSealManifestV2,
    *,
    availability: ConditionNeutralEvidenceAvailabilityV2 | None = None,
) -> EvidenceAvailabilityManifestV2:
    return EvidenceAvailabilityManifestV2(
        header=sample_header(
            schema=EvidenceAvailabilityManifestV2.SCHEMA,
            artifact_id="nps2_avail_test",
        ),
        evidence_seal_digest=FIXED_DIGEST,
        episode_id=seal.episode_id,
        occurrence_reference=seal.occurrence_reference,
        availability=availability or seal.condition_neutral_evidence_availability,
    )


def clone_lineage_edge(
    *, from_instance: str, to_instance: str, lineage_id: str = "lineage-1"
) -> LineageEdgeV2:
    return LineageEdgeV2(
        logical_lineage_id=lineage_id,
        from_physical_instance_id=from_instance,
        to_physical_instance_id=to_instance,
        relation_kind=LineageRelationKind.CLONE,
        issuer_attested=True,
    )

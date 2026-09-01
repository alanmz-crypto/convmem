"""Hermetic fixtures for Naturalistic V2 P1 source-backed authority tests."""

from __future__ import annotations

from eval_naturalistic.v2.authority_issuance import (
    EvidenceSealManifestDraftV2,
    ImmediateParentBindingV2,
    IssuanceAuthorityRepository,
    SealedP1AuthorityV2,
    issue_occurrence_reference,
)
from eval_naturalistic.v2.capture_attestation import (
    CaptureAttestationRepository,
    seal_capture_attestation,
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
from eval_naturalistic.v2.evidence_commitments import bind_p1_evidence_commitments
from eval_naturalistic.v2.identity import LineageEdgeV2, LineageRelationKind, OccurrenceReferenceV2
from eval_naturalistic.v2.lineage_attestation import (
    LineageAttestationRepository,
    occurrence_commitment_digest,
    seal_lineage_attestation,
)
from eval_naturalistic.v2.p0_construct import (
    ConstructFreezeManifestV2,
    InMemoryConstructFreezeRepository,
    seal_construct_freeze_manifest,
)
from eval_naturalistic.v2.source_authority import (
    seal_source_capture_package,
    verify_source_capture_authority,
)

FIXED_DIGEST = "a" * 64
ALT_DIGEST = "b" * 64
CREATED_AT = "2026-08-31T00:00:00Z"
SEAL_TIME = "2026-08-31T00:00:01Z"
DEFAULT_ISSUER_IDENTITY = "capture-attestor-v1"
DEFAULT_RAW_RECORD_DIGEST = "c" * 64


def sample_p0_repository(
    *,
    construct_policy_digest: str = FIXED_DIGEST,
) -> InMemoryConstructFreezeRepository:
    repo = InMemoryConstructFreezeRepository()
    manifest = seal_construct_freeze_manifest(
        construct_policy_digest=construct_policy_digest,
        study_id="study-naturalistic-v2-test",
        responsible_role="study_owner",
        created_at=CREATED_AT,
        seal_time=SEAL_TIME,
    )
    repo.register(manifest)
    return repo


def registered_construct_freeze(
    repo: InMemoryConstructFreezeRepository,
) -> ConstructFreezeManifestV2:
    return next(iter(repo._artifacts.values()))


def construct_freeze_content_digest(repo: InMemoryConstructFreezeRepository) -> str:
    manifest = registered_construct_freeze(repo)
    digest = manifest.header.content_digest
    if digest is None:
        raise ValueError("registered construct freeze missing content digest")
    return digest


def sample_construct_parent(
    repo: InMemoryConstructFreezeRepository,
) -> ImmediateParentBindingV2:
    manifest = registered_construct_freeze(repo)
    digest = construct_freeze_content_digest(repo)
    return ImmediateParentBindingV2(
        parent_kind="construct_freeze",
        parent_artifact_id=manifest.header.artifact_id,
        parent_digest=digest,
    )


def build_source_capture_body(
    *,
    physical_instance: str = "phys-a",
    native_record: str = "msg-1",
    revision: str = "rev-1",
    namespace: str = "ns-a",
    snapshot_id: str = "snap-1",
    raw_record_digest: str = DEFAULT_RAW_RECORD_DIGEST,
    issuer_capture_attestation: str | None = None,
) -> dict:
    body = {
        "source_system_id": "sys-crush",
        "tenant_or_realm_id": "tenant-1",
        "authority_scope_id": "scope-1",
        "occurrence_namespace_id": namespace,
        "physical_source_instance_id": physical_instance,
        "native_id_namespace": "crush.message",
        "native_record_id": native_record,
        "source_revision_or_asof_id": revision,
        "evidence_snapshot_id": snapshot_id,
        "raw_record_digest": raw_record_digest,
    }
    if issuer_capture_attestation is not None:
        body["issuer_capture_attestation"] = issuer_capture_attestation
    return body


def sample_capture_attestation_repository(
    *,
    physical_instance: str = "phys-a",
    native_record: str = "msg-1",
    revision: str = "rev-1",
    namespace: str = "ns-a",
    snapshot_id: str = "snap-1",
    issuer_identity: str = DEFAULT_ISSUER_IDENTITY,
) -> CaptureAttestationRepository:
    occurrence = OccurrenceReferenceV2(
        source_system_id="sys-crush",
        tenant_or_realm_id="tenant-1",
        authority_scope_id="scope-1",
        occurrence_namespace_id=namespace,
        physical_source_instance_id=physical_instance,
        native_id_namespace="crush.message",
        native_record_id=native_record,
        source_revision_or_asof_id=revision,
    )
    artifact = seal_capture_attestation(
        occurrence_reference=occurrence,
        evidence_snapshot_id=snapshot_id,
        issuer_identity=issuer_identity,
        responsible_role="capture_issuer",
        created_at=CREATED_AT,
        seal_time=SEAL_TIME,
    )
    repo = CaptureAttestationRepository()
    repo.register(artifact)
    return repo


def seal_verified_source_capture(
    body: dict,
    *,
    attestation_repository: CaptureAttestationRepository | None = None,
) -> tuple:
    """Seal capture bytes and return (capture, attestation_repo, authority)."""

    snapshot_id = body["evidence_snapshot_id"]
    occurrence = OccurrenceReferenceV2(
        source_system_id=body["source_system_id"],
        tenant_or_realm_id=body["tenant_or_realm_id"],
        authority_scope_id=body["authority_scope_id"],
        occurrence_namespace_id=body["occurrence_namespace_id"],
        physical_source_instance_id=body["physical_source_instance_id"],
        native_id_namespace=body["native_id_namespace"],
        native_record_id=body["native_record_id"],
        source_revision_or_asof_id=body["source_revision_or_asof_id"],
    )
    repo = attestation_repository or sample_capture_attestation_repository(
        physical_instance=occurrence.physical_source_instance_id,
        native_record=occurrence.native_record_id,
        revision=occurrence.source_revision_or_asof_id,
        namespace=occurrence.occurrence_namespace_id,
        snapshot_id=snapshot_id,
    )
    attestation_digest = next(iter(repo._artifacts))
    working = dict(body)
    working["issuer_capture_attestation"] = attestation_digest
    capture = seal_source_capture_package(working)
    authority = verify_source_capture_authority(capture, attestation_repository=repo)
    return capture, repo, authority


def sample_verified_source_authority(**kwargs):
    body = build_source_capture_body(**kwargs)
    _, _, authority = seal_verified_source_capture(body)
    return authority


def sample_issuance_repository(**kwargs) -> IssuanceAuthorityRepository:
    repo = IssuanceAuthorityRepository()
    issue_occurrence_reference(sample_verified_source_authority(**kwargs), issuance_repository=repo)
    return repo


def sample_occurrence(**kwargs):
    repo = IssuanceAuthorityRepository()
    issued = issue_occurrence_reference(
        sample_verified_source_authority(**kwargs),
        issuance_repository=repo,
    )
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


def sample_sealed_authority(
    *,
    p0_repository: InMemoryConstructFreezeRepository | None = None,
    issuance_repository: IssuanceAuthorityRepository | None = None,
    lineage_edges: list[LineageEdgeV2] | None = None,
    lineage_repository: LineageAttestationRepository | None = None,
    occurrence: OccurrenceReferenceV2 | None = None,
    availability: ConditionNeutralEvidenceAvailabilityV2 | None = None,
    canonical_content_digest: str = FIXED_DIGEST,
) -> SealedP1AuthorityV2:
    repo = p0_repository or sample_p0_repository()
    parent = sample_construct_parent(repo)
    construct_digest = construct_freeze_content_digest(repo)
    issuance_repo = issuance_repository or IssuanceAuthorityRepository()
    if occurrence is not None:
        capture_body = build_source_capture_body(
            physical_instance=occurrence.physical_source_instance_id,
            native_record=occurrence.native_record_id,
            revision=occurrence.source_revision_or_asof_id,
            namespace=occurrence.occurrence_namespace_id,
            snapshot_id="snap-1",
        )
        capture_body.update(
            {
                "source_system_id": occurrence.source_system_id,
                "tenant_or_realm_id": occurrence.tenant_or_realm_id,
                "authority_scope_id": occurrence.authority_scope_id,
                "native_id_namespace": occurrence.native_id_namespace,
            }
        )
        capture, att_repo, authority = seal_verified_source_capture(capture_body)
        issued = issue_occurrence_reference(authority, issuance_repository=issuance_repo)
    else:
        capture, att_repo, authority = seal_verified_source_capture(build_source_capture_body())
        issued = issue_occurrence_reference(authority, issuance_repository=issuance_repo)
    commitments = bind_p1_evidence_commitments(
        sealed_capture=capture,
        verified_authority=authority,
        attestation_repository=att_repo,
        canonical_content_digest=canonical_content_digest,
        canonicalization_profile_digest=FIXED_DIGEST,
        adapter_implementation_digest=FIXED_DIGEST,
    )
    draft = EvidenceSealManifestDraftV2(
        construct_freeze_digest=construct_digest,
        episode_id="episode-1",
        issued_occurrence=issued,
        evidence_commitments=commitments,
        condition_neutral_evidence_availability=availability or sample_availability(),
        immediate_parents=(parent,),
        responsible_role="evidence_capture",
        created_at=CREATED_AT,
        lineage_edges=lineage_edges or [],
    )
    return draft.finalize_and_seal(
        seal_time=SEAL_TIME,
        p0_repository=repo,
        lineage_repository=lineage_repository,
        issuance_repository=issuance_repo,
    )


def sample_sealed_authority_bundle(
    **kwargs,
) -> tuple[SealedP1AuthorityV2, InMemoryConstructFreezeRepository, IssuanceAuthorityRepository]:
    p0_repo = kwargs.pop("p0_repository", None) or sample_p0_repository()
    issuance_repo = kwargs.pop("issuance_repository", None) or IssuanceAuthorityRepository()
    sealed = sample_sealed_authority(
        p0_repository=p0_repo,
        issuance_repository=issuance_repo,
        **kwargs,
    )
    return sealed, p0_repo, issuance_repo


def build_p1_draft(
    *,
    p0_repository: InMemoryConstructFreezeRepository,
    issuance_repository: IssuanceAuthorityRepository,
    issued=None,
    evidence_commitments=None,
    lineage_edges=None,
    episode_id: str = "episode-1",
) -> EvidenceSealManifestDraftV2:
    construct_digest = construct_freeze_content_digest(p0_repository)
    if issued is None:
        capture, att_repo, authority = seal_verified_source_capture(build_source_capture_body())
        issued = issue_occurrence_reference(authority, issuance_repository=issuance_repository)
        evidence_commitments = evidence_commitments or bind_p1_evidence_commitments(
            sealed_capture=capture,
            verified_authority=authority,
            attestation_repository=att_repo,
            canonical_content_digest=FIXED_DIGEST,
            canonicalization_profile_digest=FIXED_DIGEST,
            adapter_implementation_digest=FIXED_DIGEST,
        )
    if evidence_commitments is None:
        raise ValueError("evidence_commitments required when issued is supplied")
    return EvidenceSealManifestDraftV2(
        construct_freeze_digest=construct_digest,
        episode_id=episode_id,
        issued_occurrence=issued,
        evidence_commitments=evidence_commitments,
        condition_neutral_evidence_availability=sample_availability(),
        immediate_parents=(sample_construct_parent(p0_repository),),
        responsible_role="evidence_capture",
        created_at=CREATED_AT,
        lineage_edges=lineage_edges or [],
    )


def sample_seal_manifest(**kwargs) -> EvidenceSealManifestV2:
    return sample_sealed_authority(**kwargs).manifest


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
    child_occurrence,
    parent_occurrence,
    from_instance: str,
    to_instance: str,
    lineage_id: str = "lineage-1",
    lineage_repository: LineageAttestationRepository,
) -> LineageEdgeV2:
    artifact = seal_lineage_attestation(
        logical_lineage_id=lineage_id,
        relation_kind=LineageRelationKind.CLONE,
        child_occurrence=child_occurrence,
        parent_occurrence=parent_occurrence,
        issuer_identity="lineage-issuer-v1",
        responsible_role="lineage_issuer",
        created_at=CREATED_AT,
        seal_time=SEAL_TIME,
    )
    lineage_repository.register(artifact)
    return LineageEdgeV2(
        logical_lineage_id=lineage_id,
        from_physical_instance_id=from_instance,
        to_physical_instance_id=to_instance,
        relation_kind=LineageRelationKind.CLONE,
        issuer_attested=True,
        child_occurrence_digest=occurrence_commitment_digest(child_occurrence),
        parent_occurrence_digest=occurrence_commitment_digest(parent_occurrence),
        attestation_evidence_digest=artifact.attestation_evidence_digest(),
    )

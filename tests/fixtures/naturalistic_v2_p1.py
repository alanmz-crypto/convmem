"""Hermetic fixtures for Naturalistic V2 P1 source-backed authority tests."""

# Contract fixtures intentionally mirror serialized authority shapes.
# pylint: disable=duplicate-code

from __future__ import annotations

from eval_naturalistic.base import StructuralContractError
from eval_naturalistic.v2.authority_issuance import (
    EvidenceSealManifestDraftV2,
    ImmediateParentBindingV2,
    IssuanceAuthorityRepository,
    SealedP1AuthorityV2,
    issue_occurrence_reference,
)
from eval_naturalistic.v2.authority_substrate import _provision_host_authority_source
from eval_naturalistic.v2.capture_attestation import CaptureAttestationRepository
from eval_naturalistic.v2.capture_attestation_issuance import issue_capture_attestation
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
from eval_naturalistic.v2.issuer_attestation_capability import (
    IssuerCaptureAttestationCapabilityRepository,
    mint_issuer_capture_attestation_capability,
)
from eval_naturalistic.v2.source_issuer_authority import (
    SourceIssuerGrantRepository,
    build_source_issuer_grant_record,
)
from tests import _HOST_BOOTSTRAP_SECRET

FIXED_DIGEST = "a" * 64
ALT_DIGEST = "b" * 64
CREATED_AT = "2026-08-31T00:00:00Z"
SEAL_TIME = "2026-08-31T00:00:01Z"
DEFAULT_ISSUER_IDENTITY = "capture-attestor-v1"
DEFAULT_RAW_RECORD_DIGEST = "c" * 64
PLACEHOLDER_ATTESTATION_DIGEST = "f" * 64


class FixtureAuthoritySource:
    """Test-only stand-in for the host-owned authority substrate.

    The production API has no record-to-authority factory.  This source is
    kept outside the portable claim graph and is deliberately the only place
    from which the fixture's P0, capability, attestation, capture, and
    issuance records resolve as study authority.
    """

    def __init__(self) -> None:
        _provision_host_authority_source(
            self,
            bootstrap_secret=_HOST_BOOTSTRAP_SECRET,
        )
        self.construct_freeze_repository = None
        self.capability_repository = None
        self.attestation_repository = None
        self.issuance_repository = None
        self._captures = {}

    def resolve_construct_freeze(self, *, artifact_id: str, content_digest: str):
        if self.construct_freeze_repository is None:
            raise StructuralContractError("fixture authority: construct freeze unavailable")
        return self.construct_freeze_repository.resolve(
            artifact_id=artifact_id, content_digest=content_digest
        )

    def resolve_issuer_capability(
        self, *, issuer_identity: str, issuer_grant_digest: str, construct_freeze_digest: str
    ):
        if self.capability_repository is None:
            raise StructuralContractError("fixture authority: capability unavailable")
        capability = self.capability_repository.resolve(
            issuer_identity=issuer_identity,
            issuer_grant_digest=issuer_grant_digest,
        )
        if capability.construct_freeze_digest != construct_freeze_digest:
            raise StructuralContractError("fixture authority: capability freeze mismatch")
        return capability

    def resolve_capture_attestation(self, attestation_digest: str):
        if self.attestation_repository is None:
            raise StructuralContractError("fixture authority: attestation unavailable")
        return self.attestation_repository.resolve(attestation_digest)

    def resolve_source_capture(self, source_capture_digest: str):
        capture = self._captures.get(source_capture_digest)
        if capture is None:
            raise StructuralContractError("fixture authority: source capture unavailable")
        return capture

    def resolve_issuance(self, issuance_digest: str):
        if self.issuance_repository is None:
            raise StructuralContractError("fixture authority: issuance unavailable")
        return self.issuance_repository.resolve(issuance_digest)

    def register_source_capture(self, capture) -> None:
        self._captures[capture.source_evidence_digest()] = capture

    def register_issuance_repository(self, repository) -> None:
        self.issuance_repository = repository


def default_study_issuer_grant_record(
    *,
    issuer_identity: str = DEFAULT_ISSUER_IDENTITY,
    source_system_id: str = "sys-crush",
    authority_scope_id: str = "scope-1",
) -> dict[str, str]:
    return build_source_issuer_grant_record(
        issuer_identity=issuer_identity,
        source_system_id=source_system_id,
        authority_scope_id=authority_scope_id,
    )


def sample_p0_repository(
    *,
    construct_policy_digest: str = FIXED_DIGEST,
    issuer_grant_record: dict[str, str] | None = None,
) -> InMemoryConstructFreezeRepository:
    source = FixtureAuthoritySource()
    repo = InMemoryConstructFreezeRepository(authority_source=source)
    grant_record = issuer_grant_record or default_study_issuer_grant_record()
    manifest = seal_construct_freeze_manifest(
        construct_policy_digest=construct_policy_digest,
        study_id="study-naturalistic-v2-test",
        responsible_role="study_owner",
        created_at=CREATED_AT,
        seal_time=SEAL_TIME,
        authorized_capture_issuer_grants=(grant_record,),
    )
    repo.register(manifest)
    source.construct_freeze_repository = repo
    return repo


def registered_construct_freeze(
    repo: InMemoryConstructFreezeRepository,
) -> ConstructFreezeManifestV2:
    return repo.manifests()[0]


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


def sample_issuer_capability_repository(
    p0_repository: InMemoryConstructFreezeRepository,
    *,
    issuer_identity: str = DEFAULT_ISSUER_IDENTITY,
) -> IssuerCaptureAttestationCapabilityRepository:
    manifest = registered_construct_freeze(p0_repository)
    construct_digest = construct_freeze_content_digest(p0_repository)
    grant_repo = SourceIssuerGrantRepository.from_construct_freeze(manifest)
    grant = grant_repo.resolve(
        issuer_identity=issuer_identity,
        source_system_id="sys-crush",
        authority_scope_id="scope-1",
    )
    capability = mint_issuer_capture_attestation_capability(
        grant,
        construct_freeze_digest=construct_digest,
    )
    repo = IssuerCaptureAttestationCapabilityRepository.from_capabilities(
        construct_freeze_digest=construct_digest,
        capabilities=(capability,),
        authority_source=p0_repository.authority_source(),
    )
    p0_repository.authority_source().capability_repository = repo
    return repo


def sample_capture_attestation_repository(
    *,
    p0_repository: InMemoryConstructFreezeRepository,
    physical_instance: str = "phys-a",
    native_record: str = "msg-1",
    revision: str = "rev-1",
    namespace: str = "ns-a",
    snapshot_id: str = "snap-1",
    issuer_identity: str = DEFAULT_ISSUER_IDENTITY,
) -> CaptureAttestationRepository:
    manifest = registered_construct_freeze(p0_repository)
    construct_digest = construct_freeze_content_digest(p0_repository)
    capability_repo = sample_issuer_capability_repository(
        p0_repository,
        issuer_identity=issuer_identity,
    )
    working = build_source_capture_body(
        physical_instance=physical_instance,
        native_record=native_record,
        revision=revision,
        namespace=namespace,
        snapshot_id=snapshot_id,
        issuer_capture_attestation=PLACEHOLDER_ATTESTATION_DIGEST,
    )
    temp_capture = seal_source_capture_package(working)
    repo = CaptureAttestationRepository(authority_source=p0_repository.authority_source())
    p0_repository.authority_source().attestation_repository = repo
    issue_capture_attestation(
        temp_capture,
        attestation_repository=repo,
        p0_repository=p0_repository,
        issuer_capability_repository=capability_repo,
        construct_freeze_digest=construct_digest,
        construct_freeze_artifact_id=manifest.header.artifact_id,
        responsible_role="capture_issuer",
        created_at=CREATED_AT,
        seal_time=SEAL_TIME,
    )
    return repo


def seal_verified_source_capture(
    body: dict,
    *,
    p0_repository: InMemoryConstructFreezeRepository,
    attestation_repository: CaptureAttestationRepository | None = None,
    issuer_capability_repository: IssuerCaptureAttestationCapabilityRepository | None = None,
) -> tuple:
    """Seal capture bytes and return (capture, attestation_repo, p0_repo, authority)."""

    manifest = registered_construct_freeze(p0_repository)
    construct_digest = construct_freeze_content_digest(p0_repository)
    capability_repo = issuer_capability_repository or sample_issuer_capability_repository(
        p0_repository
    )
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
        p0_repository=p0_repository,
        physical_instance=occurrence.physical_source_instance_id,
        native_record=occurrence.native_record_id,
        revision=occurrence.source_revision_or_asof_id,
        namespace=occurrence.occurrence_namespace_id,
        snapshot_id=snapshot_id,
    )
    attestation_digest = repo.artifacts()[0].attestation_evidence_digest()
    working = dict(body)
    working["issuer_capture_attestation"] = attestation_digest
    capture = seal_source_capture_package(working)
    source = p0_repository.authority_source()
    source.register_source_capture(capture)
    authority = verify_source_capture_authority(
        capture,
        attestation_repository=repo,
        issuer_capability_repository=capability_repo,
        p0_repository=p0_repository,
        construct_freeze_digest=construct_digest,
        construct_freeze_artifact_id=manifest.header.artifact_id,
    )
    return capture, repo, p0_repository, authority


def sample_verified_source_authority(**kwargs):
    p0_repo = sample_p0_repository()
    body = build_source_capture_body(**kwargs)
    _, _, _, authority = seal_verified_source_capture(body, p0_repository=p0_repo)
    return authority


def sample_issuance_repository(**kwargs) -> IssuanceAuthorityRepository:
    authority = sample_verified_source_authority(**kwargs)
    source_authority = authority.authority_source()
    repo = IssuanceAuthorityRepository(authority_source=source_authority)
    source_authority.register_issuance_repository(repo)
    issue_occurrence_reference(authority, issuance_repository=repo)
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
    adapter_implementation_digest: str = FIXED_DIGEST,
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
        capture, att_repo, _, authority = seal_verified_source_capture(capture_body, p0_repository=repo)
        issued = issue_occurrence_reference(authority, issuance_repository=issuance_repo)
    else:
        capture, att_repo, _, authority = seal_verified_source_capture(
            build_source_capture_body(),
            p0_repository=repo,
        )
        issued = issue_occurrence_reference(authority, issuance_repository=issuance_repo)
    capability_repo = sample_issuer_capability_repository(repo)
    commitments = bind_p1_evidence_commitments(
        sealed_capture=capture,
        verified_authority=authority,
        attestation_repository=att_repo,
        issuer_capability_repository=capability_repo,
        p0_repository=repo,
        construct_freeze_digest=construct_digest,
        construct_freeze_artifact_id=parent.parent_artifact_id,
        canonical_content_digest=canonical_content_digest,
        canonicalization_profile_digest=FIXED_DIGEST,
        adapter_implementation_digest=adapter_implementation_digest,
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
    parent = sample_construct_parent(p0_repository)
    if issued is None:
        capture, att_repo, _, authority = seal_verified_source_capture(
            build_source_capture_body(),
            p0_repository=p0_repository,
        )
        issued = issue_occurrence_reference(authority, issuance_repository=issuance_repository)
        capability_repo = sample_issuer_capability_repository(p0_repository)
        evidence_commitments = evidence_commitments or bind_p1_evidence_commitments(
            sealed_capture=capture,
            verified_authority=authority,
            attestation_repository=att_repo,
            issuer_capability_repository=capability_repo,
            p0_repository=p0_repository,
            construct_freeze_digest=construct_digest,
            construct_freeze_artifact_id=parent.parent_artifact_id,
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
        immediate_parents=(parent,),
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

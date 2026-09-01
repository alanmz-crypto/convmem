"""Capture attestation issuance — binds sealed capture to issuer capability authority."""

from __future__ import annotations

from eval_naturalistic.base import StructuralContractError
from eval_naturalistic.v2.capture_attestation import (
    CaptureAttestationArtifactV2,
    CaptureAttestationRepository,
    seal_authorized_capture_attestation,
)
from eval_naturalistic.v2.identity import occurrence_reference_from_fields
from eval_naturalistic.v2.issuer_attestation_capability import (
    IssuerCaptureAttestationCapabilityRepository,
    reverify_issuer_capture_attestation_capability,
)
from eval_naturalistic.v2.p0_construct import (
    ConstructFreezeAuthorityRepository,
    verify_construct_freeze_parent_binding,
)
from eval_naturalistic.v2.source_issuer_authority import SourceIssuerGrantRepository
from eval_naturalistic.v2.authority_substrate import resolve_shared_authority_source, same_authority_object


def issue_capture_attestation(  # pylint: disable=too-many-arguments
    sealed_capture: object,
    *,
    attestation_repository: CaptureAttestationRepository,
    p0_repository: ConstructFreezeAuthorityRepository,
    issuer_capability_repository: IssuerCaptureAttestationCapabilityRepository,
    construct_freeze_digest: str,
    construct_freeze_artifact_id: str,
    responsible_role: str,
    created_at: str,
    seal_time: str,
    authority_source: object | None = None,
) -> CaptureAttestationArtifactV2:
    """Issue capture attestation only with issuer capability — grant metadata alone is insufficient."""

    from eval_naturalistic.v2.source_authority import SealedSourceCapturePackageV2

    if not isinstance(sealed_capture, SealedSourceCapturePackageV2):
        raise TypeError("issue_capture_attestation requires SealedSourceCapturePackageV2")

    source = resolve_shared_authority_source(
        explicit=authority_source,
        repositories=(p0_repository, issuer_capability_repository, attestation_repository),
    )

    manifest = verify_construct_freeze_parent_binding(
        parent_kind="construct_freeze",
        parent_artifact_id=construct_freeze_artifact_id,
        parent_digest=construct_freeze_digest,
        construct_freeze_digest=construct_freeze_digest,
        repository=p0_repository,
        authority_source=source,
    )
    issuer_grant_repository = SourceIssuerGrantRepository.from_construct_freeze(manifest)
    fields = sealed_capture.occurrence_fields()
    occurrence = occurrence_reference_from_fields(fields)
    grant = issuer_grant_repository.resolve_for_occurrence(occurrence)
    capability = issuer_capability_repository.resolve(
        issuer_identity=grant.issuer_identity,
        issuer_grant_digest=grant.grant_digest,
    )
    trusted_capability = source.resolve_issuer_capability(
        issuer_identity=grant.issuer_identity,
        issuer_grant_digest=grant.grant_digest,
        construct_freeze_digest=construct_freeze_digest,
    )
    same_authority_object(
        capability,
        trusted_capability,
        message="capture attestation: capability is not independently resolved",
    )
    verified_capability = reverify_issuer_capture_attestation_capability(capability)
    if verified_capability.issuer_grant_digest != grant.grant_digest:
        raise StructuralContractError("capture attestation: issuer grant/capability mismatch")
    if verified_capability.issuer_identity != grant.issuer_identity:
        raise StructuralContractError("capture attestation: issuer identity mismatch with capability")
    if verified_capability.construct_freeze_digest != construct_freeze_digest:
        raise StructuralContractError("capture attestation: capability freeze mismatch")
    artifact = seal_authorized_capture_attestation(
        grant=grant,
        issuer_attestation_capability_digest=verified_capability.capability_digest,
        construct_freeze_digest=construct_freeze_digest,
        construct_freeze_artifact_id=construct_freeze_artifact_id,
        source_capture_digest=sealed_capture.source_evidence_digest(),
        raw_record_digest=sealed_capture.capture_body["raw_record_digest"],
        occurrence_reference=occurrence,
        evidence_snapshot_id=sealed_capture.evidence_snapshot_id(),
        responsible_role=responsible_role,
        created_at=created_at,
        seal_time=seal_time,
    )
    return attestation_repository.commit_authorized_attestation(
        artifact,
        issuer_grant_repository=issuer_grant_repository,
        construct_freeze_digest=construct_freeze_digest,
        construct_freeze_artifact_id=construct_freeze_artifact_id,
    )

"""P1 evidence commitments bound to verified source capture authority."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any

from eval_naturalistic.base import StructuralContractError
from eval_naturalistic.digest import canonical_artifact_bytes
from eval_naturalistic.v2.capture_attestation import CaptureAttestationRepository
from eval_naturalistic.v2.identity import OccurrenceReferenceV2, digest_hex
from eval_naturalistic.v2.issuer_attestation_capability import (
    IssuerCaptureAttestationCapabilityRepository,
)
from eval_naturalistic.v2.p0_construct import ConstructFreezeAuthorityRepository
from eval_naturalistic.v2.source_authority import (
    SealedSourceCapturePackageV2,
    VerifiedSourceAuthorityV2,
    reverify_source_authority_record,
    verify_source_capture_authority,
)


def compute_source_and_snapshot_identity_digest(
    *,
    occurrence: OccurrenceReferenceV2,
    evidence_snapshot_id: str,
) -> str:
    body = {
        "occurrence_reference": occurrence.to_dict(),
        "evidence_snapshot_id": evidence_snapshot_id,
    }
    return hashlib.sha256(canonical_artifact_bytes(body)).hexdigest()


def compute_evidence_complete_envelope_digest(
    *,
    source_capture_digest: str,
    source_authority_digest: str,
    raw_record_digest: str,
    canonical_content_digest: str,
    canonicalization_profile_digest: str,
    adapter_implementation_digest: str,
    attachment_reference_inventory_digest: str | None,
    source_and_snapshot_identity_digest: str | None,
) -> str:
    body: dict[str, Any] = {
        "source_capture_digest": source_capture_digest,
        "source_authority_digest": source_authority_digest,
        "raw_record_digest": raw_record_digest,
        "canonical_content_digest": canonical_content_digest,
        "canonicalization_profile_digest": canonicalization_profile_digest,
        "adapter_implementation_digest": adapter_implementation_digest,
    }
    if attachment_reference_inventory_digest is not None:
        body["attachment_reference_inventory_digest"] = attachment_reference_inventory_digest
    if source_and_snapshot_identity_digest is not None:
        body["source_and_snapshot_identity_digest"] = source_and_snapshot_identity_digest
    return hashlib.sha256(canonical_artifact_bytes(body)).hexdigest()


@dataclass(frozen=True)
class VerifiedP1EvidenceCommitmentsV2:
    """Evidence commitments derived from verified capture — not caller restated."""

    source_capture_digest: str
    source_authority_digest: str
    evidence_snapshot_id: str
    raw_record_digest: str
    evidence_complete_envelope_digest: str
    canonical_content_digest: str
    canonicalization_profile_digest: str
    adapter_implementation_digest: str
    attachment_reference_inventory_digest: str | None
    source_and_snapshot_identity_digest: str | None

    def verify_against_manifest_fields(
        self,
        *,
        source_authority_digest: str,
        evidence_snapshot_id: str,
        evidence_complete_envelope_digest: str,
        canonical_content_digest: str,
        canonicalization_profile_digest: str,
        adapter_implementation_digest: str,
        raw_record_digest: str | None,
        attachment_reference_inventory_digest: str | None,
        source_and_snapshot_identity_digest: str | None,
    ) -> None:
        if self.source_authority_digest != source_authority_digest:
            raise StructuralContractError("P1 authority: source authority digest mismatch")
        if self.evidence_snapshot_id != evidence_snapshot_id:
            raise StructuralContractError("P1 authority: evidence snapshot mismatch")
        if self.evidence_complete_envelope_digest != evidence_complete_envelope_digest:
            raise StructuralContractError("P1 authority: evidence envelope commitment mismatch")
        if self.canonical_content_digest != canonical_content_digest:
            raise StructuralContractError("P1 authority: canonical content commitment mismatch")
        if self.canonicalization_profile_digest != canonicalization_profile_digest:
            raise StructuralContractError("P1 authority: canonicalization profile mismatch")
        if self.adapter_implementation_digest != adapter_implementation_digest:
            raise StructuralContractError("P1 authority: adapter implementation mismatch")
        if raw_record_digest is None or self.raw_record_digest != raw_record_digest:
            raise StructuralContractError("P1 authority: raw record commitment mismatch")
        if self.attachment_reference_inventory_digest != attachment_reference_inventory_digest:
            raise StructuralContractError("P1 authority: attachment inventory commitment mismatch")
        if self.source_and_snapshot_identity_digest != source_and_snapshot_identity_digest:
            raise StructuralContractError("P1 authority: source/snapshot identity mismatch")


def bind_p1_evidence_commitments(
    *,
    sealed_capture: SealedSourceCapturePackageV2,
    verified_authority: VerifiedSourceAuthorityV2,
    attestation_repository: CaptureAttestationRepository,
    issuer_capability_repository: IssuerCaptureAttestationCapabilityRepository,
    p0_repository: ConstructFreezeAuthorityRepository,
    construct_freeze_digest: str,
    construct_freeze_artifact_id: str,
    canonical_content_digest: str,
    canonicalization_profile_digest: str,
    adapter_implementation_digest: str,
    attachment_reference_inventory_digest: str | None = None,
) -> VerifiedP1EvidenceCommitmentsV2:
    """Derive P1 evidence commitments only from independently verified capture."""

    reparsed = verify_source_capture_authority(
        sealed_capture.canonical_bytes,
        attestation_repository=attestation_repository,
        issuer_capability_repository=issuer_capability_repository,
        p0_repository=p0_repository,
        construct_freeze_digest=construct_freeze_digest,
        construct_freeze_artifact_id=construct_freeze_artifact_id,
    )
    authority = reverify_source_authority_record(verified_authority)
    if reparsed.authority_record_digest != authority.authority_record_digest:
        raise StructuralContractError("evidence commitments: source authority mismatch")
    if reparsed.source_capture_digest != authority.source_capture_digest:
        raise StructuralContractError("evidence commitments: source capture digest mismatch")
    raw_record_digest = digest_hex(
        sealed_capture.capture_body["raw_record_digest"], "raw_record_digest"
    )
    snapshot_id = authority.evidence_snapshot_id
    source_snapshot_digest = compute_source_and_snapshot_identity_digest(
        occurrence=authority.occurrence_reference,
        evidence_snapshot_id=snapshot_id,
    )
    envelope_digest = compute_evidence_complete_envelope_digest(
        source_capture_digest=authority.source_capture_digest,
        source_authority_digest=authority.authority_record_digest,
        raw_record_digest=raw_record_digest,
        canonical_content_digest=digest_hex(canonical_content_digest, "canonical_content_digest"),
        canonicalization_profile_digest=digest_hex(
            canonicalization_profile_digest, "canonicalization_profile_digest"
        ),
        adapter_implementation_digest=digest_hex(
            adapter_implementation_digest, "adapter_implementation_digest"
        ),
        attachment_reference_inventory_digest=(
            digest_hex(
                attachment_reference_inventory_digest,
                "attachment_reference_inventory_digest",
            )
            if attachment_reference_inventory_digest is not None
            else None
        ),
        source_and_snapshot_identity_digest=source_snapshot_digest,
    )
    return VerifiedP1EvidenceCommitmentsV2(
        source_capture_digest=authority.source_capture_digest,
        source_authority_digest=authority.authority_record_digest,
        evidence_snapshot_id=snapshot_id,
        raw_record_digest=raw_record_digest,
        evidence_complete_envelope_digest=envelope_digest,
        canonical_content_digest=digest_hex(canonical_content_digest, "canonical_content_digest"),
        canonicalization_profile_digest=digest_hex(
            canonicalization_profile_digest, "canonicalization_profile_digest"
        ),
        adapter_implementation_digest=digest_hex(
            adapter_implementation_digest, "adapter_implementation_digest"
        ),
        attachment_reference_inventory_digest=(
            digest_hex(
                attachment_reference_inventory_digest,
                "attachment_reference_inventory_digest",
            )
            if attachment_reference_inventory_digest is not None
            else None
        ),
        source_and_snapshot_identity_digest=source_snapshot_digest,
    )


def recompute_evidence_commitments_from_manifest(
    *,
    source_capture_digest: str,
    source_authority_digest: str,
    occurrence: OccurrenceReferenceV2,
    evidence_snapshot_id: str,
    raw_record_digest: str,
    canonical_content_digest: str,
    canonicalization_profile_digest: str,
    adapter_implementation_digest: str,
    attachment_reference_inventory_digest: str | None,
) -> VerifiedP1EvidenceCommitmentsV2:
    """Recompute bound commitments during independent P1 verification."""

    source_snapshot_digest = compute_source_and_snapshot_identity_digest(
        occurrence=occurrence,
        evidence_snapshot_id=evidence_snapshot_id,
    )
    envelope_digest = compute_evidence_complete_envelope_digest(
        source_capture_digest=source_capture_digest,
        source_authority_digest=source_authority_digest,
        raw_record_digest=raw_record_digest,
        canonical_content_digest=canonical_content_digest,
        canonicalization_profile_digest=canonicalization_profile_digest,
        adapter_implementation_digest=adapter_implementation_digest,
        attachment_reference_inventory_digest=attachment_reference_inventory_digest,
        source_and_snapshot_identity_digest=source_snapshot_digest,
    )
    return VerifiedP1EvidenceCommitmentsV2(
        source_capture_digest=source_capture_digest,
        source_authority_digest=source_authority_digest,
        evidence_snapshot_id=evidence_snapshot_id,
        raw_record_digest=raw_record_digest,
        evidence_complete_envelope_digest=envelope_digest,
        canonical_content_digest=canonical_content_digest,
        canonicalization_profile_digest=canonicalization_profile_digest,
        adapter_implementation_digest=adapter_implementation_digest,
        attachment_reference_inventory_digest=attachment_reference_inventory_digest,
        source_and_snapshot_identity_digest=source_snapshot_digest,
    )

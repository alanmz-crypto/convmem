"""Independent issuer attestation artifacts for sealed source capture authority."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any

from eval_naturalistic.base import (
    ArtifactHeaderV1,
    StructuralContractError,
    _require_dict,
    _require_no_unknown_props,
    _require_str,
    strip_digest_metadata,
)
from eval_naturalistic.digest import canonical_artifact_bytes
from eval_naturalistic.v2.contracts import ARTIFACT_ID_PREFIX_V2, SCHEMA_NAMESPACE_V2
from eval_naturalistic.v2.identity import OccurrenceReferenceV2, digest_hex
from eval_naturalistic.v2.source_issuer_authority import (
    SourceIssuerGrantRepository,
    SourceIssuerGrantV2,
    reverify_source_issuer_grant,
)

CAPTURE_ATTESTATION_SCHEMA = f"{SCHEMA_NAMESPACE_V2}/capture-attestation-v2"


@dataclass(frozen=True)
class CaptureAttestationArtifactV2:
    """Sealed issuer attestation backing source-capture occurrence authority."""

    header: ArtifactHeaderV1
    occurrence_reference: OccurrenceReferenceV2
    evidence_snapshot_id: str
    issuer_identity: str
    issuer_grant_digest: str
    issuer_attestation_capability_digest: str

    _FIELDS = {
        "header",
        "occurrence_reference",
        "evidence_snapshot_id",
        "issuer_identity",
        "issuer_grant_digest",
        "issuer_attestation_capability_digest",
    }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CaptureAttestationArtifactV2":
        data = _require_dict(data, "CaptureAttestationArtifactV2")
        _require_no_unknown_props(data, cls._FIELDS, "CaptureAttestationArtifactV2")
        header = ArtifactHeaderV1.from_dict(_require_dict(data["header"], "header"))
        if header.schema_version != CAPTURE_ATTESTATION_SCHEMA:
            raise StructuralContractError("capture attestation: wrong schema_version")
        return cls(
            header=header,
            occurrence_reference=OccurrenceReferenceV2.from_dict(
                _require_dict(data["occurrence_reference"], "occurrence_reference")
            ),
            evidence_snapshot_id=_require_str(data["evidence_snapshot_id"], "evidence_snapshot_id"),
            issuer_identity=_require_str(data["issuer_identity"], "issuer_identity"),
            issuer_grant_digest=_require_str(data["issuer_grant_digest"], "issuer_grant_digest"),
            issuer_attestation_capability_digest=_require_str(
                data["issuer_attestation_capability_digest"],
                "issuer_attestation_capability_digest",
            ),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "header": self.header.to_dict(),
            "occurrence_reference": self.occurrence_reference.to_dict(),
            "evidence_snapshot_id": self.evidence_snapshot_id,
            "issuer_identity": self.issuer_identity,
            "issuer_grant_digest": self.issuer_grant_digest,
            "issuer_attestation_capability_digest": self.issuer_attestation_capability_digest,
        }

    def attestation_evidence_digest(self) -> str:
        body = {
            "occurrence_reference": self.occurrence_reference.to_dict(),
            "evidence_snapshot_id": self.evidence_snapshot_id,
            "issuer_identity": self.issuer_identity,
            "issuer_grant_digest": self.issuer_grant_digest,
            "issuer_attestation_capability_digest": self.issuer_attestation_capability_digest,
        }
        return hashlib.sha256(canonical_artifact_bytes(body)).hexdigest()


def _derive_artifact_id(*, schema: str, content_digest: str) -> str:
    kind = schema.rsplit("/", 1)[-1]
    return f"{ARTIFACT_ID_PREFIX_V2}{kind}_{content_digest}"


def seal_authorized_capture_attestation(
    *,
    grant: SourceIssuerGrantV2,
    issuer_attestation_capability_digest: str,
    occurrence_reference: OccurrenceReferenceV2,
    evidence_snapshot_id: str,
    responsible_role: str,
    created_at: str,
    seal_time: str,
) -> CaptureAttestationArtifactV2:
    verified_grant = reverify_source_issuer_grant(grant)
    capability_digest = digest_hex(
        issuer_attestation_capability_digest,
        "issuer_attestation_capability_digest",
    )
    if verified_grant.issuer_identity == "":
        raise StructuralContractError("capture attestation: missing issuer identity")
    if verified_grant.source_system_id != occurrence_reference.source_system_id:
        raise StructuralContractError("capture attestation: source system mismatch with grant")
    if verified_grant.authority_scope_id != occurrence_reference.authority_scope_id:
        raise StructuralContractError("capture attestation: authority scope mismatch with grant")
    placeholder_header = ArtifactHeaderV1(
        artifact_id="pending",
        schema_version=CAPTURE_ATTESTATION_SCHEMA,
        parent_artifact_id=None,
        parent_digest=None,
        created_at=created_at,
        seal_time=None,
        responsible_role=responsible_role,
        content_digest=None,
        sealed=False,
    )
    body = {
        "header": placeholder_header.to_dict(),
        "occurrence_reference": occurrence_reference.to_dict(),
        "evidence_snapshot_id": evidence_snapshot_id,
        "issuer_identity": verified_grant.issuer_identity,
        "issuer_grant_digest": verified_grant.grant_digest,
        "issuer_attestation_capability_digest": capability_digest,
    }
    content_digest = hashlib.sha256(canonical_artifact_bytes(strip_digest_metadata(body))).hexdigest()
    artifact_id = _derive_artifact_id(schema=CAPTURE_ATTESTATION_SCHEMA, content_digest=content_digest)
    header = ArtifactHeaderV1(
        artifact_id=artifact_id,
        schema_version=CAPTURE_ATTESTATION_SCHEMA,
        parent_artifact_id=None,
        parent_digest=None,
        created_at=created_at,
        seal_time=seal_time,
        responsible_role=responsible_role,
        content_digest=content_digest,
        sealed=True,
    )
    artifact = CaptureAttestationArtifactV2(
        header=header,
        occurrence_reference=occurrence_reference,
        evidence_snapshot_id=evidence_snapshot_id,
        issuer_identity=verified_grant.issuer_identity,
        issuer_grant_digest=verified_grant.grant_digest,
        issuer_attestation_capability_digest=capability_digest,
    )
    verify_capture_attestation_artifact(artifact)
    return artifact


def verify_capture_attestation_artifact(
    artifact: CaptureAttestationArtifactV2,
) -> CaptureAttestationArtifactV2:
    header = artifact.header
    if not header.sealed:
        raise StructuralContractError("capture attestation: sealed=false")
    if header.schema_version != CAPTURE_ATTESTATION_SCHEMA:
        raise StructuralContractError("capture attestation: wrong artifact kind")
    recomputed = hashlib.sha256(
        canonical_artifact_bytes(strip_digest_metadata(artifact.to_dict()))
    ).hexdigest()
    if recomputed != header.content_digest:
        raise StructuralContractError("capture attestation: content digest mismatch")
    expected_id = _derive_artifact_id(schema=CAPTURE_ATTESTATION_SCHEMA, content_digest=recomputed)
    if header.artifact_id != expected_id:
        raise StructuralContractError("capture attestation: artifact ID mismatch")
    if artifact.issuer_identity == "":
        raise StructuralContractError("capture attestation: missing issuer identity")
    if not artifact.issuer_grant_digest:
        raise StructuralContractError("capture attestation: missing issuer grant digest")
    if not artifact.issuer_attestation_capability_digest:
        raise StructuralContractError("capture attestation: missing issuer attestation capability digest")
    return artifact


class CaptureAttestationRepository:
    """Portable capture-attestation substrate — artifacts are committed, not self-registered."""

    def __init__(self) -> None:
        self._artifacts: dict[str, CaptureAttestationArtifactV2] = {}

    @classmethod
    def from_artifacts(
        cls, artifacts: tuple[CaptureAttestationArtifactV2, ...]
    ) -> "CaptureAttestationRepository":
        repo = cls()
        for artifact in artifacts:
            verified = verify_capture_attestation_artifact(artifact)
            repo._artifacts[verified.attestation_evidence_digest()] = verified
        return repo

    def artifacts(self) -> tuple[CaptureAttestationArtifactV2, ...]:
        return tuple(self._artifacts.values())

    def commit_authorized_attestation(
        self,
        artifact: CaptureAttestationArtifactV2,
        *,
        issuer_grant_repository: SourceIssuerGrantRepository,
        construct_freeze_digest: str,
    ) -> CaptureAttestationArtifactV2:
        """Commit attestation only when issuer grant resolves from construct freeze."""

        if issuer_grant_repository.construct_freeze_digest() != construct_freeze_digest:
            raise StructuralContractError("capture attestation: construct-freeze digest mismatch")
        verified = verify_capture_attestation_artifact(artifact)
        occurrence = verified.occurrence_reference
        grant = issuer_grant_repository.resolve(
            issuer_identity=verified.issuer_identity,
            source_system_id=occurrence.source_system_id,
            authority_scope_id=occurrence.authority_scope_id,
        )
        if grant.grant_digest != verified.issuer_grant_digest:
            raise StructuralContractError("capture attestation: issuer grant digest mismatch")
        digest = verified.attestation_evidence_digest()
        self._artifacts[digest] = verified
        return verified

    def resolve(self, attestation_digest: str) -> CaptureAttestationArtifactV2:
        artifact = self._artifacts.get(attestation_digest)
        if artifact is None:
            raise StructuralContractError("capture attestation artifact not found")
        return verify_capture_attestation_artifact(artifact)

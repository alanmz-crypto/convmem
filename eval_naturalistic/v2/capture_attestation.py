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
from eval_naturalistic.v2.identity import OccurrenceReferenceV2

CAPTURE_ATTESTATION_SCHEMA = f"{SCHEMA_NAMESPACE_V2}/capture-attestation-v2"


@dataclass(frozen=True)
class CaptureAttestationArtifactV2:
    """Sealed issuer attestation backing source-capture occurrence authority."""

    header: ArtifactHeaderV1
    occurrence_reference: OccurrenceReferenceV2
    evidence_snapshot_id: str
    issuer_identity: str

    _FIELDS = {
        "header",
        "occurrence_reference",
        "evidence_snapshot_id",
        "issuer_identity",
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
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "header": self.header.to_dict(),
            "occurrence_reference": self.occurrence_reference.to_dict(),
            "evidence_snapshot_id": self.evidence_snapshot_id,
            "issuer_identity": self.issuer_identity,
        }

    def attestation_evidence_digest(self) -> str:
        body = {
            "occurrence_reference": self.occurrence_reference.to_dict(),
            "evidence_snapshot_id": self.evidence_snapshot_id,
            "issuer_identity": self.issuer_identity,
        }
        return hashlib.sha256(canonical_artifact_bytes(body)).hexdigest()


def _derive_artifact_id(*, schema: str, content_digest: str) -> str:
    kind = schema.rsplit("/", 1)[-1]
    return f"{ARTIFACT_ID_PREFIX_V2}{kind}_{content_digest}"


def seal_capture_attestation(
    *,
    occurrence_reference: OccurrenceReferenceV2,
    evidence_snapshot_id: str,
    issuer_identity: str,
    responsible_role: str,
    created_at: str,
    seal_time: str,
) -> CaptureAttestationArtifactV2:
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
        "issuer_identity": issuer_identity,
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
        issuer_identity=issuer_identity,
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
    return artifact


class CaptureAttestationRepository:
    def __init__(self) -> None:
        self._artifacts: dict[str, CaptureAttestationArtifactV2] = {}

    def register(self, artifact: CaptureAttestationArtifactV2) -> CaptureAttestationArtifactV2:
        verified = verify_capture_attestation_artifact(artifact)
        digest = verified.attestation_evidence_digest()
        self._artifacts[digest] = verified
        return verified

    def resolve(self, attestation_digest: str) -> CaptureAttestationArtifactV2:
        artifact = self._artifacts.get(attestation_digest)
        if artifact is None:
            raise StructuralContractError("capture attestation artifact not found")
        return verify_capture_attestation_artifact(artifact)


def verify_capture_attestation_binding(
    *,
    attestation_digest: str,
    occurrence_reference: OccurrenceReferenceV2,
    evidence_snapshot_id: str,
    repository: CaptureAttestationRepository,
) -> CaptureAttestationArtifactV2:
    artifact = repository.resolve(attestation_digest)
    if not artifact.occurrence_reference.same_occurrence_as(occurrence_reference):
        raise StructuralContractError("capture attestation occurrence mismatch")
    if artifact.evidence_snapshot_id != evidence_snapshot_id:
        raise StructuralContractError("capture attestation evidence snapshot mismatch")
    if artifact.attestation_evidence_digest() != attestation_digest:
        raise StructuralContractError("capture attestation digest mismatch")
    return artifact

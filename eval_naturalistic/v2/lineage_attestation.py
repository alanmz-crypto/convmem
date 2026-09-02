"""Independent lineage attestation artifacts for issuer-attested edges."""

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
from eval_naturalistic.v2.identity import LineageEdgeV2, LineageRelationKind, OccurrenceReferenceV2, digest_hex

LINEAGE_ATTESTATION_SCHEMA = f"{SCHEMA_NAMESPACE_V2}/lineage-attestation-v2"


def occurrence_commitment_digest(occurrence: OccurrenceReferenceV2) -> str:
    return hashlib.sha256(canonical_artifact_bytes(occurrence.to_dict())).hexdigest()


@dataclass(frozen=True)
class LineageAttestationArtifactV2:
    """Sealed issuer attestation backing a lineage edge."""

    header: ArtifactHeaderV1
    logical_lineage_id: str
    relation_kind: LineageRelationKind
    child_occurrence: OccurrenceReferenceV2
    parent_occurrence: OccurrenceReferenceV2
    issuer_identity: str

    _FIELDS = {
        "header",
        "logical_lineage_id",
        "relation_kind",
        "child_occurrence",
        "parent_occurrence",
        "issuer_identity",
    }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "LineageAttestationArtifactV2":
        data = _require_dict(data, "LineageAttestationArtifactV2")
        _require_no_unknown_props(data, cls._FIELDS, "LineageAttestationArtifactV2")
        header = ArtifactHeaderV1.from_dict(_require_dict(data["header"], "header"))
        if header.schema_version != LINEAGE_ATTESTATION_SCHEMA:
            raise StructuralContractError("lineage attestation: wrong schema_version")
        return cls(
            header=header,
            logical_lineage_id=_require_str(data["logical_lineage_id"], "logical_lineage_id"),
            relation_kind=LineageRelationKind(data["relation_kind"]),
            child_occurrence=OccurrenceReferenceV2.from_dict(
                _require_dict(data["child_occurrence"], "child_occurrence")
            ),
            parent_occurrence=OccurrenceReferenceV2.from_dict(
                _require_dict(data["parent_occurrence"], "parent_occurrence")
            ),
            issuer_identity=_require_str(data["issuer_identity"], "issuer_identity"),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "header": self.header.to_dict(),
            "logical_lineage_id": self.logical_lineage_id,
            "relation_kind": self.relation_kind.value,
            "child_occurrence": self.child_occurrence.to_dict(),
            "parent_occurrence": self.parent_occurrence.to_dict(),
            "issuer_identity": self.issuer_identity,
        }

    def attestation_evidence_digest(self) -> str:
        body = {
            "logical_lineage_id": self.logical_lineage_id,
            "relation_kind": self.relation_kind.value,
            "child_occurrence": self.child_occurrence.to_dict(),
            "parent_occurrence": self.parent_occurrence.to_dict(),
            "issuer_identity": self.issuer_identity,
        }
        return hashlib.sha256(canonical_artifact_bytes(body)).hexdigest()


def _derive_artifact_id(*, schema: str, content_digest: str) -> str:
    kind = schema.rsplit("/", 1)[-1]
    return f"{ARTIFACT_ID_PREFIX_V2}{kind}_{content_digest}"


def seal_lineage_attestation(
    *,
    logical_lineage_id: str,
    relation_kind: LineageRelationKind,
    child_occurrence: OccurrenceReferenceV2,
    parent_occurrence: OccurrenceReferenceV2,
    issuer_identity: str,
    responsible_role: str,
    created_at: str,
    seal_time: str,
) -> LineageAttestationArtifactV2:
    placeholder_header = ArtifactHeaderV1(
        artifact_id="pending",
        schema_version=LINEAGE_ATTESTATION_SCHEMA,
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
        "logical_lineage_id": logical_lineage_id,
        "relation_kind": relation_kind.value,
        "child_occurrence": child_occurrence.to_dict(),
        "parent_occurrence": parent_occurrence.to_dict(),
        "issuer_identity": issuer_identity,
    }
    content_digest = hashlib.sha256(canonical_artifact_bytes(strip_digest_metadata(body))).hexdigest()
    artifact_id = _derive_artifact_id(schema=LINEAGE_ATTESTATION_SCHEMA, content_digest=content_digest)
    header = ArtifactHeaderV1(
        artifact_id=artifact_id,
        schema_version=LINEAGE_ATTESTATION_SCHEMA,
        parent_artifact_id=None,
        parent_digest=None,
        created_at=created_at,
        seal_time=seal_time,
        responsible_role=responsible_role,
        content_digest=content_digest,
        sealed=True,
    )
    artifact = LineageAttestationArtifactV2(
        header=header,
        logical_lineage_id=logical_lineage_id,
        relation_kind=relation_kind,
        child_occurrence=child_occurrence,
        parent_occurrence=parent_occurrence,
        issuer_identity=issuer_identity,
    )
    verify_lineage_attestation_artifact(artifact)
    return artifact


def verify_lineage_attestation_artifact(
    artifact: LineageAttestationArtifactV2,
) -> LineageAttestationArtifactV2:
    header = artifact.header
    if not header.sealed:
        raise StructuralContractError("lineage attestation: sealed=false")
    if header.schema_version != LINEAGE_ATTESTATION_SCHEMA:
        raise StructuralContractError("lineage attestation: wrong artifact kind")
    recomputed = hashlib.sha256(
        canonical_artifact_bytes(strip_digest_metadata(artifact.to_dict()))
    ).hexdigest()
    if recomputed != header.content_digest:
        raise StructuralContractError("lineage attestation: content digest mismatch")
    expected_id = _derive_artifact_id(schema=LINEAGE_ATTESTATION_SCHEMA, content_digest=recomputed)
    if header.artifact_id != expected_id:
        raise StructuralContractError("lineage attestation: artifact ID mismatch")
    return artifact


class LineageAttestationRepository:
    def __init__(self) -> None:
        self._artifacts: dict[str, LineageAttestationArtifactV2] = {}

    def register(self, artifact: LineageAttestationArtifactV2) -> LineageAttestationArtifactV2:
        verified = verify_lineage_attestation_artifact(artifact)
        digest = verified.attestation_evidence_digest()
        self._artifacts[digest] = verified
        return verified

    def resolve(self, attestation_digest: str) -> LineageAttestationArtifactV2:
        artifact = self._artifacts.get(attestation_digest)
        if artifact is None:
            raise StructuralContractError("lineage attestation artifact not found")
        return verify_lineage_attestation_artifact(artifact)


def verify_lineage_edge_attestation(
    edge: LineageEdgeV2,
    *,
    child_occurrence: OccurrenceReferenceV2,
    parent_occurrence: OccurrenceReferenceV2,
    repository: LineageAttestationRepository,
) -> None:
    if not edge.issuer_attested:
        return
    if edge.attestation_evidence_digest is None:
        raise StructuralContractError("issuer_attested lineage requires attestation artifact")
    if edge.from_physical_instance_id != parent_occurrence.physical_source_instance_id:
        raise StructuralContractError(
            "lineage edge from_physical_instance_id must match parent occurrence"
        )
    if edge.to_physical_instance_id != child_occurrence.physical_source_instance_id:
        raise StructuralContractError(
            "lineage edge to_physical_instance_id must match child occurrence"
        )
    if not edge.preserves_physical_separation():
        raise StructuralContractError(
            "lineage edge must preserve physical instance separation"
        )
    artifact = repository.resolve(edge.attestation_evidence_digest)
    if artifact.logical_lineage_id != edge.logical_lineage_id:
        raise StructuralContractError("lineage attestation logical_lineage_id mismatch")
    if artifact.relation_kind != edge.relation_kind:
        raise StructuralContractError("lineage attestation relation_kind mismatch")
    if artifact.issuer_identity == "":
        raise StructuralContractError("lineage attestation missing issuer identity")
    child_digest = occurrence_commitment_digest(child_occurrence)
    parent_digest = occurrence_commitment_digest(parent_occurrence)
    if edge.child_occurrence_digest != child_digest:
        raise StructuralContractError("lineage attestation child occurrence mismatch")
    if edge.parent_occurrence_digest != parent_digest:
        raise StructuralContractError("lineage attestation parent occurrence mismatch")
    if artifact.child_occurrence.same_occurrence_as(child_occurrence) is False:
        raise StructuralContractError("lineage attestation child occurrence tuple mismatch")
    if artifact.parent_occurrence.same_occurrence_as(parent_occurrence) is False:
        raise StructuralContractError("lineage attestation parent occurrence tuple mismatch")
    if artifact.attestation_evidence_digest() != edge.attestation_evidence_digest:
        raise StructuralContractError("lineage attestation digest mismatch")

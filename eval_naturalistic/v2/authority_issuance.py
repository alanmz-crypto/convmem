"""Authoritative P1 occurrence issuance, seal finalization, and byte verification."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
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
from eval_naturalistic.v2.contracts import (
    ARTIFACT_ID_PREFIX_V2,
    EvidenceSealManifestV2,
    _ISSUANCE_TOKEN,
)
from eval_naturalistic.v2.evidence import ConditionNeutralEvidenceAvailabilityV2
from eval_naturalistic.v2.identity import (
    LineageEdgeV2,
    OccurrenceReferenceV2,
    digest_hex,
    reject_hash_or_locator_identity,
)

P1_ISSUER_MANIFEST_CLASS = "naturalistic_v2_p1_issuer_authority"
P1_ISSUER_REVISION_PREFIX = "nps2-p1-issuer/"
P1_STAGE = "P1_EVIDENCE_SEAL"
REQUIRED_IMMEDIATE_PARENT_KINDS = frozenset({"construct_freeze"})

_REPO_ROOT = Path(__file__).resolve().parents[2]
_P1_ISSUER_SEED_MODULES = (
    "eval_naturalistic/v2/authority_issuance.py",
    "eval_naturalistic/v2/identity.py",
    "eval_naturalistic/v2/contracts.py",
    "eval_naturalistic/v2/validators.py",
    "eval_naturalistic/v2/evidence.py",
    "eval_naturalistic/digest.py",
    "eval_naturalistic/base.py",
)


@dataclass(frozen=True)
class ImmediateParentBindingV2:
    parent_kind: str
    parent_artifact_id: str
    parent_digest: str
    _FIELDS = {"parent_kind", "parent_artifact_id", "parent_digest"}

    def to_dict(self) -> dict[str, str]:
        return {
            "parent_kind": self.parent_kind,
            "parent_artifact_id": self.parent_artifact_id,
            "parent_digest": self.parent_digest,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ImmediateParentBindingV2":
        data = _require_dict(data, "ImmediateParentBindingV2")
        _require_no_unknown_props(data, cls._FIELDS, "ImmediateParentBindingV2")
        return cls(
            parent_kind=_require_str(data["parent_kind"], "parent_kind"),
            parent_artifact_id=_require_str(data["parent_artifact_id"], "parent_artifact_id"),
            parent_digest=digest_hex(data["parent_digest"], "parent_digest"),
        )


@dataclass(frozen=True)
class OccurrenceIssuanceEvidenceV2:
    source_system_id: str
    tenant_or_realm_id: str
    authority_scope_id: str
    occurrence_namespace_id: str
    physical_source_instance_id: str
    native_id_namespace: str
    native_record_id: str
    source_revision_or_asof_id: str
    evidence_snapshot_id: str
    issuer_attestation_digest: str | None = None
    _FIELDS = frozenset({
        "source_system_id", "tenant_or_realm_id", "authority_scope_id",
        "occurrence_namespace_id", "physical_source_instance_id",
        "native_id_namespace", "native_record_id", "source_revision_or_asof_id",
        "evidence_snapshot_id", "issuer_attestation_digest",
    })

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "source_system_id": self.source_system_id,
            "tenant_or_realm_id": self.tenant_or_realm_id,
            "authority_scope_id": self.authority_scope_id,
            "occurrence_namespace_id": self.occurrence_namespace_id,
            "physical_source_instance_id": self.physical_source_instance_id,
            "native_id_namespace": self.native_id_namespace,
            "native_record_id": self.native_record_id,
            "source_revision_or_asof_id": self.source_revision_or_asof_id,
            "evidence_snapshot_id": self.evidence_snapshot_id,
        }
        if self.issuer_attestation_digest is not None:
            out["issuer_attestation_digest"] = self.issuer_attestation_digest
        return out

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "OccurrenceIssuanceEvidenceV2":
        data = _require_dict(data, "OccurrenceIssuanceEvidenceV2")
        _require_no_unknown_props(data, cls._FIELDS, "OccurrenceIssuanceEvidenceV2")
        reject_hash_or_locator_identity(data)
        attestation = data.get("issuer_attestation_digest")
        return cls(
            source_system_id=_require_str(data["source_system_id"], "source_system_id"),
            tenant_or_realm_id=_require_str(data["tenant_or_realm_id"], "tenant_or_realm_id"),
            authority_scope_id=_require_str(data["authority_scope_id"], "authority_scope_id"),
            occurrence_namespace_id=_require_str(data["occurrence_namespace_id"], "occurrence_namespace_id"),
            physical_source_instance_id=_require_str(data["physical_source_instance_id"], "physical_source_instance_id"),
            native_id_namespace=_require_str(data["native_id_namespace"], "native_id_namespace"),
            native_record_id=_require_str(data["native_record_id"], "native_record_id"),
            source_revision_or_asof_id=_require_str(data["source_revision_or_asof_id"], "source_revision_or_asof_id"),
            evidence_snapshot_id=_require_str(data["evidence_snapshot_id"], "evidence_snapshot_id"),
            issuer_attestation_digest=digest_hex(attestation, "issuer_attestation_digest") if attestation is not None else None,
        )


@dataclass(frozen=True)
class IssuedOccurrenceReferenceV2:
    occurrence_reference: OccurrenceReferenceV2
    issuance_digest: str
    issuer_implementation_revision: str
    evidence_snapshot_id: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "occurrence_reference": self.occurrence_reference.to_dict(),
            "issuance_digest": self.issuance_digest,
            "issuer_implementation_revision": self.issuer_implementation_revision,
            "evidence_snapshot_id": self.evidence_snapshot_id,
        }


def _hash_file(rel_path: str) -> str:
    return hashlib.sha256((_REPO_ROOT / rel_path).read_bytes()).hexdigest()


def build_p1_issuer_authority_manifest() -> dict[str, Any]:
    entries = [{"path": rel, "content_digest": _hash_file(rel)} for rel in _P1_ISSUER_SEED_MODULES]
    return {
        "manifest_class": P1_ISSUER_MANIFEST_CLASS,
        "manifest_version": 1,
        "stage": P1_STAGE,
        "seed_modules": list(_P1_ISSUER_SEED_MODULES),
        "governed_files": entries,
    }


def clear_p1_issuer_revision_cache() -> None:
    _cached_p1_issuer_revision.cache_clear()


@lru_cache(maxsize=1)
def _cached_p1_issuer_revision() -> str:
    manifest = build_p1_issuer_authority_manifest()
    canonical = json.dumps(manifest, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(f"{P1_ISSUER_REVISION_PREFIX}{canonical}".encode()).hexdigest()[:40]


def compute_p1_issuer_implementation_revision() -> str:
    return _cached_p1_issuer_revision()


def _occurrence_issuance_digest(evidence: OccurrenceIssuanceEvidenceV2) -> str:
    body = {
        "issuer_implementation_revision": compute_p1_issuer_implementation_revision(),
        "evidence": evidence.to_dict(),
    }
    return hashlib.sha256(canonical_artifact_bytes(body)).hexdigest()


def issue_occurrence_reference(evidence: OccurrenceIssuanceEvidenceV2) -> IssuedOccurrenceReferenceV2:
    reject_hash_or_locator_identity(evidence.to_dict())
    occurrence = OccurrenceReferenceV2(
        source_system_id=evidence.source_system_id,
        tenant_or_realm_id=evidence.tenant_or_realm_id,
        authority_scope_id=evidence.authority_scope_id,
        occurrence_namespace_id=evidence.occurrence_namespace_id,
        physical_source_instance_id=evidence.physical_source_instance_id,
        native_id_namespace=evidence.native_id_namespace,
        native_record_id=evidence.native_record_id,
        source_revision_or_asof_id=evidence.source_revision_or_asof_id,
    )
    return IssuedOccurrenceReferenceV2(
        occurrence_reference=occurrence,
        issuance_digest=_occurrence_issuance_digest(evidence),
        issuer_implementation_revision=compute_p1_issuer_implementation_revision(),
        evidence_snapshot_id=evidence.evidence_snapshot_id,
    )


def _derive_artifact_id(*, schema: str, content_digest: str) -> str:
    kind = schema.rsplit("/", 1)[-1]
    return f"{ARTIFACT_ID_PREFIX_V2}{kind}_{content_digest[:16]}"


def _compute_manifest_content_digest(body: dict[str, Any]) -> str:
    return hashlib.sha256(canonical_artifact_bytes(strip_digest_metadata(body))).hexdigest()


@dataclass
class EvidenceSealManifestDraftV2:
    construct_freeze_digest: str
    episode_id: str
    issued_occurrence: IssuedOccurrenceReferenceV2
    evidence_complete_envelope_digest: str
    canonical_content_digest: str
    canonicalization_profile_digest: str
    adapter_implementation_digest: str
    condition_neutral_evidence_availability: ConditionNeutralEvidenceAvailabilityV2
    immediate_parents: tuple[ImmediateParentBindingV2, ...]
    responsible_role: str
    created_at: str
    logical_lineage_id: str | None = None
    lineage_edges: list[LineageEdgeV2] = field(default_factory=list)
    raw_record_digest: str | None = None
    attachment_reference_inventory_digest: str | None = None
    source_and_snapshot_identity_digest: str | None = None

    def _validate_parents(self) -> None:
        kinds = {p.parent_kind for p in self.immediate_parents}
        missing = REQUIRED_IMMEDIATE_PARENT_KINDS - kinds
        if missing:
            raise StructuralContractError(f"missing required immediate parent(s): {', '.join(sorted(missing))}")
        construct = next(p for p in self.immediate_parents if p.parent_kind == "construct_freeze")
        if construct.parent_digest != self.construct_freeze_digest:
            raise StructuralContractError("construct_freeze parent digest must match construct_freeze_digest")

    def _body_without_seal_metadata(self) -> dict[str, Any]:
        occ = self.issued_occurrence.occurrence_reference
        body: dict[str, Any] = {
            "construct_freeze_digest": self.construct_freeze_digest,
            "episode_id": self.episode_id,
            "occurrence_reference": occ.to_dict(),
            "occurrence_issuance_digest": self.issued_occurrence.issuance_digest,
            "issuer_implementation_revision": self.issued_occurrence.issuer_implementation_revision,
            "physical_instance_id": occ.physical_source_instance_id,
            "revision_or_asof_id": occ.source_revision_or_asof_id,
            "evidence_snapshot_id": self.issued_occurrence.evidence_snapshot_id,
            "evidence_complete_envelope_digest": self.evidence_complete_envelope_digest,
            "canonical_content_digest": self.canonical_content_digest,
            "canonicalization_profile_digest": self.canonicalization_profile_digest,
            "adapter_implementation_digest": self.adapter_implementation_digest,
            "condition_neutral_evidence_availability": self.condition_neutral_evidence_availability.to_dict(),
            "immediate_parents": [p.to_dict() for p in self.immediate_parents],
            "lineage_edges": [edge.to_dict() for edge in self.lineage_edges],
        }
        if self.logical_lineage_id is not None:
            body["logical_lineage_id"] = self.logical_lineage_id
        if self.raw_record_digest is not None:
            body["raw_record_digest"] = self.raw_record_digest
        if self.attachment_reference_inventory_digest is not None:
            body["attachment_reference_inventory_digest"] = self.attachment_reference_inventory_digest
        if self.source_and_snapshot_identity_digest is not None:
            body["source_and_snapshot_identity_digest"] = self.source_and_snapshot_identity_digest
        return body

    def finalize_and_seal(self, *, seal_time: str) -> "SealedP1AuthorityV2":
        self._validate_parents()
        occ = self.issued_occurrence.occurrence_reference
        construct_parent = next(p for p in self.immediate_parents if p.parent_kind == "construct_freeze")
        body = self._body_without_seal_metadata()
        placeholder_header = ArtifactHeaderV1(
            artifact_id="pending",
            schema_version=EvidenceSealManifestV2.SCHEMA,
            parent_artifact_id=construct_parent.parent_artifact_id,
            parent_digest=construct_parent.parent_digest,
            created_at=self.created_at,
            seal_time=None,
            responsible_role=self.responsible_role,
            content_digest=None,
            sealed=False,
        )
        placeholder = EvidenceSealManifestV2(
            _token=_ISSUANCE_TOKEN,
            header=placeholder_header,
            construct_freeze_digest=self.construct_freeze_digest,
            episode_id=self.episode_id,
            occurrence_reference=occ,
            occurrence_issuance_digest=self.issued_occurrence.issuance_digest,
            issuer_implementation_revision=self.issued_occurrence.issuer_implementation_revision,
            physical_instance_id=occ.physical_source_instance_id,
            revision_or_asof_id=occ.source_revision_or_asof_id,
            evidence_snapshot_id=self.issued_occurrence.evidence_snapshot_id,
            evidence_complete_envelope_digest=self.evidence_complete_envelope_digest,
            canonical_content_digest=self.canonical_content_digest,
            canonicalization_profile_digest=self.canonicalization_profile_digest,
            adapter_implementation_digest=self.adapter_implementation_digest,
            condition_neutral_evidence_availability=self.condition_neutral_evidence_availability,
            immediate_parents=self.immediate_parents,
            logical_lineage_id=self.logical_lineage_id,
            lineage_edges=list(self.lineage_edges),
            raw_record_digest=self.raw_record_digest,
            attachment_reference_inventory_digest=self.attachment_reference_inventory_digest,
            source_and_snapshot_identity_digest=self.source_and_snapshot_identity_digest,
        )
        content_digest = _compute_manifest_content_digest(placeholder.to_dict())
        artifact_id = _derive_artifact_id(schema=EvidenceSealManifestV2.SCHEMA, content_digest=content_digest)
        header = ArtifactHeaderV1(
            artifact_id=artifact_id,
            schema_version=EvidenceSealManifestV2.SCHEMA,
            parent_artifact_id=construct_parent.parent_artifact_id,
            parent_digest=construct_parent.parent_digest,
            created_at=self.created_at,
            seal_time=seal_time,
            responsible_role=self.responsible_role,
            content_digest=content_digest,
            sealed=True,
        )
        manifest = EvidenceSealManifestV2(
            _token=_ISSUANCE_TOKEN,
            header=header,
            construct_freeze_digest=self.construct_freeze_digest,
            episode_id=self.episode_id,
            occurrence_reference=occ,
            occurrence_issuance_digest=self.issued_occurrence.issuance_digest,
            issuer_implementation_revision=self.issued_occurrence.issuer_implementation_revision,
            physical_instance_id=occ.physical_source_instance_id,
            revision_or_asof_id=occ.source_revision_or_asof_id,
            evidence_snapshot_id=self.issued_occurrence.evidence_snapshot_id,
            evidence_complete_envelope_digest=self.evidence_complete_envelope_digest,
            canonical_content_digest=self.canonical_content_digest,
            canonicalization_profile_digest=self.canonicalization_profile_digest,
            adapter_implementation_digest=self.adapter_implementation_digest,
            condition_neutral_evidence_availability=self.condition_neutral_evidence_availability,
            immediate_parents=self.immediate_parents,
            logical_lineage_id=self.logical_lineage_id,
            lineage_edges=list(self.lineage_edges),
            raw_record_digest=self.raw_record_digest,
            attachment_reference_inventory_digest=self.attachment_reference_inventory_digest,
            source_and_snapshot_identity_digest=self.source_and_snapshot_identity_digest,
        )
        canonical_bytes = canonical_artifact_bytes(manifest.to_dict())
        sealed = SealedP1AuthorityV2(manifest=manifest, canonical_bytes=canonical_bytes, content_digest=content_digest)
        verify_sealed_p1_authority(sealed)
        return sealed


@dataclass(frozen=True)
class SealedP1AuthorityV2:
    manifest: EvidenceSealManifestV2
    canonical_bytes: bytes
    content_digest: str

    def to_dict(self) -> dict[str, Any]:
        return self.manifest.to_dict()


def verify_sealed_p1_authority(authority: SealedP1AuthorityV2 | dict[str, Any]) -> SealedP1AuthorityV2:
    if isinstance(authority, dict):
        manifest = EvidenceSealManifestV2.from_dict(authority)
        canonical_bytes = canonical_artifact_bytes(manifest.to_dict())
        content_digest = _compute_manifest_content_digest(manifest.to_dict())
        sealed = SealedP1AuthorityV2(manifest=manifest, canonical_bytes=canonical_bytes, content_digest=content_digest)
    else:
        sealed = authority
        data = sealed.manifest.to_dict()
        canonical_bytes = sealed.canonical_bytes
        content_digest = sealed.content_digest

    header = sealed.manifest.header
    if not header.sealed:
        raise StructuralContractError("P1 authority: sealed=false")
    if not header.seal_time:
        raise StructuralContractError("P1 authority: missing seal_time")
    if header.schema_version != EvidenceSealManifestV2.SCHEMA:
        raise StructuralContractError("P1 authority: wrong artifact kind/schema")
    if not header.content_digest:
        raise StructuralContractError("P1 authority: missing content_digest")
    recomputed = _compute_manifest_content_digest(sealed.manifest.to_dict())
    if recomputed != header.content_digest:
        raise StructuralContractError("P1 authority: content digest mismatch")
    if recomputed != content_digest:
        raise StructuralContractError("P1 authority: wrapper content digest mismatch")
    expected_id = _derive_artifact_id(schema=EvidenceSealManifestV2.SCHEMA, content_digest=recomputed)
    if header.artifact_id != expected_id:
        raise StructuralContractError("P1 authority: artifact ID mismatch")
    if not sealed.manifest.immediate_parents:
        raise StructuralContractError("P1 authority: missing required immediate parent")
    construct = next((p for p in sealed.manifest.immediate_parents if p.parent_kind == "construct_freeze"), None)
    if construct is None:
        raise StructuralContractError("P1 authority: missing construct_freeze parent")
    if construct.parent_digest != sealed.manifest.construct_freeze_digest:
        raise StructuralContractError("P1 authority: construct-freeze mismatch")
    if not sealed.manifest.occurrence_issuance_digest:
        raise StructuralContractError("P1 authority: missing occurrence issuance digest")
    if canonical_artifact_bytes(sealed.manifest.to_dict()) != canonical_bytes:
        raise StructuralContractError("P1 authority: canonical bytes mismatch")
    return sealed


def reject_raw_unfinalized_p1(manifest: EvidenceSealManifestV2) -> None:
    if not manifest.header.sealed:
        raise StructuralContractError("raw P1 manifest: sealed=false")
    if not manifest.occurrence_issuance_digest:
        raise StructuralContractError("raw P1 manifest: missing occurrence issuance — not issued authority")
    verify_sealed_p1_authority(SealedP1AuthorityV2(
        manifest=manifest,
        canonical_bytes=canonical_artifact_bytes(manifest.to_dict()),
        content_digest=_compute_manifest_content_digest(manifest.to_dict()),
    ))

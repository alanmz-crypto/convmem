"""Authoritative P1 occurrence issuance, seal finalization, and byte verification."""

# P1 authority modules intentionally share contract-shaped serialization blocks.
# pylint: disable=duplicate-code

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
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
from eval_naturalistic.v2.evidence_commitments import (
    VerifiedP1EvidenceCommitmentsV2,
    recompute_evidence_commitments_from_manifest,
)
from eval_naturalistic.v2.identity import LineageEdgeV2, OccurrenceReferenceV2
from eval_naturalistic.v2.lineage_attestation import (
    LineageAttestationRepository,
    verify_lineage_edge_attestation,
)
from eval_naturalistic.v2.p0_construct import (
    ConstructFreezeAuthorityRepository,
    verify_construct_freeze_parent_binding,
)
from eval_naturalistic.v2.source_authority import (
    VerifiedSourceAuthorityV2,
    reverify_source_authority_record,
)
from eval_naturalistic.v2.authority_substrate import (
    resolve_shared_authority_source,
    same_authority_object,
    validate_authority_source,
)

P1_ISSUER_MANIFEST_CLASS = "naturalistic_v2_p1_issuer_authority"
P1_ISSUER_REVISION_PREFIX = "nps2-p1-issuer/"
P1_STAGE = "P1_EVIDENCE_SEAL"
REQUIRED_IMMEDIATE_PARENT_KINDS = frozenset({"construct_freeze"})

_REPO_ROOT = Path(__file__).resolve().parents[2]
_P1_ISSUER_SEED_MODULES = (
    "canonical_json.py",
    "eval_naturalistic/v2/authority_issuance.py",
    "eval_naturalistic/v2/identity.py",
    "eval_naturalistic/v2/contracts.py",
    "eval_naturalistic/v2/validators.py",
    "eval_naturalistic/v2/evidence.py",
    "eval_naturalistic/v2/evidence_commitments.py",
    "eval_naturalistic/v2/source_authority.py",
    "eval_naturalistic/v2/capture_attestation.py",
    "eval_naturalistic/v2/capture_attestation_issuance.py",
    "eval_naturalistic/v2/source_issuer_authority.py",
    "eval_naturalistic/v2/issuer_attestation_capability.py",
    "eval_naturalistic/v2/authority_substrate.py",
    "eval_naturalistic/v2/p0_construct.py",
    "eval_naturalistic/v2/lineage_attestation.py",
    "eval_naturalistic/digest.py",
    "eval_naturalistic/base.py",
)

_ISSUED_REFERENCE_TOKEN = object()


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
            parent_digest=_digest_hex(data["parent_digest"], "parent_digest"),
        )


@dataclass(frozen=True)
class IssuedOccurrenceReferenceV2:  # pylint: disable=too-many-instance-attributes
    """Issuer-produced occurrence authority — not caller-constructible."""

    occurrence_reference: Any
    issuance_digest: str
    issuer_implementation_revision: str
    evidence_snapshot_id: str
    source_authority_digest: str
    construct_freeze_digest: str
    construct_freeze_artifact_id: str
    source_capture_digest: str
    raw_record_digest: str

    def __init__(  # pylint: disable=too-many-arguments
        self,
        *,
        _token: object,
        occurrence_reference: Any,
        issuance_digest: str,
        issuer_implementation_revision: str,
        evidence_snapshot_id: str,
        source_authority_digest: str,
        construct_freeze_digest: str = "",
        construct_freeze_artifact_id: str = "",
        source_capture_digest: str = "",
        raw_record_digest: str = "",
    ) -> None:
        if _token is not _ISSUED_REFERENCE_TOKEN:
            raise TypeError(
                "IssuedOccurrenceReferenceV2 is only produced by verified source-backed issuance"
            )
        object.__setattr__(self, "occurrence_reference", occurrence_reference)
        object.__setattr__(self, "issuance_digest", issuance_digest)
        object.__setattr__(self, "issuer_implementation_revision", issuer_implementation_revision)
        object.__setattr__(self, "evidence_snapshot_id", evidence_snapshot_id)
        object.__setattr__(self, "source_authority_digest", source_authority_digest)
        object.__setattr__(self, "construct_freeze_digest", construct_freeze_digest)
        object.__setattr__(self, "construct_freeze_artifact_id", construct_freeze_artifact_id)
        object.__setattr__(self, "source_capture_digest", source_capture_digest)
        object.__setattr__(self, "raw_record_digest", raw_record_digest)

    def to_dict(self) -> dict[str, Any]:
        return {
            "occurrence_reference": self.occurrence_reference.to_dict(),
            "issuance_digest": self.issuance_digest,
            "issuer_implementation_revision": self.issuer_implementation_revision,
            "evidence_snapshot_id": self.evidence_snapshot_id,
            "source_authority_digest": self.source_authority_digest,
            "construct_freeze_digest": self.construct_freeze_digest,
            "construct_freeze_artifact_id": self.construct_freeze_artifact_id,
            "source_capture_digest": self.source_capture_digest,
            "raw_record_digest": self.raw_record_digest,
        }


@dataclass(frozen=True)
class IssuanceAuthorityRecordV2:  # pylint: disable=too-many-instance-attributes
    """Portable issuance authority substrate — reconstructable across processes."""

    occurrence_reference: Any
    issuance_digest: str
    issuer_implementation_revision: str
    evidence_snapshot_id: str
    source_authority_digest: str
    source_capture_digest: str
    construct_freeze_digest: str
    construct_freeze_artifact_id: str
    raw_record_digest: str

    _FIELDS = {
        "occurrence_reference",
        "issuance_digest",
        "issuer_implementation_revision",
        "evidence_snapshot_id",
        "source_authority_digest",
        "source_capture_digest",
        "construct_freeze_digest",
        "construct_freeze_artifact_id",
        "raw_record_digest",
    }

    def to_dict(self) -> dict[str, Any]:
        return {
            "occurrence_reference": self.occurrence_reference.to_dict(),
            "issuance_digest": self.issuance_digest,
            "issuer_implementation_revision": self.issuer_implementation_revision,
            "evidence_snapshot_id": self.evidence_snapshot_id,
            "source_authority_digest": self.source_authority_digest,
            "source_capture_digest": self.source_capture_digest,
            "construct_freeze_digest": self.construct_freeze_digest,
            "construct_freeze_artifact_id": self.construct_freeze_artifact_id,
            "raw_record_digest": self.raw_record_digest,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "IssuanceAuthorityRecordV2":
        data = _require_dict(data, "IssuanceAuthorityRecordV2")
        _require_no_unknown_props(data, cls._FIELDS, "IssuanceAuthorityRecordV2")
        return cls(
            occurrence_reference=OccurrenceReferenceV2.from_dict(
                _require_dict(data["occurrence_reference"], "occurrence_reference")
            ),
            issuance_digest=_digest_hex(data["issuance_digest"], "issuance_digest"),
            issuer_implementation_revision=_require_str(
                data["issuer_implementation_revision"], "issuer_implementation_revision"
            ),
            evidence_snapshot_id=_require_str(data["evidence_snapshot_id"], "evidence_snapshot_id"),
            source_authority_digest=_digest_hex(
                data["source_authority_digest"], "source_authority_digest"
            ),
            source_capture_digest=_digest_hex(
                data["source_capture_digest"], "source_capture_digest"
            ),
            construct_freeze_digest=_digest_hex(
                data["construct_freeze_digest"], "construct_freeze_digest"
            ),
            construct_freeze_artifact_id=_require_str(
                data["construct_freeze_artifact_id"], "construct_freeze_artifact_id"
            ),
            raw_record_digest=_digest_hex(data["raw_record_digest"], "raw_record_digest"),
        )


class IssuanceAuthorityRepository:
    """Candidate issuance store; only source-backed commits are authority."""

    def __init__(self, *, authority_source: Any = None) -> None:
        self._records: dict[str, IssuanceAuthorityRecordV2] = {}
        self._authority_source = authority_source

    def authority_source(self) -> Any:
        """Return the non-serialized study-authority source binding."""

        return self._authority_source

    @classmethod
    def from_records(
        cls, records: tuple[IssuanceAuthorityRecordV2, ...]
    ) -> "IssuanceAuthorityRepository":
        repo = cls()
        for record in records:
            repo._records[record.issuance_digest] = record
        return repo

    def records(self) -> tuple[IssuanceAuthorityRecordV2, ...]:
        return tuple(self._records.values())

    def _commit_verified_issuance(
        self,
        issued: IssuedOccurrenceReferenceV2,
        *,
        source_authority: VerifiedSourceAuthorityV2,
        source_capture_digest: str,
        authority_source: Any,
    ) -> IssuanceAuthorityRecordV2:
        source = validate_authority_source(authority_source)
        if self._authority_source is None:
            self._authority_source = source
        elif self._authority_source is not source:
            raise StructuralContractError("issuance authority repository bound to different source")
        verified = reverify_source_authority_record(source_authority)
        if issued.source_authority_digest != verified.authority_record_digest:
            raise StructuralContractError("issuance authority: source authority digest mismatch")
        if source_capture_digest != verified.source_capture_digest:
            raise StructuralContractError("issuance authority: source capture digest mismatch")
        expected = _occurrence_issuance_digest(
            source_authority=verified,
            issuer_implementation_revision=issued.issuer_implementation_revision,
        )
        if expected != issued.issuance_digest:
            raise StructuralContractError("issuance authority: issuance digest mismatch")
        record = IssuanceAuthorityRecordV2(
            occurrence_reference=issued.occurrence_reference,
            issuance_digest=issued.issuance_digest,
            issuer_implementation_revision=issued.issuer_implementation_revision,
            evidence_snapshot_id=issued.evidence_snapshot_id,
            source_authority_digest=issued.source_authority_digest,
            source_capture_digest=source_capture_digest,
            construct_freeze_digest=verified.construct_freeze_digest,
            construct_freeze_artifact_id=verified.construct_freeze_artifact_id,
            raw_record_digest=verified.raw_record_digest,
        )
        self._records[issued.issuance_digest] = record
        register = getattr(source, "register_issuance_repository", None)
        if callable(register):
            register(self)
        return record

    def resolve(self, issuance_digest: str) -> IssuanceAuthorityRecordV2:
        record = self._records.get(issuance_digest)
        if record is None:
            raise StructuralContractError("P1 authority: unregistered occurrence issuance")
        if record.issuance_digest != issuance_digest:
            raise StructuralContractError("P1 authority: issuance digest mismatch")
        return record


def _digest_hex(value: Any, field_name: str) -> str:
    digest = _require_str(value, field_name)
    if len(digest) != 64 or any(ch not in "0123456789abcdef" for ch in digest):
        raise StructuralContractError(
            f"{field_name}: must be 64-character lowercase SHA-256 hex digest"
        )
    return digest


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
    """No-op retained for test compatibility — revision is always recomputed."""


def compute_p1_issuer_implementation_revision() -> str:
    manifest = build_p1_issuer_authority_manifest()
    canonical = json.dumps(manifest, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(f"{P1_ISSUER_REVISION_PREFIX}{canonical}".encode()).hexdigest()[:40]


def _occurrence_issuance_digest(
    *,
    source_authority: VerifiedSourceAuthorityV2,
    issuer_implementation_revision: str,
) -> str:
    body = {
        "issuer_implementation_revision": issuer_implementation_revision,
        "source_authority_digest": source_authority.authority_record_digest,
        "occurrence_reference": source_authority.occurrence_reference.to_dict(),
        "evidence_snapshot_id": source_authority.evidence_snapshot_id,
        "source_capture_digest": source_authority.source_capture_digest,
        "raw_record_digest": source_authority.raw_record_digest,
        "construct_freeze_digest": source_authority.construct_freeze_digest,
        "construct_freeze_artifact_id": source_authority.construct_freeze_artifact_id,
    }
    return hashlib.sha256(canonical_artifact_bytes(body)).hexdigest()


def issue_occurrence_reference(
    source_authority: VerifiedSourceAuthorityV2,
    *,
    issuance_repository: IssuanceAuthorityRepository,
    authority_source: Any = None,
) -> IssuedOccurrenceReferenceV2:
    """Mint P1 occurrence authority only from verified source-backed evidence."""

    if not isinstance(source_authority, VerifiedSourceAuthorityV2):
        raise TypeError("issue_occurrence_reference requires VerifiedSourceAuthorityV2")
    verified = reverify_source_authority_record(source_authority)
    source = validate_authority_source(
        authority_source if authority_source is not None else verified.authority_source()
    )
    trusted_capture = source.resolve_source_capture(verified.source_capture_digest)
    if trusted_capture.source_evidence_digest() != verified.source_capture_digest:
        raise StructuralContractError("issuance authority: source capture is not independently resolved")
    revision = compute_p1_issuer_implementation_revision()
    issued = IssuedOccurrenceReferenceV2(
        _token=_ISSUED_REFERENCE_TOKEN,
        occurrence_reference=verified.occurrence_reference,
        issuance_digest=_occurrence_issuance_digest(
            source_authority=verified,
            issuer_implementation_revision=revision,
        ),
        issuer_implementation_revision=revision,
        evidence_snapshot_id=verified.evidence_snapshot_id,
        source_authority_digest=verified.authority_record_digest,
        construct_freeze_digest=verified.construct_freeze_digest,
        construct_freeze_artifact_id=verified.construct_freeze_artifact_id,
        source_capture_digest=verified.source_capture_digest,
        raw_record_digest=verified.raw_record_digest,
    )
    issuance_repository._commit_verified_issuance(  # pylint: disable=protected-access
        issued,
        source_authority=verified,
        source_capture_digest=verified.source_capture_digest,
        authority_source=source,
    )
    return issued


def _derive_artifact_id(*, schema: str, content_digest: str) -> str:
    kind = schema.rsplit("/", 1)[-1]
    return f"{ARTIFACT_ID_PREFIX_V2}{kind}_{content_digest}"


def _compute_manifest_content_digest(body: dict[str, Any]) -> str:
    return hashlib.sha256(canonical_artifact_bytes(strip_digest_metadata(body))).hexdigest()


def _verify_immediate_parents(
    *,
    parents: tuple[ImmediateParentBindingV2, ...],
    construct_freeze_digest: str,
    p0_repository: ConstructFreezeAuthorityRepository,
    authority_source: Any,
) -> None:
    kinds = {p.parent_kind for p in parents}
    missing = REQUIRED_IMMEDIATE_PARENT_KINDS - kinds
    if missing:
        raise StructuralContractError(f"missing required immediate parent(s): {', '.join(sorted(missing))}")
    extra = kinds - REQUIRED_IMMEDIATE_PARENT_KINDS
    if extra:
        raise StructuralContractError(
            f"unknown immediate parent kind(s): {', '.join(sorted(extra))}"
        )
    construct_parents = [p for p in parents if p.parent_kind == "construct_freeze"]
    if len(construct_parents) != 1:
        raise StructuralContractError("exactly one construct_freeze parent required")
    verify_construct_freeze_parent_binding(
        parent_kind=construct_parents[0].parent_kind,
        parent_artifact_id=construct_parents[0].parent_artifact_id,
        parent_digest=construct_parents[0].parent_digest,
        construct_freeze_digest=construct_freeze_digest,
        repository=p0_repository,
        authority_source=authority_source,
    )


def _verify_lineage_edges(
    *,
    edges: list[LineageEdgeV2],
    child_occurrence: Any,
    lineage_repository: LineageAttestationRepository,
) -> None:
    if not edges:
        return
    for edge in edges:
        if not edge.issuer_attested:
            continue
        artifact = lineage_repository.resolve(edge.attestation_evidence_digest or "")
        verify_lineage_edge_attestation(
            edge,
            child_occurrence=child_occurrence,
            parent_occurrence=artifact.parent_occurrence,
            repository=lineage_repository,
        )


@dataclass
class EvidenceSealManifestDraftV2:  # pylint: disable=too-many-instance-attributes
    construct_freeze_digest: str
    episode_id: str
    issued_occurrence: IssuedOccurrenceReferenceV2
    evidence_commitments: VerifiedP1EvidenceCommitmentsV2
    condition_neutral_evidence_availability: ConditionNeutralEvidenceAvailabilityV2
    immediate_parents: tuple[ImmediateParentBindingV2, ...]
    responsible_role: str
    created_at: str
    logical_lineage_id: str | None = None
    lineage_edges: list[LineageEdgeV2] = field(default_factory=list)

    def _body_without_seal_metadata(self) -> dict[str, Any]:
        occ = self.issued_occurrence.occurrence_reference
        commitments = self.evidence_commitments
        body: dict[str, Any] = {
            "construct_freeze_digest": self.construct_freeze_digest,
            "episode_id": self.episode_id,
            "occurrence_reference": occ.to_dict(),
            "occurrence_issuance_digest": self.issued_occurrence.issuance_digest,
            "issuer_implementation_revision": self.issued_occurrence.issuer_implementation_revision,
            "source_authority_digest": self.issued_occurrence.source_authority_digest,
            "physical_instance_id": occ.physical_source_instance_id,
            "revision_or_asof_id": occ.source_revision_or_asof_id,
            "evidence_snapshot_id": self.issued_occurrence.evidence_snapshot_id,
            "evidence_complete_envelope_digest": commitments.evidence_complete_envelope_digest,
            "canonical_content_digest": commitments.canonical_content_digest,
            "canonicalization_profile_digest": commitments.canonicalization_profile_digest,
            "adapter_implementation_digest": commitments.adapter_implementation_digest,
            "condition_neutral_evidence_availability": self.condition_neutral_evidence_availability.to_dict(),
            "immediate_parents": [p.to_dict() for p in self.immediate_parents],
            "lineage_edges": [edge.to_dict() for edge in self.lineage_edges],
            "raw_record_digest": commitments.raw_record_digest,
        }
        if self.logical_lineage_id is not None:
            body["logical_lineage_id"] = self.logical_lineage_id
        if commitments.attachment_reference_inventory_digest is not None:
            body["attachment_reference_inventory_digest"] = (
                commitments.attachment_reference_inventory_digest
            )
        if commitments.source_and_snapshot_identity_digest is not None:
            body["source_and_snapshot_identity_digest"] = (
                commitments.source_and_snapshot_identity_digest
            )
        return body

    def finalize_and_seal(
        self,
        *,
        seal_time: str,
        p0_repository: ConstructFreezeAuthorityRepository,
        issuance_repository: IssuanceAuthorityRepository,
        lineage_repository: LineageAttestationRepository | None = None,
    ) -> "SealedP1AuthorityV2":
        has_attested_edges = any(edge.issuer_attested for edge in self.lineage_edges)
        if has_attested_edges and lineage_repository is None:
            raise StructuralContractError("lineage repository required for attested edges")
        _verify_immediate_parents(
            parents=self.immediate_parents,
            construct_freeze_digest=self.construct_freeze_digest,
            p0_repository=p0_repository,
            authority_source=resolve_shared_authority_source(
                repositories=(p0_repository, issuance_repository)
            ),
        )
        if has_attested_edges:
            _verify_lineage_edges(
                edges=self.lineage_edges,
                child_occurrence=self.issued_occurrence.occurrence_reference,
                lineage_repository=lineage_repository or LineageAttestationRepository(),
            )
        occ = self.issued_occurrence.occurrence_reference
        commitments = self.evidence_commitments
        construct_parent = next(p for p in self.immediate_parents if p.parent_kind == "construct_freeze")
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
            source_authority_digest=self.issued_occurrence.source_authority_digest,
            physical_instance_id=occ.physical_source_instance_id,
            revision_or_asof_id=occ.source_revision_or_asof_id,
            evidence_snapshot_id=self.issued_occurrence.evidence_snapshot_id,
            evidence_complete_envelope_digest=commitments.evidence_complete_envelope_digest,
            canonical_content_digest=commitments.canonical_content_digest,
            canonicalization_profile_digest=commitments.canonicalization_profile_digest,
            adapter_implementation_digest=commitments.adapter_implementation_digest,
            condition_neutral_evidence_availability=self.condition_neutral_evidence_availability,
            immediate_parents=self.immediate_parents,
            logical_lineage_id=self.logical_lineage_id,
            lineage_edges=list(self.lineage_edges),
            raw_record_digest=commitments.raw_record_digest,
            attachment_reference_inventory_digest=commitments.attachment_reference_inventory_digest,
            source_and_snapshot_identity_digest=commitments.source_and_snapshot_identity_digest,
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
            source_authority_digest=self.issued_occurrence.source_authority_digest,
            physical_instance_id=occ.physical_source_instance_id,
            revision_or_asof_id=occ.source_revision_or_asof_id,
            evidence_snapshot_id=self.issued_occurrence.evidence_snapshot_id,
            evidence_complete_envelope_digest=commitments.evidence_complete_envelope_digest,
            canonical_content_digest=commitments.canonical_content_digest,
            canonicalization_profile_digest=commitments.canonicalization_profile_digest,
            adapter_implementation_digest=commitments.adapter_implementation_digest,
            condition_neutral_evidence_availability=self.condition_neutral_evidence_availability,
            immediate_parents=self.immediate_parents,
            logical_lineage_id=self.logical_lineage_id,
            lineage_edges=list(self.lineage_edges),
            raw_record_digest=commitments.raw_record_digest,
            attachment_reference_inventory_digest=commitments.attachment_reference_inventory_digest,
            source_and_snapshot_identity_digest=commitments.source_and_snapshot_identity_digest,
        )
        canonical_bytes = canonical_artifact_bytes(manifest.to_dict())
        sealed = SealedP1AuthorityV2(
            manifest=manifest,
            canonical_bytes=canonical_bytes,
            content_digest=content_digest,
        )
        verify_sealed_p1_authority(
            sealed,
            p0_repository=p0_repository,
            lineage_repository=lineage_repository,
            issuance_repository=issuance_repository,
        )
        return sealed


@dataclass(frozen=True)
class SealedP1AuthorityV2:
    manifest: EvidenceSealManifestV2
    canonical_bytes: bytes
    content_digest: str

    def to_dict(self) -> dict[str, Any]:
        return self.manifest.to_dict()


def _verify_issuer_implementation_revision(declared: str) -> None:
    expected = compute_p1_issuer_implementation_revision()
    if declared != expected:
        raise StructuralContractError("P1 authority: issuer implementation revision mismatch")


def _verify_issuance_authority(
    manifest: EvidenceSealManifestV2,
    *,
    issuance_repository: IssuanceAuthorityRepository,
    authority_source: Any,
) -> IssuanceAuthorityRecordV2:
    if not manifest.occurrence_issuance_digest:
        raise StructuralContractError("P1 authority: missing occurrence issuance digest")
    if not manifest.source_authority_digest:
        raise StructuralContractError("P1 authority: missing source authority digest")
    record = issuance_repository.resolve(manifest.occurrence_issuance_digest)
    trusted_record = authority_source.resolve_issuance(manifest.occurrence_issuance_digest)
    same_authority_object(
        record,
        trusted_record,
        message="P1 authority: issuance is not independently resolved",
    )
    if record.issuance_digest != manifest.occurrence_issuance_digest:
        raise StructuralContractError("P1 authority: occurrence issuance digest mismatch")
    if record.source_authority_digest != manifest.source_authority_digest:
        raise StructuralContractError("P1 authority: source authority digest mismatch")
    if not record.occurrence_reference.same_occurrence_as(manifest.occurrence_reference):
        raise StructuralContractError("P1 authority: occurrence reference mismatch")
    if record.evidence_snapshot_id != manifest.evidence_snapshot_id:
        raise StructuralContractError("P1 authority: evidence snapshot mismatch")
    if record.issuer_implementation_revision != manifest.issuer_implementation_revision:
        raise StructuralContractError("P1 authority: issuer revision mismatch on issuance record")
    if record.construct_freeze_digest != manifest.construct_freeze_digest:
        raise StructuralContractError("P1 authority: issuance construct-freeze mismatch")
    construct_parent = next(
        (parent for parent in manifest.immediate_parents if parent.parent_kind == "construct_freeze"),
        None,
    )
    if construct_parent is None or record.construct_freeze_artifact_id != construct_parent.parent_artifact_id:
        raise StructuralContractError("P1 authority: issuance construct-freeze artifact mismatch")
    if manifest.raw_record_digest is None or record.raw_record_digest != manifest.raw_record_digest:
        raise StructuralContractError("P1 authority: issuance raw-record binding mismatch")
    body = {
        "issuer_implementation_revision": record.issuer_implementation_revision,
        "source_authority_digest": record.source_authority_digest,
        "occurrence_reference": record.occurrence_reference.to_dict(),
        "evidence_snapshot_id": record.evidence_snapshot_id,
        "source_capture_digest": record.source_capture_digest,
        "raw_record_digest": record.raw_record_digest,
        "construct_freeze_digest": record.construct_freeze_digest,
        "construct_freeze_artifact_id": record.construct_freeze_artifact_id,
    }
    expected = hashlib.sha256(canonical_artifact_bytes(body)).hexdigest()
    if expected != manifest.occurrence_issuance_digest:
        raise StructuralContractError("P1 authority: occurrence issuance digest mismatch")
    return record


def _verify_evidence_commitments(
    manifest: EvidenceSealManifestV2,
    *,
    issuance_record: IssuanceAuthorityRecordV2,
) -> None:
    if manifest.raw_record_digest is None:
        raise StructuralContractError("P1 authority: missing raw record commitment")
    if issuance_record.raw_record_digest != manifest.raw_record_digest:
        raise StructuralContractError("P1 authority: issuance/raw-record commitment mismatch")
    recomputed = recompute_evidence_commitments_from_manifest(
        source_capture_digest=issuance_record.source_capture_digest,
        source_authority_digest=manifest.source_authority_digest,
        occurrence=manifest.occurrence_reference,
        evidence_snapshot_id=manifest.evidence_snapshot_id,
        raw_record_digest=manifest.raw_record_digest,
        canonical_content_digest=manifest.canonical_content_digest,
        canonicalization_profile_digest=manifest.canonicalization_profile_digest,
        adapter_implementation_digest=manifest.adapter_implementation_digest,
        attachment_reference_inventory_digest=manifest.attachment_reference_inventory_digest,
    )
    recomputed.verify_against_manifest_fields(
        source_authority_digest=manifest.source_authority_digest,
        evidence_snapshot_id=manifest.evidence_snapshot_id,
        evidence_complete_envelope_digest=manifest.evidence_complete_envelope_digest,
        canonical_content_digest=manifest.canonical_content_digest,
        canonicalization_profile_digest=manifest.canonicalization_profile_digest,
        adapter_implementation_digest=manifest.adapter_implementation_digest,
        raw_record_digest=manifest.raw_record_digest,
        attachment_reference_inventory_digest=manifest.attachment_reference_inventory_digest,
        source_and_snapshot_identity_digest=manifest.source_and_snapshot_identity_digest,
    )


def _verify_header_parent_binding(manifest: EvidenceSealManifestV2) -> None:
    construct_parents = [
        p for p in manifest.immediate_parents if p.parent_kind == "construct_freeze"
    ]
    if len(construct_parents) != 1:
        raise StructuralContractError("exactly one construct_freeze parent required")
    parent = construct_parents[0]
    header = manifest.header
    if header.parent_artifact_id != parent.parent_artifact_id:
        raise StructuralContractError("P1 authority: header parent_artifact_id mismatch")
    if header.parent_digest != parent.parent_digest:
        raise StructuralContractError("P1 authority: header parent_digest mismatch")


def verify_sealed_p1_authority(
    authority: SealedP1AuthorityV2 | dict[str, Any],
    *,
    p0_repository: ConstructFreezeAuthorityRepository | None = None,
    lineage_repository: LineageAttestationRepository | None = None,
    issuance_repository: IssuanceAuthorityRepository | None = None,
    authority_source: Any = None,
) -> SealedP1AuthorityV2:
    if p0_repository is None:
        raise StructuralContractError("P1 authority: construct-freeze repository required")
    if issuance_repository is None:
        raise StructuralContractError("P1 authority: issuance repository required")
    source = resolve_shared_authority_source(
        explicit=authority_source,
        repositories=(p0_repository, issuance_repository),
    )
    if isinstance(authority, dict):
        manifest = EvidenceSealManifestV2.from_dict(authority)
        canonical_bytes = canonical_artifact_bytes(manifest.to_dict())
        content_digest = _compute_manifest_content_digest(manifest.to_dict())
        sealed = SealedP1AuthorityV2(
            manifest=manifest,
            canonical_bytes=canonical_bytes,
            content_digest=content_digest,
        )
    else:
        sealed = authority
        manifest = sealed.manifest
        canonical_bytes = sealed.canonical_bytes
        content_digest = sealed.content_digest

    header = manifest.header
    if not header.sealed:
        raise StructuralContractError("P1 authority: sealed=false")
    if not header.seal_time:
        raise StructuralContractError("P1 authority: missing seal_time")
    if header.schema_version != EvidenceSealManifestV2.SCHEMA:
        raise StructuralContractError("P1 authority: wrong artifact kind/schema")
    if not header.content_digest:
        raise StructuralContractError("P1 authority: missing content_digest")
    _verify_issuer_implementation_revision(manifest.issuer_implementation_revision)
    _verify_header_parent_binding(manifest)
    construct_parent = next(
        (parent for parent in manifest.immediate_parents if parent.parent_kind == "construct_freeze"),
        None,
    )
    if construct_parent is None:
        raise StructuralContractError("P1 authority: construct-freeze parent required")
    issuance_record = _verify_issuance_authority(
        manifest,
        issuance_repository=issuance_repository,
        authority_source=source,
    )
    from eval_naturalistic.v2.source_authority import verify_source_capture_authority

    source_capture = source.resolve_source_capture(issuance_record.source_capture_digest)
    source_authority = verify_source_capture_authority(
        source_capture,
        construct_freeze_digest=manifest.construct_freeze_digest,
        construct_freeze_artifact_id=construct_parent.parent_artifact_id,
        authority_source=source,
    )
    if source_authority.authority_record_digest != manifest.source_authority_digest:
        raise StructuralContractError("P1 authority: source authority is not bound to issuance")
    if source_authority.raw_record_digest != issuance_record.raw_record_digest:
        raise StructuralContractError("P1 authority: source raw-record binding mismatch")
    _verify_evidence_commitments(manifest, issuance_record=issuance_record)
    recomputed = _compute_manifest_content_digest(manifest.to_dict())
    if recomputed != header.content_digest:
        raise StructuralContractError("P1 authority: content digest mismatch")
    if recomputed != content_digest:
        raise StructuralContractError("P1 authority: wrapper content digest mismatch")
    expected_id = _derive_artifact_id(schema=EvidenceSealManifestV2.SCHEMA, content_digest=recomputed)
    if header.artifact_id != expected_id:
        raise StructuralContractError("P1 authority: artifact ID mismatch")
    if not manifest.immediate_parents:
        raise StructuralContractError("P1 authority: missing required immediate parent")
    _verify_immediate_parents(
        parents=manifest.immediate_parents,
        construct_freeze_digest=manifest.construct_freeze_digest,
        p0_repository=p0_repository,
        authority_source=source,
    )
    attested_edges = [edge for edge in manifest.lineage_edges if edge.issuer_attested]
    if attested_edges:
        if lineage_repository is None:
            raise StructuralContractError("P1 authority: lineage repository required for attested edges")
        for edge in attested_edges:
            artifact = lineage_repository.resolve(edge.attestation_evidence_digest or "")
            verify_lineage_edge_attestation(
                edge,
                child_occurrence=manifest.occurrence_reference,
                parent_occurrence=artifact.parent_occurrence,
                repository=lineage_repository,
            )
    if canonical_artifact_bytes(manifest.to_dict()) != canonical_bytes:
        raise StructuralContractError("P1 authority: canonical bytes mismatch")
    return sealed


def reject_raw_unfinalized_p1(
    manifest: EvidenceSealManifestV2,
    *,
    p0_repository: ConstructFreezeAuthorityRepository | None = None,
    issuance_repository: IssuanceAuthorityRepository | None = None,
) -> None:
    if p0_repository is None:
        raise StructuralContractError("P1 authority: construct-freeze repository required")
    if issuance_repository is None:
        raise StructuralContractError("P1 authority: issuance repository required")
    if not manifest.header.sealed:
        raise StructuralContractError("raw P1 manifest: sealed=false")
    if not manifest.occurrence_issuance_digest:
        raise StructuralContractError("raw P1 manifest: missing occurrence issuance — not issued authority")
    verify_sealed_p1_authority(
        SealedP1AuthorityV2(
            manifest=manifest,
            canonical_bytes=canonical_artifact_bytes(manifest.to_dict()),
            content_digest=_compute_manifest_content_digest(manifest.to_dict()),
        ),
        p0_repository=p0_repository,
        issuance_repository=issuance_repository,
    )

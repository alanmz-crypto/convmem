"""Source-backed, occurrence-bound capability manifests for Naturalistic V2.

Adapter profiles describe what an adapter can preserve.  They do not establish
authority.  This module is the authority boundary: the only issuance function
starts with a sealed P1 authority, re-verifies it against the V2-01C source,
resolves a trusted profile from the closed registry, and seals a manifest whose
content digest covers every binding and capability value.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from eval_naturalistic.base import (
    ArtifactHeaderV1,
    StructuralContractError,
    _require_dict,
    _require_no_unknown_props,
    _require_str,
    strip_digest_metadata,
)
from eval_naturalistic.digest import canonical_artifact_bytes
from eval_naturalistic.v2.adapters.capability import CapabilityVectorV2
from eval_naturalistic.v2.adapters.profile import (
    EvidenceAdapterProfileV2,
    profile_content_digest,
)
from eval_naturalistic.v2.adapters.registry import resolve_profile_or_fail
from eval_naturalistic.v2.authority_issuance import (
    IssuanceAuthorityRecordV2,
    SealedP1AuthorityV2,
    verify_sealed_p1_authority,
)
from eval_naturalistic.v2.contracts import EvidenceSealManifestV2
from eval_naturalistic.v2.evidence import ConditionNeutralEvidenceAvailabilityV2
from eval_naturalistic.v2.identity import OccurrenceReferenceV2, digest_hex

if TYPE_CHECKING:
    from eval_naturalistic.v2.authority_substrate import IndependentAuthoritySourceV2
    from eval_naturalistic.v2.lineage_attestation import LineageAttestationRepository
    from eval_naturalistic.v2.p0_construct import ConstructFreezeAuthorityRepository


CAPABILITY_MANIFEST_SCHEMA = "convmem/naturalistic/v2/capability-manifest-v2"
CAPABILITY_ARTIFACT_KIND = "capability-manifest-v2"
_CAPABILITY_ISSUANCE_TOKEN = object()


def _digest(value: Any, field_name: str) -> str:
    return digest_hex(value, field_name)


def _compute_content_digest(data: dict[str, Any]) -> str:
    """Hash manifest content while excluding only seal-generated metadata."""

    return hashlib.sha256(
        canonical_artifact_bytes(strip_digest_metadata(data))
    ).hexdigest()


def _derive_artifact_id(content_digest: str) -> str:
    return f"nps2_{CAPABILITY_ARTIFACT_KIND}_{content_digest}"


def _required(data: dict[str, Any], field_name: str) -> Any:
    try:
        return data[field_name]
    except KeyError as exc:
        raise StructuralContractError(
            f"CapabilityManifestV2: missing required property '{field_name}'"
        ) from exc


@dataclass(frozen=True)
class CapabilityManifestV2:  # pylint: disable=too-many-instance-attributes
    """Canonical capability record bound to one verified V2-01C occurrence."""

    header: ArtifactHeaderV1
    p1_authority_artifact_id: str
    p1_authority_digest: str
    construct_freeze_artifact_id: str
    construct_freeze_digest: str
    episode_id: str
    occurrence_reference: OccurrenceReferenceV2
    occurrence_issuance_digest: str
    source_authority_digest: str
    source_capture_digest: str
    issuer_implementation_revision: str
    p1_adapter_implementation_digest: str
    evidence_snapshot_id: str
    raw_record_digest: str
    evidence_complete_envelope_digest: str
    canonical_content_digest: str
    canonicalization_profile_digest: str
    legacy_format: str
    adapter_profile_id: str
    adapter_profile_digest: str
    adapter_implementation_digest: str
    capability_vector: CapabilityVectorV2
    condition_neutral_evidence_availability: ConditionNeutralEvidenceAvailabilityV2

    _FIELDS = {
        "header",
        "p1_authority_artifact_id",
        "p1_authority_digest",
        "construct_freeze_artifact_id",
        "construct_freeze_digest",
        "episode_id",
        "occurrence_reference",
        "occurrence_issuance_digest",
        "source_authority_digest",
        "source_capture_digest",
        "issuer_implementation_revision",
        "p1_adapter_implementation_digest",
        "evidence_snapshot_id",
        "raw_record_digest",
        "evidence_complete_envelope_digest",
        "canonical_content_digest",
        "canonicalization_profile_digest",
        "legacy_format",
        "adapter_profile_id",
        "adapter_profile_digest",
        "adapter_implementation_digest",
        "capability_vector",
        "condition_neutral_evidence_availability",
    }

    def __init__(
        self,
        *,
        _token: object,
        header: ArtifactHeaderV1,
        p1_authority_artifact_id: str,
        p1_authority_digest: str,
        construct_freeze_artifact_id: str,
        construct_freeze_digest: str,
        episode_id: str,
        occurrence_reference: OccurrenceReferenceV2,
        occurrence_issuance_digest: str,
        source_authority_digest: str,
        source_capture_digest: str,
        issuer_implementation_revision: str,
        p1_adapter_implementation_digest: str,
        evidence_snapshot_id: str,
        raw_record_digest: str,
        evidence_complete_envelope_digest: str,
        canonical_content_digest: str,
        canonicalization_profile_digest: str,
        legacy_format: str,
        adapter_profile_id: str,
        adapter_profile_digest: str,
        adapter_implementation_digest: str,
        capability_vector: CapabilityVectorV2,
        condition_neutral_evidence_availability: ConditionNeutralEvidenceAvailabilityV2,
    ) -> None:
        if _token is not _CAPABILITY_ISSUANCE_TOKEN:
            raise TypeError(
                "CapabilityManifestV2 is issuer-finalized only; "
                "derive it from verified V2-01C authority"
            )
        values = {
            "header": header,
            "p1_authority_artifact_id": p1_authority_artifact_id,
            "p1_authority_digest": p1_authority_digest,
            "construct_freeze_artifact_id": construct_freeze_artifact_id,
            "construct_freeze_digest": construct_freeze_digest,
            "episode_id": episode_id,
            "occurrence_reference": occurrence_reference,
            "occurrence_issuance_digest": occurrence_issuance_digest,
            "source_authority_digest": source_authority_digest,
            "source_capture_digest": source_capture_digest,
            "issuer_implementation_revision": issuer_implementation_revision,
            "p1_adapter_implementation_digest": p1_adapter_implementation_digest,
            "evidence_snapshot_id": evidence_snapshot_id,
            "raw_record_digest": raw_record_digest,
            "evidence_complete_envelope_digest": evidence_complete_envelope_digest,
            "canonical_content_digest": canonical_content_digest,
            "canonicalization_profile_digest": canonicalization_profile_digest,
            "legacy_format": legacy_format,
            "adapter_profile_id": adapter_profile_id,
            "adapter_profile_digest": adapter_profile_digest,
            "adapter_implementation_digest": adapter_implementation_digest,
            "capability_vector": capability_vector,
            "condition_neutral_evidence_availability": condition_neutral_evidence_availability,
        }
        for name, value in values.items():
            object.__setattr__(self, name, value)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CapabilityManifestV2":
        data = _require_dict(data, "CapabilityManifestV2")
        _require_no_unknown_props(data, cls._FIELDS, "CapabilityManifestV2")
        try:
            occurrence = OccurrenceReferenceV2.from_dict(
                _require_dict(_required(data, "occurrence_reference"), "occurrence_reference")
            )
            vector = CapabilityVectorV2.from_dict(
                _require_dict(_required(data, "capability_vector"), "capability_vector")
            )
            availability = ConditionNeutralEvidenceAvailabilityV2.from_dict(
                _require_dict(
                    _required(data, "condition_neutral_evidence_availability"),
                    "condition_neutral_evidence_availability",
                )
            )
            return cls(
                _token=_CAPABILITY_ISSUANCE_TOKEN,
                header=ArtifactHeaderV1.from_dict(
                    _require_dict(_required(data, "header"), "header")
                ),
                p1_authority_artifact_id=_require_str(
                    _required(data, "p1_authority_artifact_id"),
                    "p1_authority_artifact_id",
                ),
                p1_authority_digest=_digest(
                    _required(data, "p1_authority_digest"), "p1_authority_digest"
                ),
                construct_freeze_artifact_id=_require_str(
                    _required(data, "construct_freeze_artifact_id"),
                    "construct_freeze_artifact_id",
                ),
                construct_freeze_digest=_digest(
                    _required(data, "construct_freeze_digest"), "construct_freeze_digest"
                ),
                episode_id=_require_str(_required(data, "episode_id"), "episode_id"),
                occurrence_reference=occurrence,
                occurrence_issuance_digest=_digest(
                    _required(data, "occurrence_issuance_digest"),
                    "occurrence_issuance_digest",
                ),
                source_authority_digest=_digest(
                    _required(data, "source_authority_digest"), "source_authority_digest"
                ),
                source_capture_digest=_digest(
                    _required(data, "source_capture_digest"), "source_capture_digest"
                ),
                issuer_implementation_revision=_require_str(
                    _required(data, "issuer_implementation_revision"),
                    "issuer_implementation_revision",
                ),
                p1_adapter_implementation_digest=_digest(
                    _required(data, "p1_adapter_implementation_digest"),
                    "p1_adapter_implementation_digest",
                ),
                evidence_snapshot_id=_require_str(
                    _required(data, "evidence_snapshot_id"), "evidence_snapshot_id"
                ),
                raw_record_digest=_digest(
                    _required(data, "raw_record_digest"), "raw_record_digest"
                ),
                evidence_complete_envelope_digest=_digest(
                    _required(data, "evidence_complete_envelope_digest"),
                    "evidence_complete_envelope_digest",
                ),
                canonical_content_digest=_digest(
                    _required(data, "canonical_content_digest"),
                    "canonical_content_digest",
                ),
                canonicalization_profile_digest=_digest(
                    _required(data, "canonicalization_profile_digest"),
                    "canonicalization_profile_digest",
                ),
                legacy_format=_require_str(
                    _required(data, "legacy_format"), "legacy_format"
                ),
                adapter_profile_id=_require_str(
                    _required(data, "adapter_profile_id"), "adapter_profile_id"
                ),
                adapter_profile_digest=_digest(
                    _required(data, "adapter_profile_digest"), "adapter_profile_digest"
                ),
                adapter_implementation_digest=_digest(
                    _required(data, "adapter_implementation_digest"),
                    "adapter_implementation_digest",
                ),
                capability_vector=vector,
                condition_neutral_evidence_availability=availability,
            )
        except KeyError as exc:
            # Nested contract implementations may still use direct indexing.
            raise StructuralContractError(
                f"CapabilityManifestV2: missing required property '{exc.args[0]}'"
            ) from exc

    @classmethod
    def from_canonical_bytes(cls, canonical_bytes: bytes) -> "CapabilityManifestV2":
        if not isinstance(canonical_bytes, bytes):
            raise TypeError("CapabilityManifestV2 canonical bytes must be bytes")
        try:
            data = json.loads(canonical_bytes.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise StructuralContractError(
                "CapabilityManifestV2: invalid canonical bytes"
            ) from exc
        data = _require_dict(data, "CapabilityManifestV2")
        if canonical_artifact_bytes(data) != canonical_bytes:
            raise StructuralContractError("CapabilityManifestV2: canonical bytes mismatch")
        return cls.from_dict(data)

    def to_dict(self) -> dict[str, Any]:
        return {
            "header": self.header.to_dict(),
            "p1_authority_artifact_id": self.p1_authority_artifact_id,
            "p1_authority_digest": self.p1_authority_digest,
            "construct_freeze_artifact_id": self.construct_freeze_artifact_id,
            "construct_freeze_digest": self.construct_freeze_digest,
            "episode_id": self.episode_id,
            "occurrence_reference": self.occurrence_reference.to_dict(),
            "occurrence_issuance_digest": self.occurrence_issuance_digest,
            "source_authority_digest": self.source_authority_digest,
            "source_capture_digest": self.source_capture_digest,
            "issuer_implementation_revision": self.issuer_implementation_revision,
            "p1_adapter_implementation_digest": self.p1_adapter_implementation_digest,
            "evidence_snapshot_id": self.evidence_snapshot_id,
            "raw_record_digest": self.raw_record_digest,
            "evidence_complete_envelope_digest": self.evidence_complete_envelope_digest,
            "canonical_content_digest": self.canonical_content_digest,
            "canonicalization_profile_digest": self.canonicalization_profile_digest,
            "legacy_format": self.legacy_format,
            "adapter_profile_id": self.adapter_profile_id,
            "adapter_profile_digest": self.adapter_profile_digest,
            "adapter_implementation_digest": self.adapter_implementation_digest,
            "capability_vector": self.capability_vector.to_dict(),
            "condition_neutral_evidence_availability": (
                self.condition_neutral_evidence_availability.to_dict()
            ),
        }


@dataclass(frozen=True)
class SealedCapabilityManifestV2:
    """Portable capability bytes whose authority is re-established on verify."""

    manifest: CapabilityManifestV2
    canonical_bytes: bytes
    content_digest: str

    @classmethod
    def from_canonical_bytes(cls, canonical_bytes: bytes) -> "SealedCapabilityManifestV2":
        manifest = CapabilityManifestV2.from_canonical_bytes(canonical_bytes)
        return cls(
            manifest=manifest,
            canonical_bytes=canonical_bytes,
            content_digest=_compute_content_digest(manifest.to_dict()),
        )

    def to_dict(self) -> dict[str, Any]:
        return self.manifest.to_dict()


# Descriptive aliases make the boundary explicit to callers without creating
# a second artifact or identity scheme.
OccurrenceCapabilityManifestV2 = CapabilityManifestV2
SealedOccurrenceCapabilityV2 = SealedCapabilityManifestV2


def _require_sealed_p1(authority: Any) -> SealedP1AuthorityV2:
    if type(authority) is not SealedP1AuthorityV2:  # pylint: disable=unidiomatic-typecheck
        raise TypeError(
            "capability derivation requires an issued SealedP1AuthorityV2; "
            "raw occurrence claims are not accepted"
        )
    return authority


def _construct_parent(p1: EvidenceSealManifestV2) -> Any:
    parents = [parent for parent in p1.immediate_parents if parent.parent_kind == "construct_freeze"]
    if len(parents) != 1:
        raise StructuralContractError(
            "capability derivation requires exactly one construct-freeze parent"
        )
    return parents[0]


def _verified_p1_context(
    p1_authority: SealedP1AuthorityV2,
    *,
    p0_repository: "ConstructFreezeAuthorityRepository | None",
    issuance_repository: Any,
    lineage_repository: "LineageAttestationRepository | None",
    authority_source: "IndependentAuthoritySourceV2 | None",
) -> tuple[SealedP1AuthorityV2, IssuanceAuthorityRecordV2]:
    p1_authority = _require_sealed_p1(p1_authority)
    verified = verify_sealed_p1_authority(
        p1_authority,
        p0_repository=p0_repository,
        lineage_repository=lineage_repository,
        issuance_repository=issuance_repository,
        authority_source=authority_source,
    )
    record = issuance_repository.resolve(verified.manifest.occurrence_issuance_digest)
    if type(record) is not IssuanceAuthorityRecordV2:  # pylint: disable=unidiomatic-typecheck
        raise StructuralContractError("capability derivation: invalid issuance authority record")
    if record.occurrence_reference.to_dict() != verified.manifest.occurrence_reference.to_dict():
        raise StructuralContractError("capability derivation: issuance occurrence mismatch")
    if record.raw_record_digest != verified.manifest.raw_record_digest:
        raise StructuralContractError("capability derivation: issuance raw-record mismatch")
    return verified, record


def _profile_for_derivation(legacy_format: Any) -> EvidenceAdapterProfileV2:
    if not isinstance(legacy_format, str) or not legacy_format:
        raise StructuralContractError("capability derivation requires a legacy format")
    profile = resolve_profile_or_fail(legacy_format)
    profile.validate()
    if profile.capability_vector.occurrence_identity.value == "NATIVE_UNIQUE":
        raise StructuralContractError(
            "capability derivation: V2-01C does not prove universal native uniqueness"
        )
    if profile.capability_vector.source_instance_binding.value == "ABSENT":
        raise StructuralContractError(
            "capability derivation: profile has no source-instance binding"
        )
    return profile


def _manifest_from_verified_p1(
    p1: SealedP1AuthorityV2,
    record: IssuanceAuthorityRecordV2,
    profile: EvidenceAdapterProfileV2,
) -> CapabilityManifestV2:
    p1_manifest = p1.manifest
    p1_digest = p1_manifest.header.content_digest
    if not p1_digest:
        raise StructuralContractError("capability derivation: P1 authority has no content digest")
    parent = _construct_parent(p1_manifest)
    raw_record_digest = p1_manifest.raw_record_digest
    if raw_record_digest is None:
        raise StructuralContractError("capability derivation: P1 authority has no raw-record binding")
    if record.source_capture_digest == "":
        raise StructuralContractError("capability derivation: issuance has no source capture binding")
    if p1_manifest.adapter_implementation_digest != profile.adapter_implementation_digest:
        raise StructuralContractError(
            "capability derivation: adapter profile is not the verified P1 adapter"
        )
    return CapabilityManifestV2(
        _token=_CAPABILITY_ISSUANCE_TOKEN,
        header=ArtifactHeaderV1(
            artifact_id="pending",
            schema_version=CAPABILITY_MANIFEST_SCHEMA,
            parent_artifact_id=p1_manifest.header.artifact_id,
            parent_digest=p1_digest,
            created_at=p1_manifest.header.created_at,
            seal_time=None,
            responsible_role="evidence_adapter",
            content_digest=None,
            sealed=False,
        ),
        p1_authority_artifact_id=p1_manifest.header.artifact_id,
        p1_authority_digest=p1_digest,
        construct_freeze_artifact_id=parent.parent_artifact_id,
        construct_freeze_digest=p1_manifest.construct_freeze_digest,
        episode_id=p1_manifest.episode_id,
        occurrence_reference=p1_manifest.occurrence_reference,
        occurrence_issuance_digest=p1_manifest.occurrence_issuance_digest,
        source_authority_digest=p1_manifest.source_authority_digest,
        source_capture_digest=record.source_capture_digest,
        issuer_implementation_revision=p1_manifest.issuer_implementation_revision,
        p1_adapter_implementation_digest=p1_manifest.adapter_implementation_digest,
        evidence_snapshot_id=p1_manifest.evidence_snapshot_id,
        raw_record_digest=raw_record_digest,
        evidence_complete_envelope_digest=p1_manifest.evidence_complete_envelope_digest,
        canonical_content_digest=p1_manifest.canonical_content_digest,
        canonicalization_profile_digest=p1_manifest.canonicalization_profile_digest,
        legacy_format=profile.legacy_format or "",
        adapter_profile_id=profile.profile_id,
        adapter_profile_digest=profile_content_digest(profile),
        adapter_implementation_digest=profile.adapter_implementation_digest,
        capability_vector=profile.capability_vector,
        condition_neutral_evidence_availability=(
            p1_manifest.condition_neutral_evidence_availability
        ),
    )


def _seal_manifest(
    manifest: CapabilityManifestV2,
    *,
    p1_authority: SealedP1AuthorityV2,
    p0_repository: "ConstructFreezeAuthorityRepository | None",
    issuance_repository: Any,
    lineage_repository: "LineageAttestationRepository | None",
    authority_source: "IndependentAuthoritySourceV2 | None",
) -> SealedCapabilityManifestV2:
    content_digest = _compute_content_digest(manifest.to_dict())
    header = ArtifactHeaderV1(
        artifact_id=_derive_artifact_id(content_digest),
        schema_version=CAPABILITY_MANIFEST_SCHEMA,
        parent_artifact_id=manifest.header.parent_artifact_id,
        parent_digest=manifest.header.parent_digest,
        created_at=manifest.header.created_at,
        seal_time=p1_authority.manifest.header.seal_time,
        responsible_role=manifest.header.responsible_role,
        content_digest=content_digest,
        sealed=True,
    )
    final = CapabilityManifestV2(
        _token=_CAPABILITY_ISSUANCE_TOKEN,
        header=header,
        p1_authority_artifact_id=manifest.p1_authority_artifact_id,
        p1_authority_digest=manifest.p1_authority_digest,
        construct_freeze_artifact_id=manifest.construct_freeze_artifact_id,
        construct_freeze_digest=manifest.construct_freeze_digest,
        episode_id=manifest.episode_id,
        occurrence_reference=manifest.occurrence_reference,
        occurrence_issuance_digest=manifest.occurrence_issuance_digest,
        source_authority_digest=manifest.source_authority_digest,
        source_capture_digest=manifest.source_capture_digest,
        issuer_implementation_revision=manifest.issuer_implementation_revision,
        p1_adapter_implementation_digest=manifest.p1_adapter_implementation_digest,
        evidence_snapshot_id=manifest.evidence_snapshot_id,
        raw_record_digest=manifest.raw_record_digest,
        evidence_complete_envelope_digest=manifest.evidence_complete_envelope_digest,
        canonical_content_digest=manifest.canonical_content_digest,
        canonicalization_profile_digest=manifest.canonicalization_profile_digest,
        legacy_format=manifest.legacy_format,
        adapter_profile_id=manifest.adapter_profile_id,
        adapter_profile_digest=manifest.adapter_profile_digest,
        adapter_implementation_digest=manifest.adapter_implementation_digest,
        capability_vector=manifest.capability_vector,
        condition_neutral_evidence_availability=manifest.condition_neutral_evidence_availability,
    )
    sealed = SealedCapabilityManifestV2(
        manifest=final,
        canonical_bytes=canonical_artifact_bytes(final.to_dict()),
        content_digest=content_digest,
    )
    return verify_capability_manifest(
        sealed,
        p1_authority=p1_authority,
        p0_repository=p0_repository,
        issuance_repository=issuance_repository,
        lineage_repository=lineage_repository,
        authority_source=authority_source,
    )


def derive_capability_manifest(
    p1_authority: SealedP1AuthorityV2,
    *,
    legacy_format: str,
    p0_repository: "ConstructFreezeAuthorityRepository | None" = None,
    issuance_repository: Any = None,
    lineage_repository: "LineageAttestationRepository | None" = None,
    authority_source: "IndependentAuthoritySourceV2 | None" = None,
) -> SealedCapabilityManifestV2:
    """Derive and seal capability from verified V2-01C P1 authority only."""

    if issuance_repository is None:
        raise StructuralContractError("capability derivation requires issuance repository")
    verified, record = _verified_p1_context(
        p1_authority,
        p0_repository=p0_repository,
        issuance_repository=issuance_repository,
        lineage_repository=lineage_repository,
        authority_source=authority_source,
    )
    profile = _profile_for_derivation(legacy_format)
    return _seal_manifest(
        _manifest_from_verified_p1(verified, record, profile),
        p1_authority=verified,
        p0_repository=p0_repository,
        issuance_repository=issuance_repository,
        lineage_repository=lineage_repository,
        authority_source=authority_source,
    )


def _coerce_capability_input(
    authority: SealedCapabilityManifestV2 | bytes | dict[str, Any],
) -> SealedCapabilityManifestV2:
    if isinstance(authority, bytes):
        return SealedCapabilityManifestV2.from_canonical_bytes(authority)
    if type(authority) is SealedCapabilityManifestV2:  # pylint: disable=unidiomatic-typecheck
        return authority
    if isinstance(authority, dict):
        manifest = CapabilityManifestV2.from_dict(authority)
        return SealedCapabilityManifestV2(
            manifest=manifest,
            canonical_bytes=canonical_artifact_bytes(manifest.to_dict()),
            content_digest=_compute_content_digest(manifest.to_dict()),
        )
    raise TypeError(
        "capability verification requires canonical bytes, a sealed capability, or a mapping"
    )


def _verify_profile_binding(manifest: CapabilityManifestV2) -> None:
    profile = _profile_for_derivation(manifest.legacy_format)
    if profile.profile_id != manifest.adapter_profile_id:
        raise StructuralContractError("capability manifest: adapter profile identity mismatch")
    if profile_content_digest(profile) != manifest.adapter_profile_digest:
        raise StructuralContractError("capability manifest: adapter profile content mismatch")
    if profile.adapter_implementation_digest != manifest.adapter_implementation_digest:
        raise StructuralContractError("capability manifest: adapter implementation mismatch")
    if manifest.p1_adapter_implementation_digest != manifest.adapter_implementation_digest:
        raise StructuralContractError(
            "capability manifest: profile is not bound to the verified P1 adapter"
        )
    if profile.capability_vector.to_dict() != manifest.capability_vector.to_dict():
        raise StructuralContractError("capability manifest: capability vector is not derived")


def _compare_p1_bindings(
    manifest: CapabilityManifestV2,
    p1: SealedP1AuthorityV2,
    record: IssuanceAuthorityRecordV2,
) -> None:
    p1_manifest = p1.manifest
    p1_digest = p1_manifest.header.content_digest
    parent = _construct_parent(p1_manifest)
    expected = {
        "p1_authority_artifact_id": p1_manifest.header.artifact_id,
        "p1_authority_digest": p1_digest,
        "construct_freeze_artifact_id": parent.parent_artifact_id,
        "construct_freeze_digest": p1_manifest.construct_freeze_digest,
        "episode_id": p1_manifest.episode_id,
        "occurrence_issuance_digest": p1_manifest.occurrence_issuance_digest,
        "source_authority_digest": p1_manifest.source_authority_digest,
        "source_capture_digest": record.source_capture_digest,
        "issuer_implementation_revision": p1_manifest.issuer_implementation_revision,
        "p1_adapter_implementation_digest": p1_manifest.adapter_implementation_digest,
        "evidence_snapshot_id": p1_manifest.evidence_snapshot_id,
        "raw_record_digest": p1_manifest.raw_record_digest,
        "evidence_complete_envelope_digest": p1_manifest.evidence_complete_envelope_digest,
        "canonical_content_digest": p1_manifest.canonical_content_digest,
        "canonicalization_profile_digest": p1_manifest.canonicalization_profile_digest,
    }
    for field_name, expected_value in expected.items():
        if getattr(manifest, field_name) != expected_value:
            raise StructuralContractError(
                f"capability manifest: {field_name} is not bound to verified P1"
            )
    if manifest.occurrence_reference.to_dict() != p1_manifest.occurrence_reference.to_dict():
        raise StructuralContractError("capability manifest: occurrence reference mismatch")
    if (
        manifest.condition_neutral_evidence_availability
        != p1_manifest.condition_neutral_evidence_availability
    ):
        raise StructuralContractError("capability manifest: availability is not derived from P1")


def verify_capability_manifest(
    authority: SealedCapabilityManifestV2 | bytes | dict[str, Any],
    *,
    p1_authority: SealedP1AuthorityV2 | None = None,
    p0_repository: "ConstructFreezeAuthorityRepository | None" = None,
    issuance_repository: Any = None,
    lineage_repository: "LineageAttestationRepository | None" = None,
    authority_source: "IndependentAuthoritySourceV2 | None" = None,
) -> SealedCapabilityManifestV2:
    """Parse and verify capability plus its complete source-backed P1 parent."""

    if p1_authority is None:
        raise StructuralContractError(
            "capability verification requires source-backed SealedP1AuthorityV2"
        )
    if issuance_repository is None:
        raise StructuralContractError("capability verification requires issuance repository")
    capability = _coerce_capability_input(authority)
    p1, record = _verified_p1_context(
        _require_sealed_p1(p1_authority),
        p0_repository=p0_repository,
        issuance_repository=issuance_repository,
        lineage_repository=lineage_repository,
        authority_source=authority_source,
    )
    manifest = capability.manifest
    header = manifest.header
    if header.schema_version != CAPABILITY_MANIFEST_SCHEMA:
        raise StructuralContractError("capability manifest: wrong schema_version")
    if not header.sealed or not header.seal_time:
        raise StructuralContractError("capability manifest: unsealed or missing seal_time")
    if header.responsible_role != "evidence_adapter":
        raise StructuralContractError("capability manifest: invalid responsible_role")
    if not header.content_digest:
        raise StructuralContractError("capability manifest: missing content_digest")
    if header.parent_artifact_id != manifest.p1_authority_artifact_id:
        raise StructuralContractError("capability manifest: P1 parent artifact mismatch")
    if header.parent_digest != manifest.p1_authority_digest:
        raise StructuralContractError("capability manifest: P1 parent digest mismatch")
    _compare_p1_bindings(manifest, p1, record)
    _verify_profile_binding(manifest)
    recomputed = _compute_content_digest(manifest.to_dict())
    if recomputed != header.content_digest:
        raise StructuralContractError("capability manifest: content digest mismatch")
    if recomputed != capability.content_digest:
        raise StructuralContractError("capability manifest: wrapper content digest mismatch")
    if header.artifact_id != _derive_artifact_id(recomputed):
        raise StructuralContractError("capability manifest: artifact ID mismatch")
    if canonical_artifact_bytes(manifest.to_dict()) != capability.canonical_bytes:
        raise StructuralContractError("capability manifest: canonical bytes mismatch")
    return capability


def parse_capability_manifest_v2(
    canonical_bytes: bytes,
    *,
    p1_authority: SealedP1AuthorityV2 | None = None,
    p0_repository: "ConstructFreezeAuthorityRepository | None" = None,
    issuance_repository: Any = None,
    lineage_repository: "LineageAttestationRepository | None" = None,
    authority_source: "IndependentAuthoritySourceV2 | None" = None,
) -> SealedCapabilityManifestV2:
    """Public byte-loading path; it cannot grant authority without V2-01C P1."""

    if not isinstance(canonical_bytes, bytes):
        raise TypeError("parse_capability_manifest_v2 requires canonical bytes")
    return verify_capability_manifest(
        canonical_bytes,
        p1_authority=p1_authority,
        p0_repository=p0_repository,
        issuance_repository=issuance_repository,
        lineage_repository=lineage_repository,
        authority_source=authority_source,
    )


# Explicit name for callers that describe issuance as occurrence derivation.
derive_capability_for_occurrence = derive_capability_manifest

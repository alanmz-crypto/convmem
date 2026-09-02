"""Fail-closed P1 validators for V2 identity and evidence seal invariants."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from eval_naturalistic.base import NaturalisticValidation, StructuralContractError
from eval_naturalistic.v2.contracts import (
    EvidenceAvailabilityManifestV2,
    EvidenceSealManifestV2,
    P1_FORBIDDEN_FIELDS,
    SnapshotAuthorityDecisionV2,
)
from eval_naturalistic.v2.evidence import (
    ConditionNeutralEvidenceAvailabilityV2,
    PostSealSourceStateV2,
    SourcePresenceV2,
    VerbatimEvidenceAvailabilityV2,
    normalized_reported_presence,
)
from eval_naturalistic.v2.authority_issuance import (
    IssuanceAuthorityRepository,
    SealedP1AuthorityV2,
    reject_raw_unfinalized_p1,
    verify_sealed_p1_authority,
)
from eval_naturalistic.v2.lineage_attestation import LineageAttestationRepository
from eval_naturalistic.v2.p0_construct import ConstructFreezeAuthorityRepository
from eval_naturalistic.v2.identity import (
    LineageEdgeV2,
    OccurrenceReferenceV2,
    reject_hash_or_locator_identity,
)


@dataclass(frozen=True)
class RevisionBindingObservationV2:
    """Observed revision/as-of at validation time."""

    revision_or_asof_id: str
    physical_instance_id: str


def validate_p1_forbidden_fields(data: dict[str, Any], *, label: str) -> None:
    present = P1_FORBIDDEN_FIELDS & set(data)
    if present:
        names = ", ".join(sorted(present))
        raise StructuralContractError(f"{label}: forbidden P1 fields present: {names}")


def validate_occurrence_binding(manifest: EvidenceSealManifestV2) -> None:
    occ = manifest.occurrence_reference
    if occ.physical_source_instance_id != manifest.physical_instance_id:
        raise StructuralContractError(
            "physical_instance_id must bind occurrence_reference.physical_source_instance_id"
        )
    if occ.source_revision_or_asof_id != manifest.revision_or_asof_id:
        raise StructuralContractError(
            "revision_or_asof_id must bind occurrence_reference.source_revision_or_asof_id"
        )


def validate_lineage_preserves_physical_separation(edges: list[LineageEdgeV2]) -> None:
    for edge in edges:
        if not edge.preserves_physical_separation():
            raise StructuralContractError(
                "lineage edge must not collapse distinct physical instances"
            )


def validate_distinct_occurrences(
    left: OccurrenceReferenceV2, right: OccurrenceReferenceV2, *, context: str
) -> None:
    if left.same_occurrence_as(right):
        raise StructuralContractError(
            f"{context}: occurrence references must remain distinct"
        )


def validate_native_id_reuse_is_not_same_occurrence(
    left: OccurrenceReferenceV2, right: OccurrenceReferenceV2
) -> None:
    if left.native_record_identity() != right.native_record_identity():
        return
    if left.physical_source_instance_id == right.physical_source_instance_id:
        if left.source_revision_or_asof_id == right.source_revision_or_asof_id:
            raise StructuralContractError(
                "identical native record in same instance and revision is the same occurrence"
            )
        return
    if left.same_occurrence_as(right):
        raise StructuralContractError(
            "native ID reuse across instances must not collapse into one occurrence"
        )


def validate_duplicate_content_distinct_occurrences(
    left: EvidenceSealManifestV2, right: EvidenceSealManifestV2
) -> None:
    if left.canonical_content_digest != right.canonical_content_digest:
        return
    validate_distinct_occurrences(
        left.occurrence_reference,
        right.occurrence_reference,
        context="duplicate content across occurrences",
    )


def validate_revision_binding(
    manifest: EvidenceSealManifestV2,
    observed: RevisionBindingObservationV2,
) -> None:
    if manifest.physical_instance_id != observed.physical_instance_id:
        raise StructuralContractError(
            "revision binding observed on wrong physical instance"
        )
    if manifest.revision_or_asof_id != observed.revision_or_asof_id:
        raise StructuralContractError(
            "revision_or_asof mismatch: mutable evidence bound to wrong revision/as-of"
        )


def validate_issue_263_availability(
    availability: ConditionNeutralEvidenceAvailabilityV2,
) -> None:
    availability.validate_issue_263()
    reported = normalized_reported_presence(availability)
    if (
        availability.source_presence == SourcePresenceV2.PRESENT
        and availability.verbatim_evidence_availability
        == VerbatimEvidenceAvailabilityV2.UNAVAILABLE
        and reported == SourcePresenceV2.ABSENT
    ):
        raise StructuralContractError(
            "Issue #263: source present with verbatim unavailable must never become absent"
        )


def evaluate_post_seal_source_state(
    *,
    capture_obligation_satisfied: bool,
    capture_time_occurrence_revision_match: bool,
    preserved_package_integrity: bool,
    post_seal_source_state: PostSealSourceStateV2,
) -> SnapshotAuthorityDecisionV2:
    """Apply locked snapshot_authority ordered decision rules."""

    if not capture_obligation_satisfied:
        return SnapshotAuthorityDecisionV2(
            result="PROTOCOL_OR_INSTRUMENTATION_FAILURE",
            package_use="NON_NORMATIVE",
            post_seal_source_state=post_seal_source_state,
        )
    if not capture_time_occurrence_revision_match:
        return SnapshotAuthorityDecisionV2(
            result="INTEGRITY_FAILURE",
            package_use="NON_NORMATIVE",
            post_seal_source_state=post_seal_source_state,
        )
    if not preserved_package_integrity:
        return SnapshotAuthorityDecisionV2(
            result="PRESERVATION_FAILURE",
            package_use="NON_EVALUABLE",
            post_seal_source_state=post_seal_source_state,
        )
    if post_seal_source_state == PostSealSourceStateV2.UNCHANGED:
        return SnapshotAuthorityDecisionV2(
            result="VALID_SEALED_EVIDENCE",
            package_use="NORMATIVE_WITH_CAPABILITY_CEILING",
            post_seal_source_state=post_seal_source_state,
        )
    if post_seal_source_state == PostSealSourceStateV2.MODIFIED:
        return SnapshotAuthorityDecisionV2(
            result="VALID_ASOF_SEALED_EVIDENCE_WITH_SOURCE_DRIFT_DIAGNOSTIC",
            package_use="NORMATIVE_WITH_CAPTURE_TIME_CAPABILITY_CEILING",
            post_seal_source_state=post_seal_source_state,
        )
    if post_seal_source_state == PostSealSourceStateV2.DELETED:
        return SnapshotAuthorityDecisionV2(
            result="VALID_ASOF_SEALED_EVIDENCE_WITH_SOURCE_DELETION_DIAGNOSTIC",
            package_use="NORMATIVE_WITH_CAPTURE_TIME_CAPABILITY_CEILING",
            post_seal_source_state=post_seal_source_state,
        )
    return SnapshotAuthorityDecisionV2(
        result="INVALID_UNCLASSIFIED_AUTHORITY_STATE",
        package_use="NON_NORMATIVE",
        post_seal_source_state=post_seal_source_state,
    )


def validate_evidence_seal_manifest(manifest: EvidenceSealManifestV2) -> NaturalisticValidation:
    errors: list[str] = []
    try:
        validate_occurrence_binding(manifest)
        validate_lineage_preserves_physical_separation(list(manifest.lineage_edges))
        validate_issue_263_availability(manifest.condition_neutral_evidence_availability)
        if manifest.header.schema_version != EvidenceSealManifestV2.SCHEMA:
            errors.append("EvidenceSealManifestV2 schema_version mismatch")
        if manifest.header.schema_version.startswith("convmem/naturalistic/") and (
            "/v2/" not in manifest.header.schema_version
        ):
            errors.append("V1 schema must not be accepted as EvidenceSealManifestV2")
    except StructuralContractError as exc:
        errors.append(str(exc))
    return NaturalisticValidation(errors=errors)


def validate_availability_manifest(
    manifest: EvidenceAvailabilityManifestV2,
    *,
    seal: EvidenceSealManifestV2,
) -> NaturalisticValidation:
    errors: list[str] = []
    try:
        validate_issue_263_availability(manifest.availability)
        if manifest.episode_id != seal.episode_id:
            errors.append("availability manifest episode_id mismatch")
        if not manifest.occurrence_reference.same_occurrence_as(seal.occurrence_reference):
            errors.append("availability manifest occurrence_reference mismatch")
        if manifest.header.schema_version != EvidenceAvailabilityManifestV2.SCHEMA:
            errors.append("EvidenceAvailabilityManifestV2 schema_version mismatch")
    except StructuralContractError as exc:
        errors.append(str(exc))
    return NaturalisticValidation(errors=errors)


def parse_evidence_seal_manifest_v2(
    data: dict[str, Any],
    *,
    p0_repository: ConstructFreezeAuthorityRepository | None = None,
    lineage_repository: LineageAttestationRepository | None = None,
    issuance_repository: IssuanceAuthorityRepository | None = None,
) -> EvidenceSealManifestV2:
    validate_p1_forbidden_fields(data, label="EvidenceSealManifestV2")
    reject_hash_or_locator_identity(data.get("occurrence_reference", {}))
    manifest = EvidenceSealManifestV2.from_dict(data)
    result = validate_evidence_seal_manifest(manifest)
    if not result.ok:
        raise StructuralContractError("; ".join(result.errors))
    sealed = verify_sealed_p1_authority(
        manifest.to_dict(),
        p0_repository=p0_repository,
        lineage_repository=lineage_repository,
        issuance_repository=issuance_repository,
    )
    return sealed.manifest


def parse_sealed_p1_authority_v2(
    data: dict[str, Any],
    *,
    p0_repository: ConstructFreezeAuthorityRepository | None = None,
    lineage_repository: LineageAttestationRepository | None = None,
    issuance_repository: IssuanceAuthorityRepository | None = None,
) -> SealedP1AuthorityV2:
    """Parse and independently verify sealed P1 authority bytes."""

    manifest = parse_evidence_seal_manifest_v2(
        data,
        p0_repository=p0_repository,
        lineage_repository=lineage_repository,
        issuance_repository=issuance_repository,
    )
    return verify_sealed_p1_authority(
        manifest.to_dict(),
        p0_repository=p0_repository,
        lineage_repository=lineage_repository,
        issuance_repository=issuance_repository,
    )


def parse_evidence_availability_manifest_v2(
    data: dict[str, Any],
    *,
    seal: EvidenceSealManifestV2,
) -> EvidenceAvailabilityManifestV2:
    validate_p1_forbidden_fields(data, label="EvidenceAvailabilityManifestV2")
    manifest = EvidenceAvailabilityManifestV2.from_dict(data)
    result = validate_availability_manifest(manifest, seal=seal)
    if not result.ok:
        raise StructuralContractError("; ".join(result.errors))
    return manifest

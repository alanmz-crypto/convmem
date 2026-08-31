"""Read-only opaque P2 resolver over sealed P1 evidence packages."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any

from eval_naturalistic.base import ArtifactHeaderV1, StructuralContractError
from eval_naturalistic.digest import artifact_content_digest, canonical_artifact_bytes
from eval_naturalistic.v2.adapters.capability import (
    CapabilityVectorV2,
    EvidenceCompletenessCapability,
    OccurrenceIdentityCapability,
)
from eval_naturalistic.v2.adapters.profile import EvidenceAdapterProfileV2
from eval_naturalistic.v2.contracts import (
    EvidenceAvailabilityManifestV2,
    EvidenceSealManifestV2,
)
from eval_naturalistic.v2.evidence import (
    SourcePresenceV2,
    SummaryEvidenceAvailabilityV2,
    VerbatimEvidenceAvailabilityV2,
    normalized_reported_presence,
)
from eval_naturalistic.v2.firewall import reject_p2_fields_on_p1
from eval_naturalistic.v2.identity import OccurrenceReferenceV2, reject_hash_or_locator_identity
from eval_naturalistic.v2.resolver_contracts import (
    OpaqueResolverManifestV2,
    ResolutionDetailV2,
    ResolverResultV2,
)

RESOLVER_IMPLEMENTATION_ID = "v2/opaque-resolver/1"
RESOLVER_FORBIDDEN_OUTPUT_FIELDS = frozenset(
    {
        "registry_membership",
        "target_census",
        "target_ground_truth",
        "probe_keys",
        "agent_b_outputs",
        "scores",
        "effects",
        "discovered_targets",
        "eligible_targets",
    }
)


def resolver_implementation_digest() -> str:
    payload = {"implementation_id": RESOLVER_IMPLEMENTATION_ID, "read_only": True}
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()


@dataclass(frozen=True)
class ResolverInputV2:
    """Complete bound input tuple for compute-once opaque resolution."""

    construct_freeze_digest: str
    evidence_seal: EvidenceSealManifestV2
    evidence_availability: EvidenceAvailabilityManifestV2
    adapter_profile: EvidenceAdapterProfileV2
    legacy_format: str
    query_occurrence_reference: OccurrenceReferenceV2
    observed_canonical_content_digest: str | None = None
    observed_physical_instance_id: str | None = None
    observed_revision_or_asof_id: str | None = None
    ambiguous_candidate_count: int = 1
    allow_hash_locator_fallback: bool = False
    forbid_target_authority: bool = True

    def to_binding_dict(self) -> dict[str, Any]:
        return {
            "construct_freeze_digest": self.construct_freeze_digest,
            "evidence_seal_digest": artifact_content_digest(self.evidence_seal.to_dict()),
            "evidence_availability_digest": artifact_content_digest(
                self.evidence_availability.to_dict()
            ),
            "adapter_profile_id": self.adapter_profile.profile_id,
            "adapter_implementation_digest": self.adapter_profile.adapter_implementation_digest,
            "legacy_format": self.legacy_format,
            "query_occurrence_reference": self.query_occurrence_reference.to_dict(),
            "observed_canonical_content_digest": self.observed_canonical_content_digest,
            "observed_physical_instance_id": self.observed_physical_instance_id,
            "observed_revision_or_asof_id": self.observed_revision_or_asof_id,
            "ambiguous_candidate_count": self.ambiguous_candidate_count,
            "resolver_implementation_id": RESOLVER_IMPLEMENTATION_ID,
        }


def compute_resolver_input_digest(resolver_input: ResolverInputV2) -> str:
    return hashlib.sha256(
        canonical_artifact_bytes(resolver_input.to_binding_dict())
    ).hexdigest()


def compute_resolver_output_digest(body: dict[str, Any]) -> str:
    return hashlib.sha256(canonical_artifact_bytes(body)).hexdigest()


def _bind_capability_from_profile(
    profile: EvidenceAdapterProfileV2,
    *,
    resolver_result: ResolverResultV2,
) -> CapabilityVectorV2:
    """Derive capability from profile facts — never optimistically promote UNKNOWN."""

    vector = profile.capability_vector
    if resolver_result == ResolverResultV2.EXACT_MATCH:
        return vector
    if resolver_result == ResolverResultV2.SUMMARY_ONLY:
        return vector.with_overrides(
            evidence_completeness=EvidenceCompletenessCapability.PARTIAL_KNOWN.value
        )
    if resolver_result in {
        ResolverResultV2.EVIDENCE_UNAVAILABLE,
        ResolverResultV2.NO_MATCH,
        ResolverResultV2.ERROR,
    }:
        overrides: dict[str, str] = {}
        if vector.evidence_completeness == EvidenceCompletenessCapability.UNKNOWN:
            overrides["evidence_completeness"] = EvidenceCompletenessCapability.UNKNOWN.value
        if vector.occurrence_identity == OccurrenceIdentityCapability.ABSENT:
            overrides["occurrence_identity"] = OccurrenceIdentityCapability.ABSENT.value
        return vector.with_overrides(**overrides) if overrides else vector
    return vector


def _validate_p1_bindings(resolver_input: ResolverInputV2) -> str | None:
    seal_body = resolver_input.evidence_seal.to_dict()
    avail_body = resolver_input.evidence_availability.to_dict()
    reject_p2_fields_on_p1(seal_body, label="EvidenceSealManifestV2")
    reject_p2_fields_on_p1(avail_body, label="EvidenceAvailabilityManifestV2")

    seal_digest = artifact_content_digest(seal_body)
    if resolver_input.evidence_availability.evidence_seal_digest != seal_digest:
        return ResolutionDetailV2.INPUT_MUTATION.value

    if not resolver_input.evidence_availability.occurrence_reference.same_occurrence_as(
        resolver_input.evidence_seal.occurrence_reference
    ):
        return ResolutionDetailV2.INPUT_MUTATION.value

    if resolver_input.allow_hash_locator_fallback:
        return ResolutionDetailV2.LOCATOR_HASH_FALLBACK_REJECTED.value

    try:
        reject_hash_or_locator_identity(resolver_input.query_occurrence_reference.to_dict())
    except StructuralContractError:
        return ResolutionDetailV2.LOCATOR_HASH_FALLBACK_REJECTED.value

    if resolver_input.forbid_target_authority:
        binding = resolver_input.to_binding_dict()
        for forbidden in RESOLVER_FORBIDDEN_OUTPUT_FIELDS:
            if forbidden in binding:
                return ResolutionDetailV2.TARGET_AUTHORITY_FORBIDDEN.value

    return None


def _resolve_result_from_availability(
    availability: EvidenceAvailabilityManifestV2,
    *,
    query_matches: bool,
) -> ResolverResultV2:
    avail = availability.availability
    normalized_reported_presence(avail)
    if not query_matches:
        return ResolverResultV2.NO_MATCH
    if avail.source_presence == SourcePresenceV2.ABSENT:
        return ResolverResultV2.NO_MATCH
    if avail.verbatim_evidence_availability == VerbatimEvidenceAvailabilityV2.AVAILABLE:
        return ResolverResultV2.EXACT_MATCH
    if avail.summary_evidence_availability == SummaryEvidenceAvailabilityV2.AVAILABLE:
        return ResolverResultV2.SUMMARY_ONLY
    if avail.source_presence == SourcePresenceV2.PRESENT:
        return ResolverResultV2.EVIDENCE_UNAVAILABLE
    return ResolverResultV2.EVIDENCE_UNAVAILABLE


def resolve_opaque(
    resolver_input: ResolverInputV2,
    *,
    header: ArtifactHeaderV1 | None = None,
) -> OpaqueResolverManifestV2:
    """Compute-once read-only resolution over sealed P1 packages."""

    detail_error = _validate_p1_bindings(resolver_input)
    seal_digest = artifact_content_digest(resolver_input.evidence_seal.to_dict())
    preserved_presence = normalized_reported_presence(
        resolver_input.evidence_availability.availability
    )

    if detail_error is not None:
        return _error_manifest(
            resolver_input,
            seal_digest=seal_digest,
            preserved_presence=preserved_presence,
            detail=ResolutionDetailV2(detail_error),
            header=header,
        )

    profile = resolver_input.adapter_profile
    if profile.profile_id == "v2/evidence/unsupported":
        return _error_manifest(
            resolver_input,
            seal_digest=seal_digest,
            preserved_presence=preserved_presence,
            detail=ResolutionDetailV2.UNSUPPORTED_SOURCE_PROFILE,
            header=header,
        )

    if resolver_input.ambiguous_candidate_count > 1:
        return _error_manifest(
            resolver_input,
            seal_digest=seal_digest,
            preserved_presence=preserved_presence,
            detail=ResolutionDetailV2.AMBIGUOUS_MATCH,
            header=header,
        )

    if (
        resolver_input.observed_physical_instance_id is not None
        and resolver_input.observed_physical_instance_id
        != resolver_input.evidence_seal.physical_instance_id
    ):
        return _error_manifest(
            resolver_input,
            seal_digest=seal_digest,
            preserved_presence=preserved_presence,
            detail=ResolutionDetailV2.WRONG_SOURCE_INSTANCE,
            header=header,
        )

    if (
        resolver_input.observed_revision_or_asof_id is not None
        and resolver_input.observed_revision_or_asof_id
        != resolver_input.evidence_seal.revision_or_asof_id
    ):
        return _error_manifest(
            resolver_input,
            seal_digest=seal_digest,
            preserved_presence=preserved_presence,
            detail=ResolutionDetailV2.WRONG_REVISION_ASOF,
            header=header,
        )

    if (
        resolver_input.observed_canonical_content_digest is not None
        and resolver_input.observed_canonical_content_digest
        != resolver_input.evidence_seal.canonical_content_digest
    ):
        return _error_manifest(
            resolver_input,
            seal_digest=seal_digest,
            preserved_presence=preserved_presence,
            detail=ResolutionDetailV2.HASH_MISMATCH,
            header=header,
        )

    query_matches = resolver_input.query_occurrence_reference.same_occurrence_as(
        resolver_input.evidence_seal.occurrence_reference
    )
    resolver_result = _resolve_result_from_availability(
        resolver_input.evidence_availability,
        query_matches=query_matches,
    )
    capability_vector = _bind_capability_from_profile(
        profile, resolver_result=resolver_result
    )

    return _build_manifest(
        resolver_input,
        seal_digest=seal_digest,
        resolver_result=resolver_result,
        capability_vector=capability_vector,
        preserved_presence=preserved_presence,
        resolution_detail=None,
        header=header,
    )


def verify_opaque_resolver_manifest(
    manifest: OpaqueResolverManifestV2,
    *,
    resolver_input: ResolverInputV2,
    expected_implementation_digest: str | None = None,
) -> None:
    """Verify output binding against input tuple and digests."""

    impl_digest = expected_implementation_digest or resolver_implementation_digest()
    if manifest.resolver_implementation_digest != impl_digest:
        raise StructuralContractError("resolver implementation digest mismatch")
    expected_input = compute_resolver_input_digest(resolver_input)
    if manifest.resolver_input_digest != expected_input:
        raise StructuralContractError("resolver input digest mismatch")
    expected_output = compute_resolver_output_digest(manifest.authority_body_for_digest())
    if manifest.resolver_output_digest != expected_output:
        raise StructuralContractError("resolver output digest mismatch")
    seal_digest = artifact_content_digest(resolver_input.evidence_seal.to_dict())
    if manifest.evidence_seal_digest != seal_digest:
        raise StructuralContractError("evidence seal digest mismatch")


def _error_manifest(
    resolver_input: ResolverInputV2,
    *,
    seal_digest: str,
    preserved_presence: SourcePresenceV2,
    detail: ResolutionDetailV2,
    header: ArtifactHeaderV1 | None,
) -> OpaqueResolverManifestV2:
    capability_vector = _bind_capability_from_profile(
        resolver_input.adapter_profile,
        resolver_result=ResolverResultV2.ERROR,
    )
    return _build_manifest(
        resolver_input,
        seal_digest=seal_digest,
        resolver_result=ResolverResultV2.ERROR,
        capability_vector=capability_vector,
        preserved_presence=preserved_presence,
        resolution_detail=detail,
        header=header,
    )


def _build_manifest(
    resolver_input: ResolverInputV2,
    *,
    seal_digest: str,
    resolver_result: ResolverResultV2,
    capability_vector: CapabilityVectorV2,
    preserved_presence: SourcePresenceV2,
    resolution_detail: ResolutionDetailV2 | None,
    header: ArtifactHeaderV1 | None,
) -> OpaqueResolverManifestV2:
    input_digest = compute_resolver_input_digest(resolver_input)
    impl_digest = resolver_implementation_digest()
    body = {
        "evidence_seal_digest": seal_digest,
        "resolver_implementation_digest": impl_digest,
        "resolver_input_digest": input_digest,
        "resolver_result": resolver_result.value,
        "capability_vector": capability_vector.to_dict(),
        "preserved_source_presence": preserved_presence.value,
        "resolution_detail": resolution_detail.value if resolution_detail else None,
    }
    output_digest = compute_resolver_output_digest(body)
    manifest_header = header or ArtifactHeaderV1(
        artifact_id="nps2_resolver_pending",
        schema_version=OpaqueResolverManifestV2.SCHEMA,
        parent_artifact_id=None,
        parent_digest=None,
        created_at="2026-08-31T00:00:00Z",
        seal_time="2026-08-31T00:00:01Z",
        responsible_role="opaque_resolver",
        content_digest=output_digest,
        sealed=True,
    )
    return OpaqueResolverManifestV2(
        header=manifest_header,
        evidence_seal_digest=seal_digest,
        resolver_implementation_digest=impl_digest,
        resolver_input_digest=input_digest,
        resolver_result=resolver_result,
        capability_vector=capability_vector,
        resolver_output_digest=output_digest,
        preserved_source_presence=preserved_presence,
        resolution_detail=resolution_detail,
    )

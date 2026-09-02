"""PRE-G6 Naturalistic V2 runtime types — separate namespace from V1."""

from eval_naturalistic.v2.authority_issuance import (
    EvidenceSealManifestDraftV2,
    ImmediateParentBindingV2,
    IssuanceAuthorityRecordV2,
    IssuanceAuthorityRepository,
    IssuedOccurrenceReferenceV2,
    SealedP1AuthorityV2,
    issue_occurrence_reference,
    verify_sealed_p1_authority,
)
from eval_naturalistic.v2.authority_substrate import IndependentAuthoritySourceV2
from eval_naturalistic.v2.contracts import (
    EvidenceAvailabilityManifestV2,
    EvidenceSealManifestV2,
)
from eval_naturalistic.v2.evidence import ConditionNeutralEvidenceAvailabilityV2
from eval_naturalistic.v2.identity import OccurrenceReferenceV2
from eval_naturalistic.v2.capture_attestation import CaptureAttestationRepository
from eval_naturalistic.v2.capture_attestation_issuance import issue_capture_attestation
from eval_naturalistic.v2.issuer_attestation_capability import (
    IssuerCaptureAttestationCapabilityRepository,
    build_issuer_capture_attestation_capability_record,
)
from eval_naturalistic.v2.lineage_attestation import LineageAttestationRepository
from eval_naturalistic.v2.p0_construct import InMemoryConstructFreezeRepository
from eval_naturalistic.v2.source_authority import (
    SealedSourceCapturePackageV2,
    VerifiedSourceAuthorityV2,
    seal_source_capture_package,
    verify_source_capture_authority,
)
from eval_naturalistic.v2.source_issuer_authority import (
    SourceIssuerGrantRepository,
    build_source_issuer_grant_record,
)
from eval_naturalistic.v2.adapters.capability_manifest import (
    CAPABILITY_MANIFEST_SCHEMA,
    CapabilityManifestV2,
    OccurrenceCapabilityManifestV2,
    SealedCapabilityManifestV2,
    SealedOccurrenceCapabilityV2,
    derive_capability_for_occurrence,
    derive_capability_manifest,
    parse_capability_manifest_v2,
    verify_capability_manifest,
)
from eval_naturalistic.v2.resolver import (
    RESOLVER_IMPLEMENTATION_ID,
    RESOLVER_MANIFEST_SCHEMA,
    OpaqueResolverManifestV2,
    OpaqueResolverResultV2,
    ResolverInputV2,
    ResolverOutputV2,
    ResolverResultV2,
    SealedOpaqueResolverManifestV2,
    SealedResolverManifestV2,
    compute_resolver_implementation_digest,
    derive_opaque_resolver_manifest,
    parse_opaque_resolver_manifest_v2,
    parse_resolver_manifest_v2,
    resolve_opaque_occurrence,
    resolve_opaque_resolver,
    trusted_resolver_implementation_identity,
    verify_opaque_resolver_manifest,
    verify_resolver_manifest,
)

__all__ = [
    "CaptureAttestationRepository",
    "CAPABILITY_MANIFEST_SCHEMA",
    "IssuerCaptureAttestationCapabilityRepository",
    "build_issuer_capture_attestation_capability_record",
    "issue_capture_attestation",
    "build_source_issuer_grant_record",
    "ConditionNeutralEvidenceAvailabilityV2",
    "CapabilityManifestV2",
    "EvidenceAvailabilityManifestV2",
    "EvidenceSealManifestDraftV2",
    "EvidenceSealManifestV2",
    "ImmediateParentBindingV2",
    "IndependentAuthoritySourceV2",
    "InMemoryConstructFreezeRepository",
    "IssuanceAuthorityRecordV2",
    "IssuanceAuthorityRepository",
    "IssuedOccurrenceReferenceV2",
    "LineageAttestationRepository",
    "OccurrenceReferenceV2",
    "OccurrenceCapabilityManifestV2",
    "SourceIssuerGrantRepository",
    "SealedP1AuthorityV2",
    "SealedSourceCapturePackageV2",
    "SealedCapabilityManifestV2",
    "SealedOccurrenceCapabilityV2",
    "VerifiedSourceAuthorityV2",
    "issue_occurrence_reference",
    "seal_source_capture_package",
    "verify_sealed_p1_authority",
    "verify_source_capture_authority",
    "derive_capability_for_occurrence",
    "derive_capability_manifest",
    "parse_capability_manifest_v2",
    "verify_capability_manifest",
    "RESOLVER_IMPLEMENTATION_ID",
    "RESOLVER_MANIFEST_SCHEMA",
    "OpaqueResolverManifestV2",
    "OpaqueResolverResultV2",
    "ResolverInputV2",
    "ResolverOutputV2",
    "ResolverResultV2",
    "SealedOpaqueResolverManifestV2",
    "SealedResolverManifestV2",
    "compute_resolver_implementation_digest",
    "derive_opaque_resolver_manifest",
    "parse_opaque_resolver_manifest_v2",
    "parse_resolver_manifest_v2",
    "resolve_opaque_occurrence",
    "resolve_opaque_resolver",
    "trusted_resolver_implementation_identity",
    "verify_opaque_resolver_manifest",
    "verify_resolver_manifest",
]

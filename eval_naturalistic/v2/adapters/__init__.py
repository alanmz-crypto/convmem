"""V2 evidence adapter profiles and capability vectors."""

from eval_naturalistic.v2.adapters.capability import (
    CAPABILITY_DIMENSIONS,
    CapabilityVectorV2,
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
from eval_naturalistic.v2.adapters.profile import (
    EvidenceAdapterProfileV2,
    NativeRecordIdentityMode,
    bind_profile_identity,
    profile_content_digest,
)
from eval_naturalistic.v2.adapters.reduction import CapabilityDecisionV2, CapabilityUseV2
from eval_naturalistic.v2.adapters.registry import profile_for_legacy_format, resolve_profile_or_fail

__all__ = [
    "CAPABILITY_DIMENSIONS",
    "CAPABILITY_MANIFEST_SCHEMA",
    "CapabilityDecisionV2",
    "CapabilityUseV2",
    "CapabilityVectorV2",
    "CapabilityManifestV2",
    "EvidenceAdapterProfileV2",
    "NativeRecordIdentityMode",
    "OccurrenceCapabilityManifestV2",
    "SealedCapabilityManifestV2",
    "SealedOccurrenceCapabilityV2",
    "derive_capability_for_occurrence",
    "derive_capability_manifest",
    "parse_capability_manifest_v2",
    "bind_profile_identity",
    "profile_content_digest",
    "profile_for_legacy_format",
    "resolve_profile_or_fail",
    "verify_capability_manifest",
]

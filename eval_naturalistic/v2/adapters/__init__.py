"""V2 evidence adapter profiles and capability vectors."""

from eval_naturalistic.v2.adapters.capability import (
    CAPABILITY_DIMENSIONS,
    CapabilityVectorV2,
)
from eval_naturalistic.v2.adapters.profile import (
    EvidenceAdapterProfileV2,
    NativeRecordIdentityMode,
)
from eval_naturalistic.v2.adapters.reduction import CapabilityDecisionV2, CapabilityUseV2
from eval_naturalistic.v2.adapters.registry import profile_for_legacy_format, resolve_profile_or_fail

__all__ = [
    "CAPABILITY_DIMENSIONS",
    "CapabilityDecisionV2",
    "CapabilityUseV2",
    "CapabilityVectorV2",
    "EvidenceAdapterProfileV2",
    "NativeRecordIdentityMode",
    "profile_for_legacy_format",
    "resolve_profile_or_fail",
]

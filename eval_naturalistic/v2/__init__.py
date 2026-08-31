"""PRE-G6 Naturalistic V2 runtime types — separate namespace from V1."""

from eval_naturalistic.v2.contracts import (
    EvidenceAvailabilityManifestV2,
    EvidenceSealManifestV2,
)
from eval_naturalistic.v2.evidence import ConditionNeutralEvidenceAvailabilityV2
from eval_naturalistic.v2.firewall import reject_p2_fields_on_p1
from eval_naturalistic.v2.identity import OccurrenceReferenceV2
from eval_naturalistic.v2.resolver import ResolverInputV2, resolve_opaque
from eval_naturalistic.v2.resolver_contracts import OpaqueResolverManifestV2, ResolverResultV2

__all__ = [
    "ConditionNeutralEvidenceAvailabilityV2",
    "EvidenceAvailabilityManifestV2",
    "EvidenceSealManifestV2",
    "OccurrenceReferenceV2",
    "OpaqueResolverManifestV2",
    "ResolverInputV2",
    "ResolverResultV2",
    "reject_p2_fields_on_p1",
    "resolve_opaque",
]

"""Locked nine-axis capability vector for Naturalistic V2 evidence adapters.

The nine explicit dimensions are intentionally represented as one value object;
the instance-attribute count is the contract, not accidental state.
"""

# pylint: disable=too-many-instance-attributes

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

from eval_naturalistic.base import (
    StructuralContractError,
    _enum_from_value,
    _require_dict,
    _require_no_unknown_props,
)

CAPABILITY_DIMENSIONS = (
    "occurrence_identity",
    "source_instance_binding",
    "revision_asof_binding",
    "evidence_completeness",
    "canonical_verification",
    "temporal_reproducibility",
    "attachment_material_span_completeness",
    "preservation_replay_capability",
    "lineage_assurance",
)


class OccurrenceIdentityCapability(str, Enum):
    NATIVE_UNIQUE = "NATIVE_UNIQUE"
    ISSUER_ATTESTED = "ISSUER_ATTESTED"
    DERIVED = "DERIVED"
    ABSENT = "ABSENT"


class SourceInstanceBindingCapability(str, Enum):
    ATTESTED = "ATTESTED"
    DECLARED = "DECLARED"
    ABSENT = "ABSENT"


class RevisionAsofBindingCapability(str, Enum):
    REVISION_PINNED = "REVISION_PINNED"
    ASOF_PINNED = "ASOF_PINNED"
    CURRENT_ONLY = "CURRENT_ONLY"
    UNKNOWN = "UNKNOWN"


class EvidenceCompletenessCapability(str, Enum):
    COMPLETE = "COMPLETE"
    PARTIAL_KNOWN = "PARTIAL_KNOWN"
    UNKNOWN = "UNKNOWN"
    MISSING = "MISSING"


class CanonicalVerificationCapability(str, Enum):
    VERIFIED = "VERIFIED"
    UNVERIFIED = "UNVERIFIED"
    MISMATCH = "MISMATCH"


class TemporalReproducibilityCapability(str, Enum):
    REPLAYABLE = "REPLAYABLE"
    CAPTURE_ATTESTED = "CAPTURE_ATTESTED"
    MUTABLE = "MUTABLE"
    UNKNOWN = "UNKNOWN"


class AttachmentMaterialSpanCapability(str, Enum):
    COMPLETE = "COMPLETE"
    PARTIAL_KNOWN = "PARTIAL_KNOWN"
    UNKNOWN = "UNKNOWN"
    MISSING = "MISSING"


class PreservationReplayCapability(str, Enum):
    SEALED_REPLAYABLE = "SEALED_REPLAYABLE"
    SEALED_NONREPLAYABLE = "SEALED_NONREPLAYABLE"
    UNSEALED = "UNSEALED"
    ABSENT = "ABSENT"


class LineageAssuranceCapability(str, Enum):
    IMMUTABLE_ATTESTED = "IMMUTABLE_ATTESTED"
    DECLARED = "DECLARED"
    UNKNOWN = "UNKNOWN"
    ABSENT = "ABSENT"


@dataclass(frozen=True)
class CapabilityVectorV2:
    """Exact locked capability-vector dimensions — no scalar assurance authority."""

    occurrence_identity: OccurrenceIdentityCapability
    source_instance_binding: SourceInstanceBindingCapability
    revision_asof_binding: RevisionAsofBindingCapability
    evidence_completeness: EvidenceCompletenessCapability
    canonical_verification: CanonicalVerificationCapability
    temporal_reproducibility: TemporalReproducibilityCapability
    attachment_material_span_completeness: AttachmentMaterialSpanCapability
    preservation_replay_capability: PreservationReplayCapability
    lineage_assurance: LineageAssuranceCapability

    _FIELDS = frozenset(CAPABILITY_DIMENSIONS)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CapabilityVectorV2":
        data = _require_dict(data, "CapabilityVectorV2")
        _require_no_unknown_props(data, cls._FIELDS, "CapabilityVectorV2")
        missing = sorted(cls._FIELDS - set(data))
        if missing:
            raise StructuralContractError(
                "CapabilityVectorV2: missing required property(s): " + ", ".join(missing)
            )
        return cls(
            occurrence_identity=_enum_from_value(
                OccurrenceIdentityCapability,
                data["occurrence_identity"],
                "occurrence_identity",
            ),
            source_instance_binding=_enum_from_value(
                SourceInstanceBindingCapability,
                data["source_instance_binding"],
                "source_instance_binding",
            ),
            revision_asof_binding=_enum_from_value(
                RevisionAsofBindingCapability,
                data["revision_asof_binding"],
                "revision_asof_binding",
            ),
            evidence_completeness=_enum_from_value(
                EvidenceCompletenessCapability,
                data["evidence_completeness"],
                "evidence_completeness",
            ),
            canonical_verification=_enum_from_value(
                CanonicalVerificationCapability,
                data["canonical_verification"],
                "canonical_verification",
            ),
            temporal_reproducibility=_enum_from_value(
                TemporalReproducibilityCapability,
                data["temporal_reproducibility"],
                "temporal_reproducibility",
            ),
            attachment_material_span_completeness=_enum_from_value(
                AttachmentMaterialSpanCapability,
                data["attachment_material_span_completeness"],
                "attachment_material_span_completeness",
            ),
            preservation_replay_capability=_enum_from_value(
                PreservationReplayCapability,
                data["preservation_replay_capability"],
                "preservation_replay_capability",
            ),
            lineage_assurance=_enum_from_value(
                LineageAssuranceCapability,
                data["lineage_assurance"],
                "lineage_assurance",
            ),
        )

    def to_dict(self) -> dict[str, str]:
        return {
            "occurrence_identity": self.occurrence_identity.value,
            "source_instance_binding": self.source_instance_binding.value,
            "revision_asof_binding": self.revision_asof_binding.value,
            "evidence_completeness": self.evidence_completeness.value,
            "canonical_verification": self.canonical_verification.value,
            "temporal_reproducibility": self.temporal_reproducibility.value,
            "attachment_material_span_completeness": (
                self.attachment_material_span_completeness.value
            ),
            "preservation_replay_capability": self.preservation_replay_capability.value,
            "lineage_assurance": self.lineage_assurance.value,
        }

    def with_overrides(self, **overrides: Any) -> "CapabilityVectorV2":
        current = self.to_dict()
        current.update(overrides)
        return CapabilityVectorV2.from_dict(current)

    def derived_human_ceiling(self) -> str:
        """Display-only recomputation — not normative authority."""

        if self.occurrence_identity == OccurrenceIdentityCapability.ABSENT:
            return "unsupported"
        if self.evidence_completeness == EvidenceCompletenessCapability.MISSING:
            return "missing"
        if self.canonical_verification == CanonicalVerificationCapability.MISMATCH:
            return "mismatch"
        if self.evidence_completeness == EvidenceCompletenessCapability.PARTIAL_KNOWN:
            return "partial_known"
        if any(
            value.value.endswith("UNKNOWN")
            for value in (
                self.revision_asof_binding,
                self.temporal_reproducibility,
                self.attachment_material_span_completeness,
                self.lineage_assurance,
                self.evidence_completeness,
            )
        ):
            return "unknown_ceiling"
        return "vector_defined"

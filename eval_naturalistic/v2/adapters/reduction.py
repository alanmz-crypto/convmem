"""Deterministic per-use capability reduction — derived from vector, not stored."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from eval_naturalistic.v2.adapters.capability import (
    AttachmentMaterialSpanCapability,
    CanonicalVerificationCapability,
    CapabilityVectorV2,
    EvidenceCompletenessCapability,
    OccurrenceIdentityCapability,
    PreservationReplayCapability,
    SourceInstanceBindingCapability,
    TemporalReproducibilityCapability,
)


class CapabilityUseV2(str, Enum):
    DISCOVERY_ELIGIBILITY = "DISCOVERY_ELIGIBILITY"
    ADJUDICATION = "ADJUDICATION"
    PRIMARY_SCORING = "PRIMARY_SCORING"
    SECONDARY_DIAGNOSTIC = "SECONDARY_DIAGNOSTIC"
    REPLAY_AUDIT = "REPLAY_AUDIT"


@dataclass(frozen=True)
class CapabilityDecisionV2:
    use: CapabilityUseV2
    allowed: bool
    failure_reasons: tuple[str, ...]
    degradation: str | None = None


def evaluate_capability_for_use(
    vector: CapabilityVectorV2,
    use: CapabilityUseV2,
    *,
    assurance_decision_selected: bool = False,
    target_material_span_policy_passes: bool = True,
) -> CapabilityDecisionV2:
    """Apply locked per_use_acceptance predicates deterministically."""

    failures: list[str] = []
    degradation: str | None = None

    if use == CapabilityUseV2.DISCOVERY_ELIGIBILITY:
        if vector.occurrence_identity == OccurrenceIdentityCapability.ABSENT:
            failures.append("occurrence_identity==ABSENT")
        if vector.evidence_completeness == EvidenceCompletenessCapability.MISSING:
            failures.append("evidence_completeness==MISSING")
        if vector.canonical_verification == CanonicalVerificationCapability.MISMATCH:
            failures.append("canonical_verification==MISMATCH")
        if vector.evidence_completeness in {
            EvidenceCompletenessCapability.PARTIAL_KNOWN,
            EvidenceCompletenessCapability.UNKNOWN,
        }:
            degradation = "partial_or_unknown_completeness_sets_multiplicity_unknown"

    elif use == CapabilityUseV2.ADJUDICATION:
        if vector.occurrence_identity == OccurrenceIdentityCapability.ABSENT:
            failures.append("occurrence_identity==ABSENT")
        if vector.source_instance_binding == SourceInstanceBindingCapability.ABSENT:
            failures.append("source_instance_binding==ABSENT")
        if vector.evidence_completeness not in {
            EvidenceCompletenessCapability.COMPLETE,
            EvidenceCompletenessCapability.PARTIAL_KNOWN,
        }:
            failures.append("evidence_completeness not in [COMPLETE,PARTIAL_KNOWN]")
        if vector.canonical_verification == CanonicalVerificationCapability.MISMATCH:
            failures.append("canonical_verification==MISMATCH")
        if vector.evidence_completeness == EvidenceCompletenessCapability.PARTIAL_KNOWN:
            degradation = "target_specific_material_gap_sets_non_evaluable"

    elif use == CapabilityUseV2.PRIMARY_SCORING:
        if not assurance_decision_selected:
            failures.append("decision:D_ASSURANCE_001 unselected")
        if vector.canonical_verification != CanonicalVerificationCapability.VERIFIED:
            failures.append("canonical_verification!=VERIFIED")
        if vector.preservation_replay_capability not in {
            PreservationReplayCapability.SEALED_REPLAYABLE,
            PreservationReplayCapability.SEALED_NONREPLAYABLE,
        }:
            failures.append(
                "preservation_replay_capability not in [SEALED_REPLAYABLE,SEALED_NONREPLAYABLE]"
            )
        if not target_material_span_policy_passes:
            failures.append("target_material_span_policy_passes==false")
        degradation = "blocked_or_non_evaluable"

    elif use == CapabilityUseV2.SECONDARY_DIAGNOSTIC:
        if vector.occurrence_identity == OccurrenceIdentityCapability.ABSENT:
            failures.append("occurrence_identity==ABSENT")
        if vector.canonical_verification == CanonicalVerificationCapability.MISMATCH:
            failures.append("canonical_verification==MISMATCH")
        degradation = "label_lower_assurance"

    elif use == CapabilityUseV2.REPLAY_AUDIT:
        if vector.preservation_replay_capability != PreservationReplayCapability.SEALED_REPLAYABLE:
            failures.append("preservation_replay_capability!=SEALED_REPLAYABLE")
        if vector.temporal_reproducibility != TemporalReproducibilityCapability.REPLAYABLE:
            failures.append("temporal_reproducibility!=REPLAYABLE")
        if vector.canonical_verification != CanonicalVerificationCapability.VERIFIED:
            failures.append("canonical_verification!=VERIFIED")
        degradation = "audit_only_without_replay_claim"

    else:
        failures.append(f"unknown capability use '{use.value}'")

    return CapabilityDecisionV2(
        use=use,
        allowed=not failures,
        failure_reasons=tuple(failures),
        degradation=degradation if failures or degradation else None,
    )


def evaluate_all_uses(
    vector: CapabilityVectorV2,
    *,
    assurance_decision_selected: bool = False,
    target_material_span_policy_passes: bool = True,
) -> dict[CapabilityUseV2, CapabilityDecisionV2]:
    return {
        use: evaluate_capability_for_use(
            vector,
            use,
            assurance_decision_selected=assurance_decision_selected,
            target_material_span_policy_passes=target_material_span_policy_passes,
        )
        for use in CapabilityUseV2
    }

"""Explicit fail-closed unsupported evidence adapter profile."""

from __future__ import annotations

from eval_naturalistic.v2.adapters.capability import (
    AttachmentMaterialSpanCapability,
    CanonicalVerificationCapability,
    CapabilityVectorV2,
    EvidenceCompletenessCapability,
    LineageAssuranceCapability,
    OccurrenceIdentityCapability,
    PreservationReplayCapability,
    RevisionAsofBindingCapability,
    SourceInstanceBindingCapability,
    TemporalReproducibilityCapability,
)
from eval_naturalistic.v2.adapters.profile import (
    EvidenceAdapterProfileV2,
    NativeRecordIdentityMode,
    ProfileSemanticsV2,
    profile_implementation_digest,
)
from eval_naturalistic.v2.evidence import (
    ConditionNeutralEvidenceAvailabilityV2,
    SourcePresenceV2,
    SummaryEvidenceAvailabilityV2,
    VerbatimEvidenceAvailabilityV2,
)

PROFILE_ID = "v2/evidence/unsupported"


def unsupported_profile(
    *,
    reason: str,
    source_present: bool = True,
) -> EvidenceAdapterProfileV2:
    """Unsupported capability — not source absence."""

    vector = CapabilityVectorV2(
        occurrence_identity=OccurrenceIdentityCapability.ABSENT,
        source_instance_binding=SourceInstanceBindingCapability.ABSENT,
        revision_asof_binding=RevisionAsofBindingCapability.UNKNOWN,
        evidence_completeness=EvidenceCompletenessCapability.UNKNOWN,
        canonical_verification=CanonicalVerificationCapability.UNVERIFIED,
        temporal_reproducibility=TemporalReproducibilityCapability.UNKNOWN,
        attachment_material_span_completeness=AttachmentMaterialSpanCapability.UNKNOWN,
        preservation_replay_capability=PreservationReplayCapability.ABSENT,
        lineage_assurance=LineageAssuranceCapability.ABSENT,
    )
    presence = SourcePresenceV2.PRESENT if source_present else SourcePresenceV2.UNKNOWN
    profile = EvidenceAdapterProfileV2(
        profile_id=PROFILE_ID,
        legacy_format=None,
        adapter_implementation_digest=profile_implementation_digest(PROFILE_ID),
        capability_vector=vector,
        native_record_identity_mode=NativeRecordIdentityMode.UNSUPPORTED,
        semantics=ProfileSemanticsV2(
            acceptance_rejection=f"Unsupported profile: {reason}",
            ordering="Unsupported — no ordering authority.",
            duplicate_handling="Unsupported — fail closed.",
            authorship="Unsupported — no authorship authority.",
            chronology_timezone="Unsupported — chronology unknown.",
            reply_structure="Unsupported — no thread authority.",
            validity_currentness="Unsupported — validity unknown.",
            unknown_extension_fields="Unsupported — extension handling unknown.",
            attachments_blobs="Unsupported — attachment handling unknown.",
            tool_referenced_material="Unsupported — tool material unknown.",
            omissions_truncation=f"All evidence semantics unsupported: {reason}",
            canonicalization_profile="No canonicalization profile — unsupported.",
            source_instance_binding="No source-instance binding authority.",
            native_record_identity="No native or derived record identity authority.",
            revision_asof="No revision/as-of authority.",
            raw_envelope_recovery="No raw envelope recovery.",
            replay_asof="No replay/as-of authority.",
        ),
        declared_omissions=("unsupported_profile",),
        default_availability=ConditionNeutralEvidenceAvailabilityV2(
            source_presence=presence,
            verbatim_evidence_availability=VerbatimEvidenceAvailabilityV2.UNAVAILABLE,
            summary_evidence_availability=SummaryEvidenceAvailabilityV2.UNAVAILABLE,
        ),
        schema_version=None,
    )
    profile.validate()
    return profile

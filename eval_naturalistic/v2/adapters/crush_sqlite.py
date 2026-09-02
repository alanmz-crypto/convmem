"""Crush SQLite evidence adapter profile."""

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
    bind_profile_identity,
    profile_implementation_digest,
)
from eval_naturalistic.v2.evidence import (
    ConditionNeutralEvidenceAvailabilityV2,
    SourcePresenceV2,
    SummaryEvidenceAvailabilityV2,
    VerbatimEvidenceAvailabilityV2,
)

PROFILE_ID = "v2/evidence/crush-sqlite"
LEGACY_FORMAT = "sqlite_crush"


def _base_semantics(*, omissions: str) -> ProfileSemanticsV2:
    return ProfileSemanticsV2(
        acceptance_rejection=(
            "Accept user/assistant messages with JSON parts arrays; reject malformed rows."
        ),
        ordering="Preserve messages.created_at ascending within session_id.",
        duplicate_handling="Distinct message row IDs; duplicates surfaced explicitly, not merged.",
        authorship="Role from messages.role; model/provider retained when present.",
        chronology_timezone="Unix-ms timestamps converted to UTC ISO-8601 at capture.",
        reply_structure="Session-scoped linear thread; no cross-session parent linkage in legacy parse.",
        validity_currentness="Capture-time as-of; deletion/reuse/migration limitations remain unknown.",
        unknown_extension_fields="Non-text part types declared omitted unless raw envelope captured.",
        attachments_blobs="Attachment parts not preserved in legacy parse output.",
        tool_referenced_material="Reasoning/finish/tool parts omitted from legacy canonical text.",
        omissions_truncation=omissions,
        canonicalization_profile="Legacy sqlite_chat canonical message dict; V2 profile is separate.",
        source_instance_binding="DB file path + schema fingerprint declare local source instance.",
        native_record_identity=(
            "messages.id namespace crush.message when present; not upgraded to NATIVE_UNIQUE."
        ),
        revision_asof="Row updated_at/created_at provide capture as-of; reuse after delete unknown.",
        raw_envelope_recovery="Full raw parts JSON required for evidence envelope; legacy parse is lossy.",
        replay_asof="Replay requires sealed raw envelope; legacy parse alone is non-replayable.",
    )


def crush_sqlite_profile(*, truncated: bool = False) -> EvidenceAdapterProfileV2:
    completeness = (
        EvidenceCompletenessCapability.PARTIAL_KNOWN
        if truncated
        else EvidenceCompletenessCapability.PARTIAL_KNOWN
    )
    omissions = (
        "Legacy parse drops tool/reasoning/finish parts and attachment material."
        if not truncated
        else "Truncated capture omits tail messages and non-text parts."
    )
    vector = CapabilityVectorV2(
        occurrence_identity=OccurrenceIdentityCapability.ISSUER_ATTESTED,
        source_instance_binding=SourceInstanceBindingCapability.DECLARED,
        revision_asof_binding=RevisionAsofBindingCapability.ASOF_PINNED,
        evidence_completeness=completeness,
        canonical_verification=CanonicalVerificationCapability.UNVERIFIED,
        temporal_reproducibility=TemporalReproducibilityCapability.CAPTURE_ATTESTED,
        attachment_material_span_completeness=AttachmentMaterialSpanCapability.MISSING,
        preservation_replay_capability=PreservationReplayCapability.UNSEALED,
        lineage_assurance=LineageAssuranceCapability.UNKNOWN,
    )
    profile = EvidenceAdapterProfileV2(
        profile_id=PROFILE_ID,
        legacy_format=LEGACY_FORMAT,
        adapter_implementation_digest=profile_implementation_digest(PROFILE_ID),
        capability_vector=vector,
        native_record_identity_mode=NativeRecordIdentityMode.UNKNOWN,
        semantics=_base_semantics(omissions=omissions),
        declared_omissions=(
            "reasoning_parts",
            "finish_parts",
            "tool_parts",
            "attachment_blobs",
            "non_text_parts",
        ),
        default_availability=ConditionNeutralEvidenceAvailabilityV2(
            source_presence=SourcePresenceV2.PRESENT,
            verbatim_evidence_availability=VerbatimEvidenceAvailabilityV2.UNAVAILABLE,
            summary_evidence_availability=SummaryEvidenceAvailabilityV2.AVAILABLE,
        ),
        schema_version="crush.messages.parts.v1",
    )
    profile = bind_profile_identity(profile)
    profile.validate()
    return profile


def crush_sqlite_profile_missing_native_authority() -> EvidenceAdapterProfileV2:
    profile = crush_sqlite_profile()
    vector = profile.capability_vector.with_overrides(
        occurrence_identity=OccurrenceIdentityCapability.DERIVED.value
    )
    return profile.with_capability_vector(vector)

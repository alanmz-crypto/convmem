"""JSONL-like evidence adapter profiles (Cursor/Codex/Kiro/Copilot)."""

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

JSONL_FORMATS = frozenset(
    {
        "jsonl_cursor",
        "jsonl_codex_rollout",
        "jsonl_codex_history",
        "jsonl_kiro_session",
        "jsonl_copilot_session",
    }
)


def _jsonl_semantics(*, format_label: str, omissions: str) -> ProfileSemanticsV2:
    return ProfileSemanticsV2(
        acceptance_rejection=f"Accept user/assistant JSONL lines for {format_label}; skip non-chat records.",
        ordering="File line order is authoritative; must not be silently reordered.",
        duplicate_handling="Duplicate lines remain distinct occurrences unless explicit dedup policy declared.",
        authorship="Role from JSONL record when present.",
        chronology_timezone="Timestamp retained when present; otherwise explicitly null/unknown.",
        reply_structure="Linear file order; provider thread structure often absent in legacy parse.",
        validity_currentness="Snapshot/file-instance as-of capture only.",
        unknown_extension_fields="Non-text blocks and extension keys declared omitted unless raw line preserved.",
        attachments_blobs="Tool blocks and non-text content omitted from legacy parse.",
        tool_referenced_material="Tool/status events explicitly declared omitted when skipped.",
        omissions_truncation=omissions,
        canonicalization_profile="Legacy jsonl adapters extract text-only canonical dicts.",
        source_instance_binding="Snapshot-scoped file instance + byte/line occurrence binding.",
        native_record_identity="Derived snapshot-scoped occurrence; never provider-native without real event ID.",
        revision_asof="File revision digest or capture as-of; mutable file state declared CURRENT_ONLY.",
        raw_envelope_recovery="Requires raw JSONL line envelope; legacy parse is lossy.",
        replay_asof="Replay limited to sealed snapshot; live file mutation makes replay unknown.",
    )


def jsonl_derived_profile(
    legacy_format: str,
    *,
    truncated: bool = False,
) -> EvidenceAdapterProfileV2:
    if legacy_format not in JSONL_FORMATS:
        raise ValueError(f"unsupported JSONL legacy format '{legacy_format}'")
    omissions = (
        "Legacy parse drops tool-only turns, non-text blocks, and status records."
        if not truncated
        else "Truncated JSONL omits tail lines and tool-bearing events."
    )
    completeness = (
        EvidenceCompletenessCapability.PARTIAL_KNOWN
        if not truncated
        else EvidenceCompletenessCapability.PARTIAL_KNOWN
    )
    vector = CapabilityVectorV2(
        occurrence_identity=OccurrenceIdentityCapability.DERIVED,
        source_instance_binding=SourceInstanceBindingCapability.DECLARED,
        revision_asof_binding=RevisionAsofBindingCapability.CURRENT_ONLY,
        evidence_completeness=completeness,
        canonical_verification=CanonicalVerificationCapability.UNVERIFIED,
        temporal_reproducibility=TemporalReproducibilityCapability.MUTABLE,
        attachment_material_span_completeness=AttachmentMaterialSpanCapability.MISSING,
        preservation_replay_capability=PreservationReplayCapability.UNSEALED,
        lineage_assurance=LineageAssuranceCapability.ABSENT,
    )
    profile_id = f"v2/evidence/jsonl-derived/{legacy_format}"
    profile = EvidenceAdapterProfileV2(
        profile_id=profile_id,
        legacy_format=legacy_format,
        adapter_implementation_digest=profile_implementation_digest(profile_id),
        capability_vector=vector,
        native_record_identity_mode=NativeRecordIdentityMode.DERIVED,
        semantics=_jsonl_semantics(format_label=legacy_format, omissions=omissions),
        declared_omissions=(
            "tool_only_turns",
            "status_records",
            "non_text_blocks",
            "missing_timestamps",
        ),
        default_availability=ConditionNeutralEvidenceAvailabilityV2(
            source_presence=SourcePresenceV2.PRESENT,
            verbatim_evidence_availability=VerbatimEvidenceAvailabilityV2.UNAVAILABLE,
            summary_evidence_availability=SummaryEvidenceAvailabilityV2.AVAILABLE,
        ),
        schema_version=f"{legacy_format}.jsonl.v1",
    )
    profile.validate()
    return profile


def jsonl_derived_profile_invented_native() -> EvidenceAdapterProfileV2:
    """Adversarial fixture: synthesized ID must not upgrade capability."""

    profile = jsonl_derived_profile("jsonl_cursor")
    vector = profile.capability_vector.with_overrides(
        occurrence_identity=OccurrenceIdentityCapability.NATIVE_UNIQUE.value
    )
    return profile.with_capability_vector(vector)

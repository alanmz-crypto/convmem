"""Markdown-like evidence adapter profiles (Aider/inter-model)."""

# Profile constructors share the explicit schema by design.
# pylint: disable=duplicate-code

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

MARKDOWN_FORMATS = frozenset({"aider_markdown", "inter_model_doc", "kiro_steering"})


def markdown_derived_profile(
    legacy_format: str,
    *,
    truncated: bool = False,
) -> EvidenceAdapterProfileV2:
    if legacy_format not in MARKDOWN_FORMATS:
        raise ValueError(f"unsupported Markdown legacy format '{legacy_format}'")
    omissions = (
        "Parser-generated block positions; metadata lines and token summaries omitted."
        if not truncated
        else "Truncated Markdown omits steering sections and trailing blocks."
    )
    vector = CapabilityVectorV2(
        occurrence_identity=OccurrenceIdentityCapability.DERIVED,
        source_instance_binding=SourceInstanceBindingCapability.DECLARED,
        revision_asof_binding=RevisionAsofBindingCapability.ASOF_PINNED,
        evidence_completeness=(
            EvidenceCompletenessCapability.PARTIAL_KNOWN
            if truncated
            else EvidenceCompletenessCapability.PARTIAL_KNOWN
        ),
        canonical_verification=CanonicalVerificationCapability.UNVERIFIED,
        temporal_reproducibility=TemporalReproducibilityCapability.CAPTURE_ATTESTED,
        attachment_material_span_completeness=AttachmentMaterialSpanCapability.PARTIAL_KNOWN,
        preservation_replay_capability=PreservationReplayCapability.UNSEALED,
        lineage_assurance=LineageAssuranceCapability.UNKNOWN,
    )
    profile_id = f"v2/evidence/markdown-derived/{legacy_format}"
    profile = EvidenceAdapterProfileV2(
        profile_id=profile_id,
        legacy_format=legacy_format,
        adapter_implementation_digest=profile_implementation_digest(profile_id),
        capability_vector=vector,
        native_record_identity_mode=NativeRecordIdentityMode.DERIVED,
        semantics=ProfileSemanticsV2(
            acceptance_rejection=f"Accept parsed user/assistant blocks for {legacy_format}.",
            ordering="Document order preserved; heading/block sequence is authoritative.",
            duplicate_handling="Duplicate headings/blocks remain distinct byte spans.",
            authorship="Role inferred from Markdown structure; not provider-native record IDs.",
            chronology_timezone="File timestamp or session header when present; otherwise unknown.",
            reply_structure="Linear section/block order; no provider thread IDs.",
            validity_currentness="File revision digest binds capture as-of.",
            unknown_extension_fields="Non-chat metadata lines declared omitted.",
            attachments_blobs="No attachment/blob authority in Markdown parse.",
            tool_referenced_material="Token summaries and steering truncation declared omitted.",
            omissions_truncation=omissions,
            canonicalization_profile="Legacy markdown adapters produce derived block messages.",
            source_instance_binding="Physical file instance + revision digest.",
            native_record_identity="Byte/heading span occurrence only; never provider-native.",
            revision_asof="File mtime/digest as capture as-of.",
            raw_envelope_recovery="Requires raw file bytes/spans; parsed blocks are lossy.",
            replay_asof="Replay requires sealed file snapshot.",
        ),
        declared_omissions=("token_summaries", "steering_truncation", "metadata_lines"),
        default_availability=ConditionNeutralEvidenceAvailabilityV2(
            source_presence=SourcePresenceV2.PRESENT,
            verbatim_evidence_availability=VerbatimEvidenceAvailabilityV2.UNAVAILABLE,
            summary_evidence_availability=SummaryEvidenceAvailabilityV2.AVAILABLE,
        ),
        schema_version=f"{legacy_format}.md.v1",
    )
    profile = bind_profile_identity(profile)
    profile.validate()
    return profile

"""OpenCode SQLite evidence adapter profile."""

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

PROFILE_ID = "v2/evidence/opencode-sqlite"
LEGACY_FORMAT = "sqlite_opencode"


def opencode_sqlite_profile(*, schema_version: str = "opencode.message.part.v1") -> EvidenceAdapterProfileV2:
    vector = CapabilityVectorV2(
        occurrence_identity=OccurrenceIdentityCapability.ISSUER_ATTESTED,
        source_instance_binding=SourceInstanceBindingCapability.DECLARED,
        revision_asof_binding=RevisionAsofBindingCapability.UNKNOWN,
        evidence_completeness=EvidenceCompletenessCapability.PARTIAL_KNOWN,
        canonical_verification=CanonicalVerificationCapability.UNVERIFIED,
        temporal_reproducibility=TemporalReproducibilityCapability.UNKNOWN,
        attachment_material_span_completeness=AttachmentMaterialSpanCapability.UNKNOWN,
        preservation_replay_capability=PreservationReplayCapability.UNSEALED,
        lineage_assurance=LineageAssuranceCapability.UNKNOWN,
    )
    profile = EvidenceAdapterProfileV2(
        profile_id=PROFILE_ID,
        legacy_format=LEGACY_FORMAT,
        adapter_implementation_digest=profile_implementation_digest(
            PROFILE_ID, schema_version=schema_version
        ),
        capability_vector=vector,
        native_record_identity_mode=NativeRecordIdentityMode.UNKNOWN,
        semantics=ProfileSemanticsV2(
            acceptance_rejection="Accept message/part rows with JSON data columns; reject malformed JSON.",
            ordering="Preserve message and part ordering as stored in SQLite.",
            duplicate_handling="Message/part IDs treated as distinct; duplicates declared not merged silently.",
            authorship="Role and model/provider from message JSON when present.",
            chronology_timezone="Timestamps taken from stored columns; timezone semantics issuer-dependent.",
            reply_structure="Session-scoped message/part hierarchy when available.",
            validity_currentness="Issuer guarantees for revision/reuse remain unknown.",
            unknown_extension_fields="Extension JSON keys must be preserved in raw envelope or declared omitted.",
            attachments_blobs="Attachment/part blobs require raw envelope; legacy parse may omit.",
            tool_referenced_material="Tool/event parts require explicit omission inventory when skipped.",
            omissions_truncation="Legacy parse may discard message/part IDs and non-text material.",
            canonicalization_profile="Separate V2 evidence profile; legacy sqlite_chat remains ingest-only.",
            source_instance_binding="Local DB file instance + schema version fingerprint.",
            native_record_identity="message.id and part.id when retained; not NATIVE_UNIQUE without issuer proof.",
            revision_asof="Schema/version binding declared; issuer revision semantics unknown.",
            raw_envelope_recovery="Requires raw message/part JSON envelope beyond legacy canonical dict.",
            replay_asof="Replay unknown until issuer guarantees and sealed envelope exist.",
        ),
        declared_omissions=("discarded_message_ids", "discarded_part_ids", "tool_events"),
        default_availability=ConditionNeutralEvidenceAvailabilityV2(
            source_presence=SourcePresenceV2.PRESENT,
            verbatim_evidence_availability=VerbatimEvidenceAvailabilityV2.UNAVAILABLE,
            summary_evidence_availability=SummaryEvidenceAvailabilityV2.AVAILABLE,
        ),
        schema_version=schema_version,
    )
    profile = bind_profile_identity(profile)
    profile.validate()
    return profile


def opencode_sqlite_profile_schema_drift(new_schema: str) -> EvidenceAdapterProfileV2:
    profile = opencode_sqlite_profile(schema_version=new_schema)
    vector = profile.capability_vector.with_overrides(
        revision_asof_binding=RevisionAsofBindingCapability.UNKNOWN.value,
        evidence_completeness=EvidenceCompletenessCapability.UNKNOWN.value,
    )
    return profile.with_capability_vector(vector)

"""Synthetic hermetic fixtures for naturalistic G1 tests."""

from __future__ import annotations

import copy
from eval_naturalistic.base import ArtifactHeaderV1
from eval_naturalistic.contracts import (
    AdjudicationRecordV1,
    CensusSampleManifestV1,
    ConvMemCaptureStateV1,
    EpisodeFrameV1,
    EpisodeRecordV1,
    EpisodeRegistryEntryV1,
    EvidenceSourceV1,
    ParameterSlotV1,
    ProbeManifestV1,
    RawEvidenceManifestV1,
    SampleRosterEntryV1,
    ScoringKeyV1,
    TargetCaptureStateV1,
    TargetRecordV1,
    TargetRegistryV1,
    TargetSpanBindingV1,
    seal_artifact_dict,
)
from eval_naturalistic.digest import artifact_content_digest, make_artifact_id
from eval_naturalistic.enums import (
    AdmissibleSourceClass,
    CaptureDiagnosticState,
    CensusMode,
    EligibilityDisposition,
    EpisodeDisposition,
    EpisodeRegistryStatus,
    EvidenceCompletenessState,
    LeakageReviewDisposition,
    ParameterFreezeStatus,
    SamplingMode,
)


def _base_header(*, role: str, parent_id: str | None = None, parent_digest: str | None = None) -> ArtifactHeaderV1:
    return ArtifactHeaderV1(
        artifact_id="pending",
        schema_version="pending",
        parent_artifact_id=parent_id,
        parent_digest=parent_digest,
        created_at="2026-08-30T00:00:00Z",
        seal_time=None,
        responsible_role=role,
        content_digest=None,
        sealed=False,
    )


def _finalize(artifact_dict: dict, *, kind: str, schema: str, role: str, seal: bool = True) -> dict:
    body = copy.deepcopy(artifact_dict)
    body["header"] = {
        **body["header"],
        "schema_version": schema,
        "responsible_role": role,
    }
    digest = artifact_content_digest(body)
    body["header"] = {
        **body["header"],
        "artifact_id": make_artifact_id(kind=kind, content_digest=digest),
        "content_digest": digest,
    }
    if seal:
        body = seal_artifact_dict(body, seal_time="2026-08-30T01:00:00Z")
    return body


def make_synthetic_frame(*, study_id: str = "study-synthetic-001") -> EpisodeFrameV1:
    frame = EpisodeFrameV1(
        header=_base_header(role="study_owner"),
        study_id=study_id,
        frame_version="v1",
        episode_population_policy_id="policy-pop-001",
        inclusion_exclusion_policy_id="policy-inc-exc-001",
        episode_count_contract_id="contract-count-001",
        observation_window_contract_id="contract-window-001",
        episode_close_rule_id="rule-close-001",
        context_gap_schedule_id="schedule-gap-001",
        model_build_settings_id="settings-model-001",
        ordinary_tool_environment_id="env-ordinary-001",
        eligibility_unitization_policy_id="policy-elig-001",
        adjudicator_workflow_id="workflow-adj-001",
        census_sampling_policy_id="policy-sample-001",
        probe_role_policy_id="policy-probe-role-001",
        outcome_estimand_policy_id="policy-estimand-001",
        terminal_state_policy_id="policy-terminal-001",
        parent_revision_id=None,
        parent_revision_digest=None,
        parameter_slots=[
            ParameterSlotV1(
                slot_name="meaningful_advantage",
                freeze_status=ParameterFreezeStatus.PENDING,
                construct_defining=True,
            ),
            ParameterSlotV1(
                slot_name="equivalence_margin",
                freeze_status=ParameterFreezeStatus.PENDING,
                construct_defining=True,
            ),
        ],
    )
    body = _finalize(frame.to_dict(), kind="frame", schema=EpisodeFrameV1.SCHEMA, role="study_owner")
    return EpisodeFrameV1.from_dict(body)


def make_synthetic_episode(*, frame: EpisodeFrameV1, episode_id: str = "ep-001") -> EpisodeRecordV1:
    record = EpisodeRecordV1(
        header=_base_header(
            role="study_controller",
            parent_id=frame.header.artifact_id,
            parent_digest=frame.header.content_digest,
        ),
        episode_id=episode_id,
        frame_artifact_id=frame.header.artifact_id,
        frame_digest=frame.header.content_digest or "",
        selection_position=1,
        scheduled_window_start="2026-08-30T08:00:00Z",
        scheduled_window_end="2026-08-30T09:00:00Z",
        disposition=EpisodeDisposition.OBSERVED_COMPLETE,
    )
    body = _finalize(
        record.to_dict(),
        kind="episode",
        schema=EpisodeRecordV1.SCHEMA,
        role="study_controller",
    )
    return EpisodeRecordV1.from_dict(body)


def make_synthetic_evidence(
    *,
    episode: EpisodeRecordV1,
    complete: bool = True,
) -> RawEvidenceManifestV1:
    manifest = RawEvidenceManifestV1(
        header=_base_header(
            role="evidence_recorder",
            parent_id=episode.header.artifact_id,
            parent_digest=episode.header.content_digest,
        ),
        episode_id=episode.episode_id,
        episode_record_artifact_id=episode.header.artifact_id,
        episode_record_digest=episode.header.content_digest or "",
        sources=[
            EvidenceSourceV1(
                source_id="src-001",
                source_class=AdmissibleSourceClass.TRANSCRIPT,
                locator="synthetic://transcript/ep-001",
                event_time="2026-08-30T08:15:00Z",
                capture_time="2026-08-30T08:16:00Z",
                content_digest="abc123" * 8,
            )
        ],
        completeness_state=(
            EvidenceCompletenessState.COMPLETE
            if complete
            else EvidenceCompletenessState.PARTIAL
        ),
        missing_source_explanation=None if complete else "synthetic missing tool output",
    )
    body = _finalize(
        manifest.to_dict(),
        kind="evidence",
        schema=RawEvidenceManifestV1.SCHEMA,
        role="evidence_recorder",
    )
    return RawEvidenceManifestV1.from_dict(body)


def make_synthetic_registry(
    *,
    evidence: RawEvidenceManifestV1,
    zero_targets: bool = False,
    evidence_incomplete: bool = False,
    ambiguous: bool = False,
) -> TargetRegistryV1:
    if evidence_incomplete:
        status = EpisodeRegistryStatus.EVIDENCE_INCOMPLETE
        targets: list[TargetRecordV1] = []
    elif ambiguous:
        status = EpisodeRegistryStatus.TARGET_ADJUDICATION_AMBIGUOUS
        targets = []
    elif zero_targets:
        status = EpisodeRegistryStatus.ZERO_ELIGIBLE_TARGETS
        targets = []
    else:
        status = EpisodeRegistryStatus.TARGETS_PRESENT
        targets = [
            TargetRecordV1(
                target_id="tgt-001",
                episode_id=evidence.episode_id,
                span_bindings=[
                    TargetSpanBindingV1(source_id="src-001", span_start=0, span_end=42)
                ],
                eligibility_disposition=EligibilityDisposition.ELIGIBLE,
                ground_truth_partition_digest="def456" * 8,
                provenance_requirement="source_required",
                admissibility_rationale="synthetic eligible target",
                unitization_rationale="atomic proposition",
                duplicate_of_target_id=None,
                parent_target_id=None,
                ambiguity_state=None,
                secondary_strata=["current_at_probe"],
                adjudication_records=[
                    AdjudicationRecordV1(
                        adjudicator_id="adj-a",
                        disposition=EligibilityDisposition.ELIGIBLE,
                        rationale="synthetic pass",
                    ),
                    AdjudicationRecordV1(
                        adjudicator_id="adj-b",
                        disposition=EligibilityDisposition.ELIGIBLE,
                        rationale="synthetic pass",
                    ),
                ],
                resolution_identity=None,
                adjudicator_ids=["adj-a", "adj-b"],
            )
        ]

    registry = TargetRegistryV1(
        header=_base_header(
            role="study_owner",
            parent_id=evidence.header.artifact_id,
            parent_digest=evidence.header.content_digest,
        ),
        evidence_manifest_ids=[evidence.header.artifact_id],
        episode_entries=[
            EpisodeRegistryEntryV1(
                episode_id=evidence.episode_id,
                registry_status=status,
                evidence_manifest_digest=evidence.header.content_digest or "",
                target_ids=[t.target_id for t in targets],
            )
        ],
        targets=targets,
        registry_policy_version="registry-policy-v1",
    )
    body = _finalize(
        registry.to_dict(),
        kind="registry",
        schema=TargetRegistryV1.SCHEMA,
        role="study_owner",
    )
    return TargetRegistryV1.from_dict(body)


def make_synthetic_census(*, registry: TargetRegistryV1) -> CensusSampleManifestV1:
    census = CensusSampleManifestV1(
        header=_base_header(
            role="study_controller",
            parent_id=registry.header.artifact_id,
            parent_digest=registry.header.content_digest,
        ),
        census_mode=CensusMode.COMPLETE,
        sampling_mode=SamplingMode.NOT_APPLICABLE,
        target_registry_artifact_id=registry.header.artifact_id,
        target_registry_digest=registry.header.content_digest or "",
        sampling_rule_identity="rule-census-complete-001",
        random_seed_identity=None,
        selected_roster=[
            SampleRosterEntryV1(
                episode_id=entry.episode_id,
                target_ids=list(entry.target_ids),
                inclusion_probability=1.0,
            )
            for entry in registry.episode_entries
        ],
        unsampled_roster_digest="000" * 21 + "0",
    )
    body = _finalize(
        census.to_dict(),
        kind="census",
        schema=CensusSampleManifestV1.SCHEMA,
        role="study_controller",
    )
    return CensusSampleManifestV1.from_dict(body)


def make_synthetic_probe(
    *,
    registry: TargetRegistryV1,
    probe_author_id: str = "probe-author-001",
    adjudicator_collision: bool = False,
) -> ProbeManifestV1:
    target = registry.targets[0] if registry.targets else None
    target_id = target.target_id if target else "tgt-none"
    probe = ProbeManifestV1(
        header=_base_header(
            role="probe_author",
            parent_id=registry.header.artifact_id,
            parent_digest=registry.header.content_digest,
        ),
        probe_id="probe-001",
        target_id=target_id,
        episode_id=registry.episode_entries[0].episode_id,
        probe_family_id="family-continuation-001",
        probe_author_id=probe_author_id,
        leakage_reviewer_id="leak-reviewer-001",
        adjudicator_collision_check_passed=not adjudicator_collision,
        leakage_review_disposition=LeakageReviewDisposition.APPROVED,
        prompt_content_digest="111" * 21 + "1",
        scoring_key_digest="222" * 21 + "2",
        scoring_key_partition_identity="partition-scorer-001",
    )
    body = _finalize(
        probe.to_dict(),
        kind="probe",
        schema=ProbeManifestV1.SCHEMA,
        role="probe_author",
    )
    return ProbeManifestV1.from_dict(body)


def make_synthetic_scoring_key(*, probe: ProbeManifestV1) -> ScoringKeyV1:
    key = ScoringKeyV1(
        header=_base_header(
            role="scorer_partition",
            parent_id=probe.header.artifact_id,
            parent_digest=probe.header.content_digest,
        ),
        probe_id=probe.probe_id,
        target_id=probe.target_id,
        key_partition_identity=probe.scoring_key_partition_identity,
        key_content_digest=probe.scoring_key_digest,
    )
    body = _finalize(
        key.to_dict(),
        kind="scoring_key",
        schema=ScoringKeyV1.SCHEMA,
        role="scorer_partition",
    )
    return ScoringKeyV1.from_dict(body)


def make_synthetic_capture(
    *,
    registry: TargetRegistryV1,
    capture_state: CaptureDiagnosticState = CaptureDiagnosticState.ABSENT_FROM_CONVMEM,
) -> ConvMemCaptureStateV1:
    capture = ConvMemCaptureStateV1(
        header=_base_header(
            role="study_controller",
            parent_id=registry.header.artifact_id,
            parent_digest=registry.header.content_digest,
        ),
        target_registry_artifact_id=registry.header.artifact_id,
        target_registry_digest=registry.header.content_digest or "",
        target_states=[
            TargetCaptureStateV1(
                target_id=target.target_id,
                capture_state=capture_state,
                capture_manifest_digest=None,
            )
            for target in registry.targets
        ],
    )
    body = _finalize(
        capture.to_dict(),
        kind="capture",
        schema=ConvMemCaptureStateV1.SCHEMA,
        role="study_controller",
    )
    return ConvMemCaptureStateV1.from_dict(body)

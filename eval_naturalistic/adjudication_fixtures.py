"""Synthetic hermetic fixtures for naturalistic G2 adjudication tests."""

from __future__ import annotations

from eval_naturalistic.adjudication import (
    AdjudicationWorkflowConfigV1,
    CandidateAdjudicationBundleV1,
)
from eval_naturalistic.contracts import AdjudicationRecordV1, TargetSpanBindingV1
from eval_naturalistic.enums import AdjudicationResolutionMethod, EligibilityDisposition
from eval_naturalistic.fixtures import (
    make_synthetic_episode,
    make_synthetic_evidence,
    make_synthetic_frame,
)


def make_default_workflow(
    *,
    adjudicator_a_id: str = "adj-a",
    adjudicator_b_id: str = "adj-b",
    prohibited_probe_author_ids: frozenset[str] | None = None,
) -> AdjudicationWorkflowConfigV1:
    return AdjudicationWorkflowConfigV1(
        adjudicator_a_id=adjudicator_a_id,
        adjudicator_b_id=adjudicator_b_id,
        resolution_method=AdjudicationResolutionMethod.THIRD_ADJUDICATOR,
        registry_policy_version="registry-policy-v1",
        prohibited_probe_author_ids=prohibited_probe_author_ids or frozenset(),
    )


def make_synthetic_adjudication_chain(*, complete_evidence: bool = True):
    frame = make_synthetic_frame()
    episode = make_synthetic_episode(frame=frame)
    evidence = make_synthetic_evidence(episode=episode, complete=complete_evidence)
    workflow = make_default_workflow()
    return frame, episode, evidence, workflow


def make_agreeing_eligible_candidate(
    *,
    target_id: str = "tgt-001",
    adjudicator_a_id: str = "adj-a",
    adjudicator_b_id: str = "adj-b",
) -> CandidateAdjudicationBundleV1:
    return CandidateAdjudicationBundleV1(
        target_id=target_id,
        span_bindings=[TargetSpanBindingV1(source_id="src-001", span_start=0, span_end=42)],
        adjudication_records=[
            AdjudicationRecordV1(
                adjudicator_id=adjudicator_a_id,
                disposition=EligibilityDisposition.ELIGIBLE,
                rationale="synthetic eligible pass A",
            ),
            AdjudicationRecordV1(
                adjudicator_id=adjudicator_b_id,
                disposition=EligibilityDisposition.ELIGIBLE,
                rationale="synthetic eligible pass B",
            ),
        ],
        ground_truth_partition_digest="def456" * 8,
        provenance_requirement="source_required",
        admissibility_rationale="synthetic eligible target",
        unitization_rationale="atomic proposition",
        secondary_strata=["current_at_probe"],
    )


def make_disagreeing_candidate_with_resolution(
    *,
    target_id: str = "tgt-disagree-001",
) -> CandidateAdjudicationBundleV1:
    return CandidateAdjudicationBundleV1(
        target_id=target_id,
        span_bindings=[TargetSpanBindingV1(source_id="src-001", span_start=10, span_end=20)],
        adjudication_records=[
            AdjudicationRecordV1(
                adjudicator_id="adj-a",
                disposition=EligibilityDisposition.ELIGIBLE,
                rationale="A says eligible",
            ),
            AdjudicationRecordV1(
                adjudicator_id="adj-b",
                disposition=EligibilityDisposition.INELIGIBLE,
                rationale="B says ineligible",
            ),
        ],
        resolution_record=AdjudicationRecordV1(
            adjudicator_id="adj-c",
            disposition=EligibilityDisposition.ELIGIBLE,
            rationale="third adjudicator resolves to eligible",
        ),
        resolution_identity="third-adj-resolver-001",
        ground_truth_partition_digest="abc123" * 8,
        admissibility_rationale="resolved eligible",
        unitization_rationale="atomic",
        secondary_strata=["current_at_probe"],
    )


def make_disagreeing_candidate_without_resolution(
    *,
    target_id: str = "tgt-unresolved-001",
) -> CandidateAdjudicationBundleV1:
    return CandidateAdjudicationBundleV1(
        target_id=target_id,
        span_bindings=[TargetSpanBindingV1(source_id="src-001", span_start=5, span_end=15)],
        adjudication_records=[
            AdjudicationRecordV1(
                adjudicator_id="adj-a",
                disposition=EligibilityDisposition.ELIGIBLE,
                rationale="A says eligible",
            ),
            AdjudicationRecordV1(
                adjudicator_id="adj-b",
                disposition=EligibilityDisposition.AMBIGUOUS_NON_EVALUABLE,
                rationale="B says ambiguous",
            ),
        ],
    )

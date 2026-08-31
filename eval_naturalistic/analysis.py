"""G4 analysis and statistical machinery for the naturalistic product-value study.

Synthetic/pre-live only: bounded within-episode scores, co-primary aggregation,
sparse reliability states, scorer-reliability records, and information-gate slots.
No live numerical thresholds or product conclusions.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

from eval_naturalistic.base import ArtifactHeaderV1
from eval_naturalistic.contract_validate import NaturalisticValidation
from eval_naturalistic.contracts import (
    EpisodeOutcomeV1,
    ParameterSlotV1,
    TargetScoreV1,
)
from eval_naturalistic.digest import artifact_content_digest
from eval_naturalistic.enums import (
    EpisodeRegistryStatus,
    InformationSufficiencyState,
    MissingnessComparabilityState,
    OutcomeReasonCode,
    ParameterFreezeStatus,
    ProtocolValidityState,
    ReliabilityState,
    ScorerIntegrityState,
    ScorerReliabilityDispositionState,
    StudyTerminalDisposition,
    TrialCondition,
)

SCORE_BOUND_MIN = 0.0
SCORE_BOUND_MAX = 1.0
WITHIN_EPISODE_AGGREGATION_RULE_ID = "mean-of-evaluable-target-scores-v1"
SCORER_RELIABILITY_STATISTIC_ID = "bounded-score-within-tolerance-agreement-rate-v1"

REQUIRED_INFORMATION_PARAMETER_SLOTS = frozenset(
    {
        "meaningful_advantage",
        "equivalence_margin",
        "target_bearing_episode_information_floor",
        "secondary_information_floor",
        "precision_confidence_criterion",
        "sparse_reliability_criterion",
        "scorer_reliability_gate",
        "terminal_disposition_rules",
    }
)

TARGET_BEARING_EVALUABLE_STATUSES = frozenset(
    {
        EpisodeRegistryStatus.TARGETS_PRESENT,
    }
)

TARGET_BEARING_STATUSES = frozenset(
    {
        EpisodeRegistryStatus.TARGETS_PRESENT,
        EpisodeRegistryStatus.TARGETS_PRESENT_BUT_NOT_EVALUABLE,
    }
)

SPARSE_RELIABILITY_STATES = frozenset(
    {
        ReliabilityState.RELIABILITY_SPARSE,
        ReliabilityState.RELIABILITY_NON_ESTIMABLE,
    }
)


@dataclass
class EpisodeRegistryViewV1:
    """Minimal episode registry row for aggregation (synthetic or sealed)."""

    episode_id: str
    registry_status: EpisodeRegistryStatus
    eligible_target_count: int


@dataclass
class WithinEpisodeScoreV1:
    """One bounded normalized continuation-utility score per episode and condition."""

    episode_id: str
    condition: TrialCondition
    normalized_score: float | None
    reliability_state: ReliabilityState
    target_count: int
    aggregation_rule_id: str = WITHIN_EPISODE_AGGREGATION_RULE_ID
    validation_errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "episode_id": self.episode_id,
            "condition": self.condition.value,
            "reliability_state": self.reliability_state.value,
            "target_count": self.target_count,
            "aggregation_rule_id": self.aggregation_rule_id,
            "validation_errors": self.validation_errors,
        }
        if self.normalized_score is not None:
            out["normalized_score"] = self.normalized_score
        return out


@dataclass
class ScorerSubmissionV1:
    scorer_id: str
    episode_id: str
    condition: TrialCondition
    normalized_score: float | None
    reliability_state: ReliabilityState

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "scorer_id": self.scorer_id,
            "episode_id": self.episode_id,
            "condition": self.condition.value,
            "reliability_state": self.reliability_state.value,
        }
        if self.normalized_score is not None:
            out["normalized_score"] = self.normalized_score
        return out


@dataclass
class ScorerReliabilityRecordV1:  # pylint: disable=too-many-instance-attributes
    """Scorer agreement record with frozen statistic/gate slots (no live gate value)."""

    statistic_identity: str
    gate_slot_name: str
    gate_value: str | None
    observed_statistic: float | None
    agreement_count: int
    disagreement_count: int
    passes_gate: bool | None
    scorer_ids: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "statistic_identity": self.statistic_identity,
            "gate_slot_name": self.gate_slot_name,
            "agreement_count": self.agreement_count,
            "disagreement_count": self.disagreement_count,
            "passes_gate": self.passes_gate,
            "scorer_ids": self.scorer_ids,
            "errors": self.errors,
        }
        if self.gate_value is not None:
            out["gate_value"] = self.gate_value
        if self.observed_statistic is not None:
            out["observed_statistic"] = self.observed_statistic
        return out


@dataclass
class CoPrimaryAggregationV1:  # pylint: disable=too-many-instance-attributes
    """Two-part co-primary structure: opportunity + conditional continuation benefit."""

    opportunity_prevalence: float
    opportunity_density: float
    opportunity_episode_count: int
    target_bearing_episode_count: int
    target_bearing_evaluable_episode_count: int
    target_bearing_not_evaluable_episode_count: int
    eligible_target_count: int
    zero_target_episode_count: int
    incomplete_episode_count: int
    ambiguous_episode_count: int
    protocol_invalid_episode_count: int
    conditional_mean_effect: float | None
    conditional_episode_count: int
    sparse_episode_count: int
    non_estimable_episode_count: int
    aggregation_reliability_state: ReliabilityState
    lineage_digest: str

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "opportunity_prevalence": self.opportunity_prevalence,
            "opportunity_density": self.opportunity_density,
            "opportunity_episode_count": self.opportunity_episode_count,
            "target_bearing_episode_count": self.target_bearing_episode_count,
            "target_bearing_evaluable_episode_count": self.target_bearing_evaluable_episode_count,
            "target_bearing_not_evaluable_episode_count": self.target_bearing_not_evaluable_episode_count,
            "eligible_target_count": self.eligible_target_count,
            "zero_target_episode_count": self.zero_target_episode_count,
            "incomplete_episode_count": self.incomplete_episode_count,
            "ambiguous_episode_count": self.ambiguous_episode_count,
            "protocol_invalid_episode_count": self.protocol_invalid_episode_count,
            "conditional_episode_count": self.conditional_episode_count,
            "sparse_episode_count": self.sparse_episode_count,
            "non_estimable_episode_count": self.non_estimable_episode_count,
            "aggregation_reliability_state": self.aggregation_reliability_state.value,
            "lineage_digest": self.lineage_digest,
        }
        if self.conditional_mean_effect is not None:
            out["conditional_mean_effect"] = self.conditional_mean_effect
        return out


@dataclass
class InformationGateEvaluationV1:  # pylint: disable=too-many-instance-attributes
    """T10 gate machinery: slots and readiness only — no opportunistic live values."""

    parameter_slots_digest: str
    all_required_slots_present: bool
    all_slots_frozen: bool
    scorer_reliability_passes: bool | None
    sparse_blocks_conclusion: bool
    disposition: StudyTerminalDisposition
    rationale: str
    errors: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors


@dataclass
class AnalysisAggregationResult:
    ok: bool
    co_primary: CoPrimaryAggregationV1 | None
    episode_outcomes: list[EpisodeOutcomeV1]
    errors: list[str]


def validate_bounded_normalized_score(
    score: float | None,
    *,
    label: str = "normalized_score",
) -> NaturalisticValidation:
    errors: list[str] = []
    if score is None:
        return NaturalisticValidation(errors=errors)
    if isinstance(score, bool) or not isinstance(score, (int, float)):
        errors.append(f"{label}: must be numeric")
        return NaturalisticValidation(errors=errors)
    value = float(score)
    if not math.isfinite(value):
        errors.append(f"{label}: must be finite")
    elif value < SCORE_BOUND_MIN or value > SCORE_BOUND_MAX:
        errors.append(
            f"{label}: {value} outside bounded contract [{SCORE_BOUND_MIN}, {SCORE_BOUND_MAX}]"
        )
    return NaturalisticValidation(errors=errors)


def is_target_bearing_evaluable(status: EpisodeRegistryStatus) -> bool:
    return status in TARGET_BEARING_EVALUABLE_STATUSES


def is_target_bearing(status: EpisodeRegistryStatus) -> bool:
    return status in TARGET_BEARING_STATUSES


def is_zero_target_episode(status: EpisodeRegistryStatus) -> bool:
    return status == EpisodeRegistryStatus.ZERO_ELIGIBLE_TARGETS


def sparse_blocks_ordinary_conclusion(reliability_state: ReliabilityState) -> bool:
    """Sparse or non-estimable evidence must not become confidence/null/product verdict."""

    return reliability_state in SPARSE_RELIABILITY_STATES


def aggregate_targets_to_within_episode_score(
    target_scores: list[TargetScoreV1],
    *,
    episode_id: str,
    condition: TrialCondition,
    aggregation_rule_id: str = WITHIN_EPISODE_AGGREGATION_RULE_ID,
) -> WithinEpisodeScoreV1:
    """Form one bounded within-episode score; target count does not weight the episode."""

    if not target_scores:
        return WithinEpisodeScoreV1(
            episode_id=episode_id,
            condition=condition,
            normalized_score=None,
            reliability_state=ReliabilityState.RELIABILITY_NOT_APPLICABLE,
            target_count=0,
            aggregation_rule_id=aggregation_rule_id,
        )

    errors: list[str] = []
    seen_target_ids: set[str] = set()
    seen_trial_ids: set[str] = set()
    for score in target_scores:
        bound = validate_bounded_normalized_score(
            score.normalized_score,
            label=f"target_score[{score.target_id}]",
        )
        errors.extend(bound.errors)
        if score.target_id in seen_target_ids:
            errors.append(f"duplicate target score row: {score.target_id}")
        seen_target_ids.add(score.target_id)
        if score.trial_id in seen_trial_ids:
            errors.append(f"duplicate trial score row: {score.trial_id}")
        seen_trial_ids.add(score.trial_id)
    if errors:
        return WithinEpisodeScoreV1(
            episode_id=episode_id,
            condition=condition,
            normalized_score=None,
            reliability_state=ReliabilityState.RELIABILITY_NON_ESTIMABLE,
            target_count=len(target_scores),
            aggregation_rule_id=aggregation_rule_id,
            validation_errors=errors,
        )

    reliability_states = {score.reliability_state for score in target_scores}
    if ReliabilityState.RELIABILITY_NON_ESTIMABLE in reliability_states:
        return WithinEpisodeScoreV1(
            episode_id=episode_id,
            condition=condition,
            normalized_score=None,
            reliability_state=ReliabilityState.RELIABILITY_NON_ESTIMABLE,
            target_count=len(target_scores),
            aggregation_rule_id=aggregation_rule_id,
        )
    if ReliabilityState.RELIABILITY_SPARSE in reliability_states:
        acceptable = [
            score.normalized_score
            for score in target_scores
            if score.reliability_state == ReliabilityState.RELIABILITY_ACCEPTABLE
            and score.normalized_score is not None
        ]
        descriptive = sum(acceptable) / len(acceptable) if acceptable else None
        return WithinEpisodeScoreV1(
            episode_id=episode_id,
            condition=condition,
            normalized_score=descriptive,
            reliability_state=ReliabilityState.RELIABILITY_SPARSE,
            target_count=len(target_scores),
            aggregation_rule_id=aggregation_rule_id,
        )

    acceptable_scores = [
        score.normalized_score
        for score in target_scores
        if score.reliability_state == ReliabilityState.RELIABILITY_ACCEPTABLE
        and score.normalized_score is not None
    ]
    if not acceptable_scores:
        return WithinEpisodeScoreV1(
            episode_id=episode_id,
            condition=condition,
            normalized_score=None,
            reliability_state=ReliabilityState.RELIABILITY_NON_ESTIMABLE,
            target_count=len(target_scores),
            aggregation_rule_id=aggregation_rule_id,
        )

    episode_score = sum(acceptable_scores) / len(acceptable_scores)
    return WithinEpisodeScoreV1(
        episode_id=episode_id,
        condition=condition,
        normalized_score=episode_score,
        reliability_state=ReliabilityState.RELIABILITY_ACCEPTABLE,
        target_count=len(target_scores),
        aggregation_rule_id=aggregation_rule_id,
    )


def _score_for_condition(
    scores_by_condition: dict[TrialCondition, WithinEpisodeScoreV1],
    condition: TrialCondition,
) -> WithinEpisodeScoreV1 | None:
    return scores_by_condition.get(condition)


# This is the one orchestration boundary that validates and assembles both co-primary parts.
# pylint: disable-next=too-many-locals,too-many-branches
def compute_co_primary_aggregation(
    episodes: list[EpisodeRegistryViewV1],
    within_episode_scores: list[WithinEpisodeScoreV1],
    *,
    lineage_inputs: dict[str, Any],
) -> AnalysisAggregationResult:
    """Co-primary A across all episodes; co-primary B among target-bearing/evaluable only."""

    errors: list[str] = []
    if not episodes:
        errors.append("co-primary aggregation requires at least one episode")
        return AnalysisAggregationResult(ok=False, co_primary=None, episode_outcomes=[], errors=errors)

    episode_ids = [episode.episode_id for episode in episodes]
    known_episode_ids = set(episode_ids)
    duplicate_episode_ids = sorted(
        episode_id for episode_id in known_episode_ids if episode_ids.count(episode_id) > 1
    )
    if duplicate_episode_ids:
        errors.append("duplicate episode registry rows: " + ", ".join(duplicate_episode_ids))

    one_score = prove_one_score_per_episode_per_condition(within_episode_scores)
    errors.extend(one_score.errors)

    scores_by_episode: dict[str, dict[TrialCondition, WithinEpisodeScoreV1]] = {}
    for score in within_episode_scores:
        bound = validate_bounded_normalized_score(
            score.normalized_score,
            label=f"within_episode_score[{score.episode_id}/{score.condition.value}]",
        )
        errors.extend(bound.errors)
        errors.extend(score.validation_errors)
        if score.episode_id not in known_episode_ids:
            errors.append(f"within-episode score references unknown episode: {score.episode_id}")
        if score.target_count <= 0:
            errors.append(
                f"{score.episode_id}/{score.condition.value}: scored condition must have target_count > 0"
            )
        scores_by_episode.setdefault(score.episode_id, {})[score.condition] = score

    for episode in episodes:
        if not is_target_bearing_evaluable(episode.registry_status) and episode.episode_id in scores_by_episode:
            errors.append(
                f"{episode.episode_id}: non-evaluable episode must not carry condition scores"
            )
        if episode.eligible_target_count < 0:
            errors.append(f"{episode.episode_id}: eligible_target_count must be non-negative")
        if is_target_bearing(episode.registry_status) and episode.eligible_target_count == 0:
            errors.append(f"{episode.episode_id}: target-bearing episode requires eligible_target_count > 0")
        if not is_target_bearing(episode.registry_status) and episode.eligible_target_count != 0:
            errors.append(
                f"{episode.episode_id}: non-target-bearing episode requires eligible_target_count == 0"
            )

    if errors:
        return AnalysisAggregationResult(ok=False, co_primary=None, episode_outcomes=[], errors=errors)

    total = len(episodes)
    target_bearing = 0
    target_bearing_evaluable = 0
    target_bearing_not_evaluable = 0
    eligible_target_count = 0
    zero_target = 0
    incomplete = 0
    ambiguous = 0
    protocol_invalid = 0
    sparse_count = 0
    non_estimable_count = 0
    paired_effects: list[float] = []

    episode_outcomes: list[EpisodeOutcomeV1] = []
    header_stub = ArtifactHeaderV1(
        artifact_id="pending",
        schema_version="convmem/naturalistic/episode-outcome-v1",
        parent_artifact_id=None,
        parent_digest=None,
        created_at="2026-08-30T00:00:00Z",
        seal_time=None,
        responsible_role="analysis_owner",
        content_digest=None,
        sealed=False,
    )

    for episode in episodes:
        status = episode.registry_status
        if is_target_bearing(status):
            target_bearing += 1
            eligible_target_count += episode.eligible_target_count
        if is_zero_target_episode(status):
            zero_target += 1
        elif status == EpisodeRegistryStatus.EVIDENCE_INCOMPLETE:
            incomplete += 1
        elif status == EpisodeRegistryStatus.TARGET_ADJUDICATION_AMBIGUOUS:
            ambiguous += 1
        elif status == EpisodeRegistryStatus.TARGETS_PRESENT_BUT_NOT_EVALUABLE:
            target_bearing_not_evaluable += 1
        elif status == EpisodeRegistryStatus.PROTOCOL_INVALID:
            protocol_invalid += 1
            errors.append(f"{episode.episode_id}: protocol-invalid episode blocks valid aggregation")
        elif is_target_bearing_evaluable(status):
            target_bearing_evaluable += 1

        opportunity_component = 1.0 if is_target_bearing(status) else 0.0
        conditional_effect: float | None = None
        reliability = ReliabilityState.RELIABILITY_NOT_APPLICABLE

        if is_target_bearing_evaluable(status):
            episode_scores = scores_by_episode.get(episode.episode_id, {})
            c0 = _score_for_condition(episode_scores, TrialCondition.C0)
            c1 = _score_for_condition(episode_scores, TrialCondition.C1)
            if c0 is None or c1 is None:
                errors.append(
                    f"{episode.episode_id}: target-bearing episode missing paired condition scores"
                )
                reliability = ReliabilityState.RELIABILITY_NON_ESTIMABLE
                non_estimable_count += 1
            elif sparse_blocks_ordinary_conclusion(
                c0.reliability_state
            ) or sparse_blocks_ordinary_conclusion(c1.reliability_state):
                if ReliabilityState.RELIABILITY_SPARSE in (
                    c0.reliability_state,
                    c1.reliability_state,
                ):
                    sparse_count += 1
                    reliability = ReliabilityState.RELIABILITY_SPARSE
                else:
                    non_estimable_count += 1
                    reliability = ReliabilityState.RELIABILITY_NON_ESTIMABLE
            elif (
                c0.normalized_score is not None
                and c1.normalized_score is not None
                and c0.reliability_state == ReliabilityState.RELIABILITY_ACCEPTABLE
                and c1.reliability_state == ReliabilityState.RELIABILITY_ACCEPTABLE
            ):
                conditional_effect = c1.normalized_score - c0.normalized_score
                paired_effects.append(conditional_effect)
                reliability = ReliabilityState.RELIABILITY_ACCEPTABLE
            else:
                non_estimable_count += 1
                reliability = ReliabilityState.RELIABILITY_NON_ESTIMABLE

        episode_outcomes.append(
            EpisodeOutcomeV1(
                header=header_stub,
                episode_id=episode.episode_id,
                registry_status=status,
                conditional_effect=conditional_effect,
                reliability_state=reliability,
                opportunity_component=opportunity_component,
            )
        )

    opportunity_prevalence = target_bearing / total
    opportunity_density = eligible_target_count / total
    conditional_mean = sum(paired_effects) / len(paired_effects) if paired_effects else None

    has_incomplete_primary_evidence = any(
        count > 0
        for count in (
            sparse_count,
            non_estimable_count,
            incomplete,
            ambiguous,
            target_bearing_not_evaluable,
            protocol_invalid,
        )
    )
    if target_bearing == 0 or has_incomplete_primary_evidence or conditional_mean is None:
        agg_reliability = ReliabilityState.RELIABILITY_NON_ESTIMABLE
    else:
        agg_reliability = ReliabilityState.RELIABILITY_ACCEPTABLE

    lineage_digest = artifact_content_digest(lineage_inputs)
    co_primary = CoPrimaryAggregationV1(
        opportunity_prevalence=opportunity_prevalence,
        opportunity_density=opportunity_density,
        opportunity_episode_count=total,
        target_bearing_episode_count=target_bearing,
        target_bearing_evaluable_episode_count=target_bearing_evaluable,
        target_bearing_not_evaluable_episode_count=target_bearing_not_evaluable,
        eligible_target_count=eligible_target_count,
        zero_target_episode_count=zero_target,
        incomplete_episode_count=incomplete,
        ambiguous_episode_count=ambiguous,
        protocol_invalid_episode_count=protocol_invalid,
        conditional_mean_effect=conditional_mean,
        conditional_episode_count=len(paired_effects),
        sparse_episode_count=sparse_count,
        non_estimable_episode_count=non_estimable_count,
        aggregation_reliability_state=agg_reliability,
        lineage_digest=lineage_digest,
    )

    return AnalysisAggregationResult(
        ok=not errors,
        co_primary=co_primary,
        episode_outcomes=episode_outcomes,
        errors=errors,
    )


def validate_required_parameter_slots(
    slots: list[ParameterSlotV1],
) -> NaturalisticValidation:
    errors: list[str] = []
    slot_names = [slot.slot_name for slot in slots]
    present = set(slot_names)
    duplicates = sorted(name for name in present if slot_names.count(name) > 1)
    if duplicates:
        errors.append("duplicate information parameter slots: " + ", ".join(duplicates))
    missing = REQUIRED_INFORMATION_PARAMETER_SLOTS - present
    if missing:
        errors.append(
            "missing required information parameter slots: "
            + ", ".join(sorted(missing))
        )
    for slot in slots:
        if slot.slot_name not in REQUIRED_INFORMATION_PARAMETER_SLOTS:
            continue
        if slot.freeze_status == ParameterFreezeStatus.FROZEN and slot.value is None:
            errors.append(f"frozen parameter slot '{slot.slot_name}' requires a value")
        if slot.freeze_status == ParameterFreezeStatus.PENDING and slot.value is not None:
            errors.append(f"pending parameter slot '{slot.slot_name}' must not carry a value")
    return NaturalisticValidation(errors=errors)


def reject_post_result_parameter_mutation(
    slots_before: list[ParameterSlotV1],
    slots_after: list[ParameterSlotV1],
) -> NaturalisticValidation:
    """Post-result slot fills or value changes invalidate the analysis generation."""

    errors: list[str] = []
    validation_before = validate_required_parameter_slots(slots_before)
    validation_after = validate_required_parameter_slots(slots_after)
    errors.extend(validation_before.errors)
    errors.extend(validation_after.errors)
    before = {slot.slot_name: slot for slot in slots_before}
    after = {slot.slot_name: slot for slot in slots_after}

    removed = sorted(set(before) - set(after))
    added = sorted(set(after) - set(before))
    if removed:
        errors.append("post-result removal of parameter slots: " + ", ".join(removed))
    if added:
        errors.append("post-result addition of parameter slots: " + ", ".join(added))

    for name in REQUIRED_INFORMATION_PARAMETER_SLOTS:
        if name not in before or name not in after:
            continue
        prev = before[name]
        curr = after[name]
        if prev.to_dict() != curr.to_dict():
            errors.append(f"post-result mutation of parameter slot '{name}'")
        if (
            prev.freeze_status in {ParameterFreezeStatus.PENDING, ParameterFreezeStatus.NOT_APPLICABLE}
            and curr.freeze_status == ParameterFreezeStatus.FROZEN
            and curr.value is not None
            and prev.value is None
        ):
            errors.append(f"post-result fill of parameter slot '{name}'")

    return NaturalisticValidation(errors=errors)


def record_scorer_reliability(
    primary_submissions: list[ScorerSubmissionV1],
    secondary_submissions: list[ScorerSubmissionV1],
    *,
    gate_value: str | None = None,
    agreement_tolerance: float,
) -> ScorerReliabilityRecordV1:
    """Record bounded-score agreement; product use still requires a T0-frozen gate."""

    errors: list[str] = []

    def _submission_map(
        submissions: list[ScorerSubmissionV1],
        *,
        label: str,
    ) -> dict[tuple[str, str], ScorerSubmissionV1]:
        result: dict[tuple[str, str], ScorerSubmissionV1] = {}
        for submission in submissions:
            key = (submission.episode_id, submission.condition.value)
            if key in result:
                errors.append(
                    f"duplicate {label} scorer submission for "
                    f"episode={submission.episode_id} condition={submission.condition.value}"
                )
            result[key] = submission
            bound = validate_bounded_normalized_score(
                submission.normalized_score,
                label=f"{label}_scorer[{submission.episode_id}/{submission.condition.value}]",
            )
            errors.extend(bound.errors)
        return result

    primary_by_key = _submission_map(primary_submissions, label="primary")
    secondary_by_key = _submission_map(secondary_submissions, label="secondary")
    primary_ids = {sub.scorer_id for sub in primary_submissions}
    secondary_ids = {sub.scorer_id for sub in secondary_submissions}
    if len(primary_ids) != 1:
        errors.append("primary scorer submissions must have exactly one scorer identity")
    if len(secondary_ids) != 1:
        errors.append("secondary scorer submissions must have exactly one scorer identity")
    if primary_ids & secondary_ids:
        errors.append("primary and secondary scorer identities must be independent")
    tolerance_validation = validate_bounded_normalized_score(
        agreement_tolerance,
        label="agreement_tolerance",
    )
    errors.extend(tolerance_validation.errors)
    keys = sorted(set(primary_by_key) | set(secondary_by_key))
    agreement = 0
    disagreement = 0
    for key in keys:
        a = primary_by_key.get(key)
        b = secondary_by_key.get(key)
        if a is None or b is None:
            disagreement += 1
            missing_role = "primary" if a is None else "secondary"
            errors.append(
                f"missing {missing_role} scorer submission for episode={key[0]} condition={key[1]}"
            )
            continue
        if a.normalized_score is None or b.normalized_score is None:
            disagreement += 1
            continue
        if abs(a.normalized_score - b.normalized_score) <= agreement_tolerance:
            agreement += 1
        else:
            disagreement += 1

    observed = agreement / len(keys) if keys else None
    passes: bool | None = None
    if gate_value is not None and observed is not None and not errors:
        try:
            threshold = float(gate_value)
            if not math.isfinite(threshold) or not SCORE_BOUND_MIN <= threshold <= SCORE_BOUND_MAX:
                errors.append("scorer reliability gate must be finite and within [0.0, 1.0]")
            else:
                passes = observed >= threshold
        except (TypeError, ValueError):
            errors.append("scorer reliability gate must be numeric")

    scorer_ids = sorted(
        {sub.scorer_id for sub in primary_submissions}
        | {sub.scorer_id for sub in secondary_submissions}
    )
    return ScorerReliabilityRecordV1(
        statistic_identity=SCORER_RELIABILITY_STATISTIC_ID,
        gate_slot_name="scorer_reliability_gate",
        gate_value=gate_value,
        observed_statistic=observed,
        agreement_count=agreement,
        disagreement_count=disagreement,
        passes_gate=passes,
        scorer_ids=scorer_ids,
        errors=errors,
    )


def evaluate_information_gate_readiness(
    parameter_slots: list[ParameterSlotV1],
    co_primary: CoPrimaryAggregationV1,
    scorer_reliability: ScorerReliabilityRecordV1 | None,
) -> InformationGateEvaluationV1:
    """Fail-closed gate machinery; product dispositions require frozen slots and passing gates."""

    errors: list[str] = []
    slot_validation = validate_required_parameter_slots(parameter_slots)
    errors.extend(slot_validation.errors)

    slots_digest = artifact_content_digest(
        {"parameter_slots": [slot.to_dict() for slot in parameter_slots]}
    )
    all_frozen = slot_validation.ok and all(
        slot.freeze_status == ParameterFreezeStatus.FROZEN and slot.value is not None
        for slot in parameter_slots
        if slot.slot_name in REQUIRED_INFORMATION_PARAMETER_SLOTS
    )
    sparse_blocks = co_primary.sparse_episode_count > 0 or sparse_blocks_ordinary_conclusion(
        co_primary.aggregation_reliability_state
    )

    scorer_passes: bool | None = None
    if scorer_reliability is not None:
        errors.extend(scorer_reliability.errors)
        scorer_passes = scorer_reliability.passes_gate
        if scorer_reliability.gate_value is None or scorer_reliability.errors:
            scorer_passes = None
        elif scorer_passes is False:
            errors.append("scorer reliability below frozen gate")

    if sparse_blocks:
        disposition = StudyTerminalDisposition.BLOCKED_NON_ESTIMABLE
        rationale = "sparse or non-estimable evidence blocks product conclusion"
    elif co_primary.target_bearing_episode_count == 0:
        disposition = StudyTerminalDisposition.BLOCKED_NON_ESTIMABLE
        rationale = "no target-bearing evaluable episodes for conditional product effect"
    elif not all_frozen:
        disposition = StudyTerminalDisposition.BLOCKED_NON_ESTIMABLE
        rationale = "information parameter slots remain pending — no product conclusion"
    elif scorer_passes is False:
        disposition = StudyTerminalDisposition.BLOCKED_NON_ESTIMABLE
        rationale = "scorer reliability gate failed"
    elif scorer_passes is None:
        disposition = StudyTerminalDisposition.BLOCKED_NON_ESTIMABLE
        rationale = "scorer reliability gate not yet frozen/evaluable"
    else:
        disposition = StudyTerminalDisposition.BLOCKED_NON_ESTIMABLE
        rationale = (
            "co-primary aggregation complete; terminal disposition awaits G6+ frozen "
            "parameter values and authorized T10 evaluation"
        )

    return InformationGateEvaluationV1(
        parameter_slots_digest=slots_digest,
        all_required_slots_present=slot_validation.ok,
        all_slots_frozen=all_frozen,
        scorer_reliability_passes=scorer_passes,
        sparse_blocks_conclusion=sparse_blocks,
        disposition=disposition,
        rationale=rationale,
        errors=errors,
    )


def validate_analysis_lineage(
    *,
    expected_parent_digest: str,
    actual_parent_digest: str,
    label: str,
) -> NaturalisticValidation:
    errors: list[str] = []
    if expected_parent_digest != actual_parent_digest:
        errors.append(
            f"{label}: lineage digest mismatch "
            f"(expected {expected_parent_digest}, got {actual_parent_digest})"
        )
    return NaturalisticValidation(errors=errors)


def prove_one_score_per_episode_per_condition(
    within_episode_scores: list[WithinEpisodeScoreV1],
) -> NaturalisticValidation:
    """Target-rich episodes must not produce duplicate primary episode scores."""

    errors: list[str] = []
    seen: set[tuple[str, str]] = set()
    for score in within_episode_scores:
        key = (score.episode_id, score.condition.value)
        if key in seen:
            errors.append(
                f"duplicate within-episode score for episode={score.episode_id} "
                f"condition={score.condition.value}"
            )
        seen.add(key)
    return NaturalisticValidation(errors=errors)


@dataclass
class MissingnessBoundsV1:
    lower_bound: float
    upper_bound: float
    point_estimate: float | None
    boundable_episode_count: int
    complete_pair_count: int
    inconclusive: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "lower_bound": self.lower_bound,
            "upper_bound": self.upper_bound,
            "point_estimate": self.point_estimate,
            "boundable_episode_count": self.boundable_episode_count,
            "complete_pair_count": self.complete_pair_count,
            "inconclusive": self.inconclusive,
        }


@dataclass
class StructuredSyntheticResultV1:
    """G5C structured synthetic result — no authoritative scalar or product disposition."""

    classification: str
    opportunity_prevalence: float
    complete_pair_effect: float | None
    bounds: MissingnessBoundsV1 | None
    process_accounting: dict[str, Any]
    orthogonal_state: dict[str, Any]
    disposition: StudyTerminalDisposition
    reason_codes: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "classification": self.classification,
            "opportunity_prevalence": self.opportunity_prevalence,
            "complete_pair_effect": self.complete_pair_effect,
            "bounds": self.bounds.to_dict() if self.bounds else None,
            "process_accounting": self.process_accounting,
            "orthogonal_state": self.orthogonal_state,
            "disposition": self.disposition.value,
            "reason_codes": list(self.reason_codes),
        }


def compute_deterministic_bounds(
    *,
    complete_pair_effects: list[float],
    valid_missing_count: int,
    invalid_count: int,
    denominator_episode_count: int,
) -> MissingnessBoundsV1:
    """Deterministic worst/best-case bounds on [0,1] for valid missing only."""

    if invalid_count > 0:
        return MissingnessBoundsV1(
            lower_bound=0.0,
            upper_bound=0.0,
            point_estimate=None,
            boundable_episode_count=0,
            complete_pair_count=len(complete_pair_effects),
            inconclusive=True,
        )

    if denominator_episode_count <= 0:
        return MissingnessBoundsV1(
            lower_bound=0.0,
            upper_bound=0.0,
            point_estimate=None,
            boundable_episode_count=0,
            complete_pair_count=0,
            inconclusive=True,
        )

    complete = len(complete_pair_effects)
    missing = valid_missing_count
    total = denominator_episode_count
    if complete == 0 and missing == 0:
        return MissingnessBoundsV1(
            lower_bound=0.0,
            upper_bound=0.0,
            point_estimate=None,
            boundable_episode_count=0,
            complete_pair_count=0,
            inconclusive=True,
        )

    if complete > 0 and missing == 0:
        point = sum(complete_pair_effects) / complete
        return MissingnessBoundsV1(
            lower_bound=point,
            upper_bound=point,
            point_estimate=point,
            boundable_episode_count=0,
            complete_pair_count=complete,
            inconclusive=False,
        )

    # valid missing: worst/best on unit interval contribution per missing episode
    complete_sum = sum(complete_pair_effects)
    lower = (complete_sum + missing * (SCORE_BOUND_MIN - SCORE_BOUND_MAX)) / total
    upper = (complete_sum + missing * (SCORE_BOUND_MAX - SCORE_BOUND_MIN)) / total
    lower = max(SCORE_BOUND_MIN, min(SCORE_BOUND_MAX, lower))
    upper = max(SCORE_BOUND_MIN, min(SCORE_BOUND_MAX, upper))
    point = complete_sum / complete if complete else None
    inconclusive = upper - lower > 0.5
    return MissingnessBoundsV1(
        lower_bound=lower,
        upper_bound=upper,
        point_estimate=point,
        boundable_episode_count=missing,
        complete_pair_count=complete,
        inconclusive=inconclusive,
    )


def derive_orthogonal_disposition(
    *,
    protocol_validity: ProtocolValidityState,
    information_sufficiency: InformationSufficiencyState,
    missingness_comparability: MissingnessComparabilityState,
    scorer_integrity: ScorerIntegrityState,
    scorer_reliability: ScorerReliabilityDispositionState,
    apparent_positive_effect: bool = False,
) -> tuple[StudyTerminalDisposition, list[str], list[str]]:
    """Orthogonal precedence — G5C never emits product conclusions."""

    reason_codes: list[str] = []
    precedence_path: list[str] = []

    if protocol_validity == ProtocolValidityState.INVALID:
        precedence_path.append("protocol_invalidity")
        reason_codes.append(OutcomeReasonCode.PROTOCOL_INVALID.value)
        return StudyTerminalDisposition.INVALID, reason_codes, precedence_path

    if scorer_integrity == ScorerIntegrityState.INVALID_UNBLINDED:
        precedence_path.append("environment_or_scorer_integrity_invalidity")
        reason_codes.append(OutcomeReasonCode.SCORER_INTEGRITY_FAILURE.value)
        return StudyTerminalDisposition.INVALID, reason_codes, precedence_path

    if information_sufficiency == InformationSufficiencyState.INSUFFICIENT:
        precedence_path.append("insufficient_opportunity_or_information")
        reason_codes.append(OutcomeReasonCode.INCOMPLETE_PROSPECTIVE_MANIFEST.value)
        return StudyTerminalDisposition.BLOCKED_NON_ESTIMABLE, reason_codes, precedence_path

    if scorer_reliability == ScorerReliabilityDispositionState.BELOW_THRESHOLD:
        precedence_path.append("below_threshold_reliability_or_inconclusive_bounds")
        reason_codes.append(OutcomeReasonCode.SCORER_RELIABILITY_BELOW_THRESHOLD.value)
        return StudyTerminalDisposition.BLOCKED_NON_ESTIMABLE, reason_codes, precedence_path

    if missingness_comparability == MissingnessComparabilityState.INCONCLUSIVE_BOUNDS:
        precedence_path.append("below_threshold_reliability_or_inconclusive_bounds")
        reason_codes.append(OutcomeReasonCode.VALID_MISSING_OUTCOME.value)
        return StudyTerminalDisposition.BLOCKED_NON_ESTIMABLE, reason_codes, precedence_path

    if apparent_positive_effect:
        precedence_path.append("effect_interpretation_deferred_to_later_study")
        reason_codes.append("methodology_validation_not_product_evidence")
        return StudyTerminalDisposition.BLOCKED_NON_ESTIMABLE, reason_codes, precedence_path

    precedence_path.append("effect_interpretation_deferred_to_later_study")
    return StudyTerminalDisposition.BLOCKED_NON_ESTIMABLE, reason_codes, precedence_path


def build_structured_synthetic_result(
    *,
    co_primary: CoPrimaryAggregationV1,
    bounds: MissingnessBoundsV1,
    process_accounting: dict[str, Any],
    apparent_positive_effect: bool,
) -> StructuredSyntheticResultV1:
    missingness = (
        MissingnessComparabilityState.COMPLETE
        if bounds.point_estimate is not None and not bounds.inconclusive
        else MissingnessComparabilityState.BOUNDED
        if not bounds.inconclusive
        else MissingnessComparabilityState.INCONCLUSIVE_BOUNDS
    )
    info_suff = (
        InformationSufficiencyState.INSUFFICIENT
        if co_primary.target_bearing_episode_count == 0
        else InformationSufficiencyState.SUFFICIENT
    )
    disposition, reason_codes, precedence_path = derive_orthogonal_disposition(
        protocol_validity=ProtocolValidityState.VALID,
        information_sufficiency=info_suff,
        missingness_comparability=missingness,
        scorer_integrity=ScorerIntegrityState.VALID,
        scorer_reliability=ScorerReliabilityDispositionState.NOT_APPLICABLE,
        apparent_positive_effect=apparent_positive_effect,
    )
    orthogonal = {
        "protocol_validity": ProtocolValidityState.VALID.value,
        "information_sufficiency": info_suff.value,
        "missingness_comparability": missingness.value,
        "scorer_integrity": ScorerIntegrityState.VALID.value,
        "scorer_reliability": ScorerReliabilityDispositionState.NOT_APPLICABLE.value,
        "precedence_path": precedence_path,
    }
    return StructuredSyntheticResultV1(
        classification="methodology_validation_not_product_evidence",
        opportunity_prevalence=co_primary.opportunity_prevalence,
        complete_pair_effect=bounds.point_estimate,
        bounds=bounds,
        process_accounting=process_accounting,
        orthogonal_state=orthogonal,
        disposition=disposition,
        reason_codes=reason_codes,
    )


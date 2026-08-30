"""G4 hermetic synthetic paired fixtures for analysis/statistical machinery tests."""

from __future__ import annotations

from eval_naturalistic.analysis import (
    EpisodeRegistryViewV1,
    ScorerSubmissionV1,
    WithinEpisodeScoreV1,
)
from eval_naturalistic.base import ArtifactHeaderV1
from eval_naturalistic.contracts import ParameterSlotV1, TargetScoreV1
from eval_naturalistic.enums import (
    EpisodeRegistryStatus,
    ParameterFreezeStatus,
    ReliabilityState,
    TrialCondition,
)
from eval_naturalistic.fixtures import (
    make_synthetic_episode,
    make_synthetic_evidence,
    make_synthetic_frame,
    make_synthetic_registry,
)

G4_SYNTHETIC_FIXTURE_SEED = 20260830

_SCORE_HEADER = ArtifactHeaderV1(
    artifact_id="pending",
    schema_version="convmem/naturalistic/target-score-v1",
    parent_artifact_id=None,
    parent_digest=None,
    created_at="2026-08-30T00:00:00Z",
    seal_time=None,
    responsible_role="scorer",
    content_digest=None,
    sealed=False,
)


def make_pending_parameter_slots() -> list[ParameterSlotV1]:
    """Required T0 information slots — pending only, no live numerical values."""

    return [
        ParameterSlotV1(
            slot_name=name,
            freeze_status=ParameterFreezeStatus.PENDING,
            construct_defining=True,
        )
        for name in sorted(
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
    ]


def make_synthetic_target_score(
    *,
    target_id: str,
    trial_id: str,
    normalized_score: float | None,
    reliability_state: ReliabilityState = ReliabilityState.RELIABILITY_ACCEPTABLE,
) -> TargetScoreV1:
    return TargetScoreV1(
        header=_SCORE_HEADER,
        target_id=target_id,
        trial_id=trial_id,
        normalized_score=normalized_score,
        reliability_state=reliability_state,
    )


def make_paired_episode_scores(
    *,
    episode_id: str,
    c0_score: float,
    c1_score: float,
    target_count: int = 1,
) -> list[WithinEpisodeScoreV1]:
    return [
        WithinEpisodeScoreV1(
            episode_id=episode_id,
            condition=TrialCondition.C0,
            normalized_score=c0_score,
            reliability_state=ReliabilityState.RELIABILITY_ACCEPTABLE,
            target_count=target_count,
        ),
        WithinEpisodeScoreV1(
            episode_id=episode_id,
            condition=TrialCondition.C1,
            normalized_score=c1_score,
            reliability_state=ReliabilityState.RELIABILITY_ACCEPTABLE,
            target_count=target_count,
        ),
    ]


def make_c1_better_than_c0_fixture() -> tuple[list[EpisodeRegistryViewV1], list[WithinEpisodeScoreV1]]:
    episodes = [
        EpisodeRegistryViewV1("ep-c1-win-001", EpisodeRegistryStatus.TARGETS_PRESENT),
        EpisodeRegistryViewV1("ep-c1-win-002", EpisodeRegistryStatus.TARGETS_PRESENT),
    ]
    scores: list[WithinEpisodeScoreV1] = []
    scores.extend(make_paired_episode_scores(episode_id="ep-c1-win-001", c0_score=0.40, c1_score=0.70))
    scores.extend(make_paired_episode_scores(episode_id="ep-c1-win-002", c0_score=0.35, c1_score=0.65))
    return episodes, scores


def make_c0_better_than_c1_fixture() -> tuple[list[EpisodeRegistryViewV1], list[WithinEpisodeScoreV1]]:
    episodes = [
        EpisodeRegistryViewV1("ep-c0-win-001", EpisodeRegistryStatus.TARGETS_PRESENT),
    ]
    scores = make_paired_episode_scores(episode_id="ep-c0-win-001", c0_score=0.80, c1_score=0.55)
    return episodes, scores


def make_equivalent_null_like_fixture() -> tuple[list[EpisodeRegistryViewV1], list[WithinEpisodeScoreV1]]:
    """Synthetic near-zero paired effect — not a live product null declaration."""

    episodes = [
        EpisodeRegistryViewV1("ep-equiv-001", EpisodeRegistryStatus.TARGETS_PRESENT),
        EpisodeRegistryViewV1("ep-equiv-002", EpisodeRegistryStatus.TARGETS_PRESENT),
    ]
    scores: list[WithinEpisodeScoreV1] = []
    scores.extend(make_paired_episode_scores(episode_id="ep-equiv-001", c0_score=0.50, c1_score=0.51))
    scores.extend(make_paired_episode_scores(episode_id="ep-equiv-002", c0_score=0.48, c1_score=0.49))
    return episodes, scores


def make_zero_target_episodes_fixture() -> tuple[list[EpisodeRegistryViewV1], list[WithinEpisodeScoreV1]]:
    episodes = [
        EpisodeRegistryViewV1("ep-zero-001", EpisodeRegistryStatus.ZERO_ELIGIBLE_TARGETS),
        EpisodeRegistryViewV1("ep-zero-002", EpisodeRegistryStatus.ZERO_ELIGIBLE_TARGETS),
    ]
    return episodes, []


def make_mixed_zero_and_target_fixture() -> tuple[list[EpisodeRegistryViewV1], list[WithinEpisodeScoreV1]]:
    episodes = [
        EpisodeRegistryViewV1("ep-mix-zero", EpisodeRegistryStatus.ZERO_ELIGIBLE_TARGETS),
        EpisodeRegistryViewV1("ep-mix-target", EpisodeRegistryStatus.TARGETS_PRESENT),
        EpisodeRegistryViewV1("ep-mix-zero-2", EpisodeRegistryStatus.ZERO_ELIGIBLE_TARGETS),
    ]
    scores = make_paired_episode_scores(episode_id="ep-mix-target", c0_score=0.45, c1_score=0.60)
    return episodes, scores


def make_sparse_non_estimable_fixture() -> tuple[list[EpisodeRegistryViewV1], list[WithinEpisodeScoreV1]]:
    episodes = [
        EpisodeRegistryViewV1("ep-sparse-001", EpisodeRegistryStatus.TARGETS_PRESENT),
    ]
    scores = [
        WithinEpisodeScoreV1(
            episode_id="ep-sparse-001",
            condition=TrialCondition.C0,
            normalized_score=0.42,
            reliability_state=ReliabilityState.RELIABILITY_SPARSE,
            target_count=1,
        ),
        WithinEpisodeScoreV1(
            episode_id="ep-sparse-001",
            condition=TrialCondition.C1,
            normalized_score=0.58,
            reliability_state=ReliabilityState.RELIABILITY_ACCEPTABLE,
            target_count=1,
        ),
    ]
    return episodes, scores


def make_scorer_disagreement_fixture() -> tuple[list[ScorerSubmissionV1], list[ScorerSubmissionV1]]:
    primary = [
        ScorerSubmissionV1("scorer-a", "ep-rel-001", TrialCondition.C0, 0.80, ReliabilityState.RELIABILITY_ACCEPTABLE),
        ScorerSubmissionV1("scorer-a", "ep-rel-001", TrialCondition.C1, 0.85, ReliabilityState.RELIABILITY_ACCEPTABLE),
        ScorerSubmissionV1("scorer-a", "ep-rel-002", TrialCondition.C0, 0.40, ReliabilityState.RELIABILITY_ACCEPTABLE),
        ScorerSubmissionV1("scorer-a", "ep-rel-002", TrialCondition.C1, 0.45, ReliabilityState.RELIABILITY_ACCEPTABLE),
    ]
    secondary = [
        ScorerSubmissionV1("scorer-b", "ep-rel-001", TrialCondition.C0, 0.30, ReliabilityState.RELIABILITY_ACCEPTABLE),
        ScorerSubmissionV1("scorer-b", "ep-rel-001", TrialCondition.C1, 0.35, ReliabilityState.RELIABILITY_ACCEPTABLE),
        ScorerSubmissionV1("scorer-b", "ep-rel-002", TrialCondition.C0, 0.42, ReliabilityState.RELIABILITY_ACCEPTABLE),
        ScorerSubmissionV1("scorer-b", "ep-rel-002", TrialCondition.C1, 0.44, ReliabilityState.RELIABILITY_ACCEPTABLE),
    ]
    return primary, secondary


def make_scorer_agreement_fixture() -> tuple[list[ScorerSubmissionV1], list[ScorerSubmissionV1]]:
    primary = [
        ScorerSubmissionV1("scorer-a", "ep-rel-ok", TrialCondition.C0, 0.60, ReliabilityState.RELIABILITY_ACCEPTABLE),
        ScorerSubmissionV1("scorer-a", "ep-rel-ok", TrialCondition.C1, 0.70, ReliabilityState.RELIABILITY_ACCEPTABLE),
    ]
    secondary = [
        ScorerSubmissionV1("scorer-b", "ep-rel-ok", TrialCondition.C0, 0.61, ReliabilityState.RELIABILITY_ACCEPTABLE),
        ScorerSubmissionV1("scorer-b", "ep-rel-ok", TrialCondition.C1, 0.71, ReliabilityState.RELIABILITY_ACCEPTABLE),
    ]
    return primary, secondary


def make_target_rich_episode_target_scores(
    *,
    episode_id: str = "ep-rich-001",
    c0_scores: list[float],
    c1_scores: list[float],
) -> tuple[list[TargetScoreV1], list[TargetScoreV1]]:
    c0 = [
        make_synthetic_target_score(
            target_id=f"tgt-{episode_id}-c0-{idx}",
            trial_id=f"trial-{episode_id}-c0-{idx}",
            normalized_score=score,
        )
        for idx, score in enumerate(c0_scores)
    ]
    c1 = [
        make_synthetic_target_score(
            target_id=f"tgt-{episode_id}-c1-{idx}",
            trial_id=f"trial-{episode_id}-c1-{idx}",
            normalized_score=score,
        )
        for idx, score in enumerate(c1_scores)
    ]
    return c0, c1


def make_sealed_registry_chain_for_lineage():
    """Minimal G1–G3 chain for lineage/digest binding tests."""

    frame = make_synthetic_frame()
    episode = make_synthetic_episode(frame=frame, episode_id="ep-lineage-001")
    evidence = make_synthetic_evidence(episode=episode)
    registry = make_synthetic_registry(evidence=evidence)
    return frame, episode, evidence, registry

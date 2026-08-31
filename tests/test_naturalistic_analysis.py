"""Hermetic G4 tests for naturalistic analysis/statistical machinery."""

# pylint: disable=wrong-import-position

from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from eval_naturalistic.analysis import (
    REQUIRED_INFORMATION_PARAMETER_SLOTS,
    SCORE_BOUND_MAX,
    SCORE_BOUND_MIN,
    aggregate_targets_to_within_episode_score,
    compute_co_primary_aggregation,
    evaluate_information_gate_readiness,
    prove_one_score_per_episode_per_condition,
    record_scorer_reliability,
    reject_post_result_parameter_mutation,
    sparse_blocks_ordinary_conclusion,
    validate_analysis_lineage,
    validate_bounded_normalized_score,
    validate_required_parameter_slots,
)
from eval_naturalistic.analysis_fixtures import (
    G4_SYNTHETIC_FIXTURE_SEED,
    make_c0_better_than_c1_fixture,
    make_c1_better_than_c0_fixture,
    make_equivalent_null_like_fixture,
    make_mixed_zero_and_target_fixture,
    make_pending_parameter_slots,
    make_post_result_threshold_fill_attempt,
    make_scorer_agreement_fixture,
    make_scorer_disagreement_fixture,
    make_sealed_registry_chain_for_lineage,
    make_sparse_non_estimable_fixture,
    make_target_rich_episode_target_scores,
    make_zero_target_episodes_fixture,
)
from eval_naturalistic.contracts import ParameterSlotV1
from eval_naturalistic.digest import artifact_content_digest
from eval_naturalistic.enums import (
    EpisodeRegistryStatus,
    ParameterFreezeStatus,
    ReliabilityState,
    StudyTerminalDisposition,
    TrialCondition,
)


class BoundedScoreContractTests(unittest.TestCase):
    def test_valid_scores_accepted(self):
        for score in (0.0, 0.5, 1.0):
            result = validate_bounded_normalized_score(score)
            self.assertTrue(result.ok, result.errors)

    def test_out_of_bounds_rejected(self):
        for score in (-0.01, 1.01, 2.0):
            result = validate_bounded_normalized_score(score)
            self.assertFalse(result.ok)

    def test_non_finite_and_boolean_scores_rejected(self):
        for score in (float("nan"), float("inf"), -float("inf"), True, False):
            result = validate_bounded_normalized_score(score)
            self.assertFalse(result.ok, repr(score))

    def test_none_allowed_for_non_scored_states(self):
        self.assertTrue(validate_bounded_normalized_score(None).ok)


class CoPrimaryAggregationTests(unittest.TestCase):
    def _aggregate(self, episodes, scores):
        return compute_co_primary_aggregation(
            episodes,
            scores,
            lineage_inputs={"fixture_seed": G4_SYNTHETIC_FIXTURE_SEED, "scores": len(scores)},
        )

    def test_c1_better_than_c0(self):
        episodes, scores = make_c1_better_than_c0_fixture()
        result = self._aggregate(episodes, scores)
        self.assertTrue(result.ok, result.errors)
        assert result.co_primary is not None
        self.assertGreater(result.co_primary.conditional_mean_effect or 0, 0)
        self.assertEqual(result.co_primary.conditional_episode_count, 2)

    def test_c0_better_than_c1(self):
        episodes, scores = make_c0_better_than_c1_fixture()
        result = self._aggregate(episodes, scores)
        self.assertTrue(result.ok, result.errors)
        assert result.co_primary is not None
        self.assertLess(result.co_primary.conditional_mean_effect or 0, 0)

    def test_equivalent_null_like_without_product_null(self):
        episodes, scores = make_equivalent_null_like_fixture()
        result = self._aggregate(episodes, scores)
        self.assertTrue(result.ok, result.errors)
        assert result.co_primary is not None
        effect = result.co_primary.conditional_mean_effect
        assert effect is not None
        self.assertAlmostEqual(effect, 0.01, places=2)
        gate = evaluate_information_gate_readiness(
            make_pending_parameter_slots(),
            result.co_primary,
            None,
        )
        self.assertEqual(gate.disposition, StudyTerminalDisposition.BLOCKED_NON_ESTIMABLE)

    def test_zero_target_episodes_in_opportunity_denominator_only(self):
        episodes, scores = make_zero_target_episodes_fixture()
        result = self._aggregate(episodes, scores)
        self.assertTrue(result.ok, result.errors)
        assert result.co_primary is not None
        self.assertEqual(result.co_primary.opportunity_prevalence, 0.0)
        self.assertEqual(result.co_primary.zero_target_episode_count, 2)
        self.assertIsNone(result.co_primary.conditional_mean_effect)
        self.assertEqual(result.co_primary.conditional_episode_count, 0)

    def test_mixed_zero_and_target_episodes(self):
        episodes, scores = make_mixed_zero_and_target_fixture()
        result = self._aggregate(episodes, scores)
        self.assertTrue(result.ok, result.errors)
        assert result.co_primary is not None
        self.assertAlmostEqual(result.co_primary.opportunity_prevalence, 1 / 3)
        self.assertAlmostEqual(result.co_primary.opportunity_density, 1 / 3)
        self.assertEqual(result.co_primary.zero_target_episode_count, 2)
        self.assertEqual(result.co_primary.conditional_episode_count, 1)
        self.assertAlmostEqual(result.co_primary.conditional_mean_effect or 0, 0.15, places=2)

    def test_sparse_episode_blocks_conditional_numerator(self):
        episodes, scores = make_sparse_non_estimable_fixture()
        result = self._aggregate(episodes, scores)
        assert result.co_primary is not None
        self.assertEqual(result.co_primary.sparse_episode_count, 1)
        self.assertEqual(result.co_primary.conditional_episode_count, 0)
        self.assertIsNone(result.co_primary.conditional_mean_effect)
        self.assertEqual(
            result.co_primary.aggregation_reliability_state,
            ReliabilityState.RELIABILITY_NON_ESTIMABLE,
        )

    def test_zero_target_does_not_contribute_zero_treatment_effect(self):
        episodes, scores = make_mixed_zero_and_target_fixture()
        result = self._aggregate(episodes, scores)
        assert result.co_primary is not None
        zero_outcomes = [
            outcome
            for outcome in result.episode_outcomes
            if outcome.registry_status == EpisodeRegistryStatus.ZERO_ELIGIBLE_TARGETS
        ]
        self.assertEqual(len(zero_outcomes), 2)
        for outcome in zero_outcomes:
            self.assertIsNone(outcome.conditional_effect)
            self.assertEqual(outcome.opportunity_component, 0.0)
            self.assertEqual(
                outcome.reliability_state,
                ReliabilityState.RELIABILITY_NOT_APPLICABLE,
            )

    def test_target_present_but_not_evaluable_counts_as_opportunity_only(self):
        from eval_naturalistic.analysis import EpisodeRegistryViewV1

        episodes = [
            EpisodeRegistryViewV1(
                "ep-not-evaluable",
                EpisodeRegistryStatus.TARGETS_PRESENT_BUT_NOT_EVALUABLE,
                3,
            )
        ]
        result = self._aggregate(episodes, [])
        self.assertTrue(result.ok, result.errors)
        assert result.co_primary is not None
        self.assertEqual(result.co_primary.opportunity_prevalence, 1.0)
        self.assertEqual(result.co_primary.opportunity_density, 3.0)
        self.assertEqual(result.co_primary.target_bearing_episode_count, 1)
        self.assertEqual(result.co_primary.target_bearing_evaluable_episode_count, 0)
        self.assertEqual(result.co_primary.target_bearing_not_evaluable_episode_count, 1)
        self.assertIsNone(result.co_primary.conditional_mean_effect)

    def test_duplicate_registry_episode_fails_closed(self):
        from eval_naturalistic.analysis import EpisodeRegistryViewV1

        episodes, scores = make_c0_better_than_c1_fixture()
        episodes.append(
            EpisodeRegistryViewV1("ep-c0-win-001", EpisodeRegistryStatus.TARGETS_PRESENT, 1)
        )
        result = self._aggregate(episodes, scores)
        self.assertFalse(result.ok)
        self.assertIsNone(result.co_primary)
        self.assertTrue(any("duplicate episode registry" in error for error in result.errors))

    def test_duplicate_condition_score_fails_closed(self):
        episodes, scores = make_c0_better_than_c1_fixture()
        scores.append(copy.deepcopy(scores[0]))
        scores[-1].normalized_score = 0.10
        result = self._aggregate(episodes, scores)
        self.assertFalse(result.ok)
        self.assertIsNone(result.co_primary)
        self.assertTrue(any("duplicate within-episode score" in error for error in result.errors))

    def test_orphan_score_fails_closed(self):
        episodes, scores = make_c0_better_than_c1_fixture()
        orphan = copy.deepcopy(scores[0])
        orphan.episode_id = "ep-unknown"
        scores.append(orphan)
        result = self._aggregate(episodes, scores)
        self.assertFalse(result.ok)
        self.assertIsNone(result.co_primary)
        self.assertTrue(any("unknown episode" in error for error in result.errors))


class TargetRichEpisodeWeightingTests(unittest.TestCase):
    def test_many_targets_produce_one_episode_score(self):
        c0_targets, c1_targets = make_target_rich_episode_target_scores(
            c0_scores=[0.40, 0.60, 0.80],
            c1_scores=[0.50, 0.70, 0.90],
        )
        c0_episode = aggregate_targets_to_within_episode_score(
            c0_targets,
            episode_id="ep-rich-001",
            condition=TrialCondition.C0,
        )
        c1_episode = aggregate_targets_to_within_episode_score(
            c1_targets,
            episode_id="ep-rich-001",
            condition=TrialCondition.C1,
        )
        self.assertEqual(c0_episode.target_count, 3)
        self.assertAlmostEqual(c0_episode.normalized_score or 0, 0.60, places=2)
        self.assertAlmostEqual(c1_episode.normalized_score or 0, 0.70, places=2)

        proof = prove_one_score_per_episode_per_condition([c0_episode, c1_episode])
        self.assertTrue(proof.ok, proof.errors)

        from eval_naturalistic.analysis import EpisodeRegistryViewV1

        result = compute_co_primary_aggregation(
            [EpisodeRegistryViewV1("ep-rich-001", EpisodeRegistryStatus.TARGETS_PRESENT, 3)],
            [c0_episode, c1_episode],
            lineage_inputs={"episode": "ep-rich-001"},
        )
        assert result.co_primary is not None
        self.assertEqual(result.co_primary.conditional_episode_count, 1)
        self.assertAlmostEqual(result.co_primary.conditional_mean_effect or 0, 0.10, places=2)

    def test_duplicate_target_rows_are_non_estimable(self):
        c0_targets, _ = make_target_rich_episode_target_scores(
            c0_scores=[0.40, 0.60],
            c1_scores=[0.50, 0.70],
        )
        c0_targets[1].target_id = c0_targets[0].target_id
        score = aggregate_targets_to_within_episode_score(
            c0_targets,
            episode_id="ep-rich-001",
            condition=TrialCondition.C0,
        )
        self.assertIsNone(score.normalized_score)
        self.assertEqual(score.reliability_state, ReliabilityState.RELIABILITY_NON_ESTIMABLE)
        self.assertTrue(any("duplicate target score" in error for error in score.validation_errors))

    def test_invalid_target_score_is_non_estimable(self):
        c0_targets, _ = make_target_rich_episode_target_scores(
            c0_scores=[float("nan")],
            c1_scores=[0.50],
        )
        score = aggregate_targets_to_within_episode_score(
            c0_targets,
            episode_id="ep-rich-001",
            condition=TrialCondition.C0,
        )
        self.assertIsNone(score.normalized_score)
        self.assertTrue(score.validation_errors)


class ScorerReliabilityTests(unittest.TestCase):
    def test_disagreement_without_frozen_gate(self):
        primary, secondary = make_scorer_disagreement_fixture()
        record = record_scorer_reliability(
            primary, secondary, gate_value=None, agreement_tolerance=0.05
        )
        self.assertIsNone(record.passes_gate)
        self.assertGreater(record.disagreement_count, 0)

    def test_disagreement_below_frozen_gate_fails_closed(self):
        primary, secondary = make_scorer_disagreement_fixture()
        record = record_scorer_reliability(
            primary, secondary, gate_value="0.95", agreement_tolerance=0.05
        )
        self.assertFalse(record.passes_gate)

    def test_agreement_with_frozen_gate_passes(self):
        primary, secondary = make_scorer_agreement_fixture()
        record = record_scorer_reliability(
            primary, secondary, gate_value="0.50", agreement_tolerance=0.05
        )
        self.assertTrue(record.passes_gate)

    def test_same_scorer_identity_cannot_pass_independence_gate(self):
        primary, secondary = make_scorer_agreement_fixture()
        for submission in secondary:
            submission.scorer_id = "scorer-a"
        record = record_scorer_reliability(
            primary, secondary, gate_value="0.50", agreement_tolerance=0.05
        )
        self.assertIsNone(record.passes_gate)
        self.assertTrue(any("independent" in error for error in record.errors))

    def test_missing_pair_counts_against_observed_agreement(self):
        primary, secondary = make_scorer_agreement_fixture()
        secondary.pop()
        record = record_scorer_reliability(
            primary, secondary, gate_value="0.75", agreement_tolerance=0.05
        )
        self.assertEqual(record.observed_statistic, 0.5)
        self.assertIsNone(record.passes_gate)
        self.assertTrue(any("missing secondary" in error for error in record.errors))


class ParameterSlotTests(unittest.TestCase):
    def test_required_slots_present(self):
        slots = make_pending_parameter_slots()
        result = validate_required_parameter_slots(slots)
        self.assertTrue(result.ok, result.errors)
        self.assertEqual(
            {slot.slot_name for slot in slots},
            REQUIRED_INFORMATION_PARAMETER_SLOTS,
        )

    def test_missing_required_slot_rejected(self):
        slots = make_pending_parameter_slots()[:-1]
        result = validate_required_parameter_slots(slots)
        self.assertFalse(result.ok)

    def test_duplicate_required_slot_rejected(self):
        slots = make_pending_parameter_slots()
        slots.append(copy.deepcopy(slots[0]))
        result = validate_required_parameter_slots(slots)
        self.assertFalse(result.ok)
        self.assertTrue(any("duplicate information parameter" in error for error in result.errors))

    def test_post_result_fill_rejected(self):
        before, after = make_post_result_threshold_fill_attempt()
        result = reject_post_result_parameter_mutation(before, after)
        self.assertFalse(result.ok)
        self.assertTrue(any("post-result fill" in err for err in result.errors))

    def test_post_result_frozen_mutation_rejected(self):
        before = [
            ParameterSlotV1(
                slot_name="meaningful_advantage",
                freeze_status=ParameterFreezeStatus.FROZEN,
                value="0.10",
                construct_defining=True,
            )
        ]
        after = [
            ParameterSlotV1(
                slot_name="meaningful_advantage",
                freeze_status=ParameterFreezeStatus.FROZEN,
                value="0.20",
                construct_defining=True,
            )
        ]
        result = reject_post_result_parameter_mutation(before, after)
        self.assertFalse(result.ok)


class InformationGateTests(unittest.TestCase):
    def test_pending_slots_block_product_conclusion(self):
        episodes, scores = make_c1_better_than_c0_fixture()
        agg = compute_co_primary_aggregation(
            episodes,
            scores,
            lineage_inputs={"seed": G4_SYNTHETIC_FIXTURE_SEED},
        )
        assert agg.co_primary is not None
        gate = evaluate_information_gate_readiness(
            make_pending_parameter_slots(),
            agg.co_primary,
            None,
        )
        self.assertEqual(gate.disposition, StudyTerminalDisposition.BLOCKED_NON_ESTIMABLE)
        self.assertFalse(gate.all_slots_frozen)

    def test_sparse_blocks_product_conclusion(self):
        episodes, scores = make_sparse_non_estimable_fixture()
        agg = compute_co_primary_aggregation(
            episodes,
            scores,
            lineage_inputs={"seed": G4_SYNTHETIC_FIXTURE_SEED},
        )
        assert agg.co_primary is not None
        gate = evaluate_information_gate_readiness(
            make_pending_parameter_slots(),
            agg.co_primary,
            None,
        )
        self.assertTrue(gate.sparse_blocks_conclusion)
        self.assertEqual(gate.disposition, StudyTerminalDisposition.BLOCKED_NON_ESTIMABLE)

    def test_low_scorer_reliability_blocks_conclusion(self):
        episodes, scores = make_c1_better_than_c0_fixture()
        agg = compute_co_primary_aggregation(
            episodes,
            scores,
            lineage_inputs={"seed": G4_SYNTHETIC_FIXTURE_SEED},
        )
        assert agg.co_primary is not None
        primary, secondary = make_scorer_disagreement_fixture()
        record = record_scorer_reliability(
            primary, secondary, gate_value="0.95", agreement_tolerance=0.05
        )
        gate = evaluate_information_gate_readiness(
            make_pending_parameter_slots(),
            agg.co_primary,
            record,
        )
        self.assertFalse(record.passes_gate)
        self.assertEqual(gate.disposition, StudyTerminalDisposition.BLOCKED_NON_ESTIMABLE)


class SparseStateDistinctionTests(unittest.TestCase):
    def test_sparse_not_null_or_confidence(self):
        self.assertTrue(sparse_blocks_ordinary_conclusion(ReliabilityState.RELIABILITY_SPARSE))
        self.assertTrue(sparse_blocks_ordinary_conclusion(ReliabilityState.RELIABILITY_NON_ESTIMABLE))
        self.assertFalse(sparse_blocks_ordinary_conclusion(ReliabilityState.RELIABILITY_ACCEPTABLE))
        self.assertNotEqual(
            ReliabilityState.RELIABILITY_SPARSE.value,
            StudyTerminalDisposition.COMPLETE_NULL_EQUIVALENT.value,
        )


class LineageFailClosedTests(unittest.TestCase):
    def test_lineage_digest_mismatch_rejected(self):
        frame, _, _, registry = make_sealed_registry_chain_for_lineage()
        expected = artifact_content_digest(
            {
                "frame": frame.header.content_digest,
                "registry": registry.header.content_digest,
            }
        )
        result = validate_analysis_lineage(
            expected_parent_digest=expected,
            actual_parent_digest="0" * 64,
            label="EpisodeAggregationReport",
        )
        self.assertFalse(result.ok)


class SyntheticOnlyGuardTests(unittest.TestCase):
    def test_fixtures_use_synthetic_paths_only(self):
        _, _, evidence, _ = make_sealed_registry_chain_for_lineage()
        for source in evidence.sources:
            self.assertTrue(source.locator.startswith("synthetic://"))

    def test_no_live_threshold_constants_in_module(self):
        import eval_naturalistic.analysis as analysis_mod

        forbidden = ("MEANINGFUL_ADVANTAGE", "EQUIVALENCE_MARGIN", "DEFAULT_GATE")
        for name in forbidden:
            self.assertFalse(hasattr(analysis_mod, name), f"unexpected live constant {name}")

    def test_score_bounds_are_contract_not_live_values(self):
        self.assertEqual(SCORE_BOUND_MIN, 0.0)
        self.assertEqual(SCORE_BOUND_MAX, 1.0)


if __name__ == "__main__":
    unittest.main()

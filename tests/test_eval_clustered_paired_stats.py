"""Tests for the frozen domain/cluster inference contract."""

from __future__ import annotations

import pytest

from eval_corpus.paired_stats import (
    label_challenger,
    paired_cluster_bootstrap_ci,
    paired_cluster_sign_flip,
    paired_outcomes,
)


def _clustered_outcomes():
    return paired_outcomes(
        [0, 0, 0, 0, 0],
        [1, 1, 1, -1, -1],
        queries=[f"q-{i}" for i in range(5)],
        domains=["a", "a", "a", "b", "b"],
        source_groups=["a-1", "a-1", "a-2", "b-1", "b-2"],
        tie_epsilon=0.0,
    )


def test_cluster_bootstrap_uses_equal_domain_query_weighting():
    result = paired_cluster_bootstrap_ci(
        _clustered_outcomes(),
        seed=20260804,
        resamples=100,
        confidence_level=0.95,
    )
    # Domain A mean is 1; domain B mean is -1. The point estimand is 0,
    # despite domain A having three queries and domain B only two.
    assert result["mean_delta"] == 0.0
    assert result["algorithm"] == "domain_stratified_cluster_percentile_v1"
    assert result["resampling_unit"] == "source_group_within_domain"


def test_cluster_sign_flip_is_seeded_and_reports_group_count():
    result_a = paired_cluster_sign_flip(_clustered_outcomes(), seed=7, draws=200)
    result_b = paired_cluster_sign_flip(_clustered_outcomes(), seed=7, draws=200)
    assert result_a == result_b
    assert result_a["group_count"] == 4
    assert result_a["algorithm"] == "domain_stratified_cluster_sign_flip_v1"


def test_cluster_label_counts_non_tied_source_groups():
    outcomes = _clustered_outcomes()
    report = label_challenger(
        outcomes=outcomes,
        significance_alpha=0.05,
        confidence_level=0.95,
        bootstrap_seed=1,
        bootstrap_resamples=100,
        minimum_non_tied_pairs=20,
        permutation_seed=2,
        permutation_draws=100,
        minimum_non_tied_groups=4,
    )
    assert report["effective_sample_unit"] == "source_group"
    assert report["effective_sample_size"] == 4
    assert report["minimum_non_tied_groups"] == 4


def test_cluster_inference_rejects_cross_domain_source_group():
    outcomes = paired_outcomes(
        [0, 0],
        [1, 1],
        domains=["a", "b"],
        source_groups=["shared", "shared"],
    )
    with pytest.raises(ValueError, match="spans domains"):
        paired_cluster_bootstrap_ci(
            outcomes,
            seed=1,
            resamples=10,
            confidence_level=0.95,
        )

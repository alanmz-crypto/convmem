"""Paired uncertainty: sign test + seeded paired bootstrap (Gate 2 evidence)."""

from __future__ import annotations

import math
import random
from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any


@dataclass
class PairedOutcome:
    query: str
    baseline: float
    challenger: float
    delta: float
    label: str  # win | loss | tie
    domain: str = ""
    source_group: str = ""


def classify_pair(
    baseline: float,
    challenger: float,
    *,
    tie_epsilon: float,
) -> str:
    delta = challenger - baseline
    if abs(delta) <= tie_epsilon:
        return "tie"
    return "win" if delta > 0 else "loss"


def paired_outcomes(
    baseline_scores: Sequence[float],
    challenger_scores: Sequence[float],
    *,
    queries: Sequence[str] | None = None,
    tie_epsilon: float = 0.0,
    domains: Sequence[str] | None = None,
    source_groups: Sequence[str] | None = None,
) -> list[PairedOutcome]:
    if len(baseline_scores) != len(challenger_scores):
        raise ValueError("paired score lengths differ")
    if domains is not None and len(domains) != len(baseline_scores):
        raise ValueError("paired domain lengths differ")
    if source_groups is not None and len(source_groups) != len(baseline_scores):
        raise ValueError("paired source-group lengths differ")
    out: list[PairedOutcome] = []
    for i, (b, c) in enumerate(zip(baseline_scores, challenger_scores)):
        label = classify_pair(float(b), float(c), tie_epsilon=tie_epsilon)
        q = str(queries[i]) if queries is not None else f"q{i}"
        out.append(
            PairedOutcome(
                query=q,
                baseline=float(b),
                challenger=float(c),
                delta=float(c) - float(b),
                label=label,
                domain=str(domains[i]) if domains is not None else "",
                source_group=(
                    str(source_groups[i]) if source_groups is not None else ""
                ),
            )
        )
    return out


def _binom_two_sided_p(wins: int, n: int) -> float:
    """Exact two-sided binomial sign-test p-value under p=0.5."""
    if n <= 0:
        return 1.0
    # Sum probabilities of outcomes as or more extreme than observed.
    # Two-sided: min(1, 2 * min(cdf, 1-cdf+pmf tail)).
    from math import comb

    observed = wins
    # Probability of k wins in n trials
    def pmf(k: int) -> float:
        return comb(n, k) / (2**n)

    # Two-sided exact: sum pmf for all k with pmf(k) <= pmf(observed)
    # Standard approach: 2 * sum_{k=0}^{min(w,n-w)} pmf(k) clipped to 1
    lo = min(observed, n - observed)
    p = sum(pmf(k) for k in range(lo + 1)) * 2.0
    return min(1.0, p)


def sign_test(outcomes: Sequence[PairedOutcome]) -> dict[str, Any]:
    non_ties = [o for o in outcomes if o.label != "tie"]
    wins = sum(1 for o in non_ties if o.label == "win")
    losses = sum(1 for o in non_ties if o.label == "loss")
    ties = sum(1 for o in outcomes if o.label == "tie")
    n = wins + losses
    return {
        "wins": wins,
        "losses": losses,
        "ties": ties,
        "effective_sample_size": n,
        "p_value": _binom_two_sided_p(wins, n),
    }


def paired_bootstrap_ci(
    outcomes: Sequence[PairedOutcome],
    *,
    seed: int,
    resamples: int,
    confidence_level: float,
) -> dict[str, Any]:
    """Deterministic paired bootstrap CI for mean challenger-baseline delta."""
    if not outcomes:
        return {
            "mean_delta": 0.0,
            "ci_low": 0.0,
            "ci_high": 0.0,
            "seed": seed,
            "resamples": resamples,
            "confidence_level": confidence_level,
        }
    deltas = [o.delta for o in outcomes]
    mean_delta = sum(deltas) / len(deltas)
    rng = random.Random(seed)
    n = len(deltas)
    boots: list[float] = []
    for _ in range(resamples):
        sample = [deltas[rng.randrange(n)] for _ in range(n)]
        boots.append(sum(sample) / n)
    boots.sort()
    alpha = 1.0 - confidence_level
    lo_i = math.floor((alpha / 2.0) * (resamples - 1))
    hi_i = math.ceil((1.0 - alpha / 2.0) * (resamples - 1))
    lo_i = max(0, min(resamples - 1, lo_i))
    hi_i = max(0, min(resamples - 1, hi_i))
    return {
        "mean_delta": mean_delta,
        "ci_low": boots[lo_i],
        "ci_high": boots[hi_i],
        "seed": seed,
        "resamples": resamples,
        "confidence_level": confidence_level,
    }


def _cluster_index(
    outcomes: Sequence[PairedOutcome],
) -> dict[str, dict[str, list[PairedOutcome]]]:
    """Index outcomes by domain and source group, rejecting cross-domain groups."""
    indexed: dict[str, dict[str, list[PairedOutcome]]] = defaultdict(
        lambda: defaultdict(list)
    )
    group_domains: dict[str, str] = {}
    for outcome in outcomes:
        if not outcome.domain or not outcome.source_group:
            raise ValueError("clustered inference requires domain and source_group")
        prior = group_domains.setdefault(outcome.source_group, outcome.domain)
        if prior != outcome.domain:
            raise ValueError(
                f"source_group spans domains: {outcome.source_group!r}"
            )
        indexed[outcome.domain][outcome.source_group].append(outcome)
    return {domain: dict(groups) for domain, groups in indexed.items()}


def _domain_equal_query_mean(
    outcomes_by_domain: Mapping[str, Sequence[PairedOutcome]],
) -> float:
    """Equal-weight domain mean with equal query weight within each domain."""
    domain_means = []
    for domain in sorted(outcomes_by_domain):
        rows = list(outcomes_by_domain[domain])
        if not rows:
            continue
        domain_means.append(sum(row.delta for row in rows) / len(rows))
    return sum(domain_means) / len(domain_means) if domain_means else 0.0


def paired_cluster_bootstrap_ci(
    outcomes: Sequence[PairedOutcome],
    *,
    seed: int,
    resamples: int,
    confidence_level: float,
) -> dict[str, Any]:
    """Domain-stratified source-group cluster percentile bootstrap."""
    indexed = _cluster_index(outcomes)
    original_by_domain = {
        domain: [row for group in groups.values() for row in group]
        for domain, groups in indexed.items()
    }
    mean_delta = _domain_equal_query_mean(original_by_domain)
    rng = random.Random(seed)
    boots: list[float] = []
    for _ in range(resamples):
        sampled: dict[str, list[PairedOutcome]] = {}
        for domain, groups in indexed.items():
            group_values = list(groups.values())
            sampled[domain] = [
                row
                for _index in range(len(group_values))
                for row in group_values[rng.randrange(len(group_values))]
            ]
        boots.append(_domain_equal_query_mean(sampled))
    boots.sort()
    alpha = 1.0 - confidence_level
    if boots:
        lo_i = max(0, min(len(boots) - 1, math.floor((alpha / 2.0) * len(boots))))
        hi_i = max(
            0,
            min(len(boots) - 1, math.ceil((1.0 - alpha / 2.0) * len(boots)) - 1),
        )
        ci_low, ci_high = boots[lo_i], boots[hi_i]
    else:
        ci_low = ci_high = mean_delta
    return {
        "mean_delta": mean_delta,
        "ci_low": ci_low,
        "ci_high": ci_high,
        "seed": seed,
        "resamples": resamples,
        "confidence_level": confidence_level,
        "algorithm": "domain_stratified_cluster_percentile_v1",
        "resampling_unit": "source_group_within_domain",
    }


def paired_cluster_sign_flip(
    outcomes: Sequence[PairedOutcome],
    *,
    seed: int,
    draws: int,
) -> dict[str, Any]:
    """Domain-stratified source-group sign-flip permutation test."""
    indexed = _cluster_index(outcomes)
    groups = [
        (domain, group_rows)
        for domain in sorted(indexed)
        for group_rows in indexed[domain].values()
    ]
    observed = _domain_equal_query_mean(
        {
            domain: [row for rows in indexed[domain].values() for row in rows]
            for domain in indexed
        }
    )
    rng = random.Random(seed)
    positive_extreme = 0
    negative_extreme = 0
    for _ in range(draws):
        flipped: dict[str, list[PairedOutcome]] = defaultdict(list)
        for domain, rows in groups:
            sign = -1.0 if rng.getrandbits(1) else 1.0
            flipped[domain].extend(
                [
                    PairedOutcome(
                        query=row.query,
                        baseline=row.baseline,
                        challenger=row.baseline + sign * row.delta,
                        delta=sign * row.delta,
                        label=row.label,
                        domain=row.domain,
                        source_group=row.source_group,
                    )
                    for row in rows
                ]
            )
        statistic = _domain_equal_query_mean(flipped)
        if statistic >= observed:
            positive_extreme += 1
        if statistic <= observed:
            negative_extreme += 1
    denominator = draws + 1
    return {
        "observed_statistic": observed,
        "positive_p_value": (positive_extreme + 1) / denominator,
        "negative_p_value": (negative_extreme + 1) / denominator,
        "seed": seed,
        "draws": draws,
        "algorithm": "domain_stratified_cluster_sign_flip_v1",
        "resampling_unit": "source_group_within_domain",
        "group_count": len(groups),
    }


def label_challenger(
    *,
    outcomes: Sequence[PairedOutcome],
    significance_alpha: float,
    confidence_level: float,
    bootstrap_seed: int,
    bootstrap_resamples: int,
    minimum_non_tied_pairs: int,
    permutation_seed: int = 20260805,
    permutation_draws: int = 100000,
    minimum_non_tied_groups: int | None = None,
) -> dict[str, Any]:
    """BETTER only when delta>0, CI excludes 0 positively, p<=alpha, n>=min; else INCONCLUSIVE/WORSE."""
    clustered = any(o.domain or o.source_group for o in outcomes)
    if clustered:
        indexed = _cluster_index(outcomes)
        groups = [
            rows
            for domain in sorted(indexed)
            for rows in indexed[domain].values()
        ]
        non_tied_groups = sum(
            1
            for rows in groups
            if abs(sum(row.delta for row in rows) / len(rows)) > 0.0
        )
        st = sign_test(outcomes)
        st["effective_sample_size"] = non_tied_groups
        st["effective_sample_unit"] = "source_group"
        boot = paired_cluster_bootstrap_ci(
            outcomes,
            seed=bootstrap_seed,
            resamples=bootstrap_resamples,
            confidence_level=confidence_level,
        )
        permutation = paired_cluster_sign_flip(
            outcomes,
            seed=permutation_seed,
            draws=permutation_draws,
        )
        st["p_value"] = (
            permutation["positive_p_value"]
            if boot["mean_delta"] >= 0
            else permutation["negative_p_value"]
        )
        st["positive_p_value"] = permutation["positive_p_value"]
        st["negative_p_value"] = permutation["negative_p_value"]
        minimum = (
            minimum_non_tied_groups
            if minimum_non_tied_groups is not None
            else minimum_non_tied_pairs
        )
    else:
        st = sign_test(outcomes)
        boot = paired_bootstrap_ci(
            outcomes,
            seed=bootstrap_seed,
            resamples=bootstrap_resamples,
            confidence_level=confidence_level,
        )
        permutation = None
        minimum = minimum_non_tied_pairs
    n_eff = int(st["effective_sample_size"])
    mean_delta = float(boot["mean_delta"])
    ci_low = float(boot["ci_low"])
    ci_high = float(boot["ci_high"])
    p_value = float(st["p_value"])

    if n_eff < minimum:
        verdict = "INCONCLUSIVE"
        reason = "effective_sample_below_minimum"
    elif mean_delta > 0 and ci_low > 0 and p_value <= significance_alpha:
        verdict = "BETTER"
        reason = "all_criteria_met"
    elif mean_delta < 0 and ci_high < 0 and p_value <= significance_alpha:
        verdict = "WORSE"
        reason = "negative_significant"
    else:
        verdict = "INCONCLUSIVE"
        reason = "ci_crosses_zero_or_nonsignificant"

    return {
        **st,
        **boot,
        "verdict": verdict,
        "reason": reason,
        "significance_alpha": significance_alpha,
        "minimum_non_tied_pairs": minimum_non_tied_pairs,
        "minimum_non_tied_groups": minimum if clustered else None,
        "permutation": permutation,
        "evidence_only": True,
        "not_promotion_authority": True,
    }

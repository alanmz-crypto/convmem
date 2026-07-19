"""Paired uncertainty: sign test + seeded paired bootstrap (Gate 2 evidence)."""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from typing import Any, Sequence


@dataclass
class PairedOutcome:
    query: str
    baseline: float
    challenger: float
    delta: float
    label: str  # win | loss | tie


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
) -> list[PairedOutcome]:
    if len(baseline_scores) != len(challenger_scores):
        raise ValueError("paired score lengths differ")
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
    p = sum(pmf(k) for k in range(0, lo + 1)) * 2.0
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
    lo_i = int(math.floor((alpha / 2.0) * (resamples - 1)))
    hi_i = int(math.ceil((1.0 - alpha / 2.0) * (resamples - 1)))
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


def label_challenger(
    *,
    outcomes: Sequence[PairedOutcome],
    significance_alpha: float,
    confidence_level: float,
    bootstrap_seed: int,
    bootstrap_resamples: int,
    minimum_non_tied_pairs: int,
) -> dict[str, Any]:
    """BETTER only when delta>0, CI excludes 0 positively, p<=alpha, n>=min; else INCONCLUSIVE/WORSE."""
    st = sign_test(outcomes)
    boot = paired_bootstrap_ci(
        outcomes,
        seed=bootstrap_seed,
        resamples=bootstrap_resamples,
        confidence_level=confidence_level,
    )
    n_eff = int(st["effective_sample_size"])
    mean_delta = float(boot["mean_delta"])
    ci_low = float(boot["ci_low"])
    ci_high = float(boot["ci_high"])
    p_value = float(st["p_value"])

    if n_eff < minimum_non_tied_pairs:
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
        "evidence_only": True,
        "not_promotion_authority": True,
    }

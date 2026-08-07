"""Pure ANN realization repeatability checks for fixture and R7 reporting."""

from __future__ import annotations

import itertools
import math
from collections.abc import Mapping, Sequence
from typing import Any

REALIZATION_COUNT = 3
ALLOWED_VERDICTS = {"BETTER", "WORSE", "INCONCLUSIVE"}


def _invalid(error: str) -> dict[str, Any]:
    return {
        "technical_status": "INVALID",
        "evidence_verdict": "NOT_ISSUED",
        "ann_stability": "NOT_ISSUED",
        "errors": [error],
    }


def assess_ann_repeatability(
    realizations: Mapping[str, Mapping[str, Sequence[str]]],
    verdicts: Mapping[str, str],
    *,
    top_k: int = 5,
    top1_change_pair_limit: int = 1,
    mean_pairwise_top5_jaccard_minimum: float = 0.98,
) -> dict[str, Any]:
    """Assess exactly three independently captured ANN realizations.

    The function never turns malformed or incomplete captures into an
    inconclusive quality result: those are ``INVALID``/``NOT_ISSUED``.
    Semantic instability of otherwise valid realizations is ``INCONCLUSIVE``.
    """
    if len(realizations) != REALIZATION_COUNT:
        return _invalid(f"expected exactly {REALIZATION_COUNT} ANN realizations")
    names = sorted(realizations)
    if set(verdicts) != set(names):
        return _invalid("ANN verdicts must cover exactly the realization names")
    if (
        top_k < 1
        or top1_change_pair_limit < 0
        or not math.isfinite(float(mean_pairwise_top5_jaccard_minimum))
        or not 0.0 <= float(mean_pairwise_top5_jaccard_minimum) <= 1.0
    ):
        return _invalid("ANN stability parameters are malformed")
    query_sets = [set(realizations[name]) for name in names]
    if not query_sets[0] or any(query_set != query_sets[0] for query_set in query_sets[1:]):
        return _invalid("ANN realizations do not contain the same nonempty query IDs")
    for name in names:
        for query_id, hits in realizations[name].items():
            if not isinstance(query_id, str) or not query_id:
                return _invalid(f"{name} contains an invalid query ID")
            if not isinstance(hits, Sequence) or isinstance(hits, (str, bytes)):
                return _invalid(f"{name}:{query_id} hits are not an ordered sequence")
            if len(hits) < top_k:
                return _invalid(f"{name}:{query_id} has fewer than top_k hits")
            normalized = [str(hit) for hit in hits[:top_k]]
            if any(not hit for hit in normalized):
                return _invalid(f"{name}:{query_id} contains an empty hit ID")
            if len(normalized) != len(set(normalized)):
                return _invalid(f"{name}:{query_id} contains duplicate hit IDs")

    pair_reports: list[dict[str, Any]] = []
    for left, right in itertools.combinations(names, 2):
        top1_changes = 0
        jaccards: list[float] = []
        for query_id in sorted(query_sets[0]):
            left_hits = [str(hit) for hit in realizations[left][query_id][:top_k]]
            right_hits = [str(hit) for hit in realizations[right][query_id][:top_k]]
            top1_changes += int(left_hits[0] != right_hits[0])
            left_set = set(left_hits)
            right_set = set(right_hits)
            jaccards.append(
                len(left_set & right_set) / len(left_set | right_set)
                if left_set | right_set
                else 1.0
            )
        pair_reports.append(
            {
                "left": left,
                "right": right,
                "top1_change_count": top1_changes,
                "top5_jaccard_mean": sum(jaccards) / len(jaccards),
                "top5_jaccard_minimum": min(jaccards),
                "query_count": len(jaccards),
            }
        )
    mean_jaccard = sum(row["top5_jaccard_mean"] for row in pair_reports) / len(pair_reports)
    minimum_jaccard = min(row["top5_jaccard_minimum"] for row in pair_reports)
    top1_change_count = sum(row["top1_change_count"] for row in pair_reports)
    top1_changed_pair_count = sum(
        int(row["top1_change_count"] > 0) for row in pair_reports
    )
    verdict_values = {str(verdicts[name]) for name in names}
    if not verdict_values <= ALLOWED_VERDICTS:
        return _invalid("ANN realization verdict is unsupported")
    verdict_consistent = len(verdict_values) == 1
    stable = (
        top1_changed_pair_count <= top1_change_pair_limit
        and mean_jaccard >= mean_pairwise_top5_jaccard_minimum
        and verdict_consistent
    )
    primary_verdict = next(iter(verdict_values)) if verdict_consistent else "INCONCLUSIVE"
    return {
        "technical_status": "VALID",
        "ann_stability": "STABLE" if stable else "UNSTABLE",
        "evidence_verdict": primary_verdict if stable else "INCONCLUSIVE",
        "verdict_consistent": verdict_consistent,
        "realization_count": REALIZATION_COUNT,
        "query_count": len(query_sets[0]),
        "top_k": top_k,
        "top1_change_count": top1_change_count,
        "top1_changed_pair_count": top1_changed_pair_count,
        "top1_change_pair_limit": top1_change_pair_limit,
        "mean_pairwise_top5_jaccard": mean_jaccard,
        "minimum_pairwise_top5_jaccard": minimum_jaccard,
        "mean_pairwise_top5_jaccard_minimum": mean_pairwise_top5_jaccard_minimum,
        "pair_reports": pair_reports,
        "realization_verdicts": {name: verdicts[name] for name in names},
    }


__all__ = ["assess_ann_repeatability"]

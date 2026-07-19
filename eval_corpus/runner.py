"""Evaluation runner: namespaced metrics + dual retrieval views + latency harness.

Designed for injectable query callables — no live model or Chroma required in tests.
Live/shadow evaluation remains gated to R7 outside this module.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Callable

from eval_corpus.metrics import (
    expand_acceptable_ids,
    hit_at_k,
    mrr,
    ndcg_at_k,
    p_at_1,
    recall_at_k_complete,
)

RETRIEVAL_VIEWS = ("embedding_influenced", "operational_pipeline")

QueryFn = Callable[..., list[dict]]


@dataclass
class RowEval:  # pylint: disable=too-many-instance-attributes
    query: str
    view: str
    top_k: int
    p_at_1: bool
    hit_at_k: bool
    mrr: float
    recall_at_k: float | None
    ndcg_at_k: float
    rank: int | None
    hit_count: int


@dataclass
class ViewReport:  # pylint: disable=too-many-instance-attributes
    view: str
    count: int
    p_at_1: float
    hit_at_k: float
    mrr: float
    recall_at_k: float | None
    ndcg_at_k: float
    rows: list[RowEval] = field(default_factory=list)


def _first_rank(hits: list[dict], relevant: list[dict[str, Any]]) -> int | None:
    from eval_corpus.metrics import first_relevant_rank

    return first_relevant_rank(hits, relevant)


def evaluate_row(
    row: dict,
    hits: list[dict],
    *,
    view: str,
    top_k: int | None = None,
) -> RowEval:
    relevant = expand_acceptable_ids(row)
    k = int(top_k or row.get("top_k") or 5)
    ranked = hits[:k]
    rank = _first_rank(ranked, relevant)
    recall = None
    if row.get("relevant_complete"):
        recall = recall_at_k_complete(ranked, relevant, k)
    return RowEval(
        query=str(row.get("query") or ""),
        view=view,
        top_k=k,
        p_at_1=p_at_1(ranked, relevant),
        hit_at_k=hit_at_k(ranked, relevant, k),
        mrr=mrr(ranked, relevant),
        recall_at_k=recall,
        ndcg_at_k=ndcg_at_k(ranked, relevant, k),
        rank=rank,
        hit_count=len(ranked),
    )


def evaluate_view(
    rows: list[dict],
    query_fn: QueryFn,
    *,
    view: str,
    top_k: int | None = None,
) -> ViewReport:
    """Run golden rows through ``query_fn`` with a retrieval view.

    ``query_fn`` signature: ``(query, *, top_k, eval_view) -> list[hit]``.
    """
    if view not in RETRIEVAL_VIEWS:
        raise ValueError(f"unknown view {view!r}; expected one of {RETRIEVAL_VIEWS}")
    results: list[RowEval] = []
    for row in rows:
        k = int(top_k or row.get("top_k") or 5)
        hits = query_fn(str(row["query"]), top_k=k, eval_view=view)
        results.append(evaluate_row(row, hits, view=view, top_k=k))
    n = len(results) or 1
    recall_vals = [r.recall_at_k for r in results if r.recall_at_k is not None]
    return ViewReport(
        view=view,
        count=len(results),
        p_at_1=sum(1 for r in results if r.p_at_1) / n,
        hit_at_k=sum(1 for r in results if r.hit_at_k) / n,
        mrr=sum(r.mrr for r in results) / n,
        recall_at_k=(sum(recall_vals) / len(recall_vals)) if recall_vals else None,
        ndcg_at_k=sum(r.ndcg_at_k for r in results) / n,
        rows=results,
    )


def evaluate_both_views(
    rows: list[dict],
    query_fn: QueryFn,
    *,
    top_k: int | None = None,
    views: tuple[str, ...] = RETRIEVAL_VIEWS,
) -> dict[str, ViewReport]:
    return {
        view: evaluate_view(rows, query_fn, view=view, top_k=top_k) for view in views
    }


def view_report_to_dict(report: ViewReport) -> dict[str, Any]:
    return {
        "view": report.view,
        "count": report.count,
        "p_at_1": round(report.p_at_1, 4),
        "hit_at_k": round(report.hit_at_k, 4),
        "mrr": round(report.mrr, 4),
        "recall_at_k": None if report.recall_at_k is None else round(report.recall_at_k, 4),
        "ndcg_at_k": round(report.ndcg_at_k, 4),
        "rows": [
            {
                "query": r.query,
                "view": r.view,
                "top_k": r.top_k,
                "p_at_1": r.p_at_1,
                "hit_at_k": r.hit_at_k,
                "mrr": round(r.mrr, 4),
                "recall_at_k": r.recall_at_k,
                "ndcg_at_k": round(r.ndcg_at_k, 4),
                "rank": r.rank,
            }
            for r in report.rows
        ],
    }


@dataclass
class LatencySample:
    query: str
    view: str
    elapsed_ms: float


@dataclass
class LatencyReport:
    view: str
    samples: list[LatencySample]
    count: int
    mean_ms: float
    p50_ms: float
    p95_ms: float
    max_ms: float


def _percentile(sorted_vals: list[float], p: float) -> float:
    if not sorted_vals:
        return 0.0
    if len(sorted_vals) == 1:
        return sorted_vals[0]
    idx = min(len(sorted_vals) - 1, max(0, int(round((p / 100.0) * (len(sorted_vals) - 1)))))
    return sorted_vals[idx]


def measure_view_latency(
    queries: list[str],
    query_fn: QueryFn,
    *,
    view: str,
    top_k: int = 5,
    warmup: int = 0,
    clock: Callable[[], float] = time.perf_counter,
) -> LatencyReport:
    """Per-view latency harness. ``query_fn`` is injectable — no real models.

    ``clock`` defaults to ``time.perf_counter``; tests may inject a fake clock.
    """
    if view not in RETRIEVAL_VIEWS:
        raise ValueError(f"unknown view {view!r}; expected one of {RETRIEVAL_VIEWS}")
    for i in range(max(0, warmup)):
        if queries:
            query_fn(queries[i % len(queries)], top_k=top_k, eval_view=view)
    samples: list[LatencySample] = []
    for q in queries:
        t0 = clock()
        query_fn(q, top_k=top_k, eval_view=view)
        elapsed_ms = (clock() - t0) * 1000.0
        samples.append(LatencySample(query=q, view=view, elapsed_ms=elapsed_ms))
    vals = sorted(s.elapsed_ms for s in samples)
    n = len(vals) or 1
    return LatencyReport(
        view=view,
        samples=samples,
        count=len(samples),
        mean_ms=sum(vals) / n if vals else 0.0,
        p50_ms=_percentile(vals, 50),
        p95_ms=_percentile(vals, 95),
        max_ms=max(vals) if vals else 0.0,
    )


def measure_both_views_latency(
    queries: list[str],
    query_fn: QueryFn,
    *,
    top_k: int = 5,
    warmup: int = 0,
    views: tuple[str, ...] = RETRIEVAL_VIEWS,
    clock: Callable[[], float] = time.perf_counter,
) -> dict[str, LatencyReport]:
    return {
        view: measure_view_latency(
            queries, query_fn, view=view, top_k=top_k, warmup=warmup, clock=clock
        )
        for view in views
    }


def latency_report_to_dict(report: LatencyReport) -> dict[str, Any]:
    return {
        "view": report.view,
        "count": report.count,
        "mean_ms": round(report.mean_ms, 3),
        "p50_ms": round(report.p50_ms, 3),
        "p95_ms": round(report.p95_ms, 3),
        "max_ms": round(report.max_ms, 3),
        "queries_per_sec": round(1000.0 / report.mean_ms, 6) if report.mean_ms > 0 else 0.0,
        "samples": [
            {"query": s.query, "view": s.view, "elapsed_ms": round(s.elapsed_ms, 3)}
            for s in report.samples
        ],
    }


def _primary_score(row_eval: RowEval, primary_metric: str) -> float:
    if primary_metric == "hit_at_k":
        return 1.0 if row_eval.hit_at_k else 0.0
    if primary_metric == "p_at_1":
        return 1.0 if row_eval.p_at_1 else 0.0
    if primary_metric == "mrr":
        return float(row_eval.mrr)
    if primary_metric == "ndcg_at_k":
        return float(row_eval.ndcg_at_k)
    if primary_metric == "recall_at_k":
        return float(row_eval.recall_at_k or 0.0)
    raise ValueError(f"unknown primary_metric {primary_metric!r}")


def compare_paired_arms(  # pylint: disable=too-many-locals
    rows: list[dict],
    baseline_fn: QueryFn,
    challenger_fn: QueryFn,
    *,
    package_units: list[dict],
    uncertainty: dict[str, Any],
    top_k: int | None = None,
) -> dict[str, Any]:
    """Paired baseline/challenger compare with recipe strata + uncertainty.

    Primary inference uses primary_view (must be embedding_influenced) + primary_metric.
    Other views/strata are diagnostic only.
    """
    from eval_corpus.paired_stats import label_challenger, paired_outcomes
    from eval_corpus.recipe_strata import (
        index_package_units,
        resolve_relevant_recipes,
        validate_recipe_stratum,
    )

    primary_view = str(uncertainty.get("primary_view") or "embedding_influenced")
    primary_metric = str(uncertainty.get("primary_metric") or "hit_at_k")
    if primary_view != "embedding_influenced":
        raise ValueError("primary_view must be embedding_influenced")

    pkg_index = index_package_units(package_units)
    stratum_rows: list[dict[str, Any]] = []
    for row in rows:
        relevant = expand_acceptable_ids(row)
        resolved = resolve_relevant_recipes(relevant, pkg_index)
        validation = validate_recipe_stratum(
            str(row.get("recipe_stratum") or ""), resolved
        )
        stratum_rows.append(
            {
                "query": row["query"],
                "recipe_stratum": validation["declared"],
                "resolved_recipes": validation["resolved_recipes"],
            }
        )

    base_view = evaluate_view(rows, baseline_fn, view=primary_view, top_k=top_k)
    chal_view = evaluate_view(rows, challenger_fn, view=primary_view, top_k=top_k)
    base_scores = [_primary_score(r, primary_metric) for r in base_view.rows]
    chal_scores = [_primary_score(r, primary_metric) for r in chal_view.rows]
    outcomes = paired_outcomes(
        base_scores,
        chal_scores,
        queries=[r.query for r in base_view.rows],
        tie_epsilon=float(uncertainty.get("tie_epsilon") or 0.0),
    )
    uncertainty_report = label_challenger(
        outcomes=outcomes,
        significance_alpha=float(uncertainty.get("significance_alpha") or 0.05),
        confidence_level=float(uncertainty.get("confidence_level") or 0.95),
        bootstrap_seed=int(uncertainty.get("bootstrap_seed") or 0),
        bootstrap_resamples=int(uncertainty.get("bootstrap_resamples") or 1999),
        minimum_non_tied_pairs=int(uncertainty.get("minimum_non_tied_pairs") or 20),
    )

    # Diagnostic: both views + per-stratum hit rates (explicit n; no confidence claim)
    both_base = evaluate_both_views(rows, baseline_fn, top_k=top_k)
    both_chal = evaluate_both_views(rows, challenger_fn, top_k=top_k)
    by_stratum: dict[str, Any] = {}
    for stratum in sorted({r["recipe_stratum"] for r in stratum_rows}):
        idxs = [i for i, r in enumerate(stratum_rows) if r["recipe_stratum"] == stratum]
        n = len(idxs)
        b_hits = sum(1 for i in idxs if base_view.rows[i].hit_at_k)
        c_hits = sum(1 for i in idxs if chal_view.rows[i].hit_at_k)
        by_stratum[stratum] = {
            "n": n,
            "descriptive_only": True,
            "baseline_hit_rate": b_hits / n if n else 0.0,
            "challenger_hit_rate": c_hits / n if n else 0.0,
            "delta_hit_rate": (c_hits - b_hits) / n if n else 0.0,
            "note": "small strata are descriptive; do not imply statistical confidence",
        }

    return {
        "primary_view": primary_view,
        "primary_metric": primary_metric,
        "primary_inferential_surface": True,
        "anti_cherry_pick": (
            "operational_pipeline and recipe strata are diagnostic only"
        ),
        "baseline": view_report_to_dict(base_view),
        "challenger": view_report_to_dict(chal_view),
        "diagnostic_views": {
            "baseline": {k: view_report_to_dict(v) for k, v in both_base.items()},
            "challenger": {k: view_report_to_dict(v) for k, v in both_chal.items()},
        },
        "recipe_strata": {
            "per_query": stratum_rows,
            "by_stratum": by_stratum,
        },
        "paired_outcomes": [
            {
                "query": o.query,
                "baseline": o.baseline,
                "challenger": o.challenger,
                "delta": o.delta,
                "label": o.label,
            }
            for o in outcomes
        ],
        "uncertainty": uncertainty_report,
        "evidence_only": True,
        "not_promotion_authority": True,
    }

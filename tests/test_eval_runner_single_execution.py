"""Quality comparison must not re-query captured views during reporting."""

from __future__ import annotations

from eval_corpus.runner import RETRIEVAL_VIEWS, compare_paired_arms


def test_compare_executes_each_query_arm_view_once_and_retains_raw_hits():
    rows = [
        {
            "query_id": "q-1",
            "query": "find the target",
            "relevant": [{"namespace": "unit_id", "id": "target", "grade": 1}],
            "recipe_stratum": "ordinary",
            "top_k": 5,
        }
    ]
    package = [
        {
            "id": "target",
            "ledger_id": "ledger-target",
            "document_recipe_version": "ordinary_summary_keywords@v1",
        }
    ]
    calls = {"baseline": [], "challenger": []}

    def make_fn(arm: str):
        def _fn(query: str, *, top_k: int, eval_view: str):
            calls[arm].append((query, top_k, eval_view))
            if arm == "challenger" and eval_view == "embedding_influenced":
                return [{"id": "target", "metadata": {"ledger_id": "ledger-target"}}]
            return [{"id": "other", "metadata": {"ledger_id": "ledger-other"}}]

        return _fn

    report = compare_paired_arms(
        rows,
        make_fn("baseline"),
        make_fn("challenger"),
        package_units=package,
        uncertainty={
            "primary_view": "embedding_influenced",
            "primary_metric": "hit_at_k",
            "tie_epsilon": 0.0,
            "significance_alpha": 0.05,
            "confidence_level": 0.95,
            "bootstrap_seed": 1,
            "bootstrap_resamples": 20,
            "minimum_non_tied_pairs": 1,
        },
    )

    assert len(calls["baseline"]) == len(RETRIEVAL_VIEWS)
    assert len(calls["challenger"]) == len(RETRIEVAL_VIEWS)
    assert {call[2] for call in calls["baseline"]} == set(RETRIEVAL_VIEWS)
    assert {call[2] for call in calls["challenger"]} == set(RETRIEVAL_VIEWS)
    assert len(report["raw_quality_results"]) == 2 * len(RETRIEVAL_VIEWS)
    assert all(item["query_id"] == "q-1" for item in report["raw_quality_results"])
    assert report["baseline"]["hit_at_k"] == 0.0
    assert report["challenger"]["hit_at_k"] == 1.0

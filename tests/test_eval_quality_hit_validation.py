"""Production subprocess comparison rejects semantic hit corruption."""

from __future__ import annotations

import pytest

from eval_corpus.runner import compare_paired_arms


def test_strict_quality_validation_rejects_unknown_hit_id():
    rows = [
        {
            "query_id": "q1",
            "query": "question",
            "relevant": [{"namespace": "unit_id", "id": "u1", "grade": 1}],
            "recipe_stratum": "ordinary",
            "top_k": 1,
        }
    ]
    package = [{"id": "u1", "document_recipe_version": "ordinary_summary_keywords@v1"}]

    def query_fn(query, *, top_k, eval_view):
        return [{"id": "not-in-package"}]

    with pytest.raises(ValueError, match="unknown hit id"):
        compare_paired_arms(
            rows,
            query_fn,
            query_fn,
            package_units=package,
            uncertainty={"primary_view": "embedding_influenced", "primary_metric": "hit_at_k"},
            strict_quality_validation=True,
        )

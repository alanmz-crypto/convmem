"""Comparison-side validation of worker vector-evidence flags."""

from __future__ import annotations

import pytest

from eval_corpus.subprocess_compare import (
    WorkerFailure,
    verify_enrichment_reader_result,
    verify_ranked_hit_payload,
    verify_vector_only_result,
)


def _valid() -> dict:
    return {
        "retrieval_mode": "vector",
        "vector_query_attempted": True,
        "fallback_used": False,
        "query_vector_fingerprint": "a" * 64,
        "query_vector_dimension": 768,
        "query_vector_finite": True,
        "query_vector_norm": 1.25,
    }


def test_valid_vector_result_is_accepted():
    verify_vector_only_result(_valid(), context="test")


def test_ranked_hit_payload_rejects_duplicate_ids():
    result = {
        "hits": [
            {"id": "unit-1", "metadata": {}, "distance": 0.1},
            {"id": "unit-1", "metadata": {}, "distance": 0.2},
        ]
    }
    with pytest.raises(WorkerFailure, match="duplicate"):
        verify_ranked_hit_payload(result, top_k=5, context="test")


@pytest.mark.parametrize(
    ("result", "message"),
    [
        ({}, "hits must be a list"),
        ({"hits": [{"id": "unit-1"}] * 3}, "above requested"),
        ({"hits": ["unit-1"]}, "must be an object"),
        ({"hits": [{"metadata": {}}]}, "no unit id"),
        ({"hits": [{"id": "unit-1", "distance": "bad"}]}, "not numeric"),
    ],
)
def test_ranked_hit_payload_rejects_malformed_shape(result, message):
    with pytest.raises(WorkerFailure, match=message):
        verify_ranked_hit_payload(result, top_k=2, context="test")


def test_ranked_hit_payload_rejects_nonfinite_scores_and_unknown_ids():
    with pytest.raises(WorkerFailure, match="not finite"):
        verify_ranked_hit_payload(
            {"hits": [{"id": "unit-1", "score": float("nan")}]},
            top_k=5,
            context="test",
        )
    with pytest.raises(WorkerFailure, match="unknown"):
        verify_ranked_hit_payload(
            {"hits": [{"id": "unit-2"}]},
            top_k=5,
            expected_ids={"unit-1"},
            context="test",
        )


def test_enrichment_provenance_is_checked_for_operational_view():
    result = {
        **_valid(),
        "eval_view": "operational_pipeline",
        "enrichment_reader": {
            "schema_version": "approved_decisions_reader_v1",
            "encoding": "utf-8",
            "path": "/tmp/arm/decisions-approved.jsonl",
            "sha256": "b" * 64,
            "row_count": 2,
            "semantic_fingerprint": "c" * 64,
            "used_by_view": True,
        },
    }
    verify_enrichment_reader_result(
        result,
        expected_identity={
            "enrichment_path": "/tmp/arm/decisions-approved.jsonl",
            "enrichment_sha256": "b" * 64,
        },
        require_reader=True,
        context="test",
    )


def test_missing_enrichment_provenance_is_rejected():
    result = {**_valid(), "eval_view": "operational_pipeline"}
    with pytest.raises(WorkerFailure, match="missing"):
        verify_enrichment_reader_result(
            result,
            expected_identity={
                "enrichment_path": "/tmp/arm/decisions-approved.jsonl",
                "enrichment_sha256": "b" * 64,
            },
            require_reader=True,
            context="test",
        )


@pytest.mark.parametrize(
    ("key", "value", "message"),
    [
        ("retrieval_mode", "fallback", "retrieval_mode"),
        ("vector_query_attempted", False, "attempted"),
        ("fallback_used", True, "fallback"),
        ("query_vector_fingerprint", "", "fingerprint"),
        ("query_vector_finite", False, "finite"),
        ("query_vector_norm", 0.0, "dimension/norm"),
    ],
)
def test_invalid_vector_result_is_rejected(key, value, message):
    result = _valid()
    result[key] = value
    with pytest.raises(WorkerFailure, match=message):
        verify_vector_only_result(result, context="test")

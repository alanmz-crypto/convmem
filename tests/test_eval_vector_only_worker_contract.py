"""Comparison-side validation of worker vector-evidence flags."""

from __future__ import annotations

import pytest

from eval_corpus.subprocess_compare import WorkerFailure, verify_vector_only_result


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

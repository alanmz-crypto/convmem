"""Scored retrieval must fail closed when vector access fails."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from query import QueryUnitTrace, query_units


def _cfg(policy: str) -> dict:
    return {
        "models": {"embed_model": "test", "ollama_host": "http://ollama"},
        "index": {"chroma_dir": "/tmp/eval-only-chroma"},
        "query": {"fallback_policy": policy, "top_k_candidates": 5},
        "eval": {"retrieval_view": "embedding_influenced"},
    }


def test_forbid_policy_rejects_vector_failure_without_lexical_hits():
    trace = QueryUnitTrace()
    with patch("query.ollama_embed", return_value=[1.0, 0.0]), patch(
        "query.open_chroma_for_read", side_effect=OSError("collection unavailable")
    ), patch(
        "query._fallback_query_rows",
        return_value=[{"id": "lexical-fallback", "metadata": {}}],
    ) as fallback, pytest.raises(RuntimeError, match="fallback_policy=forbid"):
        query_units(
            "vector query",
            top_k=1,
            cfg=_cfg("forbid"),
            retrieval_trace=trace,
        )
    fallback.assert_not_called()
    assert trace.retrieval_mode == "failed"
    assert trace.fallback_used is False
    assert trace.vector_query_attempted is True


def test_allow_policy_marks_lexical_fallback_explicitly():
    trace = QueryUnitTrace()
    rows = [
        {
            "id": "lexical-fallback",
            "metadata": {},
            "document": "fallback document",
            "score": 1.0,
        }
    ]
    with patch("query.ollama_embed", return_value=[1.0, 0.0]), patch(
        "query.open_chroma_for_read", side_effect=OSError("collection unavailable")
    ), patch("query._fallback_query_rows", return_value=rows), patch(
        "query._apply_keyword_rank", side_effect=lambda _text, values: values
    ), patch(
        "query._fuse_retrieval_ranks", side_effect=lambda values, **_kwargs: values
    ), patch("rerank.rerank", side_effect=lambda _text, values, _model, _top_k: values):
        result = query_units(
            "vector query",
            top_k=1,
            cfg=_cfg("allow"),
            retrieval_trace=trace,
        )
    assert result[0]["id"] == "lexical-fallback"
    assert trace.retrieval_mode == "fallback"
    assert trace.fallback_used is True
    assert trace.vector_query_attempted is True

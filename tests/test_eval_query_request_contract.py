"""Scored query workers use the explicit Ollama request contract."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from query import QueryUnitTrace, query_units


def test_query_units_uses_ollama_embed_v1_contract():
    client = MagicMock()
    client.embed.return_value = (
        [1.0, 0.0],
        {
            "request_schema_version": "ollama.embed.v1",
            "endpoint_path": "/api/embed",
            "total_duration": 12,
        },
    )
    store = MagicMock()
    store.query_units.return_value = [
        {"id": "unit-1", "distance": 0.1, "document": "doc", "metadata": {}}
    ]
    cfg = {
        "models": {"embed_model": "qwen", "ollama_host": "http://127.0.0.1:11434"},
        "index": {"chroma_dir": "/tmp/eval-chroma"},
        "query": {"fallback_policy": "forbid", "top_k_candidates": 5},
        "eval": {
            "retrieval_view": "embedding_influenced",
            "embedding_request_contract": "ollama.embed.v1",
            "embedding_dimensions": 2,
        },
    }
    trace = QueryUnitTrace()
    with patch("eval_corpus.ollama_identity.OllamaEmbedClient", return_value=client), patch(
        "query.open_chroma_for_read", return_value=store
    ), patch("rerank.rerank", side_effect=lambda _q, values, _m, _k: values):
        query_units("request contract", top_k=1, cfg=cfg, retrieval_trace=trace)
    client.embed.assert_called_once()
    assert client.embed.call_args.kwargs["dimensions"] == 2
    assert trace.embedding_request_diagnostics["endpoint_path"] == "/api/embed"

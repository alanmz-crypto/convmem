"""The exact-vector diagnostic is quality-only, not a latency view."""

from __future__ import annotations

import query


def test_exact_vector_view_is_accepted():
    assert query._resolve_eval_retrieval_view("exact_vector", {"eval": {}}) == "exact_vector"
    assert (
        query._resolve_eval_retrieval_view("embedding-influenced", {"eval": {}})
        == "embedding_influenced"
    )


def test_quality_views_include_exact_vector_without_changing_latency_views():
    from eval_corpus.runner import QUALITY_VIEWS, RETRIEVAL_VIEWS

    assert QUALITY_VIEWS == (
        "embedding_influenced",
        "operational_pipeline",
        "exact_vector",
    )
    assert RETRIEVAL_VIEWS == ("embedding_influenced", "operational_pipeline")


def test_exact_vector_returns_store_candidates_before_downstream_ranking(monkeypatch):
    class Store:
        def query_units(self, embedding, n_fetch):
            assert embedding == [1.0, 0.0]
            assert n_fetch == 20
            return [
                {"id": "vector-first", "metadata": {}, "distance": 0.1},
                {"id": "vector-second", "metadata": {}, "distance": 0.2},
            ]

        def close(self):
            return None

    cfg = {
        "models": {"embed_model": "fixture", "ollama_host": "http://fixture"},
        "query": {"top_k_candidates": 20, "fallback_policy": "forbid"},
        "index": {"chroma_dir": "/fixture"},
        "eval": {},
    }
    monkeypatch.setattr(query, "ollama_embed", lambda text, model, host: [1.0, 0.0])
    monkeypatch.setattr(query, "open_chroma_for_read", lambda path: Store())
    trace = query.QueryUnitTrace()
    hits = query.query_units("question", top_k=1, cfg=cfg, eval_view="exact_vector", retrieval_trace=trace)
    assert [hit["id"] for hit in hits] == ["vector-first"]
    assert [hit["id"] for hit in trace.candidates] == ["vector-first", "vector-second"]
    assert trace.retrieval_mode == "vector"
    assert trace.enrichment_reader["used_by_view"] is False

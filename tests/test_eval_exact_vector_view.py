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
                {"id": "vector-second", "metadata": {}, "distance": 0.1},
                {"id": "vector-first", "metadata": {}, "distance": 0.1},
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
    assert [hit["id"] for hit in trace.candidates] == ["vector-second", "vector-first"]
    assert trace.retrieval_mode == "vector"
    assert trace.enrichment_reader["used_by_view"] is False


def test_subprocess_exact_vector_reuses_production_payload(monkeypatch, tmp_path):
    from eval_corpus import subprocess_compare

    calls = []

    def fake_run_one_shot_query(**kwargs):
        calls.append(kwargs["eval_view"])
        return {
            "result": {
                "eval_view": kwargs["eval_view"],
                "hits": [{"id": "post-rank"}],
                "vector_candidates": [
                    {"id": "vector-second", "distance": 0.1},
                    {"id": "vector-first", "distance": 0.1},
                ],
                "query_vector_fingerprint": "a" * 64,
            },
            "stdout": "raw-worker-output",
            "stderr": "",
        }

    monkeypatch.setattr(subprocess_compare, "run_one_shot_query", fake_run_one_shot_query)
    query_fn = subprocess_compare.make_subprocess_query_fn(tmp_path / "config.toml")
    assert query_fn("question", top_k=5, eval_view="embedding_influenced")[0]["id"] == "post-rank"
    exact = query_fn("question", top_k=5, eval_view="exact_vector")
    assert [hit["id"] for hit in exact] == ["vector-first", "vector-second"]
    assert calls == ["embedding_influenced"]
    assert query_fn.last_payload["result"]["same_captured_query_vector"] is True

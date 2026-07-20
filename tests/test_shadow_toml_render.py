"""shadow.toml must round-trip list values as TOML arrays (not str(list))."""

from __future__ import annotations

import tomllib

from eval_corpus.shadow_config import render_toml


def test_render_toml_lists_round_trip_via_tomllib():
    cfg = {
        "sources": {
            "paths": ["~/a", "~/b"],
            "inventory": "~/.local/share/convmem/inventory.jsonl",
        },
        "refine": {
            "jobs": ["chroma_dedupe", "semantic_dedupe"],
        },
        "watch": {
            "extra_paths": ["~/Projects/convmem/docs/inter-model"],
        },
        "index": {"chroma_dir": "/tmp/chroma"},
        "models": {"embed_model": "nomic-embed-text", "ollama_host": "http://localhost:11434"},
        "eval": {"rerank_mode": "identity", "retrieval_view": "embedding_influenced"},
    }
    text = render_toml(cfg)
    assert 'paths = ["~/a", "~/b"]' in text
    assert "paths = \"[" not in text
    parsed = tomllib.loads(text)
    assert parsed["sources"]["paths"] == ["~/a", "~/b"]
    assert parsed["refine"]["jobs"] == ["chroma_dedupe", "semantic_dedupe"]
    assert isinstance(parsed["sources"]["paths"], list)
    assert isinstance(parsed["refine"]["jobs"], list)


def test_render_toml_nested_list_of_ints():
    text = render_toml({"sec": {"nums": [1, 2, 3], "flag": True}})
    parsed = tomllib.loads(text)
    assert parsed["sec"]["nums"] == [1, 2, 3]
    assert parsed["sec"]["flag"] is True


def test_render_toml_nested_tables_round_trip_via_tomllib():
    cfg = {
        "refine": {
            "enabled": True,
            "cost": {
                "backfill_domain_calls_per_hour": 60,
                "redistill_calls_per_hour": 15,
            },
        },
    }
    text = render_toml(cfg)
    assert "[refine.cost]" in text
    assert tomllib.loads(text) == cfg

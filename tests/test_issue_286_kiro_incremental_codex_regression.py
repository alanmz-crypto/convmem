"""Pin Codex v2 behavior unchanged by Kiro slice (C-KI3)."""

from __future__ import annotations

from incremental_transform_contract import build_transform_descriptor


def test_codex_rollout_descriptor_unchanged_by_kiro_contract_bump() -> None:
    codex = build_transform_descriptor(
        chunk_size=60,
        overlap=10,
        min_confidence=0.6,
        models={
            "summarize_model": "fake",
            "distill_model": "fake",
            "embed_model": "fake",
            "ollama_host": "http://127.0.0.1:9",
        },
        embed_dimension=768,
        adapter_format="jsonl_codex_rollout",
        adapter_contract_version="codex-rollout-complete-prefix-v1",
    )
    assert codex.digest
    assert codex.adapter_format == "jsonl_codex_rollout"

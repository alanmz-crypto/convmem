"""Pin Codex v2 behavior unchanged by Kiro slice (C-KI3)."""

from __future__ import annotations

from incremental_jsonl_formats import get_format_spec
from incremental_transform_contract import build_transform_descriptor


def test_codex_rollout_descriptor_unchanged_by_kiro_contract_bump() -> None:
    spec = get_format_spec("jsonl_codex_rollout")
    assert spec is not None
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
        adapter_format=spec.format_id,
        adapter_contract_version=spec.adapter_contract_version,
    )
    # Golden computed from main at 07117ed6196292b3156c0e165dd69e84fe967cdd
    # with these exact inputs; changes to shared epochs/prompts must fail here.
    assert codex.digest == "841b1c8d3f0500419d3ae5e3d61db09f9c8c687d2f00f0668bedc5e1c631e805"
    assert codex.adapter_format == "jsonl_codex_rollout"

# ref: ../incremental_transform_contract.py, ../incremental_jsonl_formats.py — Codex v2 golden identity

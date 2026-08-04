"""Build-level adapter and stored-vector provenance tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from eval_corpus.embed_adapters import fake_embed_fn
from eval_corpus.fingerprint import corpus_fingerprint_hex, package_sha256_hex
from eval_corpus.reconstruct import build_canonical_unit
from eval_corpus.shadow_build import run_shadow_build


def _unit():
    return build_canonical_unit(
        {
            "id": "vector-provenance-1",
            "summary": "vector provenance fixture",
            "keywords": ["vector"],
            "tool": "test",
            "source_path": "test:vector",
        }
    )


def _manifest(units):
    return {
        "embed_model": "fixture-model",
        "embed_dimensions": 8,
        "embed_mode": "fake",
        "unit_corpus_fingerprint": corpus_fingerprint_hex(units),
        "package_sha256": package_sha256_hex(units),
        "unit_count": len(units),
        "batch_size": 1,
        "schema_version": "1",
    }


def test_fixture_build_records_stored_vector_fingerprint(tmp_path: Path):
    units = [_unit()]
    result = run_shadow_build(
        units=units,
        chroma_dir=tmp_path / "chroma",
        manifest=_manifest(units),
        embed_fn=fake_embed_fn(8),
        manifest_path=tmp_path / "manifest.json",
        result_path=tmp_path / "result.json",
    )
    assert len(result["embedding_matrix_fingerprint"]) == 64
    assert result["embedding_matrix_fingerprint_scope"] == "stored_float32_readback"


def test_real_build_rejects_injected_fake_callable_even_with_ollama_mode(tmp_path):
    units = [_unit()]
    manifest = _manifest(units)
    manifest["embed_mode"] = "ollama"
    with pytest.raises(RuntimeError, match="injected embedding"):
        run_shadow_build(
            units=units,
            chroma_dir=tmp_path / "chroma",
            manifest=manifest,
            embed_fn=fake_embed_fn(8),
            execution_mode="real",
            embed_mode="ollama",
        )

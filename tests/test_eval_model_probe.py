"""Fixture-only model probe contract tests."""

from __future__ import annotations

import pytest

from eval_corpus.embed_adapters import fake_embed_fn
from eval_corpus.model_probe import run_model_probe
from eval_corpus.ollama_identity import OllamaIdentityError


class _FixtureClient:
    def __init__(self, dimensions=8, digest="sha256:test"):
        self.dimensions = dimensions
        self.digest = digest
        self.calls = []

    def list_models(self):
        return [{"name": "fixture-model", "digest": self.digest}]

    def resolve_model(self, tag):
        assert tag == "fixture-model"
        return {"model_tag": tag, "model_digest": self.digest, "variant": "fixture"}

    def embed(self, text, *, model_tag, dimensions):
        self.calls.append((text, model_tag, dimensions))
        vector = fake_embed_fn(dimensions)(text)
        return vector, {
            "request": {
                "model": model_tag,
                "input": text,
                "dimensions": dimensions,
            },
            "dimension": dimensions,
            "finite": True,
            "norm": 1.0,
            "vector_fingerprint": "f" * 64,
        }


def test_probe_captures_identity_request_and_diagnostics():
    client = _FixtureClient()
    report = run_model_probe(
        client,
        model_tag="fixture-model",
        expected_digest="sha256:test",
        dimensions=8,
        probe_text="probe text",
        transform_id="production_swap_v1",
        transform_sha256="a" * 64,
    )
    assert report["schema_version"] == "model_probe_v1"
    assert report["model_digest"] == "sha256:test"
    assert report["embedding_diagnostics"]["request"]["dimensions"] == 8
    assert len(client.calls) == 1


def test_probe_rejects_digest_drift():
    client = _FixtureClient(digest="sha256:wrong")
    with pytest.raises(OllamaIdentityError, match="digest mismatch"):
        run_model_probe(
            client,
            model_tag="fixture-model",
            expected_digest="sha256:expected",
            dimensions=8,
            probe_text="probe text",
            transform_id="production_swap_v1",
            transform_sha256="a" * 64,
        )

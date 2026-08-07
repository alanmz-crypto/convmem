"""Hermetic worker-side model identity enforcement tests."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


def _worker_module():
    path = Path(__file__).parents[1] / "scripts" / "eval_query_arm_worker.py"
    spec = importlib.util.spec_from_file_location("eval_query_arm_worker_identity", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class _IdentityClient:
    def __init__(self, _host: str):
        pass

    def resolve_model(self, _tag: str):
        return {
            "model_tag": "test:latest",
            "model_digest": "sha256:" + ("a" * 64),
            "variant": "qwen",
            "quantization": "Q8_0",
        }

    def resolve_loaded_model(self, _tag: str, _digest: str, *, required: bool = False):
        _ = required
        return {
            "model_tag": "test:latest",
            "model_digest": "sha256:" + ("a" * 64),
            "size_vram": 123,
        }


def test_worker_requires_resolved_digest_match(monkeypatch):
    module = _worker_module()
    monkeypatch.setattr("eval_corpus.ollama_identity.OllamaEmbedClient", _IdentityClient)
    cfg = {
        "models": {
            "embed_model": "test:latest",
            "embed_model_digest": "sha256:" + ("a" * 64),
            "ollama_host": "http://127.0.0.1:11434",
        },
        "eval": {"embedding_request_contract": "ollama.embed.v1"},
    }
    identity = module._verify_current_model(cfg)
    assert identity["model_digest"] == "sha256:" + ("a" * 64)
    assert identity["residency_status"] == "resident"


def test_worker_rejects_digest_mismatch(monkeypatch):
    module = _worker_module()
    monkeypatch.setattr("eval_corpus.ollama_identity.OllamaEmbedClient", _IdentityClient)
    cfg = {
        "models": {
            "embed_model": "test:latest",
            "embed_model_digest": "sha256:" + ("b" * 64),
            "ollama_host": "http://127.0.0.1:11434",
        },
        "eval": {"embedding_request_contract": "ollama.embed.v1"},
    }
    with pytest.raises(RuntimeError, match="digest"):
        module._verify_current_model(cfg)

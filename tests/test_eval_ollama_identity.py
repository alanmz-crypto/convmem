"""Hermetic tests for the pinned Ollama model/request contract."""

from __future__ import annotations

from typing import Any

import pytest

from eval_corpus.ollama_identity import (
    OllamaEmbedClient,
    OllamaIdentityError,
    canonical_loopback_host,
)


class _Response:
    def __init__(self, payload: dict[str, Any], *, status_code: int = 200):
        self.payload = payload
        self.status_code = status_code

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


class _InvalidJsonResponse(_Response):
    def json(self):
        raise ValueError("invalid json")


class _Session:
    def __init__(self):
        self.trust_env = True
        self.calls: list[tuple[str, str, dict[str, Any]]] = []

    def request(self, method, url, **kwargs):
        self.calls.append((method, url, kwargs))
        if url.endswith("/api/tags"):
            return _Response({"models": [{"name": "test:latest", "digest": "sha256:test"}]})
        if url.endswith("/api/show"):
            return _Response(
                {
                    "details": {
                        "family": "qwen",
                        "quantization_level": "Q8_0",
                        "parameter_size": "8B",
                    }
                }
            )
        if url.endswith("/api/ps"):
            return _Response(
                {
                    "models": [
                        {
                            "name": "test:latest",
                            "digest": "sha256:test",
                            "size_vram": 123,
                        }
                    ]
                }
            )
        if url.endswith("/api/embed"):
            return _Response(
                {
                    "embeddings": [[1.0, 0.0]],
                    "load_duration": 10,
                    "total_duration": 20,
                    "prompt_eval_count": 2,
                }
            )
        raise AssertionError(url)


def test_loopback_and_proxy_controls(monkeypatch):
    session = _Session()
    monkeypatch.setattr("requests.Session", lambda: session)
    client = OllamaEmbedClient("http://127.0.0.1:11434")
    assert session.trust_env is False
    identity = client.resolve_model("test:latest")
    assert identity["model_digest"] == "sha256:test"
    assert identity["quantization"] == "Q8_0"
    loaded = client.resolve_loaded_model("test:latest", "sha256:test", required=True)
    assert loaded["model_digest"] == "sha256:test"
    assert loaded["size_vram"] == 123
    vector, diagnostics = client.embed(
        "query",
        model_tag="test:latest",
        dimensions=2,
        truncate=False,
        keep_alive="10m",
        options={"temperature": 0},
    )
    assert vector == [1.0, 0.0]
    assert diagnostics["endpoint_path"] == "/api/embed"
    assert diagnostics["request"]["input"] == "query"
    assert diagnostics["request"]["dimensions"] == 2
    assert diagnostics["request"]["truncate"] is False
    assert diagnostics["total_duration"] == 20
    assert session.calls[-1][2]["timeout"] == 120.0


def test_ollama_adapter_exposes_resolved_model_identity(monkeypatch):
    session = _Session()
    monkeypatch.setattr("requests.Session", lambda: session)
    from eval_corpus.embed_adapters import ollama_embed_fn

    embed_fn = ollama_embed_fn(
        "http://127.0.0.1:11434", "test:latest", dimensions=2
    )

    identity = embed_fn.__eval_model_identity__
    assert identity["model_tag"] == "test:latest"
    assert identity["model_digest"] == "sha256:test"
    assert identity["quantization"] == "Q8_0"


@pytest.mark.parametrize("host", ["https://127.0.0.1:11434", "http://example.test:11434"])
def test_nonapproved_ollama_hosts_are_rejected(host):
    with pytest.raises(OllamaIdentityError, match="loopback|plain HTTP"):
        canonical_loopback_host(host)


def test_missing_digest_is_rejected(monkeypatch):
    session = _Session()
    monkeypatch.setattr("requests.Session", lambda: session)
    original = session.request

    def no_digest(method, url, **kwargs):
        response = original(method, url, **kwargs)
        if url.endswith("/api/tags"):
            return _Response({"models": [{"name": "test:latest"}]})
        return response

    session.request = no_digest
    client = OllamaEmbedClient("http://127.0.0.1:11434")
    with pytest.raises(OllamaIdentityError, match="no local digest"):
        client.resolve_model("test:latest")


def test_wrong_response_dimension_is_rejected(monkeypatch):
    session = _Session()
    monkeypatch.setattr("requests.Session", lambda: session)
    original = session.request

    def wrong_dimension(method, url, **kwargs):
        response = original(method, url, **kwargs)
        if url.endswith("/api/embed"):
            return _Response({"embeddings": [[1.0, 0.0, 0.0]]})
        return response

    session.request = wrong_dimension
    client = OllamaEmbedClient("http://127.0.0.1:11434")
    with pytest.raises(OllamaIdentityError, match="dimension"):
        client.embed("query", model_tag="test:latest", dimensions=2)
    assert all(not url.endswith("/api/embeddings") for _, url, _ in session.calls)


@pytest.mark.parametrize(
    "embeddings, message",
    [
        ([[[1.0, 0.0]]], "non-numeric"),
        ([[]], "dimension"),
        ([["not-a-number"]], "non-numeric"),
    ],
)
def test_malformed_embedding_values_are_identity_failures(monkeypatch, embeddings, message):
    session = _Session()
    monkeypatch.setattr("requests.Session", lambda: session)
    original = session.request

    def malformed(method, url, **kwargs):
        response = original(method, url, **kwargs)
        if url.endswith("/api/embed"):
            return _Response({"embeddings": embeddings})
        return response

    session.request = malformed
    client = OllamaEmbedClient("http://127.0.0.1:11434")
    with pytest.raises(OllamaIdentityError, match=message) as error:
        client.embed("query", model_tag="test:latest", dimensions=1)
    assert "model='test:latest'" in str(error.value)
    assert "endpoint=/api/embed" in str(error.value)
    assert "expected_dimension=1" in str(error.value)


def test_invalid_json_is_an_identity_failure_with_endpoint_context(monkeypatch):
    session = _Session()
    monkeypatch.setattr("requests.Session", lambda: session)
    original = session.request

    def invalid_json(method, url, **kwargs):
        response = original(method, url, **kwargs)
        if url.endswith("/api/embed"):
            return _InvalidJsonResponse({}, status_code=200)
        return response

    session.request = invalid_json
    client = OllamaEmbedClient("http://127.0.0.1:11434")
    with pytest.raises(OllamaIdentityError, match="valid JSON") as error:
        client.embed("query", model_tag="test:latest", dimensions=2)
    assert "model='test:latest'" in str(error.value)
    assert "endpoint=/api/embed" in str(error.value)
    assert "expected_dimension=2" in str(error.value)


def test_legacy_endpoint_is_rejected_without_fallback():
    with pytest.raises(OllamaIdentityError, match="only the approved /api/embed"):
        OllamaEmbedClient("http://127.0.0.1:11434", endpoint_path="/api/embeddings")

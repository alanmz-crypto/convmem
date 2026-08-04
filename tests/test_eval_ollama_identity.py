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
    def __init__(self, payload: dict[str, Any]):
        self.payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


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

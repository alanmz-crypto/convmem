"""Hermetic tests for OpenAI distill routing (Arc Codex, gpt-* models)."""

from __future__ import annotations

import json
from unittest import mock

import pytest
import requests

import distill
import llm
from incremental_transform_contract import build_transform_descriptor
from llm import PAID_PROVIDERS

LIVE_SHAPED_MODELS = {
    "summarize_model": "deepseek-v4-flash",
    "distill_model": "deepseek-v4-flash",
    "embed_model": "nomic-embed-text",
}

PINNED_LIVE_TRANSFORM_DESCRIPTOR_DIGEST = (
    "de86766d38df7dcedb42e931eebd4502d784a12896962a4b0c9f00cb621f8d96"
)


def _openai_success_response(content: str = "[]") -> mock.MagicMock:
    resp = mock.MagicMock()
    resp.raise_for_status = mock.MagicMock()
    resp.json.return_value = {
        "choices": [{"message": {"content": content}}],
        "usage": {
            "prompt_tokens": 10,
            "completion_tokens": 5,
            "total_tokens": 15,
            "completion_tokens_details": {"reasoning_tokens": 3},
        },
    }
    resp._convmem_provider_event = {
        "provider": "openai",
        "operation": "generate",
        "model": "gpt-6-luna",
        "base_url": "https://api.openai.com",
    }
    return resp


@pytest.fixture(autouse=True)
def _clean_openai_env(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)


def test_paid_providers_includes_openai() -> None:
    assert PAID_PROVIDERS == frozenset({"deepseek", "openai"})


def test_transform_descriptor_golden_without_reasoning_effort() -> None:
    descriptor = build_transform_descriptor(
        chunk_size=60,
        overlap=10,
        min_confidence=0.6,
        models=LIVE_SHAPED_MODELS,
        embed_dimension=768,
        adapter_format="jsonl_codex_rollout",
        adapter_contract_version="codex-rollout-complete-prefix-v1",
    )
    assert descriptor.digest == PINNED_LIVE_TRANSFORM_DESCRIPTOR_DIGEST
    assert "distill_reasoning_effort" not in descriptor.body


def test_transform_descriptor_includes_reasoning_effort_when_set() -> None:
    models = {**LIVE_SHAPED_MODELS, "distill_reasoning_effort": "max"}
    descriptor = build_transform_descriptor(
        chunk_size=60,
        overlap=10,
        min_confidence=0.6,
        models=models,
        embed_dimension=768,
        adapter_format="jsonl_codex_rollout",
        adapter_contract_version="codex-rollout-complete-prefix-v1",
    )
    assert descriptor.body["distill_reasoning_effort"] == "max"
    assert descriptor.digest != PINNED_LIVE_TRANSFORM_DESCRIPTOR_DIGEST


def test_openai_generate_success(monkeypatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    calls: list[dict] = []

    def fake_post(url, **kwargs):
        calls.append({"url": url, "json": kwargs.get("json")})
        return _openai_success_response("[{\"type\":\"pattern\"}]")

    monkeypatch.setattr(llm.requests, "post", fake_post)
    out = llm.generate(
        "prompt",
        "gpt-6-luna",
        "http://ollama.invalid",
        reasoning_effort="max",
    )
    assert json.loads(out) == [{"type": "pattern"}]
    assert calls[0]["url"] == "https://api.openai.com/v1/chat/completions"
    assert calls[0]["json"]["reasoning_effort"] == "max"
    assert "temperature" not in calls[0]["json"]


def test_openai_generate_timeout_retries(monkeypatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    attempts = {"n": 0}

    def fake_post(*_args, **_kwargs):
        attempts["n"] += 1
        if attempts["n"] == 1:
            raise requests.exceptions.Timeout("slow")
        return _openai_success_response("ok")

    monkeypatch.setattr(llm.requests, "post", fake_post)
    monkeypatch.setattr(llm.time, "sleep", lambda *_a, **_k: None)
    assert (
        llm._openai_generate(
            "p",
            "gpt-6-luna",
            "https://api.openai.com",
            max_attempts=2,
            retry_backoff=0.001,
        )
        == "ok"
    )
    assert attempts["n"] == 2


def test_openai_generate_4xx_not_retried(monkeypatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    attempts = {"n": 0}

    def fake_post(*_args, **_kwargs):
        attempts["n"] += 1
        response = mock.MagicMock()
        response.status_code = 401
        raise requests.exceptions.HTTPError(response=response)

    monkeypatch.setattr(llm.requests, "post", fake_post)
    with pytest.raises(requests.exceptions.HTTPError):
        llm._openai_generate(
            "p",
            "gpt-6-luna",
            "https://api.openai.com",
            max_attempts=3,
        )
    assert attempts["n"] == 1


def test_openai_missing_key_fail_closed(monkeypatch) -> None:
    ollama_calls: list[str] = []
    monkeypatch.setattr(
        llm,
        "_ollama_generate",
        lambda *_a, **_k: ollama_calls.append("called") or "ollama",
    )
    with pytest.raises(llm.ModelFallbackError, match="OPENAI_API_KEY"):
        llm.generate("p", "gpt-6-luna", "http://h")
    assert ollama_calls == []


def test_openai_write_scope_refused(monkeypatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    import purge_locks

    monkeypatch.setattr(purge_locks, "index_write_lock_depth", lambda: 1)
    with pytest.raises(RuntimeError, match="provider calls are forbidden"):
        distill.distill("chunk", "gpt-6-luna", "http://h")


def test_openai_usage_reported(monkeypatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.setattr(llm.requests, "post", lambda *_a, **_k: _openai_success_response())
    seen: list[dict] = []

    def reporter(_event, usage):
        seen.append(dict(usage))

    token = llm._PROVIDER_USAGE_REPORTER.set(reporter)
    try:
        llm.generate("p", "gpt-6-luna", "http://h")
    finally:
        llm._PROVIDER_USAGE_REPORTER.reset(token)
    assert seen
    assert seen[0]["completion_tokens_details"]["reasoning_tokens"] == 3


def test_resolve_generation_binding_openai() -> None:
    binding = llm.resolve_generation_binding("gpt-6-luna")
    assert binding["provider"] == "openai"
    assert binding["resolved_model"] == "gpt-6-luna"


def test_distill_provenance_binding(monkeypatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.setattr(
        distill,
        "generate",
        lambda *_a, **_k: '[{"type":"pattern","title":"t","summary":"s","keywords":["k"],"confidence":0.9,"domain":"general"}]',
    )
    units, _raw = distill.distill_with_response("chunk", "gpt-6-luna", "http://h")
    assert units
    binding = llm.resolve_generation_binding("gpt-6-luna")
    assert binding["provider"] == "openai"


def test_openai_generate_passes_max_attempts_via_internal(monkeypatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    attempts = {"n": 0}

    def fake_post(*_args, **_kwargs):
        attempts["n"] += 1
        if attempts["n"] < 2:
            raise requests.exceptions.ConnectionError("drop")
        return _openai_success_response("x")

    monkeypatch.setattr(llm.requests, "post", fake_post)
    monkeypatch.setattr(llm.time, "sleep", lambda *_a, **_k: None)
    llm._openai_generate(
        "p",
        "gpt-6-luna",
        "https://api.openai.com",
        max_attempts=2,
        retry_backoff=0.001,
    )
    assert attempts["n"] == 2

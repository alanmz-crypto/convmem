"""Bug 5 — silent provider fallback (Role 5 / SRE: silent-degradation).

A configured ``deepseek-v4*`` model with no ``DEEPSEEK_API_KEY`` used to swap
to a local Ollama model with zero signal, in several places. All swaps now
route through ``llm._resolve_fallback_model`` which:

- warns once per process to stderr (default: warn-and-continue), and
- fails closed when ``CONVMEM_FAIL_ON_FALLBACK=1`` (raises ``ModelFallbackError``
  and never touches the local model — effect, not presence).

These tests exercise ``generate``, ``generate_stream``, ``summarize`` (llm.py)
and ``distill.distill`` (the hot path the first draft missed).
"""

from __future__ import annotations

import pytest

import distill
import llm


@pytest.fixture(autouse=True)
def _reset_fallback_state(monkeypatch):
    """Each test starts with a fresh warn-once flag and a clean env."""
    monkeypatch.setattr(llm, "_warned_fallback", False)
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    monkeypatch.delenv("CONVMEM_FAIL_ON_FALLBACK", raising=False)
    monkeypatch.delenv("CONVMEM_FALLBACK_MODEL", raising=False)
    yield


def _stub_backends(monkeypatch):
    """Record which backend ran and with which model."""
    calls: dict[str, list[str]] = {"ollama": [], "deepseek": []}

    def _ollama(prompt, model, ollama_host, timeout=300):
        calls["ollama"].append(model)
        return f"ollama:{model}"

    def _deepseek(prompt, model, deepseek_base_url, timeout=300):
        calls["deepseek"].append(model)
        return f"deepseek:{model}"

    def _ollama_stream(prompt, model, ollama_host, *, stop=None, timeout=None):
        calls["ollama"].append(model)
        yield f"ollama:{model}"

    def _deepseek_stream(prompt, model, deepseek_base_url, *, stop=None, timeout=None):
        calls["deepseek"].append(model)
        yield f"deepseek:{model}"

    monkeypatch.setattr(llm, "_ollama_generate", _ollama)
    monkeypatch.setattr(llm, "_deepseek_generate", _deepseek)
    monkeypatch.setattr(llm, "_ollama_generate_stream", _ollama_stream)
    monkeypatch.setattr(llm, "_deepseek_generate_stream", _deepseek_stream)
    return calls


# --- generate --------------------------------------------------------------


def test_generate_no_key_warns_once(monkeypatch, capsys):
    calls = _stub_backends(monkeypatch)

    out1 = llm.generate("p", "deepseek-v4-flash", "http://h")
    out2 = llm.generate("p", "deepseek-v4-flash", "http://h")

    # Local fallback taken both times, DeepSeek never called.
    assert out1 == "ollama:llama3.1:8b"
    assert out2 == "ollama:llama3.1:8b"
    assert calls["deepseek"] == []
    assert calls["ollama"] == ["llama3.1:8b", "llama3.1:8b"]

    # Warn exactly once for the whole process, on stderr.
    err = capsys.readouterr().err
    assert err.count("DEEPSEEK_API_KEY") == 1
    assert "WARNING" in err


def test_generate_with_key_no_warning(monkeypatch, capsys):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-test")
    calls = _stub_backends(monkeypatch)

    out = llm.generate("p", "deepseek-v4-flash", "http://h")

    assert out == "deepseek:deepseek-v4-flash"
    assert calls["ollama"] == []
    assert capsys.readouterr().err == ""


def test_generate_non_deepseek_no_warning(monkeypatch, capsys):
    calls = _stub_backends(monkeypatch)

    out = llm.generate("p", "llama3.1:8b", "http://h")

    assert out == "ollama:llama3.1:8b"
    assert calls["deepseek"] == []
    assert capsys.readouterr().err == ""


def test_generate_fail_closed_does_not_call_local(monkeypatch):
    monkeypatch.setenv("CONVMEM_FAIL_ON_FALLBACK", "1")
    calls = _stub_backends(monkeypatch)

    with pytest.raises(llm.ModelFallbackError):
        llm.generate("p", "deepseek-v4-flash", "http://h")

    # Effect, not presence: the local backend must NOT have run.
    assert calls["ollama"] == []
    assert calls["deepseek"] == []


def test_generate_honors_custom_fallback_model(monkeypatch):
    monkeypatch.setenv("CONVMEM_FALLBACK_MODEL", "qwen2.5:7b")
    calls = _stub_backends(monkeypatch)

    out = llm.generate("p", "deepseek-v4-flash", "http://h")

    assert out == "ollama:qwen2.5:7b"
    assert calls["ollama"] == ["qwen2.5:7b"]


# --- generate_stream -------------------------------------------------------


def test_generate_stream_no_key_falls_back(monkeypatch, capsys):
    calls = _stub_backends(monkeypatch)

    tokens = list(llm.generate_stream("p", "deepseek-v4-flash", "http://h"))

    assert tokens == ["ollama:llama3.1:8b"]
    assert calls["deepseek"] == []
    assert capsys.readouterr().err.count("DEEPSEEK_API_KEY") == 1


def test_generate_stream_fail_closed_does_not_call_local(monkeypatch):
    monkeypatch.setenv("CONVMEM_FAIL_ON_FALLBACK", "1")
    calls = _stub_backends(monkeypatch)

    gen = llm.generate_stream("p", "deepseek-v4-flash", "http://h")
    # A generator: the raise surfaces on first iteration, not at call.
    with pytest.raises(llm.ModelFallbackError):
        list(gen)

    assert calls["ollama"] == []
    assert calls["deepseek"] == []


# --- summarize -------------------------------------------------------------


def test_summarize_no_key_falls_back_and_warns(monkeypatch, capsys):
    calls = _stub_backends(monkeypatch)

    out = llm.summarize("some chunk", "deepseek-v4-flash", "http://h")

    assert out == "ollama:llama3.1:8b"
    assert calls["deepseek"] == []
    assert capsys.readouterr().err.count("DEEPSEEK_API_KEY") == 1


def test_summarize_fail_closed_does_not_call_local(monkeypatch):
    monkeypatch.setenv("CONVMEM_FAIL_ON_FALLBACK", "1")
    calls = _stub_backends(monkeypatch)

    with pytest.raises(llm.ModelFallbackError):
        llm.summarize("some chunk", "deepseek-v4-flash", "http://h")

    assert calls["ollama"] == []


# --- distill.distill (the hot path the first draft missed) -----------------


def test_distill_no_key_warns_via_centralized_helper(monkeypatch, capsys):
    calls = _stub_backends(monkeypatch)
    # distill.generate is the llm.generate imported into distill's namespace.
    monkeypatch.setattr(distill, "safe_json_parse", lambda raw: [{"raw": raw}])

    out = distill.distill("chunk", "deepseek-v4-flash", "http://h")

    assert out == [{"raw": "ollama:llama3.1:8b"}]
    assert calls["deepseek"] == []
    assert capsys.readouterr().err.count("DEEPSEEK_API_KEY") == 1


def test_distill_fail_closed_does_not_call_local(monkeypatch):
    monkeypatch.setenv("CONVMEM_FAIL_ON_FALLBACK", "1")
    calls = _stub_backends(monkeypatch)
    monkeypatch.setattr(distill, "safe_json_parse", lambda raw: [{"raw": raw}])

    with pytest.raises(llm.ModelFallbackError):
        distill.distill("chunk", "deepseek-v4-flash", "http://h")

    assert calls["ollama"] == []

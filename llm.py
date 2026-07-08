"""LLM access: Ollama embeddings + provider-aware summarization.

Embeddings always run locally via Ollama (nomic-embed-text).

Summarization provider is inferred from the model name:
  - a name containing "deepseek-v4" -> DeepSeek API (needs DEEPSEEK_API_KEY)
  - anything else                   -> local Ollama model

This keeps the system local-first while leaving a one-line switch to the
DeepSeek API once a key is available.
"""

import json
import os
import sys
import threading
from collections.abc import Iterator

import requests

# Prompt is locked per the handoff — do not edit without escalation.
SUMMARIZE_PROMPT = """You are indexing an AI conversation for later retrieval.
Write exactly 3 sentences summarizing what was discussed and what was resolved or built.
Then list 5-8 topic keywords as a comma-separated line prefixed with "Keywords:".
Be specific: include tool names, file paths, model names, and technical terms.
Do not use vague phrases like "various topics" or "several issues."

Conversation:
{messages}"""

# Cap chunk text fed to the summarizer to keep latency and context bounded.
_MAX_CHUNK_CHARS = 8000


def ollama_embed(text: str, model: str, host: str) -> list[float]:
    """Return an embedding vector for `text` from a local Ollama model."""
    resp = requests.post(
        f"{host.rstrip('/')}/api/embeddings",
        json={"model": model, "prompt": text},
        timeout=120,
    )
    resp.raise_for_status()
    data = resp.json()
    embedding = data.get("embedding")
    if not embedding:
        raise RuntimeError(f"Empty embedding from Ollama for model {model!r}")
    return embedding


def _ollama_generate(prompt: str, model: str, host: str, *, timeout: float = 300) -> str:
    resp = requests.post(
        f"{host.rstrip('/')}/api/generate",
        json={
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {"num_ctx": 8192, "temperature": 0.2},
        },
        timeout=timeout,
    )
    resp.raise_for_status()
    return resp.json().get("response", "").strip()


def _deepseek_generate(
    prompt: str, model: str, base_url: str, *, timeout: float = 300
) -> str:
    api_key = os.environ.get("DEEPSEEK_API_KEY")
    if not api_key:
        raise RuntimeError(
            "summarize_model requests DeepSeek but DEEPSEEK_API_KEY is not set."
        )
    resp = requests.post(
        f"{base_url.rstrip('/')}/v1/chat/completions",
        headers={"Authorization": f"Bearer {api_key}"},
        json={
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.2,
            "stream": False,
        },
        timeout=timeout,
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"].strip()


def _check_stream_stop(stop: threading.Event | None, timeout: float | None) -> None:
    if stop is not None and stop.is_set():
        limit = timeout if timeout is not None else 0
        raise TimeoutError(f"synthesis exceeded {limit}s wall clock")


def _ollama_generate_stream(
    prompt: str,
    model: str,
    host: str,
    *,
    stop: threading.Event | None = None,
    timeout: float | None = None,
    connection_timeout: float = 10,
) -> Iterator[str]:
    resp = requests.post(
        f"{host.rstrip('/')}/api/generate",
        json={
            "model": model,
            "prompt": prompt,
            "stream": True,
            "options": {"num_ctx": 8192, "temperature": 0.2},
        },
        timeout=connection_timeout,
        stream=True,
    )
    resp.raise_for_status()
    for line in resp.iter_lines(decode_unicode=True):
        _check_stream_stop(stop, timeout)
        if not line:
            continue
        try:
            data = json.loads(line)
        except json.JSONDecodeError:
            continue
        chunk = (data.get("response") or "").strip("\0")
        if chunk:
            yield chunk
        if data.get("done"):
            break


def _deepseek_generate_stream(
    prompt: str,
    model: str,
    base_url: str,
    *,
    stop: threading.Event | None = None,
    timeout: float | None = None,
    connection_timeout: float = 10,
) -> Iterator[str]:
    api_key = os.environ.get("DEEPSEEK_API_KEY")
    if not api_key:
        raise RuntimeError(
            "summarize_model requests DeepSeek but DEEPSEEK_API_KEY is not set."
        )
    resp = requests.post(
        f"{base_url.rstrip('/')}/v1/chat/completions",
        headers={"Authorization": f"Bearer {api_key}"},
        json={
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.2,
            "stream": True,
        },
        timeout=connection_timeout,
        stream=True,
    )
    resp.raise_for_status()
    for line in resp.iter_lines(decode_unicode=True):
        _check_stream_stop(stop, timeout)
        if not line or not line.startswith("data: "):
            continue
        payload = line[6:].strip()
        if payload == "[DONE]":
            break
        try:
            data = json.loads(payload)
        except json.JSONDecodeError:
            continue
        choices = data.get("choices") or []
        if not choices:
            continue
        delta = choices[0].get("delta") or {}
        content = delta.get("content") or ""
        if content:
            yield content


class ModelFallbackError(RuntimeError):
    """Raised when a ``deepseek-v4`` model would silently fall back to a local
    model (no ``DEEPSEEK_API_KEY``) but ``CONVMEM_FAIL_ON_FALLBACK=1`` forbids
    the silent degrade. Opt-in fail-closed; default behavior is warn-and-continue."""


# Best-effort "warn once per process" so watch/refine don't spam the journal on
# a local-only setup. A rare duplicate across threads is acceptable.
_warned_fallback = False


def _resolve_fallback_model(configured_model: str) -> str:
    """Resolve the local model to use when a ``deepseek-v4`` model has no API key.

    This is the single source of truth for the provider fallback (Role 5 SRE:
    silent-degradation detection). Fail-closed when ``CONVMEM_FAIL_ON_FALLBACK=1``
    (raise, no silent degrade); otherwise warn once to stderr and return
    ``CONVMEM_FALLBACK_MODEL`` (default ``llama3.1:8b``). Only called on the
    genuine no-key fallback path.
    """
    global _warned_fallback
    fallback = os.environ.get("CONVMEM_FALLBACK_MODEL", "llama3.1:8b")
    if os.environ.get("CONVMEM_FAIL_ON_FALLBACK") == "1":
        raise ModelFallbackError(
            f"model {configured_model!r} needs DEEPSEEK_API_KEY (unset); "
            f"CONVMEM_FAIL_ON_FALLBACK=1 forbids the local fallback to {fallback!r}"
        )
    if not _warned_fallback:
        _warned_fallback = True
        print(
            f"convmem: WARNING - {configured_model!r} requested but DEEPSEEK_API_KEY "
            f"is unset; falling back to local {fallback!r} (degraded synthesis "
            f"quality). Set the key, or CONVMEM_FAIL_ON_FALLBACK=1 to fail instead.",
            file=sys.stderr,
        )
    return fallback


def generate_stream(
    prompt: str,
    model: str,
    ollama_host: str,
    deepseek_base_url: str = "https://api.deepseek.com",
    *,
    timeout: float | None = None,
) -> Iterator[str]:
    """Yield synthesis tokens. Raises TimeoutError when wall-clock limit hits."""
    stop = threading.Event()
    timer: threading.Timer | None = None
    if timeout is not None and timeout > 0:
        timer = threading.Timer(timeout, stop.set)
        timer.start()
    try:
        if "deepseek-v4" in model:
            api_key = os.environ.get("DEEPSEEK_API_KEY")
            if api_key:
                yield from _deepseek_generate_stream(
                    prompt,
                    model,
                    deepseek_base_url,
                    stop=stop,
                    timeout=timeout,
                )
                return
            model = _resolve_fallback_model(model)
        yield from _ollama_generate_stream(
            prompt, model, ollama_host, stop=stop, timeout=timeout
        )
    finally:
        if timer is not None:
            timer.cancel()


def generate(
    prompt: str,
    model: str,
    ollama_host: str,
    deepseek_base_url: str = "https://api.deepseek.com",
    *,
    timeout: float = 300,
) -> str:
    """Provider-aware text generation (summarization, distillation, etc.)."""
    if "deepseek-v4" in model:
        api_key = os.environ.get("DEEPSEEK_API_KEY")
        if api_key:
            return _deepseek_generate(
                prompt, model, deepseek_base_url, timeout=timeout
            )
        model = _resolve_fallback_model(model)
    return _ollama_generate(prompt, model, ollama_host, timeout=timeout)


def summarize(
    chunk_text: str,
    model: str,
    ollama_host: str,
    deepseek_base_url: str = "https://api.deepseek.com",
) -> str:
    """Summarize a conversation chunk into 3 sentences + a Keywords line."""
    if len(chunk_text) > _MAX_CHUNK_CHARS:
        chunk_text = chunk_text[:_MAX_CHUNK_CHARS]
    prompt = SUMMARIZE_PROMPT.format(messages=chunk_text)

    if "deepseek-v4" in model and os.environ.get("DEEPSEEK_API_KEY"):
        return _deepseek_generate(prompt, model, deepseek_base_url)
    if "deepseek-v4" in model:
        model = _resolve_fallback_model(model)
    return _ollama_generate(prompt, model, ollama_host)

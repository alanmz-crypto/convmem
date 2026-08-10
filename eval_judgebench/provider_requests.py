"""Hermetic provider request builders and drift validators.

These functions construct and validate request envelopes only.  They never
import a client, read a key, open a socket, retry, or fall back to another
model.
"""

from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from typing import Any


class ProviderPreflightError(ValueError):
    """A pinned provider request is missing a required invariant."""


DEEPSEEK_MAX_TOKENS = 4096
DEEPSEEK_MODELS = {"deepseek-v4-pro", "deepseek-v4-flash"}
LLAMA_MODEL = "llama3.1:8b"
LLAMA_DECODING = {
    "temperature": 0,
    "seed": 0,
    "top_p": 1,
    "num_ctx": 8192,
    "num_predict": 1024,
}


def deepseek_decoding_signature() -> dict[str, Any]:
    """Return recorded settings without pretending temperature is supported."""
    return {
        "thinking": "enabled",
        "reasoning_effort": "high",
        "response_mode": "json_object",
        "max_tokens": DEEPSEEK_MAX_TOKENS,
        "stream": False,
        "attempts": 1,
        "temperature": {"status": "unsupported", "behavior": "ignored"},
    }


def build_deepseek_request(
    prompt: str,
    *,
    model: str,
) -> dict[str, Any]:
    """Build the one permitted DeepSeek JSON-object request envelope."""
    request = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "thinking": {"type": "enabled"},
        "reasoning_effort": "high",
        "response_format": {"type": "json_object"},
        "max_tokens": DEEPSEEK_MAX_TOKENS,
        "stream": False,
        "attempts": 1,
    }
    validate_deepseek_request(request)
    return request


def validate_deepseek_request(request: Mapping[str, Any]) -> bool:
    """Fail closed on any DeepSeek setting drift; temperature is forbidden."""
    required = {
        "thinking",
        "reasoning_effort",
        "response_format",
        "max_tokens",
        "stream",
        "attempts",
    }
    if set(request) != required | {"model", "messages"}:
        raise ProviderPreflightError("DeepSeek request fields drifted")
    if request.get("model") not in DEEPSEEK_MODELS:
        raise ProviderPreflightError("DeepSeek model identity drifted")
    if request.get("thinking") != {"type": "enabled"}:
        raise ProviderPreflightError("DeepSeek thinking must be enabled")
    if request.get("reasoning_effort") != "high":
        raise ProviderPreflightError("DeepSeek reasoning_effort must be high")
    if request.get("response_format") != {"type": "json_object"}:
        raise ProviderPreflightError("DeepSeek response mode must be JSON object")
    if request.get("max_tokens") != DEEPSEEK_MAX_TOKENS:
        raise ProviderPreflightError("DeepSeek max_tokens drifted")
    if request.get("stream") is not False or request.get("attempts") != 1:
        raise ProviderPreflightError("DeepSeek must be non-streaming with one attempt")
    if "temperature" in request:
        raise ProviderPreflightError(
            "DeepSeek temperature is unsupported and must not be sent"
        )
    return True


def llama_decoding_signature(runtime_digest: str) -> dict[str, Any]:
    if not runtime_digest:
        raise ProviderPreflightError("Llama runtime digest is required")
    return {
        "model": LLAMA_MODEL,
        "runtime_digest": runtime_digest,
        **LLAMA_DECODING,
        "attempts": 1,
    }


def build_llama_request(
    prompt: str,
    *,
    runtime_digest: str,
    json_schema: Mapping[str, Any],
) -> dict[str, Any]:
    """Build the exact local Llama request plus its pinned runtime metadata."""
    if not runtime_digest:
        raise ProviderPreflightError("Llama runtime digest is required")
    request = {
        "model": LLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
        "format": deepcopy(dict(json_schema)),
        "options": deepcopy(LLAMA_DECODING),
        "runtime_digest": runtime_digest,
        "attempts": 1,
    }
    validate_llama_request(request, runtime_digest=runtime_digest)
    return request


def validate_llama_request(
    request: Mapping[str, Any],
    *,
    runtime_digest: str,
    expected_schema: Mapping[str, Any] | None = None,
) -> bool:
    """Fail closed on model, runtime, decoding, schema, or retry drift."""
    if not runtime_digest:
        raise ProviderPreflightError("Llama runtime digest is required")
    required = {
        "model",
        "prompt",
        "stream",
        "format",
        "options",
        "runtime_digest",
        "attempts",
    }
    if set(request) != required:
        raise ProviderPreflightError("Llama request fields drifted")
    if request.get("model") != LLAMA_MODEL:
        raise ProviderPreflightError("Llama model must be exactly llama3.1:8b")
    if request.get("stream") is not False or request.get("attempts") != 1:
        raise ProviderPreflightError("Llama must be non-streaming with one attempt")
    if request.get("runtime_digest") != runtime_digest:
        raise ProviderPreflightError("Llama runtime digest drifted")
    if request.get("options") != LLAMA_DECODING:
        raise ProviderPreflightError("Llama decoding settings drifted")
    if not isinstance(request.get("format"), dict):
        raise ProviderPreflightError("Llama response mode must be a JSON schema")
    if expected_schema is not None and request.get("format") != dict(expected_schema):
        raise ProviderPreflightError("Llama JSON schema drifted")
    return True


def validate_provider_request(
    provider: str, request: Mapping[str, Any], **kwargs: Any
) -> bool:
    """Common preflight entry point for callers that pin a provider family."""
    normalized = provider.strip().lower()
    if normalized == "deepseek":
        return validate_deepseek_request(request)
    if normalized in {"ollama", "llama"}:
        return validate_llama_request(request, **kwargs)
    raise ProviderPreflightError(f"unsupported provider family: {provider!r}")

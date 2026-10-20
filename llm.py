"""LLM access: Ollama embeddings + provider-aware summarization.

Embeddings always run locally via Ollama (nomic-embed-text).

Summarization provider is inferred from the model name:
  - a name containing "deepseek-v4" -> DeepSeek API (needs DEEPSEEK_API_KEY)
  - a name starting with "gpt-"     -> OpenAI API (needs OPENAI_API_KEY; never Ollama)
  - anything else                   -> local Ollama model

This keeps the system local-first while leaving a one-line switch to the
DeepSeek API once a key is available.
"""

import json
import os
import sys
import threading
import time
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Callable

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

PAID_PROVIDERS = frozenset({"deepseek", "openai"})

ProviderAttemptPermit = Callable[[dict[str, object]], None]
ProviderUsageReporter = Callable[[dict[str, object], dict[str, object]], None]
ProviderAttemptFinished = Callable[[dict[str, object], bool], None]
_PROVIDER_ATTEMPT_FINISHED: ContextVar[ProviderAttemptFinished | None] = ContextVar(
    "provider_attempt_finished", default=None
)
_PROVIDER_ATTEMPT_PERMIT: ContextVar[ProviderAttemptPermit | None] = ContextVar(
    "provider_attempt_permit", default=None
)
_PROVIDER_USAGE_REPORTER: ContextVar[ProviderUsageReporter | None] = ContextVar(
    "provider_usage_reporter", default=None
)


class ProviderAttemptBudgetExceeded(RuntimeError):
    """Raised before transport when a bootstrap HTTP-attempt cap is exhausted."""


class ModelFallbackError(RuntimeError):
    """Raised when a configured remote model cannot run (missing API key or
    ``CONVMEM_FAIL_ON_FALLBACK=1`` forbids silent local degrade)."""


def _compose_provider_usage_nested(
    inner: ProviderUsageReporter,
    outer: ProviderUsageReporter | None,
) -> ProviderUsageReporter:
    if outer is None:
        return inner

    def composed(event: dict[str, object], usage: dict[str, object]) -> None:
        inner(event, usage)
        outer(event, usage)

    return composed


def _compose_provider_attempt_finished_nested(
    inner: ProviderAttemptFinished | None,
    outer: ProviderAttemptFinished | None,
) -> ProviderAttemptFinished | None:
    if inner is None and outer is None:
        return None

    def composed(event: dict[str, object], success: bool) -> None:
        if inner is not None:
            inner(event, success)
        if outer is not None:
            outer(event, success)

    return composed


def _compose_provider_permit_nested(
    inner: ProviderAttemptPermit,
    inner_finished: ProviderAttemptFinished | None,
    outer: ProviderAttemptPermit | None,
    outer_finished: ProviderAttemptFinished | None,
) -> ProviderAttemptPermit:
    if outer is None:
        return inner

    def composed(event: dict[str, object]) -> None:
        ev = dict(event)
        settled: list[ProviderAttemptFinished | None] = []
        inner(ev)
        settled.append(inner_finished)
        try:
            outer(ev)
            settled.append(outer_finished)
        except Exception:
            for finished in settled:
                if finished is not None:
                    finished(ev, False)
            raise

    return composed


@contextmanager
def provider_http_accounting(
    permit: ProviderAttemptPermit,
    usage_reporter: ProviderUsageReporter,
    *,
    attempt_finished: ProviderAttemptFinished | None = None,
):
    """Install bootstrap-only HTTP accounting without changing ordinary calls."""

    outer_permit = _PROVIDER_ATTEMPT_PERMIT.get()
    outer_usage = _PROVIDER_USAGE_REPORTER.get()
    outer_finished = _PROVIDER_ATTEMPT_FINISHED.get()
    nested = (
        outer_permit is not None
        or outer_usage is not None
        or outer_finished is not None
    )
    if not nested:
        active_permit = permit
        active_usage = usage_reporter
        active_finished = attempt_finished
    else:
        active_permit = _compose_provider_permit_nested(
            permit,
            attempt_finished,
            outer_permit,
            outer_finished,
        )
        active_usage = _compose_provider_usage_nested(usage_reporter, outer_usage)
        active_finished = _compose_provider_attempt_finished_nested(
            attempt_finished,
            outer_finished,
        )

    permit_token = _PROVIDER_ATTEMPT_PERMIT.set(active_permit)
    usage_token = _PROVIDER_USAGE_REPORTER.set(active_usage)
    finished_token = _PROVIDER_ATTEMPT_FINISHED.set(active_finished)
    try:
        yield
    finally:
        _PROVIDER_ATTEMPT_FINISHED.reset(finished_token)
        _PROVIDER_USAGE_REPORTER.reset(usage_token)
        _PROVIDER_ATTEMPT_PERMIT.reset(permit_token)


def _permit_provider_http_attempt(
    *, provider: str, operation: str, model: str, base_url: str
) -> dict[str, object]:
    event: dict[str, object] = {
        "provider": provider,
        "operation": operation,
        "model": model,
        "base_url": base_url.rstrip("/"),
    }
    permit = _PROVIDER_ATTEMPT_PERMIT.get()
    if permit is not None:
        permit(dict(event))
    return event


def _finish_provider_http_attempt(event: dict[str, object], success: bool) -> None:
    """Settle a completed transport attempt independently of token-usage data."""
    reporter = _PROVIDER_ATTEMPT_FINISHED.get()
    if reporter is not None:
        reporter(dict(event), success)


def _report_provider_usage(
    event: dict[str, object], payload: dict[str, object]
) -> None:
    reporter = _PROVIDER_USAGE_REPORTER.get()
    if reporter is None:
        return
    usage = payload.get("usage")
    if isinstance(usage, dict):
        reporter(dict(event), dict(usage))
        return
    local_usage = {
        key: payload[key]
        for key in (
            "prompt_eval_count",
            "eval_count",
            "prompt_eval_duration",
            "eval_duration",
            "total_duration",
        )
        if key in payload
    }
    if local_usage:
        reporter(dict(event), local_usage)


def _is_openai_model(model: str) -> bool:
    return model.startswith("gpt-")


def _require_openai_key(model: str) -> str:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise ModelFallbackError(
            f"model {model!r} needs OPENAI_API_KEY (unset); "
            "OpenAI models never fall back to a local Ollama model"
        )
    return api_key


def resolve_generation_binding(model: str) -> dict[str, object]:
    """Describe the provider/model path selected by the generation contract.

    This is observational metadata only.  Actual generation continues through
    the existing provider fallback code below; this helper never elevates an
    origin or changes the selected model.
    """

    requested = str(model)
    if "deepseek-v4" in requested and os.environ.get("DEEPSEEK_API_KEY"):
        return {
            "provider": "deepseek",
            "requested_model": requested,
            "resolved_model": requested,
            "fallback": False,
        }
    if "deepseek-v4" in requested:
        return {
            "provider": "ollama",
            "requested_model": requested,
            "resolved_model": os.environ.get("CONVMEM_FALLBACK_MODEL", "llama3.1:8b"),
            "fallback": True,
        }
    if _is_openai_model(requested):
        has_key = bool(os.environ.get("OPENAI_API_KEY"))
        return {
            "provider": "openai",
            "requested_model": requested,
            "resolved_model": requested,
            "fallback": not has_key,
        }
    return {
        "provider": "ollama",
        "requested_model": requested,
        "resolved_model": requested,
        "fallback": False,
    }


def summarize_consumed_view(chunk_text: str) -> str:
    """Return the exact bounded text sent to the summarization provider."""

    return chunk_text[:_MAX_CHUNK_CHARS]


def summarize_prompt(chunk_text: str) -> str:
    """Return the exact summarization request prompt."""

    return SUMMARIZE_PROMPT.format(messages=summarize_consumed_view(chunk_text))


def ollama_embed(text: str, model: str, host: str) -> list[float]:
    """Return an embedding vector for `text` from a local Ollama model."""
    from purge_locks import reject_provider_under_write_scope

    reject_provider_under_write_scope()
    event = _permit_provider_http_attempt(
        provider="ollama",
        operation="embed",
        model=model,
        base_url=host,
    )
    resp = requests.post(
        f"{host.rstrip('/')}/api/embeddings",
        json={"model": model, "prompt": text},
        timeout=300,
    )
    resp.raise_for_status()
    data = resp.json()
    _report_provider_usage(event, data)
    embedding = data.get("embedding")
    if not embedding:
        raise RuntimeError(f"Empty embedding from Ollama for model {model!r}")
    return embedding


def _ollama_generate(prompt: str, model: str, host: str, *, timeout: float = 300) -> str:
    event = _permit_provider_http_attempt(
        provider="ollama",
        operation="generate",
        model=model,
        base_url=host,
    )
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
    data = resp.json()
    _report_provider_usage(event, data)
    return data.get("response", "").strip()


def _post_deepseek(
    prompt: str,
    model: str,
    base_url: str,
    api_key: str,
    *,
    stream: bool,
    timeout: float,
) -> requests.Response:
    """POST a DeepSeek chat completion; raise on non-2xx. Shared by stream/generate."""
    event = _permit_provider_http_attempt(
        provider="deepseek",
        operation="generate_stream" if stream else "generate",
        model=model,
        base_url=base_url,
    )
    body: dict = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.2,
        "stream": stream,
    }
    try:
        resp = requests.post(
            f"{base_url.rstrip('/')}/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}"},
            json=body,
            timeout=timeout,
            allow_redirects=False,
            **({"stream": True} if stream else {}),
        )
        resp.raise_for_status()
    except Exception:
        _finish_provider_http_attempt(event, False)
        raise
    _finish_provider_http_attempt(event, True)
    setattr(resp, "_convmem_provider_event", event)
    return resp


def _post_openai(
    prompt: str,
    model: str,
    base_url: str,
    api_key: str,
    *,
    stream: bool,
    timeout: float,
    reasoning_effort: str | None = None,
) -> requests.Response:
    """POST an OpenAI chat completion; raise on non-2xx."""
    event = _permit_provider_http_attempt(
        provider="openai",
        operation="generate_stream" if stream else "generate",
        model=model,
        base_url=base_url,
    )
    body: dict = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "stream": stream,
    }
    if reasoning_effort:
        body["reasoning_effort"] = reasoning_effort
    else:
        body["temperature"] = 0.2
    try:
        resp = requests.post(
            f"{base_url.rstrip('/')}/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}"},
            json=body,
            timeout=timeout,
            allow_redirects=False,
            **({"stream": True} if stream else {}),
        )
        resp.raise_for_status()
    except Exception:
        _finish_provider_http_attempt(event, False)
        raise
    _finish_provider_http_attempt(event, True)
    setattr(resp, "_convmem_provider_event", event)
    return resp


def _deepseek_retry_decision(
    exc: BaseException,
    *,
    attempt: int,
    effective: int,
    retry_backoff: float,
    label: str,
    yielded_any: bool = False,
) -> None:
    """Backoff/sleep for a transient error or raise when retry is exhausted/forbidden.

    Retries ConnectionError/Timeout (plus 5xx). Streaming additionally refuses to
    retry once any token was yielded (yielded_any). 4xx is never retried.
    """
    events: tuple[type[BaseException], ...] = (
        requests.exceptions.ConnectionError,
        requests.exceptions.Timeout,
    )
    if isinstance(exc, requests.exceptions.HTTPError):
        status = exc.response.status_code if exc.response is not None else None  # type: ignore[union-attr]
        if status is None or status < 500:
            raise exc
    elif not isinstance(exc, events):
        raise exc
    if yielded_any or attempt >= effective:
        raise exc
    sys.stderr.write(
        f"[llm] DeepSeek {label} attempt {attempt} failed before a complete "
        f"response; retrying (attempt {attempt + 1}/{effective})\n"
    )
    time.sleep(retry_backoff * attempt)


def _deepseek_generate(
    prompt: str,
    model: str,
    base_url: str,
    *,
    timeout: float = 300,
    max_attempts: int = 2,
    retry_backoff: float = 1.0,
) -> str:
    """Non-streaming DeepSeek completion with a bounded transient retry."""
    api_key = os.environ.get("DEEPSEEK_API_KEY")
    if not api_key:
        raise RuntimeError(
            "summarize_model requests DeepSeek but DEEPSEEK_API_KEY is not set."
        )
    effective = max(1, int(max_attempts))
    for attempt in range(1, effective + 1):
        try:
            resp = _post_deepseek(
                prompt, model, base_url, api_key, stream=False, timeout=timeout
            )
            data = resp.json()
            event = getattr(resp, "_convmem_provider_event", {})
            _report_provider_usage(event, data)
            return data["choices"][0]["message"]["content"].strip()
        except (
            requests.exceptions.ConnectionError,
            requests.exceptions.Timeout,
            requests.exceptions.HTTPError,
        ) as exc:
            _deepseek_retry_decision(
                exc,
                attempt=attempt,
                effective=effective,
                retry_backoff=retry_backoff,
                label="generate",
            )
    raise RuntimeError("unreachable: retry loop must return or raise")


def _openai_generate(
    prompt: str,
    model: str,
    base_url: str,
    *,
    reasoning_effort: str | None = None,
    timeout: float = 300,
    max_attempts: int = 2,
    retry_backoff: float = 1.0,
) -> str:
    """Non-streaming OpenAI completion with a bounded transient retry."""
    api_key = _require_openai_key(model)
    effective = max(1, int(max_attempts))
    for attempt in range(1, effective + 1):
        try:
            resp = _post_openai(
                prompt,
                model,
                base_url,
                api_key,
                stream=False,
                timeout=timeout,
                reasoning_effort=reasoning_effort,
            )
            data = resp.json()
            event = getattr(resp, "_convmem_provider_event", {})
            _report_provider_usage(event, data)
            return data["choices"][0]["message"]["content"].strip()
        except (
            requests.exceptions.ConnectionError,
            requests.exceptions.Timeout,
            requests.exceptions.HTTPError,
        ) as exc:
            _deepseek_retry_decision(
                exc,
                attempt=attempt,
                effective=effective,
                retry_backoff=retry_backoff,
                label="generate",
            )
    raise RuntimeError("unreachable: retry loop must return or raise")


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
    event = _permit_provider_http_attempt(
        provider="ollama",
        operation="generate_stream",
        model=model,
        base_url=host,
    )
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
            _report_provider_usage(event, data)
            break


def _deepseek_generate_stream(
    prompt: str,
    model: str,
    base_url: str,
    *,
    stop: threading.Event | None = None,
    timeout: float | None = None,
    connection_timeout: float = 10,
    max_attempts: int = 2,
    retry_backoff: float = 1.0,
) -> Iterator[str]:
    """Stream DeepSeek completion tokens with a bounded transient retry.

    The DeepSeek API intermittently drops streaming responses (urllib3
    "Response ended prematurely", 5xx, timeouts) before emitting any token.
    When nothing has been yielded, retry up to ``max_attempts - 1`` extra times
    with a short backoff, so a single transient drop does not degrade the answer
    to citations-only. If any content token has already been yielded, the failure
    is propagated to the caller's partial-buffer path (no re-stream on top of
    partial output). 4xx auth errors are never retried.
    """
    api_key = os.environ.get("DEEPSEEK_API_KEY")
    if not api_key:
        raise RuntimeError(
            "summarize_model requests DeepSeek but DEEPSEEK_API_KEY is not set."
        )
    effective = max(1, int(max_attempts))
    for attempt in range(1, effective + 1):
        yielded_any = False
        try:
            resp = _post_deepseek(
                prompt,
                model,
                base_url,
                api_key,
                stream=True,
                timeout=connection_timeout or 0,
            )
            final_usage: dict[str, object] = {}
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
                if isinstance(data.get("usage"), dict):
                    final_usage = dict(data["usage"])
                if not choices:
                    continue
                delta = choices[0].get("delta") or {}
                content = delta.get("content") or ""
                if content:
                    yielded_any = True
                    yield content
            if final_usage:
                event = getattr(resp, "_convmem_provider_event", {})
                reporter = _PROVIDER_USAGE_REPORTER.get()
                if reporter is not None:
                    reporter(dict(event), final_usage)
            return
        except (
            requests.exceptions.ConnectionError,
            requests.exceptions.Timeout,
            requests.exceptions.HTTPError,
        ) as exc:
            _deepseek_retry_decision(
                exc,
                attempt=attempt,
                effective=effective,
                retry_backoff=retry_backoff,
                label="stream",
                yielded_any=yielded_any,
            )


def _openai_generate_stream(  # pylint: disable=too-many-arguments
    prompt: str,
    model: str,
    base_url: str,
    *,
    reasoning_effort: str | None = None,
    stop: threading.Event | None = None,
    timeout: float | None = None,
    connection_timeout: float = 10,
    max_attempts: int = 2,
    retry_backoff: float = 1.0,
) -> Iterator[str]:
    """Stream OpenAI completion tokens with a bounded transient retry."""
    api_key = _require_openai_key(model)
    effective = max(1, int(max_attempts))
    for attempt in range(1, effective + 1):
        yielded_any = False
        try:
            resp = _post_openai(
                prompt,
                model,
                base_url,
                api_key,
                stream=True,
                timeout=connection_timeout or 0,
                reasoning_effort=reasoning_effort,
            )
            final_usage: dict[str, object] = {}
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
                if isinstance(data.get("usage"), dict):
                    final_usage = dict(data["usage"])
                if not choices:
                    continue
                delta = choices[0].get("delta") or {}
                content = delta.get("content") or ""
                if content:
                    yielded_any = True
                    yield content
            if final_usage:
                event = getattr(resp, "_convmem_provider_event", {})
                _report_provider_usage(event, final_usage)
            return
        except (
            requests.exceptions.ConnectionError,
            requests.exceptions.Timeout,
            requests.exceptions.HTTPError,
        ) as exc:
            _deepseek_retry_decision(
                exc,
                attempt=attempt,
                effective=effective,
                retry_backoff=retry_backoff,
                label="stream",
                yielded_any=yielded_any,
            )


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


def generate_stream(  # pylint: disable=too-many-arguments
    prompt: str,
    model: str,
    ollama_host: str,
    deepseek_base_url: str = "https://api.deepseek.com",
    *,
    openai_base_url: str = "https://api.openai.com",
    reasoning_effort: str | None = None,
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
        if _is_openai_model(model):
            yield from _openai_generate_stream(
                prompt,
                model,
                openai_base_url,
                reasoning_effort=reasoning_effort,
                stop=stop,
                timeout=timeout,
            )
            return
        yield from _ollama_generate_stream(
            prompt, model, ollama_host, stop=stop, timeout=timeout
        )
    finally:
        if timer is not None:
            timer.cancel()


def generate(  # pylint: disable=too-many-arguments
    prompt: str,
    model: str,
    ollama_host: str,
    deepseek_base_url: str = "https://api.deepseek.com",
    *,
    openai_base_url: str = "https://api.openai.com",
    reasoning_effort: str | None = None,
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
    if _is_openai_model(model):
        return _openai_generate(
            prompt,
            model,
            openai_base_url,
            reasoning_effort=reasoning_effort,
            timeout=timeout,
        )
    return _ollama_generate(prompt, model, ollama_host, timeout=timeout)


def summarize(
    chunk_text: str,
    model: str,
    ollama_host: str,
    deepseek_base_url: str = "https://api.deepseek.com",
    *,
    openai_base_url: str = "https://api.openai.com",
) -> str:
    """Summarize a conversation chunk into 3 sentences + a Keywords line."""
    from purge_locks import reject_provider_under_write_scope

    reject_provider_under_write_scope()
    prompt = summarize_prompt(chunk_text)

    if "deepseek-v4" in model and os.environ.get("DEEPSEEK_API_KEY"):
        return _deepseek_generate(prompt, model, deepseek_base_url, timeout=120)
    if "deepseek-v4" in model:
        model = _resolve_fallback_model(model)
    if _is_openai_model(model):
        return _openai_generate(prompt, model, openai_base_url, timeout=120)
    return _ollama_generate(prompt, model, ollama_host)

# ref: ./incremental_jsonl_cohort_budget.py — transport completion settles paid reservations

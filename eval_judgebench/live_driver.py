"""Zero-call-ready live transports for the locked JudgeBench boundary.

The public entry point is :func:`run_live_calibration`.  It accepts only one
of the three explicitly pinned candidates, resolves the local Llama metadata
with GET requests before constructing a generation transport, and delegates
all corpus, prompt, identity, request, and comparison-signature preflight to
``run_calibration``.  This module has no CLI and creates no result files.

Tests should pass a fake ``HttpClient``.  The default requests client is
provided for the separately authorized experiment, not used by this package's
tests.
"""

from __future__ import annotations

import copy
import hashlib
import json
import time
from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any, Protocol

import requests

from eval_judgebench.calibration import (
    MAX_CALIBRATION_CALLS,
    CalibrationBoundaryError,
    build_calibration_provider_requests,
    load_calibration_package,
    run_calibration,
)
from eval_judgebench.metrics import build_calibration_report
from eval_judgebench.provider_requests import (
    DEEPSEEK_MAX_TOKENS,
    LLAMA_MODEL,
    ProviderTransportResult,
    build_deepseek_request,
    build_deepseek_wire_request,
    build_llama_request,
    build_llama_wire_request,
    deepseek_decoding_signature,
    llama_decoding_signature,
    validate_deepseek_request,
    validate_deepseek_wire_request,
    validate_llama_request,
    validate_llama_wire_request,
)
from eval_judgebench.prompt_wrappers import semantic_output_schema
from eval_provenance import comparison_signature_digest

SUPPORTED_CANDIDATES = {
    "deepseek-v4-pro": "deepseek",
    "deepseek-v4-flash": "deepseek",
    LLAMA_MODEL: "llama",
}


class LiveDriverConfigurationError(CalibrationBoundaryError):
    """The live driver was not given an exact, safe configuration."""


class RemoteCostConfigurationError(LiveDriverConfigurationError):
    """Remote pricing or the explicit cost ceiling is unavailable/unsafe."""


class LlamaRuntimeError(LiveDriverConfigurationError):
    """The pinned local model digest or serving runtime cannot be established."""


class HttpResponse(Protocol):
    """Small response surface used by both mocked and real HTTP clients."""

    def raise_for_status(self) -> None: ...

    def json(self) -> Any: ...


class HttpClient(Protocol):
    """HTTP surface; one call here means one attempted provider transport."""

    def get(self, url: str, **kwargs: Any) -> HttpResponse: ...

    def post(self, url: str, **kwargs: Any) -> HttpResponse: ...


@dataclass(frozen=True)
class RemotePriceBasis:
    """Operator-pinned remote price input; no provider price is guessed."""

    cache_miss_input_usd_per_million_tokens: Decimal
    output_usd_per_million_tokens: Decimal
    source: str
    effective_at: str

    def __post_init__(self) -> None:
        for label, value in (
            ("cache-miss input", self.cache_miss_input_usd_per_million_tokens),
            ("output", self.output_usd_per_million_tokens),
        ):
            if value < 0:
                raise RemoteCostConfigurationError(f"remote {label} price cannot be negative")
        if not self.source.strip() or not self.effective_at.strip():
            raise RemoteCostConfigurationError(
                "remote price basis requires source and effective_at"
            )


@dataclass(frozen=True)
class LlamaRuntimeEvidence:
    """Separate model-weight identity from the serving-runtime identity."""

    model: str
    model_digest: str
    serving_runtime: str
    serving_runtime_version: str


@dataclass(frozen=True)
class LiveCalibrationResult:
    """In-memory deterministic report plus bounded transport evidence."""

    run: Any
    report: dict[str, Any]
    transport_evidence: tuple[dict[str, Any], ...]
    llama_runtime: LlamaRuntimeEvidence | None
    remote_price_basis: RemotePriceBasis | None
    maximum_remote_cost_usd: Decimal | None


class RequestsHttpClient:
    """Explicit opt-in Requests transport for the authorized live run."""

    def __init__(self) -> None:
        self._session = requests.Session()

    def get(self, url: str, **kwargs: Any) -> HttpResponse:
        return self._session.get(url, **kwargs)

    def post(self, url: str, **kwargs: Any) -> HttpResponse:
        return self._session.post(url, **kwargs)


def _json_object(response: HttpResponse, label: str) -> dict[str, Any]:
    response.raise_for_status()
    value = response.json()
    if not isinstance(value, dict):
        raise LiveDriverConfigurationError(f"{label} response must be an object")
    return value


def resolve_llama_runtime(
    client: HttpClient,
    *,
    host: str,
    expected_model_digest: str | None = None,
    expected_runtime_version: str | None = None,
) -> LlamaRuntimeEvidence:
    """Read Ollama tags/version only; never call a generation endpoint."""
    base = host.rstrip("/")
    tags = _json_object(client.get(f"{base}/api/tags", timeout=5), "Ollama tags")
    matches = [
        item
        for item in tags.get("models") or []
        if isinstance(item, Mapping)
        and (item.get("name") == LLAMA_MODEL or item.get("model") == LLAMA_MODEL)
    ]
    if len(matches) != 1:
        raise LlamaRuntimeError(
            "Ollama must expose exactly one installed llama3.1:8b metadata row"
        )
    model_digest = str(matches[0].get("digest") or "")
    if not model_digest:
        raise LlamaRuntimeError("Ollama llama3.1:8b model digest is unavailable")
    version = _json_object(
        client.get(f"{base}/api/version", timeout=5), "Ollama version"
    )
    runtime_version = str(version.get("version") or "")
    if not runtime_version:
        raise LlamaRuntimeError("Ollama serving-runtime version is unavailable")
    if expected_model_digest is not None and model_digest != expected_model_digest:
        raise LlamaRuntimeError("installed Llama model digest drifted")
    if expected_runtime_version is not None and runtime_version != expected_runtime_version:
        raise LlamaRuntimeError("Ollama serving-runtime version drifted")
    return LlamaRuntimeEvidence(
        model=LLAMA_MODEL,
        model_digest=model_digest,
        serving_runtime="ollama",
        serving_runtime_version=runtime_version,
    )


def _usage(value: Any, *, required: bool) -> dict[str, int] | None:
    if not isinstance(value, Mapping):
        if required:
            raise LiveDriverConfigurationError("remote provider usage metadata is required")
        return None
    input_tokens = value.get("prompt_tokens", value.get("input_tokens"))
    output_tokens = value.get("completion_tokens", value.get("output_tokens"))
    if not isinstance(input_tokens, int) or isinstance(input_tokens, bool):
        if required:
            raise LiveDriverConfigurationError("remote input-token metadata is required")
        return None
    if not isinstance(output_tokens, int) or isinstance(output_tokens, bool):
        if required:
            raise LiveDriverConfigurationError("remote output-token metadata is required")
        return None
    if input_tokens < 0 or output_tokens < 0:
        raise LiveDriverConfigurationError("provider token metadata cannot be negative")
    return {"prompt_tokens": input_tokens, "completion_tokens": output_tokens}


def _response_hash(envelope: Mapping[str, Any]) -> str:
    payload = json.dumps(envelope, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class _DeepSeekTransport:
    def __init__(
        self,
        client: HttpClient,
        *,
        base_url: str,
        api_key: str,
        model: str,
        budget: "_RemoteBudget",
    ) -> None:
        if not api_key.strip():
            raise LiveDriverConfigurationError("DeepSeek API key must be supplied explicitly")
        self._client = client
        self._url = f"{base_url.rstrip('/')}/v1/chat/completions"
        self._api_key = api_key
        self._model = model
        self._budget = budget

    def __call__(self, request: Mapping[str, Any]) -> ProviderTransportResult:
        validate_deepseek_request(request)
        if request.get("model") != self._model:
            raise LiveDriverConfigurationError("DeepSeek request model drifted")
        wire_request = build_deepseek_wire_request(request)
        validate_deepseek_wire_request(wire_request)
        self._budget.before_call()
        started = time.monotonic()
        response = self._client.post(
            self._url,
            headers={"Authorization": f"Bearer {self._api_key}"},
            json=wire_request,
            timeout=300,
        )
        envelope = _json_object(response, "DeepSeek")
        latency_ms = (time.monotonic() - started) * 1000
        if envelope.get("model") != self._model:
            raise LiveDriverConfigurationError("DeepSeek response model drifted")
        usage = _usage(envelope.get("usage"), required=True)
        assert usage is not None
        cost = self._budget.record(usage)
        return ProviderTransportResult(
            envelope=envelope,
            provider="deepseek",
            model=self._model,
            latency_ms=latency_ms,
            usage=usage,
            cost=float(cost),
        )


class _LlamaTransport:
    def __init__(self, client: HttpClient, *, host: str, runtime: LlamaRuntimeEvidence) -> None:
        self._client = client
        self._url = f"{host.rstrip('/')}/api/generate"
        self._runtime = runtime

    def __call__(self, request: Mapping[str, Any]) -> ProviderTransportResult:
        validate_llama_request(
            request,
            runtime_digest=self._runtime.model_digest,
            expected_schema=semantic_output_schema(),
        )
        wire_request = build_llama_wire_request(request)
        validate_llama_wire_request(wire_request)
        started = time.monotonic()
        response = self._client.post(
            self._url,
            json=wire_request,
            timeout=300,
        )
        envelope = _json_object(response, "Ollama")
        latency_ms = (time.monotonic() - started) * 1000
        if envelope.get("model") != LLAMA_MODEL:
            raise LiveDriverConfigurationError("Ollama response model drifted")
        usage = _usage(
            {
                "prompt_tokens": envelope.get("prompt_eval_count"),
                "completion_tokens": envelope.get("eval_count"),
            },
            required=False,
        )
        return ProviderTransportResult(
            envelope=envelope,
            provider="llama",
            model=LLAMA_MODEL,
            latency_ms=latency_ms,
            usage=usage,
            runtime_version=self._runtime.serving_runtime_version,
        )


class _RemoteBudget:  # pylint: disable=too-many-instance-attributes
    def __init__(
        self,
        *,
        ceiling: Decimal,
        price_basis: RemotePriceBasis,
        input_token_bounds: tuple[int, ...],
        caller_input_token_ceiling: int,
    ) -> None:
        if ceiling <= 0:
            raise RemoteCostConfigurationError("remote cost ceiling must be positive")
        if not input_token_bounds or len(input_token_bounds) != MAX_CALIBRATION_CALLS:
            raise RemoteCostConfigurationError(
                "exactly 20 locked request input bounds are required"
            )
        if caller_input_token_ceiling <= 0:
            raise RemoteCostConfigurationError(
                "caller input-token ceiling must be positive"
            )
        self.input_token_bounds = input_token_bounds
        self.input_token_bound = sum(input_token_bounds)
        if self.input_token_bound > caller_input_token_ceiling:
            raise RemoteCostConfigurationError(
                "20-call request input bound exceeds the caller input-token ceiling"
            )
        self.ceiling = ceiling
        self.price_basis = price_basis
        self.caller_input_token_ceiling = caller_input_token_ceiling
        self.total = Decimal("0")
        self.calls = 0
        self.maximum_total = self.maximum_cost()
        if self.maximum_total > ceiling:
            raise RemoteCostConfigurationError(
                "20-call worst-case remote cost exceeds the explicit ceiling"
            )

    def maximum_cost(self) -> Decimal:
        return (
            Decimal(self.input_token_bound)
            * self.price_basis.cache_miss_input_usd_per_million_tokens
            + Decimal(MAX_CALIBRATION_CALLS * DEEPSEEK_MAX_TOKENS)
            * self.price_basis.output_usd_per_million_tokens
        ) / Decimal(1_000_000)

    def maximum_remaining_cost(self) -> Decimal:
        remaining_input = sum(self.input_token_bounds[self.calls :])
        remaining_output = (MAX_CALIBRATION_CALLS - self.calls) * DEEPSEEK_MAX_TOKENS
        return (
            Decimal(remaining_input)
            * self.price_basis.cache_miss_input_usd_per_million_tokens
            + Decimal(remaining_output)
            * self.price_basis.output_usd_per_million_tokens
        ) / Decimal(1_000_000)

    def before_call(self) -> None:
        if self.calls >= MAX_CALIBRATION_CALLS:
            raise RemoteCostConfigurationError("remote 20-call cap exceeded")
        if self.total + self.maximum_remaining_cost() > self.ceiling:
            raise RemoteCostConfigurationError("remote cost ceiling would be exceeded")
        self.calls += 1

    def record(self, usage: Mapping[str, int]) -> Decimal:
        cost = (
            Decimal(int(usage["prompt_tokens"]))
            * self.price_basis.cache_miss_input_usd_per_million_tokens
            + Decimal(int(usage["completion_tokens"]))
            * self.price_basis.output_usd_per_million_tokens
        ) / Decimal(1_000_000)
        self.total += cost
        if self.total > self.ceiling:
            raise RemoteCostConfigurationError("remote cost ceiling exceeded")
        return cost


def _decimal(value: Any, label: str) -> Decimal:
    try:
        result = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise RemoteCostConfigurationError(f"invalid {label}") from exc
    if not result.is_finite() or result < 0:
        raise RemoteCostConfigurationError(f"invalid {label}")
    return result


def _price_basis(value: RemotePriceBasis | Mapping[str, Any] | None) -> RemotePriceBasis:
    if isinstance(value, RemotePriceBasis):
        return value
    if not isinstance(value, Mapping):
        raise RemoteCostConfigurationError(
            "remote pricing is required; unknown pricing cannot be guessed"
        )
    return RemotePriceBasis(
        cache_miss_input_usd_per_million_tokens=_decimal(
            value.get("cache_miss_input_usd_per_million_tokens"),
            "DeepSeek cache-miss input price",
        ),
        output_usd_per_million_tokens=_decimal(
            value.get("output_usd_per_million_tokens"), "remote output price"
        ),
        source=str(value.get("source") or ""),
        effective_at=str(value.get("effective_at") or ""),
    )


def _serialized_request_bytes(request: Mapping[str, Any]) -> int:
    """Return a conservative UTF-8 byte/token ceiling for one wire request."""
    serialized = json.dumps(
        request, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    )
    return len(serialized.encode("utf-8"))


def _reject_retry_or_fallback(cfg: Mapping[str, Any]) -> None:
    section = cfg.get("judgebench") or {}
    if not isinstance(section, Mapping):
        raise LiveDriverConfigurationError("judgebench configuration must be an object")
    for key in ("fallback", "fallback_model", "fallback_provider"):
        if section.get(key):
            raise LiveDriverConfigurationError(f"{key} is forbidden for canonical calibration")
    if section.get("retries", 0) not in (0, None):
        raise LiveDriverConfigurationError("retries are forbidden for canonical calibration")
    for key in ("attempts", "max_attempts"):
        if section.get(key, 1) != 1:
            raise LiveDriverConfigurationError("canonical calibration requires exactly one attempt")


def _reject_model_drift(cfg: Mapping[str, Any], candidate_model: str) -> None:
    models = cfg.get("models") or {}
    if not isinstance(models, Mapping):
        raise LiveDriverConfigurationError("models configuration must be an object")
    configured = models.get("distill_model")
    if configured is not None and str(configured).strip() != candidate_model:
        raise LiveDriverConfigurationError("configured candidate model drifted")


def _reject_provider_drift(
    cfg: Mapping[str, Any],
    *,
    family: str,
    request: Mapping[str, Any],
    settings: Mapping[str, Any],
) -> None:
    """Reject stale provider pins instead of silently replacing them."""
    section = cfg.get("judgebench") or {}
    configured_provider = section.get("provider")
    if configured_provider is not None and str(configured_provider).strip().lower() != family:
        raise LiveDriverConfigurationError("configured provider drifted")
    configured_request = section.get("provider_request")
    if (
        configured_request is not None
        and (
            not isinstance(configured_request, Mapping)
            or dict(configured_request) != dict(request)
        )
    ):
        raise LiveDriverConfigurationError("configured provider request drifted")
    configured_settings = section.get("provider_settings")
    if (
        configured_settings is not None
        and (
            not isinstance(configured_settings, Mapping)
            or dict(configured_settings) != dict(settings)
        )
    ):
        raise LiveDriverConfigurationError("configured provider settings drifted")


def run_live_calibration(  # pylint: disable=too-many-arguments,too-many-locals
    corpus_dir: str,
    *,
    cfg: dict[str, Any],
    candidate_model: str,
    under_test_model: str,
    registry_path: str,
    expected_full_hashes: Mapping[str, str],
    expected_rubric_hashes: Mapping[str, str],
    expected_prompt_wrapper_hash: str,
    expected_comparison_signature: dict[str, Any],
    http_client: HttpClient,
    deepseek_api_key: str | None = None,
    deepseek_base_url: str = "https://api.deepseek.com",
    ollama_host: str = "http://localhost:11434",
    remote_cost_ceiling_usd: Decimal | str | float | None = None,
    remote_price_basis: RemotePriceBasis | Mapping[str, Any] | None = None,
    max_input_tokens: int | None = None,
    expected_llama_model_digest: str | None = None,
    expected_llama_runtime_version: str | None = None,
) -> LiveCalibrationResult:
    """Run one explicitly configured candidate through the Phase A boundary.

    The function is intentionally the only live-driver interface.  It always
    uses canonical ``run_calibration`` and returns in-memory data only.  A
    caller must supply exact corpus/rubric/prompt/signature locks and, for a
    remote candidate, a pinned cache-miss price basis, an explicit 20-call
    worst-case cost ceiling, and a total input-token ceiling at least as large
    as the serialized-byte bound computed from the locked wire requests.
    """
    if candidate_model not in SUPPORTED_CANDIDATES:
        raise LiveDriverConfigurationError("candidate model is not one of the three pinned models")
    _reject_model_drift(cfg, candidate_model)
    _reject_retry_or_fallback(cfg)
    package = load_calibration_package(
        corpus_dir,
        expected_full_hashes=expected_full_hashes,
        expected_rubric_hashes=expected_rubric_hashes,
    )
    family = SUPPORTED_CANDIDATES[candidate_model]
    client = http_client
    llama_runtime: LlamaRuntimeEvidence | None = None
    budget: _RemoteBudget | None = None
    price: RemotePriceBasis | None = None
    if family == "deepseek":
        price = _price_basis(remote_price_basis)
        if remote_cost_ceiling_usd is None or max_input_tokens is None:
            raise RemoteCostConfigurationError(
                "remote cost ceiling and max_input_tokens are required"
            )
        provider_request = build_deepseek_request("preflight-only", model=candidate_model)
        provider_settings = deepseek_decoding_signature()
        runtime_version = str((cfg.get("judgebench") or {}).get("runtime_version") or "")
    else:
        # This function performs two GETs and no POST.  Generation is impossible
        # until a complete model digest and serving-runtime version are present.
        if not str(expected_llama_model_digest or "").strip():
            raise LlamaRuntimeError(
                "expected Llama model digest is required for a canonical run"
            )
        if not str(expected_llama_runtime_version or "").strip():
            raise LlamaRuntimeError(
                "expected Ollama runtime version is required for a canonical run"
            )
        llama_runtime = resolve_llama_runtime(
            client,
            host=ollama_host,
            expected_model_digest=expected_llama_model_digest,
            expected_runtime_version=expected_llama_runtime_version,
        )
        provider_settings = llama_decoding_signature(llama_runtime.model_digest)
        provider_request = build_llama_request(
            "preflight-only",
            runtime_digest=llama_runtime.model_digest,
            json_schema=semantic_output_schema(),
        )
        validate_llama_request(
            provider_request,
            runtime_digest=llama_runtime.model_digest,
            expected_schema=semantic_output_schema(),
        )
        runtime_version = llama_runtime.serving_runtime_version

    _reject_provider_drift(
        cfg,
        family=family,
        request=provider_request,
        settings=provider_settings,
    )

    exact_requests = build_calibration_provider_requests(
        package,
        family=family,
        judge_model=candidate_model,
        decoding=provider_settings,
    )
    if len(exact_requests) != MAX_CALIBRATION_CALLS:
        raise LiveDriverConfigurationError(
            "locked calibration request set must contain exactly 20 envelopes"
        )
    if family == "deepseek":
        wire_requests = tuple(
            build_deepseek_wire_request(request) for request in exact_requests
        )
        input_token_bounds = tuple(
            _serialized_request_bytes(request) for request in wire_requests
        )
        if not isinstance(max_input_tokens, int) or isinstance(max_input_tokens, bool):
            raise RemoteCostConfigurationError(
                "max_input_tokens must be an integer total ceiling"
            )
        budget = _RemoteBudget(
            ceiling=_decimal(remote_cost_ceiling_usd, "remote cost ceiling"),
            price_basis=price,
            input_token_bounds=input_token_bounds,
            caller_input_token_ceiling=max_input_tokens,
        )
        transport: Any = _DeepSeekTransport(
            client,
            base_url=deepseek_base_url,
            api_key=deepseek_api_key or "",
            model=candidate_model,
            budget=budget,
        )
    else:
        for request in exact_requests:
            wire_request = build_llama_wire_request(request)
            validate_llama_wire_request(wire_request)
        transport = _LlamaTransport(client, host=ollama_host, runtime=llama_runtime)

    run_cfg = copy.deepcopy(cfg)
    run_cfg.setdefault("judgebench", {})
    run_cfg["judgebench"].update(
        {
            "provider": family,
            "provider_request": provider_request,
            "provider_settings": provider_settings,
            "runtime_version": runtime_version,
        }
    )
    calibration_ids = tuple(str(case["case_id"]) for case in package.cases)
    evidence: list[dict[str, Any]] = []

    def recorded_transport(request: Mapping[str, Any]) -> ProviderTransportResult:
        index = len(evidence)
        if index >= len(calibration_ids):
            raise LiveDriverConfigurationError("transport attempted beyond calibration cases")
        case_id = calibration_ids[index]
        try:
            result = transport(request)
        except Exception as exc:
            evidence.append(
                {"case_id": case_id, "status": "provider_error", "failure": type(exc).__name__}
            )
            raise
        if not isinstance(result, ProviderTransportResult):
            raise LiveDriverConfigurationError("live transport must return ProviderTransportResult")
        evidence.append(
            {
                "case_id": case_id,
                "status": "response",
                "provider": result.provider,
                "model": result.model,
                "latency_ms": result.latency_ms,
                "usage": dict(result.usage) if result.usage is not None else None,
                "cost": result.cost,
                "runtime_version": result.runtime_version,
                "response_hash": _response_hash(result.envelope),
                "envelope": dict(result.envelope),
            }
        )
        return result

    run = run_calibration(
        corpus_dir,
        cfg=run_cfg,
        judge_model=candidate_model,
        under_test_model=under_test_model,
        registry_path=registry_path,
        transport=recorded_transport,
        expected_full_hashes=expected_full_hashes,
        expected_rubric_hashes=expected_rubric_hashes,
        expected_prompt_wrapper_hash=expected_prompt_wrapper_hash,
        expected_comparison_signature=expected_comparison_signature,
        provider=family,
        provider_request=provider_request,
        provider_settings=provider_settings,
    )
    if len(evidence) != MAX_CALIBRATION_CALLS:
        raise LiveDriverConfigurationError("live run did not attempt exactly 20 calibration transports")
    if llama_runtime is not None:
        try:
            post_runtime = resolve_llama_runtime(
                client,
                host=ollama_host,
                expected_model_digest=expected_llama_model_digest,
                expected_runtime_version=expected_llama_runtime_version,
            )
        except LlamaRuntimeError as exc:
            raise LlamaRuntimeError(
                "Llama model or Ollama runtime changed during calibration"
            ) from exc
        if post_runtime != llama_runtime:
            raise LlamaRuntimeError(
                "Llama model or Ollama runtime changed during calibration"
            )
    run.transport_evidence = evidence
    report = build_calibration_report(package, run)
    report["provenance"] = {
        "comparison_signature": run.comparison_signature,
        "comparison_signature_digest": comparison_signature_digest(
            run.comparison_signature
        ),
    }
    report["transport"] = {
        "attempted_calls": len(evidence),
        "provider": family,
        "model": candidate_model,
        "telemetry": [
            {
                "case_id": item["case_id"],
                "status": item["status"],
                "latency_ms": item.get("latency_ms"),
                "response_hash": item.get("response_hash"),
                "usage": item.get("usage"),
                "cost": item.get("cost"),
            }
            for item in evidence
        ],
    }
    if budget is not None and price is not None:
        report["transport"]["remote_cost"] = {
            "ceiling_usd": str(budget.ceiling),
            "maximum_usd": str(budget.maximum_total),
            "input_token_bound": budget.input_token_bound,
            "input_token_bound_method": (
                "sum of UTF-8 serialized bytes for the exact 20 provider wire requests"
            ),
            "caller_input_token_ceiling": budget.caller_input_token_ceiling,
            "worst_case_formula": (
                "(input_token_bound * cache_miss_input_rate + "
                "20 * max_output_tokens * output_rate) / 1,000,000"
            ),
            "price_basis": {
                "cache_miss_input_usd_per_million_tokens": str(
                    price.cache_miss_input_usd_per_million_tokens
                ),
                "output_usd_per_million_tokens": str(price.output_usd_per_million_tokens),
                "source": price.source,
                "effective_at": price.effective_at,
            },
        }
    if llama_runtime is not None:
        report["transport"]["llama_runtime"] = {
            "model": llama_runtime.model,
            "model_digest": llama_runtime.model_digest,
            "serving_runtime": llama_runtime.serving_runtime,
            "serving_runtime_version": llama_runtime.serving_runtime_version,
        }
    return LiveCalibrationResult(
        run=run,
        report=report,
        transport_evidence=tuple(evidence),
        llama_runtime=llama_runtime,
        remote_price_basis=price,
        maximum_remote_cost_usd=budget.maximum_total if budget is not None else None,
    )

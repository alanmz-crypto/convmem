"""Pinned Ollama model identity and embedding request contract.

The client is intentionally explicit about endpoint, request fields, timeout,
and proxy isolation.  Callers decide whether a model operation is authorized;
these functions only execute after that authorization has been bound.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from typing import Any
from urllib.parse import urlparse

import requests

from eval_corpus.vector_fingerprint import (
    VectorIntegrityError,
    validate_vector,
    vector_fingerprint_v1,
)


class OllamaIdentityError(RuntimeError):
    """The Ollama server or model response is not identity-safe."""


REQUEST_SCHEMA_VERSION = "ollama.embed.v1"
DEFAULT_ENDPOINT_PATH = "/api/embed"
DEFAULT_TIMEOUT_SECONDS = 120.0


def canonical_loopback_host(host: str) -> str:
    """Require a direct local HTTP endpoint and reject proxy/remote ambiguity."""
    parsed = urlparse(str(host).strip())
    if parsed.scheme != "http" or parsed.path not in {"", "/"}:
        raise OllamaIdentityError("Ollama endpoint must be a plain HTTP host URL")
    if parsed.hostname not in {"127.0.0.1", "localhost", "::1"}:
        raise OllamaIdentityError("Ollama endpoint must be loopback")
    if not parsed.netloc:
        raise OllamaIdentityError("Ollama endpoint must include a host")
    return f"http://{parsed.netloc}"


class OllamaEmbedClient:
    """Direct non-proxying client for the frozen `/api/embed` contract."""

    def __init__(
        self,
        host: str,
        *,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
        endpoint_path: str = DEFAULT_ENDPOINT_PATH,
    ) -> None:
        if endpoint_path != DEFAULT_ENDPOINT_PATH:
            raise OllamaIdentityError("only the approved /api/embed endpoint is supported")
        self.host = canonical_loopback_host(host)
        self.timeout_seconds = float(timeout_seconds)
        if self.timeout_seconds <= 0 or not math.isfinite(self.timeout_seconds):
            raise OllamaIdentityError("Ollama timeout must be finite and positive")
        self.session = requests.Session()
        self.session.trust_env = False

    def _request(self, method: str, path: str, **kwargs: Any) -> Mapping[str, Any]:
        url = f"{self.host}{path}"
        try:
            response = self.session.request(
                method,
                url,
                timeout=self.timeout_seconds,
                **kwargs,
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            status = getattr(locals().get("response"), "status_code", "unknown")
            raise OllamaIdentityError(
                f"Ollama request failed method={method} endpoint={path} "
                f"status={status}: {exc}"
            ) from exc
        try:
            payload = response.json()
        except (TypeError, ValueError) as exc:
            status = getattr(response, "status_code", "unknown")
            raise OllamaIdentityError(
                f"Ollama response was not valid JSON method={method} "
                f"endpoint={path} status={status}"
            ) from exc
        if not isinstance(payload, Mapping):
            status = getattr(response, "status_code", "unknown")
            raise OllamaIdentityError(
                f"Ollama response must be an object endpoint={path} status={status}"
            )
        return payload

    def list_models(self) -> list[dict[str, Any]]:
        payload = self._request("GET", "/api/tags")
        models = payload.get("models")
        if not isinstance(models, list):
            raise OllamaIdentityError("Ollama /api/tags response lacks models list")
        return [dict(model) for model in models if isinstance(model, Mapping)]

    def list_running_models(self) -> list[dict[str, Any]]:
        """Return the server's currently loaded model records from ``/api/ps``."""
        payload = self._request("GET", "/api/ps")
        models = payload.get("models")
        if not isinstance(models, list):
            raise OllamaIdentityError("Ollama /api/ps response lacks models list")
        return [dict(model) for model in models if isinstance(model, Mapping)]

    def resolve_loaded_model(
        self,
        model_tag: str,
        model_digest: str,
        *,
        required: bool = False,
    ) -> dict[str, Any] | None:
        """Resolve the exact loaded model, or return ``None`` when not resident."""
        tag = str(model_tag).strip()
        digest = str(model_digest).strip()
        matches = []
        for record in self.list_running_models():
            loaded_tag = str(record.get("name") or record.get("model") or "").strip()
            if loaded_tag == tag:
                matches.append(record)
        if len(matches) > 1:
            raise OllamaIdentityError(
                f"Ollama loaded model tag must resolve at most once: {tag!r} "
                f"count={len(matches)}"
            )
        if not matches:
            if required:
                raise OllamaIdentityError(
                    f"Ollama model is not resident: tag={tag!r} digest={digest!r}"
                )
            return None
        loaded = matches[0]
        loaded_digest = str(loaded.get("digest") or "").strip()
        if not loaded_digest:
            raise OllamaIdentityError(f"Ollama loaded model {tag!r} has no digest")
        if loaded_digest != digest:
            raise OllamaIdentityError(
                f"Ollama loaded model digest mismatch: tag={tag!r} "
                f"loaded={loaded_digest!r} expected={digest!r}"
            )
        return {
            "model_tag": tag,
            "model_digest": loaded_digest,
            "size": loaded.get("size"),
            "size_vram": loaded.get("size_vram"),
            "expires_at": loaded.get("expires_at"),
        }

    def resolve_model(self, model_tag: str) -> dict[str, Any]:
        """Resolve exact tag, digest, variant and quantization from Ollama APIs."""
        tag = str(model_tag).strip()
        if not tag:
            raise OllamaIdentityError("model tag must be nonempty")
        entries = [row for row in self.list_models() if str(row.get("name")) == tag]
        if len(entries) != 1:
            raise OllamaIdentityError(
                f"Ollama model tag must resolve exactly once: {tag!r} count={len(entries)}"
            )
        listed = entries[0]
        digest = str(listed.get("digest") or "").strip()
        if not digest:
            raise OllamaIdentityError(f"Ollama model {tag!r} has no local digest")
        details_payload = self._request("POST", "/api/show", json={"name": tag})
        details = details_payload.get("details")
        if not isinstance(details, Mapping):
            details = {}
        return {
            "model_tag": tag,
            "model_digest": digest,
            "variant": str(details.get("families") or details.get("family") or ""),
            "quantization": str(
                details.get("quantization_level") or details.get("quantization") or ""
            ),
            "parameter_size": str(details.get("parameter_size") or ""),
            "listed_size": listed.get("size"),
            "details": dict(details),
        }

    def embed(
        self,
        text: str,
        *,
        model_tag: str,
        dimensions: int,
        truncate: bool = False,
        keep_alive: str = "10m",
        options: Mapping[str, Any] | None = None,
    ) -> tuple[list[float], dict[str, Any]]:
        """Execute and validate one exact embedding request."""
        if int(dimensions) <= 0:
            raise OllamaIdentityError("requested embedding dimension must be positive")
        request_body = {
            "model": model_tag,
            "input": str(text),
            "dimensions": int(dimensions),
            "truncate": bool(truncate),
            "keep_alive": str(keep_alive),
            "options": dict(options or {}),
        }
        try:
            payload = self._request("POST", DEFAULT_ENDPOINT_PATH, json=request_body)
        except OllamaIdentityError as exc:
            raise OllamaIdentityError(
                f"Ollama embed failed model={model_tag!r} "
                f"endpoint={DEFAULT_ENDPOINT_PATH} expected_dimension={dimensions}: {exc}"
            ) from exc
        embeddings = payload.get("embeddings")
        if not isinstance(embeddings, list) or len(embeddings) != 1:
            raise OllamaIdentityError(
                f"Ollama embed response invalid model={model_tag!r} "
                f"endpoint={DEFAULT_ENDPOINT_PATH} expected_dimension={dimensions}: "
                "must return one embedding"
            )
        vector = embeddings[0]
        if not isinstance(vector, Sequence) or isinstance(vector, (str, bytes)):
            raise OllamaIdentityError(
                f"Ollama embed response invalid model={model_tag!r} "
                f"endpoint={DEFAULT_ENDPOINT_PATH} expected_dimension={dimensions}: "
                "embedding must be a numeric sequence"
            )
        try:
            diagnostics = validate_vector(vector, expected_dimension=int(dimensions))
            fingerprint = vector_fingerprint_v1(vector)
        except VectorIntegrityError as exc:
            raise OllamaIdentityError(
                f"Ollama embed response invalid model={model_tag!r} "
                f"endpoint={DEFAULT_ENDPOINT_PATH} expected_dimension={dimensions}: {exc}"
            ) from exc
        return list(diagnostics["values"]), {
            "request_schema_version": REQUEST_SCHEMA_VERSION,
            "endpoint_path": DEFAULT_ENDPOINT_PATH,
            "request": request_body,
            "dimension": diagnostics["dimension"],
            "finite": diagnostics["finite"],
            "norm": diagnostics["norm"],
            "vector_fingerprint": fingerprint,
            "load_duration": payload.get("load_duration"),
            "total_duration": payload.get("total_duration"),
            "prompt_eval_count": payload.get("prompt_eval_count"),
        }


__all__ = [
    "DEFAULT_ENDPOINT_PATH",
    "DEFAULT_TIMEOUT_SECONDS",
    "REQUEST_SCHEMA_VERSION",
    "OllamaEmbedClient",
    "OllamaIdentityError",
    "canonical_loopback_host",
]

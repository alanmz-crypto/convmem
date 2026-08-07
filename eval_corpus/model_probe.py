"""Fail-closed model inventory and embedding-probe evidence."""

from __future__ import annotations

import hashlib
from collections.abc import Mapping
from typing import Any

from eval_corpus.ollama_identity import OllamaIdentityError


def _identity_digest(identity: Mapping[str, Any], *, label: str) -> str:
    digest = str(identity.get("model_digest") or "")
    if not digest:
        raise OllamaIdentityError(f"{label} model identity lacks a digest")
    return digest


def run_model_probe(
    client: Any,
    *,
    model_tag: str,
    expected_digest: str,
    dimensions: int,
    probe_text: str,
    transform_id: str,
    transform_sha256: str,
) -> dict[str, Any]:
    """Resolve, embed once, and prove model identity did not drift."""
    if not model_tag or not expected_digest:
        raise OllamaIdentityError("probe requires model tag and expected digest")
    if dimensions <= 0:
        raise OllamaIdentityError("probe requires a positive dimension")
    if not transform_id or len(transform_sha256) != 64:
        raise OllamaIdentityError("probe requires a transform identity")

    before_inventory = client.list_models()
    before = client.resolve_model(model_tag)
    before_digest = _identity_digest(before, label="pre-probe")
    if before_digest != expected_digest:
        raise OllamaIdentityError(
            f"pre-probe digest mismatch: observed={before_digest} expected={expected_digest}"
        )
    vector, diagnostics = client.embed(
        probe_text,
        model_tag=model_tag,
        dimensions=dimensions,
    )
    after_inventory = client.list_models()
    after = client.resolve_model(model_tag)
    after_digest = _identity_digest(after, label="post-probe")
    if after_digest != expected_digest or after_digest != before_digest:
        raise OllamaIdentityError(
            "model digest changed during probe: "
            f"before={before_digest} after={after_digest} expected={expected_digest}"
        )
    if len(vector) != dimensions:
        raise OllamaIdentityError("probe vector dimension mismatch")
    if not isinstance(diagnostics, Mapping):
        raise OllamaIdentityError("probe diagnostics must be an object")
    request = diagnostics.get("request")
    if not isinstance(request, Mapping):
        raise OllamaIdentityError("probe diagnostics lack the actual request")
    if str(request.get("model") or "") != model_tag:
        raise OllamaIdentityError("probe request model does not match approved tag")
    if int(request.get("dimensions") or 0) != dimensions:
        raise OllamaIdentityError("probe request dimensions do not match approved dimension")
    return {
        "schema_version": "model_probe_v1",
        "operation": "probe",
        "model_tag": model_tag,
        "model_digest": expected_digest,
        "dimensions": dimensions,
        "transform_id": transform_id,
        "transform_sha256": transform_sha256,
        "probe_text_sha256": hashlib.sha256(probe_text.encode("utf-8")).hexdigest(),
        "before_inventory": before_inventory,
        "before_identity": dict(before),
        "after_inventory": after_inventory,
        "after_identity": dict(after),
        "embedding_diagnostics": dict(diagnostics),
    }


__all__ = ["run_model_probe"]

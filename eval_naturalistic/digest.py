"""Content-addressing helpers for naturalistic study artifacts."""

from __future__ import annotations

import hashlib
from typing import Any

from canonical_json import canonical_json_bytes

from eval_naturalistic.base import StructuralContractError, strip_digest_metadata

ARTIFACT_ID_PREFIX = "nps1_"
SCHEMA_NAMESPACE = "convmem/naturalistic"


def _reject_non_json_safe(value: Any) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            if not isinstance(key, str):
                raise StructuralContractError("canonical JSON object keys must be strings")
            _reject_non_json_safe(child)
    elif isinstance(value, list):
        for child in value:
            _reject_non_json_safe(child)
    elif isinstance(value, float):
        import math

        if not math.isfinite(value):
            raise StructuralContractError("non-finite floats are not canonical JSON")


def canonical_artifact_bytes(value: Any) -> bytes:
    """Return stable JSON bytes for artifact body hashing."""

    return canonical_json_bytes(
        value,
        validate=_reject_non_json_safe,
        error_type=StructuralContractError,
    )


def artifact_content_digest(body: dict[str, Any]) -> str:
    """Compute SHA-256 over authoritative artifact content."""

    return hashlib.sha256(
        canonical_artifact_bytes(strip_digest_metadata(body))
    ).hexdigest()


def make_artifact_id(*, kind: str, content_digest: str) -> str:
    """Derive a stable artifact ID from kind and content digest."""

    if not kind:
        raise StructuralContractError("artifact kind must not be empty")
    if len(content_digest) != 64:
        raise StructuralContractError("content digest must be 64-char SHA-256 hex")
    return f"{ARTIFACT_ID_PREFIX}{kind}_{content_digest[:16]}"

"""Versioned semantic transform contract for incremental JSONL (Arc Codex #286)."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from distill import DISTILL_PROMPT
from llm import SUMMARIZE_PROMPT

FINGERPRINT_SCHEME = "incremental-transform-v2"
TRANSFORM_CONTRACT_VERSION = 1
CHECKPOINT_VERSION_V1 = 1
CHECKPOINT_VERSION_V2 = 2
TRANSACTION_VERSION_V1 = 1
TRANSACTION_VERSION_V2 = 2
RECOVERY_PROTOCOL_VERSION = 1
SUPPORTED_RECOVERY_PROTOCOL_VERSIONS = frozenset({RECOVERY_PROTOCOL_VERSION})

GENERATION_SCHEME_V1 = "jsonl-incremental-generation-v1"
GENERATION_SCHEME_V2 = "jsonl-incremental-generation-v2"

RENDERING_LIMITS = {"summary_max_chars": 8000, "distill_max_chars": 8000}
MESSAGE_SELECTION = "chunk_messages"
SUMMARY_TEMPERATURE = 0.2
DISTILL_TEMPERATURE = 0.2
NORMALIZATION_CONTRACT = "normalize_unit-v1"
PROVENANCE_ENVELOPE_CONTRACT = "build_ingest_envelope-v1"
ID_CONTRACT = "make_unit_id-v1"
DEDUPE_CONTRACT = "ingest_dedupe-v1"
PREPARED_PAYLOAD_CONTRACT = "prepared-artifact-v1"


def _sha(value: bytes | str) -> str:
    if isinstance(value, str):
        value = value.encode("utf-8")
    return hashlib.sha256(value).hexdigest()


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)


def prompt_template_digests() -> dict[str, str]:
    return {
        "summarize_prompt_template_sha256": _sha(SUMMARIZE_PROMPT),
        "distill_prompt_template_sha256": _sha(DISTILL_PROMPT),
    }


def contract_inventory_sources() -> dict[str, str]:
    """Hashed semantic inputs for C1 fail-closed inventory (not module hashes)."""
    return {
        "fingerprint_scheme": FINGERPRINT_SCHEME,
        "transform_contract_version": str(TRANSFORM_CONTRACT_VERSION),
        **prompt_template_digests(),
        "rendering_limits": _canonical_json(RENDERING_LIMITS),
        "message_selection": MESSAGE_SELECTION,
        "summary_temperature": str(SUMMARY_TEMPERATURE),
        "distill_temperature": str(DISTILL_TEMPERATURE),
        "normalization_contract": NORMALIZATION_CONTRACT,
        "provenance_envelope": PROVENANCE_ENVELOPE_CONTRACT,
        "id_contract": ID_CONTRACT,
        "dedupe_contract": DEDUPE_CONTRACT,
        "prepared_payload_contract": PREPARED_PAYLOAD_CONTRACT,
    }


def contract_inventory_digest() -> str:
    return _sha(_canonical_json(contract_inventory_sources()))


EPOCH_BUMP_CHECKLIST_REL = "docs/plans/incremental_transform_epoch_bump_checklist.md"


def contract_inventory_drift_message(live: str, pinned: str) -> str:
    return (
        "transform contract inventory drifted without epoch bump; "
        f"live={live} pinned={pinned}; "
        f"update transform_contract_version or descriptor per {EPOCH_BUMP_CHECKLIST_REL}"
    )


def assert_contract_inventory_matches(pinned_digest: str) -> None:
    live = contract_inventory_digest()
    if live != pinned_digest:
        raise AssertionError(contract_inventory_drift_message(live, pinned_digest))


@dataclass(frozen=True)
class TransformDescriptor:  # pylint: disable=too-many-instance-attributes
    scheme: str
    transform_contract_version: int
    adapter_format: str
    adapter_contract_version: str
    chunk_size: int
    overlap: int
    min_confidence: float
    models: dict[str, Any]
    embed_dimension: int
    prompt_digests: dict[str, str]
    body: dict[str, Any]
    digest: str


def build_transform_descriptor(
    *,
    chunk_size: int,
    overlap: int,
    min_confidence: float,
    models: dict[str, Any],
    embed_dimension: int,
    adapter_format: str,
    adapter_contract_version: str,
    transform_contract_version: int = TRANSFORM_CONTRACT_VERSION,
) -> TransformDescriptor:
    if embed_dimension <= 0:
        raise ValueError("embed_dimension must be resolved")
    summarize_model = models.get("summarize_model")
    distill_model = models.get("distill_model")
    embed_model = models.get("embed_model")
    if not summarize_model or not distill_model or not embed_model:
        raise ValueError("models must include summarize, distill, and embed identities")
    prompt_digests = prompt_template_digests()
    body = {
        "fingerprint_scheme": FINGERPRINT_SCHEME,
        "transform_contract_version": transform_contract_version,
        "adapter_format": adapter_format,
        "adapter_contract_version": adapter_contract_version,
        "chunk_size": chunk_size,
        "overlap": overlap,
        "rendering_limits": RENDERING_LIMITS,
        "message_selection": MESSAGE_SELECTION,
        "summary_prompt_template_sha256": prompt_digests["summarize_prompt_template_sha256"],
        "distill_prompt_template_sha256": prompt_digests["distill_prompt_template_sha256"],
        "summary_temperature": SUMMARY_TEMPERATURE,
        "distill_temperature": DISTILL_TEMPERATURE,
        "summarize_model": summarize_model,
        "distill_model": distill_model,
        "embed_model": embed_model,
        "embed_dimension": embed_dimension,
        "normalization_contract": NORMALIZATION_CONTRACT,
        "confidence_threshold": min_confidence,
        "provenance_envelope": PROVENANCE_ENVELOPE_CONTRACT,
        "id_contract": ID_CONTRACT,
        "dedupe_contract": DEDUPE_CONTRACT,
        "prepared_payload_contract": PREPARED_PAYLOAD_CONTRACT,
    }
    distill_reasoning_effort = models.get("distill_reasoning_effort")
    if distill_reasoning_effort:
        body["distill_reasoning_effort"] = distill_reasoning_effort
    digest = _sha(FINGERPRINT_SCHEME + ":" + _canonical_json(body))
    return TransformDescriptor(
        scheme=FINGERPRINT_SCHEME,
        transform_contract_version=transform_contract_version,
        adapter_format=adapter_format,
        adapter_contract_version=adapter_contract_version,
        chunk_size=chunk_size,
        overlap=overlap,
        min_confidence=min_confidence,
        models=dict(models),
        embed_dimension=embed_dimension,
        prompt_digests=prompt_digests,
        body=body,
        digest=digest,
    )


def descriptor_to_checkpoint_fields(descriptor: TransformDescriptor) -> dict[str, Any]:
    return {
        "fingerprint_scheme": descriptor.scheme,
        "transform_contract_version": descriptor.transform_contract_version,
        "transform_descriptor": descriptor.body,
        "transform_fingerprint": descriptor.digest,
    }


def validate_descriptor_digest(descriptor_body: dict[str, Any], digest: str) -> None:
    expected = _sha(FINGERPRINT_SCHEME + ":" + _canonical_json(descriptor_body))
    if digest != expected:
        raise ValueError("transform descriptor digest mismatch")


def compute_legacy_v1_transform_fingerprint(
    *,
    chunk_size: int,
    overlap: int,
    min_confidence: float,
    models: dict[str, Any],
    embed_dimension: int,
    implementation_revision: str,
    adapter_format: str,
    adapter_contract_version: str,
) -> str:
    payload = {
        "adapter_format": adapter_format,
        "adapter_contract_version": adapter_contract_version,
        "chunk_size": chunk_size,
        "overlap": overlap,
        "rendering_limits": RENDERING_LIMITS,
        "message_selection": MESSAGE_SELECTION,
        "summary_prompt_version": "locked-summarize-prompt-v1",
        "distill_prompt_version": "locked-distill-prompt-v1",
        "summary_temperature": SUMMARY_TEMPERATURE,
        "distill_temperature": DISTILL_TEMPERATURE,
        "summarize_model": models.get("summarize_model"),
        "distill_model": models.get("distill_model"),
        "embed_model": models.get("embed_model"),
        "embed_dimension": embed_dimension,
        "normalization_contract": NORMALIZATION_CONTRACT,
        "confidence_threshold": min_confidence,
        "provenance_envelope": PROVENANCE_ENVELOPE_CONTRACT,
        "id_contract": ID_CONTRACT,
        "dedupe_contract": DEDUPE_CONTRACT,
        "implementation_revision": implementation_revision,
    }
    return _sha(_canonical_json(payload))


def generation_id_v1(
    *,
    source_id: str,
    prefix_sha256: str,
    complete_boundary: int,
    transform_fingerprint: str,
) -> str:
    return _sha(
        f"{GENERATION_SCHEME_V1}:{source_id}:{prefix_sha256}:{complete_boundary}:"
        f"{transform_fingerprint}"
    )


def generation_id_v2(
    *,
    source_id: str,
    prefix_sha256: str,
    complete_boundary: int,
    transform_fingerprint: str,
) -> str:
    return _sha(
        f"{GENERATION_SCHEME_V2}:{source_id}:{prefix_sha256}:{complete_boundary}:"
        f"{transform_fingerprint}"
    )


def prepared_cache_key(
    *,
    source_id: str,
    input_digest: str,
    transform_fingerprint: str,
    chunk_start: int,
) -> str:
    return _sha(f"{source_id}:{input_digest}:{transform_fingerprint}:{chunk_start}")


def recovery_protocol_supported(version: int | None) -> bool:
    if version is None:
        return False
    return int(version) in SUPPORTED_RECOVERY_PROTOCOL_VERSIONS


def checklist_path() -> Path:
    return Path(__file__).resolve().parent / EPOCH_BUMP_CHECKLIST_REL

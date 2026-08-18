"""P2 bindings that carry the P1 provenance envelope through projections.

This module is deliberately a boundary adapter, not a second authority store.
It creates the envelope for a supported ingest transformation, serializes the
authoritative envelope for scalar-safe projections, and validates a projection
against its own commitment.  The P1 registry remains the authority; a unit,
export row, or Chroma metadata record is never sufficient to mint or elevate
an assertion.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from typing import Any

from provenance import (
    EnvelopeValidationError,
    ProvenanceRegistry,
    base_envelope,
    canonical_bytes,
    canonical_hash,
    provenance_commitment,
    root_binding,
    sha256_hex,
    validate_envelope,
)

PROVENANCE_ENVELOPE_KEY = "provenance_envelope"
PROVENANCE_COMMITMENT_KEY = "provenance_commitment"
PROVENANCE_STATUS_KEY = "provenance_status"
PROVENANCE_ASSERTION_ID_KEY = "assertion_id"
PROVENANCE_INTEGRITY_KEY = "effective_integrity"

_UNVERIFIED_CHANNEL = {
    "channel_class": "unverified",
    "channel_locator": "unverified://none",
    "channel_evidence_sha256": sha256_hex(b"no-authenticated-evidence"),
}


def _json_text(value: Any) -> str:
    return canonical_bytes(value).decode("utf-8")


def _hash_record(record: Any) -> str:
    if isinstance(record, bytes):
        return sha256_hex(record)
    if isinstance(record, str):
        return sha256_hex(record)
    return canonical_hash(record)


def _origin_class(source_type: str | None) -> str:
    """Map a source label to classification only; it never grants assurance."""

    label = str(source_type or "").lower()
    if "inter_model" in label or "inter-model" in label or label == "kiro_steering":
        return "inter_model"
    return "external"


def _root_bindings(
    records: Sequence[Any],
    consumed_views: Sequence[str],
    *,
    source_identity: str,
    locator_prefix: str,
    source_type: str | None,
) -> list[dict[str, Any]]:
    roots: list[dict[str, Any]] = []
    origin_class = _origin_class(source_type)
    for index, record in enumerate(records):
        view = consumed_views[index] if index < len(consumed_views) else record
        roots.append(
            root_binding(
                source_identity=source_identity,
                record_locator=f"{locator_prefix}:{index}",
                raw_record_sha256=_hash_record(record),
                input_view_sha256=_hash_record(view),
                origin_class=origin_class,
                origin_assurance="unknown",
                **_UNVERIFIED_CHANNEL,
            )
        )
    return roots


def build_ingest_envelope(
    *,
    records: Sequence[Any],
    consumed_views: Sequence[str],
    source_identity: str,
    locator_prefix: str,
    source_type: str | None,
    transformer_class: str,
    transformer_identity: str,
    transformer_version: str,
    derivation_kind: str,
    producer_class: str,
    producer_assurance: str,
    selection_parameters: Mapping[str, Any],
    provider_payload: Mapping[str, Any],
    recipe_id: str,
    recipe_spec: Mapping[str, Any],
    output_locator: str,
    output_value: Any,
) -> dict[str, Any]:
    """Mint one P1 assertion envelope for a supported P2 boundary.

    The source inputs are intentionally unverified in production.  The local
    registry is used only to apply the locked P1 policy while constructing the
    assertion; durable authority remains a later registry/recovery concern.
    """

    registry = ProvenanceRegistry()
    recipe_sha = registry.register_recipe(recipe_id, recipe_spec)
    selection = dict(selection_parameters)
    selection.update(
        {
            "output_locator": output_locator,
            "output_sha256": _hash_record(output_value),
            "source_type_claim": str(source_type or ""),
        }
    )
    envelope = base_envelope(
        root_bindings=_root_bindings(
            records,
            consumed_views,
            source_identity=source_identity,
            locator_prefix=locator_prefix,
            source_type=source_type,
        ),
        producer_class=producer_class,
        producer_assurance=producer_assurance,
        derivation_kind=derivation_kind,
        transformer_class=transformer_class,
        transformer_identity=transformer_identity,
        transformer_version=transformer_version,
        transformer_recipe_id=recipe_id,
        transformer_recipe_sha256=recipe_sha,
        selection_parameters=selection,
        provider_payload_sha256=canonical_hash(provider_payload),
        recipe_config_sha256=canonical_hash(recipe_spec),
    )
    record = registry.mint(envelope)
    result = registry.verify(record.assertion_id)
    serialized = record.as_dict()
    serialized[PROVENANCE_INTEGRITY_KEY] = result.effective_integrity
    return serialized


def envelope_from_unit(unit: Mapping[str, Any]) -> dict[str, Any] | None:
    """Read a nested or scalar-safe envelope without trusting flat fields."""

    value = unit.get(PROVENANCE_ENVELOPE_KEY)
    if value is None:
        value = unit.get("provenance")
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except json.JSONDecodeError:
            return None
    if not isinstance(value, Mapping):
        return None
    try:
        return validate_envelope(_thaw(value))
    except (EnvelopeValidationError, TypeError, ValueError):
        return None


def validate_projection(unit: Mapping[str, Any]) -> dict[str, Any]:
    """Validate a projection's envelope/commitment pair conservatively."""

    envelope = envelope_from_unit(unit)
    if envelope is None:
        return {
            "status": "untrusted",
            "reason": "missing or malformed provenance envelope",
            "envelope": None,
            "commitment": None,
            "assertion_id": unit.get(PROVENANCE_ASSERTION_ID_KEY),
            "effective_integrity": "untrusted",
        }
    expected = provenance_commitment(envelope)
    supplied = unit.get(PROVENANCE_COMMITMENT_KEY) or envelope.get(
        PROVENANCE_COMMITMENT_KEY
    )
    if supplied != expected:
        return {
            "status": "untrusted",
            "reason": "provenance commitment mismatch",
            "envelope": envelope,
            "commitment": expected,
            "assertion_id": envelope.get(PROVENANCE_ASSERTION_ID_KEY),
            "effective_integrity": "untrusted",
        }
    return {
        "status": "self-consistent",
        "reason": None,
        "envelope": envelope,
        "commitment": expected,
        "assertion_id": envelope[PROVENANCE_ASSERTION_ID_KEY],
        # A projection cannot recompute authority.  This is only the P1 cache;
        # authoritative recursive verification remains registry-bound.
        "effective_integrity": "untrusted",
    }


def attach_unit_provenance(unit: Mapping[str, Any], envelope: Mapping[str, Any]) -> dict[str, Any]:
    """Attach the canonical envelope and commitment to an in-memory unit."""

    result = dict(unit)
    parsed = envelope_from_unit({PROVENANCE_ENVELOPE_KEY: envelope})
    if parsed is None:
        raise EnvelopeValidationError("cannot attach an invalid provenance envelope")
    commitment = provenance_commitment(parsed)
    result[PROVENANCE_ENVELOPE_KEY] = parsed
    result[PROVENANCE_COMMITMENT_KEY] = commitment
    result[PROVENANCE_ASSERTION_ID_KEY] = parsed[PROVENANCE_ASSERTION_ID_KEY]
    result[PROVENANCE_INTEGRITY_KEY] = "untrusted"
    result[PROVENANCE_STATUS_KEY] = "self-consistent"
    return result


def projection_metadata(unit: Mapping[str, Any]) -> dict[str, Any]:
    """Return scalar-safe Chroma metadata derived from the unit envelope."""

    checked = validate_projection(unit)
    metadata = {
        PROVENANCE_ENVELOPE_KEY: _json_text(checked["envelope"])
        if checked["envelope"] is not None
        else "",
        PROVENANCE_COMMITMENT_KEY: checked["commitment"] or "",
        PROVENANCE_ASSERTION_ID_KEY: checked["assertion_id"] or "",
        PROVENANCE_STATUS_KEY: checked["status"],
        PROVENANCE_INTEGRITY_KEY: "untrusted",
    }
    return metadata


def enforce_projection_metadata(metadata: Mapping[str, Any]) -> dict[str, Any]:
    """Validate projection provenance before a Chroma write.

    Legacy rows without a provenance envelope remain explicitly untrusted.  A
    row that presents provenance fields must be internally self-consistent;
    accepting a malformed or divergent pair would let a projection silently
    replace authoritative continuity.
    """

    result = dict(metadata)
    has_provenance_pair = PROVENANCE_ENVELOPE_KEY in result or PROVENANCE_COMMITMENT_KEY in result
    if not has_provenance_pair:
        if PROVENANCE_INTEGRITY_KEY in result:
            result[PROVENANCE_INTEGRITY_KEY] = "untrusted"
        return result
    checked = validate_projection(result)
    if checked["envelope"] is None or checked["status"] != "self-consistent":
        raise ValueError(f"invalid projection provenance: {checked['reason']}")
    result.update(projection_metadata(result))
    return result


def _thaw(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {key: _thaw(child) for key, child in value.items()}
    if isinstance(value, (list, tuple)):
        return [_thaw(child) for child in value]
    return value


__all__ = [
    "PROVENANCE_ASSERTION_ID_KEY",
    "PROVENANCE_COMMITMENT_KEY",
    "PROVENANCE_ENVELOPE_KEY",
    "PROVENANCE_INTEGRITY_KEY",
    "PROVENANCE_STATUS_KEY",
    "attach_unit_provenance",
    "build_ingest_envelope",
    "enforce_projection_metadata",
    "envelope_from_unit",
    "projection_metadata",
    "validate_projection",
]

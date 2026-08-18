"""P2 continuity tests for ingest-shaped units and rebuildable projections."""

from __future__ import annotations

from eval_corpus.reconstruct import build_canonical_unit, normalized_shadow_metadata
from provenance_binding import (
    PROVENANCE_COMMITMENT_KEY,
    PROVENANCE_ENVELOPE_KEY,
    attach_unit_provenance,
    build_ingest_envelope,
    enforce_projection_metadata,
    projection_metadata,
    validate_projection,
)


def _envelope() -> dict:
    source = {"role": "user", "content": "source", "timestamp": "2026-01-01"}
    return build_ingest_envelope(
        records=[source],
        consumed_views=["user: source"],
        source_identity="fixture/source.jsonl",
        locator_prefix="chunk:0",
        source_type="inter_model_doc",
        transformer_class="packaging",
        transformer_identity="fixture-packager",
        transformer_version="fixture-v1",
        derivation_kind="packaging",
        producer_class="external",
        producer_assurance="claimed",
        selection_parameters={"chunk_start": 0, "message_order": [0]},
        provider_payload={"content": "source"},
        recipe_id="fixture-packaging-v1",
        recipe_spec={"kind": "fixture-packaging"},
        output_locator="fixture/source.jsonl#chunk:0:unit:0",
        output_value={"summary": "source"},
    )


def test_unit_projection_round_trip_preserves_authoritative_identity() -> None:
    unit = attach_unit_provenance(
        {
            "id": "unit-1",
            "title": "Source",
            "summary": "source",
            "keywords": ["source"],
            "source_path": "fixture/source.jsonl",
            "source_type": "inter_model_doc",
        },
        _envelope(),
    )

    checked = validate_projection(unit)
    metadata = projection_metadata(unit)
    rebuilt = build_canonical_unit(unit)

    assert checked["status"] == "self-consistent"
    assert rebuilt["assertion_id"] == unit["assertion_id"]
    assert rebuilt[PROVENANCE_COMMITMENT_KEY] == unit[PROVENANCE_COMMITMENT_KEY]
    assert rebuilt[PROVENANCE_ENVELOPE_KEY]["assertion_id"] == unit["assertion_id"]
    assert metadata[PROVENANCE_COMMITMENT_KEY] == unit[PROVENANCE_COMMITMENT_KEY]
    assert metadata["effective_integrity"] == "untrusted"
    assert normalized_shadow_metadata(unit)["source_type"] == "inter_model_doc"


def test_projection_cannot_self_upgrade_or_repair_a_commitment() -> None:
    unit = attach_unit_provenance(
        {"id": "unit-2", "summary": "source", "keywords": []}, _envelope()
    )
    metadata = projection_metadata(unit)
    metadata["effective_integrity"] = "trusted"
    enforced = enforce_projection_metadata(metadata)
    assert enforced["effective_integrity"] == "untrusted"

    metadata[PROVENANCE_COMMITMENT_KEY] = "0" * 64
    try:
        enforce_projection_metadata(metadata)
    except ValueError as exc:
        assert "commitment" in str(exc)
    else:
        raise AssertionError("divergent projection commitment was accepted")


def test_missing_projection_provenance_is_explicitly_untrusted() -> None:
    checked = validate_projection({"id": "legacy", "summary": "old"})
    assert checked["status"] == "untrusted"
    assert checked["effective_integrity"] == "untrusted"

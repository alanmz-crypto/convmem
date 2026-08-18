"""P1 provenance policy, identity, canonicalization, and pin tests."""

from __future__ import annotations

import copy
import json

import pytest

from provenance import (
    BINDING_VERSION,
    EnvelopeValidationError,
    IdentityReplayError,
    PinError,
    ProvenanceRegistry,
    ReclamationDisabled,
    SCHEMA_SEMANTICS_SHA256,
    SCHEMA_VERSION,
    TransformerRule,
    base_envelope,
    canonical_envelope_bytes,
    input_binding,
    parse_envelope,
    parse_json,
    provenance_commitment,
    root_binding,
    sha256_hex,
    validate_envelope,
)


def _root(*, verified: bool = True) -> dict:
    return root_binding(
        source_identity="fixture/source",
        record_locator="event-1",
        raw_record_sha256=sha256_hex("raw record"),
        input_view_sha256=sha256_hex("raw record"),
        origin_class="synthetic",
        origin_assurance="verified" if verified else "unknown",
        channel_class="synthetic-authenticated" if verified else "unverified",
        channel_locator="fixture://authenticated" if verified else "unverified://none",
    )


def _root_record(registry: ProvenanceRegistry, *, verified: bool = True):
    return registry.mint(
        base_envelope(
            root_bindings=[_root(verified=verified)],
            producer_class="trusted_tool" if verified else "external",
            producer_assurance="verified" if verified else "unknown",
        )
    )


def _derived_template(registry: ProvenanceRegistry, parent, *, transformer_class="llm"):
    recipe_id = "summary-v1"
    recipe_sha = registry.register_recipe(recipe_id, {"kind": "summary", "version": 1})
    return base_envelope(
        input_bindings=[input_binding(parent, exact_input_view_sha256=sha256_hex("view"))],
        producer_class="agent",
        producer_assurance="claimed",
        derivation_kind="summarize",
        transformer_class=transformer_class,
        transformer_identity="fixture-model",
        transformer_version="1",
        transformer_recipe_id=recipe_id,
        transformer_recipe_sha256=recipe_sha,
    )


def test_verified_root_and_untrusted_production_root_are_conservative() -> None:
    registry = ProvenanceRegistry()
    trusted = _root_record(registry)
    untrusted = _root_record(registry, verified=False)

    trusted_result = registry.verify(trusted.assertion_id)
    untrusted_result = registry.verify(untrusted.assertion_id)

    assert trusted_result.verified
    assert trusted_result.effective_integrity == "trusted"
    assert untrusted_result.verified
    assert untrusted_result.effective_integrity == "untrusted"


def test_llm_meet_never_elevates_an_untrusted_root() -> None:
    registry = ProvenanceRegistry()
    trusted_parent = _root_record(registry)
    untrusted_parent = _root_record(registry, verified=False)
    trusted_child = registry.mint(_derived_template(registry, trusted_parent))
    untrusted_child = registry.mint(_derived_template(registry, untrusted_parent))

    assert registry.verify(trusted_child.assertion_id).effective_integrity == "agent"
    assert registry.verify(untrusted_child.assertion_id).effective_integrity == "untrusted"


def test_empty_input_is_rejected_before_it_can_mint_authority() -> None:
    registry = ProvenanceRegistry()
    with pytest.raises(EnvelopeValidationError, match="binding family"):
        registry.mint(base_envelope())


def test_caller_cannot_supply_an_assertion_id_to_mint() -> None:
    registry = ProvenanceRegistry()
    template = base_envelope(root_bindings=[_root()])
    template["assertion_id"] = "11111111-1111-4111-8111-111111111111"
    with pytest.raises(IdentityReplayError, match="monitor"):
        registry.mint(template)


def test_identity_is_not_part_of_content_equivalence() -> None:
    registry = ProvenanceRegistry()
    first = _root_record(registry)
    second = _root_record(registry)
    assert first.assertion_id != second.assertion_id
    assert first.commitment != second.commitment


def test_commitment_excludes_only_commitment_and_cache_fields() -> None:
    registry = ProvenanceRegistry()
    record = _root_record(registry)
    payload = record.as_dict()
    commitment = provenance_commitment(payload)
    payload["effective_integrity"] = "trusted"
    assert provenance_commitment(payload) == commitment
    assert canonical_envelope_bytes(payload) == canonical_envelope_bytes(record.envelope)
    assert payload["provenance_commitment"] == commitment


def test_strict_parser_rejects_duplicate_keys_nonfinite_and_surrogates() -> None:
    with pytest.raises(EnvelopeValidationError, match="duplicate"):
        parse_json('{"a": 1, "a": 2}')
    with pytest.raises(EnvelopeValidationError, match="undefined"):
        parse_json('{"a": NaN}')
    with pytest.raises(EnvelopeValidationError, match="surrogate"):
        parse_json('{"a": "\\ud800"}')


def test_schema_and_typed_boundary_reject_drift_and_unknown_fields() -> None:
    registry = ProvenanceRegistry()
    record = _root_record(registry)
    payload = record.as_dict()
    payload["schema_semantics_sha256"] = "0" * 64
    with pytest.raises(EnvelopeValidationError, match="semantic"):
        validate_envelope(payload)
    payload = record.as_dict()
    payload["new_field"] = "not accepted"
    with pytest.raises(EnvelopeValidationError, match="unknown"):
        validate_envelope(payload)


def test_json_round_trip_has_one_canonical_typed_form() -> None:
    registry = ProvenanceRegistry()
    record = _root_record(registry)
    serialized = json.dumps(record.as_dict(), ensure_ascii=False, sort_keys=True)
    parsed = parse_envelope(serialized)
    assert parsed["assertion_id"] == record.assertion_id
    assert provenance_commitment(parsed) == record.commitment
    assert parsed["schema_version"] == SCHEMA_VERSION
    assert parsed["binding_version"] == BINDING_VERSION
    assert parsed["schema_semantics_sha256"] == SCHEMA_SEMANTICS_SHA256


def test_parent_commitment_mismatch_and_missing_parent_fail_closed() -> None:
    registry = ProvenanceRegistry()
    parent = _root_record(registry)
    bad_binding = input_binding(parent, exact_input_view_sha256=sha256_hex("view"))
    bad_binding["parent_provenance_commitment"] = "0" * 64
    mismatch = registry.mint(
        base_envelope(
            input_bindings=[bad_binding],
            producer_class="agent",
            producer_assurance="claimed",
            derivation_kind="summarize",
            transformer_class="llm",
            transformer_identity="fixture-model",
            transformer_version="1",
            transformer_recipe_id="root-v1",
            transformer_recipe_sha256=sha256_hex(b"convmem:root-recipe-v1"),
        )
    )
    missing_binding = {
        "parent_assertion_id": "22222222-2222-4222-8222-222222222222",
        "parent_provenance_commitment": "0" * 64,
        "exact_input_view_sha256": sha256_hex("view"),
    }
    missing = registry.mint(
        base_envelope(
            input_bindings=[missing_binding],
            producer_class="agent",
            producer_assurance="claimed",
            derivation_kind="summarize",
            transformer_class="llm",
            transformer_identity="fixture-model",
            transformer_version="1",
            transformer_recipe_id="root-v1",
            transformer_recipe_sha256=sha256_hex(b"convmem:root-recipe-v1"),
        )
    )

    assert registry.verify(mismatch.assertion_id).effective_integrity == "untrusted"
    assert registry.verify(missing.assertion_id).effective_integrity == "untrusted"


def test_trusted_cap_requires_exact_rule_and_immutable_artifact() -> None:
    registry = ProvenanceRegistry()
    artifact = sha256_hex("packaged-artifact")
    policy = registry.register_policy(
        "policy-trusted-fixture",
        {"name": "fixture trusted packaging", "version": 1},
        rules=(
            TransformerRule(
                "packaging",
                "fixture-packager",
                "1",
                "package-v1",
                "trusted",
                preservation_contract="bytes-preserved-v1",
                artifact_sha256=artifact,
            ),
        ),
    )
    recipe_sha = registry.register_recipe("package-v1", {"kind": "package"})
    parent = _root_record(registry)
    child = registry.mint(
        base_envelope(
            input_bindings=[input_binding(parent, exact_input_view_sha256=sha256_hex("view"))],
            producer_class="trusted_tool",
            producer_assurance="verified",
            derivation_kind="package",
            transformer_class="packaging",
            transformer_identity="fixture-packager",
            transformer_version="1",
            transformer_artifact_sha256=artifact,
            transformer_recipe_id="package-v1",
            transformer_recipe_sha256=recipe_sha,
            provenance_policy_version=policy.version,
            provenance_policy_sha256=policy.semantic_sha256,
        )
    )
    assert registry.verify(child.assertion_id).effective_integrity == "trusted"

    tampered = copy.deepcopy(child.as_dict())
    tampered["transformer_artifact_sha256"] = sha256_hex("different-artifact")
    tampered["provenance_commitment"] = provenance_commitment(tampered)
    with pytest.raises(IdentityReplayError, match="not verifiable"):
        registry.import_replay(tampered, tampered["provenance_commitment"])


def test_operation_pin_survives_new_generation_and_reclamation_is_safe() -> None:
    registry = ProvenanceRegistry()
    first = _root_record(registry)
    with registry.pin() as pin:
        first_result = registry.verify(first.assertion_id, pin)
        pinned_generation = pin.generation
        _root_record(registry)
        second_result = registry.verify(first.assertion_id, pin)
        assert first_result.authority_generation == pinned_generation
        assert second_result.authority_generation == pinned_generation
        with pytest.raises(PinError, match="active"):
            registry.reclaim(pinned_generation)
    with pytest.raises(ReclamationDisabled):
        registry.reclaim(pinned_generation)


def test_pinned_snapshot_records_are_deeply_immutable() -> None:
    registry = ProvenanceRegistry()
    record = _root_record(registry)
    with pytest.raises(TypeError):
        record.envelope["root_bindings"][0]["record_locator"] = "tampered"


def test_recipe_replacement_does_not_reinterpret_an_old_pinned_snapshot() -> None:
    registry = ProvenanceRegistry()
    parent = _root_record(registry)
    registry.register_recipe("summary-v1", {"meaning": "old"})
    child = registry.mint(_derived_template(registry, parent))
    with registry.pin() as pin:
        old = registry.verify(child.assertion_id, pin)
        registry.register_recipe("summary-v1", {"meaning": "new"})
        still_old = registry.verify(child.assertion_id, pin)
        assert old.verified and still_old.verified
        assert old.policy_snapshot == still_old.policy_snapshot
    current = registry.verify(child.assertion_id)
    assert not current.verified
    assert current.effective_integrity == "untrusted"


def test_invalid_replay_never_overwrites_existing_identity() -> None:
    registry = ProvenanceRegistry()
    record = _root_record(registry)
    payload = record.as_dict()
    payload["root_bindings"][0]["record_locator"] = "tampered"
    with pytest.raises(IdentityReplayError, match="commitment mismatch"):
        registry.import_replay(payload, record.commitment)
    assert registry.get(record.assertion_id).commitment == record.commitment

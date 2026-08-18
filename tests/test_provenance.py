"""P1 provenance policy, identity, canonicalization, and pin tests."""

from __future__ import annotations

import copy
import json

import pytest

from provenance import (
    BINDING_VERSION,
    EnvelopeValidationError,
    IdentityReplayError,
    INTEGRITY_LEVELS,
    MAX_VERIFICATION_BYTES,
    MAX_VERIFICATION_DEPTH,
    MAX_VERIFICATION_NODES,
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
    _VerificationContext,
)

_SYNTHETIC_CHANNEL_EVIDENCE = sha256_hex("monitor-owned synthetic fixture")


def _register_synthetic_channel(registry: ProvenanceRegistry) -> None:
    registry._monitor_authority.register_verified_channel(  # pylint: disable=protected-access
        origin_class="synthetic",
        channel_class="synthetic-authenticated",
        channel_locator="fixture://authenticated",
        channel_evidence_sha256=_SYNTHETIC_CHANNEL_EVIDENCE,
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
        channel_evidence_sha256=(
            _SYNTHETIC_CHANNEL_EVIDENCE
            if verified
            else sha256_hex("no authenticated channel")
        ),
    )


def _root_record(registry: ProvenanceRegistry, *, verified: bool = True):
    if verified:
        _register_synthetic_channel(registry)
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


def test_monitor_inventory_is_the_only_root_elevation_authority() -> None:
    registry = ProvenanceRegistry()
    forged = _root()
    forged["origin_evidence"]["channel_locator"] = "fixture://caller-claimed"
    forged_record = registry.mint(
        base_envelope(
            root_bindings=[forged],
            producer_class="trusted_tool",
            producer_assurance="verified",
        )
    )

    forged_result = registry.verify(forged_record.assertion_id)
    assert forged_result.verified
    assert forged_result.effective_integrity == "untrusted"

    _register_synthetic_channel(registry)
    monitor_record = _root_record(registry)
    monitor_result = registry.verify(monitor_record.assertion_id)
    assert monitor_result.verified
    assert monitor_result.effective_integrity == "trusted"


def test_root_transformer_cap_is_applied_on_root_path() -> None:
    registry = ProvenanceRegistry()
    _register_synthetic_channel(registry)
    record = registry.mint(
        base_envelope(
            root_bindings=[_root()],
            transformer_class="llm",
            producer_class="external",
            producer_assurance="claimed",
        )
    )

    result = registry.verify(record.assertion_id)
    assert result.verified
    assert result.effective_integrity == "agent"


def test_origin_class_is_closed_before_it_can_reach_authority_logic() -> None:
    registry = ProvenanceRegistry()
    forged = _root(verified=False)
    forged["origin_class"] = "caller-invented"
    with pytest.raises(EnvelopeValidationError, match="origin_class"):
        registry.mint(base_envelope(root_bindings=[forged]))


def test_llm_meet_never_elevates_an_untrusted_root() -> None:
    registry = ProvenanceRegistry()
    trusted_parent = _root_record(registry)
    untrusted_parent = _root_record(registry, verified=False)
    trusted_child = registry.mint(_derived_template(registry, trusted_parent))
    untrusted_child = registry.mint(_derived_template(registry, untrusted_parent))

    assert registry.verify(trusted_child.assertion_id).effective_integrity == "agent"
    assert registry.verify(untrusted_child.assertion_id).effective_integrity == "untrusted"


@pytest.mark.parametrize(
    ("transformer_class", "expected"),
    [
        ("root", ("untrusted", "agent", "trusted")),
        ("llm", ("untrusted", "agent", "agent")),
        ("unknown-transformer", ("untrusted", "untrusted", "untrusted")),
    ],
)
def test_lattice_caps_and_monotonicity_cover_all_levels(
    transformer_class: str, expected: tuple[str, str, str]
) -> None:
    registry = ProvenanceRegistry()
    untrusted = _root_record(registry, verified=False)
    trusted = _root_record(registry)
    agent = registry.mint(_derived_template(registry, trusted))
    parents = (untrusted, agent, trusted)

    parent_levels = tuple(
        registry.verify(parent.assertion_id).effective_integrity for parent in parents
    )
    assert parent_levels == ("untrusted", "agent", "trusted")
    for parent, parent_level, expected_level in zip(parents, parent_levels, expected):
        child = registry.mint(
            _derived_template(registry, parent, transformer_class=transformer_class)
        )
        child_level = registry.verify(child.assertion_id).effective_integrity
        assert child_level == expected_level
        assert INTEGRITY_LEVELS.index(child_level) <= INTEGRITY_LEVELS.index(parent_level)


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


def test_canonicalization_literal_golden_vector() -> None:
    envelope = base_envelope(
        assertion_id="00000000-0000-4000-8000-000000000001",
        root_bindings=[_root(verified=False)],
        selection_parameters={"z": "é", "a": 1},
    )
    assert canonical_envelope_bytes(envelope) == (
        b'{"ancestry_completeness":"complete","assertion_id":"00000000-0000-4000-8000-000000000001",'
        b'"binding_version":"convmem/provenance-binding-v1","derivation_kind":"root","input_bindings":[],'
        b'"producer_assurance":"unknown","producer_class":"unknown",'
        b'"provenance_policy_sha256":"db5228903350aeb32d373dbdfd4faa3114ac6e599b89b8ae560d2e892a172742",'
        b'"provenance_policy_version":"convmem/provenance-policy-v1",'
        b'"provider_payload_sha256":null,"recipe_config_sha256":null,"root_bindings":[{'
        b'"input_view_sha256":"b686fdce0bf3ff6ee947b8ae82c3bcb8c1ff71374ea27435fb73aaa6760a246b",'
        b'"origin_assurance":"unknown","origin_class":"synthetic",'
        b'"origin_evidence":{"channel_class":"unverified",'
        b'"channel_evidence_sha256":"67a32e84193d6989f0d499427357efe78eefe8f2800b7d207097eb12d6912129",'
        b'"channel_locator":"unverified://none"},'
        b'"raw_record_sha256":"b686fdce0bf3ff6ee947b8ae82c3bcb8c1ff71374ea27435fb73aaa6760a246b",'
        b'"record_locator":"event-1","source_identity":"fixture/source"}],'
        b'"schema_semantics_sha256":"2c923dfaa84846552d606ffdd37e8ea1163dfd318a6e6038c8c9f14fc6cf4927",'
        b'"schema_version":"convmem/provenance-envelope-v1",'
        b'"selection_parameters":{"a":1,"z":"\xc3\xa9"},'
        b'"transformer_artifact_sha256":null,"transformer_class":"root",'
        b'"transformer_identity":"monitor","transformer_recipe_id":"root-v1",'
        b'"transformer_recipe_sha256":"cf2a98a4bb0dc0a5407cdb67f70611b53d396ec88602c03327b7fa44695dc180",'
        b'"transformer_version":"1"}'
    )
    assert provenance_commitment(envelope) == "1849adc132d5d41c1ae3868eaf952b89fd2ccbe3c4373788717e3c34ee6f7418"


def test_registered_schema_semantics_are_snapshot_bound() -> None:
    registry = ProvenanceRegistry()
    schema_version = "convmem/provenance-envelope-v2"
    binding_version = "convmem/provenance-binding-v2"
    semantic_spec = {"meaning": "v2-preserves-envelope"}
    semantic_sha = registry.register_schema_semantics(
        schema_version, binding_version, semantic_spec
    )
    envelope = base_envelope(root_bindings=[_root(verified=False)])
    envelope["schema_version"] = schema_version
    envelope["binding_version"] = binding_version
    envelope["schema_semantics_sha256"] = semantic_sha
    record = registry.mint(envelope)
    assert registry.verify(record.assertion_id).verified

    registry.register_schema_semantics(
        schema_version, binding_version, {"meaning": "v2-reinterpreted"}
    )
    result = registry.verify(record.assertion_id)
    assert not result.verified
    assert "schema semantic" in (result.reason or "")


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


def test_successful_replay_is_idempotent() -> None:
    registry = ProvenanceRegistry()
    record = _root_record(registry)
    before_generation = registry.current_generation
    replayed, was_replay = registry.import_replay(record.as_dict(), record.commitment)

    assert was_replay
    assert replayed.assertion_id == record.assertion_id
    assert replayed.commitment == record.commitment
    assert registry.current_generation == before_generation


def test_recursive_cycle_fails_closed() -> None:
    registry = ProvenanceRegistry()
    record = _root_record(registry)
    with registry.pin() as pin:
        result = registry._verify(  # pylint: disable=protected-access
            record.assertion_id,
            pin,
            context=_VerificationContext(memo={}, active={record.assertion_id}),
        )
    assert not result.verified
    assert result.reason == "cycle detected"


def _make_chain(registry: ProvenanceRegistry, root: object, length: int):
    recipe_id = "bounded-chain-v1"
    recipe_sha = registry.register_recipe(recipe_id, {"kind": "bounded-chain"})
    parent = root
    for _ in range(length):
        parent = registry.mint(
            base_envelope(
                input_bindings=[input_binding(parent, exact_input_view_sha256=sha256_hex("view"))],
                producer_class="agent",
                producer_assurance="claimed",
                derivation_kind="derive",
                transformer_class="llm",
                transformer_identity="fixture-model",
                transformer_version="1",
                transformer_recipe_id=recipe_id,
                transformer_recipe_sha256=recipe_sha,
            )
        )
    return parent


def test_recursive_depth_node_and_byte_budgets_fail_closed() -> None:
    depth_registry = ProvenanceRegistry()
    depth_tip = _make_chain(depth_registry, _root_record(depth_registry), MAX_VERIFICATION_DEPTH + 1)
    depth_result = depth_registry.verify(depth_tip.assertion_id)
    assert not depth_result.verified
    assert "depth budget" in (depth_result.reason or "")

    node_registry = ProvenanceRegistry()
    parents = [_root_record(node_registry) for _ in range(MAX_VERIFICATION_NODES)]
    node_tip = node_registry.mint(
        base_envelope(
            input_bindings=[
                input_binding(parent, exact_input_view_sha256=sha256_hex("view"))
                for parent in parents
            ],
            producer_class="agent",
            producer_assurance="claimed",
            derivation_kind="merge",
            transformer_class="root",
            transformer_identity="monitor",
            transformer_version="1",
            transformer_recipe_id="root-v1",
            transformer_recipe_sha256=sha256_hex(b"convmem:root-recipe-v1"),
        )
    )
    node_result = node_registry.verify(node_tip.assertion_id)
    assert not node_result.verified
    assert "node budget" in (node_result.reason or "")

    byte_registry = ProvenanceRegistry()
    byte_record = byte_registry.mint(
        base_envelope(
            root_bindings=[_root(verified=False)],
            selection_parameters={"oversized": "x" * MAX_VERIFICATION_BYTES},
        )
    )
    byte_result = byte_registry.verify(byte_record.assertion_id)
    assert not byte_result.verified
    assert "byte budget" in (byte_result.reason or "")


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

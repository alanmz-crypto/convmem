"""Deterministic residual evidence controls for the Trapdoor T3 closure lane."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import llm
from eval_corpus.reconstruct import build_canonical_unit
from provenance import (
    ProvenanceRegistry,
    base_envelope,
    input_binding,
    parse_envelope,
    provenance_commitment,
    root_binding,
    sha256_hex,
)
from provenance_binding import attach_unit_provenance, build_ingest_envelope


ROOT = Path(__file__).resolve().parents[1]
MUTATOR_CENSUS = ROOT / "docs/plans/P1-PROVENANCE-MUTATOR-CENSUS.md"
WRITER_INVENTORY = ROOT / "docs/plans/SHADOW-WRITER-COVERAGE-INVENTORY.json"


def _untrusted_root(source: str = "fixture/source") -> dict[str, object]:
    return root_binding(
        source_identity=source,
        record_locator="fixture:0",
        raw_record_sha256=sha256_hex("raw record"),
        input_view_sha256=sha256_hex("raw record"),
        origin_class="external",
        origin_assurance="unknown",
        channel_class="unverified",
        channel_locator="unverified://none",
        channel_evidence_sha256=sha256_hex("no authenticated evidence"),
    )


def _ingest_stage(source: str, content: str, *, model: str) -> dict:
    return build_ingest_envelope(
        records=[{"role": "assistant", "content": content}],
        consumed_views=[content],
        source_identity=source,
        locator_prefix="fixture:0",
        source_type="inter_model_doc",
        transformer_class="llm" if model else "packaging",
        transformer_identity=model or "fixture-packager",
        transformer_version="fixture-v1",
        derivation_kind="summarize" if model else "packaging",
        producer_class="agent" if model else "external",
        producer_assurance="claimed" if model else "unknown",
        selection_parameters={"requested_model": model or "fixture-packager"},
        provider_payload={"model": model or "fixture-packager", "content": content},
        recipe_id="residual-fixture-v1",
        recipe_spec={"kind": "residual-fixture", "model": model or "none"},
        output_locator=f"{source}#unit",
        output_value={"summary": content},
    )


def test_v3f_serialized_envelope_contains_hashes_but_no_secret_material() -> None:
    """V3f: payload meaning is represented by hashes, never secret bytes."""
    secret = "residual-fixture-api-secret-123"
    payload_hash = sha256_hex(secret)
    registry = ProvenanceRegistry()
    record = registry.mint(
        base_envelope(
            root_bindings=[_untrusted_root()],
            selection_parameters={"semantic_payload_sha256": payload_hash},
            provider_payload_sha256=payload_hash,
            recipe_config_sha256=sha256_hex('{"secret_ref":"provider"}'),
        )
    )

    serialized = record.as_dict()
    encoded = json.dumps(serialized, ensure_ascii=False, sort_keys=True)
    parsed = parse_envelope(encoded)

    assert secret not in encoded
    assert "api_key" not in encoded.lower()
    assert "authorization" not in encoded.lower()
    assert parsed["provider_payload_sha256"] == payload_hash
    assert parsed["selection_parameters"]["semantic_payload_sha256"] == payload_hash
    assert provenance_commitment(parsed) == record.commitment


def test_v8c_same_root_does_not_create_corroboration_or_elevation() -> None:
    """V8c: two model paths share lineage but cannot corroborate authority."""
    registry = ProvenanceRegistry()
    root = registry.mint(
        base_envelope(
            root_bindings=[_untrusted_root("fixture/same-root")],
            producer_class="external",
            producer_assurance="unknown",
        )
    )
    recipe_id = "residual-model-v1"
    recipe_sha = registry.register_recipe(recipe_id, {"kind": "residual-model"})

    children = [
        registry.mint(
            base_envelope(
                input_bindings=[
                    input_binding(root, exact_input_view_sha256=sha256_hex("view"))
                ],
                producer_class="agent",
                producer_assurance="claimed",
                derivation_kind="summarize",
                transformer_class="llm",
                transformer_identity=model,
                transformer_version="fixture-v1",
                transformer_recipe_id=recipe_id,
                transformer_recipe_sha256=recipe_sha,
                selection_parameters={"model": model},
                provider_payload_sha256=sha256_hex(model),
                recipe_config_sha256=recipe_sha,
            )
        )
        for model in ("fixture-model-a", "fixture-model-b")
    ]

    results = [registry.verify(child.assertion_id) for child in children]
    assert children[0].assertion_id != children[1].assertion_id
    assert [result.effective_integrity for result in results] == [
        "untrusted",
        "untrusted",
    ]
    assert all(
        child.envelope["input_bindings"][0]["parent_assertion_id"] == root.assertion_id
        for child in children
    )
    assert all(result.reason is None for result in results)


def test_v8e_untrusted_retrieval_conversation_recapture_distill_chain() -> None:
    """V8e: each real-data stage remains untrusted through recapture."""
    source = "retrieval fixture content"
    ingest = _ingest_stage("fixture/source", source, model="")
    unit = attach_unit_provenance(
        {"id": "retrieval-fixture", "summary": source, "keywords": ["fixture"]},
        ingest,
    )
    retrieved = build_canonical_unit(unit)
    conversation = f"Retrieved memory: {retrieved['document']}"
    recaptured = _ingest_stage("fixture/conversation", conversation, model="")
    distilled = _ingest_stage("fixture/distill", conversation, model="fixture-model")

    assert ingest["effective_integrity"] == "untrusted"
    assert recaptured["effective_integrity"] == "untrusted"
    assert distilled["effective_integrity"] == "untrusted"
    assert len({
        ingest["assertion_id"],
        recaptured["assertion_id"],
        distilled["assertion_id"],
    }) == 3


def test_v8g_provider_fallback_is_explicit_and_cannot_elevate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """V8g: fallback is observable and fail-closed mode avoids silent degrade."""
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    monkeypatch.setenv("CONVMEM_FALLBACK_MODEL", "fixture-local")
    binding = llm.resolve_generation_binding("deepseek-v4-fixture")
    assert binding == {
        "provider": "ollama",
        "requested_model": "deepseek-v4-fixture",
        "resolved_model": "fixture-local",
        "fallback": True,
    }

    monkeypatch.setenv("CONVMEM_FAIL_ON_FALLBACK", "1")
    with pytest.raises(llm.ModelFallbackError):
        llm.generate("fixture prompt", "deepseek-v4-fixture", "http://unused")

    degraded = _ingest_stage("fixture/fallback", "fallback content", model="deepseek-v4-fixture")
    assert degraded["effective_integrity"] == "untrusted"


def test_v4m_finalized_p1_p3_census_is_explicitly_revalidated_but_not_promoted() -> None:
    """V4m: inventory is inspectable; final universal proof stays pending."""
    census = MUTATOR_CENSUS.read_text(encoding="utf-8")
    inventory = json.loads(WRITER_INVENTORY.read_text(encoding="utf-8"))

    for marker in ("## P1 authority set", "## P2 revalidation", "## P3 revalidation"):
        assert marker in census
    for mutator in (
        "ProvenanceRegistry.mint()",
        "ingest._commit_chunk_to_stores()",
        "ChromaStore.add_unit()",
        "ingest_dedupe.evaluate_ingest_batch()",
        "refine.job_chroma_dedupe()",
    ):
        assert mutator in census
    assert inventory["must_use_factory_bypass_sites"] == []
    assert inventory["must_use_factory_count"] == 0
    assert inventory["production_chroma_write_session_call_sites"]
    assert inventory["open_production_write_store_call_sites"]
    assert "**V4m: PENDING.**" in census

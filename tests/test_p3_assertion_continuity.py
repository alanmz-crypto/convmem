"""P3 adversarial tests for assertion identity versus content equivalence."""

from __future__ import annotations

from pathlib import Path

import pytest

from chroma_store import ChromaStore
from evidence import dedupe_results_by_ledger_id
from ingest_dedupe import evaluate_ingest_batch
from provenance import (
    IdentityReplayError,
    ProvenanceRegistry,
    base_envelope,
    input_binding,
    root_binding,
)
from provenance_binding import (
    attach_unit_provenance,
    build_ingest_envelope,
    projection_metadata,
)
from refine import apply_dedupe_queue_record, job_chroma_dedupe


def _provenance_row(
    unit_id: str,
    source_identity: str,
    document: str = "identical content",
    *,
    ledger_id: str = "obs_shared",
) -> tuple[dict, str, list[float], dict]:
    envelope = build_ingest_envelope(
        records=[{"source": source_identity, "content": document}],
        consumed_views=[document],
        source_identity=source_identity,
        locator_prefix="fixture:0",
        source_type="inter_model_doc",
        transformer_class="packaging",
        transformer_identity="p3-fixture",
        transformer_version="p3-v1",
        derivation_kind="packaging",
        producer_class="external",
        producer_assurance="claimed",
        selection_parameters={"source": source_identity},
        provider_payload={"content": document},
        recipe_id="p3-fixture-v1",
        recipe_spec={"kind": "p3-fixture"},
        output_locator=f"{source_identity}#unit",
        output_value={"summary": document},
    )
    unit = attach_unit_provenance(
        {
            "id": unit_id,
            "title": "P3 fixture",
            "summary": document,
            "keywords": ["p3", "fixture", "identity"],
            "source_path": source_identity,
        },
        envelope,
    )
    metadata = {
        "id": unit_id,
        "title": "P3 fixture",
        "source_path": source_identity,
        "ledger_id": ledger_id,
        **projection_metadata(unit),
    }
    return unit, document, [1.0, 0.0], metadata


def _cfg(tmp_path: Path) -> dict:
    return {
        "index": {"chroma_dir": str(tmp_path / "chroma")},
        "ingest_dedup": {
            "semantic_similarity": 0.92,
            "candidate_k": 10,
            "max_semantic_candidates_per_unit": 3,
        },
        "refine": {"dedupe_similarity": 0.92},
        "models": {},
    }


def _registry_root(source: str) -> dict:
    return root_binding(
        source_identity=source,
        record_locator="fixture:0",
        raw_record_sha256="0" * 64,
        input_view_sha256="1" * 64,
        origin_class="external",
    )


def test_exact_content_with_distinct_provenance_remains_accepted(tmp_path: Path) -> None:
    chroma = tmp_path / "chroma"
    chroma.mkdir()
    store = ChromaStore(str(chroma))
    try:
        existing = _provenance_row("existing", "source-a")
        incoming = _provenance_row("incoming", "source-b")
        store.add_unit(existing[0]["id"], existing[1], existing[2], existing[3])

        result = evaluate_ingest_batch(store, _cfg(tmp_path), [incoming])

        assert [row[0]["id"] for row in result.accepted] == ["incoming"]
        assert result.exact_suppressions == []
    finally:
        store.close()


def test_content_only_match_cannot_alias_new_row_to_authoritative_projection(
    tmp_path: Path,
) -> None:
    chroma = tmp_path / "chroma"
    chroma.mkdir()
    store = ChromaStore(str(chroma))
    try:
        existing = _provenance_row("existing", "source-a")
        incoming = {
            "id": "legacy-incoming",
            "summary": "identical content",
        }, "identical content", [1.0, 0.0], {"id": "legacy-incoming"}
        store.add_unit(existing[0]["id"], existing[1], existing[2], existing[3])

        result = evaluate_ingest_batch(store, _cfg(tmp_path), [incoming])

        assert [row[0]["id"] for row in result.accepted] == ["legacy-incoming"]
        assert result.exact_suppressions == []
    finally:
        store.close()


def test_retrieval_keeps_same_ledger_id_when_assertions_have_distinct_provenance():
    first = _provenance_row("first", "source-a")[3]
    second = _provenance_row("second", "source-b")[3]
    results = [
        {"id": "first", "metadata": first, "rank_score": 0.9},
        {"id": "second", "metadata": second, "rank_score": 0.8},
    ]

    kept = dedupe_results_by_ledger_id(results)

    assert [row["id"] for row in kept] == ["first", "second"]
    assert all(row["metadata"].get("provenance_commitment") for row in kept)


def test_retrieval_keeps_integrity_fields_independent_for_duplicate_content():
    first = _provenance_row("first", "source-a")[3]
    second = _provenance_row("second", "source-b")[3]
    first["effective_integrity"] = "untrusted"
    second["effective_integrity"] = "trusted"
    results = [
        {"id": "first", "metadata": first},
        {"id": "second", "metadata": second},
    ]

    kept = dedupe_results_by_ledger_id(results)

    assert [row["metadata"]["effective_integrity"] for row in kept] == [
        "untrusted",
        "trusted",
    ]


def test_approved_semantic_tombstone_requires_provenance_adjudication(
    tmp_path: Path,
) -> None:
    chroma = tmp_path / "chroma"
    chroma.mkdir()
    store = ChromaStore(str(chroma))
    try:
        canonical = _provenance_row("canonical", "source-a")
        duplicate = _provenance_row("duplicate", "source-b")
        store.add_unit(canonical[0]["id"], canonical[1], canonical[2], canonical[3])
        store.add_unit(duplicate[0]["id"], duplicate[1], duplicate[2], duplicate[3])

        stats = apply_dedupe_queue_record(
            store,
            _cfg(tmp_path),
            {
                "status": "approved_merge_a_canonical",
                "canonical_id": "canonical",
                "tombstone_id": "duplicate",
            },
            verbose=False,
        )

        assert stats["tombstoned"] == 0
        assert stats["errors"] == 1
        assert not (store.get_unit("duplicate") or {}).get("metadata", {}).get(
            "superseded"
        )
    finally:
        store.close()


def test_automatic_ledger_dedupe_does_not_tombstone_distinct_assertions(
    tmp_path: Path,
) -> None:
    chroma = tmp_path / "chroma"
    chroma.mkdir()
    store = ChromaStore(str(chroma))
    try:
        first = _provenance_row("first", "source-a")
        second = _provenance_row("second", "source-b")
        store.add_unit(first[0]["id"], first[1], first[2], first[3])
        store.add_unit(second[0]["id"], second[1], second[2], second[3])

        stats = job_chroma_dedupe(store, _cfg(tmp_path), verbose=False)

        assert stats["tombstoned"] == 0
        assert not (store.get_unit("first") or {}).get("metadata", {}).get(
            "superseded"
        )
        assert not (store.get_unit("second") or {}).get("metadata", {}).get(
            "superseded"
        )
    finally:
        store.close()


def test_same_content_without_replay_pair_gets_new_monitor_assertion():
    registry = ProvenanceRegistry()
    first = registry.mint(
        base_envelope(
            root_bindings=[_registry_root("source-a")],
            selection_parameters={"content": "same"},
            provider_payload_sha256="0" * 64,
            recipe_config_sha256="1" * 64,
        )
    )
    second = registry.mint(
        base_envelope(
            root_bindings=[_registry_root("source-b")],
            selection_parameters={"content": "same"},
            provider_payload_sha256="0" * 64,
            recipe_config_sha256="1" * 64,
        )
    )

    assert first.assertion_id != second.assertion_id


def test_invalid_parent_identity_replay_fails_closed():
    registry = ProvenanceRegistry()
    parent = registry.mint(
        base_envelope(
            root_bindings=[_registry_root("source-parent")],
            selection_parameters={"content": "parent"},
            provider_payload_sha256="0" * 64,
            recipe_config_sha256="1" * 64,
        )
    )
    child = registry.mint(
        base_envelope(
            input_bindings=[input_binding(parent, exact_input_view_sha256="2" * 64)],
            derivation_kind="packaging",
            transformer_class="packaging",
            transformer_identity="p3-fixture",
            transformer_version="p3-v1",
            selection_parameters={"content": "child"},
            provider_payload_sha256="0" * 64,
            recipe_config_sha256="1" * 64,
        )
    )
    tampered = child.as_dict()
    tampered["input_bindings"][0]["parent_assertion_id"] = parent.assertion_id[:-1] + "0"

    with pytest.raises(IdentityReplayError):
        registry.import_replay(tampered, child.commitment)

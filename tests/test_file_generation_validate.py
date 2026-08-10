from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from chroma_store import SUMMARIES, UNITS
from file_generation_builder import build_candidate_generation
from file_generation_contract import build_generation_manifest
from file_generation_pointer import (
    GenerationQualificationError,
    publish_active_pointer,
    publish_manifest,
    recover_active_pointer,
)
from file_generation_store import FileGenerationStore, StagedRow
from file_generation_validate import cold_validate, run_cold_validation
from projection_parity import entity_key


class EmptyCommittedView:
    def query_units(self, _embedding, _top_k):
        return []

    def get_unit(self, _unit_id):
        return None


def _candidate(source: Path):
    raw = source.read_bytes()
    return build_candidate_generation(
        source_path=str(source),
        source_bytes=raw,
        parse=lambda _raw: [{"start_offset": 0, "end_offset": 1}],
        extract_chunk=lambda _chunk: (
            "summary",
            [{"document": "committed fact", "metadata": {"title": "Fact"}}],
        ),
        embed=lambda text: [1.0, float(len(text) % 2)],
        committed_store=EmptyCommittedView(),
        dedupe_cfg={"ingest_dedup": {"candidate_k": 10}},
        pipeline_fingerprint={
            "parser": "test-parser-v1",
            "chunk": "test-chunk-v1",
            "model": "test-model-v1",
            "prompt": "test-prompt-v1",
        },
        embedding_model="test-embed-v1",
    )


def _staged(candidate):
    return [
        StagedRow(
            row.collection_name,
            row.physical_id,
            row.logical_id,
            row.document,
            list(row.embedding),
            row.metadata,
            "file",
            candidate.owner_digest,
            candidate.generation_id,
        )
        for row in candidate.all_rows
    ]


def _prepare_staged_generation(tmp_path: Path, label: str):
    source = tmp_path / f"source-{label}.jsonl"
    source.write_text(f"source-{label}", encoding="utf-8")
    chroma = tmp_path / f"chroma-{label}"
    generations = tmp_path / f"generations-{label}"
    candidate = _candidate(source)
    with FileGenerationStore(chroma, active_generations=dict) as store:
        store.stage_rows(_staged(candidate))
        collections = {
            name: store.build_manifest_collection_spec(
                name,
                owner_digest=candidate.owner_digest,
                generation_id=candidate.generation_id,
                embedding_model="test-embed-v1",
                embedding_dimension=2,
            )
            for name in (UNITS, SUMMARIES)
        }
    manifest = build_generation_manifest(
        owner_key=candidate.ownership_key,
        generation_id=candidate.generation_id,
        canonical_source=candidate.canonical_source_path,
        source_hash=candidate.source_hash,
        candidate_bundle_hash=candidate.candidate_bundle_hash,
        fingerprints={"pipeline": candidate.pipeline_fingerprint},
        collections=collections,
        suppression_outcomes=candidate.exact_suppressions,
        known_projection_loss_risks=candidate.known_projection_loss_risks,
    )
    return source, chroma, generations, candidate, publish_manifest(generations, manifest)


def _corrupt_immutable_document(chroma: Path, candidate) -> None:
    with FileGenerationStore(chroma, active_generations=dict) as store:
        collection = store.raw_store._collection(UNITS)  # pylint: disable=protected-access
        collection.update(
            ids=[candidate.unit_rows[0].physical_id],
            documents=["corrupted by caller revalidation"],
            embeddings=[list(candidate.unit_rows[0].embedding)],
        )


def test_revalidator_mutation_cannot_cross_final_cold_qualification(
    tmp_path: Path,
) -> None:
    _, chroma, generations, candidate, reference = _prepare_staged_generation(
        tmp_path, "publish"
    )

    def corrupt_before_publish(_manifest):
        _corrupt_immutable_document(chroma, candidate)
        return True

    with pytest.raises(GenerationQualificationError, match="fresh-process exact generation"):
        publish_active_pointer(
            generations,
            reference,
            chroma_dir=chroma,
            cfg={"index": {"processed_log": str(tmp_path / "processed.json")}},
            expected_previous_generation_id=None,
            backend_fingerprint="rust-bindings/test",
            candidate_revalidator=corrupt_before_publish,
        )
    assert (
        __import__("file_generation_pointer").read_unqualified_pointer(
            generations, candidate.owner_digest
        )
        is None
    )

    _, recovery_chroma, recovery_generations, recovery_candidate, recovery_reference = (
        _prepare_staged_generation(tmp_path, "recover")
    )
    publish_active_pointer(
        recovery_generations,
        recovery_reference,
        chroma_dir=recovery_chroma,
        cfg={"index": {"processed_log": str(tmp_path / "processed-recover.json")}},
        expected_previous_generation_id=None,
        backend_fingerprint="rust-bindings/test",
    )

    def corrupt_before_recovery(_manifest):
        _corrupt_immutable_document(recovery_chroma, recovery_candidate)
        return True

    with pytest.raises(GenerationQualificationError, match="fresh-process exact generation"):
        recover_active_pointer(
            recovery_generations,
            recovery_candidate.ownership_key,
            chroma_dir=recovery_chroma,
            cfg={"index": {"processed_log": str(tmp_path / "processed-recover.json")}},
            recovery_revalidator=corrupt_before_recovery,
        )


def test_cold_process_validation_precedes_pointer_and_export_view_round_trips(
    tmp_path: Path,
) -> None:
    source = tmp_path / "source.jsonl"
    source.write_text("source-v1", encoding="utf-8")
    chroma = tmp_path / "chroma"
    generations = tmp_path / "generations"
    active: dict[str, str] = {}
    candidate = _candidate(source)

    with FileGenerationStore(chroma, active_generations=lambda: active) as store:
        store.stage_rows(_staged(candidate))
        collections = {
            name: store.build_manifest_collection_spec(
                name,
                owner_digest=candidate.owner_digest,
                generation_id=candidate.generation_id,
                embedding_model="test-embed-v1",
                embedding_dimension=2,
            )
            for name in (UNITS, SUMMARIES)
        }
        # Candidate rows exist but no qualified active resolver exposes them.
        assert store.count_units() == 0

    manifest = build_generation_manifest(
        owner_key=candidate.ownership_key,
        generation_id=candidate.generation_id,
        canonical_source=candidate.canonical_source_path,
        source_hash=candidate.source_hash,
        candidate_bundle_hash=candidate.candidate_bundle_hash,
        fingerprints={"pipeline": candidate.pipeline_fingerprint},
        collections=collections,
        suppression_outcomes=candidate.exact_suppressions,
        known_projection_loss_risks=candidate.known_projection_loss_risks,
    )
    reference = publish_manifest(generations, manifest)

    # Both direct reopen and a genuinely fresh interpreter prove the exact set.
    assert cold_validate(chroma, manifest)["valid"] is True
    child = run_cold_validation(
        chroma,
        reference.path,
        expected_manifest_sha256=reference.file_sha256,
    )
    assert child["valid"] is True
    assert child["manifest_sha256"] == reference.file_sha256
    with pytest.raises(RuntimeError, match="manifest hash mismatch"):
        run_cold_validation(
            chroma,
            reference.path,
            expected_manifest_sha256="0" * 64,
        )

    qualified = publish_active_pointer(
        generations,
        reference,
        chroma_dir=chroma,
        cfg={"index": {"processed_log": str(tmp_path / "processed.json")}},
        expected_previous_generation_id=None,
        backend_fingerprint="rust-bindings/test",
        candidate_revalidator=lambda value: (
            hashlib.sha256(source.read_bytes()).hexdigest() == value["source_hash"]
        ),
    )
    active[candidate.owner_digest] = qualified.pointer["active_generation_id"]

    with FileGenerationStore(chroma, active_generations=lambda: active) as serving:
        assert serving.count_units() == 1
        promoted = serving.get_unit_by_logical_id(candidate.unit_rows[0].logical_id)
        assert promoted is not None
        assert promoted["id"] == candidate.unit_rows[0].physical_id

    logical = candidate.unit_rows[0].logical_id
    original_export = {"id": logical, "source_path": str(source)}
    reconstructed_export = {
        "id": next(iter(collections[UNITS]["logical_to_physical"])),
        "source_path": str(source),
    }
    assert (
        entity_key(original_export)
        == entity_key(reconstructed_export)
        == f"id:{logical}"
    )
    assert promoted["metadata"]["id"] == candidate.unit_rows[0].physical_id

    # Recovery has the same mandatory fresh-process qualification boundary as
    # promotion.  No caller-supplied truthy callback can mint authority.
    recovered = recover_active_pointer(
        generations,
        candidate.ownership_key,
        chroma_dir=chroma,
        cfg={"index": {"processed_log": str(tmp_path / "processed.json")}},
    )
    assert recovered.recovered is True

    # A subsequent persisted immutable mismatch also blocks recovery: visible
    # pointer bytes never let recovery guess or accept a partial generation.
    physical_id = candidate.unit_rows[0].physical_id
    with FileGenerationStore(chroma, active_generations=lambda: active) as store:
        collection = store.raw_store._collection(UNITS)  # pylint: disable=protected-access
        collection.update(
            ids=[physical_id],
            documents=["corrupted after promotion"],
            embeddings=[list(candidate.unit_rows[0].embedding)],
        )
    with pytest.raises(GenerationQualificationError, match="fresh-process exact generation"):
        recover_active_pointer(
            generations,
            candidate.ownership_key,
            chroma_dir=chroma,
            cfg={"index": {"processed_log": str(tmp_path / "processed.json")}},
        )


def test_cold_validation_fails_after_corruption_in_fresh_process(
    tmp_path: Path,
) -> None:
    """A closed/reopened validator must reject persisted immutable row corruption."""
    source = tmp_path / "source.jsonl"
    source.write_text("source-v1", encoding="utf-8")
    chroma = tmp_path / "chroma"
    generations = tmp_path / "generations"
    candidate = _candidate(source)

    with FileGenerationStore(chroma, active_generations=dict) as store:
        store.stage_rows(_staged(candidate))
        collections = {
            name: store.build_manifest_collection_spec(
                name,
                owner_digest=candidate.owner_digest,
                generation_id=candidate.generation_id,
                embedding_model="test-embed-v1",
                embedding_dimension=2,
            )
            for name in (UNITS, SUMMARIES)
        }

    manifest = build_generation_manifest(
        owner_key=candidate.ownership_key,
        generation_id=candidate.generation_id,
        canonical_source=candidate.canonical_source_path,
        source_hash=candidate.source_hash,
        candidate_bundle_hash=candidate.candidate_bundle_hash,
        fingerprints={"pipeline": candidate.pipeline_fingerprint},
        collections=collections,
        suppression_outcomes=candidate.exact_suppressions,
        known_projection_loss_risks=candidate.known_projection_loss_risks,
    )
    reference = publish_manifest(generations, manifest)

    # Corrupt an enforced immutable field after the manifest is durable, then
    # close this writer before the validator spawns a new interpreter.
    physical_id = candidate.unit_rows[0].physical_id
    with FileGenerationStore(chroma, active_generations=dict) as store:
        collection = store.raw_store._collection(UNITS)  # pylint: disable=protected-access
        collection.update(
            ids=[physical_id],
            documents=["corrupted fact"],
            embeddings=[list(candidate.unit_rows[0].embedding)],
        )

    with pytest.raises(RuntimeError, match="document hash mismatch"):
        run_cold_validation(chroma, reference.path)

    # The public promotion API runs that same fresh-process qualification
    # itself; corrupt persisted rows cannot be promoted by supplying a fake
    # truthy validator because it has no validator argument.
    with pytest.raises(GenerationQualificationError, match="fresh-process exact generation"):
        publish_active_pointer(
            generations,
            reference,
            chroma_dir=chroma,
            cfg={"index": {"processed_log": str(tmp_path / "processed.json")}},
            expected_previous_generation_id=None,
            backend_fingerprint="rust-bindings/test",
        )

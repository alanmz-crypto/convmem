from __future__ import annotations

import copy
import hashlib
from pathlib import Path

import pytest

from file_generation_contract import (
    GenerationContractError,
    build_active_pointer,
    build_generation_manifest,
    candidate_bundle_hash,
    canonical_hash,
    canonical_source_path,
    make_generation_id,
    make_physical_id,
    owner_digest,
    ownership_key,
    validate_active_pointer,
    validate_generation_manifest,
)


def _manifest(source: Path, *, source_hash: str = "source-a") -> dict:
    canonical = canonical_source_path(source)
    key = ownership_key(source)
    unit_logical = "unit-logical"
    summary_logical = "summary-logical"
    bundle_hash = candidate_bundle_hash(
        [{"logical_id": unit_logical, "document": "fact a"}],
        [{"logical_id": summary_logical, "document": "summary a"}],
    )
    generation = make_generation_id(
        owner_digest=owner_digest(key),
        source_hash=source_hash,
        pipeline_fingerprint="pipeline-a",
        candidate_bundle_hash=bundle_hash,
    )
    unit_physical = make_physical_id("knowledge_units", generation, unit_logical)
    summary_physical = make_physical_id(
        "conversation_summaries", generation, summary_logical
    )
    return build_generation_manifest(
        owner_key=key,
        generation_id=generation,
        canonical_source=canonical,
        source_hash=source_hash,
        candidate_bundle_hash=bundle_hash,
        fingerprints={
            "parser": "parser-a",
            "chunk": "chunk-a",
            "model": "model-a",
            "prompt": "prompt-a",
            "pipeline": "pipeline-a",
        },
        collections={
            "knowledge_units": {
                "collection_uuid": "units-uuid",
                "configuration": {"space": "cosine"},
                "embedding_model": "embed-a",
                "embedding_dimension": 3,
                "logical_to_physical": {unit_logical: unit_physical},
                "rows": {
                    unit_physical: {
                        "logical_id": unit_logical,
                        "document_hash": canonical_hash("fact a"),
                        "embedding_hash": canonical_hash([1.0, 0.0, 0.0]),
                        "embedding_dimension": 3,
                        "embedding_model": "embed-a",
                        "immutable_metadata": {
                            "start_offset": 0,
                            "content_hash": canonical_hash("fact a"),
                        },
                    }
                },
            },
            "conversation_summaries": {
                "collection_uuid": "summaries-uuid",
                "configuration": {"space": "cosine"},
                "embedding_model": "embed-a",
                "embedding_dimension": 3,
                "logical_to_physical": {summary_logical: summary_physical},
                "rows": {
                    summary_physical: {
                        "logical_id": summary_logical,
                        "document_hash": canonical_hash("summary a"),
                        "embedding_hash": canonical_hash([0.0, 1.0, 0.0]),
                        "embedding_dimension": 3,
                        "embedding_model": "embed-a",
                        "immutable_metadata": {
                            "start_offset": 0,
                            "content_hash": canonical_hash("summary a"),
                        },
                    }
                },
            },
        },
        recorded_only_annotations={"domain": "coding", "updated_at": "later"},
    )


def test_path_aliases_have_one_owner(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "real" / "source.jsonl"
    source.parent.mkdir()
    source.write_text("{}\n", encoding="utf-8")
    alias_dir = tmp_path / "alias"
    alias_dir.symlink_to(source.parent, target_is_directory=True)
    monkeypatch.chdir(tmp_path)

    forms = [
        source,
        Path("real/source.jsonl"),
        alias_dir / "source.jsonl",
        source.parent / ".." / "real" / "source.jsonl",
    ]
    keys = {ownership_key(path) for path in forms}
    assert keys == {f"source:{source.resolve()}"}
    assert len({owner_digest(key) for key in keys}) == 1


def test_candidate_bundle_is_pre_dedupe_and_physical_id_independent() -> None:
    base = {
        "id": "logical-a",
        "logical_id": "logical-a",
        "document": "same",
        "metadata": {"logical_id": "logical-a", "quality": 1},
    }
    physicalized = copy.deepcopy(base)
    physicalized["physical_id"] = "fg1_one"
    physicalized["metadata"].update({"id": "fg1_one", "physical_id": "fg1_one"})
    assert candidate_bundle_hash([base], []) == candidate_bundle_hash(
        [physicalized], []
    )

    changed = copy.deepcopy(base)
    changed["document"] = "different extraction"
    assert candidate_bundle_hash([base], []) != candidate_bundle_hash([changed], [])


def test_generation_changes_for_nondeterministic_extraction() -> None:
    key = ownership_key("/tmp/example.jsonl")
    kwargs = {
        "owner_digest": owner_digest(key),
        "source_hash": "same-source",
        "pipeline_fingerprint": "same-pipeline",
    }
    first = make_generation_id(
        **kwargs, candidate_bundle_hash=candidate_bundle_hash([{"text": "a"}], [])
    )
    second = make_generation_id(
        **kwargs, candidate_bundle_hash=candidate_bundle_hash([{"text": "b"}], [])
    )
    assert first != second
    assert make_physical_id("knowledge_units", first, "logical") != make_physical_id(
        "knowledge_units", second, "logical"
    )


def test_manifest_and_pointer_hashes_fail_closed(tmp_path: Path) -> None:
    source = tmp_path / "source.jsonl"
    source.write_text("x", encoding="utf-8")
    manifest = _manifest(source)
    validate_generation_manifest(manifest)

    mutated = copy.deepcopy(manifest)
    physical = next(iter(mutated["collections"]["knowledge_units"]["rows"]))
    mutated["collections"]["knowledge_units"]["rows"][physical]["document_hash"] = (
        "tampered"
    )
    with pytest.raises(GenerationContractError, match="manifest_payload_hash mismatch"):
        validate_generation_manifest(mutated)

    pointer = build_active_pointer(
        manifest=manifest,
        manifest_filename=f"{manifest['owner_digest']}--{manifest['generation_id']}.json",
        manifest_sha256=hashlib.sha256(b"manifest file").hexdigest(),
        previous_generation_id=None,
        backend_fingerprint="rust-bindings-a",
        published_at="2026-08-10T00:00:00Z",
    )
    validate_active_pointer(pointer)
    pointer["active_generation_id"] = "other"
    with pytest.raises(GenerationContractError, match="pointer_payload_hash mismatch"):
        validate_active_pointer(pointer)


def test_owner_mismatch_is_rejected(tmp_path: Path) -> None:
    source = tmp_path / "source.jsonl"
    source.write_text("x", encoding="utf-8")
    manifest = _manifest(source)
    manifest["owner_key"] = ownership_key(tmp_path / "other.jsonl")
    # Re-hashing must not make an owner/source mismatch acceptable.
    unsigned = dict(manifest)
    unsigned.pop("manifest_payload_hash")
    manifest["manifest_payload_hash"] = canonical_hash(unsigned)
    with pytest.raises(GenerationContractError, match="owner/source mismatch"):
        validate_generation_manifest(manifest)

"""D1 reference-v2 retained rollback baseline oracles."""

# pylint: disable=duplicate-code,protected-access

from __future__ import annotations

import copy
import hashlib
import inspect
import struct
from dataclasses import replace
from unittest.mock import patch

import pytest
from chromadb.errors import DuplicateIDError

from cg2_legacy_vector_attestation import (
    D0AttestationError,
    KNOWN_MODEL_AND_VECTOR_V1,
    LEGACY_EXACT_VECTOR_UNKNOWN_MODEL_V1,
    vector_encoding_sha256,
)
from cg2_retained_reference import (
    READER_CALL_LOG,
    RetainedReferenceError,
    RetainedReferenceTargetDescriptor,
    build_descriptor_from_manifest,
    qualify_retained_reference_membership,
    read_retained_reference_rows,
    serving_selector_fingerprint,
)
from cg2_rollback_baseline import (
    CONVERT_V1_FINGERPRINT,
    REFERENCE_V2_FINGERPRINT,
    RollbackBaselineError,
    retain_reference_v2_rollback_baseline,
    validate_retained_rollback_baseline_evidence_v2,
)
from chroma_store import SUMMARIES, UNITS, ChromaStore
from complete_data_restore import validate_reference_v2_recovery_eligibility
from file_generation_builder import build_candidate_generation
from file_generation_contract import (
    FAILED_CONVERT_V1_TARGET_ID,
    _REFERENCE_V2_FORBIDDEN_MANIFEST_KEYS,
    build_generation_manifest,
    canonical_hash,
    canonical_source_path,
    is_failed_convert_v1_target_id,
    make_generation_id,
    refuse_failed_convert_v1_target_id,
)
from file_generation_pointer import (
    load_manifest_reference,
    publish_first_cutover_active_pointer,
    publish_manifest,
    rollback_active_pointer,
)
from file_generation_store import FileGenerationStore, StagedRow
from file_generation_validate import cold_validate_reference_v2
from serving_authority import publish_legacy_fence

from tests.test_cg2_first_cutover import EmptyCommittedView
from tests.test_cg2_rollback_baseline import (
    EMBED_DIM,
    EMBED_MODEL,
    _mock_d0_runtime,
    _mock_hermetic_production_paths,
    _mock_ollama_only,
    _prepare,
    _ratify_d0_chain,
)


def _retain_v2(*, cfg, store, generation_root, owner_digest_value, ratification_id):
    return retain_reference_v2_rollback_baseline(
        cfg=cfg,
        store=store,
        generation_root=generation_root,
        owner_digest_value=owner_digest_value,
        ratification_id=ratification_id,
    )


@pytest.fixture(name="ref_v2_env")
def _ref_v2_env_fixture(tmp_path, monkeypatch):
    _mock_hermetic_production_paths(monkeypatch, tmp_path)
    _mock_d0_runtime(monkeypatch, tmp_path)
    source, accepted_hash, chroma, generations, cfg, seeded = _prepare(tmp_path)
    owner_digest_value, ratification_id, candidate_body, _cand, _val = _ratify_d0_chain(
        cfg, source, accepted_hash
    )
    return {
        "source": source,
        "accepted_hash": accepted_hash,
        "chroma": chroma,
        "generations": generations,
        "cfg": cfg,
        "seeded": seeded,
        "owner_digest": owner_digest_value,
        "ratification_id": ratification_id,
        "candidate_body": candidate_body,
    }


def test_deterministic_reference_v2_target_id(ref_v2_env):
    assert REFERENCE_V2_FINGERPRINT == "convmem/cg2-rollback-baseline-reference-v2"
    env = ref_v2_env
    with FileGenerationStore(env["chroma"], active_generations=dict) as store:
        first = _retain_v2(
            cfg=env["cfg"],
            store=store,
            generation_root=env["generations"],
            owner_digest_value=env["owner_digest"],
            ratification_id=env["ratification_id"],
        )
        second = _retain_v2(
            cfg=env["cfg"],
            store=store,
            generation_root=env["generations"],
            owner_digest_value=env["owner_digest"],
            ratification_id=env["ratification_id"],
        )
    assert first.generation_id == second.generation_id
    assert first.selector_fingerprint == second.selector_fingerprint


def test_reference_v2_id_differs_from_convert_v1(ref_v2_env):
    env = ref_v2_env
    with FileGenerationStore(env["chroma"], active_generations=dict) as store:
        result = _retain_v2(
            cfg=env["cfg"],
            store=store,
            generation_root=env["generations"],
            owner_digest_value=env["owner_digest"],
            ratification_id=env["ratification_id"],
        )
    convert_id = make_generation_id(
        owner_digest=result.owner_digest,
        source_hash=result.snapshot.accepted_source_hash,
        pipeline_fingerprint=CONVERT_V1_FINGERPRINT,
        candidate_bundle_hash=result.snapshot.candidate_bundle_hash,
    )
    assert result.generation_id != convert_id
    assert result.generation_id != FAILED_CONVERT_V1_TARGET_ID


def test_failed_convert_v1_target_id_refuses():
    assert is_failed_convert_v1_target_id(FAILED_CONVERT_V1_TARGET_ID)
    with pytest.raises(Exception):
        refuse_failed_convert_v1_target_id(FAILED_CONVERT_V1_TARGET_ID)


def test_zero_copied_vector_rows(ref_v2_env, monkeypatch):
    env = ref_v2_env
    stage_calls: list[int] = []

    def _spy_stage(self, rows):
        stage_calls.append(1)

    monkeypatch.setattr(FileGenerationStore, "stage_rows", _spy_stage)

    with FileGenerationStore(env["chroma"], active_generations=dict) as store:
        _retain_v2(
            cfg=env["cfg"],
            store=store,
            generation_root=env["generations"],
            owner_digest_value=env["owner_digest"],
            ratification_id=env["ratification_id"],
        )
    assert stage_calls == []


def test_reference_v2_happy_path(ref_v2_env):
    env = ref_v2_env
    with FileGenerationStore(env["chroma"], active_generations=dict) as store:
        result = _retain_v2(
            cfg=env["cfg"],
            store=store,
            generation_root=env["generations"],
            owner_digest_value=env["owner_digest"],
            ratification_id=env["ratification_id"],
        )
    evidence = validate_retained_rollback_baseline_evidence_v2(
        env["generations"],
        owner_digest_value=env["owner_digest"],
        generation_id=result.generation_id,
        expected_manifest_sha256=result.manifest_sha256,
    )
    assert evidence["reference_fingerprint"] == REFERENCE_V2_FINGERPRINT
    assert evidence["proof_profile"] == LEGACY_EXACT_VECTOR_UNKNOWN_MODEL_V1


def test_same_reader_spy_qualification_and_serving(ref_v2_env):
    env = ref_v2_env
    READER_CALL_LOG.clear()
    with FileGenerationStore(env["chroma"], active_generations=dict) as store:
        result = _retain_v2(
            cfg=env["cfg"],
            store=store,
            generation_root=env["generations"],
            owner_digest_value=env["owner_digest"],
            ratification_id=env["ratification_id"],
        )
        reference = load_manifest_reference(
            env["generations"],
            manifest_filename=result.manifest_filename,
            expected_sha256=result.manifest_sha256,
        )
        descriptor = build_descriptor_from_manifest(reference.manifest)
        cold = cold_validate_reference_v2(env["chroma"], reference.manifest, descriptor=descriptor)
        assert cold["valid"] is True
        query_store = FileGenerationStore(
            env["chroma"],
            active_generations=lambda: {env["owner_digest"]: result.generation_id},
            reference_v2_descriptors=lambda: {env["owner_digest"]: descriptor},
        )
        try:
            hits = query_store.query_units([1.0, 0.0], top_k=3, owner_digest=env["owner_digest"])
        finally:
            query_store.close()
    assert hits
    assert READER_CALL_LOG
    assert cold.get("reader_log")


def test_serving_reads_referenced_rows_only(ref_v2_env):
    env = ref_v2_env
    with FileGenerationStore(env["chroma"], active_generations=dict) as store:
        result = _retain_v2(
            cfg=env["cfg"],
            store=store,
            generation_root=env["generations"],
            owner_digest_value=env["owner_digest"],
            ratification_id=env["ratification_id"],
        )
        reference = load_manifest_reference(
            env["generations"],
            manifest_filename=result.manifest_filename,
            expected_sha256=result.manifest_sha256,
        )
        descriptor = build_descriptor_from_manifest(reference.manifest)
        expected_ids = {
            physical_id
            for spec in descriptor.collections.values()
            for physical_id in list(dict(spec).get("physical_ids") or [])
        }
        query_store = FileGenerationStore(
            env["chroma"],
            active_generations=lambda: {env["owner_digest"]: result.generation_id},
            reference_v2_descriptors=lambda: {env["owner_digest"]: descriptor},
        )
        try:
            hits = query_store.query_units([1.0, 0.0], top_k=10, owner_digest=env["owner_digest"])
        finally:
            query_store.close()
    assert {row["id"] for row in hits}.issubset(expected_ids)


def test_adversarial_missing_physical_id_refuses(ref_v2_env):
    env = ref_v2_env
    with FileGenerationStore(env["chroma"], active_generations=dict) as store:
        result = _retain_v2(
            cfg=env["cfg"],
            store=store,
            generation_root=env["generations"],
            owner_digest_value=env["owner_digest"],
            ratification_id=env["ratification_id"],
        )
        reference = load_manifest_reference(
            env["generations"],
            manifest_filename=result.manifest_filename,
            expected_sha256=result.manifest_sha256,
        )
        descriptor = build_descriptor_from_manifest(reference.manifest)
        chroma = ChromaStore(str(env["chroma"]))
        try:
            col = chroma._collection(UNITS)
            first_id = list(dict(descriptor.collections[UNITS]).get("physical_ids") or [])[0]
            col.delete(ids=[first_id])
            with pytest.raises((RetainedReferenceError, RollbackBaselineError, RuntimeError)):
                cold_validate_reference_v2(env["chroma"], reference.manifest, descriptor=descriptor)
        finally:
            chroma.close()


def test_adversarial_substituted_physical_id_refuses(ref_v2_env):
    env = ref_v2_env
    with FileGenerationStore(env["chroma"], active_generations=dict) as store:
        result = _retain_v2(
            cfg=env["cfg"],
            store=store,
            generation_root=env["generations"],
            owner_digest_value=env["owner_digest"],
            ratification_id=env["ratification_id"],
        )
        reference = load_manifest_reference(
            env["generations"],
            manifest_filename=result.manifest_filename,
            expected_sha256=result.manifest_sha256,
        )
        descriptor = build_descriptor_from_manifest(reference.manifest)
        d0_bindings = dict(reference.manifest.get("d0_bindings") or {})
        d0_roots = {
            "snapshot": str(d0_bindings["accepted_legacy_snapshot_root"]),
            "vector": str(d0_bindings["accepted_legacy_vector_root"]),
        }
        with FileGenerationStore(env["chroma"], active_generations=dict) as read_store:
            rows = read_retained_reference_rows(
                read_store,
                descriptor,
                include_embeddings=True,
            )
        tampered = dict(rows[0])
        tampered["document"] = "tampered document body"
        with pytest.raises(RetainedReferenceError):
            qualify_retained_reference_membership([tampered], descriptor, d0_roots)


def test_recovery_eligibility_binds_rows(ref_v2_env):
    env = ref_v2_env
    with FileGenerationStore(env["chroma"], active_generations=dict) as store:
        result = _retain_v2(
            cfg=env["cfg"],
            store=store,
            generation_root=env["generations"],
            owner_digest_value=env["owner_digest"],
            ratification_id=env["ratification_id"],
        )
        reference = load_manifest_reference(
            env["generations"],
            manifest_filename=result.manifest_filename,
            expected_sha256=result.manifest_sha256,
        )
    recovery = validate_reference_v2_recovery_eligibility(
        env["cfg"],
        generation_root=env["generations"],
        manifest=reference.manifest,
        evidence=result.evidence,
        chroma_dir=env["chroma"],
    )
    assert recovery["eligible"] is True
    assert recovery["referenced_physical_row_count"] > 0


def test_malformed_embedding_raises_d0_attestation_error():
    with pytest.raises(D0AttestationError):
        vector_encoding_sha256([{"not": "a float"}])


def _next_float32_up(value: float) -> float:
    bits = struct.unpack(">I", struct.pack(">f", float(value)))[0]
    return struct.unpack(">f", struct.pack(">I", bits + 1))[0]


def test_adversarial_one_ulp_vector_drift_refuses(ref_v2_env):
    """D1R4: one-ULP embedding mutation must refuse exact readback."""
    env = ref_v2_env
    with FileGenerationStore(env["chroma"], active_generations=dict) as store:
        result = _retain_v2(
            cfg=env["cfg"],
            store=store,
            generation_root=env["generations"],
            owner_digest_value=env["owner_digest"],
            ratification_id=env["ratification_id"],
        )
        reference = load_manifest_reference(
            env["generations"],
            manifest_filename=result.manifest_filename,
            expected_sha256=result.manifest_sha256,
        )
        descriptor = build_descriptor_from_manifest(reference.manifest)
        d0_bindings = dict(reference.manifest.get("d0_bindings") or {})
        d0_roots = {
            "snapshot": str(d0_bindings["accepted_legacy_snapshot_root"]),
            "vector": str(d0_bindings["accepted_legacy_vector_root"]),
        }
        with FileGenerationStore(env["chroma"], active_generations=dict) as read_store:
            rows = read_retained_reference_rows(
                read_store,
                descriptor,
                include_embeddings=True,
            )
    tampered = dict(rows[0])
    embedding = list(tampered["embedding"])
    embedding[0] = _next_float32_up(embedding[0])
    tampered["embedding"] = embedding
    with pytest.raises(RetainedReferenceError, match="exact|non_equivalent|readback"):
        qualify_retained_reference_membership([tampered] + list(rows[1:]), descriptor, d0_roots)


def test_reference_v2_fresh_process_failure_refuses_retained_evidence(ref_v2_env):
    """D1R7: subprocess cold qualification failure must refuse retention."""
    env = ref_v2_env
    with FileGenerationStore(env["chroma"], active_generations=dict) as store:
        with patch(
            "file_generation_validate.run_reference_v2_cold_validation",
            side_effect=RuntimeError("fresh-process refused"),
        ):
            with pytest.raises(RollbackBaselineError, match="fresh-process"):
                _retain_v2(
                    cfg=env["cfg"],
                    store=store,
                    generation_root=env["generations"],
                    owner_digest_value=env["owner_digest"],
                    ratification_id=env["ratification_id"],
                )
    assert not list(env["generations"].rglob("rollback_baselines/*.json"))


def test_retention_lifecycle_uses_retained_rollback_baseline_only(ref_v2_env):
    """D1R8: evidence state is RETAINED_ROLLBACK_BASELINE, not convert literals."""
    env = ref_v2_env
    with FileGenerationStore(env["chroma"], active_generations=dict) as store:
        result = _retain_v2(
            cfg=env["cfg"],
            store=store,
            generation_root=env["generations"],
            owner_digest_value=env["owner_digest"],
            ratification_id=env["ratification_id"],
        )
    evidence = validate_retained_rollback_baseline_evidence_v2(
        env["generations"],
        owner_digest_value=env["owner_digest"],
        generation_id=result.generation_id,
        expected_manifest_sha256=result.manifest_sha256,
    )
    assert evidence["state"] == "RETAINED_ROLLBACK_BASELINE"
    assert "G_RB_CONVERT_COLD_VALIDATED" not in str(evidence)
    assert "abandoned_d1" not in str(evidence)


BACKEND_FINGERPRINT = "rust-bindings/cg2-d1r5-test"

_REFERENCE_V2_INVENTORY_FORBIDDEN = (
    ".f32le",
    "vector_sidecar",
    "sidecar_path",
    "re-embed",
    "reconstruct",
    "stage_rows(",
    "ollama_embed",
    "col.upsert",
    "col.add",
)


def _retain_and_load(env: dict):
    with FileGenerationStore(env["chroma"], active_generations=dict) as store:
        result = _retain_v2(
            cfg=env["cfg"],
            store=store,
            generation_root=env["generations"],
            owner_digest_value=env["owner_digest"],
            ratification_id=env["ratification_id"],
        )
    reference = load_manifest_reference(
        env["generations"],
        manifest_filename=result.manifest_filename,
        expected_sha256=result.manifest_sha256,
    )
    descriptor = build_descriptor_from_manifest(reference.manifest)
    d0_bindings = dict(reference.manifest.get("d0_bindings") or {})
    d0_roots = {
        "snapshot": str(d0_bindings["accepted_legacy_snapshot_root"]),
        "vector": str(d0_bindings["accepted_legacy_vector_root"]),
    }
    return result, reference, descriptor, d0_roots


def _descriptor_with_duplicate_physical_id(
    descriptor: RetainedReferenceTargetDescriptor,
) -> RetainedReferenceTargetDescriptor:
    collections = copy.deepcopy(dict(descriptor.collections))
    if UNITS in collections:
        target_name = UNITS
    else:
        target_name = next(iter(collections))
    spec = dict(collections[target_name])
    physical_ids = list(spec.get("physical_ids") or [])
    if not physical_ids:
        raise AssertionError("reference-v2 fixture lacks physical ids for duplicate oracle")
    spec["physical_ids"] = physical_ids + [physical_ids[0]]
    collections[target_name] = spec
    return replace(descriptor, collections=collections)


def _build_hermetic_canary(env: dict, *, retained: dict[str, set[str]]):
    source = env["source"]
    raw = source.read_bytes()
    candidate = build_candidate_generation(
        source_path=str(source),
        source_bytes=raw,
        parse=lambda _raw: [{"start_offset": 0, "end_offset": max(len(raw), 1)}],
        extract_chunk=lambda _chunk: (
            "canary summary",
            [{"document": "canary unit body", "metadata": {"title": "Canary"}}],
        ),
        embed=lambda _text: [0.01, 0.02],
        committed_store=EmptyCommittedView(),
        dedupe_cfg={"ingest_dedup": {"candidate_k": 10}},
        pipeline_fingerprint={
            "parser": "cg2-canary-parser-v1",
            "chunk": "cg2-canary-chunk-v1",
            "model": EMBED_MODEL,
            "prompt": "cg2-canary-prompt-v1",
        },
        embedding_model=EMBED_MODEL,
    )
    staged = [
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
    with FileGenerationStore(
        env["chroma"],
        active_generations=dict,
        retained_baselines=lambda: {k: set(v) for k, v in retained.items()},
    ) as store:
        store.stage_rows(staged)
        collections = {
            name: store.build_manifest_collection_spec(
                name,
                owner_digest=candidate.owner_digest,
                generation_id=candidate.generation_id,
                embedding_model=EMBED_MODEL,
                embedding_dimension=EMBED_DIM,
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
        recorded_only_annotations={"proof_profile": KNOWN_MODEL_AND_VECTOR_V1},
    )
    return candidate, publish_manifest(env["generations"], manifest)


def test_adversarial_duplicate_physical_id_refuses(ref_v2_env):
    """D1R3: duplicate physical ID in selector refuses via retained reader."""
    env = ref_v2_env
    _result, _reference, descriptor, _d0_roots = _retain_and_load(env)
    tampered = _descriptor_with_duplicate_physical_id(descriptor)
    with FileGenerationStore(env["chroma"], active_generations=dict) as store:
        with pytest.raises(
            (RetainedReferenceError, DuplicateIDError),
            match="duplicate referenced physical ids|unique",
        ):
            read_retained_reference_rows(store, tampered, include_embeddings=True)


def test_adversarial_additional_physical_id_refuses(ref_v2_env, monkeypatch):
    """D1R3: additional physical ID refuses via reference-v2 cold qualification."""
    env = ref_v2_env
    _result, reference, descriptor, _d0_roots = _retain_and_load(env)
    original = read_retained_reference_rows

    def _append_extra_row(store, desc, **kwargs):
        rows = original(store, desc, **kwargs)
        extra = dict(rows[0])
        extra["physical_id"] = "additional-physical-id"
        extra["id"] = "additional-physical-id"
        return rows + [extra]

    monkeypatch.setattr(
        "file_generation_validate.read_retained_reference_rows",
        _append_extra_row,
    )
    with pytest.raises(RetainedReferenceError, match="unexpected|membership mismatch"):
        cold_validate_reference_v2(env["chroma"], reference.manifest, descriptor=descriptor)


def test_adversarial_wrong_owner_physical_id_refuses(ref_v2_env, monkeypatch):
    """D1R3: wrong-owner physical ID refuses via reference-v2 cold qualification."""
    env = ref_v2_env
    _result, reference, descriptor, _d0_roots = _retain_and_load(env)
    original = read_retained_reference_rows

    def _inject_wrong_owner(store, desc, **kwargs):
        rows = original(store, desc, **kwargs)
        tampered = dict(rows[0])
        meta = dict(tampered.get("metadata") or {})
        meta["owner_digest"] = "0" * 64
        tampered["metadata"] = meta
        return [tampered] + list(rows[1:])

    monkeypatch.setattr(
        "file_generation_validate.read_retained_reference_rows",
        _inject_wrong_owner,
    )
    with pytest.raises(RetainedReferenceError, match="wrong-owner physical ids"):
        cold_validate_reference_v2(env["chroma"], reference.manifest, descriptor=descriptor)


def test_reference_v2_first_cutover_rollback_same_reader_rehearsal(
    ref_v2_env, monkeypatch
):
    """D1R5: qualification, cutover rebind, and rollback scoring share one reader."""
    env = ref_v2_env
    _mock_ollama_only(monkeypatch)
    grb_result, reference, descriptor, _d0_roots = _retain_and_load(env)
    selector_fingerprint = serving_selector_fingerprint(descriptor)

    READER_CALL_LOG.clear()
    cold = cold_validate_reference_v2(
        env["chroma"], reference.manifest, descriptor=descriptor
    )
    qualification_log = list(READER_CALL_LOG)
    assert cold["valid"] is True
    assert qualification_log

    retained = {env["owner_digest"]: {grb_result.generation_id}}
    canary_candidate, canary_ref = _build_hermetic_canary(env, retained=retained)

    READER_CALL_LOG.clear()
    active = publish_first_cutover_active_pointer(
        env["generations"],
        canary_ref,
        rollback_baseline_generation_id=grb_result.generation_id,
        chroma_dir=env["chroma"],
        cfg=env["cfg"],
        backend_fingerprint=BACKEND_FINGERPRINT,
    )
    rebind = cold_validate_reference_v2(
        env["chroma"], reference.manifest, descriptor=descriptor
    )
    rebind_log = list(READER_CALL_LOG)
    assert rebind["valid"] is True
    assert active.pointer["previous_generation_id"] == grb_result.generation_id
    assert active.pointer["active_generation_id"] == canary_candidate.generation_id

    publish_legacy_fence(
        env["generations"],
        str(reference.manifest["owner_key"]),
        published_at="2026-08-30T00:00:00Z",
    )

    evidence_sha = hashlib.sha256(grb_result.evidence_path.read_bytes()).hexdigest()
    rolled = rollback_active_pointer(
        env["generations"],
        reference,
        chroma_dir=env["chroma"],
        cfg=env["cfg"],
        expected_active_generation_id=active.pointer["active_generation_id"],
        backend_fingerprint=BACKEND_FINGERPRINT,
        grb_ratification_id=env["ratification_id"],
        grb_evidence_sha256=evidence_sha,
    )
    assert rolled.pointer["active_generation_id"] == grb_result.generation_id

    get_rows_calls: list[tuple] = []
    original_get_rows = FileGenerationStore._get_rows

    def _spy_get_rows(self, *args, **kwargs):
        get_rows_calls.append((args, kwargs))
        return original_get_rows(self, *args, **kwargs)

    READER_CALL_LOG.clear()
    with patch.object(FileGenerationStore, "_get_rows", _spy_get_rows):
        query_store = FileGenerationStore(
            env["chroma"],
            active_generations=lambda: {env["owner_digest"]: grb_result.generation_id},
            reference_v2_descriptors=lambda: {env["owner_digest"]: descriptor},
        )
        try:
            hits = query_store.query_units(
                [1.0, 0.0], top_k=3, owner_digest=env["owner_digest"]
            )
        finally:
            query_store.close()
    scoring_log = list(READER_CALL_LOG)

    assert hits
    assert not get_rows_calls
    assert qualification_log
    assert rebind_log
    assert scoring_log
    for entry in qualification_log + rebind_log + scoring_log:
        assert entry["selector_fingerprint"] == selector_fingerprint
        assert entry["generation_id"] == grb_result.generation_id
        assert entry["owner_digest"] == env["owner_digest"]
    assert {row["id"] for row in hits}.issubset(
        {
            physical_id
            for spec in descriptor.collections.values()
            for physical_id in list(dict(spec).get("physical_ids") or [])
        }
    )


def test_reference_v2_static_inventory_no_sidecar_or_copied_vector_authority():
    """D1R6: reference-v2 path modules forbid sidecar/copied-vector authority."""
    import cg2_retained_reference as retained_reference
    import cg2_rollback_baseline as rollback_baseline
    import file_generation_validate as generation_validate

    assert "vector_sidecar" in _REFERENCE_V2_FORBIDDEN_MANIFEST_KEYS
    assert "sidecar_path" in _REFERENCE_V2_FORBIDDEN_MANIFEST_KEYS
    assert ".f32le" not in _REFERENCE_V2_FORBIDDEN_MANIFEST_KEYS

    inventoried_sources = "\n".join(
        inspect.getsource(function)
        for function in (
            retained_reference.read_retained_reference_rows,
            retained_reference.qualify_retained_reference_membership,
            generation_validate.cold_validate_reference_v2,
            rollback_baseline.retain_reference_v2_rollback_baseline,
        )
    )
    lowered = inventoried_sources.lower()
    for token in _REFERENCE_V2_INVENTORY_FORBIDDEN:
        assert token.lower() not in lowered, f"forbidden reference-v2 authority: {token}"


def test_reference_v2_lookup_spy_no_sidecar_or_generation_get_rows(ref_v2_env, monkeypatch):
    """D1R6: reference-v2 qualification/serving never uses generation lookup paths."""
    env = ref_v2_env
    _result, reference, descriptor, _d0_roots = _retain_and_load(env)

    get_rows_calls: list[tuple] = []
    sidecar_calls: list[tuple] = []
    original_get_rows = FileGenerationStore._get_rows

    def _spy_get_rows(self, *args, **kwargs):
        get_rows_calls.append((args, kwargs))
        return original_get_rows(self, *args, **kwargs)

    def _forbidden_sidecar_lookup(*_args, **_kwargs):
        sidecar_calls.append((_args, _kwargs))
        raise AssertionError("reference-v2 path must not consult sidecar lookup")

    monkeypatch.setattr(FileGenerationStore, "_get_rows", _spy_get_rows)
    monkeypatch.setattr(
        "cg2_legacy_vector_attestation.ollama_embed",
        _forbidden_sidecar_lookup,
    )

    cold_validate_reference_v2(env["chroma"], reference.manifest, descriptor=descriptor)
    query_store = FileGenerationStore(
        env["chroma"],
        active_generations=lambda: {env["owner_digest"]: _result.generation_id},
        reference_v2_descriptors=lambda: {env["owner_digest"]: descriptor},
    )
    try:
        query_store.query_units([1.0, 0.0], top_k=3, owner_digest=env["owner_digest"])
    finally:
        query_store.close()

    assert not get_rows_calls
    assert not sidecar_calls

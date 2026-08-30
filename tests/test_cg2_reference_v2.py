"""D1 reference-v2 retained rollback baseline oracles."""

# pylint: disable=duplicate-code,protected-access

from __future__ import annotations

import pytest

from cg2_legacy_vector_attestation import (
    D0AttestationError,
    LEGACY_EXACT_VECTOR_UNKNOWN_MODEL_V1,
    vector_encoding_sha256,
)
from cg2_retained_reference import (
    READER_CALL_LOG,
    RetainedReferenceError,
    build_descriptor_from_manifest,
    qualify_retained_reference_membership,
    read_retained_reference_rows,
)
from cg2_rollback_baseline import (
    CONVERT_V1_FINGERPRINT,
    REFERENCE_V2_FINGERPRINT,
    RollbackBaselineError,
    retain_reference_v2_rollback_baseline,
    validate_retained_rollback_baseline_evidence_v2,
)
from chroma_store import UNITS, ChromaStore
from complete_data_restore import validate_reference_v2_recovery_eligibility
from file_generation_contract import (
    FAILED_CONVERT_V1_TARGET_ID,
    canonical_hash,
    canonical_source_path,
    is_failed_convert_v1_target_id,
    make_generation_id,
    refuse_failed_convert_v1_target_id,
)
from file_generation_pointer import load_manifest_reference
from file_generation_store import FileGenerationStore
from file_generation_validate import cold_validate_reference_v2

from tests.test_cg2_rollback_baseline import (
    _mock_d0_runtime,
    _mock_hermetic_production_paths,
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


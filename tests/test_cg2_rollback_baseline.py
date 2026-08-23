"""D1 — exact G_rb conversion from ratified D0 chain (hermetic adversarial matrix)."""

# pylint: disable=too-many-lines,duplicate-code,protected-access

from __future__ import annotations

import hashlib
import inspect
import json
from pathlib import Path
from unittest.mock import patch

import pytest

from cg2_legacy_vector_attestation import (
    CG2_D0_RATIFICATION_V1,
    D0AttestationError,
    LEGACY_EXACT_VECTOR_UNKNOWN_MODEL_V1,
    capture_d0_legacy_vector_candidate,
    load_ratified_d0_chain,
    validate_d0_legacy_vector_candidate,
    verify_d0_chain_for_grb_conversion,
    _publish_immutable,
    ratification_path,
)
from cg2_rollback_baseline import (
    CONVERT_V1_FINGERPRINT,
    LegacyServingSnapshot,
    RollbackBaselineError,
    convert_and_retain_rollback_baseline,
    rollback_baseline_evidence_path,
    validate_retained_rollback_baseline_evidence,

    D0_PHYSICAL_ID_KEY,
    _d1_generation_logical_key,
)
from chroma_store import SUMMARIES, UNITS, ChromaStore
from file_generation_contract import (
    canonical_bytes,
    canonical_hash,
    canonical_source_path,
    make_generation_id,
    ownership_key,
)
from file_generation_pointer import load_manifest_reference, provision_generation_layout
from file_generation_store import FILE_SCOPE, STABLE_SCOPE, FileGenerationStore
from provenance_binding import (
    attach_unit_provenance,
    build_ingest_envelope,
    projection_metadata,
)
from serving_authority import generation_root_for_cfg, publish_legacy_fence

EMBED_MODEL = "nomic-embed-text"
EMBED_DIM = 2


def _cfg(*, chroma: Path, generations: Path, processed: Path) -> dict:
    return {
        "models": {"embed_model": EMBED_MODEL, "ollama_host": "http://127.0.0.1:9"},
        "index": {
            "chroma_dir": str(chroma),
            "generation_root": str(generations),
            "processed_log": str(processed),
        },
    }


def _mock_ollama_only(monkeypatch) -> None:
    class _Resp:
        def __init__(self, url: str) -> None:
            self.url = url

        def raise_for_status(self) -> None:
            return None

        def json(self):
            if self.url.endswith("/api/tags"):
                return {
                    "models": [
                        {
                            "name": EMBED_MODEL,
                            "digest": "sha256:" + ("a" * 64),
                            "details": {"quantization_level": "Q4_0"},
                        }
                    ]
                }
            if self.url.endswith("/api/version"):
                return {"version": "0.11.4"}
            raise AssertionError(self.url)

    monkeypatch.setattr(
        "cg2_legacy_vector_attestation.ollama_embed",
        lambda text, model, host: [0.01, 0.02],
    )
    monkeypatch.setattr(
        "cg2_legacy_vector_attestation.requests.get",
        lambda url, timeout=5: _Resp(url),
    )


def _mock_hermetic_production_paths(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(
        "cg2_legacy_vector_attestation._resolve_live_production_paths",
        lambda: (tmp_path / "live-chroma", tmp_path / "live-generations"),
    )
    monkeypatch.setattr(
        "cg2_rollback_baseline._resolve_live_production_paths",
        lambda: (tmp_path / "live-chroma", tmp_path / "live-generations"),
    )


def _mock_d0_runtime(monkeypatch, tmp_path: Path) -> None:
    _mock_hermetic_production_paths(monkeypatch, tmp_path)
    _mock_ollama_only(monkeypatch)


def _provenance_meta(
    *,
    unit_id: str,
    source_path: str,
    document: str,
    ledger_id: str,
    source_identity: str,
) -> dict:
    envelope = build_ingest_envelope(
        records=[{"source": source_identity, "content": document}],
        consumed_views=[document],
        source_identity=source_identity,
        locator_prefix=f"fixture:{source_identity}",
        source_type="inter_model_doc",
        transformer_class="packaging",
        transformer_identity="cg2-d1-fixture",
        transformer_version="d1-v1",
        derivation_kind="packaging",
        producer_class="external",
        producer_assurance="claimed",
        selection_parameters={"source": source_identity, "unit": unit_id},
        provider_payload={"content": document, "unit": unit_id},
        recipe_id="cg2-d1-fixture-v1",
        recipe_spec={"kind": "cg2-d1-fixture"},
        output_locator=f"{source_identity}#{unit_id}",
        output_value={"summary": document},
    )
    unit = attach_unit_provenance(
        {
            "id": unit_id,
            "title": "CG2 D1 fixture",
            "summary": document,
            "source_path": source_path,
        },
        envelope,
    )
    return {
        "id": unit_id,
        "title": "CG2 D1 fixture",
        "source_path": source_path,
        "ledger_id": ledger_id,
        "logical_id": unit_id,
        "content_hash": canonical_hash(document),
        "start_offset": 0,
        **projection_metadata(unit),
    }


def _seed_legacy_corpus(
    chroma: Path,
    source: Path,
    *,
    with_provenance_twins: bool = True,
    with_invalid_provenance: bool = True,
    with_superseded: bool = True,
    with_stable: bool = True,
    with_summary: bool = True,
    with_other_source: bool = True,
) -> dict[str, object]:
    canonical = canonical_source_path(source)
    store = ChromaStore(str(chroma))
    try:
        docs: dict[str, object] = {"canonical": canonical}
        store.add_unit(
            "legacy-plain",
            "plain legacy unit",
            [1.0, 0.0],
            {
                "id": "legacy-plain",
                "logical_id": "legacy-plain",
                "source_path": canonical,
                "ledger_id": "obs_plain",
                "content_hash": canonical_hash("plain legacy unit"),
                "start_offset": 0,
            },
        )
        docs["plain_id"] = "legacy-plain"

        if with_provenance_twins:
            meta_a = _provenance_meta(
                unit_id="legacy-twin-a",
                source_path=canonical,
                document="shared ledger twin body",
                ledger_id="obs_shared_twin",
                source_identity=f"{canonical}#a",
            )
            meta_b = _provenance_meta(
                unit_id="legacy-twin-b",
                source_path=canonical,
                document="shared ledger twin body",
                ledger_id="obs_shared_twin",
                source_identity=f"{canonical}#b",
            )
            assert meta_a["assertion_id"] != meta_b["assertion_id"]
            store.add_unit("legacy-twin-a", "shared ledger twin body", [0.9, 0.1], meta_a)
            store.add_unit("legacy-twin-b", "shared ledger twin body", [0.8, 0.2], meta_b)
            docs["twin_a"] = meta_a
            docs["twin_b"] = meta_b

        if with_invalid_provenance:
            store._collection(UNITS).upsert(
                ids=["legacy-bad-prov"],
                documents=["invalid provenance unit"],
                embeddings=[[0.7, 0.3]],
                metadatas=[
                    {
                        "id": "legacy-bad-prov",
                        "logical_id": "legacy-bad-prov",
                        "source_path": canonical,
                        "ledger_id": "obs_bad_prov",
                        "content_hash": canonical_hash("invalid provenance unit"),
                        "start_offset": 1,
                        "provenance_envelope": "{not-json",
                        "provenance_commitment": "0" * 64,
                        "assertion_id": "not-a-uuid",
                    }
                ],
            )
            docs["bad_prov_id"] = "legacy-bad-prov"

        if with_superseded:
            store.add_unit(
                "legacy-superseded",
                "superseded unit",
                [0.5, 0.5],
                {
                    "id": "legacy-superseded",
                    "logical_id": "legacy-superseded",
                    "source_path": canonical,
                    "ledger_id": "obs_superseded",
                    "content_hash": canonical_hash("superseded unit"),
                    "start_offset": 2,
                    "superseded": True,
                    "superseded_by": "fixture",
                },
            )

        if with_stable:
            store.add_unit(
                "dec_stable_fixture",
                "stable governed",
                [0.4, 0.6],
                {
                    "id": "dec_stable_fixture",
                    "logical_id": "dec_stable_fixture",
                    "ledger_id": "dec_stable_fixture",
                    "generation_scope": STABLE_SCOPE,
                    "source_path": canonical,
                },
            )

        if with_other_source:
            other = canonical_source_path(str(source) + ".other")
            store.add_unit(
                "legacy-other-source",
                "other source unit",
                [0.3, 0.7],
                {
                    "id": "legacy-other-source",
                    "logical_id": "legacy-other-source",
                    "source_path": other,
                    "ledger_id": "obs_other",
                    "content_hash": canonical_hash("other source unit"),
                    "start_offset": 0,
                },
            )

        if with_summary:
            store.add_summary(
                "legacy-summary",
                "legacy summary text",
                [0.2, 0.8],
                {
                    "id": "legacy-summary",
                    "logical_id": "legacy-summary",
                    "source_path": canonical,
                    "start_offset": 0,
                    "content_hash": canonical_hash("legacy summary text"),
                    "distill_status": "done",
                },
            )
            docs["summary_id"] = "legacy-summary"

        return docs
    finally:
        store.close()




def _seed_same_logical_distinct_physical(chroma: Path, source: Path) -> dict[str, object]:
    """Two LEGACY rows sharing conversion logical id with distinct physical ids."""

    canonical = canonical_source_path(source)
    store = ChromaStore(str(chroma))
    try:
        shared_logical = "shared-conversion-logical"
        meta_a = {
            "id": "phys-shared-a",
            "logical_id": shared_logical,
            "source_path": canonical,
            "ledger_id": "obs_shared_logical_a",
            "content_hash": canonical_hash("identical twin body"),
            "start_offset": 10,
        }
        meta_b = {
            "id": "phys-shared-b",
            "logical_id": shared_logical,
            "source_path": canonical,
            "ledger_id": "obs_shared_logical_b",
            "content_hash": canonical_hash("identical twin body"),
            "start_offset": 11,
        }
        store.add_unit("phys-shared-a", "identical twin body", [0.2, 0.8], meta_a)
        store.add_unit("phys-shared-b", "identical twin body", [0.2, 0.8], meta_b)
        return {
            "canonical": canonical,
            "shared_logical": shared_logical,
            "phys_a": "phys-shared-a",
            "phys_b": "phys-shared-b",
            "meta_a": meta_a,
            "meta_b": meta_b,
        }
    finally:
        store.close()


def _seed_same_logical_distinct_provenance(chroma: Path, source: Path) -> dict[str, object]:
    canonical = canonical_source_path(source)
    store = ChromaStore(str(chroma))
    try:
        shared_logical = "shared-conversion-logical-prov"
        meta_a = _provenance_meta(
            unit_id="phys-prov-a",
            source_path=canonical,
            document="shared logical provenance body",
            ledger_id="obs_shared_logical_prov",
            source_identity=f"{canonical}#prov-a",
        )
        meta_b = _provenance_meta(
            unit_id="phys-prov-b",
            source_path=canonical,
            document="shared logical provenance body",
            ledger_id="obs_shared_logical_prov",
            source_identity=f"{canonical}#prov-b",
        )
        meta_a["logical_id"] = shared_logical
        meta_b["logical_id"] = shared_logical
        store.add_unit("phys-prov-a", "shared logical provenance body", [0.55, 0.45], meta_a)
        store.add_unit("phys-prov-b", "shared logical provenance body", [0.45, 0.55], meta_b)
        return {
            "canonical": canonical,
            "shared_logical": shared_logical,
            "meta_a": meta_a,
            "meta_b": meta_b,
        }
    finally:
        store.close()


def _prepare(tmp_path: Path, **seed_kwargs):
    tmp_path.mkdir(parents=True, exist_ok=True)
    source = tmp_path / "accepted-source.jsonl"
    source.write_text("accepted-legacy-bytes-v1", encoding="utf-8")
    accepted_hash = hashlib.sha256(source.read_bytes()).hexdigest()
    chroma = tmp_path / "chroma"
    generations = tmp_path / "generations"
    processed = tmp_path / "processed.json"
    processed.write_text(
        json.dumps(
            {
                accepted_hash: {
                    "path": str(source.resolve()),
                    "indexed_at": "2026-08-21T00:00:00Z",
                }
            }
        ),
        encoding="utf-8",
    )
    seeded = _seed_legacy_corpus(chroma, source, **seed_kwargs)
    cfg = _cfg(chroma=chroma, generations=generations, processed=processed)
    provision_generation_layout(generations)
    return source, accepted_hash, chroma, generations, cfg, seeded


def _ratify_d0_chain(
    cfg,
    source,
    accepted_hash,
    *,
    ratification_id: str = "ryan-d1-fixture-1",
):
    owner_key = ownership_key(canonical_source_path(source))
    candidate = capture_d0_legacy_vector_candidate(
        cfg,
        owner_key=owner_key,
        source_path=source,
        accepted_source_hash=accepted_hash,
    )
    validation = validate_d0_legacy_vector_candidate(
        cfg,
        owner_key=owner_key,
        source_path=source,
        accepted_source_hash=accepted_hash,
        candidate_sha256=candidate.candidate_sha256,
        validator_identity="d1-hermetic-validator",
    )
    cand = json.loads(candidate.path.read_text(encoding="utf-8"))
    record = {
        "schema_version": CG2_D0_RATIFICATION_V1,
        "ratification_id": ratification_id,
        "candidate_artifact_sha256": candidate.candidate_sha256,
        "validation_result_sha256": validation.validation_result_sha256,
        "owner_key": owner_key,
        "owner_digest": candidate.owner_digest,
        "accepted_legacy_snapshot_root": cand["accepted_legacy_snapshot_root"],
        "accepted_legacy_vector_root": cand["accepted_legacy_vector_root"],
        "producer_repository_sha": cand["producer_repository_sha"],
        "capture_identity": cand["capture_module_identity"],
        "capture_time": cand["capture_start_time"],
        "query_embedding_context_sha256": cand["query_embedding_context_sha256"],
    }
    generation_root = generation_root_for_cfg(cfg)
    _publish_immutable(
        ratification_path(generation_root, candidate.owner_digest, ratification_id),
        canonical_bytes(record),
    )
    return candidate.owner_digest, ratification_id, cand, candidate, validation


def _convert_grb(*, cfg, store, generation_root, owner_digest_value, ratification_id):
    return convert_and_retain_rollback_baseline(
        cfg=cfg,
        store=store,
        generation_root=generation_root,
        owner_digest_value=owner_digest_value,
        ratification_id=ratification_id,
    )


def _rehash_evidence(payload: dict) -> dict:
    out = {key: value for key, value in payload.items() if key != "evidence_payload_hash"}
    out["evidence_payload_hash"] = canonical_hash(out)
    return out


def _fake_live_cfg(tmp_path: Path) -> dict:
    live_chroma = tmp_path / "configured-live-chroma"
    live_gens = tmp_path / "configured-live-generations"
    live_chroma.mkdir(parents=True, exist_ok=True)
    live_gens.mkdir(parents=True, exist_ok=True)
    return {
        "index": {
            "chroma_dir": str(live_chroma),
            "generation_root": str(live_gens),
        }
    }


@pytest.fixture(name="d1_env")
def _d1_env_fixture(tmp_path, monkeypatch):
    _mock_hermetic_production_paths(monkeypatch, tmp_path)
    _mock_ollama_only(monkeypatch)
    source, accepted_hash, chroma, generations, cfg, seeded = _prepare(tmp_path)
    owner_digest_value, ratification_id, candidate_body, _cand_ref, _val = _ratify_d0_chain(
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


# --- Happy path / bidirectional equivalence ---


def test_frozen_legacy_set_is_bidirectionally_equivalent_to_grb(d1_env):
    retained: dict[str, set[str]] = {}
    with FileGenerationStore(
        d1_env["chroma"],
        active_generations=dict,
        retained_baselines=lambda: {k: set(v) for k, v in retained.items()},
    ) as store:
        result = _convert_grb(
            cfg=d1_env["cfg"],
            store=store,
            generation_root=d1_env["generations"],
            owner_digest_value=d1_env["owner_digest"],
            ratification_id=d1_env["ratification_id"],
        )
        retained.setdefault(d1_env["owner_digest"], set()).add(result.generation_id)
    validate_retained_rollback_baseline_evidence(
        d1_env["generations"],
        owner_digest_value=d1_env["owner_digest"],
        generation_id=result.generation_id,
        expected_manifest_sha256=result.manifest_sha256,
    )
    twin_a = d1_env["seeded"]["twin_a"]
    twin_b = d1_env["seeded"]["twin_b"]
    identities = {
        (row["assertion_id"], row["provenance_commitment"])
        for row in result.evidence.get("provenance_identity_evidence") or []
    }
    assert (twin_a["assertion_id"], twin_a["provenance_commitment"]) in identities
    assert (twin_b["assertion_id"], twin_b["provenance_commitment"]) in identities


def test_literal_convert_v1_fingerprint_and_deterministic_generation_id(d1_env):
    assert CONVERT_V1_FINGERPRINT == "convmem/cg2-rollback-baseline-convert-v1"
    with FileGenerationStore(d1_env["chroma"], active_generations=dict) as store:
        result = _convert_grb(
            cfg=d1_env["cfg"],
            store=store,
            generation_root=d1_env["generations"],
            owner_digest_value=d1_env["owner_digest"],
            ratification_id=d1_env["ratification_id"],
        )
    expected = make_generation_id(
        owner_digest=d1_env["owner_digest"],
        source_hash=d1_env["accepted_hash"],
        pipeline_fingerprint=CONVERT_V1_FINGERPRINT,
        candidate_bundle_hash=result.snapshot.candidate_bundle_hash,
    )
    assert result.generation_id == expected
    assert result.convert_fingerprint == CONVERT_V1_FINGERPRINT


# --- A1: no caller snapshot trust ---


def test_a1_convert_rejects_caller_snapshot_kwargs():
    params = inspect.signature(convert_and_retain_rollback_baseline).parameters
    assert "snapshot" not in params
    assert "embedding_provenance" not in params


def test_a1_persisted_chroma_mutation_after_ratification_refuses(d1_env):
    with FileGenerationStore(d1_env["chroma"], active_generations=dict) as store:
        store.raw_store.add_unit(
            "legacy-new-row",
            "new row after ratification",
            [0.1, 0.9],
            {
                "id": "legacy-new-row",
                "logical_id": "legacy-new-row",
                "source_path": canonical_source_path(d1_env["source"]),
                "ledger_id": "obs_new",
                "content_hash": canonical_hash("new row after ratification"),
                "start_offset": 3,
            },
        )
        with pytest.raises(RollbackBaselineError, match="root|churn|equivalent"):
            _convert_grb(
                cfg=d1_env["cfg"],
                store=store,
                generation_root=d1_env["generations"],
                owner_digest_value=d1_env["owner_digest"],
                ratification_id=d1_env["ratification_id"],
            )


def test_a1_in_memory_snapshot_cannot_authorize_convert(d1_env):
    forged = LegacyServingSnapshot(
        owner_key=ownership_key(d1_env["source"]),
        owner_digest=d1_env["owner_digest"],
        canonical_source_path=canonical_source_path(d1_env["source"]),
        accepted_source_hash=d1_env["accepted_hash"],
        rows=(),
        snapshot_digest="f" * 64,
        candidate_bundle_hash="e" * 64,
    )
    with FileGenerationStore(d1_env["chroma"], active_generations=dict) as store:
        call_kwargs = {
            "cfg": d1_env["cfg"],
            "store": store,
            "generation_root": d1_env["generations"],
            "owner_digest_value": d1_env["owner_digest"],
            "ratification_id": d1_env["ratification_id"],
        }
        call_kwargs["".join(("snap", "shot"))] = forged
        with pytest.raises(TypeError):
            convert_and_retain_rollback_baseline(**call_kwargs)


# --- A2: fresh-process qualification ---


def test_a2_fresh_process_failure_refuses_retained_evidence(d1_env):
    with FileGenerationStore(d1_env["chroma"], active_generations=dict) as store:
        with patch(
            "cg2_rollback_baseline.run_cold_validation",
            side_effect=RuntimeError("fresh-process refused"),
        ):
            with pytest.raises(RollbackBaselineError, match="fresh-process"):
                _convert_grb(
                    cfg=d1_env["cfg"],
                    store=store,
                    generation_root=d1_env["generations"],
                    owner_digest_value=d1_env["owner_digest"],
                    ratification_id=d1_env["ratification_id"],
                )
    assert not list(d1_env["generations"].rglob("rollback_baselines/*.json"))


def test_a2_in_process_cold_without_sequence_positions_refuses_validation(d1_env):
    with FileGenerationStore(d1_env["chroma"], active_generations=dict) as store:
        result = _convert_grb(
            cfg=d1_env["cfg"],
            store=store,
            generation_root=d1_env["generations"],
            owner_digest_value=d1_env["owner_digest"],
            ratification_id=d1_env["ratification_id"],
        )
    path = rollback_baseline_evidence_path(
        d1_env["generations"], d1_env["owner_digest"], result.generation_id
    )
    payload = json.loads(path.read_text(encoding="utf-8"))
    cold = dict(payload["cold_qualification"])
    cold.pop("sequence_positions", None)
    payload["cold_qualification"] = cold
    path.write_text(json.dumps(_rehash_evidence(payload), indent=2, sort_keys=True) + "\n")
    with pytest.raises(RollbackBaselineError, match="sequence_positions|cold-qualification"):
        validate_retained_rollback_baseline_evidence(
            d1_env["generations"],
            owner_digest_value=d1_env["owner_digest"],
            generation_id=result.generation_id,
            expected_manifest_sha256=result.manifest_sha256,
        )


def test_a2_cold_qualification_missing_bindings_refuse(d1_env):
    with FileGenerationStore(d1_env["chroma"], active_generations=dict) as store:
        result = _convert_grb(
            cfg=d1_env["cfg"],
            store=store,
            generation_root=d1_env["generations"],
            owner_digest_value=d1_env["owner_digest"],
            ratification_id=d1_env["ratification_id"],
        )
    path = rollback_baseline_evidence_path(
        d1_env["generations"], d1_env["owner_digest"], result.generation_id
    )
    original = json.loads(path.read_text(encoding="utf-8"))
    for field in (
        "valid",
        "generation_id",
        "owner_digest",
        "manifest_sha256",
        "identity",
        "sequence_positions",
    ):
        payload = json.loads(json.dumps(original))
        cold = dict(payload["cold_qualification"])
        cold.pop(field, None)
        payload["cold_qualification"] = cold
        path.write_text(json.dumps(_rehash_evidence(payload), indent=2, sort_keys=True) + "\n")
        with pytest.raises(RollbackBaselineError, match="cold-qualification|cold qualification"):
            validate_retained_rollback_baseline_evidence(
                d1_env["generations"],
                owner_digest_value=d1_env["owner_digest"],
                generation_id=result.generation_id,
                expected_manifest_sha256=result.manifest_sha256,
            )


def test_a2_byte_distinct_cold_not_idempotent(d1_env):
    with FileGenerationStore(d1_env["chroma"], active_generations=dict) as store:
        result = _convert_grb(
            cfg=d1_env["cfg"],
            store=store,
            generation_root=d1_env["generations"],
            owner_digest_value=d1_env["owner_digest"],
            ratification_id=d1_env["ratification_id"],
        )
    path = rollback_baseline_evidence_path(
        d1_env["generations"], d1_env["owner_digest"], result.generation_id
    )
    payload = json.loads(path.read_text(encoding="utf-8"))
    cold = dict(payload["cold_qualification"])
    cold["sequence_positions"] = {"knowledge_units": 999, "conversation_summaries": 999}
    cold["manifest_sha256"] = "f" * 64
    payload["cold_qualification"] = cold
    path.write_text(json.dumps(_rehash_evidence(payload), indent=2, sort_keys=True) + chr(10))
    with pytest.raises(RollbackBaselineError, match="cold-qualification|manifest SHA"):
        validate_retained_rollback_baseline_evidence(
            d1_env["generations"],
            owner_digest_value=d1_env["owner_digest"],
            generation_id=result.generation_id,
            expected_manifest_sha256=result.manifest_sha256,
        )



# --- B1/B3: no historical model invention ---


def test_b1_manifest_unknown_model_profile(d1_env):
    with FileGenerationStore(d1_env["chroma"], active_generations=dict) as store:
        result = _convert_grb(
            cfg=d1_env["cfg"],
            store=store,
            generation_root=d1_env["generations"],
            owner_digest_value=d1_env["owner_digest"],
            ratification_id=d1_env["ratification_id"],
        )
    assert result.evidence["proof_profile"] == LEGACY_EXACT_VECTOR_UNKNOWN_MODEL_V1
    for name in (UNITS, SUMMARIES):
        prov = result.evidence["embedding_provenance"].get(name)
        if prov is None:
            continue
        assert prov["embedding_model"] == "UNKNOWN"
        assert prov["historical_embedding_model"] == {
            "status": "UNKNOWN",
            "identifier": None,
        }
        assert prov["proof_profile"] == LEGACY_EXACT_VECTOR_UNKNOWN_MODEL_V1
    reference = load_manifest_reference(
        d1_env["generations"],
        manifest_filename=result.manifest_filename,
        expected_sha256=result.manifest_sha256,
    )
    for _name, spec in dict(reference.manifest.get("collections") or {}).items():
        assert str(spec.get("embedding_model")) == "UNKNOWN"


def test_b3_configured_embed_model_is_not_historical_authority(d1_env):
    with FileGenerationStore(d1_env["chroma"], active_generations=dict) as store:
        result = _convert_grb(
            cfg=d1_env["cfg"],
            store=store,
            generation_root=d1_env["generations"],
            owner_digest_value=d1_env["owner_digest"],
            ratification_id=d1_env["ratification_id"],
        )
    for name in (UNITS, SUMMARIES):
        prov = result.evidence["embedding_provenance"].get(name)
        if prov is None:
            continue
        assert prov["embedding_model"] != EMBED_MODEL
        assert prov.get("provenance_evidence_digest") != canonical_hash(
            {
                "collection_uuid": prov["collection_uuid"],
                "configuration": prov["configuration"],
                "embedding_model": EMBED_MODEL,
                "embedding_dimension": prov["embedding_dimension"],
            }
        )


def test_b3_query_context_mismatch_refuses(tmp_path, monkeypatch):
    _mock_d0_runtime(monkeypatch, tmp_path)
    source, accepted_hash, chroma, generations, cfg, _seeded = _prepare(tmp_path)
    owner_digest_value, ratification_id, _body, _cand, _val = _ratify_d0_chain(
        cfg, source, accepted_hash
    )

    class _Resp:
        def __init__(self, url: str) -> None:
            self.url = url

        def raise_for_status(self) -> None:
            return None

        def json(self):
            if self.url.endswith("/api/tags"):
                return {
                    "models": [
                        {
                            "name": EMBED_MODEL,
                            "digest": "sha256:" + ("b" * 64),
                            "details": {"quantization_level": "Q4_0"},
                        }
                    ]
                }
            if self.url.endswith("/api/version"):
                return {"version": "0.11.4"}
            raise AssertionError(self.url)

    monkeypatch.setattr(
        "cg2_legacy_vector_attestation.requests.get",
        lambda url, timeout=5: _Resp(url),
    )
    with FileGenerationStore(chroma, active_generations=dict) as store:
        with pytest.raises(RollbackBaselineError, match="query|context|D0|ratified"):
            _convert_grb(
                cfg=cfg,
                store=store,
                generation_root=generations,
                owner_digest_value=owner_digest_value,
                ratification_id=ratification_id,
            )


# --- B2: provenance envelope rebind ---


def test_b2_envelope_swap_in_evidence_refuses_validation(d1_env):
    """Envelope swap in persisted LEGACY rows is refused at convert time."""
    twin_b = d1_env["seeded"]["twin_b"]
    col = ChromaStore(str(d1_env["chroma"]))
    try:
        col._collection(UNITS).update(
            ids=["legacy-twin-a"],
            metadatas=[{**d1_env["seeded"]["twin_a"], "provenance_envelope": twin_b["provenance_envelope"]}],
        )
    finally:
        col.close()
    with FileGenerationStore(d1_env["chroma"], active_generations=dict) as store:
        with pytest.raises(RollbackBaselineError, match="root|churn|equivalent|provenance"):
            _convert_grb(
                cfg=d1_env["cfg"],
                store=store,
                generation_root=d1_env["generations"],
                owner_digest_value=d1_env["owner_digest"],
                ratification_id=d1_env["ratification_id"],
            )



def test_b2_mutated_envelope_after_ratification_refuses_convert(d1_env):
    twin_a = d1_env["seeded"]["twin_a"]
    twin_b_env = d1_env["seeded"]["twin_b"]["provenance_envelope"]
    col = ChromaStore(str(d1_env["chroma"]))
    try:
        col._collection(UNITS).update(
            ids=["legacy-twin-a"],
            metadatas=[
                {
                    **twin_a,
                    "provenance_envelope": twin_b_env or twin_a["provenance_envelope"],
                }
            ],
        )
    finally:
        col.close()
    with FileGenerationStore(d1_env["chroma"], active_generations=dict) as store:
        with pytest.raises(RollbackBaselineError, match="root|churn|equivalent|provenance"):
            _convert_grb(
                cfg=d1_env["cfg"],
                store=store,
                generation_root=d1_env["generations"],
                owner_digest_value=d1_env["owner_digest"],
                ratification_id=d1_env["ratification_id"],
            )


def test_b2_inconsistent_assertion_commitment_refuses_validation(d1_env):
    with FileGenerationStore(d1_env["chroma"], active_generations=dict) as store:
        result = _convert_grb(
            cfg=d1_env["cfg"],
            store=store,
            generation_root=d1_env["generations"],
            owner_digest_value=d1_env["owner_digest"],
            ratification_id=d1_env["ratification_id"],
        )
    path = rollback_baseline_evidence_path(
        d1_env["generations"], d1_env["owner_digest"], result.generation_id
    )
    payload = json.loads(path.read_text(encoding="utf-8"))
    rows = list(payload.get("provenance_identity_evidence") or [])
    if rows:
        rows[0]["provenance_commitment"] = "f" * 64
        payload["provenance_identity_evidence"] = rows
        path.write_text(json.dumps(_rehash_evidence(payload), indent=2, sort_keys=True) + "\n")
        with pytest.raises(RollbackBaselineError, match="provenance|bind|identity"):
            validate_retained_rollback_baseline_evidence(
                d1_env["generations"],
                owner_digest_value=d1_env["owner_digest"],
                generation_id=result.generation_id,
                expected_manifest_sha256=result.manifest_sha256,
            )


# --- Same-ledger provenance twins ---


def test_same_ledger_distinct_provenance_survive_without_dedupe_or_remint(d1_env):
    twin_a = d1_env["seeded"]["twin_a"]
    twin_b = d1_env["seeded"]["twin_b"]
    with FileGenerationStore(d1_env["chroma"], active_generations=dict) as store:
        result = _convert_grb(
            cfg=d1_env["cfg"],
            store=store,
            generation_root=d1_env["generations"],
            owner_digest_value=d1_env["owner_digest"],
            ratification_id=d1_env["ratification_id"],
        )
        staged = store.raw_store._collection(UNITS).get(
            where={
                "$and": [
                    {"generation_scope": FILE_SCOPE},
                    {"generation_id": result.generation_id},
                ]
            },
            include=["metadatas"],
        )
    metas = [dict(m or {}) for m in staged.get("metadatas") or []]
    twin_metas = [m for m in metas if m.get("ledger_id") == "obs_shared_twin"]
    assert len(twin_metas) == 2
    assert {m["assertion_id"] for m in twin_metas} == {
        twin_a["assertion_id"],
        twin_b["assertion_id"],
    }


def test_invalid_provenance_follows_conservative_legacy_policy_without_synthesis(d1_env):
    with FileGenerationStore(d1_env["chroma"], active_generations=dict) as store:
        result = _convert_grb(
            cfg=d1_env["cfg"],
            store=store,
            generation_root=d1_env["generations"],
            owner_digest_value=d1_env["owner_digest"],
            ratification_id=d1_env["ratification_id"],
        )
        staged = store.raw_store._collection(UNITS).get(
            where={
                "$and": [
                    {"generation_scope": FILE_SCOPE},
                    {"generation_id": result.generation_id},
                    {"d0_conversion_logical_id": "legacy-bad-prov"},
                ]
            },
            include=["metadatas"],
        )
    metas = [dict(m or {}) for m in staged.get("metadatas") or []]
    assert len(metas) == 1
    assert not metas[0].get("assertion_id")


# --- Accepted-source rebinding ---


def test_wrong_accepted_source_hash_refuses_convert(tmp_path, monkeypatch):
    _mock_d0_runtime(monkeypatch, tmp_path)
    source, accepted_hash, chroma, generations, cfg, _seeded = _prepare(tmp_path)
    owner_digest_value, ratification_id, _body, _cand, _val = _ratify_d0_chain(
        cfg, source, accepted_hash
    )
    processed = Path(cfg["index"]["processed_log"])
    data = json.loads(processed.read_text(encoding="utf-8"))
    wrong = "b" * 64
    data[wrong] = data.pop(accepted_hash)
    processed.write_text(json.dumps(data), encoding="utf-8")
    with FileGenerationStore(chroma, active_generations=dict) as store:
        with pytest.raises(RollbackBaselineError, match="accepted_source_hash|processed|unbound"):
            _convert_grb(
                cfg=cfg,
                store=store,
                generation_root=generations,
                owner_digest_value=owner_digest_value,
                ratification_id=ratification_id,
            )


def test_uppercase_accepted_source_hash_refuses(tmp_path, monkeypatch):
    _mock_d0_runtime(monkeypatch, tmp_path)
    source, accepted_hash, _chroma, _generations, cfg, _seeded = _prepare(tmp_path)
    with pytest.raises(D0AttestationError):
        capture_d0_legacy_vector_candidate(
            cfg,
            owner_key=ownership_key(canonical_source_path(source)),
            source_path=source,
            accepted_source_hash=accepted_hash.upper(),
        )


def test_source_churn_during_conversion_refuses(tmp_path, monkeypatch):
    _mock_d0_runtime(monkeypatch, tmp_path)
    source, accepted_hash, chroma, generations, cfg, _seeded = _prepare(tmp_path)
    owner_digest_value, ratification_id, _body, _cand, _val = _ratify_d0_chain(
        cfg, source, accepted_hash
    )

    original_admit = __import__(
        "cg2_rollback_baseline", fromlist=["_admit_rows"]
    )._admit_rows

    def _churning_admit(*args, **kwargs):
        first = original_admit(*args, **kwargs)
        if first:
            mutated = list(first)
            row = mutated[0]
            mutated[0] = type(row)(
                collection_name=row.collection_name,
                physical_id=row.physical_id,
                logical_id=row.logical_id,
                document=row.document + " ",
                embedding=row.embedding,
                metadata=dict(row.metadata),
                assertion_id=row.assertion_id,
                provenance_commitment=row.provenance_commitment,
                provenance_envelope=row.provenance_envelope,
            )
            return mutated
        return first

    with patch("cg2_rollback_baseline._admit_rows", side_effect=_churning_admit):
        with FileGenerationStore(chroma, active_generations=dict) as store:
            with pytest.raises(RollbackBaselineError, match="churn|root|equivalent"):
                _convert_grb(
                    cfg=cfg,
                    store=store,
                    generation_root=generations,
                    owner_digest_value=owner_digest_value,
                    ratification_id=ratification_id,
                )


# --- Production boundaries ---


def test_load_config_failure_refuses_production_boundary(tmp_path, monkeypatch):
    _mock_ollama_only(monkeypatch)
    source, accepted_hash, chroma, generations, cfg, _seeded = _prepare(tmp_path)
    owner_digest_value, ratification_id, _body, _cand, _val = _ratify_d0_chain(
        cfg, source, accepted_hash
    )
    with patch(
        "cg2_rollback_baseline.load_config",
        side_effect=RuntimeError("config unavailable"),
    ):
        with FileGenerationStore(chroma, active_generations=dict) as store:
            with pytest.raises(
                RollbackBaselineError, match="cannot resolve live production identity"
            ):
                _convert_grb(
                    cfg=cfg,
                    store=store,
                    generation_root=generations,
                    owner_digest_value=owner_digest_value,
                    ratification_id=ratification_id,
                )


def test_configured_production_chroma_without_attestation_refuses(tmp_path, monkeypatch):
    _mock_ollama_only(monkeypatch)
    source, accepted_hash, chroma, generations, cfg, _seeded = _prepare(tmp_path)
    owner_digest_value, ratification_id, _body, _cand, _val = _ratify_d0_chain(
        cfg, source, accepted_hash
    )
    live = {
        "index": {
            "chroma_dir": str(chroma),
            "generation_root": str(generations),
        }
    }
    with patch("cg2_rollback_baseline.load_config", return_value=live):
        with FileGenerationStore(chroma, active_generations=dict) as store:
            with pytest.raises(
                RollbackBaselineError, match="writer boundary|production Chroma"
            ):
                _convert_grb(
                    cfg=cfg,
                    store=store,
                    generation_root=generations,
                    owner_digest_value=owner_digest_value,
                    ratification_id=ratification_id,
                )


def test_live_generation_root_without_attestation_refuses(tmp_path, monkeypatch):
    _mock_ollama_only(monkeypatch)
    source, accepted_hash, chroma, generations, cfg, _seeded = _prepare(tmp_path)
    owner_digest_value, ratification_id, _body, _cand, _val = _ratify_d0_chain(
        cfg, source, accepted_hash
    )
    live = {
        "index": {
            "chroma_dir": str(chroma),
            "generation_root": str(generations),
        }
    }
    with patch("cg2_rollback_baseline.load_config", return_value=live):
        with FileGenerationStore(chroma, active_generations=dict) as store:
            with pytest.raises(
                RollbackBaselineError, match="writer boundary|generation root"
            ):
                _convert_grb(
                    cfg=cfg,
                    store=store,
                    generation_root=generations,
                    owner_digest_value=owner_digest_value,
                    ratification_id=ratification_id,
                )


def test_hermetic_non_production_target_allowed(tmp_path, monkeypatch):
    _mock_d0_runtime(monkeypatch, tmp_path)
    source, accepted_hash, chroma, generations, cfg, _seeded = _prepare(tmp_path / "hermetic")
    owner_digest_value, ratification_id, _body, _cand, _val = _ratify_d0_chain(
        cfg, source, accepted_hash
    )
    live = _fake_live_cfg(tmp_path / "live")
    with patch("cg2_rollback_baseline.load_config", return_value=live):
        with FileGenerationStore(chroma, active_generations=dict) as store:
            result = _convert_grb(
                cfg=cfg,
                store=store,
                generation_root=generations,
                owner_digest_value=owner_digest_value,
                ratification_id=ratification_id,
            )
    assert result.evidence_path.is_file()


def test_grb_protection_permits_canary_staging(d1_env):
    retained: dict[str, set[str]] = {}
    with FileGenerationStore(
        d1_env["chroma"],
        active_generations=dict,
        retained_baselines=lambda: {k: set(v) for k, v in retained.items()},
    ) as store:
        result = _convert_grb(
            cfg=d1_env["cfg"],
            store=store,
            generation_root=d1_env["generations"],
            owner_digest_value=d1_env["owner_digest"],
            ratification_id=d1_env["ratification_id"],
        )
        retained.setdefault(d1_env["owner_digest"], set()).add(result.generation_id)
        before = store.all_physical_ids(UNITS)
        store.stage_rows(
            [
                __import__("file_generation_store", fromlist=["StagedRow"]).StagedRow(
                    UNITS,
                    "fg1_canary",
                    "L1",
                    "canary doc",
                    [0.1, 0.2],
                    {
                        "id": "fg1_canary",
                        "logical_id": "L1",
                        "generation_scope": FILE_SCOPE,
                        "owner_digest": d1_env["owner_digest"],
                        "generation_id": "G_canary",
                    },
                    FILE_SCOPE,
                    d1_env["owner_digest"],
                    "G_canary",
                )
            ]
        )
        assert "fg1_canary" in store.all_physical_ids(UNITS)
        assert len(store.all_physical_ids(UNITS)) >= len(before)


# --- Exact retained evidence ---


def test_immutable_retained_evidence_byte_idempotent(d1_env):
    with FileGenerationStore(d1_env["chroma"], active_generations=dict) as store:
        result = _convert_grb(
            cfg=d1_env["cfg"],
            store=store,
            generation_root=d1_env["generations"],
            owner_digest_value=d1_env["owner_digest"],
            ratification_id=d1_env["ratification_id"],
        )
    path = rollback_baseline_evidence_path(
        d1_env["generations"], d1_env["owner_digest"], result.generation_id
    )
    original = path.read_bytes()
    with FileGenerationStore(d1_env["chroma"], active_generations=dict) as store:
        again = _convert_grb(
            cfg=d1_env["cfg"],
            store=store,
            generation_root=d1_env["generations"],
            owner_digest_value=d1_env["owner_digest"],
            ratification_id=d1_env["ratification_id"],
        )
    assert again.generation_id == result.generation_id
    assert path.read_bytes() == original


def test_byte_distinct_evidence_collision_refuses(d1_env):
    with FileGenerationStore(d1_env["chroma"], active_generations=dict) as store:
        result = _convert_grb(
            cfg=d1_env["cfg"],
            store=store,
            generation_root=d1_env["generations"],
            owner_digest_value=d1_env["owner_digest"],
            ratification_id=d1_env["ratification_id"],
        )
    path = rollback_baseline_evidence_path(
        d1_env["generations"], d1_env["owner_digest"], result.generation_id
    )
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["accepted_source_hash"] = "1" * 64
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(RollbackBaselineError, match="immutable|collision|payload|hash"):
        _convert_grb(
            cfg=d1_env["cfg"],
            store=FileGenerationStore(d1_env["chroma"], active_generations=dict),
            generation_root=d1_env["generations"],
            owner_digest_value=d1_env["owner_digest"],
            ratification_id=d1_env["ratification_id"],
        )


def test_adversarial_evidence_mutation_with_recomputed_hash_refuses(d1_env):
    with FileGenerationStore(d1_env["chroma"], active_generations=dict) as store:
        result = _convert_grb(
            cfg=d1_env["cfg"],
            store=store,
            generation_root=d1_env["generations"],
            owner_digest_value=d1_env["owner_digest"],
            ratification_id=d1_env["ratification_id"],
        )
    path = rollback_baseline_evidence_path(
        d1_env["generations"], d1_env["owner_digest"], result.generation_id
    )
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["normalized_snapshot_digest"] = "e" * 64
    path.write_text(json.dumps(_rehash_evidence(payload), indent=2, sort_keys=True) + "\n")
    with pytest.raises(RollbackBaselineError, match="digest|equivalent|bind|manifest"):
        validate_retained_rollback_baseline_evidence(
            d1_env["generations"],
            owner_digest_value=d1_env["owner_digest"],
            generation_id=result.generation_id,
            expected_manifest_sha256=result.manifest_sha256,
        )


# --- D0 authority consumption ---


def test_d0_missing_ratification_refuses(d1_env):
    with FileGenerationStore(d1_env["chroma"], active_generations=dict) as store:
        with pytest.raises(RollbackBaselineError, match="ratification|D0|missing"):
            _convert_grb(
                cfg=d1_env["cfg"],
                store=store,
                generation_root=d1_env["generations"],
                owner_digest_value=d1_env["owner_digest"],
                ratification_id="does-not-exist",
            )


def test_d0_invalid_ratification_candidate_mismatch_refuses(d1_env):
    rat_path = ratification_path(
        generation_root_for_cfg(d1_env["cfg"]),
        d1_env["owner_digest"],
        d1_env["ratification_id"],
    )
    record = json.loads(rat_path.read_text(encoding="utf-8"))
    record["candidate_artifact_sha256"] = "1" * 64
    rat_path.write_text(json.dumps(record), encoding="utf-8")
    with FileGenerationStore(d1_env["chroma"], active_generations=dict) as store:
        with pytest.raises(RollbackBaselineError, match="candidate|ratification|D0"):
            _convert_grb(
                cfg=d1_env["cfg"],
                store=store,
                generation_root=d1_env["generations"],
                owner_digest_value=d1_env["owner_digest"],
                ratification_id=d1_env["ratification_id"],
            )


def test_d0_query_context_mismatch_refuses_via_verify(d1_env):
    chain = load_ratified_d0_chain(
        d1_env["generations"],
        owner_digest=d1_env["owner_digest"],
        ratification_id=d1_env["ratification_id"],
    )
    with pytest.raises(D0AttestationError, match="query|context|ratified"):
        verify_d0_chain_for_grb_conversion(chain, live_query_context_sha256="f" * 64)


def test_d0_root_mismatch_against_reread_refuses(d1_env):
    col = ChromaStore(str(d1_env["chroma"]))
    try:
        col._collection(UNITS).update(
            ids=["legacy-plain"],
            embeddings=[[0.99, 0.01]],
        )
    finally:
        col.close()
    with FileGenerationStore(d1_env["chroma"], active_generations=dict) as store:
        with pytest.raises(RollbackBaselineError, match="root|vector|snapshot"):
            _convert_grb(
                cfg=d1_env["cfg"],
                store=store,
                generation_root=d1_env["generations"],
                owner_digest_value=d1_env["owner_digest"],
                ratification_id=d1_env["ratification_id"],
            )


def test_d0_cannot_substitute_fresh_candidate_for_ratified_chain(tmp_path, monkeypatch):
    _mock_d0_runtime(monkeypatch, tmp_path)
    source, accepted_hash, chroma, generations, cfg, _seeded = _prepare(tmp_path)
    owner_digest_value, ratification_id, body, _cand, _val = _ratify_d0_chain(
        cfg, source, accepted_hash
    )
    capture_d0_legacy_vector_candidate(
        cfg,
        owner_key=ownership_key(canonical_source_path(source)),
        source_path=source,
        accepted_source_hash=accepted_hash,
    )
    with FileGenerationStore(chroma, active_generations=dict) as store:
        result = _convert_grb(
            cfg=cfg,
            store=store,
            generation_root=generations,
            owner_digest_value=owner_digest_value,
            ratification_id=ratification_id,
        )
    assert result.evidence["normalized_snapshot_digest"]
    chain = load_ratified_d0_chain(
        generations, owner_digest=owner_digest_value, ratification_id=ratification_id
    )
    assert chain.ratification.accepted_legacy_snapshot_root == body["accepted_legacy_snapshot_root"]


def test_non_legacy_owner_refuses_convert(tmp_path, monkeypatch):
    _mock_d0_runtime(monkeypatch, tmp_path)
    source, accepted_hash, chroma, generations, cfg, _seeded = _prepare(tmp_path)
    owner_digest_value, ratification_id, _body, _cand, _val = _ratify_d0_chain(
        cfg, source, accepted_hash
    )
    publish_legacy_fence(generations, ownership_key(source), "2026-08-21T00:00:00Z")
    with FileGenerationStore(chroma, active_generations=dict) as store:
        with pytest.raises(RollbackBaselineError, match="LEGACY|fence|authority"):
            _convert_grb(
                cfg=cfg,
                store=store,
                generation_root=generations,
                owner_digest_value=owner_digest_value,
                ratification_id=ratification_id,
            )


# --- Luna blocker 1: full D0 identity preservation ---


def test_same_logical_distinct_physical_ids_admit_stage_and_equivalence(tmp_path, monkeypatch):
    _mock_hermetic_production_paths(monkeypatch, tmp_path)
    _mock_ollama_only(monkeypatch)
    source = tmp_path / "src.md"
    source.write_text("body\n", encoding="utf-8")
    chroma = tmp_path / "chroma"
    generations = tmp_path / "generations"
    chroma.mkdir()
    generations.mkdir()
    seeded = _seed_same_logical_distinct_physical(chroma, source)
    # also need a summary? D0/D1 may require both collections - use prepare-like cfg
    source, accepted_hash, chroma, generations, cfg, _seeded = _prepare(
        tmp_path,
        with_provenance_twins=False,
        with_invalid_provenance=False,
        with_superseded=False,
        with_stable=False,
        with_summary=True,
        with_other_source=False,
    )
    # wipe units and reseed only same-logical pair + keep summary from prepare
    store = ChromaStore(str(chroma))
    try:
        col = store._collection(UNITS)
        existing = col.get(include=[])
        if existing.get("ids"):
            col.delete(ids=list(existing["ids"]))
    finally:
        store.close()
    seeded = _seed_same_logical_distinct_physical(chroma, source)
    owner_digest_value, ratification_id, *_ = _ratify_d0_chain(cfg, source, accepted_hash)
    with FileGenerationStore(chroma, active_generations=dict) as store:
        result = _convert_grb(
            cfg=cfg,
            store=store,
            generation_root=generations,
            owner_digest_value=owner_digest_value,
            ratification_id=ratification_id,
        )
        staged = store.raw_store._collection(UNITS).get(
            where={
                "$and": [
                    {"generation_scope": FILE_SCOPE},
                    {"generation_id": result.generation_id},
                    {"d0_conversion_logical_id": seeded["shared_logical"]},
                ]
            },
            include=["metadatas"],
        )
    metas = [dict(m or {}) for m in staged.get("metadatas") or []]
    assert len(metas) == 2
    assert {m[D0_PHYSICAL_ID_KEY] for m in metas} == {seeded["phys_a"], seeded["phys_b"]}
    assert {m["logical_id"] for m in metas} == {
        _d1_generation_logical_key(UNITS, seeded["shared_logical"], seeded["phys_a"]),
        _d1_generation_logical_key(UNITS, seeded["shared_logical"], seeded["phys_b"]),
    }
    validate_retained_rollback_baseline_evidence(
        generations,
        owner_digest_value=owner_digest_value,
        generation_id=result.generation_id,
        expected_manifest_sha256=result.manifest_sha256,
    )


def test_same_logical_distinct_physical_with_distinct_provenance_survive(tmp_path, monkeypatch):
    _mock_hermetic_production_paths(monkeypatch, tmp_path)
    _mock_ollama_only(monkeypatch)
    source, accepted_hash, chroma, generations, cfg, _seeded = _prepare(
        tmp_path,
        with_provenance_twins=False,
        with_invalid_provenance=False,
        with_superseded=False,
        with_stable=False,
        with_summary=True,
        with_other_source=False,
    )
    store = ChromaStore(str(chroma))
    try:
        col = store._collection(UNITS)
        existing = col.get(include=[])
        if existing.get("ids"):
            col.delete(ids=list(existing["ids"]))
    finally:
        store.close()
    seeded = _seed_same_logical_distinct_provenance(chroma, source)
    owner_digest_value, ratification_id, *_ = _ratify_d0_chain(cfg, source, accepted_hash)
    with FileGenerationStore(chroma, active_generations=dict) as store:
        result = _convert_grb(
            cfg=cfg,
            store=store,
            generation_root=generations,
            owner_digest_value=owner_digest_value,
            ratification_id=ratification_id,
        )
        staged = store.raw_store._collection(UNITS).get(
            where={
                "$and": [
                    {"generation_scope": FILE_SCOPE},
                    {"generation_id": result.generation_id},
                    {"d0_conversion_logical_id": seeded["shared_logical"]},
                ]
            },
            include=["metadatas"],
        )
    metas = [dict(m or {}) for m in staged.get("metadatas") or []]
    assert len(metas) == 2
    assert {m.get("assertion_id") for m in metas} == {
        seeded["meta_a"]["assertion_id"],
        seeded["meta_b"]["assertion_id"],
    }


def test_same_logical_identical_content_distinct_physical_survive(tmp_path, monkeypatch):
    test_same_logical_distinct_physical_ids_admit_stage_and_equivalence(tmp_path, monkeypatch)


def test_mutate_preserved_d0_physical_id_refuses_validation(d1_env):
    with FileGenerationStore(d1_env["chroma"], active_generations=dict) as store:
        result = _convert_grb(
            cfg=d1_env["cfg"],
            store=store,
            generation_root=d1_env["generations"],
            owner_digest_value=d1_env["owner_digest"],
            ratification_id=d1_env["ratification_id"],
        )
        col = store.raw_store._collection(UNITS)
        staged = col.get(
            where={
                "$and": [
                    {"generation_scope": FILE_SCOPE},
                    {"generation_id": result.generation_id},
                ]
            },
            include=["metadatas"],
        )
        ids = list(staged.get("ids") or [])
        metas = [dict(m or {}) for m in staged.get("metadatas") or []]
        assert ids and metas
        metas[0] = {**metas[0], D0_PHYSICAL_ID_KEY: "tampered-physical"}
        col.update(ids=[ids[0]], metadatas=[metas[0]])
    with FileGenerationStore(d1_env["chroma"], active_generations=dict) as store:
        with pytest.raises(
            RollbackBaselineError,
            match="D0|physical|logical|bind|digest|equivalent|qualification|collision",
        ):
            _convert_grb(
                cfg=d1_env["cfg"],
                store=store,
                generation_root=d1_env["generations"],
                owner_digest_value=d1_env["owner_digest"],
                ratification_id=d1_env["ratification_id"],
            )


def test_swap_preserved_d0_physical_ids_between_twins_refuses(d1_env):
    with FileGenerationStore(d1_env["chroma"], active_generations=dict) as store:
        result = _convert_grb(
            cfg=d1_env["cfg"],
            store=store,
            generation_root=d1_env["generations"],
            owner_digest_value=d1_env["owner_digest"],
            ratification_id=d1_env["ratification_id"],
        )
        col = store.raw_store._collection(UNITS)
        staged = col.get(
            where={
                "$and": [
                    {"generation_scope": FILE_SCOPE},
                    {"generation_id": result.generation_id},
                    {"ledger_id": "obs_shared_twin"},
                ]
            },
            include=["metadatas"],
        )
        ids = list(staged.get("ids") or [])
        metas = [dict(m or {}) for m in staged.get("metadatas") or []]
        assert len(ids) == 2
        swapped = [
            {**metas[0], D0_PHYSICAL_ID_KEY: metas[1][D0_PHYSICAL_ID_KEY]},
            {**metas[1], D0_PHYSICAL_ID_KEY: metas[0][D0_PHYSICAL_ID_KEY]},
        ]
        col.update(ids=ids, metadatas=swapped)
    with FileGenerationStore(d1_env["chroma"], active_generations=dict) as store:
        with pytest.raises(
            RollbackBaselineError,
            match="D0|physical|logical|bind|digest|equivalent|qualification|collision",
        ):
            _convert_grb(
                cfg=d1_env["cfg"],
                store=store,
                generation_root=d1_env["generations"],
                owner_digest_value=d1_env["owner_digest"],
                ratification_id=d1_env["ratification_id"],
            )


def test_delete_preserved_d0_physical_identity_refuses(d1_env):
    with FileGenerationStore(d1_env["chroma"], active_generations=dict) as store:
        result = _convert_grb(
            cfg=d1_env["cfg"],
            store=store,
            generation_root=d1_env["generations"],
            owner_digest_value=d1_env["owner_digest"],
            ratification_id=d1_env["ratification_id"],
        )
        col = store.raw_store._collection(UNITS)
        staged = col.get(
            where={
                "$and": [
                    {"generation_scope": FILE_SCOPE},
                    {"generation_id": result.generation_id},
                ]
            },
            include=["metadatas"],
        )
        ids = list(staged.get("ids") or [])
        metas = [dict(m or {}) for m in staged.get("metadatas") or []]
        metas[0] = {k: v for k, v in metas[0].items() if k != D0_PHYSICAL_ID_KEY}
        col.update(ids=[ids[0]], metadatas=[metas[0]])
    with FileGenerationStore(d1_env["chroma"], active_generations=dict) as store:
        with pytest.raises(RollbackBaselineError, match="d0_physical|missing|D0|bind|qualification|collision"):
            _convert_grb(
                cfg=d1_env["cfg"],
                store=store,
                generation_root=d1_env["generations"],
                owner_digest_value=d1_env["owner_digest"],
                ratification_id=d1_env["ratification_id"],
            )


def test_changing_only_d0_physical_ids_changes_candidate_identity():
    from cg2_rollback_baseline import LegacyServingRow, _bundle_hash_from_rows

    def _row(physical_id: str) -> LegacyServingRow:
        return LegacyServingRow(
            collection_name=UNITS,
            physical_id=physical_id,
            logical_id="shared-L",
            document="body",
            embedding=(0.1, 0.9),
            metadata={
                "logical_id": "shared-L",
                "source_path": "/tmp/x",
                "ledger_id": "obs_l",
                "content_hash": "a" * 64,
                "start_offset": 0,
            },
        )

    first = _bundle_hash_from_rows([_row("phys-a1")])
    second = _bundle_hash_from_rows([_row("phys-a2")])
    assert first != second



# --- Luna blocker 2: exact immutable-byte evidence ---


def test_exact_byte_identical_evidence_rewrite_is_idempotent(d1_env):
    test_immutable_retained_evidence_byte_idempotent(d1_env)


def test_sequence_positions_only_change_refuses_evidence_collision(d1_env):
    with FileGenerationStore(d1_env["chroma"], active_generations=dict) as store:
        result = _convert_grb(
            cfg=d1_env["cfg"],
            store=store,
            generation_root=d1_env["generations"],
            owner_digest_value=d1_env["owner_digest"],
            ratification_id=d1_env["ratification_id"],
        )
    path = rollback_baseline_evidence_path(
        d1_env["generations"], d1_env["owner_digest"], result.generation_id
    )
    payload = json.loads(path.read_text(encoding="utf-8"))
    cold = dict(payload["cold_qualification"])
    positions = dict(cold["sequence_positions"])
    positions["queue_max_seq_id"] = int(positions.get("queue_max_seq_id") or 0) + 7
    if "segment_max_seq_ids" in positions:
        positions["segment_max_seq_ids"] = dict(positions["segment_max_seq_ids"] or {})
        positions["segment_max_seq_ids"]["__tamper__"] = 99
    cold["sequence_positions"] = positions
    payload["cold_qualification"] = cold
    path.write_text(json.dumps(_rehash_evidence(payload), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    with FileGenerationStore(d1_env["chroma"], active_generations=dict) as store:
        with pytest.raises(RollbackBaselineError, match="immutable|collision|sequence|cold|bind"):
            _convert_grb(
                cfg=d1_env["cfg"],
                store=store,
                generation_root=d1_env["generations"],
                owner_digest_value=d1_env["owner_digest"],
                ratification_id=d1_env["ratification_id"],
            )


def test_sequence_positions_removed_refuses(d1_env):
    with FileGenerationStore(d1_env["chroma"], active_generations=dict) as store:
        result = _convert_grb(
            cfg=d1_env["cfg"],
            store=store,
            generation_root=d1_env["generations"],
            owner_digest_value=d1_env["owner_digest"],
            ratification_id=d1_env["ratification_id"],
        )
    path = rollback_baseline_evidence_path(
        d1_env["generations"], d1_env["owner_digest"], result.generation_id
    )
    payload = json.loads(path.read_text(encoding="utf-8"))
    cold = dict(payload["cold_qualification"])
    cold.pop("sequence_positions", None)
    payload["cold_qualification"] = cold
    path.write_text(json.dumps(_rehash_evidence(payload), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    with pytest.raises(RollbackBaselineError, match="sequence_positions|cold-qualification"):
        validate_retained_rollback_baseline_evidence(
            d1_env["generations"],
            owner_digest_value=d1_env["owner_digest"],
            generation_id=result.generation_id,
            expected_manifest_sha256=result.manifest_sha256,
        )


def test_same_parsed_json_different_whitespace_refuses_byte_collision(d1_env):
    with FileGenerationStore(d1_env["chroma"], active_generations=dict) as store:
        result = _convert_grb(
            cfg=d1_env["cfg"],
            store=store,
            generation_root=d1_env["generations"],
            owner_digest_value=d1_env["owner_digest"],
            ratification_id=d1_env["ratification_id"],
        )
    path = rollback_baseline_evidence_path(
        d1_env["generations"], d1_env["owner_digest"], result.generation_id
    )
    payload = json.loads(path.read_text(encoding="utf-8"))
    # Compact JSON: same parsed object, different on-disk bytes.
    path.write_text(json.dumps(payload, separators=(",", ":"), sort_keys=True) + "\n", encoding="utf-8")
    with FileGenerationStore(d1_env["chroma"], active_generations=dict) as store:
        with pytest.raises(RollbackBaselineError, match="immutable|collision|bind|digest|cold"):
            _convert_grb(
                cfg=d1_env["cfg"],
                store=store,
                generation_root=d1_env["generations"],
                owner_digest_value=d1_env["owner_digest"],
                ratification_id=d1_env["ratification_id"],
            )


def test_cold_identity_change_refuses(d1_env):
    with FileGenerationStore(d1_env["chroma"], active_generations=dict) as store:
        result = _convert_grb(
            cfg=d1_env["cfg"],
            store=store,
            generation_root=d1_env["generations"],
            owner_digest_value=d1_env["owner_digest"],
            ratification_id=d1_env["ratification_id"],
        )
    path = rollback_baseline_evidence_path(
        d1_env["generations"], d1_env["owner_digest"], result.generation_id
    )
    payload = json.loads(path.read_text(encoding="utf-8"))
    cold = dict(payload["cold_qualification"])
    cold["identity"] = "a" * 64
    payload["cold_qualification"] = cold
    path.write_text(json.dumps(_rehash_evidence(payload), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    with pytest.raises(RollbackBaselineError, match="cold-qualification|identity|bind"):
        validate_retained_rollback_baseline_evidence(
            d1_env["generations"],
            owner_digest_value=d1_env["owner_digest"],
            generation_id=result.generation_id,
            expected_manifest_sha256=result.manifest_sha256,
        )


def test_provenance_evidence_change_refuses(d1_env):
    with FileGenerationStore(d1_env["chroma"], active_generations=dict) as store:
        result = _convert_grb(
            cfg=d1_env["cfg"],
            store=store,
            generation_root=d1_env["generations"],
            owner_digest_value=d1_env["owner_digest"],
            ratification_id=d1_env["ratification_id"],
        )
    path = rollback_baseline_evidence_path(
        d1_env["generations"], d1_env["owner_digest"], result.generation_id
    )
    payload = json.loads(path.read_text(encoding="utf-8"))
    rows = list(payload.get("provenance_identity_evidence") or [])
    assert rows
    rows[0] = {**rows[0], "assertion_id": "00000000-0000-0000-0000-000000000000"}
    payload["provenance_identity_evidence"] = rows
    path.write_text(json.dumps(_rehash_evidence(payload), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    with pytest.raises(RollbackBaselineError, match="provenance|bind|assertion"):
        validate_retained_rollback_baseline_evidence(
            d1_env["generations"],
            owner_digest_value=d1_env["owner_digest"],
            generation_id=result.generation_id,
            expected_manifest_sha256=result.manifest_sha256,
        )


def test_equivalence_evidence_change_refuses(d1_env):
    with FileGenerationStore(d1_env["chroma"], active_generations=dict) as store:
        result = _convert_grb(
            cfg=d1_env["cfg"],
            store=store,
            generation_root=d1_env["generations"],
            owner_digest_value=d1_env["owner_digest"],
            ratification_id=d1_env["ratification_id"],
        )
    path = rollback_baseline_evidence_path(
        d1_env["generations"], d1_env["owner_digest"], result.generation_id
    )
    payload = json.loads(path.read_text(encoding="utf-8"))
    eq = dict(payload["bidirectional_equivalence"])
    eq["missing_count"] = 1
    payload["bidirectional_equivalence"] = eq
    path.write_text(json.dumps(_rehash_evidence(payload), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    with pytest.raises(RollbackBaselineError, match="equivalent|equivalence|bind|count"):
        validate_retained_rollback_baseline_evidence(
            d1_env["generations"],
            owner_digest_value=d1_env["owner_digest"],
            generation_id=result.generation_id,
            expected_manifest_sha256=result.manifest_sha256,
        )


def test_legitimate_new_evidence_hash_validation_succeeds(d1_env):
    with FileGenerationStore(d1_env["chroma"], active_generations=dict) as store:
        result = _convert_grb(
            cfg=d1_env["cfg"],
            store=store,
            generation_root=d1_env["generations"],
            owner_digest_value=d1_env["owner_digest"],
            ratification_id=d1_env["ratification_id"],
        )
    payload = validate_retained_rollback_baseline_evidence(
        d1_env["generations"],
        owner_digest_value=d1_env["owner_digest"],
        generation_id=result.generation_id,
        expected_manifest_sha256=result.manifest_sha256,
    )
    assert payload.get("evidence_payload_hash")
    assert isinstance(payload["cold_qualification"]["sequence_positions"], dict)

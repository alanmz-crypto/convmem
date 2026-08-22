"""D1 — Exact LEGACY snapshot, convert-v1, and retained rollback baseline."""

from __future__ import annotations

import hashlib
import json
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

import pytest

from chroma_store import SUMMARIES, UNITS, ChromaStore
from file_generation_contract import (
    canonical_hash,
    canonical_source_path,
    make_generation_id,
    ownership_key,
)
from file_generation_pointer import provision_generation_layout
from file_generation_store import (
    FILE_SCOPE,
    STABLE_SCOPE,
    FileGenerationStore,
    GenerationBackpressureError,
    StagedRow,
)
from provenance_binding import (
    attach_unit_provenance,
    build_ingest_envelope,
    projection_metadata,
)
from serving_authority import publish_legacy_fence

from cg2_rollback_baseline import (
    CONVERT_V1_FINGERPRINT,
    RETAINED_ROLLBACK_BASELINE,
    LegacyServingSnapshot,
    RollbackBaselineError,
    capture_accepted_legacy_serving_snapshot,
    convert_and_retain_rollback_baseline,
    prove_bidirectional_equivalence,
    rollback_baseline_evidence_path,
    validate_retained_rollback_baseline_evidence,
)

EMBED_MODEL = "test-embed-v1"
EMBED_DIM = 2


def _cfg(tmp_path: Path, *, chroma: Path, generations: Path, processed: Path) -> dict:
    return {
        "index": {
            "chroma_dir": str(chroma),
            "generation_root": str(generations),
            "processed_log": str(processed),
        }
    }


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
        # Ordinary LEGACY unit without provenance.
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
            assert meta_a["provenance_commitment"] != meta_b["provenance_commitment"]
            store.add_unit(
                "legacy-twin-a",
                "shared ledger twin body",
                [0.9, 0.1],
                meta_a,
            )
            store.add_unit(
                "legacy-twin-b",
                "shared ledger twin body",
                [0.8, 0.2],
                meta_b,
            )
            docs["twin_a"] = meta_a
            docs["twin_b"] = meta_b

        if with_invalid_provenance:
            # Bypass enforce_projection_metadata so we can seed the conservative
            # missing/invalid-provenance LEGACY case that conversion must not invent.
            store._collection(UNITS).upsert(  # pylint: disable=protected-access
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


def _embedding_provenance(store: FileGenerationStore | ChromaStore) -> dict[str, dict]:
    raw = store.raw_store if isinstance(store, FileGenerationStore) else store
    out: dict[str, dict] = {}
    for name in (UNITS, SUMMARIES):
        identity = {
            "collection_uuid": str(raw._collection(name).id),  # pylint: disable=protected-access
            "configuration": dict(raw._collection(name).configuration_json),  # pylint: disable=protected-access
        }
        digest = canonical_hash(
            {
                "collection_uuid": identity["collection_uuid"],
                "configuration": identity["configuration"],
                "embedding_model": EMBED_MODEL,
                "embedding_dimension": EMBED_DIM,
            }
        )
        out[name] = {
            **identity,
            "embedding_model": EMBED_MODEL,
            "embedding_dimension": EMBED_DIM,
            "provenance_evidence_digest": digest,
            "capture_timestamp": "2026-08-21T00:00:00Z",
        }
    return out


def _read_generation_rows_for_test(
    chroma: Path, owner_digest_value: str, generation_id: str
):
    from cg2_rollback_baseline import _read_generation_rows

    with FileGenerationStore(chroma, active_generations=dict) as store:
        return _read_generation_rows(
            store,
            owner_digest_value=owner_digest_value,
            generation_id=generation_id,
        )


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
    cfg = _cfg(tmp_path, chroma=chroma, generations=generations, processed=processed)
    provision_generation_layout(generations)
    return source, accepted_hash, chroma, generations, cfg, seeded


def test_frozen_legacy_set_is_bidirectionally_equivalent_to_grb(tmp_path: Path) -> None:
    source, accepted_hash, chroma, generations, cfg, seeded = _prepare(tmp_path)
    snapshot = capture_accepted_legacy_serving_snapshot(
        cfg=cfg,
        source_path=str(source),
        accepted_source_hash=accepted_hash,
    )
    admitted_ids = {row.physical_id for row in snapshot.rows}
    assert "legacy-plain" in admitted_ids
    assert "legacy-summary" in admitted_ids
    assert "legacy-twin-a" in admitted_ids
    assert "legacy-twin-b" in admitted_ids
    assert "legacy-bad-prov" in admitted_ids
    assert "legacy-superseded" not in admitted_ids
    assert "dec_stable_fixture" not in admitted_ids
    assert "legacy-other-source" not in admitted_ids

    retained: dict[str, set[str]] = {}
    with FileGenerationStore(
        chroma,
        active_generations=dict,
        previous_generations=dict,
        retained_baselines=lambda: {
            owner: set(gens) for owner, gens in retained.items()
        },
    ) as store:
        result = convert_and_retain_rollback_baseline(
            snapshot=snapshot,
            store=store,
            generation_root=generations,
            embedding_provenance=_embedding_provenance(store),
        )
        retained.setdefault(snapshot.owner_digest, set()).add(result.generation_id)

    assert result.convert_fingerprint == CONVERT_V1_FINGERPRINT
    expected_id = make_generation_id(
        owner_digest=snapshot.owner_digest,
        source_hash=accepted_hash,
        pipeline_fingerprint=CONVERT_V1_FINGERPRINT,
        candidate_bundle_hash=snapshot.candidate_bundle_hash,
    )
    assert result.generation_id == expected_id
    equivalence = prove_bidirectional_equivalence(snapshot, result)
    assert equivalence["missing_count"] == 0
    assert equivalence["unexpected_count"] == 0
    assert equivalence["duplicate_count"] == 0
    assert equivalence["wrong_owner_count"] == 0
    assert equivalence["non_equivalent_count"] == 0
    assert equivalence["provenance_identity_changing_count"] == 0

    twin_a = seeded["twin_a"]
    twin_b = seeded["twin_b"]
    evidence = validate_retained_rollback_baseline_evidence(
        generations,
        owner_digest=snapshot.owner_digest,
        generation_id=result.generation_id,
        expected_manifest_sha256=result.manifest_sha256,
    )
    assert evidence["state"] == RETAINED_ROLLBACK_BASELINE
    identities = {
        (row["assertion_id"], row["provenance_commitment"])
        for row in evidence["provenance_identity_evidence"]
        if row.get("assertion_id")
    }
    assert (twin_a["assertion_id"], twin_a["provenance_commitment"]) in identities
    assert (twin_b["assertion_id"], twin_b["provenance_commitment"]) in identities


def test_same_ledger_distinct_provenance_survive_without_dedupe_or_remint(
    tmp_path: Path,
) -> None:
    source, accepted_hash, chroma, generations, cfg, seeded = _prepare(tmp_path)
    snapshot = capture_accepted_legacy_serving_snapshot(
        cfg=cfg,
        source_path=str(source),
        accepted_source_hash=accepted_hash,
    )
    twin_rows = [
        row
        for row in snapshot.rows
        if row.metadata.get("ledger_id") == "obs_shared_twin"
    ]
    assert len(twin_rows) == 2
    assert {row.assertion_id for row in twin_rows} == {
        seeded["twin_a"]["assertion_id"],
        seeded["twin_b"]["assertion_id"],
    }

    with FileGenerationStore(chroma, active_generations=dict) as store:
        result = convert_and_retain_rollback_baseline(
            snapshot=snapshot,
            store=store,
            generation_root=generations,
            embedding_provenance=_embedding_provenance(store),
        )
        staged = store.raw_store._collection(UNITS).get(  # pylint: disable=protected-access
            where={
                "$and": [
                    {"generation_scope": FILE_SCOPE},
                    {"generation_id": result.generation_id},
                ]
            },
            include=["metadatas", "documents"],
        )
    metas = [dict(m or {}) for m in staged.get("metadatas") or []]
    twin_metas = [m for m in metas if m.get("ledger_id") == "obs_shared_twin"]
    assert len(twin_metas) == 2
    assert {m["assertion_id"] for m in twin_metas} == {
        seeded["twin_a"]["assertion_id"],
        seeded["twin_b"]["assertion_id"],
    }
    assert {m["provenance_commitment"] for m in twin_metas} == {
        seeded["twin_a"]["provenance_commitment"],
        seeded["twin_b"]["provenance_commitment"],
    }
    for meta in twin_metas:
        original = (
            seeded["twin_a"]
            if meta["assertion_id"] == seeded["twin_a"]["assertion_id"]
            else seeded["twin_b"]
        )
        assert meta["provenance_envelope"] == original["provenance_envelope"]
        assert meta["assertion_id"] == original["assertion_id"]
        assert meta["provenance_commitment"] == original["provenance_commitment"]


def test_invalid_provenance_follows_conservative_legacy_policy_without_synthesis(
    tmp_path: Path,
) -> None:
    source, accepted_hash, chroma, generations, cfg, _seeded = _prepare(tmp_path)
    snapshot = capture_accepted_legacy_serving_snapshot(
        cfg=cfg,
        source_path=str(source),
        accepted_source_hash=accepted_hash,
    )
    bad = next(row for row in snapshot.rows if row.physical_id == "legacy-bad-prov")
    assert bad.assertion_id is None
    assert bad.provenance_commitment is None
    assert bad.provenance_envelope is None

    with FileGenerationStore(chroma, active_generations=dict) as store:
        result = convert_and_retain_rollback_baseline(
            snapshot=snapshot,
            store=store,
            generation_root=generations,
            embedding_provenance=_embedding_provenance(store),
        )
        staged = store.raw_store._collection(UNITS).get(  # pylint: disable=protected-access
            where={
                "$and": [
                    {"generation_scope": FILE_SCOPE},
                    {"generation_id": result.generation_id},
                    {"logical_id": "legacy-bad-prov"},
                ]
            },
            include=["metadatas"],
        )
    metas = [dict(m or {}) for m in staged.get("metadatas") or []]
    assert len(metas) == 1
    # Conservative: do not invent a valid provenance identity.
    assert not metas[0].get("assertion_id") or metas[0].get("provenance_status") != (
        "self-consistent"
    )


def test_literal_convert_v1_fingerprint_and_deterministic_generation_id(
    tmp_path: Path,
) -> None:
    source, accepted_hash, chroma, generations, cfg, _seeded = _prepare(tmp_path)
    snapshot = capture_accepted_legacy_serving_snapshot(
        cfg=cfg,
        source_path=str(source),
        accepted_source_hash=accepted_hash,
    )
    assert CONVERT_V1_FINGERPRINT == "convmem/cg2-rollback-baseline-convert-v1"
    with FileGenerationStore(chroma, active_generations=dict) as store:
        first = convert_and_retain_rollback_baseline(
            snapshot=snapshot,
            store=store,
            generation_root=generations,
            embedding_provenance=_embedding_provenance(store),
        )
        second_id = make_generation_id(
            owner_digest=snapshot.owner_digest,
            source_hash=accepted_hash,
            pipeline_fingerprint=CONVERT_V1_FINGERPRINT,
            candidate_bundle_hash=snapshot.candidate_bundle_hash,
        )
    assert first.generation_id == second_id
    assert first.convert_fingerprint == CONVERT_V1_FINGERPRINT


def test_persisted_embeddings_and_explicit_embedding_provenance(tmp_path: Path) -> None:
    source, accepted_hash, chroma, generations, cfg, _seeded = _prepare(tmp_path)
    snapshot = capture_accepted_legacy_serving_snapshot(
        cfg=cfg,
        source_path=str(source),
        accepted_source_hash=accepted_hash,
    )
    plain = next(row for row in snapshot.rows if row.physical_id == "legacy-plain")
    assert len(plain.embedding) == EMBED_DIM
    assert all(isinstance(value, float) for value in plain.embedding)

    with FileGenerationStore(chroma, active_generations=dict) as store:
        result = convert_and_retain_rollback_baseline(
            snapshot=snapshot,
            store=store,
            generation_root=generations,
            embedding_provenance=_embedding_provenance(store),
        )
        evidence = validate_retained_rollback_baseline_evidence(
            generations,
            owner_digest=snapshot.owner_digest,
            generation_id=result.generation_id,
            expected_manifest_sha256=result.manifest_sha256,
        )
    for name in (UNITS, SUMMARIES):
        prov = evidence["embedding_provenance"][name]
        assert prov["embedding_model"] == EMBED_MODEL
        assert int(prov["embedding_dimension"]) == EMBED_DIM
        assert prov["collection_uuid"]
        assert isinstance(prov["configuration"], dict)


def test_immutable_retained_evidence_and_manifest_sha_binding(tmp_path: Path) -> None:
    source, accepted_hash, chroma, generations, cfg, _seeded = _prepare(tmp_path)
    snapshot = capture_accepted_legacy_serving_snapshot(
        cfg=cfg,
        source_path=str(source),
        accepted_source_hash=accepted_hash,
    )
    with FileGenerationStore(chroma, active_generations=dict) as store:
        result = convert_and_retain_rollback_baseline(
            snapshot=snapshot,
            store=store,
            generation_root=generations,
            embedding_provenance=_embedding_provenance(store),
        )
    path = rollback_baseline_evidence_path(
        generations, snapshot.owner_digest, result.generation_id
    )
    assert path.is_file()
    original = path.read_bytes()
    evidence = validate_retained_rollback_baseline_evidence(
        generations,
        owner_digest=snapshot.owner_digest,
        generation_id=result.generation_id,
        expected_manifest_sha256=result.manifest_sha256,
    )
    assert evidence["manifest_sha256"] == result.manifest_sha256
    assert evidence["generation_id"] == result.generation_id
    assert evidence["convert_fingerprint"] == CONVERT_V1_FINGERPRINT
    assert evidence["state"] == RETAINED_ROLLBACK_BASELINE
    assert evidence.get("active_pointer") in (None, False)
    assert path.read_bytes() == original

    # Idempotent only for identical bytes.
    with FileGenerationStore(chroma, active_generations=dict) as store:
        again = convert_and_retain_rollback_baseline(
            snapshot=snapshot,
            store=store,
            generation_root=generations,
            embedding_provenance=_embedding_provenance(store),
        )
    assert again.generation_id == result.generation_id
    assert path.read_bytes() == original

    # Overwrite with divergent payload must refuse validation.
    divergent = json.loads(original.decode("utf-8"))
    divergent["accepted_source_hash"] = "1" * 64
    path.write_text(json.dumps(divergent), encoding="utf-8")
    with pytest.raises(
        RollbackBaselineError, match="immutable|collision|overwrite|payload|hash"
    ):
        validate_retained_rollback_baseline_evidence(
            generations,
            owner_digest=snapshot.owner_digest,
            generation_id=result.generation_id,
            expected_manifest_sha256=result.manifest_sha256,
        )


def test_missing_corrupt_wrong_owner_wrong_sha_non_equivalent_refusals(
    tmp_path: Path,
) -> None:
    source, accepted_hash, chroma, generations, cfg, _seeded = _prepare(tmp_path)
    snapshot = capture_accepted_legacy_serving_snapshot(
        cfg=cfg,
        source_path=str(source),
        accepted_source_hash=accepted_hash,
    )
    with FileGenerationStore(chroma, active_generations=dict) as store:
        result = convert_and_retain_rollback_baseline(
            snapshot=snapshot,
            store=store,
            generation_root=generations,
            embedding_provenance=_embedding_provenance(store),
        )

    with pytest.raises(RollbackBaselineError, match="missing|not found"):
        validate_retained_rollback_baseline_evidence(
            generations,
            owner_digest=snapshot.owner_digest,
            generation_id="missing-generation",
            expected_manifest_sha256=result.manifest_sha256,
        )

    path = rollback_baseline_evidence_path(
        generations, snapshot.owner_digest, result.generation_id
    )
    path.write_text("{not-json", encoding="utf-8")
    with pytest.raises(RollbackBaselineError, match="corrupt|invalid|JSON"):
        validate_retained_rollback_baseline_evidence(
            generations,
            owner_digest=snapshot.owner_digest,
            generation_id=result.generation_id,
            expected_manifest_sha256=result.manifest_sha256,
        )

    source2, accepted_hash2, chroma2, generations2, cfg2, _ = _prepare(
        tmp_path / "fresh"
    )
    snapshot2 = capture_accepted_legacy_serving_snapshot(
        cfg=cfg2,
        source_path=str(source2),
        accepted_source_hash=accepted_hash2,
    )
    with FileGenerationStore(chroma2, active_generations=dict) as store:
        result2 = convert_and_retain_rollback_baseline(
            snapshot=snapshot2,
            store=store,
            generation_root=generations2,
            embedding_provenance=_embedding_provenance(store),
        )

    evidence_path = rollback_baseline_evidence_path(
        generations2, snapshot2.owner_digest, result2.generation_id
    )
    payload = json.loads(evidence_path.read_text(encoding="utf-8"))
    payload["owner_digest"] = "0" * 64
    payload.pop("evidence_payload_hash", None)
    from file_generation_contract import canonical_hash as _ch

    payload["evidence_payload_hash"] = _ch(
        {k: v for k, v in payload.items() if k != "evidence_payload_hash"}
    )
    evidence_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    with pytest.raises(RollbackBaselineError, match="owner"):
        validate_retained_rollback_baseline_evidence(
            generations2,
            owner_digest=snapshot2.owner_digest,
            generation_id=result2.generation_id,
            expected_manifest_sha256=result2.manifest_sha256,
        )

    # Restore a fresh convert for SHA / non-equivalent checks.
    source3, accepted_hash3, chroma3, generations3, cfg3, _ = _prepare(
        tmp_path / "sha"
    )
    snapshot3 = capture_accepted_legacy_serving_snapshot(
        cfg=cfg3,
        source_path=str(source3),
        accepted_source_hash=accepted_hash3,
    )
    with FileGenerationStore(chroma3, active_generations=dict) as store:
        result3 = convert_and_retain_rollback_baseline(
            snapshot=snapshot3,
            store=store,
            generation_root=generations3,
            embedding_provenance=_embedding_provenance(store),
        )

    with pytest.raises(RollbackBaselineError, match="SHA|sha|manifest"):
        validate_retained_rollback_baseline_evidence(
            generations3,
            owner_digest=snapshot3.owner_digest,
            generation_id=result3.generation_id,
            expected_manifest_sha256="0" * 64,
        )

    evidence_path3 = rollback_baseline_evidence_path(
        generations3, snapshot3.owner_digest, result3.generation_id
    )
    payload3 = json.loads(evidence_path3.read_text(encoding="utf-8"))
    payload3["normalized_snapshot_digest"] = "f" * 64
    payload3.pop("evidence_payload_hash", None)
    evidence_path3.write_text(json.dumps(payload3, indent=2, sort_keys=True) + "\n")
    with pytest.raises(RollbackBaselineError, match="equivalent|digest|payload"):
        validate_retained_rollback_baseline_evidence(
            generations3,
            owner_digest=snapshot3.owner_digest,
            generation_id=result3.generation_id,
            expected_manifest_sha256=result3.manifest_sha256,
        )


def test_mixed_or_missing_embedding_provenance_refuses(tmp_path: Path) -> None:
    source, accepted_hash, chroma, generations, cfg, _seeded = _prepare(tmp_path)
    snapshot = capture_accepted_legacy_serving_snapshot(
        cfg=cfg,
        source_path=str(source),
        accepted_source_hash=accepted_hash,
    )
    # Inject a mixed-dimension peer into the frozen snapshot without touching Chroma.
    from cg2_rollback_baseline import LegacyServingRow

    mixed_row = LegacyServingRow(
        collection_name=UNITS,
        physical_id="legacy-mixed-dim",
        logical_id="legacy-mixed-dim",
        document="mixed dimension unit",
        embedding=(0.1, 0.2, 0.3),
        metadata={
            "id": "legacy-mixed-dim",
            "logical_id": "legacy-mixed-dim",
            "source_path": snapshot.canonical_source_path,
            "ledger_id": "obs_mixed",
            "content_hash": canonical_hash("mixed dimension unit"),
            "start_offset": 9,
        },
    )
    mixed_snapshot = LegacyServingSnapshot(
        owner_key=snapshot.owner_key,
        owner_digest=snapshot.owner_digest,
        canonical_source_path=snapshot.canonical_source_path,
        accepted_source_hash=snapshot.accepted_source_hash,
        rows=snapshot.rows + (mixed_row,),
        snapshot_digest=snapshot.snapshot_digest,
        candidate_bundle_hash=snapshot.candidate_bundle_hash,
    )
    with FileGenerationStore(chroma, active_generations=dict) as store:
        provenance = _embedding_provenance(store)
        with pytest.raises(RollbackBaselineError, match="dimension|mixed"):
            convert_and_retain_rollback_baseline(
                snapshot=mixed_snapshot,
                store=store,
                generation_root=generations,
                embedding_provenance=provenance,
            )

    source2, accepted_hash2, chroma2, generations2, cfg2, _ = _prepare(
        tmp_path / "missing-model"
    )
    snapshot2 = capture_accepted_legacy_serving_snapshot(
        cfg=cfg2,
        source_path=str(source2),
        accepted_source_hash=accepted_hash2,
    )
    with FileGenerationStore(chroma2, active_generations=dict) as store:
        provenance = _embedding_provenance(store)
        provenance[UNITS] = dict(provenance[UNITS])
        provenance[UNITS]["embedding_model"] = ""
        with pytest.raises(RollbackBaselineError, match="embedding_model|provenance"):
            convert_and_retain_rollback_baseline(
                snapshot=snapshot2,
                store=store,
                generation_root=generations2,
                embedding_provenance=provenance,
            )


def test_non_legacy_owner_refuses_capture(tmp_path: Path) -> None:
    source, accepted_hash, _chroma, generations, cfg, _seeded = _prepare(tmp_path)
    publish_legacy_fence(
        generations, ownership_key(source), "2026-08-21T00:00:00Z"
    )
    with pytest.raises(RollbackBaselineError, match="LEGACY|fence|authority"):
        capture_accepted_legacy_serving_snapshot(
            cfg=cfg,
            source_path=str(source),
            accepted_source_hash=accepted_hash,
        )


def test_empty_peer_set_is_not_bidirectionally_equivalent(tmp_path: Path) -> None:
    source, accepted_hash, chroma, generations, cfg, _seeded = _prepare(tmp_path)
    snapshot = capture_accepted_legacy_serving_snapshot(
        cfg=cfg,
        source_path=str(source),
        accepted_source_hash=accepted_hash,
    )
    with FileGenerationStore(chroma, active_generations=dict) as store:
        result = convert_and_retain_rollback_baseline(
            snapshot=snapshot,
            store=store,
            generation_root=generations,
            embedding_provenance=_embedding_provenance(store),
        )
    empty_snapshot = LegacyServingSnapshot(
        owner_key=snapshot.owner_key,
        owner_digest=snapshot.owner_digest,
        canonical_source_path=snapshot.canonical_source_path,
        accepted_source_hash=snapshot.accepted_source_hash,
        rows=(),
        snapshot_digest=canonical_hash({"rows": []}),
        candidate_bundle_hash=canonical_hash({"units": [], "summaries": []}),
    )
    with pytest.raises(RollbackBaselineError, match="equivalent|missing|unexpected"):
        prove_bidirectional_equivalence(
            empty_snapshot,
            result,
            generation_rows=_read_generation_rows_for_test(
                chroma, snapshot.owner_digest, result.generation_id
            ),
            embedding_provenance=dict(result.evidence["embedding_provenance"]),
        )


def test_grb_protection_permits_g_canary_staging_and_unrelated_abandoned_still_blocks(
    tmp_path: Path,
) -> None:
    source, accepted_hash, chroma, generations, cfg, _seeded = _prepare(tmp_path)
    snapshot = capture_accepted_legacy_serving_snapshot(
        cfg=cfg,
        source_path=str(source),
        accepted_source_hash=accepted_hash,
    )
    retained: dict[str, set[str]] = {}
    active: dict[str, str] = {}
    previous: dict[str, str] = {}
    with FileGenerationStore(
        chroma,
        active_generations=lambda: dict(active),
        previous_generations=lambda: dict(previous),
        retained_baselines=lambda: {
            owner: set(gens) for owner, gens in retained.items()
        },
    ) as store:
        result = convert_and_retain_rollback_baseline(
            snapshot=snapshot,
            store=store,
            generation_root=generations,
            embedding_provenance=_embedding_provenance(store),
        )
        retained.setdefault(snapshot.owner_digest, set()).add(result.generation_id)
        before = store.all_physical_ids(UNITS)

        # G_canary can stage after protected G_rb.
        canary_physical = "fg1_" + "c" * 64
        store.stage_rows(
            [
                StagedRow(
                    UNITS,
                    canary_physical,
                    "canary-logical",
                    "canary document",
                    [1.0, 0.0],
                    {"source_path": snapshot.canonical_source_path},
                    FILE_SCOPE,
                    snapshot.owner_digest,
                    "g-canary",
                )
            ]
        )
        active[snapshot.owner_digest] = "g-canary"
        assert canary_physical in store.all_physical_ids(UNITS)

        # Unrelated abandoned generation still blocks a third stage.
        abandoned_physical = "fg1_" + "a" * 64
        store.stage_rows(
            [
                StagedRow(
                    UNITS,
                    abandoned_physical,
                    "abandoned-logical",
                    "abandoned document",
                    [0.0, 1.0],
                    {"source_path": snapshot.canonical_source_path},
                    FILE_SCOPE,
                    snapshot.owner_digest,
                    "g-abandoned",
                )
            ]
        )
        with pytest.raises(GenerationBackpressureError, match="abandoned"):
            store.stage_rows(
                [
                    StagedRow(
                        UNITS,
                        "fg1_" + "b" * 64,
                        "blocked-logical",
                        "blocked",
                        [0.5, 0.5],
                        {"source_path": snapshot.canonical_source_path},
                        FILE_SCOPE,
                        snapshot.owner_digest,
                        "g-blocked",
                    )
                ]
            )
        # No deletion of prior physical rows.
        assert before.issubset(store.all_physical_ids(UNITS))
        assert abandoned_physical in store.all_physical_ids(UNITS)
        assert result.generation_id in {
            str((meta or {}).get("generation_id") or "")
            for meta in store.raw_store._collection(UNITS).get(  # pylint: disable=protected-access
                include=["metadatas"]
            ).get("metadatas")
            or []
        }


def test_conflicting_foreign_owner_digest_refuses_capture(tmp_path: Path) -> None:
    source, accepted_hash, chroma, _generations, cfg, _seeded = _prepare(tmp_path)
    store = ChromaStore(str(chroma))
    try:
        store.add_unit(
            "legacy-foreign-owner",
            "foreign owner unit",
            [0.15, 0.85],
            {
                "id": "legacy-foreign-owner",
                "logical_id": "legacy-foreign-owner",
                "source_path": canonical_source_path(source),
                "ledger_id": "obs_foreign",
                "content_hash": canonical_hash("foreign owner unit"),
                "start_offset": 3,
                "owner_digest": "ab" * 32,
            },
        )
    finally:
        store.close()
    with pytest.raises(RollbackBaselineError, match="owner|foreign|conflict"):
        capture_accepted_legacy_serving_snapshot(
            cfg=cfg,
            source_path=str(source),
            accepted_source_hash=accepted_hash,
        )


def test_semantic_metadata_churn_refuses_capture(tmp_path: Path) -> None:
    source, accepted_hash, _chroma, _generations, cfg, _seeded = _prepare(tmp_path)
    import cg2_rollback_baseline as baseline

    real_admit = baseline._admit_rows
    calls = {"n": 0}

    def churning_admit(*args, **kwargs):
        rows = real_admit(*args, **kwargs)
        calls["n"] += 1
        if calls["n"] == 2:
            first = rows[0]
            mutated = dict(first.metadata)
            mutated["ledger_id"] = "obs_churned_ledger"
            mutated["content_hash"] = canonical_hash("churned-content-hash")
            rows[0] = replace(first, metadata=mutated)
        return rows

    with patch.object(baseline, "_admit_rows", side_effect=churning_admit):
        with pytest.raises(RollbackBaselineError, match="churn"):
            capture_accepted_legacy_serving_snapshot(
                cfg=cfg,
                source_path=str(source),
                accepted_source_hash=accepted_hash,
            )


def test_wrong_collection_uuid_and_configuration_refuse_convert(tmp_path: Path) -> None:
    source, accepted_hash, chroma, generations, cfg, _seeded = _prepare(tmp_path)
    snapshot = capture_accepted_legacy_serving_snapshot(
        cfg=cfg,
        source_path=str(source),
        accepted_source_hash=accepted_hash,
    )
    with FileGenerationStore(chroma, active_generations=dict) as store:
        provenance = _embedding_provenance(store)
        bad_uuid = dict(provenance)
        bad_uuid[UNITS] = dict(bad_uuid[UNITS])
        bad_uuid[UNITS]["collection_uuid"] = "00000000-0000-0000-0000-000000000000"
        with pytest.raises(RollbackBaselineError, match="UUID|uuid"):
            convert_and_retain_rollback_baseline(
                snapshot=snapshot,
                store=store,
                generation_root=generations,
                embedding_provenance=bad_uuid,
            )

        bad_cfg = _embedding_provenance(store)
        bad_cfg[UNITS] = dict(bad_cfg[UNITS])
        bad_cfg[UNITS]["configuration"] = {"hnsw:space": "l2"}
        with pytest.raises(RollbackBaselineError, match="configuration"):
            convert_and_retain_rollback_baseline(
                snapshot=snapshot,
                store=store,
                generation_root=generations,
                embedding_provenance=bad_cfg,
            )


def test_wrong_accepted_source_hash_refuses_capture(tmp_path: Path) -> None:
    source, _accepted_hash, _chroma, _generations, cfg, _seeded = _prepare(tmp_path)
    with pytest.raises(RollbackBaselineError, match="accepted_source_hash|processed"):
        capture_accepted_legacy_serving_snapshot(
            cfg=cfg,
            source_path=str(source),
            accepted_source_hash="f" * 64,
        )


def test_adversarial_evidence_mutation_with_recomputed_hash_refuses(
    tmp_path: Path,
) -> None:
    source, accepted_hash, chroma, generations, cfg, _seeded = _prepare(tmp_path)
    snapshot = capture_accepted_legacy_serving_snapshot(
        cfg=cfg,
        source_path=str(source),
        accepted_source_hash=accepted_hash,
    )
    with FileGenerationStore(chroma, active_generations=dict) as store:
        result = convert_and_retain_rollback_baseline(
            snapshot=snapshot,
            store=store,
            generation_root=generations,
            embedding_provenance=_embedding_provenance(store),
        )
    path = rollback_baseline_evidence_path(
        generations, snapshot.owner_digest, result.generation_id
    )
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["normalized_snapshot_digest"] = "e" * 64
    payload["bidirectional_equivalence"]["missing_count"] = 0
    payload.pop("evidence_payload_hash", None)
    payload["evidence_payload_hash"] = canonical_hash(
        {key: value for key, value in payload.items() if key != "evidence_payload_hash"}
    )
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    with pytest.raises(RollbackBaselineError, match="digest|equivalent|bind|manifest"):
        validate_retained_rollback_baseline_evidence(
            generations,
            owner_digest=snapshot.owner_digest,
            generation_id=result.generation_id,
            expected_manifest_sha256=result.manifest_sha256,
        )

    payload["accepted_source_hash"] = "a" * 64
    payload.pop("evidence_payload_hash", None)
    payload["evidence_payload_hash"] = canonical_hash(
        {key: value for key, value in payload.items() if key != "evidence_payload_hash"}
    )
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    with pytest.raises(RollbackBaselineError, match="source|digest|bind|generation"):
        validate_retained_rollback_baseline_evidence(
            generations,
            owner_digest=snapshot.owner_digest,
            generation_id=result.generation_id,
            expected_manifest_sha256=result.manifest_sha256,
        )

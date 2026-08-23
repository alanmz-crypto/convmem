"""D3 — first-cutover structural gate (hermetic adversarial matrix)."""

# pylint: disable=duplicate-code,protected-access

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import pytest

from atomic_files import atomic_write_json
from cg2_cutover_guard import read_canary_open_guard
from cg2_first_cutover import (
    FirstCutoverError,
    FirstCutoverGrant,
    publish_first_cutover_active_pointer,
)
from cg2_legacy_vector_attestation import (
    KNOWN_MODEL_AND_VECTOR_V1,
    derive_query_embedding_context,
)
from cg2_rollback_baseline import RollbackBaselineError, rollback_baseline_evidence_path
from chroma_store import SUMMARIES, UNITS
from file_generation_builder import build_candidate_generation
from file_generation_contract import build_generation_manifest
from file_generation_pointer import (
    ManifestReference,
    publish_manifest,
    read_unqualified_pointer,
    recover_active_pointer,
    rollback_active_pointer,
)
from file_generation_store import FileGenerationStore, StagedRow
from serving_authority import (
    OwnerAuthorityMode,
    fence_path,
    resolve_frozen_authority_vector,
)
from source_reconciler import reconciliation_state_path

from tests.test_cg2_rollback_baseline import (
    EMBED_DIM,
    EMBED_MODEL,
    _cfg,
    _convert_grb,
    _mock_d0_runtime,
    _mock_hermetic_production_paths,
    _mock_ollama_only,
    _prepare,
    _ratify_d0_chain,
)

BACKEND_FINGERPRINT = "rust-bindings/cg2-d3-test"


class EmptyCommittedView:
    def query_units(self, _embedding, _top_k):
        return []

    def get_unit(self, _unit_id):
        return None


class _OneLockOracle:
    def __init__(self) -> None:
        self.acquisitions: list[str] = []
        self._held = False

    def __call__(self, cfg, canonical_source):
        if self._held:
            raise AssertionError(f"nested source_flock reentry for {canonical_source}")
        self._held = True
        self.acquisitions.append(str(canonical_source))
        return self

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self._held = False
        return False


def _mark_reconciliation_fresh(cfg: dict) -> None:
    atomic_write_json(
        reconciliation_state_path(cfg),
        {
            "dirty_scopes": [],
            "pending_by_owner": {},
            "last_successful_sweep_at": datetime.now(timezone.utc)
            .isoformat()
            .replace("+00:00", "Z"),
        },
    )


def _build_canary(env: dict, *, retained: dict[str, set[str]]):
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
    canary_ref = publish_manifest(env["generations"], manifest)
    assert (
        canary_ref.manifest["recorded_only_annotations"]["proof_profile"]
        == KNOWN_MODEL_AND_VECTOR_V1
    )
    return candidate, canary_ref


def _make_grant(env: dict, grb_result, canary_ref: ManifestReference, *, grant_id: str):
    evidence_path = rollback_baseline_evidence_path(
        env["generations"],
        env["owner_digest"],
        grb_result.generation_id,
    )
    evidence_sha = hashlib.sha256(evidence_path.read_bytes()).hexdigest()
    _context, query_sha = derive_query_embedding_context(
        env["cfg"], admitted_dimension=EMBED_DIM
    )
    return FirstCutoverGrant(
        grant_id=grant_id,
        owner_digest=env["owner_digest"],
        ratification_id=env["ratification_id"],
        grb_generation_id=grb_result.generation_id,
        grb_manifest_sha256=grb_result.manifest_sha256,
        grb_evidence_sha256=evidence_sha,
        canary_generation_id=str(canary_ref.manifest["generation_id"]),
        canary_manifest_sha256=canary_ref.file_sha256,
        query_embedding_context_sha256=query_sha,
    )


def _cutover(
    env: dict,
    canary_ref: ManifestReference,
    grant: FirstCutoverGrant,
    *,
    prior_grant_id: str | None = None,
    published_at: str = "2026-08-23T00:00:00Z",
):
    return publish_first_cutover_active_pointer(
        env["generations"],
        canary_ref,
        grant=grant,
        chroma_dir=env["chroma"],
        cfg=env["cfg"],
        backend_fingerprint=BACKEND_FINGERPRINT,
        prior_grant_id=prior_grant_id,
        published_at=published_at,
    )


@pytest.fixture(name="d3_env")
def _d3_env_fixture(tmp_path, monkeypatch):
    _mock_hermetic_production_paths(monkeypatch, tmp_path)
    _mock_ollama_only(monkeypatch)
    source, accepted_hash, chroma, generations, cfg, seeded = _prepare(tmp_path)
    owner_digest_value, ratification_id, candidate_body, _cand_ref, _val = _ratify_d0_chain(
        cfg, source, accepted_hash
    )
    retained: dict[str, set[str]] = {}
    with FileGenerationStore(
        chroma,
        active_generations=dict,
        retained_baselines=lambda: {k: set(v) for k, v in retained.items()},
    ) as store:
        grb_result = _convert_grb(
            cfg=cfg,
            store=store,
            generation_root=generations,
            owner_digest_value=owner_digest_value,
            ratification_id=ratification_id,
        )
        retained.setdefault(owner_digest_value, set()).add(grb_result.generation_id)
        _candidate, canary_ref = _build_canary(
            {
                "source": source,
                "chroma": chroma,
                "generations": generations,
                "owner_digest": owner_digest_value,
            },
            retained=retained,
        )
    _mark_reconciliation_fresh(cfg)
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
        "grb_result": grb_result,
        "canary_ref": canary_ref,
    }


def test_successful_first_cutover(d3_env):
    grant = _make_grant(d3_env, d3_env["grb_result"], d3_env["canary_ref"], grant_id="grant-success-1")
    qualified = _cutover(d3_env, d3_env["canary_ref"], grant)
    assert qualified.pointer["active_generation_id"] == grant.canary_generation_id
    assert qualified.pointer["previous_generation_id"] == grant.grb_generation_id
    assert fence_path(d3_env["generations"], grant.owner_digest).exists()
    assert read_canary_open_guard(d3_env["generations"], grant.owner_digest) is not None
    vector = resolve_frozen_authority_vector(
        d3_env["cfg"], owner_digests={grant.owner_digest}
    )
    assert vector.by_owner[grant.owner_digest].mode == OwnerAuthorityMode.GENERATIONAL


def test_preflight_refuses_grb_equals_canary(d3_env):
    grb = d3_env["grb_result"]
    grant = _make_grant(d3_env, grb, d3_env["canary_ref"], grant_id="grant-same-id")
    bad = FirstCutoverGrant(
        grant_id=grant.grant_id,
        owner_digest=grant.owner_digest,
        ratification_id=grant.ratification_id,
        grb_generation_id=grant.canary_generation_id,
        grb_manifest_sha256=grant.canary_manifest_sha256,
        grb_evidence_sha256=grant.grb_evidence_sha256,
        canary_generation_id=grant.canary_generation_id,
        canary_manifest_sha256=grant.canary_manifest_sha256,
        query_embedding_context_sha256=grant.query_embedding_context_sha256,
    )
    oracle = _OneLockOracle()
    with patch("cg2_first_cutover.source_flock", oracle):
        with pytest.raises(FirstCutoverError, match="distinct generation IDs"):
            _cutover(d3_env, d3_env["canary_ref"], bad)
    assert oracle.acquisitions == []


@pytest.mark.parametrize(
    "mutator,match",
    [
        (
            lambda grant, _env, _grb: FirstCutoverGrant(
                grant_id=grant.grant_id,
                owner_digest=grant.owner_digest,
                ratification_id=grant.ratification_id,
                grb_generation_id=grant.grb_generation_id,
                grb_manifest_sha256="f" * 64,
                grb_evidence_sha256=grant.grb_evidence_sha256,
                canary_generation_id=grant.canary_generation_id,
                canary_manifest_sha256=grant.canary_manifest_sha256,
                query_embedding_context_sha256=grant.query_embedding_context_sha256,
            ),
            "manifest SHA|baseline evidence",
        ),
        (
            lambda grant, _env, _grb: FirstCutoverGrant(
                grant_id=grant.grant_id,
                owner_digest=grant.owner_digest,
                ratification_id=grant.ratification_id,
                grb_generation_id=grant.grb_generation_id,
                grb_manifest_sha256=grant.grb_manifest_sha256,
                grb_evidence_sha256=grant.grb_evidence_sha256,
                canary_generation_id=grant.canary_generation_id,
                canary_manifest_sha256="e" * 64,
                query_embedding_context_sha256=grant.query_embedding_context_sha256,
            ),
            "canary manifest SHA",
        ),
        (
            lambda grant, env, grb: FirstCutoverGrant(
                grant_id=grant.grant_id,
                owner_digest=grant.owner_digest,
                ratification_id=grant.ratification_id,
                grb_generation_id=grant.grb_generation_id,
                grb_manifest_sha256=grant.grb_manifest_sha256,
                grb_evidence_sha256="d" * 64,
                canary_generation_id=grant.canary_generation_id,
                canary_manifest_sha256=grant.canary_manifest_sha256,
                query_embedding_context_sha256=grant.query_embedding_context_sha256,
            ),
            "evidence SHA",
        ),
        (
            lambda grant, env, grb: (
                rollback_baseline_evidence_path(
                    env["generations"], env["owner_digest"], grb.generation_id
                ).unlink(),
                grant,
            )[1],
            "missing|retained|baseline",
        ),
    ],
)
def test_preflight_refusal_matrix(d3_env, mutator, match):
    grant = _make_grant(
        d3_env, d3_env["grb_result"], d3_env["canary_ref"], grant_id="grant-preflight"
    )
    bad = mutator(grant, d3_env, d3_env["grb_result"])
    oracle = _OneLockOracle()
    with patch("cg2_first_cutover.source_flock", oracle):
        with pytest.raises((FirstCutoverError, RollbackBaselineError), match=match):
            _cutover(d3_env, d3_env["canary_ref"], bad)
    assert oracle.acquisitions == []
    assert read_unqualified_pointer(d3_env["generations"], grant.owner_digest) is None
    assert not fence_path(d3_env["generations"], grant.owner_digest).exists()


def test_one_lock_successful_cutover(d3_env):
    grant = _make_grant(d3_env, d3_env["grb_result"], d3_env["canary_ref"], grant_id="grant-one-lock")
    oracle = _OneLockOracle()
    with patch("cg2_first_cutover.source_flock", oracle):
        _cutover(d3_env, d3_env["canary_ref"], grant)
    assert len(oracle.acquisitions) == 1


def test_lock_held_reread_before_fence(d3_env):
    import cg2_first_cutover as cutover_mod
    from serving_authority import publish_legacy_fence as real_fence

    grant = _make_grant(d3_env, d3_env["grb_result"], d3_env["canary_ref"], grant_id="grant-reread")
    call_order: list[str] = []
    real_reread = cutover_mod._lock_held_reread_d0_legacy

    def _track_reread(*args, **kwargs):
        call_order.append("reread")
        return real_reread(*args, **kwargs)

    def _track_fence(*args, **kwargs):
        call_order.append("fence")
        return real_fence(*args, **kwargs)

    with patch.object(cutover_mod, "_lock_held_reread_d0_legacy", side_effect=_track_reread):
        with patch.object(cutover_mod, "publish_legacy_fence", side_effect=_track_fence):
            _cutover(d3_env, d3_env["canary_ref"], grant)
    assert "reread" in call_order
    assert "fence" in call_order
    assert call_order.index("reread") < call_order.index("fence")


def test_drift_before_fence_refuses(d3_env):
    grant = _make_grant(d3_env, d3_env["grb_result"], d3_env["canary_ref"], grant_id="grant-drift")
    with patch(
        "cg2_first_cutover._lock_held_reread_d0_legacy",
        side_effect=FirstCutoverError("lock-held LEGACY reread snapshot root drifted"),
    ):
        with pytest.raises(FirstCutoverError, match="drifted|reread"):
            _cutover(d3_env, d3_env["canary_ref"], grant)
    assert not fence_path(d3_env["generations"], grant.owner_digest).exists()
    assert read_unqualified_pointer(d3_env["generations"], grant.owner_digest) is None


def test_crash_after_fence_leaves_fenced_no_pointer(d3_env):
    grant = _make_grant(d3_env, d3_env["grb_result"], d3_env["canary_ref"], grant_id="grant-crash")
    with patch(
        "cg2_first_cutover._publish_pointer_under_lock",
        side_effect=RuntimeError("simulated crash after fence"),
    ):
        with pytest.raises(RuntimeError, match="simulated crash"):
            _cutover(d3_env, d3_env["canary_ref"], grant)
    assert fence_path(d3_env["generations"], grant.owner_digest).exists()
    assert read_unqualified_pointer(d3_env["generations"], grant.owner_digest) is None
    vector = resolve_frozen_authority_vector(
        d3_env["cfg"], owner_digests={grant.owner_digest}
    )
    state = vector.by_owner[grant.owner_digest]
    assert state.mode == OwnerAuthorityMode.FENCED_NO_POINTER
    assert state.mode != OwnerAuthorityMode.LEGACY


def test_fresh_grant_resume_after_fence_crash(d3_env):
    first_grant = _make_grant(
        d3_env, d3_env["grb_result"], d3_env["canary_ref"], grant_id="grant-crash-old"
    )
    with patch(
        "cg2_first_cutover._publish_pointer_under_lock",
        side_effect=RuntimeError("simulated crash after fence"),
    ):
        with pytest.raises(RuntimeError, match="simulated crash"):
            _cutover(d3_env, d3_env["canary_ref"], first_grant)
    assert fence_path(d3_env["generations"], first_grant.owner_digest).exists()
    assert read_unqualified_pointer(d3_env["generations"], first_grant.owner_digest) is None

    resume_grant = _make_grant(
        d3_env, d3_env["grb_result"], d3_env["canary_ref"], grant_id="grant-crash-new"
    )
    qualified = _cutover(
        d3_env,
        d3_env["canary_ref"],
        resume_grant,
        prior_grant_id=first_grant.grant_id,
    )
    assert qualified.pointer["active_generation_id"] == resume_grant.canary_generation_id
    assert qualified.pointer["previous_generation_id"] == resume_grant.grb_generation_id


def test_old_grant_refused_on_resume(d3_env):
    first_grant = _make_grant(
        d3_env, d3_env["grb_result"], d3_env["canary_ref"], grant_id="grant-resume-same"
    )
    with patch(
        "cg2_first_cutover._publish_pointer_under_lock",
        side_effect=RuntimeError("simulated crash after fence"),
    ):
        with pytest.raises(RuntimeError, match="simulated crash"):
            _cutover(d3_env, d3_env["canary_ref"], first_grant)

    with pytest.raises(FirstCutoverError, match="prior_grant_id distinct"):
        _cutover(
            d3_env,
            d3_env["canary_ref"],
            first_grant,
            prior_grant_id=first_grant.grant_id,
        )


def test_open_guard_blocks_second_first_cutover(d3_env):
    grant = _make_grant(
        d3_env, d3_env["grb_result"], d3_env["canary_ref"], grant_id="grant-guard-block"
    )
    _cutover(d3_env, d3_env["canary_ref"], grant)
    second = _make_grant(
        d3_env, d3_env["grb_result"], d3_env["canary_ref"], grant_id="grant-guard-block-2"
    )
    with pytest.raises(FirstCutoverError, match="prior_grant_id|pointer absence|guard absence|initial cutover"):
        _cutover(d3_env, d3_env["canary_ref"], second)


def test_rollback_and_recovery_remain_callable_with_open_guard(d3_env):
    grant = _make_grant(
        d3_env, d3_env["grb_result"], d3_env["canary_ref"], grant_id="grant-rollback-open-guard"
    )
    active = _cutover(d3_env, d3_env["canary_ref"], grant)
    assert read_canary_open_guard(d3_env["generations"], grant.owner_digest) is not None

    from file_generation_pointer import load_manifest_reference

    grb_reference = load_manifest_reference(
        d3_env["generations"],
        manifest_filename=d3_env["grb_result"].manifest_filename,
        expected_sha256=d3_env["grb_result"].manifest_sha256,
    )
    rolled = rollback_active_pointer(
        d3_env["generations"],
        grb_reference,
        chroma_dir=d3_env["chroma"],
        cfg=d3_env["cfg"],
        expected_active_generation_id=active.pointer["active_generation_id"],
        backend_fingerprint=BACKEND_FINGERPRINT,
    )
    assert rolled.pointer["active_generation_id"] == grant.grb_generation_id
    assert read_canary_open_guard(d3_env["generations"], grant.owner_digest) is not None

    recovered = recover_active_pointer(
        d3_env["generations"],
        rolled.pointer["owner_key"],
        chroma_dir=d3_env["chroma"],
        cfg=d3_env["cfg"],
    )
    assert recovered.pointer["active_generation_id"] == grant.grb_generation_id
    assert read_canary_open_guard(d3_env["generations"], grant.owner_digest) is not None

"""CG-2 Design A isolated rehearsal and Execute evidence (D5)."""

# pylint: disable=duplicate-code,too-many-lines

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from unittest.mock import patch

import chromadb

from atomic_files import atomic_write_json
from cg2_cutover_guard import read_canary_open_guard
from cg2_first_cutover import FirstCutoverGrant, FirstCutoverError, publish_first_cutover_active_pointer
from cg2_legacy_vector_attestation import (
    CG2_D0_RATIFICATION_V1,
    KNOWN_MODEL_AND_VECTOR_V1,
    capture_d0_legacy_vector_candidate,
    derive_query_embedding_context,
    validate_d0_legacy_vector_candidate,
)
from cg2_property_map import build_property_map_report, verify_property_map_completeness
from cg2_rollback_baseline import (
    convert_and_retain_rollback_baseline,
    rollback_baseline_evidence_path,
)
from chroma_store import ChromaStore, SUMMARIES, UNITS, open_chroma_for_read
from file_generation_builder import build_candidate_generation
from file_generation_contract import (
    build_generation_manifest,
    canonical_bytes,
    canonical_hash,
    canonical_source_path,
    ownership_key,
)
import file_generation_pointer as fg_pointer
from file_generation_pointer import (
    ManifestReference,
    load_manifest_reference,
    pointer_path,
    publish_manifest,
    read_unqualified_pointer,
    rollback_active_pointer,
)
from file_generation_store import FileGenerationStore, StagedRow
from mixed_mode_proof import (
    PHYSICAL_DELETION_DISABLED,
    RehearsalEmptyCommittedView,
    open_rehearsal_serving_session,
    resolve_rehearsal_authority_vector,
    run_rehearsal_subprocess_public_open,
    run_rehearsal_subprocess_restart_recovery,
)
from mixed_mode_retrieval import PINNED_CHROMA_VERSION
from serving_authority import (
    fence_path,
    generation_root_for_cfg,
    resolve_frozen_authority_vector,
)
from serving_index_repository import ServingIndexRepository, open_serving_index_repository
from source_reconciler import (
    pending_owner_work,
    record_rollback_reconciliation_obligation,
    reconciliation_state_path,
)

REHEARSAL_SCHEMA = "convmem/cg2-rehearsal-v1"
DESIGN_A_REHEARSAL_SCHEMA = "convmem/cg2-design-a-rehearsal-v1"
ARCHITECTURE_SHA = "3d8b151907f02c8b8ead89585fb43904840b210b"
EXECUTION_PLAN_SHA = "9a171bdf03d501ff891d991bbdad6acc1abda56c"
BACKEND_FINGERPRINT = "rust-bindings/cg2-d5-rehearsal"
EMBED_MODEL = "nomic-embed-text"
EMBED_DIM = 2


class RehearsalProductionIsolationError(RuntimeError):
    """Production path resolution or isolation check failed during rehearsal."""


def _git_sha(path: str | None = None) -> str:
    cmd = ["git", "rev-parse", "HEAD"]
    if path:
        cmd = ["git", "rev-parse", path]
    return subprocess.check_output(cmd, text=True).strip()


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _sha256_file(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def _sha256_json(path: Path) -> str:
    return _sha256_bytes(canonical_bytes(json.loads(path.read_text(encoding="utf-8"))))


def _durable_reconciliation_hash(cfg: dict[str, Any]) -> str:
    return _sha256_bytes(reconciliation_state_path(cfg).read_bytes())


def _durable_fence_guard_hashes(env: dict[str, Any]) -> tuple[str, str]:
    fence_file = fence_path(env["generations"], env["owner_digest"])
    guard = read_canary_open_guard(env["generations"], env["owner_digest"])
    return _sha256_file(fence_file), _sha256_bytes(canonical_bytes(dict(guard or {})))


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


def install_hermetic_production_boundary_patches(monkeypatch, tmp_path: Path) -> tuple[Path, Path]:
    """Point configured production identity at isolated markers under ``tmp_path``."""

    live_chroma = tmp_path / "configured-live-chroma"
    live_generations = tmp_path / "configured-live-generations"
    live_chroma.mkdir(parents=True, exist_ok=True)
    live_generations.mkdir(parents=True, exist_ok=True)
    for module in (
        "cg2_legacy_vector_attestation",
        "cg2_rollback_baseline",
    ):
        monkeypatch.setattr(
            f"{module}._resolve_live_production_paths",
            lambda _c=live_chroma, _g=live_generations: (_c, _g),
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
    return live_chroma, live_generations


def _cfg(*, chroma: Path, generations: Path, processed: Path) -> dict[str, Any]:
    return {
        "models": {"embed_model": EMBED_MODEL, "ollama_host": "http://127.0.0.1:9"},
        "index": {
            "chroma_dir": str(chroma),
            "generation_root": str(generations),
            "processed_log": str(processed),
        },
    }


def _seed_minimal_legacy_corpus(chroma: Path, source: Path) -> None:
    canonical = canonical_source_path(source)
    store = ChromaStore(str(chroma))
    try:
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
    finally:
        store.close()


def _prepare_hermetic_roots(tmp_path: Path) -> dict[str, Any]:
    tmp_path.mkdir(parents=True, exist_ok=True)
    source = tmp_path / "accepted-source.jsonl"
    source.write_text("accepted-legacy-bytes-v1", encoding="utf-8")
    accepted_hash = _sha256_file(source)
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
    _seed_minimal_legacy_corpus(chroma, source)
    cfg = _cfg(chroma=chroma, generations=generations, processed=processed)
    from file_generation_pointer import provision_generation_layout

    provision_generation_layout(generations)
    return {
        "source": source,
        "accepted_hash": accepted_hash,
        "chroma": chroma,
        "generations": generations,
        "cfg": cfg,
    }


def _ratify_synthetic_d0_chain(
    cfg: dict[str, Any],
    source: Path,
    accepted_hash: str,
    *,
    ratification_id: str = "ryan-d5-hermetic-1",
) -> dict[str, Any]:
    from cg2_legacy_vector_attestation import _publish_immutable, ratification_path

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
        validator_identity="d5-hermetic-validator",
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
    _context, live_query_sha = derive_query_embedding_context(
        cfg, admitted_dimension=EMBED_DIM
    )
    return {
        "owner_digest": candidate.owner_digest,
        "owner_key": owner_key,
        "ratification_id": ratification_id,
        "candidate_sha256": candidate.candidate_sha256,
        "validation_sha256": validation.validation_result_sha256,
        "ratification_sha256": _sha256_bytes(canonical_bytes(record)),
        "ratified_query_context_sha256": cand["query_embedding_context_sha256"],
        "live_query_context_sha256": live_query_sha,
        "candidate_body": cand,
    }


def _convert_grb(
    *,
    cfg: dict[str, Any],
    chroma: Path,
    generations: Path,
    owner_digest: str,
    ratification_id: str,
) -> Any:
    with FileGenerationStore(chroma, active_generations=dict) as store:
        return convert_and_retain_rollback_baseline(
            cfg=cfg,
            store=store,
            generation_root=generations,
            owner_digest_value=owner_digest,
            ratification_id=ratification_id,
        )


def _build_canary(
    env: dict[str, Any],
    *,
    retained: dict[str, set[str]],
) -> tuple[Any, ManifestReference]:
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
        committed_store=RehearsalEmptyCommittedView(),
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
    return candidate, canary_ref


def build_hermetic_design_a_environment(tmp_path: Path) -> dict[str, Any]:
    """Prepare D0 ratification, G_rb, and qualified G_canary under temporary roots."""

    env = _prepare_hermetic_roots(tmp_path)
    d0 = _ratify_synthetic_d0_chain(
        env["cfg"], env["source"], env["accepted_hash"]
    )
    retained: dict[str, set[str]] = {}
    grb_result = _convert_grb(
        cfg=env["cfg"],
        chroma=env["chroma"],
        generations=env["generations"],
        owner_digest=d0["owner_digest"],
        ratification_id=d0["ratification_id"],
    )
    retained.setdefault(d0["owner_digest"], set()).add(grb_result.generation_id)
    _candidate, canary_ref = _build_canary(env, retained=retained)
    atomic_write_json(
        reconciliation_state_path(env["cfg"]),
        {
            "dirty_scopes": [],
            "pending_by_owner": {},
            "last_successful_sweep_at": datetime.now(timezone.utc)
            .isoformat()
            .replace("+00:00", "Z"),
        },
    )
    env.update(
        {
            "owner_digest": d0["owner_digest"],
            "owner_key": d0["owner_key"],
            "ratification_id": d0["ratification_id"],
            "d0": d0,
            "grb_result": grb_result,
            "canary_ref": canary_ref,
            "retained": retained,
        }
    )
    return env


def _make_cutover_grant(env: dict[str, Any], *, grant_id: str) -> FirstCutoverGrant:
    grb_result = env["grb_result"]
    canary_ref = env["canary_ref"]
    evidence_path = rollback_baseline_evidence_path(
        env["generations"], env["owner_digest"], grb_result.generation_id
    )
    evidence_sha = _sha256_file(evidence_path)
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


def _publish_cutover(
    env: dict[str, Any],
    grant: FirstCutoverGrant,
    *,
    prior_grant_id: str | None = None,
) -> Any:
    return publish_first_cutover_active_pointer(
        env["generations"],
        env["canary_ref"],
        grant=grant,
        chroma_dir=env["chroma"],
        cfg=env["cfg"],
        backend_fingerprint=BACKEND_FINGERPRINT,
        prior_grant_id=prior_grant_id,
    )


def _rollback_grb(env: dict[str, Any], grant: FirstCutoverGrant, *, active_generation_id: str):
    grb_reference = load_manifest_reference(
        env["generations"],
        manifest_filename=env["grb_result"].manifest_filename,
        expected_sha256=env["grb_result"].manifest_sha256,
    )
    return rollback_active_pointer(
        env["generations"],
        grb_reference,
        chroma_dir=env["chroma"],
        cfg=env["cfg"],
        expected_active_generation_id=active_generation_id,
        backend_fingerprint=BACKEND_FINGERPRINT,
        grb_ratification_id=grant.ratification_id,
        grb_evidence_sha256=grant.grb_evidence_sha256,
    )


@contextmanager
def _frozen_serving_repository(env: dict[str, Any]):
    vector = resolve_frozen_authority_vector(
        env["cfg"], owner_digests={env["owner_digest"]}
    )
    from serving_index_repository import _open_backing_store

    store = _open_backing_store(vector)
    repo = ServingIndexRepository(vector, store, cfg=env["cfg"])
    try:
        yield repo
    finally:
        repo.close()


def _assert_frozen_generation_stable(env: dict[str, Any], grant: FirstCutoverGrant) -> dict[str, Any]:
    """Prove request freeze survives a mid-request pointer rollback."""

    embedding = [0.01, 0.02]
    owner_digest = env["owner_digest"]
    pointer_file = pointer_path(env["generations"], owner_digest)
    saved_pointer = json.loads(pointer_file.read_text(encoding="utf-8"))
    frozen_vector_id: int | None = None
    with _frozen_serving_repository(env) as repo:
        frozen_vector_id = id(repo.authority_vector)
        frozen_generation = repo.authority_vector.active_generations()[owner_digest]
        before_rows = repo.query_units(embedding, 5)
        before_ids = {row["id"] for row in before_rows}
        _rollback_grb(env, grant, active_generation_id=grant.canary_generation_id)
        after_pointer = read_unqualified_pointer(env["generations"], owner_digest)
        assert after_pointer is not None
        assert after_pointer["active_generation_id"] == grant.grb_generation_id
        after_rows = repo.query_units(embedding, 5)
        after_ids = {row["id"] for row in after_rows}
        still_frozen = repo.authority_vector.active_generations()[owner_digest]

    disk_after_rollback = read_unqualified_pointer(env["generations"], owner_digest)
    assert disk_after_rollback is not None
    disk_authority_after_rollback = resolve_rehearsal_authority_vector(env["cfg"]).by_owner[
        owner_digest
    ].generation_id

    grb_fresh_open = run_rehearsal_subprocess_public_open(env["cfg"], owner_digest)
    assert grb_fresh_open["active_generation_id"] == grant.grb_generation_id

    atomic_write_json(pointer_file, saved_pointer)
    restored = read_unqualified_pointer(env["generations"], owner_digest)

    canary_fresh_open = run_rehearsal_subprocess_public_open(env["cfg"], owner_digest)

    return {
        "frozen_generation_id": frozen_generation,
        "still_frozen_generation_id": still_frozen,
        "pointer_changed_to": after_pointer["active_generation_id"],
        "pointer_restored_to": restored["active_generation_id"] if restored else None,
        "query_ids_unchanged": before_ids == after_ids,
        "disk_pointer_after_rollback": disk_after_rollback["active_generation_id"],
        "disk_authority_after_rollback": disk_authority_after_rollback,
        "fresh_open_grb_generation_id": grb_fresh_open["active_generation_id"],
        "fresh_open_grb_via_subprocess": grb_fresh_open["via_public_serving_open"],
        "fresh_open_grb_subprocess_pid": grb_fresh_open["pid"],
        "fresh_open_after_restore_generation_id": canary_fresh_open["active_generation_id"],
        "fresh_open_canary_via_subprocess": canary_fresh_open["via_public_serving_open"],
        "fresh_open_canary_subprocess_pid": canary_fresh_open["pid"],
        "fresh_open_vector_is_new_resolution": (
            frozen_vector_id
            not in (
                grb_fresh_open["authority_vector_id"],
                canary_fresh_open["authority_vector_id"],
            )
        ),
        "fresh_open_via_public_api": True,
        "fresh_open_resolves_disk_not_frozen": (
            disk_authority_after_rollback == grant.grb_generation_id
            and grb_fresh_open["active_generation_id"] == grant.grb_generation_id
            and canary_fresh_open["active_generation_id"] == grant.canary_generation_id
            and grb_fresh_open["subprocess_is_fresh_process"]
            and canary_fresh_open["subprocess_is_fresh_process"]
        ),
        "pass": (
            frozen_generation == grant.canary_generation_id
            and still_frozen == grant.canary_generation_id
            and after_pointer["active_generation_id"] == grant.grb_generation_id
            and before_ids == after_ids
            and restored is not None
            and restored["active_generation_id"] == grant.canary_generation_id
            and disk_authority_after_rollback == grant.grb_generation_id
            and grb_fresh_open["active_generation_id"] == grant.grb_generation_id
            and canary_fresh_open["active_generation_id"] == grant.canary_generation_id
            and grb_fresh_open["subprocess_is_fresh_process"]
            and canary_fresh_open["subprocess_is_fresh_process"]
        ),
    }


def _verify_no_production_contact(
    env: dict[str, Any],
    *,
    production_chroma: Path | None,
    production_generation_root: Path | None,
) -> bool:
    """Prove rehearsal roots never equal configured production identity paths."""

    rehearsal_roots = {
        Path(env["chroma"]).expanduser().resolve(),
        Path(env["generations"]).expanduser().resolve(),
    }
    if production_chroma is not None and production_generation_root is not None:
        configured = {
            production_chroma.expanduser().resolve(),
            production_generation_root.expanduser().resolve(),
        }
        if not rehearsal_roots.isdisjoint(configured):
            raise RehearsalProductionIsolationError(
                "rehearsal roots overlap configured production markers"
            )
        return True
    try:
        from cg2_legacy_vector_attestation import _resolve_live_production_paths

        live_chroma, live_generations = _resolve_live_production_paths()
        configured = {
            live_chroma.expanduser().resolve(),
            live_generations.expanduser().resolve(),
        }
    except (OSError, TypeError, ValueError, KeyError) as exc:
        raise RehearsalProductionIsolationError(
            "production path resolution failed during rehearsal isolation check"
        ) from exc
    if not rehearsal_roots.isdisjoint(configured):
        raise RehearsalProductionIsolationError(
            "rehearsal roots overlap resolved production paths"
        )
    return True


def _exercise_cutover_crash_resume_controls(
    env: dict[str, Any],
) -> tuple[FirstCutoverGrant, FirstCutoverGrant, FirstCutoverGrant, Any, _OneLockOracle]:
    grant_fence = _make_cutover_grant(env, grant_id="d5-grant-fence-crash")
    with patch(
        "cg2_first_cutover.publish_canary_open_guard",
        side_effect=RuntimeError("simulated crash after fence"),
    ):
        try:
            _publish_cutover(env, grant_fence)
        except RuntimeError as exc:
            if "simulated crash after fence" not in str(exc):
                raise
    assert fence_path(env["generations"], env["owner_digest"]).exists()
    assert read_canary_open_guard(env["generations"], env["owner_digest"]) is None
    assert read_unqualified_pointer(env["generations"], env["owner_digest"]) is None

    grant_guard = _make_cutover_grant(env, grant_id="d5-grant-guard-crash")
    with patch(
        "cg2_first_cutover._publish_pointer_under_lock",
        side_effect=RuntimeError("simulated crash after guard"),
    ):
        try:
            _publish_cutover(
                env,
                grant_guard,
                prior_grant_id=grant_fence.grant_id,
            )
        except RuntimeError as exc:
            if "simulated crash after guard" not in str(exc):
                raise
    assert read_canary_open_guard(env["generations"], env["owner_digest"]) is not None
    assert read_unqualified_pointer(env["generations"], env["owner_digest"]) is None

    grant_cutover = _make_cutover_grant(env, grant_id="d5-grant-cutover-success")
    pointer_absent_before_first_cutover = (
        read_unqualified_pointer(env["generations"], env["owner_digest"]) is None
    )
    cutover_oracle = _OneLockOracle()
    with patch("cg2_first_cutover.source_flock", cutover_oracle):
        active = _publish_cutover(
            env,
            grant_cutover,
            prior_grant_id=grant_guard.grant_id,
        )
    pointer = active.pointer
    assert pointer.get("previous_generation_id") == grant_cutover.grb_generation_id
    assert pointer.get("active_generation_id") == grant_cutover.canary_generation_id
    assert read_unqualified_pointer(env["generations"], env["owner_digest"]) is not None
    return (
        grant_fence,
        grant_guard,
        grant_cutover,
        active,
        cutover_oracle,
        pointer_absent_before_first_cutover,
    )


def _complete_rollback_recovery_phase(
    env: dict[str, Any],
    grant_cutover: FirstCutoverGrant,
) -> dict[str, Any]:
    pre_restart_session = open_rehearsal_serving_session(env["cfg"])
    ordering_trace: list[str] = []
    env["source"].write_text("advanced-source-bytes-v2", encoding="utf-8")
    ordering_trace.append("source_advanced")
    pointer_before_rollback = dict(
        read_unqualified_pointer(env["generations"], env["owner_digest"]) or {}
    )
    rollback_oracle = _OneLockOracle()
    original_record = record_rollback_reconciliation_obligation
    original_publish = fg_pointer._publish_pointer_under_lock  # pylint: disable=protected-access

    def _track_record(*args, **kwargs):
        ordering_trace.append("reconciliation_obligation_durable")
        return original_record(*args, **kwargs)

    def _track_publish(*args, **kwargs):
        ordering_trace.append("rollback_pointer_publication")
        return original_publish(*args, **kwargs)

    with patch("file_generation_pointer.source_flock", rollback_oracle), patch(
        "source_reconciler.record_rollback_reconciliation_obligation",
        side_effect=_track_record,
    ), patch.object(
        fg_pointer,
        "_publish_pointer_under_lock",
        side_effect=_track_publish,
    ):
        rolled = _rollback_grb(
            env,
            grant_cutover,
            active_generation_id=grant_cutover.canary_generation_id,
        )
    pending_after_rollback = pending_owner_work(env["cfg"])
    reconciliation_hash_before_restart = _durable_reconciliation_hash(env["cfg"])
    fence_hash_before_restart, guard_hash_before_restart = _durable_fence_guard_hashes(env)
    parent_pid = os.getpid()
    parent_serving_repo_id = (
        id(pre_restart_session.serving_repo)
        if pre_restart_session.serving_repo is not None
        else None
    )
    pre_restart_session.close()
    restart_boundary = run_rehearsal_subprocess_restart_recovery(
        env["cfg"],
        owner_key=env["owner_key"],
        owner_digest=env["owner_digest"],
        chroma_dir=env["chroma"],
        expected_grb_generation_id=grant_cutover.grb_generation_id,
        parent_pid=parent_pid,
        parent_serving_repo_id=parent_serving_repo_id,
    )
    restart_boundary["session_closed_before_recovery"] = (
        pre_restart_session.is_closed() and parent_serving_repo_id is not None
    )
    reconciliation_hash_after_restart = _durable_reconciliation_hash(env["cfg"])
    fence_hash_after_restart, guard_hash_after_restart = _durable_fence_guard_hashes(env)
    pending_after_restart = restart_boundary["pending_after_restart"]
    reopened_state = {
        "mode": restart_boundary["reopened_authority_mode"],
        "generation_id": restart_boundary["reopened_active_generation_id"],
    }
    retention = restart_boundary["retention"]
    evidence_path = rollback_baseline_evidence_path(
        env["generations"], env["owner_digest"], grant_cutover.grb_generation_id
    )
    return {
        "pointer_before_rollback": pointer_before_rollback,
        "pointer_after_rollback": dict(rolled.pointer),
        "pending_after_rollback": bool(pending_after_rollback),
        "pending_after_restart": bool(pending_after_restart),
        "ordering_trace": ordering_trace,
        "reconciliation_hash_before_restart": reconciliation_hash_before_restart,
        "reconciliation_hash_after_restart": reconciliation_hash_after_restart,
        "fence_hash_before_restart": fence_hash_before_restart,
        "fence_hash_after_restart": fence_hash_after_restart,
        "guard_hash_before_restart": guard_hash_before_restart,
        "guard_hash_after_restart": guard_hash_after_restart,
        "restart_boundary": restart_boundary,
        "recovered_active_generation_id": restart_boundary["recovered_active_generation_id"],
        "reopened_state": reopened_state,
        "retention": retention,
        "retained_evidence_sha": _sha256_file(evidence_path),
        "rollback_oracle": rollback_oracle,
    }


def run_design_a_isolated_rehearsal(
    tmp_path: Path,
    *,
    production_chroma: Path | None = None,
    production_generation_root: Path | None = None,
) -> dict[str, Any]:
    """Hermetic Design A drill: D0→D1→cutover→freeze→rollback→recovery."""

    env = build_hermetic_design_a_environment(tmp_path)
    grant_fence, grant_guard, grant_cutover, active, cutover_oracle, pointer_absent_before_first_cutover = (
        _exercise_cutover_crash_resume_controls(env)
    )
    pointer = active.pointer
    freeze = _assert_frozen_generation_stable(env, grant_cutover)
    phase = _complete_rollback_recovery_phase(env, grant_cutover)

    second_cutover_grant = _make_cutover_grant(env, grant_id="d5-grant-guard-block")
    guard_blocks_second = False
    try:
        _publish_cutover(env, second_cutover_grant)
    except FirstCutoverError:
        guard_blocks_second = True

    no_production = _verify_no_production_contact(
        env,
        production_chroma=production_chroma,
        production_generation_root=production_generation_root,
    )
    rehearsal_roots = {
        str(env["chroma"].resolve()),
        str(env["generations"].resolve()),
    }
    rolled_pointer = phase["pointer_after_rollback"]
    recovered_generation_id = phase["recovered_active_generation_id"]
    reopened_state = phase["reopened_state"]

    return {
        "schema": DESIGN_A_REHEARSAL_SCHEMA,
        "architecture_sha": ARCHITECTURE_SHA,
        "execution_plan_sha": EXECUTION_PLAN_SHA,
        "implementation_sha": _git_sha(),
        "d0_candidate_digest": env["d0"]["candidate_sha256"],
        "d0_validation_digest": env["d0"]["validation_sha256"],
        "d0_ratification_digest": env["d0"]["ratification_sha256"],
        "ratified_query_context_digest": env["d0"]["ratified_query_context_sha256"],
        "live_query_context_digest": env["d0"]["live_query_context_sha256"],
        "grb_generation_id": grant_cutover.grb_generation_id,
        "grb_manifest_sha256": grant_cutover.grb_manifest_sha256,
        "canary_generation_id": grant_cutover.canary_generation_id,
        "canary_manifest_sha256": grant_cutover.canary_manifest_sha256,
        "retained_evidence_sha256": phase["retained_evidence_sha"],
        "pointer_before_rollback": phase["pointer_before_rollback"],
        "pointer_after_rollback": rolled_pointer,
        "first_pointer_cas_from_none": pointer_absent_before_first_cutover,
        "first_pointer_pre_publication_absent": pointer_absent_before_first_cutover,
        "first_pointer_previous_is_grb": pointer.get("previous_generation_id") == grant_cutover.grb_generation_id,
        "first_pointer_active_is_canary": pointer.get("active_generation_id") == grant_cutover.canary_generation_id,
        "fence_content_hash_before_restart": phase["fence_hash_before_restart"],
        "fence_content_hash_after_restart": phase["fence_hash_after_restart"],
        "guard_content_hash_before_restart": phase["guard_hash_before_restart"],
        "guard_content_hash_after_restart": phase["guard_hash_after_restart"],
        "reconciliation_state_hash_before_restart": phase["reconciliation_hash_before_restart"],
        "reconciliation_state_hash_after_restart": phase["reconciliation_hash_after_restart"],
        "reconciliation_ordering_trace": phase["ordering_trace"],
        "restart_boundary": phase["restart_boundary"],
        "retention_inventory": phase["retention"],
        "fresh_grant_fence_crash": grant_fence.grant_id,
        "fresh_grant_guard_crash": grant_guard.grant_id,
        "one_lock_cutover_oracle": {
            "acquisitions": cutover_oracle.acquisitions,
            "pass": len(cutover_oracle.acquisitions) == 1,
        },
        "one_lock_rollback_oracle": {
            "acquisitions": phase["rollback_oracle"].acquisitions,
            "pass": len(phase["rollback_oracle"].acquisitions) == 1,
        },
        "request_freeze": freeze,
        "reconciliation_pending_after_source_advance": phase["pending_after_rollback"],
        "reconciliation_pending_after_restart": phase["pending_after_restart"],
        "recovery_active_generation_id": recovered_generation_id,
        "recovery_matches_rollback": recovered_generation_id == grant_cutover.grb_generation_id,
        "reopened_authority_mode": reopened_state["mode"],
        "reopened_active_generation_id": reopened_state["generation_id"],
        "guard_blocks_second_first_cutover": guard_blocks_second,
        "physical_deletion_disabled": PHYSICAL_DELETION_DISABLED,
        "no_production_operations": no_production,
        "rehearsal_roots": sorted(rehearsal_roots),
    }


def measured_budgets() -> dict[str, Any]:
    from serving_authority import AuthorityResolutionRetryBudget
    from source_reconciler import ReconciliationBudget

    authority = AuthorityResolutionRetryBudget()
    reconciliation = ReconciliationBudget()
    return {
        "authority_resolution_retry_budget": {
            "max_attempts": authority.max_attempts,
            "max_elapsed_seconds": authority.max_elapsed,
        },
        "reconciliation": {
            "max_pending_owners": reconciliation.max_pending_owners,
            "max_reconciliation_staleness_seconds": reconciliation.max_reconciliation_staleness,
        },
        "chroma_version": PINNED_CHROMA_VERSION,
        "physical_deletion_disabled": PHYSICAL_DELETION_DISABLED,
        "note": "Latency and soak budgets ratified at gateway soak grant; not measured in isolated rehearsal",
    }


def _git_blob_sha(path: str) -> str:
    return subprocess.check_output(
        ["git", "rev-parse", f"HEAD:{path}"], text=True
    ).strip()


def external_review_record(
    *,
    reviewed_sha: str | None = None,
    reviewer_lane: str | None = None,
    verdict: str | None = None,
) -> dict[str, Any]:
    return {
        "gate_applicability": "d7_execute_closure_independent_review",
        "reason": (
            "Independent review of exact D7 closure tip required; "
            "D6 CORRECTIVE PASS does not substitute"
        ),
        "reviewed_sha": reviewed_sha,
        "reviewer_lane": reviewer_lane,
        "verdict": verdict,
        "bugbot_reviewed_sha": reviewed_sha,
    }


def run_legacy_gateway_rehearsal(tmp_path: Path) -> dict[str, Any]:
    chroma = tmp_path / "chroma"
    chroma.mkdir(parents=True, exist_ok=True)
    cfg = {
        "models": {
            "embed_model": "nomic-embed-text",
            "ollama_host": "http://localhost:11434",
            "rerank_model": "rerank",
        },
        "query": {"rerank": False, "recency_weight": 0.0, "top_k_candidates": 5},
        "index": {
            "chroma_dir": str(chroma),
            "generation_root": str(tmp_path / "file_generations"),
            "processed_log": str(tmp_path / "processed.json"),
        },
    }
    embedding = [0.2, 0.8, 0.1, 0.3, 0.0, 0.5, 0.4, 0.9]
    store = ChromaStore(str(chroma))
    store.add_unit(
        "unit-a",
        "alpha knowledge for rehearsal",
        embedding,
        {"id": "unit-a", "title": "alpha"},
    )
    store.add_unit(
        "unit-b",
        "bravo knowledge for rehearsal",
        [0.1] * 8,
        {"id": "unit-b", "title": "bravo"},
    )
    store.close()

    started = time.perf_counter()
    direct = open_chroma_for_read(str(chroma))
    try:
        direct_rows = direct.query_units(embedding, 3)
    finally:
        direct.close()
    with open_serving_index_repository(cfg) as repo:
        gateway_rows = repo.query_units(embedding, 3)
        serving_count = repo.serving_count_units()
        physical_count = repo.physical_count_units()
    elapsed_ms = (time.perf_counter() - started) * 1000.0
    direct_ids = [row["id"] for row in direct_rows]
    gateway_ids = [row["id"] for row in gateway_rows]
    return {
        "schema": REHEARSAL_SCHEMA,
        "legacy_global": True,
        "direct_ids": direct_ids,
        "gateway_ids": gateway_ids,
        "equivalence_pass": direct_ids == gateway_ids,
        "serving_units": serving_count,
        "physical_units": physical_count,
        "elapsed_ms": round(elapsed_ms, 2),
    }


def failure_matrix_evidence() -> dict[str, list[str]]:
    return {
        "authority_races": [
            "tests/test_serving_authority.py",
            "tests/test_serving_index_repository.py",
        ],
        "source_races": [
            "tests/test_source_freshness_promotion.py",
            "tests/test_source_reconciler.py",
        ],
        "lost_notification": [
            "tests/test_source_reconciler.py::test_discover_legacy_drift_when_source_changes",
        ],
        "mixed_mode": [
            "tests/test_mixed_mode_proof.py",
            "tests/test_file_generation_read_paths.py",
        ],
        "logical_accounting": [
            "tests/test_logical_accounting.py",
            "tests/test_doctor_logical_projection.py",
        ],
        "boundary_inventory": [
            "tests/test_file_generation_read_path_inventory.py",
            "tests/test_shadow_writer_coverage_scan.py",
        ],
        "crash_recovery_pointer": [
            "tests/test_file_generation_validate.py",
            "tests/test_file_generation_pointer.py",
        ],
        "retention_restart": [
            "tests/test_mixed_mode_proof.py::test_retention_survives_restart",
            "tests/test_mixed_mode_proof.py::test_grb_retained_across_design_a_lifecycle",
            "tests/test_file_generation_store.py",
        ],
        "design_a_rehearsal": [
            "tests/test_cg2_rehearsal.py::test_design_a_isolated_rehearsal",
        ],
        "request_freeze": [
            (
                "tests/test_serving_index_repository.py::"
                "test_frozen_generation_stays_stable_when_pointer_changes_mid_request"
            ),
        ],
    }


def shadow_comparison_status() -> dict[str, Any]:
    return {
        "shadow_ledger": "disabled",
        "comparison_run": False,
        "reason": (
            "Shadow Phase 0 default is disabled; isolated rehearsal uses copied "
            "corpus only.  Shadow divergence gate applies at separately granted soak."
        ),
    }


def collect_execute_evidence(
    *,
    execution_plan_sha: str | None = None,
    rehearsal_report: dict[str, Any] | None = None,
    mechanical_bundle: dict[str, Any] | None = None,
    tlc_closure_evidence: dict[str, Any] | None = None,
    external_review: dict[str, Any] | None = None,
    d6_accepted_tip: str | None = None,
) -> dict[str, Any]:
    subject_tip = _git_sha()
    plan_sha = execution_plan_sha or EXECUTION_PLAN_SHA
    chroma_version = chromadb.__version__
    formal_model_sha = _git_blob_sha("docs/plans/formal/cg2/CG2Authority.tla")
    property_map = build_property_map_report()
    return {
        "schema": "convmem/cg2-design-a-execute-evidence-v2",
        "execute_phase": "D7_closure",
        "branch": subprocess.check_output(
            ["git", "branch", "--show-current"], text=True
        ).strip(),
        "subject_tip_sha": subject_tip,
        "d6_accepted_tip_sha": d6_accepted_tip,
        "architecture_sha": ARCHITECTURE_SHA,
        "execution_plan_sha": plan_sha,
        "formal_model_sha": formal_model_sha,
        "chroma_version": chroma_version,
        "chroma_version_matches_pin": chroma_version == PINNED_CHROMA_VERSION,
        "property_map": property_map,
        "property_map_completeness": verify_property_map_completeness(),
        "budgets": measured_budgets(),
        "external_review": external_review or external_review_record(),
        "failure_matrix": failure_matrix_evidence(),
        "shadow": shadow_comparison_status(),
        "design_a_rehearsal": rehearsal_report,
        "mechanical_bundle": mechanical_bundle,
        "tlc_closure_evidence": tlc_closure_evidence,
        "production_activation_performed": False,
        "automatic_gc_performed": False,
        "production_d0_capture_performed": False,
        "production_d0_ratification_performed": False,
        "production_grb_build_performed": False,
        "production_g_canary_build_performed": False,
        "v8c_grant_issued": False,
        "no_production_operations": True,
    }

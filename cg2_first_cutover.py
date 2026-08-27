"""CG-2 Design A D3 — first-cutover structural gate and orchestration."""

from __future__ import annotations

import hashlib
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from cg2_cutover_guard import (
    build_canary_open_guard,
    publish_canary_open_guard,
    read_canary_open_guard,
    validate_canary_open_guard,
)
from cg2_legacy_vector_attestation import (
    ADMITTED_COLLECTIONS,
    D0AttestationError,
    KNOWN_MODEL_AND_VECTOR_V1,
    LEGACY_EXACT_VECTOR_UNKNOWN_MODEL_V1,
    derive_query_embedding_context,
    load_ratified_d0_chain,
    verify_d0_chain_for_grb_conversion,
)
from cg2_rollback_baseline import (
    RollbackBaselineError,
    rollback_baseline_evidence_path,
    validate_retained_rollback_baseline_evidence,
)
from file_generation_contract import canonical_source_path
from file_generation_pointer import (
    GenerationQualificationError,
    ManifestReference,
    QualifiedActivePointer,
    _publish_pointer_under_lock,
    _read_json,
    _reload_verified_caller_reference,
    load_manifest_reference,
    pointer_path,
    provision_generation_layout,
    read_unqualified_pointer,
)
from file_generation_store import FileGenerationStore
from file_generation_validate import run_cold_validation
from purge_locks import source_flock
from serving_authority import (
    OwnerAuthorityMode,
    build_legacy_fence,
    fence_path,
    publish_legacy_fence,
    resolve_frozen_authority_vector,
    validate_legacy_fence,
)
from source_observation import observe_source_hash
from source_reconciler import ReconciliationBudget, assert_reconciliation_fresh



class FirstCutoverError(RuntimeError):
    """First-cutover preflight or structural gate refused."""


@dataclass(frozen=True)
class FirstCutoverGrant:  # pylint: disable=too-many-instance-attributes
    """Ryan one-shot activation grant bound to exact G_rb and G_canary."""

    grant_id: str
    owner_digest: str
    ratification_id: str
    grb_generation_id: str
    grb_manifest_sha256: str
    grb_evidence_sha256: str
    canary_generation_id: str
    canary_manifest_sha256: str
    query_embedding_context_sha256: str


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _evidence_file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _validate_grb_proof_profile(evidence: Mapping[str, Any]) -> None:
    if evidence.get("proof_profile") != LEGACY_EXACT_VECTOR_UNKNOWN_MODEL_V1:
        raise FirstCutoverError(
            "G_rb proof profile must be LEGACY_EXACT_VECTOR_UNKNOWN_MODEL_V1"
        )


def _validate_canary_proof_profile(manifest: Mapping[str, Any]) -> None:
    annotations = dict(manifest.get("recorded_only_annotations") or {})
    if annotations.get("proof_profile") != KNOWN_MODEL_AND_VECTOR_V1:
        raise FirstCutoverError(
            "G_canary proof profile must be KNOWN_MODEL_AND_VECTOR_V1"
        )
    collections = dict(manifest.get("collections") or {})
    if set(collections) != set(ADMITTED_COLLECTIONS):
        raise FirstCutoverError(
            "G_canary must declare the exact ratified admitted collection set"
        )
    for collection_name in ADMITTED_COLLECTIONS:
        raw_spec = collections[collection_name]
        if not isinstance(raw_spec, Mapping):
            raise FirstCutoverError(
                f"G_canary collection {collection_name} is not an object"
            )
        spec = dict(raw_spec)
        model = str(spec.get("embedding_model") or "").strip()
        if not model:
            raise FirstCutoverError(
                f"G_canary collection {collection_name} lacks known embedding model"
            )
        dimension = int(spec.get("embedding_dimension") or 0)
        if dimension <= 0:
            raise FirstCutoverError(
                f"G_canary collection {collection_name} has invalid embedding dimension"
            )
        rows = dict(spec.get("rows") or {})
        if not rows:
            raise FirstCutoverError(
                f"G_canary collection {collection_name} lacks writer-produced rows"
            )
        for physical_id, raw_row in rows.items():
            row = dict(raw_row)
            row_model = str(row.get("embedding_model") or "").strip()
            if row_model != model:
                raise FirstCutoverError(
                    f"G_canary row {collection_name}/{physical_id} model identity mismatch"
                )
            row_dimension = int(row.get("embedding_dimension") or 0)
            if row_dimension != dimension:
                raise FirstCutoverError(
                    f"G_canary row {collection_name}/{physical_id} dimension mismatch"
                )
            for field in ("document_hash", "embedding_hash"):
                if not str(row.get(field) or "").strip():
                    raise FirstCutoverError(
                        f"G_canary row {collection_name}/{physical_id} lacks vector identity"
                    )
            immutable = dict(row.get("immutable_metadata") or {})
            if not immutable:
                raise FirstCutoverError(
                    f"G_canary row {collection_name}/{physical_id} "
                    "lacks writer-produced provenance"
                )


def _fresh_qualify(
    chroma_dir: str | Path, reference: ManifestReference
) -> None:
    try:
        result = run_cold_validation(
            chroma_dir,
            reference.path,
            expected_manifest_sha256=reference.file_sha256,
        )
    except RuntimeError as exc:
        raise FirstCutoverError(
            f"fresh-process qualification failed: {exc}"
        ) from exc
    if result.get("valid") is not True:
        raise FirstCutoverError("fresh-process qualification refused")


def _lock_held_reread_d0_legacy(
    cfg: Mapping[str, Any],
    store: FileGenerationStore,
    chain,
) -> dict[str, Any]:
    from cg2_legacy_vector_attestation import (  # pylint: disable=import-outside-toplevel
        _admitted_dimension,
        _aggregate_roots,
        _bind_accepted_source_hash,
        _collection_bindings,
        _ordered_leaves,
        _read_admitted_rows,
        _sorted_utf8,
    )

    candidate = chain.candidate
    owner_key = str(candidate["owner_key"])
    owner_digest_value = chain.owner_digest
    canonical_source = str(candidate["canonical_source_path"])
    accepted_source_hash = str(candidate["accepted_source_hash"])
    bound_hash = _bind_accepted_source_hash(
        cfg,
        canonical_source=canonical_source,
        claimed=accepted_source_hash,
    )
    rows = _read_admitted_rows(
        store.raw_store,
        owner_digest_value=owner_digest_value,
        owner_key=owner_key,
        canonical_source=canonical_source,
    )
    dimension = _admitted_dimension(rows)
    leaves = _ordered_leaves(rows)
    chroma_dir = str(store.chroma_dir)
    collections = [
        _collection_bindings(chroma_dir, name, dimension, leaves)
        for name in _sorted_utf8({row["collection_name"] for row in rows})
    ]
    snapshot_root, vector_root = _aggregate_roots(collections)
    if snapshot_root != chain.ratification.accepted_legacy_snapshot_root:
        raise FirstCutoverError(
            "lock-held LEGACY reread snapshot root drifted from ratified D0 chain"
        )
    if vector_root != chain.ratification.accepted_legacy_vector_root:
        raise FirstCutoverError(
            "lock-held LEGACY reread vector root drifted from ratified D0 chain"
        )
    return {
        "accepted_source_hash": bound_hash,
        "accepted_legacy_snapshot_root": snapshot_root,
        "accepted_legacy_vector_root": vector_root,
        "embedding_dimension": dimension,
    }





def _lock_held_revalidate_grant_material(
    generation_root: str | Path,
    canary_manifest_reference: ManifestReference,
    *,
    grant: FirstCutoverGrant,
    chroma_dir: str | Path,
    canonical_source: str,
) -> tuple[ManifestReference, dict[str, Any], ManifestReference]:
    """Reread grant-bound G_canary, G_rb evidence, and source under source_flock."""

    try:
        canary_ref = _reload_verified_caller_reference(
            generation_root, canary_manifest_reference
        )
    except GenerationQualificationError as exc:
        raise FirstCutoverError(
            f"lock-held G_canary manifest reload refused: {exc}"
        ) from exc

    if canary_ref.file_sha256 != grant.canary_manifest_sha256:
        raise FirstCutoverError("lock-held G_canary manifest SHA drift")
    if str(canary_ref.manifest.get("generation_id") or "") != grant.canary_generation_id:
        raise FirstCutoverError("lock-held G_canary generation identity drift")
    _validate_canary_proof_profile(canary_ref.manifest)
    _fresh_qualify(chroma_dir, canary_ref)

    evidence_path = rollback_baseline_evidence_path(
        generation_root, grant.owner_digest, grant.grb_generation_id
    )
    if not evidence_path.is_file():
        raise FirstCutoverError("lock-held G_rb evidence missing")
    if _evidence_file_sha256(evidence_path) != grant.grb_evidence_sha256:
        raise FirstCutoverError("lock-held G_rb evidence SHA drift")
    try:
        evidence = validate_retained_rollback_baseline_evidence(
            generation_root,
            owner_digest_value=grant.owner_digest,
            generation_id=grant.grb_generation_id,
            expected_manifest_sha256=grant.grb_manifest_sha256,
        )
    except RollbackBaselineError as exc:
        raise FirstCutoverError(
            f"lock-held G_rb evidence revalidation refused: {exc}"
        ) from exc
    _validate_grb_proof_profile(evidence)

    grb_ref = load_manifest_reference(
        generation_root,
        manifest_filename=str(evidence["manifest_filename"]),
        expected_sha256=grant.grb_manifest_sha256,
    )
    if str(grb_ref.manifest.get("generation_id") or "") != grant.grb_generation_id:
        raise FirstCutoverError("lock-held G_rb generation identity drift")

    live_source = observe_source_hash(canonical_source)
    if live_source != str(canary_ref.manifest.get("source_hash") or ""):
        raise FirstCutoverError("lock-held source hash drift")

    return canary_ref, evidence, grb_ref


def _require_grant_bound_guard(
    existing_guard: Mapping[str, Any],
    *,
    owner_key: str,
    grant: FirstCutoverGrant,
) -> None:
    validate_canary_open_guard(existing_guard)
    expected_guard = build_canary_open_guard(
        owner_key=owner_key,
        canary_generation_id=grant.canary_generation_id,
        rollback_baseline_generation_id=grant.grb_generation_id,
        published_at=str(existing_guard["published_at"]),
    )
    if dict(existing_guard) != expected_guard:
        raise FirstCutoverError(
            "lock-held guard does not match grant-bound expectation"
        )


def _preflight_authority_state(
    generation_root: str | Path,
    grant: FirstCutoverGrant,
    cfg: Mapping[str, Any],
    *,
    resume: bool,
    prior_grant_id: str | None,
    guard: Mapping[str, Any] | None,
) -> None:
    fence_exists = fence_path(generation_root, grant.owner_digest).exists()
    pointer = read_unqualified_pointer(generation_root, grant.owner_digest)
    if resume:
        if prior_grant_id is None or prior_grant_id == grant.grant_id:
            raise FirstCutoverError(
                "fresh-grant resume requires prior_grant_id distinct from grant_id"
            )
        if not fence_exists:
            raise FirstCutoverError("resume requires existing fence")
        if pointer is not None:
            raise FirstCutoverError("resume requires pointer absence")
        vector = resolve_frozen_authority_vector(
            cfg, owner_digests={grant.owner_digest}
        )
        state = vector.by_owner.get(grant.owner_digest)
        if state is None or state.mode != OwnerAuthorityMode.FENCED_NO_POINTER:
            raise FirstCutoverError(
                "resume requires FENCED_NO_POINTER authority"
            )
        return
    if prior_grant_id is not None:
        raise FirstCutoverError("prior_grant_id is only valid for resume")
    if fence_exists:
        raise FirstCutoverError("initial cutover requires fence absence")
    if pointer is not None:
        raise FirstCutoverError("initial cutover requires pointer absence")
    if guard is not None:
        raise FirstCutoverError("initial cutover requires guard absence")
    vector = resolve_frozen_authority_vector(cfg, owner_digests={grant.owner_digest})
    state = vector.by_owner.get(grant.owner_digest)
    if state is None or state.mode != OwnerAuthorityMode.LEGACY:
        raise FirstCutoverError("initial cutover requires LEGACY authority")


def _preflight_first_cutover(
    generation_root: str | Path,
    canary_ref: ManifestReference,
    *,
    grant: FirstCutoverGrant,
    chroma_dir: str | Path,
    cfg: Mapping[str, Any],
    prior_grant_id: str | None,
    resume: bool,
) -> tuple[ManifestReference, dict[str, Any], dict[str, Any]]:
    if not str(grant.grant_id or "").strip():
        raise FirstCutoverError("grant_id is required")
    if grant.grb_generation_id == grant.canary_generation_id:
        raise FirstCutoverError("G_rb and G_canary must be distinct generation IDs")

    evidence = validate_retained_rollback_baseline_evidence(
        generation_root,
        owner_digest_value=grant.owner_digest,
        generation_id=grant.grb_generation_id,
        expected_manifest_sha256=grant.grb_manifest_sha256,
    )
    _validate_grb_proof_profile(evidence)
    evidence_path = rollback_baseline_evidence_path(
        generation_root, grant.owner_digest, grant.grb_generation_id
    )
    if _evidence_file_sha256(evidence_path) != grant.grb_evidence_sha256:
        raise FirstCutoverError("retained G_rb evidence SHA does not match grant")

    grb_ref = load_manifest_reference(
        generation_root,
        manifest_filename=str(evidence["manifest_filename"]),
        expected_sha256=grant.grb_manifest_sha256,
    )
    canary_manifest = dict(canary_ref.manifest)
    if str(canary_manifest.get("generation_id") or "") != grant.canary_generation_id:
        raise FirstCutoverError("canary manifest generation_id does not match grant")
    if canary_ref.file_sha256 != grant.canary_manifest_sha256:
        raise FirstCutoverError("canary manifest SHA does not match grant")
    _validate_canary_proof_profile(canary_manifest)

    chain = load_ratified_d0_chain(
        generation_root,
        owner_digest=grant.owner_digest,
        ratification_id=grant.ratification_id,
    )
    dimension = int(evidence.get("embedding_provenance", {}).get("knowledge_units", {}).get("embedding_dimension") or 0)
    if dimension <= 0:
        for spec in dict(evidence.get("embedding_provenance") or {}).values():
            dimension = int(dict(spec).get("embedding_dimension") or 0)
            if dimension > 0:
                break
    if dimension <= 0:
        raise FirstCutoverError("cannot derive admitted dimension from G_rb evidence")
    _context, live_query_sha = derive_query_embedding_context(
        cfg, admitted_dimension=dimension
    )
    if live_query_sha != grant.query_embedding_context_sha256:
        raise FirstCutoverError("live query embedding context does not match grant")
    try:
        verify_d0_chain_for_grb_conversion(
            chain, live_query_context_sha256=live_query_sha
        )
    except D0AttestationError as exc:
        raise FirstCutoverError(str(exc)) from exc
    if chain.ratification.query_embedding_context_sha256 != grant.query_embedding_context_sha256:
        raise FirstCutoverError("ratified query context does not match grant")

    owner_key = str(grb_ref.manifest["owner_key"])
    if str(canary_manifest.get("owner_key") or "") != owner_key:
        raise FirstCutoverError("G_rb and G_canary owner_key mismatch")
    if str(canary_manifest.get("owner_digest") or "") != grant.owner_digest:
        raise FirstCutoverError("G_canary owner_digest mismatch")
    canonical = str(grb_ref.manifest["canonical_source_path"])
    if str(canary_manifest.get("canonical_source_path") or "") != canonical:
        raise FirstCutoverError("G_rb and G_canary canonical source mismatch")

    _fresh_qualify(chroma_dir, grb_ref)
    _fresh_qualify(chroma_dir, canary_ref)

    guard = read_canary_open_guard(generation_root, grant.owner_digest)
    _preflight_authority_state(
        generation_root,
        grant,
        cfg,
        resume=resume,
        prior_grant_id=prior_grant_id,
        guard=guard,
    )

    assert_reconciliation_fresh(cfg, budget=ReconciliationBudget())
    live_source = observe_source_hash(canonical_source_path(canary_manifest["canonical_source_path"]))
    if live_source != str(canary_manifest.get("source_hash") or ""):
        raise FirstCutoverError(
            "current source hash does not match G_canary manifest source_hash"
        )

    if resume and guard is not None:
        _require_grant_bound_guard(
            guard, owner_key=owner_key, grant=grant
        )

    return grb_ref, evidence, chain


def publish_first_cutover_active_pointer(
    generation_root: str | Path,
    canary_manifest_reference: ManifestReference,
    *,
    grant: FirstCutoverGrant,
    chroma_dir: str | Path,
    cfg: Mapping[str, Any],
    backend_fingerprint: str,
    prior_grant_id: str | None = None,
    published_at: str | None = None,
) -> QualifiedActivePointer:
    """Structural first-cutover gate: one lock from LEGACY reread through pointer."""

    generation_root = Path(generation_root)
    provision_generation_layout(generation_root)
    owner_key = str(canary_manifest_reference.manifest["owner_key"])
    canonical_source = canonical_source_path(
        str(canary_manifest_reference.manifest["canonical_source_path"])
    )
    owner_digest_value = str(canary_manifest_reference.manifest["owner_digest"])
    pointer_file = pointer_path(generation_root, owner_digest_value)
    fence_file = fence_path(generation_root, owner_digest_value)

    resume = fence_file.exists()
    _, _evidence, chain = _preflight_first_cutover(
        generation_root,
        canary_manifest_reference,
        grant=grant,
        chroma_dir=chroma_dir,
        cfg=cfg,
        prior_grant_id=prior_grant_id,
        resume=resume,
    )

    published_fence_at = published_at or _utc_now()
    with source_flock(dict(cfg), canonical_source):
        if resume:
            vector = resolve_frozen_authority_vector(
                cfg, owner_digests={owner_digest_value}
            )
            state = vector.by_owner.get(owner_digest_value)
            if state is None or state.mode != OwnerAuthorityMode.FENCED_NO_POINTER:
                raise FirstCutoverError(
                    "lock-held resume requires FENCED_NO_POINTER authority"
                )
            fence = _read_json(fence_file)
            validate_legacy_fence(fence)
            expected_fence = build_legacy_fence(owner_key, str(fence["published_at"]))
            if fence != expected_fence:
                raise FirstCutoverError("existing fence bytes are not grant-bound")
        else:
            vector = resolve_frozen_authority_vector(
                cfg, owner_digests={owner_digest_value}
            )
            state = vector.by_owner.get(owner_digest_value)
            if state is None or state.mode != OwnerAuthorityMode.LEGACY:
                raise FirstCutoverError("lock-held cutover requires LEGACY authority")

        chain = load_ratified_d0_chain(
            generation_root,
            owner_digest=grant.owner_digest,
            ratification_id=grant.ratification_id,
        )
        dimension = int(
            dict(_evidence.get("embedding_provenance") or {})
            .get("knowledge_units", {})
            .get("embedding_dimension")
            or 0
        )
        if dimension <= 0:
            raise FirstCutoverError("G_rb evidence lacks embedding dimension")
        _context, live_query_sha = derive_query_embedding_context(
            cfg, admitted_dimension=dimension
        )
        if live_query_sha != grant.query_embedding_context_sha256:
            raise FirstCutoverError("lock-held query context drift")
        verify_d0_chain_for_grb_conversion(
            chain, live_query_context_sha256=live_query_sha
        )

        with FileGenerationStore(str(chroma_dir), active_generations=dict) as store:
            _lock_held_reread_d0_legacy(cfg, store, chain)

        canary_manifest_reference, _evidence, _grb_locked = _lock_held_revalidate_grant_material(
            generation_root,
            canary_manifest_reference,
            grant=grant,
            chroma_dir=chroma_dir,
            canonical_source=canonical_source,
        )

        current_pointer = read_unqualified_pointer(generation_root, owner_digest_value)
        if current_pointer is not None:
            raise FirstCutoverError("lock-held cutover requires pointer absence")

        if not resume:
            publish_legacy_fence(
                generation_root, owner_key, published_fence_at
            )
        if not fence_file.exists():
            raise FirstCutoverError("fence must exist before guard/pointer publication")

        existing_guard = read_canary_open_guard(generation_root, owner_digest_value)
        if existing_guard is None:
            publish_canary_open_guard(
                generation_root,
                owner_key=owner_key,
                canary_generation_id=grant.canary_generation_id,
                rollback_baseline_generation_id=grant.grb_generation_id,
                published_at=published_at or _utc_now(),
            )
        else:
            _require_grant_bound_guard(
                existing_guard,
                owner_key=owner_key,
                grant=grant,
            )

        if read_canary_open_guard(generation_root, owner_digest_value) is None:
            raise FirstCutoverError("open canary guard must exist before pointer")

        return _publish_pointer_under_lock(
            generation_root,
            canary_manifest_reference,
            path=pointer_file,
            chroma_dir=chroma_dir,
            previous_generation_id=grant.grb_generation_id,
            backend_fingerprint=backend_fingerprint,
            published_at=published_at or _utc_now(),
        )

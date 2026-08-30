"""Durable immutable manifests and per-owner active pointers for CG-1.

Reading a pointer never creates serving authority.  Only successful publication
or successful exact recovery returns :class:`QualifiedActivePointer`.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable, Mapping
from copy import deepcopy
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from types import MappingProxyType
from typing import Any

from atomic_files import atomic_write_json
from file_generation_contract import (
    LAYOUT_SCHEMA,
    build_active_pointer,
    canonical_hash,
    canonical_source_path,
    owner_digest,
    validate_active_pointer,
    validate_generation_manifest,
    validate_published_manifest,
    is_retained_legacy_reference_manifest,
    is_failed_convert_v1_target_id,
    refuse_failed_convert_v1_target_id,
)
from purge_locks import source_flock


class GenerationPublicationError(RuntimeError):
    """A manifest/pointer cannot be safely published or qualified."""


class StaleGenerationError(GenerationPublicationError):
    """The candidate was built against a generation that is no longer active."""


class StaleSourceError(GenerationPublicationError):
    """The canonical source bytes no longer match the candidate manifest."""


class GenerationQualificationError(GenerationPublicationError):
    """The manifest or its exact Chroma generation failed qualification."""


class GenerationHealthState(str, Enum):
    HEALTHY = "HEALTHY"
    DEGRADED_SAFE = "DEGRADED-SAFE"
    UNVERIFIED_FAIL = "UNVERIFIED / FAIL"


@dataclass(frozen=True)
class ManifestReference:
    path: Path
    manifest: dict[str, Any]
    file_sha256: str


_QUALIFIED_POINTER_SEAL = object()


@dataclass(frozen=True, init=False)
class QualifiedActivePointer:
    """Process-local proof that exact validation and durable publish succeeded."""

    path: Path
    pointer: Mapping[str, Any]
    manifest: Mapping[str, Any]
    recovered: bool = False
    _seal: object | None = field(repr=False, compare=False, default=None)

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Reject normal construction outside the authority-minting path."""
        del args, kwargs
        raise TypeError(
            "QualifiedActivePointer is sealed; use publish or recovery authority"
        )


def _make_qualified_active_pointer(
    *,
    path: Path,
    pointer: Mapping[str, Any],
    manifest: Mapping[str, Any],
    recovered: bool,
) -> QualifiedActivePointer:
    """Mint a serving token only after the local authority sequence succeeds."""
    frozen_pointer = _freeze_authority_value(deepcopy(dict(pointer)))
    frozen_manifest = _freeze_authority_value(deepcopy(dict(manifest)))
    if not isinstance(frozen_pointer, Mapping) or not isinstance(frozen_manifest, Mapping):
        raise GenerationQualificationError("qualified authority payload is not a mapping")
    token = object.__new__(QualifiedActivePointer)
    object.__setattr__(token, "path", path)
    object.__setattr__(token, "pointer", frozen_pointer)
    object.__setattr__(token, "manifest", frozen_manifest)
    object.__setattr__(token, "recovered", recovered)
    object.__setattr__(token, "_seal", _QUALIFIED_POINTER_SEAL)
    return token


def _freeze_authority_value(value: Any) -> Any:
    """Recursively detach and freeze authority payloads held by serving tokens."""
    if isinstance(value, Mapping):
        return MappingProxyType(
            {key: _freeze_authority_value(nested) for key, nested in value.items()}
        )
    if isinstance(value, list):
        return tuple(_freeze_authority_value(item) for item in value)
    if isinstance(value, tuple):
        return tuple(_freeze_authority_value(item) for item in value)
    if isinstance(value, set):
        return frozenset(_freeze_authority_value(item) for item in value)
    return value


@dataclass(frozen=True)
class GenerationHealth:
    state: GenerationHealthState
    owner_key: str
    generation_id: str | None
    reason: str
    may_serve: bool


def _require_sealed_authority(qualified: QualifiedActivePointer) -> None:
    # Exact-type check is deliberate: isinstance would let a subclass carry a
    # forged seal through the authority boundary. pylint's unidiomatic-typecheck
    # fits the general case but not this subclass-proofing guard.
    if (
        type(qualified) is not QualifiedActivePointer  # pylint: disable=unidiomatic-typecheck
        or getattr(qualified, "_seal", None) is not _QUALIFIED_POINTER_SEAL
    ):
        raise GenerationQualificationError(
            "serving state requires a module-sealed qualified active pointer"
        )


def healthy_state(qualified: QualifiedActivePointer) -> GenerationHealth:
    _require_sealed_authority(qualified)
    return GenerationHealth(
        GenerationHealthState.HEALTHY,
        str(qualified.pointer["owner_key"]),
        str(qualified.pointer["active_generation_id"]),
        "active pointer and exact generation are durability-qualified",
        True,
    )


def degraded_safe_state(
    previous: QualifiedActivePointer, reason: str
) -> GenerationHealth:
    _require_sealed_authority(previous)
    return GenerationHealth(
        GenerationHealthState.DEGRADED_SAFE,
        str(previous.pointer["owner_key"]),
        str(previous.pointer["active_generation_id"]),
        reason,
        True,
    )


def unverified_state(
    owner_key: str, reason: str, *, visible_generation_id: str | None = None
) -> GenerationHealth:
    return GenerationHealth(
        GenerationHealthState.UNVERIFIED_FAIL,
        owner_key,
        visible_generation_id,
        reason,
        False,
    )


def manifest_dir(generation_root: str | Path) -> Path:
    return Path(generation_root) / "manifests"


def active_dir(generation_root: str | Path) -> Path:
    return Path(generation_root) / "active"


def manifest_path(
    generation_root: str | Path, owner_digest_value: str, generation_id: str
) -> Path:
    return manifest_dir(generation_root) / f"{owner_digest_value}--{generation_id}.json"


def pointer_path(generation_root: str | Path, owner_digest_value: str) -> Path:
    return active_dir(generation_root) / f"{owner_digest_value}.json"


def provision_generation_layout(generation_root: str | Path) -> Path:
    """Provision and durability-publish the two fixed layout directories."""

    root = Path(generation_root)
    root.mkdir(parents=True, exist_ok=True)
    manifest_dir(root).mkdir(exist_ok=True)
    active_dir(root).mkdir(exist_ok=True)
    marker = root / "layout.json"
    payload = {
        "schema": LAYOUT_SCHEMA,
        "directories": ["active", "manifests"],
    }
    payload["layout_payload_hash"] = canonical_hash(payload)
    if marker.exists():
        current = _read_json(marker)
        if current != payload:
            raise GenerationPublicationError("generation layout marker mismatch")
        return marker
    atomic_write_json(marker, payload)
    return marker


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise GenerationQualificationError(f"cannot read {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise GenerationQualificationError(f"{path} is not a JSON object")
    return value


def _file_sha256(path: Path) -> str:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError as exc:
        raise GenerationQualificationError(f"cannot hash {path}: {exc}") from exc


def publish_manifest(
    generation_root: str | Path, manifest: Mapping[str, Any]
) -> ManifestReference:
    """Durably publish an immutable manifest, idempotently for identical bytes."""

    validate_published_manifest(manifest)
    provision_generation_layout(generation_root)
    path = manifest_path(
        generation_root, str(manifest["owner_digest"]), str(manifest["generation_id"])
    )
    obj = dict(manifest)
    if path.exists():
        current = _read_json(path)
        if current != obj:
            raise GenerationPublicationError(f"immutable manifest collision at {path}")
    else:
        atomic_write_json(path, obj)
    reread = _read_json(path)
    validate_published_manifest(reread)
    if reread != obj:
        raise GenerationQualificationError("published manifest reread mismatch")
    return ManifestReference(path=path, manifest=reread, file_sha256=_file_sha256(path))


def load_manifest_reference(
    generation_root: str | Path,
    *,
    manifest_filename: str,
    expected_sha256: str,
) -> ManifestReference:
    if Path(manifest_filename).name != manifest_filename:
        raise GenerationQualificationError("manifest filename escapes manifest root")
    path = manifest_dir(generation_root) / manifest_filename
    actual = _file_sha256(path)
    if actual != expected_sha256:
        raise GenerationQualificationError("pointer-to-manifest file hash mismatch")
    manifest = _read_json(path)
    validate_published_manifest(manifest)
    return ManifestReference(path=path, manifest=manifest, file_sha256=actual)


def _reload_verified_caller_reference(
    generation_root: str | Path, manifest_reference: ManifestReference
) -> ManifestReference:
    """Bind caller-held manifest identity to its canonical persisted bytes."""
    validate_published_manifest(manifest_reference.manifest)
    expected_path = manifest_path(
        generation_root,
        str(manifest_reference.manifest["owner_digest"]),
        str(manifest_reference.manifest["generation_id"]),
    )
    if manifest_reference.path.name != expected_path.name:
        raise GenerationQualificationError(
            "manifest reference filename does not match caller-held owner/generation"
        )
    if manifest_reference.path.resolve() != expected_path.resolve():
        raise GenerationQualificationError(
            "manifest reference path does not match canonical generation path"
        )
    fresh_ref = load_manifest_reference(
        generation_root,
        manifest_filename=expected_path.name,
        expected_sha256=manifest_reference.file_sha256,
    )
    if dict(manifest_reference.manifest) != fresh_ref.manifest:
        raise GenerationQualificationError(
            "caller-held manifest does not match persisted hash-bound manifest"
        )
    return fresh_ref


def read_unqualified_pointer(
    generation_root: str | Path, owner_digest_value: str
) -> dict[str, Any] | None:
    """Read bytes only; the result is intentionally not serving-qualified."""

    path = pointer_path(generation_root, owner_digest_value)
    if not path.exists():
        return None
    pointer = _read_json(path)
    validate_active_pointer(pointer)
    if pointer["owner_digest"] != owner_digest_value:
        raise GenerationQualificationError("pointer stored under wrong owner digest")
    return pointer


def _require_true(result: Any, message: str) -> None:
    if result is False:
        raise GenerationQualificationError(message)


def _run_fresh_process_qualification(
    chroma_dir: str | Path, manifest_reference: ManifestReference
) -> None:
    """Require the module-owned cold validator for exact manifest bytes.

    This is deliberately private so pointer mechanics tests can replace the
    expensive process boundary.  Public authority-minting APIs never accept a
    caller-supplied substitute: durable promotion and recovery must both
    validate the exact, hash-bound manifest in a fresh interpreter.
    """

    # Keep the import local: file_generation_validate imports the store, while
    # this module owns only pointer authority and must not create an import
    # cycle at module initialization.
    from file_generation_validate import run_cold_validation

    try:
        result = run_cold_validation(
            chroma_dir,
            manifest_reference.path,
            expected_manifest_sha256=manifest_reference.file_sha256,
        )
    except Exception as exc:
        raise GenerationQualificationError(
            "fresh-process exact generation qualification failed"
        ) from exc
    if result.get("valid") is not True:
        raise GenerationQualificationError(
            "fresh-process exact generation qualification refused"
        )
    if result.get("owner_digest") != manifest_reference.manifest["owner_digest"]:
        raise GenerationQualificationError(
            "fresh-process qualification owner mismatch"
        )
    if result.get("generation_id") != manifest_reference.manifest["generation_id"]:
        raise GenerationQualificationError(
            "fresh-process qualification generation mismatch"
        )
    if result.get("manifest_sha256") != manifest_reference.file_sha256:
        raise GenerationQualificationError(
            "fresh-process qualification manifest hash mismatch"
        )


def _qualify_pointer(
    generation_root: str | Path,
    pointer: Mapping[str, Any],
    *,
    chroma_dir: str | Path,
    candidate_revalidator: Callable[[Mapping[str, Any]], Any] | None,
) -> ManifestReference:
    ref = load_manifest_reference(
        generation_root,
        manifest_filename=str(pointer["manifest_filename"]),
        expected_sha256=str(pointer["manifest_sha256"]),
    )
    manifest = ref.manifest
    if manifest["owner_key"] != pointer["owner_key"]:
        raise GenerationQualificationError("pointer/manifest owner mismatch")
    if manifest["generation_id"] != pointer["active_generation_id"]:
        raise GenerationQualificationError("pointer/manifest generation mismatch")
    if manifest["source_hash"] != pointer["source_hash"]:
        raise GenerationQualificationError("pointer/manifest source mismatch")
    if candidate_revalidator is not None:
        _require_true(
            candidate_revalidator(manifest),
            "source/config/model/exclusion revalidation failed",
        )
    # Caller/source/config drift is rechecked before the final process-boundary
    # exact Chroma qualification.  A revalidator cannot mutate immutable rows
    # after the last qualification and still mint serving authority.
    _run_fresh_process_qualification(chroma_dir, ref)
    return ref


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _publish_pointer_under_lock(
    generation_root: str | Path,
    manifest_reference: ManifestReference,
    *,
    path: Path,
    chroma_dir: str | Path,
    previous_generation_id: str | None,
    backend_fingerprint: str,
    candidate_revalidator: Callable[[Mapping[str, Any]], Any] | None = None,
    published_at: str | None = None,
) -> QualifiedActivePointer:
    """Qualify and write one active pointer while the owner source lock is held."""

    fresh_ref = _reload_verified_caller_reference(
        generation_root, manifest_reference
    )
    pointer = build_active_pointer(
        manifest=fresh_ref.manifest,
        manifest_filename=fresh_ref.path.name,
        manifest_sha256=fresh_ref.file_sha256,
        previous_generation_id=previous_generation_id,
        backend_fingerprint=backend_fingerprint,
        published_at=published_at or _utc_now(),
    )
    _qualify_pointer(
        generation_root,
        pointer,
        chroma_dir=chroma_dir,
        candidate_revalidator=candidate_revalidator,
    )
    atomic_write_json(path, pointer)
    return _make_qualified_active_pointer(
        path=path,
        pointer=pointer,
        manifest=fresh_ref.manifest,
        recovered=False,
    )


def publish_active_pointer(
    generation_root: str | Path,
    manifest_reference: ManifestReference,
    *,
    chroma_dir: str | Path,
    cfg: Mapping[str, Any],
    expected_active_generation_id: str,
    backend_fingerprint: str,
    candidate_revalidator: Callable[[Mapping[str, Any]], Any] | None = None,
    published_at: str | None = None,
) -> QualifiedActivePointer:
    """Ordinary forward publication: CAS current active and record durable lineage.

    ``PostPublicationDurabilityError`` is deliberately not caught.  Visible
    bytes after that exception remain unqualified; rereading them is not
    recovery.
    """

    if expected_active_generation_id is None:
        raise GenerationPublicationError(
            "ordinary forward publication requires non-None expected_active_generation_id"
        )
    if not str(expected_active_generation_id).strip():
        raise GenerationPublicationError(
            "ordinary forward publication requires non-empty expected_active_generation_id"
        )

    verified_ref = _reload_verified_caller_reference(
        generation_root, manifest_reference
    )
    manifest = verified_ref.manifest
    canonical_source = canonical_source_path(manifest["canonical_source_path"])
    owner_digest_value = str(manifest["owner_digest"])
    path = pointer_path(generation_root, owner_digest_value)
    with source_flock(dict(cfg), canonical_source):
        from cg2_cutover_guard import read_canary_open_guard

        if read_canary_open_guard(generation_root, owner_digest_value) is not None:
            raise GenerationPublicationError(
                "ordinary forward publication refused while first-canary guard is open"
            )

        fresh_ref = _reload_verified_caller_reference(
            generation_root, manifest_reference
        )
        current = read_unqualified_pointer(generation_root, owner_digest_value)
        if current is None:
            raise GenerationPublicationError(
                "ordinary forward publication cannot create the first active pointer"
            )
        current_generation = str(current["active_generation_id"])
        if current_generation != expected_active_generation_id:
            raise StaleGenerationError(
                "active generation changed while candidate was queued: "
                f"expected {expected_active_generation_id!r}, got {current_generation!r}"
            )
        from source_observation import observe_source_hash

        observed_hash = observe_source_hash(canonical_source)
        if observed_hash != fresh_ref.manifest["source_hash"]:
            raise StaleSourceError(
                "canonical source bytes changed since candidate build: "
                f"manifest={fresh_ref.manifest['source_hash']!r} "
                f"current={observed_hash!r}"
            )
        return _publish_pointer_under_lock(
            generation_root,
            manifest_reference,
            path=path,
            chroma_dir=chroma_dir,
            previous_generation_id=current_generation,
            backend_fingerprint=backend_fingerprint,
            candidate_revalidator=candidate_revalidator,
            published_at=published_at,
        )


def publish_first_cutover_active_pointer(
    generation_root: str | Path,
    canary_manifest_reference: ManifestReference,
    *,
    rollback_baseline_generation_id: str,
    chroma_dir: str | Path,
    cfg: Mapping[str, Any],
    backend_fingerprint: str,
    candidate_revalidator: Callable[[Mapping[str, Any]], Any] | None = None,
    published_at: str | None = None,
) -> QualifiedActivePointer:
    """Pointer-layer first-cutover capability: CAS absence, previous=G_rb."""

    if not str(rollback_baseline_generation_id or "").strip():
        raise GenerationPublicationError(
            "first-cutover publication requires rollback_baseline_generation_id"
        )

    verified_ref = _reload_verified_caller_reference(
        generation_root, canary_manifest_reference
    )
    manifest = verified_ref.manifest
    canonical_source = canonical_source_path(manifest["canonical_source_path"])
    owner_digest_value = str(manifest["owner_digest"])
    path = pointer_path(generation_root, owner_digest_value)
    with source_flock(dict(cfg), canonical_source):
        current = read_unqualified_pointer(generation_root, owner_digest_value)
        if current is not None:
            raise StaleGenerationError(
                "first-cutover publication requires pointer absence: "
                f"found active {current['active_generation_id']!r}"
            )
        return _publish_pointer_under_lock(
            generation_root,
            canary_manifest_reference,
            path=path,
            chroma_dir=chroma_dir,
            previous_generation_id=str(rollback_baseline_generation_id),
            backend_fingerprint=backend_fingerprint,
            candidate_revalidator=candidate_revalidator,
            published_at=published_at,
        )


def rollback_active_pointer(  # pylint: disable=too-many-arguments
    generation_root: str | Path,
    retained_manifest_reference: ManifestReference,
    *,
    chroma_dir: str | Path,
    cfg: Mapping[str, Any],
    expected_active_generation_id: str,
    backend_fingerprint: str,
    candidate_revalidator: Callable[[Mapping[str, Any]], Any] | None = None,
    published_at: str | None = None,
    grb_ratification_id: str | None = None,
    grb_evidence_sha256: str | None = None,
) -> QualifiedActivePointer:
    """Rollback to a retained target under one owner lock with durable reconciliation."""

    if expected_active_generation_id is None:
        raise GenerationPublicationError(
            "rollback publication requires non-None expected_active_generation_id"
        )
    if not str(expected_active_generation_id).strip():
        raise GenerationPublicationError(
            "rollback publication requires non-empty expected_active_generation_id"
        )

    verified_ref = _reload_verified_caller_reference(
        generation_root, retained_manifest_reference
    )
    manifest = verified_ref.manifest
    canonical_source = canonical_source_path(manifest["canonical_source_path"])
    owner_key = str(manifest["owner_key"])
    owner_digest_value = str(manifest["owner_digest"])
    path = pointer_path(generation_root, owner_digest_value)
    with source_flock(dict(cfg), canonical_source):
        fence_before, guard_before, fence_file = _rollback_fence_and_guard_snapshot(
            generation_root, owner_digest_value
        )
        current_generation = _rollback_validate_cas_and_lineage(
            generation_root,
            owner_digest_value,
            expected_active_generation_id=expected_active_generation_id,
            retained_manifest_reference=retained_manifest_reference,
            chroma_dir=chroma_dir,
            cfg=cfg,
            grb_authority=(grb_ratification_id, grb_evidence_sha256),
            candidate_revalidator=candidate_revalidator,
        )
        fresh_ref = _reload_verified_caller_reference(
            generation_root, retained_manifest_reference
        )
        _rollback_record_reconciliation_if_needed(
            cfg,
            owner_key=owner_key,
            canonical_source=canonical_source,
            target_source_hash=str(fresh_ref.manifest.get("source_hash") or ""),
        )
        published = _publish_pointer_under_lock(
            generation_root,
            retained_manifest_reference,
            path=path,
            chroma_dir=chroma_dir,
            previous_generation_id=current_generation,
            backend_fingerprint=backend_fingerprint,
            candidate_revalidator=None,
            published_at=published_at,
        )
        _rollback_assert_authority_artifacts_preserved(
            generation_root,
            owner_digest_value,
            fence_file=fence_file,
            fence_before=fence_before,
            guard_before=guard_before,
        )
        return published


def _rollback_fence_and_guard_snapshot(
    generation_root: str | Path,
    owner_digest_value: str,
) -> tuple[dict[str, Any], dict[str, Any] | None, Path]:
    from cg2_cutover_guard import read_canary_open_guard
    from serving_authority import fence_path, validate_legacy_fence

    fence_file = fence_path(generation_root, owner_digest_value)
    if not fence_file.exists():
        raise GenerationPublicationError(
            "rollback publication requires a monotonic legacy fence"
        )
    fence_before = _read_json(fence_file)
    validate_legacy_fence(fence_before)
    guard_before = read_canary_open_guard(generation_root, owner_digest_value)
    return fence_before, guard_before, fence_file


def _rollback_validate_cas_and_lineage(
    generation_root: str | Path,
    owner_digest_value: str,
    *,
    expected_active_generation_id: str,
    retained_manifest_reference: ManifestReference,
    chroma_dir: str | Path,
    cfg: Mapping[str, Any],
    grb_authority: tuple[str | None, str | None] | None,
    candidate_revalidator: Callable[[Mapping[str, Any]], Any] | None = None,
) -> str:
    current = read_unqualified_pointer(generation_root, owner_digest_value)
    if current is None:
        raise StaleGenerationError("rollback publication requires an existing pointer")
    current_generation = str(current["active_generation_id"])
    if current_generation != expected_active_generation_id:
        raise StaleGenerationError(
            "rollback CAS mismatch: "
            f"expected {expected_active_generation_id!r}, got {current_generation!r}"
        )
    durable_previous = current.get("previous_generation_id")
    if durable_previous is None or not str(durable_previous).strip():
        raise GenerationPublicationError(
            "rollback publication requires durable previous_generation_id"
        )
    fresh_ref = _reload_verified_caller_reference(
        generation_root, retained_manifest_reference
    )
    target_generation_id = str(fresh_ref.manifest["generation_id"])
    if target_generation_id != str(durable_previous):
        raise GenerationPublicationError(
            "rollback target must equal pointer durable previous_generation_id: "
            f"target={target_generation_id!r} previous={durable_previous!r}"
        )
    _run_fresh_process_qualification(chroma_dir, fresh_ref)
    if candidate_revalidator is not None:
        _require_true(
            candidate_revalidator(fresh_ref.manifest),
            "source/config/model/exclusion revalidation failed",
        )
    if _is_grb_rollback_target(generation_root, fresh_ref.manifest):
        grb_ratification_id, grb_evidence_sha256 = grb_authority or (None, None)
        _validate_grb_rollback_authority(
            generation_root,
            fresh_ref,
            cfg=cfg,
            grb_ratification_id=grb_ratification_id,
            grb_evidence_sha256=grb_evidence_sha256,
        )
    return current_generation


def _rollback_record_reconciliation_if_needed(
    cfg: Mapping[str, Any],
    *,
    owner_key: str,
    canonical_source: str,
    target_source_hash: str,
) -> None:
    from source_observation import SourceObservationError, observe_source_hash
    from source_reconciler import (
        RollbackReconciliationError,
        record_rollback_reconciliation_obligation,
    )

    try:
        observed_source_hash = observe_source_hash(canonical_source)
    except SourceObservationError:
        observed_source_hash = None
    if observed_source_hash == target_source_hash:
        return
    source_reason = (
        "generational_source_missing"
        if observed_source_hash is None
        else "generational_source_hash_mismatch"
    )
    try:
        record_rollback_reconciliation_obligation(
            cfg,
            owner_key=owner_key,
            canonical_path=canonical_source,
            target_source_hash=target_source_hash,
            observed_source_hash=observed_source_hash,
            source_reason=source_reason,
        )
    except RollbackReconciliationError as exc:
        raise GenerationPublicationError(str(exc)) from exc


def _rollback_assert_authority_artifacts_preserved(
    generation_root: str | Path,
    owner_digest_value: str,
    *,
    fence_file: Path,
    fence_before: Mapping[str, Any],
    guard_before: Mapping[str, Any] | None,
) -> None:
    from cg2_cutover_guard import read_canary_open_guard
    from serving_authority import validate_legacy_fence

    fence_after = _read_json(fence_file)
    validate_legacy_fence(fence_after)
    if fence_after != fence_before:
        raise GenerationPublicationError(
            "rollback publication must preserve monotonic fence bytes"
        )
    guard_after = read_canary_open_guard(generation_root, owner_digest_value)
    if guard_before is None:
        if guard_after is not None:
            raise GenerationPublicationError(
                "rollback publication must not create a first-canary guard"
            )
        return
    if guard_after is None or dict(guard_after) != dict(guard_before):
        raise GenerationPublicationError(
            "rollback publication must preserve open first-canary guard bytes"
        )


def _manifest_proof_profile(manifest: Mapping[str, Any]) -> str | None:
    annotations = dict(manifest.get("recorded_only_annotations") or {})
    profile = annotations.get("proof_profile")
    return str(profile) if profile else None


def _is_grb_rollback_target(
    generation_root: str | Path,
    manifest: Mapping[str, Any],
) -> bool:
    profile = _manifest_proof_profile(manifest)
    from cg2_legacy_vector_attestation import (
        KNOWN_MODEL_AND_VECTOR_V1,
        LEGACY_EXACT_VECTOR_UNKNOWN_MODEL_V1,
    )

    if profile == KNOWN_MODEL_AND_VECTOR_V1:
        return False
    if profile == LEGACY_EXACT_VECTOR_UNKNOWN_MODEL_V1:
        return True
    from file_generation_contract import is_retained_legacy_reference_manifest  # pylint: disable=import-outside-toplevel
    if is_retained_legacy_reference_manifest(manifest):
        return True
    from cg2_rollback_baseline import (  # pylint: disable=import-outside-toplevel
        RollbackBaselineError,
        rollback_baseline_evidence_path,
        validate_retained_rollback_baseline_evidence,
        validate_retained_rollback_baseline_evidence_v2,
    )

    owner_digest_value = str(manifest["owner_digest"])
    generation_id = str(manifest["generation_id"])
    evidence_path = rollback_baseline_evidence_path(
        generation_root, owner_digest_value, generation_id
    )
    if not evidence_path.is_file():
        return False
    try:
        if is_retained_legacy_reference_manifest(manifest):
            evidence = validate_retained_rollback_baseline_evidence_v2(
                generation_root,
                owner_digest_value=owner_digest_value,
                generation_id=generation_id,
                expected_manifest_sha256=None,
            )
        else:
            evidence = validate_retained_rollback_baseline_evidence(
                generation_root,
                owner_digest_value=owner_digest_value,
                generation_id=generation_id,
                expected_manifest_sha256=None,
            )
    except RollbackBaselineError:
        return False
    return evidence.get("proof_profile") == LEGACY_EXACT_VECTOR_UNKNOWN_MODEL_V1


def _validate_grb_rollback_authority(
    generation_root: str | Path,
    fresh_ref: ManifestReference,
    *,
    cfg: Mapping[str, Any],
    grb_ratification_id: str | None,
    grb_evidence_sha256: str | None,
) -> None:
    from cg2_legacy_vector_attestation import (  # pylint: disable=import-outside-toplevel
        D0AttestationError,
        derive_query_embedding_context,
        load_ratified_d0_chain,
        verify_d0_chain_for_grb_conversion,
    )
    from cg2_rollback_baseline import (  # pylint: disable=import-outside-toplevel
        ROLLBACK_BASELINE_EVIDENCE_V2_SCHEMA,
        RollbackBaselineError,
        rollback_baseline_evidence_path,
        validate_retained_rollback_baseline_evidence,
        validate_retained_rollback_baseline_evidence_v2,
    )

    if not str(grb_ratification_id or "").strip():
        raise GenerationPublicationError(
            "G_rb rollback requires grb_ratification_id"
        )
    owner_digest_value = str(fresh_ref.manifest["owner_digest"])
    generation_id = str(fresh_ref.manifest["generation_id"])
    refuse_failed_convert_v1_target_id(generation_id)
    evidence_path = rollback_baseline_evidence_path(
        generation_root, owner_digest_value, generation_id
    )
    if not evidence_path.is_file():
        raise GenerationPublicationError("G_rb rollback requires retained baseline evidence")
    if grb_evidence_sha256 is not None:
        actual_sha = hashlib.sha256(evidence_path.read_bytes()).hexdigest()
        if actual_sha != grb_evidence_sha256:
            raise GenerationPublicationError("G_rb retained evidence SHA mismatch")
    try:
        if is_retained_legacy_reference_manifest(fresh_ref.manifest):
            evidence = validate_retained_rollback_baseline_evidence_v2(
                generation_root,
                owner_digest_value=owner_digest_value,
                generation_id=generation_id,
                expected_manifest_sha256=fresh_ref.file_sha256,
            )
        else:
            evidence = validate_retained_rollback_baseline_evidence(
                generation_root,
                owner_digest_value=owner_digest_value,
                generation_id=generation_id,
                expected_manifest_sha256=fresh_ref.file_sha256,
            )
    except RollbackBaselineError as exc:
        raise GenerationPublicationError(str(exc)) from exc
    dimension = next(
        (
            int(dict(spec).get("embedding_dimension") or 0)
            for spec in dict(evidence.get("embedding_provenance") or {}).values()
            if int(dict(spec).get("embedding_dimension") or 0) > 0
        ),
        int(
            dict(dict(evidence.get("embedding_provenance") or {}).get("knowledge_units") or {})
            .get("embedding_dimension")
            or 0
        ),
    )
    if dimension <= 0:
        raise GenerationPublicationError(
            "G_rb evidence lacks embedding dimension for query-context binding"
        )
    try:
        chain = load_ratified_d0_chain(
            generation_root,
            owner_digest=owner_digest_value,
            ratification_id=str(grb_ratification_id),
        )
        _, live_query_sha = derive_query_embedding_context(
            cfg, admitted_dimension=dimension
        )
        verify_d0_chain_for_grb_conversion(
            chain, live_query_context_sha256=live_query_sha
        )
    except D0AttestationError as exc:
        raise GenerationPublicationError(str(exc)) from exc


def recover_active_pointer(
    generation_root: str | Path,
    owner_key: str,
    *,
    chroma_dir: str | Path,
    cfg: Mapping[str, Any],
    recovery_revalidator: Callable[[Mapping[str, Any]], Any] | None = None,
) -> QualifiedActivePointer:
    """Validate visible complete authority and durably republish exact bytes.

    Recovery never chooses the "most complete" generation.  It accepts only the
    one named by the structurally valid visible pointer and republishes that
    exact payload while holding the same owner's source lock.
    """

    digest = owner_digest(owner_key)
    canonical_source = owner_key.removeprefix("source:")
    path = pointer_path(generation_root, digest)
    with source_flock(dict(cfg), canonical_source):
        pointer = read_unqualified_pointer(generation_root, digest)
        if pointer is None:
            raise GenerationQualificationError("owner has no visible active pointer")
        ref = _qualify_pointer(
            generation_root,
            pointer,
            chroma_dir=chroma_dir,
            candidate_revalidator=recovery_revalidator,
        )
        # Publishing the exact payload is the durability qualification.  A
        # second PostPublicationDurabilityError remains FAIL and propagates.
        atomic_write_json(path, pointer)
        return _make_qualified_active_pointer(
            path=path,
            pointer=dict(pointer),
            manifest=ref.manifest,
            recovered=True,
        )

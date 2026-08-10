"""Durable immutable manifests and per-owner active pointers for CG-1.

Reading a pointer never creates serving authority.  Only successful publication
or successful exact recovery returns :class:`QualifiedActivePointer`.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
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
)
from purge_locks import source_flock


class GenerationPublicationError(RuntimeError):
    """A manifest/pointer cannot be safely published or qualified."""


class StaleGenerationError(GenerationPublicationError):
    """The candidate was built against a generation that is no longer active."""


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


@dataclass(frozen=True)
class QualifiedActivePointer:
    """Process-local proof that exact validation and durable publish succeeded."""

    path: Path
    pointer: dict[str, Any]
    manifest: dict[str, Any]
    recovered: bool = False


@dataclass(frozen=True)
class GenerationHealth:
    state: GenerationHealthState
    owner_key: str
    generation_id: str | None
    reason: str
    may_serve: bool


def healthy_state(qualified: QualifiedActivePointer) -> GenerationHealth:
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

    validate_generation_manifest(manifest)
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
    validate_generation_manifest(reread)
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
    validate_generation_manifest(manifest)
    return ManifestReference(path=path, manifest=manifest, file_sha256=actual)


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


def _qualify_pointer(
    generation_root: str | Path,
    pointer: Mapping[str, Any],
    *,
    exact_generation_validator: Callable[[Mapping[str, Any]], Any],
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
    _require_true(
        exact_generation_validator(manifest),
        "manifest expected Chroma set did not validate exactly",
    )
    if candidate_revalidator is not None:
        _require_true(
            candidate_revalidator(manifest),
            "source/config/model/exclusion revalidation failed",
        )
    return ref


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def publish_active_pointer(
    generation_root: str | Path,
    manifest_reference: ManifestReference,
    *,
    cfg: Mapping[str, Any],
    expected_previous_generation_id: str | None,
    backend_fingerprint: str,
    exact_generation_validator: Callable[[Mapping[str, Any]], Any],
    candidate_revalidator: Callable[[Mapping[str, Any]], Any] | None = None,
    published_at: str | None = None,
) -> QualifiedActivePointer:
    """Qualify and durably promote one owner under its existing source lock.

    ``PostPublicationDurabilityError`` is deliberately not caught.  Visible
    bytes after that exception remain unqualified; rereading them is not
    recovery.
    """

    manifest = manifest_reference.manifest
    validate_generation_manifest(manifest)
    canonical_source = canonical_source_path(manifest["canonical_source_path"])
    path = pointer_path(generation_root, str(manifest["owner_digest"]))
    with source_flock(dict(cfg), canonical_source):
        current = read_unqualified_pointer(
            generation_root, str(manifest["owner_digest"])
        )
        current_generation = (
            None if current is None else str(current["active_generation_id"])
        )
        if current_generation != expected_previous_generation_id:
            raise StaleGenerationError(
                "active generation changed while candidate was queued: "
                f"expected {expected_previous_generation_id!r}, got {current_generation!r}"
            )
        # Re-hash the exact immutable manifest here so a stale caller-held
        # reference cannot promote bytes that changed after publication.
        fresh_ref = load_manifest_reference(
            generation_root,
            manifest_filename=manifest_reference.path.name,
            expected_sha256=manifest_reference.file_sha256,
        )
        pointer = build_active_pointer(
            manifest=fresh_ref.manifest,
            manifest_filename=fresh_ref.path.name,
            manifest_sha256=fresh_ref.file_sha256,
            previous_generation_id=expected_previous_generation_id,
            backend_fingerprint=backend_fingerprint,
            published_at=published_at or _utc_now(),
        )
        _qualify_pointer(
            generation_root,
            pointer,
            exact_generation_validator=exact_generation_validator,
            candidate_revalidator=candidate_revalidator,
        )
        atomic_write_json(path, pointer)
        return QualifiedActivePointer(
            path=path,
            pointer=pointer,
            manifest=fresh_ref.manifest,
            recovered=False,
        )


def recover_active_pointer(
    generation_root: str | Path,
    owner_key: str,
    *,
    cfg: Mapping[str, Any],
    exact_generation_validator: Callable[[Mapping[str, Any]], Any],
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
            exact_generation_validator=exact_generation_validator,
            candidate_revalidator=recovery_revalidator,
        )
        # Publishing the exact payload is the durability qualification.  A
        # second PostPublicationDurabilityError remains FAIL and propagates.
        atomic_write_json(path, pointer)
        return QualifiedActivePointer(
            path=path,
            pointer=dict(pointer),
            manifest=ref.manifest,
            recovered=True,
        )

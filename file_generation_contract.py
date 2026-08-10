"""Hermetic contracts for file-derived committed generations (CG-1).

This module is deliberately not wired into production ingest or retrieval.  It
contains deterministic identities and self-validating schemas shared by the
temporary-store proof.
"""

from __future__ import annotations

import copy
import hashlib
import json
import math
from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path
from typing import Any

MANIFEST_SCHEMA = "convmem/file-generation-manifest-v1"
POINTER_SCHEMA = "convmem/file-active-generation-pointer-v1"
LAYOUT_SCHEMA = "convmem/file-generation-layout-v1"
GENERATION_SCOPE = "file-derived"
PHYSICAL_ID_PREFIX = "fg1_"


class GenerationContractError(ValueError):
    """A generation artifact violates its deterministic contract."""


def canonical_source_path(path: str | Path) -> str:
    """Return the source identity used by ``source_flock`` and owner keys.

    ``resolve(strict=False)`` deliberately collapses ``~``, relative paths,
    existing symlinks, and lexical ``..`` aliases without requiring the final
    source to continue existing during recovery.
    """

    raw = str(path).strip()
    if not raw:
        raise GenerationContractError("source path must not be empty")
    return str(Path(raw).expanduser().resolve(strict=False))


def ownership_key(path: str | Path) -> str:
    return f"source:{canonical_source_path(path)}"


def owner_digest(key: str) -> str:
    if not key.startswith("source:") or not key.removeprefix("source:"):
        raise GenerationContractError("owner key must be source:<canonical-path>")
    return hashlib.sha256(key.encode("utf-8")).hexdigest()


def _reject_nonfinite(value: Any) -> None:
    if isinstance(value, float) and not math.isfinite(value):
        raise GenerationContractError("non-finite floats are not canonical JSON")
    if isinstance(value, Mapping):
        for key, child in value.items():
            if not isinstance(key, str):
                raise GenerationContractError(
                    "canonical JSON object keys must be strings"
                )
            _reject_nonfinite(child)
    elif isinstance(value, (list, tuple)):
        for child in value:
            _reject_nonfinite(child)


def canonical_bytes(value: Any) -> bytes:
    """Return the sole JSON representation used by CG-1 hashes."""

    _reject_nonfinite(value)
    try:
        return json.dumps(
            value,
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise GenerationContractError(f"value is not canonical JSON: {exc}") from exc


def canonical_hash(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def _pre_dedupe_row(row: Mapping[str, Any]) -> dict[str, Any]:
    """Normalize a pre-dedupe row without allowing physical identity in its hash."""

    normalized = copy.deepcopy(dict(row))
    if "physical_id" in normalized:
        normalized.pop("physical_id")
    metadata = normalized.get("metadata")
    if isinstance(metadata, dict):
        # metadata.id becomes a Chroma-resolved physical address after the
        # generation is known.  logical_id remains and therefore stays hashed.
        metadata.pop("physical_id", None)
        metadata.pop("id", None)
    return normalized


def candidate_bundle_hash(
    units: Sequence[Mapping[str, Any]],
    summaries: Sequence[Mapping[str, Any]],
) -> str:
    """Hash the full, ordered, pre-dedupe candidate bundle.

    The accepted/deduped set is intentionally not an input.  Physical identity
    is assigned only after this hash and the generation id exist.
    """

    return canonical_hash(
        {
            "schema": "convmem/file-generation-candidate-bundle-v1",
            "units": [_pre_dedupe_row(row) for row in units],
            "summaries": [_pre_dedupe_row(row) for row in summaries],
        }
    )


def make_generation_id(
    *,
    owner_digest: str,
    source_hash: str,
    pipeline_fingerprint: str,
    candidate_bundle_hash: str,
) -> str:
    fields = (owner_digest, source_hash, pipeline_fingerprint, candidate_bundle_hash)
    if any(not isinstance(field, str) or not field for field in fields):
        raise GenerationContractError(
            "generation identity fields must be non-empty strings"
        )
    return hashlib.sha256("\0".join(fields).encode("utf-8")).hexdigest()


def generation_id(**kwargs: str) -> str:
    """Compatibility spelling used by the CG-1 execution brief."""

    return make_generation_id(**kwargs)


def make_physical_id(collection_name: str, generation_id: str, logical_id: str) -> str:
    if not collection_name or not generation_id or not logical_id:
        raise GenerationContractError("physical identity fields must be non-empty")
    digest = hashlib.sha256(
        ("file-generation-v1" + collection_name + generation_id + logical_id).encode(
            "utf-8"
        )
    ).hexdigest()
    return f"{PHYSICAL_ID_PREFIX}{digest}"


def physical_id(collection_name: str, generation_id: str, logical_id: str) -> str:
    return make_physical_id(collection_name, generation_id, logical_id)


def build_logical_to_physical_map(
    collection_name: str, generation_id: str, logical_ids: Iterable[str]
) -> dict[str, str]:
    result: dict[str, str] = {}
    for logical_id in logical_ids:
        if logical_id in result:
            raise GenerationContractError(
                f"duplicate logical id in {collection_name}: {logical_id}"
            )
        result[logical_id] = make_physical_id(
            collection_name, generation_id, logical_id
        )
    return result


def logical_to_physical_map(
    collection_name: str, generation_id: str, logical_ids: Iterable[str]
) -> dict[str, str]:
    return build_logical_to_physical_map(collection_name, generation_id, logical_ids)


def _with_payload_hash(payload: Mapping[str, Any], field: str) -> dict[str, Any]:
    result = copy.deepcopy(dict(payload))
    result.pop(field, None)
    result[field] = canonical_hash(result)
    return result


def validate_payload_hash(payload: Mapping[str, Any], field: str) -> None:
    expected = payload.get(field)
    if not isinstance(expected, str) or len(expected) != 64:
        raise GenerationContractError(f"missing or invalid {field}")
    unhashed = copy.deepcopy(dict(payload))
    unhashed.pop(field, None)
    actual = canonical_hash(unhashed)
    if actual != expected:
        raise GenerationContractError(f"{field} mismatch: {actual} != {expected}")


def build_generation_manifest(
    *,
    owner_key: str,
    generation_id: str,
    canonical_source: str,
    source_hash: str,
    candidate_bundle_hash: str,
    fingerprints: Mapping[str, str],
    collections: Mapping[str, Mapping[str, Any]],
    recorded_only_annotations: Mapping[str, Any] | None = None,
    suppression_outcomes: Sequence[Mapping[str, Any]] = (),
    known_projection_loss_risks: Sequence[str] = (),
) -> dict[str, Any]:
    """Build a self-hashed immutable candidate manifest.

    ``collections`` carries exact enforced identity rows and the
    logical-to-physical maps.  Mutable refinement/linking annotations live only
    in ``recorded_only_annotations`` and are never compared by row validators.
    """

    expected_owner = ownership_key(canonical_source)
    if owner_key != expected_owner:
        raise GenerationContractError("owner key does not match canonical source")
    manifest = {
        "schema": MANIFEST_SCHEMA,
        "generation_scope": GENERATION_SCOPE,
        "owner_key": owner_key,
        "owner_digest": owner_digest(owner_key),
        "generation_id": generation_id,
        "canonical_source_path": canonical_source_path(canonical_source),
        "source_hash": source_hash,
        "candidate_bundle_hash": candidate_bundle_hash,
        "fingerprints": copy.deepcopy(dict(fingerprints)),
        "collections": copy.deepcopy(dict(collections)),
        "recorded_only_annotations": copy.deepcopy(
            dict(recorded_only_annotations or {})
        ),
        "suppression_outcomes": copy.deepcopy(list(suppression_outcomes)),
        "self_source_cross_logical_suppression_count": sum(
            1
            for outcome in suppression_outcomes
            if outcome.get("same_owner")
            and outcome.get("suppressed_logical_id")
            != outcome.get("matched_logical_id")
        ),
        "known_projection_loss_risks": list(known_projection_loss_risks),
    }
    return _with_payload_hash(manifest, "manifest_payload_hash")


def validate_generation_manifest(manifest: Mapping[str, Any]) -> None:
    if manifest.get("schema") != MANIFEST_SCHEMA:
        raise GenerationContractError("unsupported generation manifest schema")
    if manifest.get("generation_scope") != GENERATION_SCOPE:
        raise GenerationContractError("manifest is not file-derived")
    canonical = canonical_source_path(str(manifest.get("canonical_source_path", "")))
    if manifest.get("owner_key") != ownership_key(canonical):
        raise GenerationContractError("manifest owner/source mismatch")
    if manifest.get("owner_digest") != owner_digest(str(manifest["owner_key"])):
        raise GenerationContractError("manifest owner digest mismatch")
    if not manifest.get("generation_id") or not isinstance(
        manifest.get("collections"), dict
    ):
        raise GenerationContractError("manifest lacks generation identity/collections")
    _validate_manifest_collections(
        manifest["collections"], generation_id=str(manifest["generation_id"])
    )
    validate_payload_hash(manifest, "manifest_payload_hash")


_COLLECTION_SPEC_FIELDS = {
    "collection_uuid",
    "configuration",
    "embedding_model",
    "embedding_dimension",
    "logical_to_physical",
    "rows",
}
_ROW_IDENTITY_FIELDS = {
    "logical_id",
    "document_hash",
    "embedding_hash",
    "embedding_dimension",
    "embedding_model",
    "immutable_metadata",
}


def _validate_manifest_collections(
    collections: Mapping[str, Any], *, generation_id: str
) -> None:
    """Validate the enforced identity half of a manifest.

    Mutable Chroma annotations are intentionally absent.  They may be recorded
    by the manifest at top level, but exact-generation validation compares only
    this collection identity set.
    """

    for collection_name, raw_spec in collections.items():
        if not isinstance(collection_name, str) or not collection_name:
            raise GenerationContractError("collection names must be non-empty strings")
        if not isinstance(raw_spec, Mapping):
            raise GenerationContractError(
                f"collection {collection_name} is not an object"
            )
        extra_or_missing = set(raw_spec) ^ _COLLECTION_SPEC_FIELDS
        if extra_or_missing:
            raise GenerationContractError(
                f"collection {collection_name} fields mismatch: {sorted(extra_or_missing)}"
            )
        spec = dict(raw_spec)
        if not isinstance(spec["collection_uuid"], str) or not spec["collection_uuid"]:
            raise GenerationContractError(f"collection {collection_name} lacks UUID")
        if not isinstance(spec["configuration"], Mapping):
            raise GenerationContractError(
                f"collection {collection_name} configuration is not an object"
            )
        if not isinstance(spec["embedding_model"], str) or not spec["embedding_model"]:
            raise GenerationContractError(
                f"collection {collection_name} lacks embedding model"
            )
        dimension = spec["embedding_dimension"]
        if (
            not isinstance(dimension, int)
            or isinstance(dimension, bool)
            or dimension < 1
        ):
            raise GenerationContractError(
                f"collection {collection_name} has invalid embedding dimension"
            )
        logical_map = spec["logical_to_physical"]
        rows = spec["rows"]
        if not isinstance(logical_map, Mapping) or not isinstance(rows, Mapping):
            raise GenerationContractError(
                f"collection {collection_name} identity maps must be objects"
            )
        if set(logical_map.values()) != set(rows):
            raise GenerationContractError(
                f"collection {collection_name} logical/physical expected sets differ"
            )
        if len(set(logical_map.values())) != len(logical_map):
            raise GenerationContractError(
                f"collection {collection_name} maps multiple logical ids to one physical id"
            )
        for logical_id, physical_id_value in logical_map.items():
            if not isinstance(logical_id, str) or not logical_id:
                raise GenerationContractError("logical ids must be non-empty strings")
            expected_physical = make_physical_id(
                collection_name, generation_id, logical_id
            )
            if physical_id_value != expected_physical:
                raise GenerationContractError(
                    f"physical id does not derive from {collection_name}/{logical_id}"
                )
            row = rows[physical_id_value]
            if not isinstance(row, Mapping) or set(row) != _ROW_IDENTITY_FIELDS:
                raise GenerationContractError(
                    f"row identity fields mismatch for {physical_id_value}"
                )
            if row["logical_id"] != logical_id:
                raise GenerationContractError(
                    f"row logical id mismatch for {physical_id_value}"
                )
            if row["embedding_model"] != spec["embedding_model"]:
                raise GenerationContractError(
                    f"row embedding model mismatch for {physical_id_value}"
                )
            if row["embedding_dimension"] != dimension:
                raise GenerationContractError(
                    f"row embedding dimension mismatch for {physical_id_value}"
                )
            if not isinstance(row["immutable_metadata"], Mapping):
                raise GenerationContractError(
                    f"row immutable metadata is not an object for {physical_id_value}"
                )
            for field in ("document_hash", "embedding_hash"):
                if not isinstance(row[field], str) or not row[field]:
                    raise GenerationContractError(
                        f"row {field} missing for {physical_id_value}"
                    )


def build_active_pointer(
    *,
    manifest: Mapping[str, Any],
    manifest_filename: str,
    manifest_sha256: str,
    previous_generation_id: str | None,
    backend_fingerprint: str,
    published_at: str,
) -> dict[str, Any]:
    validate_generation_manifest(manifest)
    pointer = {
        "schema": POINTER_SCHEMA,
        "owner_key": manifest["owner_key"],
        "owner_digest": manifest["owner_digest"],
        "active_generation_id": manifest["generation_id"],
        "manifest_filename": manifest_filename,
        "manifest_sha256": manifest_sha256,
        "source_hash": manifest["source_hash"],
        "previous_generation_id": previous_generation_id,
        "backend_fingerprint": backend_fingerprint,
        "published_at": published_at,
    }
    return _with_payload_hash(pointer, "pointer_payload_hash")


def validate_active_pointer(pointer: Mapping[str, Any]) -> None:
    if pointer.get("schema") != POINTER_SCHEMA:
        raise GenerationContractError("unsupported active pointer schema")
    if pointer.get("owner_digest") != owner_digest(str(pointer.get("owner_key", ""))):
        raise GenerationContractError("pointer owner digest mismatch")
    manifest_filename = str(pointer.get("manifest_filename", ""))
    if Path(manifest_filename).name != manifest_filename or not manifest_filename:
        raise GenerationContractError("pointer manifest filename is not immutable-flat")
    for field in ("active_generation_id", "manifest_sha256", "source_hash"):
        if not isinstance(pointer.get(field), str) or not pointer[field]:
            raise GenerationContractError(f"pointer missing {field}")
    validate_payload_hash(pointer, "pointer_payload_hash")

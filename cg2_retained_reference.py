"""Typed retained-reference reader for CG-2 reference-v2 rollback targets."""

from __future__ import annotations

import copy
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from chroma_store import ChromaStore
from file_generation_contract import (
    GenerationContractError,
    REFERENCE_V2_FINGERPRINT,
    canonical_hash,
    is_retained_legacy_reference_manifest,
    validate_retained_legacy_reference_manifest,
)
from file_generation_store import FileGenerationStore

from cg2_legacy_vector_attestation import (
    D0AttestationError,
    vector_encoding_sha256,
)

READER_CALL_LOG: list[dict[str, Any]] = []


class RetainedReferenceError(RuntimeError):
    """Retained-reference membership or readback refused."""


@dataclass(frozen=True)
class RetainedReferenceTargetDescriptor:
    owner_digest: str
    generation_id: str
    reference_fingerprint: str
    proof_profile: str
    collections: Mapping[str, Mapping[str, Any]]


def serving_selector_fingerprint(descriptor: RetainedReferenceTargetDescriptor) -> str:
    payload = {
        "schema": "convmem/cg2-retained-reference-serving-selector-v1",
        "owner_digest": descriptor.owner_digest,
        "generation_id": descriptor.generation_id,
        "reference_fingerprint": descriptor.reference_fingerprint,
        "proof_profile": descriptor.proof_profile,
        "collections": copy.deepcopy(dict(descriptor.collections)),
    }
    return canonical_hash(payload)


def build_descriptor_from_manifest(manifest: Mapping[str, Any]) -> RetainedReferenceTargetDescriptor:
    validate_retained_legacy_reference_manifest(manifest)
    fingerprints = dict(manifest.get("fingerprints") or {})
    return RetainedReferenceTargetDescriptor(
        owner_digest=str(manifest["owner_digest"]),
        generation_id=str(manifest["generation_id"]),
        reference_fingerprint=str(
            fingerprints.get("reference") or REFERENCE_V2_FINGERPRINT
        ),
        proof_profile=str(manifest.get("proof_profile") or ""),
        collections=copy.deepcopy(dict(manifest.get("collections_selector") or {})),
    )


def _append_reader_log(*, descriptor: RetainedReferenceTargetDescriptor, collection_name: str, physical_ids: Sequence[str]) -> None:
    READER_CALL_LOG.append(
        {
            "owner_digest": descriptor.owner_digest,
            "generation_id": descriptor.generation_id,
            "collection_name": collection_name,
            "physical_ids": list(physical_ids),
            "selector_fingerprint": serving_selector_fingerprint(descriptor),
        }
    )


def _as_float_tuple(embedding: Any) -> tuple[float, ...]:
    if embedding is None:
        raise RetainedReferenceError("referenced row lacks persisted embedding")
    if hasattr(embedding, "tolist"):
        embedding = embedding.tolist()
    if not isinstance(embedding, (list, tuple)) or not embedding:
        raise RetainedReferenceError("referenced row lacks persisted embedding")
    try:
        values = tuple(float(value) for value in embedding)
    except (TypeError, ValueError) as exc:
        raise RetainedReferenceError("referenced row embedding is malformed") from exc
    return values


def read_retained_reference_rows(
    store: FileGenerationStore | ChromaStore,
    descriptor: RetainedReferenceTargetDescriptor,
    *,
    include_embeddings: bool = True,
) -> list[dict[str, Any]]:
    """Read exact physical IDs named by the reference manifest selector."""

    chroma = store.raw_store if isinstance(store, FileGenerationStore) else store
    include = ["metadatas", "documents"]
    if include_embeddings:
        include.append("embeddings")
    rows: list[dict[str, Any]] = []
    for collection_name, raw_spec in dict(descriptor.collections).items():
        spec = dict(raw_spec)
        physical_ids = [str(value) for value in list(spec.get("physical_ids") or [])]
        if not physical_ids:
            raise RetainedReferenceError(
                f"collection {collection_name} selector is empty"
            )
        _append_reader_log(
            descriptor=descriptor,
            collection_name=collection_name,
            physical_ids=physical_ids,
        )
        col = chroma._collection(collection_name)  # pylint: disable=protected-access
        actual_uuid = str(col.id)
        actual_configuration = dict(col.configuration_json)
        if actual_uuid != str(spec.get("collection_uuid") or ""):
            raise RetainedReferenceError(
                f"{collection_name} collection UUID mismatch for retained reference"
            )
        if actual_configuration != dict(spec.get("configuration") or {}):
            raise RetainedReferenceError(
                f"{collection_name} collection configuration mismatch for retained reference"
            )
        result = col.get(ids=physical_ids, include=include)
        returned_ids = list(result.get("ids") or [])
        if len(returned_ids) != len(physical_ids):
            missing = sorted(set(physical_ids) - set(returned_ids))
            raise RetainedReferenceError(
                f"missing referenced physical ids in {collection_name}: {missing}"
            )
        if len(set(returned_ids)) != len(returned_ids):
            raise RetainedReferenceError(
                f"duplicate referenced physical ids in {collection_name}"
            )
        documents = list(result.get("documents") or [])
        metadatas = list(result.get("metadatas") or [])
        embeddings = result.get("embeddings") if include_embeddings else None
        if embeddings is None:
            embeddings = []
        for index, physical_id in enumerate(returned_ids):
            meta = dict(metadatas[index] if index < len(metadatas) else {})
            document = documents[index] if index < len(documents) else None
            if not isinstance(document, str):
                raise RetainedReferenceError(
                    f"referenced row {collection_name}/{physical_id} lacks document"
                )
            row: dict[str, Any] = {
                "id": physical_id,
                "physical_id": physical_id,
                "collection_name": collection_name,
                "logical_id": meta.get("logical_id"),
                "document": document,
                "metadata": meta,
            }
            if include_embeddings:
                embedding = embeddings[index] if index < len(embeddings) else None
                row["embedding"] = list(_as_float_tuple(embedding))
            rows.append(row)
    rows.sort(key=lambda item: (str(item["collection_name"]), str(item["physical_id"])))
    return rows


def qualify_retained_reference_membership(
    rows: Sequence[Mapping[str, Any]],
    descriptor: RetainedReferenceTargetDescriptor,
    d0_roots: Mapping[str, str],
) -> dict[str, Any]:
    """Verify selector membership and D0 root equality from reader output."""

    expected_by_key: dict[tuple[str, str], Mapping[str, Any]] = {}
    for collection_name, raw_spec in dict(descriptor.collections).items():
        spec = dict(raw_spec)
        for physical_id in list(spec.get("physical_ids") or []):
            identity = dict(dict(spec.get("row_identities") or {}).get(str(physical_id)) or {})
            expected_by_key[(str(collection_name), str(physical_id))] = identity

    observed_keys = {
        (str(row.get("collection_name") or ""), str(row.get("physical_id") or ""))
        for row in rows
    }
    expected_keys = set(expected_by_key)
    missing = sorted(expected_keys - observed_keys)
    unexpected = sorted(observed_keys - expected_keys)
    if missing or unexpected:
        raise RetainedReferenceError(
            f"retained reference membership mismatch missing={missing} unexpected={unexpected}"
        )

    non_equivalent = 0
    for row in rows:
        key = (str(row["collection_name"]), str(row["physical_id"]))
        expected = dict(expected_by_key[key])
        document_hash = canonical_hash(str(row.get("document") or ""))
        if document_hash != str(expected.get("document_hash") or ""):
            non_equivalent += 1
            continue
        embedding = row.get("embedding")
        if embedding is None:
            non_equivalent += 1
            continue
        vector_hash = vector_encoding_sha256(list(embedding))
        if vector_hash != str(expected.get("vector_encoding_sha256") or ""):
            non_equivalent += 1
    if non_equivalent:
        raise RetainedReferenceError(
            f"retained reference readback is not exact ({non_equivalent} rows)"
        )

    snapshot = str(d0_roots.get("snapshot") or "")
    vector = str(d0_roots.get("vector") or "")
    if not snapshot or not vector:
        raise RetainedReferenceError("d0_roots must include snapshot and vector")
    return {
        "missing_count": len(missing),
        "unexpected_count": len(unexpected),
        "duplicate_count": 0,
        "wrong_owner_count": 0,
        "non_equivalent_count": non_equivalent,
        "provenance_identity_changing_count": 0,
        "snapshot_root": snapshot,
        "vector_root": vector,
        "selector_fingerprint": serving_selector_fingerprint(descriptor),
        "valid": True,
    }


def manifest_is_reference_v2(manifest: Mapping[str, Any]) -> bool:
    try:
        return is_retained_legacy_reference_manifest(manifest)
    except GenerationContractError:
        return False

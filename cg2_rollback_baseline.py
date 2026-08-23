"""CG-2 Design A — exact LEGACY → retained rollback baseline (convert-v1).

Hermetic conversion of one owner's accepted pre-cutover LEGACY serving set into
a manifested, cold-qualified, non-serving ``RETAINED_ROLLBACK_BASELINE``
generation ``G_rb``.  Never embeds, parses, calls an LLM, or dedupes the
accepted set.
"""

# pylint: disable=too-many-lines,too-many-instance-attributes,too-many-branches
# pylint: disable=too-many-arguments,too-many-locals,too-many-statements,duplicate-code

from __future__ import annotations

import copy
import json
import math
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from atomic_files import atomic_write_json
from chroma_store import SUMMARIES, UNITS, ChromaStore, is_superseded
from chroma_write_store import WriterBoundaryError, require_writer_attestation
from config import load_config
from file_generation_contract import (
    build_generation_manifest,
    candidate_bundle_hash,
    canonical_hash,
    canonical_source_path,
    make_generation_id,
    make_physical_id,
)
from file_generation_pointer import load_manifest_reference, publish_manifest, provision_generation_layout
from file_generation_store import FILE_SCOPE, STABLE_SCOPE, FileGenerationStore, StagedRow
from file_generation_validate import run_cold_validation
from provenance_binding import (
    PROVENANCE_ASSERTION_ID_KEY,
    PROVENANCE_COMMITMENT_KEY,
    PROVENANCE_ENVELOPE_KEY,
    envelope_from_unit,
    provenance_identity,
    validate_projection,
)
from ingest import load_processed
from purge_locks import source_flock
from serving_authority import (
    OwnerAuthorityMode,
    ServingAuthorityError,
    fence_path,
    generation_root_for_cfg,
    pointer_path,
    retirement_path,
    resolve_frozen_authority_vector,
)

from cg2_legacy_vector_attestation import (
    D0AttestationError,
    LEGACY_EXACT_VECTOR_UNKNOWN_MODEL_V1,
    derive_query_embedding_context,
    load_ratified_d0_chain,
    verify_d0_chain_for_grb_conversion,
    vector_encoding_sha256,
)
from chroma_readonly import collection_config_metadata, collection_uuid

CONVERT_V1_FINGERPRINT = "convmem/cg2-rollback-baseline-convert-v1"
ROLLBACK_BASELINE_SCHEMA = "convmem/cg2-rollback-baseline-evidence-v1"
RETAINED_ROLLBACK_BASELINE = "RETAINED_ROLLBACK_BASELINE"
UNKNOWN_EMBEDDING_MODEL = "UNKNOWN"
_SHA256_HEX = re.compile(r"^[0-9a-f]{64}$")
_EQUIVALENCE_COUNT_KEYS = (
    "missing_count",
    "unexpected_count",
    "duplicate_count",
    "wrong_owner_count",
    "non_equivalent_count",
    "provenance_identity_changing_count",
)
_EQUIVALENCE_IDENTITY_SCHEMA = "convmem/cg2-bidirectional-equivalence-v1"

_IMMUTABLE_METADATA_KEYS = (
    "source_path",
    "start_offset",
    "content_hash",
    "ledger_id",
    PROVENANCE_ASSERTION_ID_KEY,
    PROVENANCE_COMMITMENT_KEY,
    PROVENANCE_ENVELOPE_KEY,
)


class RollbackBaselineError(RuntimeError):
    """Accepted LEGACY capture/conversion/evidence validation refused."""


@dataclass(frozen=True)
class LegacyServingRow:
    """One admitted LEGACY serving row with persisted embedding bytes."""

    collection_name: str
    physical_id: str
    logical_id: str
    document: str
    embedding: tuple[float, ...]
    metadata: Mapping[str, Any]
    assertion_id: str | None = None
    provenance_commitment: str | None = None
    provenance_envelope: str | None = None

    @property
    def embedding_list(self) -> list[float]:
        return list(self.embedding)


@dataclass(frozen=True)
class LegacyServingSnapshot:
    """Frozen accepted LEGACY serving set for one owner/source."""

    owner_key: str
    owner_digest: str
    canonical_source_path: str
    accepted_source_hash: str
    rows: tuple[LegacyServingRow, ...]
    snapshot_digest: str
    candidate_bundle_hash: str


@dataclass(frozen=True)
class RollbackBaselineResult:
    """Qualified retained rollback baseline produced by convert-v1."""

    generation_id: str
    owner_digest: str
    convert_fingerprint: str
    manifest_sha256: str
    manifest_filename: str
    evidence_path: Path
    evidence: Mapping[str, Any]
    cold_qualification: Mapping[str, Any]
    equivalence: Mapping[str, Any]
    snapshot: LegacyServingSnapshot
    generation_rows: tuple[LegacyServingRow, ...] = ()


def rollback_baseline_dir(generation_root: str | Path) -> Path:
    return Path(generation_root) / "rollback_baselines"


def rollback_baseline_evidence_path(
    generation_root: str | Path, owner_digest_value: str, generation_id: str
) -> Path:
    return (
        rollback_baseline_dir(generation_root)
        / f"{owner_digest_value}--{generation_id}.json"
    )


def _as_float_tuple(embedding: Any) -> tuple[float, ...]:
    if embedding is None:
        raise RollbackBaselineError("admitted LEGACY row lacks persisted embedding")
    if hasattr(embedding, "tolist"):
        embedding = embedding.tolist()
    if not isinstance(embedding, (list, tuple)) or not embedding:
        raise RollbackBaselineError("admitted LEGACY row lacks persisted embedding")
    values = tuple(float(value) for value in embedding)
    if any(
        math.isnan(value) or value in (float("inf"), float("-inf")) for value in values
    ):
        raise RollbackBaselineError("admitted LEGACY embedding is non-finite")
    return values


def _conversion_logical_id(meta: Mapping[str, Any], physical_id: str) -> str:
    """Return the unambiguous conversion logical identity for one LEGACY row.

    ``ledger_id`` alone is never conversion logical identity: same-ledger twins
    with distinct provenance must remain distinct. Prefer an explicit
    ``logical_id``, else the LEGACY physical id.
    """

    explicit = str(meta.get("logical_id") or "").strip()
    if explicit:
        return explicit
    return str(physical_id)


def _provenance_fields(
    meta: Mapping[str, Any],
) -> tuple[str | None, str | None, str | None]:
    identity = provenance_identity(meta)
    if identity is None:
        return None, None, None
    assertion_id, commitment = identity
    envelope = meta.get(PROVENANCE_ENVELOPE_KEY)
    if envelope is None:
        return assertion_id, commitment, None
    if isinstance(envelope, Mapping):
        return assertion_id, commitment, json.dumps(envelope, sort_keys=True)
    return assertion_id, commitment, str(envelope)


def _semantic_immutable(meta: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: meta[key]
        for key in ("source_path", "start_offset", "content_hash", "ledger_id")
        if key in meta and meta[key] not in ("", None)
    }


def _identity_tuple(
    *,
    owner_digest_value: str,
    collection_name: str,
    logical_id: str,
    document_hash: str,
    persisted_embedding_hash: str,
    embedding_model: str,
    embedding_dimension: int,
    immutable_semantic_metadata_hash: str,
    provenance_envelope_hash: str | None,
    assertion_id: str | None,
    provenance_commitment: str | None,
) -> dict[str, Any]:
    return {
        "owner_digest": owner_digest_value,
        "collection_name": collection_name,
        "logical_id": logical_id,
        "document_hash": document_hash,
        "persisted_embedding_hash": persisted_embedding_hash,
        "embedding_model": embedding_model,
        "embedding_dimension": int(embedding_dimension),
        "immutable_semantic_metadata_hash": immutable_semantic_metadata_hash,
        "provenance_envelope_hash": provenance_envelope_hash,
        "assertion_id": assertion_id,
        "provenance_commitment": provenance_commitment,
    }


def _normalized_row_identity(
    *,
    owner_digest_value: str,
    row: LegacyServingRow,
    embedding_model: str,
    embedding_dimension: int,
) -> dict[str, Any]:
    envelope_value = row.provenance_envelope
    return _identity_tuple(
        owner_digest_value=owner_digest_value,
        collection_name=row.collection_name,
        logical_id=row.logical_id,
        document_hash=canonical_hash(row.document),
        persisted_embedding_hash=canonical_hash(row.embedding_list),
        embedding_model=embedding_model,
        embedding_dimension=int(embedding_dimension),
        immutable_semantic_metadata_hash=canonical_hash(
            _semantic_immutable(dict(row.metadata))
        ),
        provenance_envelope_hash=(
            canonical_hash(envelope_value) if envelope_value is not None else None
        ),
        assertion_id=row.assertion_id,
        provenance_commitment=row.provenance_commitment,
    )


def _snapshot_digest(
    owner_digest_value: str,
    rows: Sequence[LegacyServingRow],
    *,
    embedding_model_by_collection: Mapping[str, str],
    embedding_dimension_by_collection: Mapping[str, int],
) -> str:
    identities = [
        _normalized_row_identity(
            owner_digest_value=owner_digest_value,
            row=row,
            embedding_model=embedding_model_by_collection[row.collection_name],
            embedding_dimension=embedding_dimension_by_collection[row.collection_name],
        )
        for row in rows
    ]
    identities.sort(key=canonical_hash)
    return canonical_hash(
        {"schema": "convmem/cg2-legacy-serving-snapshot-v1", "rows": identities}
    )


def _observed_embedding_maps(
    rows: Sequence[LegacyServingRow],
    models: Mapping[str, str],
    dims: Mapping[str, int],
) -> tuple[dict[str, str], dict[str, int]]:
    snapshot_models = {
        name: str(models.get(name) or "unspecified") for name in (UNITS, SUMMARIES)
    }
    snapshot_dims = {name: int(dims.get(name) or 0) for name in (UNITS, SUMMARIES)}
    for row in rows:
        observed = len(row.embedding)
        current = snapshot_dims[row.collection_name]
        if current <= 0:
            snapshot_dims[row.collection_name] = observed
        elif current != observed:
            raise RollbackBaselineError(
                f"mixed embedding dimensions in {row.collection_name}"
            )
    return snapshot_models, snapshot_dims




def _utf8_sort_key(*parts: str) -> bytes:
    encoded: list[bytes] = []
    for part in parts:
        if not isinstance(part, str):
            raise RollbackBaselineError("identity component is not a string")
        encoded.append(part.encode("utf-8"))
    return b"\x00".join(encoded)


def _d0_semantic_immutable(meta: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: meta[key]
        for key in ("source_path", "start_offset", "content_hash", "ledger_id")
        if key in meta and meta[key] not in ("", None)
    }


def _d0_provenance_leaf_fields(meta: Mapping[str, Any]) -> dict[str, Any]:
    identity = provenance_identity(meta)
    envelope = envelope_from_unit(meta)
    if identity is None or envelope is None:
        return {
            "provenance_envelope": None,
            "provenance_envelope_hash": None,
            "assertion_id": None,
            "provenance_commitment": None,
        }
    assertion_id, commitment = identity
    return {
        "provenance_envelope": envelope,
        "provenance_envelope_hash": canonical_hash(envelope),
        "assertion_id": assertion_id,
        "provenance_commitment": commitment,
    }


def _legacy_rows_to_d0_leaves(rows: Sequence[LegacyServingRow]) -> list[dict[str, Any]]:
    leaves: list[dict[str, Any]] = []
    for row in rows:
        provenance = _d0_provenance_leaf_fields(row.metadata)
        leaves.append(
            {
                "collection_name": row.collection_name,
                "conversion_logical_id": row.logical_id,
                "physical_id": row.physical_id,
                "document_hash": canonical_hash(row.document),
                "immutable_semantic_metadata_hash": canonical_hash(
                    _d0_semantic_immutable(dict(row.metadata))
                ),
                "vector_encoding_sha256": vector_encoding_sha256(row.embedding),
                **provenance,
            }
        )
    seen: set[bytes] = set()
    for leaf in leaves:
        identity = _utf8_sort_key(
            leaf["collection_name"],
            leaf["conversion_logical_id"],
            leaf["physical_id"],
        )
        if identity in seen:
            raise RollbackBaselineError("duplicate conversion identity tuple")
        seen.add(identity)
    leaves.sort(
        key=lambda leaf: _utf8_sort_key(
            leaf["collection_name"],
            leaf["conversion_logical_id"],
            leaf["physical_id"],
        )
    )
    return leaves


def _recompute_d0_roots(
    rows: Sequence[LegacyServingRow], chroma_dir: str, dimension: int
) -> dict[str, str]:
    leaves = _legacy_rows_to_d0_leaves(rows)
    collection_names = sorted({row.collection_name for row in rows}, key=lambda n: n.encode("utf-8"))
    bindings: list[dict[str, Any]] = []
    for collection_name in collection_names:
        uuid = collection_uuid(chroma_dir, collection_name)
        if not uuid:
            raise RollbackBaselineError(
                f"missing immutable collection UUID for {collection_name}"
            )
        configuration = collection_config_metadata(chroma_dir, collection_name)
        ordered = [leaf for leaf in leaves if leaf["collection_name"] == collection_name]
        ordered.sort(
            key=lambda leaf: _utf8_sort_key(
                leaf["conversion_logical_id"], leaf["physical_id"]
            )
        )
        snapshot_root = canonical_hash(
            {
                "collection_configuration": configuration,
                "collection_uuid": uuid,
                "embedding_dimension": dimension,
                "leaves": ordered,
            }
        )
        vector_root = canonical_hash(
            {
                "collection_uuid": uuid,
                "embedding_dimension": dimension,
                "vector_encoding_sha256": [
                    leaf["vector_encoding_sha256"] for leaf in ordered
                ],
            }
        )
        bindings.append(
            {
                "collection_name": collection_name,
                "collection_snapshot_root": snapshot_root,
                "collection_vector_root": vector_root,
            }
        )
    snapshot = canonical_hash(
        [
            {
                "collection_name": item["collection_name"],
                "collection_snapshot_root": item["collection_snapshot_root"],
            }
            for item in bindings
        ]
    )
    vector = canonical_hash(
        [
            {
                "collection_name": item["collection_name"],
                "collection_vector_root": item["collection_vector_root"],
            }
            for item in bindings
        ]
    )
    return {"snapshot": snapshot, "vector": vector}


def _admitted_dimension_from_d0_candidate(candidate: Mapping[str, Any]) -> int:
    collections = candidate.get("collections") or []
    if not collections:
        raise RollbackBaselineError("D0 chain has no admitted collections")
    dimensions = {
        int(item["embedding_dimension"])
        for item in collections
        if isinstance(item, Mapping) and "embedding_dimension" in item
    }
    if len(dimensions) != 1:
        raise RollbackBaselineError("D0 chain lacks a unique embedding_dimension")
    dimension = next(iter(dimensions))
    if dimension <= 0:
        raise RollbackBaselineError("embedding dimension must be a positive integer")
    return dimension


def _historical_bindings_from_d0_chain(
    chain,
    store: FileGenerationStore,
    *,
    rows: Sequence[LegacyServingRow],
) -> dict[str, dict[str, Any]]:
    candidate = chain.candidate
    capture_time = chain.ratification.capture_time
    bindings: dict[str, dict[str, Any]] = {}
    for coll in candidate.get("collections") or []:
        if not isinstance(coll, Mapping):
            raise RollbackBaselineError("D0 collection binding is not an object")
        name = str(coll["collection_name"])
        has_rows = any(row.collection_name == name for row in rows)
        if not has_rows:
            continue
        live_uuid = collection_uuid(store.chroma_dir, name)
        live_config = collection_config_metadata(store.chroma_dir, name)
        if str(live_uuid or "") != str(coll["collection_uuid"]):
            raise RollbackBaselineError(f"D0 collection UUID mismatch for {name}")
        if dict(live_config) != dict(coll["collection_configuration"]):
            raise RollbackBaselineError(
                f"D0 collection configuration mismatch for {name}"
            )
        identity = store.collection_identity(name)
        dimension = int(coll["embedding_dimension"])
        digest = canonical_hash(
            {
                "collection_uuid": str(coll["collection_uuid"]),
                "configuration": dict(coll["collection_configuration"]),
                "embedding_dimension": dimension,
                "historical_embedding_model": {"identifier": None, "status": "UNKNOWN"},
                "proof_profile": LEGACY_EXACT_VECTOR_UNKNOWN_MODEL_V1,
            }
        )
        bindings[name] = {
            "collection_uuid": str(identity["collection_uuid"]),
            "configuration": copy.deepcopy(dict(identity["configuration"])),
            "embedding_model": UNKNOWN_EMBEDDING_MODEL,
            "embedding_dimension": dimension,
            "historical_embedding_model": {"identifier": None, "status": "UNKNOWN"},
            "proof_profile": LEGACY_EXACT_VECTOR_UNKNOWN_MODEL_V1,
            "provenance_evidence_digest": digest,
            "capture_timestamp": capture_time,
        }
    if UNITS not in bindings:
        raise RollbackBaselineError("D0 chain lacks knowledge_units collection binding")
    return bindings


def _snapshot_from_reread_rows(
    *,
    owner_key: str,
    owner_digest_value: str,
    canonical_source: str,
    accepted_source_hash: str,
    rows: Sequence[LegacyServingRow],
    historical_bindings: Mapping[str, Mapping[str, Any]],
) -> LegacyServingSnapshot:
    models = {
        name: UNKNOWN_EMBEDDING_MODEL for name in historical_bindings
    }
    dims = {
        name: int(spec["embedding_dimension"])
        for name, spec in historical_bindings.items()
    }
    digest = _snapshot_digest(
        owner_digest_value,
        rows,
        embedding_model_by_collection=models,
        embedding_dimension_by_collection=dims,
    )
    return LegacyServingSnapshot(
        owner_key=owner_key,
        owner_digest=owner_digest_value,
        canonical_source_path=canonical_source,
        accepted_source_hash=accepted_source_hash,
        rows=tuple(rows),
        snapshot_digest=digest,
        candidate_bundle_hash=_bundle_hash_from_rows(rows),
    )


def _reread_rows_for_d0_chain(
    cfg: Mapping[str, Any],
    store: FileGenerationStore,
    chain,
) -> list[LegacyServingRow]:
    candidate = chain.candidate
    canonical = str(candidate["canonical_source_path"])
    owner_key = str(candidate["owner_key"])
    owner_digest_value = chain.owner_digest
    dimension = _admitted_dimension_from_d0_candidate(candidate)
    with source_flock(dict(cfg), canonical):
        bound_hash = _bind_accepted_source_hash(
            cfg,
            canonical_source=canonical,
            claimed=str(candidate["accepted_source_hash"]),
        )
        if bound_hash != str(candidate["accepted_source_hash"]):
            raise RollbackBaselineError(
                "accepted_source_hash does not bind at D1 conversion boundary"
            )
        _require_legacy_owner(
            cfg, owner_digest_value=owner_digest_value, owner_key=owner_key
        )
        first_rows = _admit_rows(
            store.raw_store,
            owner_digest_value=owner_digest_value,
            owner_key=owner_key,
            canonical_source=canonical,
        )
        first_roots = _recompute_d0_roots(first_rows, store.chroma_dir, dimension)
        _require_legacy_owner(
            cfg, owner_digest_value=owner_digest_value, owner_key=owner_key
        )
        second_rows = _admit_rows(
            store.raw_store,
            owner_digest_value=owner_digest_value,
            owner_key=owner_key,
            canonical_source=canonical,
        )
        second_roots = _recompute_d0_roots(second_rows, store.chroma_dir, dimension)
    if first_roots != second_roots:
        raise RollbackBaselineError(
            "LEGACY serving set churned during D1 reread; refusing conversion"
        )
    if first_roots["snapshot"] != chain.ratification.accepted_legacy_snapshot_root:
        raise RollbackBaselineError(
            "reread snapshot root does not match ratified D0 chain"
        )
    if first_roots["vector"] != chain.ratification.accepted_legacy_vector_root:
        raise RollbackBaselineError(
            "reread vector root does not match ratified D0 chain"
        )
    return first_rows

def _require_canonical_sha256_hex(value: object, *, label: str) -> str:
    if not isinstance(value, str) or not _SHA256_HEX.fullmatch(value):
        raise RollbackBaselineError(f"{label} must be a canonical SHA-256 hex digest")
    return value


def _bind_accepted_source_hash(
    cfg: Mapping[str, Any], *, canonical_source: str, claimed: str
) -> str:
    """Bind caller hash to the processed/accepted observation for this source."""

    claimed_hash = _require_canonical_sha256_hex(
        claimed, label="accepted_source_hash"
    )
    processed_log = str((cfg.get("index") or {}).get("processed_log") or "").strip()
    if not processed_log:
        raise RollbackBaselineError(
            "config lacks processed_log for accepted source hash binding"
        )
    processed = load_processed(processed_log)
    matches: list[str] = []
    for key, entry in processed.items():
        if not isinstance(entry, dict) or entry.get("excluded"):
            continue
        path_value = entry.get("path")
        if not path_value:
            continue
        if canonical_source_path(str(path_value)) == canonical_source:
            matches.append(str(key))
    unique = sorted(set(matches))
    if len(unique) != 1:
        raise RollbackBaselineError(
            "accepted LEGACY source hash is not uniquely bound in processed log"
        )
    bound = _require_canonical_sha256_hex(
        unique[0], label="processed accepted source key"
    )
    if claimed_hash != bound:
        raise RollbackBaselineError(
            "wrong accepted_source_hash; refusing unbound or filesystem-substituted hash"
        )
    return bound


def _resolve_live_production_paths() -> tuple[Path, Path]:
    """Resolve configured live Chroma and generation-root identity.

    Inability to resolve refuses rather than assuming a caller path is safe.
    """

    try:
        live_cfg = load_config()
    except Exception as exc:  # noqa: BLE001 — any config failure is fail-closed
        raise RollbackBaselineError(
            "cannot resolve live production identity"
        ) from exc
    if not isinstance(live_cfg, Mapping):
        raise RollbackBaselineError("cannot resolve live production identity")
    try:
        chroma_raw = str((live_cfg.get("index") or {}).get("chroma_dir") or "").strip()
        if not chroma_raw:
            raise RollbackBaselineError("cannot resolve live production identity")
        live_chroma = Path(chroma_raw).expanduser().resolve()
        live_generation_root = generation_root_for_cfg(live_cfg).expanduser().resolve()
    except (
        OSError,
        TypeError,
        ValueError,
        KeyError,
        ServingAuthorityError,
        RollbackBaselineError,
    ) as exc:
        raise RollbackBaselineError(
            "cannot resolve live production identity"
        ) from exc
    return live_chroma, live_generation_root


def _refuse_unattested_production_chroma(chroma_dir: str | Path) -> None:
    """Refuse opening/mutating configured production Chroma without the writer gate.

    Temporary Execute stores differ from the live configured path and are allowed
    once live identity resolves. A later authorized production G_rb build may
    proceed when the existing writer boundary attestation is held. This is
    identity binding, not a tmp-path heuristic.
    """

    live_chroma, _live_generation_root = _resolve_live_production_paths()
    target = Path(chroma_dir).expanduser().resolve()
    if target != live_chroma:
        return
    try:
        require_writer_attestation()
    except WriterBoundaryError as exc:
        raise RollbackBaselineError(
            "production Chroma mutation requires the existing writer boundary"
        ) from exc


def _refuse_unattested_production_generation_root(generation_root: str | Path) -> None:
    """Refuse mutating the configured live generation root without the writer gate."""

    _live_chroma, live_generation_root = _resolve_live_production_paths()
    target = Path(generation_root).expanduser().resolve()
    if target != live_generation_root:
        return
    try:
        require_writer_attestation()
    except WriterBoundaryError as exc:
        raise RollbackBaselineError(
            "production generation root mutation requires the existing writer boundary"
        ) from exc


def _equivalence_identity(
    *,
    normalized_snapshot_digest: str,
    manifest_sha256: str,
    generation_id: str,
    owner_digest_value: str,
) -> str:
    """Bind zero-count equivalence to independently verified D1 identities."""

    payload = {
        "schema": _EQUIVALENCE_IDENTITY_SCHEMA,
        "normalized_snapshot_digest": normalized_snapshot_digest,
        "manifest_sha256": manifest_sha256,
        "generation_id": generation_id,
        "owner_digest": owner_digest_value,
    }
    for key in _EQUIVALENCE_COUNT_KEYS:
        payload[key] = 0
    return canonical_hash(payload)


def _assert_row_owner_consistency(
    meta: Mapping[str, Any],
    *,
    owner_digest_value: str,
    owner_key: str,
) -> None:
    indicated = str(meta.get("owner_digest") or "").strip()
    if indicated and indicated != owner_digest_value:
        raise RollbackBaselineError(
            "conflicting/foreign owner_digest on LEGACY row"
        )
    indicated_key = str(meta.get("owner_key") or "").strip()
    if indicated_key and indicated_key != owner_key:
        raise RollbackBaselineError("conflicting/foreign owner_key on LEGACY row")


def _bundle_hash_from_rows(rows: Sequence[LegacyServingRow]) -> str:
    units = [
        {
            "logical_id": row.logical_id,
            "document": row.document,
            "embedding": row.embedding_list,
            "metadata": dict(row.metadata),
        }
        for row in rows
        if row.collection_name == UNITS
    ]
    summaries = [
        {
            "logical_id": row.logical_id,
            "document": row.document,
            "embedding": row.embedding_list,
            "metadata": dict(row.metadata),
        }
        for row in rows
        if row.collection_name == SUMMARIES
    ]
    units.sort(key=lambda item: str(item["logical_id"]))
    summaries.sort(key=lambda item: str(item["logical_id"]))
    return candidate_bundle_hash(units, summaries)


def _is_legacy_serving_row(meta: Mapping[str, Any]) -> bool:
    if is_superseded(dict(meta)):
        return False
    scope = str(meta.get("generation_scope") or "")
    if scope in (STABLE_SCOPE, FILE_SCOPE):
        return False
    return True


def _read_collection_rows(
    store: ChromaStore,
    collection_name: str,
    *,
    canonical_source: str,
) -> list[tuple[str, str, dict[str, Any], tuple[float, ...]]]:
    col = store._collection(collection_name)  # pylint: disable=protected-access
    result = col.get(
        where={"source_path": canonical_source},
        include=["metadatas", "documents", "embeddings"],
    )
    ids = list(result.get("ids") or [])
    documents = list(result.get("documents") or [])
    metadatas = list(result.get("metadatas") or [])
    embeddings = result.get("embeddings")
    if embeddings is None:
        embeddings = []
    rows: list[tuple[str, str, dict[str, Any], tuple[float, ...]]] = []
    for index, physical_id in enumerate(ids):
        meta = dict(metadatas[index] if index < len(metadatas) else {})
        meta.setdefault("id", physical_id)
        if not _is_legacy_serving_row(meta):
            continue
        document = documents[index] if index < len(documents) else None
        if not isinstance(document, str):
            raise RollbackBaselineError(
                f"LEGACY row {collection_name}/{physical_id} lacks document"
            )
        embedding = embeddings[index] if index < len(embeddings) else None
        rows.append(
            (str(physical_id), document, meta, _as_float_tuple(embedding))
        )
    return rows


def _require_legacy_owner(
    cfg: Mapping[str, Any], *, owner_digest_value: str, owner_key: str
) -> None:
    generation_root = generation_root_for_cfg(cfg)
    if retirement_path(generation_root, owner_digest_value).exists():
        raise RollbackBaselineError("owner is RETIRED; capture requires LEGACY")
    if fence_path(generation_root, owner_digest_value).exists():
        raise RollbackBaselineError("owner has fence; capture requires LEGACY")
    if pointer_path(generation_root, owner_digest_value).exists():
        raise RollbackBaselineError("owner has pointer; capture requires LEGACY")
    vector = resolve_frozen_authority_vector(cfg, owner_digests={owner_digest_value})
    state = vector.by_owner.get(owner_digest_value)
    if state is None or state.mode != OwnerAuthorityMode.LEGACY:
        raise RollbackBaselineError(
            f"owner authority is not LEGACY (got {None if state is None else state.mode})"
        )
    if state.owner_key not in (None, owner_key):
        raise RollbackBaselineError("owner/source authority ambiguity")


def _admit_rows(
    store: ChromaStore,
    *,
    owner_digest_value: str,
    owner_key: str,
    canonical_source: str,
) -> list[LegacyServingRow]:
    admitted: list[LegacyServingRow] = []
    seen_logical: dict[str, str] = {}
    for collection_name in (UNITS, SUMMARIES):
        for physical_id, document, meta, embedding in _read_collection_rows(
            store, collection_name, canonical_source=canonical_source
        ):
            if str(meta.get("source_path") or "") != canonical_source:
                raise RollbackBaselineError(
                    "owner/source binding mismatch in LEGACY row"
                )
            _assert_row_owner_consistency(
                meta, owner_digest_value=owner_digest_value, owner_key=owner_key
            )
            logical_id = _conversion_logical_id(meta, physical_id)
            key = f"{collection_name}:{logical_id}"
            if key in seen_logical:
                raise RollbackBaselineError(
                    f"duplicate logical identity in accepted LEGACY set: {key}"
                )
            seen_logical[key] = physical_id
            assertion_id, commitment, envelope = _provenance_fields(meta)
            if assertion_id is None:
                checked = validate_projection(meta)
                if checked["status"] == "self-consistent":
                    raise RollbackBaselineError(
                        "provenance identity extraction failed for self-consistent row"
                    )
            admitted.append(
                LegacyServingRow(
                    collection_name=collection_name,
                    physical_id=physical_id,
                    logical_id=logical_id,
                    document=document,
                    embedding=embedding,
                    metadata=dict(meta),
                    assertion_id=assertion_id,
                    provenance_commitment=commitment,
                    provenance_envelope=envelope,
                )
            )
    admitted.sort(key=lambda row: (row.collection_name, row.logical_id, row.physical_id))
    if not admitted:
        raise RollbackBaselineError("accepted LEGACY serving set is empty")
    return admitted




def _stage_converted_rows(
    store: FileGenerationStore,
    snapshot: LegacyServingSnapshot,
    *,
    generation_id: str,
    embedding_provenance: Mapping[str, Mapping[str, Any]],
) -> list[StagedRow]:
    staged: list[StagedRow] = []
    for row in snapshot.rows:
        physical_id = make_physical_id(
            row.collection_name, generation_id, row.logical_id
        )
        meta = dict(row.metadata)
        meta.update(
            {
                "id": physical_id,
                "physical_id": physical_id,
                "logical_id": row.logical_id,
                "source_path": snapshot.canonical_source_path,
                "generation_scope": FILE_SCOPE,
                "owner_digest": snapshot.owner_digest,
                "generation_id": generation_id,
                "embedding_model": embedding_provenance[row.collection_name][
                    "embedding_model"
                ],
                "embedding_dimension": embedding_provenance[row.collection_name][
                    "embedding_dimension"
                ],
            }
        )
        if row.assertion_id is not None:
            meta[PROVENANCE_ASSERTION_ID_KEY] = row.assertion_id
            meta[PROVENANCE_COMMITMENT_KEY] = row.provenance_commitment
            if row.provenance_envelope is not None:
                meta[PROVENANCE_ENVELOPE_KEY] = row.provenance_envelope
        else:
            meta.pop(PROVENANCE_ASSERTION_ID_KEY, None)
            meta.pop(PROVENANCE_COMMITMENT_KEY, None)
            meta.pop(PROVENANCE_ENVELOPE_KEY, None)
        staged.append(
            StagedRow(
                row.collection_name,
                physical_id,
                row.logical_id,
                row.document,
                row.embedding_list,
                meta,
                FILE_SCOPE,
                snapshot.owner_digest,
                generation_id,
            )
        )
    store.stage_rows(staged)
    return staged


def _read_generation_rows(
    store: FileGenerationStore,
    *,
    owner_digest_value: str,
    generation_id: str,
) -> list[LegacyServingRow]:
    rows: list[LegacyServingRow] = []
    for collection_name in (UNITS, SUMMARIES):
        col = store.raw_store._collection(collection_name)  # pylint: disable=protected-access
        result = col.get(
            where={
                "$and": [
                    {"generation_scope": FILE_SCOPE},
                    {"owner_digest": owner_digest_value},
                    {"generation_id": generation_id},
                ]
            },
            include=["metadatas", "documents", "embeddings"],
        )
        ids = list(result.get("ids") or [])
        documents = list(result.get("documents") or [])
        metadatas = list(result.get("metadatas") or [])
        embeddings = result.get("embeddings")
        if embeddings is None:
            embeddings = []
        for index, physical_id in enumerate(ids):
            meta = dict(metadatas[index] if index < len(metadatas) else {})
            document = documents[index] if index < len(documents) else None
            if not isinstance(document, str):
                raise RollbackBaselineError(
                    f"G_rb row {collection_name}/{physical_id} lacks document"
                )
            embedding = embeddings[index] if index < len(embeddings) else None
            assertion_id, commitment, envelope = _provenance_fields(meta)
            rows.append(
                LegacyServingRow(
                    collection_name=collection_name,
                    physical_id=str(physical_id),
                    logical_id=str(meta.get("logical_id") or ""),
                    document=document,
                    embedding=_as_float_tuple(embedding),
                    metadata=meta,
                    assertion_id=assertion_id,
                    provenance_commitment=commitment,
                    provenance_envelope=envelope,
                )
            )
    rows.sort(key=lambda row: (row.collection_name, row.logical_id, row.physical_id))
    return rows


def prove_bidirectional_equivalence(
    snapshot: LegacyServingSnapshot,
    result: RollbackBaselineResult | Mapping[str, Any],
    *,
    generation_rows: Sequence[LegacyServingRow] | None = None,
    embedding_provenance: Mapping[str, Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """Prove snapshot ↔ G_rb set equality in both directions."""

    if isinstance(result, RollbackBaselineResult):
        generation_id = result.generation_id
        owner_digest_value = result.owner_digest
        provenance = dict(
            embedding_provenance
            or result.evidence.get("embedding_provenance")
            or {}
        )
        rows = list(generation_rows if generation_rows is not None else result.generation_rows)
    else:
        generation_id = str(result.get("generation_id") or "")
        owner_digest_value = str(result.get("owner_digest") or snapshot.owner_digest)
        provenance = dict(embedding_provenance or {})
        rows = list(generation_rows or ())

    if not rows:
        raise RollbackBaselineError("equivalence requires generation rows")

    model_by = {
        name: str(spec["embedding_model"]) for name, spec in provenance.items()
    }
    dim_by = {
        name: int(spec["embedding_dimension"]) for name, spec in provenance.items()
    }
    for row in list(snapshot.rows) + list(rows):
        if row.collection_name not in model_by:
            raise RollbackBaselineError(
                f"missing embedding provenance for {row.collection_name}"
            )

    left = {
        canonical_hash(
            _normalized_row_identity(
                owner_digest_value=snapshot.owner_digest,
                row=row,
                embedding_model=model_by[row.collection_name],
                embedding_dimension=dim_by[row.collection_name],
            )
        ): row
        for row in snapshot.rows
    }
    right = {
        canonical_hash(
            _normalized_row_identity(
                owner_digest_value=owner_digest_value,
                row=row,
                embedding_model=model_by[row.collection_name],
                embedding_dimension=dim_by[row.collection_name],
            )
        ): row
        for row in rows
    }
    if len(left) != len(snapshot.rows) or len(right) != len(rows):
        raise RollbackBaselineError("duplicate normalized identities in equivalence set")

    missing = sorted(set(left) - set(right))
    unexpected = sorted(set(right) - set(left))
    wrong_owner = [
        row.logical_id
        for row in rows
        if owner_digest_value and owner_digest_value != snapshot.owner_digest
    ]
    provenance_changing = []
    for digest_key in set(left) & set(right):
        left_row = left[digest_key]
        right_row = right[digest_key]
        if (
            left_row.assertion_id,
            left_row.provenance_commitment,
            left_row.provenance_envelope,
        ) != (
            right_row.assertion_id,
            right_row.provenance_commitment,
            right_row.provenance_envelope,
        ):
            provenance_changing.append(left_row.logical_id)

    report = {
        "generation_id": generation_id,
        "missing_count": len(missing),
        "unexpected_count": len(unexpected),
        "duplicate_count": 0,
        "wrong_owner_count": len(wrong_owner),
        "non_equivalent_count": len(missing) + len(unexpected),
        "provenance_identity_changing_count": len(provenance_changing),
        "missing": missing,
        "unexpected": unexpected,
        "provenance_identity_changing": provenance_changing,
    }
    if (
        report["missing_count"]
        or report["unexpected_count"]
        or report["wrong_owner_count"]
        or report["provenance_identity_changing_count"]
    ):
        raise RollbackBaselineError(
            "snapshot and G_rb are not bidirectionally equivalent: "
            f"missing={report['missing_count']} unexpected={report['unexpected_count']}"
        )
    return report


def _with_evidence_hash(payload: Mapping[str, Any]) -> dict[str, Any]:
    result = copy.deepcopy(dict(payload))
    result.pop("evidence_payload_hash", None)
    result["evidence_payload_hash"] = canonical_hash(result)
    return result


def _baseline_evidence_body(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Compare retained evidence without fresh-process position drift."""

    body = copy.deepcopy(dict(payload))
    body.pop("evidence_payload_hash", None)
    cold = dict(body.get("cold_qualification") or {})
    cold.pop("sequence_positions", None)
    body["cold_qualification"] = cold
    return body


def _baseline_evidence_matches(
    left: Mapping[str, Any], right: Mapping[str, Any]
) -> bool:
    if left == right:
        return True
    return _baseline_evidence_body(left) == _baseline_evidence_body(right)


def _publish_evidence(
    generation_root: str | Path,
    payload: Mapping[str, Any],
) -> Path:
    path = rollback_baseline_evidence_path(
        generation_root,
        str(payload["owner_digest"]),
        str(payload["generation_id"]),
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    obj = dict(payload)
    if path.exists():
        try:
            current = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise RollbackBaselineError(
                f"corrupt existing baseline evidence: {exc}"
            ) from exc
        if not _baseline_evidence_matches(current, obj):
            raise RollbackBaselineError(
                f"immutable rollback baseline evidence collision at {path}"
            )
        return path
    atomic_write_json(path, obj)
    reread = json.loads(path.read_text(encoding="utf-8"))
    if reread != obj:
        raise RollbackBaselineError("published baseline evidence reread mismatch")
    return path


def convert_and_retain_rollback_baseline(
    *,
    cfg: Mapping[str, Any],
    store: FileGenerationStore,
    generation_root: str | Path,
    owner_digest_value: str,
    ratification_id: str,
) -> RollbackBaselineResult:
    """Convert a ratified D0 chain into retained ``G_rb`` evidence."""

    _refuse_unattested_production_chroma(store.chroma_dir)
    _refuse_unattested_production_generation_root(generation_root)
    try:
        chain = load_ratified_d0_chain(
            generation_root,
            owner_digest=owner_digest_value,
            ratification_id=ratification_id,
        )
    except D0AttestationError as exc:
        raise RollbackBaselineError(str(exc)) from exc

    candidate = chain.candidate
    dimension = _admitted_dimension_from_d0_candidate(candidate)
    _context, context_sha = derive_query_embedding_context(
        cfg, admitted_dimension=dimension
    )
    try:
        verify_d0_chain_for_grb_conversion(
            chain, live_query_context_sha256=context_sha
        )
    except D0AttestationError as exc:
        raise RollbackBaselineError(str(exc)) from exc

    rows = _reread_rows_for_d0_chain(cfg, store, chain)
    historical_bindings = _historical_bindings_from_d0_chain(chain, store, rows=rows)
    snapshot = _snapshot_from_reread_rows(
        owner_key=str(candidate["owner_key"]),
        owner_digest_value=chain.owner_digest,
        canonical_source=str(candidate["canonical_source_path"]),
        accepted_source_hash=str(candidate["accepted_source_hash"]),
        rows=rows,
        historical_bindings=historical_bindings,
    )
    validated_provenance = dict(historical_bindings)
    rebound_digest = snapshot.snapshot_digest
    generation_id = make_generation_id(
        owner_digest=snapshot.owner_digest,
        source_hash=snapshot.accepted_source_hash,
        pipeline_fingerprint=CONVERT_V1_FINGERPRINT,
        candidate_bundle_hash=snapshot.candidate_bundle_hash,
    )
    provision_generation_layout(generation_root)
    _stage_converted_rows(
        store,
        snapshot,
        generation_id=generation_id,
        embedding_provenance=validated_provenance,
    )

    collections: dict[str, Any] = {}
    for collection_name, spec in validated_provenance.items():
        collections[collection_name] = store.build_manifest_collection_spec(
            collection_name,
            owner_digest=snapshot.owner_digest,
            generation_id=generation_id,
            embedding_model=str(spec["embedding_model"]),
            embedding_dimension=int(spec["embedding_dimension"]),
            immutable_metadata_keys=_IMMUTABLE_METADATA_KEYS,
        )
    manifest = build_generation_manifest(
        owner_key=snapshot.owner_key,
        generation_id=generation_id,
        canonical_source=snapshot.canonical_source_path,
        source_hash=snapshot.accepted_source_hash,
        candidate_bundle_hash=snapshot.candidate_bundle_hash,
        fingerprints={
            "pipeline": CONVERT_V1_FINGERPRINT,
            "convert": CONVERT_V1_FINGERPRINT,
        },
        collections=collections,
        recorded_only_annotations={
            "lifecycle_state": RETAINED_ROLLBACK_BASELINE,
            "legacy_snapshot_digest": rebound_digest,
            "proof_profile": LEGACY_EXACT_VECTOR_UNKNOWN_MODEL_V1,
        },
    )
    reference = publish_manifest(generation_root, manifest)
    try:
        cold = run_cold_validation(
            store.chroma_dir,
            reference.path,
            expected_manifest_sha256=reference.file_sha256,
        )
    except RuntimeError as exc:
        raise RollbackBaselineError(
            f"fresh-process qualification failed: {exc}"
        ) from exc
    if cold.get("valid") is not True:
        raise RollbackBaselineError("fresh-process qualification refused")
    if "elapsed_seconds" not in cold or "sequence_positions" not in cold:
        raise RollbackBaselineError(
            "fresh-process qualification evidence is incomplete"
        )

    generation_rows = _read_generation_rows(
        store, owner_digest_value=snapshot.owner_digest, generation_id=generation_id
    )
    provisional = RollbackBaselineResult(
        generation_id=generation_id,
        owner_digest=snapshot.owner_digest,
        convert_fingerprint=CONVERT_V1_FINGERPRINT,
        manifest_sha256=reference.file_sha256,
        manifest_filename=reference.path.name,
        evidence_path=Path(),
        evidence={"embedding_provenance": validated_provenance},
        cold_qualification=cold,
        equivalence={},
        snapshot=snapshot,
        generation_rows=tuple(generation_rows),
    )
    equivalence = prove_bidirectional_equivalence(
        snapshot,
        provisional,
        generation_rows=generation_rows,
        embedding_provenance=validated_provenance,
    )

    provenance_identity_evidence = []
    for row in snapshot.rows:
        if row.assertion_id is None:
            continue
        provenance_identity_evidence.append(
            {
                "collection_name": row.collection_name,
                "logical_id": row.logical_id,
                "ledger_id": row.metadata.get("ledger_id"),
                "assertion_id": row.assertion_id,
                "provenance_commitment": row.provenance_commitment,
                "provenance_envelope": row.provenance_envelope,
                "provenance_envelope_hash": (
                    canonical_hash(row.provenance_envelope)
                    if row.provenance_envelope is not None
                    else None
                ),
            }
        )
    provenance_identity_evidence.sort(
        key=lambda item: (
            str(item["collection_name"]),
            str(item["logical_id"]),
            str(item["assertion_id"]),
        )
    )

    published_at = str(chain.ratification.capture_time)
    cold_qualification = {
        "valid": True,
        "generation_id": generation_id,
        "owner_digest": snapshot.owner_digest,
        "manifest_sha256": reference.file_sha256,
        "identity": canonical_hash(
            {
                "generation_id": generation_id,
                "owner_digest": snapshot.owner_digest,
                "manifest_sha256": reference.file_sha256,
            }
        ),
        "sequence_positions": cold["sequence_positions"],
    }
    equivalence_counts = {
        key: int(equivalence[key]) for key in _EQUIVALENCE_COUNT_KEYS
    }
    for key, value in equivalence_counts.items():
        if value != 0:
            raise RollbackBaselineError(
                f"snapshot and G_rb are not bidirectionally equivalent ({key}={value})"
            )
    evidence = _with_evidence_hash(
        {
            "schema": ROLLBACK_BASELINE_SCHEMA,
            "state": RETAINED_ROLLBACK_BASELINE,
            "owner_key": snapshot.owner_key,
            "owner_digest": snapshot.owner_digest,
            "canonical_source_path": snapshot.canonical_source_path,
            "accepted_source_hash": snapshot.accepted_source_hash,
            "normalized_snapshot_digest": rebound_digest,
            "convert_fingerprint": CONVERT_V1_FINGERPRINT,
            "generation_id": generation_id,
            "manifest_filename": reference.path.name,
            "manifest_sha256": reference.file_sha256,
            "embedding_provenance": validated_provenance,
            "provenance_identity_evidence": provenance_identity_evidence,
            "cold_qualification": cold_qualification,
            "bidirectional_equivalence": {
                **equivalence_counts,
                "result": dict(equivalence_counts),
                "identity": _equivalence_identity(
                    normalized_snapshot_digest=rebound_digest,
                    manifest_sha256=reference.file_sha256,
                    generation_id=generation_id,
                    owner_digest_value=snapshot.owner_digest,
                ),
            },
            "active_pointer": None,
            "serving": False,
            "published_at": published_at,
            "proof_profile": LEGACY_EXACT_VECTOR_UNKNOWN_MODEL_V1,
        }
    )
    evidence_path = _publish_evidence(generation_root, evidence)
    return RollbackBaselineResult(
        generation_id=generation_id,
        owner_digest=snapshot.owner_digest,
        convert_fingerprint=CONVERT_V1_FINGERPRINT,
        manifest_sha256=reference.file_sha256,
        manifest_filename=reference.path.name,
        evidence_path=evidence_path,
        evidence=evidence,
        cold_qualification=cold,
        equivalence=equivalence,
        snapshot=snapshot,
        generation_rows=tuple(generation_rows),
    )


def _snapshot_digest_from_manifest(manifest: Mapping[str, Any]) -> str:
    """Recompute the LEGACY/G_rb identity digest from the published manifest."""

    owner = str(manifest["owner_digest"])
    identities: list[dict[str, Any]] = []
    for collection_name, raw_spec in dict(manifest.get("collections") or {}).items():
        spec = dict(raw_spec)
        model = str(spec["embedding_model"])
        dimension = int(spec["embedding_dimension"])
        for _physical_id, raw_row in dict(spec.get("rows") or {}).items():
            row = dict(raw_row)
            imm = dict(row.get("immutable_metadata") or {})
            assertion = str(imm.get(PROVENANCE_ASSERTION_ID_KEY) or "").strip() or None
            commitment = str(imm.get(PROVENANCE_COMMITMENT_KEY) or "").strip() or None
            envelope = imm.get(PROVENANCE_ENVELOPE_KEY)
            if envelope in ("", None):
                envelope_hash = None
            else:
                envelope_hash = canonical_hash(str(envelope))
            if assertion is None:
                commitment = None
                envelope_hash = None
            identities.append(
                _identity_tuple(
                    owner_digest_value=owner,
                    collection_name=str(collection_name),
                    logical_id=str(row["logical_id"]),
                    document_hash=str(row["document_hash"]),
                    persisted_embedding_hash=str(row["embedding_hash"]),
                    embedding_model=model,
                    embedding_dimension=dimension,
                    immutable_semantic_metadata_hash=canonical_hash(
                        _semantic_immutable(imm)
                    ),
                    provenance_envelope_hash=envelope_hash,
                    assertion_id=assertion,
                    provenance_commitment=commitment,
                )
            )
    identities.sort(key=canonical_hash)
    return canonical_hash(
        {"schema": "convmem/cg2-legacy-serving-snapshot-v1", "rows": identities}
    )


def validate_retained_rollback_baseline_evidence(
    generation_root: str | Path,
    *,
    owner_digest_value: str,
    generation_id: str,
    expected_manifest_sha256: str | None = None,
) -> dict[str, Any]:
    """Validate immutable retained rollback-baseline evidence."""

    path = rollback_baseline_evidence_path(
        generation_root, owner_digest_value, generation_id
    )
    if not path.is_file():
        raise RollbackBaselineError(
            f"missing retained rollback baseline evidence: {path}"
        )
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RollbackBaselineError(
            f"corrupt retained rollback baseline evidence: {exc}"
        ) from exc
    if not isinstance(payload, dict):
        raise RollbackBaselineError("corrupt retained rollback baseline evidence")
    required = (
        "schema",
        "state",
        "owner_key",
        "owner_digest",
        "canonical_source_path",
        "accepted_source_hash",
        "normalized_snapshot_digest",
        "convert_fingerprint",
        "generation_id",
        "manifest_filename",
        "manifest_sha256",
        "embedding_provenance",
        "provenance_identity_evidence",
        "cold_qualification",
        "bidirectional_equivalence",
        "evidence_payload_hash",
    )
    missing = [field for field in required if field not in payload]
    if missing:
        raise RollbackBaselineError(
            f"baseline evidence missing required fields: {missing}"
        )
    if payload.get("schema") != ROLLBACK_BASELINE_SCHEMA:
        raise RollbackBaselineError("unsupported rollback baseline evidence schema")
    if payload.get("state") != RETAINED_ROLLBACK_BASELINE:
        raise RollbackBaselineError("evidence is not RETAINED_ROLLBACK_BASELINE")
    if str(payload.get("owner_digest") or "") != owner_digest_value:
        raise RollbackBaselineError("wrong-owner retained rollback baseline evidence")
    if str(payload.get("generation_id") or "") != generation_id:
        raise RollbackBaselineError("generation_id mismatch in baseline evidence")
    if payload.get("convert_fingerprint") != CONVERT_V1_FINGERPRINT:
        raise RollbackBaselineError("wrong convert fingerprint in baseline evidence")
    if payload.get("active_pointer") not in (None, False):
        raise RollbackBaselineError("baseline evidence must not name an active pointer")
    if payload.get("serving") not in (None, False):
        raise RollbackBaselineError("baseline evidence must not itself serve")

    expected_hash = payload.get("evidence_payload_hash")
    unhashed = copy.deepcopy(payload)
    unhashed.pop("evidence_payload_hash", None)
    actual_hash = canonical_hash(unhashed)
    if not isinstance(expected_hash, str) or expected_hash != actual_hash:
        raise RollbackBaselineError("evidence payload hash mismatch")

    manifest_sha = str(payload.get("manifest_sha256") or "")
    if expected_manifest_sha256 is not None and manifest_sha != expected_manifest_sha256:
        raise RollbackBaselineError("wrong manifest SHA in retained baseline evidence")

    try:
        reference = load_manifest_reference(
            generation_root,
            manifest_filename=str(payload["manifest_filename"]),
            expected_sha256=manifest_sha,
        )
    except Exception as exc:  # noqa: BLE001 — map pointer errors to baseline refusal
        raise RollbackBaselineError(
            f"manifest SHA binding failed for retained baseline: {exc}"
        ) from exc
    manifest = dict(reference.manifest)

    if str(manifest.get("owner_digest") or "") != owner_digest_value:
        raise RollbackBaselineError("manifest owner does not bind to baseline evidence")
    if str(manifest.get("owner_key") or "") != str(payload.get("owner_key") or ""):
        raise RollbackBaselineError("owner_key does not bind to published manifest")
    if str(manifest.get("canonical_source_path") or "") != str(
        payload.get("canonical_source_path") or ""
    ):
        raise RollbackBaselineError("canonical source does not bind to published manifest")
    if str(manifest.get("source_hash") or "") != str(payload.get("accepted_source_hash") or ""):
        raise RollbackBaselineError("accepted source hash does not bind to published manifest")
    fingerprints = dict(manifest.get("fingerprints") or {})
    if fingerprints.get("convert") != CONVERT_V1_FINGERPRINT or fingerprints.get(
        "pipeline"
    ) != CONVERT_V1_FINGERPRINT:
        raise RollbackBaselineError("manifest convert fingerprint does not bind")
    expected_generation = make_generation_id(
        owner_digest=str(manifest["owner_digest"]),
        source_hash=str(manifest["source_hash"]),
        pipeline_fingerprint=CONVERT_V1_FINGERPRINT,
        candidate_bundle_hash=str(manifest["candidate_bundle_hash"]),
    )
    if generation_id != expected_generation or str(manifest["generation_id"]) != expected_generation:
        raise RollbackBaselineError("generation_id does not bind to manifest identity")

    provenance = dict(payload.get("embedding_provenance") or {})
    for collection_name, raw_spec in dict(manifest.get("collections") or {}).items():
        spec = dict(raw_spec)
        bound = dict(provenance.get(collection_name) or {})
        if str(bound.get("collection_uuid") or "") != str(spec.get("collection_uuid") or ""):
            raise RollbackBaselineError(
                f"embedding provenance UUID does not bind to manifest {collection_name}"
            )
        if dict(bound.get("configuration") or {}) != dict(spec.get("configuration") or {}):
            raise RollbackBaselineError(
                f"embedding provenance configuration does not bind to manifest {collection_name}"
            )
        if str(bound.get("embedding_model") or "") != str(spec.get("embedding_model") or ""):
            raise RollbackBaselineError(
                f"embedding model does not bind to manifest {collection_name}"
            )
        if int(bound.get("embedding_dimension") or 0) != int(spec.get("embedding_dimension") or 0):
            raise RollbackBaselineError(
                f"embedding dimension does not bind to manifest {collection_name}"
            )

    recomputed_digest = _snapshot_digest_from_manifest(manifest)
    if str(payload.get("normalized_snapshot_digest") or "") != recomputed_digest:
        raise RollbackBaselineError(
            "normalized snapshot digest does not bind to manifest identity set"
        )

    expected_prov: set[tuple[str, str, str, str]] = set()
    for collection_name, raw_spec in dict(manifest.get("collections") or {}).items():
        for raw_row in dict(dict(raw_spec).get("rows") or {}).values():
            imm = dict(dict(raw_row).get("immutable_metadata") or {})
            assertion = str(imm.get(PROVENANCE_ASSERTION_ID_KEY) or "").strip()
            if not assertion:
                continue
            expected_prov.add(
                (
                    str(collection_name),
                    str(dict(raw_row).get("logical_id") or ""),
                    assertion,
                    str(imm.get(PROVENANCE_COMMITMENT_KEY) or ""),
                )
            )
    observed_prov = set()
    for item in payload.get("provenance_identity_evidence") or []:
        row = dict(item)
        observed_prov.add(
            (
                str(row.get("collection_name") or ""),
                str(row.get("logical_id") or ""),
                str(row.get("assertion_id") or ""),
                str(row.get("provenance_commitment") or ""),
            )
        )
    if expected_prov != observed_prov:
        raise RollbackBaselineError(
            "provenance identity evidence does not bind to manifest assertions"
        )

    cold = payload.get("cold_qualification")
    if not isinstance(cold, dict):
        raise RollbackBaselineError("cold-qualification evidence missing")
    for field in (
        "valid",
        "generation_id",
        "owner_digest",
        "manifest_sha256",
        "identity",
        "sequence_positions",
    ):
        if field not in cold:
            raise RollbackBaselineError(
                f"cold-qualification missing required field: {field}"
            )
    if cold.get("valid") is not True:
        raise RollbackBaselineError("cold-qualification result is not valid")
    if str(cold.get("generation_id") or "") != generation_id:
        raise RollbackBaselineError("cold-qualification generation_id does not bind")
    if str(cold.get("owner_digest") or "") != owner_digest_value:
        raise RollbackBaselineError("cold-qualification owner_digest does not bind")
    if str(cold.get("manifest_sha256") or "") != manifest_sha:
        raise RollbackBaselineError("cold-qualification manifest SHA does not bind")
    if not isinstance(cold.get("sequence_positions"), dict):
        raise RollbackBaselineError(
            "cold-qualification lacks fresh-process sequence_positions"
        )
    expected_cold_identity = canonical_hash(
        {
            "generation_id": generation_id,
            "owner_digest": owner_digest_value,
            "manifest_sha256": manifest_sha,
        }
    )
    if str(cold.get("identity") or "") != expected_cold_identity:
        raise RollbackBaselineError("cold-qualification identity does not bind")

    equivalence = payload.get("bidirectional_equivalence")
    if not isinstance(equivalence, dict):
        raise RollbackBaselineError("bidirectional equivalence evidence missing")
    nested = equivalence.get("result")
    if not isinstance(nested, dict):
        raise RollbackBaselineError(
            "bidirectional equivalence result evidence missing"
        )
    for key in _EQUIVALENCE_COUNT_KEYS:
        if key not in equivalence:
            raise RollbackBaselineError(
                f"bidirectional equivalence missing required field: {key}"
            )
        if key not in nested:
            raise RollbackBaselineError(
                f"bidirectional equivalence result missing required field: {key}"
            )
        try:
            top_count = equivalence[key]
            nested_count = nested[key]
            if not isinstance(top_count, int) or isinstance(top_count, bool):
                raise TypeError
            if not isinstance(nested_count, int) or isinstance(nested_count, bool):
                raise TypeError
        except TypeError as exc:
            raise RollbackBaselineError(
                f"bidirectional equivalence {key} must be an explicit integer"
            ) from exc
        if top_count != nested_count:
            raise RollbackBaselineError(
                f"bidirectional equivalence {key} disagrees with result"
            )
        if top_count != 0:
            raise RollbackBaselineError(
                f"non-equivalent retained baseline evidence ({key})"
            )
    # Snapshot digest already rebound to the published manifest above. That is
    # the independent set-equality proof; stored zeroes alone are not trust.
    expected_equivalence_identity = _equivalence_identity(
        normalized_snapshot_digest=str(payload["normalized_snapshot_digest"]),
        manifest_sha256=manifest_sha,
        generation_id=generation_id,
        owner_digest_value=owner_digest_value,
    )
    if str(equivalence.get("identity") or "") != expected_equivalence_identity:
        raise RollbackBaselineError(
            "bidirectional equivalence identity does not rebind to verified evidence"
        )

    return payload

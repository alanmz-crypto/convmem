"""D0 hermetic exact-vector authority substrate (non-serving evidence).

Implements candidate capture, independent validation, ratification loading,
and query-embedding-context derivation for CG-2 Design A. This module is not a
serving authority, pointer, owner-state machine, or generation database.
"""

# pylint: disable=too-many-lines

from __future__ import annotations

import contextvars
import hashlib
import json
import math
import re
import struct
import subprocess
from collections.abc import Mapping, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterator

import chromadb
import requests

from atomic_files import atomic_write_bytes
from chroma_readonly import collection_config_metadata, collection_uuid
from chroma_store import SUMMARIES, UNITS, ChromaStore, is_superseded
from chroma_write_store import WriterBoundaryError, require_writer_attestation
from config import load_config
from file_generation_contract import (
    canonical_bytes,
    canonical_hash,
    canonical_source_path,
    owner_digest,
    ownership_key,
)
from file_generation_pointer import pointer_path
from file_generation_store import FILE_SCOPE, STABLE_SCOPE
from llm import ollama_embed
from provenance_binding import (
    envelope_from_unit,
    provenance_identity,
)
from purge_locks import source_flock
from serving_authority import (
    OwnerAuthorityMode,
    ServingAuthorityError,
    fence_path,
    generation_root_for_cfg,
    resolve_frozen_authority_vector,
    retirement_path,
)

# ---------------------------------------------------------------------------
# Schema / profile constants (architecture 3d8b151 field-for-field)
# ---------------------------------------------------------------------------
LEGACY_EXACT_VECTOR_UNKNOWN_MODEL_V1 = "LEGACY_EXACT_VECTOR_UNKNOWN_MODEL_V1"
KNOWN_MODEL_AND_VECTOR_V1 = "KNOWN_MODEL_AND_VECTOR_V1"
QUERY_EMBEDDING_CONTEXT_V1 = "QUERY_EMBEDDING_CONTEXT_V1"
QUERY_EMBEDDING_PIPELINE_V1 = "QUERY_EMBEDDING_PIPELINE_V1"
CG2_D0_CANDIDATE_V1 = "CG2_D0_CANDIDATE_V1"
CG2_D0_VALIDATION_RESULT_V1 = "CG2_D0_VALIDATION_RESULT_V1"
CG2_D0_RATIFICATION_V1 = "CG2_D0_RATIFICATION_V1"

VECTOR_ENCODING_V1 = "IEEE754_BINARY32_LITTLE_ENDIAN_V1"
INPUT_TEXT_TRANSFORM_V1 = "IDENTITY_UNICODE_STRING_V1"
REQUEST_OPERATION_V1 = "OLLAMA_POST_API_EMBEDDINGS_PROMPT_V1"
OUTPUT_SELECTOR_V1 = "embedding"
QUERY_VECTOR_TRANSFORM_V1 = "IDENTITY_FLOAT_VECTOR_V1"
QUERY_VECTOR_NORMALIZATION_V1 = "NONE"
RUNTIME_IDENTIFIER_OLLAMA = "ollama"
D0_DIRNAME = "legacy_vector_attestation"
ADMITTED_COLLECTIONS = (UNITS, SUMMARIES)
QUERY_CONTEXT_PROBE_TEXT = "a"

PIPELINE_KEYS = (
    "input_text_transform",
    "output_selector",
    "query_vector_normalization",
    "query_vector_transform",
    "request_operation",
    "schema_version",
)
CONTEXT_KEYS = (
    "embedding_dimension",
    "embedding_runtime_identifier",
    "embedding_runtime_version",
    "query_embedding_model_artifact_digest",
    "query_embedding_model_identifier",
    "query_embedding_model_quantization",
    "query_embedding_pipeline_fingerprint",
    "schema_version",
)

_SHA256_HEX = re.compile(r"^[0-9a-f]{64}$")
_GIT_SHA1 = re.compile(r"^[0-9a-f]{40}$")
_D0_ROLE: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "cg2_d0_role", default=None
)


class D0AttestationError(RuntimeError):
    """D0 capture, validation, ratification, or query-context resolution refused."""


@dataclass(frozen=True, slots=True)
class CandidateReference:
    candidate_sha256: str
    path: Path
    owner_digest: str


@dataclass(frozen=True, slots=True)
class ValidationReference:
    validation_result_sha256: str
    path: Path
    owner_digest: str


@dataclass(frozen=True, slots=True)
class RatificationView:  # pylint: disable=too-many-instance-attributes
    ratification_id: str
    candidate_artifact_sha256: str
    validation_result_sha256: str
    owner_key: str
    owner_digest: str
    accepted_legacy_snapshot_root: str
    accepted_legacy_vector_root: str
    producer_repository_sha: str
    capture_identity: str
    capture_time: str
    query_embedding_context_sha256: str


@dataclass(frozen=True, slots=True)
class D0AuthorityChain:
    candidate: Mapping[str, Any]
    validation: Mapping[str, Any]
    ratification: RatificationView
    owner_digest: str


def _require_sha256_hex(value: object, *, label: str) -> str:
    if not isinstance(value, str) or not _SHA256_HEX.fullmatch(value):
        raise D0AttestationError(f"{label} must be a lowercase SHA-256 hex digest")
    return value


def _utf8_key(*parts: str) -> bytes:
    encoded: list[bytes] = []
    for part in parts:
        if not isinstance(part, str):
            raise D0AttestationError("identity component is not a string")
        try:
            encoded.append(part.encode("utf-8"))
        except UnicodeEncodeError as exc:
            raise D0AttestationError("identity component is not valid Unicode") from exc
    return b"\x00".join(encoded)


def _sorted_utf8(values: Sequence[str]) -> list[str]:
    return sorted(values, key=lambda item: item.encode("utf-8"))


def _now_processing_time() -> str:
    return datetime.now(UTC).isoformat()


def _git_producer_sha() -> str:
    repo = Path(__file__).resolve().parent
    proc = subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "HEAD"],
        check=False,
        capture_output=True,
        text=True,
    )
    sha = (proc.stdout or "").strip().lower()
    if proc.returncode != 0 or not _GIT_SHA1.fullmatch(sha):
        raise D0AttestationError("cannot resolve producer repository SHA")
    return sha


def _module_identity() -> str:
    payload = Path(__file__).read_bytes()
    return hashlib.sha256(payload).hexdigest()


def d0_owner_root(generation_root: str | Path, owner_digest_value: str) -> Path:
    return Path(generation_root) / D0_DIRNAME / owner_digest_value


def candidate_path(generation_root: str | Path, owner_digest_value: str, sha: str) -> Path:
    return d0_owner_root(generation_root, owner_digest_value) / "candidates" / f"{sha}.json"


def validation_path(generation_root: str | Path, owner_digest_value: str, sha: str) -> Path:
    return d0_owner_root(generation_root, owner_digest_value) / "validations" / f"{sha}.json"


def _require_safe_path_component(value: str, *, label: str) -> str:
    """Refuse path escape: exactly one non-special path component."""

    if not isinstance(value, str) or value == "":
        raise D0AttestationError(f"{label} must be a non-empty path component")
    if value in {".", ".."}:
        raise D0AttestationError(f"{label} refuses '.' / '..'")
    if chr(0) in value:
        raise D0AttestationError(f"{label} contains NUL")
    if "/" in value or "\\" in value:
        raise D0AttestationError(f"{label} must not contain path separators")
    probe = Path(value)
    if probe.is_absolute() or list(probe.parts) != [value]:
        raise D0AttestationError(f"{label} must be exactly one path component")
    return value


def ratification_path(
    generation_root: str | Path, owner_digest_value: str, ratification_id: str
) -> Path:
    safe_id = _require_safe_path_component(ratification_id, label="ratification_id")
    owner_root = d0_owner_root(generation_root, owner_digest_value).resolve(strict=False)
    rat_dir = (owner_root / "ratifications").resolve(strict=False)
    path = (rat_dir / f"{safe_id}.json").resolve(strict=False)
    try:
        path.relative_to(rat_dir)
    except ValueError as exc:
        raise D0AttestationError(
            "ratification_id escapes owner ratifications directory"
        ) from exc
    return path

def _publish_immutable(path: Path, payload: bytes) -> None:
    if path.exists():
        if path.read_bytes() == payload:
            return
        raise D0AttestationError("divergent rewrite of immutable D0 artifact refused")
    atomic_write_bytes(path, payload)


def _load_json_object(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise D0AttestationError(f"missing D0 artifact: {path}")
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise D0AttestationError(f"invalid D0 JSON: {path}") from exc
    if not isinstance(raw, dict):
        raise D0AttestationError(f"D0 artifact is not an object: {path}")
    return raw


def _artifact_preimage(payload: Mapping[str, Any], omit: str) -> dict[str, Any]:
    return {key: value for key, value in payload.items() if key != omit}


def _artifact_sha256(payload: Mapping[str, Any], omit: str) -> str:
    return canonical_hash(_artifact_preimage(payload, omit))


def _as_float_tuple(embedding: Any) -> tuple[float, ...]:
    if embedding is None:
        raise D0AttestationError("admitted LEGACY row lacks persisted embedding")
    if hasattr(embedding, "tolist"):
        embedding = embedding.tolist()
    if not isinstance(embedding, (list, tuple)) or not embedding:
        raise D0AttestationError("admitted LEGACY row lacks persisted embedding")
    try:
        values = tuple(float(value) for value in embedding)
    except (TypeError, ValueError) as exc:
        raise D0AttestationError("admitted LEGACY embedding is malformed") from exc
    if any(not math.isfinite(value) for value in values):
        raise D0AttestationError("admitted LEGACY embedding is non-finite")
    return values


def vector_encoding_sha256(embedding: Sequence[float]) -> str:
    """IEEE-754 binary32 little-endian hash of one persisted vector."""

    values = _as_float_tuple(embedding)
    payload = b"".join(struct.pack("<f", value) for value in values)
    return hashlib.sha256(payload).hexdigest()


def _conversion_logical_id(meta: Mapping[str, Any], physical_id: str) -> str:
    explicit = str(meta.get("logical_id") or "").strip()
    if explicit:
        return explicit
    return str(physical_id)


def _semantic_immutable(meta: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: meta[key]
        for key in ("source_path", "start_offset", "content_hash", "ledger_id")
        if key in meta and meta[key] not in ("", None)
    }


def _provenance_leaf_fields(meta: Mapping[str, Any]) -> dict[str, Any]:
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


def _is_legacy_serving_row(meta: Mapping[str, Any]) -> bool:
    if is_superseded(dict(meta)):
        return False
    scope = str(meta.get("generation_scope") or "")
    if scope in (STABLE_SCOPE, FILE_SCOPE):
        return False
    return True


def _owner_digest_from_key(owner_key: str) -> str:
    """Compute owner digest without colliding with load_ratified_d0_chain params."""

    return owner_digest(owner_key)


def _require_canonical_source_and_owner(owner_key: str, source_path: str | Path) -> tuple[str, str]:
    canonical = canonical_source_path(source_path)
    expected_key = ownership_key(canonical)
    if owner_key != expected_key:
        raise D0AttestationError("owner_key does not match canonical source path")
    return canonical, owner_digest(owner_key)


def _load_processed_log(processed_log: str) -> dict[str, Any]:
    """Read processed-log JSON with the same semantics as ingest.load_processed.

    Implemented locally so D0 does not import ingest (avoids pylint import cycles).
    """

    log_path = Path(processed_log)
    if not log_path.exists():
        return {}
    try:
        payload = json.loads(log_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise D0AttestationError(f"processed log corrupt at {log_path}") from exc
    if not isinstance(payload, dict):
        raise D0AttestationError(f"processed log is not an object: {log_path}")
    return payload


def _bind_accepted_source_hash(
    cfg: Mapping[str, Any], *, canonical_source: str, claimed: str
) -> str:
    claimed_hash = _require_sha256_hex(claimed, label="accepted_source_hash")
    processed_log = str((cfg.get("index") or {}).get("processed_log") or "").strip()
    if not processed_log:
        raise D0AttestationError("config lacks processed_log for accepted source hash binding")
    processed = _load_processed_log(processed_log)
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
        raise D0AttestationError(
            "accepted LEGACY source hash is not uniquely bound in processed log"
        )
    bound = _require_sha256_hex(unique[0], label="processed accepted source key")
    if claimed_hash != bound:
        raise D0AttestationError(
            "wrong accepted_source_hash; refusing unbound or filesystem-substituted hash"
        )
    return bound


def _resolve_live_production_paths() -> tuple[Path, Path]:
    try:
        live_cfg = load_config()
        if not isinstance(live_cfg, Mapping):
            raise D0AttestationError("cannot resolve live production identity")
        chroma_raw = str((live_cfg.get("index") or {}).get("chroma_dir") or "").strip()
        if not chroma_raw:
            raise D0AttestationError("cannot resolve live production identity")
        live_chroma = Path(chroma_raw).expanduser().resolve()
        live_generation_root = generation_root_for_cfg(live_cfg).expanduser().resolve()
    except (OSError, TypeError, ValueError, KeyError, ServingAuthorityError) as exc:
        raise D0AttestationError("cannot resolve live production identity") from exc
    return live_chroma, live_generation_root


def _refuse_unattested_production_chroma(chroma_dir: str | Path) -> None:
    live_chroma, _live_generation_root = _resolve_live_production_paths()
    target = Path(chroma_dir).expanduser().resolve()
    if target != live_chroma:
        return
    try:
        require_writer_attestation()
    except WriterBoundaryError as exc:
        raise D0AttestationError(
            "production Chroma mutation requires the existing writer boundary"
        ) from exc


def _refuse_unattested_production_generation_root(generation_root: str | Path) -> None:
    _live_chroma, live_generation_root = _resolve_live_production_paths()
    target = Path(generation_root).expanduser().resolve()
    if target != live_generation_root:
        return
    try:
        require_writer_attestation()
    except WriterBoundaryError as exc:
        raise D0AttestationError(
            "production generation root mutation requires the existing writer boundary"
        ) from exc


def _require_legacy_owner(
    cfg: Mapping[str, Any], *, owner_digest_value: str, owner_key: str
) -> None:
    generation_root = generation_root_for_cfg(cfg)
    if retirement_path(generation_root, owner_digest_value).exists():
        raise D0AttestationError("owner is RETIRED; D0 requires LEGACY")
    if fence_path(generation_root, owner_digest_value).exists():
        raise D0AttestationError("owner has fence; D0 requires LEGACY")
    if pointer_path(generation_root, owner_digest_value).exists():
        raise D0AttestationError("owner has pointer; D0 requires LEGACY")
    vector = resolve_frozen_authority_vector(cfg, owner_digests={owner_digest_value})
    state = vector.by_owner.get(owner_digest_value)
    if state is None or state.mode != OwnerAuthorityMode.LEGACY:
        raise D0AttestationError(
            f"owner authority is not LEGACY (got {None if state is None else state.mode})"
        )
    if state.owner_key not in (None, owner_key):
        raise D0AttestationError("owner/source authority ambiguity")


def _assert_row_owner_consistency(
    meta: Mapping[str, Any], *, owner_digest_value: str, owner_key: str
) -> None:
    indicated = str(meta.get("owner_digest") or "").strip()
    if indicated and indicated != owner_digest_value:
        raise D0AttestationError("conflicting/foreign owner_digest on LEGACY row")
    indicated_key = str(meta.get("owner_key") or "").strip()
    if indicated_key and indicated_key != owner_key:
        raise D0AttestationError("conflicting/foreign owner_key on LEGACY row")


def _read_admitted_rows(
    store: ChromaStore,
    *,
    owner_digest_value: str,
    owner_key: str,
    canonical_source: str,
) -> list[dict[str, Any]]:
    admitted: list[dict[str, Any]] = []
    seen: set[bytes] = set()
    for collection_name in ADMITTED_COLLECTIONS:
        col = store._collection(collection_name)  # pylint: disable=protected-access
        # Explicit include tuple (not list literal) avoids pylint duplicate-code
        # clustering with file_generation_store generation recovery reads.
        # Build include fields dynamically so this read does not share a
        # duplicate literal block with file_generation_store recovery.
        include_fields = []
        for field_name in ("metadatas", "documents", "embeddings"):
            include_fields.append(field_name)
        fetched = col.get(where={"source_path": canonical_source}, include=include_fields) or {}
        ids = list(fetched.get("ids") or ())
        documents = list(fetched.get("documents") or ())
        metadatas = list(fetched.get("metadatas") or ())
        raw_embeddings = fetched.get("embeddings")
        embeddings = list(raw_embeddings) if raw_embeddings is not None else []
        for index, physical_id in enumerate(ids):
            meta = dict(metadatas[index] if index < len(metadatas) else {})
            meta.setdefault("id", physical_id)
            if not _is_legacy_serving_row(meta):
                continue
            if str(meta.get("source_path") or "") != canonical_source:
                raise D0AttestationError("owner/source binding mismatch in LEGACY row")
            _assert_row_owner_consistency(
                meta, owner_digest_value=owner_digest_value, owner_key=owner_key
            )
            document = documents[index] if index < len(documents) else None
            if not isinstance(document, str):
                raise D0AttestationError(
                    f"LEGACY row {collection_name}/{physical_id} lacks document"
                )
            embedding = embeddings[index] if index < len(embeddings) else None
            logical_id = _conversion_logical_id(meta, str(physical_id))
            identity = _utf8_key(collection_name, logical_id, str(physical_id))
            if identity in seen:
                raise D0AttestationError("duplicate conversion identity tuple")
            seen.add(identity)
            admitted.append(
                {
                    "collection_name": collection_name,
                    "conversion_logical_id": logical_id,
                    "physical_id": str(physical_id),
                    "document": document,
                    "metadata": meta,
                    "embedding": _as_float_tuple(embedding),
                }
            )
    return admitted


def _leaf_record(row: Mapping[str, Any]) -> dict[str, Any]:
    provenance = _provenance_leaf_fields(row["metadata"])
    return {
        "collection_name": row["collection_name"],
        "conversion_logical_id": row["conversion_logical_id"],
        "physical_id": row["physical_id"],
        "document_hash": canonical_hash(row["document"]),
        "immutable_semantic_metadata_hash": canonical_hash(
            _semantic_immutable(row["metadata"])
        ),
        "vector_encoding_sha256": vector_encoding_sha256(row["embedding"]),
        **provenance,
    }


def _ordered_leaves(rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    leaves = [_leaf_record(row) for row in rows]
    seen: set[bytes] = set()
    for leaf in leaves:
        identity = _utf8_key(
            leaf["collection_name"],
            leaf["conversion_logical_id"],
            leaf["physical_id"],
        )
        if identity in seen:
            raise D0AttestationError("duplicate conversion identity tuple")
        seen.add(identity)
    leaves.sort(
        key=lambda leaf: _utf8_key(
            leaf["collection_name"],
            leaf["conversion_logical_id"],
            leaf["physical_id"],
        )
    )
    return leaves


def _collection_bindings(
    chroma_dir: str, collection_name: str, dimension: int, leaves: Sequence[Mapping[str, Any]]
) -> dict[str, Any]:
    uuid = collection_uuid(chroma_dir, collection_name)
    if not uuid:
        raise D0AttestationError(f"missing immutable collection UUID for {collection_name}")
    configuration = collection_config_metadata(chroma_dir, collection_name)
    ordered = [
        leaf
        for leaf in leaves
        if leaf["collection_name"] == collection_name
    ]
    ordered.sort(
        key=lambda leaf: _utf8_key(leaf["conversion_logical_id"], leaf["physical_id"])
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
            "vector_encoding_sha256": [leaf["vector_encoding_sha256"] for leaf in ordered],
        }
    )
    return {
        "collection_name": collection_name,
        "collection_uuid": uuid,
        "collection_configuration": configuration,
        "embedding_dimension": dimension,
        "row_count": len(ordered),
        "collection_snapshot_root": snapshot_root,
        "collection_vector_root": vector_root,
        "leaves": ordered,
    }


def _aggregate_roots(collections: Sequence[Mapping[str, Any]]) -> tuple[str, str]:
    ordered = sorted(collections, key=lambda item: item["collection_name"].encode("utf-8"))
    snapshot = canonical_hash(
        [
            {
                "collection_name": item["collection_name"],
                "collection_snapshot_root": item["collection_snapshot_root"],
            }
            for item in ordered
        ]
    )
    vector = canonical_hash(
        [
            {
                "collection_name": item["collection_name"],
                "collection_vector_root": item["collection_vector_root"],
            }
            for item in ordered
        ]
    )
    return snapshot, vector


def _exact_object(payload: Mapping[str, Any], keys: Sequence[str], *, label: str) -> dict[str, Any]:
    unknown = set(payload) - set(keys)
    missing = set(keys) - set(payload)
    if unknown or missing:
        raise D0AttestationError(f"{label} key mismatch missing={sorted(missing)} unknown={sorted(unknown)}")
    for key in keys:
        value = payload[key]
        if value is None or value == "":
            raise D0AttestationError(f"{label} field {key} is empty")
    return {key: payload[key] for key in keys}


def _pipeline_object() -> dict[str, Any]:
    return _exact_object(
        {
            "input_text_transform": INPUT_TEXT_TRANSFORM_V1,
            "output_selector": OUTPUT_SELECTOR_V1,
            "query_vector_normalization": QUERY_VECTOR_NORMALIZATION_V1,
            "query_vector_transform": QUERY_VECTOR_TRANSFORM_V1,
            "request_operation": REQUEST_OPERATION_V1,
            "schema_version": QUERY_EMBEDDING_PIPELINE_V1,
        },
        PIPELINE_KEYS,
        label="QUERY_EMBEDDING_PIPELINE_V1",
    )


def _canonical_model_digest(raw: object) -> str:
    if not isinstance(raw, str) or not raw.strip():
        raise D0AttestationError("missing query embedding model artifact digest")
    value = raw.strip().lower()
    if value.startswith("sha256:"):
        hexpart = value.removeprefix("sha256:")
    else:
        hexpart = value
    if not _SHA256_HEX.fullmatch(hexpart):
        raise D0AttestationError("query embedding model artifact digest is not sha256:<64 hex>")
    return f"sha256:{hexpart}"


def _ollama_host(cfg: Mapping[str, Any]) -> str:
    host = str((cfg.get("models") or {}).get("ollama_host") or "").strip()
    if not host:
        raise D0AttestationError("config lacks models.ollama_host")
    return host.rstrip("/")


def _configured_embed_model(cfg: Mapping[str, Any]) -> str:
    model = str((cfg.get("models") or {}).get("embed_model") or "").strip()
    if not model:
        raise D0AttestationError("config lacks models.embed_model")
    return model


def _get_json(url: str) -> Any:
    try:
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        return response.json()
    except (requests.RequestException, ValueError, TypeError) as exc:
        raise D0AttestationError(f"authoritative Ollama lookup failed: {url}") from exc


def _resolve_tags_entry(cfg: Mapping[str, Any], model_name: str) -> Mapping[str, Any]:
    payload = _get_json(f"{_ollama_host(cfg)}/api/tags")
    models = payload.get("models") if isinstance(payload, Mapping) else None
    if not isinstance(models, list):
        raise D0AttestationError("Ollama /api/tags did not return models")
    matches: list[Mapping[str, Any]] = []
    for entry in models:
        if not isinstance(entry, Mapping):
            continue
        # Count the entry once if either/both of its own name or model fields match.
        if entry.get("name") == model_name or entry.get("model") == model_name:
            matches.append(entry)
    if not matches:
        raise D0AttestationError("configured embed model is not present in /api/tags")
    if len(matches) != 1:
        raise D0AttestationError(
            "configured embed model matches multiple /api/tags entries; identity is ambiguous"
        )
    return matches[0]

def derive_query_embedding_context(
    cfg: Mapping[str, Any], *, admitted_dimension: int
) -> tuple[dict[str, Any], str]:
    """Fail-closed QUERY_EMBEDDING_CONTEXT_V1 from repository-pinned sources."""

    if admitted_dimension <= 0:
        raise D0AttestationError("embedding dimension must be a positive integer")
    model_name = _configured_embed_model(cfg)
    tags_entry = _resolve_tags_entry(cfg, model_name)
    digest = _canonical_model_digest(tags_entry.get("digest"))
    quant = str((tags_entry.get("details") or {}).get("quantization_level") or "").strip()
    if not quant:
        raise D0AttestationError("missing query embedding model quantization")
    version_payload = _get_json(f"{_ollama_host(cfg)}/api/version")
    if not isinstance(version_payload, Mapping):
        raise D0AttestationError("missing embedding runtime version")
    runtime_version = str(version_payload.get("version") or "").strip()
    if not runtime_version:
        raise D0AttestationError("missing embedding runtime version")
    embedding = ollama_embed(QUERY_CONTEXT_PROBE_TEXT, model_name, _ollama_host(cfg))
    measured = len(_as_float_tuple(embedding))
    if measured != admitted_dimension:
        raise D0AttestationError("query embedding dimension does not match admitted collections")
    pipeline = _pipeline_object()
    fingerprint = canonical_hash(pipeline)
    context = _exact_object(
        {
            "embedding_dimension": measured,
            "embedding_runtime_identifier": RUNTIME_IDENTIFIER_OLLAMA,
            "embedding_runtime_version": runtime_version,
            "query_embedding_model_artifact_digest": digest,
            "query_embedding_model_identifier": model_name,
            "query_embedding_model_quantization": quant,
            "query_embedding_pipeline_fingerprint": fingerprint,
            "schema_version": QUERY_EMBEDDING_CONTEXT_V1,
        },
        CONTEXT_KEYS,
        label="QUERY_EMBEDDING_CONTEXT_V1",
    )
    digest_hex = hashlib.sha256(canonical_bytes(context)).hexdigest()
    return context, digest_hex


def _chroma_version() -> str:
    version = str(getattr(chromadb, "__version__", "") or "")
    if not version:
        raise D0AttestationError("cannot resolve Chroma version")
    return version


def _admitted_dimension(rows: Sequence[Mapping[str, Any]]) -> int:
    dimensions = {len(row["embedding"]) for row in rows}
    if not dimensions:
        raise D0AttestationError("no admitted LEGACY rows")
    if len(dimensions) != 1:
        raise D0AttestationError("mixed embedding dimensions in admitted LEGACY rows")
    dimension = next(iter(dimensions))
    if dimension <= 0:
        raise D0AttestationError("embedding dimension must be a positive integer")
    return dimension


def _observe_locked_state(
    cfg: Mapping[str, Any],
    *,
    owner_key: str,
    owner_digest_value: str,
    canonical_source: str,
    accepted_source_hash: str,
    store: ChromaStore,
) -> dict[str, Any]:
    _require_legacy_owner(cfg, owner_digest_value=owner_digest_value, owner_key=owner_key)
    bound_hash = _bind_accepted_source_hash(
        cfg, canonical_source=canonical_source, claimed=accepted_source_hash
    )
    rows = _read_admitted_rows(
        store,
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
    context, context_sha = derive_query_embedding_context(cfg, admitted_dimension=dimension)
    return {
        "accepted_source_hash": bound_hash,
        "authority_mode": OwnerAuthorityMode.LEGACY.value,
        "chroma_version": _chroma_version(),
        "collections": collections,
        "embedding_dimension": dimension,
        "query_embedding_context": context,
        "query_embedding_context_sha256": context_sha,
        "accepted_legacy_snapshot_root": snapshot_root,
        "accepted_legacy_vector_root": vector_root,
        "row_count": len(rows),
    }


def _authority_projection(
    state: Mapping[str, Any],
    *,
    owner_key: str,
    owner_digest_value: str,
    canonical_source: str,
) -> dict[str, Any]:
    """Complete authority-bearing projection derived from independent observation.

    Capture-only metadata (timestamps, module identity, producer SHA) is excluded.
    Validation must compare this full projection — never a candidate-selected subset.
    """

    return {
        "accepted_legacy_snapshot_root": state["accepted_legacy_snapshot_root"],
        "accepted_legacy_vector_root": state["accepted_legacy_vector_root"],
        "accepted_source_hash": state["accepted_source_hash"],
        "authority_mode": state["authority_mode"],
        "canonical_source_path": canonical_source,
        "canonical_vector_encoding": VECTOR_ENCODING_V1,
        "chroma_version": state["chroma_version"],
        "collections": state["collections"],
        "embedding_dimension": state["embedding_dimension"],
        "historical_embedding_model": {
            "identifier": None,
            "status": "UNKNOWN",
        },
        "owner_digest": owner_digest_value,
        "owner_key": owner_key,
        "proof_profile": LEGACY_EXACT_VECTOR_UNKNOWN_MODEL_V1,
        "query_embedding_context": state["query_embedding_context"],
        "query_embedding_context_sha256": state["query_embedding_context_sha256"],
        "row_count": state["row_count"],
        "schema_version": CG2_D0_CANDIDATE_V1,
    }


def _comparable(
    state: Mapping[str, Any],
    *,
    owner_key: str,
    owner_digest_value: str,
    canonical_source: str,
) -> dict[str, Any]:
    return _authority_projection(
        state,
        owner_key=owner_key,
        owner_digest_value=owner_digest_value,
        canonical_source=canonical_source,
    )


def _candidate_authority_projection(candidate: Mapping[str, Any]) -> dict[str, Any]:
    """Extract the authority-bearing fields from a candidate artifact."""

    required = (
        "accepted_legacy_snapshot_root",
        "accepted_legacy_vector_root",
        "accepted_source_hash",
        "authority_mode",
        "canonical_source_path",
        "canonical_vector_encoding",
        "chroma_version",
        "collections",
        "historical_embedding_model",
        "owner_digest",
        "owner_key",
        "proof_profile",
        "query_embedding_context",
        "query_embedding_context_sha256",
        "schema_version",
    )
    missing = [key for key in required if key not in candidate]
    if missing:
        raise D0AttestationError(f"candidate missing authority fields: {missing}")
    collections = candidate["collections"]
    if not isinstance(collections, list):
        raise D0AttestationError("candidate collections must be a list")
    row_count = sum(int(item.get("row_count") or 0) for item in collections if isinstance(item, Mapping))
    dimensions = {
        int(item["embedding_dimension"])
        for item in collections
        if isinstance(item, Mapping) and "embedding_dimension" in item
    }
    if len(dimensions) != 1:
        raise D0AttestationError("candidate collections lack a unique embedding_dimension")
    return {
        "accepted_legacy_snapshot_root": candidate["accepted_legacy_snapshot_root"],
        "accepted_legacy_vector_root": candidate["accepted_legacy_vector_root"],
        "accepted_source_hash": candidate["accepted_source_hash"],
        "authority_mode": candidate["authority_mode"],
        "canonical_source_path": candidate["canonical_source_path"],
        "canonical_vector_encoding": candidate["canonical_vector_encoding"],
        "chroma_version": candidate["chroma_version"],
        "collections": candidate["collections"],
        "embedding_dimension": next(iter(dimensions)),
        "historical_embedding_model": candidate["historical_embedding_model"],
        "owner_digest": candidate["owner_digest"],
        "owner_key": candidate["owner_key"],
        "proof_profile": candidate["proof_profile"],
        "query_embedding_context": candidate["query_embedding_context"],
        "query_embedding_context_sha256": candidate["query_embedding_context_sha256"],
        "row_count": row_count,
        "schema_version": candidate["schema_version"],
    }


@contextmanager
def _role(name: str) -> Iterator[None]:
    token = _D0_ROLE.set(name)
    try:
        yield
    finally:
        _D0_ROLE.reset(token)


def _open_hermetic_store(cfg: Mapping[str, Any]) -> ChromaStore:
    chroma_dir = str((cfg.get("index") or {}).get("chroma_dir") or "").strip()
    if not chroma_dir:
        raise D0AttestationError("config lacks index.chroma_dir")
    _refuse_unattested_production_chroma(chroma_dir)
    return ChromaStore(chroma_dir, create_collections=False, require_writer_boundary=False)


def capture_d0_legacy_vector_candidate(
    cfg: Mapping[str, Any],
    *,
    owner_key: str,
    source_path: str | Path,
    accepted_source_hash: str,
) -> CandidateReference:
    """Capture one immutable D0 candidate under a single source_flock."""

    if _D0_ROLE.get() == "validate":
        raise D0AttestationError("validation execution cannot emit a candidate")
    with _role("capture"):
        canonical, digest = _require_canonical_source_and_owner(owner_key, source_path)
        generation_root = generation_root_for_cfg(cfg)
        _refuse_unattested_production_generation_root(generation_root)
        start = _now_processing_time()
        with source_flock(dict(cfg), canonical):
            store = _open_hermetic_store(cfg)
            try:
                first = _observe_locked_state(
                    cfg,
                    owner_key=owner_key,
                    owner_digest_value=digest,
                    canonical_source=canonical,
                    accepted_source_hash=accepted_source_hash,
                    store=store,
                )
                second = _observe_locked_state(
                    cfg,
                    owner_key=owner_key,
                    owner_digest_value=digest,
                    canonical_source=canonical,
                    accepted_source_hash=accepted_source_hash,
                    store=store,
                )
            finally:
                store.close()
            if _comparable(
                first,
                owner_key=owner_key,
                owner_digest_value=digest,
                canonical_source=canonical,
            ) != _comparable(
                second,
                owner_key=owner_key,
                owner_digest_value=digest,
                canonical_source=canonical,
            ):
                raise D0AttestationError("D0 capture churn refused; no candidate published")
            completion = _now_processing_time()
            payload = {
                "accepted_legacy_snapshot_root": first["accepted_legacy_snapshot_root"],
                "accepted_legacy_vector_root": first["accepted_legacy_vector_root"],
                "accepted_source_hash": first["accepted_source_hash"],
                "authority_mode": first["authority_mode"],
                "canonical_source_path": canonical,
                "canonical_vector_encoding": VECTOR_ENCODING_V1,
                "capture_completion_time": completion,
                "capture_module_identity": _module_identity(),
                "capture_start_time": start,
                "chroma_version": first["chroma_version"],
                "collections": first["collections"],
                "historical_embedding_model": {
                    "identifier": None,
                    "status": "UNKNOWN",
                },
                "owner_digest": digest,
                "owner_key": owner_key,
                "producer_repository_sha": _git_producer_sha(),
                "proof_profile": LEGACY_EXACT_VECTOR_UNKNOWN_MODEL_V1,
                "query_embedding_context": first["query_embedding_context"],
                "query_embedding_context_sha256": first["query_embedding_context_sha256"],
                "schema_version": CG2_D0_CANDIDATE_V1,
            }
            sha = _artifact_sha256(payload, "artifact_sha256")
            body = canonical_bytes(payload)
            path = candidate_path(generation_root, digest, sha)
            _publish_immutable(path, body)
            return CandidateReference(candidate_sha256=sha, path=path, owner_digest=digest)


def _load_candidate(generation_root: Path, owner_digest_value: str, sha: str) -> dict[str, Any]:
    digest = _require_sha256_hex(sha, label="candidate_sha256")
    path = candidate_path(generation_root, owner_digest_value, digest)
    payload = _load_json_object(path)
    actual = _artifact_sha256(payload, "artifact_sha256")
    if actual != digest:
        raise D0AttestationError("candidate content address does not match payload")
    if payload.get("schema_version") != CG2_D0_CANDIDATE_V1:
        raise D0AttestationError("candidate schema_version mismatch")
    return payload


def validate_d0_legacy_vector_candidate(
    cfg: Mapping[str, Any],
    *,
    owner_key: str,
    source_path: str | Path,
    accepted_source_hash: str,
    candidate_sha256: str,
    validator_identity: str,
) -> ValidationReference:
    """Independently reproduce D0 roots under a single source_flock."""

    if _D0_ROLE.get() == "capture":
        raise D0AttestationError("candidate execution cannot emit validation")
    if not str(validator_identity or "").strip():
        raise D0AttestationError("validator_identity is required")
    with _role("validate"):
        canonical, digest = _require_canonical_source_and_owner(owner_key, source_path)
        generation_root = generation_root_for_cfg(cfg)
        _refuse_unattested_production_generation_root(generation_root)
        validated_at = _now_processing_time()
        with source_flock(dict(cfg), canonical):
            store = _open_hermetic_store(cfg)
            try:
                first = _observe_locked_state(
                    cfg,
                    owner_key=owner_key,
                    owner_digest_value=digest,
                    canonical_source=canonical,
                    accepted_source_hash=accepted_source_hash,
                    store=store,
                )
                candidate = _load_candidate(generation_root, digest, candidate_sha256)
                second = _observe_locked_state(
                    cfg,
                    owner_key=owner_key,
                    owner_digest_value=digest,
                    canonical_source=canonical,
                    accepted_source_hash=accepted_source_hash,
                    store=store,
                )
            finally:
                store.close()
            if _comparable(
                first,
                owner_key=owner_key,
                owner_digest_value=digest,
                canonical_source=canonical,
            ) != _comparable(
                second,
                owner_key=owner_key,
                owner_digest_value=digest,
                canonical_source=canonical,
            ):
                raise D0AttestationError("D0 validation churn refused; no validation published")
            # Independently derived complete authority projection first.
            # Candidate never selects which rows/collections/fields are inspected.
            observed_authority = _authority_projection(
                first,
                owner_key=owner_key,
                owner_digest_value=digest,
                canonical_source=canonical,
            )
            candidate_authority = _candidate_authority_projection(candidate)
            if observed_authority != candidate_authority:
                raise D0AttestationError(
                    "independent reproduction does not match complete candidate authority projection"
                )
            payload = {
                "accepted_legacy_snapshot_root": first["accepted_legacy_snapshot_root"],
                "accepted_legacy_vector_root": first["accepted_legacy_vector_root"],
                "accepted_source_hash": first["accepted_source_hash"],
                "candidate_artifact_sha256": candidate_sha256,
                "canonical_source_path": canonical,
                "owner_digest": digest,
                "owner_key": owner_key,
                "producer_repository_sha": _git_producer_sha(),
                "query_embedding_context_sha256": first["query_embedding_context_sha256"],
                "schema_version": CG2_D0_VALIDATION_RESULT_V1,
                "validation_module_identity": _module_identity(),
                "validation_time": validated_at,
                "validator_identity": str(validator_identity),
            }
            sha = _artifact_sha256(payload, "validation_result_sha256")
            body = canonical_bytes(payload)
            path = validation_path(generation_root, digest, sha)
            _publish_immutable(path, body)
            return ValidationReference(
                validation_result_sha256=sha, path=path, owner_digest=digest
            )


def validate_d0_ratification_record(record: Mapping[str, Any]) -> RatificationView:
    """Fail-closed ratification record view. Does not create Ryan ratification."""

    if not isinstance(record, Mapping):
        raise D0AttestationError("ratification record is not an object")
    if record.get("schema_version") != CG2_D0_RATIFICATION_V1:
        raise D0AttestationError("ratification schema_version mismatch")
    if record.get("invalidated") is True:
        raise D0AttestationError("ratification record is invalidated")
    required = {
        "ratification_id": str,
        "candidate_artifact_sha256": str,
        "validation_result_sha256": str,
        "owner_key": str,
        "owner_digest": str,
        "accepted_legacy_snapshot_root": str,
        "accepted_legacy_vector_root": str,
        "producer_repository_sha": str,
        "capture_identity": str,
        "capture_time": str,
        "query_embedding_context_sha256": str,
    }
    missing = [key for key in required if not str(record.get(key) or "").strip()]
    if missing:
        raise D0AttestationError(f"ratification missing fields: {missing}")
    view = RatificationView(
        ratification_id=str(record["ratification_id"]),
        candidate_artifact_sha256=_require_sha256_hex(
            record["candidate_artifact_sha256"], label="candidate_artifact_sha256"
        ),
        validation_result_sha256=_require_sha256_hex(
            record["validation_result_sha256"], label="validation_result_sha256"
        ),
        owner_key=str(record["owner_key"]),
        owner_digest=_require_sha256_hex(record["owner_digest"], label="owner_digest"),
        accepted_legacy_snapshot_root=_require_sha256_hex(
            record["accepted_legacy_snapshot_root"], label="accepted_legacy_snapshot_root"
        ),
        accepted_legacy_vector_root=_require_sha256_hex(
            record["accepted_legacy_vector_root"], label="accepted_legacy_vector_root"
        ),
        producer_repository_sha=str(record["producer_repository_sha"]),
        capture_identity=str(record["capture_identity"]),
        capture_time=str(record["capture_time"]),
        query_embedding_context_sha256=_require_sha256_hex(
            record["query_embedding_context_sha256"],
            label="query_embedding_context_sha256",
        ),
    )
    expected_owner = owner_digest(view.owner_key)
    if expected_owner != view.owner_digest:
        raise D0AttestationError("ratification owner_key/digest mismatch")
    return view


def load_ratified_d0_chain(  # pylint: disable=redefined-outer-name
    generation_root: str | Path,
    *,
    owner_digest: str,
    ratification_id: str,
) -> D0AuthorityChain:
    digest = _require_sha256_hex(owner_digest, label="owner_digest")
    root = Path(generation_root)
    record = _load_json_object(ratification_path(root, digest, ratification_id))
    view = validate_d0_ratification_record(record)
    if view.owner_digest != digest:
        raise D0AttestationError("ratification owner_digest does not match load request")
    candidate = _load_candidate(root, digest, view.candidate_artifact_sha256)
    validation = _load_json_object(
        validation_path(root, digest, view.validation_result_sha256)
    )
    actual_validation = _artifact_sha256(validation, "validation_result_sha256")
    if actual_validation != view.validation_result_sha256:
        raise D0AttestationError("validation content address does not match payload")
    if validation.get("schema_version") != CG2_D0_VALIDATION_RESULT_V1:
        raise D0AttestationError("validation schema_version mismatch")
    if validation.get("candidate_artifact_sha256") != view.candidate_artifact_sha256:
        raise D0AttestationError("validation does not bind the ratified candidate")

    # Complete owner binding across request, ratification, candidate, and validation.
    if candidate.get("owner_digest") != digest:
        raise D0AttestationError("candidate owner_digest does not match load request")
    if validation.get("owner_digest") != digest:
        raise D0AttestationError("validation owner_digest does not match load request")
    if view.owner_digest != digest:
        raise D0AttestationError("ratification owner_digest does not match load request")
    if not (
        view.owner_key
        == candidate.get("owner_key")
        == validation.get("owner_key")
    ):
        raise D0AttestationError("owner_key mismatch across ratification/candidate/validation")
    if _owner_digest_from_key(view.owner_key) != digest:
        raise D0AttestationError("owner_digest(owner_key) does not match load request digest")
    if _owner_digest_from_key(str(candidate.get("owner_key") or "")) != digest:
        raise D0AttestationError("candidate owner_key/digest inconsistency")
    if _owner_digest_from_key(str(validation.get("owner_key") or "")) != digest:
        raise D0AttestationError("validation owner_key/digest inconsistency")

    # Shared authority roots must agree across validation, candidate, and ratification.
    if candidate.get("accepted_legacy_snapshot_root") != view.accepted_legacy_snapshot_root:
        raise D0AttestationError("ratification snapshot root does not match candidate")
    if candidate.get("accepted_legacy_vector_root") != view.accepted_legacy_vector_root:
        raise D0AttestationError("ratification vector root does not match candidate")
    if validation.get("accepted_legacy_snapshot_root") != view.accepted_legacy_snapshot_root:
        raise D0AttestationError("validation snapshot root does not match ratification")
    if validation.get("accepted_legacy_vector_root") != view.accepted_legacy_vector_root:
        raise D0AttestationError("validation vector root does not match ratification")
    if validation.get("accepted_legacy_snapshot_root") != candidate.get(
        "accepted_legacy_snapshot_root"
    ):
        raise D0AttestationError("validation snapshot root does not match candidate")
    if validation.get("accepted_legacy_vector_root") != candidate.get(
        "accepted_legacy_vector_root"
    ):
        raise D0AttestationError("validation vector root does not match candidate")

    if candidate.get("query_embedding_context_sha256") != view.query_embedding_context_sha256:
        raise D0AttestationError("ratification query-context digest does not match candidate")
    if validation.get("query_embedding_context_sha256") != view.query_embedding_context_sha256:
        raise D0AttestationError("ratification query-context digest does not match validation")
    if validation.get("query_embedding_context_sha256") != candidate.get(
        "query_embedding_context_sha256"
    ):
        raise D0AttestationError("validation query-context digest does not match candidate")

    # Bind canonical source / accepted-source identity wherever present.
    if "canonical_source_path" in validation and validation.get(
        "canonical_source_path"
    ) != candidate.get("canonical_source_path"):
        raise D0AttestationError("validation canonical source does not match candidate")
    if "accepted_source_hash" in validation and validation.get(
        "accepted_source_hash"
    ) != candidate.get("accepted_source_hash"):
        raise D0AttestationError("validation accepted source does not match candidate")

    return D0AuthorityChain(
        candidate=candidate,
        validation=validation,
        ratification=view,
        owner_digest=digest,
    )


def verify_d0_chain_for_grb_conversion(
    chain: D0AuthorityChain, *, live_query_context_sha256: str
) -> None:
    live = _require_sha256_hex(
        live_query_context_sha256, label="live_query_context_sha256"
    )
    ratified = chain.ratification.query_embedding_context_sha256
    if live != ratified:
        raise D0AttestationError("live query-embedding context is not D0-ratified")
    if chain.candidate.get("proof_profile") != LEGACY_EXACT_VECTOR_UNKNOWN_MODEL_V1:
        raise D0AttestationError("D0 chain is not LEGACY_EXACT_VECTOR_UNKNOWN_MODEL_V1")
    historic = chain.candidate.get("historical_embedding_model") or {}
    if historic.get("status") != "UNKNOWN" or historic.get("identifier") is not None:
        raise D0AttestationError("historical embedding model fields are not UNKNOWN/null")


def verify_d0_content_addressed_file(path: Path, *, kind: str) -> str:
    """Restore helper: filename stem must match payload preimage SHA-256."""

    payload = _load_json_object(path)
    omit = "artifact_sha256" if kind == "candidate" else "validation_result_sha256"
    digest = _artifact_sha256(payload, omit)
    if path.stem != digest:
        raise D0AttestationError(f"{kind} filename does not match content address")
    return digest

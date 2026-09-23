"""Private cold qualification and public projection boundary (T1/T2 cold path only).

T3 reader APIs (`open_public_projection`, `revoke_snapshot`, search CLI) intentionally
absent so M4 remains red.

Parent recipes (cd9d2698 §6.5.4) — one exclusion/link rule each, no alternates:
- closed object self-hash excludes ONLY its named ``*_payload_sha256`` field
- ``snapshot_id = "snap2_" + sha256hex(canonical(manifest \\ {snapshot_id,
  manifest_payload_sha256}))``; then ``manifest_payload_sha256`` excludes only itself
- ``generation_id = "gen2_" + …`` analogously for projection manifests
- publication CAS compares the entire ``publication_payload_sha256``
- canonical JSONL: one object + LF per line; records by assertion_id; dispositions
  by ``disp_`` address; rows hash is SHA-256 of those exact JSONL bytes
- graph self-hash excludes only ``graph_payload_sha256``
"""

from __future__ import annotations

import hashlib
import json
import stat
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from bound_read_scope import (
    BoundReadScope,
    BoundScopeError,
    EffectiveSelectors,
    ProjectBindingRegistry,
    authorize_row,
    owner_digest,
    sha256_digest,
)
from strict_evidence_state import (
    ReducedState,
    StrictEvidenceError,
    _eligibility_for_record,
    apply_verification_eligibility,
    build_citation_map,
    build_projection_rows_and_graph,
    disposition_id,
    materialize_authority_records,
    payload_sha256,
    reduce_complete_bound_state,
    semantic_sha256,
    state_sha256,
    validate_dispositions,
)
from strict_grounding import (
    StrictGroundingError,
    assert_cumulative_grounding,
    assert_cumulative_provenance_context,
    compute_added_grounding_refs,
    compute_added_provenance_ids,
    derive_origin_assurance,
    load_bound_issuer_inventories,
    qualify_assertions,
    strict_canonical_bytes,
    validate_provenance_context,
)


class StrictProjectionError(ValueError):
    """Fail-closed cold qualification / public-open error."""


# Closed top-level field sets (parent §6.5.4 / schema_field_sets TOP_LEVEL).
_LAYOUT_FIELDS = frozenset(
    {
        "schema",
        "authority_dir",
        "projection_dir",
        "active_dir",
        "locks_dir",
        "control_dir",
        "layout_payload_sha256",
    }
)
_ENROLLMENT_FIELDS = frozenset(
    {
        "schema",
        "lineage_id",
        "slot_id",
        "mode",
        "owner_digest",
        "operator_uid",
        "controller_uid",
        "supervisor_uid",
        "runtime_uid",
        "scope_sha256",
        "registry_sha256",
        "semantic_contract_sha256",
        "initial_source_cutoff_sha256",
        "enrollment_payload_sha256",
    }
)
_PUBLICATION_FIELDS = frozenset(
    {
        "schema",
        "lineage_id",
        "owner_digest",
        "epoch",
        "authority_seq",
        "authority_snapshot_id",
        "authority_manifest_sha256",
        "authority_source_cutoff_sha256",
        "serving_generation_id",
        "projection_manifest_sha256",
        "semantic_contract_sha256",
        "pending_operation_id",
        "mode",
        "previous_publication_sha256",
        "freshness_anchor",
        "published_at",
        "publication_payload_sha256",
    }
)
_AUTHORITY_MANIFEST_FIELDS = frozenset(
    {
        "schema",
        "lineage_id",
        "authority_seq",
        "owner_digest",
        "snapshot_id",
        "parent_snapshot_id",
        "parent_manifest_sha256",
        "scope_sha256",
        "registry_sha256",
        "input_sha256",
        "source_cutoff_sha256",
        "operation_id",
        "authority_records_sha256",
        "record_count",
        "dispositions_sha256",
        "disposition_count",
        "citation_map_sha256",
        "provenance_context_sha256",
        "grounding_sha256",
        "added_assertion_ids",
        "added_disposition_ids",
        "added_provenance_ids",
        "added_grounding_refs",
        "semantic_contract_sha256",
        "reducer_version",
        "canonicalization_version",
        "builder_version",
        "builder_tree_sha256",
        "built_at",
        "as_of",
        "expires_at",
        "manifest_payload_sha256",
    }
)
_PROJECTION_MANIFEST_FIELDS = frozenset(
    {
        "schema",
        "lineage_id",
        "authority_seq",
        "owner_digest",
        "generation_id",
        "previous_generation_id",
        "snapshot_id",
        "authority_manifest_sha256",
        "scope_sha256",
        "registry_sha256",
        "semantic_contract_sha256",
        "rows_sha256",
        "row_count",
        "graph_sha256",
        "graph_node_count",
        "search_kernel",
        "search_kernel_version",
        "tokenizer_unicode_version",
        "builder_version",
        "builder_tree_sha256",
        "built_at",
        "as_of",
        "expires_at",
        "manifest_payload_sha256",
    }
)
_SEMANTIC_CONTRACT_FIELDS = frozenset(
    {
        "schema",
        "reducer_version",
        "grounding_version",
        "canonicalization_version",
        "identity_version",
        "search_kernel",
        "search_kernel_version",
        "tokenizer_unicode_version",
        "schema_digests",
        "contract_payload_sha256",
    }
)
# Frozen M3 semantic-contract constants — duplicated locally (never import publisher).
_REQUIRED_REDUCER_VERSION = "v1"
_REQUIRED_GROUNDING_VERSION = "v1"
_REQUIRED_CANONICALIZATION_VERSION = "v1"
_REQUIRED_IDENTITY_VERSION = "v2"
_REQUIRED_SEARCH_KERNEL = "lexical_v1"
_REQUIRED_SEARCH_KERNEL_VERSION = "1"
_REQUIRED_TOKENIZER_UNICODE_VERSION = "15.1.0"
_REQUIRED_SEMANTIC_CONTRACT = {
    "reducer_version": _REQUIRED_REDUCER_VERSION,
    "grounding_version": _REQUIRED_GROUNDING_VERSION,
    "canonicalization_version": _REQUIRED_CANONICALIZATION_VERSION,
    "identity_version": _REQUIRED_IDENTITY_VERSION,
    "search_kernel": _REQUIRED_SEARCH_KERNEL,
    "search_kernel_version": _REQUIRED_SEARCH_KERNEL_VERSION,
    "tokenizer_unicode_version": _REQUIRED_TOKENIZER_UNICODE_VERSION,
}
_SOURCE_CUTOFF_FIELDS = frozenset(
    {"schema", "lineage_id", "mode", "operations", "cutoff_payload_sha256"}
)
_CITATION_MAP_FIELDS = frozenset(
    {"schema", "citations", "citation_map_payload_sha256"}
)
_PROVENANCE_CONTEXT_FIELDS = frozenset(
    {
        "schema",
        "schema_semantics",
        "policies",
        "recipes",
        "verified_channels",
        "registered_assertions",
        "grounding_sha256",
        "context_payload_sha256",
    }
)
_GROUNDING_FIELDS = frozenset(
    {
        "schema",
        "blobs",
        "roots",
        "edges",
        "outputs",
        "receipts",
        "grounding_payload_sha256",
    }
)
_AUTHORITY_RECORD_FIELDS = frozenset(
    {
        "schema",
        "project_binding_id",
        "source_registration_id",
        "authority_site",
        "authority_domain",
        "record_kind",
        "logical_id",
        "assertion_id",
        "source_event_id",
        "producer",
        "logical_key",
        "semantic_sha256",
        "payload_sha256",
        "title",
        "document",
        "observed_at",
        "recorded_at",
        "confidence_bps",
        "relates_to_assertion_id",
        "target_assertion_id",
        "verification_result",
        "supersedes_assertion_ids",
        "decision_disposition_ref",
        "supersession_disposition_ref",
        "provenance_envelope",
        "provenance_commitment",
        "origin_assurance",
        "provenance_qualification",
        "check_eligibility",
    }
)
_DISPOSITION_FIELDS = frozenset(
    {
        "schema",
        "action",
        "project_binding_id",
        "subject_assertion_id",
        "subject_semantic_sha256",
        "target_assertion_ids",
        "basis_snapshot_id",
        "expected_head_assertion_ids",
        "replaces_disposition_ref",
        "review_actor",
        "review_role",
        "review_outcome",
        "reviewed_at",
        "ratifier_actor",
        "ratifier_role",
        "ratified_at",
        "rationale_sha256",
    }
)
_PROJECTION_ROW_FIELDS = frozenset(
    {
        "schema",
        "project_binding_id",
        "public_binding_ref",
        "source_registration_id",
        "authority_site",
        "authority_domain",
        "record_kind",
        "logical_id",
        "assertion_id",
        "public_ledger_id",
        "citation_ref",
        "title",
        "document",
        "observed_at",
        "recorded_at",
        "confidence_bps",
        "relates_to_assertion_id",
        "target_assertion_id",
        "verification_result",
        "supersedes_assertion_ids",
        "decision_disposition_ref",
        "supersession_disposition_ref",
        "origin_assurance",
        "provenance_qualification",
        "check_eligibility",
        "authority_state",
        "verification_state",
        "state_disposition_refs",
        "payload_sha256",
        "state_sha256",
    }
)
_GRAPH_FIELDS = frozenset({"schema", "nodes", "edges", "graph_payload_sha256"})
_GRAPH_EDGE_FIELDS = frozenset({"kind", "from_assertion_id", "to_assertion_id"})
_FRESHNESS_ANCHOR_FIELDS = frozenset(
    {
        "boot_id",
        "authority_snapshot_id",
        "sampled_wall_time",
        "sampled_boottime_ns",
        "snapshot_deadline_boottime_ns",
        "clock_review_ref",
    }
)
_INPUT_PAYLOAD_FIELD = {
    "convmem.strict-fixture-bundle.v2": "fixture_payload_sha256",
    "convmem.approved-admission.v1": "artifact_payload_sha256",
}
_FIXTURE_BUNDLE_FIELDS = frozenset(
    {
        "schema",
        "lineage_id",
        "operation_id",
        "expected_parent_manifest_sha256",
        "batches",
        "dispositions",
        "provenance_context",
        "grounding",
        "built_at",
        "as_of",
        "expires_at",
        "fixture_payload_sha256",
    }
)
_LAYOUT_DIR_VALUES = {
    "authority_dir": "authority",
    "projection_dir": "projection",
    "active_dir": "active",
    "locks_dir": "locks",
    "control_dir": "control",
}


@dataclass(frozen=True, slots=True)
class QualifiedAuthorityGeneration:
    """Module-sealed capability produced only by private cold qualification."""

    lineage_id: str
    authority_seq: int
    snapshot_id: str | None
    authority_manifest_sha256: str | None
    generation_id: str | None
    projection_manifest_sha256: str | None
    rows_sha256: str | None
    graph_sha256: str | None
    state_by_assertion: Mapping[str, ReducedState]
    publication_payload_sha256: str
    semantic_contract_sha256: str
    expires_at: str | None
    as_of: str | None


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in pairs:
        if key in out:
            raise StrictProjectionError(f"duplicate_key:{key}")
        out[key] = value
    return out


def _read_json(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise StrictProjectionError(f"missing_file:{path}")
    raw = path.read_bytes()
    try:
        obj = json.loads(raw.decode("utf-8"), object_pairs_hook=_reject_duplicate_keys)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise StrictProjectionError(f"json_invalid:{path}") from exc
    if not isinstance(obj, dict):
        raise StrictProjectionError(f"json_object_required:{path}")
    return obj


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if path.is_symlink() or not path.is_file():
        raise StrictProjectionError(f"missing_file:{path}")
    rows: list[dict[str, Any]] = []
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line:
            raise StrictProjectionError(f"jsonl_empty_line:{path}:{line_no}")
        try:
            obj = json.loads(line, object_pairs_hook=_reject_duplicate_keys)
        except json.JSONDecodeError as exc:
            raise StrictProjectionError(f"jsonl_invalid:{path}:{line_no}") from exc
        if not isinstance(obj, dict):
            raise StrictProjectionError(f"jsonl_object_required:{path}:{line_no}")
        rows.append(obj)
    return rows


def _require_closed(
    obj: Mapping[str, Any],
    fields: frozenset[str],
    *,
    schema: str,
    label: str,
) -> None:
    if set(obj) != fields:
        raise StrictProjectionError(f"{label}_keys")
    if obj["schema"] != schema:
        raise StrictProjectionError(f"{label}_schema")


def _labeled_self_hash(obj: Mapping[str, Any], field: str) -> str:
    """Parent self-hash: exclude ONLY the named payload-hash field."""
    if field not in obj:
        raise StrictProjectionError(f"self_hash_field_missing:{field}")
    body = {k: v for k, v in obj.items() if k != field}
    return sha256_digest(strict_canonical_bytes(body))


def _require_self_hash(obj: Mapping[str, Any], field: str, *, label: str) -> str:
    digest = _labeled_self_hash(obj, field)
    if obj[field] != digest:
        raise StrictProjectionError(f"{label}_hash_mismatch")
    return digest


def _sha256hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _authority_snapshot_id(manifest: Mapping[str, Any]) -> str:
    body = {
        k: v
        for k, v in manifest.items()
        if k not in {"snapshot_id", "manifest_payload_sha256"}
    }
    return "snap2_" + _sha256hex(strict_canonical_bytes(body))


def _projection_generation_id(manifest: Mapping[str, Any]) -> str:
    body = {
        k: v
        for k, v in manifest.items()
        if k not in {"generation_id", "manifest_payload_sha256"}
    }
    return "gen2_" + _sha256hex(strict_canonical_bytes(body))


def _canonical_jsonl_bytes(objects: list[dict[str, Any]]) -> bytes:
    """Exact parent JSONL: one canonical object + LF per line (including trailing LF)."""
    if not objects:
        return b""
    parts = [strict_canonical_bytes(obj) + b"\n" for obj in objects]
    return b"".join(parts)


def _jsonl_sha256(objects: list[dict[str, Any]]) -> str:
    return sha256_digest(_canonical_jsonl_bytes(objects))


def _input_payload_digest(input_obj: Mapping[str, Any]) -> str:
    if "schema" not in input_obj:
        raise StrictProjectionError("input_schema")
    schema = input_obj["schema"]
    if not isinstance(schema, str) or schema not in _INPUT_PAYLOAD_FIELD:
        raise StrictProjectionError("input_schema")
    field = _INPUT_PAYLOAD_FIELD[schema]
    if field not in input_obj:
        raise StrictProjectionError("input_payload_field")
    if schema == "convmem.strict-fixture-bundle.v2":
        _require_closed(
            input_obj,
            _FIXTURE_BUNDLE_FIELDS,
            schema="convmem.strict-fixture-bundle.v2",
            label="fixture_bundle",
        )
    return _require_self_hash(input_obj, field, label="input")


def _empty_source_cutoff_digest(*, lineage_id: str, mode: str) -> str:
    """SHA-256 of the hashed-empty cutoff (operations=[]), matching enrollment genesis."""
    body = {
        "schema": "convmem.strict-source-cutoff.v1",
        "lineage_id": lineage_id,
        "mode": mode,
        "operations": [],
    }
    return sha256_digest(strict_canonical_bytes(body))


@dataclass(frozen=True, slots=True)
class _AuthorityHead:
    """One content-addressed authority snapshot loaded during cold replay."""

    snapshot_id: str
    manifest: dict[str, Any]
    manifest_payload_sha256: str
    input_obj: dict[str, Any]
    cutoff: dict[str, Any]
    records: list[dict[str, Any]]
    dispositions: list[dict[str, Any]]
    citation_map: dict[str, Any]
    provenance_context: dict[str, Any]
    grounding: dict[str, Any]


def _sorted_unique_str_array(value: Any, *, label: str) -> list[str]:
    if not isinstance(value, list):
        raise StrictProjectionError(f"{label}_type")
    if any(not isinstance(x, str) or not x for x in value):
        raise StrictProjectionError(f"{label}_entry")
    if value != sorted(set(value)):
        raise StrictProjectionError(f"{label}_sorted_unique")
    return list(value)


def _record_bytes_by_id(records: list[dict[str, Any]]) -> dict[str, bytes]:
    out: dict[str, bytes] = {}
    for rec in records:
        aid = rec["assertion_id"]
        raw = strict_canonical_bytes(rec)
        if aid in out:
            raise StrictProjectionError("record_id_duplicate")
        out[aid] = raw
    return out


def _disposition_bytes_by_id(dispositions: list[dict[str, Any]]) -> dict[str, bytes]:
    out: dict[str, bytes] = {}
    for disp in dispositions:
        did = disposition_id(disp)
        raw = strict_canonical_bytes(disp)
        if did in out:
            raise StrictProjectionError("disposition_id_duplicate")
        out[did] = raw
    return out


def _assert_cumulative_maps(
    parent: Mapping[str, bytes],
    child: Mapping[str, bytes],
    *,
    label: str,
) -> None:
    for key, raw in parent.items():
        if key not in child:
            raise StrictProjectionError(f"{label}_cumulative_deleted")
        if child[key] != raw:
            raise StrictProjectionError(f"{label}_cumulative_mutated")


def _load_authority_head(
    root_path: Path,
    *,
    snapshot_id: str,
    lineage_id: str,
    owner_digest_value: str,
    scope_sha256: str,
    registry_sha256: str,
    semantic_contract_sha256: str,
    expected_seq: int | None = None,
    expected_manifest_sha256: str | None = None,
) -> _AuthorityHead:
    if not isinstance(snapshot_id, str) or not snapshot_id.startswith("snap2_"):
        raise StrictProjectionError("authority_snapshot_id")
    auth_dir = root_path / "authority" / snapshot_id
    if auth_dir.is_symlink() or not auth_dir.is_dir():
        raise StrictProjectionError("authority_dir")

    for name in (
        "input.json",
        "source-cutoff.json",
        "records.jsonl",
        "dispositions.jsonl",
        "citation-map.json",
        "provenance-context.json",
        "grounding.json",
        "manifest.json",
    ):
        path = auth_dir / name
        if not path.is_file() or path.is_symlink():
            raise StrictProjectionError(f"private_missing:{name}")

    manifest = _read_json(auth_dir / "manifest.json")
    _require_closed(
        manifest,
        _AUTHORITY_MANIFEST_FIELDS,
        schema="convmem.bound-authority-manifest.v3",
        label="authority_manifest",
    )
    if manifest["lineage_id"] != lineage_id:
        raise StrictProjectionError("authority_manifest_lineage")
    if manifest["owner_digest"] != owner_digest_value:
        raise StrictProjectionError("authority_manifest_owner")
    if manifest["semantic_contract_sha256"] != semantic_contract_sha256:
        raise StrictProjectionError("authority_manifest_semantic_contract_link")
    if manifest["scope_sha256"] != scope_sha256:
        raise StrictProjectionError("authority_manifest_scope_link")
    if manifest["registry_sha256"] != registry_sha256:
        raise StrictProjectionError("authority_manifest_registry_link")
    if manifest["snapshot_id"] != snapshot_id:
        raise StrictProjectionError("authority_snapshot_id_mismatch")
    recomputed_snapshot_id = _authority_snapshot_id(manifest)
    if manifest["snapshot_id"] != recomputed_snapshot_id:
        raise StrictProjectionError("authority_snapshot_id_recompute")
    recomputed_payload = _labeled_self_hash(manifest, "manifest_payload_sha256")
    if manifest["manifest_payload_sha256"] != recomputed_payload:
        raise StrictProjectionError("authority_manifest_hash")
    if expected_manifest_sha256 is not None and recomputed_payload != expected_manifest_sha256:
        raise StrictProjectionError("authority_manifest_link")
    seq = manifest["authority_seq"]
    if not isinstance(seq, int) or isinstance(seq, bool) or seq < 1:
        raise StrictProjectionError("authority_manifest_seq")
    if expected_seq is not None and seq != expected_seq:
        raise StrictProjectionError("authority_seq_mismatch")

    _sorted_unique_str_array(manifest["added_assertion_ids"], label="added_assertion_ids")
    _sorted_unique_str_array(manifest["added_disposition_ids"], label="added_disposition_ids")
    _sorted_unique_str_array(manifest["added_provenance_ids"], label="added_provenance_ids")
    _sorted_unique_str_array(manifest["added_grounding_refs"], label="added_grounding_refs")

    input_obj = _read_json(auth_dir / "input.json")
    input_digest = _input_payload_digest(input_obj)
    if manifest["input_sha256"] != input_digest:
        raise StrictProjectionError("input_link")

    cutoff = _read_json(auth_dir / "source-cutoff.json")
    _require_closed(
        cutoff,
        _SOURCE_CUTOFF_FIELDS,
        schema="convmem.strict-source-cutoff.v1",
        label="source_cutoff",
    )
    if cutoff["lineage_id"] != lineage_id:
        raise StrictProjectionError("source_cutoff_lineage")
    cutoff_digest = _require_self_hash(cutoff, "cutoff_payload_sha256", label="source_cutoff")
    if manifest["source_cutoff_sha256"] != cutoff_digest:
        raise StrictProjectionError("source_cutoff_link")
    operations = cutoff["operations"]
    if not isinstance(operations, list):
        raise StrictProjectionError("source_cutoff_operations")
    seen_ops: set[str] = set()
    for op in operations:
        if not isinstance(op, dict) or set(op) != {
            "operation_id",
            "input_sha256",
            "source_prefix_sha256",
        }:
            raise StrictProjectionError("source_cutoff_operation_keys")
        oid = op["operation_id"]
        if not isinstance(oid, str) or not oid or oid in seen_ops:
            raise StrictProjectionError("source_cutoff_operation_id")
        seen_ops.add(oid)

    records = _read_jsonl(auth_dir / "records.jsonl")
    for rec in records:
        _require_closed(
            rec,
            _AUTHORITY_RECORD_FIELDS,
            schema="convmem.bound-authority-record.v3",
            label="authority_record",
        )
    record_ids = [r["assertion_id"] for r in records]
    if record_ids != sorted(record_ids) or len(record_ids) != len(set(record_ids)):
        raise StrictProjectionError("records_sort")
    records_digest = _jsonl_sha256(records)
    if manifest["authority_records_sha256"] != records_digest:
        raise StrictProjectionError("records_link")
    if manifest["record_count"] != len(records):
        raise StrictProjectionError("record_count")

    dispositions = _read_jsonl(auth_dir / "dispositions.jsonl")
    for disp in dispositions:
        _require_closed(
            disp,
            _DISPOSITION_FIELDS,
            schema="convmem.authority-disposition.v1",
            label="disposition",
        )
    disp_addrs = [disposition_id(d) for d in dispositions]
    if disp_addrs != sorted(disp_addrs) or len(disp_addrs) != len(set(disp_addrs)):
        raise StrictProjectionError("dispositions_sort")
    dispositions_digest = _jsonl_sha256(dispositions)
    if manifest["dispositions_sha256"] != dispositions_digest:
        raise StrictProjectionError("dispositions_link")
    if manifest["disposition_count"] != len(dispositions):
        raise StrictProjectionError("disposition_count")

    citation_map = _read_json(auth_dir / "citation-map.json")
    _require_closed(
        citation_map,
        _CITATION_MAP_FIELDS,
        schema="convmem.strict-citation-map.v1",
        label="citation_map",
    )
    citation_digest = _require_self_hash(
        citation_map, "citation_map_payload_sha256", label="citation_map"
    )
    if manifest["citation_map_sha256"] != citation_digest:
        raise StrictProjectionError("citation_map_link")

    provenance_context = _read_json(auth_dir / "provenance-context.json")
    grounding = _read_json(auth_dir / "grounding.json")
    _require_closed(
        grounding,
        _GROUNDING_FIELDS,
        schema="convmem.strict-grounding.v1",
        label="grounding",
    )
    grounding_digest = _require_self_hash(
        grounding, "grounding_payload_sha256", label="grounding"
    )
    if manifest["grounding_sha256"] != grounding_digest:
        raise StrictProjectionError("grounding_link")
    try:
        provenance_context = validate_provenance_context(
            provenance_context, expected_grounding_sha256=grounding_digest
        )
    except StrictGroundingError as exc:
        raise StrictProjectionError(f"provenance_context:{exc}") from exc
    context_digest = provenance_context["context_payload_sha256"]
    if manifest["provenance_context_sha256"] != context_digest:
        raise StrictProjectionError("provenance_context_link")

    return _AuthorityHead(
        snapshot_id=snapshot_id,
        manifest=manifest,
        manifest_payload_sha256=recomputed_payload,
        input_obj=input_obj,
        cutoff=cutoff,
        records=records,
        dispositions=dispositions,
        citation_map=citation_map,
        provenance_context=provenance_context,
        grounding=grounding,
    )


def _walk_lineage_forward(
    root_path: Path,
    *,
    tip_snapshot_id: str,
    tip_manifest_sha256: str,
    tip_seq: int,
    lineage_id: str,
    owner_digest_value: str,
    scope_sha256: str,
    registry_sha256: str,
    semantic_contract_sha256: str,
) -> list[_AuthorityHead]:
    """Walk parent pointers to seq1, then return heads ordered seq1..tip."""

    backward: list[_AuthorityHead] = []
    seen: set[str] = set()
    current_id: str | None = tip_snapshot_id
    expected_hash: str | None = tip_manifest_sha256
    expected_seq = tip_seq
    while current_id is not None:
        if current_id in seen:
            raise StrictProjectionError("lineage_cycle")
        seen.add(current_id)
        head = _load_authority_head(
            root_path,
            snapshot_id=current_id,
            lineage_id=lineage_id,
            owner_digest_value=owner_digest_value,
            scope_sha256=scope_sha256,
            registry_sha256=registry_sha256,
            semantic_contract_sha256=semantic_contract_sha256,
            expected_seq=expected_seq,
            expected_manifest_sha256=expected_hash,
        )
        backward.append(head)
        parent_id = head.manifest["parent_snapshot_id"]
        parent_hash = head.manifest["parent_manifest_sha256"]
        seq = head.manifest["authority_seq"]
        if seq == 1:
            if parent_id is not None or parent_hash is not None:
                raise StrictProjectionError("authority_parent_null")
            current_id = None
        else:
            if not isinstance(parent_id, str) or not parent_id.startswith("snap2_"):
                raise StrictProjectionError("authority_parent_snapshot")
            if not isinstance(parent_hash, str) or not parent_hash.startswith("sha256:"):
                raise StrictProjectionError("authority_parent_manifest")
            current_id = parent_id
            expected_hash = parent_hash
            expected_seq = seq - 1
    if not backward or backward[-1].manifest["authority_seq"] != 1:
        raise StrictProjectionError("lineage_missing_seq1")
    if len(backward) != tip_seq:
        raise StrictProjectionError("lineage_skipped_or_forked")
    forward = list(reversed(backward))
    for idx, head in enumerate(forward, start=1):
        if head.manifest["authority_seq"] != idx:
            raise StrictProjectionError("lineage_seq_order")
    if forward[-1].snapshot_id != tip_snapshot_id:
        raise StrictProjectionError("lineage_tip_mismatch")
    if forward[-1].manifest_payload_sha256 != tip_manifest_sha256:
        raise StrictProjectionError("lineage_tip_hash_mismatch")
    return forward


# ---------------------------------------------------------------------------
# Reader-local builder tree (never import the publisher; two-root independent)
# ---------------------------------------------------------------------------

# Frozen publisher builder version string — duplicated here so cold qualify does
# not import strict_projection_publisher (which imports this module).
_FROZEN_BUILDER_VERSION = "strict-projection-publisher/v1"

# Exact publisher component membership (Architecture §6.5.9 CORE + Gate B/C
# schemas + publisher). Production-local literal — never imported from tests.
_BUILDER_CORE_MEMBERS: tuple[str, ...] = (
    "canonical_json.py",
    "provenance.py",
    "provenance_binding.py",
    "domains.py",
    "bound_read_scope.py",
    "strict_grounding.py",
    "strict_evidence_state.py",
    "strict_projection.py",
    "requirements.txt",
)

_BUILDER_SCHEMAS_BC: tuple[str, ...] = (
    "schemas/convmem-bound-read-scope-v2.schema.json",
    "schemas/convmem-project-binding-registry-v3.schema.json",
    "schemas/convmem-bound-authority-record-v3.schema.json",
    "schemas/convmem-authority-disposition-v1.schema.json",
    "schemas/convmem-strict-provenance-context-v2.schema.json",
    "schemas/convmem-strict-grounding-v1.schema.json",
    "schemas/convmem-capture-receipt-v1.schema.json",
    "schemas/convmem-strict-fixture-bundle-v2.schema.json",
    "schemas/convmem-strict-citation-map-v1.schema.json",
    "schemas/convmem-bound-authority-manifest-v3.schema.json",
    "schemas/convmem-bound-projection-row-v2.schema.json",
    "schemas/convmem-strict-graph-v1.schema.json",
    "schemas/convmem-bound-projection-manifest-v3.schema.json",
    "schemas/convmem-strict-generation-layout-v2.schema.json",
    "schemas/convmem-strict-publication-v2.schema.json",
    "schemas/convmem-strict-enrollment-v1.schema.json",
    "schemas/convmem-strict-slot-v1.schema.json",
    "schemas/convmem-strict-source-cutoff-v1.schema.json",
    "schemas/convmem-strict-semantic-contract-v1.schema.json",
    "schemas/convmem-strict-state-v2.schema.json",
    "schemas/convmem-clock-review-v1.schema.json",
    "schemas/convmem-raw-evidence-v3.schema.json",
    "schemas/convmem-error-v1.schema.json",
    "schemas/convmem-strict-config-v2.schema.json",
    "schemas/convmem-openclaw-connector-launch-v2.schema.json",
    "schemas/convmem-openclaw-activation-v2.schema.json",
    "schemas/convmem-activation-control-v1.schema.json",
    "schemas/convmem-activation-retirement-v1.schema.json",
    "schemas/convmem-activation-launch-policy-v1.schema.json",
    "schemas/convmem-activation-manager-policy-v1.schema.json",
    "schemas/convmem-controller-socket-policy-v1.schema.json",
)

_BUILDER_TREE_MEMBERS: tuple[str, ...] = tuple(
    sorted(
        set(_BUILDER_CORE_MEMBERS)
        | set(_BUILDER_SCHEMAS_BC)
        | {"strict_projection_publisher.py"}
    )
)


def _builder_member_entry(base: Path, rel: str) -> dict[str, str]:
    """Path/mode/bytes entry — same algorithm as the publisher builder tree."""
    path = base / rel
    if path.is_symlink():
        raise StrictProjectionError(f"builder_symlink:{rel}")
    if not path.is_file():
        raise StrictProjectionError(f"builder_missing:{rel}")
    st = path.lstat()
    if not stat.S_ISREG(st.st_mode):
        raise StrictProjectionError(f"builder_not_regular:{rel}")
    mode = f"{st.st_mode & 0o7777:04o}"
    if len(mode) != 4 or any(ch not in "01234567" for ch in mode):
        raise StrictProjectionError(f"builder_mode_invalid:{rel}")
    return {
        "path": rel,
        "mode": mode,
        "sha256": sha256_digest(path.read_bytes()),
    }


def _recompute_builder_tree_sha256(root: Path | None = None) -> str:
    """Independent reader recomputation of publisher builder_tree_sha256."""
    base = Path(__file__).resolve().parent if root is None else root
    entries = [_builder_member_entry(base, rel) for rel in _BUILDER_TREE_MEMBERS]
    if len(entries) != len(_BUILDER_TREE_MEMBERS):
        raise StrictProjectionError("builder_inventory_drift")
    return sha256_digest(strict_canonical_bytes(entries))


def _recompute_schema_digests(root: Path | None = None) -> list[dict[str, str]]:
    """Independent Gate B/C schema digests — same inventory as the publisher."""
    base = Path(__file__).resolve().parent if root is None else root
    digests: list[dict[str, str]] = []
    for rel in sorted(_BUILDER_SCHEMAS_BC):
        path = base / rel
        if path.is_symlink():
            raise StrictProjectionError(f"schema_symlink:{rel}")
        if not path.is_file():
            raise StrictProjectionError(f"schema_missing:{rel}")
        st = path.lstat()
        if not stat.S_ISREG(st.st_mode):
            raise StrictProjectionError(f"schema_not_regular:{rel}")
        digests.append(
            {
                "path": rel,
                "sha256": sha256_digest(path.read_bytes()),
            }
        )
    return digests


def _enforce_semantic_contract(contract: Mapping[str, Any]) -> None:
    """Reader-local closed contract: frozen versions + independent schema digests."""
    if unicodedata.unidata_version != _REQUIRED_TOKENIZER_UNICODE_VERSION:
        raise StrictProjectionError("tokenizer_unicode_runtime")
    for key, expected in _REQUIRED_SEMANTIC_CONTRACT.items():
        if contract[key] != expected:
            raise StrictProjectionError(f"semantic_contract_{key}")
    digests = contract["schema_digests"]
    if not isinstance(digests, list):
        raise StrictProjectionError("schema_digests_type")
    expected = _recompute_schema_digests()
    if strict_canonical_bytes(digests) != strict_canonical_bytes(expected):
        raise StrictProjectionError("schema_digests_mismatch")


def _verify_fixture_source_cutoff_head(
    head: _AuthorityHead,
    *,
    prev: _AuthorityHead | None,
    lineage_id: str,
    enrollment_mode: str,
) -> None:
    """§6.5.5 fixture source-cutoff: closed input, lineage, parent, ops, batches, digest."""
    input_obj = head.input_obj
    # Fixture enrollment never skips: every head must carry the closed fixture bundle.
    if enrollment_mode == "fixture":
        if input_obj.get("schema") != "convmem.strict-fixture-bundle.v2":
            raise StrictProjectionError("fixture_input_schema_required")
    elif input_obj.get("schema") != "convmem.strict-fixture-bundle.v2":
        return

    if input_obj["lineage_id"] != lineage_id:
        raise StrictProjectionError("fixture_bundle_lineage")
    if input_obj["expected_parent_manifest_sha256"] != head.manifest["parent_manifest_sha256"]:
        raise StrictProjectionError("fixture_expected_parent_mismatch")

    batches = input_obj["batches"]
    if not isinstance(batches, list):
        raise StrictProjectionError("fixture_batches_type")

    if prev is not None:
        if prev.input_obj.get("schema") != "convmem.strict-fixture-bundle.v2":
            raise StrictProjectionError("fixture_parent_input_schema")
        prior_batches = prev.input_obj["batches"]
        if not isinstance(prior_batches, list):
            raise StrictProjectionError("fixture_parent_batches_type")
        if len(batches) < len(prior_batches):
            raise StrictProjectionError("fixture_batches_not_prefix")
        if strict_canonical_bytes(list(batches[: len(prior_batches)])) != (
            strict_canonical_bytes(prior_batches)
        ):
            raise StrictProjectionError("fixture_batches_not_prefix")

    ops = head.cutoff["operations"]
    if not ops:
        raise StrictProjectionError("source_cutoff_empty_ops")
    new_op = ops[-1]
    if input_obj["operation_id"] != head.manifest["operation_id"]:
        raise StrictProjectionError("operation_id_input_manifest_mismatch")
    if input_obj["operation_id"] != new_op["operation_id"]:
        raise StrictProjectionError("operation_id_cutoff_mismatch")
    if head.manifest["operation_id"] != new_op["operation_id"]:
        raise StrictProjectionError("operation_id_cutoff_mismatch")

    input_digest = head.manifest["input_sha256"]
    if input_digest != new_op["input_sha256"]:
        raise StrictProjectionError("input_sha256_cutoff_mismatch")
    # Manifest↔input link already checked in _load_authority_head; re-assert equality.
    if input_digest != _labeled_self_hash(input_obj, "fixture_payload_sha256"):
        raise StrictProjectionError("input_sha256_mismatch")

    expected_prefix = sha256_digest(strict_canonical_bytes(batches))
    if new_op["source_prefix_sha256"] != expected_prefix:
        raise StrictProjectionError("source_prefix_mismatch")


def _parent_heads_by_logical(
    records: list[dict[str, Any]],
    dispositions: Mapping[str, Mapping[str, Any]],
) -> dict[str, list[str]]:
    """Immediate-parent head map for disposition validation (reader-local; no publisher)."""
    reduced = reduce_complete_bound_state(records, dispositions)
    by_assertion = {r["assertion_id"]: r for r in records}
    heads: dict[str, list[str]] = {}
    for assertion_id, state in reduced.items():
        if state.authority_state not in {"current", "conflict"}:
            continue
        logical = by_assertion[assertion_id]["logical_id"]
        heads.setdefault(logical, []).append(assertion_id)
    for logical in heads:
        heads[logical] = sorted(set(heads[logical]))
    return heads


def _original_qualifications_from_records(
    records: list[dict[str, Any]],
) -> dict[str, dict[str, str]]:
    originals: dict[str, dict[str, str]] = {}
    for rec in records:
        env = rec.get("provenance_envelope")
        pq = rec.get("provenance_qualification")
        if isinstance(env, Mapping) and isinstance(pq, Mapping):
            pid = env.get("assertion_id")
            if isinstance(pid, str) and pid:
                originals[pid] = {
                    "commitments": str(pq["commitments"]),
                    "byte_grounding": str(pq["byte_grounding"]),
                    "capture": str(pq["capture"]),
                    "transformer_cap": str(pq["transformer_cap"]),
                }
    return originals


def _independently_replay_head_admission(
    head: _AuthorityHead,
    prev: _AuthorityHead | None,
    *,
    binding: Any,
    issuer_inventory: Mapping[str, bytes] | None,
) -> None:
    """Reconstruct this head's admission from its committed fixture input alone.

    Materializes the cumulative-batches suffix through the bound ProjectBinding and
    existing materializer (source-event + envelope selection binding), applies input
    dispositions against staging records and the immediate parent head map, then
    requires reconstructed added/cumulative record and disposition bytes equal the
    committed head exactly. Retained parent bytes stay immutable by construction.
    """

    input_obj = head.input_obj
    batches = input_obj["batches"]
    if not isinstance(batches, list):
        raise StrictProjectionError("fixture_batches_type")
    prior_batches: list[Any] = []
    if prev is not None:
        prior_raw = prev.input_obj.get("batches")
        if not isinstance(prior_raw, list):
            raise StrictProjectionError("fixture_parent_batches_type")
        prior_batches = list(prior_raw)
    delta_batches = list(batches[len(prior_batches) :])

    parent_records = list(prev.records) if prev is not None else []
    parent_dispositions = list(prev.dispositions) if prev is not None else []
    parent_snapshot_id = prev.snapshot_id if prev is not None else None

    registered: dict[str, Any] = {}
    for entry in head.provenance_context["registered_assertions"]:
        aid = entry["assertion_id"]
        if aid in registered:
            raise StrictProjectionError("admission_registered_duplicate")
        registered[aid] = entry

    originals = _original_qualifications_from_records(parent_records)
    try:
        qual_map = qualify_assertions(
            grounding=head.grounding,
            provenance_context=head.provenance_context,
            issuer_inventory=issuer_inventory,
            capture_issuers=binding.capture_issuers,
            allowed_issuer_ids={i.issuer_id for i in binding.capture_issuers},
            allowed_source_registration_ids={
                r.id for r in binding.source_registrations
            },
            original_qualifications=originals or None,
        )
    except StrictGroundingError as exc:
        raise StrictProjectionError(f"admission_qualify:{exc}") from exc

    added_records: list[dict[str, Any]] = []
    for batch in delta_batches:
        if not isinstance(batch, Mapping):
            raise StrictProjectionError("admission_batch_type")
        try:
            new_recs = materialize_authority_records(
                binding=binding,
                source_registration_id=batch["source_registration_id"],
                scan=batch["source"],
                registered_assertions=registered,
                qualification_by_provenance=qual_map,
                prior_records=parent_records + added_records,
            )
        except StrictEvidenceError as exc:
            raise StrictProjectionError(f"admission_materialize:{exc}") from exc
        added_records.extend(new_recs)

    parent_ids = {r["assertion_id"] for r in parent_records}
    parent_disp_map = {disposition_id(d): d for d in parent_dispositions}
    parent_heads = (
        _parent_heads_by_logical(parent_records, parent_disp_map)
        if parent_records
        else {}
    )
    staging_records = list(parent_records) + [dict(r) for r in added_records]
    try:
        new_disp_map = validate_dispositions(
            list(input_obj["dispositions"]),
            records=staging_records,
            parent_snapshot_id=parent_snapshot_id,
            parent_heads_by_logical=parent_heads if parent_heads else None,
        )
    except StrictEvidenceError as exc:
        raise StrictProjectionError(f"admission_dispositions:{exc}") from exc

    added_by_id = {r["assertion_id"]: dict(r) for r in added_records}
    for disp_id, disp in new_disp_map.items():
        subject = disp["subject_assertion_id"]
        action = disp["action"]
        if subject in parent_ids:
            continue
        if subject not in added_by_id:
            raise StrictProjectionError("admission_disposition_subject")
        rec = added_by_id[subject]
        if action in {"decision_approved", "decision_rejected"}:
            rec["decision_disposition_ref"] = disp_id
        elif action == "supersession_authorized":
            rec["supersession_disposition_ref"] = disp_id
            rec["supersedes_assertion_ids"] = sorted(set(disp["target_assertion_ids"]))
        added_by_id[subject] = rec
    for rec in added_by_id.values():
        rec["semantic_sha256"] = semantic_sha256(rec)
        rec["payload_sha256"] = payload_sha256(rec)
    added_records = list(added_by_id.values())

    all_records = sorted(
        list(parent_records) + added_records, key=lambda r: r["assertion_id"]
    )
    all_dispositions = list(parent_dispositions) + [
        new_disp_map[k] for k in sorted(new_disp_map)
    ]
    all_dispositions.sort(key=lambda d: disposition_id(d))

    reconstructed_added = {
        r["assertion_id"]: strict_canonical_bytes(r) for r in added_records
    }
    committed_parent = _record_bytes_by_id(parent_records)
    committed_child = _record_bytes_by_id(head.records)
    committed_added_ids = sorted(set(committed_child) - set(committed_parent))
    committed_added = {aid: committed_child[aid] for aid in committed_added_ids}
    if reconstructed_added != committed_added:
        raise StrictProjectionError("admission_added_records_mismatch")

    reconstructed_disp_ids = sorted(new_disp_map)
    if reconstructed_disp_ids != list(head.manifest["added_disposition_ids"]):
        raise StrictProjectionError("admission_added_disposition_ids_mismatch")
    committed_disp_bytes = _disposition_bytes_by_id(head.dispositions)
    for did in reconstructed_disp_ids:
        if did not in committed_disp_bytes:
            raise StrictProjectionError("admission_added_disposition_missing")
        if strict_canonical_bytes(new_disp_map[did]) != committed_disp_bytes[did]:
            raise StrictProjectionError("admission_added_disposition_bytes_mismatch")

    if _canonical_jsonl_bytes(all_records) != _canonical_jsonl_bytes(head.records):
        raise StrictProjectionError("admission_cumulative_records_mismatch")
    if _canonical_jsonl_bytes(all_dispositions) != _canonical_jsonl_bytes(
        head.dispositions
    ):
        raise StrictProjectionError("admission_cumulative_dispositions_mismatch")


def _replay_cumulative_and_deltas(
    heads: list[_AuthorityHead],
    *,
    enrollment: Mapping[str, Any],
    binding: Any,
    issuer_inventory: Mapping[str, bytes] | None,
) -> None:
    tip_builder_version = heads[-1].manifest["builder_version"]
    tip_builder_tree = heads[-1].manifest["builder_tree_sha256"]
    tip_reducer = heads[-1].manifest["reducer_version"]
    tip_canon = heads[-1].manifest["canonicalization_version"]
    if tip_builder_version != _FROZEN_BUILDER_VERSION:
        raise StrictProjectionError("builder_version_mismatch")
    recomputed_tree = _recompute_builder_tree_sha256()
    if tip_builder_tree != recomputed_tree:
        raise StrictProjectionError("builder_tree_mismatch")

    lineage_id = enrollment["lineage_id"]
    mode = enrollment["mode"]
    if not isinstance(mode, str):
        raise StrictProjectionError("enrollment_mode")
    empty_cutoff = _empty_source_cutoff_digest(lineage_id=lineage_id, mode=mode)
    if enrollment["initial_source_cutoff_sha256"] != empty_cutoff:
        raise StrictProjectionError("enrollment_cutoff_mismatch")

    prev: _AuthorityHead | None = None
    for head in heads:
        if head.manifest["builder_version"] != tip_builder_version:
            raise StrictProjectionError("builder_version_drift")
        if head.manifest["builder_tree_sha256"] != tip_builder_tree:
            raise StrictProjectionError("builder_tree_drift")
        if head.manifest["reducer_version"] != tip_reducer:
            raise StrictProjectionError("reducer_version_drift")
        if head.manifest["canonicalization_version"] != tip_canon:
            raise StrictProjectionError("canonicalization_version_drift")

        parent_grounding = prev.grounding if prev is not None else None
        parent_context = prev.provenance_context if prev is not None else None
        try:
            assert_cumulative_grounding(parent_grounding, head.grounding)
            assert_cumulative_provenance_context(parent_context, head.provenance_context)
        except StrictGroundingError as exc:
            raise StrictProjectionError(f"cumulative_inventory:{exc}") from exc

        parent_records = _record_bytes_by_id(prev.records) if prev else {}
        child_records = _record_bytes_by_id(head.records)
        _assert_cumulative_maps(parent_records, child_records, label="records")

        parent_disps = _disposition_bytes_by_id(prev.dispositions) if prev else {}
        child_disps = _disposition_bytes_by_id(head.dispositions)
        _assert_cumulative_maps(parent_disps, child_disps, label="dispositions")

        if prev is not None:
            parent_ops = prev.cutoff["operations"]
            child_ops = head.cutoff["operations"]
            if child_ops[: len(parent_ops)] != parent_ops:
                raise StrictProjectionError("source_cutoff_not_prefix")
            if len(child_ops) != len(parent_ops) + 1:
                raise StrictProjectionError("source_cutoff_delta")
        else:
            if len(head.cutoff["operations"]) != 1:
                raise StrictProjectionError("source_cutoff_genesis")

        _verify_fixture_source_cutoff_head(
            head,
            prev=prev,
            lineage_id=lineage_id,
            enrollment_mode=mode,
        )
        if mode == "fixture":
            _independently_replay_head_admission(
                head,
                prev,
                binding=binding,
                issuer_inventory=issuer_inventory,
            )

        expected_assertions = sorted(set(child_records) - set(parent_records))
        expected_dispositions = sorted(set(child_disps) - set(parent_disps))
        try:
            expected_provenance = compute_added_provenance_ids(
                parent_context, head.provenance_context
            )
            expected_grounding = compute_added_grounding_refs(
                parent_grounding, head.grounding
            )
        except StrictGroundingError as exc:
            raise StrictProjectionError(f"delta_recompute:{exc}") from exc

        if head.manifest["added_assertion_ids"] != expected_assertions:
            raise StrictProjectionError("added_assertion_ids_mismatch")
        if head.manifest["added_disposition_ids"] != expected_dispositions:
            raise StrictProjectionError("added_disposition_ids_mismatch")
        if head.manifest["added_provenance_ids"] != expected_provenance:
            raise StrictProjectionError("added_provenance_ids_mismatch")
        if head.manifest["added_grounding_refs"] != expected_grounding:
            raise StrictProjectionError("added_grounding_refs_mismatch")

        # Envelope/commitment bytes for retained provenance must be unchanged.
        if prev is not None:
            parent_reg = {
                e["assertion_id"]: strict_canonical_bytes(e)
                for e in prev.provenance_context["registered_assertions"]
            }
            child_reg = {
                e["assertion_id"]: strict_canonical_bytes(e)
                for e in head.provenance_context["registered_assertions"]
            }
            for aid, raw in parent_reg.items():
                if child_reg.get(aid) != raw:
                    raise StrictProjectionError("registered_assertion_mutated")

        prev = head


def _first_admission_index(heads: list[_AuthorityHead], *, field: str) -> dict[str, int]:
    first: dict[str, int] = {}
    for idx, head in enumerate(heads):
        for item_id in head.manifest[field]:
            if item_id not in first:
                first[item_id] = idx
    return first


def _verify_original_admission_qualifications(
    heads: list[_AuthorityHead],
    *,
    binding: Any,
    issuer_inventory: Mapping[str, bytes] | None,
) -> None:
    """Requalify each retained record at its original admission context."""

    tip = heads[-1]
    first_assertion = _first_admission_index(heads, field="added_assertion_ids")
    first_provenance = _first_admission_index(heads, field="added_provenance_ids")

    for rec in tip.records:
        aid = rec["assertion_id"]
        if aid not in first_assertion:
            raise StrictProjectionError("assertion_admission_missing")
        adm_idx = first_assertion[aid]
        adm = heads[adm_idx]
        # Retained tip bytes must equal the admission-head record bytes.
        adm_rec = next(r for r in adm.records if r["assertion_id"] == aid)
        if strict_canonical_bytes(adm_rec) != strict_canonical_bytes(rec):
            raise StrictProjectionError("record_bytes_not_retained")

        env = rec["provenance_envelope"]
        if not isinstance(env, Mapping):
            raise StrictProjectionError("record_envelope")
        prov_id = env.get("assertion_id")
        if not isinstance(prov_id, str) or not prov_id:
            raise StrictProjectionError("record_provenance_id")
        if prov_id not in first_provenance:
            raise StrictProjectionError("provenance_admission_missing")
        prov_idx = first_provenance[prov_id]
        prov_head = heads[prov_idx]

        try:
            quals = qualify_assertions(
                grounding=prov_head.grounding,
                provenance_context=prov_head.provenance_context,
                issuer_inventory=issuer_inventory,
                capture_issuers=binding.capture_issuers,
                allowed_issuer_ids={i.issuer_id for i in binding.capture_issuers},
                allowed_source_registration_ids={
                    r.id for r in binding.source_registrations
                },
            )
        except StrictGroundingError as exc:
            raise StrictProjectionError(f"original_admission_qualify:{exc}") from exc
        if prov_id not in quals:
            raise StrictProjectionError("original_admission_missing_tuple")
        expected_pq = quals[prov_id].as_dict()
        if rec["provenance_qualification"] != expected_pq:
            raise StrictProjectionError("original_qualification_mismatch")
        if rec["origin_assurance"] != derive_origin_assurance(quals[prov_id]):
            raise StrictProjectionError("original_origin_assurance_mismatch")

        # Expected eligibility from admission envelope + original qualification;
        # reject forged or drifted persisted check_eligibility.
        expected_eligibility = _eligibility_for_record(
            binding=binding,
            record_kind=rec["record_kind"],
            source_registration_id=rec["source_registration_id"],
            producer=rec["producer"],
            envelope=env,
            qualification=quals[prov_id],
        )
        if rec.get("check_eligibility") != expected_eligibility:
            raise StrictProjectionError("original_eligibility_mismatch")

        # Envelope/commitment frozen at provenance admission.
        prov_entry = next(
            e
            for e in prov_head.provenance_context["registered_assertions"]
            if e["assertion_id"] == prov_id
        )
        if strict_canonical_bytes(prov_entry["envelope"]) != strict_canonical_bytes(env):
            raise StrictProjectionError("envelope_not_retained")
        if rec["provenance_commitment"] != prov_entry["provenance_commitment"]:
            raise StrictProjectionError("commitment_not_retained")

        # Independent semantic/payload — do not trust stored claims.
        if rec["semantic_sha256"] != semantic_sha256(rec):
            raise StrictProjectionError("semantic_sha256_mismatch")
        if rec["payload_sha256"] != payload_sha256(rec):
            raise StrictProjectionError("payload_sha256_mismatch")


def _verify_citation_map(head: _AuthorityHead) -> None:
    try:
        expected = build_citation_map(head.records)
    except StrictEvidenceError as exc:
        raise StrictProjectionError(f"citation_rebuild:{exc}") from exc
    if strict_canonical_bytes(expected) != strict_canonical_bytes(head.citation_map):
        raise StrictProjectionError("citation_map_mismatch")
    for cite in head.citation_map["citations"]:
        if not isinstance(cite, dict):
            raise StrictProjectionError("citation_entry")
        # Empty placeholder bindings are forbidden when envelope had real bindings;
        # rebuild already copies envelope bytes — still reject swapped empties vs map.
        roots = cite.get("root_bindings")
        inputs = cite.get("input_bindings")
        if not isinstance(roots, list) or not isinstance(inputs, list):
            raise StrictProjectionError("citation_bindings")


def _independent_record_digests(records: list[dict[str, Any]]) -> None:
    for rec in records:
        if rec["semantic_sha256"] != semantic_sha256(rec):
            raise StrictProjectionError("semantic_sha256_mismatch")
        if rec["payload_sha256"] != payload_sha256(rec):
            raise StrictProjectionError("payload_sha256_mismatch")


def qualify_authority_generation(
    *,
    root: str | Path,
    scope: BoundReadScope,
    registry: ProjectBindingRegistry,
    expected_publication_sha256: str | None = None,
    require_serving: bool = False,
) -> QualifiedAuthorityGeneration:
    """Full private cold reconstruction over authority (+ projection when serving).

    Walks cumulative lineage to seq1 and replays forward. Reads private
    citation/grounding/provenance files. Independently recomputes state, citation
    map, and serving rows/graph. Never opens a query-time reducer path.
    """

    root_path = Path(root)
    if root_path.is_symlink() or not root_path.is_dir():
        raise StrictProjectionError("root_invalid")

    layout = _read_json(root_path / "layout.json")
    _require_closed(
        layout,
        _LAYOUT_FIELDS,
        schema="convmem.strict-generation-layout.v2",
        label="layout",
    )
    for key, expected in _LAYOUT_DIR_VALUES.items():
        if layout[key] != expected:
            raise StrictProjectionError(f"layout_dir:{key}")
    _require_self_hash(layout, "layout_payload_sha256", label="layout")

    enrollment = _read_json(root_path / "control" / "enrollment.json")
    _require_closed(
        enrollment,
        _ENROLLMENT_FIELDS,
        schema="convmem.strict-enrollment.v1",
        label="enrollment",
    )
    _require_self_hash(enrollment, "enrollment_payload_sha256", label="enrollment")
    lineage_id = enrollment["lineage_id"]
    if not isinstance(lineage_id, str) or len(lineage_id) != 32:
        raise StrictProjectionError("enrollment_lineage_id")

    semantic_contract = _read_json(root_path / "control" / "semantic-contract.json")
    _require_closed(
        semantic_contract,
        _SEMANTIC_CONTRACT_FIELDS,
        schema="convmem.strict-semantic-contract.v1",
        label="semantic_contract",
    )
    semantic_contract_sha256 = _require_self_hash(
        semantic_contract, "contract_payload_sha256", label="semantic_contract"
    )
    _enforce_semantic_contract(semantic_contract)
    if enrollment["semantic_contract_sha256"] != semantic_contract_sha256:
        raise StrictProjectionError("enrollment_semantic_contract_link")

    try:
        binding_id = scope.allowed_project_bindings[0]
        recomputed_owner = owner_digest(
            scope_sha256=scope.scope_sha256,
            registry_sha256=registry.registry_sha256,
            project_binding_id=binding_id,
        )
    except (BoundScopeError, IndexError, KeyError) as exc:
        raise StrictProjectionError("scope_registry") from exc

    if enrollment["owner_digest"] != recomputed_owner:
        raise StrictProjectionError("enrollment_owner_digest")
    if enrollment["scope_sha256"] != scope.scope_sha256:
        raise StrictProjectionError("enrollment_scope_link")
    if enrollment["registry_sha256"] != registry.registry_sha256:
        raise StrictProjectionError("enrollment_registry_link")

    pub_path = root_path / "active" / f"{lineage_id}.json"
    publication = _read_json(pub_path)
    _require_closed(
        publication,
        _PUBLICATION_FIELDS,
        schema="convmem.strict-publication.v2",
        label="publication",
    )
    if publication["lineage_id"] != lineage_id:
        raise StrictProjectionError("publication_lineage")
    pub_hash = _require_self_hash(
        publication, "publication_payload_sha256", label="publication"
    )
    if expected_publication_sha256 is not None and pub_hash != expected_publication_sha256:
        raise StrictProjectionError("publication_cas_mismatch")
    if publication["owner_digest"] != recomputed_owner:
        raise StrictProjectionError("publication_owner_digest")
    if publication["semantic_contract_sha256"] != semantic_contract_sha256:
        raise StrictProjectionError("publication_semantic_contract_link")

    mode = publication["mode"]
    if mode not in {"serving", "unavailable", "fenced"}:
        raise StrictProjectionError("publication_mode")
    if mode == "fenced":
        raise StrictProjectionError("publication_fenced")
    if require_serving and mode != "serving":
        raise StrictProjectionError("publication_not_serving")

    authority_seq = publication["authority_seq"]
    if not isinstance(authority_seq, int) or isinstance(authority_seq, bool) or authority_seq < 0:
        raise StrictProjectionError("authority_seq")

    if authority_seq == 0:
        if mode != "unavailable":
            raise StrictProjectionError("genesis_mode")
        if publication["authority_snapshot_id"] is not None:
            raise StrictProjectionError("genesis_snapshot_id")
        if publication["authority_manifest_sha256"] is not None:
            raise StrictProjectionError("genesis_authority_manifest")
        if publication["serving_generation_id"] is not None:
            raise StrictProjectionError("genesis_generation_id")
        if publication["projection_manifest_sha256"] is not None:
            raise StrictProjectionError("genesis_projection_manifest")
        if publication["freshness_anchor"] is not None:
            raise StrictProjectionError("genesis_freshness_anchor")
        if publication["pending_operation_id"] is not None:
            raise StrictProjectionError("genesis_pending")
        if (
            publication["authority_source_cutoff_sha256"]
            != enrollment["initial_source_cutoff_sha256"]
        ):
            raise StrictProjectionError("genesis_cutoff_link")
        empty_cutoff = _empty_source_cutoff_digest(
            lineage_id=lineage_id, mode=str(enrollment["mode"])
        )
        if enrollment["initial_source_cutoff_sha256"] != empty_cutoff:
            raise StrictProjectionError("enrollment_cutoff_mismatch")
        return QualifiedAuthorityGeneration(
            lineage_id=lineage_id,
            authority_seq=0,
            snapshot_id=None,
            authority_manifest_sha256=None,
            generation_id=None,
            projection_manifest_sha256=None,
            rows_sha256=None,
            graph_sha256=None,
            state_by_assertion={},
            publication_payload_sha256=pub_hash,
            semantic_contract_sha256=semantic_contract_sha256,
            expires_at=None,
            as_of=None,
        )

    snapshot_id = publication["authority_snapshot_id"]
    authority_manifest_sha256 = publication["authority_manifest_sha256"]
    if not isinstance(snapshot_id, str) or not snapshot_id.startswith("snap2_"):
        raise StrictProjectionError("authority_snapshot_id")
    if not isinstance(authority_manifest_sha256, str) or not authority_manifest_sha256.startswith(
        "sha256:"
    ):
        raise StrictProjectionError("authority_manifest_sha256")

    serving_generation_id = publication["serving_generation_id"]
    projection_manifest_sha256 = publication["projection_manifest_sha256"]
    if mode == "serving":
        if not isinstance(serving_generation_id, str) or not serving_generation_id.startswith(
            "gen2_"
        ):
            raise StrictProjectionError("serving_generation_id")
        if not isinstance(projection_manifest_sha256, str) or not projection_manifest_sha256.startswith(
            "sha256:"
        ):
            raise StrictProjectionError("projection_manifest_sha256")
        if publication["pending_operation_id"] is not None:
            raise StrictProjectionError("serving_pending")
        anchor = publication["freshness_anchor"]
        if not isinstance(anchor, dict):
            raise StrictProjectionError("freshness_anchor")
        if set(anchor) != _FRESHNESS_ANCHOR_FIELDS:
            raise StrictProjectionError("freshness_anchor_keys")
        if anchor["authority_snapshot_id"] != snapshot_id:
            raise StrictProjectionError("freshness_anchor_snapshot")
    else:
        if serving_generation_id is not None or projection_manifest_sha256 is not None:
            raise StrictProjectionError("unavailable_projection_ids")
        if publication["pending_operation_id"] is not None:
            raise StrictProjectionError("unavailable_pending")
        anchor = publication["freshness_anchor"]
        if not isinstance(anchor, dict):
            raise StrictProjectionError("freshness_anchor")
        if set(anchor) != _FRESHNESS_ANCHOR_FIELDS:
            raise StrictProjectionError("freshness_anchor_keys")
        if anchor["authority_snapshot_id"] != snapshot_id:
            raise StrictProjectionError("freshness_anchor_snapshot")

    binding = registry.binding(binding_id)
    try:
        issuer_inventory: Mapping[str, bytes] | None = (
            load_bound_issuer_inventories(binding.capture_issuers)
            if binding.capture_issuers
            else None
        )
    except StrictGroundingError as exc:
        raise StrictProjectionError(f"issuer_inventory:{exc}") from exc

    heads = _walk_lineage_forward(
        root_path,
        tip_snapshot_id=snapshot_id,
        tip_manifest_sha256=authority_manifest_sha256,
        tip_seq=authority_seq,
        lineage_id=lineage_id,
        owner_digest_value=recomputed_owner,
        scope_sha256=scope.scope_sha256,
        registry_sha256=registry.registry_sha256,
        semantic_contract_sha256=semantic_contract_sha256,
    )
    _replay_cumulative_and_deltas(
        heads,
        enrollment=enrollment,
        binding=binding,
        issuer_inventory=issuer_inventory,
    )
    tip = heads[-1]
    if publication["authority_source_cutoff_sha256"] != tip.cutoff["cutoff_payload_sha256"]:
        raise StrictProjectionError("publication_cutoff_link")
    if tip.manifest["reducer_version"] != semantic_contract["reducer_version"]:
        raise StrictProjectionError("authority_reducer_version")
    if tip.manifest["canonicalization_version"] != semantic_contract[
        "canonicalization_version"
    ]:
        raise StrictProjectionError("authority_canonicalization_version")

    _verify_original_admission_qualifications(
        heads, binding=binding, issuer_inventory=issuer_inventory
    )
    _independent_record_digests(tip.records)
    for head in heads:
        _verify_citation_map(head)

    # Never trust stored check_eligibility at reduce: rederive on copies only.
    eligibility_records = [dict(rec) for rec in tip.records]
    try:
        apply_verification_eligibility(eligibility_records, binding=binding)
        reduced = reduce_complete_bound_state(
            eligibility_records, tip.dispositions
        )
    except (StrictGroundingError, BoundScopeError, StrictEvidenceError, ValueError) as exc:
        raise StrictProjectionError(f"reduce:{exc}") from exc

    selectors = EffectiveSelectors(
        project=scope.project,
        site=scope.site,
        site_mode=scope.site_mode,
        domain=scope.domain,
        binding_id=binding_id,
    )
    for rec in tip.records:
        try:
            authorize_row(
                scope=scope,
                registry=registry,
                selectors=selectors,
                project_binding_id=rec["project_binding_id"],
                source_registration_id=rec["source_registration_id"],
                authority_site=rec["authority_site"],
                authority_domain=rec["authority_domain"],
            )
        except BoundScopeError as exc:
            raise StrictProjectionError(f"authorization:{exc}") from exc

    generation_id: str | None = None
    rows_sha256: str | None = None
    graph_sha256: str | None = None
    sealed_projection_manifest_sha256: str | None = None

    if mode == "serving":
        if not isinstance(serving_generation_id, str) or not isinstance(
            projection_manifest_sha256, str
        ):
            raise StrictProjectionError("serving_projection_required")
        generation_id = serving_generation_id
        sealed_projection_manifest_sha256 = projection_manifest_sha256

        gen_dir = root_path / "projection" / generation_id
        if gen_dir.is_symlink() or not gen_dir.is_dir():
            raise StrictProjectionError("projection_dir")

        proj_manifest = _read_json(gen_dir / "manifest.json")
        _require_closed(
            proj_manifest,
            _PROJECTION_MANIFEST_FIELDS,
            schema="convmem.bound-projection-manifest.v3",
            label="projection_manifest",
        )
        if proj_manifest["lineage_id"] != lineage_id:
            raise StrictProjectionError("projection_manifest_lineage")
        if proj_manifest["authority_seq"] != authority_seq:
            raise StrictProjectionError("projection_manifest_seq")
        if proj_manifest["owner_digest"] != recomputed_owner:
            raise StrictProjectionError("projection_manifest_owner")
        if proj_manifest["snapshot_id"] != snapshot_id:
            raise StrictProjectionError("projection_snapshot_link")
        if proj_manifest["authority_manifest_sha256"] != authority_manifest_sha256:
            raise StrictProjectionError("projection_authority_manifest_link")
        if proj_manifest["semantic_contract_sha256"] != semantic_contract_sha256:
            raise StrictProjectionError("projection_semantic_contract_link")
        if proj_manifest["scope_sha256"] != scope.scope_sha256:
            raise StrictProjectionError("projection_scope_link")
        if proj_manifest["registry_sha256"] != registry.registry_sha256:
            raise StrictProjectionError("projection_registry_link")
        if proj_manifest["as_of"] != tip.manifest["as_of"] or proj_manifest[
            "expires_at"
        ] != tip.manifest["expires_at"]:
            raise StrictProjectionError("projection_time_copy")
        if proj_manifest["search_kernel"] != semantic_contract["search_kernel"]:
            raise StrictProjectionError("projection_search_kernel")
        if proj_manifest["search_kernel_version"] != semantic_contract[
            "search_kernel_version"
        ]:
            raise StrictProjectionError("projection_search_kernel_version")
        if proj_manifest["tokenizer_unicode_version"] != semantic_contract[
            "tokenizer_unicode_version"
        ]:
            raise StrictProjectionError("projection_tokenizer_unicode_version")

        recomputed_generation_id = _projection_generation_id(proj_manifest)
        if proj_manifest["generation_id"] != recomputed_generation_id:
            raise StrictProjectionError("projection_generation_id_mismatch")
        if generation_id != recomputed_generation_id:
            raise StrictProjectionError("publication_generation_id_link")

        recomputed_proj_payload = _labeled_self_hash(proj_manifest, "manifest_payload_sha256")
        if proj_manifest["manifest_payload_sha256"] != recomputed_proj_payload:
            raise StrictProjectionError("projection_manifest_hash")
        if sealed_projection_manifest_sha256 != recomputed_proj_payload:
            raise StrictProjectionError("projection_manifest_link")

        stored_rows = _read_jsonl(gen_dir / "rows.jsonl")
        for row in stored_rows:
            _require_closed(
                row,
                _PROJECTION_ROW_FIELDS,
                schema="convmem.bound-projection-row.v2",
                label="projection_row",
            )
        stored_graph = _read_json(gen_dir / "graph.json")
        _require_closed(
            stored_graph, _GRAPH_FIELDS, schema="convmem.strict-graph.v1", label="graph"
        )

        try:
            expected_rows, expected_graph = build_projection_rows_and_graph(
                records=tip.records,
                reduced=reduced,
                lineage_id=lineage_id,
                authority_seq=authority_seq,
                authority_manifest_sha256=authority_manifest_sha256,
                semantic_contract_sha256=semantic_contract_sha256,
                binding_public_ref=binding.public_ref,
            )
        except StrictEvidenceError as exc:
            raise StrictProjectionError(f"projection_rebuild:{exc}") from exc

        if _canonical_jsonl_bytes(stored_rows) != _canonical_jsonl_bytes(expected_rows):
            raise StrictProjectionError("rows_byte_mismatch")
        if strict_canonical_bytes(stored_graph) != strict_canonical_bytes(expected_graph):
            raise StrictProjectionError("graph_byte_mismatch")

        rows_sha256 = _jsonl_sha256(stored_rows)
        if proj_manifest["rows_sha256"] != rows_sha256:
            raise StrictProjectionError("rows_hash_mismatch")
        if proj_manifest["row_count"] != len(stored_rows):
            raise StrictProjectionError("row_count")
        graph_sha256 = _require_self_hash(stored_graph, "graph_payload_sha256", label="graph")
        if proj_manifest["graph_sha256"] != graph_sha256:
            raise StrictProjectionError("graph_hash_mismatch")
        if proj_manifest["graph_node_count"] != len(stored_graph["nodes"]):
            raise StrictProjectionError("graph_node_count")

        for row in stored_rows:
            try:
                authorize_row(
                    scope=scope,
                    registry=registry,
                    selectors=selectors,
                    project_binding_id=row["project_binding_id"],
                    source_registration_id=row["source_registration_id"],
                    authority_site=row["authority_site"],
                    authority_domain=row["authority_domain"],
                )
            except BoundScopeError as exc:
                raise StrictProjectionError(f"row_authorization:{exc}") from exc

    return QualifiedAuthorityGeneration(
        lineage_id=lineage_id,
        authority_seq=authority_seq,
        snapshot_id=snapshot_id,
        authority_manifest_sha256=authority_manifest_sha256,
        generation_id=generation_id,
        projection_manifest_sha256=sealed_projection_manifest_sha256,
        rows_sha256=rows_sha256,
        graph_sha256=graph_sha256,
        state_by_assertion=reduced,
        publication_payload_sha256=pub_hash,
        semantic_contract_sha256=semantic_contract_sha256,
        expires_at=tip.manifest["expires_at"],
        as_of=tip.manifest["as_of"],
    )


# Intentionally no open_public_projection / revoke_snapshot / read CLI here (M4/T3).


__all__ = [
    "QualifiedAuthorityGeneration",
    "StrictProjectionError",
    "qualify_authority_generation",
]

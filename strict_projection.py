"""Private cold qualification and public projection read surface (T1–T3).

Parent recipes (d5f986f0 §6.5.4) — one exclusion/link rule each, no alternates:
- closed object self-hash excludes ONLY its named ``*_payload_sha256`` field
- ``snapshot_id = "snap2_" + sha256hex(canonical(manifest \\ {snapshot_id,
  manifest_payload_sha256}))``; then ``manifest_payload_sha256`` excludes only itself
- ``generation_id = "gen2_" + …`` analogously for projection manifests
- publication CAS compares the entire ``publication_payload_sha256``
- canonical JSONL: one object + LF per line; records by assertion_id; dispositions
  by ``disp_`` address; rows hash is SHA-256 of those exact JSONL bytes
- graph self-hash excludes only ``graph_payload_sha256``

T3 public opening: ``open_published_generation`` (parent) / ``open_public_projection``
(capability alias), ``StrictProjectionReader``, ``revoke_snapshot``, and the
``read`` CLI. Public opening does not import the publisher.
"""

# pylint: disable=C0302  # preserved projection authority/reader component boundary


from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
import re
import secrets
import stat
import sys
import time
import unicodedata
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from types import MappingProxyType
from typing import Any, Mapping, Sequence

from bound_read_scope import (
    BoundReadScope,
    BoundScopeError,
    EffectiveSelectors,
    OMITTED,
    ProjectBindingRegistry,
    authorize_row,
    load_bound_read_scope,
    load_project_binding_registry,
    owner_digest,
    resolve_selectors,
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
    looks_like_public_ledger_handle,
    materialize_authority_records,
    parse_public_ledger_handle,
    payload_sha256,
    reduce_complete_bound_state,
    semantic_sha256,
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
def _projection_field_set(*names: str) -> frozenset[str]:
    """Build projection closed field sets from an explicit name tuple."""

    return frozenset(names)


def _projection_inventory_lines(blob: str) -> tuple[str, ...]:
    """Projection-local inventory materializer (keeps byte-identical member strings)."""

    return tuple(line for line in blob.splitlines() if line)


_LAYOUT_FIELDS = _projection_field_set(
    "schema",
    "authority_dir",
    "projection_dir",
    "active_dir",
    "locks_dir",
    "control_dir",
    "layout_payload_sha256",
)
_ENROLLMENT_FIELDS = _projection_field_set(
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
)
_PUBLICATION_FIELDS = _projection_field_set(
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
)



_AUTHORITY_MANIFEST_FIELDS = _projection_field_set(
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
)
_PROJECTION_MANIFEST_FIELDS = _projection_field_set(
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
)


_SEMANTIC_CONTRACT_FIELDS = _projection_field_set(
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
_SOURCE_CUTOFF_FIELDS = _projection_field_set(
    "schema",
    "lineage_id",
    "mode",
    "operations",
    "cutoff_payload_sha256",
)
_CITATION_MAP_FIELDS = _projection_field_set(
    "schema",
    "citations",
    "citation_map_payload_sha256",
)
_PROVENANCE_CONTEXT_FIELDS = _projection_field_set(
    "schema",
    "schema_semantics",
    "policies",
    "recipes",
    "verified_channels",
    "registered_assertions",
    "grounding_sha256",
    "context_payload_sha256",
)
_GROUNDING_FIELDS = _projection_field_set(
    "schema",
    "blobs",
    "roots",
    "edges",
    "outputs",
    "receipts",
    "grounding_payload_sha256",
)
_AUTHORITY_RECORD_FIELDS = _projection_field_set(
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
)
_DISPOSITION_FIELDS = _projection_field_set(
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
)
_PROJECTION_ROW_FIELDS = _projection_field_set(
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
)
_GRAPH_FIELDS = _projection_field_set(
    "schema",
    "nodes",
    "edges",
    "graph_payload_sha256",
)
_GRAPH_EDGE_FIELDS = _projection_field_set(
    "kind",
    "from_assertion_id",
    "to_assertion_id",
)
_FRESHNESS_ANCHOR_FIELDS = _projection_field_set(
    "boot_id",
    "authority_snapshot_id",
    "sampled_wall_time",
    "sampled_boottime_ns",
    "snapshot_deadline_boottime_ns",
    "clock_review_ref",
)
_INPUT_PAYLOAD_FIELD = {
    "convmem.strict-fixture-bundle.v2": "fixture_payload_sha256",
    "convmem.approved-admission.v1": "artifact_payload_sha256",
}
_FIXTURE_BUNDLE_FIELDS = _projection_field_set(
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
)
_LAYOUT_DIR_VALUES = {
    "authority_dir": "authority",
    "projection_dir": "projection",
    "active_dir": "active",
    "locks_dir": "locks",
    "control_dir": "control",
}


@dataclass(frozen=True, slots=True)
class QualifiedAuthorityGeneration:  # pylint: disable=R0902  # attributes mirror qualified authority generation fields
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
    body = {k: v for k, v in manifest.items() if k not in {"snapshot_id", "manifest_payload_sha256"}}
    return "snap2_" + _sha256hex(strict_canonical_bytes(body))


def _projection_generation_id(manifest: Mapping[str, Any]) -> str:
    body = {k: v for k, v in manifest.items() if k not in {"generation_id", "manifest_payload_sha256"}}
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
class _AuthorityHead:  # pylint: disable=R0902  # attributes mirror authority-head reconstruction fields
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


def _lah_p0(work: SimpleNamespace) -> None:
    if not isinstance(work.snapshot_id, str) or not work.snapshot_id.startswith("snap2_"):
        raise StrictProjectionError("authority_snapshot_id")
    work.auth_dir = work.root_path / "authority" / work.snapshot_id
    if work.auth_dir.is_symlink() or not work.auth_dir.is_dir():
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
        work.path = work.auth_dir / name
        if not work.path.is_file() or work.path.is_symlink():
            raise StrictProjectionError(f"private_missing:{name}")
    work.manifest = _read_json(work.auth_dir / "manifest.json")
    _require_closed(
        work.manifest,
        _AUTHORITY_MANIFEST_FIELDS,
        schema="convmem.bound-authority-manifest.v3",
        label="authority_manifest",
    )
    if work.manifest["lineage_id"] != work.lineage_id:
        raise StrictProjectionError("authority_manifest_lineage")
    if work.manifest["owner_digest"] != work.owner_digest_value:
        raise StrictProjectionError("authority_manifest_owner")
    if work.manifest["semantic_contract_sha256"] != work.semantic_contract_sha256:
        raise StrictProjectionError("authority_manifest_semantic_contract_link")
    if work.manifest["scope_sha256"] != work.scope_sha256:
        raise StrictProjectionError("authority_manifest_scope_link")
    if work.manifest["registry_sha256"] != work.registry_sha256:
        raise StrictProjectionError("authority_manifest_registry_link")
    if work.manifest["snapshot_id"] != work.snapshot_id:
        raise StrictProjectionError("authority_snapshot_id_mismatch")
    work.recomputed_snapshot_id = _authority_snapshot_id(work.manifest)
    if work.manifest["snapshot_id"] != work.recomputed_snapshot_id:
        raise StrictProjectionError("authority_snapshot_id_recompute")
    work.recomputed_payload = _labeled_self_hash(work.manifest, "manifest_payload_sha256")
    if work.manifest["manifest_payload_sha256"] != work.recomputed_payload:
        raise StrictProjectionError("authority_manifest_hash")
    if work.expected_manifest_sha256 is not None and work.recomputed_payload != work.expected_manifest_sha256:
        raise StrictProjectionError("authority_manifest_link")
    work.seq = work.manifest["authority_seq"]
    if not isinstance(work.seq, int) or isinstance(work.seq, bool) or work.seq < 1:
        raise StrictProjectionError("authority_manifest_seq")
    if work.expected_seq is not None and work.seq != work.expected_seq:
        raise StrictProjectionError("authority_seq_mismatch")
    _sorted_unique_str_array(work.manifest["added_assertion_ids"], label="added_assertion_ids")


def _lah_p1(work: SimpleNamespace) -> None:
    _sorted_unique_str_array(work.manifest["added_disposition_ids"], label="added_disposition_ids")
    _sorted_unique_str_array(work.manifest["added_provenance_ids"], label="added_provenance_ids")
    _sorted_unique_str_array(work.manifest["added_grounding_refs"], label="added_grounding_refs")
    work.input_obj = _read_json(work.auth_dir / "input.json")
    work.input_digest = _input_payload_digest(work.input_obj)
    if work.manifest["input_sha256"] != work.input_digest:
        raise StrictProjectionError("input_link")
    work.cutoff = _read_json(work.auth_dir / "source-cutoff.json")
    _require_closed(work.cutoff, _SOURCE_CUTOFF_FIELDS, schema="convmem.strict-source-cutoff.v1", label="source_cutoff")
    if work.cutoff["lineage_id"] != work.lineage_id:
        raise StrictProjectionError("source_cutoff_lineage")
    work.cutoff_digest = _require_self_hash(work.cutoff, "cutoff_payload_sha256", label="source_cutoff")
    if work.manifest["source_cutoff_sha256"] != work.cutoff_digest:
        raise StrictProjectionError("source_cutoff_link")
    work.operations = work.cutoff["operations"]
    if not isinstance(work.operations, list):
        raise StrictProjectionError("source_cutoff_operations")
    work.seen_ops: set[str] = set()
    for op in work.operations:
        if not isinstance(op, dict) or set(op) != {"operation_id", "input_sha256", "source_prefix_sha256"}:
            raise StrictProjectionError("source_cutoff_operation_keys")
        work.oid = op["operation_id"]
        if not isinstance(work.oid, str) or not work.oid or work.oid in work.seen_ops:
            raise StrictProjectionError("source_cutoff_operation_id")
        work.seen_ops.add(work.oid)
    work.records = _read_jsonl(work.auth_dir / "records.jsonl")
    for rec in work.records:
        _require_closed(
            rec, _AUTHORITY_RECORD_FIELDS, schema="convmem.bound-authority-record.v3", label="authority_record"
        )
    work.record_ids = [r["assertion_id"] for r in work.records]
    if work.record_ids != sorted(work.record_ids) or len(work.record_ids) != len(set(work.record_ids)):
        raise StrictProjectionError("records_sort")
    work.records_digest = _jsonl_sha256(work.records)
    if work.manifest["authority_records_sha256"] != work.records_digest:
        raise StrictProjectionError("records_link")


def _lah_p2(work: SimpleNamespace) -> Any:
    if work.manifest["record_count"] != len(work.records):
        raise StrictProjectionError("record_count")
    work.dispositions = _read_jsonl(work.auth_dir / "dispositions.jsonl")
    for disp in work.dispositions:
        _require_closed(disp, _DISPOSITION_FIELDS, schema="convmem.authority-disposition.v1", label="disposition")
    work.disp_addrs = [disposition_id(d) for d in work.dispositions]
    if work.disp_addrs != sorted(work.disp_addrs) or len(work.disp_addrs) != len(set(work.disp_addrs)):
        raise StrictProjectionError("dispositions_sort")
    work.dispositions_digest = _jsonl_sha256(work.dispositions)
    if work.manifest["dispositions_sha256"] != work.dispositions_digest:
        raise StrictProjectionError("dispositions_link")
    if work.manifest["disposition_count"] != len(work.dispositions):
        raise StrictProjectionError("disposition_count")
    work.citation_map = _read_json(work.auth_dir / "citation-map.json")
    _require_closed(
        work.citation_map, _CITATION_MAP_FIELDS, schema="convmem.strict-citation-map.v1", label="citation_map"
    )
    work.citation_digest = _require_self_hash(work.citation_map, "citation_map_payload_sha256", label="citation_map")
    if work.manifest["citation_map_sha256"] != work.citation_digest:
        raise StrictProjectionError("citation_map_link")
    work.provenance_context = _read_json(work.auth_dir / "provenance-context.json")
    work.grounding = _read_json(work.auth_dir / "grounding.json")
    _require_closed(work.grounding, _GROUNDING_FIELDS, schema="convmem.strict-grounding.v1", label="grounding")
    work.grounding_digest = _require_self_hash(work.grounding, "grounding_payload_sha256", label="grounding")
    if work.manifest["grounding_sha256"] != work.grounding_digest:
        raise StrictProjectionError("grounding_link")
    try:
        work.provenance_context = validate_provenance_context(
            work.provenance_context, expected_grounding_sha256=work.grounding_digest
        )
    except StrictGroundingError as exc:
        raise StrictProjectionError(f"provenance_context:{exc}") from exc
    work.context_digest = work.provenance_context["context_payload_sha256"]
    if work.manifest["provenance_context_sha256"] != work.context_digest:
        raise StrictProjectionError("provenance_context_link")
    return _AuthorityHead(
        snapshot_id=work.snapshot_id,
        manifest=work.manifest,
        manifest_payload_sha256=work.recomputed_payload,
        input_obj=work.input_obj,
        cutoff=work.cutoff,
        records=work.records,
        dispositions=work.dispositions,
        citation_map=work.citation_map,
        provenance_context=work.provenance_context,
        grounding=work.grounding,
    )


def _load_authority_head(  # pylint: disable=R0913  # authority-head loader arity mirrors closed head inputs
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
    work = SimpleNamespace(
        root_path=root_path,
        snapshot_id=snapshot_id,
        lineage_id=lineage_id,
        owner_digest_value=owner_digest_value,
        scope_sha256=scope_sha256,
        registry_sha256=registry_sha256,
        semantic_contract_sha256=semantic_contract_sha256,
        expected_seq=expected_seq,
        expected_manifest_sha256=expected_manifest_sha256,
    )
    _lah_p0(work)
    _lah_p1(work)
    return _lah_p2(work)


def _irha_p0(work: SimpleNamespace) -> None:
    work.input_obj = work.head.input_obj
    work.batches = work.input_obj["batches"]
    if not isinstance(work.batches, list):
        raise StrictProjectionError("fixture_batches_type")
    work.prior_batches: list[Any] = []
    if work.prev is not None:
        work.prior_raw = work.prev.input_obj.get("batches")
        if not isinstance(work.prior_raw, list):
            raise StrictProjectionError("fixture_parent_batches_type")
        work.prior_batches = list(work.prior_raw)
    work.delta_batches = list(work.batches[len(work.prior_batches) :])
    work.parent_records = list(work.prev.records) if work.prev is not None else []
    work.parent_dispositions = list(work.prev.dispositions) if work.prev is not None else []
    work.parent_snapshot_id = work.prev.snapshot_id if work.prev is not None else None
    work.registered: dict[str, Any] = {}
    for entry in work.head.provenance_context["registered_assertions"]:
        aid = entry["assertion_id"]
        if aid in work.registered:
            raise StrictProjectionError("admission_registered_duplicate")
        work.registered[aid] = entry
    work.originals = _original_qualifications_from_records(work.parent_records)
    try:
        work.qual_map = qualify_assertions(
            grounding=work.head.grounding,
            provenance_context=work.head.provenance_context,
            issuer_inventory=work.issuer_inventory,
            capture_issuers=work.binding.capture_issuers,
            allowed_issuer_ids={i.issuer_id for i in work.binding.capture_issuers},
            allowed_source_registration_ids={r.id for r in work.binding.source_registrations},
            original_qualifications=work.originals or None,
        )
    except StrictGroundingError as exc:
        raise StrictProjectionError(f"admission_qualify:{exc}") from exc
    work.added_records: list[dict[str, Any]] = []


def _irha_p1(work: SimpleNamespace) -> None:
    for batch in work.delta_batches:
        if not isinstance(batch, Mapping):
            raise StrictProjectionError("admission_batch_type")
        try:
            work.new_recs = materialize_authority_records(
                binding=work.binding,
                source_registration_id=batch["source_registration_id"],
                scan=batch["source"],
                registered_assertions=work.registered,
                qualification_by_provenance=work.qual_map,
                prior_records=work.parent_records + work.added_records,
            )
        except StrictEvidenceError as exc:
            raise StrictProjectionError(f"admission_materialize:{exc}") from exc
        work.added_records.extend(work.new_recs)
    work.parent_ids = {r["assertion_id"] for r in work.parent_records}
    work.parent_disp_map = {disposition_id(d): d for d in work.parent_dispositions}
    work.parent_heads = (
        _parent_heads_by_logical(work.parent_records, work.parent_disp_map) if work.parent_records else {}
    )
    work.staging_records = list(work.parent_records) + [dict(r) for r in work.added_records]
    try:
        work.new_disp_map = validate_dispositions(
            list(work.input_obj["dispositions"]),
            records=work.staging_records,
            parent_snapshot_id=work.parent_snapshot_id,
            parent_heads_by_logical=work.parent_heads if work.parent_heads else None,
        )
    except StrictEvidenceError as exc:
        raise StrictProjectionError(f"admission_dispositions:{exc}") from exc
    work.added_by_id = {r["assertion_id"]: dict(r) for r in work.added_records}
    for disp_id, disp in work.new_disp_map.items():
        work.subject = disp["subject_assertion_id"]
        work.action = disp["action"]
        if work.subject in work.parent_ids:
            continue
        if work.subject not in work.added_by_id:
            raise StrictProjectionError("admission_disposition_subject")
        rec = work.added_by_id[work.subject]
        if work.action in {"decision_approved", "decision_rejected"}:
            rec["decision_disposition_ref"] = disp_id
        elif work.action == "supersession_authorized":
            rec["supersession_disposition_ref"] = disp_id
            rec["supersedes_assertion_ids"] = sorted(set(disp["target_assertion_ids"]))
        work.added_by_id[work.subject] = rec
    for rec in work.added_by_id.values():
        rec["semantic_sha256"] = semantic_sha256(rec)
        rec["payload_sha256"] = payload_sha256(rec)
    work.added_records = list(work.added_by_id.values())
    work.all_records = sorted(list(work.parent_records) + work.added_records, key=lambda r: r["assertion_id"])
    work.all_dispositions = list(work.parent_dispositions) + [work.new_disp_map[k] for k in sorted(work.new_disp_map)]
    work.all_dispositions.sort(key=disposition_id)


def _irha_p2(work: SimpleNamespace) -> None:
    work.reconstructed_added = {r["assertion_id"]: strict_canonical_bytes(r) for r in work.added_records}
    work.committed_parent = _record_bytes_by_id(work.parent_records)
    work.committed_child = _record_bytes_by_id(work.head.records)
    work.committed_added_ids = sorted(set(work.committed_child) - set(work.committed_parent))
    work.committed_added = {aid: work.committed_child[aid] for aid in work.committed_added_ids}
    if work.reconstructed_added != work.committed_added:
        raise StrictProjectionError("admission_added_records_mismatch")
    work.reconstructed_disp_ids = sorted(work.new_disp_map)
    if work.reconstructed_disp_ids != list(work.head.manifest["added_disposition_ids"]):
        raise StrictProjectionError("admission_added_disposition_ids_mismatch")
    work.committed_disp_bytes = _disposition_bytes_by_id(work.head.dispositions)
    for did in work.reconstructed_disp_ids:
        if did not in work.committed_disp_bytes:
            raise StrictProjectionError("admission_added_disposition_missing")
        if strict_canonical_bytes(work.new_disp_map[did]) != work.committed_disp_bytes[did]:
            raise StrictProjectionError("admission_added_disposition_bytes_mismatch")
    if _canonical_jsonl_bytes(work.all_records) != _canonical_jsonl_bytes(work.head.records):
        raise StrictProjectionError("admission_cumulative_records_mismatch")
    if _canonical_jsonl_bytes(work.all_dispositions) != _canonical_jsonl_bytes(work.head.dispositions):
        raise StrictProjectionError("admission_cumulative_dispositions_mismatch")


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
    work = SimpleNamespace(head=head, prev=prev, binding=binding, issuer_inventory=issuer_inventory)
    _irha_p0(work)
    _irha_p1(work)
    _irha_p2(work)


def _rcad_p0(work: SimpleNamespace) -> None:
    work.tip_builder_version = work.heads[-1].manifest["builder_version"]
    work.tip_builder_tree = work.heads[-1].manifest["builder_tree_sha256"]
    work.tip_reducer = work.heads[-1].manifest["reducer_version"]
    work.tip_canon = work.heads[-1].manifest["canonicalization_version"]
    if work.tip_builder_version != _FROZEN_BUILDER_VERSION:
        raise StrictProjectionError("builder_version_mismatch")
    work.recomputed_tree = _recompute_builder_tree_sha256()
    if work.tip_builder_tree != work.recomputed_tree:
        raise StrictProjectionError("builder_tree_mismatch")
    work.lineage_id = work.enrollment["lineage_id"]
    work.mode = work.enrollment["mode"]
    if not isinstance(work.mode, str):
        raise StrictProjectionError("enrollment_mode")
    work.empty_cutoff = _empty_source_cutoff_digest(lineage_id=work.lineage_id, mode=work.mode)
    if work.enrollment["initial_source_cutoff_sha256"] != work.empty_cutoff:
        raise StrictProjectionError("enrollment_cutoff_mismatch")
    work.prev: _AuthorityHead | None = None


def _rcad_check_builder_drift(work: SimpleNamespace, head) -> None:
    if head.manifest["builder_version"] != work.tip_builder_version:
        raise StrictProjectionError("builder_version_drift")
    if head.manifest["builder_tree_sha256"] != work.tip_builder_tree:
        raise StrictProjectionError("builder_tree_drift")
    if head.manifest["reducer_version"] != work.tip_reducer:
        raise StrictProjectionError("reducer_version_drift")
    if head.manifest["canonicalization_version"] != work.tip_canon:
        raise StrictProjectionError("canonicalization_version_drift")


def _rcad_process_head(work: SimpleNamespace, head) -> None:
    _rcad_check_builder_drift(work, head)
    work.parent_grounding = work.prev.grounding if work.prev is not None else None
    work.parent_context = work.prev.provenance_context if work.prev is not None else None
    try:
        assert_cumulative_grounding(work.parent_grounding, head.grounding)
        assert_cumulative_provenance_context(work.parent_context, head.provenance_context)
    except StrictGroundingError as exc:
        raise StrictProjectionError(f"cumulative_inventory:{exc}") from exc
    work.parent_records = _record_bytes_by_id(work.prev.records) if work.prev else {}
    work.child_records = _record_bytes_by_id(head.records)
    _assert_cumulative_maps(work.parent_records, work.child_records, label="records")
    work.parent_disps = _disposition_bytes_by_id(work.prev.dispositions) if work.prev else {}
    work.child_disps = _disposition_bytes_by_id(head.dispositions)
    _assert_cumulative_maps(work.parent_disps, work.child_disps, label="dispositions")
    if work.prev is not None:
        work.parent_ops = work.prev.cutoff["operations"]
        work.child_ops = head.cutoff["operations"]
        if work.child_ops[: len(work.parent_ops)] != work.parent_ops:
            raise StrictProjectionError("source_cutoff_not_prefix")
        if len(work.child_ops) != len(work.parent_ops) + 1:
            raise StrictProjectionError("source_cutoff_delta")
    elif len(head.cutoff["operations"]) != 1:
        raise StrictProjectionError("source_cutoff_genesis")
    _verify_fixture_source_cutoff_head(head, prev=work.prev, lineage_id=work.lineage_id, enrollment_mode=work.mode)
    if work.mode == "fixture":
        _independently_replay_head_admission(
            head, work.prev, binding=work.binding, issuer_inventory=work.issuer_inventory
        )
    work.expected_assertions = sorted(set(work.child_records) - set(work.parent_records))
    work.expected_dispositions = sorted(set(work.child_disps) - set(work.parent_disps))
    try:
        work.expected_provenance = compute_added_provenance_ids(work.parent_context, head.provenance_context)
        work.expected_grounding = compute_added_grounding_refs(work.parent_grounding, head.grounding)
    except StrictGroundingError as exc:
        raise StrictProjectionError(f"delta_recompute:{exc}") from exc
    if head.manifest["added_assertion_ids"] != work.expected_assertions:
        raise StrictProjectionError("added_assertion_ids_mismatch")
    if head.manifest["added_disposition_ids"] != work.expected_dispositions:
        raise StrictProjectionError("added_disposition_ids_mismatch")
    if head.manifest["added_provenance_ids"] != work.expected_provenance:
        raise StrictProjectionError("added_provenance_ids_mismatch")
    if head.manifest["added_grounding_refs"] != work.expected_grounding:
        raise StrictProjectionError("added_grounding_refs_mismatch")
    if work.prev is not None:
        work.parent_reg = {
            e["assertion_id"]: strict_canonical_bytes(e) for e in work.prev.provenance_context["registered_assertions"]
        }
        work.child_reg = {
            e["assertion_id"]: strict_canonical_bytes(e) for e in head.provenance_context["registered_assertions"]
        }
        for aid, raw in work.parent_reg.items():
            if work.child_reg.get(aid) != raw:
                raise StrictProjectionError("registered_assertion_mutated")
    work.prev = head


def _rcad_p1(work: SimpleNamespace) -> None:
    for head in work.heads:
        _rcad_process_head(work, head)


def _replay_cumulative_and_deltas(
    heads: list[_AuthorityHead],
    *,
    enrollment: Mapping[str, Any],
    binding: Any,
    issuer_inventory: Mapping[str, bytes] | None,
) -> None:
    work = SimpleNamespace(heads=heads, enrollment=enrollment, binding=binding, issuer_inventory=issuer_inventory)
    _rcad_p0(work)
    _rcad_p1(work)


def _walk_lineage_forward(  # pylint: disable=R0913  # lineage walk arity mirrors closed lineage inputs
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
_BUILDER_CORE_MEMBERS: tuple[str, ...] = tuple(
    member
    for member in (
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
)

_BUILDER_SCHEMAS_GATE_B: tuple[str, ...] = (
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
)
_BUILDER_SCHEMAS_GATE_C: tuple[str, ...] = (
    "schemas/convmem-openclaw-connector-launch-v2.schema.json",
    "schemas/convmem-openclaw-activation-v2.schema.json",
    "schemas/convmem-activation-control-v1.schema.json",
    "schemas/convmem-activation-retirement-v1.schema.json",
    "schemas/convmem-activation-launch-policy-v1.schema.json",
    "schemas/convmem-activation-manager-policy-v1.schema.json",
    "schemas/convmem-controller-socket-policy-v1.schema.json",
)
_BUILDER_SCHEMAS_BC: tuple[str, ...] = _BUILDER_SCHEMAS_GATE_B + _BUILDER_SCHEMAS_GATE_C

_BUILDER_TREE_MEMBERS: tuple[str, ...] = tuple(
    sorted(set(_BUILDER_CORE_MEMBERS) | set(_BUILDER_SCHEMAS_BC) | {"strict_projection_publisher.py"})
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
        if strict_canonical_bytes(list(batches[: len(prior_batches)])) != (strict_canonical_bytes(prior_batches)):
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
                allowed_source_registration_ids={r.id for r in binding.source_registrations},
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
            e for e in prov_head.provenance_context["registered_assertions"] if e["assertion_id"] == prov_id
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


def _qauth_qualify_authority_generation_p0(work: SimpleNamespace) -> None:
    work.root_path = Path(work.root)
    if work.root_path.is_symlink() or not work.root_path.is_dir():
        raise StrictProjectionError("root_invalid")
    work.layout = _read_json(work.root_path / "layout.json")
    _require_closed(work.layout, _LAYOUT_FIELDS, schema="convmem.strict-generation-layout.v2", label="layout")
    for key, expected in _LAYOUT_DIR_VALUES.items():
        if work.layout[key] != expected:
            raise StrictProjectionError(f"layout_dir:{key}")
    _require_self_hash(work.layout, "layout_payload_sha256", label="layout")
    work.enrollment = _read_json(work.root_path / "control" / "enrollment.json")


def _qauth_qualify_authority_generation_p1(work: SimpleNamespace) -> None:
    _require_closed(work.enrollment, _ENROLLMENT_FIELDS, schema="convmem.strict-enrollment.v1", label="enrollment")
    _require_self_hash(work.enrollment, "enrollment_payload_sha256", label="enrollment")
    work.lineage_id = work.enrollment["lineage_id"]
    if not isinstance(work.lineage_id, str) or len(work.lineage_id) != 32:
        raise StrictProjectionError("enrollment_lineage_id")
    work.semantic_contract = _read_json(work.root_path / "control" / "semantic-contract.json")
    _require_closed(
        work.semantic_contract,
        _SEMANTIC_CONTRACT_FIELDS,
        schema="convmem.strict-semantic-contract.v1",
        label="semantic_contract",
    )
    work.semantic_contract_sha256 = _require_self_hash(
        work.semantic_contract, "contract_payload_sha256", label="semantic_contract"
    )
    _enforce_semantic_contract(work.semantic_contract)


def _qauth_qualify_authority_generation_p2(work: SimpleNamespace) -> None:
    if work.enrollment["semantic_contract_sha256"] != work.semantic_contract_sha256:
        raise StrictProjectionError("enrollment_semantic_contract_link")
    try:
        work.binding_id = work.scope.allowed_project_bindings[0]
        work.recomputed_owner = owner_digest(
            scope_sha256=work.scope.scope_sha256,
            registry_sha256=work.registry.registry_sha256,
            project_binding_id=work.binding_id,
        )
    except (BoundScopeError, IndexError, KeyError) as exc:
        raise StrictProjectionError("scope_registry") from exc
    if work.enrollment["owner_digest"] != work.recomputed_owner:
        raise StrictProjectionError("enrollment_owner_digest")
    if work.enrollment["scope_sha256"] != work.scope.scope_sha256:
        raise StrictProjectionError("enrollment_scope_link")
    if work.enrollment["registry_sha256"] != work.registry.registry_sha256:
        raise StrictProjectionError("enrollment_registry_link")
    work.pub_path = work.root_path / "active" / f"{work.lineage_id}.json"
    work.publication = _read_json(work.pub_path)
    _require_closed(work.publication, _PUBLICATION_FIELDS, schema="convmem.strict-publication.v2", label="publication")


def _qauth_qualify_authority_generation_p3(work: SimpleNamespace) -> None:
    if work.publication["lineage_id"] != work.lineage_id:
        raise StrictProjectionError("publication_lineage")
    work.pub_hash = _require_self_hash(work.publication, "publication_payload_sha256", label="publication")
    if work.expected_publication_sha256 is not None and work.pub_hash != work.expected_publication_sha256:
        raise StrictProjectionError("publication_cas_mismatch")
    if work.publication["owner_digest"] != work.recomputed_owner:
        raise StrictProjectionError("publication_owner_digest")
    if work.publication["semantic_contract_sha256"] != work.semantic_contract_sha256:
        raise StrictProjectionError("publication_semantic_contract_link")
    work.mode = work.publication["mode"]
    if work.mode not in {"serving", "unavailable", "fenced"}:
        raise StrictProjectionError("publication_mode")
    if work.mode == "fenced":
        raise StrictProjectionError("publication_fenced")


def _qauth_qualify_authority_generation_p4(work: SimpleNamespace) -> QualifiedAuthorityGeneration | None:
    if work.require_serving and work.mode != "serving":
        raise StrictProjectionError("publication_not_serving")
    work.authority_seq = work.publication["authority_seq"]
    if not isinstance(work.authority_seq, int) or isinstance(work.authority_seq, bool) or work.authority_seq < 0:
        raise StrictProjectionError("authority_seq")
    if work.authority_seq == 0:
        if work.mode != "unavailable":
            raise StrictProjectionError("genesis_mode")
        if work.publication["authority_snapshot_id"] is not None:
            raise StrictProjectionError("genesis_snapshot_id")
        if work.publication["authority_manifest_sha256"] is not None:
            raise StrictProjectionError("genesis_authority_manifest")
        if work.publication["serving_generation_id"] is not None:
            raise StrictProjectionError("genesis_generation_id")
        if work.publication["projection_manifest_sha256"] is not None:
            raise StrictProjectionError("genesis_projection_manifest")
        if work.publication["freshness_anchor"] is not None:
            raise StrictProjectionError("genesis_freshness_anchor")
        if work.publication["pending_operation_id"] is not None:
            raise StrictProjectionError("genesis_pending")
        if work.publication["authority_source_cutoff_sha256"] != work.enrollment["initial_source_cutoff_sha256"]:
            raise StrictProjectionError("genesis_cutoff_link")
        work.empty_cutoff = _empty_source_cutoff_digest(lineage_id=work.lineage_id, mode=str(work.enrollment["mode"]))
        if work.enrollment["initial_source_cutoff_sha256"] != work.empty_cutoff:
            raise StrictProjectionError("enrollment_cutoff_mismatch")
        return QualifiedAuthorityGeneration(
            lineage_id=work.lineage_id,
            authority_seq=0,
            snapshot_id=None,
            authority_manifest_sha256=None,
            generation_id=None,
            projection_manifest_sha256=None,
            rows_sha256=None,
            graph_sha256=None,
            state_by_assertion={},
            publication_payload_sha256=work.pub_hash,
            semantic_contract_sha256=work.semantic_contract_sha256,
            expires_at=None,
            as_of=None,
        )
    work.snapshot_id = work.publication["authority_snapshot_id"]
    work.authority_manifest_sha256 = work.publication["authority_manifest_sha256"]
    if not isinstance(work.snapshot_id, str) or not work.snapshot_id.startswith("snap2_"):
        raise StrictProjectionError("authority_snapshot_id")
    if not isinstance(work.authority_manifest_sha256, str) or not work.authority_manifest_sha256.startswith("sha256:"):
        raise StrictProjectionError("authority_manifest_sha256")
    return None


def _qauth_qualify_authority_generation_p5(work: SimpleNamespace) -> None:
    work.serving_generation_id = work.publication["serving_generation_id"]
    work.projection_manifest_sha256 = work.publication["projection_manifest_sha256"]
    if work.mode == "serving":
        if not isinstance(work.serving_generation_id, str) or not work.serving_generation_id.startswith("gen2_"):
            raise StrictProjectionError("serving_generation_id")
        if not isinstance(work.projection_manifest_sha256, str) or not work.projection_manifest_sha256.startswith(
            "sha256:"
        ):
            raise StrictProjectionError("projection_manifest_sha256")
        if work.publication["pending_operation_id"] is not None:
            raise StrictProjectionError("serving_pending")
        work.anchor = work.publication["freshness_anchor"]
        if not isinstance(work.anchor, dict):
            raise StrictProjectionError("freshness_anchor")
        if set(work.anchor) != _FRESHNESS_ANCHOR_FIELDS:
            raise StrictProjectionError("freshness_anchor_keys")
        if work.anchor["authority_snapshot_id"] != work.snapshot_id:
            raise StrictProjectionError("freshness_anchor_snapshot")
    else:
        if work.serving_generation_id is not None or work.projection_manifest_sha256 is not None:
            raise StrictProjectionError("unavailable_projection_ids")
        if work.publication["pending_operation_id"] is not None:
            raise StrictProjectionError("unavailable_pending")
        work.anchor = work.publication["freshness_anchor"]
        if not isinstance(work.anchor, dict):
            raise StrictProjectionError("freshness_anchor")
        if set(work.anchor) != _FRESHNESS_ANCHOR_FIELDS:
            raise StrictProjectionError("freshness_anchor_keys")
        if work.anchor["authority_snapshot_id"] != work.snapshot_id:
            raise StrictProjectionError("freshness_anchor_snapshot")
    work.binding = work.registry.binding(work.binding_id)
    try:
        work.issuer_inventory: Mapping[str, bytes] | None = (
            load_bound_issuer_inventories(work.binding.capture_issuers) if work.binding.capture_issuers else None
        )
    except StrictGroundingError as exc:
        raise StrictProjectionError(f"issuer_inventory:{exc}") from exc
    work.heads = _walk_lineage_forward(
        work.root_path,
        tip_snapshot_id=work.snapshot_id,
        tip_manifest_sha256=work.authority_manifest_sha256,
        tip_seq=work.authority_seq,
        lineage_id=work.lineage_id,
        owner_digest_value=work.recomputed_owner,
        scope_sha256=work.scope.scope_sha256,
        registry_sha256=work.registry.registry_sha256,
        semantic_contract_sha256=work.semantic_contract_sha256,
    )
    _replay_cumulative_and_deltas(
        work.heads, enrollment=work.enrollment, binding=work.binding, issuer_inventory=work.issuer_inventory
    )
    work.tip = work.heads[-1]


def _qauth_qualify_authority_generation_p6(work: SimpleNamespace) -> None:
    if work.publication["authority_source_cutoff_sha256"] != work.tip.cutoff["cutoff_payload_sha256"]:
        raise StrictProjectionError("publication_cutoff_link")
    if work.tip.manifest["reducer_version"] != work.semantic_contract["reducer_version"]:
        raise StrictProjectionError("authority_reducer_version")
    if work.tip.manifest["canonicalization_version"] != work.semantic_contract["canonicalization_version"]:
        raise StrictProjectionError("authority_canonicalization_version")
    _verify_original_admission_qualifications(work.heads, binding=work.binding, issuer_inventory=work.issuer_inventory)
    _independent_record_digests(work.tip.records)
    for head in work.heads:
        _verify_citation_map(head)
    work.eligibility_records = [dict(rec) for rec in work.tip.records]
    try:
        apply_verification_eligibility(work.eligibility_records, binding=work.binding)
        work.reduced = reduce_complete_bound_state(work.eligibility_records, work.tip.dispositions)
    except (StrictGroundingError, BoundScopeError, StrictEvidenceError, ValueError) as exc:
        raise StrictProjectionError(f"reduce:{exc}") from exc


def _x_qualify_authority_generation_p7_0(work: SimpleNamespace) -> None:
    work.selectors = EffectiveSelectors(
        project=work.scope.project,
        site=work.scope.site,
        site_mode=work.scope.site_mode,
        domain=work.scope.domain,
        binding_id=work.binding_id,
    )
    for rec in work.tip.records:
        try:
            authorize_row(
                scope=work.scope,
                registry=work.registry,
                selectors=work.selectors,
                project_binding_id=rec["project_binding_id"],
                source_registration_id=rec["source_registration_id"],
                authority_site=rec["authority_site"],
                authority_domain=rec["authority_domain"],
            )
        except BoundScopeError as exc:
            raise StrictProjectionError(f"authorization:{exc}") from exc


def _x_qualify_authority_generation_p7_1(work: SimpleNamespace) -> None:
    work.generation_id: str | None = None
    work.rows_sha256: str | None = None


def _x_qualify_authority_generation_p7_2(work: SimpleNamespace) -> None:
    work.graph_sha256: str | None = None
    work.sealed_projection_manifest_sha256: str | None = None


def _x_qualify_authority_generation_p7_3_c0(work: SimpleNamespace) -> None:
    if not isinstance(work.serving_generation_id, str) or not isinstance(work.projection_manifest_sha256, str):
        raise StrictProjectionError("serving_projection_required")
    work.generation_id = work.serving_generation_id
    work.sealed_projection_manifest_sha256 = work.projection_manifest_sha256
    work.gen_dir = work.root_path / "projection" / work.generation_id
    if work.gen_dir.is_symlink() or not work.gen_dir.is_dir():
        raise StrictProjectionError("projection_dir")
    work.proj_manifest = _read_json(work.gen_dir / "manifest.json")
    _require_closed(
        work.proj_manifest,
        _PROJECTION_MANIFEST_FIELDS,
        schema="convmem.bound-projection-manifest.v3",
        label="projection_manifest",
    )
    if work.proj_manifest["lineage_id"] != work.lineage_id:
        raise StrictProjectionError("projection_manifest_lineage")
    if work.proj_manifest["authority_seq"] != work.authority_seq:
        raise StrictProjectionError("projection_manifest_seq")


def _x_qualify_authority_generation_p7_3_c1(work: SimpleNamespace) -> None:
    if work.proj_manifest["owner_digest"] != work.recomputed_owner:
        raise StrictProjectionError("projection_manifest_owner")
    if work.proj_manifest["snapshot_id"] != work.snapshot_id:
        raise StrictProjectionError("projection_snapshot_link")
    if work.proj_manifest["authority_manifest_sha256"] != work.authority_manifest_sha256:
        raise StrictProjectionError("projection_authority_manifest_link")
    if work.proj_manifest["semantic_contract_sha256"] != work.semantic_contract_sha256:
        raise StrictProjectionError("projection_semantic_contract_link")
    if work.proj_manifest["scope_sha256"] != work.scope.scope_sha256:
        raise StrictProjectionError("projection_scope_link")
    if work.proj_manifest["registry_sha256"] != work.registry.registry_sha256:
        raise StrictProjectionError("projection_registry_link")
    if (
        work.proj_manifest["as_of"] != work.tip.manifest["as_of"]
        or work.proj_manifest["expires_at"] != work.tip.manifest["expires_at"]
    ):
        raise StrictProjectionError("projection_time_copy")
    if work.proj_manifest["search_kernel"] != work.semantic_contract["search_kernel"]:
        raise StrictProjectionError("projection_search_kernel")
    if work.proj_manifest["search_kernel_version"] != work.semantic_contract["search_kernel_version"]:
        raise StrictProjectionError("projection_search_kernel_version")
    if work.proj_manifest["tokenizer_unicode_version"] != work.semantic_contract["tokenizer_unicode_version"]:
        raise StrictProjectionError("projection_tokenizer_unicode_version")


def _x_qualify_authority_generation_p7_3_c2(work: SimpleNamespace) -> None:
    work.recomputed_generation_id = _projection_generation_id(work.proj_manifest)
    if work.proj_manifest["generation_id"] != work.recomputed_generation_id:
        raise StrictProjectionError("projection_generation_id_mismatch")
    if work.generation_id != work.recomputed_generation_id:
        raise StrictProjectionError("publication_generation_id_link")
    work.recomputed_proj_payload = _labeled_self_hash(work.proj_manifest, "manifest_payload_sha256")
    if work.proj_manifest["manifest_payload_sha256"] != work.recomputed_proj_payload:
        raise StrictProjectionError("projection_manifest_hash")
    if work.sealed_projection_manifest_sha256 != work.recomputed_proj_payload:
        raise StrictProjectionError("projection_manifest_link")
    work.stored_rows = _read_jsonl(work.gen_dir / "rows.jsonl")
    for row in work.stored_rows:
        _require_closed(row, _PROJECTION_ROW_FIELDS, schema="convmem.bound-projection-row.v2", label="projection_row")
    work.stored_graph = _read_json(work.gen_dir / "graph.json")
    _require_closed(work.stored_graph, _GRAPH_FIELDS, schema="convmem.strict-graph.v1", label="graph")


def _x_qualify_authority_generation_p7_3_c3(work: SimpleNamespace) -> None:
    try:
        work.expected_rows, work.expected_graph = build_projection_rows_and_graph(
            records=work.tip.records,
            reduced=work.reduced,
            lineage_id=work.lineage_id,
            authority_seq=work.authority_seq,
            authority_manifest_sha256=work.authority_manifest_sha256,
            semantic_contract_sha256=work.semantic_contract_sha256,
            binding_public_ref=work.binding.public_ref,
        )
    except StrictEvidenceError as exc:
        raise StrictProjectionError(f"projection_rebuild:{exc}") from exc
    if _canonical_jsonl_bytes(work.stored_rows) != _canonical_jsonl_bytes(work.expected_rows):
        raise StrictProjectionError("rows_byte_mismatch")
    if strict_canonical_bytes(work.stored_graph) != strict_canonical_bytes(work.expected_graph):
        raise StrictProjectionError("graph_byte_mismatch")
    work.rows_sha256 = _jsonl_sha256(work.stored_rows)
    if work.proj_manifest["rows_sha256"] != work.rows_sha256:
        raise StrictProjectionError("rows_hash_mismatch")
    if work.proj_manifest["row_count"] != len(work.stored_rows):
        raise StrictProjectionError("row_count")
    work.graph_sha256 = _require_self_hash(work.stored_graph, "graph_payload_sha256", label="graph")
    if work.proj_manifest["graph_sha256"] != work.graph_sha256:
        raise StrictProjectionError("graph_hash_mismatch")
    if work.proj_manifest["graph_node_count"] != len(work.stored_graph["nodes"]):
        raise StrictProjectionError("graph_node_count")
    for row in work.stored_rows:
        try:
            authorize_row(
                scope=work.scope,
                registry=work.registry,
                selectors=work.selectors,
                project_binding_id=row["project_binding_id"],
                source_registration_id=row["source_registration_id"],
                authority_site=row["authority_site"],
                authority_domain=row["authority_domain"],
            )
        except BoundScopeError as exc:
            raise StrictProjectionError(f"row_authorization:{exc}") from exc


def _x_qualify_authority_generation_p7_3(work: SimpleNamespace) -> QualifiedAuthorityGeneration:

    if work.mode == "serving":
        _x_qualify_authority_generation_p7_3_c0(work)
        _x_qualify_authority_generation_p7_3_c1(work)
        _x_qualify_authority_generation_p7_3_c2(work)
        _x_qualify_authority_generation_p7_3_c3(work)
    return QualifiedAuthorityGeneration(
        lineage_id=work.lineage_id,
        authority_seq=work.authority_seq,
        snapshot_id=work.snapshot_id,
        authority_manifest_sha256=work.authority_manifest_sha256,
        generation_id=work.generation_id,
        projection_manifest_sha256=work.sealed_projection_manifest_sha256,
        rows_sha256=work.rows_sha256,
        graph_sha256=work.graph_sha256,
        state_by_assertion=work.reduced,
        publication_payload_sha256=work.pub_hash,
        semantic_contract_sha256=work.semantic_contract_sha256,
        expires_at=work.tip.manifest["expires_at"],
        as_of=work.tip.manifest["as_of"],
    )


def _qauth_qualify_authority_generation_p7(work: SimpleNamespace) -> QualifiedAuthorityGeneration:

    _x_qualify_authority_generation_p7_0(work)
    _x_qualify_authority_generation_p7_1(work)
    _x_qualify_authority_generation_p7_2(work)
    return _x_qualify_authority_generation_p7_3(work)


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
    work = SimpleNamespace()
    work.expected_publication_sha256 = expected_publication_sha256
    work.registry = registry
    work.require_serving = require_serving
    work.root = root
    work.scope = scope

    _qauth_qualify_authority_generation_p0(work)
    _qauth_qualify_authority_generation_p1(work)
    _qauth_qualify_authority_generation_p2(work)
    _qauth_qualify_authority_generation_p3(work)
    _out = _qauth_qualify_authority_generation_p4(work)
    if _out is not None:
        return _out
    _qauth_qualify_authority_generation_p5(work)
    _qauth_qualify_authority_generation_p6(work)
    return _qauth_qualify_authority_generation_p7(work)


# ---------------------------------------------------------------------------
# T3 — public opening, lexical reader, errors, CLI (Architecture §§6.5.4–6.5.5, 8, 11)
# ---------------------------------------------------------------------------

_ERROR_MESSAGES: Mapping[str, str] = {
    "invalid_request": "The request is invalid.",
    "identifier_query_not_supported": "Ledger handles are not supported in search.",
    "scope_denied": "The requested evidence chain is unavailable in this scope.",
    "snapshot_stale": "The evidence snapshot is unavailable.",
    "response_too_large": "The evidence response exceeds the allowed size.",
    "temporarily_unavailable": "The evidence service is temporarily unavailable.",
    "internal_failure": "The evidence service failed.",
}

_RESPONSE_BYTE_CAP = 65536
_DOC_CODEPOINT_CAP = 4096
_QUERY_CODEPOINT_CAP = 2048
_QUERY_TOKEN_CAP = 64
_SEARCH_TOP_K_DEFAULT = 5
_SEARCH_TOP_K_MAX = 10
_UNRESOLVED_LIMIT_DEFAULT = 20
_UNRESOLVED_LIMIT_MAX = 50
_RELATED_NEIGHBORHOOD_CAP = 200
_RELATED_PARENT_HOPS = 8
_RELATED_DESCENDANT_DEPTH = 2
_CURRENT_RANK_STATES = _projection_field_set(
    "current",
    "approved",
    "conflict",
)
_STRICT_CONFIG_FIELDS = _projection_field_set(
    "schema",
    "projection_root",
    "max_projection_rows",
    "max_projection_bytes",
    "telemetry",
)


class StrictPublicError(Exception):
    """Public tool/CLI error carrying a closed convmem.error.v1 payload."""

    def __init__(self, code: str, *, correlation_id: str | None = None) -> None:
        if code not in _ERROR_MESSAGES:
            code = "internal_failure"
        self.code = code
        self.correlation_id = correlation_id or secrets.token_hex(16)
        self.payload = {
            "schema": "convmem.error.v1",
            "error": {"code": self.code, "message": _ERROR_MESSAGES[self.code]},
            "correlation_id": self.correlation_id,
        }
        super().__init__(self.code)


# Module seal for QualifiedStrictGeneration — forge attempts never become live.
_CAPABILITY_SEAL = object()
# Token-keyed live set — never keyed by id() (id reuse after GC is unsafe).
_LIVE_CAPABILITY_TOKENS: set[object] = set()

_PUBLIC_FILE_MODE = 0o444
_PUBLIC_DIR_MODE = 0o555
_GRAPH_EDGE_KINDS = _projection_field_set(
    "relates_to",
    "targets",
    "supersedes",
)
_RECORD_KINDS = _projection_field_set(
    "observation",
    "decision",
    "verification",
)
_CAPTURE_VALUES = _projection_field_set(
    "synthetic_fixture",
    "controlled_capture",
    "unattested",
)
_PROVENANCE_QUAL_FIELDS = _projection_field_set(
    "commitments",
    "byte_grounding",
    "capture",
    "transformer_cap",
)
_CLI_BOOTTIME_BUDGET_NS = 10_000_000_000
# Pin identity: (st_dev, st_ino, mode, content_sha256).
OperatorPin = tuple[int, int, int, str]
PublicPin = tuple[int, int, int, str]

# Public-opening must never consult these private relative paths.
_PRIVATE_RELATIVE_FORBIDDEN = frozenset(_projection_inventory_lines("""layout.json
control/enrollment.json
control/slot.json
control/semantic-contract.json"""))
_PRIVATE_BASENAMES_FORBIDDEN = frozenset(_projection_inventory_lines("""input.json
source-cutoff.json
records.jsonl
dispositions.jsonl
citation-map.json
provenance-context.json
grounding.json"""))

# Public mount members (Architecture §6.5.4) — only these are opened.
_PUBLIC_MOUNT_FILES = (
    "active/{lineage_id}.json",
    "authority/{snapshot_id}/manifest.json",
    "projection/{generation_id}/manifest.json",
    "projection/{generation_id}/rows.jsonl",
    "projection/{generation_id}/graph.json",
    "locks/{lineage_id}.lock",
)


class QualifiedStrictGeneration:
    """Module-sealed public read capability (Architecture §6.5.4).

    Constructible only via ``_seal_qualified_generation`` from
    ``open_published_generation``. Dataclass-style construction and public-field
    mutation cannot mint a usable live capability.
    """

    __slots__ = (
        "lineage_id",
        "authority_seq",
        "snapshot_id",
        "authority_manifest_sha256",
        "generation_id",
        "projection_manifest_sha256",
        "rows_sha256",
        "graph_sha256",
        "publication_payload_sha256",
        "semantic_contract_sha256",
        "as_of",
        "expires_at",
        "scope",
        "registry",
        "rows",
        "graph",
        "_revoked",
        "_seal",
        "_token",
        "_frozen",
        "_lock_fd",
        "_lock_inode",
        "_pinned_public",
        "_operator_path_pins",
        "_root",
        "_publication_path",
    )

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        raise TypeError("QualifiedStrictGeneration is module-sealed; use open_published_generation")

    def __setattr__(self, name: str, value: Any) -> None:
        if getattr(self, "_frozen", False):
            raise AttributeError("QualifiedStrictGeneration is immutable after mint")
        object.__setattr__(self, name, value)

    def __delattr__(self, name: str) -> None:
        if getattr(self, "_frozen", False):
            raise AttributeError("QualifiedStrictGeneration is immutable after mint")
        object.__delattr__(self, name)

    @property
    def is_revoked(self) -> bool:
        return bool(getattr(self, "_revoked", True))

    def mark_revoked(self) -> None:
        if getattr(self, "_seal", None) is not _CAPABILITY_SEAL:
            raise StrictProjectionError("forged_capability")
        token = getattr(self, "_token", None)
        object.__setattr__(self, "_frozen", False)
        object.__setattr__(self, "_revoked", True)
        if token is not None:
            _LIVE_CAPABILITY_TOKENS.discard(token)
        lock_fd = getattr(self, "_lock_fd", None)
        if isinstance(lock_fd, int) and lock_fd >= 0:
            try:
                fcntl.flock(lock_fd, fcntl.LOCK_UN)
            except OSError:
                pass
            try:
                os.close(lock_fd)
            except OSError:
                pass
            object.__setattr__(self, "_lock_fd", -1)
        object.__setattr__(self, "_frozen", True)


def _seal_qualified_generation(**fields: Any) -> QualifiedStrictGeneration:
    """Internal factory — the only way to mint a live public capability."""

    self = object.__new__(QualifiedStrictGeneration)
    object.__setattr__(self, "_frozen", False)
    token = object()
    for key, value in fields.items():
        object.__setattr__(self, key, value)
    object.__setattr__(self, "_revoked", False)
    object.__setattr__(self, "_seal", _CAPABILITY_SEAL)
    object.__setattr__(self, "_token", token)
    object.__setattr__(self, "_frozen", True)
    _LIVE_CAPABILITY_TOKENS.add(token)
    return self


def _require_live_capability(generation: Any) -> QualifiedStrictGeneration:
    if not isinstance(generation, QualifiedStrictGeneration):
        raise StrictProjectionError("forged_capability")
    if getattr(generation, "_seal", None) is not _CAPABILITY_SEAL:
        raise StrictProjectionError("forged_capability")
    token = getattr(generation, "_token", None)
    if token is None or token not in _LIVE_CAPABILITY_TOKENS or generation.is_revoked:
        raise StrictProjectionError("revoked_capability")
    return generation


@dataclass(frozen=True, slots=True)
class StrictConfig:
    projection_root: Path
    max_projection_rows: int
    max_projection_bytes: int


def _public_owner_ok(st: os.stat_result) -> bool:
    return st.st_uid in {0, os.geteuid()}


def _require_trusted_parent_dir(path: Path) -> None:
    parent = path.parent
    if parent.is_symlink():
        raise StrictProjectionError(f"parent_symlink:{path}")
    if not parent.is_dir():
        raise StrictProjectionError(f"parent_not_directory:{path}")
    pst = parent.lstat()
    if not stat.S_ISDIR(pst.st_mode):
        raise StrictProjectionError(f"parent_not_directory:{path}")
    # Parent must not be writable by untrusted OS users (other-write).
    if pst.st_mode & 0o002:
        raise StrictProjectionError(f"parent_world_writable:{path}")


def _content_digest(data: bytes) -> str:
    return f"sha256:{hashlib.sha256(data).hexdigest()}"


def _read_exact_bounded(fd: int, expected_size: int, *, label: str) -> bytes:
    """Exact full read of ``expected_size`` bytes; detect short-read and size drift."""

    if expected_size < 0:
        raise StrictProjectionError(f"negative_size:{label}")
    chunks: list[bytes] = []
    remaining = expected_size
    while remaining > 0:
        chunk = os.read(fd, remaining)
        if not chunk:
            raise StrictProjectionError(f"short_read:{label}")
        chunks.append(chunk)
        remaining -= len(chunk)
    extra = os.read(fd, 1)
    if extra:
        raise StrictProjectionError(f"size_drift:{label}")
    return b"".join(chunks)


def pin_operator_immutable_path(path: Path) -> OperatorPin:
    """Validate absolute/parent/owner/mode/nofollow; return (dev, ino, mode, digest).

    Architecture §6.1/§6.2: scope/registry/config are regular, non-symlink,
    operator/root-owned, with no owner/group/other write bit; parent is not
    writable by untrusted OS users. Opens with O_NOFOLLOW. Does not mutate
    ``bound_read_scope`` loaders — callers wrap those loaders after pinning.
    Binds exact content digest as well as identity/mode.
    """

    if not path.is_absolute():
        raise StrictProjectionError("path_must_be_absolute")
    if path.is_symlink() or not path.is_file():
        raise StrictProjectionError(f"path_not_regular:{path}")
    _require_trusted_parent_dir(path)
    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        fd = os.open(path, flags)
    except OSError as exc:
        raise StrictProjectionError(f"open_failed:{path}") from exc
    try:
        st = os.fstat(fd)
        if not stat.S_ISREG(st.st_mode):
            raise StrictProjectionError(f"not_regular:{path}")
        mode = st.st_mode & 0o7777
        if mode & 0o222:
            raise StrictProjectionError(f"file_writable:{path}")
        if not _public_owner_ok(st):
            raise StrictProjectionError(f"file_owner:{path}")
        data = _read_exact_bounded(fd, st.st_size, label=str(path))
        return (st.st_dev, st.st_ino, mode, _content_digest(data))
    finally:
        os.close(fd)


def recheck_operator_immutable_path(path: Path, expected: OperatorPin) -> None:
    """Recheck pinned operator path identity/mode/content via O_NOFOLLOW reread."""

    if path.is_symlink():
        raise StrictProjectionError(f"symlink_forbidden:{path}")
    if not path.is_file():
        raise StrictProjectionError(f"operator_path_missing:{path}")
    _require_trusted_parent_dir(path)
    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        fd = os.open(path, flags)
    except OSError as exc:
        raise StrictProjectionError(f"open_failed:{path}") from exc
    try:
        st = os.fstat(fd)
        if not stat.S_ISREG(st.st_mode):
            raise StrictProjectionError(f"not_regular:{path}")
        mode = st.st_mode & 0o7777
        got_id = (st.st_dev, st.st_ino, mode)
        if got_id != expected[:3]:
            raise StrictProjectionError(f"operator_identity_changed:{path}")
        if mode & 0o222:
            raise StrictProjectionError(f"file_writable:{path}")
        if not _public_owner_ok(st):
            raise StrictProjectionError(f"file_owner:{path}")
        data = _read_exact_bounded(fd, st.st_size, label=str(path))
        if _content_digest(data) != expected[3]:
            raise StrictProjectionError(f"operator_content_changed:{path}")
    finally:
        os.close(fd)


def load_bound_read_scope_for_strict(path: str | Path) -> BoundReadScope:
    """Pin/validate path, then call unchanged M3 ``load_bound_read_scope``."""

    p = Path(path)
    pin = pin_operator_immutable_path(p)
    scope = load_bound_read_scope(p)
    recheck_operator_immutable_path(p, pin)
    return scope


def load_project_binding_registry_for_strict(
    path: str | Path,
) -> ProjectBindingRegistry:
    """Pin/validate path, then call unchanged M3 registry loader."""

    p = Path(path)
    pin = pin_operator_immutable_path(p)
    registry = load_project_binding_registry(p)
    recheck_operator_immutable_path(p, pin)
    return registry


def _open_operator_immutable_json(path: Path) -> dict[str, Any]:
    """Absolute, non-symlink, non-writable operator file (scope/registry/config)."""

    pin = pin_operator_immutable_path(path)
    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        fd = os.open(path, flags)
    except OSError as exc:
        raise StrictProjectionError(f"open_failed:{path}") from exc
    try:
        st = os.fstat(fd)
        got = (st.st_dev, st.st_ino, st.st_mode & 0o7777)
        if got != pin[:3]:
            raise StrictProjectionError(f"operator_identity_changed:{path}")
        raw = _read_exact_bounded(fd, st.st_size, label=str(path))
        if _content_digest(raw) != pin[3]:
            raise StrictProjectionError(f"operator_content_changed:{path}")
    finally:
        os.close(fd)
    recheck_operator_immutable_path(path, pin)
    try:
        obj = json.loads(raw.decode("utf-8"), object_pairs_hook=_reject_duplicate_keys)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise StrictProjectionError(f"json_invalid:{path}") from exc
    if not isinstance(obj, dict):
        raise StrictProjectionError(f"json_object_required:{path}")
    return obj


def collect_operator_path_pins(
    *paths: str | Path,
) -> MappingProxyType[str, OperatorPin]:
    """Pin every operator authority path; used at server/CLI startup."""

    pinned: dict[str, OperatorPin] = {}
    for raw in paths:
        path = Path(raw)
        pinned[str(path)] = pin_operator_immutable_path(path)
    return MappingProxyType(pinned)


def _require_public_dir(path: Path) -> tuple[int, int]:
    """Public mount dirs: no symlink, exact mode 0555, operator/root-owned."""

    if path.is_symlink():
        raise StrictProjectionError(f"symlink_forbidden:{path}")
    if not path.is_dir():
        raise StrictProjectionError(f"not_directory:{path}")
    st = path.lstat()
    if not stat.S_ISDIR(st.st_mode):
        raise StrictProjectionError(f"not_directory:{path}")
    if not _public_owner_ok(st):
        raise StrictProjectionError(f"dir_owner:{path}")
    mode = st.st_mode & 0o7777
    if mode != _PUBLIC_DIR_MODE:
        raise StrictProjectionError(f"dir_mode:{path}:{mode:04o}")
    return (st.st_dev, st.st_ino)


def _open_public_regular(path: Path) -> tuple[bytes, PublicPin]:
    """O_RDONLY|O_NOFOLLOW public evidence file; exact mode 0444; identity+content pin."""

    rel = path.name
    if rel in _PRIVATE_BASENAMES_FORBIDDEN:
        raise StrictProjectionError(f"private_file_forbidden:{rel}")
    if path.is_symlink():
        raise StrictProjectionError(f"symlink_forbidden:{path}")
    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        fd = os.open(path, flags)
    except OSError as exc:
        raise StrictProjectionError(f"open_failed:{path}") from exc
    try:
        st = os.fstat(fd)
        if not stat.S_ISREG(st.st_mode):
            raise StrictProjectionError(f"not_regular:{path}")
        mode = st.st_mode & 0o7777
        if mode != _PUBLIC_FILE_MODE:
            raise StrictProjectionError(f"file_mode:{path}:{mode:04o}")
        if not _public_owner_ok(st):
            raise StrictProjectionError(f"file_owner:{path}")
        data = _read_exact_bounded(fd, st.st_size, label=str(path))
        st2 = os.fstat(fd)
        if (st2.st_dev, st2.st_ino, st2.st_mode & 0o7777) != (
            st.st_dev,
            st.st_ino,
            mode,
        ):
            raise StrictProjectionError(f"inode_drift:{path}")
        pinned: PublicPin = (st.st_dev, st.st_ino, mode, _content_digest(data))
        return data, pinned
    finally:
        os.close(fd)


def _open_regular_readonly(path: Path) -> bytes:
    """Read a public regular file without following links; no writes."""

    data, _pinned = _open_public_regular(path)
    return data


def _read_json_public(path: Path) -> dict[str, Any]:
    raw = _open_regular_readonly(path)
    try:
        obj = json.loads(raw.decode("utf-8"), object_pairs_hook=_reject_duplicate_keys)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise StrictProjectionError(f"json_invalid:{path}") from exc
    if not isinstance(obj, dict):
        raise StrictProjectionError(f"json_object_required:{path}")
    return obj


def _read_jsonl_public(path: Path) -> list[dict[str, Any]]:
    raw = _open_regular_readonly(path)
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise StrictProjectionError(f"jsonl_invalid:{path}") from exc
    rows: list[dict[str, Any]] = []
    for line_no, line in enumerate(text.splitlines(), start=1):
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


def _assert_not_private_relative(root: Path, candidate: Path) -> None:
    try:
        rel = candidate.resolve().relative_to(root.resolve()).as_posix()
    except ValueError as exc:
        raise StrictProjectionError("path_escape") from exc
    if rel in _PRIVATE_RELATIVE_FORBIDDEN:
        raise StrictProjectionError(f"private_file_forbidden:{rel}")
    base = Path(rel).name
    if base in _PRIVATE_BASENAMES_FORBIDDEN:
        raise StrictProjectionError(f"private_file_forbidden:{rel}")


def _acquire_shared_lineage_lock(path: Path) -> tuple[int, tuple[int, int]]:
    """Hold shared flock on an already-created lineage lock; never create.

    Parent public lock policy: regular file, O_NOFOLLOW, exact mode 0444,
    operator/root-owned. Does not create or mutate the lock file.
    """

    if path.is_symlink():
        raise StrictProjectionError(f"lock_symlink:{path}")
    if not path.is_file():
        raise StrictProjectionError(f"lock_missing:{path}")
    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        fd = os.open(path, flags)
    except OSError as exc:
        raise StrictProjectionError(f"lock_open_failed:{path}") from exc
    try:
        st = os.fstat(fd)
        if not stat.S_ISREG(st.st_mode):
            raise StrictProjectionError(f"lock_not_regular:{path}")
        mode = st.st_mode & 0o7777
        if mode != _PUBLIC_FILE_MODE:
            raise StrictProjectionError(f"lock_mode:{path}:{mode:04o}")
        if not _public_owner_ok(st):
            raise StrictProjectionError(f"lock_owner:{path}")
        fcntl.flock(fd, fcntl.LOCK_SH)
        return fd, (st.st_dev, st.st_ino)
    except Exception:
        try:
            os.close(fd)
        except OSError:
            pass
        raise


def _recheck_pinned_public(
    pinned: Mapping[str, PublicPin],
) -> None:
    """Recheck every pinned public file identity/mode/content via O_NOFOLLOW."""

    for path_s, expected in pinned.items():
        path = Path(path_s)
        if path.is_symlink():
            raise StrictProjectionError(f"symlink_forbidden:{path}")
        if not path.is_file():
            raise StrictProjectionError(f"public_missing:{path}")
        flags = os.O_RDONLY
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        try:
            fd = os.open(path, flags)
        except OSError as exc:
            raise StrictProjectionError(f"open_failed:{path}") from exc
        try:
            st = os.fstat(fd)
            if not stat.S_ISREG(st.st_mode):
                raise StrictProjectionError(f"not_regular:{path}")
            mode = st.st_mode & 0o7777
            if (st.st_dev, st.st_ino, mode) != expected[:3]:
                raise StrictProjectionError(f"public_identity_changed:{path}")
            if mode != _PUBLIC_FILE_MODE:
                raise StrictProjectionError(f"file_mode:{path}:{mode:04o}")
            data = _read_exact_bounded(fd, st.st_size, label=str(path))
            if _content_digest(data) != expected[3]:
                raise StrictProjectionError(f"public_content_changed:{path}")
        finally:
            os.close(fd)


def _validate_public_projection_row(row: Mapping[str, Any]) -> None:
    """Full closed public row schema including nested enums/types."""

    _require_closed(
        row,
        _PROJECTION_ROW_FIELDS,
        schema="convmem.bound-projection-row.v2",
        label="projection_row",
    )
    if row["record_kind"] not in _RECORD_KINDS:
        raise StrictProjectionError("projection_row_record_kind")
    if not isinstance(row["confidence_bps"], int) or isinstance(row["confidence_bps"], bool):
        raise StrictProjectionError("projection_row_confidence")
    if not 0 <= row["confidence_bps"] <= 10000:
        raise StrictProjectionError("projection_row_confidence_range")
    for ts_key in ("observed_at", "recorded_at"):
        if not isinstance(row[ts_key], str) or not re.fullmatch(
            r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z", row[ts_key]
        ):
            raise StrictProjectionError(f"projection_row_{ts_key}")
    pq = row["provenance_qualification"]
    if not isinstance(pq, Mapping) or set(pq) != _PROVENANCE_QUAL_FIELDS:
        raise StrictProjectionError("projection_row_provenance_qualification")
    if pq["commitments"] not in {"valid", "incomplete"}:
        raise StrictProjectionError("projection_row_commitments")
    if pq["byte_grounding"] not in {"complete", "missing"}:
        raise StrictProjectionError("projection_row_byte_grounding")
    if pq["capture"] not in _CAPTURE_VALUES:
        raise StrictProjectionError("projection_row_capture")
    if pq["transformer_cap"] not in {"trusted", "agent", "untrusted"}:
        raise StrictProjectionError("projection_row_transformer_cap")
    handle = row["public_ledger_id"]
    if not looks_like_public_ledger_handle(handle):
        raise StrictProjectionError("projection_row_public_ledger_id")
    try:
        pref, stored = parse_public_ledger_handle(handle)
    except StrictEvidenceError as exc:
        raise StrictProjectionError("projection_row_public_ledger_id") from exc
    if pref != row["public_binding_ref"] or stored != row["assertion_id"]:
        raise StrictProjectionError("projection_row_handle_mismatch")
    if row["record_kind"] == "verification":
        if row["verification_result"] not in {"pass", "fail", "inconclusive"}:
            raise StrictProjectionError("projection_row_verification_result")
        if not isinstance(row["target_assertion_id"], str) or not row["target_assertion_id"]:
            raise StrictProjectionError("projection_row_target_required")
    else:
        if row["verification_result"] is not None:
            raise StrictProjectionError("projection_row_verification_null")
    supersedes = row["supersedes_assertion_ids"]
    if not isinstance(supersedes, list):
        raise StrictProjectionError("projection_row_supersedes")
    if any(not isinstance(x, str) or not x for x in supersedes):
        raise StrictProjectionError("projection_row_supersedes_items")
    if len(supersedes) != len(set(supersedes)):
        raise StrictProjectionError("projection_row_supersedes_dup")


def _validate_public_graph(
    graph: Mapping[str, Any],
    *,
    rows: Sequence[Mapping[str, Any]],
) -> None:
    """Closed graph schema, unique identities, edge kinds, row agreement."""

    _require_closed(graph, _GRAPH_FIELDS, schema="convmem.strict-graph.v1", label="graph")
    nodes = graph["nodes"]
    edges = graph["edges"]
    if not isinstance(nodes, list) or not isinstance(edges, list):
        raise StrictProjectionError("graph_collections")
    if any(not isinstance(n, str) or not n for n in nodes):
        raise StrictProjectionError("graph_node_type")
    if len(nodes) != len(set(nodes)):
        raise StrictProjectionError("graph_node_dup")
    row_ids = [r["assertion_id"] for r in rows]
    if len(row_ids) != len(set(row_ids)):
        raise StrictProjectionError("projection_row_assertion_dup")
    if set(nodes) != set(row_ids):
        raise StrictProjectionError("graph_row_agreement")
    seen_edges: set[tuple[str, str, str]] = set()
    for edge in edges:
        if not isinstance(edge, Mapping):
            raise StrictProjectionError("graph_edge_type")
        if set(edge) != _GRAPH_EDGE_FIELDS:
            raise StrictProjectionError("graph_edge_keys")
        kind = edge["kind"]
        src = edge["from_assertion_id"]
        dst = edge["to_assertion_id"]
        if kind not in _GRAPH_EDGE_KINDS:
            raise StrictProjectionError("graph_edge_kind")
        if not isinstance(src, str) or not isinstance(dst, str) or not src or not dst:
            raise StrictProjectionError("graph_edge_endpoints")
        if src not in nodes or dst not in nodes:
            raise StrictProjectionError("graph_edge_unknown_node")
        key = (kind, src, dst)
        if key in seen_edges:
            raise StrictProjectionError("graph_edge_dup")
        seen_edges.add(key)
    # Required parent edges: non-null relates_to_assertion_id must appear.
    by_id = {r["assertion_id"]: r for r in rows}
    for row in rows:
        parent = row.get("relates_to_assertion_id")
        if parent is None:
            continue
        if not isinstance(parent, str) or not parent:
            raise StrictProjectionError("graph_relates_parent_type")
        if parent not in by_id:
            raise StrictProjectionError("graph_relates_parent_missing")
        expected = ("relates_to", row["assertion_id"], parent)
        if expected not in seen_edges:
            raise StrictProjectionError("graph_relates_edge_missing")


def load_strict_config(path: str | Path) -> StrictConfig:
    """Independent strict-config.v2 parser (no legacy config loader)."""

    cfg_path = Path(path)
    obj = _open_operator_immutable_json(cfg_path)
    _require_closed(
        obj,
        _STRICT_CONFIG_FIELDS,
        schema="convmem.strict-config.v2",
        label="strict_config",
    )
    if obj["max_projection_rows"] != 10000:
        raise StrictProjectionError("strict_config_max_rows")
    if obj["max_projection_bytes"] != 67108864:
        raise StrictProjectionError("strict_config_max_bytes")
    if obj["telemetry"] is not False:
        raise StrictProjectionError("strict_config_telemetry")
    root = obj["projection_root"]
    if not isinstance(root, str) or not root.startswith("/"):
        raise StrictProjectionError("strict_config_projection_root")
    return StrictConfig(
        projection_root=Path(root),
        max_projection_rows=10000,
        max_projection_bytes=67108864,
    )


def _parse_ts(value: str) -> datetime:
    if not isinstance(value, str) or not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z", value):
        raise StrictProjectionError("timestamp_invalid")
    return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)


def boottime_ns() -> int:
    """Monkeypatchable CLOCK_BOOTTIME sample (CLI 10s bound / freshness)."""

    return time.clock_gettime_ns(time.CLOCK_BOOTTIME)


def wall_time_utc() -> datetime:
    """Monkeypatchable wall clock for active-serving / freshness checks."""

    return datetime.now(timezone.utc)


def _opub_open_published_generation_p0(work: SimpleNamespace) -> None:
    if work.operator_path_pins:
        for path_s, expected in work.operator_path_pins.items():
            recheck_operator_immutable_path(Path(path_s), expected)


def _opub_open_published_generation_p1(work: SimpleNamespace) -> None:
    work.root_path = Path(work.root)
    if work.root_path.is_symlink() or not work.root_path.is_dir():
        raise StrictProjectionError("root_invalid")


def _opub_open_published_generation_p2(work: SimpleNamespace) -> None:
    _require_public_dir(work.root_path)
    try:
        work.binding_id = work.scope.allowed_project_bindings[0]
        work.recomputed_owner = owner_digest(
            scope_sha256=work.scope.scope_sha256,
            registry_sha256=work.registry.registry_sha256,
            project_binding_id=work.binding_id,
        )
        work.binding = work.registry.binding(work.binding_id)
    except (BoundScopeError, IndexError, KeyError) as exc:
        raise StrictProjectionError("scope_registry") from exc


def _opub_open_published_generation_p3(work: SimpleNamespace) -> None:
    work.lineage_id = work.binding.lineage_id
    if not isinstance(work.lineage_id, str) or len(work.lineage_id) != 32:
        raise StrictProjectionError("binding_lineage_id")


def _opub_open_published_generation_p4(work: SimpleNamespace) -> None:
    work.locks_dir = work.root_path / "locks"


def _opub_open_published_generation_p5(work: SimpleNamespace) -> None:
    _require_public_dir(work.locks_dir)
    work.lock_path = work.locks_dir / f"{work.lineage_id}.lock"


def _opub_open_published_generation_p6(work: SimpleNamespace) -> None:
    work.owns_lock = False
    if work.held_lock is not None:
        work.lock_fd, work.lock_inode = work.held_lock
        if not isinstance(work.lock_fd, int) or work.lock_fd < 0:
            raise StrictProjectionError("lock_released")
        work.held_st = os.fstat(work.lock_fd)
        if (work.held_st.st_dev, work.held_st.st_ino) != work.lock_inode:
            raise StrictProjectionError("lock_inode_drift")
        if work.lock_path.is_symlink() or not work.lock_path.is_file():
            raise StrictProjectionError(f"lock_missing:{work.lock_path}")
        work.path_st = work.lock_path.lstat()
        if (work.path_st.st_dev, work.path_st.st_ino) != work.lock_inode:
            raise StrictProjectionError("lock_path_mismatch")
        if work.path_st.st_mode & 4095 != _PUBLIC_FILE_MODE:
            raise StrictProjectionError(f"lock_mode:{work.lock_path}")
    else:
        work.lock_fd, work.lock_inode = _acquire_shared_lineage_lock(work.lock_path)
        work.owns_lock = True


def _x_open_published_generation_p7_0(work: SimpleNamespace) -> None:
    work.pinned_public: dict[str, PublicPin] = {}


def _x_open_published_generation_p7_1_c0(work: SimpleNamespace) -> None:
    work.active_dir = work.root_path / "active"
    _require_public_dir(work.active_dir)
    work.publication_path = work.active_dir / f"{work.lineage_id}.json"
    _assert_not_private_relative(work.root_path, work.publication_path)
    work.publication_raw, work.pub_pin = _open_public_regular(work.publication_path)
    work.pinned_public[str(work.publication_path)] = work.pub_pin
    try:
        work.publication = json.loads(work.publication_raw.decode("utf-8"), object_pairs_hook=_reject_duplicate_keys)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise StrictProjectionError(f"json_invalid:{work.publication_path}") from exc
    if not isinstance(work.publication, dict):
        raise StrictProjectionError(f"json_object_required:{work.publication_path}")
    _require_closed(work.publication, _PUBLICATION_FIELDS, schema="convmem.strict-publication.v2", label="publication")
    if work.publication["lineage_id"] != work.lineage_id:
        raise StrictProjectionError("publication_lineage")
    work.pub_hash = _require_self_hash(work.publication, "publication_payload_sha256", label="publication")
    if work.expected_publication_sha256 is not None and work.pub_hash != work.expected_publication_sha256:
        raise StrictProjectionError("publication_cas_mismatch")
    if work.publication["owner_digest"] != work.recomputed_owner:
        raise StrictProjectionError("publication_owner_digest")
    if work.publication["mode"] != "serving":
        raise StrictProjectionError("publication_not_serving")
    work.serving_generation_id = work.publication["serving_generation_id"]
    work.projection_manifest_sha256 = work.publication["projection_manifest_sha256"]
    work.authority_seq = work.publication["authority_seq"]
    work.snapshot_id = work.publication["authority_snapshot_id"]


def _x_open_published_generation_p7_1_c1(work: SimpleNamespace) -> None:
    work.authority_manifest_sha256 = work.publication["authority_manifest_sha256"]
    work.semantic_contract_sha256 = work.publication["semantic_contract_sha256"]
    if not isinstance(work.serving_generation_id, str) or not work.serving_generation_id:
        raise StrictProjectionError("serving_generation_required")
    if not isinstance(work.projection_manifest_sha256, str):
        raise StrictProjectionError("projection_manifest_required")
    if not isinstance(work.snapshot_id, str) or not isinstance(work.authority_manifest_sha256, str):
        raise StrictProjectionError("authority_identity_required")
    work.anchor = work.publication["freshness_anchor"]
    if not isinstance(work.anchor, Mapping):
        raise StrictProjectionError("freshness_anchor")
    if set(work.anchor) != _FRESHNESS_ANCHOR_FIELDS:
        raise StrictProjectionError("freshness_anchor_keys")
    if work.anchor["authority_snapshot_id"] != work.snapshot_id:
        raise StrictProjectionError("freshness_anchor_snapshot")
    work.deadline = work.anchor["snapshot_deadline_boottime_ns"]
    if not isinstance(work.deadline, int) or isinstance(work.deadline, bool):
        raise StrictProjectionError("freshness_anchor_deadline")
    if boottime_ns() >= work.deadline:
        raise StrictProjectionError("snapshot_expired")
    work.auth_dir = work.root_path / "authority" / work.snapshot_id
    _require_public_dir(work.root_path / "authority")
    _require_public_dir(work.auth_dir)
    work.auth_manifest_path = work.auth_dir / "manifest.json"
    _assert_not_private_relative(work.root_path, work.auth_manifest_path)
    work.auth_raw, work.auth_pin = _open_public_regular(work.auth_manifest_path)
    work.pinned_public[str(work.auth_manifest_path)] = work.auth_pin


def _x_open_published_generation_p7_1_c2(work: SimpleNamespace) -> None:
    try:
        work.auth_manifest = json.loads(work.auth_raw.decode("utf-8"), object_pairs_hook=_reject_duplicate_keys)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise StrictProjectionError(f"json_invalid:{work.auth_manifest_path}") from exc
    if not isinstance(work.auth_manifest, dict):
        raise StrictProjectionError(f"json_object_required:{work.auth_manifest_path}")
    _require_closed(
        work.auth_manifest,
        _AUTHORITY_MANIFEST_FIELDS,
        schema="convmem.bound-authority-manifest.v3",
        label="authority_manifest",
    )
    if work.auth_manifest["lineage_id"] != work.lineage_id:
        raise StrictProjectionError("authority_manifest_lineage")
    if work.auth_manifest["owner_digest"] != work.recomputed_owner:
        raise StrictProjectionError("authority_manifest_owner")
    if work.auth_manifest["authority_seq"] != work.authority_seq:
        raise StrictProjectionError("authority_manifest_seq")
    if work.auth_manifest["snapshot_id"] != work.snapshot_id:
        raise StrictProjectionError("authority_manifest_snapshot")
    if work.auth_manifest["scope_sha256"] != work.scope.scope_sha256:
        raise StrictProjectionError("authority_manifest_scope_link")
    if work.auth_manifest["registry_sha256"] != work.registry.registry_sha256:
        raise StrictProjectionError("authority_manifest_registry_link")
    if work.auth_manifest["semantic_contract_sha256"] != work.semantic_contract_sha256:
        raise StrictProjectionError("authority_manifest_semantic_contract_link")
    work.recomputed_auth_payload = _labeled_self_hash(work.auth_manifest, "manifest_payload_sha256")
    if work.auth_manifest["manifest_payload_sha256"] != work.recomputed_auth_payload:
        raise StrictProjectionError("authority_manifest_hash")
    if work.authority_manifest_sha256 != work.recomputed_auth_payload:
        raise StrictProjectionError("authority_manifest_link")
    work.recomputed_snapshot_id = _authority_snapshot_id(work.auth_manifest)
    if work.auth_manifest["snapshot_id"] != work.recomputed_snapshot_id:
        raise StrictProjectionError("authority_snapshot_id_mismatch")
    work.as_of = work.auth_manifest["as_of"]
    work.expires_at = work.auth_manifest["expires_at"]
    work.wall = work.now if work.now is not None else wall_time_utc()
    if work.wall >= _parse_ts(work.expires_at):
        raise StrictProjectionError("snapshot_expired")


def _x_open_published_generation_p7_1_c3(work: SimpleNamespace) -> None:
    work.gen_dir = work.root_path / "projection" / work.serving_generation_id
    _require_public_dir(work.root_path / "projection")
    _require_public_dir(work.gen_dir)
    work.proj_manifest_path = work.gen_dir / "manifest.json"
    work.proj_raw, work.proj_pin = _open_public_regular(work.proj_manifest_path)
    work.pinned_public[str(work.proj_manifest_path)] = work.proj_pin
    try:
        work.proj_manifest = json.loads(work.proj_raw.decode("utf-8"), object_pairs_hook=_reject_duplicate_keys)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise StrictProjectionError(f"json_invalid:{work.proj_manifest_path}") from exc
    if not isinstance(work.proj_manifest, dict):
        raise StrictProjectionError(f"json_object_required:{work.proj_manifest_path}")
    _require_closed(
        work.proj_manifest,
        _PROJECTION_MANIFEST_FIELDS,
        schema="convmem.bound-projection-manifest.v3",
        label="projection_manifest",
    )
    if work.proj_manifest["lineage_id"] != work.lineage_id:
        raise StrictProjectionError("projection_manifest_lineage")
    if work.proj_manifest["authority_seq"] != work.authority_seq:
        raise StrictProjectionError("projection_manifest_seq")
    if work.proj_manifest["owner_digest"] != work.recomputed_owner:
        raise StrictProjectionError("projection_manifest_owner")
    if work.proj_manifest["snapshot_id"] != work.snapshot_id:
        raise StrictProjectionError("projection_snapshot_link")
    if work.proj_manifest["authority_manifest_sha256"] != work.authority_manifest_sha256:
        raise StrictProjectionError("projection_authority_manifest_link")
    if work.proj_manifest["semantic_contract_sha256"] != work.semantic_contract_sha256:
        raise StrictProjectionError("projection_semantic_contract_link")
    if work.proj_manifest["scope_sha256"] != work.scope.scope_sha256:
        raise StrictProjectionError("projection_scope_link")
    if work.proj_manifest["registry_sha256"] != work.registry.registry_sha256:
        raise StrictProjectionError("projection_registry_link")
    if work.proj_manifest["as_of"] != work.as_of or work.proj_manifest["expires_at"] != work.expires_at:
        raise StrictProjectionError("projection_freshness_link")


def _x_open_published_generation_p7_1_c4(work: SimpleNamespace) -> None:
    work.recomputed_generation_id = _projection_generation_id(work.proj_manifest)
    if work.proj_manifest["generation_id"] != work.recomputed_generation_id:
        raise StrictProjectionError("projection_generation_id_mismatch")
    if work.serving_generation_id != work.recomputed_generation_id:
        raise StrictProjectionError("publication_generation_id_link")
    work.recomputed_proj_payload = _labeled_self_hash(work.proj_manifest, "manifest_payload_sha256")
    if work.proj_manifest["manifest_payload_sha256"] != work.recomputed_proj_payload:
        raise StrictProjectionError("projection_manifest_hash")
    if work.projection_manifest_sha256 != work.recomputed_proj_payload:
        raise StrictProjectionError("projection_manifest_link")
    work.rows_path = work.gen_dir / "rows.jsonl"
    work.rows_raw, work.rows_pin = _open_public_regular(work.rows_path)
    work.pinned_public[str(work.rows_path)] = work.rows_pin
    try:
        work.text = work.rows_raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise StrictProjectionError(f"jsonl_invalid:{work.rows_path}") from exc
    work.stored_rows: list[dict[str, Any]] = []
    for line_no, line in enumerate(work.text.splitlines(), start=1):
        if not line:
            raise StrictProjectionError(f"jsonl_empty_line:{work.rows_path}:{line_no}")
        try:
            work.obj = json.loads(line, object_pairs_hook=_reject_duplicate_keys)
        except json.JSONDecodeError as exc:
            raise StrictProjectionError(f"jsonl_invalid:{work.rows_path}:{line_no}") from exc
        if not isinstance(work.obj, dict):
            raise StrictProjectionError(f"jsonl_object_required:{work.rows_path}:{line_no}")
        work.stored_rows.append(work.obj)
    if len(work.stored_rows) > 10000:
        raise StrictProjectionError("projection_row_cap")
    work.row_bytes = _canonical_jsonl_bytes(work.stored_rows)
    if len(work.row_bytes) > 67108864:
        raise StrictProjectionError("projection_byte_cap")
    for row in work.stored_rows:
        _validate_public_projection_row(row)
    work.graph_path = work.gen_dir / "graph.json"
    work.graph_raw, work.graph_pin = _open_public_regular(work.graph_path)
    work.pinned_public[str(work.graph_path)] = work.graph_pin


def _x_open_published_generation_p7_1_c5(work: SimpleNamespace) -> QualifiedStrictGeneration:
    try:
        work.stored_graph = json.loads(work.graph_raw.decode("utf-8"), object_pairs_hook=_reject_duplicate_keys)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise StrictProjectionError(f"json_invalid:{work.graph_path}") from exc
    if not isinstance(work.stored_graph, dict):
        raise StrictProjectionError(f"json_object_required:{work.graph_path}")
    _validate_public_graph(work.stored_graph, rows=work.stored_rows)
    work.rows_digest = sha256_digest(work.row_bytes)
    if work.proj_manifest["rows_sha256"] != work.rows_digest:
        raise StrictProjectionError("rows_hash_mismatch")
    if work.proj_manifest["row_count"] != len(work.stored_rows):
        raise StrictProjectionError("row_count")
    work.graph_digest = _require_self_hash(work.stored_graph, "graph_payload_sha256", label="graph")
    if work.proj_manifest["graph_sha256"] != work.graph_digest:
        raise StrictProjectionError("graph_hash_mismatch")
    if work.proj_manifest["graph_node_count"] != len(work.stored_graph["nodes"]):
        raise StrictProjectionError("graph_node_count")
    work.selectors = EffectiveSelectors(
        project=work.scope.project,
        site=work.scope.site,
        site_mode=work.scope.site_mode,
        domain=work.scope.domain,
        binding_id=work.binding_id,
    )
    for row in work.stored_rows:
        if row["public_binding_ref"] != work.binding.public_ref:
            raise StrictProjectionError("row_public_ref")
        try:
            authorize_row(
                scope=work.scope,
                registry=work.registry,
                selectors=work.selectors,
                project_binding_id=row["project_binding_id"],
                source_registration_id=row["source_registration_id"],
                authority_site=row["authority_site"],
                authority_domain=row["authority_domain"],
            )
        except BoundScopeError as exc:
            raise StrictProjectionError(f"row_authorization:{exc}") from exc
    _recheck_pinned_public(work.pinned_public)
    work.lock_st = os.fstat(work.lock_fd)
    if (work.lock_st.st_dev, work.lock_st.st_ino) != work.lock_inode:
        raise StrictProjectionError("lock_inode_drift")
    _recheck_pinned_public({str(work.publication_path): work.pub_pin})
    work.wall2 = work.now if work.now is not None else wall_time_utc()
    if work.wall2 >= _parse_ts(work.expires_at):
        raise StrictProjectionError("snapshot_expired")
    if boottime_ns() >= work.deadline:
        raise StrictProjectionError("snapshot_expired")
    return _seal_qualified_generation(
        lineage_id=work.lineage_id,
        authority_seq=work.authority_seq,
        snapshot_id=work.snapshot_id,
        authority_manifest_sha256=work.authority_manifest_sha256,
        generation_id=work.serving_generation_id,
        projection_manifest_sha256=work.projection_manifest_sha256,
        rows_sha256=work.rows_digest,
        graph_sha256=work.graph_digest,
        publication_payload_sha256=work.pub_hash,
        semantic_contract_sha256=work.semantic_contract_sha256,
        as_of=work.as_of,
        expires_at=work.expires_at,
        scope=work.scope,
        registry=work.registry,
        rows=tuple(work.stored_rows),
        graph=MappingProxyType(dict(work.stored_graph)),
        _lock_fd=work.lock_fd,
        _lock_inode=work.lock_inode,
        _pinned_public=MappingProxyType(dict(work.pinned_public)),
        _operator_path_pins=MappingProxyType(dict(work.operator_path_pins) if work.operator_path_pins else {}),
        _root=work.root_path,
        _publication_path=work.publication_path,
    )


def _x_open_published_generation_p7_1(work: SimpleNamespace) -> QualifiedStrictGeneration:

    try:
        _x_open_published_generation_p7_1_c0(work)
        _x_open_published_generation_p7_1_c1(work)
        _x_open_published_generation_p7_1_c2(work)
        _x_open_published_generation_p7_1_c3(work)
        _x_open_published_generation_p7_1_c4(work)
        return _x_open_published_generation_p7_1_c5(work)
    except Exception:
        if work.owns_lock:
            try:
                fcntl.flock(work.lock_fd, fcntl.LOCK_UN)
            except OSError:
                pass
            try:
                os.close(work.lock_fd)
            except OSError:
                pass
        raise


def _opub_open_published_generation_p7(work: SimpleNamespace) -> QualifiedStrictGeneration:

    _x_open_published_generation_p7_0(work)
    return _x_open_published_generation_p7_1(work)


def open_published_generation(
    *,
    root: str | Path,
    scope: BoundReadScope,
    registry: ProjectBindingRegistry,
    expected_publication_sha256: str | None = None,
    now: datetime | None = None,
    operator_path_pins: Mapping[str, OperatorPin] | None = None,
    held_lock: tuple[int, tuple[int, int]] | None = None,
) -> QualifiedStrictGeneration:
    """Public-only opening: publication + public authority manifest + projection.

    Architecture §6.5.4: runtime mount inputs are only the public authority
    manifest, public projection files, exact serving publication, unchanged
    scope/registry/config, and precreated read-lock files. Does not read
    layout.json, control/enrollment.json, citation maps, inputs, grounding, or
    any other private file. Holds a shared flock on the lineage lock while the
    capability is live. Reader path is read-only: no cache, mtime, manifest,
    publication, or lock mutation.

    ``held_lock`` — optional already-acquired ``(fd, (dev, ino))`` from
    ``_acquire_shared_lineage_lock``. Direct CLI passes this so the same lock
    spans private qualification + public opening. On success the capability
    owns the fd; on failure a held lock is left for the caller to release.
    """
    work = SimpleNamespace()
    work.expected_publication_sha256 = expected_publication_sha256
    work.held_lock = held_lock
    work.now = now
    work.operator_path_pins = operator_path_pins
    work.registry = registry
    work.root = root
    work.scope = scope

    _opub_open_published_generation_p0(work)
    _opub_open_published_generation_p1(work)
    _opub_open_published_generation_p2(work)
    _opub_open_published_generation_p3(work)
    _opub_open_published_generation_p4(work)
    _opub_open_published_generation_p5(work)
    _opub_open_published_generation_p6(work)
    return _opub_open_published_generation_p7(work)


# Capability-probe alias used by T0a/M3 red markers; same public opening as parent.
open_public_projection = open_published_generation


def revoke_snapshot(generation: QualifiedStrictGeneration) -> None:
    """In-process seal of a public capability. No filesystem mutation."""

    live = _require_live_capability(generation)
    live.mark_revoked()


# pylint: disable=W0212  # live capability recheck reads pinned private reader state
def recheck_live_public_capability(generation: QualifiedStrictGeneration) -> None:
    """Recheck pinned public identities + active serving/freshness while locked."""

    live = _require_live_capability(generation)
    _recheck_pinned_public(live._pinned_public)
    for path_s, expected in live._operator_path_pins.items():
        recheck_operator_immutable_path(Path(path_s), expected)
    lock_fd = live._lock_fd
    if not isinstance(lock_fd, int) or lock_fd < 0:
        raise StrictProjectionError("lock_released")
    st = os.fstat(lock_fd)
    if (st.st_dev, st.st_ino) != live._lock_inode:
        raise StrictProjectionError("lock_inode_drift")
    if wall_time_utc() >= _parse_ts(live.expires_at):
        raise StrictProjectionError("snapshot_expired")
    publication_raw, _ = _open_public_regular(live._publication_path)
    try:
        publication = json.loads(publication_raw.decode("utf-8"), object_pairs_hook=_reject_duplicate_keys)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise StrictProjectionError(f"json_invalid:{live._publication_path}") from exc
    if not isinstance(publication, dict):
        raise StrictProjectionError(f"json_object_required:{live._publication_path}")
    _require_closed(
        publication,
        _PUBLICATION_FIELDS,
        schema="convmem.strict-publication.v2",
        label="publication",
    )
    if publication.get("mode") != "serving":
        raise StrictProjectionError("publication_not_serving")
    recomputed = _require_self_hash(publication, "publication_payload_sha256", label="publication")
    if recomputed != live.publication_payload_sha256:
        raise StrictProjectionError("publication_cas_mismatch")
    anchor = publication.get("freshness_anchor")
    if not isinstance(anchor, Mapping):
        raise StrictProjectionError("freshness_anchor")
    if set(anchor) != _FRESHNESS_ANCHOR_FIELDS:
        raise StrictProjectionError("freshness_anchor_keys")
    deadline = anchor.get("snapshot_deadline_boottime_ns")
    if not isinstance(deadline, int) or isinstance(deadline, bool):
        raise StrictProjectionError("freshness_anchor_deadline")
    if boottime_ns() >= deadline:
        raise StrictProjectionError("snapshot_expired")


def tokenize_lexical(text: str) -> list[str]:
    """NFC + casefold + maximal L/N/_ runs (Architecture §6.5.5)."""

    if not isinstance(text, str):
        raise StrictPublicError("invalid_request")
    normalized = unicodedata.normalize("NFC", text).casefold()
    tokens: list[str] = []
    current: list[str] = []
    for ch in normalized:
        cat = unicodedata.category(ch)
        if cat.startswith("L") or cat.startswith("N") or ch == "_":
            current.append(ch)
        else:
            if current:
                tokens.append("".join(current))
                current = []
    if current:
        tokens.append("".join(current))
    return tokens


def _distinct_first(tokens: Sequence[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for tok in tokens:
        if tok in seen:
            continue
        seen.add(tok)
        out.append(tok)
    return out


def _count_occurrences(haystack: str, needle: str) -> int:
    if not needle:
        return 0
    count = 0
    start = 0
    while True:
        idx = haystack.find(needle, start)
        if idx < 0:
            break
        count += 1
        start = idx + 1
    return count


def _score_row(
    *,
    normalized_query: str,
    query_tokens: Sequence[str],
    title: str,
    document: str,
) -> int:
    title_tokens = tokenize_lexical(title)
    doc_tokens = tokenize_lexical(document)
    normalized_title = " ".join(title_tokens)
    normalized_document = " ".join(doc_tokens)
    score = 0
    if normalized_query and normalized_query in normalized_title:
        score += 16
    if normalized_query and normalized_query in normalized_document:
        score += 4
    for tok in query_tokens:
        score += 8 * min(3, _count_occurrences(normalized_title, tok))
        score += 1 * min(3, _count_occurrences(normalized_document, tok))
    return score


def _truncate_document(document: str) -> tuple[str, bool]:
    if len(document) <= _DOC_CODEPOINT_CAP:
        return document, False
    return document[:_DOC_CODEPOINT_CAP], True


def _new_correlation_id() -> str:
    return secrets.token_hex(16)


def _provenance_basis_from_capture(qualification: Any) -> str:
    """Public provenance_basis is exactly the validated capture class."""

    if not isinstance(qualification, Mapping):
        raise StrictProjectionError("provenance_qualification_type")
    capture = qualification.get("capture")
    if capture not in _CAPTURE_VALUES:
        raise StrictProjectionError("provenance_capture_invalid")
    return str(capture)


def _related_add(work: SimpleNamespace, row: Mapping[str, Any]) -> None:
    if len(work.collected) >= _RELATED_NEIGHBORHOOD_CAP and row["assertion_id"] not in work.collected:
        raise StrictPublicError("scope_denied", correlation_id=work.cid)
    work.collected[row["assertion_id"]] = dict(row)


def _related_row_or_deny(reader: Any, work: SimpleNamespace, assertion_id: str) -> dict[str, Any]:
    rows = reader._rows_by_assertion.get(assertion_id)
    if rows is None or len(rows) != 1:
        raise StrictPublicError("scope_denied", correlation_id=work.cid)
    return rows[0]


def _related_collect_descendants(
    reader: Any, work: SimpleNamespace, root_id: str, depth: int, stack: frozenset[str] = frozenset()
) -> None:
    if depth <= 0:
        return
    if root_id in stack:
        raise StrictPublicError("scope_denied", correlation_id=work.cid)
    next_stack = stack | {root_id}
    for kind, child_id in reader._children.get(root_id, []):
        if kind not in _GRAPH_EDGE_KINDS:
            raise StrictPublicError("scope_denied", correlation_id=work.cid)
        if child_id in next_stack:
            raise StrictPublicError("scope_denied", correlation_id=work.cid)
        child = _related_row_or_deny(reader, work, child_id)
        kind_ok = child.get("record_kind")
        if kind_ok not in _RECORD_KINDS:
            raise StrictPublicError("scope_denied", correlation_id=work.cid)
        if child_id not in work.collected and len(work.collected) >= _RELATED_NEIGHBORHOOD_CAP:
            raise StrictPublicError("scope_denied", correlation_id=work.cid)
        _related_add(work, child)
        _related_collect_descendants(reader, work, child_id, depth - 1, next_stack)


def _related_walk_parents(reader: Any, work: SimpleNamespace) -> None:
    cursor = work.target
    _related_add(work, cursor)
    work.observation_anchor = None
    work.non_expanding_hit = None
    for _ in range(_RELATED_PARENT_HOPS):
        parents = reader._relates_parents.get(cursor["assertion_id"], [])
        if not parents:
            break
        if len(parents) != 1:
            raise StrictPublicError("scope_denied", correlation_id=work.cid)
        parent_id = parents[0]
        if parent_id in work.collected:
            raise StrictPublicError("scope_denied", correlation_id=work.cid)  # cycle
        parent_row = _related_row_or_deny(reader, work, parent_id)
        _related_add(work, parent_row)
        if parent_id in reader._non_expanding:
            work.non_expanding_hit = parent_id
            break
        if parent_row["record_kind"] == "observation":
            for back_id in reader._relates_parents.get(parent_id, []):
                if back_id in work.collected:
                    raise StrictPublicError("scope_denied", correlation_id=work.cid)
            work.observation_anchor = parent_id
            break
        cursor = parent_row
    else:
        if reader._relates_parents.get(cursor["assertion_id"]):
            raise StrictPublicError("scope_denied", correlation_id=work.cid)


def _related_expand_heads(reader: Any, work: SimpleNamespace) -> None:
    logical_id = work.target["logical_id"]
    head_rows = [
        row
        for row in reader._generation.rows
        if row["logical_id"] == logical_id and row["authority_state"] in {"current", "conflict", "approved"}
    ]
    for head in head_rows:
        _related_add(work, head)
        if head["record_kind"] not in {"observation", "decision"}:
            continue
        for kind, child_id in reader._children.get(head["assertion_id"], []):
            if kind != "targets":
                continue
            child = _related_row_or_deny(reader, work, child_id)
            if child["record_kind"] == "verification":
                _related_add(work, child)


class StrictProjectionReader:
    """Shared lexical reader over one sealed public generation."""

    def __init__(self, generation: QualifiedStrictGeneration) -> None:
        self._generation = _require_live_capability(generation)
        # Binding-scoped multimap: assertion_id → all matching rows (never LWW).
        multimap: dict[str, list[dict[str, Any]]] = {}
        for row in generation.rows:
            multimap.setdefault(row["assertion_id"], []).append(dict(row))
        self._rows_by_assertion = multimap
        # Edge convention from builder: from=child/dependent, to=parent/target.
        self._children: dict[str, list[tuple[str, str]]] = {}
        self._relates_parents: dict[str, list[str]] = {}
        for edge in generation.graph.get("edges", []):
            if not isinstance(edge, Mapping):
                raise StrictProjectionError("graph_edge_type")
            if set(edge) != _GRAPH_EDGE_FIELDS:
                raise StrictProjectionError("graph_edge_keys")
            kind = edge.get("kind")
            src = edge.get("from_assertion_id")
            dst = edge.get("to_assertion_id")
            if kind not in _GRAPH_EDGE_KINDS:
                raise StrictProjectionError("graph_edge_kind")
            if not isinstance(src, str) or not isinstance(dst, str):
                raise StrictProjectionError("graph_edge_endpoints")
            self._children.setdefault(dst, []).append((kind, src))
            if kind == "relates_to":
                self._relates_parents.setdefault(src, []).append(dst)
        self._non_expanding = frozenset(
            generation.registry.binding(generation.scope.allowed_project_bindings[0]).non_expanding_roots
        )

    def _ensure_active(self, correlation_id: str) -> None:
        try:
            _require_live_capability(self._generation)
            recheck_live_public_capability(self._generation)
        except StrictProjectionError as exc:
            raise StrictPublicError("snapshot_stale", correlation_id=correlation_id) from exc
        if self._generation.is_revoked:
            raise StrictPublicError("snapshot_stale", correlation_id=correlation_id)
        if wall_time_utc() >= _parse_ts(self._generation.expires_at):
            raise StrictPublicError("snapshot_stale", correlation_id=correlation_id)

    def _resolve_selectors(
        self,
        *,
        correlation_id: str,
        project: Any = OMITTED,
        site: Any = OMITTED,
        domain: Any = OMITTED,
        cross_domain: Any = OMITTED,
    ) -> EffectiveSelectors:
        try:
            return resolve_selectors(
                self._generation.scope,
                project=project,
                site=site,
                domain=domain,
                cross_domain=cross_domain,
            )
        except BoundScopeError as exc:
            raise StrictPublicError("scope_denied", correlation_id=correlation_id) from exc

    def _authorize(
        self,
        row: Mapping[str, Any],
        selectors: EffectiveSelectors,
        *,
        correlation_id: str,
    ) -> None:
        try:
            authorize_row(
                scope=self._generation.scope,
                registry=self._generation.registry,
                selectors=selectors,
                project_binding_id=row["project_binding_id"],
                source_registration_id=row["source_registration_id"],
                authority_site=row["authority_site"],
                authority_domain=row["authority_domain"],
            )
        except BoundScopeError as exc:
            raise StrictPublicError("scope_denied", correlation_id=correlation_id) from exc

    def _snapshot_fields(self) -> dict[str, Any]:
        gen = self._generation
        return {
            "snapshot_id": gen.snapshot_id,
            "lineage_id": gen.lineage_id,
            "authority_seq": gen.authority_seq,
            "authority_manifest_sha256": gen.authority_manifest_sha256,
            "semantic_contract_sha256": gen.semantic_contract_sha256,
            "state_basis": "complete_bound_authority",
            "verification_basis": "recorded_qualified_checks",
            "as_of": gen.as_of,
            "expires_at": gen.expires_at,
        }

    def _format_result(self, row: Mapping[str, Any]) -> dict[str, Any]:
        document, truncated = _truncate_document(str(row["document"]))
        target = row.get("target_assertion_id")
        target_ledger = None
        if isinstance(target, str) and target:
            target_ledger = f"cm1.{row['public_binding_ref']}.{target}"
        supersedes = [
            f"cm1.{row['public_binding_ref']}.{aid}"
            for aid in row.get("supersedes_assertion_ids", [])
            if isinstance(aid, str) and aid
        ]
        site_val = row["authority_site"]
        if not isinstance(site_val, str) or not site_val:
            site_val = "not_applicable"
        return {
            "title": row["title"],
            "document": document,
            "ledger_id": row["public_ledger_id"],
            "citation_ref": row["citation_ref"],
            "record_kind": row["record_kind"],
            "logical_id": row["logical_id"],
            "authority_state": row["authority_state"],
            "verification_state": row["verification_state"],
            "verification_result": row["verification_result"],
            "target_ledger_id": target_ledger,
            "supersedes_ledger_ids": supersedes,
            "origin_assurance": row["origin_assurance"],
            "provenance_qualification": dict(row["provenance_qualification"]),
            "provenance_basis": _provenance_basis_from_capture(row.get("provenance_qualification")),
            "check_eligibility": row["check_eligibility"],
            "state_sha256": row["state_sha256"],
            "confidence_bps": row["confidence_bps"],
            "observed_at": row["observed_at"],
            "recorded_at": row["recorded_at"],
            "decision_disposition_ref": row["decision_disposition_ref"],
            "supersession_disposition_ref": row["supersession_disposition_ref"],
            "state_disposition_refs": list(row["state_disposition_refs"]),
            "truncated": truncated,
            "domain": row["authority_domain"],
            "site": site_val,
        }

    def _pack_success(
        self,
        *,
        results: list[dict[str, Any]],
        selection_complete: bool,
        display_basis: str,
        correlation_id: str,
    ) -> dict[str, Any]:
        payload = {
            "schema": "convmem.raw-evidence.v3",
            "instruction_authority": "none",
            "snapshot": self._snapshot_fields(),
            "selection_complete": selection_complete,
            "display_basis": display_basis,
            "results": results,
        }
        encoded = strict_canonical_bytes(payload)
        if len(encoded) > _RESPONSE_BYTE_CAP:
            raise StrictPublicError("response_too_large", correlation_id=correlation_id)
        return payload

    def search_rows(
        self,
        *,
        query: Any,
        top_k: Any = _SEARCH_TOP_K_DEFAULT,
        project: Any = OMITTED,
        site: Any = OMITTED,
        domain: Any = OMITTED,
        cross_domain: Any = OMITTED,
        correlation_id: str | None = None,
    ) -> dict[str, Any]:
        cid = correlation_id or _new_correlation_id()
        self._ensure_active(cid)
        if not isinstance(query, str):
            raise StrictPublicError("invalid_request", correlation_id=cid)
        if len(query) < 1 or len(query) > _QUERY_CODEPOINT_CAP:
            raise StrictPublicError("invalid_request", correlation_id=cid)
        # Architecture §6.5.5: split only on whitespace; grammar/length stage on
        # every token before tokenization/scoring. Punctuation-wrapped tokens
        # remain ordinary search text.
        for ws_token in query.split():
            if looks_like_public_ledger_handle(ws_token):
                raise StrictPublicError("identifier_query_not_supported", correlation_id=cid)
        if top_k is None:
            raise StrictPublicError("invalid_request", correlation_id=cid)
        if not isinstance(top_k, int) or isinstance(top_k, bool):
            raise StrictPublicError("invalid_request", correlation_id=cid)
        if top_k < 1 or top_k > _SEARCH_TOP_K_MAX:
            raise StrictPublicError("invalid_request", correlation_id=cid)

        selectors = self._resolve_selectors(
            correlation_id=cid,
            project=project,
            site=site,
            domain=domain,
            cross_domain=cross_domain,
        )
        tokens = tokenize_lexical(query)
        if not tokens:
            raise StrictPublicError("invalid_request", correlation_id=cid)
        distinct = _distinct_first(tokens)
        if len(distinct) > _QUERY_TOKEN_CAP:
            raise StrictPublicError("invalid_request", correlation_id=cid)
        normalized_query = " ".join(tokens)

        # Parent §6.5.5: hist asc, score desc, observed_at desc, assertion_id asc.
        ranked: list[tuple[int, int, str, str, dict[str, Any]]] = []
        for row in self._generation.rows:
            title = str(row["title"])
            document = str(row["document"])
            title_n = " ".join(tokenize_lexical(title))
            doc_n = " ".join(tokenize_lexical(document))
            if not any(tok in title_n or tok in doc_n for tok in distinct):
                continue
            if not self._row_authorized_or_false(row, selectors):
                continue
            score = _score_row(
                normalized_query=normalized_query,
                query_tokens=distinct,
                title=title,
                document=document,
            )
            hist = 0 if row["authority_state"] in _CURRENT_RANK_STATES else 1
            ranked.append((hist, score, str(row["observed_at"]), str(row["assertion_id"]), row))

        ranked.sort(key=lambda t: (t[0], -t[1], tuple(-ord(c) for c in t[2]), t[3]))
        limited = ranked[:top_k]
        packed_results: list[dict[str, Any]] = []
        for item in limited:
            formatted = self._format_result(item[4])
            candidate = packed_results + [formatted]
            trial = {
                "schema": "convmem.raw-evidence.v3",
                "instruction_authority": "none",
                "snapshot": self._snapshot_fields(),
                "selection_complete": False,
                "display_basis": "ranked_selection",
                "results": candidate,
            }
            if len(strict_canonical_bytes(trial)) > _RESPONSE_BYTE_CAP:
                if not packed_results:
                    raise StrictPublicError("response_too_large", correlation_id=cid)
                break
            packed_results.append(formatted)

        selection_complete = len(ranked) <= len(packed_results)
        return self._pack_success(
            results=packed_results,
            selection_complete=selection_complete,
            display_basis="ranked_selection",
            correlation_id=cid,
        )

    def _row_authorized_or_false(self, row: Mapping[str, Any], selectors: EffectiveSelectors) -> bool:
        try:
            authorize_row(
                scope=self._generation.scope,
                registry=self._generation.registry,
                selectors=selectors,
                project_binding_id=row["project_binding_id"],
                source_registration_id=row["source_registration_id"],
                authority_site=row["authority_site"],
                authority_domain=row["authority_domain"],
            )
            return True
        except BoundScopeError:
            return False

    def unresolved_rows(
        self,
        *,
        limit: Any = _UNRESOLVED_LIMIT_DEFAULT,
        project: Any = OMITTED,
        site: Any = OMITTED,
        domain: Any = OMITTED,
        cross_domain: Any = OMITTED,
        correlation_id: str | None = None,
    ) -> dict[str, Any]:
        cid = correlation_id or _new_correlation_id()
        self._ensure_active(cid)
        if limit is None:
            raise StrictPublicError("invalid_request", correlation_id=cid)
        if not isinstance(limit, int) or isinstance(limit, bool):
            raise StrictPublicError("invalid_request", correlation_id=cid)
        if limit < 1 or limit > _UNRESOLVED_LIMIT_MAX:
            raise StrictPublicError("invalid_request", correlation_id=cid)
        selectors = self._resolve_selectors(
            correlation_id=cid,
            project=project,
            site=site,
            domain=domain,
            cross_domain=cross_domain,
        )

        candidates: list[dict[str, Any]] = []
        for row in self._generation.rows:
            # Display-only unresolved filter over already-reduced public row fields.
            # Do not invoke a separate query-time state reducer.
            if row["record_kind"] != "observation":
                continue
            if row["authority_state"] == "conflict" or (
                row["authority_state"] == "current" and row["verification_state"] != "pass"
            ):
                pass
            else:
                continue
            if not self._row_authorized_or_false(row, selectors):
                continue
            candidates.append(row)

        candidates.sort(
            key=lambda r: (
                0 if r["authority_state"] in _CURRENT_RANK_STATES else 1,
                tuple(-ord(c) for c in str(r["observed_at"])),
                r["assertion_id"],
            )
        )

        limited = candidates[:limit]
        packed_results: list[dict[str, Any]] = []
        for row in limited:
            formatted = self._format_result(row)
            candidate = packed_results + [formatted]
            trial = {
                "schema": "convmem.raw-evidence.v3",
                "instruction_authority": "none",
                "snapshot": self._snapshot_fields(),
                "selection_complete": False,
                "display_basis": "ranked_selection",
                "results": candidate,
            }
            if len(strict_canonical_bytes(trial)) > _RESPONSE_BYTE_CAP:
                if not packed_results:
                    raise StrictPublicError("response_too_large", correlation_id=cid)
                break
            packed_results.append(formatted)

        selection_complete = len(candidates) <= len(packed_results)
        return self._pack_success(
            results=packed_results,
            selection_complete=selection_complete,
            display_basis="ranked_selection",
            correlation_id=cid,
        )

    def related_neighborhood(
        self,
        *,
        ledger_id: Any,
        project: Any = OMITTED,
        site: Any = OMITTED,
        domain: Any = OMITTED,
        cross_domain: Any = OMITTED,
        correlation_id: str | None = None,
    ) -> dict[str, Any]:
        work = SimpleNamespace()
        work.cid = correlation_id or _new_correlation_id()
        self._ensure_active(work.cid)
        work.selectors = self._resolve_selectors(
            correlation_id=work.cid,
            project=project,
            site=site,
            domain=domain,
            cross_domain=cross_domain,
        )
        try:
            work.public_ref, work.stored_id = parse_public_ledger_handle(ledger_id)
        except StrictEvidenceError as exc:
            raise StrictPublicError("scope_denied", correlation_id=work.cid) from exc

        work.binding_id = self._generation.scope.allowed_project_bindings[0]
        work.binding = self._generation.registry.binding(work.binding_id)
        if work.public_ref != work.binding.public_ref:
            raise StrictPublicError("scope_denied", correlation_id=work.cid)

        work.matches = self._rows_by_assertion.get(work.stored_id)
        if work.matches is None or len(work.matches) != 1:
            raise StrictPublicError("scope_denied", correlation_id=work.cid)
        work.target = work.matches[0]
        work.collected = {}

        _related_walk_parents(self, work)
        _related_collect_descendants(self, work, work.target["assertion_id"], _RELATED_DESCENDANT_DEPTH)

        if work.non_expanding_hit is not None:
            pass
        elif work.observation_anchor is not None:
            _related_collect_descendants(self, work, work.observation_anchor, _RELATED_DESCENDANT_DEPTH)

        _related_expand_heads(self, work)

        for row in work.collected.values():
            self._authorize(row, work.selectors, correlation_id=work.cid)

        work.ordered = sorted(work.collected.values(), key=lambda r: r["assertion_id"])
        work.results = [self._format_result(row) for row in work.ordered]
        try:
            return self._pack_success(
                results=work.results,
                selection_complete=True,
                display_basis="bounded_context",
                correlation_id=work.cid,
            )
        except StrictPublicError as exc:
            raise StrictPublicError("scope_denied", correlation_id=work.cid) from exc


def dispatch_tool(
    reader: StrictProjectionReader,
    method: str,
    arguments: Mapping[str, Any],
    *,
    correlation_id: str | None = None,
) -> dict[str, Any]:
    """Dispatch one of the three fixed methods; preserve omitted vs null via raw keys."""

    cid = correlation_id or _new_correlation_id()
    raw = dict(arguments)

    def _sel(name: str) -> Any:
        return raw[name] if name in raw else OMITTED

    try:
        if method == "search":
            if "query" not in raw:
                raise StrictPublicError("invalid_request", correlation_id=cid)
            top_k = raw["top_k"] if "top_k" in raw else _SEARCH_TOP_K_DEFAULT
            return reader.search_rows(
                query=raw["query"],
                top_k=top_k,
                project=_sel("project"),
                site=_sel("site"),
                domain=_sel("domain"),
                cross_domain=_sel("cross_domain"),
                correlation_id=cid,
            )
        if method == "unresolved":
            limit = raw["limit"] if "limit" in raw else _UNRESOLVED_LIMIT_DEFAULT
            return reader.unresolved_rows(
                limit=limit,
                project=_sel("project"),
                site=_sel("site"),
                domain=_sel("domain"),
                cross_domain=_sel("cross_domain"),
                correlation_id=cid,
            )
        if method == "related":
            if "ledger_id" not in raw:
                raise StrictPublicError("invalid_request", correlation_id=cid)
            return reader.related_neighborhood(
                ledger_id=raw["ledger_id"],
                project=_sel("project"),
                site=_sel("site"),
                domain=_sel("domain"),
                cross_domain=_sel("cross_domain"),
                correlation_id=cid,
            )
        raise StrictPublicError("invalid_request", correlation_id=cid)
    except StrictPublicError:
        raise
    except StrictProjectionError as exc:
        msg = str(exc)
        if msg in {"snapshot_expired", "publication_not_serving"} or "snapshot" in msg:
            raise StrictPublicError("snapshot_stale", correlation_id=cid) from exc
        raise StrictPublicError("internal_failure", correlation_id=cid) from exc
    except Exception as exc:  # noqa: BLE001 — equalized public failure
        raise StrictPublicError("internal_failure", correlation_id=cid) from exc


def _cli_read(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="strict_projection.py")
    sub = parser.add_subparsers(dest="command", required=True)
    read_p = sub.add_parser("read")
    read_p.add_argument("--method", required=True, choices=("search", "unresolved", "related"))
    read_p.add_argument("--scope", required=True)
    read_p.add_argument("--registry", required=True)
    read_p.add_argument("--strict-config", required=True)
    read_p.add_argument("--request-file", required=True)
    read_p.add_argument("--expected-publication", required=True)
    args = parser.parse_args(argv)

    correlation_id = _new_correlation_id()
    generation: QualifiedStrictGeneration | None = None
    lock_fd = -1
    started_boottime_ns = boottime_ns()
    try:
        scope_path = Path(args.scope)
        registry_path = Path(args.registry)
        config_path = Path(args.strict_config)
        operator_pins = collect_operator_path_pins(scope_path, registry_path, config_path)
        scope = load_bound_read_scope_for_strict(scope_path)
        registry = load_project_binding_registry_for_strict(registry_path)
        config = load_strict_config(config_path)
        request_obj = _read_json_public(Path(args.request_file))
        if not isinstance(request_obj, dict):
            raise StrictPublicError("invalid_request", correlation_id=correlation_id)

        # Acquire shared lineage lock BEFORE private qualification; hold the
        # same lock across qualify → public open → dispatch → final recheck →
        # buffered stdout commit.
        try:
            binding_id = scope.allowed_project_bindings[0]
            lineage_id = registry.binding(binding_id).lineage_id
        except (BoundScopeError, IndexError, KeyError) as exc:
            raise StrictProjectionError("scope_registry") from exc
        locks_dir = config.projection_root / "locks"
        _require_public_dir(locks_dir)
        lock_path = locks_dir / f"{lineage_id}.lock"
        lock_fd, lock_inode = _acquire_shared_lineage_lock(lock_path)

        qualify_authority_generation(
            root=config.projection_root,
            scope=scope,
            registry=registry,
            expected_publication_sha256=args.expected_publication,
            require_serving=True,
        )
        generation = open_published_generation(
            root=config.projection_root,
            scope=scope,
            registry=registry,
            expected_publication_sha256=args.expected_publication,
            operator_path_pins=operator_pins,
            held_lock=(lock_fd, lock_inode),
        )
        # Capability now owns the lock fd.
        lock_fd = -1
        reader = StrictProjectionReader(generation)
        result = dispatch_tool(reader, args.method, request_obj, correlation_id=correlation_id)
        # 10-second CLOCK_BOOTTIME bound: elapsed >= 10s is stale.
        # Final publication/time recheck before a single buffered stdout commit.
        if boottime_ns() - started_boottime_ns >= _CLI_BOOTTIME_BUDGET_NS:
            raise StrictPublicError("snapshot_stale", correlation_id=correlation_id)
        recheck_live_public_capability(generation)
        if boottime_ns() - started_boottime_ns >= _CLI_BOOTTIME_BUDGET_NS:
            raise StrictPublicError("snapshot_stale", correlation_id=correlation_id)
        out = strict_canonical_bytes(result) + b"\n"
        sys.stdout.buffer.write(out)
        return 0
    except StrictPublicError as exc:
        # No partial success stdout: errors still emit one closed error envelope.
        sys.stdout.buffer.write(strict_canonical_bytes(exc.payload))
        sys.stdout.buffer.write(b"\n")
        return 1
    except (StrictProjectionError, BoundScopeError, StrictEvidenceError, OSError) as exc:
        err = StrictPublicError("internal_failure", correlation_id=correlation_id)
        if isinstance(exc, StrictProjectionError) and str(exc) in {
            "snapshot_expired",
            "publication_not_serving",
            "publication_cas_mismatch",
        }:
            err = StrictPublicError("snapshot_stale", correlation_id=correlation_id)
        sys.stdout.buffer.write(strict_canonical_bytes(err.payload))
        sys.stdout.buffer.write(b"\n")
        return 1
    finally:
        if generation is not None and not generation.is_revoked:
            try:
                revoke_snapshot(generation)
            except StrictProjectionError:
                pass
        elif lock_fd >= 0:
            try:
                fcntl.flock(lock_fd, fcntl.LOCK_UN)
            except OSError:
                pass
            try:
                os.close(lock_fd)
            except OSError:
                pass


def main(argv: Sequence[str] | None = None) -> int:
    return _cli_read(argv)


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "QualifiedAuthorityGeneration",
    "QualifiedStrictGeneration",
    "StrictConfig",
    "StrictProjectionError",
    "StrictProjectionReader",
    "StrictPublicError",
    "boottime_ns",
    "collect_operator_path_pins",
    "dispatch_tool",
    "load_bound_read_scope_for_strict",
    "load_project_binding_registry_for_strict",
    "load_strict_config",
    "main",
    "open_public_projection",
    "open_published_generation",
    "pin_operator_immutable_path",
    "qualify_authority_generation",
    "recheck_live_public_capability",
    "recheck_operator_immutable_path",
    "revoke_snapshot",
    "tokenize_lexical",
    "wall_time_utc",
]

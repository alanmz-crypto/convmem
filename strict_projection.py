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
    disposition_id,
    reduce_complete_bound_state,
    state_sha256,
)
from strict_grounding import StrictGroundingError, strict_canonical_bytes


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
    return _require_self_hash(input_obj, field, label="input")


def qualify_authority_generation(
    *,
    root: str | Path,
    scope: BoundReadScope,
    registry: ProjectBindingRegistry,
    expected_publication_sha256: str | None = None,
    require_serving: bool = False,
) -> QualifiedAuthorityGeneration:
    """Full private cold reconstruction over authority (+ projection when serving).

    Reads private citation/grounding/provenance files. Recomputes complete-bound
    state and compares committed digests. Never opens a query-time reducer path.
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

    # --- Enrolled empty genesis (seq 0): null authority IDs/hashes/anchor; never serving ---
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
        # unavailable (non-genesis): authority present; serving/projection both null
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

    auth_dir = root_path / "authority" / snapshot_id
    if auth_dir.is_symlink() or not auth_dir.is_dir():
        raise StrictProjectionError("authority_dir")

    manifest = _read_json(auth_dir / "manifest.json")
    _require_closed(
        manifest,
        _AUTHORITY_MANIFEST_FIELDS,
        schema="convmem.bound-authority-manifest.v3",
        label="authority_manifest",
    )
    if manifest["lineage_id"] != lineage_id:
        raise StrictProjectionError("authority_manifest_lineage")
    if manifest["authority_seq"] != authority_seq:
        raise StrictProjectionError("authority_manifest_seq")
    if manifest["owner_digest"] != recomputed_owner:
        raise StrictProjectionError("authority_manifest_owner")
    if manifest["semantic_contract_sha256"] != semantic_contract_sha256:
        raise StrictProjectionError("authority_manifest_semantic_contract_link")
    if manifest["scope_sha256"] != scope.scope_sha256:
        raise StrictProjectionError("authority_manifest_scope_link")
    if manifest["registry_sha256"] != registry.registry_sha256:
        raise StrictProjectionError("authority_manifest_registry_link")

    recomputed_snapshot_id = _authority_snapshot_id(manifest)
    if manifest["snapshot_id"] != recomputed_snapshot_id:
        raise StrictProjectionError("authority_snapshot_id_mismatch")
    if snapshot_id != recomputed_snapshot_id:
        raise StrictProjectionError("publication_snapshot_id_link")

    recomputed_manifest_payload = _labeled_self_hash(manifest, "manifest_payload_sha256")
    if manifest["manifest_payload_sha256"] != recomputed_manifest_payload:
        raise StrictProjectionError("authority_manifest_hash")
    if authority_manifest_sha256 != recomputed_manifest_payload:
        raise StrictProjectionError("authority_manifest_link")

    if authority_seq == 1:
        if manifest["parent_snapshot_id"] is not None or manifest["parent_manifest_sha256"] is not None:
            raise StrictProjectionError("authority_parent_null")
    else:
        if not isinstance(manifest["parent_snapshot_id"], str):
            raise StrictProjectionError("authority_parent_snapshot")
        if not isinstance(manifest["parent_manifest_sha256"], str):
            raise StrictProjectionError("authority_parent_manifest")

    # --- Private file links committed by the authority manifest ---
    for name in (
        "input.json",
        "source-cutoff.json",
        "records.jsonl",
        "dispositions.jsonl",
        "citation-map.json",
        "provenance-context.json",
        "grounding.json",
    ):
        if not (auth_dir / name).is_file() or (auth_dir / name).is_symlink():
            raise StrictProjectionError(f"private_missing:{name}")

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
    if publication["authority_source_cutoff_sha256"] != cutoff_digest:
        raise StrictProjectionError("publication_cutoff_link")

    records = _read_jsonl(auth_dir / "records.jsonl")
    for rec in records:
        _require_closed(
            rec,
            _AUTHORITY_RECORD_FIELDS,
            schema="convmem.bound-authority-record.v3",
            label="authority_record",
        )
        payload_digest = _labeled_self_hash(rec, "payload_sha256")
        if rec["payload_sha256"] != payload_digest:
            raise StrictProjectionError("record_payload_hash")
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
    _require_closed(
        provenance_context,
        _PROVENANCE_CONTEXT_FIELDS,
        schema="convmem.strict-provenance-context.v2",
        label="provenance_context",
    )
    context_digest = _require_self_hash(
        provenance_context, "context_payload_sha256", label="provenance_context"
    )
    if manifest["provenance_context_sha256"] != context_digest:
        raise StrictProjectionError("provenance_context_link")

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
    if provenance_context["grounding_sha256"] != grounding_digest:
        raise StrictProjectionError("provenance_grounding_link")

    binding = registry.binding(binding_id)
    producers = [
        {
            "source_registration_id": p.source_registration_id,
            "producer": p.producer,
            "transformer_identity": p.transformer_identity,
            "transformer_version": p.transformer_version,
            "transformer_artifact_sha256": p.transformer_artifact_sha256,
            "recipe_sha256": p.recipe_sha256,
            "capture_class": p.capture_class,
        }
        for p in binding.verification_producers
    ]
    try:
        reduced = reduce_complete_bound_state(
            records, dispositions, verification_producers=producers
        )
    except (StrictGroundingError, BoundScopeError, ValueError) as exc:
        raise StrictProjectionError(f"reduce:{exc}") from exc

    selectors = EffectiveSelectors(
        project=scope.project,
        site=scope.site,
        site_mode=scope.site_mode,
        domain=scope.domain,
        binding_id=binding_id,
    )
    for rec in records:
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
        if proj_manifest["as_of"] != manifest["as_of"] or proj_manifest["expires_at"] != manifest[
            "expires_at"
        ]:
            raise StrictProjectionError("projection_time_copy")

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

        rows = _read_jsonl(gen_dir / "rows.jsonl")
        for row in rows:
            _require_closed(
                row,
                _PROJECTION_ROW_FIELDS,
                schema="convmem.bound-projection-row.v2",
                label="projection_row",
            )
        row_ids = [r["assertion_id"] for r in rows]
        if row_ids != sorted(row_ids) or len(row_ids) != len(set(row_ids)):
            raise StrictProjectionError("rows_sort")
        rows_sha256 = _jsonl_sha256(rows)
        if proj_manifest["rows_sha256"] != rows_sha256:
            raise StrictProjectionError("rows_hash_mismatch")
        if proj_manifest["row_count"] != len(rows):
            raise StrictProjectionError("row_count")

        for row in rows:
            st = reduced.get(row["assertion_id"])
            if st is None:
                raise StrictProjectionError("row_missing_state")
            expected_state = state_sha256(
                lineage_id=lineage_id,
                authority_seq=authority_seq,
                authority_manifest_sha256=authority_manifest_sha256,
                semantic_contract_sha256=semantic_contract_sha256,
                reduced=st,
            )
            if row["state_sha256"] != expected_state:
                raise StrictProjectionError("row_state_mismatch")
            if row["authority_state"] != st.authority_state:
                raise StrictProjectionError("row_authority_state")
            if row["verification_state"] != st.verification_state:
                raise StrictProjectionError("row_verification_state")
            if row["payload_sha256"] != next(
                r["payload_sha256"] for r in records if r["assertion_id"] == row["assertion_id"]
            ):
                raise StrictProjectionError("row_payload_link")
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

        graph = _read_json(gen_dir / "graph.json")
        _require_closed(
            graph, _GRAPH_FIELDS, schema="convmem.strict-graph.v1", label="graph"
        )
        nodes = graph["nodes"]
        edges = graph["edges"]
        if not isinstance(nodes, list) or not isinstance(edges, list):
            raise StrictProjectionError("graph_arrays")
        if nodes != sorted(set(nodes)) or any(not isinstance(n, str) for n in nodes):
            raise StrictProjectionError("graph_nodes")
        for edge in edges:
            if not isinstance(edge, dict) or set(edge) != _GRAPH_EDGE_FIELDS:
                raise StrictProjectionError("graph_edge_keys")
            if edge["kind"] not in {"relates_to", "targets", "supersedes"}:
                raise StrictProjectionError("graph_edge_kind")
            if edge["from_assertion_id"] not in nodes or edge["to_assertion_id"] not in nodes:
                raise StrictProjectionError("graph_edge_resolve")
        edge_keys = [
            (e["kind"], e["from_assertion_id"], e["to_assertion_id"]) for e in edges
        ]
        if edge_keys != sorted(set(edge_keys)):
            raise StrictProjectionError("graph_edges_sort")
        graph_sha256 = _require_self_hash(graph, "graph_payload_sha256", label="graph")
        if proj_manifest["graph_sha256"] != graph_sha256:
            raise StrictProjectionError("graph_hash_mismatch")
        if proj_manifest["graph_node_count"] != len(nodes):
            raise StrictProjectionError("graph_node_count")

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
        expires_at=manifest["expires_at"],
        as_of=manifest["as_of"],
    )


# Intentionally no open_public_projection / revoke_snapshot / read CLI here (M4/T3).


__all__ = [
    "QualifiedAuthorityGeneration",
    "StrictProjectionError",
    "qualify_authority_generation",
]

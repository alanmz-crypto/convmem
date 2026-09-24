"""Strict grounding, capture-receipt authentication, and qualification (T1)."""

# pylint: disable=C0302  # preserved grounding/provenance qualification component boundary


from __future__ import annotations

import base64
import json
import re
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Mapping, Sequence

from canonical_json import canonical_json_bytes
from provenance import (
    EnvelopeValidationError,
    ProvenanceRegistry,
    TransformerRule,
    provenance_commitment as legacy_provenance_commitment,
    validate_envelope,
)

from bound_read_scope import CaptureIssuer, sha256_digest

_SHA_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
_HEX64_RE = re.compile(r"^[0-9a-f]{64}$")
_HEX32_RE = re.compile(r"^[0-9a-f]{32}$")
_TS_RE = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z$")
_MAX_BLOB_DECODED = 32 * 1024 * 1024

_ROOT_KEYS = frozenset(
    {
        "provenance_assertion_id",
        "provenance_commitment",
        "source_registration_id",
        "source_event_id",
        "source_identity",
        "record_locator",
        "raw_blob_sha256",
        "view_blob_sha256",
        "selector",
        "receipt_ref",
    }
)
_EDGE_KEYS = frozenset(
    {
        "child_provenance_assertion_id",
        "child_provenance_commitment",
        "parent_provenance_assertion_id",
        "parent_provenance_commitment",
        "parent_output_blob_sha256",
        "view_blob_sha256",
        "selector",
        "receipt_ref",
    }
)
_OUTPUT_KEYS = frozenset(
    {
        "provenance_assertion_id",
        "provenance_commitment",
        "output_blob_sha256",
    }
)

_PROVENANCE_CONTEXT_KEYS = frozenset(
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
_SCHEMA_SEMANTICS_KEYS = frozenset(
    {
        "schema_version",
        "binding_version",
        "semantic_bytes_b64",
        "semantic_sha256",
    }
)
_POLICY_KEYS = frozenset(
    {
        "policy_version",
        "semantic_bytes_b64",
        "semantic_sha256",
        "rules",
    }
)
_RULE_KEYS = frozenset(
    {
        "transformer_class",
        "transformer_identity",
        "transformer_version",
        "recipe_id",
        "cap",
        "preservation_contract",
        "artifact_sha256",
    }
)
_RECIPE_KEYS = frozenset({"recipe_id", "recipe_bytes_b64", "recipe_sha256"})
_CHANNEL_KEYS = frozenset(
    {
        "origin_class",
        "channel_class",
        "channel_locator",
        "channel_evidence_sha256",
    }
)
_REGISTERED_ASSERTION_KEYS = frozenset({"assertion_id", "provenance_commitment", "envelope"})


class StrictGroundingError(ValueError):
    """Fail-closed grounding/qualification error."""


@dataclass(frozen=True, slots=True)
class QualificationTuple:
    commitments: str  # valid|incomplete
    byte_grounding: str  # complete|missing
    capture: str  # synthetic_fixture|controlled_capture|unattested
    transformer_cap: str  # trusted|agent|untrusted

    def as_dict(self) -> dict[str, str]:
        return {
            "commitments": self.commitments,
            "byte_grounding": self.byte_grounding,
            "capture": self.capture,
            "transformer_cap": self.transformer_cap,
        }


def _reject_floats(value: Any, *, path: str = "$") -> None:
    if isinstance(value, float):
        raise StrictGroundingError(f"float_forbidden:{path}")
    if isinstance(value, dict):
        for key, child in value.items():
            _reject_floats(child, path=f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _reject_floats(child, path=f"{path}[{index}]")


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in pairs:
        if key in out:
            raise StrictGroundingError(f"duplicate_key:{key}")
        out[key] = value
    return out


def _x_validate(work: SimpleNamespace, obj: Any) -> None:
    _reject_floats(obj)

def strict_canonical_bytes(value: Any) -> bytes:

    return canonical_json_bytes(value, validate=_validate, error_type=StrictGroundingError)



def _b64_decode(text: str) -> bytes:
    if not isinstance(text, str):
        raise StrictGroundingError("bytes_b64_invalid")
    try:
        decoded = base64.b64decode(text, validate=True)
    except Exception as exc:  # noqa: BLE001
        raise StrictGroundingError("bytes_b64_invalid") from exc
    if base64.b64encode(decoded).decode("ascii") != text:
        raise StrictGroundingError("bytes_b64_noncanonical")
    return decoded


def _labeled_hash(value: Any) -> str | None:
    """Normalize legacy bare-hex or labeled sha256 digests to sha256:<hex>."""

    if not isinstance(value, str) or not value:
        return None
    if _SHA_RE.fullmatch(value):
        return value
    if _HEX64_RE.fullmatch(value):
        return "sha256:" + value
    return None


def _hashes_equal(left: Any, right: Any) -> bool:
    a = _labeled_hash(left)
    b = _labeled_hash(right)
    return a is not None and a == b


def _bare_hex(value: Any, *, field: str) -> str:
    """Accept labeled sha256:<hex> or bare hex; return bare lowercase hex."""

    if not isinstance(value, str) or not value:
        raise StrictGroundingError(field)
    if _SHA_RE.fullmatch(value):
        return value.removeprefix("sha256:")
    if _HEX64_RE.fullmatch(value):
        return value
    raise StrictGroundingError(field)


def _to_labeled(value: Any, *, field: str) -> str:
    return "sha256:" + _bare_hex(value, field=field)


def _strip_receipt_ref(binding: Mapping[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in binding.items() if k != "receipt_ref"}


def tagged_bindings_for_hash(
    roots: Sequence[Mapping[str, Any]],
    edges: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Ordered tagged bindings with receipt_ref removed (roots then edges)."""

    tagged: list[dict[str, Any]] = []
    for root in roots:
        tagged.append({"kind": "root", "binding": _strip_receipt_ref(root)})
    for edge in edges:
        tagged.append({"kind": "edge", "binding": _strip_receipt_ref(edge)})
    return tagged


def compute_input_bindings_sha256(
    roots: Sequence[Mapping[str, Any]],
    edges: Sequence[Mapping[str, Any]],
) -> str:
    return sha256_digest(strict_canonical_bytes(tagged_bindings_for_hash(roots, edges)))


def compute_submitted_views_sha256(
    roots: Sequence[Mapping[str, Any]],
    edges: Sequence[Mapping[str, Any]],
) -> str:
    views = [r["view_blob_sha256"] for r in roots] + [e["view_blob_sha256"] for e in edges]
    return sha256_digest(strict_canonical_bytes(views))


def receipt_ref_for(receipt: Mapping[str, Any]) -> str:
    payload = {k: v for k, v in receipt.items() if k != "receipt_payload_sha256"}
    digest = sha256_digest(strict_canonical_bytes(payload))
    expected = receipt.get("receipt_payload_sha256")
    if expected != digest:
        raise StrictGroundingError("receipt_payload_mismatch")
    return "capture_" + digest.removeprefix("sha256:")


def load_issuer_receipt_inventory(receipt_root: str | Path) -> dict[str, bytes]:
    """Load protected issuer inventory: receipt_ref -> exact receipt bytes.

    Exact bytes only. No newline/format normalization, aliases, or overwrite of
    duplicate receipt_ref / capture_id rows. The receipt_root directory itself
    must not be writable (protected inventory).
    """

    root = Path(receipt_root)
    if not root.is_absolute() or root.is_symlink() or not root.is_dir():
        raise StrictGroundingError("receipt_root_invalid")
    if root.stat().st_mode & 0o222:
        raise StrictGroundingError("receipt_root_writable")
    inventory: dict[str, bytes] = {}
    seen_capture_ids: set[str] = set()
    for path in sorted(root.iterdir()):
        if path.is_symlink() or not path.is_file():
            raise StrictGroundingError("receipt_inventory_entry")
        if path.stat().st_mode & 0o222:
            raise StrictGroundingError("receipt_writable")
        raw = path.read_bytes()
        try:
            obj = json.loads(raw.decode("utf-8"), object_pairs_hook=_reject_duplicate_keys)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise StrictGroundingError("receipt_inventory_json") from exc
        if not isinstance(obj, dict) or obj.get("schema") != "convmem.capture-receipt.v1":
            raise StrictGroundingError("receipt_inventory_schema")
        validated = validate_receipt_object(obj)
        ref = receipt_ref_for(validated)
        if ref in inventory:
            raise StrictGroundingError("receipt_ref_duplicate")
        capture_id = validated["capture_id"]
        if capture_id in seen_capture_ids:
            raise StrictGroundingError("capture_id_duplicate")
        seen_capture_ids.add(capture_id)
        inventory[ref] = raw
    return inventory


def validate_receipt_object(receipt: Mapping[str, Any]) -> dict[str, Any]:
    required = {
        "schema",
        "capture_id",
        "capture_class",
        "capture_issuer_id",
        "source_registration_id",
        "source_event_id",
        "provenance_assertion_id",
        "provenance_commitment",
        "input_bindings_sha256",
        "transformer_artifact_sha256",
        "recipe_sha256",
        "submitted_views_sha256",
        "returned_output_sha256",
        "captured_at",
        "receipt_payload_sha256",
    }
    if set(receipt) != required:
        raise StrictGroundingError("receipt_keys")
    if receipt["schema"] != "convmem.capture-receipt.v1":
        raise StrictGroundingError("receipt_schema")
    if not isinstance(receipt["capture_id"], str) or not _HEX32_RE.fullmatch(receipt["capture_id"]):
        raise StrictGroundingError("capture_id")
    if receipt["capture_class"] not in {"synthetic_fixture", "controlled_capture"}:
        raise StrictGroundingError("capture_class")
    for field in (
        "capture_issuer_id",
        "source_registration_id",
        "source_event_id",
        "provenance_assertion_id",
    ):
        if not isinstance(receipt[field], str) or not receipt[field]:
            raise StrictGroundingError(field)
    for field in (
        "provenance_commitment",
        "input_bindings_sha256",
        "transformer_artifact_sha256",
        "recipe_sha256",
        "submitted_views_sha256",
        "returned_output_sha256",
        "receipt_payload_sha256",
    ):
        if not isinstance(receipt[field], str) or not _SHA_RE.fullmatch(receipt[field]):
            raise StrictGroundingError(field)
    if not isinstance(receipt["captured_at"], str) or not _TS_RE.fullmatch(receipt["captured_at"]):
        raise StrictGroundingError("captured_at")
    receipt_ref_for(receipt)  # validates payload hash
    return dict(receipt)


def authenticate_receipt(
    receipt: Mapping[str, Any],
    *,
    inventory_bytes: Mapping[str, bytes],
    allowed_issuer_ids: set[str],
    allowed_source_registration_ids: set[str],
    capture_issuers: Sequence[CaptureIssuer] | None = None,
) -> str:
    """Return receipt_ref only when exact inventory bytes already authenticate it."""

    validated = validate_receipt_object(receipt)
    issuer_id = validated["capture_issuer_id"]
    source_id = validated["source_registration_id"]
    if issuer_id not in allowed_issuer_ids:
        raise StrictGroundingError("receipt_issuer_unknown")
    if source_id not in allowed_source_registration_ids:
        raise StrictGroundingError("receipt_source_unknown")
    if capture_issuers is not None:
        issuer_map = {i.issuer_id: i for i in capture_issuers}
        if issuer_id not in issuer_map:
            raise StrictGroundingError("receipt_issuer_unenrolled")
        enrolled = issuer_map[issuer_id]
        if enrolled.capture_class != validated["capture_class"]:
            raise StrictGroundingError("receipt_issuer_class_mismatch")
        if source_id not in enrolled.source_registration_ids:
            raise StrictGroundingError("receipt_source_unenrolled")
    ref = receipt_ref_for(validated)
    exact = inventory_bytes.get(ref)
    if exact is None:
        raise StrictGroundingError("receipt_not_in_inventory")
    # Exact protected bytes only — no newline/format normalization into membership.
    expected_bytes = strict_canonical_bytes(validated)
    if exact != expected_bytes:
        raise StrictGroundingError("receipt_inventory_bytes_mismatch")
    return ref


def _validate_selector(selector: Mapping[str, Any], *, input_length: int) -> None:
    if not isinstance(selector, dict):
        raise StrictGroundingError("selector_type")
    kind = selector.get("kind")
    if kind == "identity":
        if set(selector) != {"kind"}:
            raise StrictGroundingError("selector_identity_keys")
        return
    if kind == "byte_range":
        if set(selector) != {"kind", "start", "end"}:
            raise StrictGroundingError("selector_range_keys")
        start, end = selector["start"], selector["end"]
        if not isinstance(start, int) or isinstance(start, bool):
            raise StrictGroundingError("selector_start")
        if not isinstance(end, int) or isinstance(end, bool):
            raise StrictGroundingError("selector_end")
        if not 0 <= start <= end <= input_length:
            raise StrictGroundingError("selector_bounds")
        return
    raise StrictGroundingError("selector_kind")


def _apply_selector(raw: bytes, selector: Mapping[str, Any]) -> bytes:
    if selector["kind"] == "identity":
        return raw
    return raw[selector["start"] : selector["end"]]


def _root_sort_key(root: Mapping[str, Any]) -> tuple[str, str, str, str]:
    return (
        root["provenance_assertion_id"],
        root["source_registration_id"],
        root["source_event_id"],
        root["record_locator"],
    )


def _edge_sort_key(edge: Mapping[str, Any]) -> tuple[str, str, str]:
    return (
        edge["child_provenance_assertion_id"],
        edge["parent_provenance_assertion_id"],
        edge["view_blob_sha256"],
    )


def _grounding_sort_check(items: list[Any], key_fn) -> None:
    keys = [key_fn(item) for item in items]
    if len(keys) != len(set(keys)):
        raise StrictGroundingError("grounding_duplicate_key")
    if keys != sorted(keys):
        raise StrictGroundingError("grounding_sort")


def _gdoc_validate_grounding_document_p0(work: SimpleNamespace) -> None:
    work.required = {'schema', 'blobs', 'roots', 'edges', 'outputs', 'receipts', 'grounding_payload_sha256'}
    if set(work.grounding) != work.required:
        raise StrictGroundingError('grounding_keys')
    if work.grounding['schema'] != 'convmem.strict-grounding.v1':
        raise StrictGroundingError('grounding_schema')
    work.blobs = work.grounding['blobs']
    work.roots = work.grounding['roots']
    work.edges = work.grounding['edges']
    work.outputs = work.grounding['outputs']

def _gdoc_validate_grounding_document_p1(work: SimpleNamespace) -> None:
    work.receipts = work.grounding['receipts']
    if not all((isinstance(x, list) for x in (work.blobs, work.roots, work.edges, work.outputs, work.receipts))):
        raise StrictGroundingError('grounding_arrays')
    work.blob_map: dict[str, bytes] = {}
    work.decoded_total = 0
    work.prev_hash = ''
    for blob in work.blobs:
        if not isinstance(blob, Mapping) or set(blob) != {'sha256', 'length', 'bytes_b64'}:
            raise StrictGroundingError('blob_keys')
        work.digest = blob['sha256']
        if not isinstance(work.digest, str) or not _SHA_RE.fullmatch(work.digest):
            raise StrictGroundingError('blob_sha')
        if work.prev_hash and work.digest < work.prev_hash:
            raise StrictGroundingError('blobs_unsorted')
        if work.digest == work.prev_hash:
            raise StrictGroundingError('blobs_duplicate')
        work.prev_hash = work.digest
        work.raw = _b64_decode(blob['bytes_b64'])
        if blob['length'] != len(work.raw):
            raise StrictGroundingError('blob_length')
        if sha256_digest(work.raw) != work.digest:
            raise StrictGroundingError('blob_digest_mismatch')
        work.decoded_total += len(work.raw)
        if work.decoded_total > _MAX_BLOB_DECODED:
            raise StrictGroundingError('blob_budget')
        work.blob_map[work.digest] = work.raw
    _grounding_sort_check(work.roots, _root_sort_key)

def _gdoc_p2_s0(work: SimpleNamespace) -> None:
    _grounding_sort_check(work.edges, _edge_sort_key)
    _grounding_sort_check(work.outputs, lambda o: o['provenance_assertion_id'])
    _grounding_sort_check(work.receipts, lambda r: r['capture_id'])

def _gdoc_p2_s1_item0(work: SimpleNamespace, root) -> None:
    if not isinstance(root, Mapping) or set(root) != _ROOT_KEYS:
        raise StrictGroundingError('root_keys')
    for field in ('provenance_assertion_id', 'source_registration_id', 'source_event_id', 'source_identity', 'record_locator', 'receipt_ref'):
        if not isinstance(root[field], str) or not root[field]:
            raise StrictGroundingError(f'root_{field}')
    for field in ('provenance_commitment', 'raw_blob_sha256', 'view_blob_sha256'):
        if not isinstance(root[field], str) or not _SHA_RE.fullmatch(root[field]):
            raise StrictGroundingError(f'root_{field}')
    work.raw_sha = root['raw_blob_sha256']
    work.view_sha = root['view_blob_sha256']
    if work.raw_sha not in work.blob_map or work.view_sha not in work.blob_map:
        raise StrictGroundingError('root_blob_missing')
    work.referenced_blobs.add(work.raw_sha)
    work.referenced_blobs.add(work.view_sha)
    _validate_selector(root['selector'], input_length=len(work.blob_map[work.raw_sha]))
    work.view = _apply_selector(work.blob_map[work.raw_sha], root['selector'])
    if sha256_digest(work.view) != work.view_sha:
        raise StrictGroundingError('root_view_mismatch')
    if work.blob_map[work.view_sha] != work.view:
        raise StrictGroundingError('root_view_bytes_mismatch')

def _gdoc_p2_s1_item1(work: SimpleNamespace, edge) -> None:
    if not isinstance(edge, Mapping) or set(edge) != _EDGE_KEYS:
        raise StrictGroundingError('edge_keys')
    for field in ('child_provenance_assertion_id', 'parent_provenance_assertion_id', 'receipt_ref'):
        if not isinstance(edge[field], str) or not edge[field]:
            raise StrictGroundingError(f'edge_{field}')
    for field in ('child_provenance_commitment', 'parent_provenance_commitment', 'parent_output_blob_sha256', 'view_blob_sha256'):
        if not isinstance(edge[field], str) or not _SHA_RE.fullmatch(edge[field]):
            raise StrictGroundingError(f'edge_{field}')
    work.parent_out = edge['parent_output_blob_sha256']
    work.view_sha = edge['view_blob_sha256']
    if work.parent_out not in work.blob_map or work.view_sha not in work.blob_map:
        raise StrictGroundingError('edge_blob_missing')
    work.referenced_blobs.add(work.parent_out)
    work.referenced_blobs.add(work.view_sha)
    _validate_selector(edge['selector'], input_length=len(work.blob_map[work.parent_out]))
    work.view = _apply_selector(work.blob_map[work.parent_out], edge['selector'])
    if sha256_digest(work.view) != work.view_sha:
        raise StrictGroundingError('edge_view_mismatch')
    if work.blob_map[work.view_sha] != work.view:
        raise StrictGroundingError('edge_view_bytes_mismatch')

def _gdoc_p2_s1_item2(work: SimpleNamespace, output) -> None:
    if not isinstance(output, Mapping) or set(output) != _OUTPUT_KEYS:
        raise StrictGroundingError('output_keys')
    if not isinstance(output['provenance_assertion_id'], str) or not output['provenance_assertion_id']:
        raise StrictGroundingError('output_assertion')
    for field in ('provenance_commitment', 'output_blob_sha256'):
        if not isinstance(output[field], str) or not _SHA_RE.fullmatch(output[field]):
            raise StrictGroundingError(f'output_{field}')
    if output['output_blob_sha256'] not in work.blob_map:
        raise StrictGroundingError('output_blob_missing')
    work.referenced_blobs.add(output['output_blob_sha256'])

def _gdoc_p2_s1(work: SimpleNamespace) -> None:
    work.referenced_blobs: set[str] = set()
    for root in work.roots:
        _gdoc_p2_s1_item0(work, root)
    for edge in work.edges:
        _gdoc_p2_s1_item1(work, edge)
    for output in work.outputs:
        _gdoc_p2_s1_item2(work, output)

def _gdoc_validate_grounding_document_p2(work: SimpleNamespace) -> None:
    _gdoc_p2_s0(work)
    _gdoc_p2_s1(work)

def _gdoc_validate_grounding_document_p3(work: SimpleNamespace) -> dict[str, Any]:
    work.receipt_refs: dict[str, dict[str, Any]] = {}
    for receipt in work.receipts:
        work.validated = validate_receipt_object(receipt)
        work.ref = receipt_ref_for(work.validated)
        if work.ref in work.receipt_refs:
            raise StrictGroundingError('receipt_ref_reused')
        work.receipt_refs[work.ref] = work.validated
    work.unused_blobs = set(work.blob_map) - work.referenced_blobs
    if work.unused_blobs:
        raise StrictGroundingError('blob_unused')
    work.payload = {k: v for k, v in work.grounding.items() if k != 'grounding_payload_sha256'}
    work.digest = sha256_digest(strict_canonical_bytes(work.payload))
    if work.grounding['grounding_payload_sha256'] != work.digest:
        raise StrictGroundingError('grounding_payload_mismatch')
    return dict(work.grounding)

def validate_grounding_document(grounding: Mapping[str, Any]) -> dict[str, Any]:
    work = SimpleNamespace()
    work.grounding = grounding

    _gdoc_validate_grounding_document_p0(work)
    _gdoc_validate_grounding_document_p1(work)
    _gdoc_validate_grounding_document_p2(work)
    return _gdoc_validate_grounding_document_p3(work)



def verify_legacy_commitments(
    *,
    envelope: Mapping[str, Any],
    registry: ProvenanceRegistry | None = None,
    schema_semantics: Mapping[tuple[str, str], bytes] | None = None,
) -> str:
    """Return valid|incomplete for legacy envelope verification (never upgrades alone).

    When a reconstructed ProvenanceRegistry is supplied, recursive verify against
    that context-fixed inventory decides validity. Missing/changed ancestry yields
    incomplete; this never maps legacy trust into stronger byte/capture assurance.
    """

    try:
        validated = validate_envelope(envelope, schema_semantics=schema_semantics)
        commitment = legacy_provenance_commitment(validated, schema_semantics=schema_semantics)
        if not commitment:
            return "incomplete"
        if registry is not None:
            assertion_id = validated.get("assertion_id")
            if not isinstance(assertion_id, str) or not assertion_id:
                return "incomplete"
            result = registry.verify(assertion_id)
            if not result.verified:
                return "incomplete"
        return "valid"
    except EnvelopeValidationError:
        return "incomplete"
    except Exception:  # noqa: BLE001  # pylint: disable=W0718  # fail-closed commitment/transformer boundary
        return "incomplete"


def derive_origin_assurance(qualification: QualificationTuple) -> str:
    if (
        qualification.commitments == "valid"
        and qualification.byte_grounding == "complete"
        and qualification.capture in {"synthetic_fixture", "controlled_capture"}
        and qualification.transformer_cap == "trusted"
    ):
        return "verified"
    if (
        qualification.commitments == "valid"
        and qualification.byte_grounding == "complete"
        and qualification.capture in {"synthetic_fixture", "controlled_capture"}
        and qualification.transformer_cap == "agent"
    ):
        return "claimed"
    return "untrusted"


def derive_provenance_basis(qualification: QualificationTuple) -> str:
    if qualification.capture == "synthetic_fixture":
        return "synthetic_fixture"
    if qualification.capture == "controlled_capture":
        return "controlled_capture"
    return "unattested"


def _envelope_commitment(
    envelope: Mapping[str, Any],
    *,
    schema_semantics: Mapping[tuple[str, str], bytes] | None = None,
) -> str:
    """Recompute commitment only. Never fall back to an envelope-supplied claim."""

    try:
        digest = legacy_provenance_commitment(envelope, schema_semantics=schema_semantics)
    except Exception as exc:  # noqa: BLE001
        raise StrictGroundingError("envelope_commitment") from exc
    labeled = _labeled_hash(digest)
    if labeled is None:
        raise StrictGroundingError("envelope_commitment")
    return labeled


def _bindings_for_assertion(
    grounding: Mapping[str, Any],
    assertion_id: str,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    roots = sorted(
        [dict(r) for r in grounding["roots"] if r["provenance_assertion_id"] == assertion_id],
        key=_root_sort_key,
    )
    edges = sorted(
        [dict(e) for e in grounding["edges"] if e["child_provenance_assertion_id"] == assertion_id],
        key=_edge_sort_key,
    )
    return roots, edges


def _match_root_to_envelope(
    root: Mapping[str, Any],
    *,
    envelope: Mapping[str, Any],
    commitment: str,
) -> Mapping[str, Any] | None:
    if root["provenance_assertion_id"] != envelope.get("assertion_id"):
        return None
    if not _hashes_equal(root["provenance_commitment"], commitment):
        return None
    for env_root in envelope.get("root_bindings") or []:
        if (
            env_root.get("source_identity") == root["source_identity"]
            and env_root.get("record_locator") == root["record_locator"]
            and _hashes_equal(env_root.get("raw_record_sha256"), root["raw_blob_sha256"])
            and _hashes_equal(env_root.get("input_view_sha256"), root["view_blob_sha256"])
        ):
            return env_root
    return None


def _match_edge_to_envelope(
    edge: Mapping[str, Any],
    *,
    envelope: Mapping[str, Any],
    commitment: str,
) -> Mapping[str, Any] | None:
    if edge["child_provenance_assertion_id"] != envelope.get("assertion_id"):
        return None
    if not _hashes_equal(edge["child_provenance_commitment"], commitment):
        return None
    for env_in in envelope.get("input_bindings") or []:
        if (
            env_in.get("parent_assertion_id") == edge["parent_provenance_assertion_id"]
            and _hashes_equal(
                env_in.get("parent_provenance_commitment"),
                edge["parent_provenance_commitment"],
            )
            and _hashes_equal(env_in.get("exact_input_view_sha256"), edge["view_blob_sha256"])
        ):
            return env_in
    return None


def _receipt_index(grounding: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for receipt in grounding["receipts"]:
        validated = validate_receipt_object(receipt)
        out[receipt_ref_for(validated)] = validated
    return out


def _vassert_verify_assertion_grounding_p0(work: SimpleNamespace) -> None:
    work.assertion_id = work.envelope.get('assertion_id')
    if not isinstance(work.assertion_id, str) or not work.assertion_id:
        raise StrictGroundingError('envelope_assertion_id')
    work.commitment = _envelope_commitment(work.envelope, schema_semantics=work.schema_semantics)
    work.env_roots = list(work.envelope.get('root_bindings') or [])
    work.env_inputs = list(work.envelope.get('input_bindings') or [])
    if bool(work.env_roots) == bool(work.env_inputs):
        raise StrictGroundingError('envelope_binding_family')
    work.g_roots, work.g_edges = _bindings_for_assertion(work.grounding, work.assertion_id)

def _vassert_p1_0_s0(work: SimpleNamespace) -> None:
    work.missing = False

def _vassert_p1_0_s1_then(work: SimpleNamespace) -> None:
    if len(work.g_roots) != len(work.env_roots):
        if len(work.g_roots) == 0:
            work.missing = True
        else:
            raise StrictGroundingError('root_binding_count')
    if not work.missing:
        for root in work.g_roots:
            env_root = _match_root_to_envelope(root, envelope=work.envelope, commitment=work.commitment)
            if env_root is None:
                raise StrictGroundingError('root_binding_mismatch')
            work.marked = False
            for idx, candidate in enumerate(work.grounding['roots']):
                if candidate['provenance_assertion_id'] == root['provenance_assertion_id'] and candidate['source_registration_id'] == root['source_registration_id'] and (candidate['source_event_id'] == root['source_event_id']) and (candidate['record_locator'] == root['record_locator']):
                    work.used_roots.add(idx)
                    work.marked = True
                    break
            if not work.marked:
                raise StrictGroundingError('root_index')
        for env_root in work.env_roots:
            if not any((env_root.get('source_identity') == r['source_identity'] and env_root.get('record_locator') == r['record_locator'] and _hashes_equal(env_root.get('raw_record_sha256'), r['raw_blob_sha256']) and _hashes_equal(env_root.get('input_view_sha256'), r['view_blob_sha256']) for r in work.g_roots)):
                raise StrictGroundingError('envelope_root_unmatched')

def _vassert_p1_0_s1_else(work: SimpleNamespace) -> None:
    if work.g_roots:
        raise StrictGroundingError('root_binding_unexpected')
    if len(work.g_edges) != len(work.env_inputs):
        if len(work.g_edges) == 0:
            work.missing = True
        else:
            raise StrictGroundingError('edge_binding_count')
    if not work.missing:
        for edge in work.g_edges:
            env_in = _match_edge_to_envelope(edge, envelope=work.envelope, commitment=work.commitment)
            if env_in is None:
                raise StrictGroundingError('edge_binding_mismatch')
            work.marked = False
            for idx, candidate in enumerate(work.grounding['edges']):
                if candidate['child_provenance_assertion_id'] == edge['child_provenance_assertion_id'] and candidate['parent_provenance_assertion_id'] == edge['parent_provenance_assertion_id'] and (candidate['view_blob_sha256'] == edge['view_blob_sha256']):
                    work.used_edges.add(idx)
                    work.marked = True
                    break
            if not work.marked:
                raise StrictGroundingError('edge_index')
        for env_in in work.env_inputs:
            if not any((env_in.get('parent_assertion_id') == e['parent_provenance_assertion_id'] and _hashes_equal(env_in.get('parent_provenance_commitment'), e['parent_provenance_commitment']) and _hashes_equal(env_in.get('exact_input_view_sha256'), e['view_blob_sha256']) for e in work.g_edges)):
                raise StrictGroundingError('envelope_input_unmatched')

def _vassert_p1_0_s1(work: SimpleNamespace) -> None:
    if work.env_roots:
        _vassert_p1_0_s1_then(work)
    else:
        _vassert_p1_0_s1_else(work)

def _x_verify_assertion_grounding_p1_0(work: SimpleNamespace) -> None:
    _vassert_p1_0_s0(work)
    _vassert_p1_0_s1(work)

def _x_verify_assertion_grounding_p1_1(work: SimpleNamespace) -> None:
    work.outputs = [(idx, dict(o)) for idx, o in enumerate(work.grounding['outputs']) if o['provenance_assertion_id'] == work.assertion_id]
    work.selection = work.envelope.get('selection_parameters')
    work.output_sha = None

def _x_verify_assertion_grounding_p1_2(work: SimpleNamespace) -> None:
    if isinstance(work.selection, Mapping):
        work.output_sha = work.selection.get('output_sha256')
    if work.expected_source_payload_sha256 is not None:
        if work.output_sha != work.expected_source_payload_sha256:
            raise StrictGroundingError('source_payload_binding_mismatch')
    if len(work.outputs) > 1:
        raise StrictGroundingError('output_duplicate')

def _vassert_verify_assertion_grounding_p1(work: SimpleNamespace) -> None:

    _x_verify_assertion_grounding_p1_0(work)
    _x_verify_assertion_grounding_p1_1(work)
    _x_verify_assertion_grounding_p1_2(work)


def _vassert_verify_assertion_grounding_p2(work: SimpleNamespace) -> tuple[bool, str | None] | None:
    if len(work.outputs) == 0:
        work.missing = True
        work.output_binding = None
    else:
        idx, work.output_binding = work.outputs[0]
        work.used_outputs.add(idx)
        if not _hashes_equal(work.output_binding['provenance_commitment'], work.commitment):
            raise StrictGroundingError('output_commitment_mismatch')
        if work.output_sha is not None and (not _hashes_equal(work.output_binding['output_blob_sha256'], work.output_sha)):
            raise StrictGroundingError('output_blob_mismatch')
    if work.missing:
        return (False, None)
    work.binding_refs = [r['receipt_ref'] for r in work.g_roots] + [e['receipt_ref'] for e in work.g_edges]
    if not work.binding_refs:
        return (False, None)
    if len(set(work.binding_refs)) != 1:
        raise StrictGroundingError('receipt_ref_inconsistent')
    work.receipt_ref = work.binding_refs[0]
    work.receipt = work.receipt_by_ref.get(work.receipt_ref)
    if work.receipt is None:
        raise StrictGroundingError('receipt_dangling')
    return None

def _vassert_verify_assertion_grounding_p3(work: SimpleNamespace) -> None:
    work.used_receipts.add(work.receipt_ref)
    if work.receipt['provenance_assertion_id'] != work.assertion_id:
        raise StrictGroundingError('receipt_assertion_mismatch')
    if not _hashes_equal(work.receipt['provenance_commitment'], work.commitment):
        raise StrictGroundingError('receipt_commitment_mismatch')
    if work.g_roots:
        for root in work.g_roots:
            if root['source_registration_id'] != work.receipt['source_registration_id']:
                raise StrictGroundingError('receipt_source_registration_mismatch')
            if root['source_event_id'] != work.receipt['source_event_id']:
                raise StrictGroundingError('receipt_source_event_mismatch')
    elif work.g_edges:
        if not isinstance(work.receipt['source_registration_id'], str):
            raise StrictGroundingError('receipt_source_registration')
    work.expected_inputs = compute_input_bindings_sha256(work.g_roots, work.g_edges)
    work.expected_views = compute_submitted_views_sha256(work.g_roots, work.g_edges)
    if work.receipt['input_bindings_sha256'] != work.expected_inputs:
        raise StrictGroundingError('input_bindings_sha256_mismatch')
    if work.receipt['submitted_views_sha256'] != work.expected_views:
        raise StrictGroundingError('submitted_views_sha256_mismatch')

def _vassert_verify_assertion_grounding_p4(work: SimpleNamespace) -> tuple[bool, str | None]:
    if work.output_binding is None:
        raise StrictGroundingError('output_missing')
    if not _hashes_equal(work.receipt['returned_output_sha256'], work.output_binding['output_blob_sha256']):
        raise StrictGroundingError('returned_output_mismatch')
    work.artifact = work.envelope.get('transformer_artifact_sha256')
    work.recipe = work.envelope.get('transformer_recipe_sha256')
    if work.artifact is not None and (not _hashes_equal(work.receipt['transformer_artifact_sha256'], work.artifact)):
        raise StrictGroundingError('transformer_artifact_mismatch')
    if work.recipe is not None and (not _hashes_equal(work.receipt['recipe_sha256'], work.recipe)):
        raise StrictGroundingError('recipe_mismatch')
    if work.issuer_inventory is not None:
        authenticate_receipt(work.receipt, inventory_bytes=work.issuer_inventory, allowed_issuer_ids=work.allowed_issuer_ids, allowed_source_registration_ids=work.allowed_source_registration_ids, capture_issuers=work.capture_issuers)
    else:
        return (True, None)
    return (True, work.receipt['capture_class'])

def _verify_assertion_grounding(ctx: SimpleNamespace) -> tuple[bool, str | None]:
    """Return (complete_for_assertion, capture_class_or_None).

    Raises on contradictory supplied evidence. Returns complete=False when
    required witnesses are absent (missing evidence).
    """
    work = SimpleNamespace(
        grounding=ctx.grounding,
        envelope=ctx.envelope,
        receipt_by_ref=ctx.receipt_by_ref,
        issuer_inventory=ctx.issuer_inventory,
        allowed_issuer_ids=ctx.allowed_issuer_ids,
        allowed_source_registration_ids=ctx.allowed_source_registration_ids,
        capture_issuers=ctx.capture_issuers,
        expected_source_payload_sha256=ctx.expected_source_payload_sha256,
        used_roots=ctx.used_roots,
        used_edges=ctx.used_edges,
        used_outputs=ctx.used_outputs,
        used_receipts=ctx.used_receipts,
        schema_semantics=ctx.schema_semantics,
    )

    _vassert_verify_assertion_grounding_p0(work)
    _vassert_verify_assertion_grounding_p1(work)
    _out = _vassert_verify_assertion_grounding_p2(work)
    if _out is not None:
        return _out
    _vassert_verify_assertion_grounding_p3(work)
    return _vassert_verify_assertion_grounding_p4(work)



def merge_issuer_receipt_inventories(
    inventories: Sequence[Mapping[str, bytes]],
) -> dict[str, bytes]:
    """Merge protected inventories; duplicate receipt_ref or capture_id rejects."""

    merged: dict[str, bytes] = {}
    seen_capture_ids: set[str] = set()
    for inventory in inventories:
        if not isinstance(inventory, Mapping):
            raise StrictGroundingError("issuer_inventory_type")
        for ref, raw in inventory.items():
            if not isinstance(ref, str) or not ref.startswith("capture_"):
                raise StrictGroundingError("receipt_ref")
            if not isinstance(raw, (bytes, bytearray)):
                raise StrictGroundingError("receipt_inventory_bytes")
            exact = bytes(raw)
            if ref in merged:
                raise StrictGroundingError("receipt_ref_duplicate")
            try:
                obj = json.loads(exact.decode("utf-8"), object_pairs_hook=_reject_duplicate_keys)
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise StrictGroundingError("receipt_inventory_json") from exc
            validated = validate_receipt_object(obj)
            if receipt_ref_for(validated) != ref:
                raise StrictGroundingError("receipt_ref_mismatch")
            capture_id = validated["capture_id"]
            if capture_id in seen_capture_ids:
                raise StrictGroundingError("capture_id_duplicate")
            seen_capture_ids.add(capture_id)
            merged[ref] = exact
    return merged


def load_bound_issuer_inventories(
    capture_issuers: Sequence[CaptureIssuer],
) -> dict[str, bytes]:
    """Load each enrolled issuer receipt_root and merge under enrollment permissions."""

    if not isinstance(capture_issuers, Sequence):
        raise StrictGroundingError("capture_issuers_type")
    per_issuer: list[dict[str, bytes]] = []
    for issuer in capture_issuers:
        if not isinstance(issuer, CaptureIssuer):
            raise StrictGroundingError("capture_issuer_type")
        inventory = load_issuer_receipt_inventory(issuer.receipt_root)
        allowed_sources = set(issuer.source_registration_ids)
        for ref, raw in inventory.items():
            try:
                obj = json.loads(raw.decode("utf-8"), object_pairs_hook=_reject_duplicate_keys)
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise StrictGroundingError("receipt_inventory_json") from exc
            validated = validate_receipt_object(obj)
            if validated["capture_issuer_id"] != issuer.issuer_id:
                raise StrictGroundingError("receipt_issuer_unenrolled")
            if validated["capture_class"] != issuer.capture_class:
                raise StrictGroundingError("receipt_issuer_class_mismatch")
            if validated["source_registration_id"] not in allowed_sources:
                raise StrictGroundingError("receipt_source_unenrolled")
            if receipt_ref_for(validated) != ref:
                raise StrictGroundingError("receipt_ref_mismatch")
        per_issuer.append(inventory)
    return merge_issuer_receipt_inventories(per_issuer)


def _pctx_validate_provenance_context_p0(work: SimpleNamespace) -> None:
    if not isinstance(work.provenance_context, Mapping):
        raise StrictGroundingError('provenance_context_type')
    if set(work.provenance_context) != _PROVENANCE_CONTEXT_KEYS:
        raise StrictGroundingError('provenance_context_keys')
    if work.provenance_context.get('schema') != 'convmem.strict-provenance-context.v2':
        raise StrictGroundingError('provenance_context_schema')
    work.grounding_sha = work.provenance_context['grounding_sha256']
    if not isinstance(work.grounding_sha, str) or not _SHA_RE.fullmatch(work.grounding_sha):
        raise StrictGroundingError('grounding_sha256')
    if work.expected_grounding_sha256 is not None and work.grounding_sha != work.expected_grounding_sha256:
        raise StrictGroundingError('provenance_grounding_link')

def _pctx_validate_provenance_context_p1(work: SimpleNamespace) -> None:
    work.schema_semantics_out: list[dict[str, Any]] = []
    work.prev_sem_key: tuple[str, str] | None = None
    work.seen_sem: set[tuple[str, str]] = set()
    for entry in work.provenance_context['schema_semantics']:
        if not isinstance(entry, Mapping) or set(entry) != _SCHEMA_SEMANTICS_KEYS:
            raise StrictGroundingError('schema_semantics_keys')
        work.schema_version = entry['schema_version']
        work.binding_version = entry['binding_version']
        if not isinstance(work.schema_version, str) or not work.schema_version:
            raise StrictGroundingError('schema_version')
        if not isinstance(work.binding_version, str) or not work.binding_version:
            raise StrictGroundingError('binding_version')
        work.key = (work.schema_version, work.binding_version)
        if work.key in work.seen_sem:
            raise StrictGroundingError('schema_semantics_duplicate')
        work.seen_sem.add(work.key)
        if work.prev_sem_key is not None and work.key < work.prev_sem_key:
            raise StrictGroundingError('schema_semantics_unsorted')
        work.prev_sem_key = work.key
        work.raw = _b64_decode(entry['semantic_bytes_b64'])
        work.digest = sha256_digest(work.raw)
        if entry['semantic_sha256'] != work.digest:
            raise StrictGroundingError('schema_semantics_digest_mismatch')
        work.schema_semantics_out.append(dict(entry))
    work.policies_out: list[dict[str, Any]] = []
    work.prev_policy: str | None = None

def _pctx_p2_s0_item0(work: SimpleNamespace, policy) -> None:
    if not isinstance(policy, Mapping) or set(policy) != _POLICY_KEYS:
        raise StrictGroundingError('policy_keys')
    work.version = policy['policy_version']
    if not isinstance(work.version, str) or not work.version:
        raise StrictGroundingError('policy_version')
    if work.version in work.seen_policies:
        raise StrictGroundingError('policy_duplicate')
    work.seen_policies.add(work.version)
    if work.prev_policy is not None and work.version < work.prev_policy:
        raise StrictGroundingError('policies_unsorted')
    work.prev_policy = work.version
    work.policy_bytes = _b64_decode(policy['semantic_bytes_b64'])
    if policy['semantic_sha256'] != sha256_digest(work.policy_bytes):
        raise StrictGroundingError('policy_digest_mismatch')
    work.rules = policy['rules']
    if not isinstance(work.rules, list):
        raise StrictGroundingError('policy_rules_type')
    work.prev_rule_key: tuple[str, str, str, str] | None = None
    work.seen_rules: set[tuple[str, str, str, str]] = set()
    work.rules_out: list[dict[str, Any]] = []
    for rule in work.rules:
        if not isinstance(rule, Mapping) or set(rule) != _RULE_KEYS:
            raise StrictGroundingError('policy_rule_keys')
        for field in ('transformer_class', 'transformer_identity', 'transformer_version', 'recipe_id', 'cap'):
            if not isinstance(rule[field], str) or not rule[field]:
                raise StrictGroundingError(f'policy_rule_{field}')
        if rule['cap'] not in {'trusted', 'agent', 'untrusted'}:
            raise StrictGroundingError('policy_rule_cap')
        work.preservation = rule['preservation_contract']
        if work.preservation is not None and (not isinstance(work.preservation, str) or not work.preservation):
            raise StrictGroundingError('policy_rule_preservation_contract')
        work.artifact = rule['artifact_sha256']
        if work.artifact is not None:
            if not isinstance(work.artifact, str) or not _SHA_RE.fullmatch(work.artifact):
                raise StrictGroundingError('policy_rule_artifact_sha256')
        work.rule_key = (rule['transformer_class'], rule['transformer_identity'], rule['transformer_version'], rule['recipe_id'])
        if work.rule_key in work.seen_rules:
            raise StrictGroundingError('policy_rule_duplicate')
        work.seen_rules.add(work.rule_key)
        if work.prev_rule_key is not None and work.rule_key < work.prev_rule_key:
            raise StrictGroundingError('policy_rules_unsorted')
        work.prev_rule_key = work.rule_key
        work.rules_out.append(dict(rule))
    work.policies_out.append({'policy_version': work.version, 'semantic_bytes_b64': policy['semantic_bytes_b64'], 'semantic_sha256': policy['semantic_sha256'], 'rules': work.rules_out})

def _pctx_p2_s0(work: SimpleNamespace) -> None:
    work.seen_policies: set[str] = set()
    for policy in work.provenance_context['policies']:
        _pctx_p2_s0_item0(work, policy)
    work.recipes_out: list[dict[str, Any]] = []

def _pctx_p2_s1(work: SimpleNamespace) -> None:
    work.prev_recipe: str | None = None
    work.seen_recipes: set[str] = set()
    for recipe in work.provenance_context['recipes']:
        if not isinstance(recipe, Mapping) or set(recipe) != _RECIPE_KEYS:
            raise StrictGroundingError('recipe_keys')
        work.recipe_id = recipe['recipe_id']
        if not isinstance(work.recipe_id, str) or not work.recipe_id:
            raise StrictGroundingError('recipe_id')
        if work.recipe_id in work.seen_recipes:
            raise StrictGroundingError('recipe_duplicate')
        work.seen_recipes.add(work.recipe_id)
        if work.prev_recipe is not None and work.recipe_id < work.prev_recipe:
            raise StrictGroundingError('recipes_unsorted')
        work.prev_recipe = work.recipe_id
        work.recipe_bytes = _b64_decode(recipe['recipe_bytes_b64'])
        if recipe['recipe_sha256'] != sha256_digest(work.recipe_bytes):
            raise StrictGroundingError('recipe_digest_mismatch')
        work.recipes_out.append(dict(recipe))

def _pctx_validate_provenance_context_p2(work: SimpleNamespace) -> None:
    _pctx_p2_s0(work)
    _pctx_p2_s1(work)

def _pctx_validate_provenance_context_p3(work: SimpleNamespace) -> None:
    work.channels_out: list[dict[str, Any]] = []
    work.prev_channel: tuple[str, str, str, str] | None = None
    work.seen_channels: set[tuple[str, str, str, str]] = set()
    for channel in work.provenance_context['verified_channels']:
        if not isinstance(channel, Mapping) or set(channel) != _CHANNEL_KEYS:
            raise StrictGroundingError('channel_keys')
        for field in ('origin_class', 'channel_class', 'channel_locator'):
            if not isinstance(channel[field], str) or not channel[field]:
                raise StrictGroundingError(f'channel_{field}')
        work.evidence = channel['channel_evidence_sha256']
        if not isinstance(work.evidence, str) or not _SHA_RE.fullmatch(work.evidence):
            raise StrictGroundingError('channel_evidence_sha256')
        work.key = (channel['origin_class'], channel['channel_class'], channel['channel_locator'], work.evidence)
        if work.key in work.seen_channels:
            raise StrictGroundingError('channel_duplicate')
        work.seen_channels.add(work.key)
        if work.prev_channel is not None and work.key < work.prev_channel:
            raise StrictGroundingError('channels_unsorted')
        work.prev_channel = work.key
        work.channels_out.append(dict(channel))
    work.registered_raw = work.provenance_context['registered_assertions']
    if not isinstance(work.registered_raw, list):
        raise StrictGroundingError('registered_assertions_type')

def _pctx_validate_provenance_context_p4(work: SimpleNamespace) -> None:
    work.seen_assertion_ids: set[str] = set()
    work.prev_aid: str | None = None
    work.registered_out: list[dict[str, Any]] = []
    for entry in work.registered_raw:
        if not isinstance(entry, Mapping) or set(entry) != _REGISTERED_ASSERTION_KEYS:
            raise StrictGroundingError('registered_assertion_keys')
        work.assertion_id = entry['assertion_id']
        if not isinstance(work.assertion_id, str) or not work.assertion_id:
            raise StrictGroundingError('registered_assertion_id')
        if work.assertion_id in work.seen_assertion_ids:
            raise StrictGroundingError('registered_assertion_duplicate')
        work.seen_assertion_ids.add(work.assertion_id)
        if work.prev_aid is not None and work.assertion_id < work.prev_aid:
            raise StrictGroundingError('registered_assertions_unsorted')
        work.prev_aid = work.assertion_id
        work.envelope = entry['envelope']
        if not isinstance(work.envelope, Mapping):
            raise StrictGroundingError('registered_envelope_type')
        work.env_id = work.envelope.get('assertion_id')
        if work.env_id != work.assertion_id:
            raise StrictGroundingError('registered_assertion_id_mismatch')
        work.registered_out.append({'assertion_id': work.assertion_id, 'provenance_commitment': entry['provenance_commitment'], 'envelope': dict(work.envelope)})
    work.closed = {'schema': 'convmem.strict-provenance-context.v2', 'schema_semantics': work.schema_semantics_out, 'policies': work.policies_out, 'recipes': work.recipes_out, 'verified_channels': work.channels_out, 'registered_assertions': work.registered_out, 'grounding_sha256': work.grounding_sha, 'context_payload_sha256': work.provenance_context['context_payload_sha256']}
    work.payload = {k: v for k, v in work.closed.items() if k != 'context_payload_sha256'}

def _pctx_validate_provenance_context_p5(work: SimpleNamespace) -> dict[str, Any]:
    work.digest = sha256_digest(strict_canonical_bytes(work.payload))
    if work.provenance_context['context_payload_sha256'] != work.digest:
        raise StrictGroundingError('context_payload_mismatch')
    work.closed['context_payload_sha256'] = work.digest
    work.schema_map = {(e['schema_version'], e['binding_version']): _b64_decode(e['semantic_bytes_b64']) for e in work.schema_semantics_out}
    for entry in work.closed['registered_assertions']:
        work.recomputed = _envelope_commitment(entry['envelope'], schema_semantics=work.schema_map)
        work.claimed = entry['provenance_commitment']
        if not isinstance(work.claimed, str) or not _SHA_RE.fullmatch(work.claimed):
            raise StrictGroundingError('registered_provenance_commitment')
        if work.claimed != work.recomputed:
            raise StrictGroundingError('registered_commitment_mismatch')
    return work.closed

def validate_provenance_context(
    provenance_context: Mapping[str, Any], *, expected_grounding_sha256: str | None = None
) -> dict[str, Any]:
    """Validate closed provenance-context.v2 field sets, sort, and recomputed digests."""
    work = SimpleNamespace()
    work.expected_grounding_sha256 = expected_grounding_sha256
    work.provenance_context = provenance_context

    _pctx_validate_provenance_context_p0(work)
    _pctx_validate_provenance_context_p1(work)
    _pctx_validate_provenance_context_p2(work)
    _pctx_validate_provenance_context_p3(work)
    _pctx_validate_provenance_context_p4(work)
    return _pctx_validate_provenance_context_p5(work)



def reconstruct_provenance_registry(  # pylint: disable=W0212  # intentional registry rehydrate via private store surface
    provenance_context: Mapping[str, Any],
) -> tuple[ProvenanceRegistry, Mapping[tuple[str, str], bytes]]:
    """Build ProvenanceRegistry from a validated provenance-context inventory.

    Defaults are cleared so only context-fixed schema semantics, policies,
    recipes, channels, and assertions participate. Envelope content alone is
    never authority; missing parents remain incomplete under verify().
    """

    validated = validate_provenance_context(provenance_context)

    registry = ProvenanceRegistry()
    with registry._lock:  # noqa: SLF001 — reconstruct over empty context inventory
        registry._policies.clear()
        registry._recipes.clear()
        registry._schema_semantics.clear()
        registry._verified_channels.clear()
        registry._records.clear()
        registry._publish_snapshot()

    schema_map: dict[tuple[str, str], bytes] = {}
    for entry in validated["schema_semantics"]:
        raw = _b64_decode(entry["semantic_bytes_b64"])
        schema_map[(entry["schema_version"], entry["binding_version"])] = raw
        registry.register_schema_semantics(entry["schema_version"], entry["binding_version"], raw)

    for policy in validated["policies"]:
        rules: list[TransformerRule] = []
        for rule in policy["rules"]:
            artifact = rule["artifact_sha256"]
            artifact_bare = None if artifact is None else _bare_hex(artifact, field="artifact_sha256")
            rules.append(
                TransformerRule(
                    transformer_class=rule["transformer_class"],
                    transformer_identity=rule["transformer_identity"],
                    transformer_version=rule["transformer_version"],
                    recipe_id=rule["recipe_id"],
                    cap=rule["cap"],
                    preservation_contract=rule["preservation_contract"],
                    artifact_sha256=artifact_bare,
                )
            )
        registry.register_policy(
            policy["policy_version"],
            _b64_decode(policy["semantic_bytes_b64"]),
            rules=tuple(rules),
        )

    for recipe in validated["recipes"]:
        registry.register_recipe(recipe["recipe_id"], _b64_decode(recipe["recipe_bytes_b64"]))

    for channel in validated["verified_channels"]:
        registry._register_monitor_verified_channel(  # noqa: SLF001
            origin_class=channel["origin_class"],
            channel_class=channel["channel_class"],
            channel_locator=channel["channel_locator"],
            channel_evidence_sha256=_bare_hex(channel["channel_evidence_sha256"], field="channel_evidence_sha256"),
        )

    # Store assertions without requiring recursive verify at import time so a
    # missing parent yields incomplete (not silent overwrite). Duplicate IDs
    # already rejected during validate_provenance_context.
    for entry in validated["registered_assertions"]:
        registry._store_record(entry["envelope"], schema_semantics=schema_map)  # noqa: SLF001
        stored = registry.get(entry["assertion_id"])
        if stored is None:
            raise StrictGroundingError("registered_store_missing")
        expected = _bare_hex(entry["provenance_commitment"], field="registered_provenance_commitment")
        if stored.commitment != expected:
            raise StrictGroundingError("registered_commitment_mismatch")

    return registry, schema_map


def _derive_transformer_cap(
    envelope: Mapping[str, Any],
    *,
    registry: ProvenanceRegistry,
) -> str:
    """Derive transformer_cap from context-fixed policy/rule + envelope only.

    Callers cannot select or upgrade the cap. Receipt shape is never authority.
    """

    version = envelope.get("provenance_policy_version")
    if not isinstance(version, str) or not version:
        return "untrusted"
    try:
        with registry.pin() as pin:
            policy = pin.snapshot.policies.get(version)
        if policy is None:
            return "untrusted"
        return policy.transformer_cap(envelope)
    except Exception:  # noqa: BLE001  # pylint: disable=W0718  # fail-closed commitment/transformer boundary
        return "untrusted"


def _registered_ancestry_envelopes(
    assertion_id: str,
    registered_by_id: Mapping[str, Mapping[str, Any]],
) -> dict[str, Mapping[str, Any]]:
    """Full recursively registered ancestry closure for one assertion."""

    out: dict[str, Mapping[str, Any]] = {}
    stack = [assertion_id]
    seen: set[str] = set()
    while stack:
        current = stack.pop()
        if current in seen:
            continue
        seen.add(current)
        entry = registered_by_id.get(current)
        if entry is None:
            continue
        envelope = entry["envelope"]
        if not isinstance(envelope, Mapping):
            raise StrictGroundingError("registered_envelope_type")
        out[current] = envelope
        for binding in envelope.get("input_bindings") or []:
            if not isinstance(binding, Mapping):
                continue
            parent = binding.get("parent_assertion_id")
            if isinstance(parent, str) and parent:
                stack.append(parent)
    return out


def _assert_closed_document_coverage(
    *,
    grounding: Mapping[str, Any],
    envelopes: Mapping[str, Mapping[str, Any]],
    issuer_inventory: Mapping[str, bytes] | None,
    allowed_issuer_ids: set[str],
    allowed_source_registration_ids: set[str],
    capture_issuers: Sequence[CaptureIssuer] | None,
    schema_semantics: Mapping[tuple[str, str], bytes] | None,
) -> None:
    """Every supplied witness must match some registered assertion (no orphans).

    Does not collapse per-assertion qualification into one shared tuple — it only
    enforces closed-document coverage across the full registered inventory.
    """

    validated = validate_grounding_document(grounding)
    if issuer_inventory is not None:
        for receipt in validated["receipts"]:
            authenticate_receipt(
                receipt,
                inventory_bytes=issuer_inventory,
                allowed_issuer_ids=allowed_issuer_ids,
                allowed_source_registration_ids=allowed_source_registration_ids,
                capture_issuers=capture_issuers,
            )

    receipt_by_ref = _receipt_index(validated)
    used_roots: set[int] = set()
    used_edges: set[int] = set()
    used_outputs: set[int] = set()
    used_receipts: set[str] = set()

    for env in envelopes.values():
        _verify_assertion_grounding(SimpleNamespace(
            grounding=validated,
            envelope=env,
            receipt_by_ref=receipt_by_ref,
            issuer_inventory=issuer_inventory,
            allowed_issuer_ids=allowed_issuer_ids,
            allowed_source_registration_ids=allowed_source_registration_ids,
            capture_issuers=capture_issuers,
            expected_source_payload_sha256=None,
            used_roots=used_roots,
            used_edges=used_edges,
            used_outputs=used_outputs,
            used_receipts=used_receipts,
            schema_semantics=schema_semantics,
        ))

    if len(used_roots) != len(validated["roots"]):
        raise StrictGroundingError("root_unused")
    if len(used_edges) != len(validated["edges"]):
        raise StrictGroundingError("edge_unused")
    if len(used_outputs) != len(validated["outputs"]):
        raise StrictGroundingError("output_unused")
    if len(used_receipts) != len(validated["receipts"]):
        raise StrictGroundingError("receipt_unused")


def qualify_assertions(
    *,
    grounding: Mapping[str, Any] | None,
    provenance_context: Mapping[str, Any],
    issuer_inventory: Mapping[str, bytes] | None = None,
    allowed_issuer_ids: set[str] | None = None,
    allowed_source_registration_ids: set[str] | None = None,
    capture_issuers: Sequence[CaptureIssuer] | None = None,
    original_qualifications: Mapping[str, Mapping[str, str]] | None = None,
    require_complete: bool = False,
) -> dict[str, QualificationTuple]:
    """Freeze one QualificationTuple per registered assertion at admission context.

    Does not copy one aggregate tuple onto every record. Homogeneous capture is
    enforced per assertion ancestry closure; late evidence cannot upgrade a frozen
    original. transformer_cap is derived from context-fixed policy only.
    """

    validated_ctx = validate_provenance_context(provenance_context)
    registry, schema_map = reconstruct_provenance_registry(validated_ctx)
    registered_by_id = {entry["assertion_id"]: entry for entry in validated_ctx["registered_assertions"]}
    originals = original_qualifications or {}

    allowed_issuers = allowed_issuer_ids or set()
    allowed_sources = allowed_source_registration_ids or set()
    if capture_issuers is not None:
        allowed_issuers = allowed_issuers | {i.issuer_id for i in capture_issuers}
        allowed_sources = allowed_sources | {sid for i in capture_issuers for sid in i.source_registration_ids}

    if grounding is not None:
        _assert_closed_document_coverage(
            grounding=grounding,
            envelopes={aid: e["envelope"] for aid, e in registered_by_id.items()},
            issuer_inventory=issuer_inventory,
            allowed_issuer_ids=allowed_issuers,
            allowed_source_registration_ids=allowed_sources,
            capture_issuers=capture_issuers,
            schema_semantics=schema_map,
        )

    out: dict[str, QualificationTuple] = {}
    for entry in validated_ctx["registered_assertions"]:
        assertion_id = entry["assertion_id"]
        ancestry = _registered_ancestry_envelopes(assertion_id, registered_by_id)
        derived_cap = _derive_transformer_cap(entry["envelope"], registry=registry)
        out[assertion_id] = qualify_grounding(
            grounding=grounding,
            envelope=entry["envelope"],
            envelopes=ancestry,
            issuer_inventory=issuer_inventory,
            allowed_issuer_ids=allowed_issuer_ids,
            allowed_source_registration_ids=allowed_source_registration_ids,
            capture_issuers=capture_issuers,
            transformer_cap=derived_cap,
            require_complete=require_complete,
            original_qualification=originals.get(assertion_id),
            registry=registry,
            schema_semantics=schema_map,
            orphan_check=False,
        )
    return out


def _qground_p0_s0(work: SimpleNamespace) -> QualificationTuple | None:
    if work.original_qualification is not None:
        work.frozen = QualificationTuple(commitments=str(work.original_qualification['commitments']), byte_grounding=str(work.original_qualification['byte_grounding']), capture=str(work.original_qualification['capture']), transformer_cap=str(work.original_qualification['transformer_cap']))
        work.recomputed = qualify_grounding(grounding=work.grounding, envelope=work.envelope, envelopes=work.envelopes, issuer_inventory=work.issuer_inventory, allowed_issuer_ids=work.allowed_issuer_ids, allowed_source_registration_ids=work.allowed_source_registration_ids, capture_issuers=work.capture_issuers, expected_source_payload_sha256=work.expected_source_payload_sha256, transformer_cap=work.transformer_cap, require_complete=False, original_qualification=None, registry=work.registry, schema_semantics=work.schema_semantics, orphan_check=work.orphan_check)
        work.order_commitments = {'incomplete': 0, 'valid': 1}
        work.order_bytes = {'missing': 0, 'complete': 1}
        work.order_capture = {'unattested': 0, 'synthetic_fixture': 1, 'controlled_capture': 1}
        work.order_cap = {'untrusted': 0, 'agent': 1, 'trusted': 2}
        work.upgraded = work.order_commitments[work.recomputed.commitments] > work.order_commitments[work.frozen.commitments] or work.order_bytes[work.recomputed.byte_grounding] > work.order_bytes[work.frozen.byte_grounding] or work.order_capture[work.recomputed.capture] > work.order_capture[work.frozen.capture] or (work.order_cap[work.recomputed.transformer_cap] > work.order_cap[work.frozen.transformer_cap])
        if work.upgraded:
            return work.frozen
        if work.recomputed != work.frozen:
            raise StrictGroundingError('qualification_immutable')
        return work.frozen
    if work.registry is not None and work.envelope is not None:
        work.cap = _derive_transformer_cap(work.envelope, registry=work.registry)
    else:
        work.cap = work.transformer_cap if work.transformer_cap in {'trusted', 'agent', 'untrusted'} else 'untrusted'
    work.envelope_map: dict[str, Mapping[str, Any]] = {}
    if work.envelopes:
        for key, value in work.envelopes.items():
            if not isinstance(key, str) or not isinstance(value, Mapping):
                raise StrictGroundingError('envelopes_type')
            if key in work.envelope_map:
                raise StrictGroundingError('envelopes_duplicate')
            work.envelope_map[key] = value

def _qground_p0_s1(work: SimpleNamespace) -> None:
    if work.envelope is not None:
        work.aid = work.envelope.get('assertion_id')
        if not isinstance(work.aid, str) or not work.aid:
            raise StrictGroundingError('envelope_assertion_id')
        work.envelope_map[work.aid] = work.envelope
    work.commitments = 'incomplete'
    if work.envelope_map:
        work.statuses = [verify_legacy_commitments(envelope=env, registry=work.registry, schema_semantics=work.schema_semantics) for env in work.envelope_map.values()]
        work.commitments = 'valid' if work.statuses and all((s == 'valid' for s in work.statuses)) else 'incomplete'
        if work.expected_source_payload_sha256 is not None and work.envelope is not None:
            work.selection = work.envelope.get('selection_parameters')
            if not isinstance(work.selection, Mapping):
                raise StrictGroundingError('envelope_selection_missing')
            if not _hashes_equal(work.selection.get('output_sha256'), work.expected_source_payload_sha256):
                raise StrictGroundingError('source_payload_binding_mismatch')
    return None

def _qground_qualify_grounding_p0(work: SimpleNamespace) -> QualificationTuple | None:
    _out = _qground_p0_s0(work)
    if _out is not None:
        return _out
    _qground_p0_s1(work)
    return None

def _qground_qualify_grounding_p1(work: SimpleNamespace) -> QualificationTuple | None:
    work.byte_grounding = 'missing'
    work.capture = 'unattested'
    if work.grounding is None:
        work.result = QualificationTuple(work.commitments, work.byte_grounding, work.capture, work.cap)
        if work.require_complete and (work.result.commitments != 'valid' or work.result.byte_grounding != 'complete' or work.result.capture == 'unattested'):
            raise StrictGroundingError('qualification_incomplete')
        return work.result
    work.validated = validate_grounding_document(work.grounding)
    work.allowed_issuers = work.allowed_issuer_ids or set()
    work.allowed_sources = work.allowed_source_registration_ids or set()
    if work.capture_issuers is not None:
        work.allowed_issuers = work.allowed_issuers | {i.issuer_id for i in work.capture_issuers}
        work.allowed_sources = work.allowed_sources | {sid for i in work.capture_issuers for sid in i.source_registration_ids}
    work.receipt_by_ref = _receipt_index(work.validated)
    return None

def _qground_qualify_grounding_p2(work: SimpleNamespace) -> QualificationTuple | None:
    if work.issuer_inventory is not None:
        for receipt in work.validated['receipts']:
            authenticate_receipt(receipt, inventory_bytes=work.issuer_inventory, allowed_issuer_ids=work.allowed_issuers, allowed_source_registration_ids=work.allowed_sources, capture_issuers=work.capture_issuers)
    if not work.envelope_map:
        work.result = QualificationTuple(work.commitments, 'missing', 'unattested', work.cap)
        if work.require_complete:
            raise StrictGroundingError('qualification_incomplete')
        return work.result
    work.used_roots: set[int] = set()
    work.used_edges: set[int] = set()
    work.used_outputs: set[int] = set()
    work.used_receipts: set[str] = set()
    work.capture_classes: set[str] = set()
    return None

def _qground_qualify_grounding_p3(work: SimpleNamespace) -> QualificationTuple:
    work.all_complete = True
    for _assertion_id, env in work.envelope_map.items():
        work.complete, work.capture_class = _verify_assertion_grounding(SimpleNamespace(grounding=work.validated, envelope=env, receipt_by_ref=work.receipt_by_ref, issuer_inventory=work.issuer_inventory, allowed_issuer_ids=work.allowed_issuers, allowed_source_registration_ids=work.allowed_sources, capture_issuers=work.capture_issuers, expected_source_payload_sha256=work.expected_source_payload_sha256 if env is work.envelope else None, used_roots=work.used_roots, used_edges=work.used_edges, used_outputs=work.used_outputs, used_receipts=work.used_receipts, schema_semantics=work.schema_semantics))
        if not work.complete:
            work.all_complete = False
        if work.capture_class is not None:
            work.capture_classes.add(work.capture_class)
    if work.orphan_check:
        if len(work.used_roots) != len(work.validated['roots']):
            raise StrictGroundingError('root_unused')
        if len(work.used_edges) != len(work.validated['edges']):
            raise StrictGroundingError('edge_unused')
        if len(work.used_outputs) != len(work.validated['outputs']):
            raise StrictGroundingError('output_unused')
        if len(work.used_receipts) != len(work.validated['receipts']):
            raise StrictGroundingError('receipt_unused')
    if work.all_complete and work.commitments == 'valid':
        work.byte_grounding = 'complete'
    else:
        work.byte_grounding = 'missing'
    if work.issuer_inventory is None:
        work.capture = 'unattested'
    elif work.all_complete and work.commitments == 'valid' and (len(work.capture_classes) == 1):
        work.capture = next(iter(work.capture_classes))
    elif work.all_complete and work.capture_classes and (len(work.capture_classes) != 1):
        raise StrictGroundingError('capture_ancestry_mixed')
    else:
        work.capture = 'unattested'
    work.result = QualificationTuple(work.commitments, work.byte_grounding, work.capture, work.cap)
    if work.require_complete and (work.result.commitments != 'valid' or work.result.byte_grounding != 'complete' or work.result.capture == 'unattested'):
        raise StrictGroundingError('qualification_incomplete')
    return work.result

def qualify_grounding(  # pylint: disable=R0913  # frozen public grounding qualification signature
    *,
    grounding: Mapping[str, Any] | None,
    envelope: Mapping[str, Any] | None = None,
    envelopes: Mapping[str, Mapping[str, Any]] | None = None,
    issuer_inventory: Mapping[str, bytes] | None = None,
    allowed_issuer_ids: set[str] | None = None,
    allowed_source_registration_ids: set[str] | None = None,
    capture_issuers: Sequence[CaptureIssuer] | None = None,
    expected_source_payload_sha256: str | None = None,
    transformer_cap: str = "untrusted",
    require_complete: bool = False,
    original_qualification: Mapping[str, str] | None = None,
    registry: ProvenanceRegistry | None = None,
    schema_semantics: Mapping[tuple[str, str], bytes] | None = None,
    orphan_check: bool = True,
) -> QualificationTuple:
    """Compose legacy verification with byte/capture grounding.

    Missing evidence weakens only where the parent allows. Contradictory supplied
    evidence rejects. Original admission qualification is immutable; late evidence
    never upgrades it. When a reconstructed registry is supplied, transformer_cap
    is derived from that context-fixed policy and the focus envelope — callers
    cannot upgrade it.
    """
    work = SimpleNamespace()
    work.allowed_issuer_ids = allowed_issuer_ids
    work.allowed_source_registration_ids = allowed_source_registration_ids
    work.capture_issuers = capture_issuers
    work.envelope = envelope
    work.envelopes = envelopes
    work.expected_source_payload_sha256 = expected_source_payload_sha256
    work.grounding = grounding
    work.issuer_inventory = issuer_inventory
    work.original_qualification = original_qualification
    work.orphan_check = orphan_check
    work.registry = registry
    work.require_complete = require_complete
    work.schema_semantics = schema_semantics
    work.transformer_cap = transformer_cap

    _out = _qground_qualify_grounding_p0(work)
    if _out is not None:
        return _out
    _out = _qground_qualify_grounding_p1(work)
    if _out is not None:
        return _out
    _out = _qground_qualify_grounding_p2(work)
    if _out is not None:
        return _out
    return _qground_qualify_grounding_p3(work)



def grounding_entry_hash(kind: str, entry: Mapping[str, Any]) -> str:
    """Tagged hash for added_grounding_refs."""

    if kind not in {"blob", "root", "edge", "output", "receipt"}:
        raise StrictGroundingError("grounding_entry_kind")
    if not isinstance(entry, Mapping):
        raise StrictGroundingError("grounding_entry_type")
    return sha256_digest(strict_canonical_bytes({"kind": kind, "entry": dict(entry)}))


_GROUNDING_KIND_ARRAYS: tuple[tuple[str, str], ...] = (
    ("blob", "blobs"),
    ("root", "roots"),
    ("edge", "edges"),
    ("output", "outputs"),
    ("receipt", "receipts"),
)


def grounding_ref_set(grounding: Mapping[str, Any]) -> dict[str, bytes]:
    """Map tagged grounding-ref digest -> exact canonical entry bytes."""

    validated = validate_grounding_document(grounding)
    out: dict[str, bytes] = {}
    for kind, array_name in _GROUNDING_KIND_ARRAYS:
        for entry in validated[array_name]:
            ref = grounding_entry_hash(kind, entry)
            raw = strict_canonical_bytes(dict(entry))
            if ref in out and out[ref] != raw:
                raise StrictGroundingError("grounding_ref_collision")
            out[ref] = raw
    return out


def assert_cumulative_grounding(
    parent: Mapping[str, Any] | None,
    child: Mapping[str, Any],
) -> None:
    """Child must retain every parent grounding entry byte-for-byte (append-only)."""

    if parent is None:
        validate_grounding_document(child)
        return
    parent_refs = grounding_ref_set(parent)
    child_refs = grounding_ref_set(child)
    for ref, raw in parent_refs.items():
        if ref not in child_refs:
            raise StrictGroundingError("grounding_cumulative_deleted")
        if child_refs[ref] != raw:
            raise StrictGroundingError("grounding_cumulative_mutated")


def _entry_canonical_map(
    entries: Sequence[Any], *, key_fields: Sequence[str], label: str
) -> dict[tuple[Any, ...], bytes]:
    out: dict[tuple[Any, ...], bytes] = {}
    for entry in entries:
        if not isinstance(entry, Mapping):
            raise StrictGroundingError(f"{label}_entry_type")
        key = tuple(entry[f] for f in key_fields)
        raw = strict_canonical_bytes(dict(entry))
        if key in out:
            raise StrictGroundingError(f"{label}_duplicate")
        out[key] = raw
    return out


def assert_cumulative_provenance_context(
    parent: Mapping[str, Any] | None,
    child: Mapping[str, Any],
) -> None:
    """Child context inventories must retain every parent entry byte-for-byte."""

    child_closed = validate_provenance_context(child)
    if parent is None:
        return
    parent_closed = validate_provenance_context(parent)
    checks: tuple[tuple[str, Sequence[str]], ...] = (
        ("schema_semantics", ("schema_version", "binding_version")),
        ("policies", ("policy_version",)),
        ("recipes", ("recipe_id",)),
        (
            "verified_channels",
            (
                "origin_class",
                "channel_class",
                "channel_locator",
                "channel_evidence_sha256",
            ),
        ),
        ("registered_assertions", ("assertion_id",)),
    )
    for array_name, key_fields in checks:
        parent_map = _entry_canonical_map(parent_closed[array_name], key_fields=key_fields, label=array_name)
        child_map = _entry_canonical_map(child_closed[array_name], key_fields=key_fields, label=array_name)
        for key, raw in parent_map.items():
            if key not in child_map:
                raise StrictGroundingError(f"{array_name}_cumulative_deleted")
            if child_map[key] != raw:
                raise StrictGroundingError(f"{array_name}_cumulative_mutated")


def compute_added_grounding_refs(
    parent: Mapping[str, Any] | None,
    child: Mapping[str, Any],
) -> list[str]:
    """Sorted unique set-difference of tagged grounding entry hashes."""

    child_refs = set(grounding_ref_set(child))
    parent_refs = set(grounding_ref_set(parent)) if parent is not None else set()
    added = sorted(child_refs - parent_refs)
    return added


def compute_added_provenance_ids(
    parent: Mapping[str, Any] | None,
    child: Mapping[str, Any],
) -> list[str]:
    """Sorted unique envelope UUID set-difference (not all registered IDs)."""

    child_closed = validate_provenance_context(child)
    child_ids = {e["assertion_id"] for e in child_closed["registered_assertions"]}
    if parent is None:
        return sorted(child_ids)
    parent_closed = validate_provenance_context(parent)
    parent_ids = {e["assertion_id"] for e in parent_closed["registered_assertions"]}
    return sorted(child_ids - parent_ids)


__all__ = [
    "QualificationTuple",
    "StrictGroundingError",
    "assert_cumulative_grounding",
    "assert_cumulative_provenance_context",
    "authenticate_receipt",
    "compute_added_grounding_refs",
    "compute_added_provenance_ids",
    "compute_input_bindings_sha256",
    "compute_submitted_views_sha256",
    "derive_origin_assurance",
    "derive_provenance_basis",
    "grounding_entry_hash",
    "grounding_ref_set",
    "load_bound_issuer_inventories",
    "load_issuer_receipt_inventory",
    "merge_issuer_receipt_inventories",
    "qualify_assertions",
    "qualify_grounding",
    "receipt_ref_for",
    "reconstruct_provenance_registry",
    "strict_canonical_bytes",
    "tagged_bindings_for_hash",
    "validate_grounding_document",
    "validate_provenance_context",
    "validate_receipt_object",
    "verify_legacy_commitments",
]

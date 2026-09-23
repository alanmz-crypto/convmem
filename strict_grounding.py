"""Strict grounding, capture-receipt authentication, and qualification (T1)."""

from __future__ import annotations

import base64
import json
import re
from dataclasses import dataclass
from pathlib import Path
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
_REGISTERED_ASSERTION_KEYS = frozenset(
    {"assertion_id", "provenance_commitment", "envelope"}
)


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


def strict_canonical_bytes(value: Any) -> bytes:
    def _validate(obj: Any) -> None:
        _reject_floats(obj)

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
        if not (0 <= start <= end <= input_length):
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


def validate_grounding_document(grounding: Mapping[str, Any]) -> dict[str, Any]:
    required = {
        "schema",
        "blobs",
        "roots",
        "edges",
        "outputs",
        "receipts",
        "grounding_payload_sha256",
    }
    if set(grounding) != required:
        raise StrictGroundingError("grounding_keys")
    if grounding["schema"] != "convmem.strict-grounding.v1":
        raise StrictGroundingError("grounding_schema")
    blobs = grounding["blobs"]
    roots = grounding["roots"]
    edges = grounding["edges"]
    outputs = grounding["outputs"]
    receipts = grounding["receipts"]
    if not all(isinstance(x, list) for x in (blobs, roots, edges, outputs, receipts)):
        raise StrictGroundingError("grounding_arrays")

    blob_map: dict[str, bytes] = {}
    decoded_total = 0
    prev_hash = ""
    for blob in blobs:
        if not isinstance(blob, Mapping) or set(blob) != {"sha256", "length", "bytes_b64"}:
            raise StrictGroundingError("blob_keys")
        digest = blob["sha256"]
        if not isinstance(digest, str) or not _SHA_RE.fullmatch(digest):
            raise StrictGroundingError("blob_sha")
        if prev_hash and digest < prev_hash:
            raise StrictGroundingError("blobs_unsorted")
        if digest == prev_hash:
            raise StrictGroundingError("blobs_duplicate")
        prev_hash = digest
        raw = _b64_decode(blob["bytes_b64"])
        if blob["length"] != len(raw):
            raise StrictGroundingError("blob_length")
        if sha256_digest(raw) != digest:
            raise StrictGroundingError("blob_digest_mismatch")
        decoded_total += len(raw)
        if decoded_total > _MAX_BLOB_DECODED:
            raise StrictGroundingError("blob_budget")
        blob_map[digest] = raw

    def _sort_check(items: list[Any], key_fn) -> None:
        keys = [key_fn(item) for item in items]
        if len(keys) != len(set(keys)):
            raise StrictGroundingError("grounding_duplicate_key")
        if keys != sorted(keys):
            raise StrictGroundingError("grounding_sort")

    _sort_check(roots, _root_sort_key)
    _sort_check(edges, _edge_sort_key)
    _sort_check(outputs, lambda o: o["provenance_assertion_id"])
    _sort_check(receipts, lambda r: r["capture_id"])

    referenced_blobs: set[str] = set()
    for root in roots:
        if not isinstance(root, Mapping) or set(root) != _ROOT_KEYS:
            raise StrictGroundingError("root_keys")
        for field in (
            "provenance_assertion_id",
            "source_registration_id",
            "source_event_id",
            "source_identity",
            "record_locator",
            "receipt_ref",
        ):
            if not isinstance(root[field], str) or not root[field]:
                raise StrictGroundingError(f"root_{field}")
        for field in ("provenance_commitment", "raw_blob_sha256", "view_blob_sha256"):
            if not isinstance(root[field], str) or not _SHA_RE.fullmatch(root[field]):
                raise StrictGroundingError(f"root_{field}")
        raw_sha = root["raw_blob_sha256"]
        view_sha = root["view_blob_sha256"]
        if raw_sha not in blob_map or view_sha not in blob_map:
            raise StrictGroundingError("root_blob_missing")
        referenced_blobs.add(raw_sha)
        referenced_blobs.add(view_sha)
        _validate_selector(root["selector"], input_length=len(blob_map[raw_sha]))
        view = _apply_selector(blob_map[raw_sha], root["selector"])
        if sha256_digest(view) != view_sha:
            raise StrictGroundingError("root_view_mismatch")
        if blob_map[view_sha] != view:
            raise StrictGroundingError("root_view_bytes_mismatch")

    for edge in edges:
        if not isinstance(edge, Mapping) or set(edge) != _EDGE_KEYS:
            raise StrictGroundingError("edge_keys")
        for field in (
            "child_provenance_assertion_id",
            "parent_provenance_assertion_id",
            "receipt_ref",
        ):
            if not isinstance(edge[field], str) or not edge[field]:
                raise StrictGroundingError(f"edge_{field}")
        for field in (
            "child_provenance_commitment",
            "parent_provenance_commitment",
            "parent_output_blob_sha256",
            "view_blob_sha256",
        ):
            if not isinstance(edge[field], str) or not _SHA_RE.fullmatch(edge[field]):
                raise StrictGroundingError(f"edge_{field}")
        parent_out = edge["parent_output_blob_sha256"]
        view_sha = edge["view_blob_sha256"]
        if parent_out not in blob_map or view_sha not in blob_map:
            raise StrictGroundingError("edge_blob_missing")
        referenced_blobs.add(parent_out)
        referenced_blobs.add(view_sha)
        _validate_selector(edge["selector"], input_length=len(blob_map[parent_out]))
        view = _apply_selector(blob_map[parent_out], edge["selector"])
        if sha256_digest(view) != view_sha:
            raise StrictGroundingError("edge_view_mismatch")
        if blob_map[view_sha] != view:
            raise StrictGroundingError("edge_view_bytes_mismatch")

    for output in outputs:
        if not isinstance(output, Mapping) or set(output) != _OUTPUT_KEYS:
            raise StrictGroundingError("output_keys")
        if not isinstance(output["provenance_assertion_id"], str) or not output["provenance_assertion_id"]:
            raise StrictGroundingError("output_assertion")
        for field in ("provenance_commitment", "output_blob_sha256"):
            if not isinstance(output[field], str) or not _SHA_RE.fullmatch(output[field]):
                raise StrictGroundingError(f"output_{field}")
        if output["output_blob_sha256"] not in blob_map:
            raise StrictGroundingError("output_blob_missing")
        referenced_blobs.add(output["output_blob_sha256"])

    receipt_refs: dict[str, dict[str, Any]] = {}
    for receipt in receipts:
        validated = validate_receipt_object(receipt)
        ref = receipt_ref_for(validated)
        if ref in receipt_refs:
            raise StrictGroundingError("receipt_ref_reused")
        receipt_refs[ref] = validated

    unused_blobs = set(blob_map) - referenced_blobs
    if unused_blobs:
        raise StrictGroundingError("blob_unused")

    payload = {k: v for k, v in grounding.items() if k != "grounding_payload_sha256"}
    digest = sha256_digest(strict_canonical_bytes(payload))
    if grounding["grounding_payload_sha256"] != digest:
        raise StrictGroundingError("grounding_payload_mismatch")
    return dict(grounding)


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
        commitment = legacy_provenance_commitment(
            validated, schema_semantics=schema_semantics
        )
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
    except Exception:  # noqa: BLE001
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
        digest = legacy_provenance_commitment(
            envelope, schema_semantics=schema_semantics
        )
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
        [
            dict(e)
            for e in grounding["edges"]
            if e["child_provenance_assertion_id"] == assertion_id
        ],
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
            and _hashes_equal(
                env_in.get("exact_input_view_sha256"), edge["view_blob_sha256"]
            )
        ):
            return env_in
    return None


def _receipt_index(grounding: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for receipt in grounding["receipts"]:
        validated = validate_receipt_object(receipt)
        out[receipt_ref_for(validated)] = validated
    return out


def _verify_assertion_grounding(
    *,
    grounding: Mapping[str, Any],
    envelope: Mapping[str, Any],
    receipt_by_ref: dict[str, dict[str, Any]],
    issuer_inventory: Mapping[str, bytes] | None,
    allowed_issuer_ids: set[str],
    allowed_source_registration_ids: set[str],
    capture_issuers: Sequence[CaptureIssuer] | None,
    expected_source_payload_sha256: str | None,
    used_roots: set[int],
    used_edges: set[int],
    used_outputs: set[int],
    used_receipts: set[str],
    schema_semantics: Mapping[tuple[str, str], bytes] | None = None,
) -> tuple[bool, str | None]:
    """Return (complete_for_assertion, capture_class_or_None).

    Raises on contradictory supplied evidence. Returns complete=False when
    required witnesses are absent (missing evidence).
    """

    assertion_id = envelope.get("assertion_id")
    if not isinstance(assertion_id, str) or not assertion_id:
        raise StrictGroundingError("envelope_assertion_id")
    commitment = _envelope_commitment(envelope, schema_semantics=schema_semantics)

    env_roots = list(envelope.get("root_bindings") or [])
    env_inputs = list(envelope.get("input_bindings") or [])
    if bool(env_roots) == bool(env_inputs):
        raise StrictGroundingError("envelope_binding_family")

    g_roots, g_edges = _bindings_for_assertion(grounding, assertion_id)

    missing = False

    if env_roots:
        if len(g_roots) != len(env_roots):
            if len(g_roots) == 0:
                missing = True
            else:
                raise StrictGroundingError("root_binding_count")
        if not missing:
            for root in g_roots:
                env_root = _match_root_to_envelope(
                    root, envelope=envelope, commitment=commitment
                )
                if env_root is None:
                    raise StrictGroundingError("root_binding_mismatch")
                marked = False
                for idx, candidate in enumerate(grounding["roots"]):
                    if (
                        candidate["provenance_assertion_id"]
                        == root["provenance_assertion_id"]
                        and candidate["source_registration_id"]
                        == root["source_registration_id"]
                        and candidate["source_event_id"] == root["source_event_id"]
                        and candidate["record_locator"] == root["record_locator"]
                    ):
                        used_roots.add(idx)
                        marked = True
                        break
                if not marked:
                    raise StrictGroundingError("root_index")
            for env_root in env_roots:
                if not any(
                    env_root.get("source_identity") == r["source_identity"]
                    and env_root.get("record_locator") == r["record_locator"]
                    and _hashes_equal(env_root.get("raw_record_sha256"), r["raw_blob_sha256"])
                    and _hashes_equal(env_root.get("input_view_sha256"), r["view_blob_sha256"])
                    for r in g_roots
                ):
                    raise StrictGroundingError("envelope_root_unmatched")
    else:
        if g_roots:
            raise StrictGroundingError("root_binding_unexpected")
        if len(g_edges) != len(env_inputs):
            if len(g_edges) == 0:
                missing = True
            else:
                raise StrictGroundingError("edge_binding_count")
        if not missing:
            for edge in g_edges:
                env_in = _match_edge_to_envelope(
                    edge, envelope=envelope, commitment=commitment
                )
                if env_in is None:
                    raise StrictGroundingError("edge_binding_mismatch")
                marked = False
                for idx, candidate in enumerate(grounding["edges"]):
                    if (
                        candidate["child_provenance_assertion_id"]
                        == edge["child_provenance_assertion_id"]
                        and candidate["parent_provenance_assertion_id"]
                        == edge["parent_provenance_assertion_id"]
                        and candidate["view_blob_sha256"] == edge["view_blob_sha256"]
                    ):
                        used_edges.add(idx)
                        marked = True
                        break
                if not marked:
                    raise StrictGroundingError("edge_index")
            for env_in in env_inputs:
                if not any(
                    env_in.get("parent_assertion_id")
                    == e["parent_provenance_assertion_id"]
                    and _hashes_equal(
                        env_in.get("parent_provenance_commitment"),
                        e["parent_provenance_commitment"],
                    )
                    and _hashes_equal(
                        env_in.get("exact_input_view_sha256"), e["view_blob_sha256"]
                    )
                    for e in g_edges
                ):
                    raise StrictGroundingError("envelope_input_unmatched")

    # Unique output binding
    outputs = [
        (idx, dict(o))
        for idx, o in enumerate(grounding["outputs"])
        if o["provenance_assertion_id"] == assertion_id
    ]
    selection = envelope.get("selection_parameters")
    output_sha = None
    if isinstance(selection, Mapping):
        output_sha = selection.get("output_sha256")
    if expected_source_payload_sha256 is not None:
        if output_sha != expected_source_payload_sha256:
            raise StrictGroundingError("source_payload_binding_mismatch")
    if len(outputs) > 1:
        raise StrictGroundingError("output_duplicate")
    if len(outputs) == 0:
        missing = True
        output_binding = None
    else:
        idx, output_binding = outputs[0]
        used_outputs.add(idx)
        if not _hashes_equal(output_binding["provenance_commitment"], commitment):
            raise StrictGroundingError("output_commitment_mismatch")
        if output_sha is not None and not _hashes_equal(
            output_binding["output_blob_sha256"], output_sha
        ):
            raise StrictGroundingError("output_blob_mismatch")

    if missing:
        return False, None

    # One receipt per assertion; all bindings share it.
    binding_refs = [r["receipt_ref"] for r in g_roots] + [e["receipt_ref"] for e in g_edges]
    if not binding_refs:
        return False, None
    if len(set(binding_refs)) != 1:
        raise StrictGroundingError("receipt_ref_inconsistent")
    receipt_ref = binding_refs[0]
    receipt = receipt_by_ref.get(receipt_ref)
    if receipt is None:
        raise StrictGroundingError("receipt_dangling")
    used_receipts.add(receipt_ref)

    if receipt["provenance_assertion_id"] != assertion_id:
        raise StrictGroundingError("receipt_assertion_mismatch")
    if not _hashes_equal(receipt["provenance_commitment"], commitment):
        raise StrictGroundingError("receipt_commitment_mismatch")

    # Source registration/event/identity/locator continuity via roots + receipt.
    if g_roots:
        for root in g_roots:
            if root["source_registration_id"] != receipt["source_registration_id"]:
                raise StrictGroundingError("receipt_source_registration_mismatch")
            if root["source_event_id"] != receipt["source_event_id"]:
                raise StrictGroundingError("receipt_source_event_mismatch")
    elif g_edges:
        # Edge path: receipt source fields must still be enrolled/consistent.
        if not isinstance(receipt["source_registration_id"], str):
            raise StrictGroundingError("receipt_source_registration")

    expected_inputs = compute_input_bindings_sha256(g_roots, g_edges)
    expected_views = compute_submitted_views_sha256(g_roots, g_edges)
    if receipt["input_bindings_sha256"] != expected_inputs:
        raise StrictGroundingError("input_bindings_sha256_mismatch")
    if receipt["submitted_views_sha256"] != expected_views:
        raise StrictGroundingError("submitted_views_sha256_mismatch")

    if output_binding is None:
        raise StrictGroundingError("output_missing")
    if not _hashes_equal(
        receipt["returned_output_sha256"], output_binding["output_blob_sha256"]
    ):
        raise StrictGroundingError("returned_output_mismatch")

    artifact = envelope.get("transformer_artifact_sha256")
    recipe = envelope.get("transformer_recipe_sha256")
    if artifact is not None and not _hashes_equal(
        receipt["transformer_artifact_sha256"], artifact
    ):
        raise StrictGroundingError("transformer_artifact_mismatch")
    if recipe is not None and not _hashes_equal(receipt["recipe_sha256"], recipe):
        raise StrictGroundingError("recipe_mismatch")

    if issuer_inventory is not None:
        authenticate_receipt(
            receipt,
            inventory_bytes=issuer_inventory,
            allowed_issuer_ids=allowed_issuer_ids,
            allowed_source_registration_ids=allowed_source_registration_ids,
            capture_issuers=capture_issuers,
        )
    else:
        # Missing inventory weakens capture authentication; do not accept class.
        return True, None

    return True, receipt["capture_class"]


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
                obj = json.loads(
                    exact.decode("utf-8"), object_pairs_hook=_reject_duplicate_keys
                )
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
                obj = json.loads(
                    raw.decode("utf-8"), object_pairs_hook=_reject_duplicate_keys
                )
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


def validate_provenance_context(
    provenance_context: Mapping[str, Any],
    *,
    expected_grounding_sha256: str | None = None,
) -> dict[str, Any]:
    """Validate closed provenance-context.v2 field sets, sort, and recomputed digests."""

    if not isinstance(provenance_context, Mapping):
        raise StrictGroundingError("provenance_context_type")
    if set(provenance_context) != _PROVENANCE_CONTEXT_KEYS:
        raise StrictGroundingError("provenance_context_keys")
    if provenance_context.get("schema") != "convmem.strict-provenance-context.v2":
        raise StrictGroundingError("provenance_context_schema")

    grounding_sha = provenance_context["grounding_sha256"]
    if not isinstance(grounding_sha, str) or not _SHA_RE.fullmatch(grounding_sha):
        raise StrictGroundingError("grounding_sha256")
    if expected_grounding_sha256 is not None and grounding_sha != expected_grounding_sha256:
        raise StrictGroundingError("provenance_grounding_link")

    schema_semantics_out: list[dict[str, Any]] = []
    prev_sem_key: tuple[str, str] | None = None
    seen_sem: set[tuple[str, str]] = set()
    for entry in provenance_context["schema_semantics"]:
        if not isinstance(entry, Mapping) or set(entry) != _SCHEMA_SEMANTICS_KEYS:
            raise StrictGroundingError("schema_semantics_keys")
        schema_version = entry["schema_version"]
        binding_version = entry["binding_version"]
        if not isinstance(schema_version, str) or not schema_version:
            raise StrictGroundingError("schema_version")
        if not isinstance(binding_version, str) or not binding_version:
            raise StrictGroundingError("binding_version")
        key = (schema_version, binding_version)
        if key in seen_sem:
            raise StrictGroundingError("schema_semantics_duplicate")
        seen_sem.add(key)
        if prev_sem_key is not None and key < prev_sem_key:
            raise StrictGroundingError("schema_semantics_unsorted")
        prev_sem_key = key
        raw = _b64_decode(entry["semantic_bytes_b64"])
        digest = sha256_digest(raw)
        if entry["semantic_sha256"] != digest:
            raise StrictGroundingError("schema_semantics_digest_mismatch")
        schema_semantics_out.append(dict(entry))

    policies_out: list[dict[str, Any]] = []
    prev_policy: str | None = None
    seen_policies: set[str] = set()
    for policy in provenance_context["policies"]:
        if not isinstance(policy, Mapping) or set(policy) != _POLICY_KEYS:
            raise StrictGroundingError("policy_keys")
        version = policy["policy_version"]
        if not isinstance(version, str) or not version:
            raise StrictGroundingError("policy_version")
        if version in seen_policies:
            raise StrictGroundingError("policy_duplicate")
        seen_policies.add(version)
        if prev_policy is not None and version < prev_policy:
            raise StrictGroundingError("policies_unsorted")
        prev_policy = version
        policy_bytes = _b64_decode(policy["semantic_bytes_b64"])
        if policy["semantic_sha256"] != sha256_digest(policy_bytes):
            raise StrictGroundingError("policy_digest_mismatch")
        rules = policy["rules"]
        if not isinstance(rules, list):
            raise StrictGroundingError("policy_rules_type")
        prev_rule_key: tuple[str, str, str, str] | None = None
        seen_rules: set[tuple[str, str, str, str]] = set()
        rules_out: list[dict[str, Any]] = []
        for rule in rules:
            if not isinstance(rule, Mapping) or set(rule) != _RULE_KEYS:
                raise StrictGroundingError("policy_rule_keys")
            for field in (
                "transformer_class",
                "transformer_identity",
                "transformer_version",
                "recipe_id",
                "cap",
            ):
                if not isinstance(rule[field], str) or not rule[field]:
                    raise StrictGroundingError(f"policy_rule_{field}")
            if rule["cap"] not in {"trusted", "agent", "untrusted"}:
                raise StrictGroundingError("policy_rule_cap")
            preservation = rule["preservation_contract"]
            if preservation is not None and (
                not isinstance(preservation, str) or not preservation
            ):
                raise StrictGroundingError("policy_rule_preservation_contract")
            artifact = rule["artifact_sha256"]
            if artifact is not None:
                if not isinstance(artifact, str) or not _SHA_RE.fullmatch(artifact):
                    raise StrictGroundingError("policy_rule_artifact_sha256")
            rule_key = (
                rule["transformer_class"],
                rule["transformer_identity"],
                rule["transformer_version"],
                rule["recipe_id"],
            )
            if rule_key in seen_rules:
                raise StrictGroundingError("policy_rule_duplicate")
            seen_rules.add(rule_key)
            if prev_rule_key is not None and rule_key < prev_rule_key:
                raise StrictGroundingError("policy_rules_unsorted")
            prev_rule_key = rule_key
            rules_out.append(dict(rule))
        policies_out.append(
            {
                "policy_version": version,
                "semantic_bytes_b64": policy["semantic_bytes_b64"],
                "semantic_sha256": policy["semantic_sha256"],
                "rules": rules_out,
            }
        )

    recipes_out: list[dict[str, Any]] = []
    prev_recipe: str | None = None
    seen_recipes: set[str] = set()
    for recipe in provenance_context["recipes"]:
        if not isinstance(recipe, Mapping) or set(recipe) != _RECIPE_KEYS:
            raise StrictGroundingError("recipe_keys")
        recipe_id = recipe["recipe_id"]
        if not isinstance(recipe_id, str) or not recipe_id:
            raise StrictGroundingError("recipe_id")
        if recipe_id in seen_recipes:
            raise StrictGroundingError("recipe_duplicate")
        seen_recipes.add(recipe_id)
        if prev_recipe is not None and recipe_id < prev_recipe:
            raise StrictGroundingError("recipes_unsorted")
        prev_recipe = recipe_id
        recipe_bytes = _b64_decode(recipe["recipe_bytes_b64"])
        if recipe["recipe_sha256"] != sha256_digest(recipe_bytes):
            raise StrictGroundingError("recipe_digest_mismatch")
        recipes_out.append(dict(recipe))

    channels_out: list[dict[str, Any]] = []
    prev_channel: tuple[str, str, str, str] | None = None
    seen_channels: set[tuple[str, str, str, str]] = set()
    for channel in provenance_context["verified_channels"]:
        if not isinstance(channel, Mapping) or set(channel) != _CHANNEL_KEYS:
            raise StrictGroundingError("channel_keys")
        for field in ("origin_class", "channel_class", "channel_locator"):
            if not isinstance(channel[field], str) or not channel[field]:
                raise StrictGroundingError(f"channel_{field}")
        evidence = channel["channel_evidence_sha256"]
        if not isinstance(evidence, str) or not _SHA_RE.fullmatch(evidence):
            raise StrictGroundingError("channel_evidence_sha256")
        key = (
            channel["origin_class"],
            channel["channel_class"],
            channel["channel_locator"],
            evidence,
        )
        if key in seen_channels:
            raise StrictGroundingError("channel_duplicate")
        seen_channels.add(key)
        if prev_channel is not None and key < prev_channel:
            raise StrictGroundingError("channels_unsorted")
        prev_channel = key
        channels_out.append(dict(channel))

    registered_raw = provenance_context["registered_assertions"]
    if not isinstance(registered_raw, list):
        raise StrictGroundingError("registered_assertions_type")
    seen_assertion_ids: set[str] = set()
    prev_aid: str | None = None
    registered_out: list[dict[str, Any]] = []
    for entry in registered_raw:
        if not isinstance(entry, Mapping) or set(entry) != _REGISTERED_ASSERTION_KEYS:
            raise StrictGroundingError("registered_assertion_keys")
        assertion_id = entry["assertion_id"]
        if not isinstance(assertion_id, str) or not assertion_id:
            raise StrictGroundingError("registered_assertion_id")
        if assertion_id in seen_assertion_ids:
            raise StrictGroundingError("registered_assertion_duplicate")
        seen_assertion_ids.add(assertion_id)
        if prev_aid is not None and assertion_id < prev_aid:
            raise StrictGroundingError("registered_assertions_unsorted")
        prev_aid = assertion_id
        envelope = entry["envelope"]
        if not isinstance(envelope, Mapping):
            raise StrictGroundingError("registered_envelope_type")
        env_id = envelope.get("assertion_id")
        if env_id != assertion_id:
            raise StrictGroundingError("registered_assertion_id_mismatch")
        registered_out.append(
            {
                "assertion_id": assertion_id,
                "provenance_commitment": entry["provenance_commitment"],
                "envelope": dict(envelope),
            }
        )

    closed = {
        "schema": "convmem.strict-provenance-context.v2",
        "schema_semantics": schema_semantics_out,
        "policies": policies_out,
        "recipes": recipes_out,
        "verified_channels": channels_out,
        "registered_assertions": registered_out,
        "grounding_sha256": grounding_sha,
        "context_payload_sha256": provenance_context["context_payload_sha256"],
    }
    payload = {k: v for k, v in closed.items() if k != "context_payload_sha256"}
    digest = sha256_digest(strict_canonical_bytes(payload))
    if provenance_context["context_payload_sha256"] != digest:
        raise StrictGroundingError("context_payload_mismatch")
    closed["context_payload_sha256"] = digest

    # Recompute entry commitments against context-fixed schema semantics only.
    schema_map = {
        (e["schema_version"], e["binding_version"]): _b64_decode(e["semantic_bytes_b64"])
        for e in schema_semantics_out
    }
    for entry in closed["registered_assertions"]:
        recomputed = _envelope_commitment(
            entry["envelope"], schema_semantics=schema_map
        )
        claimed = entry["provenance_commitment"]
        # v2 provenance-context digest fields are labeled sha256 values. Do not
        # normalize a bare registered commitment — that would return an object
        # whose context hash no longer matches its bytes.
        if not isinstance(claimed, str) or not _SHA_RE.fullmatch(claimed):
            raise StrictGroundingError("registered_provenance_commitment")
        if claimed != recomputed:
            raise StrictGroundingError("registered_commitment_mismatch")
    return closed


def reconstruct_provenance_registry(
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
        registry.register_schema_semantics(
            entry["schema_version"], entry["binding_version"], raw
        )

    for policy in validated["policies"]:
        rules: list[TransformerRule] = []
        for rule in policy["rules"]:
            artifact = rule["artifact_sha256"]
            artifact_bare = (
                None if artifact is None else _bare_hex(artifact, field="artifact_sha256")
            )
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
        registry.register_recipe(
            recipe["recipe_id"], _b64_decode(recipe["recipe_bytes_b64"])
        )

    for channel in validated["verified_channels"]:
        registry._register_monitor_verified_channel(  # noqa: SLF001
            origin_class=channel["origin_class"],
            channel_class=channel["channel_class"],
            channel_locator=channel["channel_locator"],
            channel_evidence_sha256=_bare_hex(
                channel["channel_evidence_sha256"], field="channel_evidence_sha256"
            ),
        )

    # Store assertions without requiring recursive verify at import time so a
    # missing parent yields incomplete (not silent overwrite). Duplicate IDs
    # already rejected during validate_provenance_context.
    for entry in validated["registered_assertions"]:
        registry._store_record(  # noqa: SLF001
            entry["envelope"], schema_semantics=schema_map
        )
        stored = registry.get(entry["assertion_id"])
        if stored is None:
            raise StrictGroundingError("registered_store_missing")
        expected = _bare_hex(
            entry["provenance_commitment"], field="registered_provenance_commitment"
        )
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
    except Exception:  # noqa: BLE001
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
        _verify_assertion_grounding(
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
        )

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
    registered_by_id = {
        entry["assertion_id"]: entry for entry in validated_ctx["registered_assertions"]
    }
    originals = original_qualifications or {}

    allowed_issuers = allowed_issuer_ids or set()
    allowed_sources = allowed_source_registration_ids or set()
    if capture_issuers is not None:
        allowed_issuers = allowed_issuers | {i.issuer_id for i in capture_issuers}
        allowed_sources = allowed_sources | {
            sid for i in capture_issuers for sid in i.source_registration_ids
        }

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


def qualify_grounding(
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

    if original_qualification is not None:
        frozen = QualificationTuple(
            commitments=str(original_qualification["commitments"]),
            byte_grounding=str(original_qualification["byte_grounding"]),
            capture=str(original_qualification["capture"]),
            transformer_cap=str(original_qualification["transformer_cap"]),
        )
        recomputed = qualify_grounding(
            grounding=grounding,
            envelope=envelope,
            envelopes=envelopes,
            issuer_inventory=issuer_inventory,
            allowed_issuer_ids=allowed_issuer_ids,
            allowed_source_registration_ids=allowed_source_registration_ids,
            capture_issuers=capture_issuers,
            expected_source_payload_sha256=expected_source_payload_sha256,
            transformer_cap=transformer_cap,
            require_complete=False,
            original_qualification=None,
            registry=registry,
            schema_semantics=schema_semantics,
            orphan_check=orphan_check,
        )
        order_commitments = {"incomplete": 0, "valid": 1}
        order_bytes = {"missing": 0, "complete": 1}
        order_capture = {"unattested": 0, "synthetic_fixture": 1, "controlled_capture": 1}
        order_cap = {"untrusted": 0, "agent": 1, "trusted": 2}
        upgraded = (
            order_commitments[recomputed.commitments] > order_commitments[frozen.commitments]
            or order_bytes[recomputed.byte_grounding] > order_bytes[frozen.byte_grounding]
            or order_capture[recomputed.capture] > order_capture[frozen.capture]
            or order_cap[recomputed.transformer_cap] > order_cap[frozen.transformer_cap]
        )
        if upgraded:
            return frozen
        if recomputed != frozen:
            # Cold disappearance/drift fails qualification; history is not downgraded.
            raise StrictGroundingError("qualification_immutable")
        return frozen

    if registry is not None and envelope is not None:
        cap = _derive_transformer_cap(envelope, registry=registry)
    else:
        cap = (
            transformer_cap
            if transformer_cap in {"trusted", "agent", "untrusted"}
            else "untrusted"
        )

    envelope_map: dict[str, Mapping[str, Any]] = {}
    if envelopes:
        for key, value in envelopes.items():
            if not isinstance(key, str) or not isinstance(value, Mapping):
                raise StrictGroundingError("envelopes_type")
            if key in envelope_map:
                raise StrictGroundingError("envelopes_duplicate")
            envelope_map[key] = value
    if envelope is not None:
        aid = envelope.get("assertion_id")
        if not isinstance(aid, str) or not aid:
            raise StrictGroundingError("envelope_assertion_id")
        # Ancestry maps intentionally include the focus assertion; overlay is
        # identity, not a duplicate registration.
        envelope_map[aid] = envelope

    commitments = "incomplete"
    if envelope_map:
        statuses = [
            verify_legacy_commitments(
                envelope=env,
                registry=registry,
                schema_semantics=schema_semantics,
            )
            for env in envelope_map.values()
        ]
        commitments = "valid" if statuses and all(s == "valid" for s in statuses) else "incomplete"
        if expected_source_payload_sha256 is not None and envelope is not None:
            selection = envelope.get("selection_parameters")
            if not isinstance(selection, Mapping):
                raise StrictGroundingError("envelope_selection_missing")
            if not _hashes_equal(
                selection.get("output_sha256"), expected_source_payload_sha256
            ):
                raise StrictGroundingError("source_payload_binding_mismatch")

    byte_grounding = "missing"
    capture = "unattested"

    if grounding is None:
        result = QualificationTuple(commitments, byte_grounding, capture, cap)
        if require_complete and (
            result.commitments != "valid"
            or result.byte_grounding != "complete"
            or result.capture == "unattested"
        ):
            raise StrictGroundingError("qualification_incomplete")
        return result

    validated = validate_grounding_document(grounding)
    allowed_issuers = allowed_issuer_ids or set()
    allowed_sources = allowed_source_registration_ids or set()
    if capture_issuers is not None:
        allowed_issuers = allowed_issuers | {i.issuer_id for i in capture_issuers}
        allowed_sources = allowed_sources | {
            sid for i in capture_issuers for sid in i.source_registration_ids
        }

    receipt_by_ref = _receipt_index(validated)

    # Authenticate every included receipt when inventory is supplied. A
    # receipt-shaped object is never self-authenticating.
    if issuer_inventory is not None:
        for receipt in validated["receipts"]:
            authenticate_receipt(
                receipt,
                inventory_bytes=issuer_inventory,
                allowed_issuer_ids=allowed_issuers,
                allowed_source_registration_ids=allowed_sources,
                capture_issuers=capture_issuers,
            )

    if not envelope_map:
        # Closed grounding object alone cannot establish envelope matching.
        result = QualificationTuple(commitments, "missing", "unattested", cap)
        if require_complete:
            raise StrictGroundingError("qualification_incomplete")
        return result

    used_roots: set[int] = set()
    used_edges: set[int] = set()
    used_outputs: set[int] = set()
    used_receipts: set[str] = set()
    capture_classes: set[str] = set()
    all_complete = True

    for assertion_id, env in envelope_map.items():
        complete, capture_class = _verify_assertion_grounding(
            grounding=validated,
            envelope=env,
            receipt_by_ref=receipt_by_ref,
            issuer_inventory=issuer_inventory,
            allowed_issuer_ids=allowed_issuers,
            allowed_source_registration_ids=allowed_sources,
            capture_issuers=capture_issuers,
            expected_source_payload_sha256=(
                expected_source_payload_sha256 if env is envelope else None
            ),
            used_roots=used_roots,
            used_edges=used_edges,
            used_outputs=used_outputs,
            used_receipts=used_receipts,
            schema_semantics=schema_semantics,
        )
        if not complete:
            all_complete = False
        if capture_class is not None:
            capture_classes.add(capture_class)

    if orphan_check:
        # Reject dangling / unused / orphan witness claims against the closed object.
        if len(used_roots) != len(validated["roots"]):
            raise StrictGroundingError("root_unused")
        if len(used_edges) != len(validated["edges"]):
            raise StrictGroundingError("edge_unused")
        if len(used_outputs) != len(validated["outputs"]):
            raise StrictGroundingError("output_unused")
        if len(used_receipts) != len(validated["receipts"]):
            raise StrictGroundingError("receipt_unused")

    if all_complete and commitments == "valid":
        byte_grounding = "complete"
    else:
        byte_grounding = "missing"

    # Capture stays unattested unless byte ancestry is complete, legacy
    # commitments are valid, and exactly one authenticated class is present.
    # Absent registered parents yield incomplete commitments and must not
    # advertise a capture class from the child's witnesses alone.
    if issuer_inventory is None:
        capture = "unattested"
    elif (
        all_complete
        and commitments == "valid"
        and len(capture_classes) == 1
    ):
        capture = next(iter(capture_classes))
    elif all_complete and capture_classes and len(capture_classes) != 1:
        raise StrictGroundingError("capture_ancestry_mixed")
    else:
        capture = "unattested"

    result = QualificationTuple(commitments, byte_grounding, capture, cap)
    if require_complete and (
        result.commitments != "valid"
        or result.byte_grounding != "complete"
        or result.capture == "unattested"
    ):
        raise StrictGroundingError("qualification_incomplete")
    return result


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
        parent_map = _entry_canonical_map(
            parent_closed[array_name], key_fields=key_fields, label=array_name
        )
        child_map = _entry_canonical_map(
            child_closed[array_name], key_fields=key_fields, label=array_name
        )
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

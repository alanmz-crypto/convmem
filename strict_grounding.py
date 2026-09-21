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
    duplicate receipt_ref / capture_id rows.
    """

    root = Path(receipt_root)
    if not root.is_absolute() or root.is_symlink() or not root.is_dir():
        raise StrictGroundingError("receipt_root_invalid")
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
) -> str:
    """Return valid|incomplete for legacy envelope verification (never upgrades alone)."""

    try:
        validate_envelope(envelope)
        commitment = legacy_provenance_commitment(envelope)
        if registry is not None:
            pin = getattr(registry, "active_pin", None)
            if pin is None:
                return "incomplete"
        return "valid" if commitment else "incomplete"
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


def _envelope_commitment(envelope: Mapping[str, Any]) -> str | None:
    try:
        return _labeled_hash(legacy_provenance_commitment(envelope))
    except Exception:  # noqa: BLE001
        return _labeled_hash(envelope.get("provenance_commitment"))


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
) -> tuple[bool, str | None]:
    """Return (complete_for_assertion, capture_class_or_None).

    Raises on contradictory supplied evidence. Returns complete=False when
    required witnesses are absent (missing evidence).
    """

    assertion_id = envelope.get("assertion_id")
    if not isinstance(assertion_id, str) or not assertion_id:
        raise StrictGroundingError("envelope_assertion_id")
    commitment = _envelope_commitment(envelope)
    if commitment is None:
        raise StrictGroundingError("envelope_commitment")

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
) -> QualificationTuple:
    """Compose legacy verification with byte/capture grounding.

    Missing evidence weakens only where the parent allows. Contradictory supplied
    evidence rejects. Original admission qualification is immutable; late evidence
    never upgrades it.
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

    cap = transformer_cap if transformer_cap in {"trusted", "agent", "untrusted"} else "untrusted"

    envelope_map: dict[str, Mapping[str, Any]] = {}
    if envelopes:
        for key, value in envelopes.items():
            if not isinstance(key, str) or not isinstance(value, Mapping):
                raise StrictGroundingError("envelopes_type")
            envelope_map[key] = value
    if envelope is not None:
        aid = envelope.get("assertion_id")
        if not isinstance(aid, str) or not aid:
            raise StrictGroundingError("envelope_assertion_id")
        envelope_map[aid] = envelope

    commitments = "incomplete"
    if envelope_map:
        statuses = [
            verify_legacy_commitments(envelope=env) for env in envelope_map.values()
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
        )
        if not complete:
            all_complete = False
        if capture_class is not None:
            capture_classes.add(capture_class)

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

    if issuer_inventory is None:
        capture = "unattested"
    elif not capture_classes:
        capture = "unattested"
    elif len(capture_classes) != 1:
        raise StrictGroundingError("capture_ancestry_mixed")
    else:
        capture = next(iter(capture_classes))

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

    return sha256_digest(strict_canonical_bytes({"kind": kind, "entry": dict(entry)}))


__all__ = [
    "QualificationTuple",
    "StrictGroundingError",
    "authenticate_receipt",
    "compute_input_bindings_sha256",
    "compute_submitted_views_sha256",
    "derive_origin_assurance",
    "derive_provenance_basis",
    "grounding_entry_hash",
    "load_issuer_receipt_inventory",
    "qualify_grounding",
    "receipt_ref_for",
    "strict_canonical_bytes",
    "tagged_bindings_for_hash",
    "validate_grounding_document",
    "validate_receipt_object",
    "verify_legacy_commitments",
]

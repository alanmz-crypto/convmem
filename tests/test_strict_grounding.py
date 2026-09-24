"""M3/T1 adversarial coverage for strict grounding and receipt authenticity."""
# pylint: disable=C0302  # preserved grounding collected-node test boundary

from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path

import pytest

from bound_read_scope import CaptureIssuer, sha256_digest
from provenance import (
    BINDING_VERSION,
    POLICY_VERSION,
    SCHEMA_SEMANTICS_BYTES,
    SCHEMA_SEMANTICS_SHA256,
    SCHEMA_VERSION,
    ProvenanceRegistry,
    base_envelope,
    provenance_commitment,
    root_binding,
)
from strict_grounding import (
    QualificationTuple,
    StrictGroundingError,
    authenticate_receipt,
    compute_input_bindings_sha256,
    compute_submitted_views_sha256,
    load_bound_issuer_inventories,
    load_issuer_receipt_inventory,
    merge_issuer_receipt_inventories,
    qualify_assertions,
    qualify_grounding,
    receipt_ref_for,
    reconstruct_provenance_registry,
    strict_canonical_bytes,
    validate_grounding_document,
    validate_provenance_context,
)

# ---------------------------------------------------------------------------
# Capability smoke (collection-safe at T0a)
# ---------------------------------------------------------------------------


def test_strict_grounding_capability_present():
    spec = importlib.util.find_spec("strict_grounding")
    assert spec is not None, "[T1] module strict_grounding absent"
    module = importlib.import_module("strict_grounding")
    assert hasattr(module, "qualify_grounding"), (
        "[T1] strict_grounding.qualify_grounding capability absent"
    )


# ---------------------------------------------------------------------------
# Helpers — self-consistent mini fixtures (not the mixed pin specimen)
# ---------------------------------------------------------------------------

_AID = "00000000-0000-4000-8000-000000000001"
_BLOB = b"test"
_BLOB_HEX = sha256_digest(_BLOB).removeprefix("sha256:")
_BLOB_SHA = "sha256:" + _BLOB_HEX  # labeled form used by strict grounding
_BLOB_B64 = "dGVzdA=="
# Same digest base_envelope defaults and _default_context_materials register.
_ROOT_RECIPE_SHA256 = sha256_digest(b"convmem:root-recipe-v1")
_TS = "2026-09-21T00:00:00Z"
_SRC = "src-reg-1"
_EVT = "evt_451b0b154430f2ef494001c177744e32b191c9344aff96a3b1fbd0d609cee204"
_ISSUER = "fixture-issuer"
_CAPTURE_ID = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"


def _envelope_root() -> dict:
    return base_envelope(
        assertion_id=_AID,
        root_bindings=[
            root_binding(
                source_identity="fixture/source-a",
                record_locator="event-1",
                raw_record_sha256=_BLOB_HEX,
                input_view_sha256=_BLOB_HEX,
            )
        ],
        transformer_artifact_sha256=_BLOB_HEX,
        selection_parameters={"output_sha256": _BLOB_HEX},
        producer_class="agent",
        producer_assurance="claimed",
    )


def _root_binding(receipt_ref: str, commitment: str) -> dict:
    return {
        "provenance_assertion_id": _AID,
        "provenance_commitment": commitment,
        "source_registration_id": _SRC,
        "source_event_id": _EVT,
        "source_identity": "fixture/source-a",
        "record_locator": "event-1",
        "raw_blob_sha256": _BLOB_SHA,
        "view_blob_sha256": _BLOB_SHA,
        "selector": {"kind": "identity"},
        "receipt_ref": receipt_ref,
    }


def _output_binding(commitment: str) -> dict:
    return {
        "provenance_assertion_id": _AID,
        "provenance_commitment": commitment,
        "output_blob_sha256": _BLOB_SHA,
    }


def _make_receipt(
    *,
    commitment: str,
    roots: list[dict],
    edges: list[dict] | None = None,
    capture_class: str = "synthetic_fixture",
    capture_id: str = _CAPTURE_ID,
    issuer_id: str = _ISSUER,
    assertion_id: str = _AID,
) -> dict:
    edges = edges or []
    receipt = {
        "schema": "convmem.capture-receipt.v1",
        "capture_id": capture_id,
        "capture_class": capture_class,
        "capture_issuer_id": issuer_id,
        "source_registration_id": _SRC,
        "source_event_id": _EVT,
        "provenance_assertion_id": assertion_id,
        "provenance_commitment": commitment,
        "input_bindings_sha256": compute_input_bindings_sha256(roots, edges),
        "transformer_artifact_sha256": _BLOB_SHA,
        "recipe_sha256": _ROOT_RECIPE_SHA256,
        "submitted_views_sha256": compute_submitted_views_sha256(roots, edges),
        "returned_output_sha256": _BLOB_SHA,
        "captured_at": _TS,
        "receipt_payload_sha256": "sha256:" + ("0" * 64),
    }
    payload = {k: v for k, v in receipt.items() if k != "receipt_payload_sha256"}
    receipt["receipt_payload_sha256"] = sha256_digest(strict_canonical_bytes(payload))
    return receipt


def _closed_grounding(env: dict) -> tuple[dict, dict, str]:
    commitment = "sha256:" + provenance_commitment(env)
    root = _root_binding("capture_" + ("0" * 64), commitment)
    receipt = _make_receipt(commitment=commitment, roots=[root])
    ref = receipt_ref_for(receipt)
    root["receipt_ref"] = ref
    receipt = _make_receipt(commitment=commitment, roots=[root])
    ref = receipt_ref_for(receipt)
    root["receipt_ref"] = ref

    grounding = {
        "schema": "convmem.strict-grounding.v1",
        "blobs": [{"sha256": _BLOB_SHA, "length": len(_BLOB), "bytes_b64": _BLOB_B64}],
        "roots": [root],
        "edges": [],
        "outputs": [_output_binding(commitment)],
        "receipts": [receipt],
        "grounding_payload_sha256": "sha256:" + ("0" * 64),
    }
    payload = {k: v for k, v in grounding.items() if k != "grounding_payload_sha256"}
    grounding["grounding_payload_sha256"] = sha256_digest(strict_canonical_bytes(payload))
    return grounding, receipt, ref


def _write_inventory(tmp_path: Path, receipt: dict, *, exact: bytes | None = None) -> Path:
    root = tmp_path / "issuer_inventory"
    root.mkdir()
    path = root / f"{receipt['capture_id']}.json"
    raw = exact if exact is not None else strict_canonical_bytes(receipt)
    path.write_bytes(raw)
    os.chmod(path, 0o444)
    os.chmod(root, 0o555)
    return root


def _issuer() -> CaptureIssuer:
    return CaptureIssuer(
        issuer_id=_ISSUER,
        capture_class="synthetic_fixture",
        enrollment_sha256=_BLOB_SHA,
        receipt_root="/var/lib/convmem/receipts/fixture-issuer",
        source_registration_ids=(_SRC,),
    )


# ---------------------------------------------------------------------------
# Pin-compatible binding hash shape
# ---------------------------------------------------------------------------


def test_input_bindings_sha256_matches_pinned_known_answer():
    pin_dir = (
        Path(__file__).resolve().parent
        / "fixtures"
        / "openclaw_strict"
        / "protocol_fixture"
        / "pin_bytes"
    )
    tagged = json.loads((pin_dir / "input_bindings.json").read_bytes().decode("utf-8"))
    roots = [row["binding"] for row in tagged if row["kind"] == "root"]
    edges = [row["binding"] for row in tagged if row["kind"] == "edge"]
    recomputed = compute_input_bindings_sha256(roots, edges)
    assert recomputed == (
        "sha256:c9634e7a395ebcc35206781b65fad8aae54b6956626c6d7eaf122af10f8f2970"
    )
    views = json.loads((pin_dir / "submitted_views.json").read_bytes().decode("utf-8"))
    assert sha256_digest(strict_canonical_bytes(views)) == (
        "sha256:01e90a2079b0443bfea44951fb3e1fd224583a95a42079ac4b897223aa8cf5d7"
    )


# ---------------------------------------------------------------------------
# Exact protected receipt bytes — no newline / alias / overwrite
# ---------------------------------------------------------------------------


def test_authenticate_receipt_requires_exact_inventory_bytes(tmp_path: Path):
    env = _envelope_root()
    _grounding, receipt, ref = _closed_grounding(env)
    inv_root = _write_inventory(tmp_path, receipt)
    inventory = load_issuer_receipt_inventory(inv_root)
    assert authenticate_receipt(
        receipt,
        inventory_bytes=inventory,
        allowed_issuer_ids={_ISSUER},
        allowed_source_registration_ids={_SRC},
        capture_issuers=(_issuer(),),
    ) == ref


def test_authenticate_receipt_rejects_trailing_newline_variant(tmp_path: Path):
    env = _envelope_root()
    _, receipt, ref = _closed_grounding(env)
    exact = strict_canonical_bytes(receipt) + b"\n"
    inv_root = _write_inventory(tmp_path, receipt, exact=exact)
    inventory = load_issuer_receipt_inventory(inv_root)
    assert ref in inventory
    with pytest.raises(StrictGroundingError, match="receipt_inventory_bytes_mismatch"):
        authenticate_receipt(
            receipt,
            inventory_bytes=inventory,
            allowed_issuer_ids={_ISSUER},
            allowed_source_registration_ids={_SRC},
            capture_issuers=(_issuer(),),
        )


def test_authenticate_receipt_rejects_object_not_in_inventory(_tmp_path: Path):
    env = _envelope_root()
    _, receipt, _ref = _closed_grounding(env)
    with pytest.raises(StrictGroundingError, match="receipt_not_in_inventory"):
        authenticate_receipt(
            receipt,
            inventory_bytes={},
            allowed_issuer_ids={_ISSUER},
            allowed_source_registration_ids={_SRC},
        )


def test_inventory_rejects_duplicate_capture_id(tmp_path: Path):
    env = _envelope_root()
    _, receipt, _ = _closed_grounding(env)
    root = tmp_path / "inv"
    root.mkdir()
    a = root / "a.json"
    b = root / "b.json"
    raw = strict_canonical_bytes(receipt)
    a.write_bytes(raw)
    b.write_bytes(raw)
    os.chmod(a, 0o444)
    os.chmod(b, 0o444)
    os.chmod(root, 0o555)
    with pytest.raises(StrictGroundingError, match="capture_id_duplicate|receipt_ref_duplicate"):
        load_issuer_receipt_inventory(root)


def test_inventory_has_no_capture_id_alias(tmp_path: Path):
    env = _envelope_root()
    _, receipt, ref = _closed_grounding(env)
    inv_root = _write_inventory(tmp_path, receipt)
    inventory = load_issuer_receipt_inventory(inv_root)
    assert ref in inventory
    assert f"id:{receipt['capture_id']}" not in inventory
    assert set(inventory) == {ref}


# ---------------------------------------------------------------------------
# Closed grounding validation — dangling / unused / duplicate / mismatch
# ---------------------------------------------------------------------------


def test_validate_grounding_rejects_unused_blob():
    env = _envelope_root()
    grounding, _, _ = _closed_grounding(env)
    other = sha256_digest(b"other")
    import base64

    grounding["blobs"].append(
        {
            "sha256": other,
            "length": 5,
            "bytes_b64": base64.b64encode(b"other").decode("ascii"),
        }
    )
    grounding["blobs"].sort(key=lambda b: b["sha256"])
    payload = {k: v for k, v in grounding.items() if k != "grounding_payload_sha256"}
    grounding["grounding_payload_sha256"] = sha256_digest(strict_canonical_bytes(payload))
    with pytest.raises(StrictGroundingError, match="blob_unused"):
        validate_grounding_document(grounding)


def test_validate_grounding_rejects_impossible_selector():
    env = _envelope_root()
    grounding, _, _ = _closed_grounding(env)
    grounding["roots"][0]["selector"] = {"kind": "byte_range", "start": 0, "end": 99}
    payload = {k: v for k, v in grounding.items() if k != "grounding_payload_sha256"}
    grounding["grounding_payload_sha256"] = sha256_digest(strict_canonical_bytes(payload))
    with pytest.raises(StrictGroundingError, match="selector_bounds"):
        validate_grounding_document(grounding)

def test_qualify_rejects_mismatched_view_bytes(_tmp_path: Path):
    env = _envelope_root()
    grounding, _receipt, _ = _closed_grounding(env)
    # Corrupt stored view blob bytes while keeping digest label (contradiction).
    grounding["blobs"][0]["bytes_b64"] = "dGVzVA=="  # "tesT" — noncanonical length path
    # Use wrong length to hit digest mismatch instead.
    grounding["blobs"][0]["bytes_b64"] = "AAAA"
    grounding["blobs"][0]["length"] = 3
    with pytest.raises(StrictGroundingError):
        validate_grounding_document(grounding)


def test_qualify_rejects_unused_receipt_against_envelope(tmp_path: Path):
    env = _envelope_root()
    grounding, receipt, _ref = _closed_grounding(env)
    # Add a second unused receipt clone with different capture_id.
    extra = dict(receipt)
    extra["capture_id"] = "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
    payload = {k: v for k, v in extra.items() if k != "receipt_payload_sha256"}
    extra["receipt_payload_sha256"] = sha256_digest(strict_canonical_bytes(payload))
    grounding["receipts"].append(extra)
    grounding["receipts"].sort(key=lambda r: r["capture_id"])
    payload_g = {k: v for k, v in grounding.items() if k != "grounding_payload_sha256"}
    grounding["grounding_payload_sha256"] = sha256_digest(strict_canonical_bytes(payload_g))

    inv = _write_inventory(tmp_path, receipt)
    # Second receipt not in inventory — authentication of all receipts fails first.
    with pytest.raises(StrictGroundingError):
        qualify_grounding(
            grounding=grounding,
            envelope=env,
            issuer_inventory=load_issuer_receipt_inventory(inv),
            allowed_issuer_ids={_ISSUER},
            allowed_source_registration_ids={_SRC},
            capture_issuers=(_issuer(),),
            transformer_cap="trusted",
        )


def test_qualify_rejects_root_identity_mismatch(tmp_path: Path):
    env = _envelope_root()
    grounding, receipt, _ = _closed_grounding(env)
    grounding["roots"][0]["source_identity"] = "fixture/other"
    # Fix view still OK; payload hash
    payload_g = {k: v for k, v in grounding.items() if k != "grounding_payload_sha256"}
    grounding["grounding_payload_sha256"] = sha256_digest(strict_canonical_bytes(payload_g))
    inv = _write_inventory(tmp_path, receipt)
    with pytest.raises(StrictGroundingError, match="root_binding_mismatch|envelope_root_unmatched"):
        qualify_grounding(
            grounding=grounding,
            envelope=env,
            issuer_inventory=load_issuer_receipt_inventory(inv),
            allowed_issuer_ids={_ISSUER},
            allowed_source_registration_ids={_SRC},
            capture_issuers=(_issuer(),),
            transformer_cap="trusted",
        )


def test_qualify_rejects_input_bindings_hash_tamper(tmp_path: Path):
    env = _envelope_root()
    grounding, _receipt, _ = _closed_grounding(env)
    grounding["receipts"][0]["input_bindings_sha256"] = "sha256:" + ("a" * 64)
    # Payload hash must be recomputed for validate_receipt_object inside qualify
    r = grounding["receipts"][0]
    payload = {k: v for k, v in r.items() if k != "receipt_payload_sha256"}
    r["receipt_payload_sha256"] = sha256_digest(strict_canonical_bytes(payload))
    # receipt_ref on root still points at old ref — dangling/mismatch
    payload_g = {k: v for k, v in grounding.items() if k != "grounding_payload_sha256"}
    grounding["grounding_payload_sha256"] = sha256_digest(strict_canonical_bytes(payload_g))
    inv_root = tmp_path / "inv"
    inv_root.mkdir()
    # Inventory must hold the tampered receipt bytes to pass auth, then hash check fails.
    path = inv_root / "r.json"
    path.write_bytes(strict_canonical_bytes(r))
    os.chmod(path, 0o444)
    os.chmod(inv_root, 0o555)
    # Update root receipt_ref to new content address
    new_ref = receipt_ref_for(r)
    grounding["roots"][0]["receipt_ref"] = new_ref
    payload_g = {k: v for k, v in grounding.items() if k != "grounding_payload_sha256"}
    grounding["grounding_payload_sha256"] = sha256_digest(strict_canonical_bytes(payload_g))
    with pytest.raises(StrictGroundingError, match="input_bindings_sha256_mismatch"):
        qualify_grounding(
            grounding=grounding,
            envelope=env,
            issuer_inventory=load_issuer_receipt_inventory(inv_root),
            allowed_issuer_ids={_ISSUER},
            allowed_source_registration_ids={_SRC},
            capture_issuers=(_issuer(),),
            transformer_cap="trusted",
        )


def test_qualify_rejects_mixed_capture_ancestry(tmp_path: Path):
    """Mixed capture within a parent→child chain rejects; not merely weakens."""
    parent_id = "00000000-0000-4000-8000-0000000000aa"
    parent_env = base_envelope(
        assertion_id=parent_id,
        root_bindings=[
            root_binding(
                source_identity="fixture/source-a",
                record_locator="event-parent",
                raw_record_sha256=_BLOB_HEX,
                input_view_sha256=_BLOB_HEX,
            )
        ],
        transformer_artifact_sha256=_BLOB_HEX,
        selection_parameters={"output_sha256": _BLOB_HEX},
        producer_class="agent",
        producer_assurance="claimed",
    )
    parent_bare = provenance_commitment(parent_env)
    parent_c = "sha256:" + parent_bare

    child_env = base_envelope(
        assertion_id=_AID,
        root_bindings=[],
        input_bindings=[
            {
                "parent_assertion_id": parent_id,
                "parent_provenance_commitment": parent_bare,
                "exact_input_view_sha256": _BLOB_HEX,
            }
        ],
        transformer_artifact_sha256=_BLOB_HEX,
        selection_parameters={"output_sha256": _BLOB_HEX},
        producer_class="agent",
        producer_assurance="claimed",
        derivation_kind="transform",
        transformer_class="llm",
        ancestry_completeness="complete",
    )
    child_c = "sha256:" + provenance_commitment(child_env)

    parent_root = {
        "provenance_assertion_id": parent_id,
        "provenance_commitment": parent_c,
        "source_registration_id": _SRC,
        "source_event_id": _EVT,
        "source_identity": "fixture/source-a",
        "record_locator": "event-parent",
        "raw_blob_sha256": _BLOB_SHA,
        "view_blob_sha256": _BLOB_SHA,
        "selector": {"kind": "identity"},
        "receipt_ref": "pending",
    }
    parent_receipt = _make_receipt(
        commitment=parent_c,
        roots=[parent_root],
        capture_class="synthetic_fixture",
        capture_id=_CAPTURE_ID,
        issuer_id="fixture-synth",
        assertion_id=parent_id,
    )
    parent_ref = receipt_ref_for(parent_receipt)
    parent_root["receipt_ref"] = parent_ref
    parent_receipt = _make_receipt(
        commitment=parent_c,
        roots=[parent_root],
        capture_class="synthetic_fixture",
        capture_id=_CAPTURE_ID,
        issuer_id="fixture-synth",
        assertion_id=parent_id,
    )
    parent_ref = receipt_ref_for(parent_receipt)
    parent_root["receipt_ref"] = parent_ref

    edge = {
        "child_provenance_assertion_id": _AID,
        "child_provenance_commitment": child_c,
        "parent_provenance_assertion_id": parent_id,
        "parent_provenance_commitment": parent_c,
        "parent_output_blob_sha256": _BLOB_SHA,
        "view_blob_sha256": _BLOB_SHA,
        "selector": {"kind": "identity"},
        "receipt_ref": "pending",
    }
    child_receipt = _make_receipt(
        commitment=child_c,
        roots=[],
        edges=[edge],
        capture_class="controlled_capture",
        capture_id="bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
        issuer_id="fixture-ctrl",
        assertion_id=_AID,
    )
    child_ref = receipt_ref_for(child_receipt)
    edge["receipt_ref"] = child_ref
    child_receipt = _make_receipt(
        commitment=child_c,
        roots=[],
        edges=[edge],
        capture_class="controlled_capture",
        capture_id="bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
        issuer_id="fixture-ctrl",
        assertion_id=_AID,
    )
    child_ref = receipt_ref_for(child_receipt)
    edge["receipt_ref"] = child_ref

    grounding = {
        "schema": "convmem.strict-grounding.v1",
        "blobs": [{"sha256": _BLOB_SHA, "length": len(_BLOB), "bytes_b64": _BLOB_B64}],
        "roots": [parent_root],
        "edges": [edge],
        "outputs": sorted(
            [
                {
                    "provenance_assertion_id": parent_id,
                    "provenance_commitment": parent_c,
                    "output_blob_sha256": _BLOB_SHA,
                },
                {
                    "provenance_assertion_id": _AID,
                    "provenance_commitment": child_c,
                    "output_blob_sha256": _BLOB_SHA,
                },
            ],
            key=lambda o: o["provenance_assertion_id"],
        ),
        "receipts": sorted(
            [parent_receipt, child_receipt], key=lambda r: r["capture_id"]
        ),
        "grounding_payload_sha256": "sha256:" + ("0" * 64),
    }
    payload_g = {k: v for k, v in grounding.items() if k != "grounding_payload_sha256"}
    grounding["grounding_payload_sha256"] = sha256_digest(strict_canonical_bytes(payload_g))

    inv_root = tmp_path / "inv"
    inv_root.mkdir()
    for rec, name in ((parent_receipt, "a.json"), (child_receipt, "b.json")):
        p = inv_root / name
        p.write_bytes(strict_canonical_bytes(rec))
        os.chmod(p, 0o444)
    os.chmod(inv_root, 0o555)

    issuers = (
        CaptureIssuer(
            issuer_id="fixture-synth",
            capture_class="synthetic_fixture",
            enrollment_sha256=_BLOB_SHA,
            receipt_root="/var/lib/convmem/receipts/fixture-synth",
            source_registration_ids=(_SRC,),
        ),
        CaptureIssuer(
            issuer_id="fixture-ctrl",
            capture_class="controlled_capture",
            enrollment_sha256=_BLOB_SHA,
            receipt_root="/var/lib/convmem/receipts/fixture-ctrl",
            source_registration_ids=(_SRC,),
        ),
    )
    ctx = _context_with_assertions(
        [
            {
                "assertion_id": parent_id,
                "provenance_commitment": parent_c,
                "envelope": parent_env,
            },
            {
                "assertion_id": _AID,
                "provenance_commitment": child_c,
                "envelope": child_env,
            },
        ],
        grounding_sha=grounding["grounding_payload_sha256"],
    )
    ctx["registered_assertions"] = sorted(
        ctx["registered_assertions"], key=lambda e: e["assertion_id"]
    )
    ctx = _seal_context(ctx)

    with pytest.raises(StrictGroundingError, match="capture_ancestry_mixed"):
        qualify_assertions(
            grounding=grounding,
            provenance_context=ctx,
            issuer_inventory=load_issuer_receipt_inventory(inv_root),
            allowed_issuer_ids={"fixture-synth", "fixture-ctrl"},
            allowed_source_registration_ids={_SRC},
            capture_issuers=issuers,
        )


# ---------------------------------------------------------------------------
# Missing weakens; late evidence never upgrades original admission
# ---------------------------------------------------------------------------


def test_missing_grounding_weakens_without_reject():
    env = _envelope_root()
    result = qualify_grounding(
        grounding=None,
        envelope=env,
        transformer_cap="trusted",
    )
    assert result.byte_grounding == "missing"
    assert result.capture == "unattested"


def test_original_admission_blocks_late_upgrade(tmp_path: Path):
    env = _envelope_root()
    grounding, receipt, _ = _closed_grounding(env)
    inv = load_issuer_receipt_inventory(_write_inventory(tmp_path, receipt))
    frozen = {
        "commitments": "incomplete",
        "byte_grounding": "missing",
        "capture": "unattested",
        "transformer_cap": "untrusted",
    }
    result = qualify_grounding(
        grounding=grounding,
        envelope=env,
        issuer_inventory=inv,
        allowed_issuer_ids={_ISSUER},
        allowed_source_registration_ids={_SRC},
        capture_issuers=(_issuer(),),
        transformer_cap="trusted",
        original_qualification=frozen,
    )
    assert result == QualificationTuple("incomplete", "missing", "unattested", "untrusted")


def test_original_admission_rejects_contradictory_cold_drift(tmp_path: Path):
    env = _envelope_root()
    grounding, receipt, _ = _closed_grounding(env)
    inv = load_issuer_receipt_inventory(_write_inventory(tmp_path, receipt))
    # Freeze at a complete tuple, then corrupt grounding so recompute differs downward.
    frozen = {
        "commitments": "valid",
        "byte_grounding": "complete",
        "capture": "synthetic_fixture",
        "transformer_cap": "trusted",
    }
    grounding["roots"][0]["record_locator"] = "tampered"
    payload_g = {k: v for k, v in grounding.items() if k != "grounding_payload_sha256"}
    grounding["grounding_payload_sha256"] = sha256_digest(strict_canonical_bytes(payload_g))
    with pytest.raises(StrictGroundingError):
        qualify_grounding(
            grounding=grounding,
            envelope=env,
            issuer_inventory=inv,
            allowed_issuer_ids={_ISSUER},
            allowed_source_registration_ids={_SRC},
            capture_issuers=(_issuer(),),
            transformer_cap="trusted",
            original_qualification=frozen,
        )


def test_happy_path_complete_synthetic_qualification(tmp_path: Path):
    env = _envelope_root()
    grounding, receipt, _ = _closed_grounding(env)
    inv = load_issuer_receipt_inventory(_write_inventory(tmp_path, receipt))
    result = qualify_grounding(
        grounding=grounding,
        envelope=env,
        issuer_inventory=inv,
        allowed_issuer_ids={_ISSUER},
        allowed_source_registration_ids={_SRC},
        capture_issuers=(_issuer(),),
        transformer_cap="trusted",
        require_complete=True,
    )
    assert result.commitments == "valid"
    assert result.byte_grounding == "complete"
    assert result.capture == "synthetic_fixture"
    assert result.transformer_cap == "trusted"


# ---------------------------------------------------------------------------
# CORRECT A — provenance-context + receipt-inventory trust boundary
# ---------------------------------------------------------------------------


def _b64(raw: bytes) -> str:
    import base64

    encoded = base64.b64encode(raw)
    return encoded.decode("ascii")


def _default_context_materials() -> tuple[list, list, list]:
    policy = ProvenanceRegistry().current_policy
    schema_semantics = [
        dict((
            ("schema_version", SCHEMA_VERSION),
            ("binding_version", BINDING_VERSION),
            ("semantic_bytes_b64", _b64(SCHEMA_SEMANTICS_BYTES)),
            ("semantic_sha256", "sha256:" + SCHEMA_SEMANTICS_SHA256),
        ))
    ]
    policies = [
        dict((
            ("policy_version", POLICY_VERSION),
            ("semantic_bytes_b64", _b64(policy.semantic_bytes)),
            ("semantic_sha256", "sha256:" + policy.semantic_sha256),
            ("rules", []),
        ))
    ]
    recipe_bytes = b"convmem:root-recipe-v1"
    recipes = [
        dict((
            ("recipe_id", "root-v1"),
            ("recipe_bytes_b64", _b64(recipe_bytes)),
            ("recipe_sha256", _ROOT_RECIPE_SHA256),
        ))
    ]
    return schema_semantics, policies, recipes


def _seal_context(ctx: dict) -> dict:
    payload = {k: v for k, v in ctx.items() if k != "context_payload_sha256"}
    ctx["context_payload_sha256"] = sha256_digest(strict_canonical_bytes(payload))
    return ctx


def _context_with_assertions(assertions: list[dict], *, grounding_sha: str) -> dict:
    schema_semantics, policies, recipes = _default_context_materials()
    ctx = {
        "schema": "convmem.strict-provenance-context.v2",
        "schema_semantics": schema_semantics,
        "policies": policies,
        "recipes": recipes,
        "verified_channels": [],
        "registered_assertions": assertions,
        "grounding_sha256": grounding_sha,
        "context_payload_sha256": "sha256:" + ("0" * 64),
    }
    return _seal_context(ctx)


def test_reject_duplicate_registered_assertion_before_mapping():
    env = _envelope_root()
    commitment = "sha256:" + provenance_commitment(env)
    entry = {
        "assertion_id": _AID,
        "provenance_commitment": commitment,
        "envelope": env,
    }
    ctx = _context_with_assertions(
        [entry, dict(entry)], grounding_sha="sha256:" + ("0" * 64)
    )
    with pytest.raises(StrictGroundingError, match="registered_assertion_duplicate"):
        validate_provenance_context(ctx)


def test_reject_changed_schema_semantics_digest():
    schema_semantics, policies, recipes = _default_context_materials()
    schema_semantics[0] = dict(schema_semantics[0])
    schema_semantics[0]["semantic_sha256"] = "sha256:" + ("f" * 64)
    ctx = _seal_context(
        {
            **{
            "schema": "convmem.strict-provenance-context.v2",
            "schema_semantics": schema_semantics,
            "policies": policies,
            "recipes": recipes,
            "verified_channels": [],
        },
            "registered_assertions": [],
            "grounding_sha256": "sha256:" + ("0" * 64),
            "context_payload_sha256": "sha256:" + ("0" * 64),
        }
    )
    with pytest.raises(StrictGroundingError, match="schema_semantics_digest_mismatch"):
        validate_provenance_context(ctx)


def test_reject_changed_policy_and_recipe_digests():
    schema_semantics, policies, recipes = _default_context_materials()
    bad_policy = dict(policies[0])
    bad_policy["semantic_sha256"] = "sha256:" + ("e" * 64)
    ctx = _seal_context(
        {
            "schema": "convmem.strict-provenance-context.v2",
            "schema_semantics": schema_semantics,
            "policies": [bad_policy],
            "recipes": recipes,
            "verified_channels": [],
            "registered_assertions": [],
            "grounding_sha256": "sha256:" + ("0" * 64),
            "context_payload_sha256": "sha256:" + ("0" * 64),
        }
    )
    with pytest.raises(StrictGroundingError, match="policy_digest_mismatch"):
        validate_provenance_context(ctx)

    bad_recipe = dict(recipes[0])
    bad_recipe["recipe_sha256"] = "sha256:" + ("d" * 64)
    ctx2 = _seal_context(
        {
            "schema": "convmem.strict-provenance-context.v2",
            "schema_semantics": schema_semantics,
            "policies": policies,
            "recipes": [bad_recipe],
            "verified_channels": [],
            "registered_assertions": [],
            "grounding_sha256": "sha256:" + ("0" * 64),
            "context_payload_sha256": "sha256:" + ("0" * 64),
        }
    )
    with pytest.raises(StrictGroundingError, match="recipe_digest_mismatch"):
        validate_provenance_context(ctx2)


def test_reject_changed_channel_bytes_duplicate_and_sort():
    schema_semantics, policies, recipes = _default_context_materials()
    channel = {
        "origin_class": "external",
        "channel_class": "fixture",
        "channel_locator": "fixture://a",
        "channel_evidence_sha256": "sha256:" + ("a" * 64),
    }
    # unsorted: b before a
    channels = [
        {
            "origin_class": "external",
            "channel_class": "fixture",
            "channel_locator": "fixture://b",
            "channel_evidence_sha256": "sha256:" + ("b" * 64),
        },
        channel,
    ]
    ctx = _seal_context(
        {
            "schema": "convmem.strict-provenance-context.v2",
            "schema_semantics": schema_semantics,
            "policies": policies,
            "recipes": recipes,
            "verified_channels": channels,
            "registered_assertions": [],
            "grounding_sha256": "sha256:" + ("0" * 64),
            "context_payload_sha256": "sha256:" + ("0" * 64),
        }
    )
    with pytest.raises(StrictGroundingError, match="channels_unsorted"):
        validate_provenance_context(ctx)

    dup = _seal_context(
        {
            "schema": "convmem.strict-provenance-context.v2",
            "schema_semantics": schema_semantics,
            "policies": policies,
            "recipes": recipes,
            "verified_channels": [channel, dict(channel)],
            "registered_assertions": [],
            "grounding_sha256": "sha256:" + ("0" * 64),
            "context_payload_sha256": "sha256:" + ("0" * 64),
        }
    )
    with pytest.raises(StrictGroundingError, match="channel_duplicate"):
        validate_provenance_context(dup)


def test_missing_parent_yields_incomplete_not_valid():
    parent_id = "00000000-0000-4000-8000-0000000000aa"
    child = base_envelope(
        assertion_id=_AID,
        root_bindings=[],
        input_bindings=[
            {
                "parent_assertion_id": parent_id,
                "parent_provenance_commitment": "a" * 64,
                "exact_input_view_sha256": _BLOB_HEX,
            }
        ],
        selection_parameters={"output_sha256": _BLOB_HEX},
        producer_class="agent",
        producer_assurance="claimed",
        derivation_kind="transform",
        transformer_class="llm",
        ancestry_completeness="complete",
    )
    commitment = "sha256:" + provenance_commitment(child)
    ctx = _context_with_assertions(
        [
            {
                "assertion_id": _AID,
                "provenance_commitment": commitment,
                "envelope": child,
            }
        ],
        grounding_sha="sha256:" + ("0" * 64),
    )
    registry, _schema = reconstruct_provenance_registry(ctx)
    result = registry.verify(_AID)
    assert not result.verified
    assert "missing parent" in (result.reason or "")
    quals = qualify_assertions(
        grounding=None,
        provenance_context=ctx,
    )
    assert quals[_AID].commitments == "incomplete"
def test_false_envelope_commitment_fallback_rejected(_tmp_path: Path):
    """Recomputation failure must not adopt an envelope-supplied commitment claim."""
    env = _envelope_root()
    grounding, _receipt, _ = _closed_grounding(env)
    good = provenance_commitment(env)
    bad = dict(env)
    bad.pop("schema_version")
    bad["provenance_commitment"] = good
    with pytest.raises(StrictGroundingError, match="envelope_commitment"):
        qualify_grounding(
            grounding=grounding,
            envelope=bad,
            transformer_cap="trusted",
        )

    # Claimed registered commitment that does not match recomputation rejects.
    env2 = _envelope_root()
    ctx = _context_with_assertions(
        [
            {
                "assertion_id": _AID,
                "provenance_commitment": "sha256:" + ("f" * 64),
                "envelope": env2,
            }
        ],
        grounding_sha="sha256:" + ("0" * 64),
    )
    with pytest.raises(StrictGroundingError, match="registered_commitment_mismatch"):
        validate_provenance_context(ctx)


def test_wrong_issuer_enrollment_and_source_rejected(tmp_path: Path):
    env = _envelope_root()
    _grounding, receipt, _ = _closed_grounding(env)
    inv_root = _write_inventory(tmp_path, receipt)
    wrong_issuer = CaptureIssuer(
        issuer_id="other-issuer",
        capture_class="synthetic_fixture",
        enrollment_sha256=_BLOB_SHA,
        receipt_root=str(inv_root),
        source_registration_ids=(_SRC,),
    )
    with pytest.raises(StrictGroundingError, match="receipt_issuer_unenrolled"):
        load_bound_issuer_inventories((wrong_issuer,))

    wrong_source = CaptureIssuer(
        issuer_id=_ISSUER,
        capture_class="synthetic_fixture",
        enrollment_sha256=_BLOB_SHA,
        receipt_root=str(inv_root),
        source_registration_ids=("src-other",),
    )
    with pytest.raises(StrictGroundingError, match="receipt_source_unenrolled"):
        load_bound_issuer_inventories((wrong_source,))


def test_missing_inventory_bytes_reject_and_merge_duplicates(tmp_path: Path):
    env = _envelope_root()
    _grounding, receipt, _ref = _closed_grounding(env)
    inv = load_issuer_receipt_inventory(_write_inventory(tmp_path, receipt))
    # Drop the only inventory row → authenticate fails.
    empty = {}
    with pytest.raises(StrictGroundingError, match="receipt_not_in_inventory"):
        authenticate_receipt(
            receipt,
            inventory_bytes=empty,
            allowed_issuer_ids={_ISSUER},
            allowed_source_registration_ids={_SRC},
            capture_issuers=(_issuer(),),
        )
    with pytest.raises(StrictGroundingError, match="receipt_ref_duplicate"):
        merge_issuer_receipt_inventories((inv, inv))


def test_mixed_per_assertion_qualification_not_one_aggregate(tmp_path: Path):
    """Each assertion freezes its own tuple; incomplete sibling does not copy over."""
    env1 = _envelope_root()
    grounding1, receipt1, _ = _closed_grounding(env1)
    aid2 = "00000000-0000-4000-8000-000000000002"
    env2 = base_envelope(
        assertion_id=aid2,
        root_bindings=[
            root_binding(
                source_identity="fixture/source-a",
                record_locator="event-2",
                raw_record_sha256=_BLOB_HEX,
                input_view_sha256=_BLOB_HEX,
            )
        ],
        transformer_artifact_sha256=_BLOB_HEX,
        selection_parameters={"output_sha256": _BLOB_HEX},
        producer_class="agent",
        producer_assurance="claimed",
    )
    c1 = "sha256:" + provenance_commitment(env1)
    c2 = "sha256:" + provenance_commitment(env2)
    # Second assertion intentionally lacks grounding witnesses → incomplete/missing.
    ctx = _context_with_assertions(
        [
            {"assertion_id": _AID, "provenance_commitment": c1, "envelope": env1},
            {"assertion_id": aid2, "provenance_commitment": c2, "envelope": env2},
        ],
        grounding_sha=grounding1["grounding_payload_sha256"],
    )
    # Sort registered_assertions by assertion_id (aid2 < _AID? compare)
    ctx["registered_assertions"] = sorted(
        ctx["registered_assertions"], key=lambda e: e["assertion_id"]
    )
    ctx = _seal_context(ctx)

    inv = load_issuer_receipt_inventory(_write_inventory(tmp_path, receipt1))
    quals = qualify_assertions(
        grounding=grounding1,
        provenance_context=ctx,
        issuer_inventory=inv,
        allowed_issuer_ids={_ISSUER},
        allowed_source_registration_ids={_SRC},
        capture_issuers=(_issuer(),),
    )
    assert quals[_AID].byte_grounding == "complete"
    assert quals[_AID].capture == "synthetic_fixture"
    assert quals[aid2].byte_grounding == "missing"
    assert quals[aid2].capture == "unattested"
    assert quals[_AID] != quals[aid2]


# ---------------------------------------------------------------------------
# M3 correction — capture attestation + focused trust-boundary cases
# ---------------------------------------------------------------------------


_PARENT_AID = "00000000-0000-4000-8000-0000000000aa"


def _parent_child_envelopes() -> tuple[dict, str, dict, str]:
    parent_env = base_envelope(
        assertion_id=_PARENT_AID,
        root_bindings=[
            root_binding(
                source_identity="fixture/source-a",
                record_locator="event-parent",
                raw_record_sha256=_BLOB_HEX,
                input_view_sha256=_BLOB_HEX,
            )
        ],
        transformer_artifact_sha256=_BLOB_HEX,
        selection_parameters={"output_sha256": _BLOB_HEX},
        producer_class="agent",
        producer_assurance="claimed",
    )
    parent_bare = provenance_commitment(parent_env)
    parent_c = "sha256:" + parent_bare
    child_env = base_envelope(
        assertion_id=_AID,
        root_bindings=[],
        input_bindings=[
            {
                "parent_assertion_id": _PARENT_AID,
                "parent_provenance_commitment": parent_bare,
                "exact_input_view_sha256": _BLOB_HEX,
            }
        ],
        transformer_artifact_sha256=_BLOB_HEX,
        selection_parameters={"output_sha256": _BLOB_HEX},
        producer_class="agent",
        producer_assurance="claimed",
        derivation_kind="transform",
        transformer_class="llm",
        ancestry_completeness="complete",
    )
    child_c = "sha256:" + provenance_commitment(child_env)
    return parent_env, parent_c, child_env, child_c


def _child_edge_grounding(_child_env: dict, child_c: str, parent_c: str) -> tuple[dict, dict]:
    edge = {
        "child_provenance_assertion_id": _AID,
        "child_provenance_commitment": child_c,
        "parent_provenance_assertion_id": _PARENT_AID,
        "parent_provenance_commitment": parent_c,
        "parent_output_blob_sha256": _BLOB_SHA,
        "view_blob_sha256": _BLOB_SHA,
        "selector": {"kind": "identity"},
        "receipt_ref": "pending",
    }
    receipt = _make_receipt(
        commitment=child_c,
        roots=[],
        edges=[edge],
        assertion_id=_AID,
    )
    ref = receipt_ref_for(receipt)
    edge["receipt_ref"] = ref
    receipt = _make_receipt(
        commitment=child_c,
        roots=[],
        edges=[edge],
        assertion_id=_AID,
    )
    ref = receipt_ref_for(receipt)
    edge["receipt_ref"] = ref
    grounding = {
        "schema": "convmem.strict-grounding.v1",
        "blobs": [{"sha256": _BLOB_SHA, "length": len(_BLOB), "bytes_b64": _BLOB_B64}],
        "roots": [],
        "edges": [edge],
        "outputs": [_output_binding(child_c)],
        "receipts": [receipt],
        "grounding_payload_sha256": "sha256:" + ("0" * 64),
    }
    payload = {k: v for k, v in grounding.items() if k != "grounding_payload_sha256"}
    grounding["grounding_payload_sha256"] = sha256_digest(strict_canonical_bytes(payload))
    return grounding, receipt


def test_writable_issuer_root_rejects_receipt_root_writable(tmp_path: Path):
    env = _envelope_root()
    _, receipt, _ = _closed_grounding(env)
    root = tmp_path / "writable_inventory"
    root.mkdir()
    path = root / f"{receipt['capture_id']}.json"
    path.write_bytes(strict_canonical_bytes(receipt))
    os.chmod(path, 0o444)
    # Directory left writable — protected inventory root must reject.
    with pytest.raises(StrictGroundingError, match="receipt_root_writable"):
        load_issuer_receipt_inventory(root)


def test_bare_registered_provenance_commitment_rejects():
    env = _envelope_root()
    bare = provenance_commitment(env)
    ctx = _context_with_assertions(
        [
            {
                "assertion_id": _AID,
                "provenance_commitment": bare,  # bare hex, not sha256:<hex>
                "envelope": env,
            }
        ],
        grounding_sha="sha256:" + ("0" * 64),
    )
    with pytest.raises(StrictGroundingError, match="registered_provenance_commitment"):
        validate_provenance_context(ctx)


def test_orphan_grounding_witness_rejects_through_qualify_assertions(tmp_path: Path):
    env = _envelope_root()
    grounding, receipt, _ = _closed_grounding(env)
    orphan = dict(receipt)
    orphan["capture_id"] = "cccccccccccccccccccccccccccccccc"
    payload = {k: v for k, v in orphan.items() if k != "receipt_payload_sha256"}
    orphan["receipt_payload_sha256"] = sha256_digest(strict_canonical_bytes(payload))
    grounding["receipts"].append(orphan)
    grounding["receipts"].sort(key=lambda r: r["capture_id"])
    payload_g = {k: v for k, v in grounding.items() if k != "grounding_payload_sha256"}
    grounding["grounding_payload_sha256"] = sha256_digest(strict_canonical_bytes(payload_g))

    inv_root = tmp_path / "inv"
    inv_root.mkdir()
    for rec, name in ((receipt, "a.json"), (orphan, "b.json")):
        p = inv_root / name
        p.write_bytes(strict_canonical_bytes(rec))
        os.chmod(p, 0o444)
    os.chmod(inv_root, 0o555)

    c1 = "sha256:" + provenance_commitment(env)
    ctx = _context_with_assertions(
        [{"assertion_id": _AID, "provenance_commitment": c1, "envelope": env}],
        grounding_sha=grounding["grounding_payload_sha256"],
    )
    with pytest.raises(StrictGroundingError, match="receipt_unused"):
        qualify_assertions(
            grounding=grounding,
            provenance_context=ctx,
            issuer_inventory=load_issuer_receipt_inventory(inv_root),
            allowed_issuer_ids={_ISSUER},
            allowed_source_registration_ids={_SRC},
            capture_issuers=(_issuer(),),
        )


def test_registered_ancestor_missing_grounding_weakens_child(tmp_path: Path):
    parent_env, parent_c, child_env, child_c = _parent_child_envelopes()
    grounding, receipt = _child_edge_grounding(child_env, child_c, parent_c)
    inv = load_issuer_receipt_inventory(_write_inventory(tmp_path, receipt))
    ctx = _context_with_assertions(
        [
            {
                "assertion_id": _PARENT_AID,
                "provenance_commitment": parent_c,
                "envelope": parent_env,
            },
            {
                "assertion_id": _AID,
                "provenance_commitment": child_c,
                "envelope": child_env,
            },
        ],
        grounding_sha=grounding["grounding_payload_sha256"],
    )
    ctx["registered_assertions"] = sorted(
        ctx["registered_assertions"], key=lambda e: e["assertion_id"]
    )
    ctx = _seal_context(ctx)

    quals = qualify_assertions(
        grounding=grounding,
        provenance_context=ctx,
        issuer_inventory=inv,
        allowed_issuer_ids={_ISSUER},
        allowed_source_registration_ids={_SRC},
        capture_issuers=(_issuer(),),
    )
    assert quals[_AID].commitments == "valid"
    assert quals[_AID].byte_grounding == "missing"
    assert quals[_AID].capture == "unattested"
    assert quals[_PARENT_AID].byte_grounding == "missing"
    assert quals[_PARENT_AID].capture == "unattested"


def test_absent_registered_parent_keeps_capture_unattested(tmp_path: Path):
    """Child witnesses alone must not attest capture when parent is unregistered."""
    _parent_env, parent_c, child_env, child_c = _parent_child_envelopes()
    grounding, receipt = _child_edge_grounding(child_env, child_c, parent_c)
    inv = load_issuer_receipt_inventory(_write_inventory(tmp_path, receipt))
    ctx = _context_with_assertions(
        [
            {
                "assertion_id": _AID,
                "provenance_commitment": child_c,
                "envelope": child_env,
            }
        ],
        grounding_sha=grounding["grounding_payload_sha256"],
    )
    quals = qualify_assertions(
        grounding=grounding,
        provenance_context=ctx,
        issuer_inventory=inv,
        allowed_issuer_ids={_ISSUER},
        allowed_source_registration_ids={_SRC},
        capture_issuers=(_issuer(),),
    )
    assert quals[_AID].commitments == "incomplete"
    assert quals[_AID].byte_grounding == "missing"
    assert quals[_AID].capture == "unattested"


def test_policy_derived_caps_through_qualify_assertions_no_caller_upgrade():
    grounding_sha = "sha256:" + ("0" * 64)

    root_env = _envelope_root()
    root_c = "sha256:" + provenance_commitment(root_env)
    llm_env = base_envelope(
        assertion_id="00000000-0000-4000-8000-000000000010",
        root_bindings=[
            root_binding(
                source_identity="fixture/source-a",
                record_locator="event-llm",
                raw_record_sha256=_BLOB_HEX,
                input_view_sha256=_BLOB_HEX,
            )
        ],
        transformer_artifact_sha256=_BLOB_HEX,
        selection_parameters={"output_sha256": _BLOB_HEX},
        producer_class="agent",
        producer_assurance="claimed",
        transformer_class="llm",
    )
    llm_c = "sha256:" + provenance_commitment(llm_env)
    unk_env = base_envelope(
        assertion_id="00000000-0000-4000-8000-000000000011",
        root_bindings=[
            root_binding(
                source_identity="fixture/source-a",
                record_locator="event-unk",
                raw_record_sha256=_BLOB_HEX,
                input_view_sha256=_BLOB_HEX,
            )
        ],
        transformer_artifact_sha256=_BLOB_HEX,
        selection_parameters={"output_sha256": _BLOB_HEX},
        producer_class="agent",
        producer_assurance="claimed",
        transformer_class="unknown-widget",
        transformer_identity="fixture-unknown",
        transformer_recipe_id="root-v1",
    )
    unk_c = "sha256:" + provenance_commitment(unk_env)

    trusted_rule = {
        "transformer_class": "normalize",
        "transformer_identity": "fixture-normalizer",
        "transformer_version": "1",
        "recipe_id": "root-v1",
        "cap": "trusted",
        "preservation_contract": "exact-bytes",
        "artifact_sha256": _BLOB_SHA,
    }
    bad_rule = {
        "transformer_class": "normalize",
        "transformer_identity": "fixture-normalizer",
        "transformer_version": "1",
        "recipe_id": "root-v1",
        "cap": "trusted",
        "preservation_contract": None,
        "artifact_sha256": _BLOB_SHA,
    }
    custom_env = base_envelope(
        assertion_id="00000000-0000-4000-8000-000000000012",
        root_bindings=[
            root_binding(
                source_identity="fixture/source-a",
                record_locator="event-custom",
                raw_record_sha256=_BLOB_HEX,
                input_view_sha256=_BLOB_HEX,
            )
        ],
        transformer_artifact_sha256=_BLOB_HEX,
        selection_parameters={"output_sha256": _BLOB_HEX},
        producer_class="agent",
        producer_assurance="claimed",
        transformer_class="normalize",
        transformer_identity="fixture-normalizer",
        transformer_version="1",
        transformer_recipe_id="root-v1",
    )
    custom_c = "sha256:" + provenance_commitment(custom_env)

    def _ctx_with_rules(assertions: list[dict], rules: list[dict]) -> dict:
        schema_semantics, policies, recipes = _default_context_materials()
        pol = dict(policies[0])
        pol["rules"] = list(rules)
        ctx = {
            "schema": "convmem.strict-provenance-context.v2",
            "schema_semantics": schema_semantics,
            "policies": [pol],
            "recipes": recipes,
            "verified_channels": [],
            "registered_assertions": assertions,
            "grounding_sha256": grounding_sha,
            "context_payload_sha256": "sha256:" + ("0" * 64),
        }
        return _seal_context(ctx)

    builtins = _context_with_assertions(
        [
            {"assertion_id": _AID, "provenance_commitment": root_c, "envelope": root_env},
            {
                "assertion_id": llm_env["assertion_id"],
                "provenance_commitment": llm_c,
                "envelope": llm_env,
            },
            {
                "assertion_id": unk_env["assertion_id"],
                "provenance_commitment": unk_c,
                "envelope": unk_env,
            },
        ],
        grounding_sha=grounding_sha,
    )
    builtins["registered_assertions"] = sorted(
        builtins["registered_assertions"], key=lambda e: e["assertion_id"]
    )
    builtins = _seal_context(builtins)
    q_builtin = qualify_assertions(grounding=None, provenance_context=builtins)
    assert q_builtin[_AID].transformer_cap == "trusted"
    assert q_builtin[llm_env["assertion_id"]].transformer_cap == "agent"
    assert q_builtin[unk_env["assertion_id"]].transformer_cap == "untrusted"

    custom_ok = _ctx_with_rules(
        [
            {
                "assertion_id": custom_env["assertion_id"],
                "provenance_commitment": custom_c,
                "envelope": custom_env,
            }
        ],
        [trusted_rule],
    )
    assert (
        qualify_assertions(grounding=None, provenance_context=custom_ok)[
            custom_env["assertion_id"]
        ].transformer_cap
        == "trusted"
    )

    custom_bad = _ctx_with_rules(
        [
            {
                "assertion_id": custom_env["assertion_id"],
                "provenance_commitment": custom_c,
                "envelope": custom_env,
            }
        ],
        [bad_rule],
    )
    assert (
        qualify_assertions(grounding=None, provenance_context=custom_bad)[
            custom_env["assertion_id"]
        ].transformer_cap
        == "untrusted"
    )

    mismatch_env = base_envelope(
        assertion_id="00000000-0000-4000-8000-000000000013",
        root_bindings=[
            root_binding(
                source_identity="fixture/source-a",
                record_locator="event-mismatch",
                raw_record_sha256=_BLOB_HEX,
                input_view_sha256=_BLOB_HEX,
            )
        ],
        transformer_artifact_sha256="a" * 64,
        selection_parameters={"output_sha256": _BLOB_HEX},
        producer_class="agent",
        producer_assurance="claimed",
        transformer_class="normalize",
        transformer_identity="fixture-normalizer",
        transformer_version="1",
        transformer_recipe_id="root-v1",
    )
    mismatch_c = "sha256:" + provenance_commitment(mismatch_env)
    custom_mismatch = _ctx_with_rules(
        [
            {
                "assertion_id": mismatch_env["assertion_id"],
                "provenance_commitment": mismatch_c,
                "envelope": mismatch_env,
            }
        ],
        [trusted_rule],
    )
    assert (
        qualify_assertions(grounding=None, provenance_context=custom_mismatch)[
            mismatch_env["assertion_id"]
        ].transformer_cap
        == "untrusted"
    )

    # qualify_assertions has no transformer_cap parameter — policy derives the
    # cap. Direct qualify_grounding with a reconstructed registry also ignores
    # a caller-supplied upgrade.
    registry, schema_map = reconstruct_provenance_registry(builtins)
    upgraded = qualify_grounding(
        grounding=None,
        envelope=llm_env,
        transformer_cap="trusted",
        registry=registry,
        schema_semantics=schema_map,
    )
    assert upgraded.transformer_cap == "agent"

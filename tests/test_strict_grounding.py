"""M3/T1 adversarial coverage for strict grounding and receipt authenticity."""

from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path

import pytest

from bound_read_scope import CaptureIssuer, sha256_digest
from provenance import base_envelope, provenance_commitment, root_binding
from strict_grounding import (
    QualificationTuple,
    StrictGroundingError,
    authenticate_receipt,
    compute_input_bindings_sha256,
    compute_submitted_views_sha256,
    load_issuer_receipt_inventory,
    qualify_grounding,
    receipt_ref_for,
    strict_canonical_bytes,
    validate_grounding_document,
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
        transformer_recipe_sha256=_BLOB_HEX,
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
) -> dict:
    edges = edges or []
    receipt = {
        "schema": "convmem.capture-receipt.v1",
        "capture_id": capture_id,
        "capture_class": capture_class,
        "capture_issuer_id": issuer_id,
        "source_registration_id": _SRC,
        "source_event_id": _EVT,
        "provenance_assertion_id": _AID,
        "provenance_commitment": commitment,
        "input_bindings_sha256": compute_input_bindings_sha256(roots, edges),
        "transformer_artifact_sha256": _BLOB_SHA,
        "recipe_sha256": _BLOB_SHA,
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
    grounding, receipt, ref = _closed_grounding(env)
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


def test_authenticate_receipt_rejects_object_not_in_inventory(tmp_path: Path):
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


def test_qualify_rejects_mismatched_view_bytes(tmp_path: Path):
    env = _envelope_root()
    grounding, receipt, _ = _closed_grounding(env)
    # Corrupt stored view blob bytes while keeping digest label (contradiction).
    grounding["blobs"][0]["bytes_b64"] = "dGVzVA=="  # "tesT" — noncanonical length path
    # Use wrong length to hit digest mismatch instead.
    grounding["blobs"][0]["bytes_b64"] = "AAAA"
    grounding["blobs"][0]["length"] = 3
    with pytest.raises(StrictGroundingError):
        validate_grounding_document(grounding)


def test_qualify_rejects_unused_receipt_against_envelope(tmp_path: Path):
    env = _envelope_root()
    grounding, receipt, ref = _closed_grounding(env)
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
    grounding, receipt, _ = _closed_grounding(env)
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
    env = _envelope_root()
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
        transformer_recipe_sha256=_BLOB_HEX,
        selection_parameters={"output_sha256": _BLOB_HEX},
        producer_class="agent",
        producer_assurance="claimed",
    )
    c1 = "sha256:" + provenance_commitment(env)
    c2 = "sha256:" + provenance_commitment(env2)

    root1 = _root_binding("pending", c1)
    receipt1 = _make_receipt(
        commitment=c1,
        roots=[root1],
        capture_class="synthetic_fixture",
        capture_id=_CAPTURE_ID,
        issuer_id="fixture-synth",
    )
    ref1 = receipt_ref_for(receipt1)
    root1["receipt_ref"] = ref1
    receipt1 = _make_receipt(
        commitment=c1,
        roots=[root1],
        capture_class="synthetic_fixture",
        capture_id=_CAPTURE_ID,
        issuer_id="fixture-synth",
    )
    ref1 = receipt_ref_for(receipt1)
    root1["receipt_ref"] = ref1

    root2 = {
        "provenance_assertion_id": aid2,
        "provenance_commitment": c2,
        "source_registration_id": _SRC,
        "source_event_id": _EVT,
        "source_identity": "fixture/source-a",
        "record_locator": "event-2",
        "raw_blob_sha256": _BLOB_SHA,
        "view_blob_sha256": _BLOB_SHA,
        "selector": {"kind": "identity"},
        "receipt_ref": "pending",
    }
    receipt2 = {
        "schema": "convmem.capture-receipt.v1",
        "capture_id": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
        "capture_class": "controlled_capture",
        "capture_issuer_id": "fixture-ctrl",
        "source_registration_id": _SRC,
        "source_event_id": _EVT,
        "provenance_assertion_id": aid2,
        "provenance_commitment": c2,
        "input_bindings_sha256": compute_input_bindings_sha256([root2], []),
        "transformer_artifact_sha256": _BLOB_SHA,
        "recipe_sha256": _BLOB_SHA,
        "submitted_views_sha256": compute_submitted_views_sha256([root2], []),
        "returned_output_sha256": _BLOB_SHA,
        "captured_at": _TS,
        "receipt_payload_sha256": "sha256:" + ("0" * 64),
    }
    payload = {k: v for k, v in receipt2.items() if k != "receipt_payload_sha256"}
    receipt2["receipt_payload_sha256"] = sha256_digest(strict_canonical_bytes(payload))
    ref2 = receipt_ref_for(receipt2)
    root2["receipt_ref"] = ref2
    receipt2["input_bindings_sha256"] = compute_input_bindings_sha256([root2], [])
    receipt2["submitted_views_sha256"] = compute_submitted_views_sha256([root2], [])
    payload = {k: v for k, v in receipt2.items() if k != "receipt_payload_sha256"}
    receipt2["receipt_payload_sha256"] = sha256_digest(strict_canonical_bytes(payload))
    ref2 = receipt_ref_for(receipt2)
    root2["receipt_ref"] = ref2

    grounding = {
        "schema": "convmem.strict-grounding.v1",
        "blobs": [{"sha256": _BLOB_SHA, "length": len(_BLOB), "bytes_b64": _BLOB_B64}],
        "roots": sorted(
            [root1, root2],
            key=lambda r: (
                r["provenance_assertion_id"],
                r["source_registration_id"],
                r["source_event_id"],
                r["record_locator"],
            ),
        ),
        "edges": [],
        "outputs": sorted(
            [
                {
                    "provenance_assertion_id": _AID,
                    "provenance_commitment": c1,
                    "output_blob_sha256": _BLOB_SHA,
                },
                {
                    "provenance_assertion_id": aid2,
                    "provenance_commitment": c2,
                    "output_blob_sha256": _BLOB_SHA,
                },
            ],
            key=lambda o: o["provenance_assertion_id"],
        ),
        "receipts": sorted([receipt1, receipt2], key=lambda r: r["capture_id"]),
        "grounding_payload_sha256": "sha256:" + ("0" * 64),
    }
    payload_g = {k: v for k, v in grounding.items() if k != "grounding_payload_sha256"}
    grounding["grounding_payload_sha256"] = sha256_digest(strict_canonical_bytes(payload_g))

    inv_root = tmp_path / "inv"
    inv_root.mkdir()
    for rec, name in ((receipt1, "a.json"), (receipt2, "b.json")):
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
    with pytest.raises(StrictGroundingError, match="capture_ancestry_mixed"):
        qualify_grounding(
            grounding=grounding,
            envelopes={_AID: env, aid2: env2},
            issuer_inventory=load_issuer_receipt_inventory(inv_root),
            allowed_issuer_ids={"fixture-synth", "fixture-ctrl"},
            allowed_source_registration_ids={_SRC},
            capture_issuers=issuers,
            transformer_cap="trusted",
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

"""Pinned known-answer vectors for M2/T0b (fixture-only; not source-component hashes).

Expected IDs/digests and canonical digest-input bytes are static constants.
Two independent oracles recompute them inside the exact runner. Later semantic
transitions (T1–T5) remain declared red — these vectors freeze bytes and
algorithms only.

Self-hash fields use the parent exclusion rule: hash canonical UTF-8 bytes of
the object with only that named payload-hash field removed. Activation-control
and buffered-release SHAs are fixture-transport known-answers (parent defines
no self-hash field on those request/result objects).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

_PIN_DIR = Path(__file__).resolve().parent / "pin_bytes"


def _pin_bytes(name: str) -> bytes:
    return (_PIN_DIR / name).read_bytes()


# Fixture material digests used as *inputs* to larger objects (not self-hashes).
MATERIAL_SHA_A = "sha256:" + ("a" * 64)
MATERIAL_SHA_B = "sha256:" + ("b" * 64)
MATERIAL_SHA_C = "sha256:" + ("c" * 64)
# Back-compat aliases for earlier M2 vector code.
SHA_A = MATERIAL_SHA_A
SHA_B = MATERIAL_SHA_B
SHA_C = MATERIAL_SHA_C

# --- Owner digest (Architecture §6.5.4) ---
OWNER_INPUT = {
    "scope_sha256": SHA_B,
    "registry_sha256": SHA_A,
    "project_binding_id": "project:convmem:v1",
}
OWNER_DIGEST = "sha256:4531392f9dfcc30e2b4d03bd8c1a7ba2a06d6705c3e8042cd0752f82e61fd755"
OWNER_CANONICAL_UTF8 = (
    b'{"project_binding_id":"project:convmem:v1",'
    b'"registry_sha256":"sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",'
    b'"schema":"convmem.strict-owner.v1",'
    b'"scope_sha256":"sha256:bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"}'
)

# --- fixture_scan_event_v1 event ID ---
SCAN_INPUT = {
    "source_registration_id": "src-reg-1",
    "source_identity": "fixture/source-a",
    "event_key": "scan-key-1",
}
EVT_ID = "evt_451b0b154430f2ef494001c177744e32b191c9344aff96a3b1fbd0d609cee204"

# --- Logical / assertion IDs (authority_site = example.com; kind→prefix derived) ---
LOGICAL_COMMON = {
    "project_binding_id": "project:convmem:v1",
    "source_identity": "fixture/source-a",
    "authority_site": "example.com",
    "producer": "form-prod",
    "logical_key": "subject-key-1",
}
FIND2_ID = "find2_1fb4c550334949f59a662dca5b6760fa3631621bbfcb97e9140cdee6133fc470"
CHOICE2_ID = "choice2_b9d7a46fc53de5770c3e80ea606d60d63a3528e26481be4d45edeaf9c94fdfcf"
OBS2_ID = "obs2_09b5f598541dfa15d44dea21352c5c0ee8f795330f73fcebcdf05245a017ff64"
CHECK2_ID = "check2_1e7670866377c8b2a08e4fef954993145f9805a1d13a4d77ac3a18344d14d1d5"
DEC2_ID = "dec2_95750a13f59fd2d9fde2e00f4b0d2226ea09bb32dbb58c7ea0e8c5ba8897c26a"
VER2_ID = "ver2_9d3391103e4545e8058799237aa1282aaadba17ed6af95aa32231cac4d3e4b4f"

# --- Citation / public handle ---
PROVENANCE_COMMITMENT = SHA_C
CITE1_REF = "cite1_7109133f0195f6338bcb7cfcefb9c798f0ebd42aae408c1c850c9b5f15dc04ac"
PUBLIC_REF = "a" * 32
PUBLIC_HANDLE = f"cm1.{PUBLIC_REF}.{OBS2_ID}"

# --- NFC composed/decomposed equivalence (LP layer) ---
NFC_COMPOSED = "caf\u00e9"
NFC_DECOMPOSED = "cafe\u0301"
LP_CAFE_HEX = "00000005636166c3a9"
CAFE_FIND2_ID = "find2_208f5df7fc9489a5df05bb495e045f4e557b317db031ebb40cef89b85977a4c1"

# --- Typed observation: semantic/payload digests + exact digest-input bytes ---
SEMANTIC_SHA256 = (
    "sha256:04cc2275f206df5d81cc82a986d612fcd0bb9c905dc12896f1e3c946d8a21088"
)
PAYLOAD_SHA256 = (
    "sha256:9ca72119937a31ae7c2d9758a3790fc20f6df90791feebd5fe721d9d4a6b0dd1"
)
TYPED_SEMANTIC_DIGEST_INPUT_UTF8 = _pin_bytes("typed_semantic_excl.json")
TYPED_PAYLOAD_DIGEST_INPUT_UTF8 = _pin_bytes("typed_payload_excl.json")

TYPED_OBSERVATION_RECORD: dict[str, Any] = {
    "schema": "convmem.bound-authority-record.v3",
    "project_binding_id": "project:convmem:v1",
    "source_registration_id": "src-reg-1",
    "authority_site": "example.com",
    "authority_domain": "coding",
    "record_kind": "observation",
    "logical_id": FIND2_ID,
    "assertion_id": OBS2_ID,
    "source_event_id": EVT_ID,
    "producer": "form-prod",
    "logical_key": "subject-key-1",
    "semantic_sha256": SEMANTIC_SHA256,
    "payload_sha256": PAYLOAD_SHA256,
    "title": "fixture title",
    "document": "fixture document",
    "observed_at": "2026-09-21T00:00:00Z",
    "recorded_at": "2026-09-21T00:00:01Z",
    "confidence_bps": 7000,
    "relates_to_assertion_id": None,
    "target_assertion_id": None,
    "verification_result": None,
    "supersedes_assertion_ids": [],
    "decision_disposition_ref": None,
    "supersession_disposition_ref": None,
    "provenance_envelope": {"schema_version": "convmem/provenance-envelope-v1"},
    "provenance_commitment": PROVENANCE_COMMITMENT,
    "origin_assurance": "untrusted",
    "provenance_qualification": {
        "commitments": "incomplete",
        "byte_grounding": "missing",
        "capture": "unattested",
        "transformer_cap": "untrusted",
    },
    "check_eligibility": "not_applicable",
}

# --- Decoded grounding blob (bytes_b64 = dGVzdA== → b"test") ---
GROUNDING_BLOB_DECODED_BYTES = b"test"
GROUNDING_BLOB_DECODED_SHA256 = (
    "sha256:9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08"
)
GROUNDING_BLOB_CANONICAL_UTF8 = _pin_bytes("grounding_blob.json")
GROUNDING_BLOB_CANONICAL_SHA256 = (
    "sha256:44a4b0a4ee90f4453e11eab10521b589dbcf979b7dc5516298ec93718bda5ffa"
)
GROUNDING_BLOB: dict[str, Any] = json.loads(GROUNDING_BLOB_CANONICAL_UTF8.decode("utf-8"))

# Binding-set hashes (receipt_ref removed from bindings before hashing)
INPUT_BINDINGS_CANONICAL_UTF8 = _pin_bytes("input_bindings.json")
INPUT_BINDINGS_SHA256 = (
    "sha256:c9634e7a395ebcc35206781b65fad8aae54b6956626c6d7eaf122af10f8f2970"
)
SUBMITTED_VIEWS_CANONICAL_UTF8 = _pin_bytes("submitted_views.json")
SUBMITTED_VIEWS_SHA256 = (
    "sha256:01e90a2079b0443bfea44951fb3e1fd224583a95a42079ac4b897223aa8cf5d7"
)

# --- Capture receipt (self-hash excludes only receipt_payload_sha256) ---
RECEIPT_CANONICAL_UTF8 = _pin_bytes("receipt_excl.json")
RECEIPT_PAYLOAD_SHA256 = (
    "sha256:5c00b3b9fa553ce5c136a97c2c81777ce5f685b866b8dbe2bc61942aaa64a118"
)
RECEIPT_PAYLOAD_HEX = "5c00b3b9fa553ce5c136a97c2c81777ce5f685b866b8dbe2bc61942aaa64a118"
CAPTURE_RECEIPT_REF = "capture_" + RECEIPT_PAYLOAD_HEX
CAPTURE_RECEIPT: dict[str, Any] = {
    **json.loads(RECEIPT_CANONICAL_UTF8.decode("utf-8")),
    "receipt_payload_sha256": RECEIPT_PAYLOAD_SHA256,
}

# --- Grounding nested objects + payload self-hash ---
GROUNDING_ROOT_CANONICAL_UTF8 = _pin_bytes("grounding_root.json")
GROUNDING_ROOT_CANONICAL_SHA256 = (
    "sha256:09a94aec98f8e6b0a4c1e27cbffe13791c7f8b3f294b343167606b2ef288b7db"
)
GROUNDING_ROOT: dict[str, Any] = json.loads(GROUNDING_ROOT_CANONICAL_UTF8.decode("utf-8"))
GROUNDING_EDGE_CANONICAL_UTF8 = _pin_bytes("grounding_edge.json")
GROUNDING_EDGE_CANONICAL_SHA256 = (
    "sha256:d6dc8e362ecab161871bea652bd25a8b25d0b8b88a2779ca2ab2b08a38a08018"
)
GROUNDING_EDGE: dict[str, Any] = json.loads(GROUNDING_EDGE_CANONICAL_UTF8.decode("utf-8"))
GROUNDING_OUTPUT_CANONICAL_UTF8 = _pin_bytes("grounding_output.json")
GROUNDING_OUTPUT_CANONICAL_SHA256 = (
    "sha256:d34e313a5c79455c05e300a74ef88da8fa5c306fad94ae08ae179c3778327773"
)
GROUNDING_OUTPUT: dict[str, Any] = json.loads(
    GROUNDING_OUTPUT_CANONICAL_UTF8.decode("utf-8")
)
GROUNDING_CANONICAL_UTF8 = _pin_bytes("grounding_excl.json")
GROUNDING_PAYLOAD_SHA256 = (
    "sha256:4c23f7e070efc3557d8b978a7b60fa168101d31ce785b4758f2ddb488023efce"
)
GROUNDING_OBJECT: dict[str, Any] = {
    **json.loads(GROUNDING_CANONICAL_UTF8.decode("utf-8")),
    "grounding_payload_sha256": GROUNDING_PAYLOAD_SHA256,
}

# --- Enrollment (exclude only enrollment_payload_sha256) ---
ENROLLMENT_CANONICAL_UTF8 = _pin_bytes("enrollment_excl.json")
ENROLLMENT_PAYLOAD_SHA256 = (
    "sha256:1a91ed6920e151d9efc9a49080f00d0f0e50d6b6c78a557083c62d296ffbb0cc"
)
ENROLLMENT_FIXTURE: dict[str, Any] = {
    **json.loads(ENROLLMENT_CANONICAL_UTF8.decode("utf-8")),
    "enrollment_payload_sha256": ENROLLMENT_PAYLOAD_SHA256,
}

# --- Publication variants (exclude only publication_payload_sha256) ---
PUBLICATION_SERVING_CANONICAL_UTF8 = _pin_bytes("publication_serving_excl.json")
PUBLICATION_SERVING_PAYLOAD_SHA256 = (
    "sha256:874ebdc71347ce0af6988fcfbd7758b895c1f10963f6d785fb86382888af186f"
)
PUBLICATION_UNAVAILABLE_CANONICAL_UTF8 = _pin_bytes("publication_unavailable_excl.json")
PUBLICATION_UNAVAILABLE_PAYLOAD_SHA256 = (
    "sha256:cf29614a298a1b3790033f80d966daac0bddca0f702d7e412b39f7edb4ab9c4d"
)
PUBLICATION_FENCED_CANONICAL_UTF8 = _pin_bytes("publication_fenced_excl.json")
PUBLICATION_FENCED_PAYLOAD_SHA256 = (
    "sha256:869f11e6affda09de1e48ee380b7b751d21ee1b9cf5192293f2e57a6efbff0f2"
)
PUBLICATION_VARIANTS: dict[str, dict[str, Any]] = {
    "serving": {
        **json.loads(PUBLICATION_SERVING_CANONICAL_UTF8.decode("utf-8")),
        "publication_payload_sha256": PUBLICATION_SERVING_PAYLOAD_SHA256,
    },
    "unavailable": {
        **json.loads(PUBLICATION_UNAVAILABLE_CANONICAL_UTF8.decode("utf-8")),
        "publication_payload_sha256": PUBLICATION_UNAVAILABLE_PAYLOAD_SHA256,
    },
    "fenced": {
        **json.loads(PUBLICATION_FENCED_CANONICAL_UTF8.decode("utf-8")),
        "publication_payload_sha256": PUBLICATION_FENCED_PAYLOAD_SHA256,
    },
}

# --- Lineage fork / multi-head join inputs (algorithm freeze; T2 reducer remains red) ---
LINEAGE_HEAD_A_CANONICAL_UTF8 = _pin_bytes("lineage_head_a.json")
LINEAGE_HEAD_A_SHA256 = (
    "sha256:39d474793792408e1f1fb72ea19a6abebbba551e6ba8ff85b557f65ba96ad470"
)
LINEAGE_HEAD_B_CANONICAL_UTF8 = _pin_bytes("lineage_head_b.json")
LINEAGE_HEAD_B_SHA256 = (
    "sha256:39182df0418fd9e1b79b1ba38065ef1727a44ebe171ef4ede40ca37a7f3467d1"
)
LINEAGE_JOIN_SET_CANONICAL_UTF8 = _pin_bytes("lineage_join_set.json")
LINEAGE_JOIN_SET_SHA256 = (
    "sha256:3f08bd7a0edff08543b8b1fa19cb4f04695366a06be5b36ac8e258a4e9f891a2"
)
LINEAGE_FORK_INPUTS: dict[str, Any] = {
    "note": "fixture-only lineage topology; T2 join/reducer remains future-step red",
    "genesis_parent": None,
    "head_a": json.loads(LINEAGE_HEAD_A_CANONICAL_UTF8.decode("utf-8")),
    "head_b_fork": json.loads(LINEAGE_HEAD_B_CANONICAL_UTF8.decode("utf-8")),
    "join_targets": json.loads(LINEAGE_JOIN_SET_CANONICAL_UTF8.decode("utf-8")),
    "join_requires_complete_parent_head_set": True,
    "head_a_sha256": LINEAGE_HEAD_A_SHA256,
    "head_b_fork_sha256": LINEAGE_HEAD_B_SHA256,
    "join_set_sha256": LINEAGE_JOIN_SET_SHA256,
}

# --- Activation control + buffered release (fixture-transport known-answers) ---
ACTIVATION_TURN_CANONICAL_UTF8 = _pin_bytes("activation_turn.json")
ACTIVATION_TURN_FIXTURE_TRANSPORT_SHA256 = (
    "sha256:42d33a3f78e3dd8e1337714bf445ef80e836f82748f0f2307736bf23662b8261"
)
ACTIVATION_CANCEL_CANONICAL_UTF8 = _pin_bytes("activation_cancel.json")
ACTIVATION_CANCEL_FIXTURE_TRANSPORT_SHA256 = (
    "sha256:565f3984ebd718c704dd5f28faaf3d0776b2900242aa4ec31252097c4be3091b"
)
ACTIVATION_STATUS_CANONICAL_UTF8 = _pin_bytes("activation_status.json")
ACTIVATION_STATUS_FIXTURE_TRANSPORT_SHA256 = (
    "sha256:f9955aded3660fda01afcee02bd6a0387acc06c7296bd70185b876863ce89305"
)
ACTIVATION_REVOKE_CANONICAL_UTF8 = _pin_bytes("activation_revoke.json")
ACTIVATION_REVOKE_FIXTURE_TRANSPORT_SHA256 = (
    "sha256:407cd81ff6d800c9db048f7a1f1c73174bb466ec22c8c289bca7356b53310b41"
)
BUFFERED_RELEASE_CANONICAL_UTF8 = _pin_bytes("buffered_release.json")
BUFFERED_RELEASE_FIXTURE_TRANSPORT_SHA256 = (
    "sha256:b69f171e85e3ce2f6ef9fcd2f16b0e9eed071f2986fa916f1bdf6eb40a19b36a"
)
BUFFERED_COMMITTED_CANONICAL_UTF8 = _pin_bytes("buffered_committed.json")
BUFFERED_COMMITTED_FIXTURE_TRANSPORT_SHA256 = (
    "sha256:2b0e19dfb3214bbc2eb10fc243004d2c3ddd287830f9108d7901efa1535bebd2"
)
ACTIVATION_CONTROL_VARIANTS: dict[str, dict[str, Any]] = {
    "turn": json.loads(ACTIVATION_TURN_CANONICAL_UTF8.decode("utf-8")),
    "cancel": json.loads(ACTIVATION_CANCEL_CANONICAL_UTF8.decode("utf-8")),
    "status": json.loads(ACTIVATION_STATUS_CANONICAL_UTF8.decode("utf-8")),
    "revoke": json.loads(ACTIVATION_REVOKE_CANONICAL_UTF8.decode("utf-8")),
}
BUFFERED_RELEASE_RESULT: dict[str, Any] = json.loads(
    BUFFERED_RELEASE_CANONICAL_UTF8.decode("utf-8")
)

# Max legal hostname = 253 octets: 63.63.63.61
_IDNA_L63 = "a" * 63
_IDNA_L61 = "a" * 61
_IDNA_MAX_LEGAL = f"{_IDNA_L63}.{_IDNA_L63}.{_IDNA_L63}.{_IDNA_L61}"
_IDNA_OVERLONG = _IDNA_MAX_LEGAL + "a"

IDNA2008_VECTORS: list[dict[str, Any]] = [
    {
        "name": "sharp_s_strasse_map",
        "input": "straße.example",
        "expect_accept": True,
        "expected_ascii": "xn--strae-oqa.example",
    },
    {
        "name": "strasse_identity",
        "input": "strasse.example",
        "expect_accept": True,
        "expected_ascii": "strasse.example",
    },
    {
        "name": "fullwidth_example",
        "input": "ｅｘａｍｐｌｅ．ｃｏｍ",
        "expect_accept": True,
        "expected_ascii": "example.com",
    },
    {
        "name": "underscore_first_label_reject",
        "input": "_bad.example",
        "expect_accept": False,
        "expected_ascii": None,
    },
    {
        "name": "underscore_middle_label_reject",
        "input": "bad._mid.example",
        "expect_accept": False,
        "expected_ascii": None,
    },
    {
        "name": "underscore_last_label_reject",
        "input": "bad.example_host",
        "expect_accept": False,
        "expected_ascii": None,
    },
    {
        "name": "underscore_inside_label_reject",
        "input": "bad_host.example",
        "expect_accept": False,
        "expected_ascii": None,
    },
    {
        "name": "max_length_legal_hostname",
        "input": _IDNA_MAX_LEGAL,
        "expect_accept": True,
        "expected_ascii": _IDNA_MAX_LEGAL,
    },
    {
        "name": "overlong_hostname_reject",
        "input": _IDNA_OVERLONG,
        "expect_accept": False,
        "expected_ascii": None,
    },
]

LEGACY_V1_NORMALIZE_VECTORS_OWNER = (
    "tests/test_site_filter.py::NormalizeSiteTests::test_normalize_site_strips_scheme"
)
LEGACY_PROVENANCE_GOLDEN_TEST = (
    "tests/test_provenance.py::test_canonicalization_literal_golden_vector"
)
LEGACY_PROVENANCE_COMMITMENT = (
    "1849adc132d5d41c1ae3868eaf952b89fd2ccbe3c4373788717e3c34ee6f7418"
)
LEGACY_PROVENANCE_ASSERTION_UUID = "00000000-0000-4000-8000-000000000001"
LEGACY_PROVENANCE_CANONICAL_PREFIX = (
    b'{"ancestry_completeness":"complete","assertion_id":"00000000-0000-4000-8000-000000000001",'
)

DECLARED_VECTOR_FUTURE_REDS: tuple[str, ...] = (
    "T1 normalize_authority_site production module",
    "T1 finding_id_v2/assertion_id_v2 production generators",
    "T2 lineage join/reducer over fork heads",
    "T2 publication CAS machine",
)

PINNED_OBJECT_INVENTORY: tuple[str, ...] = (
    "OWNER_DIGEST/OWNER_CANONICAL_UTF8",
    "EVT_ID/FIND2_ID/CHOICE2_ID/CHECK2_ID/OBS2_ID/DEC2_ID/VER2_ID/CITE1_REF/PUBLIC_HANDLE",
    "TYPED_OBSERVATION_RECORD/SEMANTIC_SHA256/PAYLOAD_SHA256/"
    "TYPED_SEMANTIC_DIGEST_INPUT_UTF8/TYPED_PAYLOAD_DIGEST_INPUT_UTF8",
    "ENROLLMENT_FIXTURE/ENROLLMENT_CANONICAL_UTF8/ENROLLMENT_PAYLOAD_SHA256",
    "PUBLICATION_VARIANTS[serving|unavailable|fenced]/canonical+payload_sha256",
    "GROUNDING_BLOB(+decoded)/ROOT/EDGE/OUTPUT/OBJECT + payload/binding-set hashes",
    "CAPTURE_RECEIPT/RECEIPT_CANONICAL_UTF8/RECEIPT_PAYLOAD_SHA256/CAPTURE_RECEIPT_REF",
    "LINEAGE_FORK_INPUTS head_a/head_b_fork/join_set digests",
    "ACTIVATION_CONTROL_VARIANTS turn/cancel/status/revoke fixture-transport SHAs",
    "BUFFERED_RELEASE_RESULT + committed fixture-transport SHAs",
    "IDNA2008_VECTORS (sharp-s/strasse/fullwidth/underscore×4/max-length/overlong)",
    "LEGACY_PROVENANCE_* golden bind",
)

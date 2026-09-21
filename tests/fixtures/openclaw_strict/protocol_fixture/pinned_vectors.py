"""Pinned known-answer vectors for M2/T0b (fixture-only; not source-component hashes).

Expected IDs/digests are static constants. Two independent oracles recompute them
inside the exact runner. Later semantic transitions (T1–T5) remain declared red —
these vectors freeze bytes and algorithms only.

LP applies NFC. Strict minting APIs require already-canonical NFC field input;
composed/decomposed equivalence is proven at the LP layer (same LP bytes) while
logical_id rejects non-NFC raw input.
"""

from __future__ import annotations

from typing import Any

SHA_A = "sha256:" + ("a" * 64)
SHA_B = "sha256:" + ("b" * 64)
SHA_C = "sha256:" + ("c" * 64)

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

# --- Citation / receipt ---
PROVENANCE_COMMITMENT = SHA_C
CITE1_REF = "cite1_7109133f0195f6338bcb7cfcefb9c798f0ebd42aae408c1c850c9b5f15dc04ac"
RECEIPT_PAYLOAD_HEX = "a" * 64
CAPTURE_RECEIPT_REF = "capture_" + RECEIPT_PAYLOAD_HEX

# --- Public handle (concatenation only; not a digest) ---
PUBLIC_REF = "a" * 32
PUBLIC_HANDLE = f"cm1.{PUBLIC_REF}.{OBS2_ID}"

# --- NFC composed/decomposed equivalence (LP layer) ---
# café: U+00E9 (composed) vs U+0065 U+0301 (decomposed)
NFC_COMPOSED = "caf\u00e9"
NFC_DECOMPOSED = "cafe\u0301"
LP_CAFE_HEX = "00000005636166c3a9"
CAFE_FIND2_ID = "find2_208f5df7fc9489a5df05bb495e045f4e557b317db031ebb40cef89b85977a4c1"

# --- Typed observation with explicit nulls (semantic/payload digests filled below) ---
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
    "semantic_sha256": "sha256:04cc2275f206df5d81cc82a986d612fcd0bb9c905dc12896f1e3c946d8a21088",
    "payload_sha256": "sha256:UPDATE_AFTER_DUAL_ORACLE_AGREEMENT",
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

SEMANTIC_SHA256 = (
    "sha256:04cc2275f206df5d81cc82a986d612fcd0bb9c905dc12896f1e3c946d8a21088"
)
PAYLOAD_SHA256 = (
    "sha256:UPDATE_AFTER_DUAL_ORACLE_AGREEMENT"
)

# --- Cumulative lineage / fork / multi-head join (algorithm freeze; T2 red) ---
LINEAGE_FORK_INPUTS: dict[str, Any] = {
    "note": "fixture-only lineage topology; T2 join/reducer remains future-step red",
    "genesis_parent": None,
    "head_a": {"authority_seq": 1, "added_assertion_ids": [OBS2_ID]},
    "head_b_fork": {"authority_seq": 1, "added_assertion_ids": [DEC2_ID]},
    "join_targets": [OBS2_ID, DEC2_ID],
    "join_requires_complete_parent_head_set": True,
}

ENROLLMENT_FIXTURE: dict[str, Any] = {
    "schema": "convmem.strict-enrollment.v1",
    "lineage_id": "b" * 32,
    "slot_id": "c" * 32,
    "mode": "fixture",
    "owner_digest": OWNER_DIGEST,
    "operator_uid": 1000,
    "controller_uid": 0,
    "supervisor_uid": 0,
    "runtime_uid": 1001,
    "scope_sha256": SHA_B,
    "registry_sha256": SHA_A,
    "semantic_contract_sha256": SHA_C,
    "initial_source_cutoff_sha256": SHA_A,
    "enrollment_payload_sha256": SHA_B,
}

PUBLICATION_VARIANTS: dict[str, dict[str, Any]] = {
    "serving": {
        "schema": "convmem.strict-publication.v2",
        "lineage_id": "b" * 32,
        "owner_digest": OWNER_DIGEST,
        "epoch": 1,
        "authority_seq": 1,
        "authority_snapshot_id": "snap2_fixture",
        "authority_manifest_sha256": SHA_A,
        "authority_source_cutoff_sha256": SHA_B,
        "serving_generation_id": "gen2_fixture",
        "projection_manifest_sha256": SHA_C,
        "semantic_contract_sha256": SHA_A,
        "pending_operation_id": None,
        "mode": "serving",
        "previous_publication_sha256": None,
        "freshness_anchor": {
            "boot_id": "boot-1",
            "authority_snapshot_id": "snap2_fixture",
            "sampled_wall_time": "2026-09-21T00:00:00Z",
            "sampled_boottime_ns": 1,
            "snapshot_deadline_boottime_ns": 2,
            "clock_review_ref": "clock_aaa",
        },
        "published_at": "2026-09-21T00:00:00Z",
        "publication_payload_sha256": SHA_B,
    },
    "unavailable": {
        "schema": "convmem.strict-publication.v2",
        "lineage_id": "b" * 32,
        "owner_digest": OWNER_DIGEST,
        "epoch": 2,
        "authority_seq": 1,
        "authority_snapshot_id": "snap2_fixture",
        "authority_manifest_sha256": SHA_A,
        "authority_source_cutoff_sha256": SHA_B,
        "serving_generation_id": None,
        "projection_manifest_sha256": None,
        "semantic_contract_sha256": SHA_A,
        "pending_operation_id": None,
        "mode": "unavailable",
        "previous_publication_sha256": SHA_C,
        "freshness_anchor": {
            "boot_id": "boot-1",
            "authority_snapshot_id": "snap2_fixture",
            "sampled_wall_time": "2026-09-21T00:00:00Z",
            "sampled_boottime_ns": 1,
            "snapshot_deadline_boottime_ns": 2,
            "clock_review_ref": "clock_aaa",
        },
        "published_at": "2026-09-21T00:00:01Z",
        "publication_payload_sha256": SHA_A,
    },
    "fenced": {
        "schema": "convmem.strict-publication.v2",
        "lineage_id": "b" * 32,
        "owner_digest": OWNER_DIGEST,
        "epoch": 3,
        "authority_seq": 1,
        "authority_snapshot_id": "snap2_fixture",
        "authority_manifest_sha256": SHA_A,
        "authority_source_cutoff_sha256": SHA_B,
        "serving_generation_id": None,
        "projection_manifest_sha256": None,
        "semantic_contract_sha256": SHA_A,
        "pending_operation_id": "c" * 32,
        "mode": "fenced",
        "previous_publication_sha256": SHA_C,
        "freshness_anchor": {
            "boot_id": "boot-1",
            "authority_snapshot_id": "snap2_fixture",
            "sampled_wall_time": "2026-09-21T00:00:00Z",
            "sampled_boottime_ns": 1,
            "snapshot_deadline_boottime_ns": 2,
            "clock_review_ref": "clock_aaa",
        },
        "published_at": "2026-09-21T00:00:02Z",
        "publication_payload_sha256": SHA_B,
    },
}

GROUNDING_BLOB = {"sha256": SHA_A, "length": 4, "bytes_b64": "dGVzdA=="}
GROUNDING_ROOT = {
    "provenance_assertion_id": "00000000-0000-4000-8000-000000000001",
    "provenance_commitment": PROVENANCE_COMMITMENT,
    "source_registration_id": "src-reg-1",
    "source_event_id": EVT_ID,
    "source_identity": "fixture/source-a",
    "record_locator": "event-1",
    "raw_blob_sha256": SHA_A,
    "view_blob_sha256": SHA_A,
    "selector": {"kind": "identity"},
    "receipt_ref": CAPTURE_RECEIPT_REF,
}
GROUNDING_EDGE = {
    "child_provenance_assertion_id": "00000000-0000-4000-8000-000000000002",
    "child_provenance_commitment": PROVENANCE_COMMITMENT,
    "parent_provenance_assertion_id": "00000000-0000-4000-8000-000000000001",
    "parent_provenance_commitment": PROVENANCE_COMMITMENT,
    "parent_output_blob_sha256": SHA_A,
    "view_blob_sha256": SHA_A,
    "selector": {"kind": "byte_range", "start": 0, "end": 4},
    "receipt_ref": CAPTURE_RECEIPT_REF,
}
GROUNDING_OUTPUT = {
    "provenance_assertion_id": "00000000-0000-4000-8000-000000000001",
    "provenance_commitment": PROVENANCE_COMMITMENT,
    "output_blob_sha256": SHA_A,
}
CAPTURE_RECEIPT = {
    "schema": "convmem.capture-receipt.v1",
    "capture_id": "a" * 32,
    "capture_class": "synthetic_fixture",
    "capture_issuer_id": "fixture-issuer",
    "source_registration_id": "src-reg-1",
    "source_event_id": EVT_ID,
    "provenance_assertion_id": "00000000-0000-4000-8000-000000000001",
    "provenance_commitment": PROVENANCE_COMMITMENT,
    "input_bindings_sha256": SHA_A,
    "transformer_artifact_sha256": SHA_B,
    "recipe_sha256": SHA_C,
    "submitted_views_sha256": SHA_A,
    "returned_output_sha256": SHA_B,
    "captured_at": "2026-09-21T00:00:00Z",
    "receipt_payload_sha256": "sha256:" + RECEIPT_PAYLOAD_HEX,
}

ACTIVATION_CONTROL_VARIANTS: dict[str, dict[str, Any]] = {
    "turn": {
        "schema": "convmem.activation-control.v1",
        "op": "turn",
        "request_id": "a" * 32,
        "slot_id": "b" * 32,
        "activation_id": "c" * 32,
        "turn_id": "d" * 32,
        "text": "fixture turn",
        "expected_publication_sha256": SHA_A,
    },
    "cancel": {
        "schema": "convmem.activation-control.v1",
        "op": "cancel",
        "request_id": "a" * 32,
        "slot_id": "b" * 32,
        "activation_id": "c" * 32,
        "turn_id": "d" * 32,
    },
    "status": {
        "schema": "convmem.activation-control.v1",
        "op": "status",
        "request_id": "a" * 32,
        "slot_id": "b" * 32,
        "activation_id": "c" * 32,
    },
    "revoke": {
        "schema": "convmem.activation-control.v1",
        "op": "revoke",
        "request_id": "a" * 32,
        "slot_id": "b" * 32,
        "activation_id": "c" * 32,
        "reason": "operator",
    },
}

BUFFERED_RELEASE_RESULT: dict[str, Any] = {
    "schema": "convmem.buffered-release.v1",
    "note": "protocol version literal; committed payload shape below is control-result",
    "committed": {
        "turn_id": "d" * 32,
        "publication_sha256": SHA_A,
        "committed_wall_time": "2026-09-21T00:00:00Z",
        "committed_boottime_ns": 100,
        "output_sha256": SHA_B,
        "model_output": {"ok": True},
        "evidence_basis": "model_output_unverified",
    },
}

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
        "name": "underscore_any_label_reject",
        "input": "bad_host.example",
        "expect_accept": False,
        "expected_ascii": None,
    },
    {
        "name": "long_legal_hostname",
        "input": ("a" * 63) + ".example",
        "expect_accept": True,
        "expected_ascii": ("a" * 63) + ".example",
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
    "T5 activation-control runtime framing",
)

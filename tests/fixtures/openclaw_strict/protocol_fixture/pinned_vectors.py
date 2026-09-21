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
FIND2_ID = "find2_50e9f819d89f80dec49b00214e391456ec1358f2020ddcee2f879b07ed7c20c6"
CHOICE2_ID = "choice2_57066efd026e0f868a8b0e1db9853ed2522e11772e03600d4f501875c2a3b402"
OBS2_ID = "obs2_eb91c542d0f063f2fcb0a981ac9d39d9e81dd0a333b17c09d91e42eba4379bd4"
CHECK2_ID = "check2_c1ffec750b3c46d96daf416f182dcdf70d64879aa44e8bfb1517e578a5b94d1f"
DEC2_ID = "dec2_af6ca0acd95097875c595fdfc9ab8f7a80123fda83d8b0d17d2d7a86e48894d7"
VER2_ID = "ver2_853cae81c15b41a056a9516ef3a365b09ccdd62b8edcbc0174274e1892cdb82b"

# --- Citation / receipt ---
PROVENANCE_COMMITMENT = SHA_C
CITE1_REF = "cite1_fcbd372591afb735c477649a04a2c9ea4bd237edb9da07375b4a7eaeb35a5547"
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
CAFE_FIND2_ID = "find2_15ac84558ae6d20b61091bb49a7fc7348be465b22ddc1f447efacbba69afdc38"

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
    "semantic_sha256": "sha256:5999394777309b1de8524a6b0e8b765cbdd5fde053380fcdb81eb659d2744e19",
    "payload_sha256": "sha256:0d45fd91031d2fd71efd89cf059ba5b4544e0480ae73d06980d2b64c5cd444bf",
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
    "sha256:5999394777309b1de8524a6b0e8b765cbdd5fde053380fcdb81eb659d2744e19"
)
PAYLOAD_SHA256 = (
    "sha256:0d45fd91031d2fd71efd89cf059ba5b4544e0480ae73d06980d2b64c5cd444bf"
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
        "expected_ascii": "strasse.example",
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

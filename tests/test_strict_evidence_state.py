"""M3/T1 adversarial coverage for identities, dispositions, and complete-bound reduction."""

from __future__ import annotations

import copy
import importlib.util
from typing import Any

import pytest

from bound_read_scope import (
    CaptureIssuer,
    ProjectBinding,
    SourceRegistration,
    VerificationProducer,
)
from provenance import base_envelope, provenance_commitment, root_binding
from strict_evidence_state import (
    LedgerIdMintDenied,
    StrictEvidenceError,
    assertion_id_v2,
    disposition_id,
    logical_id_v2,
    materialize_authority_records,
    reduce_complete_bound_state,
    source_event_id_fixture_scan,
    unresolved_predicate,
    validate_dispositions,
)
from strict_grounding import QualificationTuple
from tests.fixtures.openclaw_strict.protocol_fixture.pinned_vectors import (
    CHECK2_ID,
    EVT_ID,
    FIND2_ID,
    OBS2_ID,
    SCAN_INPUT,
)


def test_strict_evidence_state_capability_present():
    spec = importlib.util.find_spec("strict_evidence_state")
    assert spec is not None, "[T1] module strict_evidence_state absent"
    module = importlib.import_module("strict_evidence_state")
    assert hasattr(module, "reduce_complete_bound_state"), (
        "[T1] strict_evidence_state.reduce_complete_bound_state capability absent"
    )


def test_identity_generators_match_pinned_vectors_and_reject_non_nfc():
    assert (
        source_event_id_fixture_scan(
            source_registration_id=SCAN_INPUT["source_registration_id"],
            source_identity=SCAN_INPUT["source_identity"],
            event_key=SCAN_INPUT["event_key"],
        )
        == EVT_ID
    )
    assert (
        logical_id_v2(
            project_binding_id="project:convmem:v1",
            source_identity="fixture/source-a",
            authority_site="example.com",
            producer="form-prod",
            logical_key="subject-key-1",
            record_kind="observation",
            target_assertion_id=None,
        )
        == FIND2_ID
    )
    assert (
        assertion_id_v2(
            project_binding_id="project:convmem:v1",
            source_registration_id="src-reg-1",
            source_event_id=EVT_ID,
            record_kind="observation",
            logical_id=FIND2_ID,
        )
        == OBS2_ID
    )
    with pytest.raises(LedgerIdMintDenied):
        logical_id_v2(
            project_binding_id="project:convmem:v1",
            source_identity="fixture/source-a",
            authority_site="example.com",
            producer="form-prod",
            logical_key="cafe\u0301",
            record_kind="observation",
            target_assertion_id=None,
        )


def test_materialize_requires_qualification_and_payload_binding():
    binding = _binding()
    aid, envelope, commitment = _prov()
    registered = {
        aid: {
            "assertion_id": aid,
            "provenance_commitment": commitment,
            "envelope": envelope,
        }
    }
    source = _source_record(provenance_assertion_id=aid)
    # Corrupt payload binding by changing title after envelope was built for payload.
    bad_source = dict(source)
    bad_source["title"] = "other-title"
    scan = {
        "schema": "convmem.fixture-scan.v1",
        "event_key": "scan-key-1",
        "captured_at": "2026-09-21T00:00:01Z",
        "records": [bad_source],
    }
    qual = {aid: QualificationTuple("valid", "complete", "synthetic_fixture", "trusted")}
    with pytest.raises(StrictEvidenceError, match="source_payload_binding"):
        materialize_authority_records(
            binding=binding,
            source_registration_id="src-reg-1",
            scan=scan,
            registered_assertions=registered,
            qualification_by_provenance=qual,
        )
    with pytest.raises(StrictEvidenceError, match="qualification_missing"):
        materialize_authority_records(
            binding=binding,
            source_registration_id="src-reg-1",
            scan={
                "schema": "convmem.fixture-scan.v1",
                "event_key": "scan-key-1",
                "captured_at": "2026-09-21T00:00:01Z",
                "records": [source],
            },
            registered_assertions=registered,
            qualification_by_provenance={},
        )


def test_fixture_event_collision_and_idempotent_retry():
    binding = _binding()
    aid, envelope, commitment = _prov()
    registered = {
        aid: {
            "assertion_id": aid,
            "provenance_commitment": commitment,
            "envelope": envelope,
        }
    }
    source = _source_record(provenance_assertion_id=aid)
    scan = {
        "schema": "convmem.fixture-scan.v1",
        "event_key": "scan-key-1",
        "captured_at": "2026-09-21T00:00:01Z",
        "records": [source],
    }
    qual = {aid: QualificationTuple("valid", "complete", "synthetic_fixture", "trusted")}
    first = materialize_authority_records(
        binding=binding,
        source_registration_id="src-reg-1",
        scan=scan,
        registered_assertions=registered,
        qualification_by_provenance=qual,
    )
    assert len(first) == 1
    assert first[0]["assertion_id"] == OBS2_ID
    # Exact retry against prior is idempotent no-op.
    second = materialize_authority_records(
        binding=binding,
        source_registration_id="src-reg-1",
        scan=scan,
        registered_assertions=registered,
        qualification_by_provenance=qual,
        prior_records=first,
    )
    assert second == []
    # Changed content under same collision key fails.
    changed = dict(source)
    changed["document"] = "changed-document"
    # Rebuild envelope output hash for changed payload would be needed for payload bind;
    # keep same envelope to trip either payload bind or collision depending on order.
    with pytest.raises(StrictEvidenceError):
        materialize_authority_records(
            binding=binding,
            source_registration_id="src-reg-1",
            scan={
                "schema": "convmem.fixture-scan.v1",
                "event_key": "scan-key-1",
                "captured_at": "2026-09-21T00:00:01Z",
                "records": [changed],
            },
            registered_assertions=registered,
            qualification_by_provenance=qual,
            prior_records=first,
        )


def test_disposition_action_matrix_and_single_consumption():
    obs = _obs_record("obs2_" + "1" * 64, "find2_" + "1" * 64)
    dec = _dec_record("dec2_" + "2" * 64, "choice2_" + "2" * 64)
    approval = _disposition(
        action="decision_approved",
        subject=dec["assertion_id"],
        semantic=dec["semantic_sha256"],
        review_outcome="pass",
        targets=[],
        heads=[],
        basis=None,
        replaces=None,
    )
    approval_id = disposition_id(approval)
    dec["decision_disposition_ref"] = approval_id
    validated = validate_dispositions(
        [approval],
        records=[obs, dec],
        parent_snapshot_id="snap-parent",
    )
    assert approval_id in validated

    # Rejection requires fail outcome; approval+rejection on same subject fails.
    rejection = _disposition(
        action="decision_rejected",
        subject=dec["assertion_id"],
        semantic=dec["semantic_sha256"],
        review_outcome="fail",
        targets=[],
        heads=[],
        basis=None,
        replaces=None,
    )
    with pytest.raises(StrictEvidenceError):
        validate_dispositions(
            [approval, rejection],
            records=[obs, dec],
            parent_snapshot_id="snap-parent",
        )

    # Partial field omission rejected.
    bad = dict(approval)
    del bad["rationale_sha256"]
    with pytest.raises(StrictEvidenceError, match="disposition_keys"):
        validate_dispositions([bad], records=[obs, dec], parent_snapshot_id="snap-parent")


def test_reduce_permanent_supersession_terminal_precedence_and_unresolved():
    logical = "find2_" + "a" * 64
    older = _obs_record("obs2_" + "b" * 64, logical)
    newer = _obs_record("obs2_" + "c" * 64, logical)
    newer["supersedes_assertion_ids"] = [older["assertion_id"]]
    newer["semantic_sha256"] = "sha256:" + "d" * 64
    newer["payload_sha256"] = "sha256:" + "e" * 64
    # Recompute would normally run; set consistent digests via helpers after fields stable.
    from strict_evidence_state import payload_sha256, semantic_sha256

    newer["semantic_sha256"] = semantic_sha256(newer)
    newer["payload_sha256"] = payload_sha256(newer)
    older["semantic_sha256"] = semantic_sha256(older)
    older["payload_sha256"] = payload_sha256(older)

    supersession = _disposition(
        action="supersession_authorized",
        subject=newer["assertion_id"],
        semantic=newer["semantic_sha256"],
        review_outcome="pass",
        targets=[older["assertion_id"]],
        heads=[older["assertion_id"]],
        basis="snap-parent",
        replaces=None,
    )
    newer["supersession_disposition_ref"] = disposition_id(supersession)
    validated = validate_dispositions(
        [supersession],
        records=[older, newer],
        parent_snapshot_id="snap-parent",
    )
    reduced = reduce_complete_bound_state([older, newer], validated)
    assert reduced[older["assertion_id"]].authority_state == "superseded"
    assert reduced[newer["assertion_id"]].authority_state == "current"

    # Withdraw the successor; older remains superseded (permanent).
    withdraw = _disposition(
        action="evidence_withdrawn",
        subject=newer["assertion_id"],
        semantic=newer["semantic_sha256"],
        review_outcome="pass",
        targets=[],
        heads=[],
        basis="snap-parent",
        replaces=None,
    )
    validated2 = validate_dispositions(
        [supersession, withdraw],
        records=[older, newer],
        parent_snapshot_id="snap-parent",
    )
    reduced2 = reduce_complete_bound_state([older, newer], validated2)
    assert reduced2[newer["assertion_id"]].authority_state == "withdrawn"
    assert reduced2[older["assertion_id"]].authority_state == "superseded"

    # Unresolved predicate exact.
    current_unverified = reduced[newer["assertion_id"]]
    assert unresolved_predicate(current_unverified) is True
    passed = current_unverified
    # Build a pass verification head against newer.
    ver = _ver_record(
        "ver2_" + "f" * 64,
        "check2_" + "f" * 64,
        target=newer["assertion_id"],
        result="pass",
        eligibility="qualified",
    )
    reduced3 = reduce_complete_bound_state([older, newer, ver], validated)
    assert reduced3[newer["assertion_id"]].verification_state == "pass"
    assert unresolved_predicate(reduced3[newer["assertion_id"]]) is False


def test_verification_eligibility_inconclusive_never_omitted_and_conflict_fork():
    obs = _obs_record("obs2_" + "1" * 64, "find2_" + "1" * 64)
    from strict_evidence_state import payload_sha256, semantic_sha256

    obs["semantic_sha256"] = semantic_sha256(obs)
    obs["payload_sha256"] = payload_sha256(obs)
    v1 = _ver_record(
        "ver2_" + "2" * 64,
        "check2_" + "2" * 64,
        target=obs["assertion_id"],
        result="pass",
        eligibility="inconclusive_only",
    )
    v2 = _ver_record(
        "ver2_" + "3" * 64,
        "check2_" + "2" * 64,  # same check logical identity
        target=obs["assertion_id"],
        result="pass",
        eligibility="inconclusive_only",
    )
    reduced = reduce_complete_bound_state([obs, v1, v2], {})
    assert reduced[obs["assertion_id"]].verification_state == "conflict"
    assert len(reduced[obs["assertion_id"]].verification_inputs) == 2
    assert all(
        item["effective_result"] == "inconclusive"
        for item in reduced[obs["assertion_id"]].verification_inputs
    )

    # Qualified fail alone => fail; missing eligibility field rejects.
    v_fail = _ver_record(
        "ver2_" + "4" * 64,
        "check2_" + "4" * 64,
        target=obs["assertion_id"],
        result="fail",
        eligibility="qualified",
    )
    reduced_fail = reduce_complete_bound_state([obs, v_fail], {})
    assert reduced_fail[obs["assertion_id"]].verification_state == "fail"
    broken = copy.deepcopy(obs)
    del broken["check_eligibility"]
    with pytest.raises(StrictEvidenceError, match="check_eligibility_required"):
        reduce_complete_bound_state([broken], {})


def test_multi_head_conflict_without_timestamp_choice():
    logical = "find2_" + "9" * 64
    a = _obs_record("obs2_" + "7" * 64, logical, observed_at="2026-09-21T00:00:02Z")
    b = _obs_record("obs2_" + "8" * 64, logical, observed_at="2026-09-21T00:00:01Z")
    from strict_evidence_state import payload_sha256, semantic_sha256

    for rec in (a, b):
        rec["semantic_sha256"] = semantic_sha256(rec)
        rec["payload_sha256"] = payload_sha256(rec)
    reduced = reduce_complete_bound_state([a, b], {})
    assert reduced[a["assertion_id"]].authority_state == "conflict"
    assert reduced[b["assertion_id"]].authority_state == "conflict"
    assert unresolved_predicate(reduced[a["assertion_id"]]) is True


def test_no_str_coercion_on_event_key():
    binding = _binding()
    with pytest.raises(StrictEvidenceError):
        materialize_authority_records(
            binding=binding,
            source_registration_id="src-reg-1",
            scan={
                "schema": "convmem.fixture-scan.v1",
                "event_key": 12,  # type: ignore[dict-item]
                "captured_at": "2026-09-21T00:00:01Z",
                "records": [],
            },
            registered_assertions={},
            qualification_by_provenance={},
        )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_AID = "00000000-0000-4000-8000-000000000001"
_BLOB_HEX = "a" * 64
_TS = "2026-09-21T00:00:00Z"


def _binding() -> ProjectBinding:
    return ProjectBinding(
        id="project:convmem:v1",
        public_ref="a" * 32,
        project="convmem",
        domain_root="coding",
        site_mode="exact",
        site="example.com",
        non_expanding_roots=(),
        source_registrations=(
            SourceRegistration(
                id="src-reg-1",
                source_class="fixture_scan",
                source_identity="fixture/source-a",
                identity_match="exact",
                authorization_domain="coding",
                site="example.com",
                event_id_resolver="fixture_scan_event_v1",
            ),
        ),
        lineage_id="b" * 32,
        capture_issuers=(
            CaptureIssuer(
                issuer_id="fixture-issuer",
                capture_class="synthetic_fixture",
                enrollment_sha256="sha256:" + ("c" * 64),
                receipt_root="/fixture/receipts",
                source_registration_ids=("src-reg-1",),
            ),
        ),
        verification_producers=(
            VerificationProducer(
                source_registration_id="src-reg-1",
                producer="form-prod",
                transformer_identity="fixture-transformer",
                transformer_version="1",
                transformer_artifact_sha256="sha256:" + ("d" * 64),
                recipe_sha256="sha256:" + ("e" * 64),
                capture_class="synthetic_fixture",
            ),
        ),
    )


def _prov() -> tuple[str, dict[str, Any], str]:
    from bound_read_scope import sha256_digest
    from strict_evidence_state import strict_source_payload_sha256

    source = _source_record(provenance_assertion_id=_AID)
    payload = strict_source_payload_sha256(source)
    unlabeled = payload.removeprefix("sha256:")
    envelope = base_envelope(
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
        selection_parameters={"output_sha256": unlabeled},
        producer_class="agent",
        producer_assurance="claimed",
    )
    commitment = "sha256:" + provenance_commitment(envelope)
    return _AID, envelope, commitment


def _source_record(*, provenance_assertion_id: str) -> dict[str, Any]:
    return {
        "record_kind": "observation",
        "producer": "form-prod",
        "logical_key": "subject-key-1",
        "title": "fixture title",
        "document": "fixture document",
        "observed_at": _TS,
        "confidence_bps": 7000,
        "relates_to_assertion_id": None,
        "target_assertion_id": None,
        "verification_result": None,
        "provenance_assertion_id": provenance_assertion_id,
    }


def _obs_record(
    assertion_id: str,
    logical_id: str,
    *,
    observed_at: str = _TS,
) -> dict[str, Any]:
    return {
        "schema": "convmem.bound-authority-record.v3",
        "project_binding_id": "project:convmem:v1",
        "source_registration_id": "src-reg-1",
        "authority_site": "example.com",
        "authority_domain": "coding",
        "record_kind": "observation",
        "logical_id": logical_id,
        "assertion_id": assertion_id,
        "source_event_id": EVT_ID,
        "producer": "form-prod",
        "logical_key": "subject-key-1",
        "semantic_sha256": "sha256:" + "1" * 64,
        "payload_sha256": "sha256:" + "2" * 64,
        "title": "fixture title",
        "document": "fixture document",
        "observed_at": observed_at,
        "recorded_at": "2026-09-21T00:00:01Z",
        "confidence_bps": 7000,
        "relates_to_assertion_id": None,
        "target_assertion_id": None,
        "verification_result": None,
        "supersedes_assertion_ids": [],
        "decision_disposition_ref": None,
        "supersession_disposition_ref": None,
        "provenance_envelope": {"schema_version": "convmem/provenance-envelope-v1"},
        "provenance_commitment": "sha256:" + "c" * 64,
        "origin_assurance": "untrusted",
        "provenance_qualification": {
            "commitments": "valid",
            "byte_grounding": "complete",
            "capture": "synthetic_fixture",
            "transformer_cap": "trusted",
        },
        "check_eligibility": "not_applicable",
    }


def _dec_record(assertion_id: str, logical_id: str) -> dict[str, Any]:
    rec = _obs_record(assertion_id, logical_id)
    rec["record_kind"] = "decision"
    return rec


def _ver_record(
    assertion_id: str,
    logical_id: str,
    *,
    target: str,
    result: str,
    eligibility: str,
) -> dict[str, Any]:
    rec = _obs_record(assertion_id, logical_id)
    rec["record_kind"] = "verification"
    rec["target_assertion_id"] = target
    rec["verification_result"] = result
    rec["check_eligibility"] = eligibility
    return rec


def _disposition(
    *,
    action: str,
    subject: str,
    semantic: str,
    review_outcome: str,
    targets: list[str],
    heads: list[str],
    basis: str | None,
    replaces: str | None,
) -> dict[str, Any]:
    return {
        "schema": "convmem.authority-disposition.v1",
        "action": action,
        "project_binding_id": "project:convmem:v1",
        "subject_assertion_id": subject,
        "subject_semantic_sha256": semantic,
        "target_assertion_ids": targets,
        "basis_snapshot_id": basis,
        "expected_head_assertion_ids": heads,
        "replaces_disposition_ref": replaces,
        "review_actor": "kiro",
        "review_role": "kiro-design-reviewer",
        "review_outcome": review_outcome,
        "reviewed_at": "2026-09-21T00:00:02Z",
        "ratifier_actor": "ryan",
        "ratifier_role": "ryan-authority-owner",
        "ratified_at": "2026-09-21T00:00:03Z",
        "rationale_sha256": "sha256:" + "f" * 64,
    }

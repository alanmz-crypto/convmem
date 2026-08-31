"""Hermetic tests for R2b v2 contract and authority state (I1)."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from eval_corpus.run_manifest import validate_r2b_manifest_schema
from eval_corpus.r2b_v2.authority_state import (
    AuthorityState,
    AuthorityStateError,
    new_authority_state_machine,
    observe_authority_state,
    reconstruct_state_machine,
    transition_to_coverage_proven,
    transition_to_q_held,
)
from eval_corpus.r2b_v2.contract import (
    R2B_CONTRACT_VERSION,
    SERVICE_POLICY_V2,
    SOURCE_QUIESCENCE_POLICY_V2,
    _contract_version_errors,
    assert_no_ratified_duration_defaults,
    detect_contract_version,
    make_r2b_v2_run_manifest_for_tests,
    validate_r2b_v2_manifest_schema,
    validate_v2_policy_fields,
)
from eval_corpus.r2b_v2.trusted import _reset_for_tests
from tests.r2b_v2_helpers import clean_coverage_bundle
from tests.r2b_hermetic import r2b_source_paths


class R2bV2ContractTests(unittest.TestCase):
    def test_v2_policy_values(self):
        with tempfile.TemporaryDirectory() as td:
            body = make_r2b_v2_run_manifest_for_tests(paths=r2b_source_paths(Path(td)))
            self.assertEqual(body["r2b_contract_version"], R2B_CONTRACT_VERSION)
            self.assertEqual(body["service_policy"], SERVICE_POLICY_V2)
            self.assertEqual(body["source_quiescence_policy"], SOURCE_QUIESCENCE_POLICY_V2)
            errs = validate_r2b_v2_manifest_schema(body)
            self.assertEqual(errs, [], msg=errs)

    def test_v1_manifest_not_upgraded(self):
        with tempfile.TemporaryDirectory() as td:
            from eval_corpus.run_manifest import make_r2b_run_manifest_for_tests

            v1 = make_r2b_run_manifest_for_tests(paths=r2b_source_paths(Path(td)))
            self.assertEqual(detect_contract_version(v1), 1)
            v1_errs = validate_r2b_manifest_schema(v1)
            self.assertEqual(v1_errs, [], msg=v1_errs)
            v2_errs = validate_r2b_v2_manifest_schema(v1)
            self.assertTrue(v2_errs)

    def test_absent_contract_version_is_v1(self):
        self.assertEqual(detect_contract_version({}), 1)

    def test_strict_contract_version_only_exact_int_two(self):
        self.assertEqual(_contract_version_errors({"r2b_contract_version": 2}), [])
        self.assertTrue(_contract_version_errors({"r2b_contract_version": "2"}))
        self.assertTrue(_contract_version_errors({"r2b_contract_version": 2.0}))
        self.assertTrue(_contract_version_errors({"r2b_contract_version": True}))
        self.assertTrue(_contract_version_errors({"r2b_contract_version": 3}))

    def test_wrong_policy_values_refuse(self):
        with tempfile.TemporaryDirectory() as td:
            body = make_r2b_v2_run_manifest_for_tests(paths=r2b_source_paths(Path(td)))
            body["service_policy"] = "no_service_changes"
            errs = validate_v2_policy_fields(body)
            self.assertTrue(any(SERVICE_POLICY_V2 in e for e in errs))

    def test_no_default_production_duration(self):
        payload = (
            "acquisition_bound: 900\n"
            "transaction_deadline = 3600\n"
            "policy says 900 seconds is fine"
        )
        errs = assert_no_ratified_duration_defaults(payload)
        self.assertTrue(errs)

    def test_concrete_duration_fields_forbidden_on_manifest(self):
        with tempfile.TemporaryDirectory() as td:
            body = make_r2b_v2_run_manifest_for_tests(paths=r2b_source_paths(Path(td)))
            body["acquisition_bound"] = 120
            errs = validate_r2b_v2_manifest_schema(body)
            self.assertTrue(any("acquisition_bound" in e for e in errs))


class R2bV2AuthorityStateTests(unittest.TestCase):
    def setUp(self) -> None:
        _reset_for_tests()

    def test_new_authority_state_machine_factory(self):
        sm = new_authority_state_machine("run-factory")
        self.assertEqual(sm.run_id, "run-factory")
        self.assertEqual(sm.state, AuthorityState.NEW)
        obs = observe_authority_state(sm)
        self.assertFalse(obs["resumed"])

    def test_happy_path_through_coverage_proven(self):
        sm = new_authority_state_machine("run-1")
        sm.transition(AuthorityState.PREPARED, reason="init")
        sm.transition(AuthorityState.Q_AUTHORIZED, reason="prep grant")
        sm.transition(AuthorityState.Q_ACQUIRING, reason="acquire start")
        sm.transition(AuthorityState.Q_HELD, reason="lease held")
        sm.transition(AuthorityState.COVERAGE_PROVEN, reason="coverage ok")
        self.assertEqual(sm.state, AuthorityState.COVERAGE_PROVEN)

    def test_snapshot_bound_requires_coverage_proven(self):
        sm = new_authority_state_machine("run-i4")
        sm.transition(AuthorityState.PREPARED, reason="init")
        sm.transition(AuthorityState.Q_AUTHORIZED, reason="prep")
        with self.assertRaises(AuthorityStateError):
            sm.transition(AuthorityState.SNAPSHOT_BOUND, reason="skip coverage")

    def test_invalid_transition_refuses(self):
        sm = new_authority_state_machine("run-2")
        with self.assertRaises(AuthorityStateError):
            sm.transition(AuthorityState.Q_HELD, reason="skip")

    def test_aborted_cannot_return(self):
        sm = new_authority_state_machine("run-3")
        sm.transition(AuthorityState.PREPARED, reason="init")
        sm.abort(reason="fail")
        with self.assertRaises(AuthorityStateError):
            sm.transition(AuthorityState.Q_AUTHORIZED, reason="retry")

    def test_quarantined_cannot_return(self):
        sm = new_authority_state_machine("run-4")
        sm.transition(AuthorityState.PREPARED, reason="init")
        sm.quarantine(reason="hold")
        with self.assertRaises(AuthorityStateError):
            sm.transition(AuthorityState.Q_AUTHORIZED, reason="retry")

    def test_reconstructed_state_cannot_resume(self):
        sm = reconstruct_state_machine(run_id="run-5", state=AuthorityState.Q_HELD)
        with self.assertRaises(AuthorityStateError):
            sm.transition(AuthorityState.COVERAGE_PROVEN, reason="resume")

    def test_evidence_coupled_transitions(self):
        with tempfile.TemporaryDirectory() as td:
            lease, trusted, *_ = clean_coverage_bundle(
                Path(td),
                "evidence-rev",
                run_id="evidence-run",
                grant_digest="g",
                authority_digest="a",
                open_evidence_digest="open-ev",
            )
            sm = new_authority_state_machine("evidence-run")
            sm.transition(AuthorityState.PREPARED, reason="init")
            sm.transition(AuthorityState.Q_AUTHORIZED, reason="prep")
            try:
                transition_to_q_held(sm, lease, reason="lease held")
                transition_to_coverage_proven(
                    sm, lease, trusted, reason="coverage proven"
                )
                self.assertEqual(sm.state, AuthorityState.COVERAGE_PROVEN)
            finally:
                lease.release()


if __name__ == "__main__":
    unittest.main()

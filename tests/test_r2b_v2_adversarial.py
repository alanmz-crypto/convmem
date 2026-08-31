"""Adversarial regressions for R2b v2 reviewer-conflict corrective."""

from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path

from eval_corpus.r2b_v2.authority_registry import AuthorityRegistryError, invalidate_coverage_handle
from eval_corpus.r2b_v2.authority_state import (
    AuthorityState,
    AuthorityStateMachine,
    new_authority_state_machine,
    transition_to_coverage_proven,
)
from eval_corpus.r2b_v2.coverage.proof import (
    CoverageProofError,
    CoverageHoldClass,
    attempt_copy_trusted_coverage_proof,
    attempt_deepcopy_trusted_coverage_proof,
    attempt_forge_trusted_coverage_proof,
    attempt_pickle_trusted_coverage_proof,
    inspect_runtime_writers,
    mint_trusted_coverage_proof,
    source_authority_from_lease_and_coverage,
)
from eval_corpus.r2b_v2.gate_policy import test_gate_policy as hermetic_gate_policy
from eval_corpus.r2b_v2.lease import R2bQuiescenceLeaseError
from eval_corpus.r2b_v2.lock_custodian import custodian_for_tests
from eval_corpus.r2b_v2.trusted import _reset_for_tests
from tests.r2b_v2_helpers import (
    acquire_test_lease,
    clean_coverage_bundle,
    foreign_lock_holder_process,
    refuse_source_authority,
    sample_diagnostic_coverage_result,
)

class R2bV2LockSubstitutionTests(unittest.TestCase):
    def setUp(self) -> None:
        _reset_for_tests()

    def test_foreign_lock_ex_substitution_refused(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            lock = Path(td) / "gate.lock"
            lease = acquire_test_lease(Path(td), run_id="foreign-ex")
            holder = lease._holder  # pylint: disable=protected-access
            custodian_for_tests(holder).force_unlock_for_tests()
            proc, ready, done = foreign_lock_holder_process(lock)
            proc.start()
            try:
                ready.get(timeout=5)
                with self.assertRaises(R2bQuiescenceLeaseError):
                    lease.verify()
            finally:
                done.put(True)
                proc.join(timeout=5)
                lease.release()

    def test_lock_sh_downgrade_refused(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            lease = acquire_test_lease(Path(td), run_id="downgrade-sh")
            holder = lease._holder  # pylint: disable=protected-access
            custodian_for_tests(holder).downgrade_to_shared_for_tests()
            with self.assertRaises(R2bQuiescenceLeaseError):
                lease.verify()
            lease.release()


class R2bV2AuthorityForgeryTests(unittest.TestCase):
    def setUp(self) -> None:
        _reset_for_tests()

    def test_manual_diagnostic_cannot_mint(self) -> None:
        diag = sample_diagnostic_coverage_result()
        with self.assertRaises(CoverageProofError):
            mint_trusted_coverage_proof(diag)

    def test_object_new_trusted_proof_refused(self) -> None:
        with self.assertRaises(CoverageProofError):
            attempt_forge_trusted_coverage_proof()

    def test_copy_deepcopy_pickle_refused(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            lease, trusted, *_ = clean_coverage_bundle(Path(td), "forge-proof")
            try:
                with self.assertRaises(CoverageProofError):
                    attempt_copy_trusted_coverage_proof(trusted)
                with self.assertRaises(CoverageProofError):
                    attempt_deepcopy_trusted_coverage_proof(trusted)
                with self.assertRaises(CoverageProofError):
                    attempt_pickle_trusted_coverage_proof(trusted)
            finally:
                lease.release()

    def test_registry_invalidation_refuses_replay(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            lease, trusted, *_ = clean_coverage_bundle(Path(td), "mutate-proof")
            try:
                invalidate_coverage_handle(trusted.authority_handle)
                with self.assertRaises((CoverageProofError, AuthorityRegistryError)):
                    source_authority_from_lease_and_coverage(
                        lease,
                        trusted,
                        open_evidence_digest="open-bind",
                    )
            finally:
                lease.release()


class R2bV2CrossSliceReplayTests(unittest.TestCase):
    def setUp(self) -> None:
        _reset_for_tests()

    def test_foreign_run_refused(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            refuse_source_authority(
                self,
                Path(td),
                "replay-run",
                expected_run_id="other-run",
            )

    def test_foreign_inventory_refused(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            refuse_source_authority(
                self,
                Path(td),
                "replay-inv",
                expected_inventory_digest="wrong",
            )


class R2bV2RuntimeAttestationTests(unittest.TestCase):
    def setUp(self) -> None:
        _reset_for_tests()

    def test_forged_minimal_attestation_holds(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            chroma = root / "chroma"
            chroma.mkdir()
            mutable = chroma / "segment.bin"
            mutable.write_text("x", encoding="utf-8")
            attest_dir = root / "attest"
            attest_dir.mkdir()
            forged = {
                "entrypoint": "rogue",
                "code_revision": "unknown",
                "protocol_version": 1,
            }
            (attest_dir / f"{os.getpid()}.json").write_text(
                json.dumps(forged),
                encoding="utf-8",
            )
            fd = os.open(str(mutable), os.O_RDWR)
            try:
                policy = hermetic_gate_policy(root / "gate.lock")
                _, holds = inspect_runtime_writers(
                    chroma_dir=chroma,
                    processed_path=root / "processed.json",
                    export_root=root / "export",
                    gate_policy=policy,
                    attest_dir=attest_dir,
                    expected_revision="tip-sha",
                )
                self.assertTrue(
                    holds[CoverageHoldClass.MISSING_PROCESS_INSPECTION.value]
                    or holds[CoverageHoldClass.UNKNOWN_WRITER_SIGNATURE.value]
                    or holds[CoverageHoldClass.UNATTESTED_WRITER.value]
                )
            finally:
                os.close(fd)


class R2bV2StateMachineAuthorityTests(unittest.TestCase):
    def test_forged_state_alone_cannot_reach_source_authority(self) -> None:
        forged = AuthorityStateMachine(run_id="forged", state=AuthorityState.COVERAGE_PROVEN)
        self.assertEqual(forged.state, AuthorityState.COVERAGE_PROVEN)
        with tempfile.TemporaryDirectory() as td:
            lease, trusted, *_ = clean_coverage_bundle(Path(td), "state-forge")
            sm = new_authority_state_machine("bind-run")
            sm.transition(AuthorityState.PREPARED, reason="init")
            sm.transition(AuthorityState.Q_AUTHORIZED, reason="prep")
            try:
                transition_to_coverage_proven(forged, lease, trusted, reason="must-fail")
            except Exception:  # pylint: disable=broad-exception-caught
                pass
            finally:
                lease.release()


class R2bV2CustodianDeathTests(unittest.TestCase):
    def setUp(self) -> None:
        _reset_for_tests()

    def test_custodian_death_invalidates_lease(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            lease = acquire_test_lease(Path(td), run_id="custodian-death")
            holder = lease._holder  # pylint: disable=protected-access
            holder.custodian._proc.terminate()  # pylint: disable=protected-access
            holder.custodian._proc.join(timeout=2)  # pylint: disable=protected-access
            with self.assertRaises(R2bQuiescenceLeaseError):
                lease.verify()


class R2bV2ReloadBoundaryTests(unittest.TestCase):
    """Process-local I1–I3: reload invalidates prior handles; same run_id needs fresh chain."""

    def setUp(self) -> None:
        _reset_for_tests()

    def _simulate_process_restart(self) -> None:
        _reset_for_tests()

    def test_old_lease_handle_invalid_after_reload(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            lease, _, *_ = clean_coverage_bundle(Path(td), "reload-lease")
            self._simulate_process_restart()
            with self.assertRaises(R2bQuiescenceLeaseError):
                lease.verify()

    def test_old_trusted_proof_invalid_after_reload(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            lease, trusted, *_ = clean_coverage_bundle(Path(td), "reload-proof")
            self._simulate_process_restart()
            with self.assertRaises((CoverageProofError, AuthorityRegistryError)):
                source_authority_from_lease_and_coverage(
                    lease,
                    trusted,
                    open_evidence_digest="open-bind",
                )

    def test_same_run_id_requires_fresh_chain_after_reload(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            path = Path(td)
            lease, trusted, *_ = clean_coverage_bundle(
                path, "reload-fresh", run_id="reload-run"
            )
            lease.release()
            self._simulate_process_restart()
            with self.assertRaises((CoverageProofError, AuthorityRegistryError)):
                source_authority_from_lease_and_coverage(
                    lease,
                    trusted,
                    open_evidence_digest="open-bind",
                )
            fresh_lease, fresh_trusted, *_ = clean_coverage_bundle(
                path, "reload-fresh", run_id="reload-run"
            )
            try:
                auth = source_authority_from_lease_and_coverage(
                    fresh_lease,
                    fresh_trusted,
                    open_evidence_digest="open-bind",
                )
                self.assertEqual(auth.run_id, "reload-run")
            finally:
                fresh_lease.release()


if __name__ == "__main__":
    unittest.main()

"""Cross-slice binding and fork invalidation tests for R2b v2 corrective."""

from __future__ import annotations

import os
import tempfile
import time
import unittest
from pathlib import Path

from eval_corpus.r2b_v2.authority_state import (
    AuthorityState,
    new_authority_state_machine,
    transition_to_coverage_proven,
    transition_to_q_held,
)
from eval_corpus.r2b_v2.coverage.inventory import build_static_route_inventory
from eval_corpus.r2b_v2.coverage.proof import (
    CoverageProofError,
    mint_trusted_coverage_proof,
    prove_zero_bypass_coverage,
    source_authority_from_lease_and_coverage,
)
from eval_corpus.r2b_v2.lease import (
    R2bQuiescenceLeaseError,
    acquire_r2b_quiescence_lease,
    verify_r2b_quiescence_lease,
)
from eval_corpus.r2b_v2.trusted import _reset_for_tests


class R2bV2CrossSliceBindingTests(unittest.TestCase):
    def setUp(self) -> None:
        _reset_for_tests()

    def _clean_coverage_bundle(self, root: Path, rev: str) -> tuple:
        chroma = root / "chroma"
        processed = root / "processed.json"
        export = root / "export"
        chroma.mkdir()
        export.mkdir()
        processed.write_text("{}", encoding="utf-8")
        gate = root / "gate.lock"
        inv = build_static_route_inventory(code_revision=rev)
        diag = prove_zero_bypass_coverage(
            chroma_dir=chroma,
            processed_path=processed,
            export_root=export,
            test_gate_path=gate,
            code_revision=rev,
            static_inventory=inv,
        )
        trusted = mint_trusted_coverage_proof(diag)
        lease = acquire_r2b_quiescence_lease(
            run_id="bind-run",
            grant_digest="grant-bind",
            authority_digest="auth-bind",
            test_lock_path=gate,
            writer_coverage_digest=trusted.coverage_digest,
            open_evidence_digest="open-bind",
            monotonic_deadline=time.monotonic() + 30,
            bound_source_paths=(str(export), str(processed), str(chroma)),
            timeout_ms=5000,
        )
        return lease, trusted, chroma, processed, export, gate

    def test_cross_slice_binding_matrix_pass(self):
        with tempfile.TemporaryDirectory() as td:
            lease, trusted, *_ = self._clean_coverage_bundle(Path(td), "bind-pass")
            try:
                auth = source_authority_from_lease_and_coverage(
                    lease,
                    trusted,
                    open_evidence_digest="open-bind",
                )
                self.assertEqual(auth.coverage_digest, trusted.coverage_digest)
                self.assertEqual(auth.gate_identity, trusted.gate_identity)
            finally:
                lease.release()

    def test_mismatched_coverage_digest_refused(self):
        with tempfile.TemporaryDirectory() as td:
            lease, _, *_ = self._clean_coverage_bundle(Path(td), "bind-digest")
            try:
                with self.assertRaises(R2bQuiescenceLeaseError):
                    verify_r2b_quiescence_lease(
                        lease,
                        expected_coverage_digest="wrong-digest",
                    )
            finally:
                lease.release()

    def test_mismatched_open_evidence_refused(self):
        with tempfile.TemporaryDirectory() as td:
            lease, trusted, *_ = self._clean_coverage_bundle(Path(td), "bind-open")
            try:
                with self.assertRaises(CoverageProofError):
                    source_authority_from_lease_and_coverage(
                        lease,
                        trusted,
                        open_evidence_digest="wrong-open",
                    )
            finally:
                lease.release()

    def test_state_machine_cross_slice_binding(self):
        with tempfile.TemporaryDirectory() as td:
            lease, trusted, *_ = self._clean_coverage_bundle(Path(td), "bind-sm")
            sm = new_authority_state_machine("bind-run")
            sm.transition(AuthorityState.PREPARED, reason="init")
            sm.transition(AuthorityState.Q_AUTHORIZED, reason="prep")
            try:
                transition_to_q_held(sm, lease, reason="held")
                transition_to_coverage_proven(sm, lease, trusted, reason="proven")
            finally:
                lease.release()

    def test_state_machine_wrong_run_id_refused(self):
        with tempfile.TemporaryDirectory() as td:
            lease, _, *_ = self._clean_coverage_bundle(Path(td), "bind-runid")
            sm = new_authority_state_machine("other-run")
            sm.transition(AuthorityState.PREPARED, reason="init")
            sm.transition(AuthorityState.Q_AUTHORIZED, reason="prep")
            try:
                with self.assertRaises(R2bQuiescenceLeaseError):
                    transition_to_q_held(sm, lease, reason="held")
            finally:
                lease.release()


class R2bV2ForkInvalidationTests(unittest.TestCase):
    def setUp(self) -> None:
        _reset_for_tests()

    def test_fork_invalidates_lease_token(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            lease = acquire_r2b_quiescence_lease(
                run_id="fork-run",
                grant_digest="g",
                authority_digest="a",
                test_lock_path=root / "gate.lock",
                writer_coverage_digest="cov",
                open_evidence_digest="open",
                monotonic_deadline=time.monotonic() + 30,
                bound_source_paths=("/tmp/x",),
                timeout_ms=5000,
            )
            pid = os.fork()
            if pid == 0:
                try:
                    lease.verify()
                    os._exit(1)
                except R2bQuiescenceLeaseError:
                    os._exit(0)
            else:
                _, status = os.waitpid(pid, 0)
                lease.release()
                self.assertEqual(status, 0)


if __name__ == "__main__":
    unittest.main()

"""Deterministic adversarial regressions for expiry-safe authority commitment (I5)."""
# pylint: disable=duplicate-code,protected-access

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from eval_corpus.r2b_v2.authority_commit import (
    AuthorityCommitter,
    GUARDED_SUCCESS_STATES,
    PendingLease,
)
from eval_corpus.r2b_v2.authority_state import (
    AuthorityState,
    AuthorityStateError,
    new_authority_state_machine,
)
from eval_corpus.r2b_v2.capture_close import execute_authorized_capture
from eval_corpus.r2b_v2.duration_policy import (
    DurationPolicy,
    ManualClock,
    PhaseDeadlineExpired,
    TransactionDeadlineExpired,
    InsufficientRemainingBudget,
)
from eval_corpus.r2b_v2.lease import (
    acquire_r2b_quiescence_lease_physical,
    invalidate_pending_lease,
    release_pending_lease_kernel,
)
from eval_corpus.r2b_v2.scratch_capture import (
    compute_completion_marker,
    finalize_capture_report,
)
from eval_corpus.r2b_v2.trusted import _reset_for_tests
from tests.r2b_v2_helpers import (
    advance_to_materialized,
    make_test_committer,
    scratch_transaction_fixture,
)


class R2bV2I5AuthorityCommitTests(unittest.TestCase):
    def setUp(self) -> None:
        _reset_for_tests()

    def test_transaction_deadline_equality_fails_closed(self) -> None:
        policy = DurationPolicy(5.0, 5.0, 5.0, 5.0, 10.0)
        clock = ManualClock(0.0)
        committer = make_test_committer("eq-test", policy, clock=clock)
        committer.tracker.start_phase_once("hitl")
        clock.set(10.0)
        with self.assertRaises(TransactionDeadlineExpired):
            committer.tracker.observe_for_commit(
                "hitl",
                observed_at=clock(),
                commit_scope="equality",
            )

    def test_marker_validates_final_report_hash(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            fx = scratch_transaction_fixture(Path(td))
            sm, mat, committer = self._to_final_checked(fx)
            capture_dir = Path(fx["paths"]["capture_dir"])
            final_report = finalize_capture_report(capture_dir, run_id=fx["run_id"])
            marker = compute_completion_marker(
                mat, capture_dir=capture_dir, final_report=final_report
            )
            self.assertEqual(marker["final_report_status"], "COMPLETE")
            self.assertIn("capture_report.json", marker["artifact_sha256"])

    def test_no_capture_dir_writes_after_marker_commit(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            fx = scratch_transaction_fixture(Path(td))
            sm, mat, committer = self._to_final_checked(fx)
            capture_dir = Path(fx["paths"]["capture_dir"])
            final_report = finalize_capture_report(capture_dir, run_id=fx["run_id"])
            marker = compute_completion_marker(
                mat, capture_dir=capture_dir, final_report=final_report
            )
            files_before = set(capture_dir.iterdir())

            def promote() -> dict:
                from eval_corpus.r2b_v2.scratch_capture import promote_completion_marker

                return promote_completion_marker(capture_dir, marker)

            committer.commit_capture_seal(promote_marker=promote)
            files_after = set(capture_dir.iterdir())
            self.assertEqual(files_before | {capture_dir / "corpus_package_manifest.json"}, files_after)
            fx["lease"].release()

    def test_expiry_after_valid_accept_blocks_grant(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            fx = scratch_transaction_fixture(Path(td))
            sm = new_authority_state_machine(fx["run_id"])
            clock = ManualClock(0.0)
            policy = DurationPolicy(30.0, 30.0, 1.0, 1.0, 10.0)
            committer = make_test_committer(fx["run_id"], policy, sm=sm, clock=clock)
            _manifest, mat, committer = advance_to_materialized(fx, sm, committer)
            clock.set(10.0)
            from eval_corpus.r2b_v2.capture_close import grant_capture

            with self.assertRaises(
                (
                    TransactionDeadlineExpired,
                    PhaseDeadlineExpired,
                    InsufficientRemainingBudget,
                )
            ):
                grant_capture(committer, fx["lease"], mat)
            fx["lease"].release()

    def test_guarded_states_list_matches_design(self) -> None:
        expected = {
            AuthorityState.Q_HELD,
            AuthorityState.PACKET_ACCEPTED,
            AuthorityState.MATERIALIZED,
            AuthorityState.CAPTURE_GRANTED,
            AuthorityState.SEALED,
            AuthorityState.CLOSING,
            AuthorityState.CLOSED,
        }
        self.assertEqual(GUARDED_SUCCESS_STATES, expected)

    def _to_final_checked(self, fx: dict):
        sm = new_authority_state_machine(fx["run_id"])
        _manifest, mat, committer = advance_to_materialized(fx, sm)
        from eval_corpus.r2b_v2.capture_close import grant_capture
        from eval_corpus.r2b_v2.scratch_capture import prepare_scratch_capture_artifacts
        from eval_corpus.r2b_v2.capture_close import final_source_recompute

        grant_capture(committer, fx["lease"], mat)
        sm.transition(AuthorityState.CAPTURING, reason="test")
        committer.tracker.start_phase_once("capture")
        prepare_scratch_capture_artifacts(mat)
        final_source_recompute(
            sm,
            fx["lease"],
            mat.bindings.source_snapshot,
            export=mat.bindings.export,
            processed=mat.bindings.processed,
            chroma_dir=mat.bindings.chroma_dir,
            snapshot_recompute_fn=fx["snapshot_recompute_fn"],
        )
        return sm, mat, committer


if __name__ == "__main__":
    unittest.main()

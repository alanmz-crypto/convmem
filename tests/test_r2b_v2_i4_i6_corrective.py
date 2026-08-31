"""Corrective failure-injection matrix for R2b v2 I4–I6."""
# pylint: disable=duplicate-code

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

from eval_corpus.r2b_v2.authority_state import (
    AuthorityState,
    AuthorityStateError,
    new_authority_state_machine,
    reconstruct_state_machine,
)
from eval_corpus.r2b_v2.capture_close import (
    R2bV2CaptureCloseError,
    execute_authorized_capture,
    grant_capture,
    release_gate_and_write_release_evidence,
    write_close_evidence,
)
from eval_corpus.r2b_v2.duration_policy import (
    DurationPolicy,
    PhaseDeadlineExpired,
    PhaseDeadlineTracker,
)
from eval_corpus.r2b_v2.materialization import (
    R2bV2MaterializationError,
    materialize_v2_packet,
)
from eval_corpus.r2b_v2.trusted import _reset_for_tests
from tests.r2b_v2_helpers import (
    advance_to_materialized,
    advance_to_packet_accepted,
    assert_custodian_force_unlock_breaks_verify,
    scratch_benchmark_candidate_policy,
    scratch_transaction_fixture,
)


class R2bV2CorrectiveFailureMatrix(unittest.TestCase):
    def setUp(self) -> None:
        _reset_for_tests()

    def test_acquisition_deadline_expiry(self) -> None:
        policy = DurationPolicy(
            acquisition_bound=0.001,
            hitl_reservation_bound=30.0,
            capture_bound=30.0,
            release_close_bound=30.0,
            transaction_deadline=60.0,
        )
        tracker = PhaseDeadlineTracker.begin(policy)
        tracker.start_phase("acquisition")
        time.sleep(0.02)
        with self.assertRaises(PhaseDeadlineExpired) as ctx:
            tracker.check_phase_bound("acquisition", policy.acquisition_bound)
        self.assertEqual(ctx.exception.phase, "acquisition")
        self.assertTrue(tracker.consumed)

    def test_hitl_reservation_expiry(self) -> None:
        policy = DurationPolicy(
            acquisition_bound=30.0,
            hitl_reservation_bound=0.001,
            capture_bound=30.0,
            release_close_bound=30.0,
            transaction_deadline=60.0,
        )
        tracker = PhaseDeadlineTracker.begin(policy)
        tracker.start_phase("hitl")
        time.sleep(0.02)
        with self.assertRaises(PhaseDeadlineExpired):
            tracker.check_phase_bound("hitl", policy.hitl_reservation_bound)

    def test_capture_timeout(self) -> None:
        policy = DurationPolicy(
            acquisition_bound=30.0,
            hitl_reservation_bound=30.0,
            capture_bound=0.001,
            release_close_bound=30.0,
            transaction_deadline=60.0,
        )
        tracker = PhaseDeadlineTracker.begin(policy)
        tracker.start_phase("capture")
        time.sleep(0.02)
        with self.assertRaises(PhaseDeadlineExpired):
            tracker.check_phase_bound("capture", policy.capture_bound)

    def test_close_evidence_fsync_failure(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            fx = scratch_transaction_fixture(Path(td))
            sm = new_authority_state_machine(fx["run_id"])
            sm.state = AuthorityState.SEALED
            tracker = PhaseDeadlineTracker.begin(scratch_benchmark_candidate_policy())
            with mock.patch(
                "eval_corpus.r2b_v2.capture_close.write_quiescence_close",
                side_effect=OSError("fsync failed"),
            ):
                with self.assertRaises(OSError):
                    write_close_evidence(
                        sm,
                        fx["lease"],
                        tracker,
                        fx["auth_dir"],
                        marker_result="x",
                        final_source_result="x",
                        preceding_digests={},
                        gate_identity=fx["gate_identity"],
                    )
            self.assertEqual(sm.state, AuthorityState.SEALED)
            fx["lease"].release()

    def test_close_evidence_while_gate_still_held(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            fx = scratch_transaction_fixture(Path(td))
            sm = new_authority_state_machine(fx["run_id"])
            sm.state = AuthorityState.SEALED
            tracker = PhaseDeadlineTracker.begin(scratch_benchmark_candidate_policy())
            write_close_evidence(
                sm,
                fx["lease"],
                tracker,
                fx["auth_dir"],
                marker_result="ok",
                final_source_result="ok",
                preceding_digests={},
                gate_identity=fx["gate_identity"],
            )
            fx["lease"].verify()
            close_body = json.loads(
                (fx["auth_dir"] / "quiescence-close.json").read_text(encoding="utf-8")
            )
            self.assertFalse(close_body["release_success_claimed"])
            fx["lease"].release()

    def test_lease_continuity_failure(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            fx = scratch_transaction_fixture(Path(td))
            assert_custodian_force_unlock_breaks_verify(self, fx["lease"])
            fx["lease"].release()

    def test_release_evidence_failure_after_kernel_release(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            fx = scratch_transaction_fixture(Path(td))
            sm = new_authority_state_machine(fx["run_id"])
            sm.state = AuthorityState.CLOSING
            tracker = PhaseDeadlineTracker.begin(scratch_benchmark_candidate_policy())
            tracker.start_phase("release_close")
            with mock.patch(
                "eval_corpus.r2b_v2.capture_close.write_quiescence_release",
                side_effect=OSError("release evidence fsync failed"),
            ):
                with self.assertRaises(R2bV2CaptureCloseError):
                    release_gate_and_write_release_evidence(
                        sm,
                        fx["lease"],
                        tracker,
                        fx["auth_dir"],
                        close_digest="deadbeef" * 8,
                    )
            self.assertEqual(sm.state, AuthorityState.QUARANTINED)
            self.assertFalse((fx["auth_dir"] / "quiescence-release.json").exists())

    def test_release_evidence_binds_close_digest(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            fx = scratch_transaction_fixture(Path(td))
            sm = new_authority_state_machine(fx["run_id"])
            sm.state = AuthorityState.CLOSING
            tracker = PhaseDeadlineTracker.begin(scratch_benchmark_candidate_policy())
            tracker.start_phase("release_close")
            close_digest = "a" * 64
            release_gate_and_write_release_evidence(
                sm,
                fx["lease"],
                tracker,
                fx["auth_dir"],
                close_digest=close_digest,
            )
            body = json.loads(
                (fx["auth_dir"] / "quiescence-release.json").read_text(encoding="utf-8")
            )
            self.assertEqual(body["close_digest"], close_digest)

    def test_coordinator_crash_boundary_no_resume(self) -> None:
        sm = reconstruct_state_machine(
            run_id="crash-run", state=AuthorityState.CAPTURING
        )
        with self.assertRaises(AuthorityStateError):
            sm.transition(AuthorityState.SEALED, reason="resume forbidden")

    def test_materialization_refuses_existing_capture_dir(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            fx = scratch_transaction_fixture(Path(td))
            sm = new_authority_state_machine(fx["run_id"])
            manifest_path = advance_to_packet_accepted(fx, sm)
            Path(fx["paths"]["capture_dir"]).mkdir(parents=True)
            with self.assertRaises(R2bV2MaterializationError):
                materialize_v2_packet(
                    sm,
                    fx["lease"],
                    manifest_path,
                    runtime=fx["runtime"],
                    snapshot_recompute_fn=fx["snapshot_recompute_fn"],
                    restic_gate_fn=lambda: None,
                )
            fx["lease"].release()

    def test_source_mutation_during_capture_quarantines_without_marker(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            fx = scratch_transaction_fixture(Path(td))
            sm = new_authority_state_machine(fx["run_id"])
            _manifest_path, mat = advance_to_materialized(fx, sm)
            tracker = PhaseDeadlineTracker.begin(scratch_benchmark_candidate_policy())
            grant_capture(sm, fx["lease"], tracker, mat)
            original = fx["snapshot_recompute_fn"]

            def drift_recompute(**kwargs):
                Path(fx["paths"]["export"]).write_text(
                    '{"id":"mutated"}\n', encoding="utf-8"
                )
                return original(**kwargs)

            with self.assertRaises(R2bV2CaptureCloseError):
                execute_authorized_capture(
                    sm,
                    fx["lease"],
                    tracker,
                    mat,
                    snapshot_recompute_fn=drift_recompute,
                )
            self.assertEqual(sm.state, AuthorityState.QUARANTINED)
            capture_dir = Path(fx["paths"]["capture_dir"])
            self.assertFalse((capture_dir / "corpus_package_manifest.json").exists())
            fx["lease"].release()

    def test_regrant_after_terminal_refused(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            fx = scratch_transaction_fixture(Path(td))
            sm = new_authority_state_machine(fx["run_id"])
            _manifest_path, mat = advance_to_materialized(fx, sm)
            sm.state = AuthorityState.QUARANTINED
            tracker = PhaseDeadlineTracker.begin(scratch_benchmark_candidate_policy())
            with self.assertRaises(AuthorityStateError):
                grant_capture(sm, fx["lease"], tracker, mat)
            fx["lease"].release()

    def test_capture_ordering_final_source_before_marker(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            fx = scratch_transaction_fixture(Path(td))
            sm = new_authority_state_machine(fx["run_id"])
            _manifest_path, mat = advance_to_materialized(fx, sm)
            tracker = PhaseDeadlineTracker.begin(scratch_benchmark_candidate_policy())
            grant_capture(sm, fx["lease"], tracker, mat)
            execute_authorized_capture(
                sm,
                fx["lease"],
                tracker,
                mat,
                snapshot_recompute_fn=fx["snapshot_recompute_fn"],
            )
            history = [entry["to"] for entry in sm.history]
            cap_idx = history.index("CAPTURING")
            final_idx = history.index("FINAL_SOURCE_CHECKED")
            sealed_idx = history.index("SEALED")
            self.assertLess(cap_idx, final_idx)
            self.assertLess(final_idx, sealed_idx)
            fx["lease"].release()

    def test_fresh_process_smoke_transaction(self) -> None:
        repo = Path(__file__).resolve().parents[1]
        proc = subprocess.run(
            [
                sys.executable,
                "-m",
                "pytest",
                "tests/test_r2b_v2_i4_i6.py::R2bV2I6Tests::test_smoke_scratch_transaction",
                "-q",
            ],
            cwd=str(repo),
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(proc.returncode, 0, msg=proc.stdout + proc.stderr)


if __name__ == "__main__":
    unittest.main()

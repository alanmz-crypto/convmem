"""Integration regressions for R2b v2 I5 expiry-safe authority commitment."""
# pylint: disable=duplicate-code

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from eval_corpus.r2b_v2.authority_commit import AuthorityCommitter, PendingLease
from eval_corpus.r2b_v2.authority_state import (
    AuthorityState,
    AuthorityStateError,
    new_authority_state_machine,
)
from eval_corpus.r2b_v2.capture_close import (
    execute_authorized_capture,
    grant_capture,
    release_gate_and_write_release_evidence,
    write_close_evidence,
)
from eval_corpus.r2b_v2.duration_policy import (
    DurationPolicy,
    ManualClock,
    PhaseDeadlineExpired,
    TransactionDeadlineExpired,
)
from eval_corpus.r2b_v2.lease import (
    acquire_r2b_quiescence_lease_physical,
    invalidate_pending_lease,
    release_pending_lease_kernel,
)
from eval_corpus.r2b_v2.quiescence_evidence import QuiescenceEvidenceError
from eval_corpus.r2b_v2.transaction import perform_scratch_acquisition
from eval_corpus.r2b_v2.trusted import _reset_for_tests
from tests.r2b_hermetic import r2b_source_paths
from tests.r2b_v2_helpers import (
    advance_to_materialized,
    foreign_lock_holder_process,
    hermetic_implementation_revision,
    make_test_committer,
    scratch_transaction_fixture,
)


def _tiny_capture_policy(**overrides: float) -> DurationPolicy:
    values = {
        "acquisition_bound": 30.0,
        "hitl_reservation_bound": 30.0,
        "capture_bound": 0.001,
        "release_close_bound": 30.0,
        "transaction_deadline": 60.0,
    }
    values.update(overrides)
    return DurationPolicy(**values)


class R2bV2I5EnforcementTests(unittest.TestCase):
    def setUp(self) -> None:
        _reset_for_tests()

    def _advance_to_capture_granted(self, fx: dict, policy: DurationPolicy):
        sm = new_authority_state_machine(fx["run_id"])
        clock = ManualClock()
        committer = make_test_committer(fx["run_id"], policy, sm=sm, clock=clock)
        _manifest_path, mat, committer = advance_to_materialized(fx, sm, committer)
        grant_capture(committer, fx["lease"], mat)
        return sm, mat, committer, clock

    def test_capture_overrun_fails_closed_via_execute_authorized_capture(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            fx = scratch_transaction_fixture(Path(td))
            sm, mat, committer, clock = self._advance_to_capture_granted(
                fx, _tiny_capture_policy()
            )
            original_prepare = __import__(
                "eval_corpus.r2b_v2.scratch_capture",
                fromlist=["prepare_scratch_capture_artifacts"],
            ).prepare_scratch_capture_artifacts

            def prepare_and_expire(materialized):
                clock.advance(0.01)
                return original_prepare(materialized)

            with mock.patch(
                "eval_corpus.r2b_v2.capture_close.prepare_scratch_capture_artifacts",
                side_effect=prepare_and_expire,
            ):
                with self.assertRaises(PhaseDeadlineExpired) as ctx:
                    execute_authorized_capture(
                        committer,
                        fx["lease"],
                        mat,
                        snapshot_recompute_fn=fx["snapshot_recompute_fn"],
                    )
            self.assertEqual(ctx.exception.phase, "capture")
            self.assertTrue(committer.tracker.consumed)
            self.assertNotEqual(sm.state, AuthorityState.SEALED)
            capture_dir = Path(fx["paths"]["capture_dir"])
            self.assertFalse((capture_dir / "corpus_package_manifest.json").exists())
            self.assertEqual(sm.state, AuthorityState.QUARANTINED)
            fx["lease"].release()

    def test_transaction_deadline_during_capture_blocks_sealed(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            fx = scratch_transaction_fixture(Path(td))
            policy = DurationPolicy(30.0, 30.0, 1.0, 1.0, 5.0)
            sm, mat, committer, clock = self._advance_to_capture_granted(fx, policy)
            clock.set(committer.tracker.absolute_deadline())
            with self.assertRaises(TransactionDeadlineExpired):
                execute_authorized_capture(
                    committer,
                    fx["lease"],
                    mat,
                    snapshot_recompute_fn=fx["snapshot_recompute_fn"],
                )
            self.assertTrue(committer.tracker.consumed)
            self.assertNotEqual(sm.state, AuthorityState.SEALED)
            self.assertFalse(
                (Path(fx["paths"]["capture_dir"]) / "corpus_package_manifest.json").exists()
            )
            fx["lease"].release()

    def test_acquisition_overrun_fails_without_transaction_authority(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            run_id = "acq-overrun"
            rev = "acq-overrun-rev"
            paths = r2b_source_paths(root, run_id=run_id)
            gate = root / "bundle" / "gate.lock"
            gate.parent.mkdir(parents=True, exist_ok=True)
            gate.touch()
            proc, ready, done = foreign_lock_holder_process(gate)
            proc.start()
            ready.get(timeout=5)
            policy = DurationPolicy(
                acquisition_bound=0.05,
                hitl_reservation_bound=30.0,
                capture_bound=30.0,
                release_close_bound=30.0,
                transaction_deadline=60.0,
            )
            committer = make_test_committer(run_id, policy)
            revision = hermetic_implementation_revision(rev)
            with self.assertRaises(PhaseDeadlineExpired):
                perform_scratch_acquisition(
                    committer,
                    chroma_dir=Path(paths["chroma_dir"]),
                    processed_path=Path(paths["processed"]),
                    export_root=Path(paths["export"]).parent,
                    gate_path=gate,
                    open_evidence_digest="open-acq",
                    implementation_revision=revision,
                )
            self.assertTrue(committer.tracker.consumed)
            done.put("release")
            proc.join(timeout=10)

    def test_close_evidence_overrun_does_not_close(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            fx = scratch_transaction_fixture(Path(td))
            sm = new_authority_state_machine(fx["run_id"])
            sm.state = AuthorityState.SEALED
            clock = ManualClock()
            policy = DurationPolicy(30.0, 30.0, 30.0, 0.001, 60.0)
            committer = make_test_committer(fx["run_id"], policy, sm=sm, clock=clock)
            committer.tracker.start_phase_once("release_close")
            clock.advance(0.01)
            with self.assertRaises(PhaseDeadlineExpired):
                write_close_evidence(
                    committer,
                    fx["lease"],
                    fx["auth_dir"],
                    marker_result="ok",
                    final_source_result="ok",
                    preceding_digests={},
                    gate_identity=fx["gate_identity"],
                )
            self.assertEqual(sm.state, AuthorityState.SEALED)
            self.assertTrue(committer.tracker.consumed)
            fx["lease"].release()

    def test_kernel_release_overrun_quarantines_without_closed(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            fx = scratch_transaction_fixture(Path(td))
            sm = new_authority_state_machine(fx["run_id"])
            sm.state = AuthorityState.CLOSING
            clock = ManualClock()
            policy = DurationPolicy(30.0, 30.0, 30.0, 0.001, 60.0)
            committer = make_test_committer(fx["run_id"], policy, sm=sm, clock=clock)
            committer.tracker.start_phase_once("release_close")
            clock.advance(0.01)

            original_release = type(fx["lease"]).release

            def slow_release(self_lease) -> None:
                clock.advance(0.01)
                return original_release(self_lease)

            with mock.patch.object(type(fx["lease"]), "release", slow_release):
                with self.assertRaises(PhaseDeadlineExpired):
                    release_gate_and_write_release_evidence(
                        committer,
                        fx["lease"],
                        fx["auth_dir"],
                        close_digest="d" * 64,
                    )
            self.assertEqual(sm.state, AuthorityState.QUARANTINED)
            release_path = fx["auth_dir"] / "quiescence-release.json"
            self.assertTrue(release_path.exists())
            body = json.loads(release_path.read_text(encoding="utf-8"))
            self.assertTrue(body.get("kernel_released"))
            self.assertEqual(body.get("closure_outcome"), "deadline_expired")

    def test_release_evidence_overrun_quarantines_after_kernel_release(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            fx = scratch_transaction_fixture(Path(td))
            sm = new_authority_state_machine(fx["run_id"])
            sm.state = AuthorityState.CLOSING
            clock = ManualClock()
            policy = DurationPolicy(30.0, 30.0, 30.0, 0.05, 60.0)
            committer = make_test_committer(fx["run_id"], policy, sm=sm, clock=clock)
            committer.tracker.start_phase_once("release_close")

            original_release = type(fx["lease"]).release

            def release_then_expire(self_lease) -> None:
                original_release(self_lease)
                clock.advance(0.06)

            with mock.patch.object(type(fx["lease"]), "release", release_then_expire):
                with self.assertRaises(PhaseDeadlineExpired):
                    release_gate_and_write_release_evidence(
                        committer,
                        fx["lease"],
                        fx["auth_dir"],
                        close_digest="d" * 64,
                    )
            self.assertEqual(sm.state, AuthorityState.QUARANTINED)
            release_path = fx["auth_dir"] / "quiescence-release.json"
            self.assertTrue(release_path.exists())
            body = json.loads(release_path.read_text(encoding="utf-8"))
            self.assertTrue(body.get("kernel_released"))

    def test_hitl_bound_still_enforced_after_reservation(self) -> None:
        policy = DurationPolicy(
            acquisition_bound=30.0,
            hitl_reservation_bound=0.001,
            capture_bound=30.0,
            release_close_bound=30.0,
            transaction_deadline=60.0,
        )
        clock = ManualClock()
        tracker = policy and __import__(
            "eval_corpus.r2b_v2.duration_policy",
            fromlist=["PhaseDeadlineTracker"],
        ).PhaseDeadlineTracker.begin(policy, clock=clock)
        tracker.start_phase_once("hitl")
        clock.advance(0.01)
        with self.assertRaises(PhaseDeadlineExpired) as ctx:
            tracker.check_phase_bound("hitl", policy.hitl_reservation_bound)
        self.assertEqual(ctx.exception.phase, "hitl")

    def test_raw_guarded_transition_rejected(self) -> None:
        sm = new_authority_state_machine("guard-test")
        sm.transition(AuthorityState.PREPARED, reason="prep")
        sm.transition(AuthorityState.Q_AUTHORIZED, reason="auth")
        sm.transition(AuthorityState.Q_ACQUIRING, reason="acq")
        with self.assertRaises(AuthorityStateError):
            sm.transition(AuthorityState.Q_HELD, reason="bypass")

    def test_evidence_rejects_caller_deadline_state(self) -> None:
        from eval_corpus.r2b_v2.quiescence_evidence import write_quiescence_close

        with tempfile.TemporaryDirectory() as td:
            with self.assertRaises(QuiescenceEvidenceError):
                write_quiescence_close(
                    Path(td) / "close.json",
                    run_id="r",
                    terminal_disposition="SEALED",
                    marker_result="ok",
                    final_source_result="ok",
                    deadline_observation={"deadline_state": "within_budget"},
                    gate_identity="g",
                    release_intent=True,
                    preceding_digests={},
                )

    def test_phase_restart_rejected(self) -> None:
        policy = DurationPolicy(1.0, 1.0, 1.0, 1.0, 10.0)
        tracker = __import__(
            "eval_corpus.r2b_v2.duration_policy",
            fromlist=["PhaseDeadlineTracker"],
        ).PhaseDeadlineTracker.begin(policy)
        tracker.start_phase_once("hitl")
        with self.assertRaises(Exception):
            tracker.start_phase_once("hitl")

    def test_lease_deadline_equals_tracker_absolute_deadline(self) -> None:
        policy = DurationPolicy(30.0, 30.0, 30.0, 30.0, 45.0)
        tracker = __import__(
            "eval_corpus.r2b_v2.duration_policy",
            fromlist=["PhaseDeadlineTracker"],
        ).PhaseDeadlineTracker.begin(policy)
        absolute = tracker.absolute_deadline()
        with tempfile.TemporaryDirectory() as td:
            gate = Path(td) / "gate.lock"
            gate.touch()
            holder = acquire_r2b_quiescence_lease_physical(
                run_id="lease-eq",
                grant_digest="grant-eq",
                authority_digest="auth-eq",
                test_lock_path=gate,
                writer_coverage_digest="cov",
                open_evidence_digest="open",
                monotonic_deadline=absolute,
                bound_source_paths=("/tmp/a",),
                timeout_ms=5000,
                implementation_revision=hermetic_implementation_revision("lease-eq"),
            )
            self.assertEqual(holder.bindings.monotonic_deadline, absolute)
            invalidate_pending_lease(holder)
            holder._custodian.release()  # pylint: disable=protected-access


if __name__ == "__main__":
    unittest.main()

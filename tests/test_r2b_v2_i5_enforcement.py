"""Integration regressions for R2b v2 I5 hard-bound enforcement."""
# pylint: disable=duplicate-code

from __future__ import annotations

import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

from eval_corpus.r2b_v2.authority_state import (
    AuthorityState,
    new_authority_state_machine,
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
    TransactionDeadlineExpired,
)
from eval_corpus.r2b_v2.scratch_capture import prepare_scratch_capture_artifacts
from eval_corpus.r2b_v2.transaction import perform_scratch_acquisition
from eval_corpus.r2b_v2.trusted import _reset_for_tests
from tests.r2b_hermetic import r2b_source_paths
from tests.r2b_v2_helpers import (
    advance_to_materialized,
    foreign_lock_holder_process,
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
        _manifest_path, mat = advance_to_materialized(fx, sm)
        tracker = PhaseDeadlineTracker.begin(policy)
        grant_capture(sm, fx["lease"], tracker, mat)
        return sm, mat, tracker

    def test_capture_overrun_fails_closed_via_execute_authorized_capture(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            fx = scratch_transaction_fixture(Path(td))
            sm, mat, tracker = self._advance_to_capture_granted(
                fx, _tiny_capture_policy()
            )
            original = prepare_scratch_capture_artifacts

            def slow_prepare(materialized):
                time.sleep(0.03)
                return original(materialized)

            with mock.patch(
                "eval_corpus.r2b_v2.capture_close.prepare_scratch_capture_artifacts",
                side_effect=slow_prepare,
            ):
                with self.assertRaises(PhaseDeadlineExpired) as ctx:
                    execute_authorized_capture(
                        sm,
                        fx["lease"],
                        tracker,
                        mat,
                        snapshot_recompute_fn=fx["snapshot_recompute_fn"],
                    )
            self.assertEqual(ctx.exception.phase, "capture")
            self.assertTrue(tracker.consumed)
            self.assertNotEqual(sm.state, AuthorityState.SEALED)
            capture_dir = Path(fx["paths"]["capture_dir"])
            self.assertFalse((capture_dir / "corpus_package_manifest.json").exists())
            self.assertEqual(sm.state, AuthorityState.QUARANTINED)
            fx["lease"].release()

    def test_transaction_deadline_during_capture_blocks_sealed(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            fx = scratch_transaction_fixture(Path(td))
            sm, mat, tracker = self._advance_to_capture_granted(
                fx,
                DurationPolicy(
                    acquisition_bound=30.0,
                    hitl_reservation_bound=30.0,
                    capture_bound=30.0,
                    release_close_bound=30.0,
                    transaction_deadline=120.0,
                ),
            )
            tracker.transaction_start = time.monotonic() - 121.0
            with self.assertRaises(TransactionDeadlineExpired):
                execute_authorized_capture(
                    sm,
                    fx["lease"],
                    tracker,
                    mat,
                    snapshot_recompute_fn=fx["snapshot_recompute_fn"],
                )
            self.assertTrue(tracker.consumed)
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
            tracker = PhaseDeadlineTracker.begin(policy)
            from tests.r2b_v2_helpers import hermetic_implementation_revision

            revision = hermetic_implementation_revision(rev)
            with self.assertRaises(PhaseDeadlineExpired):
                perform_scratch_acquisition(
                    tracker,
                    run_id=run_id,
                    chroma_dir=Path(paths["chroma_dir"]),
                    processed_path=Path(paths["processed"]),
                    export_root=Path(paths["export"]).parent,
                    gate_path=gate,
                    open_evidence_digest="open-acq",
                    implementation_revision=revision,
                )
            self.assertTrue(tracker.consumed)
            done.put("release")
            proc.join(timeout=10)

    def test_close_evidence_overrun_does_not_close(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            fx = scratch_transaction_fixture(Path(td))
            sm = new_authority_state_machine(fx["run_id"])
            sm.state = AuthorityState.SEALED
            tracker = PhaseDeadlineTracker.begin(
                DurationPolicy(30.0, 30.0, 30.0, 0.001, 60.0)
            )

            def slow_close(*args, **kwargs):
                time.sleep(0.03)
                return "c" * 64

            with mock.patch(
                "eval_corpus.r2b_v2.capture_close.write_quiescence_close",
                side_effect=slow_close,
            ):
                with self.assertRaises(PhaseDeadlineExpired):
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
            self.assertEqual(sm.state, AuthorityState.SEALED)
            self.assertTrue(tracker.consumed)
            fx["lease"].release()

    def test_kernel_release_overrun_quarantines_without_closed(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            fx = scratch_transaction_fixture(Path(td))
            sm = new_authority_state_machine(fx["run_id"])
            sm.state = AuthorityState.CLOSING
            tracker = PhaseDeadlineTracker.begin(
                DurationPolicy(30.0, 30.0, 30.0, 0.001, 60.0)
            )
            tracker.start_phase("release_close")

            original_release = type(fx["lease"]).release

            def slow_release(self_lease) -> None:
                time.sleep(0.03)
                return original_release(self_lease)

            with mock.patch.object(type(fx["lease"]), "release", slow_release):
                with self.assertRaises(PhaseDeadlineExpired):
                    release_gate_and_write_release_evidence(
                        sm,
                        fx["lease"],
                        tracker,
                        fx["auth_dir"],
                        close_digest="d" * 64,
                    )
            self.assertEqual(sm.state, AuthorityState.QUARANTINED)
            self.assertFalse((fx["auth_dir"] / "quiescence-release.json").exists())

    def test_release_evidence_overrun_quarantines_after_kernel_release(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            fx = scratch_transaction_fixture(Path(td))
            sm = new_authority_state_machine(fx["run_id"])
            sm.state = AuthorityState.CLOSING
            tracker = PhaseDeadlineTracker.begin(
                DurationPolicy(30.0, 30.0, 30.0, 0.05, 60.0)
            )
            tracker.start_phase("release_close")

            def slow_release_evidence(*args, **kwargs):
                time.sleep(0.04)
                return "r" * 64

            with mock.patch(
                "eval_corpus.r2b_v2.capture_close.write_quiescence_release",
                side_effect=slow_release_evidence,
            ):
                with self.assertRaises(PhaseDeadlineExpired):
                    release_gate_and_write_release_evidence(
                        sm,
                        fx["lease"],
                        tracker,
                        fx["auth_dir"],
                        close_digest="d" * 64,
                    )
            self.assertEqual(sm.state, AuthorityState.QUARANTINED)
            self.assertFalse((fx["auth_dir"] / "quiescence-release.json").exists())

    def test_hitl_bound_still_enforced_after_reservation(self) -> None:
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
        with self.assertRaises(PhaseDeadlineExpired) as ctx:
            tracker.check_phase_bound("hitl", policy.hitl_reservation_bound)
        self.assertEqual(ctx.exception.phase, "hitl")


if __name__ == "__main__":
    unittest.main()

"""Hermetic I4–I6 scratch transaction tests for R2b v2."""

from __future__ import annotations

import json
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

from chroma_write_store import DEFAULT_WRITER_LOCK
from eval_corpus.r2b_v2.authority_state import (
    AuthorityState,
    AuthorityStateError,
    AuthorityStateMachine,
    new_authority_state_machine,
    transition_to_coverage_proven,
    transition_to_q_held,
)
from eval_corpus.r2b_v2.capture_close import (
    R2bV2CaptureCloseError,
    execute_authorized_capture,
    grant_capture,
    release_gate_and_write_release_evidence,
)
from eval_corpus.r2b_v2.duration_policy import (
    DurationPolicy,
    InsufficientRemainingBudget,
    PhaseDeadlineTracker,
    TransactionDeadlineExpired,
)
from eval_corpus.r2b_v2.lease import R2bQuiescenceLeaseError
from eval_corpus.r2b_v2.materialization import materialize_v2_packet
from eval_corpus.r2b_v2.packet import (
    R2bV2PacketError,
    accept_capture_packet,
    compute_trusted_snapshot,
    draft_capture_packet,
    refuse_sidecar_before_accept,
    transition_snapshot_bound,
)
from eval_corpus.r2b_v2.scratch_isolation import ScratchIsolationError, assert_scratch_path
from eval_corpus.r2b_v2.transaction import run_scratch_transaction
from eval_corpus.r2b_v2.trusted import _reset_for_tests
from tests.r2b_v2_helpers import (
    advance_to_materialized,
    obtain_source_authority,
    scratch_benchmark_candidate_policy,
    scratch_transaction_fixture,
)


def _advance_to_coverage_proven(
    sm: AuthorityStateMachine,
    lease,
    trusted,
) -> None:
    sm.transition(AuthorityState.PREPARED, reason="test prepare")
    sm.transition(AuthorityState.Q_AUTHORIZED, reason="test authorize")
    transition_to_q_held(sm, lease, reason="test held")
    transition_to_coverage_proven(sm, lease, trusted, reason="test coverage")


class R2bV2I4Tests(unittest.TestCase):
    def setUp(self) -> None:
        _reset_for_tests()

    def test_draft_packet_without_sidecar(self):
        with tempfile.TemporaryDirectory() as td:
            fx = scratch_transaction_fixture(Path(td))
            sm = new_authority_state_machine(fx["run_id"])
            _advance_to_coverage_proven(sm, fx["lease"], fx["trusted"])
            transition_snapshot_bound(
                sm,
                fx["lease"],
                obtain_source_authority(fx["lease"], fx["trusted"]),
                reason="bind",
            )
            snap = compute_trusted_snapshot(
                fx["lease"],
                export=Path(fx["paths"]["export"]),
                processed=Path(fx["paths"]["processed"]),
                chroma_dir=Path(fx["paths"]["chroma_dir"]),
                snapshot_recompute_fn=fx["snapshot_recompute_fn"],
            )
            manifest_path = draft_capture_packet(
                sm,
                fx["lease"],
                fx["trusted"],
                auth_dir=fx["auth_dir"],
                paths=fx["paths"],
                source_snapshot=snap,
                duration_policy=scratch_benchmark_candidate_policy(),
                future_argv=fx["future_argv"],
                open_evidence_digest=fx["open_evidence_digest"],
                gate_identity=fx["gate_identity"],
                implementation_revision=fx["implementation_revision"],
            )
            self.assertTrue(manifest_path.is_file())
            refuse_sidecar_before_accept(manifest_path)
            fx["lease"].release()

    def test_refuse_target_pre_existence(self):
        with tempfile.TemporaryDirectory() as td:
            fx = scratch_transaction_fixture(Path(td))
            Path(fx["paths"]["capture_dir"]).mkdir(parents=True)
            sm = new_authority_state_machine(fx["run_id"])
            _advance_to_coverage_proven(sm, fx["lease"], fx["trusted"])
            transition_snapshot_bound(
                sm,
                fx["lease"],
                obtain_source_authority(fx["lease"], fx["trusted"]),
                reason="bind",
            )
            with self.assertRaises(R2bV2PacketError):
                draft_capture_packet(
                    sm,
                    fx["lease"],
                    fx["trusted"],
                    auth_dir=fx["auth_dir"],
                    paths=fx["paths"],
                    source_snapshot=fx["snapshot_recompute_fn"](
                        export=Path(fx["paths"]["export"]),
                        processed=Path(fx["paths"]["processed"]),
                        chroma_dir=Path(fx["paths"]["chroma_dir"]),
                    ),
                    duration_policy=scratch_benchmark_candidate_policy(),
                    future_argv=fx["future_argv"],
                    open_evidence_digest=fx["open_evidence_digest"],
                    gate_identity=fx["gate_identity"],
                    implementation_revision=fx["implementation_revision"],
                )
            fx["lease"].release()

    def test_source_mutation_after_snapshot_refused(self):
        with tempfile.TemporaryDirectory() as td:
            fx = scratch_transaction_fixture(Path(td))
            export = Path(fx["paths"]["export"])
            snap = fx["snapshot_recompute_fn"](
                export=export,
                processed=Path(fx["paths"]["processed"]),
                chroma_dir=Path(fx["paths"]["chroma_dir"]),
            )
            export.write_text('{"id":"mutated"}\n', encoding="utf-8")
            sm = new_authority_state_machine(fx["run_id"])
            _advance_to_coverage_proven(sm, fx["lease"], fx["trusted"])
            transition_snapshot_bound(
                sm,
                fx["lease"],
                obtain_source_authority(fx["lease"], fx["trusted"]),
                reason="bind",
            )
            manifest_path = draft_capture_packet(
                sm,
                fx["lease"],
                fx["trusted"],
                auth_dir=fx["auth_dir"],
                paths=fx["paths"],
                source_snapshot=snap,
                duration_policy=scratch_benchmark_candidate_policy(),
                future_argv=fx["future_argv"],
                open_evidence_digest=fx["open_evidence_digest"],
                gate_identity=fx["gate_identity"],
                implementation_revision=fx["implementation_revision"],
            )
            accept_capture_packet(sm, fx["lease"], manifest_path)
            with self.assertRaises(Exception):
                materialize_v2_packet(
                    sm,
                    fx["lease"],
                    manifest_path,
                    runtime=fx["runtime"],
                    snapshot_recompute_fn=fx["snapshot_recompute_fn"],
                    restic_gate_fn=lambda: None,
                )
            fx["lease"].release()


class R2bV2I5Tests(unittest.TestCase):
    def test_insufficient_remaining_budget_before_grant(self):
        policy = DurationPolicy(
            acquisition_bound=5.0,
            hitl_reservation_bound=5.0,
            capture_bound=100.0,
            release_close_bound=100.0,
            transaction_deadline=10.0,
        )
        tracker = PhaseDeadlineTracker.begin(policy)
        time.sleep(0.05)
        with self.assertRaises(InsufficientRemainingBudget):
            tracker.prove_remaining_budget_for_grant()

    def test_transaction_deadline_expiry(self):
        policy = DurationPolicy(
            acquisition_bound=1.0,
            hitl_reservation_bound=1.0,
            capture_bound=1.0,
            release_close_bound=1.0,
            transaction_deadline=0.01,
        )
        tracker = PhaseDeadlineTracker.begin(policy)
        time.sleep(0.02)
        with self.assertRaises(TransactionDeadlineExpired):
            tracker.check_transaction_deadline()

    def test_no_in_place_extension(self):
        from eval_corpus.r2b_v2.lease import extend_lease_deadline

        with self.assertRaises(R2bQuiescenceLeaseError):
            extend_lease_deadline()


class R2bV2I6Tests(unittest.TestCase):
    def setUp(self) -> None:
        _reset_for_tests()

    def test_smoke_scratch_transaction(self):
        with tempfile.TemporaryDirectory() as td:
            fx = scratch_transaction_fixture(Path(td))
            try:
                result = run_scratch_transaction(
                    root=fx["root"],
                    run_id=fx["run_id"],
                    lease=fx["lease"],
                    trusted_coverage=fx["trusted"],
                    paths=fx["paths"],
                    auth_dir=fx["auth_dir"],
                    duration_policy=scratch_benchmark_candidate_policy(),
                    open_evidence_digest=fx["open_evidence_digest"],
                    gate_identity=fx["gate_identity"],
                    implementation_revision=fx["implementation_revision"],
                    future_argv=fx["future_argv"],
                    snapshot_recompute_fn=fx["snapshot_recompute_fn"],
                    runtime=fx["runtime"],
                )
            except Exception:
                fx["lease"].release()
                raise
            self.assertEqual(result.final_state, AuthorityState.CLOSED)
            self.assertTrue(Path(fx["paths"]["capture_dir"]).is_dir())
            close_path = fx["auth_dir"] / "quiescence-close.json"
            release_path = fx["auth_dir"] / "quiescence-release.json"
            self.assertTrue(close_path.is_file())
            self.assertTrue(release_path.is_file())
            close_body = json.loads(close_path.read_text(encoding="utf-8"))
            self.assertFalse(close_body["release_success_claimed"])

    def test_materialization_does_not_create_capture_dir(self):
        with tempfile.TemporaryDirectory() as td:
            fx = scratch_transaction_fixture(Path(td))
            sm = new_authority_state_machine(fx["run_id"])
            _advance_to_coverage_proven(sm, fx["lease"], fx["trusted"])
            transition_snapshot_bound(
                sm,
                fx["lease"],
                obtain_source_authority(fx["lease"], fx["trusted"]),
                reason="b",
            )
            snap = fx["snapshot_recompute_fn"](
                export=Path(fx["paths"]["export"]),
                processed=Path(fx["paths"]["processed"]),
                chroma_dir=Path(fx["paths"]["chroma_dir"]),
            )
            manifest_path = draft_capture_packet(
                sm,
                fx["lease"],
                fx["trusted"],
                auth_dir=fx["auth_dir"],
                paths=fx["paths"],
                source_snapshot=snap,
                duration_policy=scratch_benchmark_candidate_policy(),
                future_argv=fx["future_argv"],
                open_evidence_digest=fx["open_evidence_digest"],
                gate_identity=fx["gate_identity"],
                implementation_revision=fx["implementation_revision"],
            )
            accept_capture_packet(sm, fx["lease"], manifest_path)
            materialize_v2_packet(
                sm,
                fx["lease"],
                manifest_path,
                runtime=fx["runtime"],
                snapshot_recompute_fn=fx["snapshot_recompute_fn"],
                restic_gate_fn=lambda: None,
            )
            self.assertFalse(Path(fx["paths"]["capture_dir"]).exists())
            fx["lease"].release()


class R2bV2FailureInjectionTests(unittest.TestCase):
    def setUp(self) -> None:
        _reset_for_tests()

    def test_second_capture_attempt_refused(self):
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
            with self.assertRaises(AuthorityStateError):
                execute_authorized_capture(
                    sm,
                    fx["lease"],
                    tracker,
                    mat,
                    snapshot_recompute_fn=fx["snapshot_recompute_fn"],
                )
            fx["lease"].release()

    def test_release_failure_quarantines(self):
        with tempfile.TemporaryDirectory() as td:
            fx = scratch_transaction_fixture(Path(td))
            sm = new_authority_state_machine(fx["run_id"])
            sm.state = AuthorityState.CLOSING
            tracker = PhaseDeadlineTracker.begin(scratch_benchmark_candidate_policy())
            tracker.start_phase("release_close")
            with mock.patch(
                "eval_corpus.r2b_v2.lease.R2bQuiescenceLease.release",
                side_effect=RuntimeError("release failed"),
            ):
                with self.assertRaises(R2bV2CaptureCloseError):
                    release_gate_and_write_release_evidence(
                        sm,
                        fx["lease"],
                        tracker,
                        fx["auth_dir"],
                        close_digest="abc",
                    )
            self.assertEqual(sm.state, AuthorityState.QUARANTINED)
            fx["lease"].release()


class R2bV2ScratchIsolationTests(unittest.TestCase):
    def test_production_gate_path_rejected(self):
        with self.assertRaises(ScratchIsolationError):
            assert_scratch_path(DEFAULT_WRITER_LOCK, label="gate")

    def test_scratch_paths_under_temp_allowed(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "gate.lock"
            assert_scratch_path(p, label="gate")


if __name__ == "__main__":
    unittest.main()

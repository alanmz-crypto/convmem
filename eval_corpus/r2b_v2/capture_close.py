"""R2b v2 capture, close, and release evidence path (I6)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from eval_corpus.r2b_capture_auth import compare_source_snapshots
from eval_corpus.r2b_v2.authority_state import (
    AuthorityState,
    AuthorityStateError,
    AuthorityStateMachine,
)
from eval_corpus.r2b_v2.duration_policy import (
    PhaseDeadlineExpired,
    PhaseDeadlineTracker,
    TransactionDeadlineExpired,
)
from eval_corpus.r2b_v2.lease import R2bQuiescenceLease, verify_r2b_quiescence_lease
from eval_corpus.r2b_v2.materialization import V2MaterializationResult
from eval_corpus.r2b_v2.quiescence_evidence import (
    write_quiescence_close,
    write_quiescence_release,
)
from eval_corpus.r2b_v2.scratch_capture import (
    prepare_scratch_capture_artifacts,
    publish_scratch_completion_marker,
)
from eval_corpus.r2b_v2.scratch_isolation import assert_scratch_path

SnapshotRecomputeFn = Callable[..., dict[str, Any]]


class R2bV2CaptureCloseError(RuntimeError):
    """Capture, close, or release failure."""


def _enforce_phase_elapsed(
    tracker: PhaseDeadlineTracker,
    phase: str,
    bound: float,
) -> None:
    """Fail closed when a named phase or the absolute transaction deadline expired."""
    tracker.check_phase_bound(phase, bound)


def _handle_capture_deadline_failure(
    machine: AuthorityStateMachine,
    tracker: PhaseDeadlineTracker,
    capture_dir: Path | None,
    *,
    reason: str,
) -> None:
    tracker.mark_consumed(reason=reason)
    if capture_dir is not None:
        _remove_marker_if_present(capture_dir)
    if machine.state in (
        AuthorityState.CAPTURING,
        AuthorityState.FINAL_SOURCE_CHECKED,
    ):
        machine.quarantine(reason=reason)


def _handle_release_close_deadline_failure(
    machine: AuthorityStateMachine,
    tracker: PhaseDeadlineTracker,
    *,
    reason: str,
    kernel_released: bool,
) -> None:
    tracker.mark_consumed(reason=reason)
    if kernel_released or machine.state == AuthorityState.CLOSING:
        machine.quarantine(reason=reason)


@dataclass(frozen=True)
class CaptureCloseResult:
    capture_result: dict[str, Any]
    close_digest: str
    release_digest: str | None
    terminal_state: AuthorityState


def grant_capture(
    machine: AuthorityStateMachine,
    lease: R2bQuiescenceLease,
    tracker: PhaseDeadlineTracker,
    materialized: V2MaterializationResult,
    *,
    reason: str = "Ryan ACCEPT AND GRANT",
) -> V2MaterializationResult:
    verify_r2b_quiescence_lease(lease, expected_run_id=machine.run_id)
    lease.verify()
    tracker.prove_remaining_budget_for_grant()
    if machine.state != AuthorityState.MATERIALIZED:
        raise AuthorityStateError(
            f"CAPTURE_GRANTED requires MATERIALIZED, got {machine.state.value}"
        )
    if materialized.bindings.capture_dir.exists():
        raise R2bV2CaptureCloseError("capture_dir must be absent before grant")
    machine.transition(AuthorityState.CAPTURE_GRANTED, reason=reason)
    return materialized


def execute_authorized_capture(
    machine: AuthorityStateMachine,
    lease: R2bQuiescenceLease,
    tracker: PhaseDeadlineTracker,
    materialized: V2MaterializationResult,
    *,
    snapshot_recompute_fn: SnapshotRecomputeFn,
) -> dict[str, Any]:
    """CAPTURING → final source check → marker last → SEALED."""
    verify_r2b_quiescence_lease(lease, expected_run_id=machine.run_id)
    lease.verify()
    tracker.start_phase("capture")
    if machine.state != AuthorityState.CAPTURE_GRANTED:
        raise AuthorityStateError(
            f"CAPTURING requires CAPTURE_GRANTED, got {machine.state.value}"
        )
    bindings = materialized.bindings
    assert_scratch_path(bindings.capture_dir, label="capture_dir")
    if bindings.capture_dir.exists():
        raise R2bV2CaptureCloseError("second capture attempt refused")
    machine.transition(AuthorityState.CAPTURING, reason="begin authorized capture")
    capture_dir: Path | None = None
    try:
        prepared = prepare_scratch_capture_artifacts(materialized)
        capture_dir = Path(prepared["capture_dir"])
        _enforce_phase_elapsed(
            tracker, "capture", tracker.policy.capture_bound
        )

        final_source_recompute(
            machine,
            lease,
            bindings.source_snapshot,
            export=bindings.export,
            processed=bindings.processed,
            chroma_dir=bindings.chroma_dir,
            snapshot_recompute_fn=snapshot_recompute_fn,
        )
        _enforce_phase_elapsed(
            tracker, "capture", tracker.policy.capture_bound
        )

        _enforce_phase_elapsed(
            tracker, "capture", tracker.policy.capture_bound
        )
        sealed = publish_scratch_completion_marker(
            materialized, capture_dir=capture_dir
        )
        _enforce_phase_elapsed(
            tracker, "capture", tracker.policy.capture_bound
        )
        machine.transition(AuthorityState.SEALED, reason="marker last")
        return {**prepared, **sealed}
    except (PhaseDeadlineExpired, TransactionDeadlineExpired) as exc:
        _handle_capture_deadline_failure(
            machine,
            tracker,
            capture_dir,
            reason=f"capture deadline expired: {exc}",
        )
        raise
    except R2bV2CaptureCloseError:
        if capture_dir is not None:
            _remove_marker_if_present(capture_dir)
        raise


def _remove_marker_if_present(capture_dir: Path) -> None:
    marker = capture_dir / "corpus_package_manifest.json"
    if marker.exists():
        marker.unlink()


def final_source_recompute(
    machine: AuthorityStateMachine,
    lease: R2bQuiescenceLease,
    approved_snapshot: dict[str, Any],
    *,
    export: Path,
    processed: Path,
    chroma_dir: Path,
    snapshot_recompute_fn: SnapshotRecomputeFn,
) -> None:
    verify_r2b_quiescence_lease(lease, expected_run_id=machine.run_id)
    lease.verify()
    if machine.state != AuthorityState.CAPTURING:
        raise AuthorityStateError(
            f"final source check requires CAPTURING, got {machine.state.value}"
        )
    live = snapshot_recompute_fn(
        export=export, processed=processed, chroma_dir=chroma_dir
    )
    try:
        compare_source_snapshots(approved_snapshot, live)
    except PermissionError as exc:
        machine.quarantine(reason="source drift during capture")
        raise R2bV2CaptureCloseError(f"source drift: {exc}") from exc
    machine.transition(
        AuthorityState.FINAL_SOURCE_CHECKED, reason="final source matched"
    )


def write_close_evidence(
    machine: AuthorityStateMachine,
    lease: R2bQuiescenceLease,
    tracker: PhaseDeadlineTracker,
    auth_dir: Path,
    *,
    marker_result: str,
    final_source_result: str,
    preceding_digests: dict[str, str],
    gate_identity: str,
) -> str:
    verify_r2b_quiescence_lease(lease, expected_run_id=machine.run_id)
    lease.verify()
    tracker.start_phase("release_close")
    if machine.state != AuthorityState.SEALED:
        raise AuthorityStateError(
            f"CLOSING requires SEALED, got {machine.state.value}"
        )
    close_path = auth_dir / "quiescence-close.json"
    try:
        close_digest = write_quiescence_close(
            close_path,
            run_id=machine.run_id,
            terminal_disposition=machine.state.value,
            marker_result=marker_result,
            final_source_result=final_source_result,
            deadline_state="within_budget" if not tracker.consumed else "consumed",
            gate_identity=gate_identity,
            release_intent=True,
            preceding_digests=preceding_digests,
        )
        _enforce_phase_elapsed(
            tracker, "release_close", tracker.policy.release_close_bound
        )
    except (PhaseDeadlineExpired, TransactionDeadlineExpired) as exc:
        _handle_release_close_deadline_failure(
            machine,
            tracker,
            reason=f"release_close deadline during close evidence: {exc}",
            kernel_released=False,
        )
        raise
    machine.transition(AuthorityState.CLOSING, reason="close evidence fsynced")
    return close_digest


def release_gate_and_write_release_evidence(
    machine: AuthorityStateMachine,
    lease: R2bQuiescenceLease,
    tracker: PhaseDeadlineTracker,
    auth_dir: Path,
    *,
    close_digest: str,
) -> str:
    verify_r2b_quiescence_lease(lease, expected_run_id=machine.run_id)
    if machine.state != AuthorityState.CLOSING:
        raise AuthorityStateError(
            f"release requires CLOSING, got {machine.state.value}"
        )
    kernel_released = False
    try:
        try:
            lease.release()
        except Exception as exc:
            machine.quarantine(reason=f"release failure: {exc}")
            raise R2bV2CaptureCloseError(f"release failure: {exc}") from exc
        kernel_released = True
        _enforce_phase_elapsed(
            tracker, "release_close", tracker.policy.release_close_bound
        )

        release_path = auth_dir / "quiescence-release.json"
        release_digest = write_quiescence_release(
            release_path,
            run_id=machine.run_id,
            close_digest=close_digest,
            release_result="released",
            post_release_observation={"gate_released": True},
        )
        _enforce_phase_elapsed(
            tracker, "release_close", tracker.policy.release_close_bound
        )
    except (PhaseDeadlineExpired, TransactionDeadlineExpired) as exc:
        _handle_release_close_deadline_failure(
            machine,
            tracker,
            reason=f"release_close deadline during release: {exc}",
            kernel_released=kernel_released,
        )
        raise
    except R2bV2CaptureCloseError:
        raise
    except Exception as exc:
        machine.quarantine(reason=f"release evidence failure: {exc}")
        raise R2bV2CaptureCloseError(
            f"release evidence failure: {exc}"
        ) from exc
    machine.transition(AuthorityState.CLOSED, reason="release evidence written")
    return release_digest

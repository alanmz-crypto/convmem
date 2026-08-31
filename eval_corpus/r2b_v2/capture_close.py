"""R2b v2 capture, close, and release evidence path (I6)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from eval_corpus.r2b_capture_auth import compare_source_snapshots
from eval_corpus.r2b_v2.authority_state import (
    AuthorityState,
    AuthorityStateError,
    AuthorityStateMachine,
)
from eval_corpus.r2b_v2.duration_policy import (
    PhaseDeadlineTracker,
    PhaseDeadlineExpired,
)
from eval_corpus.r2b_v2.lease import R2bQuiescenceLease, verify_r2b_quiescence_lease
from eval_corpus.r2b_v2.materialization import V2MaterializationResult
from eval_corpus.r2b_v2.scratch_capture import run_scratch_v2_capture
from eval_corpus.r2b_v2.quiescence_evidence import (
    write_quiescence_close,
    write_quiescence_release,
)
from eval_corpus.r2b_v2.scratch_isolation import assert_scratch_path


class R2bV2CaptureCloseError(RuntimeError):
    """Capture, close, or release failure."""


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
) -> dict[str, Any]:
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
    try:
        tracker.check_phase_bound("capture", tracker.policy.capture_bound)
        result = run_scratch_v2_capture(materialized)
    except PhaseDeadlineExpired:
        tracker.mark_consumed(reason="capture timeout")
        machine.quarantine(reason="capture phase timeout")
        raise
    report = result.get("capture_report") or {}
    if report.get("status") == "FAILED":
        machine.quarantine(reason=f"capture failed: {report.get('error')}")
        raise R2bV2CaptureCloseError(str(report.get("error") or "capture failed"))
    machine.transition(AuthorityState.FINAL_SOURCE_CHECKED, reason="final source checked")
    machine.transition(AuthorityState.SEALED, reason="marker last")
    return result


def final_source_recompute(
    machine: AuthorityStateMachine,
    lease: R2bQuiescenceLease,
    approved_snapshot: dict[str, Any],
    *,
    export: Path,
    processed: Path,
    chroma_dir: Path,
    snapshot_recompute_fn: Any,
) -> None:
    verify_r2b_quiescence_lease(lease, expected_run_id=machine.run_id)
    lease.verify()
    if machine.state not in (
        AuthorityState.CAPTURING,
        AuthorityState.FINAL_SOURCE_CHECKED,
    ):
        raise AuthorityStateError("final source check at wrong state")
    live = snapshot_recompute_fn(
        export=export, processed=processed, chroma_dir=chroma_dir
    )
    try:
        compare_source_snapshots(approved_snapshot, live)
    except PermissionError as exc:
        machine.quarantine(reason="source drift after snapshot")
        raise R2bV2CaptureCloseError(f"source drift: {exc}") from exc


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
    tracker.check_phase_bound("release_close", tracker.policy.release_close_bound)
    try:
        lease.release()
    except Exception as exc:
        machine.quarantine(reason=f"release failure: {exc}")
        raise R2bV2CaptureCloseError(f"release failure: {exc}") from exc
    release_path = auth_dir / "quiescence-release.json"
    release_digest = write_quiescence_release(
        release_path,
        run_id=machine.run_id,
        close_digest=close_digest,
        release_result="released",
        post_release_observation={"gate_released": True},
    )
    machine.transition(AuthorityState.CLOSED, reason="release evidence written")
    return release_digest

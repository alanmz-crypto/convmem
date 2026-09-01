"""R2b v2 capture, close, and release evidence path (I6)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from eval_corpus.r2b_capture_auth import compare_source_snapshots
from eval_corpus.r2b_v2.authority_commit import AuthorityCommitter
from eval_corpus.r2b_v2.authority_state import (
    AuthorityState,
    AuthorityStateError,
    AuthorityStateMachine,
)
from eval_corpus.r2b_v2.duration_policy import (
    PhaseDeadlineExpired,
    TransactionDeadlineExpired,
)
from eval_corpus.r2b_v2.lease import R2bQuiescenceLease, verify_r2b_quiescence_lease
from eval_corpus.r2b_v2.materialization import V2MaterializationResult
from eval_corpus.r2b_v2.scratch_capture import (
    compute_completion_marker,
    finalize_capture_report,
    prepare_scratch_capture_artifacts,
    promote_completion_marker,
)
from eval_corpus.r2b_v2.scratch_isolation import assert_scratch_path

SnapshotRecomputeFn = Callable[..., dict[str, Any]]


class R2bV2CaptureCloseError(RuntimeError):
    """Capture, close, or release failure."""


@dataclass(frozen=True)
class CaptureCloseResult:
    capture_result: dict[str, Any]
    close_digest: str
    release_digest: str | None
    terminal_state: AuthorityState


def grant_capture(
    committer: AuthorityCommitter,
    lease: R2bQuiescenceLease,
    materialized: V2MaterializationResult,
    *,
    reason: str = "Ryan ACCEPT AND GRANT",
) -> V2MaterializationResult:
    verify_r2b_quiescence_lease(lease, expected_run_id=committer.run_id)
    lease.verify()
    committer.commit_capture_granted(materialized, reason=reason)
    return materialized


def execute_authorized_capture(
    committer: AuthorityCommitter,
    lease: R2bQuiescenceLease,
    materialized: V2MaterializationResult,
    *,
    snapshot_recompute_fn: SnapshotRecomputeFn,
) -> dict[str, Any]:
    """CAPTURING → final source check → marker last → SEALED."""
    machine = committer.machine
    verify_r2b_quiescence_lease(lease, expected_run_id=machine.run_id)
    lease.verify()
    if "capture" not in committer.tracker.phase_starts:
        committer.tracker.start_phase_once("capture")
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
        final_source_recompute(
            machine,
            lease,
            bindings.source_snapshot,
            export=bindings.export,
            processed=bindings.processed,
            chroma_dir=bindings.chroma_dir,
            snapshot_recompute_fn=snapshot_recompute_fn,
        )
        final_report = finalize_capture_report(capture_dir, run_id=bindings.run_id)
        marker = compute_completion_marker(
            materialized,
            capture_dir=capture_dir,
            final_report=final_report,
        )

        def promote() -> dict[str, Any]:
            return promote_completion_marker(capture_dir, marker)

        _observation, sealed = committer.commit_capture_seal(promote_marker=promote)
        return {**prepared, **sealed, "capture_report": final_report}
    except (PhaseDeadlineExpired, TransactionDeadlineExpired) as exc:
        committer.tracker.consume(reason=f"capture deadline expired: {exc}")
        if capture_dir is not None and machine.state in (
            AuthorityState.CAPTURING,
            AuthorityState.FINAL_SOURCE_CHECKED,
        ):
            machine.quarantine(reason=f"capture deadline expired: {exc}")
        raise
    except R2bV2CaptureCloseError:
        raise


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
    committer: AuthorityCommitter,
    lease: R2bQuiescenceLease,
    auth_dir: Path,
    *,
    marker_result: str,
    final_source_result: str,
    preceding_digests: dict[str, str],
    gate_identity: str,
) -> str:
    machine = committer.machine
    verify_r2b_quiescence_lease(lease, expected_run_id=machine.run_id)
    lease.verify()
    if "release_close" not in committer.tracker.phase_starts:
        committer.tracker.start_phase_once("release_close")
    close_path = auth_dir / "quiescence-close.json"
    try:
        _observation, close_digest = committer.commit_closing(
            close_path=close_path,
            close_body={
                "run_id": machine.run_id,
                "terminal_disposition": machine.state.value,
                "marker_result": marker_result,
                "final_source_result": final_source_result,
                "gate_identity": gate_identity,
                "release_intent": True,
                "preceding_digests": preceding_digests,
            },
        )
    except (PhaseDeadlineExpired, TransactionDeadlineExpired):
        committer.tracker.consume(reason="release_close during close evidence")
        raise
    return close_digest


def release_gate_and_write_release_evidence(
    committer: AuthorityCommitter,
    lease: R2bQuiescenceLease,
    auth_dir: Path,
    *,
    close_digest: str,
) -> str:
    machine = committer.machine
    verify_r2b_quiescence_lease(lease, expected_run_id=machine.run_id)
    if machine.state != AuthorityState.CLOSING:
        raise AuthorityStateError(
            f"release requires CLOSING, got {machine.state.value}"
        )
    kernel_released = False
    release_path = auth_dir / "quiescence-release.json"
    try:
        lease.release()
    except Exception as exc:
        machine.quarantine(reason=f"release failure: {exc}")
        raise R2bV2CaptureCloseError(f"release failure: {exc}") from exc
    kernel_released = True
    try:
        _observation, release_digest = committer.commit_closed(
            release_path=release_path,
            release_body={
                "run_id": machine.run_id,
                "close_digest": close_digest,
                "release_result": "released",
                "post_release_observation": {"gate_released": True},
                "kernel_released": True,
            },
        )
    except (PhaseDeadlineExpired, TransactionDeadlineExpired) as exc:
        committer.tracker.consume(reason=f"release_close during close: {exc}")
        machine.quarantine(reason=f"release_close deadline after kernel release: {exc}")
        from eval_corpus.r2b_v2.quiescence_evidence import write_quiescence_release

        try:
            write_quiescence_release(
                release_path,
                run_id=machine.run_id,
                close_digest=close_digest,
                release_result="released",
                post_release_observation={"gate_released": True},
                kernel_released=True,
                closure_outcome="deadline_expired",
            )
        except Exception:
            pass
        raise
    except Exception as exc:
        machine.quarantine(reason=f"release evidence failure: {exc}")
        raise R2bV2CaptureCloseError(f"release evidence failure: {exc}") from exc
    return release_digest

"""Scratch-reachable R2b v2 I4–I6 transaction orchestrator."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from eval_corpus.r2b_v2.authority_commit import AuthorityCommitter, PendingLease
from eval_corpus.r2b_v2.authority_state import (
    AuthorityState,
    new_authority_state_machine,
    transition_to_coverage_proven,
    transition_to_q_held,
)
from eval_corpus.r2b_v2.capture_close import (
    execute_authorized_capture,
    grant_capture,
    release_gate_and_write_release_evidence,
    write_close_evidence,
)
from eval_corpus.r2b_v2.coverage.inventory import build_static_route_inventory
from eval_corpus.r2b_v2.coverage.proof import (
    SourceAuthorityProof,
    TrustedCoverageProof,
    mint_trusted_coverage_proof,
    prove_zero_bypass_coverage,
    source_authority_from_lease_and_coverage,
)
from eval_corpus.r2b_v2.duration_policy import (
    DurationPolicy,
    PhaseDeadlineExpired,
    PhaseDeadlineTracker,
)
from eval_corpus.r2b_v2.lease import (
    R2bQuiescenceLease,
    acquire_r2b_quiescence_lease_physical,
)
from eval_corpus.r2b_v2.materialization import materialize_v2_packet
from eval_corpus.r2b_v2.packet import (
    accept_capture_packet,
    compute_trusted_snapshot,
    draft_capture_packet,
    transition_snapshot_bound,
)
from eval_corpus.r2b_v2.quiescence_evidence import write_quiescence_open
from eval_corpus.r2b_v2.scratch_isolation import assert_scratch_transaction_paths
from eval_corpus.run_manifest import canonical_manifest_body_sha256

SnapshotRecomputeFn = Callable[..., dict[str, Any]]


class ScratchTransactionError(RuntimeError):
    """Scratch I4–I6 transaction failure."""


def perform_scratch_acquisition(  # pylint: disable=too-many-arguments
    committer: AuthorityCommitter,
    *,
    chroma_dir: Path,
    processed_path: Path,
    export_root: Path,
    gate_path: Path,
    open_evidence_digest: str,
    implementation_revision: str,
    grant_digest: str = "scratch-grant",
    authority_digest: str = "scratch-authority",
) -> tuple[R2bQuiescenceLease, TrustedCoverageProof]:
    """Coverage proof + writer-gate acquisition under acquisition_bound."""
    tracker = committer.tracker
    run_id = committer.run_id
    tracker.start_phase_once("acquisition")
    gate_path.parent.mkdir(parents=True, exist_ok=True)
    if not gate_path.exists():
        gate_path.touch()
    inv = build_static_route_inventory(code_revision=implementation_revision)
    diag = prove_zero_bypass_coverage(
        chroma_dir=chroma_dir,
        processed_path=processed_path,
        export_root=export_root,
        test_gate_path=gate_path,
        code_revision=implementation_revision,
        static_inventory=inv,
    )
    trusted = mint_trusted_coverage_proof(diag)
    timeout_ms = max(1, int(tracker.policy.acquisition_bound * 1000))
    absolute_deadline = tracker.absolute_deadline()
    try:
        holder = acquire_r2b_quiescence_lease_physical(
            run_id=run_id,
            grant_digest=grant_digest,
            authority_digest=authority_digest,
            test_lock_path=gate_path,
            writer_coverage_digest=trusted.coverage_digest,
            open_evidence_digest=open_evidence_digest,
            monotonic_deadline=absolute_deadline,
            bound_source_paths=(
                str(export_root),
                str(processed_path),
                str(chroma_dir),
            ),
            timeout_ms=timeout_ms,
            implementation_revision=implementation_revision,
        )
    except TimeoutError as exc:
        tracker.consume(reason="acquisition lock timeout")
        raise PhaseDeadlineExpired(
            "acquisition",
            "acquisition lock wait exceeded acquisition_bound",
        ) from exc
    pending = PendingLease(holder=holder, run_id=run_id)
    lease = committer.commit_acquisition(pending)
    return lease, trusted


@dataclass(frozen=True)
class ScratchTransactionResult:
    run_id: str
    final_state: AuthorityState
    manifest_path: Path
    close_digest: str | None
    release_digest: str | None
    capture_result: dict[str, Any] | None


def run_scratch_transaction(  # pylint: disable=too-many-arguments,too-many-locals
    *,
    root: Path,
    run_id: str,
    lease: R2bQuiescenceLease,
    trusted_coverage: TrustedCoverageProof,
    paths: dict[str, str],
    auth_dir: Path,
    duration_policy: DurationPolicy,
    open_evidence_digest: str,
    gate_identity: str,
    implementation_revision: str,
    future_argv: list[str],
    snapshot_recompute_fn: SnapshotRecomputeFn,
    runtime: dict[str, str],
    committer: AuthorityCommitter | None = None,
) -> ScratchTransactionResult:
    """End-to-end scratch I4→I6 path for benchmark readiness."""
    assert_scratch_transaction_paths(root=root, auth_dir=auth_dir, paths=paths)
    if committer is None:
        committer = AuthorityCommitter.begin(run_id, duration_policy)

    machine = committer.machine
    if machine.state == AuthorityState.NEW:
        machine.transition(AuthorityState.PREPARED, reason="scratch prepare")
        machine.transition(AuthorityState.Q_AUTHORIZED, reason="scratch authorize")
        transition_to_q_held(machine, lease, committer, reason="scratch lease held")
    elif machine.state != AuthorityState.Q_HELD:
        raise ScratchTransactionError(
            f"unexpected machine state {machine.state.value} at transaction start"
        )
    transition_to_coverage_proven(
        machine, lease, trusted_coverage, reason="scratch coverage"
    )

    open_path = auth_dir / "quiescence-open.json"
    auth_dir.mkdir(parents=True, exist_ok=True)
    open_digest = write_quiescence_open(
        open_path,
        run_id=run_id,
        gate_identity=gate_identity,
        gate_path=str(lease.bindings.gate_path),
        open_evidence_digest=open_evidence_digest,
        writer_coverage_digest=trusted_coverage.coverage_digest,
        implementation_revision=implementation_revision,
        monotonic_deadline=lease.bindings.monotonic_deadline,
    )

    source_authority: SourceAuthorityProof = source_authority_from_lease_and_coverage(
        lease,
        trusted_coverage,
        open_evidence_digest=open_evidence_digest,
        expected_run_id=run_id,
    )
    transition_snapshot_bound(
        machine, lease, source_authority, reason="snapshot authority bound"
    )

    snapshot = compute_trusted_snapshot(
        lease,
        export=Path(paths["export"]),
        processed=Path(paths["processed"]),
        chroma_dir=Path(paths["chroma_dir"]),
        snapshot_recompute_fn=snapshot_recompute_fn,
    )
    committer.tracker.start_phase_once("hitl")
    manifest_path = draft_capture_packet(
        machine,
        lease,
        trusted_coverage,
        auth_dir=auth_dir,
        paths=paths,
        source_snapshot=snapshot,
        duration_policy=duration_policy,
        future_argv=future_argv,
        open_evidence_digest=open_evidence_digest,
        gate_identity=gate_identity,
        implementation_revision=implementation_revision,
    )
    approval_digest = accept_capture_packet(machine, lease, manifest_path)
    committer.commit_packet_accepted(
        manifest_path=manifest_path,
        approval_digest=approval_digest,
    )

    materialized = materialize_v2_packet(
        committer,
        lease,
        manifest_path,
        runtime=runtime,
        snapshot_recompute_fn=snapshot_recompute_fn,
        restic_gate_fn=lambda: None,
    )
    grant_capture(committer, lease, materialized)
    capture_result = execute_authorized_capture(
        committer,
        lease,
        materialized,
        snapshot_recompute_fn=snapshot_recompute_fn,
    )

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    close_digest = write_close_evidence(
        committer,
        lease,
        auth_dir,
        marker_result="marker_written",
        final_source_result="matched",
        preceding_digests={
            "open": open_digest,
            "manifest": canonical_manifest_body_sha256(manifest),
        },
        gate_identity=gate_identity,
    )
    release_digest = release_gate_and_write_release_evidence(
        committer,
        lease,
        auth_dir,
        close_digest=close_digest,
    )
    return ScratchTransactionResult(
        run_id=run_id,
        final_state=machine.state,
        manifest_path=manifest_path,
        close_digest=close_digest,
        release_digest=release_digest,
        capture_result=capture_result,
    )


def run_scratch_transaction_with_acquisition(  # pylint: disable=too-many-arguments
    *,
    root: Path,
    run_id: str,
    paths: dict[str, str],
    auth_dir: Path,
    bundle_dir: Path,
    duration_policy: DurationPolicy,
    open_evidence_digest: str,
    gate_identity: str | None = None,
    implementation_revision: str,
    future_argv: list[str],
    snapshot_recompute_fn: SnapshotRecomputeFn,
    runtime: dict[str, str],
) -> ScratchTransactionResult:
    """Composed scratch path: bounded acquisition then I4–I6 transaction."""
    committer = AuthorityCommitter.begin(run_id, duration_policy)
    lease, trusted = perform_scratch_acquisition(
        committer,
        chroma_dir=Path(paths["chroma_dir"]),
        processed_path=Path(paths["processed"]),
        export_root=Path(paths["export"]).parent,
        gate_path=bundle_dir / "gate.lock",
        open_evidence_digest=open_evidence_digest,
        implementation_revision=implementation_revision,
    )
    resolved_gate_identity = gate_identity or trusted.gate_identity
    return run_scratch_transaction(
        root=root,
        run_id=run_id,
        lease=lease,
        trusted_coverage=trusted,
        paths=paths,
        auth_dir=auth_dir,
        duration_policy=duration_policy,
        open_evidence_digest=open_evidence_digest,
        gate_identity=resolved_gate_identity,
        implementation_revision=implementation_revision,
        future_argv=future_argv,
        snapshot_recompute_fn=snapshot_recompute_fn,
        runtime=runtime,
        committer=committer,
    )

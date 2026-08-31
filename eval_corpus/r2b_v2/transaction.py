"""Scratch-reachable R2b v2 I4–I6 transaction orchestrator."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

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
from eval_corpus.r2b_v2.coverage.proof import (
    SourceAuthorityProof,
    TrustedCoverageProof,
    source_authority_from_lease_and_coverage,
)
from eval_corpus.r2b_v2.duration_policy import DurationPolicy, PhaseDeadlineTracker
from eval_corpus.r2b_v2.lease import R2bQuiescenceLease
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
) -> ScratchTransactionResult:
    """End-to-end scratch I4→I6 path for benchmark readiness."""
    assert_scratch_transaction_paths(root=root, auth_dir=auth_dir, paths=paths)
    tracker = PhaseDeadlineTracker.begin(duration_policy)
    tracker.start_phase("acquisition")

    machine = new_authority_state_machine(run_id)
    machine.transition(AuthorityState.PREPARED, reason="scratch prepare")
    machine.transition(AuthorityState.Q_AUTHORIZED, reason="scratch authorize")
    transition_to_q_held(machine, lease, reason="scratch lease held")
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
    tracker.start_phase("hitl")
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
    accept_capture_packet(machine, lease, manifest_path)
    tracker.check_phase_bound("hitl", duration_policy.hitl_reservation_bound)

    materialized = materialize_v2_packet(
        machine,
        lease,
        manifest_path,
        runtime=runtime,
        snapshot_recompute_fn=snapshot_recompute_fn,
        restic_gate_fn=lambda: None,
    )
    grant_capture(machine, lease, tracker, materialized)
    capture_result = execute_authorized_capture(
        machine,
        lease,
        tracker,
        materialized,
        snapshot_recompute_fn=snapshot_recompute_fn,
    )

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    close_digest = write_close_evidence(
        machine,
        lease,
        tracker,
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
        machine,
        lease,
        tracker,
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

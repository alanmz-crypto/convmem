"""R2b v2 source snapshot and capture packet semantics (I4)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

from eval_corpus.r2b_capture_auth import (
    canonical_source_snapshot_sha256,
    compare_source_snapshots,
)
from eval_corpus.r2b_v2.authority_state import (
    AuthorityState,
    AuthorityStateError,
    AuthorityStateMachine,
)
from eval_corpus.r2b_v2.contract import (
    R2B_V2_REQUIRED_PROHIBITED,
    make_r2b_v2_run_manifest_for_tests,
    validate_r2b_v2_manifest_schema,
    validate_v2_policy_fields,
)
from eval_corpus.r2b_v2.coverage.proof import SourceAuthorityProof, TrustedCoverageProof
from eval_corpus.r2b_v2.duration_policy import DurationPolicy
from eval_corpus.r2b_v2.lease import R2bQuiescenceLease, verify_r2b_quiescence_lease
from eval_corpus.r2b_v2.scratch_isolation import (
    assert_scratch_source_paths,
    assert_scratch_transaction_path_dict,
)
from eval_corpus.run_manifest import (
    R2B_REQUIRED_PROHIBITED,
    approval_sidecar_path,
    assert_manifest_file_matches_approval,
    canonical_manifest_body_sha256,
    write_approval_sidecar,
)

SnapshotRecomputeFn = Callable[..., dict[str, Any]]


class R2bV2PacketError(RuntimeError):
    """Snapshot or packet draft/accept failure."""


def compute_trusted_snapshot(
    lease: R2bQuiescenceLease,
    *,
    export: Path,
    processed: Path,
    chroma_dir: Path,
    snapshot_recompute_fn: SnapshotRecomputeFn,
) -> dict[str, Any]:
    """Trusted source snapshot while the exclusive lease remains live."""
    verify_r2b_quiescence_lease(lease)
    lease.verify()
    assert_scratch_source_paths(export, processed, chroma_dir)
    return snapshot_recompute_fn(
        export=export,
        processed=processed,
        chroma_dir=chroma_dir,
    )


def transition_snapshot_bound(
    machine: AuthorityStateMachine,
    lease: R2bQuiescenceLease,
    source_authority: SourceAuthorityProof,
    *,
    reason: str,
) -> dict[str, Any]:
    verify_r2b_quiescence_lease(lease, expected_run_id=machine.run_id)
    if source_authority.run_id != machine.run_id:
        raise R2bV2PacketError("source authority run_id mismatch")
    if machine.state != AuthorityState.COVERAGE_PROVEN:
        raise AuthorityStateError(
            f"SNAPSHOT_BOUND requires COVERAGE_PROVEN, got {machine.state.value}"
        )
    machine.transition(AuthorityState.SNAPSHOT_BOUND, reason=reason)
    return {"source_authority_digest": source_authority.gate_identity}


def draft_capture_packet(  # pylint: disable=too-many-arguments
    machine: AuthorityStateMachine,
    lease: R2bQuiescenceLease,
    trusted_coverage: TrustedCoverageProof,
    *,
    auth_dir: Path,
    paths: dict[str, str],
    source_snapshot: dict[str, Any],
    duration_policy: DurationPolicy,
    future_argv: list[str],
    open_evidence_digest: str,
    gate_identity: str,
    implementation_revision: str,
) -> Path:
    """Draft capture.json with no approval sidecar."""
    verify_r2b_quiescence_lease(
        lease,
        expected_run_id=machine.run_id,
        expected_coverage_digest=trusted_coverage.coverage_digest,
    )
    lease.verify()
    assert_scratch_transaction_path_dict(auth_dir, paths)
    capture_dir = Path(paths["capture_dir"])
    if capture_dir.exists():
        raise R2bV2PacketError("capture_dir must be absent before packet draft")
    sidecar = approval_sidecar_path(auth_dir / "capture.json")
    if sidecar.exists():
        raise R2bV2PacketError("approval sidecar must be absent before packet draft")
    if machine.state != AuthorityState.SNAPSHOT_BOUND:
        raise AuthorityStateError(
            f"PACKET_DRAFTED requires SNAPSHOT_BOUND, got {machine.state.value}"
        )

    body = make_r2b_v2_run_manifest_for_tests(
        paths=paths,
        run_id=machine.run_id,
        source_snapshot=source_snapshot,
        operations=["capture"],
        prohibited_actions=sorted(R2B_V2_REQUIRED_PROHIBITED | {"capture"}),
    )
    body["duration_policy_ref"] = duration_policy.as_reference_dict()
    body["future_argv"] = list(future_argv)
    body["open_evidence_digest"] = open_evidence_digest
    body["gate_identity"] = gate_identity
    body["implementation_revision"] = implementation_revision
    body["writer_coverage_digest"] = trusted_coverage.coverage_digest
    body.pop("ryan_approved_manifest_sha256", None)

    errs = validate_v2_policy_fields(body)
    if errs:
        raise R2bV2PacketError("; ".join(errs))

    auth_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = auth_dir / "capture.json"
    manifest_path.write_text(
        json.dumps(body, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    machine.transition(AuthorityState.PACKET_DRAFTED, reason="draft capture packet")
    return manifest_path


def accept_capture_packet(
    machine: AuthorityStateMachine,
    lease: R2bQuiescenceLease,
    manifest_path: Path,
    *,
    reason: str = "Ryan packet ACCEPT",
) -> str:
    """Write approval sidecar while lease remains live."""
    verify_r2b_quiescence_lease(lease, expected_run_id=machine.run_id)
    lease.verify()
    if machine.state != AuthorityState.PACKET_DRAFTED:
        raise AuthorityStateError(
            f"PACKET_ACCEPTED requires PACKET_DRAFTED, got {machine.state.value}"
        )
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["operations"] = ["capture"]
    manifest["prohibited_actions"] = sorted(R2B_REQUIRED_PROHIBITED)
    manifest.pop("ryan_approved_manifest_sha256", None)
    digest = canonical_manifest_body_sha256(manifest)
    manifest["ryan_approved_manifest_sha256"] = digest
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    write_approval_sidecar(manifest_path, digest)
    machine.transition(AuthorityState.PACKET_ACCEPTED, reason=reason)
    return digest


def refuse_source_drift(
    approved: dict[str, Any],
    recomputed: dict[str, Any],
) -> None:
    try:
        compare_source_snapshots(approved, recomputed)
    except PermissionError as exc:
        raise R2bV2PacketError(f"source drift: {exc}") from exc


def refuse_sidecar_before_accept(manifest_path: Path) -> None:
    if approval_sidecar_path(manifest_path).exists():
        raise R2bV2PacketError("sidecar present before packet ACCEPT")


def verify_accepted_manifest(manifest_path: Path) -> dict[str, Any]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert_manifest_file_matches_approval(manifest_path, manifest)
    errs = validate_r2b_v2_manifest_schema(manifest)
    if errs:
        raise R2bV2PacketError("; ".join(errs))
    return manifest


def snapshot_digest(snapshot: dict[str, Any]) -> str:
    return canonical_source_snapshot_sha256(snapshot)

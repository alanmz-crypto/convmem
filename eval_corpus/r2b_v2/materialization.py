"""V2 packet validation and binding without v1 service-policy coupling."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from eval_corpus.r2b_capture_auth import (
    R2bBindings,
    _check_no_symlinks,
    _derive_r2b_bindings,
    _validate_r2b_paths,
    _validate_snapshot_freshness,
    compare_source_snapshots,
)
from eval_corpus.r2b_v2.authority_state import (
    AuthorityState,
    AuthorityStateError,
    AuthorityStateMachine,
)
from eval_corpus.r2b_v2.contract import validate_v2_policy_fields
from eval_corpus.r2b_v2.lease import R2bQuiescenceLease, verify_r2b_quiescence_lease
from eval_corpus.r2b_v2.scratch_isolation import assert_scratch_path
from eval_corpus.run_manifest import (
    CAPTURE_FIELDS,
    _require_exact_fields,
    assert_manifest_file_matches_approval,
    load_run_manifest,
    validate_r2b_manifest_schema,
)

SnapshotRecomputeFn = Callable[..., dict[str, Any]]


class R2bV2MaterializationError(RuntimeError):
    """Binder/materializer refusal."""


@dataclass(frozen=True)
class V2MaterializationResult:
    bindings: R2bBindings
    manifest_path: Path


def _validate_v2_approved_manifest(manifest_path: Path) -> dict[str, Any]:
    manifest = load_run_manifest(manifest_path)
    assert_manifest_file_matches_approval(manifest_path, manifest)
    errs = validate_v2_policy_fields(manifest)
    for msg in validate_r2b_manifest_schema(manifest):
        if "no_service_changes" in msg:
            continue
        errs.append(msg)
    if errs:
        raise R2bV2MaterializationError("; ".join(errs))
    if str(manifest.get("authorization_phase") or "") != "r2b":
        raise R2bV2MaterializationError('authorization_phase must be "r2b"')
    return manifest


def materialize_v2_packet(
    machine: AuthorityStateMachine,
    lease: R2bQuiescenceLease,
    manifest_path: Path,
    *,
    runtime: dict[str, str],
    snapshot_recompute_fn: SnapshotRecomputeFn,
    restic_gate_fn: Callable[[], None] | None = None,
) -> V2MaterializationResult:
    """Validate approved packet and derive bindings — no capture_dir creation."""
    del restic_gate_fn
    verify_r2b_quiescence_lease(lease, expected_run_id=machine.run_id)
    lease.verify()
    assert_scratch_path(manifest_path, label="manifest_path")
    if machine.state != AuthorityState.PACKET_ACCEPTED:
        raise AuthorityStateError(
            f"MATERIALIZED requires PACKET_ACCEPTED, got {machine.state.value}"
        )

    manifest = _validate_v2_approved_manifest(manifest_path)
    _require_exact_fields("capture", CAPTURE_FIELDS, runtime)
    run_id = manifest["run_id"]
    manifest_paths = manifest["paths"]
    _validate_r2b_paths(
        manifest_paths=manifest_paths,
        runtime=runtime,
        run_id=run_id,
        manifest_path=manifest_path,
    )
    _check_no_symlinks(manifest_path, manifest_paths, runtime)

    source_snapshot = manifest["source_snapshot"]
    _validate_snapshot_freshness(source_snapshot)
    recomputed = snapshot_recompute_fn(
        export=Path(manifest_paths["export"]),
        processed=Path(manifest_paths["processed"]),
        chroma_dir=Path(manifest_paths["chroma_dir"]),
    )
    compare_source_snapshots(source_snapshot, recomputed)

    capture_dir = Path(manifest_paths["capture_dir"])
    if capture_dir.exists():
        raise R2bV2MaterializationError(
            "materialization refused: capture_dir already present"
        )

    bindings = _derive_r2b_bindings(manifest, manifest_path=manifest_path)
    if bindings.capture_dir.exists():
        raise R2bV2MaterializationError(
            "materialization must not create capture_dir"
        )

    machine.transition(AuthorityState.MATERIALIZED, reason="binder validated packet")
    return V2MaterializationResult(bindings=bindings, manifest_path=manifest_path)

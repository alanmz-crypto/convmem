"""Recovery Authority T3 — scratch-only bulk recovery workflow (V4j).

Selects one exact Restic snapshot/tree, validates complete v3 provenance
authority via landed T1/T2 surfaces, and prepares an isolated replacement
candidate without mutating live authority.

Execution: docs/plans/EXECUTION-recovery-authority.md T3
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping, Sequence

from complete_data_restore import (
    RestoreProfile,
    RestoreReport,
    _canonical_json_hash,
    locate_restored_data_root,
    record_restic_tree_binding,
    writer_census_for_root,
)
from recovery_authority import RecoveryState, evaluate_recovery_authority
from restic_snapshot import (
    EXIT_BLOCKED,
    EXIT_ISOLATION_FAILURE,
    EXIT_OK,
    TAG_COMPLETE_DATA_V3,
    BackupContext,
    ResolverError,
    SnapshotRef,
    _paths_overlap,
    resolve_snapshot,
    restore_snapshot,
)

STATUS_PASS = "PASS"
STATUS_FAIL = "FAIL"

SCRATCH_CANDIDATE_PREPARE = "scratch_recovery_candidate_prepare"
LIVE_AUTHORITY_REPLACEMENT = "live_authority_replacement"
BULK_RECOVERY_REPORT_KIND = "recovery_authority_bulk_scratch_v1"


@dataclass(frozen=True)
class OperationalGrant:
    """Explicit Ryan operational grant record (scratch tests use synthetic grants)."""

    grant_id: str
    operation: str
    authorized_target: str
    authorized_by: str = "Ryan"


@dataclass
class BulkRecoveryOutcome:
    """Structured outcome for scratch bulk-recovery candidate preparation."""

    status: str
    message: str
    exit_code: int = EXIT_OK
    source: SnapshotRef | None = None
    recovery_state: str | None = None
    provenance_tuple: dict[str, str] | None = None
    details: dict[str, Any] = field(default_factory=dict)
    report_path: Path | None = None

    @property
    def ok(self) -> bool:
        return self.status == STATUS_PASS

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "status": self.status,
            "message": self.message,
            "exit_code": self.exit_code,
            "recovery_state": self.recovery_state,
            "provenance_tuple": self.provenance_tuple,
            "report_path": str(self.report_path) if self.report_path else None,
            "details": dict(self.details),
        }
        if self.source is not None:
            payload["source"] = self.source.to_dict()
        return payload

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, sort_keys=True)


def fingerprint_data_root(
    root: Path | str,
    *,
    profile: RestoreProfile = RestoreProfile.COMPLETE_DATA_V3,
) -> str:
    """Stable fingerprint for live nonmutation proof (does not mutate root)."""
    from provenance_registry_restore import (  # pylint: disable=import-outside-toplevel
        compute_tree_commitment,
        validate_provenance_registry,
    )

    data_root = Path(root).expanduser().resolve()
    payload: dict[str, Any] = {
        "profile": profile.value,
        "exists": data_root.is_dir(),
        "census": writer_census_for_root(data_root, profile=profile),
    }
    if data_root.is_dir() and profile is RestoreProfile.COMPLETE_DATA_V3:
        if (data_root / "provenance").is_dir():
            payload["tree_commitment"] = compute_tree_commitment(data_root)
            registry = validate_provenance_registry(data_root)
            payload["registry_outcome"] = registry.outcome
            if registry.provenance_tuple is not None:
                payload["provenance_tuple"] = registry.provenance_tuple.as_dict()
    return _canonical_json_hash(payload)


def assert_scratch_target_isolated(
    scratch_target: Path | str,
    live_data_root: Path | str,
) -> None:
    """Reject scratch targets that overlap the live data root."""
    scratch = Path(scratch_target).expanduser().resolve()
    live = Path(live_data_root).expanduser().resolve()
    if _paths_overlap(scratch, live):
        raise ResolverError(
            "scratch target overlaps live CONVMEM_DATA_ROOT; "
            "bulk recovery must not mutate live authority",
            EXIT_ISOLATION_FAILURE,
        )


def validate_operational_grant(
    grant: OperationalGrant | None,
    *,
    operation: str,
    target: Path | str,
) -> tuple[bool, str]:
    """Require a fresh explicit grant naming the operation and target."""
    if grant is None:
        return False, "operational grant required"
    if grant.operation != operation:
        return (
            False,
            f"grant operation {grant.operation!r} != required {operation!r}",
        )
    authorized = str(Path(grant.authorized_target).expanduser().resolve())
    actual = str(Path(target).expanduser().resolve())
    if authorized != actual:
        return (
            False,
            f"grant target {authorized!r} != requested target {actual!r}",
        )
    if not grant.grant_id.strip():
        return False, "grant_id required"
    return True, "grant accepted"


def validate_item_import_not_registry_substitute(
    *,
    caller_assertion_ids: Sequence[str],
    registry_assertion_ids: Sequence[str],
) -> tuple[bool, str]:
    """Item-by-item import cannot preserve foreign IDs or substitute registry recovery."""
    registry = {str(x).strip() for x in registry_assertion_ids if str(x).strip()}
    foreign = [
        str(x).strip()
        for x in caller_assertion_ids
        if str(x).strip() and str(x).strip() not in registry
    ]
    if foreign:
        return (
            False,
            f"caller-provided assertion ids not in registry: {sorted(foreign)}",
        )
    return True, "item import cannot substitute for complete registry recovery"


def _assert_v3_contract(
    *,
    snapshot_ref: SnapshotRef | None,
    restored_root: Path,
    profile: RestoreProfile,
) -> tuple[bool, str]:
    """Reject v2 snapshots/roots presented as v3 authority recovery."""
    if profile is not RestoreProfile.COMPLETE_DATA_V3:
        return True, "v2 legacy contract"
    if snapshot_ref is not None and TAG_COMPLETE_DATA_V3 not in snapshot_ref.tags:
        return False, "snapshot lacks complete-data-v3 tag; cannot treat as v3 authority"
    if not (restored_root / "provenance").is_dir():
        return False, "restored root lacks provenance registry; v2 cannot be v3"
    return True, "v3 contract satisfied"


def _verify_exact_selection_binding(
    *,
    snapshot_ref: SnapshotRef,
    provenance_tuple: dict[str, str],
    binding: Mapping[str, str],
) -> tuple[bool, str]:
    """Prove the recorded tuple matches the selected snapshot and registry."""
    expected = {
        "restic_snapshot_id": snapshot_ref.id,
        "restic_root_tree_id": snapshot_ref.tree,
        "generation_id": provenance_tuple.get("generation_id", ""),
        "manifest_commitment": provenance_tuple.get("manifest_commitment", ""),
        "tree_commitment": provenance_tuple.get("tree_commitment", ""),
    }
    for key, value in expected.items():
        if binding.get(key) != value:
            return False, f"selection binding mismatch on {key}"
    return True, "exact selection binding verified"


def validate_scratch_recovery_candidate(
    restored_root: Path | str,
    *,
    snapshot_ref: SnapshotRef | None = None,
    profile: RestoreProfile = RestoreProfile.COMPLETE_DATA_V3,
    expected_binding: Mapping[str, str] | None = None,
) -> BulkRecoveryOutcome:
    """Validate a restored scratch root via T1/T2 without touching live authority."""
    root = Path(restored_root).expanduser().resolve()
    ok_contract, contract_reason = _assert_v3_contract(
        snapshot_ref=snapshot_ref,
        restored_root=root,
        profile=profile,
    )
    if not ok_contract:
        return BulkRecoveryOutcome(
            status=STATUS_FAIL,
            message=contract_reason,
            exit_code=EXIT_BLOCKED,
            details={"code": "BLOCKED_V2_AS_V3"},
        )

    authority = evaluate_recovery_authority(root)
    recovery_state = authority.state.value
    details: dict[str, Any] = {
        "recovery_authority": authority.as_dict(),
        "candidate_published": False,
        "serving_ready": authority.serving_ready,
    }

    if expected_binding is not None and snapshot_ref is not None:
        ok_bind, bind_reason = _verify_exact_selection_binding(
            snapshot_ref=snapshot_ref,
            provenance_tuple=(
                authority.provenance_tuple.as_dict()
                if authority.provenance_tuple
                else {}
            ),
            binding=expected_binding,
        )
        details["selection_binding_ok"] = ok_bind
        details["selection_binding_reason"] = bind_reason
        if not ok_bind:
            return BulkRecoveryOutcome(
                status=STATUS_FAIL,
                message=bind_reason,
                exit_code=EXIT_BLOCKED,
                source=snapshot_ref,
                recovery_state=recovery_state,
                details=details,
            )

    if authority.state in {RecoveryState.BLOCKED, RecoveryState.QUARANTINED}:
        return BulkRecoveryOutcome(
            status=STATUS_FAIL,
            message=authority.detail or authority.state.value,
            exit_code=EXIT_BLOCKED,
            source=snapshot_ref,
            recovery_state=recovery_state,
            provenance_tuple=(
                authority.provenance_tuple.as_dict()
                if authority.provenance_tuple
                else None
            ),
            details=details,
        )

    if authority.state is RecoveryState.PROVENANCE_STORE_UNAVAILABLE:
        return BulkRecoveryOutcome(
            status=STATUS_FAIL,
            message=authority.detail,
            exit_code=EXIT_BLOCKED,
            source=snapshot_ref,
            recovery_state=recovery_state,
            details=details,
        )

    if not authority.state.authority_recovered:
        return BulkRecoveryOutcome(
            status=STATUS_FAIL,
            message=authority.detail or "authority not recovered",
            exit_code=EXIT_BLOCKED,
            source=snapshot_ref,
            recovery_state=recovery_state,
            details=details,
        )

    tuple_dict = (
        authority.provenance_tuple.as_dict() if authority.provenance_tuple else None
    )
    pending = authority.state is RecoveryState.AUTHORITY_RECOVERED_PROJECTION_PENDING
    message = (
        "scratch recovery candidate prepared; authority recovered; "
        + (
            "projections pending/non-serving"
            if pending
            else "projections validated/non-serving"
        )
    )
    return BulkRecoveryOutcome(
        status=STATUS_PASS,
        message=message,
        exit_code=EXIT_OK,
        source=snapshot_ref,
        recovery_state=recovery_state,
        provenance_tuple=tuple_dict,
        details=details,
    )


def prepare_scratch_recovery_candidate(
    ctx: BackupContext,
    *,
    snapshot_id: str,
    scratch_target: Path | str,
    grant: OperationalGrant | None,
    report: RestoreReport,
    live_data_root: Path | str | None = None,
    profile: RestoreProfile = RestoreProfile.COMPLETE_DATA_V3,
) -> BulkRecoveryOutcome:
    """Select exact snapshot, restore to scratch, validate candidate — no live mutation."""
    scratch = Path(scratch_target).expanduser().resolve()
    live = Path(live_data_root or ctx.data_root).expanduser().resolve()

    report.set_meta(
        kind=BULK_RECOVERY_REPORT_KIND,
        profile=profile.value,
        scratch_target=str(scratch),
        live_data_root=str(live),
    )

    ok_grant, grant_reason = validate_operational_grant(
        grant,
        operation=SCRATCH_CANDIDATE_PREPARE,
        target=scratch,
    )
    report.step("operational_grant", "PASS" if ok_grant else "BLOCKED", grant_reason)
    if not ok_grant:
        report.finalize("BLOCKED", grant_reason, exit_code=EXIT_BLOCKED)
        return BulkRecoveryOutcome(
            status=STATUS_FAIL,
            message=grant_reason,
            exit_code=EXIT_BLOCKED,
            report_path=report.json_path,
            details={"code": "GRANT_REQUIRED"},
        )

    if grant is not None:
        report.set_meta(
            operational_grant={
                "grant_id": grant.grant_id,
                "operation": grant.operation,
                "authorized_target": grant.authorized_target,
                "authorized_by": grant.authorized_by,
            }
        )

    try:
        assert_scratch_target_isolated(scratch, live)
    except ResolverError as exc:
        report.step("scratch_isolation", "BLOCKED", str(exc))
        report.finalize("BLOCKED", str(exc), exit_code=exc.exit_code)
        return BulkRecoveryOutcome(
            status=STATUS_FAIL,
            message=str(exc),
            exit_code=exc.exit_code,
            report_path=report.json_path,
            details={"code": "LIVE_OVERLAP"},
        )

    live_before = fingerprint_data_root(live, profile=profile)
    report.set_meta(live_fingerprint_before=live_before)

    try:
        ref = resolve_snapshot(
            ctx,
            requested_id=snapshot_id,
            required_tag=TAG_COMPLETE_DATA_V3,
        )
    except ResolverError as exc:
        report.step("resolve_snapshot", "FAIL", str(exc))
        report.finalize("FAIL", str(exc), exit_code=exc.exit_code)
        return BulkRecoveryOutcome(
            status=STATUS_FAIL,
            message=str(exc),
            exit_code=exc.exit_code,
            report_path=report.json_path,
        )

    report.set_snapshot_identity(
        snapshot_id=ref.id,
        tree=ref.tree,
        original=ref.original,
        tags=ref.tags,
        paths=ref.paths,
        repository=ref.repository,
    )
    report.step("resolve_snapshot", "PASS", f"exact id={ref.id}")

    try:
        restore_snapshot(ctx, ref.id, scratch)
    except ResolverError as exc:
        report.step("restore_snapshot", "FAIL", str(exc))
        report.finalize("FAIL", str(exc), exit_code=exc.exit_code)
        return BulkRecoveryOutcome(
            status=STATUS_FAIL,
            message=str(exc),
            exit_code=exc.exit_code,
            source=ref,
            report_path=report.json_path,
        )
    report.step("restore_snapshot", "PASS", f"restored snapshot {ref.id}")

    restored_root = locate_restored_data_root(scratch, ctx.data_root)
    report.step("locate_restored_root", "PASS", str(restored_root))

    candidate = validate_scratch_recovery_candidate(
        restored_root,
        snapshot_ref=ref,
        profile=profile,
    )
    report.step(
        "validate_recovery_candidate",
        candidate.status,
        candidate.message,
        recovery_state=candidate.recovery_state,
    )

    if candidate.provenance_tuple and candidate.source is not None:
        record_restic_tree_binding(
            report,
            snapshot_id=candidate.source.id,
            tree_id=candidate.source.tree,
            provenance_tuple=candidate.provenance_tuple,
        )
        binding = dict(report.meta.get("restic_tree_binding") or {})
        candidate.details["exact_selection_binding"] = binding

    scratch_fp = fingerprint_data_root(restored_root, profile=profile)
    live_after = fingerprint_data_root(live, profile=profile)
    report.set_meta(
        scratch_fingerprint=scratch_fp,
        live_fingerprint_after=live_after,
        live_authority_unchanged=(live_before == live_after),
    )

    if live_before != live_after:
        msg = "live data root fingerprint changed during scratch preparation"
        report.finalize("BLOCKED", msg, exit_code=EXIT_ISOLATION_FAILURE)
        return BulkRecoveryOutcome(
            status=STATUS_FAIL,
            message=msg,
            exit_code=EXIT_ISOLATION_FAILURE,
            source=ref,
            recovery_state=candidate.recovery_state,
            report_path=report.json_path,
            details={"live_before": live_before, "live_after": live_after},
        )

    final_status = "CANDIDATE_PREPARED" if candidate.ok else candidate.status
    report.finalize(
        final_status,
        candidate.message,
        exit_code=candidate.exit_code,
    )
    candidate.report_path = report.json_path
    candidate.source = ref
    return candidate


def refuse_live_authority_replacement(
    grant: OperationalGrant | None,
    *,
    live_target: Path | str,
) -> BulkRecoveryOutcome:
    """Explicit boundary: live replacement requires a separate Ryan grant."""
    ok, reason = validate_operational_grant(
        grant,
        operation=LIVE_AUTHORITY_REPLACEMENT,
        target=live_target,
    )
    if ok:
        return BulkRecoveryOutcome(
            status=STATUS_FAIL,
            message="live authority replacement is not authorized in T3",
            exit_code=EXIT_BLOCKED,
            details={"code": "LIVE_REPLACEMENT_NOT_IN_T3_GRANT"},
        )
    return BulkRecoveryOutcome(
        status=STATUS_FAIL,
        message=reason,
        exit_code=EXIT_BLOCKED,
        details={"code": "LIVE_REPLACEMENT_GRANT_REQUIRED"},
    )

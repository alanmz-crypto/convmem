"""Fail-closed Restic snapshot gate before live Chroma writes."""

from __future__ import annotations

import hashlib
import os
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from backup_workflows import STATUS_PASS, ensure_current_snapshot
from restic_snapshot import (
    _DEFAULT_ENV_FILE,
    EXIT_ACTION_FAILURE,
    EXIT_INVALID_CONFIG,
    EXIT_STALE,
    EXIT_WRONG_PATH,
    BackupContext,
    BackupProfile,
    ResolverError,
    evaluation_instant,
)

SKIP_ENV = "CONVMEM_SKIP_RESTIC_GATE"

REASON_SKIP_REFUSED = "skip_refused"
REASON_PROFILE_NOT_V2 = "profile_not_complete_data_v2"
REASON_CHROMA_TARGET_MISMATCH = "chroma_target_mismatch"
REASON_PATH_OUTSIDE_DATA_ROOT = "affected_path_outside_data_root"
REASON_PROFILE_INPUTS_CHANGED = "profile_inputs_changed"
REASON_OPERATION_CONFIG_CHANGED = "operation_config_changed"
REASON_DAY_BOUNDARY = "day_boundary_crossed"


class OperationAdmissionRefused(RuntimeError):
    """A bound operation may not proceed; carries the numeric exit and reason."""

    def __init__(self, message: str, exit_code: int, reason: str | None = None):
        super().__init__(message)
        self.exit_code = exit_code
        self.reason = reason


@dataclass(frozen=True)
class OperationTarget:
    """The resolved write target of one admitted operation."""

    entrypoint: str
    chroma_dir: Path
    affected_paths: tuple[Path, ...]
    config_path: Path


@dataclass(frozen=True)
class BoundPreflight:
    """Result of the preflight bound to one OperationTarget."""

    target: OperationTarget
    status: str  # "admitted" | "isolated-exception"
    env_file: Path | None = None
    env_digest: str | None = None
    snapshot_id: str | None = None
    evaluated_at: str | None = None
    detail: str = ""


def _canonical(path: str | Path) -> Path:
    return Path(path).expanduser().resolve(strict=False)


def _env_file_path() -> Path:
    return Path(os.environ.get("CONVMEM_RESTIC_ENV") or _DEFAULT_ENV_FILE).expanduser()


def _file_digest(path: Path) -> str | None:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except FileNotFoundError:
        return None


def _local_now() -> datetime:
    return evaluation_instant()


def _skip_exception(target: OperationTarget) -> BoundPreflight | None:
    from runtime_guard import restic_gate_exception

    requested = os.environ.get(SKIP_ENV, "")
    if not requested:
        return None
    if requested != "1":
        raise OperationAdmissionRefused(
            f"{SKIP_ENV}={requested!r} is not a recognized request",
            EXIT_INVALID_CONFIG,
            REASON_SKIP_REFUSED,
        )
    allowed, why = restic_gate_exception(
        (target.chroma_dir, *target.affected_paths), config_file=target.config_path
    )
    if not allowed:
        raise OperationAdmissionRefused(
            f"{SKIP_ENV}=1 refused for {target.entrypoint}: {why}",
            EXIT_INVALID_CONFIG,
            REASON_SKIP_REFUSED,
        )
    return BoundPreflight(target=target, status="isolated-exception", detail=why)


def _require_binding(ctx: BackupContext, target: OperationTarget) -> None:
    if ctx.profile is not BackupProfile.COMPLETE_DATA_V2 or ctx.data_root_derived:
        raise OperationAdmissionRefused(
            f"{target.entrypoint} requires an explicit complete-data-v2 profile and "
            f"data root (profile={ctx.profile.value}, "
            f"data_root_derived={ctx.data_root_derived})",
            EXIT_INVALID_CONFIG,
            REASON_PROFILE_NOT_V2,
        )
    chroma = _canonical(target.chroma_dir)
    if chroma != ctx.chroma_dir:
        raise OperationAdmissionRefused(
            f"{target.entrypoint} writes Chroma {chroma} but the backup profile "
            f"protects {ctx.chroma_dir}",
            EXIT_WRONG_PATH,
            REASON_CHROMA_TARGET_MISMATCH,
        )
    root = ctx.data_root.resolve()
    for path in (chroma, *target.affected_paths):
        resolved = _canonical(path)
        if resolved == root or not resolved.is_relative_to(root):
            raise OperationAdmissionRefused(
                f"{target.entrypoint} affects {resolved}, outside the protected "
                f"data root {root}",
                EXIT_WRONG_PATH,
                REASON_PATH_OUTSIDE_DATA_ROOT,
            )


def _current_snapshot(ctx: BackupContext, target: OperationTarget):
    outcome = ensure_current_snapshot(ctx)
    if outcome.status != STATUS_PASS:
        raise OperationAdmissionRefused(
            f"{target.entrypoint}: {outcome.message}",
            outcome.exit_code or EXIT_ACTION_FAILURE,
            outcome.reason,
        )
    return outcome


def _same_day(evaluated_iso: str | None) -> bool:
    if not evaluated_iso:
        return False
    evaluated = datetime.fromisoformat(evaluated_iso)
    return _local_now().astimezone(evaluated.tzinfo).date() == evaluated.date()


def preflight_operation(target: OperationTarget) -> BoundPreflight:
    """Bind the existing Restic gate to one operation's resolved target.

    Loads one immutable BackupContext, requires the explicit v2 profile, the
    same canonical Chroma target and every affected path inside the protected
    data root, then requires a current snapshot. Crossing a local day boundary
    after resolution forces one fresh resolution before admission.
    """
    skipped = _skip_exception(target)
    if skipped is not None:
        return skipped
    env_path = _env_file_path()
    digest_before = _file_digest(env_path)
    try:
        ctx = BackupContext.from_env_file(env_path)
    except ResolverError as exc:
        raise OperationAdmissionRefused(
            f"{target.entrypoint}: {exc}", exc.exit_code, exc.reason
        ) from exc
    if _file_digest(env_path) != digest_before:
        raise OperationAdmissionRefused(
            f"{target.entrypoint}: backup profile {env_path} changed while loading",
            EXIT_INVALID_CONFIG,
            REASON_PROFILE_INPUTS_CHANGED,
        )
    _require_binding(ctx, target)
    outcome = _current_snapshot(ctx, target)
    if not _same_day(outcome.details.get("evaluated_at")):
        outcome = _current_snapshot(ctx, target)
        if not _same_day(outcome.details.get("evaluated_at")):
            raise OperationAdmissionRefused(
                f"{target.entrypoint}: local day changed during resolution",
                EXIT_STALE,
                REASON_DAY_BOUNDARY,
            )
    return BoundPreflight(
        target=target,
        status="admitted",
        env_file=env_path,
        env_digest=digest_before,
        snapshot_id=outcome.source.id if outcome.source else None,
        evaluated_at=outcome.details.get("evaluated_at"),
        detail=outcome.message,
    )


def verify_preflight_inputs_unchanged(preflight: BoundPreflight) -> None:
    """Refuse when the backup profile file differs from the one admitted."""
    if preflight.status != "admitted" or preflight.env_file is None:
        return
    if _file_digest(preflight.env_file) != preflight.env_digest:
        raise OperationAdmissionRefused(
            f"{preflight.target.entrypoint}: backup profile {preflight.env_file} "
            "changed after admission",
            EXIT_INVALID_CONFIG,
            REASON_PROFILE_INPUTS_CHANGED,
        )


def report_refusal(exc: OperationAdmissionRefused) -> None:
    reason = f" [reason={exc.reason}]" if exc.reason else ""
    print(f"Live write BLOCKED (fail-closed): {exc}{reason}", file=sys.stderr)
    print(
        "Fix Restic (docs/RECOVER.md) or use scripts/convmem-live-write.sh",
        file=sys.stderr,
    )


def ensure_chroma_snapshot_for_live_write() -> None:
    """Unbound compatibility gate for callers outside the Safe Harbor T2 set.

    Snapshot if stale; exit nonzero on any Restic/resolver failure. The named
    production consumers use ``preflight_operation`` instead.
    """
    if os.environ.get(SKIP_ENV) == "1":
        return
    env_file = os.environ.get("CONVMEM_RESTIC_ENV") or None
    try:
        ctx = BackupContext.from_env_file(env_file)
        outcome = ensure_current_snapshot(ctx)
    except ResolverError as exc:
        print(f"Live write BLOCKED (fail-closed): {exc}", file=sys.stderr)
        print(
            "Fix Restic (docs/RECOVER.md) or use scripts/convmem-live-write.sh",
            file=sys.stderr,
        )
        sys.exit(exc.exit_code if exc.exit_code else 1)
    if outcome.status == "PASS":
        return
    detail = outcome.message
    print(f"Live write BLOCKED (fail-closed): {detail}", file=sys.stderr)
    print(
        "Fix Restic (docs/RECOVER.md) or use scripts/convmem-live-write.sh",
        file=sys.stderr,
    )
    sys.exit(outcome.exit_code if outcome.exit_code else 1)

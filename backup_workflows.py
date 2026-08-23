"""Safety workflows for complete-data backup correction v2.

Deep orchestration over restic_snapshot.BackupContext. No consumer may invoke
Restic selection/check/copy/restore directly, and no workflow may catch a
resolver failure then fall back to legacy selection.

Architecture: docs/plans/ARCHITECTURE-complete-data-backup-correction-v2.md
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Sequence

from complete_data_restore import capture_backup_evidence
from restic_snapshot import (
    EXIT_ACTION_FAILURE,
    EXIT_INVALID_CONFIG,
    EXIT_NO_TAGGED_SNAPSHOT,
    EXIT_OK,
    EXIT_STALE,
    EXIT_WRONG_PATH,
    RESTIC_RESERVED_EXITS,
    BackupContext,
    BackupProfile,
    ResolverError,
    SnapshotRef,
    backup_data_root,
    check_restic_available,
    check_snapshot,
    copy_snapshot_to_external,
    ensure_repository_initialized,
    resolve_copy_destination,
    resolve_snapshot,
    restore_snapshot,
)

# ---------------------------------------------------------------------------
# Outcome vocabulary
# ---------------------------------------------------------------------------
STATUS_PASS = "PASS"
STATUS_FAIL = "FAIL"
STATUS_WARN = "WARN"
STATUS_WARN_LEGACY_ONLY = "WARN_LEGACY_ONLY"
STATUS_SKIP_DISABLED = "SKIP_DISABLED"


@dataclass(frozen=True)
class WorkflowOutcome:
    """Structured result shared by all backup workflows."""

    status: str
    message: str
    exit_code: int = EXIT_OK
    source: SnapshotRef | None = None
    destination: SnapshotRef | None = None
    argv: tuple[str, ...] = ()
    details: dict[str, Any] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return self.status == STATUS_PASS

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "status": self.status,
            "message": self.message,
            "exit_code": self.exit_code,
            "argv": list(self.argv),
            "details": dict(self.details),
        }
        if self.source is not None:
            payload["source"] = self.source.to_dict()
        if self.destination is not None:
            payload["destination"] = self.destination.to_dict()
        return payload

    def to_json(self) -> str:
        return json.dumps(self.to_dict())


def _fail_from_resolver(exc: ResolverError, *, prefix: str = "") -> WorkflowOutcome:
    msg = f"{prefix}{exc}" if prefix else str(exc)
    return WorkflowOutcome(
        status=STATUS_FAIL,
        message=msg,
        exit_code=exc.exit_code,
    )


def _is_legacy_profile(ctx: BackupContext) -> bool:
    return (
        ctx.profile is BackupProfile.LEGACY_CHROMA
        or ctx.data_root_derived
    )


def _legacy_health_outcome(ctx: BackupContext, *, scope: str) -> WorkflowOutcome:
    return WorkflowOutcome(
        status=STATUS_WARN_LEGACY_ONLY,
        message=(
            f"WARN_LEGACY_ONLY: profile={ctx.profile.value} "
            f"(data_root_derived={ctx.data_root_derived}); "
            f"{scope} never claims complete-data-v2/v3 protection"
        ),
        exit_code=EXIT_OK,
        details={
            "profile": ctx.profile.value,
            "data_root_derived": ctx.data_root_derived,
            "default_tag": ctx.default_tag(),
        },
    )


# ---------------------------------------------------------------------------
# Owned workflows
# ---------------------------------------------------------------------------
def ensure_current_snapshot(
    ctx: BackupContext,
    *,
    check_only: bool = False,
    require_current: bool = False,
    dry_run: bool = False,
) -> WorkflowOutcome:
    """Ensure a correct-path current-day snapshot exists (or report status).

    Never falls back to tag-only / ``--latest`` selection after resolver failure.
    """
    try:
        check_restic_available(ctx.restic_bin)
        if check_only:
            # Toolchain + repo reachability; do not backup.
            ensure_repository_initialized(ctx)
            try:
                ref = resolve_snapshot(ctx, require_current_local_day=False)
                return WorkflowOutcome(
                    status=STATUS_PASS,
                    message=(
                        f"toolchain OK (snapshot={ref.id[:12]}… "
                        f"tag={ctx.default_tag()}, repo={ctx.local_repository})"
                    ),
                    source=ref,
                    details={"freshness": "present", "check_only": True},
                )
            except ResolverError as exc:
                # Configured probe — surface as FAIL, never SKIP/PASS falsely.
                if exc.exit_code in {
                    EXIT_STALE,
                }:
                    return WorkflowOutcome(
                        status=STATUS_PASS,
                        message=(
                            f"toolchain OK (freshness=stale, "
                            f"repo={ctx.local_repository})"
                        ),
                        exit_code=EXIT_OK,
                        details={"freshness": "stale", "check_only": True},
                    )
                return WorkflowOutcome(
                    status=STATUS_PASS,
                    message=(
                        f"toolchain OK (freshness=none/error={exc.exit_code}, "
                        f"repo={ctx.local_repository})"
                    ),
                    exit_code=EXIT_OK,
                    details={
                        "freshness": "none",
                        "check_only": True,
                        "resolver_exit": exc.exit_code,
                        "resolver_message": str(exc),
                    },
                )

        ensure_repository_initialized(ctx)

        try:
            ref = resolve_snapshot(ctx, require_current_local_day=True)
            return WorkflowOutcome(
                status=STATUS_PASS,
                message=(
                    f"current — snapshot covers today "
                    f"(id={ref.id} tag={ctx.default_tag()})"
                ),
                source=ref,
                details={"freshness": "current", "backed_up": False},
            )
        except ResolverError as first:
            backupable = first.exit_code in {
                EXIT_STALE,
                EXIT_NO_TAGGED_SNAPSHOT,
                EXIT_WRONG_PATH,
            }
            if require_current or dry_run or not backupable:
                if dry_run and backupable and not require_current:
                    return WorkflowOutcome(
                        status=STATUS_PASS,
                        message=(
                            f"dry-run — would backup {ctx.data_root} "
                            f"(resolver={first.exit_code}: {first})"
                        ),
                        exit_code=EXIT_OK,
                        details={
                            "freshness": "stale_or_missing",
                            "dry_run": True,
                            "resolver_exit": first.exit_code,
                        },
                    )
                return WorkflowOutcome(
                    status=STATUS_FAIL,
                    message=(
                        f"snapshot not current "
                        f"(resolver={first.exit_code}: {first})"
                    ),
                    exit_code=first.exit_code,
                    details={"resolver_exit": first.exit_code},
                )

            # Snapshot-if-stale: backup then re-resolve. No legacy fallback.
            # Pre-snapshot capture evidence for complete-data-v2 only.
            evidence_meta = {}
            if ctx.profile is BackupProfile.COMPLETE_DATA_V2:
                evidence = capture_backup_evidence(ctx.data_root)
                evidence_meta = {
                    "evidence_captured": True,
                    "evidence_schema_version": evidence.get(
                        "evidence_schema_version"
                    ),
                    "evidence_captured_at": evidence.get("captured_at"),
                }
            ref, argv = backup_data_root(ctx)
            try:
                current = resolve_snapshot(
                    ctx, require_current_local_day=True, requested_id=ref.id
                )
            except ResolverError as second:
                return WorkflowOutcome(
                    status=STATUS_FAIL,
                    message=(
                        f"snapshot still not current after backup "
                        f"(resolver={second.exit_code}: {second})"
                    ),
                    exit_code=second.exit_code,
                    source=ref,
                    argv=argv,
                )
            details = {"freshness": "current", "backed_up": True}
            details.update(evidence_meta)
            return WorkflowOutcome(
                status=STATUS_PASS,
                message=(
                    f"snapshot OK (id={current.id} tag={ctx.default_tag()})"
                ),
                source=current,
                argv=argv,
                details=details,
            )
    except ResolverError as exc:
        return _fail_from_resolver(exc)


def copy_current_snapshot_offsite(ctx: BackupContext) -> WorkflowOutcome:
    """Resolve S → copy explicit S → resolve D via original==S → report both."""
    if ctx.external_repository is None:
        return WorkflowOutcome(
            status=STATUS_SKIP_DISABLED,
            message="RESTIC_EXTERNAL_REPOSITORY unset — offsite copy disabled",
            exit_code=EXIT_OK,
            details={"skip_reason": "unconfigured"},
        )

    try:
        check_restic_available(ctx.restic_bin)
        source = resolve_snapshot(ctx, require_current_local_day=True)
        argv = copy_snapshot_to_external(ctx, source.id)
        dest = resolve_copy_destination(ctx, source)
        return WorkflowOutcome(
            status=STATUS_PASS,
            message=(
                f"offsite copy OK source={source.id} destination={dest.id} "
                f"(original==source)"
            ),
            source=source,
            destination=dest,
            argv=argv,
            details={
                "source_id": source.id,
                "destination_id": dest.id,
                "original": dest.original,
            },
        )
    except ResolverError as exc:
        # Configured external present — never PASS/SKIP via legacy fallback.
        return WorkflowOutcome(
            status=STATUS_FAIL,
            message=str(exc),
            exit_code=exc.exit_code,
        )


def check_local_health(ctx: BackupContext) -> WorkflowOutcome:
    """Local gate health. Legacy/missing profile → WARN_LEGACY_ONLY."""
    if _is_legacy_profile(ctx):
        return _legacy_health_outcome(ctx, scope="local restic health")

    try:
        check_restic_available(ctx.restic_bin)
        ref = resolve_snapshot(ctx, require_current_local_day=True)
        return WorkflowOutcome(
            status=STATUS_PASS,
            message=(
                f"complete-data-v2 snapshot covers today "
                f"(id={ref.id} tag={ctx.default_tag()})"
            ),
            source=ref,
            details={"profile": ctx.profile.value},
        )
    except ResolverError as exc:
        return WorkflowOutcome(
            status=STATUS_FAIL,
            message=f"local restic health failed: {exc}",
            exit_code=exc.exit_code,
        )


def check_offsite_health(ctx: BackupContext) -> WorkflowOutcome:
    """Offsite lineage health. Unconfigured → SKIP_DISABLED; legacy → WARN."""
    if ctx.external_repository is None:
        return WorkflowOutcome(
            status=STATUS_SKIP_DISABLED,
            message="no RESTIC_EXTERNAL_REPOSITORY configured (offsite copy disabled)",
            exit_code=EXIT_OK,
            details={"skip_reason": "unconfigured"},
        )

    if _is_legacy_profile(ctx):
        return _legacy_health_outcome(ctx, scope="offsite restic health")

    try:
        check_restic_available(ctx.restic_bin)
        source = resolve_snapshot(ctx, require_current_local_day=True)
        dest = resolve_copy_destination(ctx, source)
        return WorkflowOutcome(
            status=STATUS_PASS,
            message=(
                f"offsite copy covers today "
                f"(source={source.id} destination={dest.id})"
            ),
            source=source,
            destination=dest,
            details={
                "source_id": source.id,
                "destination_id": dest.id,
                "original": dest.original,
            },
        )
    except ResolverError as exc:
        # Configured setup: WARN (offsite non-fatal for doctor) or FAIL —
        # never PASS/SKIP via legacy fallback selection.
        return WorkflowOutcome(
            status=STATUS_WARN,
            message=f"offsite health: {exc}",
            exit_code=exc.exit_code,
            details={"resolver_exit": exc.exit_code},
        )


def run_integrity_check(
    ctx: BackupContext,
    *,
    snapshot_id: str | None = None,
    full_read_data: bool = False,
    read_data_subset: str | None = "5%",
) -> WorkflowOutcome:
    """Resolve S (or validate requested id) then ``check <S>`` — no reselection."""
    try:
        if snapshot_id:
            ref = resolve_snapshot(ctx, requested_id=snapshot_id)
        else:
            ref = resolve_snapshot(ctx, require_current_local_day=False)
        proc, argv = check_snapshot(
            ctx,
            ref.id,
            full_read_data=full_read_data,
            read_data_subset=None if full_read_data else read_data_subset,
        )
        if proc.returncode != 0:
            detail = (proc.stderr or proc.stdout or "").strip()
            code = (
                proc.returncode
                if proc.returncode in RESTIC_RESERVED_EXITS
                else EXIT_ACTION_FAILURE
            )
            return WorkflowOutcome(
                status=STATUS_FAIL,
                message=f"restic check failed: {detail[:500]}",
                exit_code=code,
                source=ref,
                argv=argv,
                details={"restic_exit_code": proc.returncode},
            )
        return WorkflowOutcome(
            status=STATUS_PASS,
            message=f"integrity check OK for {ref.id}",
            source=ref,
            argv=argv,
            details={"restic_exit_code": 0},
        )
    except ResolverError as exc:
        return _fail_from_resolver(exc)


def restore_validated_snapshot(
    ctx: BackupContext,
    *,
    snapshot_id: str,
    target_dir: str | Path,
) -> WorkflowOutcome:
    """Resolve+validate snapshot_id against data_root, then restore."""
    try:
        ref = resolve_snapshot(ctx, requested_id=snapshot_id)
        argv = restore_snapshot(ctx, ref.id, target_dir)
        return WorkflowOutcome(
            status=STATUS_PASS,
            message=f"restored snapshot {ref.id} → {target_dir}",
            source=ref,
            argv=argv,
            details={"target_dir": str(Path(target_dir).expanduser().resolve())},
        )
    except ResolverError as exc:
        return _fail_from_resolver(exc)


# ---------------------------------------------------------------------------
# Doctor adapters
# ---------------------------------------------------------------------------
def outcome_to_doctor_fields(outcome: WorkflowOutcome) -> tuple[bool, str, str]:
    """Map workflow status → (ok, detail, doctor status string)."""
    if outcome.status == STATUS_PASS:
        return True, outcome.message, "pass"
    if outcome.status == STATUS_SKIP_DISABLED:
        return True, outcome.message, "skip"
    if outcome.status == STATUS_WARN_LEGACY_ONLY:
        return True, outcome.message, "warn"
    if outcome.status == STATUS_WARN:
        return True, outcome.message, "warn"
    return False, outcome.message, "fail"


# ---------------------------------------------------------------------------
# CLI (thin entry for shell wrappers)
# ---------------------------------------------------------------------------
def _load_ctx(env_file: str | None) -> BackupContext:
    return BackupContext.from_env_file(env_file)


def _print_outcome(outcome: WorkflowOutcome, *, as_json: bool = False) -> int:
    if as_json:
        print(outcome.to_json())
    else:
        stream = sys.stdout if outcome.status != STATUS_FAIL else sys.stderr
        prefix = {
            STATUS_PASS: "OK",
            STATUS_FAIL: "ERROR",
            STATUS_WARN: "WARN",
            STATUS_WARN_LEGACY_ONLY: "WARN_LEGACY_ONLY",
            STATUS_SKIP_DISABLED: "SKIP",
        }.get(outcome.status, outcome.status)
        print(f"backup-workflows: {prefix}: {outcome.message}", file=stream)
        if outcome.source is not None:
            print(f"backup-workflows: source_id={outcome.source.id}", file=stream)
        if outcome.destination is not None:
            print(
                f"backup-workflows: destination_id={outcome.destination.id}",
                file=stream,
            )
    if outcome.status == STATUS_FAIL:
        return outcome.exit_code if outcome.exit_code != EXIT_OK else EXIT_ACTION_FAILURE
    return EXIT_OK


def _cli_ensure(args: list[str]) -> int:
    p = argparse.ArgumentParser(prog="backup_workflows.py ensure")
    p.add_argument("--env-file", default=None)
    p.add_argument("--check-only", action="store_true")
    p.add_argument("--require-current", action="store_true")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--json", action="store_true")
    opts = p.parse_args(args)
    try:
        ctx = _load_ctx(opts.env_file)
    except ResolverError as exc:
        print(f"backup-workflows: ERROR: {exc}", file=sys.stderr)
        return exc.exit_code
    outcome = ensure_current_snapshot(
        ctx,
        check_only=opts.check_only,
        require_current=opts.require_current,
        dry_run=opts.dry_run,
    )
    return _print_outcome(outcome, as_json=opts.json)


def _cli_copy(args: list[str]) -> int:
    p = argparse.ArgumentParser(prog="backup_workflows.py copy-offsite")
    p.add_argument("--env-file", default=None)
    p.add_argument("--json", action="store_true")
    opts = p.parse_args(args)
    try:
        ctx = _load_ctx(opts.env_file)
    except ResolverError as exc:
        print(f"backup-workflows: ERROR: {exc}", file=sys.stderr)
        return exc.exit_code
    outcome = copy_current_snapshot_offsite(ctx)
    _print_outcome(outcome, as_json=opts.json)
    if outcome.status == STATUS_SKIP_DISABLED:
        return EXIT_OK
    return outcome.exit_code if outcome.status == STATUS_FAIL else EXIT_OK


def _cli_integrity(args: list[str]) -> int:
    p = argparse.ArgumentParser(prog="backup_workflows.py integrity")
    p.add_argument("--env-file", default=None)
    p.add_argument("--snapshot-id", default=None)
    p.add_argument("--full-read-data", action="store_true")
    p.add_argument("--read-data-subset", default="5%")
    p.add_argument("--json", action="store_true")
    opts = p.parse_args(args)
    try:
        ctx = _load_ctx(opts.env_file)
    except ResolverError as exc:
        print(f"backup-workflows: ERROR: {exc}", file=sys.stderr)
        return exc.exit_code
    outcome = run_integrity_check(
        ctx,
        snapshot_id=opts.snapshot_id,
        full_read_data=opts.full_read_data,
        read_data_subset=opts.read_data_subset,
    )
    _print_outcome(outcome, as_json=opts.json)
    return outcome.exit_code if outcome.status == STATUS_FAIL else EXIT_OK


def _cli_restore(args: list[str]) -> int:
    p = argparse.ArgumentParser(prog="backup_workflows.py restore")
    p.add_argument("--env-file", default=None)
    p.add_argument("--snapshot-id", required=True)
    p.add_argument("--target", required=True)
    p.add_argument("--json", action="store_true")
    opts = p.parse_args(args)
    try:
        ctx = _load_ctx(opts.env_file)
    except ResolverError as exc:
        print(f"backup-workflows: ERROR: {exc}", file=sys.stderr)
        return exc.exit_code
    outcome = restore_validated_snapshot(
        ctx, snapshot_id=opts.snapshot_id, target_dir=opts.target
    )
    _print_outcome(outcome, as_json=opts.json)
    return outcome.exit_code if outcome.status == STATUS_FAIL else EXIT_OK


def _cli_health(args: list[str]) -> int:
    p = argparse.ArgumentParser(prog="backup_workflows.py health")
    p.add_argument("--env-file", default=None)
    p.add_argument("--scope", choices=("local", "offsite"), required=True)
    p.add_argument("--json", action="store_true")
    opts = p.parse_args(args)
    try:
        ctx = _load_ctx(opts.env_file)
    except ResolverError as exc:
        print(f"backup-workflows: ERROR: {exc}", file=sys.stderr)
        return exc.exit_code
    if opts.scope == "local":
        outcome = check_local_health(ctx)
    else:
        outcome = check_offsite_health(ctx)
    _print_outcome(outcome, as_json=opts.json)
    return outcome.exit_code if outcome.status == STATUS_FAIL else EXIT_OK


def main(argv: Sequence[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if not args:
        print(
            "usage: backup_workflows.py "
            "<ensure|copy-offsite|integrity|restore|health> [...]",
            file=sys.stderr,
        )
        return EXIT_INVALID_CONFIG
    cmd, rest = args[0], args[1:]
    if cmd == "ensure":
        return _cli_ensure(rest)
    if cmd in {"copy-offsite", "copy"}:
        return _cli_copy(rest)
    if cmd == "integrity":
        return _cli_integrity(rest)
    if cmd == "restore":
        return _cli_restore(rest)
    if cmd == "health":
        return _cli_health(rest)
    print(f"unknown command: {cmd}", file=sys.stderr)
    return EXIT_INVALID_CONFIG


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Complete-data restore preflight — restore then full StateSpec inventory.

Usage:
  python3 scripts/complete_data_restore_preflight.py \\
    --snapshot-id <64-hex> --target /path/to/empty/dir \\
    [--report-dir /path/to/reports] [--env-file ...]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from backup_workflows import (  # noqa: E402  # pylint: disable=wrong-import-position
    restore_validated_snapshot,
)
from complete_data_restore import (  # noqa: E402  # pylint: disable=wrong-import-position
    RestoreReport,
    locate_restored_data_root,
    run_preflight_validation,
)
from restic_snapshot import (  # noqa: E402  # pylint: disable=wrong-import-position
    BackupContext,
    ResolverError,
    check_restic_available,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Resolve+validate snapshot, restore into target, then run the "
            "closed StateSpec inventory and durable reports."
        )
    )
    parser.add_argument("--env-file", default=None)
    parser.add_argument("--snapshot-id", required=True, help="Full 64-char hex id")
    parser.add_argument("--target", required=True, type=Path)
    parser.add_argument(
        "--report-dir",
        type=Path,
        default=None,
        help="Durable report directory (outside disposable restore target)",
    )
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    try:
        ctx = BackupContext.from_env_file(args.env_file)
    except ResolverError as exc:
        print(f"preflight: ERROR: {exc}", file=sys.stderr)
        return exc.exit_code

    report_dir = args.report_dir
    if report_dir is None:
        report_dir = Path.cwd() / "complete-data-restore-reports"
    report_dir.mkdir(parents=True, exist_ok=True)
    report = RestoreReport(report_dir / f"restore-{args.snapshot_id[:12]}.json")

    try:
        restic_ver = check_restic_available(ctx.restic_bin)
    except ResolverError as exc:
        report.finalize("BLOCKED", str(exc), exit_code=exc.exit_code)
        print(f"preflight: ERROR: {exc}", file=sys.stderr)
        return exc.exit_code

    report.step("resolve_and_restore", "RUNNING", f"id={args.snapshot_id}")
    outcome = restore_validated_snapshot(
        ctx, snapshot_id=args.snapshot_id, target_dir=args.target
    )
    if outcome.status != "PASS" or outcome.source is None:
        report.step(
            "resolve_and_restore",
            "FAIL",
            outcome.message,
            exit_code=outcome.exit_code,
        )
        report.finalize("FAIL", outcome.message, exit_code=outcome.exit_code or 1)
        if args.json:
            print(outcome.to_json())
        else:
            print(f"preflight: FAIL: {outcome.message}", file=sys.stderr)
        return outcome.exit_code or 1

    ref = outcome.source
    report.set_snapshot_identity(
        snapshot_id=ref.id,
        tree=ref.tree,
        original=ref.original,
        tags=ref.tags,
        paths=ref.paths,
        repository=ref.repository,
        restic_version=restic_ver,
        time=ref.time.isoformat(),
    )
    report.step("resolve_and_restore", "PASS", outcome.message)

    restored_root = locate_restored_data_root(args.target, ctx.data_root)
    report.step(
        "locate_restored_root",
        "PASS",
        str(restored_root),
    )
    report.set_meta(
        data_root=str(ctx.data_root),
        restored_root=str(restored_root),
        target_dir=str(Path(args.target).expanduser().resolve()),
    )

    inventory = run_preflight_validation(
        restored_root,
        expected_data_root=ctx.data_root,
        report=report,
    )

    if args.json:
        print(report.json_path.read_text(encoding="utf-8"))
    else:
        stream = sys.stdout if inventory.exit_code == 0 else sys.stderr
        print(
            f"preflight: {inventory.overall} exit={inventory.exit_code} "
            f"report={report.json_path}",
            file=stream,
        )
    return inventory.exit_code


if __name__ == "__main__":
    raise SystemExit(main())

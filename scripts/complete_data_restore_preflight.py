#!/usr/bin/env python3
"""Complete-data restore preflight CLI.

Restores a validated snapshot into an isolated disposable run, executes
the full inventory and classification matrix, and writes durable reports.
Never touches live data or performs automatic repair.

Architecture: docs/plans/ARCHITECTURE-complete-data-backup-audit-closure.md
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from complete_data_restore import (  # noqa: E402
    EXIT_BLOCKED,
    EXIT_INTERNAL_FAILURE,
    EXIT_REPAIRABLE_DRIFT,
    EXIT_VALID,
    InventoryResult,
    RestoreReport,
    inventory_restored_state,
)
from restic_snapshot import (  # noqa: E402
    EXIT_STALE,
    ResolverError,
    check_restic_available,
    resolve_snapshot,
)


DEFAULT_REPORT_DIR = Path(
    os.environ.get(
        "CONVMEM_BACKUP_REPORT_DIR",
        str(Path(os.environ.get("XDG_STATE_HOME", str(Path.home() / ".local" / "state")))
            / "convmem" / "backup-audit"),
    )
)


def load_restic_env(env_file: Path | None = None) -> dict[str, str]:
    path = env_file or Path(
        os.environ.get("CONVMEM_RESTIC_ENV", Path.home() / ".config/convmem/restic.env")
    )
    if not path.is_file():
        print(f"ERROR: missing restic env: {path}", file=sys.stderr)
        sys.exit(EXIT_INTERNAL_FAILURE)
    env = os.environ.copy()
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        key = key.strip()
        val = val.strip().strip("'").strip('"')
        if key:
            env[key] = val
    return env


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Complete-data restore preflight — validate a Restic snapshot in isolation."
    )
    parser.add_argument(
        "--snapshot-id",
        default=None,
        help="Explicit snapshot ID (optional; resolves current complete-data snapshot by default)",
    )
    parser.add_argument(
        "--parent",
        type=Path,
        default=Path(tempfile.gettempdir()) / "convmem-restore-preflight",
        help="Parent for isolated restore run and reports",
    )
    parser.add_argument(
        "--report-dir",
        type=Path,
        default=DEFAULT_REPORT_DIR,
        help="Durable report directory (outside the run)",
    )
    parser.add_argument(
        "--keep-run-dir",
        action="store_true",
        help="Keep the isolated run directory after completion (debug)",
    )
    parser.add_argument(
        "--env-file",
        type=Path,
        default=None,
    )
    args = parser.parse_args(argv)

    check_restic_available()

    env = load_restic_env(args.env_file)
    repo = env.get("RESTIC_REPOSITORY", "").strip()
    pass_file = env.get("RESTIC_PASSWORD_FILE", "").strip()
    if not repo or not pass_file:
        print("ERROR: RESTIC_REPOSITORY and RESTIC_PASSWORD_FILE required", file=sys.stderr)
        return EXIT_INTERNAL_FAILURE

    data_root = env.get("CONVMEM_DATA_ROOT", "").strip()
    if not data_root:
        chroma = env.get("CONVMEM_CHROMA_DIR", "").strip()
        if chroma:
            data_root = str(Path(chroma).expanduser().resolve().parent)
    if not data_root:
        print("ERROR: CONVMEM_DATA_ROOT unset", file=sys.stderr)
        return EXIT_INTERNAL_FAILURE
    expected_data_root = Path(data_root)

    # Set up report
    parent = args.parent.expanduser()
    parent.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    report_dir = args.report_dir.expanduser()
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / f"restore-preflight-{stamp}.json"
    report = RestoreReport(report_path)

    run_dir: Path | None = None

    def cleanup() -> None:
        if run_dir is not None and run_dir.exists() and not args.keep_run_dir:
            shutil.rmtree(run_dir, ignore_errors=True)

    try:
        # Resolve snapshot
        try:
            snap_ref = resolve_snapshot(
                repository=repo,
                expected_data_root=expected_data_root,
                required_tag="convmem-data-v1",
                require_current_local_day=True,
                requested_id=args.snapshot_id,
            )
        except ResolverError as exc:
            report.step("resolve_snapshot", "FAIL", str(exc))
            report.finalize("FAIL", f"resolve: {exc}", exit_code=exc.exit_code)
            print(f"FAIL: {exc}", file=sys.stderr)
            print(f"report={report_path}")
            return exc.exit_code

        report.set_meta(
            snapshot_id=snap_ref.id,
            data_root=str(expected_data_root),
            repository=snap_ref.repository,
        )
        report.step("resolve_snapshot", "PASS", f"id={snap_ref.id[:12]}")

        # Create isolated run directory
        run_dir = Path(tempfile.mkdtemp(prefix="restore-", dir=str(parent)))
        report.set_meta(restored_root=str(run_dir))
        report.step("create_run_dir", "PASS", str(run_dir))

        # Restore with --verify
        restic_env = dict(os.environ)
        restic_env["RESTIC_PASSWORD_FILE"] = str(Path(pass_file).expanduser().resolve())
        proc = subprocess.run(
            ["restic", "-r", repo, "restore", snap_ref.id, "--target", str(run_dir), "--verify"],
            capture_output=True,
            text=True,
            env=restic_env,
            check=False,
        )
        if proc.returncode != 0:
            report.step("restic_restore", "FAIL", (proc.stderr or proc.stdout or "restore failed")[:500])
            report.finalize("FAIL", "restic restore failed", exit_code=EXIT_INTERNAL_FAILURE)
            print(f"FAIL: restic restore failed", file=sys.stderr)
            print(f"report={report_path}")
            return EXIT_INTERNAL_FAILURE
        report.step("restic_restore", "PASS", "exit 0 with --verify")

        # Find the actual data root inside the restored directory
        # Restic restores the full path structure, so we need to find
        # the data root inside the restore target
        restored_data_root = run_dir
        # Walk to find the actual data
        prefix_parts = expected_data_root.parts[1:]  # strip leading /
        for part in prefix_parts:
            candidate = restored_data_root / part
            if candidate.is_dir():
                restored_data_root = candidate
            else:
                break

        if not restored_data_root.is_dir() or restored_data_root == run_dir:
            report.step("discover_root", "FAIL", f"cannot locate restored data root under {run_dir}")
            report.finalize("FAIL", "cannot locate restored data root", exit_code=EXIT_INTERNAL_FAILURE)
            return EXIT_INTERNAL_FAILURE
        report.step("discover_root", "PASS", str(restored_data_root))

        # Run the inventory and classification
        inv_result = inventory_restored_state(restored_data_root, expected_data_root)

        for c in inv_result.classifications:
            report.step(
                f"classify:{c.path_hint}",
                c.classification,
                f"{c.authority} — {c.detail}",
            )

        report.finalize(
            inv_result.overall,
            f"classification={inv_result.overall}",
            exit_code=inv_result.exit_code,
        )

        if inv_result.exit_code == EXIT_VALID:
            print(f"VALID — report={report_path}")
        elif inv_result.exit_code == EXIT_REPAIRABLE_DRIFT:
            print(f"VALID_WITH_REPAIRABLE_DERIVED_DRIFT — report={report_path}")
        else:
            print(f"BLOCKED — report={report_path}")

        print(f"  md={report_path.with_suffix('.md')}")
        return inv_result.exit_code

    except Exception as exc:
        report.step("unexpected", "FAIL", str(exc)[:500])
        report.finalize("FAIL", str(exc), exit_code=EXIT_INTERNAL_FAILURE)
        print(f"FAIL: {exc}", file=sys.stderr)
        print(f"report={report_path}")
        return EXIT_INTERNAL_FAILURE
    finally:
        cleanup()
        if run_dir is not None:
            exists = run_dir.exists()
            report.step(
                "cleanup",
                "PASS" if (not exists or args.keep_run_dir) else "FAIL",
                "kept" if args.keep_run_dir and exists else "removed",
            )


if __name__ == "__main__":
    raise SystemExit(main())

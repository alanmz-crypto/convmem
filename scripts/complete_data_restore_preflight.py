#!/usr/bin/env python3
"""Complete-data restore preflight (T2 stub).

Wires selection + restore through backup_workflows.restore_validated_snapshot.
Full StateSpec validation matrix lands in T4 (complete_data_restore.py).

Usage:
  python3 scripts/complete_data_restore_preflight.py \\
    --snapshot-id <64-hex> --target /path/to/empty/dir [--env-file ...]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from backup_workflows import restore_validated_snapshot  # noqa: E402
from restic_snapshot import BackupContext, ResolverError  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "T2 preflight: resolve+validate snapshot against data_root, then restore. "
            "Full StateSpec matrix is T4."
        )
    )
    parser.add_argument("--env-file", default=None)
    parser.add_argument("--snapshot-id", required=True, help="Full 64-char hex id")
    parser.add_argument("--target", required=True, type=Path)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    try:
        ctx = BackupContext.from_env_file(args.env_file)
    except ResolverError as exc:
        print(f"preflight: ERROR: {exc}", file=sys.stderr)
        return exc.exit_code

    outcome = restore_validated_snapshot(
        ctx, snapshot_id=args.snapshot_id, target_dir=args.target
    )
    if args.json:
        print(outcome.to_json())
    else:
        stream = sys.stdout if outcome.status == "PASS" else sys.stderr
        print(f"preflight: {outcome.status}: {outcome.message}", file=stream)
        if outcome.source is not None:
            print(f"preflight: source_id={outcome.source.id}", file=stream)
    return 0 if outcome.status == "PASS" else (outcome.exit_code or 1)


if __name__ == "__main__":
    raise SystemExit(main())

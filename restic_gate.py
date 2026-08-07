"""Fail-closed Restic snapshot gate before live Chroma writes."""

from __future__ import annotations

import os
import sys

from backup_workflows import ensure_current_snapshot
from restic_snapshot import BackupContext, ResolverError


def ensure_chroma_snapshot_for_live_write() -> None:
    """Snapshot if stale; exit nonzero on any Restic/resolver failure (blocks the write)."""
    if os.environ.get("CONVMEM_SKIP_RESTIC_GATE") == "1":
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

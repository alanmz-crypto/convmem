"""Fail-closed Restic snapshot gate before live Chroma writes.

Delegates snapshot selection to the authoritative restic_snapshot.py
resolver while preserving the existing compatibility API and exact exit
codes for protected write call sites.

Architecture: docs/plans/ARCHITECTURE-complete-data-backup-audit-closure.md
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent
_GATE_SCRIPT = _REPO_ROOT / "scripts" / "restic-ensure-chroma-snapshot.sh"


def _resolve_and_return_id() -> str:
    """Use the resolver to get the current complete-data snapshot ID.

    Falls back to the shell gate script for actual snapshot creation
    when no current snapshot exists.
    """
    from restic_snapshot import (
        EXIT_NO_TAGGED_SNAPSHOT,
        EXIT_STALE,
        EXIT_WRONG_PATH,
        ResolverError,
        resolve_snapshot,
    )

    env_file = Path(
        os.environ.get("CONVMEM_RESTIC_ENV", "~/.config/convmem/restic.env")
    ).expanduser()
    if not env_file.is_file():
        print(f"restic-gate: missing {env_file}", file=sys.stderr)
        sys.exit(1)

    from config import parse_env_file

    env = parse_env_file(env_file)
    repo = env.get("RESTIC_REPOSITORY", "").strip()
    if not repo:
        print("restic-gate: RESTIC_REPOSITORY unset", file=sys.stderr)
        sys.exit(1)

    data_root = env.get("CONVMEM_DATA_ROOT", "").strip()
    chroma_dir = env.get("CONVMEM_CHROMA_DIR", "").strip()
    if not data_root:
        if chroma_dir:
            data_root = str(Path(chroma_dir).expanduser().resolve().parent)
            print(
                f"restic-gate: CONVMEM_DATA_ROOT unset; derived from "
                f"CONVMEM_CHROMA_DIR as {data_root} (add CONVMEM_DATA_ROOT to "
                f"restic.env)",
                file=sys.stderr,
            )
        else:
            print("restic-gate: CONVMEM_DATA_ROOT and CONVMEM_CHROMA_DIR unset",
                  file=sys.stderr)
            sys.exit(1)

    try:
        ref = resolve_snapshot(
            repository=repo,
            expected_data_root=Path(data_root),
            required_tag="convmem-data-v1",
            require_current_local_day=True,
        )
        return ref.id
    except ResolverError as exc:
        if exc.exit_code in (EXIT_NO_TAGGED_SNAPSHOT, EXIT_STALE, EXIT_WRONG_PATH):
            return ""
        print(f"restic-gate: resolver error: {exc}", file=sys.stderr)
        sys.exit(exc.exit_code)


def ensure_chroma_snapshot_for_live_write() -> None:
    """Snapshot if stale; exit 1 on any Restic failure (blocks the write)."""
    if os.environ.get("CONVMEM_SKIP_RESTIC_GATE") == "1":
        return
    if not _GATE_SCRIPT.is_file():
        print(f"restic-gate: missing {_GATE_SCRIPT}", file=sys.stderr)
        sys.exit(1)

    resolved_id = _resolve_and_return_id()
    if resolved_id:
        return

    proc = subprocess.run(
        [str(_GATE_SCRIPT)],
        capture_output=True,
        text=True,
    )
    if proc.returncode == 0:
        return
    detail = (proc.stderr or proc.stdout or "Restic gate failed").strip()
    print(f"Live write BLOCKED (fail-closed): {detail}", file=sys.stderr)
    print(
        "Fix Restic (docs/RECOVER.md) or use scripts/convmem-live-write.sh",
        file=sys.stderr,
    )
    sys.exit(1)

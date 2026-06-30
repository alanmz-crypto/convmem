"""Fail-closed Restic snapshot gate before live Chroma writes."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

_GATE_SCRIPT = Path(__file__).resolve().parent / "scripts" / "restic-ensure-chroma-snapshot.sh"


def ensure_chroma_snapshot_for_live_write() -> None:
    """Snapshot if stale; exit 1 on any Restic failure (blocks the write)."""
    if os.environ.get("CONVMEM_SKIP_RESTIC_GATE") == "1":
        return
    if not _GATE_SCRIPT.is_file():
        print(f"restic-gate: missing {_GATE_SCRIPT}", file=sys.stderr)
        sys.exit(1)
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

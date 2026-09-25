#!/usr/bin/env python3
"""Inspect the Chroma write guard, or clear its quarantine after a repair.

  status            quarantine state, restore point per segment, recent guard events
  validate          structural check of every live HNSW segment      (exit 1 on failure)
  census            records Chroma lists but can no longer return by vector (exit 1 if any)
  reconcile         create or refresh restore points now; restores a torn segment if found
  clear-quarantine  remove QUARANTINE.json once the index has been repaired

status, validate and census are read-only: no Chroma client is opened and SQLite is
opened read-only. Run reconcile at deploy time with the watcher stopped, so the first
restore-point copy (a few hundred MB on the live store) does not happen inside a
memory-capped index child.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from chroma_write_guard import (  # pylint: disable=wrong-import-position
    ChromaWriteGuard,
    recover,
    segment_dirs,
    segment_signature,
    validate_segment,
    vector_census,
)


def _chroma_dir(explicit: str | None) -> Path:
    if explicit:
        return Path(explicit).expanduser()
    from config import load_config  # pylint: disable=import-outside-toplevel

    return Path(load_config()["index"]["chroma_dir"]).expanduser()


def _status(guard: ChromaWriteGuard) -> int:
    quarantine = guard.quarantine_state()
    print(f"store:       {guard.chroma_dir}")
    print(f"guard state: {guard.root}")
    print(f"quarantine:  {json.dumps(quarantine) if quarantine else 'none'}")
    for seg_id, seg in segment_dirs(guard.chroma_dir).items():
        snapshot = guard.current_snapshot(seg_id)
        if snapshot is None:
            state = "no restore point yet (created on the next guarded write)"
        elif snapshot[1].get("live_signature") == segment_signature(seg):
            state = f"restore point matches the live save ({snapshot[1].get('created_at')})"
        else:
            state = "live segment changed since the restore point (reconciled on the next guarded write)"
        print(f"segment {seg_id}: {state}")
    if guard.events_path.exists():
        print("recent events:")
        for line in guard.events_path.read_text(encoding="utf-8").splitlines()[-10:]:
            print(f"  {line}")
    return 1 if quarantine else 0


def _validate(chroma_dir: Path) -> int:
    failed = False
    for seg_id, seg in segment_dirs(chroma_dir).items():
        report = validate_segment(seg)
        print(f"segment {seg_id}: {'PASS' if report.ok else 'FAIL'}  {'; '.join(report.notes)}")
        for failure in report.failures:
            print(f"    - {failure}")
        failed = failed or not report.ok
    print(f"OVERALL: {'FAIL' if failed else 'PASS'}")
    return 1 if failed else 0


def _census(chroma_dir: Path) -> int:
    lost = 0
    for name, row in vector_census(chroma_dir).items():
        print(f"{name}: {json.dumps(row)}")
        lost += int(row["lost"])
    print(f"OVERALL: {'LOSS' if lost else 'NO LOSS'} ({lost} record(s) without a vector)")
    return 1 if lost else 0


def main(argv: list[str] | None = None) -> int:
    """Run one subcommand; exit 0 on success, 1 on a finding, 2 when the store is missing."""
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("command", choices=("status", "validate", "census", "reconcile", "clear-quarantine"))
    parser.add_argument("--chroma-dir", help="defaults to [index] chroma_dir from the convmem config")
    args = parser.parse_args(argv)
    chroma_dir = _chroma_dir(args.chroma_dir)
    if not chroma_dir.is_dir():
        print(f"no Chroma store at {chroma_dir}", file=sys.stderr)
        return 2
    guard = ChromaWriteGuard(chroma_dir)
    if args.command == "status":
        return _status(guard)
    if args.command == "validate":
        return _validate(chroma_dir)
    if args.command == "census":
        try:
            return _census(chroma_dir)
        except (OSError, sqlite3.Error) as exc:
            print(f"census unavailable: {exc}", file=sys.stderr)
            return 2
    if args.command == "reconcile":
        events = recover(chroma_dir)
        for event in events:
            print(json.dumps(event, sort_keys=True))
        print(f"reconciled: {len(events)} change(s); run status for the current restore points")
        return 0
    print(f"cleared {guard.quarantine_path}" if guard.clear_quarantine() else "no quarantine to clear")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

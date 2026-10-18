#!/usr/bin/env python3
"""Two-process T3 race worker (Arc #286)."""
from __future__ import annotations
import json, sys, time
from pathlib import Path
REPO_ROOT = Path(__file__).resolve().parents[1]
import sys as _s
_s.path.insert(0, str(REPO_ROOT))
from bootstrap_codex_v2_authority import claim_initial_authority
from bootstrap_codex_v3_preparation_lease import legacy_shared_preparation_lease
from bootstrap_codex_v3_writer_coordination import recheck_reservation_before_commit, source_state_dir_for_path
from tests.fixtures.issue_286_t2_owner_context import t2_owner_context

def main() -> int:
    action = sys.argv[1]
    cfg_path = Path(sys.argv[2])
    source = Path(sys.argv[3])
    grant_path = Path(sys.argv[4])
    barrier = Path(sys.argv[5]) if len(sys.argv) > 5 else None
    cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
    grant = json.loads(grant_path.read_text(encoding="utf-8"))
    state_dir = source_state_dir_for_path(cfg, source)
    if action == "hold_legacy_prep":
        with legacy_shared_preparation_lease(state_dir):
            if barrier: barrier.write_text("ready", encoding="utf-8")
            time.sleep(2.0)
        return 0
    if action == "claim_initial":
        if barrier:
            while not barrier.is_file(): time.sleep(0.01)
        with t2_owner_context(state_dir):
            claim_initial_authority(state_dir, grant)
        return 0
    if action == "recheck_commit":
        if barrier:
            while not barrier.is_file(): time.sleep(0.01)
        recheck_reservation_before_commit(cfg, source)
        return 0
    raise SystemExit(f"unknown action: {action}")
if __name__ == "__main__": raise SystemExit(main())

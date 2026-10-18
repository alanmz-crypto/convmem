#!/usr/bin/env python3
"""Child worker for T2 parent-driven crash matrix (Arc #286)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from bootstrap_codex_v2_authority import (
    claim_initial_authority,
    claim_recovery_authority,
    load_authority,
    mirror_invocation_start,
    publish_authority_progress,
    publish_terminal_authority,
)
from bootstrap_codex_v2_permits import CodexV2PaidLedger
from tests.fixtures.issue_286_t2_owner_context import t2_owner_context


def main() -> int:
    action = sys.argv[1]
    state_dir = Path(sys.argv[2])
    grant_path = Path(sys.argv[3])
    grant = json.loads(grant_path.read_text(encoding="utf-8"))
    with t2_owner_context(state_dir):
        if action == "initial":
            claim_initial_authority(state_dir, grant)
        elif action == "mirror":
            mirror_invocation_start(state_dir, grant)
        elif action == "recovery":
            claim_recovery_authority(state_dir, grant)
        elif action == "terminal":
            if load_authority(state_dir) is None:
                claim_initial_authority(state_dir, grant)
            publish_terminal_authority(
                state_dir,
                grant,
                receipt_digest="c" * 64,
                receipt_path=state_dir / "terminal_receipt.json",
            )
        elif action == "permit":
            if load_authority(state_dir) is None:
                claim_initial_authority(state_dir, grant)
            ledger = CodexV2PaidLedger(state_dir, grant)
            ledger.consume_provider_http_attempt(
                {
                    "provider": "deepseek",
                    "operation": "generate",
                    "model": grant["distill_model"],
                    "base_url": grant["distill_base_url"],
                }
            )
        elif action == "progress":
            if load_authority(state_dir) is None:
                claim_initial_authority(state_dir, grant)
            publish_authority_progress(state_dir, grant, progress={"checkpoint_digest": "a" * 64})
        elif action == "ordinal3":
            claim_initial_authority(state_dir, grant)
            claim_recovery_authority(state_dir, grant)
            claim_recovery_authority(state_dir, grant)
        else:
            raise SystemExit(f"unknown action: {action}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

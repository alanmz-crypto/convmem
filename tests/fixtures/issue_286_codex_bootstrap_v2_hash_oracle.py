"""Synthetic v2 hash oracle for Arc Codex #286 T1 evidence (metadata only)."""

from __future__ import annotations

from pathlib import Path

from bootstrap_codex_v2 import grant_fingerprint_v2
from incremental_jsonl import source_state_id


def build_oracle_grant(isolation_root: Path) -> dict:
    from tests.test_issue_286_codex_bootstrap_v2_t1 import _rollout_fixture, _v2_grant

    class _MonkeyPatch:
        def setenv(self, key: str, value: str) -> None:
            import os

            os.environ[key] = value

    source, cfg, prefix, boundary = _rollout_fixture(isolation_root, _MonkeyPatch())
    grant = _v2_grant(source, cfg, prefix_sha256=prefix, complete_boundary=boundary)
    return {
        "operation_id": grant["operation_id"],
        "grant_fingerprint_v2": grant_fingerprint_v2(grant),
        "source_state_id": grant["source_state_id"],
        "kiro_default_state_id": source_state_id(str(source)),
    }

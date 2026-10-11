"""T0 baseline and evidence tests for JSONL production canary P1."""

from __future__ import annotations

import hashlib
from pathlib import Path

from incremental_jsonl_canary import assemble_evidence


BASELINE_HASHES = {
    # Intentionally refreshed: Arc Poison Pill Part B write guard (2026-09-24) —
    # watch.py restores torn HNSW saves after an abrupt index-child exit; see
    # docs/inter-model/CLAUDE-2026-09-24-chroma-upsert-containment-handoff.md
    # Refreshed for issue #286 Codex rollout admission: terminal live-route
    # refusal quarantine keyed by (path, prefix digest).
    "watch.py": "c390854cfe599b61a4586d12a4154d34f4e805528d413d8ba42db143347bc59a",
    # Refreshed for issue #286's authorized bootstrap safety corrective:
    # bootstrap-only accounting and immutable replay authority cross these
    # bytes; the canary remains unreachable from the CLI and watcher.
    "ingest.py": "8d3062f262b3888ebaebd86fe2bc2f6d3311c7e964f5c446394ba9bef3d6014d",
    # Baseline refreshed for failed-bootstrap supersession/recovery authority
    # and lifetime attempt accounting; the canary remains unreachable from the
    # CLI and watcher.
    # Refreshed for issue #286 Codex rollout admission route, guards, and
    # structured admitted-run logging.
    "incremental_jsonl.py": "72d3d8d2e558550ec494a916a17bd8b0630e358731d727c0dfa89ed79ba12ea0",
    "incremental_jsonl_isolation.py": "818325221d46b1501795895b82d2465151b12ab76f0f11f21f42d8438c0a6df1",
}


def test_t0_baseline_hashes_unchanged() -> None:
    root = Path(".")
    for name, expected in BASELINE_HASHES.items():
        actual = hashlib.sha256((root / name).read_bytes()).hexdigest()
        assert actual == expected, name


def test_p1_a14_evidence_is_reproducible_structure() -> None:
    payload = assemble_evidence(t0={"baseline": BASELINE_HASHES}, hermetic=True)
    assert payload["hermetic"] is True
    assert payload["sections"]["t0"]["baseline"] == BASELINE_HASHES

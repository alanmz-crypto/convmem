"""T0 baseline and evidence tests for JSONL production canary P1."""

from __future__ import annotations

import hashlib
from pathlib import Path

from incremental_jsonl_canary import assemble_evidence


BASELINE_HASHES = {
    # Intentionally refreshed: Arc Poison Pill Part B write guard (2026-09-24) —
    # watch.py restores torn HNSW saves after an abrupt index-child exit; see
    # docs/inter-model/CLAUDE-2026-09-24-chroma-upsert-containment-handoff.md
    "watch.py": "ff226b0890017175af2664a8d5da49a9a31eca9a9ee750084b6535995a94cb7c",
    # Refreshed for issue #286's authorized bootstrap safety corrective:
    # bootstrap-only attempt accounting and recovery now cross these authority
    # bytes; the canary remains unreachable from the CLI and watcher.
    "ingest.py": "8d3062f262b3888ebaebd86fe2bc2f6d3311c7e964f5c446394ba9bef3d6014d",
    "incremental_jsonl.py": "b46445e2bd9796be93afff32baaa78060a0a776cb3a7e9dbaf9fca53f290599d",
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

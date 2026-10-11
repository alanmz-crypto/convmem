"""T0 baseline and evidence tests for JSONL production canary P1."""

from __future__ import annotations

import hashlib
from pathlib import Path

from incremental_jsonl_canary import assemble_evidence


BASELINE_HASHES = {
    # Intentionally refreshed: Arc Poison Pill Part B write guard (2026-09-24) —
    # watch.py restores torn HNSW saves after an abrupt index-child exit; see
    # docs/inter-model/CLAUDE-2026-09-24-chroma-upsert-containment-handoff.md
    # Refreshed for issue #286 terminal path refusal quarantine (§13 c3/c4) and
    # issue #268 D1 scratch diagnosis harness on the merged branch.
    "watch.py": "dde8e84a13cb4f897b51b1a18688c5bdfd93b3a148342f59d369ff803bfd6e94",
    # Refreshed for issue #286 bootstrap safety and Codex D8 lineage; refreshed
    # again for issue #268 D1 live-diagnosis phase marks on the merged branch.
    "ingest.py": "b6454436cea7c561128c7beea3a885a67884da68dd8d1acfd4023aaa2314623b",
    # Baseline refreshed for failed-bootstrap supersession/recovery authority
    # and lifetime attempt accounting; the canary remains unreachable from the
    # CLI and watcher.
    # Refreshed for issue #286 Codex rollout admission route, guards, and
    # structured admitted-run logging.
    "incremental_jsonl.py": "b06aa772d820e4563d30a1af98b45fca2329d39efc92ba79ce19859a8ceedafe",
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

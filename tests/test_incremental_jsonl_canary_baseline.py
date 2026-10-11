"""T0 baseline and evidence tests for JSONL production canary P1."""

from __future__ import annotations

import hashlib
from pathlib import Path

from incremental_jsonl_canary import assemble_evidence


BASELINE_HASHES = {
    # Intentionally refreshed: Arc Poison Pill Part B write guard (2026-09-24) —
    # watch.py restores torn HNSW saves after an abrupt index-child exit; see
    # docs/inter-model/CLAUDE-2026-09-24-chroma-upsert-containment-handoff.md
    # Refreshed for issue #268 D1 scratch diagnosis harness: env-gated
    # live-diagnosis phase marks and hermetic inner-scope wiring; the canary
    # remains unreachable from the CLI and watcher.
    "watch.py": "77dcbacd364473ab0b5c353b2fe7f953860a8db64442a1e3f94ef61484279f58",
    # Refreshed for issue #286's authorized bootstrap safety corrective:
    # bootstrap-only accounting and immutable replay authority cross these
    # bytes; the canary remains unreachable from the CLI and watcher.
    # Refreshed again for issue #268 D1: optional live-diagnosis phase marks
    # and brief-refresh refusal hook; no canary route added.
    "ingest.py": "79fcd3a64c405e759cc756a7770160997cd67729ecc4a3af479efa751fa42558",
    # Baseline refreshed for failed-bootstrap supersession/recovery authority
    # and lifetime attempt accounting; the canary remains unreachable from the
    # CLI and watcher.
    "incremental_jsonl.py": "0cbcd03fdfdd3feda7c38604fda6ce30f40aae656ee5101cc76388143409ed7e",
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

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
    # Refreshed for approved T3 runtime802d74d reporting: recover_chroma_after_abrupt_exit
    # segment_restored message now states restored-under-containment / writes quarantined
    # until validated owner release (reviewed base458b9f6..e7b56011).
    # Refreshed for issue #286 stage-2 corrective 20 (main merge + R6-F1 escape accounting).
    # Refreshed for issue #286 watcher-child --now.
    # Refreshed for issue #286 watcher child-event forwarding.
    # Refreshed for issue #286 commit digest reuse phase-timing event.
    "watch.py": "29b00777ec7648665b5e4f9d65129f1cbcb93267ba37ec1d446bebb206860efd",
    # Refreshed for issue #308 flush_path processed_log pass-through (2026-10-12).
    # Refreshed for issue #286 bootstrap safety and Codex D8 lineage; refreshed
    # again for issue #268 D1 live-diagnosis phase marks on the merged branch.
    # Refreshed for issue #308 inter-model provenance rejection sidecar (2026-10-12).
    "ingest.py": "803bfe02856872f3389ef41567d140114c9aae5558dde294c9dbb61788aaa5e5",
    # Baseline refreshed for failed-bootstrap supersession/recovery authority
    # and lifetime attempt accounting; the canary remains unreachable from the
    # CLI and watcher.
    # Refreshed for issue #286 Codex rollout admission route, guards, and
    # structured admitted-run logging; refreshed for corrective 5 checkpointless
    # recovery bootstrap_required refusal.
    # Refreshed for issue #286 stage-2 corrective 20 (R6-F1 capture-error escape accounting).
    # Refreshed for issue #286 corrective 24 pylint comment-only suppressions (no semantics).
    # Refreshed for issue #286 Kiro exact-path recovery parity (R1-R3).
    # Refreshed for issue #286 transform contract v2 (semantic fingerprint).
    # Refreshed for issue #286 v1 checkpoint full-rebuild when allow_full_rebuild.
    # Refreshed for issue #286 full-rebuild Codex admission frontier fix.
    # Refreshed for issue #286 commit digest reuse (slice 1).
    # Refreshed for issue #286 scoped proof shadow observer wiring.
    "incremental_jsonl.py": "317c2e5c3204a0b504463a2eb84211bb6663ecdf32c4c1d205e0e3b2c8e31e06",
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

# src: ../incremental_jsonl.py — pins the reviewed production runtime identity

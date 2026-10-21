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
    # Refreshed for issue #286 Kiro incremental selected-session sidecar forwarding.
    # Refreshed for issue #286 Kiro semantic revalidate + cohort budget wiring.
    # Refreshed for OpenAI distill provider merge + PAID_PROVIDERS cohort cap.
    "watch_kiro_paths.py": "f1ef8e600226bb239ababd71f696c7b022a15c2a1714c89d5e1907cdac40741d",
    "watch.py": "0a3f9f23dd192dc9aa30d46ee6b61ae5a5c6a6b9701bac8e70760d0a9edd5214",
    # Refreshed for issue #308 flush_path processed_log pass-through (2026-10-12).
    # Refreshed for issue #286 bootstrap safety and Codex D8 lineage; refreshed
    # again for issue #268 D1 live-diagnosis phase marks on the merged branch.
    # Refreshed for issue #308 inter-model provenance rejection sidecar (2026-10-12).
    # Refreshed for issue #286 rollback processed sidecar private lock (2026-10-20):
# 6850a28ceb793d3820fe3df9f455d6b7dd08f5871072852cca5e68cc93b4ef1b ->
# 2677344f034fa412899a13aad36bd71275ae7885da280c59e4615daeccb1edce
# Refreshed for issue #286 forward processed-publication source fence (2026-10-21).
    "ingest.py": "5d1d7dfac184c617c3d8de09cab3226fa311455c321adbf7c33c10526de9c92e",
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
    # Refreshed for issue #286 Kiro incremental v2 routing and policy guards.
    # Refreshed for issue #286 corrective 2: fail-closed paid cohort accounting.
# Refreshed for issue #286 corrective 4: checkpoint sidecar identity guard.
# Refreshed for issue #286 scoped proof shadow observer wiring.
# Refreshed for issue #286 rollback processed authority replay (2026-10-20):
# Refreshed for issue #286 rollback corrective 3 (pylint W0613 transaction param drop):
# Refreshed for issue #286 forward processed-publication source fence (2026-10-21).
# 2ef62294b18de8dc0723b842e79c1625f48b026eb8b3b403e470b10a57680c95 ->
# c6a0d555dcdd3243f26140437506c791a0d3729f55d9eb2daa37bd49dda22158 ->
# b63fe717951081a33e6a0bf709fb47928b5df88991ca6fba7f4d634a901b5895 ->
# 854d5882d297dcbb4c37c35bca7abccdc37fecf4b5c70ff271bd8a4139013409
    "incremental_jsonl.py": "82eaa610f52887ba15acfa982e512323f52d4b12d4747b39aee6b315e3c6ec6f",
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

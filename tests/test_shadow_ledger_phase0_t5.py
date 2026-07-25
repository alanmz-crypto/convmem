"""T5: inventory stamp and readiness verdict helpers."""

from __future__ import annotations

import json
from pathlib import Path

from shadow_inventory import (
    build_inventory_stamp,
    classify_legacy_decision_candidate,
    readiness_verdict,
    write_report,
)


def test_inventory_stamp_no_hardcoded_audit_constants() -> None:
    stamp = build_inventory_stamp(
        code_commit="abc",
        chroma_root="/tmp/chroma",
        active_count=3,
        total_count=4,
        chroma_only_ids=["a", "b"],
    )
    blob = json.dumps(stamp)
    assert "192" not in blob
    assert "3448" not in blob
    assert stamp["chroma_only_count"] == 2


def test_classify_and_readiness() -> None:
    assert (
        classify_legacy_decision_candidate(
            title="t",
            summary="s",
            approved_match=True,
            normalized_match=False,
            looks_like_observation=False,
        )
        == "matched governed decision"
    )
    assert readiness_verdict(
        corruption=True,
        unexplained_missing=False,
        unsafe_replay=False,
        covered_touched_reconcile=True,
        unknown_provenance_only=False,
    ) == "FAIL"
    assert readiness_verdict(
        corruption=False,
        unexplained_missing=False,
        unsafe_replay=False,
        covered_touched_reconcile=True,
        unknown_provenance_only=False,
    ) == "PASS — delta capture"


def test_write_report(tmp_path: Path) -> None:
    path = tmp_path / "ready.json"
    write_report(path, {"status": "PARTIAL"})
    assert json.loads(path.read_text())["status"] == "PARTIAL"

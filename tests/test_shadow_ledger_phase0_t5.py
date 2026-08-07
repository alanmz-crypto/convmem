# pylint: disable=duplicate-code
"""T5: inventory collector, readiness, redaction, non-mutation."""

from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest

pytest.importorskip("chromadb")

# pylint: disable=wrong-import-position
from chroma_store import ChromaStore
from shadow_inventory import (
    NOT_CLAIMED,
    build_inventory_stamp,
    classify_legacy_decision_candidate,
    classify_unit_metadata,
    collect_phase0_inventory,
    human_summary,
    readiness_verdict,
    redacted_stdout_view,
    write_report,
)
# pylint: enable=wrong-import-position


def test_inventory_stamp_no_hardcoded_audit_constants() -> None:
    stamp = build_inventory_stamp(
        code_commit="abc",
        chroma_root="/tmp/chroma",
        active_count=3,
        total_count=4,
        chroma_only_ids=["a", "b"],
        utc="2026-01-01T00:00:00Z",
    )
    blob = json.dumps(stamp)
    assert "192" not in blob
    assert "3448" not in blob
    assert stamp["chroma_only_count"] == 2


def test_module_source_has_no_audit_snapshot_constants() -> None:
    src = Path("shadow_inventory.py").read_text(encoding="utf-8")
    assert "192" not in src
    assert "3448" not in src
    assert "3,448" not in src


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


def test_classify_unit_metadata_local() -> None:
    assert (
        classify_unit_metadata(
            {"ledger_id": "dec_1", "proposal_id": "p1", "title": "t"}
        )
        == "matched governed decision"
    )
    assert (
        classify_unit_metadata({"ledger_id": "obs_1", "title": "t"})
        == "likely observation"
    )
    assert classify_unit_metadata({"title": "x"}) == "ambiguous"


def test_write_report(tmp_path: Path) -> None:
    path = tmp_path / "ready.json"
    write_report(path, {"status": "PARTIAL"})
    assert json.loads(path.read_text())["status"] == "PARTIAL"


def test_collect_inventory_disabled_partial(tmp_path: Path) -> None:
    chroma = tmp_path / "chroma"
    store = ChromaStore(str(chroma), mutation_sink=None)
    try:
        store.add_unit(
            "u1",
            "doc body must not appear in inventory",
            [0.01] * 8,
            {"ledger_id": "obs_1", "title": "t", "source_path": "/t"},
        )
    finally:
        store.close()
    cfg = {
        "index": {"chroma_dir": str(chroma)},
        "shadow_ledger": {
            "enabled": False,
            "ledger_path": str(tmp_path / "ledger.jsonl"),
            "activation_manifest_path": str(tmp_path / "act.json"),
            "health_path": str(tmp_path / "health.json"),
        },
    }
    a = collect_phase0_inventory(
        cfg, code_commit="deadbeef", utc="2026-07-25T00:00:00Z"
    )
    b = collect_phase0_inventory(
        cfg, code_commit="deadbeef", utc="2026-07-25T00:00:00Z"
    )
    assert a == b  # deterministic over identical inputs + fixed utc
    assert a["readiness"]["status"] == "PARTIAL"
    assert a["shadow"]["enabled"] is False
    assert a["inventory"]["active_unit_count"] == 1
    assert a["inventory"]["comparison_rule_version"] == 1
    assert "file_hashes" in a["inventory"]
    view = redacted_stdout_view(a)
    blob = json.dumps(view)
    assert "doc body must not appear" not in blob
    assert "doc body" not in json.dumps(a["candidates"])
    assert any(c["id"] == "u1" for c in a["candidates"])
    assert a["human_summary"].startswith("PARTIAL")
    assert a["readiness"]["status"] in a["human_summary"]
    for claim in NOT_CLAIMED:
        assert claim in a["claims"]["not_claimed"]


def test_collect_corrupt_ledger_fail(tmp_path: Path) -> None:
    chroma = tmp_path / "chroma"
    chroma.mkdir()
    # Minimal empty chroma via store
    store = ChromaStore(str(chroma), mutation_sink=None)
    store.close()
    ledger = tmp_path / "ledger.jsonl"
    ledger.write_text("{bad\n", encoding="utf-8")
    cfg = {
        "index": {"chroma_dir": str(chroma)},
        "shadow_ledger": {
            "enabled": True,
            "ledger_path": str(ledger),
            "activation_manifest_path": str(tmp_path / "act.json"),
            "health_path": str(tmp_path / "health.json"),
        },
    }
    report = collect_phase0_inventory(
        cfg, code_commit="x", utc="2026-07-25T00:00:00Z"
    )
    assert report["readiness"]["status"] == "FAIL"
    assert report["shadow"]["corrupt"] is True
    assert report["human_summary"].startswith("FAIL")


def test_pass_label_is_delta_capture_only() -> None:
    status = readiness_verdict(
        corruption=False,
        unexplained_missing=False,
        unsafe_replay=False,
        covered_touched_reconcile=True,
        unknown_provenance_only=False,
    )
    assert status == "PASS — delta capture"
    summary = human_summary(status, reasons=["reconciled"])
    assert "delta capture" in summary
    assert "activation" in summary.lower()
    for banned in ("historic rebuild", "cutover", "backup"):
        # Summary must mention that those are NOT authorized
        assert banned.split()[0] in summary.lower() or "Does not authorize" in summary


def test_inventory_module_has_no_llm_imports() -> None:
    tree = ast.parse(Path("shadow_inventory.py").read_text(encoding="utf-8"))
    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module.split(".")[0])
    assert "llm" not in imports
    assert "ollama" not in imports
    assert "requests" not in imports


def test_human_and_machine_status_agree() -> None:
    for status in ("PASS — delta capture", "PARTIAL", "FAIL"):
        summary = human_summary(status, reasons=["r"])
        assert status.split("—", maxsplit=1)[0].strip() in summary or status in summary

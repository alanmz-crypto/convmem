"""C4: doctor and inventory render one strict Shadow truth model."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

pytest.importorskip("chromadb")

# pylint: disable=wrong-import-position
from chroma_store import ChromaStore
from doctor import _check_shadow_ledger
from shadow_inventory import collect_phase0_inventory, redacted_stdout_view
# pylint: enable=wrong-import-position


def _emb() -> list[float]:
    return [0.01] * 8


def _cfg(tmp_path: Path, *, enabled: bool) -> tuple[dict, Path, Path]:
    chroma = tmp_path / "chroma"
    shadow = tmp_path / "shadow"
    shadow.mkdir()
    os.chmod(shadow, 0o700)
    return (
        {
            "index": {"chroma_dir": str(chroma)},
            "shadow_ledger": {
                "enabled": enabled,
                "ledger_path": str(shadow / "ledger.jsonl"),
                "activation_manifest_path": str(shadow / "activation.json"),
                "health_path": str(shadow / "health.json"),
            },
        },
        chroma,
        shadow,
    )


def _seed(chroma: Path) -> None:
    store = ChromaStore(str(chroma), mutation_sink=None)
    try:
        store.add_unit(
            "active", "active document", _emb(), {"source_path": "/active"}
        )
        store.add_unit(
            "historical", "historical document", _emb(), {"source_path": "/old"}
        )
        store.update_unit_metadata(
            "historical", {"source_path": "/old", "superseded": True}
        )
    finally:
        store.close()


def test_disabled_inventory_marks_every_current_id_chroma_only(tmp_path: Path) -> None:
    cfg, chroma, _shadow = _cfg(tmp_path, enabled=False)
    _seed(chroma)

    doctor = _check_shadow_ledger(cfg)
    report = collect_phase0_inventory(cfg, code_commit="test", utc="2026-07-29T00:00:00Z")

    assert doctor.ok
    assert doctor.status != "warn"
    assert report["readiness"]["status"] == "PARTIAL"
    assert report["shadow"]["state"] == "disabled"
    assert report["inventory"]["active_unit_count"] == 1
    assert report["inventory"]["historical_unit_count"] == 1
    assert report["inventory"]["total_unit_count"] == 2
    assert report["inventory"]["chroma_only_ids"] == ["active", "historical"]
    assert report["shadow"]["shadow_touched_entity_count"] == 0


def test_prepared_state_warns_doctor_and_is_partial_inventory(tmp_path: Path) -> None:
    cfg, chroma, shadow = _cfg(tmp_path, enabled=False)
    _seed(chroma)
    (shadow / "activation.json").write_text("{}\n", encoding="utf-8")
    os.chmod(shadow / "activation.json", 0o600)

    doctor = _check_shadow_ledger(cfg)
    report = collect_phase0_inventory(cfg, code_commit="test", utc="2026-07-29T00:00:00Z")

    assert doctor.ok
    assert doctor.status == "warn"
    assert "prepared_not_committed" in doctor.detail
    assert report["readiness"]["status"] == "PARTIAL"
    assert report["shadow"]["state"] == "prepared"
    assert report["readiness"]["codes"] == ["prepared_not_committed"]
    assert report["inventory"]["chroma_only_ids"] is None


def test_enabled_missing_manifest_has_same_truth_codes_everywhere(tmp_path: Path) -> None:
    cfg, chroma, _shadow = _cfg(tmp_path, enabled=True)
    _seed(chroma)

    doctor = _check_shadow_ledger(cfg)
    report = collect_phase0_inventory(cfg, code_commit="test", utc="2026-07-29T00:00:00Z")

    assert not doctor.ok
    assert report["readiness"]["status"] == "FAIL"
    assert "manifest_missing" in doctor.detail
    assert "manifest_missing" in report["readiness"]["codes"]
    assert report["shadow"]["validation_codes"] == report["readiness"]["codes"]
    assert "health_missing" in doctor.detail


def test_corrupt_ledger_is_not_empty_or_healthy(tmp_path: Path) -> None:
    cfg, chroma, shadow = _cfg(tmp_path, enabled=True)
    _seed(chroma)
    ledger = shadow / "ledger.jsonl"
    ledger.write_text("{bad\n", encoding="utf-8")
    os.chmod(ledger, 0o600)

    doctor = _check_shadow_ledger(cfg)
    report = collect_phase0_inventory(cfg, code_commit="test", utc="2026-07-29T00:00:00Z")

    assert not doctor.ok
    assert "ledger_corrupt" in doctor.detail
    assert report["readiness"]["status"] == "FAIL"
    assert "ledger_corrupt" in report["readiness"]["codes"]
    assert report["shadow"]["shadow_touched_entity_count"] is None
    assert report["inventory"]["chroma_only_ids"] is None


def test_truth_view_is_redacted_and_nonmutating(tmp_path: Path) -> None:
    cfg, chroma, _shadow = _cfg(tmp_path, enabled=False)
    _seed(chroma)
    db = chroma / "chroma.sqlite3"
    before = db.stat().st_mtime_ns

    report = collect_phase0_inventory(cfg, code_commit="test", utc="2026-07-29T00:00:00Z")
    view = redacted_stdout_view(report)

    assert db.stat().st_mtime_ns == before
    assert "active document" not in str(view)
    assert "historical document" not in str(view)
    assert report["validation"]["state"] == "disabled"

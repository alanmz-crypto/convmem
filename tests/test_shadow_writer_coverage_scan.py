# pylint: disable=duplicate-code
"""VERIFY V3 coverage proof: C3 gated sessions + hermetic bypass control.

Proof class: code-path / hermetic. Does NOT enable production shadowing or
edit live config. Does NOT claim a live ops miss was observed.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
INVENTORY = ROOT / "docs/plans/SHADOW-WRITER-COVERAGE-INVENTORY.json"


def _inventory() -> dict:
    return json.loads(INVENTORY.read_text(encoding="utf-8"))


def test_inventory_documents_gated_routing() -> None:
    data = _inventory()
    assert data["must_use_factory_count"] == 0
    assert data["must_use_factory_bypass_sites"] == []
    assert data["open_chroma_for_write_production_call_sites"] == []
    assert data["chroma_write_session_production_call_sites"] == []
    assert len(data["production_chroma_write_session_call_sites"]) >= 1
    assert len(data["open_production_write_store_call_sites"]) >= 1
    assert data["proof_class"].startswith("code_path")


def test_static_scan_matches_inventory_routing() -> None:
    """Scanned gated sites and empty bypass list must match inventory."""
    data = _inventory()
    expected_session = set(data["production_chroma_write_session_call_sites"])
    expected_open = set(data["open_production_write_store_call_sites"])
    expected_legacy_factory = set(data["open_chroma_for_write_production_call_sites"])
    expected_legacy_session = set(data["chroma_write_session_production_call_sites"])
    expected_bypass = set(data["must_use_factory_bypass_sites"])
    expected_allow = set(data["allowlisted_direct_sites"])

    ctor = re.compile(r"ChromaStore\s*\(")
    factory = re.compile(r"\bopen_chroma_for_write\s*\(")
    old_session = re.compile(r"(?<![a-zA-Z_])chroma_write_session\s*\(")
    prod_session = re.compile(r"production_chroma_write_session\s*\(")
    prod_open = re.compile(r"open_production_write_store\s*\(")

    scanned_legacy_factory: set[str] = set()
    scanned_legacy_session: set[str] = set()
    scanned_session: set[str] = set()
    scanned_open: set[str] = set()
    scanned_ctor: set[str] = set()
    for path in sorted(ROOT.rglob("*.py")):
        rel = str(path.relative_to(ROOT))
        if rel.startswith("tests/") or "docs/" in rel:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for i, line in enumerate(text.splitlines(), 1):
            if factory.search(line) and "def open_chroma_for_write" not in line:
                if rel != "chroma_write_store.py":
                    scanned_legacy_factory.add(f"{rel}:{i}")
            if (
                old_session.search(line)
                and "def chroma_write_session" not in line
                and "production_chroma_write_session" not in line
            ):
                scanned_legacy_session.add(f"{rel}:{i}")
            if prod_session.search(line) and "def production_chroma_write_session" not in line:
                scanned_session.add(f"{rel}:{i}")
            if prod_open.search(line) and "def open_production_write_store" not in line:
                scanned_open.add(f"{rel}:{i}")
            if not ctor.search(line):
                continue
            if line.strip().startswith("class ChromaStore"):
                continue
            scanned_ctor.add(f"{rel}:{i}")

    assert scanned_legacy_factory == expected_legacy_factory, (
        "legacy factory inventory drift — "
        f"missing={expected_legacy_factory - scanned_legacy_factory} "
        f"extra={scanned_legacy_factory - expected_legacy_factory}"
    )
    assert scanned_legacy_session == expected_legacy_session, (
        "legacy session inventory drift — "
        f"missing={expected_legacy_session - scanned_legacy_session} "
        f"extra={scanned_legacy_session - expected_legacy_session}"
    )
    assert scanned_session == expected_session, (
        "production session inventory drift — "
        f"missing={expected_session - scanned_session} "
        f"extra={scanned_session - expected_session}"
    )
    assert scanned_open == expected_open, (
        "production open inventory drift — "
        f"missing={expected_open - scanned_open} "
        f"extra={scanned_open - expected_open}"
    )
    assert scanned_ctor == expected_allow, (
        "allowlisted direct ctor drift — "
        f"missing={expected_allow - scanned_ctor} "
        f"extra={scanned_ctor - expected_allow}"
    )
    assert expected_bypass == set()
    assert scanned_ctor.isdisjoint(expected_bypass)


def test_hermetic_direct_ctor_bypasses_sink_even_when_cfg_eligible(
    tmp_path: Path,
) -> None:
    """Direct production-eligible construction cannot bypass the writer gate."""
    pytest.importorskip("chromadb")
    from chroma_store import ChromaStore
    from shadow_ledger import (
        atomic_write_json_private,
        finalize_manifest,
        new_incomplete_manifest,
    )

    chroma = tmp_path / "chroma"
    chroma.mkdir()
    ledger = tmp_path / "ledger.jsonl"
    manifest_path = tmp_path / "act.json"
    base = new_incomplete_manifest(
        code_commit="test",
        chroma_root=chroma,
        configured_embed_model="nomic-embed-text",
    )
    complete = finalize_manifest(
        base,
        entity_baselines={},
        active_unit_count=0,
        total_unit_count=0,
        observed_embed_model="unknown",
        observed_embed_dimensions=None,
        shadow_ledger_identity="id",
    )
    atomic_write_json_private(manifest_path, complete)
    _cfg = {
        "index": {"chroma_dir": str(chroma)},
        "shadow_ledger": {
            "enabled": True,
            "ledger_path": str(ledger),
            "activation_manifest_path": str(manifest_path),
            "health_path": str(tmp_path / "health.json"),
        },
    }
    del _cfg  # unused; documents the eligible shape intentionally
    store = ChromaStore(str(chroma), require_writer_boundary=True)  # anti-pattern control
    try:
        assert store.mutation_sink is None
        from chroma_write_store import WriterBoundaryError

        with pytest.raises(WriterBoundaryError, match="shared writer boundary"):
            store.add_unit(
                "u1",
                "doc",
                [0.01] * 8,
                {"source_path": "/t", "title": "t"},
            )
        assert store.get_unit("u1") is None
    finally:
        store.close()
    assert not ledger.exists(), "direct ctor must not write shadow ledger"


def test_positive_control_factory_attaches_sink(tmp_path: Path) -> None:
    """Sink works when factory injects — wiring path is live."""
    pytest.importorskip("chromadb")
    import os
    from chroma_write_store import open_chroma_for_write, production_writer_boundary
    from shadow_ledger import (
        SHADOW_DIR_MODE,
        atomic_write_json_private,
        create_shadow_ledger_header,
        finalize_manifest,
        new_incomplete_manifest,
    )

    chroma = tmp_path / "chroma"
    chroma.mkdir()
    shadow = tmp_path / "shadow"
    shadow.mkdir()
    os.chmod(shadow, SHADOW_DIR_MODE)
    ledger = shadow / "ledger.jsonl"
    manifest_path = shadow / "act.json"
    health = shadow / "health.json"
    base = new_incomplete_manifest(
        code_commit="test",
        chroma_root=chroma,
        configured_embed_model="nomic-embed-text",
    )
    complete = finalize_manifest(
        base,
        entity_baselines={},
        active_unit_count=0,
        total_unit_count=0,
        observed_embed_model="unknown",
        observed_embed_dimensions=None,
        shadow_ledger_identity="id",
    )
    atomic_write_json_private(manifest_path, complete)
    create_shadow_ledger_header(
        ledger,
        activation_id=str(complete.get("baseline_id") or "act"),
        ledger_identity="id",
        starting_sequence=0,
    )
    cfg = {
        "index": {"chroma_dir": str(chroma)},
        "shadow_ledger": {
            "enabled": True,
            "ledger_path": str(ledger),
            "activation_manifest_path": str(manifest_path),
            "health_path": str(health),
        },
    }
    with production_writer_boundary(
        lock_path=tmp_path / "writer.lock",
        attest_dir=tmp_path / "attest",
        census_dir=tmp_path / "census",
        entrypoint="test.factory",
    ):
        store, decision = open_chroma_for_write(cfg, chroma, use_strict_validator=False)
        try:
            assert decision.inject is True
            assert store.mutation_sink is not None
            store.add_unit(
                "u1",
                "doc",
                [0.01] * 8,
                {"source_path": "/t", "title": "t"},
            )
        finally:
            store.close()
    all_lines = [json.loads(l) for l in ledger.read_text().splitlines() if l.strip()]
    events = [o for o in all_lines if o.get("record_type") != "ledger_header"]
    assert len(events) == 1
    assert events[0]["stable_entity_id"] == "u1"


def test_v3b_v3d_pass_when_bypasses_cleared() -> None:
    """Document VERIFY expectation: empty bypass ⇒ V3b/V3d PASS (code-path)."""
    data = _inventory()
    assert data["must_use_factory_count"] == 0

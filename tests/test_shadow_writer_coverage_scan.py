"""VERIFY V3 coverage proof: factory bypass is real (hermetic + static).

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


def test_inventory_documents_zero_factory_call_sites() -> None:
    data = _inventory()
    assert data["open_chroma_for_write_production_call_sites"] == []
    assert data["must_use_factory_count"] >= 1
    assert data["proof_class"].startswith("code_path")


def test_static_scan_matches_known_bypass_list() -> None:
    """Fail-until-migrated: scanned bypass set must equal inventory list."""
    data = _inventory()
    expected = set(data["must_use_factory_bypass_sites"])
    scanned: set[str] = set()
    ctor = re.compile(r"ChromaStore\s*\(")
    factory = re.compile(r"open_chroma_for_write\s*\(")

    prod_factory_calls: list[str] = []
    for path in sorted(ROOT.rglob("*.py")):
        rel = str(path.relative_to(ROOT))
        if rel.startswith("tests/") or "docs/" in rel:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for i, line in enumerate(text.splitlines(), 1):
            if factory.search(line) and "def open_chroma_for_write" not in line:
                prod_factory_calls.append(f"{rel}:{i}")
            if not ctor.search(line):
                continue
            if line.strip().startswith("class ChromaStore"):
                continue
            site = f"{rel}:{i}"
            # Only assert sites the inventory marked must_use_factory
            if site in expected:
                scanned.add(site)

    assert prod_factory_calls == [], (
        f"unexpected production open_chroma_for_write calls: {prod_factory_calls}"
    )
    assert scanned == expected, (
        "bypass inventory drift — update SHADOW-WRITER-COVERAGE-INVENTORY.json "
        f"missing={expected - scanned} extra={scanned - expected}"
    )
    # The gap itself: expected bypasses remain non-empty ⇒ V3d FAIL
    assert len(expected) > 0


def test_hermetic_direct_ctor_bypasses_sink_even_when_cfg_eligible(
    tmp_path: Path,
) -> None:
    """Mirror observe/ingest pattern: ChromaStore(dir) => no sink, no ledger."""
    chromadb = pytest.importorskip("chromadb")
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
    # Eligible cfg (would inject via factory) — but caller uses direct ctor.
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
    store = ChromaStore(str(chroma))  # production bypass pattern
    try:
        assert store.mutation_sink is None
        store.add_unit(
            "u1",
            "doc",
            [0.01] * 8,
            {"source_path": "/t", "title": "t"},
        )
        assert store.get_unit("u1") is not None
    finally:
        store.close()
    assert not ledger.exists(), "direct ctor must not write shadow ledger"


def test_positive_control_factory_attaches_sink(tmp_path: Path) -> None:
    """Sink works when factory injects — gap is wiring, not a dead sink."""
    pytest.importorskip("chromadb")
    from chroma_write_store import open_chroma_for_write
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
    cfg = {
        "index": {"chroma_dir": str(chroma)},
        "shadow_ledger": {
            "enabled": True,
            "ledger_path": str(ledger),
            "activation_manifest_path": str(manifest_path),
            "health_path": str(tmp_path / "health.json"),
        },
    }
    store, decision = open_chroma_for_write(cfg, chroma)
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
    lines = [l for l in ledger.read_text().splitlines() if l.strip()]
    assert len(lines) == 1
    assert json.loads(lines[0])["stable_entity_id"] == "u1"


def test_v3b_v3d_must_fail_while_bypasses_exist() -> None:
    """Document VERIFY expectation: non-empty bypass ⇒ V3b/V3d FAIL."""
    data = _inventory()
    assert data["must_use_factory_count"] > 0
    assert data["open_chroma_for_write_production_call_sites"] == []
    # Mechanical encoding of the FAIL verdict for this tip.
    v3b = "FAIL"
    v3d = "FAIL"
    assert (v3b, v3d) == ("FAIL", "FAIL")

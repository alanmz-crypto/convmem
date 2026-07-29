# pylint: disable=duplicate-code
"""T2: UnitMutationSink coverage on knowledge_units mutators."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

pytest.importorskip("chromadb")

# pylint: disable=wrong-import-position
from chroma_store import ChromaStore
from chroma_write_store import open_chroma_for_write
from shadow_ledger import (
    SHADOW_DIR_MODE,
    atomic_write_json_private,
    create_shadow_ledger_header,
    finalize_manifest,
    new_incomplete_manifest,
)
from shadow_sink import classify_metadata_operation
import os
# pylint: enable=wrong-import-position


def _emb(n: int = 8) -> list[float]:
    return [0.01 * i for i in range(n)]


def _complete_cfg(tmp_path: Path, chroma: Path) -> dict:
    shadow = tmp_path / "shadow"
    shadow.mkdir(parents=True, exist_ok=True)
    os.chmod(shadow, SHADOW_DIR_MODE)
    manifest_path = shadow / "act.json"
    ledger_path = shadow / "ledger.jsonl"
    health_path = shadow / "health.json"
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
        shadow_ledger_identity="test-ledger",
    )
    atomic_write_json_private(manifest_path, complete)
    create_shadow_ledger_header(
        ledger_path,
        activation_id=str(complete.get("baseline_id") or "test-act"),
        ledger_identity="test-ledger",
        starting_sequence=0,
    )
    return {
        "index": {"chroma_dir": str(chroma)},
        "shadow_ledger": {
            "enabled": True,
            "ledger_path": str(ledger_path),
            "activation_manifest_path": str(manifest_path),
            "health_path": str(health_path),
        },
    }


def _read_events(path: Path) -> list[dict]:
    if not path.is_file():
        return []
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        obj = json.loads(line)
        if obj.get("record_type") == "ledger_header":
            continue
        out.append(obj)
    return out


def test_unit_mutating_methods_emit_or_exclude() -> None:
    """Enumerate mutators: unit methods must have shadow hooks; summaries must not."""
    import inspect
    CS = ChromaStore

    unit_mutators = {
        "add_unit",
        "update_unit",
        "update_unit_metadata",
        "supersede_units_for_source",
        "delete_units_for_source",
    }
    summary_mutators = {"add_summary", "delete_summaries_for_source"}
    src = inspect.getsource(CS)
    for name in unit_mutators:
        assert f"def {name}" in src
        # Each unit mutator prepares/emits shadow (except via helpers).
        assert "_prepare_shadow_event_id" in inspect.getsource(getattr(CS, name))
    for name in summary_mutators:
        body = inspect.getsource(getattr(CS, name))
        assert "_emit_shadow" not in body
        assert "_prepare_shadow_event_id" not in body


def test_add_update_delete_and_supersede_emit(tmp_path: Path) -> None:
    chroma = tmp_path / "chroma"
    cfg = _complete_cfg(tmp_path, chroma)
    store, decision = open_chroma_for_write(cfg, chroma)
    assert decision.inject is True
    assert store.mutation_sink is not None
    try:
        store.add_unit("u1", "hello", _emb(), {"source_path": "/a", "title": "t"})
        store.update_unit("u1", "hello2", _emb(), {"source_path": "/a", "title": "t2"})
        store.update_unit_metadata(
            "u1", {"source_path": "/a", "title": "t3", "id": "u1"}
        )
        store.add_unit("u2", "other", _emb(), {"source_path": "/a", "title": "x"})
        n = store.supersede_units_for_source("/a", superseded_by="job")
        assert n >= 1
        store.add_unit("u3", "z", _emb(), {"source_path": "/b", "title": "z"})
        deleted = store.delete_units_for_source("/b")
        assert deleted == 1
    finally:
        store.close()
    events = _read_events(Path(cfg["shadow_ledger"]["ledger_path"]))
    ops = [e["operation"] for e in events]
    assert "create" in ops
    assert "replace" in ops
    assert "metadata_update" in ops or "supersede" in ops
    assert "delete" in ops
    assert all(e["collection"] == "knowledge_units" for e in events)
    assert all(e.get("authority") == "shadow" for e in events)


def test_sink_failure_preserves_chroma_success(tmp_path: Path) -> None:
    chroma = tmp_path / "chroma"

    class BoomSink:
        def prepare_event_id(self) -> str:
            return "eid-1"

        def observe(self, **kwargs) -> None:
            raise RuntimeError("disk full")

    store = ChromaStore(str(chroma), mutation_sink=BoomSink())
    try:
        store.add_unit("u1", "ok", _emb(), {"source_path": "/x"})
        got = store.get_unit("u1")
        assert got is not None
        assert got["document"] == "ok"
    finally:
        store.close()


def test_no_sink_when_disabled_is_neutral(tmp_path: Path) -> None:
    """Claude note: mutation_sink=None path behaves like ordinary writes."""
    chroma = tmp_path / "chroma"
    cfg = {
        "index": {"chroma_dir": str(chroma)},
        "shadow_ledger": {"enabled": False},
    }
    store, decision = open_chroma_for_write(cfg, chroma)
    assert decision.inject is False
    assert store.mutation_sink is None
    try:
        store.add_unit("u1", "plain", _emb(), {"source_path": "/p"})
        assert store.get_unit("u1")["document"] == "plain"
    finally:
        store.close()
    assert not Path(tmp_path / "ledger.jsonl").exists()


def test_classify_metadata_operations() -> None:
    assert (
        classify_metadata_operation({"superseded": False}, {"superseded": True})
        == "supersede"
    )
    assert (
        classify_metadata_operation({"superseded": True}, {"superseded": False})
        == "restore"
    )
    assert classify_metadata_operation({"a": 1}, {"a": 2}) == "metadata_update"


def test_summaries_not_shadowed(tmp_path: Path) -> None:
    chroma = tmp_path / "chroma"
    cfg = _complete_cfg(tmp_path, chroma)
    store, _ = open_chroma_for_write(cfg, chroma)
    try:
        store.add_summary("s1", "sum", _emb(), {"source_path": "/s"})
    finally:
        store.close()
    assert not _read_events(Path(cfg["shadow_ledger"]["ledger_path"]))

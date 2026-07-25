"""T4: disposable replay projector, isolation, stub mode, comparison."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

chromadb = pytest.importorskip("chromadb")

from chroma_store import ChromaStore
from shadow_ledger import projection_state_hash, sha256_canonical
from shadow_replay import (
    ARCHITECTURE_CATEGORIES,
    LiveEmbedError,
    ReplayTargetError,
    assert_safe_replay_root,
    compare_touched,
    equality_flags,
    open_replay_store,
    prepare_replay_root,
    reduce_final_states,
    run_disposable_replay,
    stub_embedding,
)


def _event(
    eid: str,
    entity: str,
    doc: str,
    *,
    sequence: int = 1,
    meta: dict | None = None,
    embed_model: str = "unknown",
    dims: int = 8,
    deleted: bool = False,
) -> dict:
    meta = dict(meta or {"source_path": "/t", "title": "t"})
    return {
        "event_id": eid,
        "sequence": sequence,
        "stable_entity_id": entity,
        "post_state": {
            "document": None if deleted else doc,
            "metadata": meta,
            "deleted": deleted,
        },
        "document_hash": None if deleted else sha256_canonical(doc),
        "state_hash": projection_state_hash(
            stable_entity_id=entity,
            deleted=deleted,
            document=None if deleted else doc,
            metadata=meta,
        ),
        "embed_model": embed_model,
        "embed_dims": dims,
    }


def _write_ledger(path: Path, events: list[dict]) -> None:
    path.write_text(
        "\n".join(json.dumps(e, sort_keys=True) for e in events) + "\n",
        encoding="utf-8",
    )


def test_refuse_production_root(tmp_path: Path) -> None:
    prod = tmp_path / "prod_chroma"
    prod.mkdir()
    with pytest.raises(ReplayTargetError):
        assert_safe_replay_root(prod, production_chroma_root=prod)


def test_refuse_parent_of_production(tmp_path: Path) -> None:
    parent = tmp_path / "data"
    prod = parent / "chroma"
    parent.mkdir()
    prod.mkdir()
    with pytest.raises(ReplayTargetError, match="parent"):
        assert_safe_replay_root(parent, production_chroma_root=prod)


def test_refuse_symlink_alias(tmp_path: Path) -> None:
    prod = tmp_path / "prod"
    prod.mkdir()
    alias = tmp_path / "alias"
    alias.symlink_to(prod)
    with pytest.raises(ReplayTargetError):
        assert_safe_replay_root(alias, production_chroma_root=prod)


def test_refuse_nonempty_unmarked(tmp_path: Path) -> None:
    prod = tmp_path / "prod"
    prod.mkdir()
    target = tmp_path / "replay"
    target.mkdir()
    (target / "noise").write_text("x", encoding="utf-8")
    with pytest.raises(ReplayTargetError, match="unmarked"):
        assert_safe_replay_root(target, production_chroma_root=prod)


def test_prepare_marked_root(tmp_path: Path) -> None:
    prod = tmp_path / "prod"
    prod.mkdir()
    target = tmp_path / "replay"
    root = prepare_replay_root(target, production_chroma_root=prod)
    assert (root / ".convmem_shadow_replay_ok").is_file()


def test_open_replay_store_forces_sink_none(tmp_path: Path) -> None:
    prod = tmp_path / "prod"
    prod.mkdir()
    root = prepare_replay_root(tmp_path / "replay", production_chroma_root=prod)
    store = open_replay_store(root)
    try:
        assert store.mutation_sink is None
    finally:
        store.close()


def test_stub_embedding_deterministic() -> None:
    a = stub_embedding(8, entity_id="u1")
    b = stub_embedding(8, entity_id="u1")
    c = stub_embedding(8, entity_id="u2")
    assert a == b
    assert a != c
    assert len(a) == 8


def test_reduce_duplicates_and_compare(tmp_path: Path) -> None:
    events = [
        _event("e1", "u1", "a", sequence=1),
        _event("e1", "u1", "a", sequence=2),
    ]
    final, dups = reduce_final_states(iter(events))
    assert dups == 1
    assert "u1" in final
    chroma = {
        "u1": {"document": "a", "metadata": {"source_path": "/t", "title": "t"}},
        "u2": {"document": "only-chroma", "metadata": {}},
    }
    findings = compare_touched(
        shadow_final=final, chroma_units=chroma, touched_ids={"u1", "u2"}
    )
    cats = {f["category"] for f in findings}
    assert "missing-in-shadow" in cats
    assert "unknown embed provenance" in cats


def test_document_drift_fails_projection_equality() -> None:
    ev = _event("e1", "u1", "shadow-doc")
    final = {"u1": ev}
    chroma = {
        "u1": {
            "document": "other-doc",
            "metadata": {"source_path": "/t", "title": "t", "embed_model": "nomic"},
        }
    }
    findings = compare_touched(
        shadow_final=final, chroma_units=chroma, touched_ids={"u1"}
    )
    cats = {f["category"] for f in findings}
    assert "projection mismatch" in cats
    state_eq, proj_eq = equality_flags(findings)
    assert proj_eq is False


def test_run_replay_stub_projects_and_checkpoints(tmp_path: Path) -> None:
    prod = tmp_path / "prod"
    prod.mkdir()
    meta = {"source_path": "/t", "title": "t"}
    # Production unit matching shadow final state
    pstore = ChromaStore(str(prod), mutation_sink=None)
    try:
        pstore.add_unit("u1", "hello", stub_embedding(8, entity_id="u1"), meta)
    finally:
        pstore.close()

    ledger = tmp_path / "ledger.jsonl"
    _write_ledger(
        ledger,
        [
            _event("e1", "u1", "hello", sequence=1, meta=meta),
            _event("e1", "u1", "hello", sequence=2, meta=meta),  # duplicate
            _event("e2", "u1", "hello", sequence=3, meta=meta),  # replace same
        ],
    )
    replay = tmp_path / "replay"
    result = run_disposable_replay(
        ledger_path=ledger,
        replay_root=replay,
        production_chroma_root=prod,
        mode="stub",
        touched_ids={"u1"},
    )
    assert result.mutation_sink_forced_none is True
    assert result.mode == "stub"
    assert result.duplicates >= 1
    assert result.projected_count >= 1
    assert result.checkpoint.get("status") == "ok"
    assert result.checkpoint.get("last_event_id") == "e2"
    assert (replay / ".convmem_shadow_replay_checkpoint.json").is_file()
    # Projected unit present in disposable root
    rstore = ChromaStore(str(result.replay_root), mutation_sink=None)
    try:
        unit = rstore.get_unit("u1")
        assert unit is not None
        assert unit["document"] == "hello"
    finally:
        rstore.close()


def test_checkpoint_stops_on_corruption(tmp_path: Path) -> None:
    prod = tmp_path / "prod"
    prod.mkdir()
    ledger = tmp_path / "ledger.jsonl"
    good = _event("e1", "u1", "ok", sequence=1)
    ledger.write_text(
        json.dumps(good) + "\n" + "{not-json\n" + json.dumps(_event("e2", "u2", "x")) + "\n",
        encoding="utf-8",
    )
    result = run_disposable_replay(
        ledger_path=ledger,
        replay_root=tmp_path / "replay",
        production_chroma_root=prod,
        mode="stub",
        production_units={},
        touched_ids={"u1"},
    )
    assert result.corrupt_at_line == 2
    assert result.checkpoint.get("status") == "stopped_corrupt"
    assert result.checkpoint.get("last_event_id") == "e1"
    assert result.projected_count == 1
    cats = {f["category"] for f in result.findings}
    assert "corrupt records" in cats


def test_no_shadow_recursion_even_when_cfg_eligible(tmp_path: Path) -> None:
    """Projector must not append to a production ledger (sink forced off)."""
    prod = tmp_path / "prod"
    prod.mkdir()
    ledger = tmp_path / "ledger.jsonl"
    meta = {"source_path": "/t", "title": "t"}
    _write_ledger(ledger, [_event("e1", "u1", "doc", meta=meta)])
    before = ledger.read_text(encoding="utf-8")
    eligible_cfg = {
        "shadow_ledger": {
            "enabled": True,
            "ledger_path": str(ledger),
        }
    }
    result = run_disposable_replay(
        ledger_path=ledger,
        replay_root=tmp_path / "replay",
        production_chroma_root=prod,
        mode="stub",
        production_units={},
        touched_ids={"u1"},
        shadow_cfg_eligible=eligible_cfg,
    )
    assert result.mutation_sink_forced_none is True
    assert ledger.read_text(encoding="utf-8") == before


def test_live_mode_fails_without_fallback(tmp_path: Path) -> None:
    prod = tmp_path / "prod"
    prod.mkdir()
    ledger = tmp_path / "ledger.jsonl"
    _write_ledger(ledger, [_event("e1", "u1", "doc")])
    with pytest.raises(LiveEmbedError):
        run_disposable_replay(
            ledger_path=ledger,
            replay_root=tmp_path / "replay",
            production_chroma_root=prod,
            mode="live",
            ollama_host="",
            embed_model="",
            production_units={},
        )


def test_live_mode_does_not_silent_stub_on_unreachable(tmp_path: Path) -> None:
    prod = tmp_path / "prod"
    prod.mkdir()
    ledger = tmp_path / "ledger.jsonl"
    _write_ledger(ledger, [_event("e1", "u1", "doc")])

    def boom(*_a, **_k):
        raise ConnectionError("down")

    with patch("llm.ollama_embed", side_effect=boom):
        with pytest.raises(LiveEmbedError, match="unreachable"):
            run_disposable_replay(
                ledger_path=ledger,
                replay_root=tmp_path / "replay",
                production_chroma_root=prod,
                mode="live",
                ollama_host="http://127.0.0.1:9",
                embed_model="nomic-embed-text",
                production_units={},
            )


def test_architecture_categories_covered() -> None:
    # Ensure vocabulary set is complete for VERIFY V5k
    assert set(ARCHITECTURE_CATEGORIES) == {
        "missing-in-shadow",
        "missing-in-Chroma",
        "state mismatch",
        "projection mismatch",
        "unknown embed provenance",
        "duplicates",
        "corrupt records",
        "extras",
    }


def test_unverifiable_unknown_identity_not_projection_pass() -> None:
    meta = {"source_path": "/t", "title": "t"}
    ev = _event("e1", "u1", "same", embed_model="unknown", meta=meta)
    findings = compare_touched(
        shadow_final={"u1": ev},
        chroma_units={"u1": {"document": "same", "metadata": meta}},
        touched_ids={"u1"},
    )
    state_eq, proj_eq = equality_flags(findings)
    assert state_eq is True
    assert proj_eq is False
    assert any(f.get("detail") == "UNVERIFIABLE" for f in findings)

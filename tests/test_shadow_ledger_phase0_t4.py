"""T4: disposable replay root safety and comparison helpers."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from shadow_ledger import projection_state_hash, sha256_canonical
from shadow_replay import (
    ReplayTargetError,
    assert_safe_replay_root,
    compare_touched,
    prepare_replay_root,
    reduce_final_states,
)


def test_refuse_production_root(tmp_path: Path) -> None:
    prod = tmp_path / "prod_chroma"
    prod.mkdir()
    with pytest.raises(ReplayTargetError):
        assert_safe_replay_root(prod, production_chroma_root=prod)


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


def test_reduce_duplicates_and_compare(tmp_path: Path) -> None:
    events = [
        {
            "event_id": "e1",
            "stable_entity_id": "u1",
            "post_state": {"document": "a", "metadata": {"k": 1}, "deleted": False},
            "document_hash": sha256_canonical("a"),
            "state_hash": projection_state_hash(
                stable_entity_id="u1",
                deleted=False,
                document="a",
                metadata={"k": 1},
            ),
            "embed_model": "unknown",
        },
        {
            "event_id": "e1",
            "stable_entity_id": "u1",
            "post_state": {"document": "a", "metadata": {"k": 1}, "deleted": False},
            "document_hash": sha256_canonical("a"),
            "state_hash": projection_state_hash(
                stable_entity_id="u1",
                deleted=False,
                document="a",
                metadata={"k": 1},
            ),
            "embed_model": "unknown",
        },
    ]
    final, dups = reduce_final_states(iter(events))
    assert dups == 1
    assert "u1" in final
    chroma = {
        "u1": {"document": "a", "metadata": {"k": 1}},
        "u2": {"document": "only-chroma", "metadata": {}},
    }
    findings = compare_touched(
        shadow_final=final, chroma_units=chroma, touched_ids={"u1", "u2"}
    )
    cats = {f["category"] for f in findings}
    assert "missing-in-shadow" in cats

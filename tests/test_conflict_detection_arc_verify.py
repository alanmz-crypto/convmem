"""End-of-arc acceptance for knowledge-unit conflict detection (criteria 5–18 gaps)."""

from __future__ import annotations

import threading
import time
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from conflict_events import (
    governed_lock,
    load_events,
    new_event,
    reduce_events,
    unresolved,
)
from propose_decision import (
    approve,
    propose,
    rebase_proposal,
    reject,
    validate_governed_apply,
)


def _cfg(td: str) -> dict:
    return {"index": {"chroma_dir": str(Path(td) / "chroma")}}


def test_validate_tombstone_and_create_collision():
    common = {
        "unresolved_targets": set(),
        "unresolved_creates": {"dec_new"},
        "proposal_id": "p",
        "proposed_ledger_id": "dec_new",
    }
    assert (
        validate_governed_apply(
            target_ledger_id="dec_a",
            live_hash="x",
            base_hash="x",
            live_tombstoned=True,
            **common,
        )
        == "target_tombstoned"
    )
    assert (
        validate_governed_apply(
            target_ledger_id=None,
            live_hash=None,
            base_hash=None,
            **common,
        )
        == "pending_create_collision"
    )


def test_conflict_detected_keeps_proposal_unresolved():
    events = [
        new_event("PROPOSED", "p1", proposal={"summary": "x"}),
        new_event("CONFLICT_DETECTED", "p1", conflicts=["stale_base"]),
    ]
    states = reduce_events(events)
    assert states["p1"]["lifecycle_state"] == "PROPOSED"
    assert "stale_base" in states["p1"]["active_conflicts"]
    assert "p1" in unresolved(states)


def test_rebase_yields_new_id_and_superseded_link():
    with tempfile.TemporaryDirectory() as td:
        cfg = _cfg(td)
        old = propose(
            cfg,
            relates_to="dec_a",
            summary="Stale one",
            rationale="needs rebase",
            author="cursor",
            target_ledger_id="dec_shared",
        )
        # Force a known base so rebase can refresh it.
        with patch(
            "propose_decision.live_decision_state",
            return_value=("", "freshbasehash", False),
        ):
            draft = rebase_proposal(cfg, old["id"], author="cursor")
        assert draft["id"] != old["id"]
        assert draft["rebases_proposal_id"] == old["id"]
        assert draft["base_content_hash"] == "freshbasehash"
        states = reduce_events(load_events(cfg))
        assert states[old["id"]]["lifecycle_state"] == "SUPERSEDED"
        assert states[draft["id"]]["lifecycle_state"] == "PROPOSED"
        # SUPERSEDED event carries link
        superseded = [
            e
            for e in load_events(cfg)
            if e.get("event_type") == "SUPERSEDED" and e.get("proposal_id") == old["id"]
        ]
        assert superseded and superseded[0].get("superseded_by_proposal_id") == draft["id"]


def test_reject_sibling_then_other_proceeds():
    with tempfile.TemporaryDirectory() as td:
        cfg = _cfg(td)
        a = propose(
            cfg,
            relates_to="dec_a",
            summary="A",
            rationale="first",
            author="cursor",
            target_ledger_id="dec_shared",
            proposal_id="dec_prop_sib_a",
        )
        with pytest.raises(ValueError, match="pending_sibling"):
            propose(
                cfg,
                relates_to="dec_a",
                summary="B",
                rationale="second",
                author="cursor",
                target_ledger_id="dec_shared",
                proposal_id="dec_prop_sib_b",
            )
        reject(cfg, a["id"], signer="ryan", reason="letting sibling proceed")
        states = reduce_events(load_events(cfg))
        assert states[a["id"]]["lifecycle_state"] == "REJECTED"
        # After reject, same target can be proposed again.
        b = propose(
            cfg,
            relates_to="dec_a",
            summary="B",
            rationale="now alone",
            author="cursor",
            target_ledger_id="dec_shared",
            proposal_id="dec_prop_sib_b",
        )
        assert b["id"] == "dec_prop_sib_b"
        assert "dec_prop_sib_b" in unresolved(reduce_events(load_events(cfg)))


def test_barrier_race_second_writer_sees_stale_base():
    """Under flock, only the first apply can consume a given base hash."""
    with tempfile.TemporaryDirectory() as td:
        cfg = _cfg(td)
        results: list[str] = []

        def writer(name: str, base: str, live_after_first: dict):
            try:
                with governed_lock(cfg):
                    # Simulate validate under lock
                    live = live_after_first.get("hash", base)
                    conflict = validate_governed_apply(
                        target_ledger_id="dec_shared",
                        live_hash=live,
                        base_hash=base,
                        unresolved_targets=set(),
                        proposal_id=name,
                        proposed_ledger_id="dec_shared",
                    )
                    if conflict:
                        results.append(f"{name}:{conflict}")
                        return
                    # First writer "commits" by flipping live hash
                    live_after_first["hash"] = "newhash"
                    time.sleep(0.05)
                    results.append(f"{name}:ok")
            except Exception as exc:
                results.append(f"{name}:err:{exc}")

        shared = {"hash": "base1"}
        t1 = threading.Thread(target=writer, args=("w1", "base1", shared))
        t2 = threading.Thread(target=writer, args=("w2", "base1", shared))
        t1.start()
        time.sleep(0.01)
        t2.start()
        t1.join()
        t2.join()
        assert "w1:ok" in results
        assert "w2:stale_base" in results


def test_tombstoned_target_blocked_on_approve():
    with tempfile.TemporaryDirectory() as td:
        cfg = _cfg(td)
        rec = propose(
            cfg,
            relates_to="dec_a",
            summary="Onto tombstone",
            rationale="should fail",
            author="cursor",
            target_ledger_id="dec_dead",
        )
        with patch(
            "propose_decision.live_decision_state",
            return_value=("", "abc", True),
        ):
            with pytest.raises(ValueError, match="target_tombstoned"):
                approve(cfg, rec["id"], signer="ryan")

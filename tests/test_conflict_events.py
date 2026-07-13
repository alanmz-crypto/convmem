import json
from pathlib import Path

import pytest

from conflict_events import append_event, event_path, governed_lock, new_event, reduce_events, load_events, import_legacy_queue


@pytest.fixture
def cfg(tmp_path): return {"index": {"chroma_dir": str(tmp_path / "chroma")}}


def proposal(pid="p"):
    return new_event("PROPOSED", pid, proposal={"target_ledger_id": "target"})


def test_duplicate_event_id_is_idempotent():
    row = proposal()
    assert reduce_events([row, row])["p"]["lifecycle_state"] == "PROPOSED"


def test_illegal_lifecycle_transition_rejected():
    with pytest.raises(ValueError, match="illegal"):
        reduce_events([proposal(), new_event("APPROVED", "p")])


def test_malformed_final_line_fails_closed(cfg):
    path = event_path(cfg); path.parent.mkdir(exist_ok=True); path.write_text('{"event_id":"x"}\n{')
    with pytest.raises(ValueError, match="fail closed"): load_events(cfg)


def test_conflict_cleared_only_removes_named_conflict():
    state = reduce_events([proposal(), new_event("CONFLICT_DETECTED", "p", conflicts=["stale_base", "pending_sibling"]), new_event("CONFLICT_CLEARED", "p", conflicts=["stale_base"])])
    assert state["p"]["active_conflicts"] == {"pending_sibling"}


def test_lock_is_scoped_to_data_root(cfg):
    with governed_lock(cfg):
        assert (Path(cfg["index"]["chroma_dir"]).parent / "governed-ledger.lock").exists()


def test_legacy_import_is_idempotent_and_preserves_proposal_id(cfg):
    pending = Path(cfg["index"]["chroma_dir"]).parent / "pending_decisions.jsonl"
    pending.write_text(json.dumps({"id": "dec_prop_old", "summary": "old"}) + "\n")
    assert import_legacy_queue(cfg) == 1
    assert import_legacy_queue(cfg) == 0
    assert reduce_events(load_events(cfg))["dec_prop_old"]["proposal"]["summary"] == "old"

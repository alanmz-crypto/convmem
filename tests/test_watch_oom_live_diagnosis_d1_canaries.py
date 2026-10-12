"""D1 parent production-canary census contracts under a fake HOME (no production reads)."""

from __future__ import annotations

from pathlib import Path

import pytest

import agent_run_ledger
import conflict_events
import propose_decision
import shadow_ledger
from tests import watch_oom_live_diagnosis_support as support


@pytest.fixture(name="fake_home_share")
def _fake_home_share(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setattr(support, "production_canary_paths", lambda: [])
    return tmp_path / ".local/share/convmem"


def _only(share: Path, key: str) -> dict:
    incident = share.parent / "original-source.jsonl"
    return {k: v for k, v in support.snapshot_d1_parent_canaries(incident).items() if k == key}


def _drift(before: dict, after: dict) -> list[str]:
    return support.production_canary_drift_lines(before, after)


def test_d1_ledger_canary_paths_match_canonical_writers(fake_home_share: Path) -> None:
    share = fake_home_share
    cfg = {"index": {"chroma_dir": str(share / "chroma")}}
    incident = share.parent / "original-source.jsonl"
    census = {str(path): surface for surface, path in support.d1_mandatory_canary_paths(incident)}

    expected = {
        propose_decision.queue_path(cfg): "ledger_jsonl",
        propose_decision.approved_path(cfg): "ledger_jsonl",
        conflict_events.event_path(cfg): "ledger_jsonl",
        Path(shadow_ledger.DEFAULT_LEDGER_PATH).expanduser(): "ledger_jsonl",
        conflict_events.lock_path(cfg): "governed_lock",
        share / agent_run_ledger.AGENT_RUN_LOG_NAME: "agent_run_ledger",
        share / agent_run_ledger.AGENT_RUN_LOCK_NAME: "agent_run_lock",
        share: support.SHARE_ROOT_LISTING_SURFACE,
    }
    for path, surface in expected.items():
        assert census.get(str(path)) == surface, path
    names = {Path(key).name for key in census}
    for wrong in ("approved_decisions.jsonl", "observations.jsonl", "agent_runs"):
        assert wrong not in names
    assert str(share / "shadow" / "ledger.jsonl") not in census

    for name in (
        Path(shadow_ledger.DEFAULT_LEDGER_PATH).name,
        agent_run_ledger.AGENT_RUN_LOG_NAME,
        agent_run_ledger.AGENT_RUN_LOCK_NAME,
    ):
        key = str(share / name)
        before = _only(share, key)
        assert before[key].exists is False
        share.mkdir(parents=True, exist_ok=True)
        (share / name).write_text("{}\n", encoding="utf-8")
        assert _drift(before, _only(share, key)) == [f"created {census[key]} {key}"]


def test_share_root_listing_detects_unknown_entries(fake_home_share: Path) -> None:
    share = fake_home_share
    key = str(share)
    absent = _only(share, key)
    assert absent[key].exists is False

    (share / "chroma").mkdir(parents=True)
    (share / "processed.json").write_text("{}", encoding="utf-8")
    before = _only(share, key)
    assert _drift(absent, before) == [f"created share_root_listing {key}"]

    (share / "processed.json").write_text('{"changed": true}', encoding="utf-8")
    assert not _drift(before, _only(share, key))

    (share / "unknown-new-store.db").write_bytes(b"x")
    assert _drift(before, _only(share, key)) == [f"modified share_root_listing {key}"]

    (share / "unknown-new-store.db").unlink()
    (share / "unknown-dir").mkdir()
    assert _drift(before, _only(share, key)) == [f"modified share_root_listing {key}"]

    (share / "unknown-dir").rmdir()
    assert not _drift(before, _only(share, key))

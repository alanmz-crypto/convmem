"""Focused verification for Arc Runway Ledger (V0–V5, writer durability)."""

from __future__ import annotations

import json
import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

import agent_run_ledger as arl

SHA = "0123456789abcdef0123456789abcdef01234567"
SHA2 = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"


def _start(**kwargs):
    base = dict(
        client="kiro",
        native_session_id="sess_abc",
        repository="/repo",
        branch="main",
        source_kind="test",
        source_ref="start",
    )
    base.update(kwargs)
    return arl.build_start_event(**base)


def test_v0_envelope_round_trip_all_clients():
    for client in sorted(arl.VALID_CLIENTS):
        event = _start(client=client, native_session_id=None if client == "unknown" else f"id-{client}")
        again = arl.validate_envelope(event)
        assert again["client"] == client
        assert again["schema_version"] == 1


def test_v0_missing_native_id_accepted_explicitly():
    event = _start(native_session_id=None)
    assert event["native_session_id"] is None
    reduced = arl.reduce_events([dict(event, sequence=1)])
    view = reduced.runs[event["run_id"]]
    assert view.identity_completeness == "partial"


def test_v1_reducer_uses_append_order_not_event_time():
    start = _start(run_id="run_aaaa", event_id="arevt_start1", event_time="2026-08-20T20:00:00Z")
    enrich = arl.build_enrich_event(
        run_id="run_aaaa",
        client="kiro",
        source_kind="test",
        source_ref="enrich",
        event_id="arevt_enrich1",
        event_time="2026-08-20T19:00:00Z",  # earlier wall clock
        facts={"commits": [{"sha": SHA, "relation": "observed", "source": "git"}]},
    )
    stop = arl.build_stop_event(
        run_id="run_aaaa",
        client="kiro",
        status="completed",
        source_kind="test",
        source_ref="stop",
        event_id="arevt_stop1",
        event_time="2026-08-20T18:00:00Z",
    )
    # Append order: start, enrich, stop — even if event_times are shuffled.
    ordered = [
        dict(start, sequence=1),
        dict(enrich, sequence=2),
        dict(stop, sequence=3),
    ]
    shuffled_times = sorted(ordered, key=lambda e: e["event_time"])
    assert [e["event_type"] for e in shuffled_times] != ["run_started", "run_enriched", "run_stopped"]

    reduced = arl.reduce_events(ordered)
    view = reduced.runs["run_aaaa"]
    assert view.status == "completed"
    assert view.terminal_evidence is True
    assert view.commits[0]["sha"] == SHA


def test_v1_duplicate_exact_event_id_idempotent():
    start = dict(_start(event_id="arevt_dup1"), sequence=1)
    reduced = arl.reduce_events([start, start])
    assert len(reduced.runs) == 1
    assert reduced.problems == []


def test_v2_invalid_schema_and_illegal_transition():
    with pytest.raises(arl.AgentRunLedgerError):
        arl.validate_envelope({"schema_version": 99, "event_id": "arevt_x", "event_type": "run_started"})

    start = dict(_start(run_id="run_bbbb", event_id="arevt_s2"), sequence=1)
    stop = dict(
        arl.build_stop_event(
            run_id="run_bbbb",
            client="kiro",
            status="completed",
            source_kind="test",
            source_ref="stop",
            event_id="arevt_st2",
        ),
        sequence=2,
    )
    stop2 = dict(
        arl.build_stop_event(
            run_id="run_bbbb",
            client="kiro",
            status="aborted",
            source_kind="test",
            source_ref="stop2",
            event_id="arevt_st3",
        ),
        sequence=3,
    )
    reduced = arl.reduce_events([start, stop, stop2])
    assert any("already terminal" in p for p in reduced.problems)


def test_v2_event_id_collision_different_bytes(tmp_path: Path):
    ledger = arl.AgentRunLedger(data_dir=tmp_path)
    first = _start(event_id="arevt_same", native_session_id="sess_1")
    ledger.append_event(first)
    second = _start(event_id="arevt_same", native_session_id="sess_2")
    with pytest.raises(arl.CorruptionError):
        ledger.append_event(second)


def test_v2_truncated_tail_refused(tmp_path: Path):
    path = tmp_path / "agent_runs.jsonl"
    start = dict(_start(event_id="arevt_t1"), sequence=1)
    path.write_text(json.dumps(start, sort_keys=True), encoding="utf-8")  # no trailing newline
    with pytest.raises(arl.CorruptionError, match="truncated"):
        arl.validate_log_text(path.read_text(encoding="utf-8"))


def test_v2_interior_corruption_refused(tmp_path: Path):
    path = tmp_path / "agent_runs.jsonl"
    good = dict(_start(event_id="arevt_g1"), sequence=1)
    path.write_text(
        json.dumps(good, sort_keys=True) + "\n" + "{not-json\n" + json.dumps(good, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    with pytest.raises(arl.CorruptionError, match="malformed"):
        arl.validate_log_text(path.read_text(encoding="utf-8"))


def test_v3_concurrent_writers(tmp_path: Path):
    ledger = arl.AgentRunLedger(data_dir=tmp_path)

    def write_one(i: int) -> str:
        event = _start(
            event_id=f"arevt_c{i:04d}",
            run_id=f"run_c{i:04d}",
            native_session_id=f"sess_{i}",
        )
        result = ledger.append_event(event)
        assert result.created is True
        return result.event["event_id"]

    with ThreadPoolExecutor(max_workers=8) as pool:
        ids = list(pool.map(write_one, range(40)))
    assert len(ids) == 40
    assert len(set(ids)) == 40

    text = ledger.log_path.read_text(encoding="utf-8")
    events, next_seq = arl.validate_log_text(text)
    assert len(events) == 40
    assert next_seq == 41
    sequences = [e["sequence"] for e in events]
    assert sequences == sorted(sequences)
    assert sequences == list(range(1, 41))
    # No interleaved partial lines: each line parses as one object.
    assert all(line.strip().startswith("{") for line in text.splitlines() if line.strip())


def test_v4_idempotent_retry_same_delivery(tmp_path: Path):
    ledger = arl.AgentRunLedger(data_dir=tmp_path)
    event = _start(event_id="arevt_retry1")
    first = ledger.append_event(event)
    second = ledger.append_event(event)
    assert first.created is True
    assert second.created is False
    assert first.event["sequence"] == second.event["sequence"]
    events = arl.load_events_from_path(ledger.log_path)
    assert len(events) == 1


def test_v5_missing_and_ambiguous_stop_lookup(tmp_path: Path):
    ledger = arl.AgentRunLedger(data_dir=tmp_path)
    a = _start(run_id="run_x1", event_id="arevt_x1", native_session_id="sess_shared", repository="/repo")
    b = _start(run_id="run_x2", event_id="arevt_x2", native_session_id="sess_shared", repository="/repo")
    ledger.append_event(a)
    ledger.append_event(b)
    reduced = ledger.load()

    with pytest.raises(arl.AmbiguityError):
        arl.resolve_unique_active_run(
            reduced, client="kiro", native_session_id="sess_shared", repository="/repo"
        )

    with pytest.raises(arl.NotFoundError):
        arl.resolve_unique_active_run(
            reduced, client="kiro", native_session_id=None, repository="/repo"
        )

    # Start with no native id remains incomplete; stop without id does not invent a close.
    partial = _start(run_id="run_partial", event_id="arevt_p1", native_session_id=None)
    ledger.append_event(partial)
    reduced = ledger.load()
    view = reduced.runs["run_partial"]
    assert view.identity_completeness == "partial"
    assert view.terminal_evidence is False


def test_v7_observed_vs_explicit_remain_distinct():
    start = dict(_start(run_id="run_rel", event_id="arevt_r0"), sequence=1)
    enrich = dict(
        arl.build_enrich_event(
            run_id="run_rel",
            client="kiro",
            source_kind="test",
            source_ref="e",
            event_id="arevt_r1",
            facts={
                "commits": [
                    {"sha": SHA, "relation": "observed", "source": "git"},
                    {"sha": SHA, "relation": "explicit", "source": "caller"},
                ]
            },
        ),
        sequence=2,
    )
    view = arl.reduce_events([start, enrich]).runs["run_rel"]
    relations = {(c["sha"], c["relation"]) for c in view.commits}
    assert relations == {(SHA, "observed"), (SHA, "explicit")}


def test_v11_permissions_private(tmp_path: Path):
    ledger = arl.AgentRunLedger(data_dir=tmp_path / "data")
    ledger.append_event(_start(event_id="arevt_perm1"))
    mode_file = ledger.log_path.stat().st_mode & 0o777
    mode_dir = ledger.log_path.parent.stat().st_mode & 0o777
    assert mode_file == 0o600
    assert mode_dir == 0o700


def test_v11_symlink_log_refused(tmp_path: Path):
    real = tmp_path / "real.jsonl"
    real.write_text("", encoding="utf-8")
    link = tmp_path / "agent_runs.jsonl"
    link.symlink_to(real)
    ledger = arl.AgentRunLedger(log_path=link, lock_path=tmp_path / "agent_runs.lock")
    with pytest.raises(arl.CorruptionError, match="symlink"):
        ledger.append_event(_start(event_id="arevt_sym1"))


def test_forbidden_prompt_content_rejected():
    with pytest.raises(arl.AgentRunLedgerError):
        arl.validate_envelope(
            {
                **_start(),
                "assistant_response": "nope",
            }
        )


def test_delivery_event_id_stable():
    a = arl.delivery_event_id(
        client="kiro",
        hook_event_name="SessionStart",
        session_id="sess_1",
        cwd="/repo",
        source_ref="SessionStart",
    )
    b = arl.delivery_event_id(
        client="kiro",
        hook_event_name="SessionStart",
        session_id="sess_1",
        cwd="/repo",
        source_ref="SessionStart",
    )
    assert a == b
    assert a.startswith("arevt_")

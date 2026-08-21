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
    base = {
        "client": "kiro",
        "native_session_id": "sess_abc",
        "repository": "/repo",
        "branch": "main",
        "source_kind": "test",
        "source_ref": "start",
    }
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


def test_v8_kiro_hook_adapter_fail_open(tmp_path: Path, monkeypatch):
    import subprocess
    import sys

    monkeypatch.setenv("CONVMEM_AGENT_RUN_DATA_DIR", str(tmp_path))
    script = Path(__file__).resolve().parents[1] / "scripts" / "kiro-agent-run-hook.py"
    fixture = Path(__file__).resolve().parent / "fixtures" / "agent_run_ledger" / "stdin"

    def run_hook(mode: str, stdin_name: str) -> subprocess.CompletedProcess[str]:
        payload = (fixture / stdin_name).read_text(encoding="utf-8")
        return subprocess.run(
            [sys.executable, str(script), mode],
            input=payload,
            capture_output=True,
            text=True,
            check=False,
            env={**os.environ, "CONVMEM_AGENT_RUN_DATA_DIR": str(tmp_path)},
        )

    ok = run_hook("start", "session_start_ok.json")
    assert ok.returncode == 0
    assert ok.stdout == ""

    missing = run_hook("start", "session_start_missing_id.json")
    assert missing.returncode == 0

    # Stop with assistant_response must not persist that field.
    stop = run_hook("stop", "stop_with_assistant_response.json")
    assert stop.returncode == 0
    assert stop.stdout == ""
    text = (tmp_path / "agent_runs.jsonl").read_text(encoding="utf-8")
    assert "SENSITIVE_MODEL_OUTPUT_MUST_NOT_BE_PERSISTED" not in text
    assert "assistant_response" not in text

    # Writer failure path: point at a symlink log — still exit 0.
    bad = tmp_path / "bad"
    bad.mkdir()
    real = bad / "real.jsonl"
    real.write_text("", encoding="utf-8")
    link = bad / "agent_runs.jsonl"
    link.symlink_to(real)
    monkeypatch.setenv("CONVMEM_AGENT_RUN_DATA_DIR", str(bad))
    failed = subprocess.run(
        [sys.executable, str(script), "start"],
        input=(fixture / "session_start_ok.json").read_text(encoding="utf-8"),
        capture_output=True,
        text=True,
        check=False,
        env={**os.environ, "CONVMEM_AGENT_RUN_DATA_DIR": str(bad)},
    )
    assert failed.returncode == 0
    assert failed.stdout == ""


def test_v6_git_facts_non_git_cwd(tmp_path: Path):
    facts = arl.collect_git_facts(tmp_path)
    assert facts["repository"] is None
    assert facts["facts"]["head_revision"] is None


def test_v10_ledger_link_enrichment(tmp_path: Path):
    ledger = arl.AgentRunLedger(data_dir=tmp_path)
    start = ledger.append_event(_start(event_id="arevt_l1", run_id="run_ledger1"))
    arl.enrich_run(
        ledger,
        run_id=start.event["run_id"],
        client="kiro",
        source_kind="cli",
        source_ref="link",
        facts={
            "ledger_records": [
                {
                    "ledger_id": "obs_staging2_monitor_csp-missing",
                    "relation": "explicit",
                    "source": "caller",
                }
            ]
        },
    )
    view = ledger.load().runs["run_ledger1"]
    assert view.ledger_records[0]["ledger_id"] == "obs_staging2_monitor_csp-missing"


def test_v9_ingest_association_unique_and_ambiguous(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("CONVMEM_AGENT_RUN_DATA_DIR", str(tmp_path))
    # No run log → None
    assert (
        arl.resolve_agent_run_id_for_ingest(
            client="kiro", native_session_id="sess_a", data_dir=tmp_path
        )
        is None
    )

    ledger = arl.AgentRunLedger(data_dir=tmp_path)
    ledger.append_event(
        _start(event_id="arevt_i1", run_id="run_i1", native_session_id="sess_unique")
    )
    assert (
        arl.resolve_agent_run_id_for_ingest(
            client="kiro", native_session_id="sess_unique", data_dir=tmp_path
        )
        == "run_i1"
    )

    ledger.append_event(
        _start(event_id="arevt_i2", run_id="run_i2", native_session_id="sess_dup")
    )
    ledger.append_event(
        _start(event_id="arevt_i3", run_id="run_i3", native_session_id="sess_dup")
    )
    assert (
        arl.resolve_agent_run_id_for_ingest(
            client="kiro", native_session_id="sess_dup", data_dir=tmp_path
        )
        is None
    )


def test_v12_cross_client_envelopes_reduce():
    events = []
    for i, client in enumerate(["kiro", "codex", "cursor", "crush", "copilot"]):
        events.append(
            dict(
                _start(
                    client=client,
                    run_id=f"run_cc{i}",
                    event_id=f"arevt_cc{i}",
                    native_session_id=f"sess_{client}",
                ),
                sequence=i + 1,
            )
        )
    reduced = arl.reduce_events(events)
    assert len(reduced.runs) == 5
    assert {v.client for v in reduced.runs.values()} == {
        "kiro",
        "codex",
        "cursor",
        "crush",
        "copilot",
    }


def test_q4_two_sessions_no_native_id_same_cwd(tmp_path: Path):
    """Two sessions without native IDs must not collide (Claude Q4)."""
    ledger = arl.AgentRunLedger(data_dir=tmp_path)
    r1 = arl.start_run(
        ledger,
        client="kiro",
        native_session_id=None,
        source_kind="kiro_hook",
        source_ref="SessionStart",
        cwd="/home/lauer/Projects/convmem",
        collect_git=False,
    )
    r2 = arl.start_run(
        ledger,
        client="kiro",
        native_session_id=None,
        source_kind="kiro_hook",
        source_ref="SessionStart",
        cwd="/home/lauer/Projects/convmem",
        collect_git=False,
    )
    assert r1["run_id"] != r2["run_id"]
    assert r1["created"] is True
    assert r2["created"] is True
    reduced = ledger.load()
    assert len(reduced.runs) == 2


def test_q7_hook_failure_writes_stderr(tmp_path: Path, monkeypatch):
    """Hook failures must produce stderr output, not total silence (Claude Q7)."""
    import subprocess
    import sys

    # Make the log path a directory (causes OSError on open-for-append).
    bad_dir = tmp_path / "agent_runs.jsonl"
    bad_dir.mkdir()
    monkeypatch.setenv("CONVMEM_AGENT_RUN_DATA_DIR", str(tmp_path))
    script = Path(__file__).resolve().parents[1] / "scripts" / "kiro-agent-run-hook.py"
    fixture = (
        Path(__file__).resolve().parent / "fixtures" / "agent_run_ledger" / "stdin"
    )
    result = subprocess.run(
        [sys.executable, str(script), "start"],
        input=(fixture / "session_start_ok.json").read_text(encoding="utf-8"),
        capture_output=True,
        text=True,
        check=False,
        env={**os.environ, "CONVMEM_AGENT_RUN_DATA_DIR": str(tmp_path)},
    )
    assert result.returncode == 0  # still fail-open
    assert result.stdout == ""  # still empty stdout
    assert "convmem agent-run hook" in result.stderr


def test_q4_hook_two_missing_id_starts_same_cwd(tmp_path: Path, monkeypatch):
    """Hook path: two no-ID SessionStarts must both create runs (Claude Q4)."""
    import subprocess
    import sys

    monkeypatch.setenv("CONVMEM_AGENT_RUN_DATA_DIR", str(tmp_path))
    script = Path(__file__).resolve().parents[1] / "scripts" / "kiro-agent-run-hook.py"
    fixture = (
        Path(__file__).resolve().parent
        / "fixtures"
        / "agent_run_ledger"
        / "stdin"
        / "session_start_missing_id.json"
    )
    payload = fixture.read_text(encoding="utf-8")
    env = {**os.environ, "CONVMEM_AGENT_RUN_DATA_DIR": str(tmp_path)}
    for _ in range(2):
        result = subprocess.run(
            [sys.executable, str(script), "start"],
            input=payload,
            capture_output=True,
            text=True,
            check=False,
            env=env,
        )
        assert result.returncode == 0
        assert result.stdout == ""
    reduced = arl.AgentRunLedger(data_dir=tmp_path).load()
    assert len(reduced.runs) == 2
    assert all(v.identity_completeness == "partial" for v in reduced.runs.values())

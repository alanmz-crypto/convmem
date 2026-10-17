# pylint: disable=protected-access
"""Terminal lifecycle / export / CLI uncertainty cases (probe-local)."""
from __future__ import annotations

from pathlib import Path
from typing import Any


def _governed_file_bytes(cfg) -> dict[str, bytes | None]:
    from conflict_events import event_path
    from propose_decision import approved_path, queue_path

    paths = [
        queue_path(cfg),
        approved_path(cfg),
        event_path(cfg),
        Path(cfg["index"]["units_export"]),
    ]
    return {str(p): p.read_bytes() if p.exists() else None for p in paths}


def _event_log_bytes(cfg) -> bytes:
    from propose_decision import data_dir

    return (data_dir(cfg) / "pending_decision_events.jsonl").read_bytes()


def _complete_event_only_recovery(cfg) -> tuple[str, dict, dict[str, Any]]:
    from tests._safe_harbor_t4_common import (
        _dump_state,
        _recover,
        _setup_event_only,
        _unit_for_pid,
    )
    from tests._safe_harbor_t4_publication import _check_completion as check_done

    pid = _setup_event_only(cfg)
    before_unit = _unit_for_pid(_dump_state(cfg), pid)
    action = _recover(cfg, pid)
    if action != "approve":
        raise AssertionError(f"expected approve completion, got {action}")
    check_done(cfg, pid, before_unit)
    saved = {
        "event_bytes": _event_log_bytes(cfg),
        "files_bytes": _governed_file_bytes(cfg),
        "unit": _unit_for_pid(_dump_state(cfg), pid),
    }
    return pid, before_unit, saved


def _assert_terminal_retry_refused(cfg, pid, before, before_files) -> str:
    from tests._safe_harbor_t4_common import _dump_state, _pid_events, _spawn_probe_case
    rc, payload = _spawn_probe_case("recover.only", pid=pid)
    assert rc != 0, payload
    assert _governed_file_bytes(cfg) == before_files, "terminal refusal changed governed files"
    assert _dump_state(cfg) == before, "terminal refusal changed corpus/document/vector/tombstone"
    assert sum(e["event_type"] == "APPROVED" for e in _pid_events(cfg, pid)) == 1
    return str(payload.get("error") or payload)


def _guarded_tombstone_unit(unit_id: str) -> None:
    from typer.testing import CliRunner

    import convmem

    result = CliRunner().invoke(
        convmem.app,
        ["forget", unit_id, "-y", "--reason", "t4-terminal"],
    )
    if result.exit_code != 0:
        raise RuntimeError(f"forget failed: {result.stdout} {result.stderr}")


def _guarded_delete_unit(_cfg, unit_id: str, unit_meta: dict) -> None:
    from chroma_write_store import production_chroma_write_session
    from purge_locks import index_write_flock
    with index_write_flock(_cfg), production_chroma_write_session(entrypoint="tests.t4_terminal_delete") as session:
        removed = session.store.delete_units_for_source(
            str(unit_meta.get("source_path") or ""), candidate_ids={unit_id}
        )
    assert removed == 1, "guarded fixture deletion did not remove the unit"


def _missing_export(cfg) -> dict[str, Any]:
    from tests._safe_harbor_t4_common import (
        _assert_event_only_unit_unchanged,
        _dump_state,
        _pid_events,
        _spawn_probe_case,
        _unit_for_pid,
    )

    pid, _before_unit, saved = _complete_event_only_recovery(cfg)
    export_path = Path(cfg["index"]["units_export"])
    if not export_path.is_file():
        raise AssertionError("expected export file before removal")
    export_path.unlink()
    rc, payload = _spawn_probe_case("recover.only", pid=pid)
    if rc != 0 or payload.get("verdict") != "PASS":
        raise AssertionError(f"missing export retry failed: rc={rc} {payload}")

    if _event_log_bytes(cfg) != saved["event_bytes"]:
        raise AssertionError("event log bytes changed after export repair retry")
    after_unit = _unit_for_pid(_dump_state(cfg), pid)
    _assert_event_only_unit_unchanged(saved["unit"], after_unit)
    if sum(1 for e in _pid_events(cfg, pid) if e.get("event_type") == "APPROVED") != 1:
        raise AssertionError("duplicate or missing APPROVED after export repair")
    assert export_path.read_bytes() == saved["files_bytes"][str(export_path)], "export differs after repair"
    return {"verdict": "PASS", "mode": "missing_export", "pid": pid, "retry_rc": rc}


def _terminal_mutation(cfg, mode) -> dict[str, Any]:
    from tests._safe_harbor_t4_common import _dump_state
    pid, _before_unit, saved = _complete_event_only_recovery(cfg)
    unit_id = saved["unit"]["id"]
    if mode == "terminal_tombstone":
        _guarded_tombstone_unit(unit_id)
    else:
        _guarded_delete_unit(cfg, unit_id, saved["unit"]["metadata"])
    before, files = _dump_state(cfg), _governed_file_bytes(cfg)
    refusal = _assert_terminal_retry_refused(cfg, pid, before, files)
    return {"verdict": "PASS", "mode": mode, "pid": pid, "refusal": refusal}


def _cli_uncertain(cfg) -> dict[str, Any]:
    import conflict_events as ce
    from typer.testing import CliRunner

    import convmem
    from tests._safe_harbor_t4_common import (
        _dump_state,
        _setup_event_only,
        _spawn_probe_case,
        _unit_for_pid,
    )
    from tests._safe_harbor_t4_publication import _check_completion

    pid = _setup_event_only(cfg)
    before_unit = _unit_for_pid(_dump_state(cfg), pid)
    real_append = ce.append_event_durable
    hits: list[str] = []

    def append(config, event, **kwargs):
        result = real_append(config, event, **kwargs)
        if event.get("event_type") == "APPROVED":
            hits.append("approved_append")
            raise ce.EventPublicationError("lost ack after durable APPROVED append")
        return result

    ce.append_event_durable = append
    try:
        result = CliRunner().invoke(convmem.app, ["record", "--recover", pid])
    finally:
        ce.append_event_durable = real_append
    assert hits == ["approved_append"], "fault injection did not reach durable APPROVED"
    if result.exit_code == 0:
        raise AssertionError("CLI recover must not report success on uncertain publication")
    combined = f"{result.stdout}\n{result.stderr}"
    if "completion outcome unknown" not in combined.lower():
        raise AssertionError(f"missing uncertain completion wording: {combined}")
    if "Recovered" in combined and f"{pid}:" in combined:
        raise AssertionError("CLI printed recovered-success on uncertain completion")
    rc, payload = _spawn_probe_case("recover.only", pid=pid)
    if rc != 0 or payload.get("verdict") != "PASS":
        raise AssertionError(f"fresh retry after uncertain CLI failed: {rc} {payload}")
    _check_completion(cfg, pid, before_unit)
    return {
        "verdict": "PASS",
        "mode": "cli_uncertain",
        "pid": pid,
        "cli_rc": result.exit_code,
        "fault_hits": hits,
        "retry_rc": rc,
    }


def _active_conflict(cfg) -> dict[str, Any]:
    from conflict_events import append_event, governed_lock, load_events, new_event, reduce_events
    from tests._safe_harbor_t4_common import (
        _dump_state,
        _recover,
        _setup_event_only,
        _unit_for_pid,
    )

    pid = _setup_event_only(cfg)
    with governed_lock(cfg):
        append_event(
            cfg,
            new_event("CONFLICT_DETECTED", pid, conflicts=["stale_base"]),
        )
    before = _dump_state(cfg)
    before_unit = _unit_for_pid(before, pid)
    before_files = _governed_file_bytes(cfg)
    states = reduce_events(load_events(cfg))
    active = states[pid].get("active_conflicts") or set()
    if not active:
        raise AssertionError("reducer did not record active_conflicts after CONFLICT_DETECTED")
    error = None
    try:
        _recover(cfg, pid)
    except ValueError as exc:
        error = str(exc)
    if error is None:
        raise AssertionError(
            "recovery succeeded with active_conflicts set; runtime must refuse"
        )
    if _governed_file_bytes(cfg) != before_files:
        raise AssertionError("active-conflict refusal changed governed files")
    if _dump_state(cfg) != before:
        raise AssertionError("active-conflict refusal changed corpus/export snapshot")
    from tests._safe_harbor_t4_common import _assert_event_only_unit_unchanged

    _assert_event_only_unit_unchanged(
        before_unit,
        _unit_for_pid(_dump_state(cfg), pid),
    )
    return {
        "verdict": "PASS",
        "mode": "active_conflict",
        "pid": pid,
        "refusal": error,
        "active_conflicts": sorted(active),
    }


def run_terminal_case(cfg, mode: str) -> dict[str, Any]:
    if mode == "missing_export":
        return _missing_export(cfg)
    if mode in {"terminal_tombstone", "terminal_absent"}:
        return _terminal_mutation(cfg, mode)
    if mode == "cli_uncertain":
        return _cli_uncertain(cfg)
    if mode == "active_conflict":
        return _active_conflict(cfg)
    raise ValueError(f"unknown terminal mode {mode}")

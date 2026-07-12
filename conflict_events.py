"""Durable proposal lifecycle events and the single-host writer lock."""

from __future__ import annotations

import fcntl
import json
import os
import secrets
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

LIFECYCLES = {"PROPOSED", "APPROVAL_STARTED", "APPROVED", "REJECTED", "SUPERSEDED"}
_TRANSITIONS = {
    "PROPOSED": {"APPROVAL_STARTED", "REJECTED", "SUPERSEDED"},
    "APPROVAL_STARTED": {"APPROVED"},
    "APPROVED": set(), "REJECTED": set(), "SUPERSEDED": set(),
}


def data_root(cfg: dict) -> Path:
    return Path(cfg["index"]["chroma_dir"]).expanduser().parent


def event_path(cfg: dict) -> Path:
    return data_root(cfg) / "pending_decision_events.jsonl"


def lock_path(cfg: dict) -> Path:
    return data_root(cfg) / "governed-ledger.lock"


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def new_event(event_type: str, proposal_id: str, **extra: object) -> dict:
    return {"event_type": event_type, "event_id": secrets.token_hex(16),
            "proposal_id": proposal_id, "recorded_at": now_iso(), **extra}


@contextmanager
def governed_lock(cfg: dict):
    """Exclusive advisory lock scoped to the configured data root."""
    path = lock_path(cfg)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a+", encoding="utf-8") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def append_event(cfg: dict, event: dict) -> None:
    path = event_path(cfg)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")
        handle.flush()
        os.fsync(handle.fileno())


def load_events(cfg: dict) -> list[dict]:
    path = event_path(cfg)
    if not path.exists():
        return []
    rows: list[dict] = []
    lines = path.read_text(encoding="utf-8").splitlines()
    for number, raw in enumerate(lines, 1):
        if not raw.strip():
            continue
        try:
            row = json.loads(raw)
        except json.JSONDecodeError as exc:
            if number == len(lines):
                raise ValueError("malformed final event log record; fail closed") from exc
            raise ValueError(f"malformed event log record {number}") from exc
        if not isinstance(row, dict):
            raise ValueError(f"invalid event log record {number}")
        rows.append(row)
    return rows


def reduce_events(events: list[dict]) -> dict[str, dict]:
    """Replay events deterministically; duplicate ids are idempotent."""
    state: dict[str, dict] = {}
    seen: set[str] = set()
    for event in events:
        eid, typ, pid = event.get("event_id"), event.get("event_type"), event.get("proposal_id")
        if not isinstance(eid, str) or not isinstance(pid, str) or not isinstance(typ, str):
            raise ValueError("event missing id, type, or proposal id")
        if eid in seen:
            continue
        seen.add(eid)
        current = state.get(pid)
        if typ == "PROPOSED":
            if current is not None:
                raise ValueError(f"duplicate proposal {pid}")
            state[pid] = {"lifecycle_state": "PROPOSED", "active_conflicts": set(), "proposal": event.get("proposal") or {}}
            continue
        if current is None:
            raise ValueError(f"event before proposal: {pid}")
        if typ in ("CONFLICT_DETECTED", "CONFLICT_CLEARED"):
            conflicts = set(event.get("conflicts") or [])
            if typ == "CONFLICT_DETECTED": current["active_conflicts"].update(conflicts)
            else: current["active_conflicts"].difference_update(conflicts)
            continue
        if typ not in LIFECYCLES or typ not in _TRANSITIONS[current["lifecycle_state"]]:
            raise ValueError(f"illegal lifecycle transition {current['lifecycle_state']} -> {typ}")
        current["lifecycle_state"] = typ
    return state


def unresolved(states: dict[str, dict]) -> dict[str, dict]:
    return {pid: item for pid, item in states.items() if item["lifecycle_state"] in {"PROPOSED", "APPROVAL_STARTED"}}


def import_legacy_queue(cfg: dict) -> int:
    """Import legacy pending rows once, preserving their proposal ids."""
    from propose_decision import load_queue, queue_path
    with governed_lock(cfg):
        states = reduce_events(load_events(cfg))
        added = 0
        for row in load_queue(queue_path(cfg)):
            pid = str(row.get("id") or "").strip()
            if not pid or pid in states:
                continue
            append_event(cfg, new_event("PROPOSED", pid, proposal={
                "target_ledger_id": row.get("target_ledger_id"),
                "base_content_hash": row.get("base_content_hash"),
                "proposed_content_hash": row.get("proposed_content_hash"),
                "hash_schema_version": row.get("hash_schema_version"),
                "summary": row.get("summary"), "rationale": row.get("rationale"),
                "proposed_by": row.get("proposed_by"),
            }))
            added += 1
        return added

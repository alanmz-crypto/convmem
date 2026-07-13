"""Gate 5 — schema-deploy timestamp and hashless targeted warn→block graduation."""

from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

from conflict_events import data_root, load_events, reduce_events, unresolved
from ledger_content_hash import HASH_SCHEMA_VERSION

GRADUATION_DAYS = 14
DEPLOY_FILENAME = "hash_schema_deploy.json"
MIGRATION_REPORT_FILENAME = "hash_schema_migration_report.json"


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _parse_iso(value: str) -> datetime:
    raw = value.strip()
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    return datetime.fromisoformat(raw)


def deploy_path(cfg: dict) -> Path:
    return data_root(cfg) / DEPLOY_FILENAME


def migration_report_path(cfg: dict) -> Path:
    return data_root(cfg) / MIGRATION_REPORT_FILENAME


def is_hashless_targeted(proposal: dict | None) -> bool:
    """True when an update proposal lacks required content hashes."""
    if not isinstance(proposal, dict):
        return False
    target = proposal.get("target_ledger_id")
    if not target:
        return False
    base = str(proposal.get("base_content_hash") or "").strip()
    proposed = str(proposal.get("proposed_content_hash") or "").strip()
    return not base or not proposed


def hashless_targeted_unresolved(cfg: dict) -> list[dict]:
    """Unresolved PROPOSED/APPROVAL_STARTED rows that are hashless targeted."""
    out: list[dict] = []
    for pid, state in unresolved(reduce_events(load_events(cfg))).items():
        prop = dict(state.get("proposal") or {})
        if is_hashless_targeted(prop):
            out.append({"proposal_id": pid, "lifecycle_state": state["lifecycle_state"], "proposal": prop})
    return out


def load_schema_deploy(cfg: dict) -> dict | None:
    path = deploy_path(cfg)
    if not path.exists():
        return None
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict) or not raw.get("deployed_at"):
        raise ValueError(f"malformed schema deploy record: {path}")
    return raw


def ensure_schema_deploy_recorded(cfg: dict, *, force_report: bool = False) -> dict:
    """Record schema-deploy once; write one-shot migration report on first deploy.

    Returns the durable deploy record. Idempotent: later calls do not move the clock.
    """
    path = deploy_path(cfg)
    path.parent.mkdir(parents=True, exist_ok=True)
    existing = load_schema_deploy(cfg) if path.exists() else None
    if existing is not None:
        if force_report and not migration_report_path(cfg).exists():
            write_migration_report(cfg, existing)
        return existing

    record = {
        "deployed_at": _now().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "hash_schema_version": HASH_SCHEMA_VERSION,
        "graduation_days": GRADUATION_DAYS,
    }
    tmp = path.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(tmp, path)
    write_migration_report(cfg, record)
    return record


def write_migration_report(cfg: dict, deploy: dict) -> dict:
    """One-shot inventory of hashless targeted unresolved at schema deploy."""
    report_path = migration_report_path(cfg)
    if report_path.exists():
        return json.loads(report_path.read_text(encoding="utf-8"))
    rows = hashless_targeted_unresolved(cfg)
    report = {
        "generated_at": _now().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "deployed_at": deploy.get("deployed_at"),
        "hash_schema_version": deploy.get("hash_schema_version", HASH_SCHEMA_VERSION),
        "graduation_days": deploy.get("graduation_days", GRADUATION_DAYS),
        "hashless_targeted_count": len(rows),
        "hashless_targeted": [
            {
                "proposal_id": row["proposal_id"],
                "lifecycle_state": row["lifecycle_state"],
                "target_ledger_id": (row["proposal"] or {}).get("target_ledger_id"),
            }
            for row in rows
        ],
        "policy": (
            "warn until earlier of: zero hashless targeted unresolved, "
            f"or {GRADUATION_DAYS}d after schema-deploy; then block"
        ),
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = report_path.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8") as handle:
        handle.write(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(tmp, report_path)
    return report


def graduation_state(cfg: dict) -> dict:
    """Return Gate 5 mode and reasons. Records deploy if missing."""
    deploy = ensure_schema_deploy_recorded(cfg)
    deployed_at = _parse_iso(str(deploy["deployed_at"]))
    elapsed = _now() - deployed_at.astimezone(timezone.utc)
    days = elapsed.total_seconds() / 86400.0
    hashless = hashless_targeted_unresolved(cfg)
    count = len(hashless)
    graduated = count == 0 or days >= GRADUATION_DAYS
    if count == 0:
        reason = "zero_hashless_targeted"
    elif days >= GRADUATION_DAYS:
        reason = "schema_deploy_age"
    else:
        reason = "warn_window"
    return {
        "mode": "block" if graduated else "warn",
        "reason": reason,
        "deployed_at": deploy["deployed_at"],
        "days_elapsed": round(days, 4),
        "graduation_days": GRADUATION_DAYS,
        "hashless_targeted_count": count,
        "hashless_targeted_ids": [r["proposal_id"] for r in hashless],
        "hash_schema_version": deploy.get("hash_schema_version", HASH_SCHEMA_VERSION),
    }


def enforce_hashless_on_approve(cfg: dict, proposal_payload: dict) -> str | None:
    """Apply Gate 5 to a proposal being approved.

    Returns a warning string in warn mode for hashless targeted proposals.
    Raises ValueError in block mode.
    """
    if not is_hashless_targeted(proposal_payload):
        return None
    state = graduation_state(cfg)
    pid = proposal_payload.get("id") or proposal_payload.get("proposal_id") or "?"
    target = proposal_payload.get("target_ledger_id")
    msg = (
        f"hashless targeted proposal {pid} (target={target}): "
        f"missing base_content_hash and/or proposed_content_hash; "
        f"Gate 5 mode={state['mode']} reason={state['reason']} "
        f"({state['hashless_targeted_count']} hashless unresolved; "
        f"{state['days_elapsed']:.1f}/{state['graduation_days']}d since schema-deploy)"
    )
    if state["mode"] == "block":
        raise ValueError(
            f"Gate 5 graduated ({state['reason']}): refusing approve of {msg}"
        )
    return msg

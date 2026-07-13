"""Pending decision queue — propose, list, approve, reject (no Chroma writes)."""

from __future__ import annotations

import json
import os
import secrets
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

PROPOSAL_KIND = "decision_proposal"
VALID_SIGNERS = frozenset({"ryan", "kiro-review"})
INTERACTIVE_LOCK_NAME = "propose_interactive.lock"


class InteractiveLockError(ValueError):
    """Another propose_decision -i session holds the lock."""


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def data_dir(cfg: dict) -> Path:
    return Path(cfg["index"]["chroma_dir"]).expanduser().parent


def queue_path(cfg: dict) -> Path:
    return data_dir(cfg) / "pending_decisions.jsonl"


def approved_path(cfg: dict) -> Path:
    return data_dir(cfg) / "decisions-approved.jsonl"


def is_valid_signer(signer: str) -> bool:
    s = signer.strip()
    return s in VALID_SIGNERS


def generate_proposal_id() -> str:
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    return f"dec_prop_{ts}_{secrets.token_hex(2)}"


def load_queue(path: Path) -> list[dict]:
    if not path.is_file():
        return []
    records: list[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return records


def save_queue(path: Path, records: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(
        "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in records),
        encoding="utf-8",
    )
    tmp.replace(path)


def append_approved(path: Path, record: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
        f.flush()
        os.fsync(f.fileno())


def approved_for_proposal(cfg: dict, proposal_id: str) -> dict | None:
    """Find the durable approved intent by proposal id, never by ledger id alone."""
    path = approved_path(cfg)
    if not path.exists():
        return None
    for raw in reversed(path.read_text(encoding="utf-8").splitlines()):
        try:
            row = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if row.get("proposal_id") == proposal_id:
            return row
    return None


def recovery_action(cfg: dict, proposal_id: str, *, live_marker: str = "", live_hash: str = "", base_hash: str = "", proposed_hash: str = "") -> str:
    """Classify an APPROVAL_STARTED recovery without performing a blind retry."""
    if live_marker == proposal_id and live_hash == proposed_hash:
        return "approve"
    row = approved_for_proposal(cfg, proposal_id)
    if row and live_hash == proposed_hash:
        return "repair_marker"
    if row and (not live_hash or live_hash == base_hash):
        return "retry_chroma"
    return "review"


def validate_governed_apply(*, target_ledger_id: str | None, live_hash: str | None,
                           base_hash: str | None, unresolved_targets: set[str],
                           proposal_id: str, proposed_ledger_id: str,
                           live_tombstoned: bool = False,
                           unresolved_creates: set[str] | None = None) -> str | None:
    """Return the fail-closed conflict reason, if any, before a governed write."""
    creates = unresolved_creates if unresolved_creates is not None else set()
    if target_ledger_id:
        if target_ledger_id in unresolved_targets:
            return "pending_sibling"
        if live_tombstoned:
            return "target_tombstoned"
        if live_hash is None:
            return "target_missing"
        if base_hash is None or live_hash != base_hash:
            return "stale_base"
    else:
        if proposed_ledger_id in creates or proposed_ledger_id in unresolved_targets:
            return "pending_create_collision"
        if live_hash is not None:
            return "create_target_exists"
    return None


def event_proposal(cfg: dict, proposal_id: str) -> dict:
    """Return the PROPOSED payload for a proposal id (empty dict if missing)."""
    from conflict_events import load_events, reduce_events
    states = reduce_events(load_events(cfg))
    state = states.get(proposal_id) or {}
    proposal = state.get("proposal") or {}
    return dict(proposal) if isinstance(proposal, dict) else {}


def unresolved_target_ids(cfg: dict) -> set[str]:
    """Ledger ids claimed by unresolved proposals (targets or create ids)."""
    from conflict_events import load_events, reduce_events, unresolved
    out: set[str] = set()
    for pid, state in unresolved(reduce_events(load_events(cfg))).items():
        prop = state.get("proposal") or {}
        target = prop.get("target_ledger_id")
        if target:
            out.add(str(target))
        else:
            # create-if-absent: proposed ledger id defaults to proposal id
            out.add(str(prop.get("proposed_ledger_id") or pid))
    return out


def live_decision_state(cfg: dict, ledger_id: str) -> tuple[str, str, bool]:
    """Return (proposal_id_marker, content_hash, tombstoned) for a live decision."""
    if not ledger_id:
        return "", "", False
    try:
        from chroma_store import ChromaStore, is_superseded
        from ledger import find_unit_by_ledger_id
    except Exception:
        return "", "", False
    chroma_dir = (cfg.get("index") or {}).get("chroma_dir")
    if not chroma_dir:
        return "", "", False
    try:
        store = ChromaStore(chroma_dir)
        unit = find_unit_by_ledger_id(store, ledger_id)
    except Exception:
        return "", "", False
    if unit is None:
        return "", "", False
    meta = dict(unit.get("metadata") or {})
    marker = str(meta.get("proposal_id") or "").strip()
    tombstoned = is_superseded(meta)
    live_hash = str(meta.get("content_hash") or "").strip()
    if live_hash:
        return marker, live_hash, tombstoned
    try:
        import json as _json
        from ledger_content_hash import ledger_content_hash

        def _list(key: str) -> list:
            raw = meta.get(key) or "[]"
            if isinstance(raw, list):
                return list(raw)
            try:
                val = _json.loads(raw)
                return list(val) if isinstance(val, list) else []
            except Exception:
                return []

        record = {
            "ledger_id": meta.get("ledger_id") or ledger_id,
            "kind": meta.get("ledger_kind") or meta.get("type") or "decision",
            "status": meta.get("status") or "",
            "title": meta.get("title") or "",
            "summary": meta.get("summary") or "",
            "rationale": meta.get("rationale") or "",
            "relates_to": meta.get("relates_to") or "",
            "confidence": meta.get("confidence"),
            "domain": meta.get("domain") or "",
            "site": meta.get("site") or "",
            "notes": meta.get("notes") or "",
            "result": meta.get("result") or "",
            "alternatives_rejected": _list("alternatives_rejected_json"),
            "constraints": _list("constraints_json"),
        }
        return marker, ledger_content_hash(record), tombstoned
    except Exception:
        return marker, "", tombstoned


def live_decision_snapshot(cfg: dict, ledger_id: str) -> tuple[str, str]:
    """Return (proposal_id_marker, content_hash) for a live decision, or ("", "")."""
    marker, live_hash, _tomb = live_decision_state(cfg, ledger_id)
    return marker, live_hash


def recover_approval(cfg: dict, proposal_id: str) -> str:
    """Reconcile an APPROVAL_STARTED proposal per the recovery matrix.

    Returns the action taken: approve | retry_chroma | repair_marker.
    Raises ValueError when human review is required.
    """
    from conflict_events import append_event, governed_lock, load_events, new_event, reduce_events

    proposal_id = proposal_id.strip()
    with governed_lock(cfg):
        states = reduce_events(load_events(cfg))
        state = states.get(proposal_id)
        if state is None:
            raise ValueError(f"Proposal not found in event log: {proposal_id}")
        if state.get("lifecycle_state") == "APPROVED":
            return "approve"
        if state.get("lifecycle_state") != "APPROVAL_STARTED":
            raise ValueError(
                f"Proposal {proposal_id} is not recoverable "
                f"(lifecycle={state.get('lifecycle_state')})"
            )
        prop = dict(state.get("proposal") or {})
        target = str(prop.get("target_ledger_id") or prop.get("proposed_ledger_id") or proposal_id)
        base_hash = str(prop.get("base_content_hash") or "")
        proposed_hash = str(prop.get("proposed_content_hash") or "")
        live_marker, live_hash = live_decision_snapshot(cfg, target)
        # Prefer hashes from approved JSONL row when event payload lacked them.
        row = approved_for_proposal(cfg, proposal_id)
        if row and not proposed_hash:
            from ledger_content_hash import ledger_content_hash
            proposed_hash = ledger_content_hash(row)
        action = recovery_action(
            cfg,
            proposal_id,
            live_marker=live_marker,
            live_hash=live_hash,
            base_hash=base_hash,
            proposed_hash=proposed_hash,
        )
        if action == "review":
            raise ValueError(
                f"Proposal {proposal_id} needs human review "
                f"(marker={live_marker!r} live_hash={live_hash[:12]!r} "
                f"base={base_hash[:12]!r} proposed={proposed_hash[:12]!r})"
            )
        if action == "approve":
            append_event(cfg, new_event("APPROVED", proposal_id))
            return action
        if row is None:
            raise ValueError(
                f"Proposal {proposal_id} has APPROVAL_STARTED but no approved JSONL row"
            )
        # retry_chroma / repair_marker: re-upsert then APPROVED
        ingest_approved_ledger(cfg, {**row, "_governed_protocol": True})
        append_event(cfg, new_event("APPROVED", proposal_id))
        return action


def find_proposal(records: list[dict], proposal_id: str) -> dict | None:
    needle = proposal_id.strip()
    for rec in reversed(records):
        if rec.get("id") == needle:
            return rec
    return None


def proposal_to_ledger(
    proposal: dict,
    *,
    signer: str,
    ledger_id: str | None = None,
) -> dict:
    """Shape for decisions-approved.jsonl → normalize_ledger_record."""
    return {
        "id": (ledger_id or proposal["id"]).strip(),
        "kind": "decision",
        "status": "accepted",
        "relates_to": proposal["relates_to"],
        "summary": proposal["summary"],
        "rationale": proposal.get("rationale") or "",
        "alternatives_rejected": list(proposal.get("alternatives_rejected") or []),
        "constraints": list(proposal.get("constraints") or []),
        "author_model": signer.strip(),
        "domain": proposal.get("domain") or "coding.tooling",
        "site": proposal.get("site") or "",
        "confidence": float(proposal.get("confidence", 0.8)),
        "timestamp": _now_iso(),
        "tool": signer.strip(),
        # This link is required for recovery when ledger_id is reused by revisions.
        "proposal_id": proposal["id"],
    }


def propose(
    cfg: dict,
    *,
    relates_to: str,
    summary: str,
    rationale: str,
    author: str,
    alternatives: list[str] | None = None,
    constraints: list[str] | None = None,
    domain: str = "coding.tooling",
    site: str = "",
    confidence: float = 0.8,
    proposal_id: str | None = None,
    source: str = "cli",
    target_ledger_id: str | None = None,
) -> dict:
    relates_to = relates_to.strip()
    summary = summary.strip()
    rationale = rationale.strip()
    author = author.strip()
    if not relates_to:
        raise ValueError("--relates-to is required")
    if not summary:
        raise ValueError("--summary is required")
    if not rationale:
        raise ValueError("--rationale is required")
    if not author:
        raise ValueError("--author is required")

    pid = (proposal_id or generate_proposal_id()).strip()
    target = (target_ledger_id or "").strip() or None
    record = {
        "id": pid,
        "kind": PROPOSAL_KIND,
        "status": "PENDING",
        "relates_to": relates_to,
        "summary": summary,
        "rationale": rationale,
        "alternatives_rejected": list(alternatives or []),
        "constraints": list(constraints or []),
        "domain": domain.strip() or "coding.tooling",
        "site": site.strip(),
        "confidence": confidence,
        "proposed_by": author,
        "proposed_at": _now_iso(),
        "source": source,
        "signer": None,
        "signed_at": None,
        "rejection_reason": None,
        "target_ledger_id": target,
    }

    # The legacy queue remains a compatibility input until T5 migration; the
    # event is the protocol record used for conflict/lifecycle reduction.
    from conflict_events import append_event, governed_lock, new_event
    from hash_schema_gate import ensure_schema_deploy_recorded
    from ledger_content_hash import HASH_SCHEMA_VERSION, ledger_content_hash
    with governed_lock(cfg):
        ensure_schema_deploy_recorded(cfg)
        qpath = queue_path(cfg)
        records = load_queue(qpath)
        if find_proposal(records, pid) is not None:
            raise ValueError(f"Proposal already exists: {pid}")
        # Snapshot hashes under the same lock as the PROPOSED append.
        proposed_ledger_id = target or pid
        draft = proposal_to_ledger(record, signer=author, ledger_id=proposed_ledger_id)
        proposed_hash = ledger_content_hash(draft)
        base_hash = None
        if target:
            _marker, base_hash = live_decision_snapshot(cfg, target)
            base_hash = base_hash or None
        if target and target in unresolved_target_ids(cfg):
            raise ValueError(f"pending_sibling for target {target}")
        if (not target) and pid in unresolved_target_ids(cfg):
            raise ValueError(f"pending_create_collision for {pid}")
        record["base_content_hash"] = base_hash
        record["proposed_content_hash"] = proposed_hash
        record["hash_schema_version"] = HASH_SCHEMA_VERSION
        records.append(record)
        save_queue(qpath, records)
        append_event(cfg, new_event("PROPOSED", pid, proposal={
            "target_ledger_id": target,
            "proposed_ledger_id": proposed_ledger_id,
            "base_content_hash": base_hash,
            "proposed_content_hash": proposed_hash,
            "hash_schema_version": HASH_SCHEMA_VERSION,
            "summary": summary,
            "rationale": rationale,
            "proposed_by": author,
            "relates_to": relates_to,
            "alternatives_rejected": list(alternatives or []),
            "constraints": list(constraints or []),
            "domain": record["domain"],
            "site": record["site"],
            "confidence": confidence,
        }))
    return record


def list_proposals(
    cfg: dict,
    *,
    show_all: bool = False,
) -> list[dict]:
    records = load_queue(queue_path(cfg))
    if show_all:
        return records
    return [r for r in records if (r.get("status") or "PENDING") == "PENDING"]


def latest_pending(cfg: dict) -> dict | None:
    """Newest PENDING proposal by proposed_at (ISO), then queue order."""
    records = load_queue(queue_path(cfg))
    pending_indexed = [
        (i, r)
        for i, r in enumerate(records)
        if (r.get("status") or "PENDING") == "PENDING"
    ]
    if not pending_indexed:
        return None
    pending_indexed.sort(
        key=lambda t: (t[1].get("proposed_at") or "", t[0]),
    )
    return pending_indexed[-1][1]


def ingest_approved_file(cfg: dict, *, verbose: bool = False) -> dict:
    """Upsert decisions-approved.jsonl into Chroma."""
    from pathlib import Path

    from chroma_store import ChromaStore
    from observe import ingest_observation_file

    models = cfg.get("models")
    if not models:
        from config import load_config

        models = load_config()["models"]
    store = ChromaStore(cfg["index"]["chroma_dir"])
    units_export = cfg["index"].get("units_export")
    units_export_path = Path(units_export).expanduser() if units_export else None
    return ingest_observation_file(
        str(approved_path(cfg)),
        store=store,
        embed_model=models["embed_model"],
        ollama_host=models["ollama_host"],
        upsert=True,
        verbose=verbose,
        units_export=units_export_path,
    )


def ingest_approved_ledger(cfg: dict, ledger: dict, *, verbose: bool = False) -> dict:
    """Index one approved decision (fast path for record --approve-last)."""
    from pathlib import Path

    from chroma_store import ChromaStore
    from ledger import invalidate_ledger_index_cache
    from observe import ingest_observation

    models = cfg.get("models")
    if not models:
        from config import load_config

        models = load_config()["models"]
    store = ChromaStore(cfg["index"]["chroma_dir"])
    units_export = cfg["index"].get("units_export")
    units_export_path = Path(units_export).expanduser() if units_export else None
    protocol_ledger = {**ledger, "_governed_protocol": True}
    unit = ingest_observation(
        protocol_ledger,
        store=store,
        embed_model=models["embed_model"],
        ollama_host=models["ollama_host"],
        upsert=True,
        units_export=units_export_path,
    )
    stats = {"accepted": 0, "rejected": 0, "updated": 0, "skipped": 0}
    if unit is None:
        stats["rejected"] = 1
    elif unit.pop("_upserted", False):
        stats["updated"] = 1
    elif unit.pop("_skipped", False):
        stats["skipped"] = 1
    else:
        stats["accepted"] = 1
    invalidate_ledger_index_cache(cfg["index"]["chroma_dir"])
    return stats


def _approve_unlocked(
    cfg: dict,
    proposal_id: str,
    *,
    signer: str,
    ledger_id: str | None = None,
) -> tuple[dict, dict]:
    """Apply APPROVAL_STARTED + approved JSONL. Caller MUST hold governed_lock."""
    from conflict_events import append_event, load_events, new_event, reduce_events, unresolved
    from ledger_content_hash import ledger_content_hash

    qpath = queue_path(cfg)
    records = load_queue(qpath)
    proposal = find_proposal(records, proposal_id)
    if proposal is None:
        raise ValueError(f"Proposal not found: {proposal_id}")
    if proposal.get("status") != "PENDING":
        raise ValueError(
            f"Proposal {proposal_id} is not PENDING (status={proposal.get('status')})"
        )

    prop = event_proposal(cfg, proposal_id)
    # Gate 5: hashless targeted proposals warn then block after graduation.
    from hash_schema_gate import enforce_hashless_on_approve, ensure_schema_deploy_recorded
    ensure_schema_deploy_recorded(cfg)
    gate5_payload = {
        **prop,
        "id": proposal_id,
        "target_ledger_id": prop.get("target_ledger_id") or proposal.get("target_ledger_id"),
        "base_content_hash": prop.get("base_content_hash") or proposal.get("base_content_hash"),
        "proposed_content_hash": prop.get("proposed_content_hash") or proposal.get("proposed_content_hash"),
    }
    gate5_warning = enforce_hashless_on_approve(cfg, gate5_payload)
    if gate5_warning:
        # Surface via stderr for CLI operators; library callers can inspect later.
        import sys
        print(f"⚠ Gate 5: {gate5_warning}", file=sys.stderr)

    target = (ledger_id or prop.get("target_ledger_id") or prop.get("proposed_ledger_id")
              or proposal.get("target_ledger_id") or proposal_id)
    target = str(target).strip()
    base_hash = prop.get("base_content_hash")
    if base_hash is None:
        base_hash = proposal.get("base_content_hash")

    # Exclude this proposal from sibling set for the duration of its own approve.
    unresolved_targets: set[str] = set()
    unresolved_creates: set[str] = set()
    for pid, state in unresolved(reduce_events(load_events(cfg))).items():
        if pid == proposal_id:
            continue
        p = state.get("proposal") or {}
        if p.get("target_ledger_id"):
            unresolved_targets.add(str(p["target_ledger_id"]))
        else:
            unresolved_creates.add(str(p.get("proposed_ledger_id") or pid))

    live_marker, live_hash, live_tombstoned = live_decision_state(cfg, target)
    live_hash_or_none = live_hash or None
    # create-if-absent when proposal has no target_ledger_id
    target_for_validate = prop.get("target_ledger_id") or proposal.get("target_ledger_id")
    conflict = validate_governed_apply(
        target_ledger_id=target_for_validate,
        live_hash=live_hash_or_none,
        base_hash=base_hash,
        unresolved_targets=unresolved_targets,
        proposal_id=proposal_id,
        proposed_ledger_id=target,
        live_tombstoned=live_tombstoned,
        unresolved_creates=unresolved_creates,
    )
    if conflict:
        raise ValueError(conflict)

    append_event(cfg, new_event("APPROVAL_STARTED", proposal_id))
    now = _now_iso()
    proposal["status"] = "APPROVED"
    proposal["signer"] = signer.strip()
    proposal["signed_at"] = now
    save_queue(qpath, records)
    ledger = proposal_to_ledger(proposal, signer=signer, ledger_id=target)
    # Keep proposed hash aligned with the durable approved row.
    if not prop.get("proposed_content_hash"):
        prop_hash = ledger_content_hash(ledger)
    else:
        prop_hash = prop.get("proposed_content_hash")
    ledger["_proposed_content_hash"] = prop_hash  # not persisted long-term; stripped below
    row = {k: v for k, v in ledger.items() if not k.startswith("_")}
    append_approved(approved_path(cfg), row)
    return proposal, row


def approve(
    cfg: dict,
    proposal_id: str,
    *,
    signer: str,
    ledger_id: str | None = None,
) -> tuple[dict, dict]:
    if not is_valid_signer(signer):
        raise ValueError(
            f"Invalid --signer {signer!r}; use ryan or kiro-review (or kiro-* identity)"
        )

    from conflict_events import governed_lock
    with governed_lock(cfg):
        return _approve_unlocked(cfg, proposal_id, signer=signer, ledger_id=ledger_id)


def _mark_approved_unlocked(cfg: dict, proposal_id: str) -> None:
    """Append APPROVED. Caller MUST hold governed_lock."""
    from conflict_events import append_event, new_event
    append_event(cfg, new_event("APPROVED", proposal_id))


def mark_approved(cfg: dict, proposal_id: str) -> None:
    """Finish a successfully indexed approval while holding the same data-root lock."""
    from conflict_events import governed_lock
    with governed_lock(cfg):
        _mark_approved_unlocked(cfg, proposal_id)


def approve_and_ingest(cfg: dict, proposal_id: str, *, signer: str, ledger_id: str | None = None) -> tuple[dict, dict, dict]:
    """Run the durable approval saga under one data-root flock.

    An apply error deliberately leaves APPROVAL_STARTED for proposal-keyed
    recovery; it is not converted into a terminal failure event.
    """
    if not is_valid_signer(signer):
        raise ValueError(
            f"Invalid --signer {signer!r}; use ryan or kiro-review (or kiro-* identity)"
        )
    from conflict_events import governed_lock
    with governed_lock(cfg):
        proposal, ledger = _approve_unlocked(cfg, proposal_id, signer=signer, ledger_id=ledger_id)
        stats = ingest_approved_ledger(cfg, ledger)
        _mark_approved_unlocked(cfg, proposal_id)
        return proposal, ledger, stats



def rebase_proposal(
    cfg: dict,
    proposal_id: str,
    *,
    author: str | None = None,
) -> dict:
    """Gate 9: stale-base resolution — new proposal_id; old → SUPERSEDED.

    Never mutates the old proposal's base hash. Fresh base is snapshotted under lock.
    """
    from conflict_events import append_event, governed_lock, load_events, new_event, reduce_events
    from ledger_content_hash import HASH_SCHEMA_VERSION, ledger_content_hash

    proposal_id = proposal_id.strip()
    with governed_lock(cfg):
        qpath = queue_path(cfg)
        records = load_queue(qpath)
        old = find_proposal(records, proposal_id)
        if old is None:
            raise ValueError(f"Proposal not found: {proposal_id}")
        if old.get("status") != "PENDING":
            raise ValueError(
                f"Proposal {proposal_id} is not PENDING (status={old.get('status')})"
            )
        states = reduce_events(load_events(cfg))
        state = states.get(proposal_id)
        if state is not None and state.get("lifecycle_state") not in {"PROPOSED"}:
            raise ValueError(
                f"Proposal {proposal_id} cannot rebase "
                f"(lifecycle={state.get('lifecycle_state')})"
            )
        prop = dict((state or {}).get("proposal") or {})
        target = (
            prop.get("target_ledger_id")
            or old.get("target_ledger_id")
        )
        if not target:
            raise ValueError("rebase requires a targeted update proposal (target_ledger_id)")

        _marker, live_hash, tombstoned = live_decision_state(cfg, str(target))
        if tombstoned:
            raise ValueError("target_tombstoned: cannot rebase onto a tombstoned unit")
        if not live_hash:
            raise ValueError("target_missing: cannot rebase without a live base hash")

        new_id = generate_proposal_id()
        author_s = (author or old.get("proposed_by") or "rebase").strip()
        draft = {
            "id": new_id,
            "kind": PROPOSAL_KIND,
            "status": "PENDING",
            "relates_to": old["relates_to"],
            "summary": old["summary"],
            "rationale": old.get("rationale") or "",
            "alternatives_rejected": list(old.get("alternatives_rejected") or []),
            "constraints": list(old.get("constraints") or []),
            "domain": old.get("domain") or "coding.tooling",
            "site": old.get("site") or "",
            "confidence": float(old.get("confidence", 0.8)),
            "proposed_by": author_s,
            "proposed_at": _now_iso(),
            "source": "rebase",
            "signer": None,
            "signed_at": None,
            "rejection_reason": None,
            "target_ledger_id": target,
            "base_content_hash": live_hash,
            "rebases_proposal_id": proposal_id,
            "hash_schema_version": HASH_SCHEMA_VERSION,
        }
        proposed_hash = ledger_content_hash(
            proposal_to_ledger(draft, signer=author_s, ledger_id=str(target))
        )
        draft["proposed_content_hash"] = proposed_hash

        old["status"] = "SUPERSEDED"
        old["superseded_by_proposal_id"] = new_id
        old["signed_at"] = _now_iso()
        records.append(draft)
        save_queue(qpath, records)

        append_event(
            cfg,
            new_event(
                "SUPERSEDED",
                proposal_id,
                superseded_by_proposal_id=new_id,
            ),
        )
        append_event(
            cfg,
            new_event(
                "PROPOSED",
                new_id,
                proposal={
                    "target_ledger_id": target,
                    "proposed_ledger_id": target,
                    "base_content_hash": live_hash,
                    "proposed_content_hash": proposed_hash,
                    "hash_schema_version": HASH_SCHEMA_VERSION,
                    "summary": draft["summary"],
                    "rationale": draft["rationale"],
                    "proposed_by": author_s,
                    "relates_to": draft["relates_to"],
                    "alternatives_rejected": draft["alternatives_rejected"],
                    "constraints": draft["constraints"],
                    "domain": draft["domain"],
                    "site": draft["site"],
                    "confidence": draft["confidence"],
                    "rebases_proposal_id": proposal_id,
                },
            ),
        )
        return draft


def reject(
    cfg: dict,
    proposal_id: str,
    *,
    signer: str,
    reason: str,
) -> dict:
    if not is_valid_signer(signer):
        raise ValueError(
            f"Invalid --signer {signer!r}; use ryan or kiro-review (or kiro-* identity)"
        )
    reason = reason.strip()
    if not reason:
        raise ValueError("--reason is required for reject")

    from conflict_events import append_event, governed_lock, new_event
    with governed_lock(cfg):
        qpath = queue_path(cfg)
        records = load_queue(qpath)
        proposal = find_proposal(records, proposal_id)
        if proposal is None:
            raise ValueError(f"Proposal not found: {proposal_id}")
        if proposal.get("status") != "PENDING":
            raise ValueError(
                f"Proposal {proposal_id} is not PENDING (status={proposal.get('status')})"
            )

        proposal["status"] = "REJECTED"
        proposal["signer"] = signer.strip()
        proposal["signed_at"] = _now_iso()
        proposal["rejection_reason"] = reason
        save_queue(qpath, records)
        append_event(cfg, new_event("REJECTED", proposal_id, reason=reason))
        return proposal


def interactive_lock_path(cfg: dict) -> Path:
    return data_dir(cfg) / INTERACTIVE_LOCK_NAME


@contextmanager
def interactive_session_lock(cfg: dict):
    """Exclusive lock for propose_decision -i (one wizard session at a time)."""
    path = interactive_lock_path(cfg)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        fd = os.open(str(path), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
    except FileExistsError as e:
        holder = "unknown"
        try:
            lines = path.read_text(encoding="utf-8").strip().splitlines()
            if lines:
                holder = f"pid {lines[0]} since {lines[1] if len(lines) > 1 else '?'}"
        except OSError:
            pass
        raise InteractiveLockError(
            f"propose_decision -i already running ({holder}). "
            f"Lock: {path}. Remove only if that process is dead."
        ) from e
    try:
        os.write(fd, f"{os.getpid()}\n{_now_iso()}\n".encode())
        os.close(fd)
        yield path
    finally:
        try:
            path.unlink()
        except OSError:
            pass


def collect_interactive_fields(
    *,
    relates_to: str = "",
    summary: str = "",
    rationale: str = "",
    author: str = "",
    domain: str = "coding.tooling",
    site: str = "",
    constraints: list[str] | None = None,
    prompt,
) -> dict:
    """Prompt for proposal fields one at a time (npm init style)."""
    rt = relates_to.strip() or prompt(
        "relates_to (parent decision or observation id, e.g. dec_prop_...)"
    ).strip()
    sm = summary.strip() or prompt("summary (one sentence)").strip()
    ra = rationale.strip() or prompt("rationale (why this choice)").strip()
    au = author.strip() or prompt("author", default="cursor-session").strip()
    dom = domain.strip() or prompt("domain", default="coding.tooling").strip()
    st = site.strip() if site else prompt("site (optional, press Enter to skip)", default="").strip()
    cons = list(constraints or [])
    while True:
        extra = prompt(
            "constraint (optional, press Enter when done)", default=""
        ).strip()
        if not extra:
            break
        cons.append(extra)
    return {
        "relates_to": rt,
        "summary": sm,
        "rationale": ra,
        "author": au,
        "domain": dom or "coding.tooling",
        "site": st,
        "constraints": cons,
    }


def interactive_submit_snapshot(cfg: dict) -> dict:
    """Fresh brief + queue state immediately before interactive submit."""
    from brief import gather_brief_data

    data = gather_brief_data(cfg, with_tests=False)
    pending = list_proposals(cfg)
    stale = data.get("handoff_staleness") or {}
    return {
        "brief_at": data.get("generated_at", "?"),
        "stale_handoff": bool(stale.get("stale")),
        "stale_file": stale.get("newest_file"),
        "pending": pending,
    }


def confirm_interactive_submit(
    cfg: dict,
    fields: dict,
    *,
    confirm,
    echo,
) -> bool:
    """Show fresh state and ask before writing the proposal."""
    snap = interactive_submit_snapshot(cfg)
    echo("\n--- Submit check (fresh state) ---")
    echo(f"brief @ {snap['brief_at']}")
    if snap["stale_handoff"]:
        echo(f"STALE HANDOFF: LATEST.md older than {snap.get('stale_file')}")
    echo(f"Pending drafts in queue: {len(snap['pending'])}")
    for row in snap["pending"][:5]:
        echo(f"  - {row.get('id')}: {row.get('summary', '')[:60]}")
    echo(f"Your summary: {fields['summary']}")
    echo(f"  relates_to: {fields['relates_to']}")
    echo(f"  author: {fields['author']}")
    return bool(confirm("Save this draft?", default=True))

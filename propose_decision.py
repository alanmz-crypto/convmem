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
    }

    qpath = queue_path(cfg)
    records = load_queue(qpath)
    records.append(record)
    save_queue(qpath, records)
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
    unit = ingest_observation(
        ledger,
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

    qpath = queue_path(cfg)
    records = load_queue(qpath)
    proposal = find_proposal(records, proposal_id)
    if proposal is None:
        raise ValueError(f"Proposal not found: {proposal_id}")
    if proposal.get("status") != "PENDING":
        raise ValueError(
            f"Proposal {proposal_id} is not PENDING (status={proposal.get('status')})"
        )

    now = _now_iso()
    proposal["status"] = "APPROVED"
    proposal["signer"] = signer.strip()
    proposal["signed_at"] = now
    save_queue(qpath, records)

    ledger = proposal_to_ledger(proposal, signer=signer, ledger_id=ledger_id)
    append_approved(approved_path(cfg), ledger)
    return proposal, ledger


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

"""Pending decision queue — propose, list, approve, reject (no Chroma writes)."""

from __future__ import annotations

import json
import secrets
from datetime import datetime, timezone
from pathlib import Path

PROPOSAL_KIND = "decision_proposal"
VALID_SIGNERS = frozenset({"ryan", "kiro-review"})


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

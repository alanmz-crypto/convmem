"""Recent approved decisions from decisions-approved.jsonl."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from propose_decision import approved_path

RECENT_DECISIONS_DAYS = 7
RECENT_DECISIONS_LIMIT = 8
PROTOCOL_FALLBACK_LEDGER_ID = "dec_prop_20260623_161428_c311"


def parse_ts(ts: str) -> datetime | None:
    ts = (ts or "").strip()
    if not ts:
        return None
    for fmt in ("%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(ts, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


def load_recent_decisions(
    approved_path_arg: Path,
    *,
    days: int = 7,
    limit: int = 15,
) -> list[dict]:
    """Return recent approved decision records, newest first."""
    if not approved_path_arg.is_file():
        return []
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    rows: list[dict] = []
    for line in approved_path_arg.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        ts = parse_ts(rec.get("timestamp") or "")
        if ts and ts < cutoff:
            continue
        rows.append(rec)
    rows.sort(key=lambda r: r.get("timestamp") or "", reverse=True)
    return rows[:limit]


def decision_record_to_unit(rec: dict) -> dict:
    """Shape an approved decision JSONL row like a query_units hit."""
    from ledger import ledger_unit_document, normalize_ledger_record

    unit = normalize_ledger_record(rec, min_confidence=0.0)
    lid = (rec.get("id") or rec.get("ledger_id") or "").strip()
    if unit is None:
        summary = (rec.get("summary") or "").strip()
        rationale = (rec.get("rationale") or "").strip()
        doc = summary
        if rationale:
            doc = f"{summary}\n{rationale}" if summary else rationale
        title = summary[:120] if summary else lid
    else:
        lid = unit.get("ledger_id") or lid
        doc = ledger_unit_document(unit)
        title = unit.get("title") or (doc[:120] if doc else lid)
        rec = {**rec, **{k: unit[k] for k in ("domain", "timestamp", "relates_to") if k in unit}}
    return {
        "document": doc,
        "score": 1.0,
        "metadata": {
            "title": title,
            "type": "decision",
            "tool": (rec.get("author") or rec.get("author_model") or "ledger").strip(),
            "ledger_id": lid,
            "ledger_kind": "decision",
            "relates_to": (rec.get("relates_to") or "").strip(),
            "timestamp": rec.get("timestamp") or "",
            "domain": (rec.get("domain") or "coding.tooling").strip(),
            "source_path": "ledger:decisions-approved.jsonl",
        },
        "evidence_status": "recent_decision",
    }


def recent_decisions_for_cfg(cfg: dict, *, days: int = RECENT_DECISIONS_DAYS, limit: int = RECENT_DECISIONS_LIMIT) -> list[dict]:
    return load_recent_decisions(approved_path(cfg), days=days, limit=limit)


def is_protocol_anchor_query(query: str) -> bool:
    """True when query targets the session-close protocol fallback ledger id."""
    q = query.lower()
    if "fallback" in q and "root" in q:
        return True
    return "protocol" in q and "root" in q and "relat" in q


def load_approved_decision_by_id(cfg: dict, ledger_id: str) -> dict | None:
    """Load one approved decision row by ledger id (for anchor / keyword enrichment)."""
    needle = ledger_id.strip()
    if not needle:
        return None
    path = approved_path(cfg)
    if not path.is_file():
        return None
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        rid = (rec.get("id") or rec.get("ledger_id") or "").strip()
        if rid == needle:
            return rec
    return None


def approved_decision_hit(cfg: dict, ledger_id: str, *, score: float = 0.98) -> dict | None:
    rec = load_approved_decision_by_id(cfg, ledger_id)
    if not rec:
        return None
    hit = decision_record_to_unit(rec)
    hit["score"] = score
    hit["rank_score"] = score
    hit["ledger_lookup"] = True
    return hit

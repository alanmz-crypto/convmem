"""Inter-agent evidence ledger — observation / decision / verification contract.

Observations are the lingua franca between agents: structured facts, decisions,
and verifications ingested via `convmem add` without chat distillation.
"""

from __future__ import annotations

import json
import re
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any

from domains import normalize_domain

LEDGER_KINDS = ("observation", "decision", "verification")
_SEVERITIES = {"critical", "high", "medium", "low", "info"}
_LEDGER_INDEX_CACHE: dict[str, tuple[dict[str, dict], dict[str, list[dict]]]] = {}
_KIND_TO_TYPE = {
    "observation": "observation",
    "decision": "decision",
    "verification": "observation",
}


@dataclass
class Observation:
    """A fact something discovered (tool, agent, or human)."""

    id: str
    summary: str
    domain: str = "web_stack.security"
    author_model: str = ""
    site: str = ""
    severity: str = "medium"
    evidence: dict[str, Any] = field(default_factory=dict)
    timestamp: str = ""
    title: str = ""
    keywords: list[str] = field(default_factory=list)
    confidence: float = 0.85
    tool: str = ""
    source_path: str = ""
    kind: str = "observation"

    def to_dict(self) -> dict:
        d = asdict(self)
        d["kind"] = "observation"
        return d


@dataclass
class Decision:
    """What someone decided to do about an observation."""

    id: str
    summary: str
    relates_to: str
    author_model: str = ""
    status: str = "accepted"
    domain: str = "web_stack.security"
    site: str = ""
    timestamp: str = ""
    title: str = ""
    keywords: list[str] = field(default_factory=list)
    confidence: float = 0.8
    tool: str = ""
    source_path: str = ""
    kind: str = "decision"
    rationale: str = ""
    alternatives_rejected: list[str] = field(default_factory=list)
    constraints: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        d = asdict(self)
        d["kind"] = "decision"
        return d


@dataclass
class Verification:
    """Whether a fix was checked and the outcome."""

    id: str
    summary: str
    relates_to: str
    result: str = "pass"
    author_model: str = ""
    notes: str = ""
    domain: str = "web_stack.security"
    site: str = ""
    timestamp: str = ""
    title: str = ""
    keywords: list[str] = field(default_factory=list)
    confidence: float = 0.9
    tool: str = ""
    source_path: str = ""
    kind: str = "verification"

    def to_dict(self) -> dict:
        d = asdict(self)
        d["kind"] = "verification"
        return d


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _title_from_summary(summary: str, max_len: int = 80) -> str:
    s = summary.strip().replace("\n", " ")
    if len(s) <= max_len:
        return s
    return s[: max_len - 1].rstrip() + "…"


def _keywords_from_record(raw: dict, *, kind: str, summary: str) -> list[str]:
    if isinstance(raw.get("keywords"), list) and len(raw["keywords"]) >= 3:
        return [str(k).strip() for k in raw["keywords"] if str(k).strip()]
    parts: list[str] = []
    for key in (
        "kind",
        "domain",
        "author_model",
        "site",
        "severity",
        "relates_to",
        "status",
        "result",
        "tool",
    ):
        val = raw.get(key)
        if val:
            parts.append(str(val).strip())
    for token in re.findall(r"[a-zA-Z][a-zA-Z0-9_-]{2,}", summary):
        parts.append(token.lower())
        if len(parts) >= 8:
            break
    seen: set[str] = set()
    out: list[str] = []
    for p in parts:
        p = p.strip()
        if not p or p in seen:
            continue
        seen.add(p)
        out.append(p)
        if len(out) >= 8:
            break
    while len(out) < 3:
        out.append(f"ledger-{kind}")
        out.append("convmem")
        out.append(raw.get("author_model") or "unknown")
        break
    return out[:8]


def normalize_ledger_record(raw: dict, *, min_confidence: float = 0.0) -> dict | None:
    """Validate a ledger JSONL record and map it to a storable knowledge unit."""
    if not isinstance(raw, dict):
        return None

    kind = (raw.get("kind") or raw.get("type") or "observation").strip().lower()
    if kind not in LEDGER_KINDS:
        return None

    summary = raw.get("summary")
    if not isinstance(summary, str) or not summary.strip():
        return None
    summary = summary.strip()

    author_model = raw.get("author_model")
    if not isinstance(author_model, str) or not author_model.strip():
        return None
    author_model = author_model.strip()

    ledger_id = raw.get("id")
    if isinstance(ledger_id, str) and ledger_id.strip():
        ledger_id = ledger_id.strip()
    else:
        ledger_id = f"{kind[:3]}_{uuid.uuid4().hex[:12]}"

    title = raw.get("title")
    if not isinstance(title, str) or not title.strip():
        title = _title_from_summary(summary)
    else:
        title = title.strip()

    try:
        confidence = float(raw.get("confidence", 0.85 if kind == "observation" else 0.8))
    except (TypeError, ValueError):
        return None
    if confidence < min_confidence:
        return None

    timestamp = raw.get("timestamp") or _now_iso()
    domain = normalize_domain(raw.get("domain"))
    site = str(raw.get("site") or "").strip()
    severity = str(raw.get("severity") or "").strip().lower()
    if severity and severity not in _SEVERITIES:
        severity = severity  # keep unknown but store

    relates_to = str(raw.get("relates_to") or "").strip()
    if kind in ("decision", "verification") and not relates_to:
        return None

    evidence = raw.get("evidence")
    if evidence is not None and not isinstance(evidence, dict):
        return None
    evidence = evidence or {}

    unit_type = _KIND_TO_TYPE[kind]
    tool = str(raw.get("tool") or author_model)
    source_path = str(
        raw.get("source_path")
        or (f"site:{site}" if site else f"ledger:{author_model}")
    )

    if kind == "verification":
        notes = str(raw.get("notes") or "").strip()
        result = str(raw.get("result") or "pass").strip().lower()
        if notes and notes not in summary:
            summary = f"{summary} ({notes})" if summary else notes

    keywords = _keywords_from_record(raw, kind=kind, summary=summary)

    chroma_id = str(uuid.uuid4())

    return {
        "id": chroma_id,
        "ledger_id": ledger_id,
        "ledger_kind": kind,
        "type": unit_type,
        "title": title,
        "summary": summary,
        "keywords": keywords,
        "source_path": source_path,
        "confidence": confidence,
        "timestamp": str(timestamp),
        "tool": tool,
        "domain": domain,
        "author_model": author_model,
        "verifier_model": None,
        "site": site,
        "severity": severity,
        "relates_to": relates_to,
        "evidence_json": json.dumps(evidence, separators=(",", ":")) if evidence else "",
        "status": str(raw.get("status") or "").strip(),
        "result": str(raw.get("result") or "").strip().lower(),
        "notes": str(raw.get("notes") or "").strip(),
        "rationale": str(raw.get("rationale") or "").strip(),
        "alternatives_rejected_json": json.dumps(
            raw.get("alternatives_rejected") or [], separators=(",", ":")
        ) if raw.get("alternatives_rejected") else "",
        "constraints_json": json.dumps(
            raw.get("constraints") or [], separators=(",", ":")
        ) if raw.get("constraints") else "",
    }


def ledger_unit_document(unit: dict) -> str:
    """Embed text for a normalized ledger unit (summary + keywords + rationale)."""
    summary = (unit.get("summary") or "").strip()
    keywords = unit.get("keywords") or []
    parts: list[str] = []
    if summary:
        parts.append(summary)
    if keywords:
        parts.append(" ".join(str(k) for k in keywords if k))
    rationale = (unit.get("rationale") or "").strip()
    if rationale:
        parts.append(f"Rationale: {rationale}")
    return " ".join(p for p in parts if p).strip()


def ledger_unit_metadata(unit: dict) -> dict:
    """Chroma metadata dict for a normalized ledger unit."""
    return {
        "id": unit["id"],
        "type": unit["type"],
        "title": unit["title"],
        "source_path": unit["source_path"],
        "confidence": unit["confidence"],
        "timestamp": unit["timestamp"],
        "tool": unit["tool"],
        "start_offset": -1,
        "domain": unit["domain"],
        "author_model": unit["author_model"],
        "verifier_model": unit.get("verifier_model") or "",
        "conversation_id": "",
        "session_id": "",
        "ledger_id": unit.get("ledger_id") or "",
        "ledger_kind": unit.get("ledger_kind") or "",
        "relates_to": unit.get("relates_to") or "",
        "site": unit.get("site") or "",
        "severity": unit.get("severity") or "",
        "evidence_json": unit.get("evidence_json") or "",
        "status": unit.get("status") or "",
        "result": unit.get("result") or "",
        "notes": unit.get("notes") or "",
        "rationale": unit.get("rationale") or "",
        "alternatives_rejected_json": unit.get("alternatives_rejected_json") or "",
        "constraints_json": unit.get("constraints_json") or "",
    }


def find_unit_by_ledger_id(store, ledger_id: str) -> dict | None:
    """Look up a stored unit by external ledger id using the index.

    Delegates to build_ledger_index() so we share a single metadata scan
    with related_chain() and resolve_unit_ref() — no duplicated walk.
    """
    needle = ledger_id.strip()
    if not needle:
        return None
    by_ledger_id, _ = build_ledger_index(store)
    meta = by_ledger_id.get(needle)
    if meta is None:
        return None
    return store.get_unit(meta["id"])


def build_ledger_index(
    store,
) -> tuple[dict[str, dict], dict[str, list[dict]]]:
    """Single metadata pass: ledger_id -> meta, relates_to -> [meta, ...].

    Legacy units (no ledger_id) are skipped. Empty relates_to is ignored.
    Result is cached by store identity (chroma_dir) for the lifetime of the
    process — find_unit_by_ledger_id, related_chain, and resolve_unit_ref
    all share one scan with no duplicate walks.
    """
    # Session-level cache keyed by chroma_dir — one scan per process lifetime.
    cache_key = getattr(store, "chroma_dir", "")
    if cache_key and cache_key in _LEDGER_INDEX_CACHE:
        return _LEDGER_INDEX_CACHE[cache_key]

    by_ledger_id: dict[str, dict] = {}
    by_relates_to: dict[str, list[dict]] = {}
    for meta in store.units_metadata():
        lid = (meta.get("ledger_id") or "").strip()
        if not lid:
            continue
        by_ledger_id[lid] = meta
        parent = (meta.get("relates_to") or "").strip()
        if parent:
            by_relates_to.setdefault(parent, []).append(meta)

    result = (by_ledger_id, by_relates_to)
    if cache_key:
        _LEDGER_INDEX_CACHE[cache_key] = result
    return result


def invalidate_ledger_index_cache(chroma_dir: str | None = None) -> None:
    """Clear the session-level ledger index cache (called after ingest)."""
    global _LEDGER_INDEX_CACHE
    if chroma_dir:
        _LEDGER_INDEX_CACHE.pop(chroma_dir, None)
    else:
        _LEDGER_INDEX_CACHE = {}


def resolve_unit_ref_indexed(
    ref: str,
    by_ledger_id: dict[str, dict],
    store,
) -> dict | None:
    """Resolve chroma uuid or ledger id using a pre-built index + get_unit."""
    ref = ref.strip()
    if not ref:
        return None
    hit = store.get_unit(ref)
    if hit:
        return hit
    meta = by_ledger_id.get(ref)
    if meta:
        return store.get_unit(meta["id"])
    return None


def find_related_units(store, ledger_id: str) -> list[dict]:
    """Units whose relates_to equals ledger_id (one metadata scan)."""
    needle = ledger_id.strip()
    if not needle:
        return []
    _, by_relates_to = build_ledger_index(store)
    return _dedupe_by_ledger_id(by_relates_to.get(needle, []))


def _kind(meta: dict) -> str:
    return (meta.get("ledger_kind") or meta.get("type") or "").strip().lower()


def _dedupe_by_ledger_id(metas: list[dict]) -> list[dict]:
    """Keep one metadata row per ledger_id (last wins — e.g. re-ingest)."""
    by_lid: dict[str, dict] = {}
    for meta in metas:
        lid = (meta.get("ledger_id") or "").strip()
        if lid:
            by_lid[lid] = meta
    return list(by_lid.values())


def related_chain(store, ledger_id: str) -> dict | None:
    """Build evidence-chain view for a ledger id (single index scan).

    Returns None if ledger_id not found.
    """
    ref = ledger_id.strip()
    if not ref:
        return None

    by_ledger_id, by_relates_to = build_ledger_index(store)
    target = resolve_unit_ref_indexed(ref, by_ledger_id, store)
    if target is None:
        return None

    tmeta = target["metadata"]
    tkind = _kind(tmeta)
    t_lid = (tmeta.get("ledger_id") or ref).strip()

    if tkind == "observation" or not (tmeta.get("relates_to") or "").strip():
        anchor = t_lid
    else:
        anchor = (tmeta.get("relates_to") or "").strip()

    obs_meta = by_ledger_id.get(anchor)
    children = _dedupe_by_ledger_id(by_relates_to.get(anchor, []))

    decisions = [m for m in children if _kind(m) == "decision"]
    verifications = [m for m in children if _kind(m) == "verification"]

    siblings: list[dict] = []
    if tkind == "decision" and anchor:
        siblings = [m for m in decisions if m.get("ledger_id") != t_lid]

    return {
        "target": target,
        "target_kind": tkind,
        "anchor_id": anchor,
        "observation": obs_meta,
        "decisions": decisions,
        "verifications": verifications,
        "siblings": siblings,
    }


def resolve_unit_ref(store, ref: str) -> dict | None:
    """Resolve chroma uuid or external ledger id to a full unit."""
    ref = ref.strip()
    if not ref:
        return None
    hit = store.get_unit(ref)
    if hit:
        return hit
    by_ledger_id, _ = build_ledger_index(store)
    return resolve_unit_ref_indexed(ref, by_ledger_id, store)

"""Read-only cross-project coordination digest (Phase 1/2).

Writes markdown to ~/.local/share/convmem/digests/ — never auto-indexed.
Optional --propose queues a single synthesis draft in pending_decisions.jsonl.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

from ask import ask
from brief import gather_brief_payload
from config import load_config
from ledger_recent import (
    RECENT_DECISIONS_DAYS,
    RECENT_DECISIONS_LIMIT,
    load_recent_decisions,
)
from propose_decision import data_dir, propose, queue_path
from unresolved import list_unresolved

COORDINATION_DOMAIN_PREFIXES = ("tooling.", "coding.tooling")
CLIENT_SECURITY_DOMAIN = "web_stack.security"
EXCLUDED_PROJECT_SLUGS = frozenset({"ComfyUI", "ComfyUIimprov"})
DEFAULT_RELATES_TO = "dec_prop_20260623_161428_c311"
DIGEST_ASK_QUESTION = (
    "Cross-project themes and open coordination threads from the last week. "
    "Focus convmem protocol, surface coverage, and agent habit — not client deploy. "
    "Cite ledger ids (dec_prop_* or obs_*) for every claim."
)
_LEDGER_ID_RE = re.compile(r"\b(dec_prop_[0-9]{8}_[0-9]{6}_[0-9a-f]{4}|obs_[0-9a-f]{12})\b")


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse_ts(ts: str) -> datetime | None:
    ts = (ts or "").strip()
    if not ts:
        return None
    for fmt in ("%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(ts, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


def is_coordination_unresolved(obs: dict, *, site: str = "") -> bool:
    """Default lane: tooling/coordination obs without client site."""
    if site:
        return (obs.get("site") or "").strip() == site
    meta_site = (obs.get("site") or "").strip()
    if meta_site:
        return False
    domain = (obs.get("domain") or "").lower()
    if CLIENT_SECURITY_DOMAIN in domain:
        return False
    if domain == "general":
        title = (obs.get("title") or "").lower()
        return "test" not in title
    return any(domain.startswith(p) for p in COORDINATION_DOMAIN_PREFIXES)


def load_link_queue(path: Path, *, limit: int = 30) -> list[dict]:
    if not path.is_file():
        return []
    rows: list[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return rows[-limit:]


def load_attempts(path: Path, *, limit: int = 20) -> list[dict]:
    """Read attempts.jsonl, returning the most recent rows."""
    if not path.is_file():
        return []
    rows: list[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return rows[-limit:]


def _filter_projects(projects: list[dict]) -> list[dict]:
    out = []
    for p in projects or []:
        slug = (p.get("slug") or "").strip()
        if slug in EXCLUDED_PROJECT_SLUGS:
            continue
        out.append(p)
    return out


def digest_ask_question(recent_decisions: list[dict]) -> str:
    """Build digest ask prompt with explicit recent-decision anchors."""
    ids = [
        (r.get("id") or r.get("ledger_id") or "").strip()
        for r in recent_decisions[:RECENT_DECISIONS_LIMIT]
    ]
    ids = [i for i in ids if i.startswith(("dec_prop_", "obs_"))]
    if not ids:
        return DIGEST_ASK_QUESTION
    joined = ", ".join(f"`{i}`" for i in ids)
    return (
        f"{DIGEST_ASK_QUESTION} "
        f"Prioritize these recent approved decisions when relevant: {joined}."
    )


def recency_check(
    recent_decisions: list[dict],
    ask_result: dict | None,
    *,
    header_limit: int = RECENT_DECISIONS_LIMIT,
) -> dict:
    """Compare digest header ids with ask citations (overlap = recency PASS)."""
    header_ids = [
        (r.get("id") or r.get("ledger_id") or "").strip()
        for r in recent_decisions[:header_limit]
    ]
    header_ids = [i for i in header_ids if i]
    cited_ids = [
        (c.get("ledger_id") or "").strip()
        for c in (ask_result or {}).get("citations") or []
    ]
    cited_ids = [i for i in cited_ids if i]
    overlap = sorted(set(header_ids) & set(cited_ids))
    answer_text = (ask_result or {}).get("answer") or ""
    answer_ids = _LEDGER_ID_RE.findall(answer_text)
    answer_overlap = sorted(set(header_ids) & set(answer_ids))
    return {
        "header_ids": header_ids,
        "cited_ids": cited_ids,
        "overlap": overlap,
        "answer_overlap": answer_overlap,
        "pass": bool(overlap or answer_overlap),
    }


def render_recency_check_section(check: dict) -> list[str]:
    lines = ["## Recency check", ""]
    if not check.get("header_ids"):
        lines.append("- No recent approved decisions in header window — skip overlap.")
        lines.append("")
        return lines
    overlap = check.get("overlap") or []
    answer_overlap = check.get("answer_overlap") or []
    if overlap:
        lines.append(
            f"- **PASS** — {len(overlap)} header id(s) in ask citations: "
            + ", ".join(f"`{i}`" for i in overlap)
        )
    elif answer_overlap:
        lines.append(
            f"- **PASS** — {len(answer_overlap)} header id(s) in synthesis text: "
            + ", ".join(f"`{i}`" for i in answer_overlap)
        )
    else:
        lines.append("- **WARN** — no overlap between header recent decisions and ask output.")
        lines.append(
            "- Header: "
            + ", ".join(f"`{i}`" for i in check.get("header_ids", [])[:5])
        )
    lines.append("")
    return lines


def _pick_relates_to(brief: dict, ask_answer: str) -> str:
    cited = _LEDGER_ID_RE.findall(ask_answer or "")
    if cited:
        return cited[0]
    for dec in brief.get("recent_decisions") or []:
        lid = (dec.get("id") or dec.get("ledger_id") or "").strip()
        if lid.startswith("dec_prop_"):
            return lid
    return DEFAULT_RELATES_TO


def _first_sentence(text: str, *, max_len: int = 120) -> str:
    """Extract the first substantive sentence for use as a decision summary.

    Skips common LLM preamble patterns ('Based on...', 'According to...',
    'Here is/are...'). Falls back to truncation if no clean sentence found.
    """
    import re

    s = (text or "").replace("\n", " ").strip()
    if not s:
        return "Cross-project coordination digest (no synthesis text)"

    # Strip markdown bold/italic markers and list markers for cleaner summaries
    s = re.sub(r"\*{1,2}([^*]+)\*{1,2}", r"\1", s)
    s = re.sub(r"\s*-\s+", " ", s)
    s = re.sub(r"\s{2,}", " ", s)

    # Skip preamble sentences that don't carry substance
    _PREAMBLE_RE = re.compile(
        r"^(Based on|According to|Here (is|are)|The following|As (noted|shown|described)|"
        r"From the|Looking at|In (the|this)|Per the|All .{0,30} cited)\b",
        re.IGNORECASE,
    )

    # Split into sentences (period followed by space and capital letter)
    sentences = re.split(r"(?<=\.) (?=[A-Z])", s)

    # Find first non-preamble sentence with meaningful content (>20 chars)
    for sent in sentences:
        sent = sent.strip()
        if not sent or len(sent) < 20:
            continue
        if _PREAMBLE_RE.match(sent):
            continue
        # Found a substantive sentence
        if len(sent) > max_len:
            sent = sent[: max_len - 1].rstrip() + "…"
        return sent

    # All sentences are preamble — fall back to first one, truncated
    first = sentences[0].strip() if sentences else s
    if len(first) > max_len:
        first = first[: max_len - 1].rstrip() + "…"
    return first


def render_digest_markdown(
    *,
    brief: dict,
    coordination_unresolved: list[dict],
    recent_decisions: list[dict],
    link_queue: list[dict],
    ask_result: dict | None,
    recency: dict | None = None,
    site: str = "",
    attempts: list[dict] | None = None,
) -> str:
    stale = brief.get("handoff_staleness") or {}
    lines = [
        "# Cross-project coordination digest",
        "",
        f"Generated: {_now_iso()}",
        f"Lane: {'site=' + site if site else 'coordination (no client site)'}",
        "",
        "## Corpus snapshot",
        f"- Units: {brief.get('units')} | Unresolved (all): {brief.get('unresolved_count')}",
        f"- Coordination unresolved: **{len(coordination_unresolved)}**",
        "",
    ]
    if stale.get("stale"):
        lines.extend(
            [
                "## Handoff staleness",
                f"- STALE: `LATEST.md` older than `{stale.get('newest_file', '?')}`",
                f"- Newest inter-model age: {stale.get('newest_age_label', '?')}",
                "",
            ]
        )
    projects = _filter_projects(brief.get("projects") or [])
    if projects:
        lines.append("## Project activity (excludes ComfyUI churn)")
        for p in projects[:8]:
            lines.append(
                f"- **{p.get('slug')}** — {p.get('knowledge_units', 0)} units, "
                f"last {p.get('newest_source_age', '?')}"
            )
        lines.append("")

    if recent_decisions:
        lines.append("## Recent approved decisions (7d)")
        for rec in recent_decisions:
            lid = rec.get("id") or rec.get("ledger_id") or "?"
            summary = (rec.get("summary") or "")[:120]
            rel = rec.get("relates_to") or ""
            lines.append(f"- `{lid}` → relates `{rel}` — {summary}")
        lines.append("")

    if recency is not None:
        lines.extend(render_recency_check_section(recency))

    if link_queue:
        lines.append("## Link queue candidates (refine ledger_link)")
        for rec in link_queue[-10:]:
            lines.append(
                f"- `{rec.get('ledger_id_a')}` ↔ `{rec.get('ledger_id_b')}` "
                f"({rec.get('site') or 'no site'})"
            )
        lines.append("")

    if coordination_unresolved:
        lines.append("## Open coordination observations")
        for obs in coordination_unresolved:
            lines.append(
                f"- `{obs.get('ledger_id')}` [{obs.get('domain')}] "
                f"{obs.get('title', '')[:80]}"
            )
        lines.append("")

    if attempts:
        failed = [a for a in attempts if a.get("outcome") in ("failed", "partial")]
        if failed:
            lines.append("## Do not retry")
            for a in failed[-10:]:
                obs = a.get("obs_id") or "?"
                outcome = a.get("outcome") or "failed"
                label = "FAILED" if outcome == "failed" else "PARTIAL"
                path = a.get("path") or ""
                summary = (a.get("summary") or "")[:120]
                path_str = f" `{path}`" if path else ""
                lines.append(f"- [{label}] `{obs}`{path_str} — {summary}")
            lines.append("")

    if ask_result:
        lines.extend(
            [
                "## Synthesis (convmem ask)",
                "",
                ask_result.get("answer") or "(empty)",
                "",
            ]
        )
        conf = ask_result.get("confidence")
        if conf is not None:
            lines.append(f"_Confidence: {conf:.2f}_")
            lines.append("")
        cites = ask_result.get("citations") or []
        if cites:
            lines.append("### Citations")
            for c in cites[:8]:
                lid = c.get("ledger_id") or ""
                lid_part = f" `{lid}`" if lid else ""
                lines.append(f"- [{c.get('n')}] {c.get('when', '?')}{lid_part}")
            lines.append("")

    lines.extend(
        [
            "---",
            "_Read-only digest — not auto-indexed. Curate via `convmem record` if worth keeping._",
        ]
    )
    return "\n".join(lines)


def run_digest(
    cfg: dict | None = None,
    *,
    site: str = "",
    skip_ask: bool = False,
    propose_draft: bool = False,
    out_path: Path | None = None,
    decisions_days: int = RECENT_DECISIONS_DAYS,
) -> Path:
    cfg = cfg or load_config()
    brief = gather_brief_payload(project="")

    chroma_dir = cfg["index"]["chroma_dir"]
    from chroma_readonly import open_readonly_unit_store

    store = open_readonly_unit_store(chroma_dir)
    all_unresolved = list_unresolved(store, site=site or None)
    coordination_unresolved = [
        o for o in all_unresolved if is_coordination_unresolved(o, site=site)
    ]

    base = data_dir(cfg)
    recent = load_recent_decisions(
        base / "decisions-approved.jsonl",
        days=decisions_days,
        limit=RECENT_DECISIONS_LIMIT,
    )
    link_queue = load_link_queue(base / "link_queue.jsonl")
    attempts = load_attempts(base / "attempts.jsonl")

    ask_result = None
    recency: dict | None = None
    if not skip_ask:
        ask_result = ask(
            digest_ask_question(recent),
            domain=None,
            site=site or None,
            evidence=True,
        )
        recency = recency_check(recent, ask_result)

    body = render_digest_markdown(
        brief=brief,
        coordination_unresolved=coordination_unresolved,
        recent_decisions=recent,
        link_queue=link_queue,
        ask_result=ask_result,
        recency=recency,
        site=site,
        attempts=attempts,
    )

    if out_path is None:
        day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        out_path = base / "digests" / f"{day}.md"
    out_path = Path(out_path).expanduser()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(body, encoding="utf-8")

    if propose_draft and ask_result and (ask_result.get("answer") or "").strip():
        from runtime_guard import require_write_consent

        require_write_consent(cfg["index"]["chroma_dir"])
        answer = ask_result["answer"]
        relates = _pick_relates_to(brief, answer)
        summary = _first_sentence(answer)
        rationale = (
            f"Auto-draft from cross-project digest {out_path.name}. "
            f"Cited ids: {', '.join(_LEDGER_ID_RE.findall(answer)[:5]) or 'none'}. "
            "Ryan: review before approve — not auto-indexed."
        )
        record = propose(
            cfg,
            relates_to=relates,
            summary=summary,
            rationale=rationale,
            author="cross-project-digest",
            domain="coordination.cross_project",
            confidence=float(ask_result.get("confidence") or 0.65),
            source="cross_project_digest",
        )
        proposal_note = (
            f"\n\n## Proposal queued\n\n"
            f"- Pending id: `{record['id']}`\n"
            f"- Queue: `{queue_path(cfg)}`\n"
            f"- Approve: `convmem record --approve-last` or `convmem propose_decision --approve {record['id']}`\n"
        )
        out_path.write_text(body + proposal_note, encoding="utf-8")

    return out_path


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Cross-project coordination digest")
    parser.add_argument("--skip-ask", action="store_true", help="No LLM synthesis")
    parser.add_argument(
        "--propose",
        action="store_true",
        help="Queue one synthesis draft in pending_decisions.jsonl",
    )
    parser.add_argument("--site", default="", help="Client site filter for unresolved")
    parser.add_argument("-o", "--output", default="", help="Output path (default: digests/YYYY-MM-DD.md)")
    args = parser.parse_args()
    out = run_digest(
        skip_ask=args.skip_ask,
        propose_draft=args.propose,
        site=args.site.strip(),
        out_path=Path(args.output).expanduser() if args.output else None,
    )
    print(out)


if __name__ == "__main__":
    main()

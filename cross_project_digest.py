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


def load_recent_decisions(
    approved_path: Path,
    *,
    days: int = 7,
    limit: int = 15,
) -> list[dict]:
    if not approved_path.is_file():
        return []
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    rows: list[dict] = []
    for line in approved_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        ts = _parse_ts(rec.get("timestamp") or "")
        if ts and ts < cutoff:
            continue
        rows.append(rec)
    rows.sort(key=lambda r: r.get("timestamp") or "", reverse=True)
    return rows[:limit]


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


def _filter_projects(projects: list[dict]) -> list[dict]:
    out = []
    for p in projects or []:
        slug = (p.get("slug") or "").strip()
        if slug in EXCLUDED_PROJECT_SLUGS:
            continue
        out.append(p)
    return out


def _pick_relates_to(brief: dict, ask_answer: str) -> str:
    cited = _LEDGER_ID_RE.findall(ask_answer or "")
    if cited:
        return cited[0]
    for dec in brief.get("recent_decisions") or []:
        lid = (dec.get("id") or dec.get("ledger_id") or "").strip()
        if lid.startswith("dec_prop_"):
            return lid
    return DEFAULT_RELATES_TO


def _first_sentence(text: str, *, max_len: int = 200) -> str:
    s = (text or "").replace("\n", " ").strip()
    if not s:
        return "Cross-project coordination digest (no synthesis text)"
    for sep in (". ", ".\n"):
        if sep in s:
            s = s.split(sep, 1)[0] + "."
            break
    if len(s) > max_len:
        s = s[: max_len - 1].rstrip() + "…"
    return s


def render_digest_markdown(
    *,
    brief: dict,
    coordination_unresolved: list[dict],
    recent_decisions: list[dict],
    link_queue: list[dict],
    ask_result: dict | None,
    site: str = "",
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
    decisions_days: int = 7,
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
    )
    link_queue = load_link_queue(base / "link_queue.jsonl")

    ask_result = None
    if not skip_ask:
        ask_result = ask(
            DIGEST_ASK_QUESTION,
            domain=None,
            site=site or None,
            evidence=False,
        )

    body = render_digest_markdown(
        brief=brief,
        coordination_unresolved=coordination_unresolved,
        recent_decisions=recent,
        link_queue=link_queue,
        ask_result=ask_result,
        site=site,
    )

    if out_path is None:
        day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        out_path = base / "digests" / f"{day}.md"
    out_path = Path(out_path).expanduser()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(body, encoding="utf-8")

    if propose_draft and ask_result and (ask_result.get("answer") or "").strip():
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

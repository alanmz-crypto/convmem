"""`convmem unresolved` — list open observations that need attention.

No LLM. Just the ledger graph: every observation without a pass
verification, plus any with a failed check. Filterable by --site
and --domain.
"""

from __future__ import annotations

import typer
from datetime import datetime

from evidence import evidence_boost, _kind
from ledger import build_ledger_index, _dedupe_by_ledger_id

OPEN_STATUSES = {"unresolved", "failed_check", "failed_verification"}


def list_unresolved(
    store,
    *,
    site: str | None = None,
    domain: str | None = None,
) -> list[dict]:
    """Return open observations sorted by severity descending, then by ledger_id.

    Each entry has: ledger_id, severity, site, domain, title, status,
    last_touched (ISO), summary, metadata.
    """
    by_ledger_id, by_relates_to = build_ledger_index(store)

    collected: list[dict] = []

    for lid, meta in by_ledger_id.items():
        kind = _kind(meta)
        if kind != "observation" and (meta.get("type") or "").strip().lower() != "observation":
            continue

        boost, status = evidence_boost(meta, by_relates_to=by_relates_to)
        if status not in OPEN_STATUSES:
            continue

        meta_site = (meta.get("site") or "").strip()
        meta_domain = (meta.get("domain") or "").strip()

        if site and meta_site != site:
            continue
        if domain and meta_domain != domain:
            continue

        # Compute last_touched: most recent timestamp among children
        children = _dedupe_by_ledger_id(
            by_relates_to.get(lid, []) + by_relates_to.get(meta.get("id", ""), [])
        )
        timestamps = [meta.get("timestamp", "")]
        for child in children:
            ts = child.get("timestamp", "")
            if ts:
                timestamps.append(ts)
        timestamps = [t for t in timestamps if t]
        last_touched = max(timestamps) if timestamps else (meta.get("timestamp") or "")

        collected.append({
            "ledger_id": lid,
            "severity": (meta.get("severity") or "medium").strip(),
            "site": meta_site,
            "domain": meta_domain,
            "title": (meta.get("title") or lid).strip(),
            "status": status,
            "last_touched": last_touched,
            "summary": (meta.get("summary") or "").strip(),
            "metadata": meta,
        })

    # Sort: severity descending (critical > high > medium > low > info),
    # then by ledger_id for stable ordering.
    _severity_rank = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}

    collected.sort(
        key=lambda r: (
            _severity_rank.get(r["severity"], 5),
            r["ledger_id"],
        )
    )

    return collected


def unresolved_items(results: list[dict]) -> list[dict]:
    """Public JSON-serializable rows (no metadata blob)."""
    return [
        {
            "ledger_id": r["ledger_id"],
            "severity": r["severity"],
            "site": r["site"],
            "domain": r["domain"],
            "title": r["title"],
            "status": r["status"],
            "last_touched": r["last_touched"],
            "summary": r["summary"],
        }
        for r in results
    ]


def unresolved_payload(
    store,
    *,
    site: str | None = None,
    domain: str | None = None,
) -> dict:
    results = list_unresolved(store, site=site, domain=domain)
    return {"count": len(results), "items": unresolved_items(results)}


def render_unresolved_json(payload: dict) -> str:
    import json

    return json.dumps(payload, indent=2)


def render_unresolved(results: list[dict]) -> None:
    """Print a table of open observations."""
    if not results:
        typer.echo("No unresolved observations.")
        return

    # Column widths
    cols = {
        "ledger_id": max(max(len(r["ledger_id"]) for r in results), len("LEDGER ID")),
        "severity": max(max(len(r["severity"]) for r in results), len("SEVERITY")),
        "site": max(max(len(r["site"]) for r in results), len("SITE")),
        "domain": max(max(len(r["domain"]) for r in results), len("DOMAIN")),
        "status": max(max(len(r["status"]) for r in results), len("STATUS")),
        "last_touched": len("LAST TOUCHED"),
        "title": max(max(len(r["title"]) for r in results), len("TITLE")),
    }
    # Cap title width at 60
    cols["title"] = min(cols["title"], 60)

    header = (
        f"{'LEDGER ID':<{cols['ledger_id']}}  "
        f"{'SEVERITY':<{cols['severity']}}  "
        f"{'SITE':<{cols['site']}}  "
        f"{'DOMAIN':<{cols['domain']}}  "
        f"{'STATUS':<{cols['status']}}  "
        f"{'LAST TOUCHED':<{cols['last_touched']}}  "
        f"{'TITLE':<{cols['title']}}"
    )

    typer.echo(f"{len(results)} unresolved observation(s):\n")
    typer.echo(header)
    typer.echo("─" * len(header))

    for r in results:
        title = r["title"]
        if len(title) > cols["title"]:
            title = title[:cols["title"] - 1] + "…"
        # Truncate or format last_touched to a readable date
        lt = r["last_touched"]
        if lt and "T" in lt:
            try:
                dt = datetime.fromisoformat(lt.replace("Z", "+00:00"))
                lt = dt.strftime("%Y-%m-%d")
            except (ValueError, TypeError):
                pass
        line = (
            f"{r['ledger_id']:<{cols['ledger_id']}}  "
            f"{r['severity']:<{cols['severity']}}  "
            f"{r['site']:<{cols['site']}}  "
            f"{r['domain']:<{cols['domain']}}  "
            f"{r['status']:<{cols['status']}}  "
            f"{lt:<{cols['last_touched']}}  "
            f"{title:<{cols['title']}}"
        )
        typer.echo(line)

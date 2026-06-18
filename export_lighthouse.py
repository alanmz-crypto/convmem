#!/usr/bin/env python3
"""Export Lighthouse LHR JSON to convmem observations.jsonl.

Only exports audits that did not pass (score < 0.9). Stable ledger ids:
  obs_<site>_lh_<audit-id-slug>

Usage:
  python export_lighthouse.py report.json --site staging2.willowyhollow.com -o observations.jsonl
  convmem add --file observations.jsonl --upsert
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from ledger_ids import audit_key, observation_id


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _domain_for_audit(audit_id: str, title: str) -> str:
    blob = f"{audit_id} {title}".lower()
    if any(
        x in blob
        for x in (
            "csp",
            "xss",
            "security",
            "cookie",
            "https",
            "vulnerable",
            "deprecat",
            "header",
        )
    ):
        return "web_stack.security"
    return "web_stack.performance"


def _severity(score: float | None) -> str:
    if score is None:
        return "medium"
    if score < 0.5:
        return "high"
    if score < 0.9:
        return "medium"
    return "low"


def should_export_audit(audit: dict) -> bool:
    """Export failed / warning audits only (skip score == 1 and passing scores)."""
    score = audit.get("score")
    if score is None:
        return False
    try:
        score = float(score)
    except (TypeError, ValueError):
        return False
    return score < 0.9


def _normalize_site(site: str) -> str:
    return site.strip().lower().replace("https://", "").replace("http://", "").split("/")[0]


def parse_lighthouse_report(
    data: dict,
    *,
    site: str,
    score_threshold: float = 0.9,
) -> list[dict]:
    """Parse Lighthouse LHR JSON into observation records."""
    audits = data.get("audits") or {}
    if not isinstance(audits, dict):
        return []

    final_url = data.get("finalUrl") or data.get("requestedUrl") or f"https://{site}"
    out: list[dict] = []

    for audit_id, audit in sorted(audits.items()):
        if not isinstance(audit, dict):
            continue
        score = audit.get("score")
        if score is None:
            continue
        try:
            score = float(score)
        except (TypeError, ValueError):
            continue
        if score >= score_threshold:
            continue

        title = (audit.get("title") or audit_id).strip()
        key = audit_key(audit_id)
        out.append(
            {
                "id": observation_id(site, "lh", key),
                "kind": "observation",
                "domain": _domain_for_audit(audit_id, title),
                "author_model": "lighthouse-ci",
                "site": _normalize_site(site),
                "severity": _severity(score),
                "summary": f"Lighthouse: {title}",
                "tool": "lighthouse",
                "source_path": final_url,
                "timestamp": _now(),
                "evidence": {
                    "audit_id": audit_id,
                    "score": score,
                    "display_value": audit.get("displayValue"),
                    "url": final_url,
                },
            }
        )
    return out


def export_lighthouse_file(
    path: Path,
    *,
    site: str,
    score_threshold: float = 0.9,
) -> list[dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not site:
        final = data.get("finalUrl") or data.get("requestedUrl") or ""
        site = final.replace("https://", "").replace("http://", "").split("/")[0]
    return parse_lighthouse_report(data, site=site, score_threshold=score_threshold)


def main() -> None:
    ap = argparse.ArgumentParser(description="Export Lighthouse JSON to observations.jsonl")
    ap.add_argument("report", type=Path, help="Lighthouse LHR JSON (e.g. lhci report.json)")
    ap.add_argument("--site", help="Site hostname (inferred from finalUrl if omitted)")
    ap.add_argument("-o", "--output", type=Path, default=Path("observations.jsonl"))
    ap.add_argument(
        "--score-threshold",
        type=float,
        default=0.9,
        help="Export audits with score below this (default: 0.9)",
    )
    ap.add_argument("--print", action="store_true", help="Print JSONL to stdout")
    args = ap.parse_args()

    if not args.report.is_file():
        print(f"Report not found: {args.report}", file=sys.stderr)
        raise SystemExit(1)

    records = export_lighthouse_file(
        args.report,
        site=args.site or "",
        score_threshold=args.score_threshold,
    )
    if not records:
        print("No failing Lighthouse audits to export", file=sys.stderr)
        raise SystemExit(0)

    lines = [json.dumps(r, ensure_ascii=False) for r in records]
    if args.print:
        print("\n".join(lines))
    else:
        args.output.write_text("\n".join(lines) + "\n", encoding="utf-8")
        print(f"Wrote {len(records)} observation(s) → {args.output}")


if __name__ == "__main__":
    main()

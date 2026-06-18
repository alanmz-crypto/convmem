#!/usr/bin/env python3
"""Export wp-sec-agent / Lighthouse scan output to convmem observations.jsonl.

Usage:
  python export_report_to_observations.py --site staging2.willowyhollow.com \\
      --results-dir ~/Projects/wp-sec-agent/clients/staging2.willowyhollow.com/results \\
      -o observations.jsonl

  convmem add --file observations.jsonl
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path

_FINDING = re.compile(
    r"^- \[(?P<severity>[^\]]+)\] \[(?P<tool>[^\]]+)\] (?P<summary>.+)$"
)
_FIX = re.compile(r"^\s*→ FIX:\s*(?P<fix>.+)$")


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


from ledger_ids import observation_id, wpsec_finding_key


def _normalize_site(site: str) -> str:
    return site.strip().lower().replace("https://", "").replace("http://", "").split("/")[0]


def _domain_for_finding(summary: str, tool: str) -> str:
    s = summary.lower()
    if any(x in s for x in ("csp", "header", "cookie", "xss", "waf", "exposed", "version")):
        return "web_stack.security"
    if any(x in s for x in ("lighthouse", "javascript", "performance", "cls", "lcp")):
        return "web_stack.performance"
    if "plugin" in s or "wordpress" in s or tool == "wpscan":
        return "web_stack.wordpress"
    return "web_stack.security"


def parse_report_md(path: Path, *, site: str, author: str) -> list[dict]:
    site = _normalize_site(site)
    if not path.is_file():
        return []
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    out: list[dict] = []
    pending_fix: str | None = None
    for i, line in enumerate(lines):
        m_fix = _FIX.match(line)
        if m_fix and out:
            out[-1]["evidence"]["fix"] = m_fix.group("fix").strip()
            out[-1]["summary"] = (
                f"{out[-1]['summary']} → FIX: {m_fix.group('fix').strip()}"
            )
            continue
        m = _FINDING.match(line)
        if not m:
            continue
        severity = m.group("severity").strip().lower()
        tool = m.group("tool").strip().lower()
        summary = m.group("summary").strip()
        key = wpsec_finding_key(tool, summary)
        obs_id = observation_id(site, "wpsec", key)
        out.append(
            {
                "id": obs_id,
                "kind": "observation",
                "domain": _domain_for_finding(summary, tool),
                "author_model": author,
                "site": site,
                "severity": severity,
                "summary": summary,
                "tool": tool,
                "source_path": f"site:{site}",
                "timestamp": _now(),
                "evidence": {"scanner": tool, "raw_line": line.strip()},
            }
        )
    return out


def parse_wpscan_json(path: Path, *, site: str) -> list[dict]:
    site = _normalize_site(site)
    if not path.is_file():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    out: list[dict] = []
    target = data.get("target_url") or f"https://{site}"
    version = (data.get("version") or {}).get("number")
    if version:
        out.append(
            {
                "id": observation_id(site, "wpsec", "wp-version"),
                "kind": "observation",
                "domain": "web_stack.security",
                "author_model": "wp-sec-agent",
                "site": site,
                "severity": "medium",
                "summary": f"WordPress version {version} exposed",
                "tool": "wpscan",
                "source_path": target,
                "timestamp": _now(),
                "evidence": {"wordpress_version": version, "url": target},
            }
        )
    return out


def parse_lighthouse_json(path: Path, *, site: str) -> list[dict]:
    site = _normalize_site(site)
    if not path.is_file():
        return []
    try:
        from export_lighthouse import export_lighthouse_file

        return export_lighthouse_file(path, site=site)
    except (OSError, json.JSONDecodeError, ImportError):
        return []


def export_observations(
    *,
    site: str,
    results_dir: Path,
    author: str = "wp-sec-agent",
) -> list[dict]:
    site = _normalize_site(site)
    records: list[dict] = []
    records.extend(
        parse_report_md(results_dir / "report.md", site=site, author=author)
    )
    records.extend(parse_wpscan_json(results_dir / "wpscan.json", site=site))
    records.extend(parse_lighthouse_json(results_dir / "lighthouse.json", site=site))
    # de-dupe by stable ledger id
    seen: set[str] = set()
    unique: list[dict] = []
    for r in records:
        key = r.get("id") or r["summary"][:120]
        if key in seen:
            continue
        seen.add(key)
        unique.append(r)
    return unique


def main() -> None:
    ap = argparse.ArgumentParser(description="Export scan results to observations.jsonl")
    ap.add_argument("--site", required=True, help="e.g. staging2.willowyhollow.com")
    ap.add_argument(
        "--results-dir",
        type=Path,
        help="Directory with report.md, wpscan.json, lighthouse.json",
    )
    ap.add_argument(
        "--wp-sec-root",
        type=Path,
        default=Path.home() / "Projects" / "wp-sec-agent",
        help="wp-sec-agent repo root (default: ~/Projects/wp-sec-agent)",
    )
    ap.add_argument("-o", "--output", type=Path, default=Path("observations.jsonl"))
    ap.add_argument("--author", default="wp-sec-agent")
    ap.add_argument("--print", action="store_true", help="Print JSONL to stdout")
    args = ap.parse_args()

    site = args.site
    results_dir = args.results_dir
    if results_dir is None:
        results_dir = args.wp_sec_root / "clients" / site / "results"

    records = export_observations(site=site, results_dir=results_dir, author=args.author)
    if not records:
        print(f"No observations parsed from {results_dir}", file=__import__("sys").stderr)
        raise SystemExit(0)

    lines = [json.dumps(r, ensure_ascii=False) for r in records]
    if args.print:
        print("\n".join(lines))
    else:
        args.output.write_text("\n".join(lines) + "\n", encoding="utf-8")
        print(f"Wrote {len(records)} observation(s) → {args.output}")


if __name__ == "__main__":
    main()

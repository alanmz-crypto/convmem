#!/usr/bin/env python3
"""Compare Pylint JSON findings to a committed baseline (regression gate).

Fingerprints ignore line/column movement. A run fails when any fingerprint's
occurrence count exceeds the baseline (new finding or more duplicates).
Improvements (removed or fewer findings) pass.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Iterable


Fingerprint = tuple[str, str, str, str]  # path, symbol, msg_id, message


def _norm_path(path: str) -> str:
    p = path.replace("\\", "/").strip()
    if p.startswith("./"):
        p = p[2:]
    return p


def fingerprint_from_message(msg: dict[str, Any]) -> Fingerprint:
    """Stable identity for one Pylint message (no line/column)."""
    path = _norm_path(str(msg.get("path") or msg.get("module") or ""))
    symbol = str(msg.get("symbol") or "")
    msg_id = str(msg.get("message-id") or msg.get("message_id") or "")
    message = str(msg.get("message") or "").strip()
    return (path, symbol, msg_id, message)


def load_report_messages(report: Any) -> list[dict[str, Any]]:
    """Accept a JSON list or {\"messages\": [...]} wrapper."""
    if isinstance(report, list):
        return [m for m in report if isinstance(m, dict)]
    if isinstance(report, dict):
        msgs = report.get("messages")
        if isinstance(msgs, list):
            return [m for m in msgs if isinstance(m, dict)]
    raise ValueError("Pylint report must be a JSON list of messages")


def count_fingerprints(messages: Iterable[dict[str, Any]]) -> Counter[Fingerprint]:
    counts: Counter[Fingerprint] = Counter()
    for msg in messages:
        counts[fingerprint_from_message(msg)] += 1
    return counts


def baseline_to_counter(baseline: Any) -> Counter[Fingerprint]:
    """Load baseline as list of {path,symbol,msg_id,message,count} or dict map."""
    counts: Counter[Fingerprint] = Counter()
    if isinstance(baseline, dict) and "findings" in baseline:
        baseline = baseline["findings"]
    if isinstance(baseline, list):
        for row in baseline:
            if not isinstance(row, dict):
                continue
            fp = (
                _norm_path(str(row.get("path") or "")),
                str(row.get("symbol") or ""),
                str(row.get("msg_id") or row.get("message-id") or ""),
                str(row.get("message") or "").strip(),
            )
            counts[fp] += int(row.get("count") or 1)
        return counts
    raise ValueError("baseline must be a list of finding objects (or {findings: [...]})")


def counter_to_baseline(counts: Counter[Fingerprint]) -> dict[str, Any]:
    findings = [
        {
            "path": path,
            "symbol": symbol,
            "msg_id": msg_id,
            "message": message,
            "count": count,
        }
        for (path, symbol, msg_id, message), count in sorted(
            counts.items(), key=lambda kv: (kv[0][0], kv[0][2], kv[0][1], kv[0][3])
        )
    ]
    return {
        "version": 1,
        "fingerprint": ["path", "symbol", "msg_id", "message"],
        "findings": findings,
    }


def find_regressions(
    baseline: Counter[Fingerprint], current: Counter[Fingerprint]
) -> list[tuple[Fingerprint, int, int]]:
    """Return (fingerprint, baseline_count, current_count) for each regression."""
    regressions: list[tuple[Fingerprint, int, int]] = []
    for fp, cur in sorted(current.items(), key=lambda kv: (kv[0][0], kv[0][2], kv[0][3])):
        base = baseline.get(fp, 0)
        if cur > base:
            regressions.append((fp, base, cur))
    return regressions


def format_regression(fp: Fingerprint, base: int, cur: int) -> str:
    path, symbol, msg_id, message = fp
    delta = cur - base
    msg = message if len(message) <= 120 else message[:117] + "..."
    where = path or "(no-path)"
    return f"+{delta} {where} {msg_id}/{symbol}: {msg} (was {base}, now {cur})"


def compare_reports(
    baseline_counts: Counter[Fingerprint], current_counts: Counter[Fingerprint]
) -> tuple[bool, list[str]]:
    """Return (ok, lines). ok True when no count increases."""
    regs = find_regressions(baseline_counts, current_counts)
    if not regs:
        return True, [
            f"Pylint regression gate PASS "
            f"({sum(current_counts.values())} findings, "
            f"{len(current_counts)} fingerprints; no new/increased vs baseline)"
        ]
    lines = [
        f"Pylint regression gate FAIL: {len(regs)} new/increased fingerprint(s)"
    ]
    # Concise: cap display but report total
    shown = regs[:40]
    for fp, base, cur in shown:
        lines.append(format_regression(fp, base, cur))
    if len(regs) > len(shown):
        lines.append(f"... and {len(regs) - len(shown)} more")
    return False, lines


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_cmp = sub.add_parser("compare", help="Compare a report to the baseline")
    p_cmp.add_argument("--baseline", type=Path, required=True)
    p_cmp.add_argument("--report", type=Path, required=True)

    p_write = sub.add_parser(
        "write-baseline", help="Write baseline JSON from a Pylint JSON report"
    )
    p_write.add_argument("--report", type=Path, required=True)
    p_write.add_argument("--output", type=Path, required=True)

    args = parser.parse_args(argv)

    if args.cmd == "write-baseline":
        report = json.loads(args.report.read_text(encoding="utf-8"))
        counts = count_fingerprints(load_report_messages(report))
        out = counter_to_baseline(counts)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
        print(
            f"Wrote {args.output} "
            f"({sum(counts.values())} findings, {len(counts)} fingerprints)"
        )
        return 0

    if args.cmd == "compare":
        baseline_raw = json.loads(args.baseline.read_text(encoding="utf-8"))
        report_raw = json.loads(args.report.read_text(encoding="utf-8"))
        baseline = baseline_to_counter(baseline_raw)
        current = count_fingerprints(load_report_messages(report_raw))
        ok, lines = compare_reports(baseline, current)
        for line in lines:
            print(line)
        return 0 if ok else 1

    parser.error(f"unknown command {args.cmd}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())

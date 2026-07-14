#!/usr/bin/env python3
"""Compare Pylint JSON findings to a committed baseline (regression gate).

Fingerprints ignore physical line/column and normalize R0801 embedded
``==module:[start:end]`` ranges so pure line movement does not fail.

A run fails when any fingerprint's occurrence count exceeds the baseline
(new finding or more duplicates). Improvements (removed or fewer findings)
pass.

Pylint exit bits: fatal (1) and usage (32) always fail closed. Ordinary
message bits (error/warning/refactor/convention) are allowed when the
regression comparison passes.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from collections import Counter
from pathlib import Path
from typing import Any, Iterable


Fingerprint = tuple[str, str, str, str]  # path, symbol, msg_id, message

# Pylint bit flags (documented exit encoding).
PYLINT_FATAL = 1
PYLINT_ERROR = 2
PYLINT_WARNING = 4
PYLINT_REFACTOR = 8
PYLINT_CONVENTION = 16
PYLINT_USAGE = 32
PYLINT_MESSAGE_BITS = (
    PYLINT_ERROR | PYLINT_WARNING | PYLINT_REFACTOR | PYLINT_CONVENTION
)

# R0801 embeds ranges like ``==adapters.detect:[121:127]`` (module kept).
_EMBEDDED_LINE_RANGE = re.compile(r"(==[^\s\[:]+):\[\d+:\d+\]")
_CYCLIC_IMPORT = re.compile(
    r"^(Cyclic import \()([^)]+)(\))\s*$", re.MULTILINE
)


def _canonicalize_cyclic_import(message: str) -> str:
    """Stabilize R0401: same module set → same fingerprint regardless of ring order."""

    def repl(match: re.Match[str]) -> str:
        parts = [p.strip() for p in match.group(2).split("->") if p.strip()]
        if len(parts) < 2:
            return match.group(0)
        # Sorted unique module set — Pylint varies both rotation and which
        # equivalent import rings it surfaces between runs.
        uniq = sorted(set(parts))
        return f"Cyclic import modules: {', '.join(uniq)}"

    return _CYCLIC_IMPORT.sub(repl, message.strip())


def _canonicalize_duplicate_code(message: str) -> str:
    """Stabilize R0801: range-normalize, sort ==module headers, keep body text."""
    message = _EMBEDDED_LINE_RANGE.sub(r"\1:[#:#]", message)
    lines = message.split("\n")
    if not lines:
        return message
    out: list[str] = []
    i = 0
    if lines[0].startswith("Similar lines"):
        out.append(lines[0])
        i = 1
    mod_lines: list[str] = []
    while i < len(lines) and lines[i].startswith("=="):
        mod_lines.append(lines[i])
        i += 1
    out.extend(sorted(mod_lines))
    out.extend(lines[i:])
    return "\n".join(out)


def normalize_message(message: str, *, symbol: str = "", msg_id: str = "") -> str:
    """Normalize unstable Pylint message shapes before fingerprinting.

    - Always rewrite embedded ``==name:[n:m]`` ranges to ``[#:#]``.
    - R0801: sort module header lines; preserve duplicate-code body.
    - R0401: rotate the import cycle to a canonical start.
    """
    message = message.strip()
    if msg_id == "R0401" or symbol == "cyclic-import":
        return _canonicalize_cyclic_import(message)
    if msg_id == "R0801" or symbol == "duplicate-code":
        return _canonicalize_duplicate_code(message)
    return _EMBEDDED_LINE_RANGE.sub(r"\1:[#:#]", message)


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
    message = normalize_message(
        str(msg.get("message") or "").strip(), symbol=symbol, msg_id=msg_id
    )
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
    """Load baseline as list of {path,symbol,msg_id,message,count}."""
    counts: Counter[Fingerprint] = Counter()
    if isinstance(baseline, dict) and "findings" in baseline:
        baseline = baseline["findings"]
    if isinstance(baseline, list):
        for row in baseline:
            if not isinstance(row, dict):
                continue
            symbol = str(row.get("symbol") or "")
            msg_id = str(row.get("msg_id") or row.get("message-id") or "")
            fp = (
                _norm_path(str(row.get("path") or "")),
                symbol,
                msg_id,
                normalize_message(
                    str(row.get("message") or "").strip(),
                    symbol=symbol,
                    msg_id=msg_id,
                ),
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
    shown = regs[:40]
    for fp, base, cur in shown:
        lines.append(format_regression(fp, base, cur))
    if len(regs) > len(shown):
        lines.append(f"... and {len(regs) - len(shown)} more")
    return False, lines


def pylint_status_ok(exit_status: int) -> tuple[bool, str]:
    """Accept clean (0) or ordinary message bits; reject fatal/usage."""
    status = int(exit_status)
    if status < 0:
        return False, f"Pylint status {status}: invalid negative exit"
    if status & PYLINT_FATAL:
        return False, f"Pylint status {status}: fatal/internal (bit 1) — fail closed"
    if status & PYLINT_USAGE:
        return False, f"Pylint status {status}: usage error (bit 32) — fail closed"
    # Remaining bits (0 or message bits) are OK for the status gate.
    extra = status & ~PYLINT_MESSAGE_BITS
    if extra:
        return False, f"Pylint status {status}: unexpected bits {extra:#x}"
    return True, f"Pylint status {status}: accepted (no fatal/usage bits)"


def git_show_text(ref: str, path: str) -> str | None:
    """Return file contents at ref:path, or None if missing."""
    proc = subprocess.run(
        ["git", "show", f"{ref}:{path}"],
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        return None
    return proc.stdout


def resolve_baseline_bytes(
    *,
    base_ref: str | None,
    branch_baseline: Path,
    baseline_repo_path: str = "ci/pylint-baseline.json",
) -> tuple[bytes, str]:
    """Load baseline from base_ref when present; else branch file.

    BOOTSTRAP provenance is only returned when a base_ref was provided and the
    file is genuinely missing there (first introduction of the baseline).

    Returns (raw_json_bytes, provenance_label).
    """
    if base_ref:
        text = git_show_text(base_ref, baseline_repo_path)
        if text is not None:
            return text.encode("utf-8"), f"base:{base_ref}"
        # Base checked out / resolvable but file absent → first-time bootstrap.
        if not branch_baseline.is_file():
            raise FileNotFoundError(
                f"No baseline at {baseline_repo_path} on base {base_ref} "
                f"and no branch file at {branch_baseline}"
            )
        return branch_baseline.read_bytes(), "BOOTSTRAP:branch"

    if not branch_baseline.is_file():
        raise FileNotFoundError(
            f"No branch baseline at {branch_baseline} and no base-ref provided"
        )
    return branch_baseline.read_bytes(), "branch:HEAD"


def validate_baseline_change(
    base_counts: Counter[Fingerprint], branch_counts: Counter[Fingerprint]
) -> tuple[bool, list[str]]:
    """Reject baseline edits that introduce new/increased fingerprints."""
    regs = find_regressions(base_counts, branch_counts)
    if not regs:
        return True, [
            "Baseline change validation PASS "
            "(no new/increased fingerprints vs base baseline)"
        ]
    lines = [
        f"Baseline change validation FAIL: branch baseline blesses "
        f"{len(regs)} new/increased fingerprint(s) — refuse self-blessing"
    ]
    for fp, base, cur in regs[:40]:
        lines.append(format_regression(fp, base, cur))
    if len(regs) > 40:
        lines.append(f"... and {len(regs) - 40} more")
    return False, lines


def _load_json_bytes(raw: bytes) -> Any:
    return json.loads(raw.decode("utf-8"))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_cmp = sub.add_parser("compare", help="Compare a report to a baseline file")
    p_cmp.add_argument("--baseline", type=Path, required=True)
    p_cmp.add_argument("--report", type=Path, required=True)
    p_cmp.add_argument(
        "--pylint-status",
        type=int,
        default=0,
        help="Raw pylint process exit status (bits)",
    )

    p_write = sub.add_parser(
        "write-baseline", help="Write baseline JSON from a Pylint JSON report"
    )
    p_write.add_argument("--report", type=Path, required=True)
    p_write.add_argument("--output", type=Path, required=True)

    p_ci = sub.add_parser(
        "ci",
        help="CI entry: resolve base baseline, optional change check, compare report",
    )
    p_ci.add_argument("--report", type=Path, required=True)
    p_ci.add_argument("--pylint-status", type=int, required=True)
    p_ci.add_argument(
        "--base-ref",
        default="",
        help="Git SHA of PR base / parent (empty → treat as bootstrap if needed)",
    )
    p_ci.add_argument(
        "--branch-baseline",
        type=Path,
        default=Path("ci/pylint-baseline.json"),
        help="Baseline path in the checked-out branch",
    )
    p_ci.add_argument(
        "--baseline-repo-path",
        default="ci/pylint-baseline.json",
        help="Path inside the git tree for base_ref lookup",
    )

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
        status_ok, status_msg = pylint_status_ok(args.pylint_status)
        print(status_msg)
        if not status_ok:
            return 1
        baseline_raw = json.loads(args.baseline.read_text(encoding="utf-8"))
        report_raw = json.loads(args.report.read_text(encoding="utf-8"))
        baseline = baseline_to_counter(baseline_raw)
        current = count_fingerprints(load_report_messages(report_raw))
        ok, lines = compare_reports(baseline, current)
        for line in lines:
            print(line)
        return 0 if ok else 1

    if args.cmd == "ci":
        status_ok, status_msg = pylint_status_ok(args.pylint_status)
        print(status_msg)
        if not status_ok:
            # Fail closed even if a partial JSON report exists.
            print(
                "Refusing to accept report after fatal/usage Pylint status "
                "(partial nonempty report is not success)."
            )
            return 1

        base_ref = (args.base_ref or "").strip() or None
        raw, provenance = resolve_baseline_bytes(
            base_ref=base_ref,
            branch_baseline=args.branch_baseline,
            baseline_repo_path=args.baseline_repo_path,
        )
        if provenance.startswith("BOOTSTRAP"):
            print(
                "BOOTSTRAP: base ref lacks "
                f"{args.baseline_repo_path}; using branch baseline "
                f"at {args.branch_baseline} for this introduction only"
            )
        else:
            print(f"Using baseline from {provenance}")

        reference = baseline_to_counter(_load_json_bytes(raw))

        # If base had a baseline and the branch also has one, ensure the branch
        # file does not raise the bar (no self-blessing of new debt).
        if (
            provenance.startswith("base:")
            and args.branch_baseline.is_file()
        ):
            branch_counts = baseline_to_counter(
                json.loads(args.branch_baseline.read_text(encoding="utf-8"))
            )
            # Only enforce when branch file content differs from base.
            if branch_counts != reference:
                bok, blines = validate_baseline_change(reference, branch_counts)
                for line in blines:
                    print(line)
                if not bok:
                    return 1

        report_raw = json.loads(args.report.read_text(encoding="utf-8"))
        current = count_fingerprints(load_report_messages(report_raw))
        # Always compare the live report to the *reference* baseline (base SHA
        # when present), never to a branch-raised baseline.
        ok, lines = compare_reports(reference, current)
        for line in lines:
            print(line)
        return 0 if ok else 1

    parser.error(f"unknown command {args.cmd}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())

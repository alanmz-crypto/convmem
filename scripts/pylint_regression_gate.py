#!/usr/bin/env python3
"""Compare Pylint JSON findings to a committed baseline (regression gate).

Fingerprints ignore physical line/column. Embedded ``==module:[start:end]``
ranges in non-aggregate messages are normalized so pure line movement does
not fail.

**R0801 / R0401 aggregation:** duplicate-code and cyclic-import collapse to a
single fingerprint ``(*, symbol, msg_id, "")``. Only an *increased* aggregate
count fails. Accepted blind spot: replacing one pairing/ring with a different
semantic instance at the same aggregate count does not fail.

A run fails when any fingerprint's occurrence count exceeds the baseline
(new finding or more duplicates). Improvements (removed or fewer findings)
pass.

Pylint exit bits: fatal (1) and usage (32) always fail closed. Ordinary
message bits (error/warning/refactor/convention) are allowed when the
regression comparison passes.

Baseline provenance: with ``--base-ref``, the commit must resolve first.
BOOTSTRAP (use branch file) only when that valid commit lacks the baseline
path. Invalid SHA, null OID, shallow/missing history, and git errors fail
closed — they must never bootstrap.
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

# Non-aggregate messages may still embed ranges like ``==mod:[121:127]``.
_EMBEDDED_LINE_RANGE = re.compile(r"(==[^\s\[:]+):\[\d+:\d+\]")

# Aggregate symbols/ids — fingerprinted by count only (see module docstring).
_AGGREGATE_MSG_IDS = frozenset({"R0801", "R0401"})
_AGGREGATE_SYMBOLS = frozenset({"duplicate-code", "cyclic-import"})

# GitHub push "before" on branch creation (also reject shorter all-zero OIDs).
_NULL_OID = frozenset({"0" * 40, "0" * 64})


class BaselineResolveError(RuntimeError):
    """Base ref cannot be resolved or git failed — fail closed (never bootstrap)."""


_COMPLEXITY_COUNT = re.compile(r"^(.*?)\((\d+)/(\d+)\)\s*$")


def _is_complexity_finding(*, symbol: str, msg_id: str) -> bool:
    return bool(
        msg_id.startswith("R09")
        or msg_id == "C0302"
        or symbol.startswith("too-many")
        or symbol == "too-many-lines"
    )


def complexity_metric(message: str) -> int | None:
    """Return the measured N from a ``(N/limit)`` complexity message, else None."""
    match = _COMPLEXITY_COUNT.match(message.strip())
    if not match:
        return None
    return int(match.group(2))


def normalize_message(message: str, *, symbol: str = "", msg_id: str = "") -> str:
    """Normalize unstable shapes for *non-aggregate* fingerprints.

    Rewrites embedded ``==name:[n:m]`` ranges to ``[#:#]``. For complexity /
    too-many-lines messages, replaces ``(N/limit)`` with ``(#/#)`` so identity
    is stable while ``complexity_metric`` / ``find_regressions`` still detect
    increases in N. R0801/R0401 use aggregate fingerprints instead.
    """
    message = message.strip()
    if _is_complexity_finding(symbol=symbol, msg_id=msg_id):
        match = _COMPLEXITY_COUNT.match(message)
        if match:
            message = f"{match.group(1).rstrip()} (#/#)"
    return _EMBEDDED_LINE_RANGE.sub(r"\1:[#:#]", message)


def _norm_path(path: str) -> str:
    p = path.replace("\\", "/").strip()
    if p.startswith("./"):
        p = p[2:]
    return p


def fingerprint_from_message(msg: dict[str, Any]) -> Fingerprint:
    """Stable identity for one Pylint message (no line/column).

    R0801/R0401 → aggregate ``(*, symbol, msg_id, "")`` so CI pairing/ring
    flakes do not fail; increased aggregate counts still fail. Blind spot:
    equal-count semantic replacement passes. Other messages keep full
    path/symbol/id/text fingerprints (with range normalization).
    """
    path = _norm_path(str(msg.get("path") or msg.get("module") or ""))
    symbol = str(msg.get("symbol") or "")
    msg_id = str(msg.get("message-id") or msg.get("message_id") or "")
    if msg_id in _AGGREGATE_MSG_IDS or symbol in _AGGREGATE_SYMBOLS:
        return ("*", symbol, msg_id, "")
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


def count_fingerprints(
    messages: Iterable[dict[str, Any]],
) -> Counter[Fingerprint]:
    counts, _metrics = count_fingerprints_with_metrics(messages)
    return counts


def count_fingerprints_with_metrics(
    messages: Iterable[dict[str, Any]],
) -> tuple[Counter[Fingerprint], dict[Fingerprint, int]]:
    """Occurrence counts plus max complexity metric N per fingerprint."""
    counts: Counter[Fingerprint] = Counter()
    metrics: dict[Fingerprint, int] = {}
    for msg in messages:
        fp = fingerprint_from_message(msg)
        counts[fp] += 1
        symbol = str(msg.get("symbol") or "")
        msg_id = str(msg.get("message-id") or msg.get("message_id") or "")
        if _is_complexity_finding(symbol=symbol, msg_id=msg_id):
            metric = complexity_metric(str(msg.get("message") or ""))
            if metric is not None:
                prev = metrics.get(fp)
                metrics[fp] = metric if prev is None else max(prev, metric)
    return counts, metrics


def baseline_to_counter(baseline: Any) -> Counter[Fingerprint]:
    """Load baseline as list of {path,symbol,msg_id,message,count}."""
    counts, _metrics = baseline_to_counter_with_metrics(baseline)
    return counts


def baseline_to_counter_with_metrics(
    baseline: Any,
) -> tuple[Counter[Fingerprint], dict[Fingerprint, int]]:
    """Load baseline occurrence counts and complexity metrics."""
    counts: Counter[Fingerprint] = Counter()
    metrics: dict[Fingerprint, int] = {}
    if isinstance(baseline, dict) and "findings" in baseline:
        baseline = baseline["findings"]
    if isinstance(baseline, list):
        for row in baseline:
            if not isinstance(row, dict):
                continue
            # Must match fingerprint_from_message (incl. R0801/R0401 aggregates).
            raw_message = row.get("message") or ""
            msg = {
                "path": row.get("path") or "",
                "symbol": row.get("symbol") or "",
                "message-id": row.get("msg_id") or row.get("message-id") or "",
                "message": raw_message,
            }
            fp = fingerprint_from_message(msg)
            counts[fp] += int(row.get("count") or 1)
            symbol = str(msg["symbol"])
            msg_id = str(msg["message-id"])
            if _is_complexity_finding(symbol=symbol, msg_id=msg_id):
                metric = complexity_metric(str(raw_message))
                if metric is not None:
                    prev = metrics.get(fp)
                    metrics[fp] = metric if prev is None else max(prev, metric)
        return counts, metrics
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
    baseline: Counter[Fingerprint],
    current: Counter[Fingerprint],
    *,
    baseline_metrics: dict[Fingerprint, int] | None = None,
    current_metrics: dict[Fingerprint, int] | None = None,
) -> list[tuple[Fingerprint, int, int, str]]:
    """Return regressions for occurrence increases or complexity metric increases.

    Each item is ``(fingerprint, baseline_value, current_value, kind)`` where
    ``kind`` is ``"count"`` (occurrence) or ``"metric"`` (complexity N).
    """
    baseline_metrics = baseline_metrics or {}
    current_metrics = current_metrics or {}
    regressions: list[tuple[Fingerprint, int, int, str]] = []
    for fp, cur in sorted(current.items(), key=lambda kv: (kv[0][0], kv[0][2], kv[0][3])):
        base = baseline.get(fp, 0)
        if cur > base:
            regressions.append((fp, base, cur, "count"))
    for fp, cur_metric in sorted(
        current_metrics.items(), key=lambda kv: (kv[0][0], kv[0][2], kv[0][3])
    ):
        base_metric = baseline_metrics.get(fp)
        if base_metric is None:
            # New complexity fingerprint with no baseline metric — occurrence
            # path already reports new findings; skip duplicate metric noise.
            if fp not in baseline:
                continue
            continue
        if cur_metric > base_metric:
            regressions.append((fp, base_metric, cur_metric, "metric"))
    return regressions


def format_regression(
    fp: Fingerprint, base: int, cur: int, kind: str = "count"
) -> str:
    path, symbol, msg_id, message = fp
    delta = cur - base
    msg = message if len(message) <= 120 else message[:117] + "..."
    where = path or "(no-path)"
    if kind == "metric":
        return (
            f"+metric {where} {msg_id}/{symbol}: {msg} "
            f"(complexity {base} -> {cur})"
        )
    return f"+{delta} {where} {msg_id}/{symbol}: {msg} (was {base}, now {cur})"


def compare_reports(
    baseline_counts: Counter[Fingerprint],
    current_counts: Counter[Fingerprint],
    *,
    baseline_metrics: dict[Fingerprint, int] | None = None,
    current_metrics: dict[Fingerprint, int] | None = None,
) -> tuple[bool, list[str]]:
    """Return (ok, lines). ok True when no occurrence/metric increases."""
    regs = find_regressions(
        baseline_counts,
        current_counts,
        baseline_metrics=baseline_metrics,
        current_metrics=current_metrics,
    )
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
    for fp, base, cur, kind in shown:
        lines.append(format_regression(fp, base, cur, kind))
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


def _git(
    args: list[str], *, cwd: Path | None = None
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        capture_output=True,
        text=True,
        check=False,
        cwd=str(cwd) if cwd is not None else None,
    )


def _is_null_oid(ref: str) -> bool:
    return ref in _NULL_OID or (len(ref) >= 40 and set(ref) == {"0"})


def ensure_git_commit(ref: str, *, cwd: Path | None = None) -> str:
    """Return the resolved commit SHA, or raise BaselineResolveError."""
    if not ref or _is_null_oid(ref):
        raise BaselineResolveError(
            f"base ref {ref!r} is missing or a null OID — cannot resolve commit"
        )
    proc = _git(["rev-parse", "--verify", f"{ref}^{{commit}}"], cwd=cwd)
    if proc.returncode != 0:
        err = (proc.stderr or proc.stdout or "").strip() or f"exit {proc.returncode}"
        raise BaselineResolveError(
            f"Cannot resolve base ref {ref!r} as a commit "
            f"(invalid SHA, shallow/missing history, or git error): {err}"
        )
    return proc.stdout.strip()


def probe_baseline_path_in_commit(
    ref: str, path: str, *, cwd: Path | None = None
) -> str:
    """Tri-state path probe via ``git ls-tree --name-only``.

    Returns:
      ``"present"`` — exit 0 and stdout is exactly ``path``
      ``"absent"`` — exit 0 and empty stdout (only condition that may bootstrap)

    Any nonzero git status, or exit 0 with unexpected stdout, raises
    ``BaselineResolveError`` (fail closed — never bootstrap).
    """
    proc = _git(["ls-tree", "--name-only", ref, "--", path], cwd=cwd)
    if proc.returncode != 0:
        err = (proc.stderr or proc.stdout or "").strip() or f"exit {proc.returncode}"
        raise BaselineResolveError(
            f"git ls-tree failed probing {path!r} at {ref}: {err}"
        )
    lines = [ln.strip() for ln in (proc.stdout or "").splitlines() if ln.strip()]
    if not lines:
        return "absent"
    if lines == [path]:
        return "present"
    raise BaselineResolveError(
        f"git ls-tree returned unexpected paths for {ref}:{path}: {lines!r}"
    )


def git_show_text(ref: str, path: str, *, cwd: Path | None = None) -> str:
    """Return file contents at ref:path; raise BaselineResolveError on failure."""
    proc = _git(["show", f"{ref}:{path}"], cwd=cwd)
    if proc.returncode != 0:
        err = (proc.stderr or proc.stdout or "").strip() or f"exit {proc.returncode}"
        raise BaselineResolveError(
            f"git show failed for {ref}:{path}: {err}"
        )
    return proc.stdout


def resolve_baseline_bytes(
    *,
    base_ref: str | None,
    branch_baseline: Path,
    baseline_repo_path: str = "ci/pylint-baseline.json",
    git_cwd: Path | None = None,
) -> tuple[bytes, str]:
    """Load baseline from base_ref when present; else branch file.

    When ``base_ref`` is set:
      1. Verify it resolves as a commit (else BaselineResolveError — no bootstrap).
      2. Probe ``baseline_repo_path`` with ``git ls-tree --name-only``:
         present → ``git show`` base baseline; absent (empty) → BOOTSTRAP;
         any probe/show error → BaselineResolveError (never bootstrap).

    Returns (raw_json_bytes, provenance_label).
    """
    if base_ref:
        sha = ensure_git_commit(base_ref, cwd=git_cwd)
        state = probe_baseline_path_in_commit(
            sha, baseline_repo_path, cwd=git_cwd
        )
        if state == "present":
            content = git_show_text(sha, baseline_repo_path, cwd=git_cwd)
            return content.encode("utf-8"), f"base:{sha}"
        # state == "absent": only empty ls-tree may bootstrap.
        if not branch_baseline.is_file():
            raise FileNotFoundError(
                f"No baseline at {baseline_repo_path} on base {sha} "
                f"and no branch file at {branch_baseline}"
            )
        return branch_baseline.read_bytes(), "BOOTSTRAP:branch"

    if not branch_baseline.is_file():
        raise FileNotFoundError(
            f"No branch baseline at {branch_baseline} and no base-ref provided"
        )
    return branch_baseline.read_bytes(), "branch:HEAD"


def validate_baseline_change(
    base_counts: Counter[Fingerprint],
    branch_counts: Counter[Fingerprint],
    *,
    base_metrics: dict[Fingerprint, int] | None = None,
    branch_metrics: dict[Fingerprint, int] | None = None,
) -> tuple[bool, list[str]]:
    """Reject baseline edits that introduce new/increased fingerprints."""
    regs = find_regressions(
        base_counts,
        branch_counts,
        baseline_metrics=base_metrics,
        current_metrics=branch_metrics,
    )
    if not regs:
        return True, [
            "Baseline change validation PASS "
            "(no new/increased fingerprints vs base baseline)"
        ]
    lines = [
        f"Baseline change validation FAIL: branch baseline blesses "
        f"{len(regs)} new/increased fingerprint(s) — refuse self-blessing"
    ]
    for fp, base, cur, kind in regs[:40]:
        lines.append(format_regression(fp, base, cur, kind))
    if len(regs) > 40:
        lines.append(f"... and {len(regs) - 40} more")
    return False, lines


def _load_json_bytes(raw: bytes) -> Any:
    return json.loads(raw.decode("utf-8"))


def _cmd_ci(args: argparse.Namespace) -> int:
    status_ok, status_msg = pylint_status_ok(args.pylint_status)
    print(status_msg)
    if not status_ok:
        return 1

    base_ref = (args.base_ref or "").strip() or None
    try:
        raw, provenance = resolve_baseline_bytes(
            base_ref=base_ref,
            branch_baseline=args.branch_baseline,
            baseline_repo_path=args.baseline_repo_path,
            git_cwd=args.git_cwd,
        )
    except BaselineResolveError as exc:
        print(f"Baseline resolution FAIL: {exc}")
        return 1
    except FileNotFoundError as exc:
        print(f"Baseline resolution FAIL: {exc}")
        return 1
    if provenance.startswith("BOOTSTRAP"):
        print(
            "BOOTSTRAP: base ref lacks "
            f"{args.baseline_repo_path}; using branch baseline "
            f"at {args.branch_baseline} for this introduction only"
        )
    else:
        print(f"Using baseline from {provenance}")

    reference, reference_metrics = baseline_to_counter_with_metrics(
        _load_json_bytes(raw)
    )

    if provenance.startswith("base:") and args.branch_baseline.is_file():
        branch_counts, branch_metrics = baseline_to_counter_with_metrics(
            json.loads(args.branch_baseline.read_text(encoding="utf-8"))
        )
        if branch_counts != reference or branch_metrics != reference_metrics:
            bok, blines = validate_baseline_change(
                reference,
                branch_counts,
                base_metrics=reference_metrics,
                branch_metrics=branch_metrics,
            )
            for line in blines:
                print(line)
            if not bok:
                return 1

    report_raw = json.loads(args.report.read_text(encoding="utf-8"))
    current, current_metrics = count_fingerprints_with_metrics(
        load_report_messages(report_raw)
    )
    ok, lines = compare_reports(
        reference,
        current,
        baseline_metrics=reference_metrics,
        current_metrics=current_metrics,
    )
    for line in lines:
        print(line)
    return 0 if ok else 1


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
        help=(
            "Prior commit SHA: PR base.sha or push event.before. "
            "Must resolve as a commit; empty skips git lookup (local only)."
        ),
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
    p_ci.add_argument(
        "--git-cwd",
        type=Path,
        default=None,
        help="Working tree for git resolve (tests / non-ambient repos)",
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
        baseline, baseline_metrics = baseline_to_counter_with_metrics(baseline_raw)
        current, current_metrics = count_fingerprints_with_metrics(
            load_report_messages(report_raw)
        )
        ok, lines = compare_reports(
            baseline,
            current,
            baseline_metrics=baseline_metrics,
            current_metrics=current_metrics,
        )
        for line in lines:
            print(line)
        return 0 if ok else 1

    if args.cmd == "ci":
        return _cmd_ci(args)

    parser.error(f"unknown command {args.cmd}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())

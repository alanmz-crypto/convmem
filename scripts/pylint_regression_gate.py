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
# Counts and source lines in messages shift when unrelated lines are edited.
_COUNT_PAIR = re.compile(r"\((\d+)/(\d+)\)")
_OUTER_SCOPE_LINE = re.compile(r"\(line \d+\)")


def normalize_message(message: str, *, symbol: str = "", msg_id: str = "") -> str:
    """Normalize unstable shapes for *non-aggregate* fingerprints.

    Rewrites embedded ``==name:[n:m]`` ranges to ``[#:#]``. Also rewrites
    ``(N/M)`` complexity counts and ``(line N)`` outer-scope refs so edits that
    only shift line numbers or change debt magnitude do not invent new
    fingerprints. R0801/R0401 use aggregate fingerprints instead.
    """
    del symbol, msg_id  # API kept for call sites; aggregates bypass this.
    text = _EMBEDDED_LINE_RANGE.sub(r"\1:[#:#]", message.strip())
    text = _COUNT_PAIR.sub("(#/#)", text)
    text = _OUTER_SCOPE_LINE.sub("(line #)", text)
    return text


# Aggregate symbols/ids — fingerprinted by count only (see module docstring).
_AGGREGATE_MSG_IDS = frozenset({"R0801", "R0401"})
_AGGREGATE_SYMBOLS = frozenset({"duplicate-code", "cyclic-import"})

# GitHub push "before" on branch creation (also reject shorter all-zero OIDs).
_NULL_OID = frozenset({"0" * 40, "0" * 64})


class BaselineResolveError(RuntimeError):
    """Base ref cannot be resolved or git failed — fail closed (never bootstrap)."""


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
            # Must match fingerprint_from_message (incl. R0801/R0401 aggregates).
            # Re-running normalize_message on an already-aggregated empty message
            # used to invent "Similar lines modules:\n" and miss the live "*"/"" key.
            fp = fingerprint_from_message(
                {
                    "path": row.get("path") or "",
                    "symbol": row.get("symbol") or "",
                    "message-id": row.get("msg_id") or row.get("message-id") or "",
                    "message": row.get("message") or "",
                }
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

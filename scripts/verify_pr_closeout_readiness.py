#!/usr/bin/env python3
"""Verify PR closeout readiness before merge handoff.

Checks (fail-closed):

- PR OPEN, MERGEABLE, CLEAN
- headRefOid == --sha and baseRefOid == --base
- zero unresolved review threads (GraphQL pagination)
- PR body contains both SHAs as whole hex tokens
- no stale ``**Codex:**`` review bullet
- dual-lane exact-tip PASS via verify_exact_tip_lane_passes

Optional ``--require-mutex-acquired``: among issue comments matching
MAIN-MERGE-MUTEX, the latest must be exactly
``MAIN-MERGE-MUTEX ACQUIRED for PR #<n> closeout`` with no later
RELEASED/HELD token.
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Sequence

_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

# Imports after sys.path so sibling scripts resolve when run as a file.
from verify_exact_tip_lane_passes import (  # pylint: disable=wrong-import-position
    EvidenceItem,
    HEX40,
    fetch_pr_evidence,
    gh_json,
    verify_exact_tip_lane_passes,
    whole_token_sha_present,
)

# Exact twelve-path allowlist for PR #52 R2a closeout tip (set equality).
PR52_CLOSEOUT_ALLOWLIST = frozenset(
    {
        "docs/inter-model/CURSOR-2026-07-19-r2a-auth-schema-amendment.md",
        "docs/inter-model/CURSOR-2026-07-19-r2a-auth-schema-codex-fix.md",
        "docs/inter-model/CURSOR-2026-07-19-r2a-auth-schema-impl.md",
        "docs/inter-model/LATEST.md",
        "docs/plans/EXECUTION-embedding-model-eval.md",
        "eval_corpus/run_manifest.py",
        "eval_corpus/shadow_config.py",
        "scripts/eval_shadow_config_gen.py",
        "scripts/verify_exact_tip_lane_passes.py",
        "scripts/verify_pr_closeout_readiness.py",
        "tests/test_eval_r2a_auth_schema.py",
        "tests/test_verify_exact_tip_lane_passes.py",
    }
)

CODEX_REVIEW_LINE = re.compile(r"(?im)^\s*[-*]\s*\*\*Codex:\*\*")
MUTEX_ACQUIRED_RE = re.compile(
    r"^MAIN-MERGE-MUTEX ACQUIRED for PR #(?P<pr>\d+) closeout\s*$"
)
MUTEX_ANY_RE = re.compile(r"MAIN-MERGE-MUTEX")


@dataclass
class CloseoutHooks:
    """Optional injectable I/O hooks for hermetic tests."""

    fetch_evidence: Callable[[str, str, int], list[EvidenceItem]] | None = None
    fetch_pr_view: Callable[[], dict] | None = None
    count_threads: Callable[[], int] | None = None


@dataclass
class CloseoutFlags:
    """Boolean closeout gates."""

    require_mutex_acquired: bool = False
    check_allowlist: bool = False


@dataclass
class CloseoutInputs:
    """Injectable inputs for closeout readiness checks."""

    owner: str
    repo: str
    pr: int
    sha: str
    base: str
    flags: CloseoutFlags | None = None
    hooks: CloseoutHooks | None = None


def count_unresolved_threads(owner: str, repo: str, pr: int) -> int:
    """Paginate reviewThreads; fail if pagination claims hasNextPage without cursor."""
    query = """
    query($owner: String!, $name: String!, $number: Int!, $cursor: String) {
      repository(owner: $owner, name: $name) {
        pullRequest(number: $number) {
          reviewThreads(first: 100, after: $cursor) {
            pageInfo { hasNextPage endCursor }
            nodes { isResolved }
          }
        }
      }
    }
    """
    unresolved = 0
    cursor: str | None = None
    while True:
        args = [
            "api",
            "graphql",
            "-f",
            f"query={query}",
            "-F",
            f"owner={owner}",
            "-F",
            f"name={repo}",
            "-F",
            f"number={pr}",
        ]
        if cursor:
            args += ["-F", f"cursor={cursor}"]
        data = gh_json(args)
        conn = data["data"]["repository"]["pullRequest"]["reviewThreads"]
        for node in conn["nodes"]:
            if not node.get("isResolved"):
                unresolved += 1
        page = conn["pageInfo"]
        if not page.get("hasNextPage"):
            break
        cursor = page.get("endCursor")
        if not cursor:
            raise RuntimeError(
                "reviewThreads pagination: hasNextPage true but empty endCursor"
            )
    return unresolved


def assert_mutex_acquired(items: Sequence[EvidenceItem], *, pr: int) -> None:
    """Latest MAIN-MERGE-MUTEX comment must be ACQUIRED for this PR."""
    mutex_items = [
        it
        for it in items
        if it.kind == "issue_comment" and MUTEX_ANY_RE.search(it.body or "")
    ]
    if not mutex_items:
        raise RuntimeError("no MAIN-MERGE-MUTEX comments found")
    mutex_items.sort(key=lambda it: it.sort_key)
    latest = mutex_items[-1]
    body = (latest.body or "").strip()
    match = MUTEX_ACQUIRED_RE.match(body)
    if not match or int(match.group("pr")) != pr:
        raise RuntimeError(
            f"latest mutex token is not ACQUIRED for PR #{pr}: {body!r}"
        )
    if re.search(r"\b(RELEASED|HELD)\b", body):
        raise RuntimeError(f"latest mutex token is RELEASED/HELD: {body!r}")


def check_body(body: str, *, sha: str, base: str) -> list[str]:
    errs: list[str] = []
    if not whole_token_sha_present(body, sha):
        errs.append("PR body missing whole-token reviewed head SHA")
    if not whole_token_sha_present(body, base):
        errs.append("PR body missing whole-token reviewed base SHA")
    if CODEX_REVIEW_LINE.search(body):
        errs.append("PR body still has stale **Codex:** review bullet")
    return errs


def verify_closeout_readiness(inp: CloseoutInputs) -> tuple[bool, list[str]]:
    """Return (ok, messages). Injectable fetchers for unit tests."""
    messages: list[str] = []
    errs: list[str] = []
    sha = inp.sha
    base = inp.base

    if not HEX40.match(sha):
        return False, [f"sha must be 40 hex chars, got {sha!r}"]
    if not HEX40.match(base):
        return False, [f"base must be 40 hex chars, got {base!r}"]

    flags = inp.flags or CloseoutFlags()
    hooks = inp.hooks or CloseoutHooks()
    fetch_pr_view = hooks.fetch_pr_view
    if fetch_pr_view is None:

        def _view() -> dict:
            return gh_json(
                [
                    "pr",
                    "view",
                    str(inp.pr),
                    "--repo",
                    f"{inp.owner}/{inp.repo}",
                    "--json",
                    "state,headRefOid,baseRefOid,mergeable,mergeStateStatus,body,files",
                ]
            )

        fetch_pr_view = _view

    view = fetch_pr_view()
    if view.get("state") != "OPEN":
        errs.append(f"state={view.get('state')!r} (want OPEN)")
    if view.get("mergeable") != "MERGEABLE":
        errs.append(f"mergeable={view.get('mergeable')!r} (want MERGEABLE)")
    if view.get("mergeStateStatus") != "CLEAN":
        errs.append(
            f"mergeStateStatus={view.get('mergeStateStatus')!r} (want CLEAN)"
        )
    if view.get("headRefOid") != sha:
        errs.append(
            f"headRefOid={view.get('headRefOid')!r} != reviewed sha {sha}"
        )
    if view.get("baseRefOid") != base:
        errs.append(
            f"baseRefOid={view.get('baseRefOid')!r} != reviewed base {base}"
        )

    errs.extend(check_body(view.get("body") or "", sha=sha, base=base))

    count_threads = hooks.count_threads
    if count_threads is None:

        def _threads() -> int:
            return count_unresolved_threads(inp.owner, inp.repo, inp.pr)

        count_threads = _threads

    unresolved = count_threads()
    if unresolved != 0:
        errs.append(f"unresolved review threads: {unresolved}")
    else:
        messages.append("PASS unresolved threads: 0")

    if flags.check_allowlist:
        paths = {f.get("path") for f in (view.get("files") or []) if f.get("path")}
        if paths != PR52_CLOSEOUT_ALLOWLIST:
            only_remote = sorted(paths - PR52_CLOSEOUT_ALLOWLIST)
            only_allow = sorted(PR52_CLOSEOUT_ALLOWLIST - paths)
            errs.append(
                f"file allowlist mismatch; only_remote={only_remote} "
                f"only_allowlist={only_allow}"
            )
        else:
            messages.append("PASS file allowlist (12 paths)")

    fetch_fn = hooks.fetch_evidence or fetch_pr_evidence
    items = fetch_fn(inp.owner, inp.repo, inp.pr)

    if flags.require_mutex_acquired:
        try:
            assert_mutex_acquired(items, pr=inp.pr)
            messages.append("PASS mutex: ACQUIRED latest")
        except RuntimeError as exc:
            errs.append(str(exc))

    ok_lanes, lane_msgs = verify_exact_tip_lane_passes(items, sha=sha)
    messages.extend(lane_msgs)
    if not ok_lanes:
        errs.append("exact-tip lane PASS verifier failed")

    if errs:
        return False, [f"ERROR: {e}" for e in errs] + messages
    messages.append("PASS closeout readiness")
    return True, messages


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pr", type=int, required=True)
    parser.add_argument("--sha", required=True, help="Reviewed head (NEW_TIP)")
    parser.add_argument("--base", required=True, help="Reviewed base (REVIEWED_BASE)")
    parser.add_argument("--owner", default="alanmz-crypto")
    parser.add_argument("--repo", default="convmem")
    parser.add_argument(
        "--require-mutex-acquired",
        action="store_true",
        help="Require latest MAIN-MERGE-MUTEX comment is ACQUIRED (Ryan path)",
    )
    parser.add_argument(
        "--check-allowlist",
        action="store_true",
        help="Require PR file set equals the frozen 12-path closeout allowlist",
    )
    args = parser.parse_args(argv)

    ok, messages = verify_closeout_readiness(
        CloseoutInputs(
            owner=args.owner,
            repo=args.repo,
            pr=args.pr,
            sha=args.sha.lower(),
            base=args.base.lower(),
            flags=CloseoutFlags(
                require_mutex_acquired=args.require_mutex_acquired,
                check_allowlist=args.check_allowlist,
            ),
        )
    )
    sys.stdout.write("\n".join(messages) + ("\n" if messages else ""))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())

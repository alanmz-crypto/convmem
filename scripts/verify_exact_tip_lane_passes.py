#!/usr/bin/env python3
"""Verify exact-tip dual-lane PASS evidence on a pull request.

Looks at PR reviews, review comments, and issue comments. For each lane
(GitHub Copilot audit lane, Kiro), among items that mention the reviewed SHA
as a whole hex token and carry a PASS or FAIL verdict, the chronologically
latest item (timestamp, then numeric id) must be PASS.

Canonical verdict grammar (Ryan-recorded via alanmz-crypto):

    Lane: GitHub Copilot audit lane
    Verdict: PASS
    Reviewed head: <full sha>

    Lane: Kiro
    Verdict: PASS
    Reviewed head: <full sha>

Rejects edited comments (updated_at != created_at) and items that contain
both PASS and FAIL verdict lines.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from typing import Callable, Iterable, Sequence

ALLOWED_AUTHORS = frozenset({"alanmz-crypto"})
HEX40 = re.compile(r"^[0-9a-f]{40}$")

COPILOT_LANE_RE = re.compile(r"(?is)GitHub\s+Copilot\s+audit(?:[-\s]?lane)?")
KIRO_LANE_RE = re.compile(r"(?is)\bKiro\b")
VERDICT_PASS_LINE = re.compile(r"(?im)^\s*Verdict:\s*PASS\b")
VERDICT_FAIL_LINE = re.compile(r"(?im)^\s*Verdict:\s*FAIL\b")
PASS_TOKEN = re.compile(r"(?i)\bPASS\b")
FAIL_TOKEN = re.compile(r"(?i)\bFAIL\b")


@dataclass(frozen=True)
class EvidenceItem:
    """One review or comment that may carry lane verdict evidence."""

    kind: str
    item_id: int
    author: str
    body: str
    created_at: str
    updated_at: str
    url: str

    @property
    def sort_key(self) -> tuple[str, int]:
        return (self.created_at, self.item_id)


def whole_token_sha_present(body: str, sha: str) -> bool:
    """True when sha appears as a whole hex token (not a longer hash substring)."""
    if not HEX40.match(sha):
        return False
    return bool(re.search(rf"(?i)(^|[^0-9a-f]){re.escape(sha)}([^0-9a-f]|$)", body))


def classify_lane(body: str) -> str | None:
    """Return lane name if body identifies exactly one supported lane."""
    copilot = bool(COPILOT_LANE_RE.search(body))
    kiro = bool(KIRO_LANE_RE.search(body))
    if copilot and not kiro:
        return "copilot"
    if kiro and not copilot:
        return "kiro"
    return None


def verdict_of(body: str) -> str | None:
    """Return PASS, FAIL, or None. Reject mixed PASS+FAIL verdict lines."""
    has_pass_line = bool(VERDICT_PASS_LINE.search(body))
    has_fail_line = bool(VERDICT_FAIL_LINE.search(body))
    if has_pass_line and has_fail_line:
        return None
    if has_pass_line:
        return "PASS"
    if has_fail_line:
        return "FAIL"
    # Fallback: bare PASS/FAIL tokens (still reject both present).
    has_pass = bool(PASS_TOKEN.search(body))
    has_fail = bool(FAIL_TOKEN.search(body))
    if has_pass and has_fail:
        return None
    if has_pass:
        return "PASS"
    if has_fail:
        return "FAIL"
    return None


def is_edited(item: EvidenceItem) -> bool:
    """True when GitHub reports an edit (updated_at differs from created_at)."""
    if not item.updated_at or not item.created_at:
        return False
    return item.updated_at != item.created_at


def gh_json(args: Sequence[str]) -> object:
    """Run ``gh <args>`` and parse JSON. Raises on non-zero exit."""
    proc = subprocess.run(
        ["gh", *args],
        check=False,
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        raise RuntimeError(
            f"gh failed ({proc.returncode}): {proc.stderr.strip() or proc.stdout}"
        )
    return json.loads(proc.stdout)


def _paginate_rest(path: str, *, per_page: int = 100) -> list[dict]:
    page = 1
    out: list[dict] = []
    while True:
        data = gh_json(
            [
                "api",
                "-H",
                "Accept: application/vnd.github+json",
                f"{path}?per_page={per_page}&page={page}",
            ]
        )
        if not isinstance(data, list):
            raise RuntimeError(f"expected list from {path}, got {type(data).__name__}")
        if not data:
            break
        out.extend(data)
        if len(data) < per_page:
            break
        page += 1
    return out


def fetch_pr_evidence(owner: str, repo: str, pr: int) -> list[EvidenceItem]:
    """Fetch reviews + review comments + issue comments for a PR."""
    items: list[EvidenceItem] = []

    for rev in _paginate_rest(f"repos/{owner}/{repo}/pulls/{pr}/reviews"):
        user = (rev.get("user") or {}).get("login") or ""
        body = rev.get("body") or ""
        created = rev.get("submitted_at") or rev.get("created_at") or ""
        updated = rev.get("submitted_at") or created
        items.append(
            EvidenceItem(
                kind="review",
                item_id=int(rev["id"]),
                author=user,
                body=body,
                created_at=created,
                updated_at=updated,
                url=rev.get("html_url") or "",
            )
        )

    for cmt in _paginate_rest(f"repos/{owner}/{repo}/pulls/{pr}/comments"):
        user = (cmt.get("user") or {}).get("login") or ""
        items.append(
            EvidenceItem(
                kind="review_comment",
                item_id=int(cmt["id"]),
                author=user,
                body=cmt.get("body") or "",
                created_at=cmt.get("created_at") or "",
                updated_at=cmt.get("updated_at") or "",
                url=cmt.get("html_url") or "",
            )
        )

    for cmt in _paginate_rest(f"repos/{owner}/{repo}/issues/{pr}/comments"):
        user = (cmt.get("user") or {}).get("login") or ""
        items.append(
            EvidenceItem(
                kind="issue_comment",
                item_id=int(cmt["id"]),
                author=user,
                body=cmt.get("body") or "",
                created_at=cmt.get("created_at") or "",
                updated_at=cmt.get("updated_at") or "",
                url=cmt.get("html_url") or "",
            )
        )

    return items


def lane_candidates(
    items: Iterable[EvidenceItem], *, sha: str, lane: str
) -> list[tuple[EvidenceItem, str]]:
    """Return (item, verdict) for lane items mentioning sha with a clear verdict."""
    out: list[tuple[EvidenceItem, str]] = []
    for item in items:
        if item.author not in ALLOWED_AUTHORS:
            continue
        if is_edited(item):
            continue
        if classify_lane(item.body) != lane:
            continue
        if not whole_token_sha_present(item.body, sha):
            continue
        verdict = verdict_of(item.body)
        if verdict is None:
            continue
        out.append((item, verdict))
    return out


def latest_lane_verdict(
    items: Sequence[EvidenceItem], *, sha: str, lane: str
) -> tuple[EvidenceItem, str] | None:
    """Latest qualifying verdict for a lane, or None if none exist."""
    cands = lane_candidates(items, sha=sha, lane=lane)
    if not cands:
        return None
    cands.sort(key=lambda pair: pair[0].sort_key)
    return cands[-1]


def verify_exact_tip_lane_passes(
    items: Sequence[EvidenceItem],
    *,
    sha: str,
) -> tuple[bool, list[str]]:
    """Return (ok, messages). ok only when both lanes' latest verdict is PASS."""
    if not HEX40.match(sha):
        return False, [f"sha must be 40 lowercase hex chars, got {sha!r}"]

    messages: list[str] = []
    ok = True
    for lane, label in (
        ("copilot", "GitHub Copilot audit lane"),
        ("kiro", "Kiro"),
    ):
        latest = latest_lane_verdict(items, sha=sha, lane=lane)
        if latest is None:
            ok = False
            messages.append(f"FAIL {label}: no qualifying PASS/FAIL evidence for {sha}")
            continue
        item, verdict = latest
        loc = item.url or f"{item.kind}:{item.item_id}"
        if verdict != "PASS":
            ok = False
            messages.append(
                f"FAIL {label}: latest verdict is {verdict} ({loc})"
            )
        else:
            messages.append(f"PASS {label}: {loc}")
    return ok, messages


FetchFn = Callable[[str, str, int], list[EvidenceItem]]


def main(argv: Sequence[str] | None = None, *, fetch: FetchFn | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pr", type=int, required=True, help="Pull request number")
    parser.add_argument("--sha", required=True, help="Full 40-char reviewed head SHA")
    parser.add_argument("--owner", default="alanmz-crypto")
    parser.add_argument("--repo", default="convmem")
    args = parser.parse_args(argv)

    sha = args.sha.lower()
    if not HEX40.match(sha):
        print(f"error: --sha must be 40 hex chars, got {args.sha!r}", file=sys.stderr)
        return 2

    fetch_fn = fetch or fetch_pr_evidence
    items = fetch_fn(args.owner, args.repo, args.pr)
    ok, messages = verify_exact_tip_lane_passes(items, sha=sha)
    for line in messages:
        print(line)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Verify exact-tip dual-lane PASS evidence on a pull request.

Canonical verdict grammar only (Ryan-recorded via alanmz-crypto):

    Lane: GitHub Copilot audit lane
    Verdict: PASS
    Reviewed head: <full sha>
    Reviewed base: <full base sha>

    Lane: Kiro
    Verdict: PASS
    Reviewed head: <full sha>
    Reviewed base: <full base sha>

Incidental lane/SHA/PASS prose does not qualify. Edited comments
(updated_at != created_at) are rejected. PR reviews in PENDING or DISMISSED
state do not qualify.
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

LANE_LINE_COPILOT = re.compile(r"(?im)^\s*Lane:\s*GitHub Copilot audit lane\s*$")
LANE_LINE_KIRO = re.compile(r"(?im)^\s*Lane:\s*Kiro\s*$")
VERDICT_LINE = re.compile(r"(?im)^\s*Verdict:\s*(PASS|FAIL)\s*$")
REVIEWED_HEAD_LINE = re.compile(
    r"(?im)^\s*Reviewed head:\s*([0-9a-f]{40})\s*$"
)
REVIEWED_BASE_LINE = re.compile(
    r"(?im)^\s*Reviewed base:\s*([0-9a-f]{40})\s*$"
)

# Reviews in these states must not count as lane evidence.
REJECTED_REVIEW_STATES = frozenset({"PENDING", "DISMISSED"})


@dataclass(frozen=True)
class EvidenceMeta:
    """Timestamps + optional PR-review state (keeps EvidenceItem lean)."""

    created_at: str
    updated_at: str
    url: str = ""
    review_state: str = ""


@dataclass(frozen=True)
class EvidenceItem:
    """One review or comment that may carry lane verdict evidence."""

    kind: str
    item_id: int
    author: str
    body: str
    meta: EvidenceMeta

    @property
    def created_at(self) -> str:
        return self.meta.created_at

    @property
    def updated_at(self) -> str:
        return self.meta.updated_at

    @property
    def url(self) -> str:
        return self.meta.url

    @property
    def review_state(self) -> str:
        return self.meta.review_state

    @property
    def sort_key(self) -> tuple[str, int]:
        return (self.created_at, self.item_id)


def whole_token_sha_present(body: str, sha: str) -> bool:
    """True when sha appears as a whole hex token (not a longer hash substring)."""
    if not HEX40.match(sha):
        return False
    return bool(re.search(rf"(?i)(^|[^0-9a-f]){re.escape(sha)}([^0-9a-f]|$)", body))


def classify_lane(body: str) -> str | None:
    """Return lane name only from exact ``Lane:`` lines (not incidental prose)."""
    copilot = bool(LANE_LINE_COPILOT.search(body))
    kiro = bool(LANE_LINE_KIRO.search(body))
    if copilot and not kiro:
        return "copilot"
    if kiro and not copilot:
        return "kiro"
    return None


def verdict_of(body: str) -> str | None:
    """Return PASS/FAIL only from exact ``Verdict:`` lines (no bare tokens)."""
    matches = VERDICT_LINE.findall(body)
    if not matches:
        return None
    norms = [m.upper() for m in matches]
    if "PASS" in norms and "FAIL" in norms:
        return None
    if norms[-1] == "PASS":
        return "PASS"
    if norms[-1] == "FAIL":
        return "FAIL"
    return None


def reviewed_head_of(body: str) -> str | None:
    matches = REVIEWED_HEAD_LINE.findall(body)
    if len(matches) != 1:
        return None
    return matches[0].lower()


def reviewed_base_of(body: str) -> str | None:
    matches = REVIEWED_BASE_LINE.findall(body)
    if len(matches) != 1:
        return None
    return matches[0].lower()


def is_edited(item: EvidenceItem) -> bool:
    """True when GitHub reports an edit (updated_at differs from created_at)."""
    if not item.updated_at or not item.created_at:
        return False
    return item.updated_at != item.created_at


def review_state_ok(item: EvidenceItem) -> bool:
    """Issue/review comments OK; PR reviews must not be PENDING/DISMISSED."""
    if item.kind != "review":
        return True
    state = (item.review_state or "").upper()
    if not state:
        return False
    return state not in REJECTED_REVIEW_STATES


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
                meta=EvidenceMeta(
                    created_at=created,
                    updated_at=updated,
                    url=rev.get("html_url") or "",
                    review_state=str(rev.get("state") or ""),
                ),
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
                meta=EvidenceMeta(
                    created_at=cmt.get("created_at") or "",
                    updated_at=cmt.get("updated_at") or "",
                    url=cmt.get("html_url") or "",
                ),
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
                meta=EvidenceMeta(
                    created_at=cmt.get("created_at") or "",
                    updated_at=cmt.get("updated_at") or "",
                    url=cmt.get("html_url") or "",
                ),
            )
        )

    return items


def lane_candidates(
    items: Iterable[EvidenceItem], *, sha: str, base: str, lane: str
) -> list[tuple[EvidenceItem, str]]:
    """Return (item, verdict) for strict canonical lane items."""
    out: list[tuple[EvidenceItem, str]] = []
    for item in items:
        if item.author not in ALLOWED_AUTHORS:
            continue
        if is_edited(item):
            continue
        if not review_state_ok(item):
            continue
        if classify_lane(item.body) != lane:
            continue
        if reviewed_head_of(item.body) != sha:
            continue
        if reviewed_base_of(item.body) != base:
            continue
        verdict = verdict_of(item.body)
        if verdict is None:
            continue
        out.append((item, verdict))
    return out


def latest_lane_verdict(
    items: Sequence[EvidenceItem], *, sha: str, base: str, lane: str
) -> tuple[EvidenceItem, str] | None:
    """Latest qualifying verdict for a lane, or None if none exist."""
    cands = lane_candidates(items, sha=sha, base=base, lane=lane)
    if not cands:
        return None
    cands.sort(key=lambda pair: pair[0].sort_key)
    return cands[-1]


def verify_exact_tip_lane_passes(
    items: Sequence[EvidenceItem],
    *,
    sha: str,
    base: str,
) -> tuple[bool, list[str]]:
    """Return (ok, messages). ok only when both lanes' latest verdict is PASS."""
    if not HEX40.match(sha):
        return False, [f"sha must be 40 lowercase hex chars, got {sha!r}"]
    if not HEX40.match(base):
        return False, [f"base must be 40 lowercase hex chars, got {base!r}"]

    messages: list[str] = []
    ok = True
    for lane, label in (
        ("copilot", "GitHub Copilot audit lane"),
        ("kiro", "Kiro"),
    ):
        latest = latest_lane_verdict(items, sha=sha, base=base, lane=lane)
        if latest is None:
            ok = False
            messages.append(
                f"FAIL {label}: no qualifying PASS/FAIL evidence for "
                f"head={sha} base={base}"
            )
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
    parser.add_argument("--base", required=True, help="Full 40-char reviewed base SHA")
    parser.add_argument("--owner", default="alanmz-crypto")
    parser.add_argument("--repo", default="convmem")
    args = parser.parse_args(argv)

    sha = args.sha.lower()
    base = args.base.lower()
    if not HEX40.match(sha):
        print(f"error: --sha must be 40 hex chars, got {args.sha!r}", file=sys.stderr)
        return 2
    if not HEX40.match(base):
        print(f"error: --base must be 40 hex chars, got {args.base!r}", file=sys.stderr)
        return 2

    fetch_fn = fetch or fetch_pr_evidence
    items = fetch_fn(args.owner, args.repo, args.pr)
    ok, messages = verify_exact_tip_lane_passes(items, sha=sha, base=base)
    for line in messages:
        print(line)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())

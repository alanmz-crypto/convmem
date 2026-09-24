# ConvMem branch cleanup — report-only safety gate

**Status:** planning, not yet executed. No branch has been deleted under this policy.
**Author:** drafted across two adversarial review passes (Claude, Sonnet 5) against the
live repository state; reviewed through the [Decision and Review Guardrails](../inter-model/DECISION-REVIEW-GUARDRAILS.md)
lens, which recommended narrowing to report-generation rather than further speculative review.
**Tooling:** [`scripts/branch-cleanup-report.sh`](../../scripts/branch-cleanup-report.sh) implements §12 below.

## Objective

Reduce unnecessary remote Git branches in `alanmz-crypto/convmem` without deleting project
history, review evidence, operational state, experimental evidence, or branches that are
still meaningful to active or historical workflows. Safe reduction of clutter, not maximum
deletion. No PR history is deleted. No branch is deleted automatically.

## 1. Scope

The first cleanup pass covers **only** remote branches associated with a merged pull
request whose branch ref still exists. Never-PR'd branches and closed-but-unmerged
branches are explicitly out of scope for this pass — see §14 (Future cleanup tracks).

ConvMem deliberately contains branches representing experiments, design consensus,
negative results, review packets, paused work, superseded implementations, and evidence
that must remain distinct from `main`. An old branch that never became production code is
not thereby disposable.

## 2. Do not use branch-tip equality

Do not require `branch tip == merged PR head` as the deletion test. ConvMem squash-merges
by default (verified: 100% of a sampled merged-and-present branch set had tip ≠ merge
commit SHA), so a branch's original commit history routinely remains outside `main` even
though the logical change landed. Instead, explicitly determine: whether the PR was
merged, what merge method was used, and whether the branch contains commits that are the
only reachable copy of evidence referenced elsewhere.

## 3. Classification model

Every candidate ends in exactly one of: `DELETE_CANDIDATE`, `RETAIN`, `REVIEW_REQUIRED`.
Default is `REVIEW_REQUIRED`. Any tool error, incomplete scan, ambiguous reference,
parsing failure, or uncertainty never resolves to `DELETE_CANDIDATE`.

## 4. Mandatory exclusion gates

Immediate `RETAIN` when any applies:

- **A. No merged PR** — out of scope for this pass.
- **B. PR closed but not merged** — may hold intentionally preserved negative evidence or
  abandoned review paths (confirmed pattern: STATUS.md names draft PRs #246/#248/#249/#251
  as "closed as superseded, with their branches preserved").
- **C. Active/open PR relationship.**
- **D. Explicit current routing reference** — LATEST.md, STATUS.md,
  `docs/plans/STATUS-*.md`, active handoffs.

`REVIEW_REQUIRED` when:

- **E. Explicit preservation language** — "preserved," "branch-only," "evidence,"
  "historical reference," "experimental," "superseded but intentionally retained,"
  "required for review provenance." Never convert stated human preservation intent into an
  automated deletion decision.
- **F. Merge-target verification fails** — the PR's base ref was not `main`, or the
  merge/squash commit is not itself an ancestor of current `origin/main`. GitHub's
  `merged: true` reflects the state at merge time only; this repo permits Ryan-authorized
  force-pushes to `main` (documented precedent: the R2b `f8dfbb1 --force-with-lease` case),
  so merge status must be re-verified against the live tip, not trusted from the API alone.

## 5. Full-repository documentation scan

Do not treat LATEST.md and STATUS.md as the complete dependency graph. Search the full
corpus for every candidate: `docs/`, `docs/plans/`, `docs/inter-model/`, `docs/archive/`,
`scripts/`, config files, manifests/inventory files. A name hit is not automatically fatal
(some references are historical and non-load-bearing), but: any unresolved hit →
`REVIEW_REQUIRED`; any active/current hit → `RETAIN`; only a clearly historical,
non-load-bearing hit may remain eligible for further checks. Do not rely solely on exact
branch-name string matching.

## 6. Commit-SHA provenance scan

The most important gate for ConvMem. Because squash merges leave intermediate commits
outside `main`, extract SHA-like tokens from the documentation corpus and determine
whether any are: (1) ancestors of the candidate branch, (2) not ancestors of `main`, (3)
cited as review, evidence, provenance, negative-result, or historical-decision material.
Any such commit forces `REVIEW_REQUIRED` — a human must confirm the cited commit is
preserved elsewhere before the branch can be deleted.

*Confirmed live case:* `docs/plans/STATUS-codex-jsonl-production-integration.md` cites
`5bdc132`, `a47f32b`, `4acb4c5`, `6cb0107` as preserved review-decision commits on
`feat/2026-09-12-codex-jsonl-p2-runtime-readiness` (PR #301, squash-merged). Verified:
`5bdc132` is an ancestor of that branch and **not** an ancestor of `origin/main`. This is
exactly the case this gate exists to catch.

## 7. ConvMem ledger/corpus check

Repository-local grep is insufficient. For each candidate, search the ConvMem corpus for
the exact branch name, a distinctive slug, associated commit SHAs, the associated PR
number, and the associated arc identifier. Any substantive hit outside known historical
noise → `REVIEW_REQUIRED`. The ledger is a separate dependency layer from Git; absence
from Git-tracked Markdown does not imply absence from the ledger.

**Completeness caveat:** a clean `convmem search` result is evidence of absence, not proof.
`convmem doctor` in this repo currently reports unresolved `synthesis_gate` /
ingest-degraded warnings — projection completeness is admittedly unproven. Record this
caveat in the per-branch report; do not treat a clean ledger search as equal-confidence to
a clean grep.

## 8. Tag and arc-family protection

If a candidate belongs to a family with milestone tags, preserved experimental tags, a row
in a closed-arc status table, known review/provenance tags, or a documented preservation
convention, do not include it in the first automated batch — classify `REVIEW_REQUIRED`.
A tag proves *something* was preserved; it does not prove the tag fully captures every
branch or commit worth preserving.

*Confirmed live case:* the Claude Watch Parity arc (closed) has 6 `milestone/*` tags but
14 branches share the family's naming pattern — 8 are untagged.

## 9. Age is not a deletion criterion

Do not use "older than 7 days" as staleness evidence. Old branches here commonly represent
`BLOCKED_ON_RYAN`, `PENDING`, soak periods, or intentionally paused arcs — age correlates
with "waiting on a human," not "abandoned," in this review-gated workflow. Age is a
secondary prioritization signal only, after all safety checks pass. First batch: prefer
30+ days since merge, never age alone as sufficient.

## 10. First cleanup batch

A branch enters the first deletion batch only when **all** hold: merged PR exists; no open
PR depends on it; no current routing document references it; no active arc references it;
no preservation language applies; no SHA-citation dependency found; no meaningful ConvMem
ledger/corpus reference found; no tag/closed-arc family relationship; no ambiguity in merge
history; ≥30 days since merge; the branch is a simple, isolated historical
correction/documentation branch, not part of a complex gated arc.

Exclude from the first batch regardless of how clean the checks look: Codex / Trapdoor
work, Recovery Authority, CG-2, Shadow, R2b, OpenClaw, Claude watch/gate work,
experiments, and anything with active or historical review-provenance concerns. Review
those later as dedicated families (§14, Track E).

## 11. Mandatory pre-delete preservation

Before any deletion batch: create an external Git bundle containing the candidate branch
refs and their reachable history, stored outside the repository being cleaned. **Verify the
bundle** — clone from it into a scratch directory and confirm each candidate ref resolves
with intact history — before the batch proceeds; an unverified bundle is not a backup.

The cleanup record must include: branch name, originating PR, merge method, branch tip
SHA, merge commit SHA (if applicable), date of merge, deletion decision, checks performed,
and **Ryan's explicit approval** — no lane, agent, or automated process may substitute,
consistent with this project's existing "Ryan owns merges" convention extended to branch
deletion as a comparably destructive operation.

## 12. No automated deletion

A script may: inventory branches, identify merged-PR relationships, classify branches,
scan documentation, scan commit references, search the ConvMem corpus, identify tags,
generate a report, create the preservation bundle. A script may **not** directly delete
branches. Deletion remains human-controlled.

Example report entries (clean and flagged):

```text
BRANCH: docs/example
PR: #123   MERGED: yes   MERGE METHOD: squash   AGE: 47 days
CURRENT ROUTING: none   FULL DOC SCAN: clean   SHA PROVENANCE: clean
CONVMEM SEARCH: clean   TAG/FAMILY: none   ACTIVE ARC: none
CLASSIFICATION: DELETE_CANDIDATE
REASON: all required safety gates passed
```

```text
BRANCH: feat/2026-09-12-codex-jsonl-p2-runtime-readiness
PR: #301   MERGED: yes   MERGE METHOD: squash   AGE: 12 days
CURRENT ROUTING: none in LATEST.md/STATUS.md
FULL DOC SCAN: 4 hits in docs/plans/STATUS-codex-jsonl-production-integration.md
SHA PROVENANCE: 5bdc132 is ancestor of branch, NOT ancestor of main
  (cited as "Local Claude FAIL at preserved 5bdc132")
TAG/FAMILY: none   ACTIVE ARC: Codex — Kiro JSONL incremental production integration
CLASSIFICATION: REVIEW_REQUIRED
REASON: cited review-evidence commit unreachable from main if branch deleted
```

Anything less clean than the first example becomes `REVIEW_REQUIRED`.

## 13. Post-batch verification

After the first deletion batch: verify deleted refs are actually gone; verify `main` is
unchanged; verify all active branches remain; rerun repository knowledge/inventory checks;
rerun `convmem doctor`; rerun the relevant branch/document provenance scans; verify no
current status/handoff pointers broke; verify no previously referenced evidence became
unreachable. Do not establish a permanent auto-delete rule until at least one complete
batch has been reviewed and verified without an unexpected dependency surfacing.

## 14. Future cleanup tracks

- **Track B — closed but unmerged branches.** Human-reviewed only.
- **Track C — never-PR'd branches.** Likely the largest source of raw branch-count clutter
  (measured: 169 of 249 non-main branches have never had a PR), but categorically
  different from merged-PR cleanup. Never automatically sweep this category.
- **Track D — stale documentation.** Review whether dated documents are active,
  historical, redundant, superseded, or archival. Do not delete historical evidence merely
  because it is no longer current.
- **Track E — branch-family consolidation.** Review preserved arc families, tags, and
  experimental branches as groups, not individual branches.

## 15. Standing policy

Do not adopt "every merged branch is automatically deleted" yet. Prove the procedure
first. After one successful reviewed cycle, a narrower standing policy may follow: *merged
branches may be deleted after the PR lands when not explicitly retained, provided the
repository's provenance and preservation checks pass and Ryan approves deletion.* Merged
PRs themselves remain permanent historical records regardless.

## Final operating principle

PR history is historical truth. Current status documents are operational truth. Branches
are disposable references only when their unique provenance is no longer needed. The
governing question is not "was this branch merged?" — it is "does deleting this ref remove
the only reachable copy of anything the project still relies on?" Only when the answer is
demonstrably no does deletion become a candidate.

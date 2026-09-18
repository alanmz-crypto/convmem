# [Arc Claude Watch Parity] Handoff: Gate 1 PR decision after exact-tip PASS

**Date:** 2026-09-18
**Author:** Codex planning lane
**For:** Ryan (PR/merge decision); next agent may verify evidence but cannot merge
**Authorization:** Ryan requested a next-agent handoff. This document conveys
state; it is not a merge, Gate 2 Execute, live-source, or watch grant.

---

## Resume state

| Field | Value |
|---|---|
| **State** | `BLOCKED_ON_RYAN`: Gate 1 code review PASS reported, PR open, CI not yet all complete at this handoff. |
| **Branch** | `feat/2026-09-18-claude-transcript-adapter` |
| **Tip SHA** | `ab8a9e16ddd64aef55c301caf545f8e743fc33d8` on `origin` and PR #310 at check time. |
| **Push status** | Gate 1 branch pushed; this handoff is on `plan/2026-09-18-claude-watch-parity`. |
| **PR** | [#310 — Add Claude Code transcript adapter for on-demand indexing](https://github.com/alanmz-crypto/convmem/pull/310), open against `main`. |
| **Ryan gates** | Ryan decides Gate 1 PR merge after final checks; later, a separate bounded Gate 2 isolated Execute grant, exact-source canary grant, and production promotion decision. |
| **Track A ingest** | No successful Codex chat ingest has been confirmed for this planning session. Do not mistake this file for Track A. |

---

## What to build

No code from this handoff. The next action is to decide whether Gate 1 PR #310
may land after final CI and scope checks. Gate 1 provides explicit, on-demand
`convmem index --file` support for Claude Code sessions. It does **not** enable
automatic capture. If Ryan merges, update the arc snapshot to say the adapter
is on `main`, then decide the **separate** bounded Gate 2 Execute grant.

**Why this exists:** Kiro first found a list-form injected-context leak, then
a sibling-speech data-loss case. Cursor corrected both. Kiro's supplied
re-review reports PASS on full exact tip `ab8a9e16ddd64aef55c301caf545f8e743fc33d8`:
fully stripped or empty list blocks no longer erase ordinary sibling speech,
while unclosed injected wrappers still fail closed. That PASS is a code-review
verdict, not a merge or live-capture authorization.

---

## Integration point

PR #310 changes `adapters/claude_session_jsonl.py`, `adapters/detect.py`, and
`tests/test_claude_session_jsonl.py`. It also rebinds only revision/digest
fields in `docs/plans/R2B-V2-WRITER-COVERAGE-INVENTORY.json`; the 34 route
payloads and sink evidence are unchanged in the diff. The PR description says
Ryan authorized this generated R2b rebind after stale-identity CI failures.
Ryan should confirm that cross-arc authorization before merge.

The Gate 2 plan is
`docs/inter-model/CODEX-2026-09-18-claude-watch-parity-gate2-execute.md`.
Kiro PASSed it at reviewed plan tip `a811f58` with four Execute conditions;
its text remains unchanged on the planning branch.

---

## Specification

### Inputs

- Fetch `origin`; verify PR #310 still points to the reviewed full SHA and
  `origin/main` still lacks or has not already merged the adapter.
- Check **final** PR status and required CI. At this handoff, CodeQL, both
  Analyze jobs, pylint, and secret-scan passed; `pytest (3.12)` was pending.
  `mergeStateStatus` was `BLOCKED`, with `mergeable=MERGEABLE` and no GitHub
  review object. Do not treat those snapshots as final.
- Use Kiro's exact-tip review report supplied to Ryan as the code verdict.
  The earlier Gate 1 decision brief reviewed the **spec**, not this code.

### Decision sequence

1. Confirm CI finishes green on the same reviewed SHA and no new commit has
   moved the PR tip. A new tip requires a new exact-tip review decision.
2. Confirm the adapter remains on-demand only: no `[sources].paths`,
   `[watch].extra_paths`, `KIRO_ROUTE_FORMATS`, `incremental_jsonl.py`, watcher,
   or Arc Codex change. Review the R2b inventory rebind as an explicitly
   authorized cross-arc metadata update, not as hidden Claude implementation.
3. Ryan decides whether to squash-merge PR #310. The PR body says squash is OK.
   Agents do not merge or convert this handoff into a PR Steward grant.
4. After merge, verify the merged adapter and update
   `docs/plans/STATUS-claude-watch-parity.md` and `docs/inter-model/LATEST.md`
   from the *actual* `main` state. Ryan may then separately decide whether to
   grant Cursor bounded isolated Gate 2 Execute against the reviewed plan.

### Output / contract

A Ryan merge/no-merge decision with the final PR tip and CI result recorded.
If merged, the next Cursor handoff must start from the merged, Kiro-reviewed
Gate 1 mapper—not PR #310's in-flight tree—and preserve the four Gate 2 review
conditions: shared `CONVMEM_INCREMENTAL_ROOT` isolation assertions; unchanged
Kiro/Codex behavior and Kiro-only default route; live canary `NOT_RUN` without
an exact grant and safe watcher state; production-code diff confined to the
Claude adapter and `incremental_jsonl_formats.py`.

---

## What NOT to build or run

- No Gate 2 implementation from Gate 1 PASS or merge alone.
- No live Claude transcript read, paid `index --file` smoke, canary, service
  stop, production corpus mutation, or watcher/source wiring without its own
  named grant. `convmem brief` showed watch enabled/active at handoff.
- No Claude addition to `KIRO_ROUTE_FORMATS` or production source paths.
- Do not call Gate 2 “auto-capture”: this next Execute is an **isolated
  incremental route**. Automatic watch capture is a later promotion decision.

---

## Test expectations

Kiro reported, at `ab8a9e16`, two new regressions passing, the full Claude
adapter suite 18/18, R2b binding tests 35/35, and pylint 10.00/10. These are
review evidence, not a substitute for the PR's final required CI. Do not run
a real transcript smoke merely to close a test checkbox; the initial spec's
real-source acceptance case remains separately bounded.

---

## Acceptance criteria

- [ ] PR #310 is still at exact reviewed tip `ab8a9e16` when Ryan decides.
- [ ] Required CI is green, including the formerly pending pytest job.
- [ ] Ryan confirms the cross-arc R2b inventory rebind and decides merge.
- [ ] If merged, the STATUS/LATEST snapshot reflects the actual `main` tip.
- [ ] Gate 2 Execute, live-source canary, and production watch promotion remain
      separate Ryan decisions.

---

## Branch convention

Gate 1 implementation is on `feat/2026-09-18-claude-transcript-adapter`;
this handoff is on `plan/2026-09-18-claude-watch-parity`. Do not switch the
contested shared checkout; use its existing dedicated worktrees. Agents push
their own commits immediately with an explicit refspec. Ryan owns merge.

---

## Related files

| What | Path |
|---|---|
| Arc current-state brief | `docs/plans/STATUS-claude-watch-parity.md` |
| Gate 1 decision/spec | `docs/inter-model/KIRO-2026-09-18-claude-transcript-corpus-decision-brief.md` and `docs/inter-model/CURSOR-2026-09-17-claude-transcript-adapter-handoff.md` on `origin/main` |
| Gate 2 reviewed plan | `docs/inter-model/CODEX-2026-09-18-claude-watch-parity-gate2-execute.md` |
| Current routing pointer | `docs/inter-model/LATEST.md` |

---

## Leaving / picking up checklist

**Codex (leaving):** commit this handoff with the updated STATUS and LATEST
pointer; push the planning branch; report its tip and Track A outcome.

**Next lane (picking up):** Ryan verifies final PR state and decides merge.
After merge, a docs agent updates the snapshot; Cursor starts Gate 2 only
after a separate bounded Execute grant.

**TL;DR [Arc Claude Watch Parity]:** Kiro reports exact-tip Gate 1 PASS and PR
#310 is open. Ryan waits for final green CI, confirms the R2b metadata rebind,
then decides merge. Gate 2 and live capture are not authorized by this handoff.

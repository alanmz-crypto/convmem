# [Arc Claude Watch Parity] Handoff: Gate 1 adapter review before Gate 2 Execute

**Date:** 2026-09-18
**Author:** Codex planning lane
**For:** Kiro design/code-review lane; then Ryan for merge and Execute decisions
**Authorization:** Ryan requested this next-agent handoff on 2026-09-18. The
Gate 1 adapter-only decision and Gate 2 plan review do not authorize live
capture, production promotion, or a Gate 2 implementation start.

---

## Resume state

| Field | Value |
|---|---|
| **State** | `READY_FOR_KIRO_REVIEW` for Gate 1 code; Gate 2 implementation is blocked on Gate 1 review/merge and a Ryan bounded Execute grant. |
| **Review branch** | `feat/2026-09-18-claude-transcript-adapter` |
| **Exact review tip** | `cbdc88b81b4f64cacfaffd7bc2f78078bd58dfd1` (verify after fetch). Its merge base with `origin/main` was `63cd3bcd0fa06a39a79ed48c89a3b20457ae09c8` at handoff. |
| **Push status** | Gate 1 branch pushed to `origin`; this handoff is on `plan/2026-09-18-claude-watch-parity` and must be pushed with its commit. |
| **PR** | No Gate 1 PR found by `gh pr list --head feat/2026-09-18-claude-transcript-adapter --state all` at handoff. |
| **Ryan gates** | Ryan owns PR/merge disposition, then a bounded Gate 2 Execute grant; an exact live-source canary grant and production watch promotion are later, separate decisions. |
| **Track A ingest** | Codex session transcript indexing remains unconfirmed; the prior `convmem index --file` attempt stalled and was interrupted. Do not infer a successful Track A from this document. |

---

## What to build

No code in this handoff. Kiro should give a written `PASS` or specific
conditions on the **exact Gate 1 adapter tip** before Ryan considers landing it.
Gate 1 makes explicit `convmem index --file <Claude session>` work on demand;
Gate 2 later tests incremental append reuse under isolation. The adapter must
not turn Claude transcripts into an automatic watch source.

**Why this exists:** Gate 2's reviewed plan requires a merged, Kiro-reviewed
Gate 1 mapper. The adapter is available on a remote branch but absent from
`origin/main`; no PR or written code verdict was found at this handoff. Sending
Cursor into Gate 2 now would build on an unreviewed contract.

---

## Integration point

Review the three-file Gate 1 diff against its current-main merge base:

- `adapters/claude_session_jsonl.py` — format detection and canonical message
  mapping, including injected-context hygiene.
- `adapters/detect.py` — `jsonl_claude_session` registration and classification
  order without stealing neighboring formats.
- `tests/test_claude_session_jsonl.py` — hermetic cases for the adapter contract.

The Gate 1 implementation spec and Kiro's earlier **spec-only** sign-off are
on `origin/main` as
`docs/inter-model/CURSOR-2026-09-17-claude-transcript-adapter-handoff.md` and
`docs/inter-model/KIRO-2026-09-18-claude-transcript-corpus-decision-brief.md`.
They are not present in this planning branch's older base. The Gate 2 plan is
`docs/inter-model/CODEX-2026-09-18-claude-watch-parity-gate2-execute.md`;
Kiro PASSed that plan at `a811f58`, not the Gate 1 code.

---

## Specification

### Inputs

- Fetch `origin`; pin the review to `cbdc88b81b4f64cacfaffd7bc2f78078bd58dfd1`.
- Read the Gate 1 spec and decision brief on `origin/main`, plus the arc brief.
- Inspect `git diff 63cd3bc..cbdc88b -- adapters/claude_session_jsonl.py adapters/detect.py tests/test_claude_session_jsonl.py`.
- Use fixture tests only. No live Claude transcript, production index, watcher,
  config, provider, or corpus mutation is needed for this review.

### Review behavior

1. Verify detection is constrained to Claude's `.claude/projects` shape and
   that existing Cursor, Codex, Kiro, and Copilot classification stays intact.
2. Verify the canonical mapper emits only user/assistant text, keeps timestamp,
   session id, and workspace, and drops blank results.
3. Verify `isSidechain` messages, non-message records, assistant `thinking`,
   `tool_use`, and `tool_result` are excluded.
4. Verify `<system-reminder>` content (including injected `CLAUDE.md`) and
   local-command wrappers **and their contents** are stripped, including
   repeated/multiline cases, without deleting ordinary surrounding speech.
5. Verify malformed JSON tolerance and test isolation. The acceptance test in
   the old spec proposes indexing a real transcript, but that is **not** part
   of this review grant; do not run it to obtain a PASS.
6. State the exact reviewed SHA, tests run, and either `PASS` or concrete
   conditions/failures. If a fix is needed, return it to Cursor and review the
   resulting new tip; a spec-only PASS cannot substitute for code review.

### Output / contract

A written Gate 1 code-review verdict on an exact pushed revision, with enough
detail for Ryan to decide PR/merge disposition. Once Gate 1 lands, Cursor must
recheck the merged mapper before its first Gate 2 edit and use that same mapper
for `parse()` and `parse_complete_prefix()`.

---

## What NOT to build or run

- Kiro does not edit code, tests, scripts, config, or generated surfaces.
- Do not add Claude to `[sources].paths`, `[watch].extra_paths`, or
  `KIRO_ROUTE_FORMATS`; do not change `incremental_jsonl.py` or Arc Codex files.
- Do not run a live-source canary or stop the active watcher. Keep it `NOT_RUN`
  until Ryan grants one exact source and a safe inactive-watcher window.
- Do not treat Kiro's Gate 2 plan PASS as Gate 1 code PASS, a bounded Execute
  grant, permission to open/merge a PR, or permission to promote production
  routing.

---

## Test expectations

Kiro may run the focused `tests/test_claude_session_jsonl.py` suite and existing
neighboring adapter tests against the exact branch in a separate worktree.
Review the tests' assertions, not only their exit status. Gate 2's future
VERIFY must assert the shared `CONVMEM_INCREMENTAL_ROOT` isolated union
(Kiro+Codex+Claude), Kiro-only default routing, unchanged Kiro/Codex behavior,
and a static production-code diff limited to the Claude adapter and
`incremental_jsonl_formats.py`.

---

## Acceptance criteria

- [ ] Kiro records a code-review verdict on exact Gate 1 tip `cbdc88b` or a
      clearly identified successor, with hygiene/classification evidence.
- [ ] If conditions are raised, Cursor corrects them and Kiro reviews the new
      exact tip; Ryan decides the PR and merge path.
- [ ] Gate 1 is merged before Cursor begins Gate 2, and Ryan separately grants
      bounded isolated Execute against the Kiro-PASSed Gate 2 plan.
- [ ] Live canary remains `NOT_RUN`; no watch/source routing or production
      configuration changes are inferred from this handoff.

---

## Branch convention

The Gate 1 implementation branch is
`feat/2026-09-18-claude-transcript-adapter`; this handoff lives on
`plan/2026-09-18-claude-watch-parity`. Review in a separate worktree if the
shared checkout is contested. Push immediately after each commit with an
explicit branch refspec. Agents do not merge; Ryan owns that decision.

---

## Related files

| What | Path |
|---|---|
| Arc current-state brief | `docs/plans/STATUS-claude-watch-parity.md` |
| Gate 1 adapter specification (on `origin/main`) | `docs/inter-model/CURSOR-2026-09-17-claude-transcript-adapter-handoff.md` |
| Gate 1 decision and spec review (on `origin/main`) | `docs/inter-model/KIRO-2026-09-18-claude-transcript-corpus-decision-brief.md` |
| Kiro-PASSed Gate 2 plan (reviewed at `a811f58`) | `docs/inter-model/CODEX-2026-09-18-claude-watch-parity-gate2-execute.md` |
| Current routing pointer | `docs/inter-model/LATEST.md` |

---

## Leaving / picking up checklist

**Codex (leaving):**

- [ ] Commit this handoff, current-state STATUS, and top `LATEST.md` pointer.
- [ ] Push `plan/2026-09-18-claude-watch-parity` immediately; report the tip.
- [ ] Nudge Track A session indexing, report actual outcome without claiming
      success if it stalls.

**Kiro (picking up):**

- [ ] Run session-start checks and read the arc brief before review.
- [ ] Fetch and verify the exact Gate 1 tip and current-main merge base.
- [ ] Return a written exact-tip `PASS` or specific conditions; do not implement.
- [ ] Hand the verdict to Ryan for PR/merge and later Execute decisions.

**TL;DR [Arc Claude Watch Parity]:** Review the pushed Gate 1 adapter at
`cbdc88b` first. Gate 2 implementation waits for Gate 1 review and merge plus
Ryan's bounded Execute grant; live canary and watch promotion remain separate.

# Handoff: Bounded-autonomy execution-plan review R3

**Date:** 2026-07-12
**From:** Ryan + Codex
**To:** Claude Cloud
**Purpose:** Perform a narrow operational review of the new execution plan. The architecture passed Claude R2; verify that the runbook faithfully executes it without re-opening accepted architecture or citations. **No code edits, runtime activation, merges, records, or external writes.**

## Read order

1. `EXECUTION-token-efficient-bounded-autonomy.md`
2. `ARCHITECTURE-token-efficient-bounded-autonomy.md` only to check fidelity

No builder-reference or charter re-audit is requested. R2 already accepted the architecture and its corrections.

## New material under review

The execution plan adds:

- Stage 0 prerequisites and phrasebook-branch dependency.
- A live-task selection filter for three Cursor tasks.
- A paste-ready bounded-autonomy launch contract.
- A required completion-report schema.
- Task 3 positive retrieval evidence.
- Separate autonomy and coordination verdict handling.
- Two read-only external-authorization probes.
- A one-time Codex promotion-review prompt.
- Ryan's promotion decision matrix.
- Stage 2 opt-in protocol implementation with a 100-word target and 130-word review ceiling.
- Stage 3 verification that the default remains convmem-only.
- Stage 4 context compression explicitly deferred.

## Questions for Claude

1. Does the execution plan faithfully implement every blocking R2 correction?
2. Could any step accidentally activate bounded autonomy globally or authorize external/client mutation before its promotion gate?
3. Are the task-selection filter and per-task loop sufficient for Cursor without creating unnecessary Ryan work?
4. Do the completion report, Task 3 rules, and verdict matrix preserve the autonomy/coordination separation?
5. Are the two probe prompts safe and diagnostically useful as written?
6. Does the Stage 2 word budget have a clear rationale and avoid duplicated standing context?
7. Is any execution blocker present before Ryan merges the plan and Cursor selects Task 1?

## Expected output

Return concise Markdown only:

1. **R3 verdict:** execution-ready or blocked.
2. **Operational fidelity:** pass/fail for questions 1–6.
3. **Blocking edits:** quote only the smallest necessary replacement text.
4. **Non-blocking advice:** at most two items.

Do not repeat the architecture summary, citation review, or generic token/safety discussion. Do not propose new infrastructure unless a blocker cannot be fixed in the existing runbook.

## Claude prompt

> Perform a narrow R3 operational review. Read the execution plan first and consult the accepted architecture only for fidelity. Check task selection, Cursor sequencing, completion evidence, separate fitness verdicts, read-only probes, Ryan's promotion matrix, and the Stage 2 compact-protocol rollout. Identify only execution blockers or material token waste introduced by the runbook. Return a concise execution-ready verdict or the smallest blocking edits. Markdown only; no code, runtime activation, merge, record, or external writes.

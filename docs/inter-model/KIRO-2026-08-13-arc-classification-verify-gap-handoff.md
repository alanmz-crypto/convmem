# Implementation Handoff: Close the arc-classification gap in Verify Planning

**Date:** 2026-08-13  
**Author:** Kiro (design review)  
**For:** Codex (architecture planning)  
**Authorization:** Ryan, 2026-08-13 (verbal: "please check and give a handoff to codex to plan to fix the problem")

---

## Resume state

| Field | Value |
|-------|--------|
| **State** | `NOT_STARTED` |
| **Branch** | `docs/2026-08-13-arc-classification-verify-gap` |
| **Tip SHA** | (this commit) |
| **Push status** | pushed to origin |
| **PR** | not opened |
| **Ryan GATE** | Codex must produce ARCHITECTURE plan; Ryan approves before Execute |
| **Track A ingest** | Kiro session — indexed at handoff |

---

## What to build

A mechanical gate that forces explicit arc-or-not classification at task intake, so that multi-session work cannot silently bypass the Verify Planning phase.

**Why this exists:** The worktree cleanup (Pass 1-3+) received three rounds of plan review but zero post-implementation verification. Investigation reveals the `VERIFY-PLANNING.md` system is intact and well-designed — but it only fires for declared arcs. The worktree cleanup was never classified as an arc, so it fell through to the `non-arc or exempt` branch and skipped Verify entirely. This is a classification gap, not a verification system gap.

**The structural problem:** `PLANNING-PROTOCOL.md` workflow diagram has:

```
Execute Task → HITL Review → (arc?) → Verify Planning
                             ↓ non-arc
                      Revise Planning
```

The "is this an arc?" decision is informal and implicit. Nothing forces it to be asked. Multi-session work with irreversibility risk, evidence dependencies, and hard stop conditions (like worktree cleanup) slips through without anyone noticing VERIFY doesn't apply.

---

## Integration point

`docs/planning/EXECUTE-TASK.md` — Step 0 (Intake), and/or a new section in `PLANNING-PROTOCOL.md` workflow.

The classification could also live as a `convmem doctor` check (advisory) that warns when a branch has >N commits or >N days without a VERIFY stub.

---

## Specification

### The gap (precise)

1. `VERIFY-PLANNING.md` requires entry "after Execute Task + HITL review for an **arc**."
2. Arc is defined as: "work tracked by an `ARCHITECTURE-*` and/or `EXECUTION-*` plan, or a multi-PR milestone Ryan names an arc."
3. The worktree cleanup has no ARCHITECTURE/EXECUTION plan and Ryan never explicitly named it an arc.
4. Therefore VERIFY never triggers — by design, not by error.
5. But the work clearly *should* have post-implementation verification (irreversible actions, evidence dependencies, multi-session scope).

### What Codex should design (not prescriptive — Codex owns architecture)

Possible approaches (Codex picks one or invents something better):

**Option A — Explicit intake classification:**  
Add a required field to Execute Task Step 0 (Intake): `arc_classification: arc | non-arc | deferred`. If `arc`, a VERIFY stub must exist before step 7 (handoff). If `deferred`, the classification must be revisited after N commits or N sessions.

**Option B — Heuristic doctor check:**  
A `convmem doctor` advisory that warns: "Branch X has >3 commits across >2 sessions with no VERIFY stub — classify as arc or record exemption." This is weaker (advisory, not blocking) but zero-friction.

**Option C — Scope-escalation trigger:**  
Define objective criteria (multi-session, irreversible operations, evidence dependencies, >5 commits, explicit stop conditions) that auto-escalate to arc status. When any two criteria are met, the protocol requires a VERIFY stub or an explicit Ryan waiver.

### Output / contract

- A change to the planning protocol docs that closes the classification gap
- Mechanical enforcement (doctor check, intake field, or both)
- The worktree cleanup specifically: either retroactively classified as arc (gets a VERIFY stub) or explicitly exempted by Ryan with documented reason

---

## What NOT to build

- Do not rewrite VERIFY-PLANNING.md — it works correctly for declared arcs
- Do not add VERIFY requirements to truly trivial work (single-commit typos, drive-by docs)
- Do not build automation that creates VERIFY stubs without human intent
- Do not change the arc definition itself — extend the *classification mechanism*
- Do not implement code — this is a protocol/docs change (Codex plans, Ryan approves)

---

## Test expectations

1. **Worktree cleanup retroactive:** After the fix, someone should be able to look at the worktree cleanup and know whether it needs VERIFY or has an exemption. Currently neither is true.
2. **Future multi-session work:** Next time a task spans >2 sessions, the classification question must be visibly asked (in intake, in doctor output, or in the handoff).
3. **No false positives on trivial work:** A single-commit doc fix should not trigger arc-classification bureaucracy.

---

## Acceptance criteria

- [ ] The "is this an arc?" decision is explicit and recorded (not implicit/skipped)
- [ ] Multi-session work with irreversibility risk cannot silently bypass VERIFY
- [ ] Trivial single-commit work is not burdened
- [ ] The worktree cleanup is retroactively classified (arc or exempted)
- [ ] Doctor or protocol mechanically surfaces the gap (advisory or blocking)
- [ ] No regression in existing VERIFY workflow for already-declared arcs

---

## Branch convention

```
docs/2026-08-13-arc-classification-verify-gap   (this handoff)
→ Codex: plan/YYYY-MM-DD-arc-classification-gate  (architecture)
→ Cursor: feat/YYYY-MM-DD-arc-classification-gate (implementation, if code)
```

Push immediately after each commit. Open PR when acceptance criteria pass. Ryan squash-merges unless PR says **Do not squash**.

---

## Related files

| What | Path |
|------|------|
| Planning Protocol (workflow diagram) | `docs/PLANNING-PROTOCOL.md` |
| Verify Planning (the gate that should fire) | `docs/planning/VERIFY-PLANNING.md` |
| Execute Task (intake step 0) | `docs/planning/EXECUTE-TASK.md` |
| VERIFY template | `docs/plans/VERIFY-TEMPLATE.md` |
| Doctor checks (potential enforcement point) | `convmem_doctor.py` |
| Planning Guide Contract | `docs/planning/CONTRACT.md` |
| Example: worktree cleanup (the case that slipped through) | This session's review thread |

---

## Leaving / picking up checklist

**Author (leaving):**

- [x] This file committed (or on pushed branch)
- [ ] `LATEST.md` bullet at top with link and resume state
- [ ] `STATUS-*.md` Update Log line — N/A (no STATUS file for this; too small for its own arc)
- [ ] Branch pushed

**Implementer (picking up):**

- [ ] Read this file before first edit
- [ ] `convmem work resume <branch>` or start from branch convention
- [ ] Codex: produce ARCHITECTURE plan; Ryan approves before Execute

<!-- Canonical source: Kiro review session 2026-08-13. Ryan identified the gap ("we've been verifying plans but not the final work"). -->

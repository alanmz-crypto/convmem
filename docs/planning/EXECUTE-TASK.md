# Execute Task

Answers: **How do I implement an approved task with evidence and a clean handoff?**

---

## Phase Initialization

| Field | Value |
|-------|-------|
| **Phase** | Execute Task |
| **Characters** | Implementer, Test-First Reviewer |
| **Functions** | Implementer |
| **Lanes** | Cursor (Tier A active); Codex only if Ryan requests independent audit after handoff |
| **Engineering References** | [`builder-reference.md`](../builder-reference.md) when touching infra |
| **Probe Version** | v1 |
| **Exit Condition** | Scoped change verified; evidence table complete; handoff nudge issued |
| **Authority** | HITL-approved task or Ryan-directed waiver |

Only after initialization may implementation begin.

---

## Objective

Execute an HITL-approved task with minimal scope: confirm context, make the
change, verify with evidence, hand off for review — then stop.

Enter after **Execution Planning + HITL approval**, or when Ryan directs
ad-hoc execution with an explicit scope waiver.

---

## Responsibilities

### Planning Status (emit at start)

```
Planning Status

Phase:        Execute Task
Characters:   Implementer, Test-First Reviewer
Functions:    Implementer
Lanes:        Cursor
Authority:    HITL-approved task or Ryan-directed waiver
```

Start authority = approved to execute. End authority = await review at HITL
stop below.

### When to enter

- After Execution Planning and HITL approval (normal loop)
- Ryan explicitly waves planning and names scope (document the waiver in the
  evidence table)
- **Not** for plan revision (→ [`REVISE-PLANNING.md`](REVISE-PLANNING.md)) or
  greenfield design (→ ARCHITECTURE stub / builder-reference)

### Required inputs

| Input | Why |
|-------|-----|
| Approved task or plan artifact | Scope boundary |
| `git status` / branch name / `main` diff baseline | Branch reality |
| Active phase guide = this file | Precedence |
| [`AGENT-ROLES.md`](../AGENT-ROLES.md) + [`agent-protocol.md`](../../config/agent-protocol.md) | Lane must-nots; handoff ≠ record |

Optional when relevant: `convmem doctor`, `convmem brief`, `convmem "query"`
(history/architecture grounding per protocol).

### Implementation loop (ordered)

| Step | Name | Actions |
|------|------|---------|
| **0** | **Intake** | Restate task in one sentence; list in-scope / out-of-scope; confirm HITL approval or Ryan waiver |
| **1** | **Inspect branch & files** | `git status`, branch vs `main`, read touched files + callers; for bugs: reproduce or confirm symptom before editing |
| **2** | **Scoped change** | Minimal diff; match repo conventions; no drive-by refactors; respect charter must-nots (no ledger writes, no client WP mixed with convmem infra) |
| **3** | **Verify** | Run task-appropriate gates (see table below); adopt **Test-First Reviewer** — would an adversarial pass accept this? |
| **4** | **Collect evidence** | PASS/FAIL/DEFERRED table with exit codes, command output one-liners, `file:line` for claims |
| **5** | **Handoff** | Nudge Track A: `convmem index --file <session-transcript>`; **no** `convmem record` unless Ryan says record block / closing |
| **6** | **HITL stop** | Exit criteria below; do not self-advance to Revise or Architecture |

### Verification routes (interim — not Verify OS)

Link only; no new subsystem.

| Situation | Route |
|-----------|-------|
| Default convmem change | `pytest -q`; `convmem doctor`; `convmem doctor --v1` when infra touched |
| Shipped-work independent check | [`CODEX-DEEPSEEK-VERIFY.md`](../CODEX-DEEPSEEK-VERIFY.md) |
| Bug discovery (upstream) | [`TEAM-CHARTER`](../inter-model/TEAM-CHARTER-2026-07-06.md) — Crush lane; Execute implements after approval |
| Active failure / debug | [`zeller-builder-digest.md`](../builder-reference/zeller-builder-digest.md); doctor output |
| Client site promote | [`site-reference/NOTES.md`](../site-reference/NOTES.md) |
| Surface soaks (when cited) | [`VERIFICATION-MATRIX.md`](../inter-model/VERIFICATION-MATRIX.md) |
| Post-execute plan cleanup | [`REVISE-PLANNING.md`](REVISE-PLANNING.md) |
| Optional post-handoff audit | Codex — **only if Ryan requests**; not part of active execution |

### Awareness (read-only context)

- [`TEAM-CHARTER-2026-07-06.md`](../inter-model/TEAM-CHARTER-2026-07-06.md) — implementer must-nots
- [`MODEL-WORKFLOW.md`](../MODEL-WORKFLOW.md) — repo-specific routes (lab vs prod vs client)
- [`SESSION-CLOSE-RECORD.md`](../inter-model/SESSION-CLOSE-RECORD.md) — record block format (Ryan runs approve-last)

### Outputs

- Code/doc change (scoped)
- Evidence table (verification stamp)
- Handoff nudge (Track A path); Track B only if Ryan requested a log file
- **No** merge, **no** `convmem record`, **no** new `logs/*.md` unless Ryan asked

---

## Exit Criteria

This phase ends when:

- [ ] Four invariant questions answered (from [`PLANNING-PROTOCOL.md`](../PLANNING-PROTOCOL.md#four-question-invariant)):
  1. Where am I? → Phase
  2. How should I think? → Character
  3. What function am I performing? → Function
  4. What standards apply? → builder-reference
- [ ] Task scope restated; out-of-scope items explicitly deferred
- [ ] Branch/files inspected; bug repro confirmed or N/A documented
- [ ] Change is minimal and matches conventions
- [ ] Verification gates run; evidence table complete (PASS/FAIL/DEFERRED)
- [ ] Handoff nudge issued (Track A); handoff ≠ record stated
- [ ] No self-transition to Revise / Architecture / merge
- [ ] No `convmem record` unless Ryan asks

Cursor must stop here. Await HITL.

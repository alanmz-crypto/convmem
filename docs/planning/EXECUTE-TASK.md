# Execute Task

Answers: **How do I implement an approved task — including an approved active-failure or bug-fix — with evidence and a clean handoff?**

---

## Phase Initialization

| Field | Value |
|-------|-------|
| **Phase** | Execute Task |
| **Characters** | Implementer, Test-First Reviewer, Debug Investigator (active failure branch only) |
| **Functions** | Implementer |
| **Lanes** | Cursor (Tier A implementation); Codex is upstream planner, not default post-handoff auditor; PR Steward requires separate Ryan grant |
| **Engineering References** | [`builder-reference.md`](../builder-reference.md) when touching infra |
| **Probe Version** | v2 |
| **Exit Condition** | Scoped change verified; evidence table complete; handoff nudge issued |
| **Authority** | HITL-approved task or Ryan-directed waiver |

Only after initialization may implementation begin.

---

## Objective

Execute an HITL-approved task with minimal scope: confirm context, make the
change, verify with evidence, hand off for review — then stop.

Enter after **Execution Planning + HITL approval**, or when Ryan directs
ad-hoc execution with an explicit scope waiver.

This guide supports **normal implementation** and **approved active-failure/debug
execution** (§Active failure branch). It is execution discipline, not Verify OS
([`VERIFY-PLANNING.md`](VERIFY-PLANNING.md)). For an **arc**, the handoff must
name `docs/plans/VERIFY-<slug>.md` (create a stub from
[`../plans/VERIFY-TEMPLATE.md`](../plans/VERIFY-TEMPLATE.md) if missing) before
claiming merge-ready closeout. It does not authorize greenfield bug discovery —
that stays upstream (Crush / [`TEAM-CHARTER`](../inter-model/TEAM-CHARTER-2026-07-06.md)).

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

When active failure branch: add `Debug Investigator` to Characters line in
emitted status.

Start authority = approved to execute. End authority = await review at HITL
stop below.

### When to enter

- After Execution Planning and HITL approval (normal loop)
- Ryan explicitly waves planning and names scope (document the waiver in the
  evidence table)
- Approved **bug-fix** task (post Crush discovery + HITL)
- Ryan-directed **active failure** investigation with named scope
- **Not** greenfield bug discovery without approval (→ [`TEAM-CHARTER`](../inter-model/TEAM-CHARTER-2026-07-06.md) / Crush lane)
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
| **2** | **Scoped change** | Minimal diff; match repo conventions; no drive-by refactors; respect charter must-nots (no ledger writes, no client WP mixed with convmem infra). If a material scope, architecture, authorization, security, or public-contract mismatch with the approved plan appears, stop and return it to Ryan/Codex — do not silently replan or broaden scope. |
| **3** | **External Review** | Decide BugBot applicability; for required changes, obtain PR-native evidence for the subject tip and dispose every finding (§External Review gate) |
| **4** | **Verify** | Run task-appropriate gates (see table below); adopt **Test-First Reviewer** — would an adversarial pass accept this? |
| **5** | **Collect evidence** | PASS/FAIL/DEFERRED table with exit codes, command output one-liners, `file:line` for claims; include the External Review evidence row |
| **6** | **Handoff** | Nudge Track A: `convmem index --file <session-transcript>`; **no** `convmem record` unless Ryan says record block / closing |
| **7** | **HITL stop** | Exit criteria below; do not self-advance to Revise or Architecture |

D3–D6 of the active failure branch rejoin the standard implementation loop
where noted.

### External Review gate

Execute owns BugBot applicability. Verify OS confirms the recorded decision and
PR evidence; it does not decide applicability after implementation.

**Universal terms:**

- **Subject tip SHA** — the commit being accepted or handed off.
- **BugBot-reviewed SHA** — the commit BugBot evaluated.

Do not use ambiguous “current head SHA” wording unless the sentence immediately
binds it to one of these terms.

#### Applicability

BugBot is **required** when a pull request includes runtime or
correctness-affecting changes involving executable code; control flow or error
handling; persistence, schema, or API behavior; concurrency or state; security,
authentication, or input validation; or a bug fix, feature, or nontrivial
refactor.

BugBot is **exempt**, with a reason recorded in evidence, for:

- docs, plans, charter, or register-only diffs;
- comments or formatting-only diffs; and
- rename-only changes whose diff changes only paths or identifier tokens plus
  rename metadata, with no behavior-bearing literals, expressions, control
  flow, defaults, schema, or API payloads.

When unsure, the gate is required.

#### Satisfaction and tip changes

For an applicable change, publish the candidate subject tip under the task's
authorized PR lifecycle before requesting merge review. The gate is satisfied
only when visible GitHub PR BugBot evidence exists whose associated
**BugBot-reviewed SHA equals the subject tip SHA**. “Ensure BugBot has
completed” is not evidence.

`/review-bugbot` before push may front-load review for an identical diff, but it
does not satisfy the gate unless PR-native evidence is associated with the
subject tip SHA. A copied local report never satisfies the gate.

Any subject-tip SHA change after BugBot review requires a new result whose
BugBot-reviewed SHA equals the new subject-tip SHA. There is no materiality
judgment. A new tip that independently qualifies for the docs, rename, or
formatting exemption may instead record a fresh exemption and reason. When
unsure, rerun BugBot.

Posting `bugbot run`, `cursor review`, or equivalent text is a GitHub comment.
Post it only under standing comment authority or exact-brief `Authorized
external changes` naming the PR, operation, and comment text. Branch-push or PR
authority does not imply comment authority. Without comment authority, record
the blocked-trigger reason and stop.

#### Finding lifecycle

| Disposition | Meaning | Required evidence |
|-------------|---------|-------------------|
| **clean** | No open findings on the accepted tip | PR-native evidence for the subject tip shows no unresolved findings |
| **fixed** | A finding was addressed | BugBot evidence for the accepted subject tip no longer reports it, or rare Ryan tip-acceptance during outage |
| **Ryan accepted** | An unresolved finding may remain | Ryan's written acceptance names the finding and subject tip SHA |

A later commit alone does not dispose a finding. “Fixed” is bound to BugBot
evidence for the accepted tip.

If BugBot is unreachable, do not agent-exempt. Record what was attempted, the
subject tip SHA, and when; then stop and escalate to Ryan. Only Ryan's written,
tip-specific acceptance can satisfy the gate during an outage.

BugBot and the GitHub Copilot audit lane are independent and non-substituting.
When both apply, they may run in parallel once a tip exists, but each gate needs
its own evidence and disposition before merge readiness.

#### Minimum evidence row

| Field | Allowed value or purpose |
|-------|--------------------------|
| `gate_applicability` | `required` or `exempt` |
| `reason` | Why the gate is required or exempt |
| `subject_tip_sha` | Commit being accepted |
| `bugbot_reviewed_sha` | SHA BugBot evaluated; `n/a` when exempt or accepted during outage without a run |
| `result` | `clean`, `findings`, `unreachable`, or `n/a` |
| `finding_disposition` | Per finding: `fixed`, `ryan_accepted`, or `none` |
| `authority_reference` | Ryan acceptance, comment authority, or `n/a` |

### Active failure branch (ordered)

Use when an approved bug-fix or Ryan-directed active failure investigation
applies. Adopt **Debug Investigator** reasoning (see
[`reasoning-modes.md`](../reasoning-modes.md)).

| Step | Name | Actions |
|------|------|---------|
| **D0** | **Capture symptom** | Command, exit code, surface, env; minimal bug-report fields per [`zeller-builder-digest.md`](../builder-reference/zeller-builder-digest.md) |
| **D1** | **Reproduce** | Smallest repro; if not reproducible, document and **stop** — do not guess at fix |
| **D2** | **Isolate** | Remove irrelevant state; compare pass vs fail runs |
| **D3** | **Hypothesis → scoped change** | Join main loop step 2; minimal diff only |
| **D4** | **Verify against repro** | Original failure must be gone before regression gates |
| **D5** | **Regression gates** | `pytest -q`, `convmem doctor`, task-specific checks (§Verification routes) |
| **D6** | **Evidence + handoff** | Main loop steps 5–7; Track A nudge; no record unless Ryan asks |

### Verification routes (interim — not Verify OS)

Link only; no new subsystem.

| Situation | Route |
|-----------|-------|
| Default convmem change | `pytest -q`; `convmem doctor`; `convmem doctor --v1` when infra touched |
| Shipped-work independent check | [`CODEX-DEEPSEEK-VERIFY.md`](../CODEX-DEEPSEEK-VERIFY.md) |
| Bug discovery (upstream) | [`TEAM-CHARTER`](../inter-model/TEAM-CHARTER-2026-07-06.md) — Crush lane; Execute implements after approval |
| Active failure / debug | §Active failure branch above; [`zeller-builder-digest.md`](../builder-reference/zeller-builder-digest.md); `convmem doctor` output |
| Client site promote | [`site-reference/NOTES.md`](../site-reference/NOTES.md) |
| Surface soaks (when cited) | [`VERIFICATION-MATRIX.md`](../inter-model/VERIFICATION-MATRIX.md) |
| Post-execute plan cleanup | [`REVISE-PLANNING.md`](REVISE-PLANNING.md) |
| Optional post-handoff audit | Ryan-requested only; Codex is upstream planner, not default post-handoff auditor |
| Arc closeout (Verify OS) | [`VERIFY-PLANNING.md`](VERIFY-PLANNING.md) + `docs/plans/VERIFY-<slug>.md` |

### Awareness (read-only context)

- [`TEAM-CHARTER-2026-07-06.md`](../inter-model/TEAM-CHARTER-2026-07-06.md) — implementer must-nots
- [`MODEL-WORKFLOW.md`](../MODEL-WORKFLOW.md) — repo-specific routes (lab vs prod vs client)
- [`CI-WAIT-WORKFLOW.md`](../CI-WAIT-WORKFLOW.md) — when CI is pending: what to do while automated review runs
- [`.cursor/BUGBOT.md`](../../.cursor/BUGBOT.md) — BugBot review context only; applicability and invocation policy live in §External Review gate
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
- [ ] Active failure (if applicable): repro captured, fix verified against repro, or N/A documented
- [ ] Change is minimal and matches conventions
- [ ] External Review applicability and reason recorded; required BugBot evidence matches the subject tip and every finding is disposed, or a valid exemption / Ryan tip-acceptance is cited
- [ ] Verification gates run; evidence table complete (PASS/FAIL/DEFERRED)
- [ ] Handoff nudge issued (Track A); handoff ≠ record stated
- [ ] If this task closes an **arc**: VERIFY path named (stub or filled); next phase is [`VERIFY-PLANNING.md`](VERIFY-PLANNING.md) unless Ryan waives in writing
- [ ] No self-transition to Revise / Architecture / merge
- [ ] No `convmem record` unless Ryan asks

Active phase lane must stop here. Await HITL.

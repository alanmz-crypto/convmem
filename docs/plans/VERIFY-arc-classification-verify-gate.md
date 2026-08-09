# Verify Plan — arc-classification-verify-gate

```text
Planning Status

Phase:        Verify (arc-classification-verify-gate)
Characters:   Independent Reviewer, Test-First Reviewer
Functions:    Reviewer
Lanes:        Cursor (mechanical); Kiro (sign-off); Ryan (GATE)
Authority:    Post-Execute HITL — do not trust prior chat claims alone
```

**Subject / tip:** `<Cursor implementation tip SHA>`  
**PR(s):**  
**EXECUTION / ARCHITECTURE:** [`EXECUTION-2026-08-14-arc-classification-verify-gate.md`](EXECUTION-2026-08-14-arc-classification-verify-gate.md) / [`ARCHITECTURE-arc-classification-verify-gate.md`](ARCHITECTURE-arc-classification-verify-gate.md)  
**Goal:** Prove eligible work cannot silently bypass arc classification or the existing VERIFY path.

**Report format:** Each check must state PASS / FAIL / SKIP and one line of evidence.  
**GATE** = Ryan process step; not a mechanical agent PASS.

## Human consequence

**Consequence:** Ryan can see that classification is explicit, unresolved work stops, trivial work remains low-friction, and existing declared arcs still use the established VERIFY workflow.

### 5 Ws

| | |
|---|---|
| **Who** | Cursor implements; Kiro independently reviews; Ryan gates. |
| **What** | Intake classification plus doctor detection and escalation checks. |
| **When** | After Cursor implementation and before arc close. |
| **Why** | Prevent multi-session or risk-bearing work from bypassing post-implementation verification. |
| **How** | Validate task-owned `INTAKE-<slug>.md` records and scenario fixtures against the protocol. |

**TL;DR:** Verify the new classification contract and its backstop without changing Verify OS semantics.

## Scope lock

| In scope | Out of scope |
|----------|--------------|
| Intake schema, protocol integration, doctor check, tests, generated parity, and Ryan's proof-case disposition | Existing VERIFY semantics, automatic record creation, unrelated arcs, historical evidence reconstruction |

## Verification design

| Field | Answer |
|-------|--------|
| Independent oracle | Protocol contract plus deterministic doctor/test expectations, reviewed by Kiro on the exact tip. |
| Failure-injection method | Fixtures with missing fields, invalid states, missing VERIFY stubs, mismatched slugs, and escalation triggers. |
| Negative control | A deliberately omitted classification or malformed intake record must fail/surface; a single soft trigger must not falsely escalate. |
| Dual-path coverage | Explicit intake records and existing declared-arc VERIFY paths; unrelated branch history is a noise-control path. |

## V0 — Preconditions

| ID | Check | PASS / FAIL / SKIP / N/A |
|----|-------|---------------------------|
| V0a | Subject tip resolves and includes the approved execution scope | PENDING |
| V0b | Execute BugBot applicability decision and reason are recorded | PENDING |
| V0c | If required, BugBot-reviewed SHA equals subject tip SHA | PENDING |
| V0d | Architecture and execution artifacts are present at the reviewed revision | PENDING |

## V1 — Classification contract

| ID | Check | PASS / FAIL |
|----|-------|-------------|
| V1a | Valid `arc` requires matching slug and existing VERIFY stub | PENDING |
| V1b | Valid `non_arc` requires reason and authority | PENDING |
| V1c | `arc_review` is unresolved and blocks handoff | PENDING |

## V2 — Escalation and low-friction behavior

| ID | Check | PASS / FAIL |
|----|-------|-------------|
| V2a | One hard trigger or two soft triggers requires reclassification | PENDING |
| V2b | One soft trigger alone does not create a false escalation | PENDING |
| V2c | Trivial non-arc fixture passes without VERIFY | PENDING |

## V3 — Doctor backstop and noise control

| ID | Check | PASS / FAIL |
|----|-------|-------------|
| V3a | Doctor surfaces malformed or contradictory intake metadata | PENDING |
| V3b | Doctor does not infer from unrelated branch commits or dirty files | PENDING |
| V3c | Existing doctor and planning-contract checks remain green | PENDING |

## V4 — Independent sign-off

| ID | Check | PASS / FAIL |
|----|-------|-------------|
| V4a | Kiro issues written PASS/FAIL naming the exact subject tip and residuals | PENDING |
| V4b | Ryan records the worktree-cleanup arc/exemption decision and GATE | PENDING |

## Evidence log

```text
VERIFY-arc-classification-verify-gate — tip <sha> — runner <lane> — <ISO-8601>
V0: PENDING
V1: PENDING
V2: PENDING
V3: PENDING
V4: PENDING
Mechanical: PENDING
Sign-off: PENDING
```

**Active phase lane must stop here. Await HITL.**

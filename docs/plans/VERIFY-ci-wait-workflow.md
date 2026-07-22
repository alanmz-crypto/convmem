# Verify Plan — CI Wait Workflow

```
Planning Status

Phase:        Verify (ci-wait-workflow)
Characters:   Test-First Reviewer
Functions:    Mechanical documentation verification
Lanes:        Codex PR Steward (mechanical); Ryan (GATE)
Authority:    Bounded docs-only execution brief
```

**Subject:** `plan/2026-07-22-ci-wait-workflow`
**PR:** Draft PR created after mechanical acceptance
**Architecture:** `docs/plans/ARCHITECTURE-ci-wait-workflow.md`
**Goal:** Confirm the CI-wait documentation matches its content and scope
contract without adding runtime gates.

The exact committed tip and command results belong in the PR handoff. This
companion defines the light docs-only checklist; it is not an independent
architecture or governance sign-off.

---

## Scope lock

| In scope | Out of scope |
|----------|--------------|
| Architecture record, playbook, VERIFY companion, and three router pointers | Protocol, charter, Actions, hooks, doctor, standing register, runtime behavior |

---

## V0 — Preconditions

- Branch was created from current `origin/main` and empty-pushed before edits.
- The shared checkout and unrelated files were not modified.
- The live PR Steward charter was re-read before drafting.

## V1 — Content contract

- The playbook has five ordered sections and two required examples.
- Rules 1 and 2 are explicit textual expectations.
- Mechanical CI is narrowly defined.
- Flaky or unrelated CI routes to an allowed rerun or escalation without scope
  expansion.
- The approximately 80-line target is aspirational, not a hard gate.

## V2 — Discovery and boundaries

- `docs/MODEL-WORKFLOW.md`, `docs/planning/EXECUTE-TASK.md`, and
  `docs/README.md` each contain one resolving pointer.
- Only the six authorized documentation files differ from `origin/main`.
- Prohibited governance, runtime, and CI surfaces remain untouched.

## V3 — Delivery

- The commit is pushed with an explicit refspec.
- The draft PR says **docs-only; no runtime or CI changes**.
- The handoff reports the exact tip SHA, checks, residual risk, and Ryan's merge
  gate.

---

## Evidence format

```text
CI Wait Workflow — tip <sha> — Codex PR Steward — <ISO-8601>
V0: PASS|FAIL — <one-line evidence>
V1: PASS|FAIL — <one-line evidence>
V2: PASS|FAIL — <one-line evidence>
V3: PASS|FAIL — <one-line evidence>
Mechanical: PASS|FAIL
Ryan GATE: pending
```

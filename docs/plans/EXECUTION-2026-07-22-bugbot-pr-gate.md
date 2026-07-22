# Execution Plan — BugBot PR Gate

```text
Planning Status

Phase:        Execute Task
Characters:   Implementer, Test-First Reviewer
Functions:    Implementer
Lanes:        Codex (PR Steward; bounded docs delivery)
Authority:    Ryan-directed execution on 2026-07-22
```

**Source:** Cursor architecture direction
`/home/lauer/.cursor/plans/bugbot_pr_gate_72a01817.plan.md`, as amended by
the Codex feasibility and reversibility review in the authorizing session.

**Authority:** Ryan's “Execute it” direction on 2026-07-22 approves this
docs-only execution and waives the still-pending Kiro execution-plan review for
this arc. It authorizes pushing `docs/2026-07-22-bugbot-pr-gate` and opening one
pull request against `main`. It does not authorize a BugBot trigger comment,
merge, branch-protection change, or other GitHub mutation.

**Goal:** Establish BugBot as a PR-native, SHA-bound external-review gate for
correctness-affecting changes without introducing a local report or waiver
subsystem.

## Scope

### In scope

- A binding BugBot PR-gate architecture document.
- External Review step 3 in `docs/planning/EXECUTE-TASK.md`.
- BugBot confirmation rules in Verify OS.
- An arc Verify companion defining mechanical checks for this rollout.
- Git-tracked `.cursor/BUGBOT.md` review context with no workflow triggers.
- One docs/policy pull request with an exempt BugBot evidence row.

### Out of scope

- `.convmem/bugbot-reports`, waiver files, doctor probes, CI, hooks, protocol
  kernel, or branch-protection changes.
- Team-charter or HITL-role changes.
- BugBot Autofix or API automation.
- Runtime code and unrelated PR reviews.
- Org-level fail-on-unresolved configuration.
- A non-Cursor fallback reviewer product.

## Authorized path set

The pull request changes exactly these seven tracked paths:

1. `docs/plans/EXECUTION-2026-07-22-bugbot-pr-gate.md`
2. `docs/plans/ARCHITECTURE-bugbot-pr-gate.md`
3. `docs/planning/EXECUTE-TASK.md`
4. `docs/planning/VERIFY-PLANNING.md`
5. `docs/plans/VERIFY-TEMPLATE.md`
6. `docs/plans/VERIFY-bugbot-pr-gate.md`
7. `.cursor/BUGBOT.md`

## Tasks

| ID | Deliverable | Depends on | Gate |
|----|-------------|------------|------|
| **T1** | Binding architecture | Approved plan | All locked decisions present; no contradiction with source direction |
| **T2** | Execute Task External Review contract | T1 | Contract test and doctor PASS; loop/D-step invariants preserved |
| **T3** | Verify OS confirmation contract | T2 | Conditional prerequisite, SHA mismatch FAIL, and dispositions present |
| **T4** | Arc Verify companion stub | T3 | Seven-path and semantic checks defined; no premature PASS |
| **T5** | Tracked BugBot review context | T1; serialized after T4 | Tracked, context-only, and free of workflow triggers |

Execute serially: **T1 → T2 → T3 → T4 → T5**.

## Locked implementation rules

- Execute owns gate applicability. Verify confirms the decision and its
  evidence; it does not decide applicability after the fact.
- Use the universal terms **subject tip SHA** and **BugBot-reviewed SHA**.
- Any subject-tip change after review needs a BugBot result for the new SHA or
  a fresh valid exemption.
- BugBot and GitHub Copilot audit are independent and non-substituting.
- A finding is disposed only as `fixed`, `ryan_accepted`, or absent/clean under
  the binding lifecycle.
- BugBot outage blocks the agent. Only Ryan may give written, tip-specific
  acceptance.
- `.cursor/BUGBOT.md` supplies review context only; applicability and trigger
  policy remain in Execute.

## Evidence requirements

The rollout itself is exempt because it changes policy and review context, not
executable product behavior:

| Field | Expected value |
|-------|----------------|
| `gate_applicability` | `exempt` |
| `reason` | Policy/review-context-only rollout; no executable product behavior |
| `subject_tip_sha` | Final pull-request tip |
| `bugbot_reviewed_sha` | `n/a` |
| `result` | `n/a` |
| `finding_disposition` | `none` |
| `authority_reference` | `n/a` |

Ryan's execution and PR authority is recorded separately in the handoff. It is
not overloaded into the BugBot-specific `authority_reference` field.

Required mechanical evidence:

- `pytest -q tests/test_planning_guide_contract.py` passes.
- `convmem doctor` passes.
- The main Execute loop is 0–7 and External Review is step 3.
- D0–D6 labels are unchanged; D6 rejoins main-loop steps 5–7.
- The final diff contains exactly the seven authorized paths.
- `.cursor/BUGBOT.md` is tracked and contains no workflow-trigger policy.

## Rollback and STOP conditions

| Condition | Required response |
|-----------|-------------------|
| Architecture or execution authority is missing | Do not create a branch or edit tracked files |
| A choice needs policy not settled by the architecture | Stop and return to Architecture/HITL; do not improvise |
| An unauthorized path appears | Stop before commit; preserve unknown or user-owned changes |
| A task gate fails before commit | Stop task progression; repair only the owned task diff and rerun the gate |
| Passing a gate requires wider scope | Leave the task uncommitted and escalate to Ryan |
| Planning contract or doctor fails | Isolate whether the current task caused it; do not advance |
| A pushed task commit is faulty | `git revert <sha>`, rerun its gates, push the revert, and stop for Ryan |
| Rebase conflicts or changes reviewed semantics | Stop; do not force-push or guess at resolution |
| Final tip changes after evidence collection | Rerun tip-bound checks and update `subject_tip_sha` |
| GitHub needs an unapproved comment/configuration mutation | Stop and request exact authorization |
| BUGBOT context needs trigger/applicability policy | Stop and revise the architecture instead |

Keep task commits independently revertible. Do not use `git reset --hard`,
force-push, or stash unrelated files. This arc has no database or runtime
mutation, so no data-backup rollback path applies.

## `.cursor/BUGBOT.md` bootstrap review

The file remains gate-exempt, but it is operationally load-bearing. Ryan must
review its exact content before merge. Any BugBot result produced automatically
on this bootstrap PR is informational and cannot validate its own configuration.
Future changes to false-positive carve-outs, sensitive-area boundaries, or
review invariants require normal PR review.

## Arc Verify companion

- Path: `docs/plans/VERIFY-bugbot-pr-gate.md`
- Initial status: stub with checks defined and results pending
- Template: `docs/plans/VERIFY-TEMPLATE.md`
- Fill mechanical evidence only against the final subject tip.

## Delivery and HITL stop

Commit coherent task units and push immediately after every commit. Open one
docs/policy PR containing the exempt evidence row. Handoff must include branch,
`git log origin/main..HEAD --oneline`, push status, verification, and the largest
residual risk. Do not trigger BugBot, merge, write a log, or run `convmem record`.

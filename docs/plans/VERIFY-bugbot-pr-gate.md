# Verify Plan — BugBot PR Gate

```text
Planning Status

Phase:        Verify (bugbot-pr-gate)
Characters:   Independent Reviewer
Functions:    Reviewer
Lanes:        Codex (mechanical); Kiro or Ryan-named lane (sign-off); Ryan (GATE)
Authority:    Post-Execute HITL — do not trust prior chat claims alone
```

**Status:** Stub; checks defined, mechanical results pending final subject tip.
**Subject / tip:** `<final-branch-tip-pending>`
**PR:** `<pending>`
**EXECUTION:** `docs/plans/EXECUTION-2026-07-22-bugbot-pr-gate.md`
**ARCHITECTURE:** `docs/plans/ARCHITECTURE-bugbot-pr-gate.md`
**Goal:** Prove the seven-file policy rollout preserves Planning OS invariants,
binds applicable BugBot evidence to the accepted tip, and keeps review context
separate from workflow triggers.

For each check, record **PASS / FAIL / SKIP** plus one line of evidence.
BugBot-specific rows may use **N/A (exempt)** only with the recorded exemption
reason. An applicable SHA mismatch is always **FAIL**.

## Scope lock

| In scope | Out of scope |
|----------|--------------|
| Exactly seven authorized paths; architecture and execution policy; Verify OS confirmation; BUGBOT review context | Runtime code; CI/hooks; protocol kernel; charter; local report/waiver storage; GitHub configuration; BugBot trigger comment |

Authorized paths:

1. `docs/plans/EXECUTION-2026-07-22-bugbot-pr-gate.md`
2. `docs/plans/ARCHITECTURE-bugbot-pr-gate.md`
3. `docs/planning/EXECUTE-TASK.md`
4. `docs/planning/VERIFY-PLANNING.md`
5. `docs/plans/VERIFY-TEMPLATE.md`
6. `docs/plans/VERIFY-bugbot-pr-gate.md`
7. `.cursor/BUGBOT.md`

## V0 — Preconditions and External Review evidence

```bash
git rev-parse HEAD
git diff --name-only origin/main...HEAD
pytest -q tests/test_planning_guide_contract.py
convmem doctor
```

Execute evidence expected for this rollout:

| Field | Value |
|-------|-------|
| `gate_applicability` | `exempt` |
| `reason` | Policy/review-context-only rollout; no executable product behavior |
| `subject_tip_sha` | `<final-branch-tip-pending>` |
| `bugbot_reviewed_sha` | `n/a` |
| `result` | `n/a` |
| `finding_disposition` | `none` |
| `authority_reference` | `n/a` |

| ID | Check | Result |
|----|-------|--------|
| V0a | Subject tip SHA resolves to the commit being verified | PENDING |
| V0b | Execute applicability and reason are present | PENDING |
| V0c | Exemption is consistent with the final seven-file policy/context diff | PENDING |
| V0d | Exactly the seven authorized paths differ from `origin/main` | PENDING |
| V0e | Planning contract test and `convmem doctor` pass | PENDING |

## V1 — Binding architecture

| ID | Check | Result |
|----|-------|--------|
| V1a | Architecture assigns applicability to Execute, confirmation to Verify, review context to BUGBOT, and durable evidence to GitHub | PENDING |
| V1b | Universal SHA terms, any-tip-change rule, rename litmus, and unsure→required are explicit | PENDING |
| V1c | Copilot independence, finding lifecycle, evidence schema, and outage→Ryan tip-acceptance are explicit | PENDING |
| V1d | Local report/waiver storage, CI/hooks, protocol, charter, and branch protection remain non-goals | PENDING |

## V2 — Execute Task invariants

```bash
rg -n '^\| \*\*[0-7]\*\*' docs/planning/EXECUTE-TASK.md
rg -n '^\| \*\*D[0-6]\*\*' docs/planning/EXECUTE-TASK.md
rg -n 'steps 4–6|steps 5–7' docs/planning/EXECUTE-TASK.md
```

| ID | Check | Result |
|----|-------|--------|
| V2a | Main loop is exactly 0–7 and External Review is step 3 | PENDING |
| V2b | D0–D6 labels remain unchanged and D6 points to main-loop steps 5–7 | PENDING |
| V2c | Applicability, SHA equality, any-tip-change, lifecycle, outage, Copilot independence, and evidence schema are present | PENDING |
| V2d | Awareness points to BUGBOT as review context, not policy ownership | PENDING |
| V2e | Exit criteria require a valid External Review disposition | PENDING |

## V3 — Verify OS confirmation

| ID | Check | Result |
|----|-------|--------|
| V3a | Verify copies Execute applicability and does not reclassify it | PENDING |
| V3b | Applicable subject-tip / BugBot-reviewed SHA mismatch is FAIL, never SKIP | PENDING |
| V3c | Required finding dispositions and outage acceptance are checked | PENDING |
| V3d | Template mirrors all seven evidence fields and permits N/A only for a valid exemption | PENDING |

## V4 — `.cursor/BUGBOT.md` boundary

```bash
git ls-files --error-unmatch .cursor/BUGBOT.md
if rg -ni '/review-bugbot|bugbot run|cursor review|gate_applicability|when to run' \
  .cursor/BUGBOT.md; then
  exit 1
fi
```

| ID | Check | Result |
|----|-------|--------|
| V4a | `.cursor/BUGBOT.md` is git-tracked | PENDING |
| V4b | It contains tests, invariants, false-positive boundaries, and sensitive areas | PENDING |
| V4c | It contains no applicability, invocation, waiver, or merge-readiness policy | PENDING |
| V4d | Ryan reviews the bootstrap file's exact content before merge | PENDING |

## V5 — Independent sign-off

| ID | Check | Result |
|----|-------|--------|
| V5a | Written PASS/FAIL names the final subject tip SHA and residual risks | PENDING |

The verifier performs no cleanup or correction. Findings return to the
implementation lane; Ryan owns the final GATE.

## Evidence log

```text
VERIFY-bugbot-pr-gate — tip <pending> — runner <pending> — <pending ISO-8601>
V0: PENDING
V1: PENDING
V2: PENDING
V3: PENDING
V4: PENDING
V5: PENDING
Mechanical: PENDING
Sign-off: PENDING
```

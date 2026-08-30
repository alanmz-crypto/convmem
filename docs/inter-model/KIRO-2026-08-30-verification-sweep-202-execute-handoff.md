# Execute Handoff: [Arc Recent-Completions Verification Sweep] Kiro — #202 CodeQL closeout

**Date:** 2026-08-30
**Author:** Cursor (dispatch)
**For:** **Kiro** (review/sign-off lane — you execute this handoff)
**Authorization:** Ryan proxy GATE — **blocked until step 2 (#221) completes**

---

## Resume state

| Field | Value |
|-------|--------|
| **State** | `NOT_STARTED — blocked on step 2 (#221) verdicts` |
| **Sequence** | **Step 3a of 4** (Kiro) — Copilot step 3b blocked until you return |
| **Subject SHA** | `d10e1d5f4993f60a32142115f8b8c0f0f9ea4481` |
| **Live ruleset ID** | `19156572` |
| **Ryan GATE after you** | Accept verdict → dispatch Copilot step 3b |

### Prerequisite

Step 2 (#221 Copilot + Kiro) must close (both PASS or Ryan accepts residual) before
Ryan authorizes this handoff.

---

## What you must do (not optional)

**Do not** restate, summarize, or extract this handoff back to Ryan. That is not a verdict.

**Do** independently attest at **`d10e1d5f4993f60a32142115f8b8c0f0f9ea4481`** that:

1. Live ruleset `19156572` matches Grant A five-context baseline
2. Closeout docs at `d10e1d5…` accurately describe live enforcement

**Do not** treat historical Kiro PASS at `d3d0bdd…` or `cd653d9…` as verdict on `main`
— those SHAs are **NOT** on `main` ancestry (disposable evidence only).

---

## Step-by-step

### 1. Confirm subject identity

```bash
git fetch origin
git rev-parse d10e1d5f4993f60a32142115f8b8c0f0f9ea4481
git log -1 --oneline d10e1d5f4993f60a32142115f8b8c0f0f9ea4481
git merge-base --is-ancestor d10e1d5f4993f60a32142115f8b8c0f0f9ea4481 origin/main
```

Expected: merge commit for PR #202 — CodeQL Complex Therapy arc closeout (docs only).

### 2. Fetch live ruleset (do not infer from docs alone)

```bash
gh api repos/alanmz-crypto/convmem/rulesets/19156572
```

Compare against Grant A baseline in `docs/plans/VERIFY-codeql-complex-therapy.md` (V1/V2/V5e).

**Bundled snapshot (authoring-time — re-fetch and confirm):**

| Field | Value |
|-------|--------|
| **Name** | Protect Main |
| **Target** | `refs/heads/main` |
| **Enforcement** | `active` |
| **Strict policy** | `true` |
| **Required contexts** | `pylint (3.12)`, `pytest (3.12)`, `Analyze (actions)`, `Analyze (python)`, `CodeQL` |
| **CodeQL integration_id** | `57789` |

### 3. Read closeout commit scope

`d10e1d5…` — planning/protocol docs only (10 files); no workflow or ruleset file on `main`.

---

## Output contract (required)

```text
Subject SHA (docs): d10e1d5f4993f60a32142115f8b8c0f0f9ea4481
Live ruleset 19156572 vs Grant A: PASS|FAIL — <evidence>
Closeout doc accuracy: PASS|FAIL
Kiro: PASS|FAIL — <one line>
```

**Do not** proceed to Copilot step 3b from this lane.

---

## What NOT to do

- Do not start before step 2 (#221) completes.
- Do not treat Kiro PASS at `d3d0bdd…` as verdict on `main`.
- Do not merge or restore disposable branches #198–#201.
- Do not mutate ruleset from this review lane.

---

## Reference (background only)

Spec: [`CURSOR-2026-08-30-verification-sweep-202-codeql-closeout-handoff.md`](CURSOR-2026-08-30-verification-sweep-202-codeql-closeout-handoff.md)

Next agent (blocked until you return): [`COPILOT-2026-08-30-verification-sweep-202-execute-handoff.md`](COPILOT-2026-08-30-verification-sweep-202-execute-handoff.md)

**TL;DR:** [Arc Recent-Completions Verification Sweep] Kiro: attest live ruleset + doc accuracy at `d10e1d5…` — blocked until #221 step 2. Step 3a of 4.

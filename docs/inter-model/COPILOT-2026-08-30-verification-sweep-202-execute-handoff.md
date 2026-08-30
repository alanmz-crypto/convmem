# Execute Handoff: [Arc Recent-Completions Verification Sweep] Copilot audit-lane — #202 CodeQL closeout

**Date:** 2026-08-30
**Author:** Cursor (dispatch)
**For:** **Copilot audit-lane** (you execute this handoff)
**Authorization:** Ryan proxy GATE — **blocked until Kiro step 3a returns**

---

## Resume state

| Field | Value |
|-------|--------|
| **State** | `NOT_STARTED — blocked on Kiro step 3a` |
| **Sequence** | **Step 3b of 4** (Copilot) — final Tier-0 step |
| **Subject SHA** | `d10e1d5f4993f60a32142115f8b8c0f0f9ea4481` |
| **Live ruleset ID** | `19156572` |
| **Ryan GATE after you** | Accept Tier-0 complete → schedule Tier-1 queue |

### Prerequisite (Kiro step 3a)

Ryan must accept Kiro verdict from
[`KIRO-2026-08-30-verification-sweep-202-execute-handoff.md`](KIRO-2026-08-30-verification-sweep-202-execute-handoff.md)
before you execute.

---

## What you must do (not optional)

**Do not** restate this handoff or infer live ruleset state from docs alone.

**Do** issue written **PASS or FAIL** naming subject **`d10e1d5…`** and live ruleset
snapshot, explicitly addressing:

1. Producer binding claim (integration IDs, especially CodeQL `57789`)
2. No security regression vs Grant A/B evidence

Re-fetch live ruleset — do not adopt Kiro's snapshot without verification.

---

## Evidence commands (run yourself)

```bash
git fetch origin
git rev-parse d10e1d5f4993f60a32142115f8b8c0f0f9ea4481
git merge-base --is-ancestor d10e1d5f4993f60a32142115f8b8c0f0f9ea4481 origin/main

gh api repos/alanmz-crypto/convmem/rulesets/19156572
gh pr view 202 --json mergeCommit,title,reviews
```

Compare against `docs/plans/VERIFY-codeql-complex-therapy.md` Grant A baseline.

---

## Output contract (required)

```text
Subject SHA (docs): d10e1d5f4993f60a32142115f8b8c0f0f9ea4481
Live ruleset 19156572 vs Grant A: PASS|FAIL — <evidence>
Copilot audit-lane: PASS|FAIL — <one line rationale>
Step 3 GAP closed: Y|N — <both Kiro + Copilot PASS required for Y>
```

**Tier-0 GAP for #202 closes only if both Kiro (3a) and Copilot (3b) PASS.**

---

## What NOT to do

- Do not start before Kiro step 3a verdict is accepted.
- Do not treat off-main SHAs (`d3d0bdd…`) as on-main evidence.
- Do not mutate ruleset or patch workflows on `main`.

---

## Reference (background only)

Spec: [`CURSOR-2026-08-30-verification-sweep-202-codeql-closeout-handoff.md`](CURSOR-2026-08-30-verification-sweep-202-codeql-closeout-handoff.md)

Prior agent: [`KIRO-2026-08-30-verification-sweep-202-execute-handoff.md`](KIRO-2026-08-30-verification-sweep-202-execute-handoff.md)

**TL;DR:** [Arc Recent-Completions Verification Sweep] Copilot audit-lane: PASS/FAIL on producer binding + ruleset at `d10e1d5…` — blocked until Kiro step 3a. Step 3b of 4.

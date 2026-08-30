# Execute Handoff: [Arc Recent-Completions Verification Sweep] Kiro — #253 claims attestation

**Date:** 2026-08-30
**Author:** Cursor (dispatch)
**For:** **Kiro** (review/sign-off lane — you execute this handoff)
**Authorization:** Ryan proxy GATE + Tier-0 order `#253 → #221 → #202`

---

## Resume state

| Field | Value |
|-------|--------|
| **State** | `AUTHORIZED — execute now` |
| **Sequence** | **Step 1 of 3** — do not start #221 or #202 until this verdict is delivered |
| **Subject SHA** | `a924d3887329dd51f1e0ac917f8ab21bae513c57` |
| **Branch to read** | `docs/2026-08-30-2026-08-30-verification-sweep-tier0-handoffs` (optional; claims below are complete) |
| **Ryan GATE after you** | Accept verdict → dispatch Brief 2 (#221) |

---

## What you must do (not optional)

**Do not** restate, summarize, or extract this handoff back to Ryan. That is not a verdict.

**Do** independently run the checks below, fill the claims table with your own evidence lines, and return the **Output contract** block at the bottom with **Kiro: PASS or FAIL** naming subject SHA `a924d3887329dd51f1e0ac917f8ab21bae513c57`.

Cursor published a mechanical attestation (all C1–C12 PASS) in chat — **you must not adopt it without re-running checks yourself.** Independent verification is the point of this step.

---

## Step-by-step

### 1. Confirm subject identity

```bash
git fetch origin
git rev-parse a924d3887329dd51f1e0ac917f8ab21bae513c57
git log -1 --oneline a924d3887329dd51f1e0ac917f8ab21bae513c57
```

Expected: merge commit for PR #253 — `docs: reconcile project routing with landed work`.

### 2. Run ancestry checks (C1, C2, C3, C5, C8, C9, C10)

For each SHA, run `git merge-base --is-ancestor <sha> origin/main` and record YES/NO:

| Claim | SHA |
|-------|-----|
| C1 T1 #234 | `cac3cc35b8a74d43f9d353554cb7c80cb2f13801` |
| C2 T2 #236 | `62f0f2355543f1daefa237bfc0811f94d8982989` |
| C3 T3 #238 | `d250feb2bbbf81e2c3dd8513d79fb0e2140266a3` |
| C5 Execute-close #250 | `e930ae4c2fb67eabbfa570f7caacda8d9ddac79d` |
| C8 OOM #245 | `3dd355a50c1498aadc94b143f6997d2e005016be` |
| C9 relocation #247 | `a19b5cbb2e431aafeda304057c98e6bd81aa0ffd` |
| C10 writer #243 | `872a0e483dd5eff09ccaef3c655af82f5e81e92e` |

Cross-check merge SHAs: `gh pr view 234 --json mergeCommit` (same for 236, 238, 250, 245, 247, 243).

### 3. Read STATUS docs (C4, C6)

| Claim | Read |
|-------|------|
| C4 T4 unauthorized | `docs/plans/STATUS-recovery-authority.md` — T4 row must say NOT AUTHORIZED / NOT STARTED |
| C6 production unauthorized | `docs/inter-model/STATUS.md` + `docs/inter-model/LATEST.md` — V8c, D0/D1, GC, Shadow, R2b must remain unauthorized |

### 4. GitHub PR state (C7, C11)

```bash
gh pr view 252 --json state,mergedAt,mergeCommit
gh pr list --state open --search naturalistic --json number,state,headRefName
git branch -r | rg 'portland|naturalistic'
```

| Claim | Pass condition |
|-------|----------------|
| C7 | PR #252 **OPEN**, not merged |
| C11 | Naturalistic/Portland work exists only on feature/experiment branches; no unauthorized study execution claimed as landed on `main` |

### 5. C3 scope (scratch-only)

Read PR #238 title/message; confirm `recovery_bulk_workflow.py` on `main` is scratch-only / non-serving (no live publication path).

### 6. C12 (authoring-time main pointer)

Reconciliation handoff cited `main@e930ae4c` at authoring. Confirm `e930ae4c2fb67eabbfa570f7caacda8d9ddac79d` was the correct base era (ancestor of `a924d388…`). Note current tip if different — that does not fail C12 if authoring pointer was accurate then.

---

## Claims table — you fill this in

| ID | PASS / FAIL / UNVERIFIABLE | One line evidence (your words) |
|----|----------------------------|--------------------------------|
| C1 | | |
| C2 | | |
| C3 | | |
| C4 | | |
| C5 | | |
| C6 | | |
| C7 | | |
| C8 | | |
| C9 | | |
| C10 | | |
| C11 | | |
| C12 | | |

**Overall Kiro rule:** Any **FAIL** on a routing claim → **Kiro: FAIL**. All PASS → **Kiro: PASS**. UNVERIFIABLE only with explicit reason and path to resolve.

---

## Output contract (required — copy this block filled in)

```text
Subject SHA: a924d3887329dd51f1e0ac917f8ab21bae513c57
Kiro: PASS|FAIL — <one line> — claims C1–C12: <N PASS, N FAIL, N UNVERIFIABLE>
Copilot audit-lane: NOT_RUN | PASS | FAIL — <only if a code-grounded claim failed>
GAP closed: Y|N
```

Post the filled block **and** the completed claims table in your reply to Ryan.

---

## What NOT to do

- Do not edit `LATEST.md`, STATUS files, or routing docs.
- Do not implement fixes for failed claims — report only.
- Do not proceed to #221 or #202.
- Do not merge PR #252 or any other PR.
- Do not treat handoff extraction as completing this task.

---

## Reference (background only)

Full spec: [`CURSOR-2026-08-30-verification-sweep-253-claims-attestation-handoff.md`](CURSOR-2026-08-30-verification-sweep-253-claims-attestation-handoff.md)

Coordination: [`CURSOR-2026-08-30-verification-sweep-tier0-coordination-handoff.md`](CURSOR-2026-08-30-verification-sweep-tier0-coordination-handoff.md)

**TL;DR:** [Arc Recent-Completions Verification Sweep] Kiro: run C1–C12 checks yourself, fill the table, return the 4-line contract naming `a924d388…`. Extraction is not a verdict.

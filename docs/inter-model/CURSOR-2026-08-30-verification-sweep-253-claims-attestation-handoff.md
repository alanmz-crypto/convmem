# Verification Handoff: [Arc Recent-Completions Verification Sweep] #253 claims attestation

**Date:** 2026-08-30
**Author:** Cursor (drafting lane)
**For:** **Kiro** (primary) · Copilot audit-lane (only if a claim is code-grounded)
**Authorization:** Ryan proxy GATE — see [coordination handoff](CURSOR-2026-08-30-verification-sweep-tier0-coordination-handoff.md)

---

## Resume state

| Field | Value |
|-------|--------|
| **State** | `AUTHORIZED — verdict pending` |
| **Subject** | PR #253 — project-state reconciliation |
| **Landed SHA** | `a924d3887329dd51f1e0ac917f8ab21bae513c57` |
| **Tree-equivalent tip** | `ad9a9b6a039768c85b704f2bf17034c2605d63fa` |
| **Tree hash** | `183a0395dcba2c4bb8917ff19e6f9a49bf5fc569` (head == landed) |
| **GitHub reviews** | **0** |
| **Ryan GATE after verdict** | Accept/reject routing surfaces; no merge from this brief |

---

## What to verify

**Claims-accuracy attestation** — not a code audit. This PR is the **trust anchor**
for routing surfaces. Every downstream “LANDED/CLOSED” handoff inherits these
claims.

For each claim below, return **PASS / FAIL / UNVERIFIABLE** with one line of
evidence (live git, GitHub API, or doc path). Final verdict must name subject SHA
**`a924d3887329dd51f1e0ac917f8ab21bae513c57`**.

### Claims table

| ID | Claim | Verify against |
|----|-------|----------------|
| C1 | Recovery Authority T1 landed via PR #234 @ `cac3cc35b8a74d43f9d353554cb7c80cb2f13801` | `git merge-base --is-ancestor` + `STATUS-recovery-authority.md` |
| C2 | Recovery Authority T2 landed via PR #236 @ `62f0f2355543f1daefa237bfc0811f94d8982989` | same |
| C3 | Recovery Authority T3 landed via PR #238 @ `d250feb2bbbf81e2c3dd8513d79fb0e2140266a3`; scratch-only/non-serving | same + implementation scope |
| C4 | Recovery T4 unauthorized / not started | `STATUS-recovery-authority.md` |
| C5 | CG-2 Design A Execute-close landed via PR #250 @ `e930ae4c2fb67eabbfa570f7caacda8d9ddac79d` | git + `STATUS.md` |
| C6 | Production D0/D1, V8c, fence/pointer, GC, Shadow, R2b remain **unauthorized** | `LATEST.md` / STATUS briefs |
| C7 | R2b I1–I3 branch-only; draft PR #252 open; **not merged** | `gh pr view 252` |
| C8 | Watch OOM isolation landed via PR #245 @ `3dd355a50c1498aadc94b143f6997d2e005016be` | git |
| C9 | Relocation retrieval scoping landed via PR #247 @ `a19b5cbb2e431aafeda304057c98e6bd81aa0ffd` | git |
| C10 | Writer attestation hardening landed via PR #243 @ `872a0e483dd5eff09ccaef3c655af82f5e81e92e` | git |
| C11 | Naturalistic / Portland work branch-only; no study execution authorized | branch + PR state |
| C12 | Handoff `origin/main` pointer was accurate at authoring (`e930ae4…` era) | note vs current tip |

### Changed files at landed SHA

```
docs/inter-model/LATEST.md
docs/inter-model/STATUS.md
docs/plans/STATUS-recovery-authority.md
docs/plans/STATUS-r2b-capture-auth.md
```

Source narrative: `docs/inter-model/CODEX-2026-08-30-project-state-reconciliation-handoff.md`

---

## Output contract

```text
Subject SHA: a924d3887329dd51f1e0ac917f8ab21bae513c57
Kiro: PASS|FAIL — <one line> — claims C1–C12 summary
Copilot audit-lane: PASS|FAIL|NOT_RUN — <only if code-grounded claim fails>
GAP closed: Y|N
```

---

## What NOT to do

- Do not merge, edit routing docs, or reopen #252.
- Do not treat `convmem doctor` PASS as substitute for this attestation.
- Do not infer operational authorization for any arc from PASS here.
- Do not implement fixes — report FAIL claims only; Ryan prioritizes remediation.

---

## Acceptance criteria

- [ ] Every claim C1–C12 has PASS/FAIL/UNVERIFIABLE with evidence line
- [ ] Verdict names exact subject SHA `a924d388…`
- [ ] Written verdict suitable for VERIFY / LATEST update if Ryan accepts

**TL;DR:** [Arc Recent-Completions Verification Sweep] Kiro attests PR #253 routing
claims against live git/GitHub at `a924d388…` — trust-map verification, not code review.

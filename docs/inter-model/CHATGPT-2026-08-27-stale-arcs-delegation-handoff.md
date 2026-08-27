# Implementation Handoff: Stale Arc Investigation & Delegation

**Date:** 2026-08-27  
**Author:** Kiro (review/design lane)  
**For:** ChatGPT (investigation + delegation to appropriate lanes)  
**Authorization:** Ryan, 2026-08-27 (verbal — "create a handoff for ChatGPT so it can investigate and then start to delegate")

---

## Resume state

| Field | Value |
|-------|--------|
| **State** | `NOT_STARTED` |
| **Branch** | `docs/2026-08-27-stale-arcs-chatgpt-delegation-handoff` |
| **Tip SHA** | (this commit) |
| **Push status** | pushed to origin |
| **PR** | not opened |
| **Ryan GATE** | Each arc has its own Ryan grant gate — see per-arc sections below |
| **Track A ingest** | Kiro session — indexed at handoff |

---

## What to build

Nothing to *implement*. Three arcs have been stale >18 days. All code is already on `main`. What remains is governance ceremony, evidence gathering, and bounded execution — not architecture or implementation. ChatGPT's job is to:

1. **Investigate** each arc's current state (read STATUS files, confirm `main` state)
2. **Assess** what the minimal next step is for each
3. **Delegate** the actual work to the correct lane (Codex for ops/planning, Cursor for any execution, Ryan for grants)

**Why this exists:** The `arc_staleness` doctor warning has flagged these three arcs for 18+ days. They are governance-gated pauses, not defects — but they need someone to move the ball forward on the ceremony/evidence side.

---

## The Three Stale Arcs

### 1. JudgeBench Semantic Calibration v1

| Field | Value |
|-------|-------|
| **STATUS file** | `docs/plans/STATUS-judgebench.md` |
| **Last activity** | 2026-08-09 |
| **Incomplete items** | 2 (Calibration experiment, G4 judge selection) |
| **All code on `main`?** | Yes — G3 corpus locked (#170), Phase A merged (#171) |
| **What remains** | Ryan authorizes the 3-candidate × 20-case = 60-call calibration experiment; then G4 judge selection from results |
| **Is it ritual?** | Yes — one bounded experiment + human decision |
| **CG-2 conflict?** | None. JudgeBench is offline, read-only, Chroma-free. Completely orthogonal. |
| **Delegation target** | **Ryan** — only he can authorize the 60-call experiment. No agent work until that grant. |
| **Suggested next action** | Draft a one-paragraph "calibration experiment authorization request" for Ryan summarizing what the experiment does, its bounds (60 calls max, 20 per candidate, calibration IDs only), and what it produces (confusion matrix report). |

### 2. R2b Capture Authorization

| Field | Value |
|-------|-------|
| **STATUS file** | `docs/plans/STATUS-r2b-capture-auth.md` |
| **Last activity** | 2026-08-09 |
| **Incomplete items** | 4 (T4 fresh packet, T5 Ryan ACCEPT AND GRANT, T6 execute one capture, T7 verify) |
| **All code on `main`?** | Yes — merged as `c0f06f5` via PR #67 |
| **What remains** | Fresh T4 packet (snapshot + draft under new `run_id`), then Ryan two-stage HITL |
| **Is it ritual?** | Yes — produce a packet, get a grant, run one capture, verify |
| **CG-2 conflict?** | None. R2b writes to an absent `capture_dir`, doesn't touch Chroma or watch/refine. |
| **Delegation target** | **Codex** (or Cursor) to produce the fresh T4 packet; then **Ryan** for ACCEPT AND GRANT |
| **Suggested next action** | Delegate T4 packet preparation to Codex: run `convmem doctor` confirming `restic_gate: PASS`, produce fresh trusted source snapshot, create new draft packet under `AUTH_ROOT/<new_run_id>/`. Do NOT reuse quarantined `2026-07-21-r2b-capture-01/`. |
| **Pre-conditions** | `restic_gate: PASS` (currently passing). Old draft is quarantined — must be fresh. |

### 3. Shadow Ledger Phase 0

| Field | Value |
|-------|-------|
| **STATUS file** | `docs/plans/STATUS-shadow-ledger-phase0.md` |
| **Last activity** | 2026-08-09 |
| **Incomplete items** | 5 (C6 event-size evidence, C7 census, C6 canary, runbook, activation grant) |
| **All code on `main`?** | Yes — C1–C7 correctives merged (#122, #126, #131, #134); shadow disabled |
| **What remains** | Ops evidence chain: C6 event-size → C7 7-day census → C6 canary PASS → runbook → Ryan grant |
| **Is it ritual?** | Mostly — ops evidence gathering + runbook authoring. C7 census needs 7 real days. |
| **CG-2 conflict?** | ⚠️ Technically safe (Shadow is passive observer, failures can't roll back Chroma) but STATUS.md explicitly says Shadow activation is deferred until CG-2 Design A is ratified. **Can start C6/C7 evidence gathering now; cannot activate.** |
| **Delegation target** | **Codex** for C6 event-size evidence and runbook drafting; **Ryan** for census grant and activation |
| **Suggested next action** | Start C6 event-size evidence (payload-free design documentation). This is safe now and doesn't require CG-2 to finish. Do NOT attempt `shadow-activate` or hand-edit config. |
| **Constraint** | Prior C7 census was removed 2026-08-06. A fresh census arm must be started — don't assume the old run exists. |

---

## Investigation Checklist (for ChatGPT)

Before delegating, confirm current state:

```bash
# 1. Confirm system health
convmem doctor

# 2. Read each STATUS file
cat docs/plans/STATUS-judgebench.md
cat docs/plans/STATUS-r2b-capture-auth.md
cat docs/plans/STATUS-shadow-ledger-phase0.md

# 3. Confirm code is on main
git log --oneline main | grep -E "#170|#171"   # JudgeBench
git log --oneline main | grep "c0f06f5"         # R2b
git log --oneline main | grep -E "#122|#126|#131|#134"  # Shadow

# 4. Check CG-2 state (to understand constraints)
cat docs/plans/STATUS-recovery-authority.md     # Recovery Authority (adjacent)
cat docs/inter-model/STATUS.md                  # Cross-arc rollup
```

---

## Delegation Rules

| Lane | What they can do | What they cannot do |
|------|-----------------|-------------------|
| **Codex** | Author execution plans, produce T4 packets, draft runbooks, gather evidence | Activate Shadow, run captures without grant, merge to main |
| **Cursor** | Execute authorized implementation tasks | Anything not explicitly authorized |
| **Ryan** | Grant calibration experiments, ACCEPT AND GRANT packets, authorize activation | — |
| **ChatGPT (you)** | Investigate, assess, draft authorization requests, delegate, coordinate | Implement, activate, merge, grant |

---

## What NOT to do

- Do NOT activate Shadow Ledger (`shadow-activate`) — deferred until CG-2 Design A ratification
- Do NOT reuse the quarantined R2b draft packet (`2026-07-21-r2b-capture-01/`)
- Do NOT run JudgeBench calibration calls without Ryan's explicit grant
- Do NOT modify G3 corpus (cases, gold, rubrics, split, lock metadata)
- Do NOT conflate these arcs with CG-2 work — they are independent
- Do NOT treat the `arc_staleness` warning as a defect — it's a governance pause indicator

---

## Priority Recommendation

1. **JudgeBench** — lowest effort to unblock (just needs Ryan's grant for a bounded experiment). Draft the authorization request first.
2. **R2b capture** — next lowest (Codex produces a packet, Ryan grants, one execution). Can start T4 immediately.
3. **Shadow Phase 0** — longest tail (7-day census required). Start C6 evidence gathering to get the clock running, but activation is downstream of CG-2.

---

## Acceptance criteria

- [ ] ChatGPT has read all three STATUS files and confirmed current state
- [ ] Each arc has a clear next-step delegation issued to the correct lane
- [ ] JudgeBench: authorization request drafted for Ryan
- [ ] R2b: T4 packet preparation delegated to Codex (or started)
- [ ] Shadow: C6 event-size evidence work delegated or started
- [ ] No unauthorized activations, captures, or experiments were run
- [ ] Forward announcement issued after investigation is complete

---

## Related files

| What | Path |
|------|------|
| JudgeBench STATUS | `docs/plans/STATUS-judgebench.md` |
| JudgeBench Architecture | `docs/plans/ARCHITECTURE-judgebench.md` |
| R2b STATUS | `docs/plans/STATUS-r2b-capture-auth.md` |
| R2b Architecture | `docs/plans/ARCHITECTURE-r2b-capture-auth.md` |
| Shadow STATUS | `docs/plans/STATUS-shadow-ledger-phase0.md` |
| Shadow Execution (corrective) | `docs/plans/EXECUTION-shadow-phase0-activation-corrective.md` |
| Cross-arc rollup | `docs/inter-model/STATUS.md` |
| CG-2 VERIFY | `docs/plans/VERIFY-cg2-production-activation.md` |
| Team charter | `docs/inter-model/TEAM-CHARTER-2026-07-06.md` |

---

## Leaving / picking up checklist

**Author (leaving):**

- [x] This file committed (or on pushed branch)
- [ ] `LATEST.md` bullet at top with link and resume state
- [ ] `STATUS-*.md` Update Log line (if arc tracked) — N/A (cross-arc coordination, no single arc)
- [ ] Branch pushed

**Implementer (picking up):**

- [ ] Read this file before first action
- [ ] `convmem doctor` → `convmem brief --stdout-only` → `convmem unresolved`
- [ ] Read all three STATUS files listed above
- [ ] State investigation findings before delegating

<!-- Arc: none (ad-hoc) — cross-arc coordination handoff -->

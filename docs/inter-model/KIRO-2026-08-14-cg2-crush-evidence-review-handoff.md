# Review Handoff: CG-2 Architecture Evidence/Failure Review

**Date:** 2026-08-14
**Author:** Kiro (design review lane)
**For:** Crush (evidence/failure review lane)
**Authorization:** Ryan, 2026-08-14 (verbal; sequencing discussion after Kiro design PASS)

---

## Resume state

| Field | Value |
|-------|--------|
| **State** | `NOT_STARTED` |
| **Branch** | Read-only review — no branch needed; deliverable goes on any `docs/` branch |
| **Target revision** | `1222b1ede2d6cc5da582388768f06d60b36c5e50` on `plan/2026-08-14-cg2-production-activation` |
| **Push status** | Target revision pushed to origin |
| **PR** | Not applicable (review artifact, not implementation) |
| **Ryan GATE** | None — Crush may begin immediately |
| **Kiro design review** | PASS at same SHA (this session) |

---

## What to review

Evaluate whether the CG-2 architecture's safety claims, failure-mode taxonomy,
and evidence requirements are grounded in real operational behavior — not
aspirational or unfounded.

**Why this exists:** The architecture proposes authority boundaries, crash
recovery paths, and Chroma operational assumptions that must survive contact with
actual failure evidence. Crush's role is to stress-test claims against known
ConvMem operational history, CG-1 review findings, and Chroma behavioral
evidence.

---

## Target document

Read the architecture at the exact review revision:

```bash
git show 1222b1e:docs/plans/ARCHITECTURE-cg2-production-activation.md
```

Context (on `main`):
- CG-1 substrate: `file_generation_pointer.py`, `file_generation_store.py`,
  `file_generation_builder.py`, `file_generation_validate.py`,
  `file_generation_contract.py`
- CG-1 closure: `docs/inter-model/CRUSH-2026-08-13-cg1-g4b-review-pass-closure.md`
- CG-1 dependability handoff: `docs/inter-model/HANDOFF-CG1-DEPENDABILITY-2026-08-10.md`

---

## Review sections and questions

### 1. Failure-mode table (§11) — completeness and honesty

- Does every failure listed have a concrete operational precedent or a plausible
  mechanism in the current codebase?
- Are there failure modes from CG-1 review (G4a/G4b findings) or Chroma
  operational history that the table omits?
- Is "fail closed" actually achievable given the existing broad-exception
  fallback in `query.py` (lines ~428, ~523)?

### 2. Chroma evidence (§3, §13, §15) — `#7463` disposition

- Is the architecture's characterization of upstream issue `#7463` (operational
  replay-cost report, not data loss) accurate to what the reporter describes?
- Do the pinned Chroma 1.5.9 evidence gates (§13 items 15) cover the known WAL/
  HNSW persistence lag behaviors that CG-1 review surfaced?
- Is there any known Chroma behavioral evidence (from the CG-1 literature
  verification or the Tier-L reconcile) that contradicts an assumption here?

### 3. Authority-resolution linearization (§5.1) — failure plausibility

- Can the seqlock-like read/verify/retry pattern fail to converge under any
  realistic workload (e.g., rapid pointer republication during batch promotion)?
- Is the "retry" behavior bounded? The architecture doesn't name a retry limit.
- What happens if evidence bytes change every retry attempt (livelock)?

### 4. Source reconciliation (§7.1) — operational cost

- Given the current corpus size (~21k units, ~1363 indexed sources), is periodic
  reconciliation (secure open + hash every source) operationally feasible within
  the watcher's memory/CPU budget?
- Does the current watchdog (`watch.py`) expose `IN_Q_OVERFLOW` or equivalent?
  If not, what's the failure evidence gap?

### 5. Retained-generation lifetime and GC (§10) — crash evidence

- Does CG-1's existing crash-injection test suite cover the generation-retention
  invariant (active + previous remain intact)?
- Is the pin-before-dereference protocol (§10.3) consistent with what CG-1
  proved about SQLite/Chroma durability under process crash?

### 6. Cross-reference with CG-1 closure

- Did the G4b review surface any findings that this architecture should
  acknowledge but doesn't?
- Is the CG-1 durability claim (§2 item 13: "process-crash recovery, not full
  power-loss") correctly inherited here?

---

## Deliverable

**File:** `docs/inter-model/CRUSH-2026-08-14-cg2-evidence-review.md`

**Required sections:**
1. One-paragraph summary verdict (PASS / FAIL / PASS WITH RISKS)
2. Per-section findings (address each of the 6 review areas above)
3. Any new failure modes or evidence gaps discovered
4. Explicit statement of what was checked vs. what could not be verified
5. SHA confirmation: verdict applies to `1222b1e` only

---

## What NOT to review

- **Implementation feasibility** — that's Cursor's lane (parallel)
- **Design correctness of state machines** — Kiro already PASSed this
- **Formal model adequacy** — Codex does this after feasibility PASS
- **Code changes** — this is read-only; no implementation, no tests, no fixes
- **Execution plan authoring** — not authorized until architecture lock
- **Shadow Ledger, JudgeBench, or other arcs** — out of scope

---

## Acceptance criteria

- [ ] All 6 review areas addressed with specific findings or explicit "no issue found"
- [ ] Any discovered evidence gap or missing failure mode is named with severity
- [ ] Verdict is PASS, FAIL, or PASS WITH RISKS — not ambiguous
- [ ] Verdict is bound to exact SHA `1222b1e`
- [ ] No implementation or execution-plan content produced
- [ ] Deliverable pushed and `LATEST.md` updated with review status

---

## Related files

| What | Path |
|------|------|
| Architecture under review | `docs/plans/ARCHITECTURE-cg2-production-activation.md` (on branch at `1222b1e`) |
| Arc brief | `docs/plans/STATUS-cg2-production-activation.md` (on branch at `1222b1e`) |
| CG-1 closure (Crush authored) | `docs/inter-model/CRUSH-2026-08-13-cg1-g4b-review-pass-closure.md` |
| CG-1 dependability handoff | `docs/inter-model/HANDOFF-CG1-DEPENDABILITY-2026-08-10.md` |
| CG-1 literature verification | `docs/inter-model/CURSOR-2026-08-10-cg1-literature-verification-handoff.md` |
| Kiro design review | This session (PASS, not separately filed — in Track A ingest) |
| Current watcher code | `watch.py` |
| Current query fallback | `query.py` (lines ~425–435, ~520–525) |
| Chroma operational evidence | Upstream `#7463`; Tier-L reconcile closure in `STATUS-chroma-reconcile-tier-l.md` |

---

## Leaving checklist (Kiro, author)

- [ ] This file committed and pushed
- [ ] `LATEST.md` bullet updated with review handoff link
- [ ] `STATUS-cg2-production-activation.md` — no update needed (already shows Crush review as "not started")
- [ ] Branch pushed

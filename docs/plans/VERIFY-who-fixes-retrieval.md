# Verify Plan — who-fixes-retrieval

```
Planning Status

Phase:        Verify (who-fixes-retrieval)
Characters:   Cursor (mechanical closeout)
Functions:    Reviewer
Lanes:        Cursor (mechanical); Ryan (GATE / merge docs)
Authority:    Post-Execute HITL — prove Rounds 1–4 shipped; board closed to P1.3
```

**Subject / tip:** `origin/main` code anchors below + docs closeout PR for this VERIFY  
**PR(s):** #38 (R1), #35 (R2), #39 (R3), #40 (R4); docs closeout handoff  
**EXECUTION / ARCHITECTURE:** Debate board `docs/inter-model/debate-2026-07-15-who-fixes-retrieval/`  
**Goal:** Prove the who-fixes-retrieval **coordination arc** is closed; hand remainder to P1.3 without authorizing new ranking code.

**Report format:** For each check, state **PASS / FAIL / SKIP** and one line of evidence.  
**GATE** = Ryan process step; not a mechanical agent PASS.

---

## Scope lock

| In scope | Out of scope |
|----------|--------------|
| Rounds 1–4 shipped on `main` | P1.3 source-trust implementation / VERIFY freeze |
| Debate board closed → successor P1.3 | `semantic_dedupe` refine.jobs, evidence-scoping code |
| Inherit/dismiss handoff searchable | New diversification / ranking experiments |
| Session cargo indexed (Track A) | Merging stale PR #36 as current truth |

---

## V0 — Preconditions

```bash
cd ~/Projects/convmem
git fetch origin main
git rev-parse origin/main
convmem doctor
```

| ID | Check | PASS |
|----|-------|------|
| V0a | `origin/main` reachable; doctor non-blocking for docs closeout | PASS — doctor green 2026-07-22 (closeout runner) |
| V0b | Scope excludes P1.3 code changes | PASS — docs/VERIFY/handoff only |

---

## V1 — Code anchors on main

| ID | Check | PASS |
|----|-------|------|
| V1a | Round 2: `ask(trace)` / `TRACE_SCHEMA` present | PASS — `ask.py` has `TRACE_SCHEMA = "convmem.ask.trace.v1"`; PR #35 @ `950e830` |
| V1b | Round 1: nested inter-model accepted | PASS — `is_inter_model_doc` accepts `docs/inter-model/**` (not `archive`) |
| V1c | Round 3: source diversity shipped | PASS — PR #39 @ `549f74d` on main history |
| V1d | Round 4: `retrieve_for_ask` on main | PASS — `def retrieve_for_ask` in `ask.py`; PR #40 |

---

## V2 — Handoff + board close artifacts

| ID | Check | PASS |
|----|-------|------|
| V2a | Inherit/dismiss handoff exists | PASS — `docs/inter-model/CURSOR-2026-07-22-who-fixes-retrieval-closed-to-p13.md` |
| V2b | LATEST points closed arc → P1.3 | PASS — Active handoff bullet added |
| V2c | Debate README marks Closed / Round 4 shipped | PASS — on debate-close docs tip |
| V2d | Cargo path for this closeout session documented | PASS — `566966f0-…jsonl` in handoff |

---

## V3 — Independent sign-off

| ID | Check | PASS |
|----|-------|------|
| V3a | Written PASS naming residuals | PASS — Residual: debate-close PR + this VERIFY must merge; P1.3 still GATE; stale #36 should be closed by Ryan (not merged) |

Verifier performs **no** P1.3 code cleanup or correction.

---

## Evidence log

```text
VERIFY-who-fixes-retrieval — runner Cursor — 2026-07-22T04:00:00Z
V0: PASS (docs closeout; doctor green)
V1: PASS (R1–R4 anchors on main)
V2: PASS (handoff + LATEST + board close + cargo path)
V3: PASS with residual (merge docs; close #36; P1.3 untouched)
Mechanical: PASS with residual
Sign-off: Cursor mechanical closeout — Ryan GATE = merge docs PRs / dispose #36
```

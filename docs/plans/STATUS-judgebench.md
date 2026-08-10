# Arc Brief — JudgeBench Semantic Calibration (v1)

> **Every model working on this arc must read this file at session start.**
> After reading, state: "Goal: [one sentence]. My role: [what I'm here to do]. The system currently: [what exists]. Missing: [what doesn't exist yet]."

---

## 1. What This Is For (product goal)

ConvMem answers questions by retrieving evidence and generating responses. Today the only quality signal is a fragile 1–5 numeric score from a single LLM judge — no ground truth, no provenance, no way to know if a model/prompt change actually improved answers.

**JudgeBench replaces this** with offline semantic calibration: a frozen-evidence test harness where the judge's verdicts are compared against Ryan-locked gold labels. When complete, Ryan can:

1. Run `eval-judgebench` against a locked corpus
2. Get a confusion matrix (judge-agrees-with-gold vs. doesn't)
3. Use that to select/validate a judge model
4. Know — provably — whether a change improved or degraded answer quality

**Done means:** Ryan runs one command, gets a calibration report, and uses it to decide if the current judge is good enough. The system *prevents* invalid comparisons (different models, changed prompts, stale baselines) via comparison-signature enforcement.

---

## 2. System Design (how the pieces connect)

```
                    ┌─────────────────────────────────────────────┐
                    │          JUDGEBENCH (offline only)           │
                    │                                             │
  Frozen corpus     │   cases.jsonl ──┐                           │
  (no Chroma!)     │   gold.jsonl ───┤                           │
                    │   rubrics/ ─────┤                           │
                    │                 ▼                           │
                    │   ┌───────────────────┐                    │
                    │   │  Runner           │                    │
                    │   │  (runner.py)      │                    │
                    │   │                   │                    │
                    │   │  case → J0 → J1   │                    │
                    │   │  compare to gold  │                    │
                    │   └───────┬───────────┘                    │
                    │           │                                 │
                    │           ▼                                 │
                    │   ┌───────────────────┐                    │
                    │   │  Provenance       │                    │
                    │   │  (eval_provenance)│                    │
                    │   │                   │                    │
                    │   │  comparison sig   │                    │
                    │   │  needs_rebaseline │                    │
                    │   └───────────────────┘                    │
                    └─────────────────────────────────────────────┘

  Preflight (before run):
  ┌────────────────────────┐
  │  Model Identity        │
  │  (eval_model_identity) │
  │                        │
  │  classify_independence │
  │  cross_family required │
  │  unknown = fail-closed │
  └────────────────────────┘

  Legacy path (explicit --legacy only):
  ┌────────────────────────┐
  │  eval_judge.py         │
  │  1-5 scores            │
  │  cannot emit v1 prov   │
  │  cannot update v1 base │
  └────────────────────────┘
```

**Key constraints (invariants from architecture lock):**
- Chroma is **never** imported in the JudgeBench path (invariant 2, enforced by import-scan test)
- Judge execution failure ≠ semantic FAIL (invariant 5)
- One judge pinned for entire run; no mid-run switching (invariant 6)
- `unknown` independence fails closed for canonical work (invariant 7)
- Any comparison-signature change → `needs_rebaseline` before examining scores (invariant 12)

---

## 3. What Exists Right Now (file map)

### On `main` (merged, stable)

| File | What it does | State |
|------|-------------|-------|
| `eval_judgebench/contracts.py` | `SemanticJudgmentV1`, `JudgeInvocationV1`, `MechanicalGrade` dataclasses | Complete |
| `eval_judgebench/contract_validate.py` | Validates judgment dict against contract; returns `invalid_output` on malformed | Complete |
| `eval_judgebench/rubric.py` | Loads rubric by id from `rubrics/` dir | Complete |
| `eval_judgebench/rubric_validate.py` | Validates judgment against rubric-specific rules | Complete |
| `eval_judgebench/identity_registry.py` | Loads `identity-registry-v1.json`; resolves model aliases | Complete (loader only) |
| `eval_judgebench/__init__.py` | Package exports | Complete |
| `eval_corpus/fixtures/judgebench/semantic-v1/manifest.json` | Corpus version, schema, hash policy | Structure only (no real cases) |
| `eval_corpus/fixtures/judgebench/semantic-v1/cases.jsonl` | Frozen evidence + candidate per case | **Empty** (awaits G3 gold lock) |
| `eval_corpus/fixtures/judgebench/semantic-v1/gold.jsonl` | Ryan's locked gold verdicts | **Empty** (awaits G3) |
| `eval_corpus/fixtures/judgebench/semantic-v1/rubrics/synthesis-grounded-v1.json` | Synthesis rubric definition | Complete |
| `eval_corpus/fixtures/judgebench/identity-registry-v1.json` | Known model families/lineages | Starter entries |
| `eval_model_identity.py` (T2, merged #155) | `classify_independence(judge, under_test)` → `self/same_family/cross_family/unknown/not_applicable` | Complete (on main) |
| `eval_provenance.py` (T3, merged #155) | Comparison signature computation; `needs_rebaseline` detection | Complete (on main) |
| `eval_judgebench/runner.py` (T4, merged #155) | Loads cases → J0 → J1 → compare to gold; dry-run with empty corpus | Complete (on main) |
| `eval_judge.py` (T5, merged #155) | `--legacy` gate; legacy path isolated from v1 provenance | Complete (on main) |
| `tests/test_judgebench_contracts.py` | Contract validation tests | 29 tests, green |
| `tests/test_judgebench_rubric.py` | Rubric load/validate tests | Green |
| `tests/test_judgebench_no_chroma.py` | AST import scan — proves no Chroma in eval_judgebench/ | Green |

> T2–T5 source (identity, provenance, runner, legacy shim) merged to `main` via PR #155.
> Their test modules (`test_eval_model_identity.py`, `test_eval_provenance_signature.py`,
> `test_judgebench_runner.py`, `test_eval_judge_legacy.py`) are not tracked under `main`'s
> `tests/` at this revision — verify whether they were carried by #155 or need re-adding.

### Ryan-locked G3 state on `feat/2026-08-09-2026-08-09-judgebench-g3-corpus`

| Surface | Current locked state |
|---|---|
| `cases.jsonl` / `gold.jsonl` | Ryan-locked 30 matched cases; 20 calibration / 10 holdout; 15 synthesis / 15 summary |
| Rubrics | Summary rubric added; both task rubrics define support, coverage, contradiction, and verdict boundaries |
| Corpus enforcement | Strict schema, hash, split, J0-outcome, origin, and Ryan-lock validation; canonical corpus validation accepts the lock |
| Provenance | Canonical independence binds every distinct model-generated `candidate_origin`; caller identity/config cannot substitute for frozen provenance |
| Review state | **G3 locked by Ryan**; branch delivery still requires separate PR/merge authorization |

### Does NOT Exist Yet

| What | Why not | Who can create it |
|------|---------|-------------------|
| Registered identity for `gpt-5-codex-sol` | The locked candidates' frozen producer is unresolved, so canonical calibration fails closed until a later authorized registry decision | Ryan-owned identity decision (G4 or separate gate) |
| First calibration run results | Requires G3 delivery, an authorized identity decision, and a separately authorized calibration experiment | Cursor/Crush after Ryan |
| Judge model selection | Requires calibration-split results | Ryan only (G4) |
| Live `ask.py` integration | Deferred — not v1 scope | Nobody yet (separate arc) |

---

## 4. Completion State

| # | Milestone | Status | Blocking on |
|---|-----------|--------|-------------|
| G1 | Architecture locked | **DONE** | — |
| G2 | Execution plan approved | **DONE** | — |
| S1–S9 | Flash prep (contracts, rubrics, scaffold, tests) | **DONE on `main`** | — |
| T2–T5 | Identity, provenance, runner, legacy shim | **DONE on `main`** (merged #155) | — |
| PR merge | T2–T5 code on `main` | **DONE** | #155 merged |
| G3 | Gold corpus + split lock | **LOCKED on feature branch** | Ryan authorized the exact 30-case corpus; delivery to `main` awaits separate PR/merge authorization |
| Calibration | Calibration-split experiments | **NOT STARTED** | Requires G3 delivery, identity resolution, and separate Ryan authorization |
| G4 | Judge model selection | **NOT STARTED** | Requires calibration-split results |
| T7 retrieval corpus | Post-rebuild golden eval (`tests/test_eval_golden.py`) | **REPAIRED 10/10** | Was 2/10 after R3 rebuild skipped the approved-ledger channel; backfilled 356 approved decisions + CSP obs/ver into Chroma (corpus-only fix, no repo change) |

**Summary: Ryan has locked the validated 30-case G3 corpus on its feature branch. `gpt-5-codex-sol` remains unregistered, so canonical calibration stays fail-closed pending a separately authorized identity decision and calibration experiment; G4 judge selection follows those results.**

---

## 5. Your Role (read this to know what you're here to do)

**If Ryan sent you here to implement:** The T2–T5 code is already merged to `main` (#155). Unless Ryan asks for revision or a new slice, your job is probably to **fix something specific** Ryan identified or assist with **G3 gold authoring**.

**If Ryan sent you here to review:** Read `main`'s implementation. Key questions: Does identity classification enforce `cross_family`-only for canonical runs? Does comparison-signature detect all the fields listed in the architecture? Is the runner truly Chroma-free? (Note: the T2–T5 test modules are not under `main`/`tests/` at this revision — verify coverage if asked.)

**If Ryan sent you here for G3:** G3 is locked. Do not alter its cases, gold judgments, split, or lock metadata; any future corpus change requires Ryan and a new immutable corpus version.

**If you don't know why you're here:** Ask Ryan. The most likely next action is G3 gold authoring or a VERIFY/standing-check review.

---

## 6. What Remains Before "Live" (sequential)

- [ ] Ryan authorizes PR delivery and merge of the locked G3 branch
- [ ] Ryan authorizes the frozen-producer identity decision and calibration-split experiments
- [ ] First calibration run against locked gold (confusion matrix report)
- [ ] Ryan selects a judge from calibration evidence (G4)
- [ ] Standing checks `eval-provenance-wiring` and `eval-negative-control-coverage` resolved
- [ ] (Future, separate arc) Live integration into `ask.py`

---

## 7. Hard Stops (models cannot cross)

| Stop | Gate owner | What it blocks |
|------|-----------|----------------|
| G3 — locked corpus | Ryan | Corpus is immutable; any case/gold/rubric/split change requires Ryan and a new corpus version |
| G4 — judge selection | Ryan | Choosing which model judges; running calibration |
| Chroma in semantic path | Architecture invariant 2 | Never — any Chroma import in `eval_judgebench/` fails the AST test |
| Live `ask.py` integration | Invariant 1 / separate arc | Not v1 scope |
| Provenance bleed | Invariant (T5) | Legacy path must never emit v1 fields or update v1 baselines |

---

## 8. Relationship to ConvMem (the bigger picture)

JudgeBench is one piece of ConvMem's evaluation stack:

```
ConvMem evaluation landscape:
├── JudgeBench (THIS ARC) — calibrate the semantic judge offline
├── E2E synthesis eval — test retrieval→generation→judging together
├── Summary eval — summary-specific quality (shares J1 contract)
├── Chroma Tier-L — orphan/retrieval quality (SEPARATE arc, not us)
└── Live ask.py judging — uses whatever judge passes calibration (FUTURE)
```

JudgeBench is upstream of everything: until the judge is calibrated, all other quality measurements are ungrounded. But JudgeBench itself is **offline-only** and **Chroma-free** — it never touches the live system.

---

## 9. Key Design Files (for deep dives)

| Purpose | Path | Read when |
|---------|------|-----------|
| Architecture (locked, canonical) | `docs/plans/ARCHITECTURE-judgebench.md` | You need to understand invariants or design rationale |
| Execution plan (task breakdown) | `docs/plans/EXECUTION-judgebench.md` | You need task dependencies or scope lock |
| Flash slice brief (S1–S9 detail) | `docs/plans/EXECUTION-judgebench-flash-slices.md` | You're implementing prep slices |
| VERIFY checklist | `docs/plans/VERIFY-judgebench.md` | You're reviewing or closing checks |
| T2–T5 handoff (Cursor) | `docs/inter-model/CURSOR-2026-08-09-judgebench-T2-T5-handoff.md` | You're picking up T2–T5 work |

---

## 10. How to Update This Brief (departure protocol)

**When you finish working on this arc, update this file before handoff.** The goal is that the *next* model reads this one document and has the same quality of mental landscape you had — updated to reflect reality after your work.

**Rules — keep this a snapshot, not a log:**

1. **Overwrite, don't append.** Update section 3 (file map) and section 4 (completion state) to reflect current reality. Delete rows for things that no longer exist. Change "on branch" to "on `main`" when merged. This is a *current state* document, not a history.

2. **Keep section 5 (Your Role) generic.** Rewrite the role guidance to reflect what the *next* model probably needs to do — not what you just did. "If Ryan sent you here to..." should always be forward-looking.

3. **Update section 6 (What Remains) by removing completed items.** Check off and then *delete* completed steps. The list should always show only what's still ahead.

4. **Touch the diagram (section 2) only if the design changed.** If you added a new module or data flow, update the ASCII diagram. If you only implemented what was already shown, leave it alone.

5. **One line in the Update Log.** Date, your name, what changed at the milestone level. Not a session narrative. Not implementation details.

6. **Do not add session-specific context.** No "I ran into X bug," no "Ryan said Y in chat." That belongs in your session ingest (Track A), not here. This document is for the *next* model's orientation, not your work diary.

7. **The test: could a model read *only* this file and know what to do?** If your update makes that harder, you're doing it wrong.

---

## Update Log

| Date | Who | Change |
|------|-----|--------|
| 2026-08-09 | Codex Sol | Ryan locked the 30-case G3 corpus; delivery and G4 remain separately gated |
| 2026-08-09 | Kiro | Initial arc brief; T2–T5 on branch, PR not filed, G3/G4 awaiting Ryan |
| 2026-08-09 | Crush (DeepSeek) | Reconcile: T2–T5 merged to `main` via PR #155; completion state and remaining steps updated; noted T2–T5 test modules not carried to `main`/`tests/` in #155 |
| 2026-08-09 | Crush | Golden eval repaired 2/10 → 10/10 (Chroma backfill of approved ledger + CSP obs pair); T7 post-rebuild verify unblocked |

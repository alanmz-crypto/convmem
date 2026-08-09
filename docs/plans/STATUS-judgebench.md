# Arc Brief — JudgeBench Semantic Calibration (v1)

> **Every model working on this arc must read this file at session start.**
> After reading, state: "Goal: [one sentence]. My role: [what I'm here to do]. The system currently: [what exists]. Missing: [what doesn't exist yet]."

---

## 1. What This Is For (product goal)

ConvMem answers questions by retrieving evidence and generating responses. Today the only quality signal is a fragile 1–5 numeric score from a single LLM judge — no ground truth, no provenance, no way to know if a model/prompt change actually improved answers.

**JudgeBench replaces this** with offline semantic calibration: a frozen-evidence test harness where the judge's verdicts are compared against Ryan-locked gold labels. When complete, Ryan can:

1. Run `run_judgebench()` from `eval_judgebench.runner` against a locked corpus (dry-run: `semantic_judge=None`)
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

### `main`-merged and branch-only surfaces (state labeled per row)

| File | What it does | State |
|------|-------------|-------|
| `eval_judgebench/contracts.py` | `SemanticJudgmentV1`, `JudgeInvocationV1`, `MechanicalGrade` dataclasses | Complete |
| `eval_judgebench/contract_validate.py` | Validates judgment dict against contract; returns `invalid_output` on malformed | Complete |
| `eval_judgebench/rubric.py` | Loads rubric by id from `rubrics/` dir | Complete |
| `eval_judgebench/rubric_validate.py` | Validates judgment against rubric-specific rules | Complete |
| `eval_judgebench/identity_registry.py` | Loads `identity-registry-v1.json`; resolves model aliases | Complete (loader only) |
| `eval_judgebench/__init__.py` | Package exports | Complete |
| `eval_corpus/fixtures/judgebench/semantic-v1/manifest.json` | Corpus version, schema, split, lock, and hash policy | Complete G3 lock metadata |
| `eval_corpus/fixtures/judgebench/semantic-v1/cases.jsonl` | Frozen evidence + candidate per case | Complete: 30 Ryan-locked cases, 20 calibration / 10 holdout |
| `eval_corpus/fixtures/judgebench/semantic-v1/gold.jsonl` | Ryan's locked gold verdicts | Complete: matched 30-case gold lock |
| `eval_corpus/fixtures/judgebench/semantic-v1/rubrics/synthesis-grounded-v1.json` | Synthesis rubric definition | Complete |
| `eval_corpus/fixtures/judgebench/identity-registry-v1.json` | Mainline model families/lineages | Complete for the merged mainline contract |
| `eval_model_identity.py` (T2, merged #155) | `classify_independence(judge, under_test)` → `self/same_family/cross_family/unknown/not_applicable` | Complete (on main) |
| `eval_provenance.py` (T3, merged #155) | Comparison signature computation; `needs_rebaseline` detection | Complete (on main) |
| `eval_judgebench/runner.py` (T4, merged #155) | Loads locked cases → J0 → J1 → compare to gold; supports dry-run | Complete (on main; G3 populated) |
| `eval_judgebench/metrics.py` | Deterministic calibration-only confusion, agreement, status, and exploratory confidence report | Branch-only Phase A implementation; exact calibration result-ID boundary |
| `eval_judgebench/calibration.py` | Validates the locked package, builds provider-bound requests internally, and transports only calibration IDs | Branch-only Phase A implementation; DeepSeek/Llama requests built and validated offline; arbitrary semantic callbacks rejected; exact 20-transport-invocation maximum per candidate run, with no retries or fallbacks |
| `eval_judgebench/provider_requests.py` | Builds and validates pinned DeepSeek/Llama request shapes and parses provider responses | Branch-only Phase A implementation; strict provider-specific response envelopes; no provider/model calls have run |
| `eval_corpus/fixtures/judgebench/identity-registry-v2.json` | Frozen-producer identity resolution for canonical calibration | Branch-only Phase A provenance input; not on `main` |
| `eval_judge.py` (T5, merged #155; prompt upgrade #153) | `--legacy` gate; reason-before-scoring; `confidence` field; legacy path isolated from v1 provenance | Complete (on main) |
| `tests/test_judgebench_contracts.py` | Contracts + T2 identity + T3 provenance + T4 runner + T5 legacy isolation | Green — 29 tests (see `VERIFY-judgebench.md` CHK-004..008) |
| `tests/test_judgebench_rubric.py` | Rubric load/validate tests | Green |
| `tests/test_judgebench_no_chroma.py` | AST import scan — proves no Chroma in eval_judgebench/ | Green |
| `tests/test_eval_methodology.py` | Shared eval methodology gates (`--legacy` with `--judge`, negative control) | Green |

### G3 state on `main` and Phase A state on this feature branch

| Surface | Current locked state |
|---|---|
| `cases.jsonl` / `gold.jsonl` | On `main` at G3 merge `5f1a3ef`: 30 matched cases; 20 calibration / 10 holdout; 15 synthesis / 15 summary |
| Rubrics | Summary rubric added; both task rubrics define support, coverage, contradiction, and verdict boundaries |
| Corpus enforcement | Strict schema, hash, split, J0-outcome, origin, and Ryan-lock validation; canonical corpus validation accepts the lock |
| Provenance | G3 lock is on `main`; this branch's Phase A preflight implements frozen-producer identity resolution via `identity-registry-v2` only |
| Review state | **G3 merged and locked on `main`**; Phase A remains branch-only pending review, PR, and merge authorization |

### Branch-only and not yet authorized

| What | Why not | Who can create it |
|------|---------|-------------------|
| Phase A delivery on `main` | Identity/calibration-prep and deterministic metrics exist only on `feat/2026-08-09-judgebench-calibration-prep` | Ryan review, PR, and merge authorization |
| First calibration run results | No network/model/calibration calls have run; the branch-only transport boundary permits at most 20 transport invocations per candidate run over calibration IDs only, with no retries or fallbacks | Ryan authorization for the separate 3-candidate × 20-case = 60-call experiment; Cursor/Crush after Ryan |
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
| G3 | Gold corpus + split lock | **MERGED on `main` at `5f1a3ef`** | — |
| Phase A | Identity/calibration-prep, deterministic metrics, and provider-bound request/envelope validation | **IMPLEMENTED on branch** | Pending PR/merge; no network/model/calibration calls have run |
| Calibration | Calibration-split experiments | **NOT STARTED** | Phase A review/PR/merge, then Ryan authorization for the separate 3-candidate × 20-case = 60-call experiment; each candidate run is capped at 20 transport invocations over calibration IDs only |
| G4 | Judge model selection | **NOT STARTED** | Requires calibration-split results |
| Upstream Chroma reconcile | R4 post-rebuild verify | **DONE — GREEN** | [`STATUS-chroma-reconcile-tier-l.md`](STATUS-chroma-reconcile-tier-l.md); [`FLASH-2026-08-08-post-rebuild-verify-handoff.md`](../inter-model/FLASH-2026-08-08-post-rebuild-verify-handoff.md) |
| T7 retrieval corpus | Post-rebuild golden eval (`tests/test_eval_golden.py`) | **REPAIRED 10/10** | Was 2/10 after R3 rebuild skipped the approved-ledger channel; backfilled 356 approved decisions + CSP obs/ver into Chroma (corpus-only fix, no repo change) |

**Summary: G3 is merged on `main` at `5f1a3ef`. Phase A identity/calibration-prep, deterministic metrics, and provider-bound request/envelope validation are implemented on `feat/2026-08-09-judgebench-calibration-prep` after `0605670`, with no network/model/calibration calls run. The next boundary is Ryan authorization after PR/merge for the separate 3-candidate × 20-case = 60-call experiment; each candidate run remains capped at 20 transport invocations over calibration IDs only, with no retries or fallbacks. G4 judge selection remains Ryan-owned. Upstream Chroma R4 is GREEN (#161).**

---

## 5. Your Role (read this to know what you're here to do)

**If Ryan sent you here to implement:** Review and deliver the Phase A metrics/prep branch after the focused offline checks pass. Do not run calibration calls; the separate 3-candidate × 20-case = 60-call experiment requires Ryan authorization after PR/merge.

**If Ryan sent you here to review:** Read `main`'s implementation and [`VERIFY-judgebench.md`](VERIFY-judgebench.md). Key questions: Does identity classification enforce `cross_family`-only for canonical runs? Does comparison-signature detect all the fields listed in the architecture? Is the runner truly Chroma-free? T2–T5 mechanical checks live in [`tests/test_judgebench_contracts.py`](../../tests/test_judgebench_contracts.py).

**If Ryan sent you here for G3:** G3 is locked. Do not alter its cases, gold judgments, split, or lock metadata; any future corpus change requires Ryan and a new immutable corpus version.

**If you don't know why you're here:** Ask Ryan. The most likely next action is G3 gold authoring or a VERIFY/standing-check review.

---

## 6. What Remains Before "Live" (sequential)

- [ ] Ryan reviews and authorizes PR delivery and merge of the Phase A prep/metrics branch
- [ ] Ryan authorizes the separate 3-candidate × 20-case = 60-call calibration-split experiment (at most 20 transport invocations per candidate run over calibration IDs only; no retries or fallbacks)
- [ ] First authorized calibration run against locked gold (confusion matrix report)
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
├── Chroma reconcile — R4 GREEN ([`STATUS-chroma-reconcile-tier-l.md`](STATUS-chroma-reconcile-tier-l.md); upstream, closed)
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
| T2–T5 handoff (Cursor) | `docs/inter-model/CURSOR-2026-08-09-judgebench-T2-T5-handoff.md` | Historical — T2–T5 merged #155 |
| Chroma reconcile STATUS | `docs/plans/STATUS-chroma-reconcile-tier-l.md` | You need upstream retrieval/corpus health context |
| R4 verify handoff | `docs/inter-model/FLASH-2026-08-08-post-rebuild-verify-handoff.md` | You need post-rebuild corpus evidence |

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
| 2026-08-09 | Kiro | Initial arc brief; T2–T5 on branch, PR not filed, G3/G4 awaiting Ryan |
| 2026-08-09 | Crush (DeepSeek) | Reconcile: T2–T5 merged to `main` via PR #155; completion state and remaining steps updated; noted T2–T5 test modules not carried to `main`/`tests/` in #155 |
| 2026-08-09 | Crush | Golden eval repaired 2/10 → 10/10 (Chroma backfill of approved ledger + CSP obs pair); T7 post-rebuild verify unblocked |
| 2026-08-09 | Cursor | Landscape sync: T2–T5 tests in contracts file; Chroma R4 GREEN cross-links; runner API in section 1 |
| 2026-08-09 | Codex Luna Medium | Current state reconciled: G3 is merged and locked on `main` at `5f1a3ef`; Phase A remains branch-only with v2 provenance resolution, provider-bound requests/envelopes, and no network/model/calibration calls; review/PR/merge, the separate 3-candidate × 20-case = 60-call authorization, and G4 remain ahead |

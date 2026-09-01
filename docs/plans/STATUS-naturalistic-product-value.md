# Arc Brief — Naturalistic ConvMem Product-Value Evaluation

> **Every model working on this arc must read this file at session start.**
> After reading, state: "Goal: [one sentence]. My role: [what I'm here to do].
> The system currently: [what exists]. Missing: [what doesn't exist yet]."

**Arc:** Naturalistic ConvMem product-value evaluation

**Current state:** G1–G5 are landed on `main`. G1–G4 via squash-merged PR #255
(`787a6ef8…`); G5 synthetic dry-run via squash-merged PR #259 at `6843bbeebbaed6a109fe94967fdd03fb3569b583`.
Kiro independently PASSed G5 at exact implementation SHA `23b2495927a9891070c7c294e45bdb641eaab352` before
merge. V2-01C’s final provisioning-boundary corrective is implemented and
pushed at exact review target `ad50357a1c1d63fe06cf324731fd555fae4f07f2`,
awaiting fresh independent review. Classification remains **methodology
validation, not product evidence**. **G6 is not authorized.** Ryan locked G6
closed until independent review; favorable synthetic dry-run results do not
open G6.

---

## 1. What This Is For (product goal)

This arc asks whether ConvMem creates measurable product value during ordinary
work: compared with the same fresh agent without ConvMem, does ConvMem improve
meaningful recovery and continuation when evaluated prospectively, symmetrically,
and with sealed evidence?

**Done means:** a later, separately authorized prospective study can produce an
auditable co-primary report and an allowed product disposition. A methodology
merge, dry-run, or partial result is not a product conclusion.

## 2. System Design (how the pieces connect)

```
Ryan-frozen frame and roles
            │
            ▼
ordinary episodes → raw evidence → blinded target census/adjudication
                                          │
                                          ▼
                                   sealed sample / probe key
                                          │
                                          ▼
                            symmetric C0/C1 capture and scoring
                                          │
                                          ▼
                      bounded co-primary analysis + information gate
                                          │
                                          ▼
                           later allowed product disposition
```

The landed G1–G4 package supplies contracts, fixtures, adjudication and probe
scaffolds, bounded episode scoring, co-primary aggregation, sparse/scorer
reliability states, and information-gate parameter slots. It does not collect
episodes, run agents, select live thresholds, or access the ConvMem corpus.

Key invariants:

- every episode remains in the opportunity denominator;
- target count cannot weight an episode more than once in paired analysis;
- malformed, duplicate, orphaned, sparse, and non-evaluable inputs fail closed;
- target-present-but-not-evaluable is opportunity-only, never invented effect;
- scorer and gate slots are explicit pre-live records, not hidden defaults;
- G4 can never emit a positive, negative, null, or equivalent product conclusion.

## 3. What Exists Right Now (file map)

| Surface | State |
|---|---|
| `docs/plans/ARCHITECTURE-naturalistic-product-value.md` | Locked planning package; non-authorizing design document |
| `docs/plans/EXECUTION-naturalistic-product-value.md` | Serial gate plan; non-authorizing execution document |
| `eval_naturalistic/contracts.py`, `base.py`, `enums.py`, `digest.py` | G1 contract and identity substrate on `main` |
| `eval_naturalistic/adjudication.py` and fixtures | G2 target census/adjudication scaffold on `main` |
| `eval_naturalistic/probe_construction.py` and fixtures | G3 probe/key construction scaffold on `main` |
| `eval_naturalistic/analysis.py` and fixtures | G4 bounded analysis/statistical machinery on `main`; reviewed bytes unchanged at `fa7d68b` |
| `eval_naturalistic/dry_run.py`, `dry_run_mechanics.py` | G5 synthetic T0–T10 dry-run harness; not a live study controller |
| `tests/test_naturalistic_{contracts,adjudication,probe,analysis,dry_run}.py` | Focused G1–G5 coverage on `main` |
| `eval_naturalistic/v2/authority_substrate.py`, `p0_construct.py` | V2-01C host-held authority admission and historical-P0-compatible representation on the review branch |
| `tests/test_naturalistic_v2_p1_source_backed_authority.py` | V2-01C authority-boundary and historical-P0 compatibility regressions; implementation target `ad50357a…` |
| PR #255 / PR #259 | G1–G4 via #255; G5 dry-run via #259 at `6843bbeebbaed6a109fe94967fdd03fb3569b583` |
| Live runner, study controller, Agent A/B campaign, and corpus access | Absent and unauthorized; G5 does not add them |

## 4. Completion State

| Gate | State | Evidence / next authority |
|---|---|---|
| G1 architecture/contracts | **DONE on `main`** | PR #255; architecture remains non-authorizing |
| G2 adjudication machinery | **DONE on `main`** | PR #255; no natural episode census has run |
| G3 probe construction machinery | **DONE on `main`** | PR #255; no live key or study sample exists |
| G4 analysis/statistical machinery | **DONE on `main`** | Kiro PASS at exact `fa7d68b`; focused 98 tests + 8 subtests; Pylint 10/10 |
| G5 dry-run/fixture verification | **DONE on `main`** | PR #259 at `6843bbeebbaed6a109fe94967fdd03fb3569b583`; Kiro PASS at `23b2495927a9891070c7c294e45bdb641eaab352`; methodology validation only |
| V2-01C unified authority/compatibility corrective | **READY FOR INDEPENDENT REVIEW — branch-only** | Luna final target `ad50357a1c1d63fe06cf324731fd555fae4f07f2`; focused 61, V2 116, broader naturalistic 225 + 8 subtests; fresh Kiro review required |
| G6 prospective study freeze and later T7–T11 gates | **NOT AUTHORIZED — Ryan LOCKED** | Closed until ChatGPT review; then Ryan explicit G6 grant if warranted |
| Product disposition | **UNAVAILABLE** | T10 is the only later stage permitted to produce one |

## 5. Your Role (read this to know what you're here to do)

G5 is **closed on `main`**. V2-01C’s final bounded corrective is complete on
its review branch at `ad50357a…`; do not modify it while it awaits fresh
independent review, and do not start V2-02C.

If Ryan sent you for **G6 or live study**, stop. G6 remains **closed** until
independent **ChatGPT** review completes — synthetic dry-run pass or favorable
fixture numbers do not authorize G6. After ChatGPT review, Ryan must still issue
a separate explicit G6 grant. G6 is prospective study freeze (T0): roles,
schedule/window, environments, order, and all parameter slots must be Ryan-locked
before any episode collection.

If Ryan sent you for **status**, read this brief and [`LATEST.md`](../inter-model/LATEST.md).
Do not infer product value from G1–G5 machinery or synthetic fixtures.

Do not interpret synthetic `0.3` as evidence that ConvMem helps.

## 6. What Remains Before "Live"

- [x] Land G1–G4 methodology package on `main` (PR #255).
- [x] Record exact-SHA Kiro PASS and focused verification.
- [x] Reconcile canonical routing and add this arc brief.
- [x] Ryan explicitly grants G5 synthetic dry-run/fixture verification.
- [x] Cursor implements only the granted G5 dry-run; retain synthetic-only data.
- [x] Independent Kiro review accepts the exact G5 candidate SHA (`23b2495927a9891070c7c294e45bdb641eaab352`).
- [x] Ryan merges G5 (squash-merged PR #259).
- [x] Luna implements the V2-01C unified authority/compatibility corrective at `ad50357a…`; host bootstrap, focused, V2, and broader naturalistic verification is green.
- [ ] Fresh independent exact-tip review of V2-01C corrective; Ryan owns the review gate and any later V2-02C decision.
- [ ] Independent ChatGPT review of G5 methodology / G6 readiness (Ryan GATE).
- [ ] Ryan separately authorizes G6 prospective freeze and later T7–T11 gates.
- [ ] Only a fully authorized T10 path may produce a product disposition.

## 7. Hard Stops (models cannot cross)

| Stop | Owner / invariant | What it blocks |
|---|---|---|
| G4 ceiling | Analysis contract; T10-only disposition rule | Any product conclusion from G1–G4 code or fixtures |
| G6 grant | Ryan after ChatGPT review | Prospective study freeze and every live gate; not implied by G5 landing or synthetic results |
| G6 and later grants | Ryan | Prospective frame, agents, episodes, scoring, and live ConvMem |
| Pre-live numerical slots | Ryan after the required review | Choosing meaningful-advantage, equivalence, precision, sparsity, or scorer thresholds |
| Corpus/live boundary | Arc execution plan | Corpus access, mutation, or ordinary-work campaign from this lane |

## 8. Relationship to ConvMem (the bigger picture)

This is an evaluation arc, not a serving-path change. It consumes sealed
evaluation artifacts and eventually reports product evidence alongside ConvMem's
retrieval, synthesis, and provenance surfaces. It does not replace JudgeBench,
R2b capture authorization, Shadow activation, or Recovery Authority; each remains
separately governed.

## 9. Key Design Files (for deep dives)

| Purpose | Path |
|---|---|
| Locked architecture | [`ARCHITECTURE-naturalistic-product-value.md`](ARCHITECTURE-naturalistic-product-value.md) |
| Serial execution and grant plan | [`EXECUTION-naturalistic-product-value.md`](EXECUTION-naturalistic-product-value.md) |
| G4 implementation handoff and exact review scope | [`../inter-model/CODEX-2026-08-30-naturalistic-product-value-g4-handoff.md`](../inter-model/CODEX-2026-08-30-naturalistic-product-value-g4-handoff.md) |
| G5 dry-run candidate and Kiro review packet | [`../inter-model/CURSOR-2026-08-30-naturalistic-product-value-g5-handoff.md`](../inter-model/CURSOR-2026-08-30-naturalistic-product-value-g5-handoff.md) |
| Cross-arc routing | [`../inter-model/STATUS.md`](../inter-model/STATUS.md) and [`../inter-model/LATEST.md`](../inter-model/LATEST.md) |

## 10. How to Update This Brief (departure protocol)

Keep this document a current-state snapshot, not a session diary. When a gate
changes state, overwrite sections 3–6, remove completed future work from section
6, and add one milestone-level line below. Do not add chat narrative here; ingest
the session transcript separately under Track A.

### Update Log

- 2026-08-30 — Codex: recorded PR #255 squash merge of G1–G4 on `main`, exact-SHA Kiro PASS, and the separate Ryan-owned G5 boundary.
- 2026-08-30 — Cursor: implemented Ryan-granted G5 synthetic dry-run; candidate awaiting exact-SHA Kiro review. No product evidence. No G6 authority.
- 2026-08-30 — Kiro: independent G5 PASS at exact SHA `23b2495927a9891070c7c294e45bdb641eaab352`; PR Steward opened merge PR for Ryan.
- 2026-08-30 — Ryan: squash-merged G5 via PR #259 to `6843bbeebbaed6a109fe94967fdd03fb3569b583`; arc at methodology milestone; G6 Ryan-gated.
- 2026-08-30 — Ryan: squash-merged routing refresh PR #261 to `676d6b5`; locked G6 closed until ChatGPT review regardless of synthetic results.
- 2026-09-01 — Kiro: independent V2-01C authority review at exact tip `767d176` returned CORRECTIVE REQUIRED (claimant-controlled graph mints P1; authority substrate is claimant-mintable). DeepSeek takes over ChatGPT's blocked review lane. No merge; G6 stays locked.
- 2026-09-01 — Luna: implemented and pushed V2-01C unified authority/compatibility corrective at exact target `8e92af95`; focused/V2/naturalistic tests pass; fresh independent review required.
- 2026-09-01 — Luna: closed the provisioning-boundary corrective at exact target `ad50357a`; host bootstrap credential and registry mutation controls pass; fresh Kiro review required.

**TL;DR:** G1–G5 are on `main` (routing at `676d6b5` via PR #261). Methodology
validation only — not product evidence. G6 stays closed until ChatGPT review,
then Ryan explicit grant if warranted.

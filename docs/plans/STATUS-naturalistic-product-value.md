# Arc Brief — Naturalistic ConvMem Product-Value Evaluation

> **Every model working on this arc must read this file at session start.**
> After reading, state: "Goal: [one sentence]. My role: [what I'm here to do].
> The system currently: [what exists]. Missing: [what doesn't exist yet]."

**Arc:** Naturalistic ConvMem product-value evaluation

**Current state:** G1–G5 are landed on `main`. G1–G4 via squash-merged PR #255
(`787a6ef8…`); G5 synthetic dry-run via squash-merged PR #259 at `6843bbeebbaed6a109fe94967fdd03fb3569b583`.
Kiro independently PASSed G5 at exact implementation SHA `23b2495927a9891070c7c294e45bdb641eaab352` before
merge; that verdict remains historical implementation evidence. Claude later
found a compositional prospective-frame defect, and ChatGPT revised the current
methodology gate to **C — G5 corrective required**. Classification remains
**methodology validation, not product evidence**. Ryan accepted D1–D6 as the
corrective design direction, and Codex committed the bounded architecture and
execution amendment at exact revision `b6a1ccff82ef2456d5b65be122e2e714f84f5ad2`.
Kiro independently **PASSed** both files at that exact revision with two
nonblocking wording corrections; Codex applied only those corrections at
`fde840b`. Ryan has now **accepted the corrected design as design-only**.
Ryan has now issued a **bounded G5C implementation grant** covering only the
named evaluator, synthetic-fixture, and focused-test files in the Cursor
handoff. Implementation is `NOT_STARTED`. **No G6/T0 work, live evidence,
corpus/index access, parameter selection, scoring, or product disposition is
authorized.**

---

## 1. What This Is For (product goal)

This arc asks whether ConvMem creates measurable product value during ordinary
work: compared with the same fresh agent without ConvMem, does ConvMem improve
meaningful recovery and continuation when evaluated prospectively, symmetrically,
and with sealed evidence?

**Done means:** a later, separately authorized prospective study can produce an
auditable structured result tuple and an allowed product disposition. A methodology
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
                         qualified C0/C1 replay → blinded scoring
                                          │
                                          ▼
             complete-pair effect + deterministic bounds + process accounting
                                          │
                                          ▼
                 orthogonal gates → later derived disposition
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
- the sealed registry is the sole episode-opportunity denominator authority;
- valid missing outcomes may enter frozen bounds, but protocol/environment/
  isolation/scorer-integrity failures never do;
- no authoritative first-study scalar replaces the structured result tuple;
- C0/C1 replay is qualified from one sealed state with C1 ConvMem access as the
  sole intended difference.

## 3. What Exists Right Now (file map)

| Surface | State |
|---|---|
| `docs/plans/ARCHITECTURE-naturalistic-product-value.md` | Kiro PASS at exact `b6a1ccf`; “four”→“five” wording correction at `fde840b`; Ryan design-accepted; non-authorizing |
| `docs/plans/EXECUTION-naturalistic-product-value.md` | Kiro PASS at exact `b6a1ccf`; scorer-integrity wording restored at `fde840b`; Ryan design-accepted; non-authorizing |
| `eval_naturalistic/contracts.py`, `base.py`, `enums.py`, `digest.py` | G1 contract and identity substrate on `main` |
| `eval_naturalistic/adjudication.py` and fixtures | G2 target census/adjudication scaffold on `main` |
| `eval_naturalistic/probe_construction.py` and fixtures | G3 probe/key construction scaffold on `main` |
| `eval_naturalistic/analysis.py` and fixtures | G4 bounded analysis/statistical machinery on `main`; reviewed bytes unchanged at `fa7d68b` |
| `eval_naturalistic/dry_run.py`, `dry_run_mechanics.py` | G5 synthetic T0–T10 dry-run harness; not a live study controller |
| `tests/test_naturalistic_{contracts,adjudication,probe,analysis,dry_run}.py` | Focused G1–G5 coverage on `main` |
| PR #255 / PR #259 | G1–G4 via #255; G5 dry-run via #259 at `6843bbeebbaed6a109fe94967fdd03fb3569b583` |
| `docs/inter-model/CODEX-2026-08-30-naturalistic-g5-methodology-corrective-handoff.md` | Historical corrective synthesis that led to accepted D1–D6; no implementation grant |
| `docs/inter-model/CODEX-2026-08-30-naturalistic-g5-corrective-kiro-review-handoff.md` | Exact-revision Kiro review packet for `b6a1ccf`; no implementation grant |
| `docs/inter-model/CODEX-2026-08-30-naturalistic-g5c-cursor-handoff.md` | Current bounded G5C implementation grant; strict file allowlist; Cursor `NOT_STARTED` |
| Live runner, study controller, Agent A/B campaign, and corpus access | Absent and unauthorized; G5 does not add them |

## 4. Completion State

| Gate | State | Evidence / next authority |
|---|---|---|
| G1 architecture/contracts | **DONE on `main`** | PR #255; architecture remains non-authorizing |
| G2 adjudication machinery | **DONE on `main`** | PR #255; no natural episode census has run |
| G3 probe construction machinery | **DONE on `main`** | PR #255; no live key or study sample exists |
| G4 analysis/statistical machinery | **DONE on `main`** | Kiro PASS at exact `fa7d68b`; focused 98 tests + 8 subtests; Pylint 10/10 |
| G5 dry-run/fixture verification | **LANDED; METHODOLOGY GATE REOPENED — C** | Original composition defect remains in landed code; corrective design has Kiro PASS at `b6a1ccf` |
| G5C corrective implementation/dry-run | **AUTHORIZED — NOT STARTED** | Cursor may modify only the handoff allowlist on `fix/2026-08-30-naturalistic-g5c-corrective`; stop for exact-tip Kiro review |
| G6 prospective study freeze and later T7–T11 gates | **NOT AUTHORIZED — Ryan LOCKED** | Blocked on G5 corrective design, implementation, and fresh independent PASS before any separate Ryan grant |
| Product disposition | **UNAVAILABLE** | T10 is the only later stage permitted to produce one |

## 5. Your Role (read this to know what you're here to do)

G5 code remains landed on `main`, and methodology gate **C** remains open until
the accepted corrective is implemented and freshly reviewed. Ryan's acceptance
is design-only.

If Ryan sent you for **G5C implementation**, read the dedicated Cursor handoff,
start the required new worktree/branch from accepted carrier `c089070`, modify
only its strict allowlist, run synthetic verification, push, and stop for fresh
exact-tip Kiro review. If Ryan sent you for **G6 or live study**, stop. G6
remains closed until the corrective is implemented and independently PASSed,
followed by a fresh explicit Ryan grant.

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
- [x] Independent Claude/ChatGPT methodology review reopens G5 at gate C.
- [x] ChatGPT advises Ryan on the six corrective methodology decisions.
- [x] Ryan decides the corrective estimand, missingness, opportunity, failure,
      disposition, and environment policies.
- [x] Ryan authorizes a bounded Codex architecture/execution corrective.
- [x] Codex commits the co-versioned corrective amendment at `b6a1ccf`.
- [x] Kiro accepts exact corrective revision `b6a1ccf` with two nonblocking
      wording corrections.
- [x] Codex applies only those wording corrections at `fde840b`.
- [x] Ryan accepts the Kiro-PASSed corrected methodology design as design-only.
- [x] Ryan separately grants bounded Cursor G5 corrective implementation.
- [x] Codex creates the strict-allowlist Cursor implementation handoff.
- [ ] Cursor implements and pushes the bounded G5C corrective on the required
      new branch.
- [ ] Fresh independent review restores G5 PASS on the corrected scope.
- [ ] Ryan separately authorizes G6 prospective freeze and later T7–T11 gates.
- [ ] Only a fully authorized T10 path may produce a product disposition.

## 7. Hard Stops (models cannot cross)

| Stop | Owner / invariant | What it blocks |
|---|---|---|
| G4 ceiling | Analysis contract; T10-only disposition rule | Any product conclusion from G1–G4 code or fixtures |
| G5C implementation | Ryan grant + strict Cursor handoff allowlist | Any file outside the allowlist, live evidence, or continuation past exact-tip Kiro review |
| G6 grant | Ryan after corrected G5 PASS | Prospective study freeze and every live gate; not implied by landed code or synthetic results |
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
| Current G5C Cursor implementation handoff | [`../inter-model/CODEX-2026-08-30-naturalistic-g5c-cursor-handoff.md`](../inter-model/CODEX-2026-08-30-naturalistic-g5c-cursor-handoff.md) |
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
- 2026-08-30 — Codex: ingested Claude/ChatGPT methodology review; gate is C, G5 corrective design is Ryan-gated, and G6 remains closed.
- 2026-08-30 — Ryan: requested focused ChatGPT advice on the six corrective methodology decisions before choosing or authorizing a plan.
- 2026-08-30 — Codex: translated Ryan-accepted D1–D6 into exact corrective revision `b6a1ccf`; independent Kiro review is next and all implementation/live gates remain closed.
- 2026-08-30 — Kiro/Codex: Kiro PASSed exact `b6a1ccf` with two nonblocking axis-wording corrections; Codex applied only those at `fde840b`; Ryan accept/revise is next.
- 2026-08-30 — Ryan: accepted corrected design `b6a1ccf` + wording-only `fde840b` as design-only; G5C implementation and all live/T0 authority remain separately gated.
- 2026-08-30 — Ryan/Codex: Ryan granted the strict bounded G5C file/test scope; Codex routed Cursor to a new implementation branch and exact-tip Kiro stop; G6/live authority remains closed.

**TL;DR:** [Arc Naturalistic ConvMem product-value evaluation] G1–G5 remain on
`main`, and gate C remains open. G5C implementation is now narrowly authorized
but `NOT_STARTED` under the strict Cursor handoff; G6/T0, live evidence, corpus
access, scoring, parameters, and product conclusions remain closed.

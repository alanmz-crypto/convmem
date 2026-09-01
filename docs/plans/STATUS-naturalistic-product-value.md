# Arc Brief — Naturalistic ConvMem Product-Value Evaluation

> **Every model working on this arc must read this file at session start.**
> After reading, state: "Goal: [one sentence]. My role: [what I'm here to do].
> The system currently: [what exists]. Missing: [what doesn't exist yet]."

**Arc:** Naturalistic ConvMem product-value evaluation

**Current state:** G1–G5 are landed on `main`; classification remains
**methodology validation, not product evidence**. Historical PRE-G6 V2
authority is preserved at commit
`9f4791c2744c02d742fdb9c0fa1e9dd150591ac1` and RFC 8785 digest
`917ad129a4f9641f65b809e143467b1f2c48ea41203166365b8e3efd459b627e`.
The proposed V3 successor corrects only V2's contradictory multiplicity
inequality and awaits outcome-blind independent authority review plus explicit
Ryan acceptance. V2-04 is closed at descendant tip
`872390db8ac76157b3a0223d947a8eb5da66473c`; a separate V2-04A output-interface
corrective is required before V2-05 may be reconsidered. **G6 and T0 remain
unauthorized.**

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
| `docs/plans/ARCHITECTURE-naturalistic-product-value.md` | V3 explanatory projection; non-authorizing and not independently normative |
| `docs/plans/EXECUTION-naturalistic-product-value.md` | V3 stage/grant projection; non-authorizing and not independently normative |
| `docs/plans/artifacts/naturalistic-pre-g6-contract-v3.json` | Sole proposed successor authority; awaits independent review and Ryan acceptance |
| V3 schema, conformance JSON, validator, amendment manifest, and `.sha256` sidecar | Exact-byte erratum package; 12 stages, 20 decisions, 20 invariants, 50 controls, 35 conformance cases |
| `docs/plans/artifacts/naturalistic-pre-g6-contract-v2.json` and companions | Immutable historical V2 authority; not mutated by the erratum |
| `naturalistic-pre-g6-contract-v1.json` and sidecar | Superseded exact-review baseline; must not be implemented |
| `eval_naturalistic/contracts.py`, `base.py`, `enums.py`, `digest.py` | G1 contract and identity substrate on `main` |
| `eval_naturalistic/adjudication.py` and fixtures | G2 target census/adjudication scaffold on `main` |
| `eval_naturalistic/probe_construction.py` and fixtures | G3 probe/key construction scaffold on `main` |
| `eval_naturalistic/analysis.py` and fixtures | G4 bounded analysis/statistical machinery on `main`; reviewed bytes unchanged at `fa7d68b` |
| `eval_naturalistic/dry_run.py`, `dry_run_mechanics.py` | G5 synthetic T0–T10 dry-run harness; not a live study controller |
| `tests/test_naturalistic_{contracts,adjudication,probe,analysis,dry_run}.py` | Focused G1–G5 coverage on `main` |
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
| PRE-G6 exact contract | **V3 MULTIPLICITY ERRATUM PROPOSED — NOT ACCEPTED** | Successor package awaits outcome-blind independent review, then explicit Ryan acceptance |
| V2 runtime implementation | **V2-04 CLOSED; V2-04A REQUIRED** | Separate interface corrective and independent review must precede reconsidering V2-05 |
| G6 prospective study freeze and later T7–T11 gates | **NOT AUTHORIZED — Ryan LOCKED** | Closed through authority review, V2-04A, any later implementation, and independent verification; then Ryan explicit G6 grant if warranted |
| Product disposition | **UNAVAILABLE** | T10 is the only later stage permitted to produce one |

## 5. Your Role (read this to know what you're here to do)

The next lane is an **outcome-blind independent exact-byte review** of the V3
JSON, schema, 35 conformance cases, validator, sidecar, amendment manifest, and
explanatory projections at one exact corrective SHA. The reviewer must verify
that only multiplicity inequality consistency changed and must not trust this
materializer's self-checks.

After an authority-review PASS, Ryan alone may accept the V3 successor. The
separate bounded V2-04A implementation corrective and its independent review
must then close before V2-05 is reconsidered. G6/T0 remains later and separate.

If sent for **G6 or live study**, stop. G6 remains closed. Do not access natural
evidence, choose live values, build the live registry, run agents, score, or
interpret synthetic `0.3` as product evidence.

## 6. What Remains Before "Live"

- [x] Land G1–G4 methodology package on `main` (PR #255).
- [x] Record exact-SHA Kiro PASS and focused verification.
- [x] Reconcile canonical routing and add this arc brief.
- [x] Ryan explicitly grants G5 synthetic dry-run/fixture verification.
- [x] Cursor implements only the granted G5 dry-run; retain synthetic-only data.
- [x] Independent Kiro review accepts the exact G5 candidate SHA (`23b2495927a9891070c7c294e45bdb641eaab352`).
- [x] Ryan merges G5 (squash-merged PR #259).
- [x] Sol exact-review V1 and identify contract blockers.
- [x] Materialize the isolated V2 corrective with Issue #263 provenance and no G6 lane merge.
- [x] Materialize the prospective V3 multiplicity-authority erratum without mutating V2.
- [ ] Outcome-blind independent exact-byte review of one V3 corrective SHA.
- [ ] Ryan successor-acceptance decision after authority-review PASS.
- [ ] Separately bounded V2-04A implementation corrective, if Ryan authorizes it.
- [ ] Independent exact-tip V2-04A verification.
- [ ] Reconsider V2-05 only after the preceding gates close.
- [ ] Only then may Ryan reconsider G6 prospective freeze and later live gates.
- [ ] Only a fully authorized T10 path may produce a product disposition.

## 7. Hard Stops (models cannot cross)

| Stop | Owner / invariant | What it blocks |
|---|---|---|
| G4 ceiling | Analysis contract; T10-only disposition rule | Any product conclusion from G1–G4 code or fixtures |
| V3 successor acceptance | Outcome-blind independent review, then Ryan | Any dependent V2-04A/V2-05 authority; materialization is not self-certification |
| G6 grant | Ryan only after authority acceptance, implementation, and independent verification | Prospective study freeze and every live gate; not implied by G5 landing, V3 materialization, or synthetic results |
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
| Sole proposed V3 successor authority | [`artifacts/naturalistic-pre-g6-contract-v3.json`](artifacts/naturalistic-pre-g6-contract-v3.json) |
| V3 schema / conformance / validator / amendment manifest | [`artifacts/naturalistic-pre-g6-contract-v3.schema.json`](artifacts/naturalistic-pre-g6-contract-v3.schema.json), [`artifacts/naturalistic-pre-g6-contract-v3.conformance.json`](artifacts/naturalistic-pre-g6-contract-v3.conformance.json), [`artifacts/validate-naturalistic-pre-g6-contract-v3.mjs`](artifacts/validate-naturalistic-pre-g6-contract-v3.mjs), [`artifacts/naturalistic-pre-g6-contract-v3.amendment.json`](artifacts/naturalistic-pre-g6-contract-v3.amendment.json) |
| Immutable historical V2 authority | [`artifacts/naturalistic-pre-g6-contract-v2.json`](artifacts/naturalistic-pre-g6-contract-v2.json) |
| Explanatory architecture | [`ARCHITECTURE-naturalistic-product-value.md`](ARCHITECTURE-naturalistic-product-value.md) |
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
- 2026-08-30 — Ryan: squash-merged routing refresh PR #261 to `676d6b5`; locked G6 closed pending the required independent PRE-G6 exact review regardless of synthetic results.
- 2026-08-31 — Sol: materialized the Issue-#263-rooted PRE-G6 V2 exact-contract corrective after V1 exact review required correction; fresh-seed review next, with G6 separate and closed.
- 2026-08-31 — Codex Sol: materialized a prospective V3 successor correcting only V2 multiplicity inequality consistency; independent authority review and Ryan acceptance are next.

**TL;DR:** PRE-G6 V3 proposes only the multiplicity inequality erratum and now
awaits independent authority review plus Ryan acceptance; V2-04A, V2-05, and
G6/T0 remain separately gated.

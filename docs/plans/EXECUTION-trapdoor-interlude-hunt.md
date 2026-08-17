# Execution Plan — Arc Trapdoor Interlude Hunt

```text
Status: DRAFT — NOT AUTHORIZED FOR IMPLEMENTATION
Arc:    Arc Trapdoor Interlude Hunt
Branch: plan/2026-08-16-trapdoor-interlude-hunt
Base:   d10e1d5f4993f60a32142115f8b8c0f0f9ea4481
```

## Consequence

This plan produces five planning documents: a trust contract, an evidence
audit, and a bridge back to the frozen Trapdoor T3 design. It authorizes no
runtime or operational work.

## Phase 0 — Preconditions and isolation

Completed before this branch was created:

1. GitHub CodeQL/P0 closeout was verified on `main` at
   `d10e1d5f4993f60a32142115f8b8c0f0f9ea4481`.
2. The Interlude branch was created separately from current `main`.
3. The Trapdoor T3 branch is reference input only.

Stop if the reviewed main SHA, CodeQL/P0 closeout, or branch lineage cannot be
verified. Do not substitute local `convmem ask` output for current GitHub
authority.

## Phase 1 — FF1/T1 Trust Baseline

Read the parent roadmap, Trapdoor T3 plans, complete-data and CG-1/CG-2
contracts, restore documentation, writer census, and builder-reference
digests. Draft the canonical claim matrix in
`TRAPDOOR-INTERLUDE-MATRICES.md`.

For each claim, identify the product promise, scope, acknowledgement boundary,
failure consequence, severity, owner, oracle, degraded state, and assumptions.
Use repository vocabulary. Do not turn `doctor PASS` into a reliability claim.
Do not introduce numerical operational targets.

### FF1 stop condition

Stop for Ryan review when every catastrophic/critical claim has one owner, one
oracle, and one degraded state, and the vocabulary has no unresolved collision
between acknowledgement, durability, provenance, truth, ranking, serving, or
action authority.

Do not start FF2 acceptance before Ryan accepts FF1.

## Phase 2 — FF2/T2 Existing Evidence + Failure-Gap Matrix

After FF1 acceptance, inspect each accepted claim against existing evidence.
Record exact paths, test names, plan revisions, implementation SHAs, and
evidence limits. Classify each claim `SUFFICIENT`, `PARTIAL`, `ABSENT`, or
`STALE`.

Reuse existing proof whenever it covers the same property and failure window.
For a gap, name only the smallest missing oracle. Do not write or run a broad
fault campaign merely because it would be reassuring.

### FF2 stop condition

Stop for Ryan review when every claim has one evidence classification, every
critical gap has an owner and degraded state, and duplicate oracles have been
rejected by distinct failure window, owner, boundary, transition, or recovery
condition.

## Phase 3 — Trapdoor Bridge

After FF2 acceptance, map each relevant T1 claim through its T2 evidence to the
existing Trapdoor T3 requirement and VERIFY row. Preserve R8.2, V4m, the
mutator-census precondition, migration/version boundaries, identity rules, and
projection/authority separation.

If a contradiction appears, write a bounded finding containing:

1. affected T1 claim;
2. T2 evidence or missing oracle;
3. exact T3 requirement/row affected; and
4. smallest planning correction.

Do not edit the Trapdoor branch from this arc and do not grant T3 execution.

## Evidence discipline

- Bind every review to the exact Interlude commit SHA.
- Keep all VERIFY rows `PENDING` until evidence is actually collected under an
  authorized phase.
- Treat ChatGPT, Kiro, and Copilot reviews as recommendations; Ryan accepts.
- Record no runtime, live-data, Chroma, Shadow, R2b, CG-2, migration, or cloud
  operation.
- Do not create auxiliary documents beyond the five named artifacts unless a
  reviewer demonstrates a real separation need.

## Definition of done

```text
CODEQL_P0_CLOSED
∧ FF1_CLAIM_MATRIX_ACCEPTED
∧ EVERY_CATASTROPHIC_OR_CRITICAL_CLAIM_HAS_OWNER
∧ EVERY_CATASTROPHIC_OR_CRITICAL_CLAIM_HAS_ORACLE
∧ EVERY_CATASTROPHIC_OR_CRITICAL_CLAIM_HAS_DECLARED_DEGRADED_STATE
∧ FF2_EVIDENCE_GAP_MATRIX_ACCEPTED
∧ DUPLICATE_ORACLES_REJECTED
∧ TRAPDOOR_BRIDGE_COMPLETE
∧ NO_ARBITRARY_SLO_NUMBERS
∧ NO_RUNTIME_OR_OPERATIONAL_WORK
∧ RYAN_INTERLUDE_LOCK
```

**TL;DR:** FF1 precedes FF2; both precede the bridge; none grants Trapdoor
implementation.

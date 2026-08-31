# [Arc Naturalistic ConvMem product-value evaluation] Kiro Review Handoff — G5 Corrective Amendment

**Date:** 2026-08-30

**Mode:** Independent architecture/execution review only. No implementation,
parameter selection or freeze, G6/T0 grant, natural evidence access, Agent A/B,
scoring, or product interpretation.

**Exact review revision:** `b6a1ccff82ef2456d5b65be122e2e714f84f5ad2`

**Branch:** `plan/2026-08-30-naturalistic-g5-corrective-amendment`

## Context brief

**Who:** Codex authored the amendment after Ryan accepted ChatGPT's D1–D6
recommendations as the corrective design direction. An independent Luna
falsification pass reviewed the choices and a second pass found no remaining
blocking ambiguity in the draft.

**What:** One co-versioned architecture/execution amendment that repairs G5's
composition contract and defines the smallest later `G5C` corrective slice.

**When:** After Claude overturned the prior synthetic G5 PASS because
`run_g5_end_to_end()` labeled `T0_T2` successful with an incomplete prospective
frame. G1–G5 remain landed on `main`; the current methodology verdict is C.

**Why:** The prior orchestration could bypass a stricter isolated validator.
The larger review also found treatment-dependent evaluability, denominator
drift, invalidity-as-missingness, scorer disclosure, and paired-environment
asymmetry capable of producing a wrong product conclusion.

**How:** Review the two files together at the exact revision. Return one
architecture/execution verdict and bounded corrections. Do not inspect natural
study evidence or authorize implementation.

## Accepted direction under review

1. Capture/evaluability are co-primary process outcomes. The fixed registry
   denominator is preserved; complete-pair effect degrades to prospectively
   frozen deterministic bounds and then inconclusive bounds.
2. The first study has no authoritative scalar. Its result is opportunity
   prevalence, complete-pair effect/bounds, and complete failure accounting.
3. The sealed raw-evidence `TargetRegistry` is the sole episode-opportunity
   denominator authority and is fixed before C0/C1 execution.
4. Valid missing outcomes are boundable; protocol, environment, isolation,
   lineage, registry, freeze, and scorer-integrity failures are invalid and
   never bounded.
5. Orthogonal validity, information, missingness/comparability, scorer-integrity,
   and scorer-reliability states derive the final disposition by frozen
   precedence.
6. C0/C1 replay one sealed pre-trial state in fresh sessions. Mechanical
   comparison establishes C1 ConvMem access as the sole intended difference;
   mutable external services are replayed identically or excluded.

## Load-bearing corrective mechanics

- T0 completeness is validated from canonical serialized bytes, not stage
  success or completion flags; placeholder values fail.
- A second responsible validator re-derives the digest from the exact artifact
  handed downstream and verifies study-data isolation mechanically.
- Natural ConvMem capture, per-arm trial-evidence capture, and per-arm score
  evaluability remain separate axes.
- Bounds use one `episode_opportunity_id` per target-bearing episode; target
  rows remain secondary inputs to frozen within-episode aggregation.
- Scorer unblinding/package contamination is `INVALID`; valid below-threshold
  scorer disagreement is `BLOCKED`; an isolated secondary disagreement may be
  `DIAGNOSTIC`.
- `G5C` is a bounded corrective over the landed baseline, not a retroactive G4
  grant. Its `StageBoundaryLedger` records every individual T0–T10 boundary;
  grouped `T0_T2`/`T3_T5`/`T6_T7`/`T8_T10` statuses are summaries only.
- Synthetic negatives cover incomplete/false-complete frames, stage-local
  corruption, boundary assumptions, artifact tamper, arm-dependent registry
  rules, asymmetric valid missingness, invalid-versus-boundable separation,
  disposition precedence, and replay mismatch.

## Required Kiro review

Return `PASS`, `FAIL`, or `CORRECTIVE REQUIRED` at the exact revision and answer:

1. Does the structured result tuple answer the intended product question
   without silently transporting complete-pair effects to missing episodes?
2. Are valid missingness and protocol/environment/scorer invalidity separated
   completely enough that invalid evidence can never enter bounds?
3. Does the sealed registry remain the sole episode-opportunity authority at
   every downstream stage?
4. Are scorer integrity and scorer reliability separated and ordered correctly?
5. Does paired replay establish causal treatment symmetry without prescribing
   unnecessary infrastructure?
6. Does the individual `StageBoundaryLedger` plus injected-fault matrix repair
   the original isolated-validator/orchestration-bypass defect throughout G5?
7. Are all remaining live values and operational identities legitimately
   deferred to a later T0 decision rather than hidden in prose placeholders?
8. Does the gate remain C, or does either identification contingency require D:
   opportunity authority needs treatment/capture-derived evidence, or paired
   replay cannot exclude uncontrolled environment differences?

For every failure, cite the exact file/section, the violated invariant, and the
smallest correction. Distinguish a G5C blocker from a T0 prerequisite or
nonblocking hardening item.

## Review surfaces

- [`ARCHITECTURE-naturalistic-product-value.md`](../plans/ARCHITECTURE-naturalistic-product-value.md)
- [`EXECUTION-naturalistic-product-value.md`](../plans/EXECUTION-naturalistic-product-value.md)
- [`STATUS-naturalistic-product-value.md`](../plans/STATUS-naturalistic-product-value.md)
- Historical defect/synthesis context:
  [`CODEX-2026-08-30-naturalistic-g5-methodology-corrective-handoff.md`](CODEX-2026-08-30-naturalistic-g5-methodology-corrective-handoff.md)
- Accepted D1–D6 advisory packet:
  [`CHATGPT-2026-08-30-naturalistic-g5-corrective-advisory-handoff.md`](CHATGPT-2026-08-30-naturalistic-g5-corrective-advisory-handoff.md)

## Scope firewall

This review does not grant `G5C` implementation. A PASS returns to Ryan for an
accept/revise decision and, only if separately granted, a bounded implementation
handoff. It grants no G6/T0 activity, parameter freeze, natural corpus/index
inspection, Agent A/B, scoring, or product conclusion.

**TL;DR:** [Arc Naturalistic ConvMem product-value evaluation] Independently
review architecture and execution together at `b6a1ccf`. Decide whether D1–D6
form a coherent G5C contract that repairs the composition defect while keeping
all implementation and live-study authority closed.

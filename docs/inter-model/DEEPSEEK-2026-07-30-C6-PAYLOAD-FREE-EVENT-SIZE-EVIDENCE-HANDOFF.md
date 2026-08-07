# DeepSeek handoff — C6 payload-free event-size evidence design

**Lane:** DeepSeek / Crush investigation and design critique.  
**Date:** 2026-07-30.  
**Mode:** Review and planning only; do not implement or operate live state.

## Current state

C7 is merged to `main` at
`869aec7431b600ed7602a7a64ff98502340be066` (Shadow writer-census merge,
PR #134). It will eventually provide C6 with a final private census report
containing peak writer concurrency and conservative opens/day. Shadow remains
disabled; activation remains forbidden.

The remaining C6 input gap is **fresh event-size evidence**. C6 needs P50,
P95, maximum synthetic event sizes and a SHA-256 of redacted evidence. The
previous draft suggested measuring a live Shadow ledger. That is not allowed:
Shadow is disabled, no live Shadow artifacts may be created to manufacture
evidence, and C6 must not read production Chroma payloads.

## Objective

Produce an execution-ready recommendation for a fresh, payload-free source of
C6 event-size evidence. If no credible source exists without a small additional
implementation slice, say so explicitly and define the smallest safe slice;
do not invent measurements or authorize a workaround.

## Fixed constraints

- No Shadow activation, ledger creation, manifest creation, or configuration
  change.
- No production Chroma document, metadata, embedding, or source-content read.
- No network, service control, backup change, or Chroma schema change.
- The resulting evidence may retain only numeric lengths, counts, schema /
  encoder revision, timestamp, provenance, and SHA-256—not content or stable
  identifiers.
- Evidence must be fresh at the time C6 is requested, reproducible, private,
  and independently reviewable.
- `shadow_canary.py` remains scratch-only and its production Chroma root is
  overlap-refusal only. Preserve that guarantee.

## Required investigation

Review the merged C6/C7 sources and the Shadow event/ledger encoder contracts:

- `shadow_canary.py`
- `shadow_sink.py`
- `shadow_ledger.py`
- `writer_census.py`
- `docs/plans/PHASE0-SHADOW-CONTRACT.md`

Evaluate only mechanisms that meet the fixed constraints, for example a
deterministic structural estimator based on public event-schema bounds, or a
new hermetic generator whose inputs are non-payload declared dimensions. Do
not assume either is adequate; assess representativeness, circularity, and the
risk of underestimating an append size.

## Required output

1. **Feasible options** — at least two options, each with data source,
   freshness method, payload/privacy proof, representativeness limits, and
   failure modes.
2. **Recommendation** — one preferred option, or an explicit HOLD if no
   option provides credible P50/P95/max values under the constraints.
3. **Evidence contract** — exact redacted JSON fields, hashing/canonicalization,
   required mode/ownership, operator command boundary, and independent-review
   checks.
4. **If implementation is required** — bounded slice, allowed/prohibited
   files, tests (including negative privacy controls), rollback, and merge-
   disabled requirement. Do not write code.
5. **C6 interaction** — how the evidence feeds the existing CLI without
   weakening C6's scratch-only isolation or allowing manual census metrics.
6. **Independent C7-report review checklist** — after the seven-day window,
   define how a reviewer validates the exact report SHA, payload-free fields,
   revision/root/gate bindings, and metric plausibility before Ryan may request
   C6.

End with exactly one verdict:

```text
C6 EVENT-SIZE EVIDENCE DESIGN READY
```

or:

```text
C6 EVENT-SIZE EVIDENCE HOLD — <specific unresolved constraint>
```

## Prohibited

- Do not start C7, generate a report, run C6, enable Shadow, or activate
  Shadow.
- Do not modify code, tests, docs, configs, production data, or services.
- Do not treat a chat claim, a synthetic estimate without an approved basis, or
  a stale historical artifact as fresh evidence.


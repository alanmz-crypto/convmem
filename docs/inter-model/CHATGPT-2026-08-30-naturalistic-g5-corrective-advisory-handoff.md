# [Arc Naturalistic ConvMem product-value evaluation] Handoff — ChatGPT Corrective Advisory

**Date:** 2026-08-30

**From:** Ryan, prepared by Codex Sol

**For:** ChatGPT, adversarial research-methodology reviewer

**Authority:** Advisory only. Ryan retains every design choice and grant.

## Role

Review the reopened G5 methodology gate and advise Ryan on six load-bearing
choices. Give one recommended default for each choice, its accepted downside,
and the evidence that would overturn it. Do not implement, select live numerical
parameters, inspect natural study evidence, authorize G6/T0, or draw a product
conclusion.

## Why Ryan needs your advice

G1–G5 are landed on `main`, but G5's methodology gate is now **C — corrective
required**. The decisive implementation defect is compositional:
`run_g5_end_to_end()` can label its synthetic `T0_T2` stage successful even
though the frame contains only two of the eight required information slots.

Claude's broader review then identified treatment-dependent evaluability,
ambiguous product estimands, structural scorer unblinding, incomplete freeze
semantics, and generic non-estimability as risks that could invalidate a later
product conclusion. Codex Sol and a delegated Luna-high T9 falsification pass
agree that these risks should be resolved in one bounded amendment—not by
patching only the local `T0_T2` bug.

No live-study authority exists. Ryan wants your recommendation before deciding
the corrective architecture.

## Facts and constraints to preserve

1. The full prospectively selected episode frame remains the population
   denominator. Zero-target, incomplete, failed, and non-evaluable episodes do
   not disappear.
2. The landed design already has an arm/result-blind raw-evidence target registry.
   Treat it as the current opportunity authority unless you show why it cannot
   serve that role; do not casually add a duplicate opportunity subsystem.
3. Keep three distinct axes:
   - natural ConvMem capture state;
   - C0/C1 trial-evidence capture or instrumentation state;
   - C0/C1 score evaluability.
4. The paired continuation score is normalized to `[0,1]`, enabling
   support-based worst/best-case bounds for some genuinely missing scores.
5. Protocol, environment, isolation, or lineage failures are not automatically
   ordinary missing scores with meaningful latent outcomes.
6. `P_opp × Effect_evaluable`, with `P_opp` defined over all opportunities,
   assumes the evaluable subset's effect transports to non-evaluable
   opportunities. It does not assign zero effect to those opportunities.
7. Validator independence means recomputing from serialized manifest bytes
   without trusting orchestration status. Canonical serialization and digest
   primitives may remain a small shared trusted kernel.
8. The existing architecture already defines Ryan/controller/recorder/
   adjudicator/probe-author/leakage-reviewer/Agent-B/scorer/model-lane roles.
   Recommend only new separations required by the corrective.
9. Gate C remains in force. D/full redesign is only a contingency if a clean
   pre-C0/C1 opportunity rule or usable missingness estimand cannot be defined.

## Decisions — recommend one answer for each

### D1. Missingness and treatment-dependent evaluability

Choose the default analysis policy:

- support-based bounds plus per-arm process accounting;
- a predeclared composite failure outcome;
- tolerance-only non-comparability;
- or a better fourth option.

Specify whether the complete-pair effect remains reportable, when bounds become
decision-informative versus blocked, and whether any tighter Lee/principal-
stratum analysis is justified without a Ryan-frozen monotonicity assumption.

### D2. Product-value scalar

Should the study avoid a single headline scalar and report opportunity
prevalence, evaluability coverage, conditional effect, and bounds together?
If you recommend a scalar, give its exact estimand and every assumption required
to interpret it. Distinguish:

- `P_opp × Effect_evaluable`;
- `P_evaluable × Effect_evaluable`;
- an all-opportunity bounded effect;
- any composite outcome you recommend.

### D3. Opportunity authority

Should the corrective bind and strengthen the existing raw-evidence target
registry, or create a distinct opportunity-adjudication artifact? Explain the
minimum input view that makes adjudication genuinely pre-C0/C1, arm-blind,
capture-blind, and result-blind.

### D4. Failure semantics

Define which failures may enter missing-score bounds and which must instead
route to `DIAGNOSTIC` or `INVALID`. At minimum address:

- valid trial with one unscorable arm;
- Agent-B failure under the frozen stopping rule;
- trial evidence/instrumentation loss;
- environment asymmetry or carryover;
- scorer unreliability;
- isolation breach;
- manifest/hash/lineage mismatch;
- protocol violation.

### D5. Disposition taxonomy and precedence

Advise whether the existing top-level enum can remain:

`INVALID`, `DIAGNOSTIC`, `BLOCKED_NON_ESTIMABLE`, positive, null/equivalent,
and negative.

If it can, specify the minimum machine-readable reason taxonomy and precedence.
The final system must distinguish insufficient opportunities, asymmetric
capture/evaluability, uninformative bounds, scorer failure, environment failure,
protocol failure, and integrity failure without using
`blocked_non_estimable` as an unexplained sink.

### D6. Minimum environment guarantee

Choose the least-complex defensible C0/C1 environment contract. Address:

- per-pair snapshot/reset behavior;
- shared writable caches, database rows, rate-limit state, and external tools;
- time-varying API or repository state;
- execution-order randomization and carryover diagnostics;
- scorer-presentation order as a separate concern;
- C0 denial versus C1 ConvMem mount as the sole intended treatment difference.

## Secondary checks

After D1–D6, advise briefly on:

- whether the second responsible validator is required at G5 or only before T0;
- the minimum injected-fault tests for freeze/hash/handoff integrity;
- whether raw latency/tool traces should be mechanically analyzed rather than
  shown to subjective scorers;
- the minimum prompt-injection boundary if an LLM scores untrusted transcripts;
- what exact finding would escalate C to D/constructed-panel redesign.

## Required output

Return:

1. **Executive recommendation** — one sentence per D1–D6, with no neutral menu.
2. **Decision matrix** — recommendation, rationale, accepted downside, evidence
   that would overturn it, and whether it blocks G5 or only T0.
3. **Corrections to prior reasoning** — identify any Claude, Codex Sol, or Luna
   claim you reject or narrow.
4. **Smallest coherent amendment** — exact architecture/execution sections that
   must change before code.
5. **Gate verdict** — C or D, plus the precise escalation condition.
6. **Ryan action list** — decisions Ryan must explicitly lock versus matters the
   architecture can safely determine without another choice.

## Do not do

- Do not write code, tests, schemas, configuration, or generated artifacts.
- Do not choose numerical margins, tolerances, sample size, seed, or study window.
- Do not inspect the natural corpus, Chroma, study-derived statistics, or live
  evidence.
- Do not authorize planning, implementation, G6/T0, Agent A/B, scoring, or a
  product disposition.
- Do not restart settled G1–G4 mechanics unless a finding directly invalidates
  them.
- Do not treat model-family diversity alone as methodological independence.

## Read these first

| Purpose | Path |
|---|---|
| Current corrective synthesis and Luna findings | [`CODEX-2026-08-30-naturalistic-g5-methodology-corrective-handoff.md`](CODEX-2026-08-30-naturalistic-g5-methodology-corrective-handoff.md) |
| Current arc state and hard stops | [`../plans/STATUS-naturalistic-product-value.md`](../plans/STATUS-naturalistic-product-value.md) |
| Landed architecture and role/access model | [`../plans/ARCHITECTURE-naturalistic-product-value.md`](../plans/ARCHITECTURE-naturalistic-product-value.md) |
| Landed execution gates and adversarial matrix | [`../plans/EXECUTION-naturalistic-product-value.md`](../plans/EXECUTION-naturalistic-product-value.md) |
| G5 orchestration containing the composition defect | [`../../eval_naturalistic/dry_run.py`](../../eval_naturalistic/dry_run.py) |
| G5 focused tests | [`../../tests/test_naturalistic_dry_run.py`](../../tests/test_naturalistic_dry_run.py) |
| Terminal enums and frame contracts | [`../../eval_naturalistic/enums.py`](../../eval_naturalistic/enums.py), [`../../eval_naturalistic/contracts.py`](../../eval_naturalistic/contracts.py) |
| Analysis and information-gate behavior | [`../../eval_naturalistic/analysis.py`](../../eval_naturalistic/analysis.py) |

**TL;DR:** [Arc Naturalistic ConvMem product-value evaluation] Advise Ryan with
one recommendation for each of D1–D6, identify what would overturn each choice,
and return a C-or-D verdict. Analysis only; no implementation or G6/T0 authority.

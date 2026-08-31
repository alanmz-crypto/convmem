# [Arc Naturalistic ConvMem product-value evaluation] G5 Methodology Corrective Handoff

**Date:** 2026-08-30

**Author:** Codex Sol, with delegated Codex Luna T9 falsification support

**For:** Codex architecture/planning lane; then Kiro exact-revision design review

**Authorization:** Ryan, 2026-08-30 — select the best collaborator, delegate down where possible, and create a handoff

---

## Resume state

| Field | Value |
|---|---|
| **State** | `BLOCKED_ON_RYAN` — decision packet ready; corrective-plan authoring not yet granted |
| **Branch** | `plan/2026-08-30-naturalistic-g5-methodology-corrective-handoff` |
| **Tip SHA** | Branch tip containing this handoff |
| **Push status** | Pushed to origin after each commit |
| **PR** | Not opened; Ryan did not authorize PR creation |
| **Ryan GATE** | Decide the six methodology choices below, then explicitly authorize a bounded architecture/execution corrective if desired |
| **Track A ingest** | Codex rollout indexed under the session-start protocol |

## Consequence for Ryan

The prior G5 synthetic dry-run remains landed on `main`, but its methodology
gate is reopened. Claude found that `run_g5_end_to_end()` can label `T0_T2`
successful while the synthetic frame contains only two of the eight required
information slots. ChatGPT revised the gate to **C — corrective required before
any G6/T0 grant**. A delegated Codex Luna T9 falsification pass independently
agreed with C and found no basis for D/full redesign yet.

**Who:** Ryan owns every methodology choice and later grant; Codex may author a
corrective plan only after authorization; Kiro reviews the exact plan revision;
Cursor implements only after a later bounded grant.

**What:** One corrective amendment spanning estimand, validator/state,
disposition/roles/environment/scoring, and G5 acceptance.

**When:** Before any G5 corrective code and before any G6/T0 activity.

**Why:** Prevent post-treatment selection, incomplete prospective state, or
unblinded scoring from producing a confidently wrong product conclusion.

**How:** Resolve the decisions below, amend the existing architecture rather
than layering duplicate subsystems, then require exact-revision review.

## Delegated collaborator and result

Codex Sol retained the load-bearing architecture judgment and delegated a
read-only falsification/mapping pass to **Codex Luna high**, the ConvMem ladder's
T9 comparison/signature tier. Luna inspected the landed architecture,
execution contracts, G5 orchestration, enums, and tests without editing files.

Luna's verdict was **REVISE / gate C**:

- treatment-dependent evaluability is the strongest validity threat, but a
  tolerance-only `non-comparable` cliff is too weak;
- `P_opp × Effect_evaluable` assumes transportability from evaluable to
  non-evaluable opportunities, not zero effect;
- validator independence should recompute from serialized bytes without
  duplicating canonical serialization and digest primitives;
- natural ConvMem capture, per-arm trial evidence capture, and per-arm score
  evaluability are separate axes and must not be collapsed;
- the existing raw-evidence target registry is already the opportunity concept;
  bind and strengthen it rather than inventing a second opportunity subsystem;
- role, reason-code, environment-reset, execution-order, and scorer-package
  contracts need one bounded planning amendment before code.

## Ryan decisions required

1. **Missingness policy:** bounds plus per-arm process accounting, a predeclared
   composite failure outcome, or tolerance-only non-comparability. Recommended:
   support-based bounds plus process accounting; tolerance is an alarm, not the
   sole estimator switch.
2. **Population scalar:** whether any single product-value scalar is required.
   Recommended: no headline scalar; report opportunity prevalence, evaluability
   coverage, conditional paired effect, and bounds together.
3. **Opportunity identity:** confirm that the existing arm/result-blind
   raw-evidence target registry is the sole opportunity authority.
4. **Failure semantics:** identify which missing scores have a meaningful latent
   bounded outcome and which protocol, environment, instrumentation, or lineage
   failures are `INVALID`/`DIAGNOSTIC` instead.
5. **Disposition reasons:** freeze a machine-readable reason taxonomy and
   precedence beneath the existing top-level terminal enum.
6. **Environment guarantee:** choose the minimum per-pair reset/isolation rule,
   including caches, writable state, time-varying tools, execution order, and
   carryover diagnostics.

## Smallest next planning slice

After Ryan decides and grants planning, Codex should produce one short amendment
package with four coordinated parts:

1. **Estimand decision** — define `P_opp`, evaluability coverage, the conditional
   effect, missingness bounds/composite alternative, and the status of every
   derived scalar.
2. **Validator/state contract** — require structural completeness from serialized
   manifest bytes, atomic freeze identity, independent downstream re-verification,
   and distinct transitions for ordinary incompleteness versus integrity breach.
3. **Disposition/role/environment/scorer matrix** — add reason-code precedence,
   only the necessary role separations, the three capture/evaluability axes,
   pair isolation/order rules, and condition-neutral scorer packaging. If an LLM
   scores, treat transcript content as untrusted prompt input.
4. **G5 acceptance matrix** — cover incomplete and placeholder frames, genuine
   `PENDING` fixtures, stage-local corruption, manifest tampering, mismatched
   handoff bytes, arm/result-dependent adjudication, and asymmetric missingness.

Kiro then reviews the exact amendment revision. Cursor receives no implementation
handoff unless Ryan accepts that reviewed design and separately grants a bounded
G5 corrective.

## Scope firewall

- No implementation, test, schema, runtime, or configuration edits.
- No G6/T0 grant or parameter selection.
- No natural evidence, corpus/index inspection for study design, Agent A/B,
  scoring, or product interpretation.
- No new opportunity subsystem, microservice, or duplicate hash/schema stack.
- No Lee/monotonicity assumption without an explicit Ryan decision.
- No bounds applied to protocol-invalid or environment-invalid executions as if
  they were ordinary missing scores.

## Acceptance criteria for the later corrective plan

- The complete episode frame remains the population denominator.
- Opportunity authority is pre-C0/C1, arm-blind, result-blind, and independent
  of capture/evaluability.
- Every non-scored opportunity has one frozen reason and remains reported.
- The estimand remains honest under treatment-dependent evaluability.
- Structural validation cannot be bypassed by an orchestration success flag.
- Integrity tampering is exercised by injected-fault tests, not inspection alone.
- Existing top-level terminal states carry explicit reason codes and precedence.
- G5 remains synthetic-only and cannot produce a product disposition or imply G6.

## Related evidence

| What | Path |
|---|---|
| Landed architecture and role model | [`../plans/ARCHITECTURE-naturalistic-product-value.md`](../plans/ARCHITECTURE-naturalistic-product-value.md) |
| Landed serial gates and adversarial matrix | [`../plans/EXECUTION-naturalistic-product-value.md`](../plans/EXECUTION-naturalistic-product-value.md) |
| Current arc snapshot | [`../plans/STATUS-naturalistic-product-value.md`](../plans/STATUS-naturalistic-product-value.md) |
| G5 implementation handoff | [`CURSOR-2026-08-30-naturalistic-product-value-g5-handoff.md`](CURSOR-2026-08-30-naturalistic-product-value-g5-handoff.md) |
| G5 orchestration | [`../../eval_naturalistic/dry_run.py`](../../eval_naturalistic/dry_run.py) |
| G5 focused tests | [`../../tests/test_naturalistic_dry_run.py`](../../tests/test_naturalistic_dry_run.py) |

**TL;DR:** [Arc Naturalistic ConvMem product-value evaluation] Gate remains C.
Ryan must resolve the six methodology choices before Codex authors one bounded
corrective amendment; Kiro reviews it, and no G5 code or G6/T0 activity follows
without later explicit grants.

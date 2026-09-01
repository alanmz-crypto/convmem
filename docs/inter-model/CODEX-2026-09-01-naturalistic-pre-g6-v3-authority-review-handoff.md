# [Arc Naturalistic ConvMem product-value evaluation] PRE-G6 V3 authority-review handoff

**Date:** 2026-09-01
**Author:** Codex Sol (canonical-authority corrective lane)
**For:** Kiro (outcome-blind independent authority review; read-only)
**Authorization:** Ryan, 2026-09-01 (requested the next-step handoff after the V3 erratum was prepared)

---

## Resume state

| Field | Value |
|---|---|
| **State** | `NOT_STARTED` — independent authority review pending |
| **Branch** | `fix/2026-08-31-naturalistic-v2-multiplicity-authority-erratum` |
| **Historical parent** | `9f4791c2744c02d742fdb9c0fa1e9dd150591ac1` |
| **Frozen review target** | `d5b03a6c8c53cfebbb7239ea4fb3ac31721e1ad7` |
| **Push status** | Frozen review target pushed to `origin` |
| **PR** | Not opened; this historical-root review branch is not a merge grant |
| **Ryan GATE** | Kiro PASS/FAIL at exact target → Ryan successor-acceptance decision |
| **Track A ingest** | Codex session indexed at the 2026-09-01 stopping point |

The commit containing this handoff is a routing-only carrier after the frozen
review target. Review the authority package and its projections exactly at
`d5b03a6c8c53cfebbb7239ea4fb3ac31721e1ad7`; do not substitute a later carrier
SHA. The handoff carrier must not change any V3 artifact, validator,
architecture, or execution-plan byte from the frozen target.

## What to build

**Nothing.** This is a read-only, outcome-blind independent review.

Kiro must determine whether the proposed PRE-G6 V3 successor corrects only the
V2 multiplicity inequality contradiction while preserving the locked V2
authority immutably and leaving every unrelated construct unchanged.

**Why this exists:** historical V2 says `lower_bound` must be at least
`known_count`, but `D_MULTIPLICITY_001` used validator wording equivalent to
`lower <= known`. V3 must establish exactly:

```text
0 <= known_count <= lower_bound
and either upper_bound is null or lower_bound <= upper_bound
```

Exact totals additionally require:

```text
known_count == lower_bound == upper_bound
plus exact/completeness proof authority
```

No `D_MULTIPLICITY_001.bound_sources` value may be selected.

## Exact authority identities

| Authority | Identity |
|---|---|
| Historical V2 commit | `9f4791c2744c02d742fdb9c0fa1e9dd150591ac1` |
| Historical V2 digest | `917ad129a4f9641f65b809e143467b1f2c48ea41203166365b8e3efd459b627e` |
| Proposed successor version | `naturalistic-pre-g6-contract-v3` |
| Frozen V3 review commit | `d5b03a6c8c53cfebbb7239ea4fb3ac31721e1ad7` |
| Proposed V3 digest | `f5cc62a3881bc06ddb0d0f1bc3b68d8c3e2cb29b5abda9675e32c84eea04d2a4` |
| Proposed V3 canonical bytes | `48268` |

The separately closed V2-04 descendant
`872390db8ac76157b3a0223d947a8eb5da66473c` is not the parent of this semantic
authority erratum. Its runtime state is outside this review.

## Exact review package

| What | Path |
|---|---|
| Canonical successor | `docs/plans/artifacts/naturalistic-pre-g6-contract-v3.json` |
| Schema | `docs/plans/artifacts/naturalistic-pre-g6-contract-v3.schema.json` |
| Conformance cases | `docs/plans/artifacts/naturalistic-pre-g6-contract-v3.conformance.json` |
| Validator | `docs/plans/artifacts/validate-naturalistic-pre-g6-contract-v3.mjs` |
| SHA-256 sidecar | `docs/plans/artifacts/naturalistic-pre-g6-contract-v3.json.sha256` |
| Changed-field manifest | `docs/plans/artifacts/naturalistic-pre-g6-contract-v3.amendment.json` |
| Architecture projection | `docs/plans/ARCHITECTURE-naturalistic-product-value.md` |
| Execution projection | `docs/plans/EXECUTION-naturalistic-product-value.md` |
| Arc snapshot at frozen target | `docs/plans/STATUS-naturalistic-product-value.md` |

## Required independent procedure

Use a detached worktree at the frozen target. Do not trust the shared checkout
or Codex's reported PASS.

```bash
git fetch origin
git worktree add --detach /tmp/convmem-pre-g6-v3-review \
  d5b03a6c8c53cfebbb7239ea4fb3ac31721e1ad7
cd /tmp/convmem-pre-g6-v3-review
git rev-parse HEAD
node docs/plans/artifacts/validate-naturalistic-pre-g6-contract-v2.mjs
node docs/plans/artifacts/validate-naturalistic-pre-g6-contract-v3.mjs
git diff --check \
  9f4791c2744c02d742fdb9c0fa1e9dd150591ac1..d5b03a6c8c53cfebbb7239ea4fb3ac31721e1ad7
```

Expected independent reproduction:

```text
V2 validator: PASS
V2 digest: 917ad129a4f9641f65b809e143467b1f2c48ea41203166365b8e3efd459b627e
V3 validator: PASS
V3 digest and sidecar: f5cc62a3881bc06ddb0d0f1bc3b68d8c3e2cb29b5abda9675e32c84eea04d2a4
V3 canonical byte count: 48268
V3 conformance cases: 35 total, 13 multiplicity cases
unrelated_semantics_regression: PASS
amendment_manifest_validation: PASS
trailing_byte_negative_control: PASS
git diff --check: no output
```

Also prove that historical and runtime surfaces did not change:

```bash
git diff --exit-code \
  9f4791c2744c02d742fdb9c0fa1e9dd150591ac1..d5b03a6c8c53cfebbb7239ea4fb3ac31721e1ad7 -- \
  docs/plans/artifacts/naturalistic-pre-g6-contract-v2.json \
  docs/plans/artifacts/naturalistic-pre-g6-contract-v2.schema.json \
  docs/plans/artifacts/naturalistic-pre-g6-contract-v2.conformance.json \
  docs/plans/artifacts/naturalistic-pre-g6-contract-v2.json.sha256 \
  docs/plans/artifacts/validate-naturalistic-pre-g6-contract-v2.mjs \
  eval_naturalistic tests
```

Expected result: exit `0`, no diff.

## Review questions

Kiro must answer every question independently.

1. **Historical authority preservation:** Are all V2 canonical and companion
   bytes unchanged, with the old digest still independently reproducible?
2. **Successor identity:** Does V3 name V2 commit/digest as its exact parent,
   use a new contract version, bind all companion paths, and remain
   `PROPOSED_NOT_LOCKED` pending review and Ryan acceptance?
3. **Inequality correction:** Does every valid multiplicity record require
   `0 <= known_count <= lower_bound`, with null upper or
   `lower_bound <= upper_bound`?
4. **Exact multiplicity:** Does exact status require equal known/lower/upper
   counts and separate exact-completeness proof authority?
5. **Proof preservation:** Does finite upper still require proof authority, and
   does a lower bound above recovered identities require separate lower-bound
   proof, without V3 choosing the proof source?
6. **Changed-field completeness:** Are the only semantic fields changed
   `/denominator_model/target_count_bounds/rules` and
   `/decision_registry/18/validator` for `D_MULTIPLICITY_001`?
7. **Mechanical/semantic separation:** Does the amendment manifest fully and
   accurately distinguish semantic correction from version, path, digest,
   conformance, control, dependency, and prose-routing mechanics?
8. **Conformance strength:** Do all 13 new cases exercise the claimed rule,
   rather than merely carry expected labels that the validator never tests?
9. **Regression proof:** Does the V3 validator's allowlisted projection really
   reject any unrelated contract change, rather than normalize away excess
   differences?
10. **Canonicalization:** Are RFC 8785 ordering/number handling, UTF-8 byte
    count, sidecar format, and trailing-byte negative control mechanically
    sound?
11. **Unchanged constructs:** Are stage graph, P1 identity/evidence, P2
    authority, P1/P2 firewall, P3 blindness, capability vectors, Issue #263,
    semantic dedup, null-upper blocking, episode-first weighting, C0/C1
    governance, amendment policy, and unrelated Ryan decisions unchanged?
12. **Scope firewall:** Did the corrective avoid V2-04A, V2-05 runtime types,
    V2-06, G6/T0, live evidence, Agent A/B, scoring, and product inference?

## Required adversarial cases

Confirm the validator actually evaluates these records:

### Valid

- `known=0, lower=0, upper=0`, exact proof present.
- `known=1, lower=1, upper=1`, exact proof present.
- `known=1, lower=1, upper=null`.
- `known=1, lower=3, upper=null`, lower-bound proof present.
- `known=1, lower=3, upper=5`, lower- and upper-bound proofs present.
- `known=0, lower=2, upper=7`, separate lower- and upper-bound proofs present.

### Invalid

- Negative `known_count`.
- Negative `lower_bound`.
- `known=2, lower=1`.
- `lower=4, upper=3`.
- Exact status with null upper.
- Exact status with unequal known/lower/upper.
- Finite upper without finite-upper proof authority.

## What NOT to build or do

- No edits from the Kiro review lane.
- No V2-04A implementation or tests.
- No V2-05 or V2-06 runtime work.
- No G6/T0, live evidence, Agent A/B, registry population, scoring, or product
  inference.
- No selection of `D_MULTIPLICITY_001.bound_sources`.
- No claim of Claude concurrence; Claude has not reviewed this package.
- No merge, PR creation, authority lock, or downstream grant. Ryan owns those
  decisions after review.

If Kiro finds a defect, stop at a written, reproducible corrective finding. Do
not repair it in the review lane.

## Required verdict

Return exactly one:

**`PRE-G6 V2 MULTIPLICITY AUTHORITY ERRATUM — PASS`**

or

**`PRE-G6 V2 MULTIPLICITY AUTHORITY ERRATUM — CORRECTIVE REQUIRED`**

Bind the verdict to exact target
`d5b03a6c8c53cfebbb7239ea4fb3ac31721e1ad7`. A PASS must report independently
observed V2/V3 digests, byte count, validator results, conformance results,
semantic changed fields, regression result, and scope result. A corrective
verdict must name the exact failing file/field or reproducible command and
classify whether it is semantic drift, incomplete conformance, invalid
canonicalization, inadequate regression proof, or projection/routing error.

## Acceptance criteria

- [ ] Review uses detached target `d5b03a6c8c53cfebbb7239ea4fb3ac31721e1ad7`.
- [ ] Historical V2 digest and immutable bytes independently confirmed.
- [ ] V3 digest, sidecar, and `48268` canonical bytes independently confirmed.
- [ ] All 13 multiplicity cases independently inspected and executed.
- [ ] Exactly two semantic changed fields confirmed, or discrepancy reported.
- [ ] Unrelated-semantics regression and prohibited-scope absence confirmed.
- [ ] Exact required verdict returned with evidence.
- [ ] Reviewer stops without implementation or grant.

## Review disposition sequence

```text
Kiro exact-target authority review
        ↓
Ryan accepts or rejects the V3 successor authority
        ↓
separately bounded V2-04A implementation corrective
        ↓
independent V2-04A review
        ↓
only then reconsider V2-05
```

G6/T0 remains closed throughout this sequence.

## Leaving / picking up checklist

**Codex Sol (leaving):**

- [x] V3 authority erratum committed at frozen target and pushed.
- [x] V2 and V3 validators run before handoff.
- [x] This handoff prepared on a later routing-only carrier.
- [x] `LATEST.md` points to this handoff.
- [x] Arc STATUS names this review as the next lane.
- [x] Routing-only carrier committed and pushed.

**Kiro (picking up):**

- [ ] Read this file before review.
- [ ] Use detached worktree at the exact frozen target.
- [ ] Independently inspect validator logic, not only its output.
- [ ] Return the required evidence-bound verdict.
- [ ] Stop without implementation.

## TL;DR

Kiro must independently review frozen target `d5b03a6c…` and determine whether
V3 fixes only the reversed multiplicity inequality while preserving V2 and all
unrelated PRE-G6 semantics. No implementation or downstream authority follows
from this handoff.

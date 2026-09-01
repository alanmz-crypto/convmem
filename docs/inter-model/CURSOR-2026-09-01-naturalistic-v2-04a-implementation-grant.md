# [Arc Naturalistic ConvMem product-value evaluation] Cursor V2-04A bounded implementation grant packet

**Date:** 2026-09-01
**Prepared by:** Luna
**For:** Ryan decision; Cursor only after an explicit grant
**Status:** `V2-04A GRANT READY FOR RYAN DECISION — NOT GRANTED`

## Human consequence

V2-04A is a narrowly bounded output-interface corrective. It supplies sealed
P1/P3 semantic candidate closure state that the later V2-05 slice will need,
while preserving the already-passed V2-04 blindness/noninterference boundary.
This packet does not itself grant implementation and does not authorize V2-05,
V2-06, G6/T0, evidence, Agent A/B, scoring, or product inference.

## Exact authority and lineage

| Dimension | Required identity |
|---|---|
| Accepted semantic authority | `naturalistic-pre-g6-contract-v3` |
| Accepted V3 semantic-authority commit | `d5b03a6c8c53cfebbb7239ea4fb3ac31721e1ad7` |
| Accepted V3 canonical RFC 8785/JCS digest | `f5cc62a3881bc06ddb0d0f1bc3b68d8c3e2cb29b5abda9675e32c84eea04d2a4` |
| Accepted V3 canonical byte count | `48,268` |
| Historical V2 semantic authority | Commit `9f4791c2744c02d742fdb9c0fa1e9dd150591ac1`; digest `917ad129a4f9641f65b809e143467b1f2c48ea41203166365b8e3efd459b627e` |
| Existing implementation-plan authority | Commit `1a72a761b2cca3d9f955ad09d7b8b265d1fcaa9c`, `docs/plans/EXECUTION-naturalistic-pre-g6-v2-implementation.md` |
| **Required implementation parent** | **`872390db8ac76157b3a0223d947a8eb5da66473c`** |
| Existing implementation state | V2-04 independently passed; blindness/noninterference PASS remains closed |

The V3 semantic authority is not the implementation Git parent. Cursor must
name both exact identities in its implementation and review handoffs.

## Objective and bounded output

Starting from exactly `872390db8ac76157b3a0223d947a8eb5da66473c`, extend the
V2-04 output interface so a sealed P1/P3 adjudication closure preserves the
semantic candidate/target state required by accepted V3 and later V2-05.

The existing `CandidateClosureV2` retains only candidate IDs and digests derived
from the same candidate-ID tuple plus phase labels. V2-04A must replace that
insufficiency with the smallest typed, sealed closure representation at the
existing V2-04 facade/view boundary. Cursor may extend the existing closure
type or add one tightly bounded semantic-closure module if that keeps the
interface deeper and the boundary clearer. It must not create a V2-05 registry
or move semantic authority into P2.

The implementation must use the exact V3 canonical vocabulary and rules. The
field groups below define required retained authority, not an alternate
semantic SSoT.

### Required retained semantic state

The sealed P1/P3 closure must preserve, at minimum:

1. **Semantic unit:** stable subject; proposition/state; validity interval; and
   frozen unitization-policy identity, version, and digest.
2. **Evidence relation:** every supporting opaque occurrence/span token for the
   candidate. Supporting spans are evidence, not semantic identity. Native,
   physical, revision, path, locator, and other raw source IDs must not cross
   the adjudicator-facing boundary.
3. **Pre-dedup authority:** candidate relationships before irreversible collapse,
   including enough lineage to explain which candidate records were compared.
4. **Duplicate relation:** an explicit closed relation equivalent to
   `SAME_TARGET`, `DISTINCT_TARGETS`, or `UNKNOWN`. `UNKNOWN` must remain
   unknown; it may not be silently converted into a merge or split.
5. **Candidate disposition:** eligible, ineligible, ambiguous, or the exact
   V3-compatible equivalent, stored separately from target existence.
6. **Candidate census/completeness:** explicit state distinguishing a complete
   candidate census, known candidates with possible additional candidates, and
   incomplete/unknown census. No recovered-candidate absence may imply zero.
7. **Closure lineage:** bind all of the following as typed fields and include
   them in the final sealed closure digest:
   - sealed P1 view digest;
   - submission A digest;
   - submission B digest;
   - disagreement-set digest;
   - blind disagreement-resolution digest;
   - unitization-policy digest;
   - semantic candidate-set digest;
   - dedup-relation digest; and
   - final membership/closure digest.

The closure must be immutable after sealing. Arbitrary/free-form submission
strings cannot become semantic authority. Forged or stale role contexts must
remain rejected.

## P2 firewall and noninterference

The existing rule remains binding: P2 may join only after semantic candidate
closure. P2 is append-only annotation and must not determine or modify:

- candidate existence or membership;
- semantic target identity, subject, proposition/state, or validity interval;
- unitization or deduplication relation;
- candidate ordering;
- census completeness;
- denominator membership.

For identical sealed P1/P3 state, varying P2 across every resolver state must
leave unchanged:

- adjudicator-visible bytes;
- semantic candidate membership and semantic candidate IDs;
- unitization results;
- dedup relations;
- ordering;
- closure digest; and
- serialized P1/P3 semantic closure.

Preserve the five existing resolver states: `EXACT_MATCH`, `NO_MATCH`,
`SUMMARY_ONLY`, `EVIDENCE_UNAVAILABLE`, and `ERROR`. In particular, P2
`EXACT_MATCH` cannot add membership, `NO_MATCH` cannot delete a candidate,
`SUMMARY_ONLY` cannot alter target identity, `EVIDENCE_UNAVAILABLE` cannot
alter census completeness, and `ERROR` cannot alter unitization or dedup.

## Issue #263 and exact-zero boundary

Retain independent representation of source presence, verbatim availability,
summary availability, and resolver result. Source present with verbatim
unavailable must remain represented; it must not become source absent, no
target, or zero opportunity.

V2-04A must not choose the later V2-05 multiplicity estimator or any
`D_MULTIPLICITY_001.bound_sources` value. It must preserve enough information
for V2-05 to prove exact zero only from a genuinely complete P1/adjudication
census. “No candidate recovered” is never sufficient for a complete zero.

Semantic target identity must remain based on stable subject,
proposition/state, validity interval, and frozen unitization policy. It must not
be defined solely through candidate ID, occurrence token, source identity,
content hash, text equality, or resolver result.

## Narrow implementation surfaces

Cursor should inspect the exact implementation parent first. Preferred scope:

- `eval_naturalistic/v2/adjudication_facade.py` — closure state machine and
  post-adjudication join boundary;
- `eval_naturalistic/v2/adjudication_view.py` — only if the sealed view needs a
  tightly bounded typed support relation, without exposing native/source IDs;
- a new narrowly scoped `eval_naturalistic/v2/semantic_closure.py` only if it
  reduces complexity rather than adding a pass-through layer;
- focused V2-04A tests, preferably a new
  `tests/test_naturalistic_v2_adjudication_v2_04a.py` or the smallest existing
  V2-04 test extension.

Do not modify `eval_naturalistic/adjudication.py` (V1) unless an unavoidable
dependency is discovered. That is a STOP condition for Ryan, not permission
for casual reuse or redesign.

Do not create `TargetRegistryV2`, multiplicity-bound runtime objects,
estimand propagation, analysis adapters, or T9/T10 behavior. V2-04A supplies
sealed semantic input only.

## Required adversarial test minimum

The implementation must add focused tests for all 20 cases below:

1. one semantic target supported by multiple spans;
2. duplicate source records supporting one target;
3. identical text representing distinct semantic targets;
4. same subject/proposition with different validity intervals;
5. uncertain duplicate relation remains `UNKNOWN`;
6. complete candidate census with zero candidates;
7. no candidates observed under incomplete evidence does not claim complete zero;
8. source present plus verbatim unavailable remains represented;
9. P2 `EXACT_MATCH` cannot alter membership;
10. P2 `NO_MATCH` cannot delete a candidate;
11. P2 `SUMMARY_ONLY` cannot alter target identity;
12. P2 `EVIDENCE_UNAVAILABLE` cannot alter census completeness;
13. P2 `ERROR` cannot alter unitization/dedup;
14. same P1 plus all five P2 states yields byte-identical P1/P3 closure;
15. supporting spans are retained without becoming target identity;
16. pre-dedup relations survive closure;
17. raw native/physical/revision/path/locator data remains unavailable through
    the adjudicator-facing boundary;
18. arbitrary/free-form submission strings cannot become semantic authority;
19. forged/stale role contexts remain rejected;
20. historical V1 adjudication remains unchanged.

The test set must also prove deterministic serialization, seal immutability,
lineage completeness, rejected post-seal mutation, and blocked early P2 join.
All fixtures remain synthetic and local.

## Acceptance criteria for Cursor's later execution

Cursor may begin only if Ryan explicitly grants this packet. A completed slice
must provide:

- exact implementation parent `872390db8ac76157b3a0223d947a8eb5da66473c`;
- explicit binding to accepted V3 commit/digest above;
- typed, sealed P1/P3 semantic closure with all required state and lineage;
- unchanged P2 firewall and same-P1/different-P2 byte equality;
- all 20 adversarial tests plus focused existing V2-04 regressions;
- no V1 changes, registry/estimator/runtime V2-05 objects, live evidence, or
  product inference;
- exact-tip branch, commit, tests, and diff; and
- an implementation handoff that reports any semantic or scope discrepancy
  instead of repairing it by widening this grant.

## Stop conditions

Cursor must stop and return to Ryan if:

- preserving the required state would change accepted V3 semantics or its
  canonical digest;
- a new semantic choice is required, including a bound-source selection;
- P2 must participate in semantic candidate closure;
- the blinded interface must be reopened or adjudicator-visible raw IDs would
  be required;
- V1 adjudication must be redesigned;
- the implementation needs V2-05, V2-06, T9/T10, live evidence, Agent A/B,
  scoring, or product inference; or
- the exact implementation parent cannot be preserved.

## Review recommendation

After implementation, request a **fresh Kiro independent implementation review**
at the exact tip, using the V2-04A tests and the same accepted V3 identities.
If Kiro finds that the slice materially changes semantic-methodology authority
beyond preserving accepted V3 state, stop the normal review path and request a
stronger preflight before any merge or downstream grant. No V2-05 review or
grant follows automatically from a V2-04A PASS.

## Ryan decision

Choose one explicit disposition:

- grant Cursor the bounded V2-04A slice above;
- hold/reject it and return a named clarification; or
- do not proceed with the Naturalistic implementation arc.

Until Ryan grants it, this document is planning only.

**Required verdict:** `V2-04A GRANT READY FOR RYAN DECISION`

**TL;DR:** The bounded Cursor slice starts exactly at `872390db…`, binds to
accepted V3 `d5b03a6c…` / `f5cc62a3…`, extends only sealed P1/P3 semantic
closure, preserves the P2 firewall, and covers all 20 required adversarial
tests. Ryan must explicitly grant it before Cursor implements; fresh Kiro
review follows.

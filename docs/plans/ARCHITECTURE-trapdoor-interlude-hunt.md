# Architecture — Arc Trapdoor Interlude Hunt

```text
Planning status: DRAFT — NOT AUTHORIZED FOR IMPLEMENTATION
Arc:            Arc Trapdoor Interlude Hunt
Parent:         Full Fathom Five
Purpose:        FF1/T1 and FF2/T2 prerequisites for Trapdoor Hunt FF3/T3
Baseline:       origin/main @ d10e1d5f4993f60a32142115f8b8c0f0f9ea4481
Reference T3:   plan/2026-08-15-dependability-provenance @ 8f037a50c4cdce170320bbfd6160c932f7661798
```

## 1. Decision and consequence

This interlude defines what ConvMem may truthfully call trustworthy, inventories
which of those claims are already supported by repository evidence, and records
the smallest missing oracle for each unsupported or partial claim.

It is a prerequisite contract for the already-designed Trapdoor Hunt FF3/T3
compatibility and provenance architecture. It does not replace, redesign, or
expand that architecture. It grants no runtime change, migration, corpus
rewrite, Chroma mutation, operational activation, or T3 implementation.

The interlude has two gated outputs:

1. an accepted FF1/T1 Trust Baseline claim matrix; and
2. an accepted FF2/T2 Existing Evidence + Failure-Gap Matrix.

FF2 cannot begin as an accepted phase until FF1 is accepted. Trapdoor Hunt T3
cannot receive an implementation grant until both outputs are accepted.

## 2. Entry gate and exact baseline

The hard prerequisite is P0 CI Merge Gate closure. GitHub `main` contains
CodeQL Complex Therapy closeout commit `d10e1d5f4993f60a32142115f8b8c0f0f9ea4481`
(`docs: close CodeQL Complex Therapy arc (#202)`), which is the starting point
for this branch. The local corpus may lag GitHub and is not authoritative for
this gate.

The Interlude branch is separate from the Trapdoor T3 branch. T3 is read-only
upstream design input at the reference revision above. If this interlude finds
a contradiction in T3, it records the exact claim, boundary, and smallest
correction; it does not silently edit T3.

## 3. Trust vocabulary

The matrix distinguishes these properties rather than collapsing them:

- **durable acknowledgement:** success from the named authoritative durable
  write boundary;
- **generation coherence:** one published authority generation, not a mixture;
- **capture/sealing consistency:** a sealed generation came from one consistent
  logical source state;
- **provenance integrity:** origin evidence and derivation history did not gain
  authority through transformation or projection;
- **factual truth:** whether an assertion is correct;
- **serving authority:** which CG-2 generation may answer a request;
- **retrieval priority:** relevance, recency, and existing ranking heuristics;
- **downstream action authority:** whether a consumer may act on retrieved data.

One successful health command, including `doctor PASS`, is evidence about that
command's checks only. It is not the definition of trustworthy memory.

`unknown`, `untrusted`, `quarantine`, `BLOCKED`, and
`provenance_store_unavailable` are materially different states where the
existing boundary uses them. The matrix must not collapse an unproved claim
into a generic healthy or generic error state.

## 4. FF1/T1 contract

The canonical claim matrix is in
`docs/plans/TRAPDOOR-INTERLUDE-MATRICES.md`. Every claim records:

`claim_id`, `property`, `scope`, `acknowledgement_boundary`,
`failure_consequence`, `severity`, `owner`, `oracle`, `degraded_state`, and
`notes_assumptions`.

Severity is a review field, not a numerical budget. The initial draft uses only
the repository/parent vocabulary needed to identify catastrophic or critical
trust loss; Ryan must accept the final labels. No RPO, RTO, uptime, latency,
memory, corpus-size, or recovery-minute target belongs in FF1.

FF1 is complete only when the vocabulary is accepted, every catastrophic or
critical claim has one explicit owner and one explicit oracle, and every such
claim has a declared degraded state.

## 5. FF2/T2 contract

FF2 begins from the accepted FF1 claim IDs. It inventories existing evidence
from CG-1, CG-2, complete-data generation and restore machinery, writer/process
locking, Restic gates, backup workflows, projection/reconstruction checks,
existing tests, and existing VERIFY plans.

Each claim is classified as exactly one of:

- `SUFFICIENT` — the evidence proves the claim at its stated boundary;
- `PARTIAL` — evidence proves a narrower window, projection, or predecessor;
- `ABSENT` — no current evidence proves the claim;
- `STALE` — evidence is bound to an obsolete revision or contract.

The FF2 matrix records the evidence revision, genuine failure window, evidence
limit, smallest missing oracle, expected degraded state, and owner. A new check
is justified only by a distinct failure window, authority boundary, owner,
state transition, recovery condition, or previously unproved property.

Broad disk-full, SIGKILL, provider-outage, concurrency, corruption, endurance,
and resource-pressure campaigns remain deferred unless FF2 identifies one
specific campaign as the smallest oracle for one accepted claim.

## 6. Trapdoor Bridge

The final section of `TRAPDOOR-INTERLUDE-MATRICES.md` maps:

```text
accepted T1 claim
  → accepted T2 evidence/oracle
  → existing Trapdoor T3 requirement
  → existing T3 VERIFY row
```

The bridge must cover, at minimum, acknowledgement, provenance-store
authority, recovery, selected-generation coherence, capture/sealing consistency
(R8.2/V4m), the manifest-bound mutator census, migration/version handling,
identity preservation, and projection-versus-authority boundaries.

The bridge is an integration map, not a rewrite of R1–R10 or V0–V10. A
contradiction is reported with its smallest bounded correction and remains a
review finding until Ryan decides it.

## 7. Explicit non-goals

This package does not authorize:

- runtime code, tests that mutate production state, or live configuration;
- provenance implementation, registry implementation, or migration;
- live Chroma/corpus changes, Shadow activation, R2b capture, or CG-2 action;
- CG-1/CG-2 redesign;
- broad fault injection, soak, endurance, or performance optimization;
- arbitrary numerical SLO/RPO/RTO/RTO-like targets;
- new cloud policy, egress policy, or unrelated security work;
- automatic T3 implementation authorization.

## 8. Human gates

FF1 is frozen only by Ryan acceptance. FF2 is frozen only after FF1 acceptance
and Ryan acceptance of the evidence/gap matrix. The Trapdoor Bridge does not
grant T3 implementation. Trapdoor Hunt retains its own exact-revision review,
architecture lock, and separate Ryan Execute grant.

**TL;DR:** This arc defines and audits the trust contract upstream of Trapdoor
T3; it creates no runtime authority and cannot grant T3 implementation.

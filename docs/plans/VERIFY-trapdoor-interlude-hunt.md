# VERIFY — Arc Trapdoor Interlude Hunt

```text
Status: PLANNING STUB — ALL IMPLEMENTATION EVIDENCE PENDING
Arc:    Arc Trapdoor Interlude Hunt
Subject baseline: d10e1d5f4993f60a32142115f8b8c0f0f9ea4481
```

No row below is PASS, FAIL, or GREEN. These are predeclared planning checks;
evidence may be recorded only in an explicitly authorized verification phase.

## V0 — Revision, entry gate, and scope

| ID | Required check | Result |
|---|---|---|
| V0a | Exact subject SHA, branch, and parent `main` SHA are recorded. | PENDING |
| V0b | GitHub CodeQL/P0 closeout is reachable from the starting `main` SHA and the five required contexts are recorded from authoritative GitHub evidence. | PENDING |
| V0c | Interlude branch is separate from Trapdoor T3 and starts from current `main`; no existing T3 branch is modified. | PENDING |
| V0d | Changed-file inventory contains only the named planning artifacts and required status-index references. | PENDING |
| V0e | No runtime, live-data, Chroma, Shadow, R2b, CG-2, migration, cloud-policy, or operational action occurred. | PENDING |

## V1 — FF1/T1 claim-matrix completeness

| ID | Required check | Result |
|---|---|---|
| V1a | Every claim has a stable ID and a single property stated as a product promise. | PENDING |
| V1b | Every claim names scope and, where relevant, the authoritative acknowledgement boundary. | PENDING |
| V1c | Every claim names failure consequence and an accepted categorical severity; no numerical SLO/RPO/RTO target appears. | PENDING |
| V1d | Every catastrophic/critical claim has exactly one explicit owner. | PENDING |
| V1e | Every catastrophic/critical claim has one independently inspectable oracle. | PENDING |
| V1f | Every catastrophic/critical claim has a concrete degraded state, not merely `error` or `doctor failed`. | PENDING |
| V1g | Acknowledgement, durability, provenance integrity, factual truth, ranking, serving authority, and downstream action authority remain distinct. | PENDING |
| V1h | FF1 vocabulary and severity labels are explicitly marked for Ryan acceptance before FF2 begins. | PENDING |

## V2 — FF2/T2 evidence and gap matrix

| ID | Required check | Result |
|---|---|---|
| V2a | Every accepted FF1 claim has one evidence row with exact artifact/path and revision where practical. | PENDING |
| V2b | Each evidence row is classified exactly `SUFFICIENT`, `PARTIAL`, `ABSENT`, or `STALE`. | PENDING |
| V2c | Each row states the failure window genuinely covered and the evidence limit. | PENDING |
| V2d | Each gap names the smallest missing oracle, owner, and expected degraded state. | PENDING |
| V2e | Existing evidence is reused when it covers the same property, owner, boundary, and failure window. | PENDING |
| V2f | Duplicate proposed checks are rejected unless a distinct failure window, owner, authority boundary, state transition, or recovery condition is shown. | PENDING |
| V2g | Stale evidence is labeled stale rather than silently carried forward from another architecture or SHA. | PENDING |
| V2h | FF2 does not launch or authorize a broad fault-injection, soak, endurance, or performance campaign. | PENDING |
| V2i | FF2 cannot be accepted until FF1 acceptance is recorded at an exact prior revision. | PENDING |

## V3 — Trapdoor Bridge continuity

| ID | Required check | Result |
|---|---|---|
| V3a | Each relevant T1 claim maps to a T2 evidence/gap row, an existing T3 requirement, and an existing T3 VERIFY row. | PENDING |
| V3b | Bridge covers acknowledgement, provenance-store authority, recovery, selected-generation coherence, R8.2/V4m, mutator census, migration/version rules, identity preservation, and projection/authority separation. | PENDING |
| V3c | Existing T3 requirements are not silently rewritten or broadened. | PENDING |
| V3d | Any T1/T2 contradiction with T3 is recorded with exact claim, boundary, row, and smallest bounded correction. | PENDING |
| V3e | The bridge does not imply a T3 implementation grant, migration grant, activation, or runtime change. | PENDING |

## V4 — Review and acceptance gates

| ID | Required check | Result |
|---|---|---|
| V4a | ChatGPT reviews the exact Interlude SHA and checks sequencing, scope, claim/oracle completeness, and duplicate-oracle rejection. | PENDING |
| V4b | Kiro or another authorized design-review lane reviews the exact planning SHA if Ryan requests it. | PENDING |
| V4c | Any Copilot audit is targeted to safety/isolation/document integrity at the same exact SHA. | PENDING |
| V4d | Ryan explicitly accepts FF1 before FF2 begins. | PENDING |
| V4e | Ryan explicitly accepts FF2 and the Trapdoor Bridge. | PENDING |
| V4f | Ryan records `RYAN_INTERLUDE_LOCK`; no T3 implementation authorization is inferred. | PENDING |

## V5 — Planning hygiene

| ID | Required check | Result |
|---|---|---|
| V5a | No arbitrary RPO, RTO, uptime, latency, memory, corpus-size, or recovery-minute target appears. | PENDING |
| V5b | No runtime or operational command was authorized by the package. | PENDING |
| V5c | All review claims are bound to exact revisions; persona simulation is not called independent review. | PENDING |
| V5d | The final handback names unresolved missing oracles and confirms deferred broad fault injection. | PENDING |

**TL;DR:** This is a planning-only VERIFY contract; every row remains PENDING
until its separately authorized evidence exists.

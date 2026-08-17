# STATUS — Arc Trapdoor Interlude Hunt

> Current-state arc brief. This is not a changelog and grants no implementation
> or operational authority.

**State:** Interlude branch is at
`3c746faa47409f7def02d2fd24351fbc936a9720`; Ryan accepted FF1/T1 at that exact
SHA; FF2/T2 validation is in progress and remains unaccepted; no runtime work
is authorized.

## 1. What this project is for

ConvMem's existing Trapdoor Hunt T3 design requires an accepted upstream trust
contract and evidence-gap inventory. This interlude defines what ConvMem must
be able to truthfully call trustworthy, determines what the current system
already proves, and records the smallest missing oracle without implementing
anything.

## 2. How the planned work connects

```text
P0 CI Merge Gate CLOSED/PASS
          │
          ▼
FF1/T1 Trust Baseline
          │ Ryan acceptance
          ▼
FF2/T2 Existing Evidence + Failure-Gap Matrix
          │ Ryan acceptance
          ▼
Trapdoor Hunt FF3/T3 Bridge
          │
          ▼
T3 remains separately locked and separately executable
```

The bridge maps accepted T1 claims and T2 evidence to existing T3 requirements
and VERIFY rows. It does not redesign T3 or grant implementation.

## 3. What exists on disk now

| Surface | State |
|---|---|
| Interlude branch | Pushed at `3c746faa47409f7def02d2fd24351fbc936a9720`; FF1 acceptance is bound to this exact revision. |
| `ARCHITECTURE-trapdoor-interlude-hunt.md` | Draft planning contract; not locked. |
| `EXECUTION-trapdoor-interlude-hunt.md` | Draft gated sequencing; not authorized for runtime work. |
| `VERIFY-trapdoor-interlude-hunt.md` | Planning stub; all rows PENDING. |
| `TRAPDOOR-INTERLUDE-MATRICES.md` | FF1 accepted; FF2/T2 validation draft in progress; Bridge remains gated. |
| Trapdoor T3 reference branch | Read-only upstream design at `8f037a50`; not modified. |
| CodeQL/P0 | Closed/PASS on GitHub main before Interlude branch creation. |

## 4. Completion state

| Milestone | State | Exit condition |
|---|---|---|
| P0 CI Merge Gate | **CLOSED/PASS** | GitHub main CodeQL closeout is reachable and accepted. |
| FF1/T1 Trust Baseline | **ACCEPTED** at `3c746faa47409f7def02d2fd24351fbc936a9720` | Ryan accepted vocabulary, severity, sequencing, and critical-row owner/oracle/degraded-state normalization. |
| FF2/T2 Evidence + Gap Matrix | Validation in progress; not accepted | Every accepted claim has one classification, failure window, evidence limit, smallest missing oracle, owner, and degraded state; Ryan accepts FF2 before the Bridge. |
| Trapdoor Bridge | Not started | FF2 accepted and each relevant T3 requirement has an upstream mapping. |
| Interlude lock | Not authorized | Ryan accepts FF1, FF2, Bridge, and no prohibited work occurred. |
| Trapdoor T3 implementation | Not authorized | Separate T3 lock and Ryan Execute grant remain required. |

## 5. Your role now

The current owner is the fresh Codex Interlude planning lane. It is validating
the accepted FF1 claims against existing repository evidence, classifying each
row without runtime work, and bounding the smallest missing oracle. It must
stop for Ryan's FF2 decision before beginning the Trapdoor Bridge.

Kiro is reserved for non-implementing design review; Copilot for a targeted
safety/isolation/document-integrity audit; Crush for bounded repository
discovery if needed; Cursor for implementation only after a separate Ryan
Execute grant. None of these lanes may silently redesign Trapdoor T3, and no
lane may infer Ryan acceptance or T3 authorization.

## 6. What remains before this is complete

1. Complete and review the FF2 evidence/gap matrix from accepted FF1 claims.
2. Obtain Ryan's explicit FF2 acceptance.
3. Complete the Trapdoor Bridge and resolve bounded contradictions.
4. Obtain exact-SHA review and Ryan's Interlude lock.
5. Hand back the closing SHA, accepted matrices, unresolved oracles, T3 impact,
   and confirmation that runtime work and numerical operational targets remain
   deferred.

## 7. Hard stops and residual limitations

- `doctor PASS` is not a trust baseline.
- Partial, stale, or projection-only evidence cannot become `SUFFICIENT` by
  wording.
- Unknown or missing authority is not silently healthy.
- No implementation, migration, Chroma/corpus mutation, Shadow/R2b operation,
  CG-2 activation, cloud-policy change, or broad fault campaign is allowed.
- FF1/FF2 acceptance never grants T3 implementation.

## 8. Relationship to other arcs

| Arc/control | Relationship |
|---|---|
| CodeQL Complex Therapy | P0 prerequisite; closed before this branch was created. |
| Full Fathom Five | Parent roadmap; FF1 → FF2 → FF3/T3 remains frozen. |
| Trapdoor Hunt | Existing FF3/T3 design; read-only upstream dependency. |
| CG-1 / CG-2 / backup / restore | Evidence sources for FF2, not redesigned here. |
| T4/T5 | Remain later parent arcs; no scope pulled forward. |

## 9. Key files and review order

1. `docs/plans/ARCHITECTURE-trapdoor-interlude-hunt.md`
2. `docs/plans/EXECUTION-trapdoor-interlude-hunt.md`
3. `docs/plans/VERIFY-trapdoor-interlude-hunt.md`
4. `docs/plans/TRAPDOOR-INTERLUDE-MATRICES.md`
5. `docs/plans/STATUS-trapdoor-interlude-hunt.md`
6. Parent roadmap and Trapdoor T3 reference branch at the exact revisions named
   in the architecture header.

## 10. Update protocol and log

Keep this file a current-state snapshot. Overwrite Sections 3–6 when state
changes and add one milestone-level line below. Session narrative belongs in
Track A, not here.

| Date | Lane | Milestone change |
|---|---|---|
| 2026-08-16 | Codex | Created isolated Interlude branch after CodeQL/P0 closeout verification; ChatGPT review now requires a fresh Codex owner, concrete FF1 owners/oracles, and explicit FF2-seed wording. |
| 2026-08-17 | Codex | Ryan accepted FF1 at `3c746faa47409f7def02d2fd24351fbc936a9720`; FF2 evidence validation began with bounded classifications and missing-oracle ownership. |

**TL;DR:** FF1 is accepted at the exact normalization tip; FF2 validation is
in progress, FF2 and the Trapdoor Bridge remain gated by Ryan acceptance, and no
implementation is authorized.

# STATUS — Arc Trapdoor Interlude Hunt

> Current-state arc brief. This is not a changelog and grants no implementation
> or operational authority.

**State:** Branch created from GitHub `main` at
`d10e1d5f4993f60a32142115f8b8c0f0f9ea4481`; FF1/T1 planning draft in progress;
FF1 is not accepted, FF2 has not begun, and no runtime work is authorized.

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
| Interlude branch | Created and pushed from `main` at `d10e1d5f4993f60a32142115f8b8c0f0f9ea4481`. |
| `ARCHITECTURE-trapdoor-interlude-hunt.md` | Draft planning contract; not locked. |
| `EXECUTION-trapdoor-interlude-hunt.md` | Draft gated sequencing; not authorized for runtime work. |
| `VERIFY-trapdoor-interlude-hunt.md` | Planning stub; all rows PENDING. |
| `TRAPDOOR-INTERLUDE-MATRICES.md` | FF1/FF2/Bridge draft; Ryan acceptance pending. |
| Trapdoor T3 reference branch | Read-only upstream design at `8f037a50`; not modified. |
| CodeQL/P0 | Closed/PASS on GitHub main before Interlude branch creation. |

## 4. Completion state

| Milestone | State | Exit condition |
|---|---|---|
| P0 CI Merge Gate | **CLOSED/PASS** | GitHub main CodeQL closeout is reachable and accepted. |
| FF1/T1 Trust Baseline | Draft in progress | Ryan accepts vocabulary and every critical claim has owner, oracle, degraded state. |
| FF2/T2 Evidence + Gap Matrix | Not started | FF1 accepted first; then every claim classified and missing oracle bounded. |
| Trapdoor Bridge | Not started | FF2 accepted and each relevant T3 requirement has an upstream mapping. |
| Interlude lock | Not authorized | Ryan accepts FF1, FF2, Bridge, and no prohibited work occurred. |
| Trapdoor T3 implementation | Not authorized | Separate T3 lock and Ryan Execute grant remain required. |

## 5. Your role now

The next lane is the planning/review lane for FF1/T1. Read the five Interlude
artifacts, inspect the repository evidence, and challenge claims that lack an
owner, oracle, or degraded state. Do not begin FF2 acceptance until Ryan locks
FF1. Do not modify Trapdoor T3.

## 6. What remains before this is complete

1. Complete and review the FF1 claim matrix.
2. Obtain Ryan's explicit FF1 acceptance.
3. Complete the FF2 evidence/gap matrix from accepted FF1 claims.
4. Obtain Ryan's explicit FF2 acceptance.
5. Complete the Trapdoor Bridge and resolve bounded contradictions.
6. Obtain exact-SHA review and Ryan's Interlude lock.
7. Hand back the closing SHA, accepted matrices, unresolved oracles, T3 impact,
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
| 2026-08-16 | Codex | Created isolated Interlude branch from GitHub main after CodeQL/P0 closeout verification; began FF1 draft. |

**TL;DR:** Interlude is in FF1 draft only; FF2 and the Trapdoor bridge remain
gated by Ryan acceptance and no implementation is authorized.

# STATUS — Arc Trapdoor Interlude Hunt

> Current-state arc brief. This is not a changelog and grants no implementation
> or operational authority.

**State:** FF2/T2 is accepted at exact reviewed package SHA
`0c2ab32b49a1a970fb3d1f76409d53ec1f0c6361`; FF1/T1 acceptance remains bound to
`3c746faa47409f7def02d2fd24351fbc936a9720`; the Interlude holds for the
literature/evidence challenge before any Bridge construction; no runtime work
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
| Interlude branch | FF2 accepted at exact reviewed package SHA `0c2ab32b49a1a970fb3d1f76409d53ec1f0c6361`; prior FF2 validation/content revision `a85e4d4613218a9ef2c165db47f021ea83a11dbc`; FF1 acceptance remains bound to `3c746faa47409f7def02d2fd24351fbc936a9720`. |
| `ARCHITECTURE-trapdoor-interlude-hunt.md` | Draft planning contract; not locked. |
| `EXECUTION-trapdoor-interlude-hunt.md` | Draft gated sequencing; not authorized for runtime work. |
| `VERIFY-trapdoor-interlude-hunt.md` | Planning stub; all rows PENDING. |
| `TRAPDOOR-INTERLUDE-MATRICES.md` | FF1 and FF2 accepted at their exact review revisions; Bridge remains gated pending the literature/evidence challenge. |
| Trapdoor T3 reference branch | Read-only upstream design at `8f037a50`; not modified. |
| CodeQL/P0 | Closed/PASS on GitHub main before Interlude branch creation. |

## 4. Completion state

| Milestone | State | Exit condition |
|---|---|---|
| P0 CI Merge Gate | **CLOSED/PASS** | GitHub main CodeQL closeout is reachable and accepted. |
| FF1/T1 Trust Baseline | **ACCEPTED** at `3c746faa47409f7def02d2fd24351fbc936a9720` | Ryan accepted vocabulary, severity, sequencing, and critical-row owner/oracle/degraded-state normalization. |
| FF2/T2 Evidence + Gap Matrix | **ACCEPTED** at `0c2ab32b49a1a970fb3d1f76409d53ec1f0c6361` | Ryan accepted 9 PARTIAL / 2 ABSENT / 0 SUFFICIENT / 0 STALE and the documented evidence boundaries, limits, missing oracles, owners, and degraded states. |
| Literature/evidence challenge | **NEXT; Bridge held** | ChatGPT challenges accepted FF1/FF2 assumptions before any Bridge construction decision. |
| Trapdoor Bridge | Not started; not authorized | A separate decision follows the literature challenge and resolution of any material findings. |
| Interlude lock | Not authorized | Ryan accepts FF1, FF2, Bridge, and no prohibited work occurred. |
| Trapdoor T3 implementation | Not authorized | Separate T3 lock and Ryan Execute grant remain required. |

## 5. Your role now

The current owner is the fresh Codex Interlude planning lane. It has completed
FF1/FF2 planning and must now hold the accepted package for ChatGPT's external
literature/evidence challenge. It must not construct the Trapdoor Bridge or
implement missing oracles unless a later decision explicitly authorizes that
work.

Kiro is reserved for non-implementing design review; Copilot for a targeted
safety/isolation/document-integrity audit; Crush for bounded repository
discovery if needed; Cursor for implementation only after a separate Ryan
Execute grant. None of these lanes may silently redesign Trapdoor T3, and no
lane may infer Ryan acceptance or T3 authorization.

## 6. What remains before this is complete

1. Complete the ChatGPT literature/evidence challenge against accepted FF1/FF2.
2. Report each material finding with the affected row, challenged assumption,
   external evidence, challenge severity, survival decision, and smallest
   correction if required.
3. Obtain a separate decision on any material findings and on Bridge
   construction.
4. If authorized, complete the Trapdoor Bridge and obtain exact-SHA review and
   Ryan's Interlude lock.
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
| 2026-08-17 | Ryan | Accepted FF2 at exact reviewed package SHA `0c2ab32b49a1a970fb3d1f76409d53ec1f0c6361`; Interlude holds for the literature/evidence challenge before Bridge construction. |

**TL;DR:** FF1 and FF2 are accepted at their exact review revisions; the
literature/evidence challenge is next, while the Trapdoor Bridge and all
implementation remain gated.

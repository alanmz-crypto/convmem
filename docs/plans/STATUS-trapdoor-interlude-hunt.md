# STATUS — Arc Trapdoor Interlude Hunt

> Current-state arc brief. This is not a changelog and grants no implementation
> or operational authority.

**State:** **CLOSED / LOCKED — `RYAN_INTERLUDE_LOCK — PASS`.** Original
FF1/T1 is accepted at exact reviewed SHA
`3c746faa47409f7def02d2fd24351fbc936a9720`; original FF2/T2 is accepted at
exact reviewed package SHA `0c2ab32b49a1a970fb3d1f76409d53ec1f0c6361`; the
bounded T1-GEN/T1-REC/T1-BACK amendment is accepted at
`41d6af4e6e56797d65cbc23e52c40f4dc1795c94`; and the completed Interlude/Bridge
is locked at exact revision `ccd8c271b7918ecaa2363de489262fd1c3be054c` against
T3 planning basis `a46a3be2ed21252354dc0b18245059d342cfcb31`. FF1/FF2 and the
Bridge are accepted as the planning/traceability foundation. All T3 VERIFY
results remain PENDING; no runtime work is authorized.

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
| Interlude branch | Locked at exact Interlude/Bridge revision `ccd8c271b7918ecaa2363de489262fd1c3be054c`; original FF1/FF2 acceptance remains bound to `3c746faa47409f7def02d2fd24351fbc936a9720` / `0c2ab32b49a1a970fb3d1f76409d53ec1f0c6361`; the bounded T1-GEN/T1-REC/T1-BACK amendment remains accepted at `41d6af4e6e56797d65cbc23e52c40f4dc1795c94`. |
| `ARCHITECTURE-trapdoor-interlude-hunt.md` | Draft planning contract; not locked. |
| `EXECUTION-trapdoor-interlude-hunt.md` | Draft gated sequencing; not authorized for runtime work. |
| `VERIFY-trapdoor-interlude-hunt.md` | Planning stub; all rows PENDING. |
| `TRAPDOOR-INTERLUDE-MATRICES.md` | FF1, FF2, and the bounded T1-GEN/T1-REC/T1-BACK amendment are accepted at their exact review revisions; the 11-row Bridge is locked at `ccd8c271b7918ecaa2363de489262fd1c3be054c` against corrected T3 `a46a3be2ed21252354dc0b18245059d342cfcb31`. |
| Trapdoor T3 reference branch | Read-only corrected planning basis at `a46a3be2ed21252354dc0b18245059d342cfcb31`, superseding `2bb0de4c4c9444b3ddefdb910a609f91eccb24c3` for this recheck; no implementation occurred. |
| CodeQL/P0 | Closed/PASS on GitHub main before Interlude branch creation. |

## 4. Completion state

| Milestone | State | Exit condition |
|---|---|---|
| P0 CI Merge Gate | **CLOSED/PASS** | GitHub main CodeQL closeout is reachable and accepted. |
| FF1/T1 Trust Baseline | **ACCEPTED** at `3c746faa47409f7def02d2fd24351fbc936a9720` | Ryan accepted vocabulary, severity, sequencing, and critical-row owner/oracle/degraded-state normalization. |
| FF2/T2 Evidence + Gap Matrix | **ACCEPTED** at `0c2ab32b49a1a970fb3d1f76409d53ec1f0c6361` | Ryan accepted 9 PARTIAL / 2 ABSENT / 0 SUFFICIENT / 0 STALE and the documented evidence boundaries, limits, missing oracles, owners, and degraded states. |
| Literature/evidence challenge | **COMPLETE** | ChatGPT/Sol literature findings were bounded, accepted corrections were applied, and the authority-first amendment was accepted at `41d6af4e6e56797d65cbc23e52c40f4dc1795c94`. |
| Trapdoor Bridge | **LOCKED — `RYAN_INTERLUDE_LOCK — PASS`** at `ccd8c271b7918ecaa2363de489262fd1c3be054c` | All 11 accepted T1 claims remain mapped to accepted FF2 evidence/gaps; T1-TRANS and T1-SCHEMA surface the corrected T3 requirements without changing classifications. |
| Interlude lock | **CLOSED / LOCKED** | Ryan accepted the planning/traceability foundation at exact Interlude revision `ccd8c271b7918ecaa2363de489262fd1c3be054c`; all VERIFY rows remain PENDING. |
| Trapdoor T3 implementation | Not authorized | Separate T3 lock and Ryan Execute grant remain required. |

## 5. Your role now

The current owner was the fresh Codex Interlude planning lane. It completed
FF1/FF2 planning, applied only the accepted bounded literature amendments, and
constructed and refreshed the planning-only Trapdoor Bridge. Ryan has now
locked the Interlude at `ccd8c271b7918ecaa2363de489262fd1c3be054c` against T3
planning basis `a46a3be2ed21252354dc0b18245059d342cfcb31`. No further
Interlude work is authorized by this closeout, and no missing oracle or
Verified Ingress Bootstrap work occurred.

Kiro is reserved for non-implementing design review; Copilot for a targeted
safety/isolation/document-integrity audit; Crush for bounded repository
discovery if needed; Cursor for implementation only after a separate Ryan
Execute grant. None of these lanes may silently redesign Trapdoor T3, and no
lane may infer Ryan acceptance or T3 authorization.

## 6. What remains before this is complete

1. The Interlude is closed/locked; no further Interlude changes are authorized
   absent a new Ryan correction decision.
2. The next gate is a separate T3 lock/review decision against planning basis
   `a46a3be2ed21252354dc0b18245059d342cfcb31`; Kiro's non-implementing design
   review and any targeted safety audit belong at that gate, not in this
   bookkeeping closeout.
3. A separate Ryan T3 Execute grant is required before Cursor or any other lane
   performs implementation, migration, runtime, live-data, or operational work.
4. Verified Ingress Bootstrap design requires a separate later planning
   decision; it is not included in this closeout.

## 7. Hard stops and residual limitations

- `doctor PASS` is not a trust baseline.
- Partial, stale, or projection-only evidence cannot become `SUFFICIENT` by
  wording.
- Unknown or missing authority is not silently healthy.
- No implementation, migration, Chroma/corpus mutation, Shadow/R2b operation,
  CG-2 activation, cloud-policy change, or broad fault campaign is allowed.
- FF1/FF2 acceptance never grants T3 implementation.
- The Bridge is traceability only; its mapped T3 requirements and PENDING VERIFY
  rows are not implementation or acceptance evidence.

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
| 2026-08-17 | Codex | Constructed the bounded 11-row Trapdoor Bridge on accepted amendment `41d6af4e6e56797d65cbc23e52c40f4dc1795c94` and T3 basis `2bb0de4c4c9444b3ddefdb910a609f91eccb24c3`; awaiting exact-SHA review and Ryan's Interlude lock. |
| 2026-08-17 | Codex | Applied the four bounded T3 planning corrections at `a46a3be2ed21252354dc0b18245059d342cfcb31`; held the unchanged Bridge for exact-SHA recheck and kept implementation/lock gated. |
| 2026-08-17 | Codex | Refreshed T1-TRANS/T1-SCHEMA Bridge traceability against corrected T3 `a46a3be2ed21252354dc0b18245059d342cfcb31`; kept implementation gated and awaiting Ryan's Interlude lock. |
| 2026-08-17 | Ryan | Recorded `RYAN_INTERLUDE_LOCK — PASS` for Interlude/Bridge `ccd8c271b7918ecaa2363de489262fd1c3be054c` against T3 planning basis `a46a3be2ed21252354dc0b18245059d342cfcb31`; Interlude closed/locked with all VERIFY rows PENDING. |

**TL;DR:** [Arc Trapdoor Interlude Hunt] FF1/FF2 and the bounded amendment are
accepted and locked at `ccd8c271b7918ecaa2363de489262fd1c3be054c` against T3
planning basis `a46a3be2ed21252354dc0b18245059d342cfcb31`; all VERIFY rows
remain PENDING and T3 implementation remains unauthorized.

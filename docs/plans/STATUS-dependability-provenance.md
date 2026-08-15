# Arc Brief — Dependability and Provenance Trust Arc

> Every model working on this arc must read this file and state: “Goal: … My
> role: … The system currently: … Missing: …”

## 1. What This Is For (product goal)

ConvMem should preserve and use accumulated memory without silently losing
acknowledged data, serving the wrong authority, accepting untrusted content as
instruction, or hiding degraded operation behind a green-looking health check.
This arc defines the claims, evidence, and enforcement needed for that boundary.

## 2. System Design (how the pieces connect)

```text
Authoritative ledger/source/backups
              │
              ▼
     T1 Trust Baseline matrix
     (authority, failure, evidence,
      degraded state, severity, gate)
              │
    ┌─────────┼─────────┐
    ▼         ▼         ▼
 CG-1/CG-2  Recovery  Security/egress
 proof map  evidence  lifecycle controls
    └─────────┼─────────┘
              ▼
     T2 gap-driven failure matrix
              ▼
     T3 compatibility → T4 security → T5 operations
```

The arc is planning-only. CI merge protection is prerequisite infrastructure,
not a Trust Arc milestone. CG-2 activation, owner cutover, GC, Shadow activation,
and live capture remain separately authorized.

## 3. What Exists Right Now (file map)

| Surface | State |
|---|---|
| CG-1 committed-generation durability | On `main`; existing handoff and verification evidence |
| CG-2 authority migration | On `main`; soak, owner activation, and GC remain gated |
| Full pytest CI | On `main` via #187; required-check enforcement is separate |
| Backup/restore safeguards | Existing complete-data and restore-drill machinery |
| Shadow Ledger Phase 0 | On `main`; disabled pending activation-ready evidence and Ryan grant |
| Trust architecture | This planning branch; not yet locked or implemented |
| Trust Baseline / proof inventory / migration policy | Not yet authored before this branch |
| Egress/local-only hard stop | Not yet implemented as this arc's contract |
| Literature inputs | Outside repo; claims remain provisional until primary-source verification |

## 4. Completion State

| Milestone | Status | Blocking on |
|---|---|---|
| CI merge protection | Workflow landed; required-check closure separate | Ryan/platform settings evidence |
| T1 Trust Baseline | Drafted in planning package | Ryan architecture review |
| T2 Proof inventory | Not started | T1 lock |
| T3 Compatibility/provenance | Not started | T1/T2 and Execute grant |
| T4 Security boundary | Not started | T1/T2/T3 and named grants |
| T5 Operational envelope | Not started | T1–T4 |
| Arc VERIFY | Planning skeleton | Execute and evidence |

## 5. Your Role (read this to know what you are here to do)

Review the Trust Baseline claims, confirm severity/gate vocabulary, and produce
the existing-proof inventory. Do not implement runtime controls, run live corpus
mutations, authorize cloud egress, or treat this brief as an operational grant.

## 6. What Remains Before “Live” (sequential)

- Ryan reviews and locks architecture.
- Codex produces the claim matrix and proof inventory.
- Ryan authorizes execution scope if implementation is warranted.
- Cursor implements only the granted slice and records exact evidence.
- Kiro independently reviews the same revision.
- VERIFY records mechanical evidence, residuals, and Ryan’s separate gate.
- Migration, activation, GC, live capture, and cloud policy remain exact-grant work.

## 7. Hard Stops (models cannot cross)

- No implementation is implied by this planning branch.
- No CG-2 soak, owner activation, cutover, or GC.
- No Shadow activation or live capture.
- No live configuration or corpus mutation.
- No cloud-policy change merely because an egress claim appears in T1.
- No new fault suite before CG-1/CG-2 evidence is inventoried.
- No threshold becomes a gate without a bad outcome, severity, and owner.

## 8. Relationship to ConvMem (the bigger picture)

```text
CI prerequisite → T1 trust claims → T2 proof gaps → T3 compatibility
                → T4 security boundary → T5 endurance/enforcement
```

Retrieval freshness/ranking, JudgeBench calibration, and release work are
neighboring tracks. They join this arc only when a direct integrity, authority,
or provenance failure is demonstrated.

## 9. Key Design Files

| Purpose | Path |
|---|---|
| Architecture | `docs/plans/ARCHITECTURE-dependability-provenance.md` |
| Execution | `docs/plans/EXECUTION-dependability-provenance.md` |
| Verification | `docs/plans/VERIFY-dependability-provenance.md` |
| CG-1 evidence | `docs/inter-model/HANDOFF-CG1-DEPENDABILITY-2026-08-10.md` |
| CG-2 evidence | `docs/plans/VERIFY-cg2-production-activation.md` |
| Shadow contract | `docs/plans/PHASE0-SHADOW-CONTRACT.md` |
| Shadow status | `docs/plans/STATUS-shadow-ledger-phase0.md` |

## 10. How to Update This Brief (departure protocol)

Keep this file a current-state snapshot. Overwrite sections 3–6 when state
changes, remove completed items, rewrite the next model’s role, and add one
milestone-level line to the Update Log. Do not append session narrative.

## Update Log

| Date | Who | Change |
|---|---|---|
| 2026-08-15 | Codex | Created planning-only trust arc brief; CI is prerequisite and T1 begins the arc. |

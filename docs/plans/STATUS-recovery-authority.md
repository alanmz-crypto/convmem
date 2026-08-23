# Arc Brief — Recovery Authority

> **Arc: Recovery Authority.** This is a current-state brief, not a changelog
> and grants no implementation or operational authority.

## 1. What This Is For (product goal)

ConvMem needs recovery that can restore provenance authority without confusing
capture evidence, JSONL, or Chroma projections with that authority. The goal is
an additive, fail-closed recovery contract: legacy complete-data-v2 remains
valid, provenance-aware recovery uses complete-data-v3, selected generations
are exact, projections can remain pending, and interruption cannot publish
mixed state.

## 2. System Design (how the pieces connect)

```text
complete-data-v3 Restic snapshot/tree
        │ exact (snapshot, tree, T_g, P_g, M_g)
        ▼
immutable provenance registry generation P_g
        │ manifest/history/graph validation
        ▼
recovered authority
        │ JSONL + Chroma exact projection agreement
        ├── projection pending / blocked (not serving)
        └── bounded CG-2 handoff → serving-ready (later, separately gated)

complete-data-v2 remains a legacy contract and is not migrated to v3.
```

## 3. What Exists Right Now (file map)

| Surface | State |
|---|---|
| `docs/plans/ARCHITECTURE-recovery-authority.md` | **Locked architecture** bytes at `22852a07e66920874045e0e85c4572ab6c0b29b8`; chooses v3 registry authority and bounded CG-1/CG-2 interfaces. |
| `docs/plans/EXECUTION-recovery-authority.md` | **Accepted Execution Plan** at `b0c1dd226fa4e1f7cee5c74ae99a13191d7742ab`; independently Kiro-verified (PASS, off-GitHub). |
| `docs/plans/VERIFY-recovery-authority.md` | Current arc VERIFY companion; maps to canonical V4/V8/V6/V7 rows. |
| `docs/plans/VERIFY-dependability-provenance.md` | Existing authoritative oracle rows; V4g–V4l/V8i/V8j/V8l remain deferred/PENDING and are not silently replaced. |
| `complete_data_restore.py` / `backup_workflows.py` / `restic_snapshot.py` | Existing v2 restore/profile surfaces; the **complete-data-v3 substrate and registry validation now exist** (T1). |
| `docs/RECOVER.md` | Existing v2 recovery guide and provenance integration boundary; **T1 v3 wording correction landed**. |
| CG-1/CG-2 generation and serving surfaces | Existing bounded contracts; V4k execution remains blocked pending CG-2 Design A ratification and stable semantics. |

## 4. Completion State

| Milestone | Status | Blocking on |
|---|---|---|
| Architecture Direction | **LOCKED** at `22852a07e66920874045e0e85c4572ab6c0b29b8` | — |
| Execution Plan | **ACCEPTED** at `b0c1dd226fa4e1f7cee5c74ae99a13191d7742ab`; Kiro PASS | — |
| Recovery Authority T1 | **COMPLETE / LANDED** via PR #234; squash SHA `cac3cc35b8a74d43f9d353554cb7c80cb2f13801` on `main` | — |
| T2 | **NOT AUTHORIZED** | Separate Ryan grant after T1 |
| T3–T4 implementation | **NOT AUTHORIZED / NOT STARTED** | Separate Ryan grants after T2 |
| V4k selected-generation/rollback execution | **BLOCKED (D1)** | CG-2 Design A ratification and stable generation/pointer semantics, then a fresh Ryan grant |
| Live recovery/activation | **NOT AUTHORIZED** | Separate Ryan operational grants; outside this package |

## 5. Your Role (read this to know what you're here to do)

**If you are Kiro:** the committed Execution Plan package has been reviewed at
the exact tip and returned `PASS` (off-GitHub). No further Kiro review is
required for the accepted plan; re-verify only if a downstream change alters its
boundaries.

**If you are Ryan:** decide whether to accept the Kiro-reviewed Plan (already
PASS) and issue separate Execute grants. T2 is the next planned task but is
NOT yet authorized. Do not treat plan acceptance or the T1 landing as live
recovery or authority activation.

**If you are Cursor:** do not begin from this brief. Wait for a Ryan grant
naming exactly one eligible task, branch/worktree, and acceptance evidence.
T1 is complete and landed; T2 onward are not authorized.

## 6. What Remains Before "Live" (sequential)

- [x] Kiro reviews the committed Execution Plan package (PASS, off-GitHub).
- [x] Ryan accepts the plan.
- [x] Ryan issues a separate T1 grant; T1 implemented, verified, and landed via PR #234 at `cac3cc35`.
- [ ] T2, T3, and T4 proceed only as separately granted downstream tasks (T2 next, still NOT AUTHORIZED).
- [ ] CG-2 Design A is ratified with stable generation/pointer semantics.
- [ ] Only after that unlock, Ryan may separately grant V4k planning/execute work (D1).
- [ ] Any live recovery, replacement, projection activation, or serving change
      requires a distinct Ryan operational grant.

## 7. Hard Stops (models cannot cross)

- No implementation, migration, bulk restore, live-data mutation, provenance
  authority activation, CG-2 activation, Shadow, R2b, V1h, V3i, T5, or T3
  reopening.
- No automatic v2→v3 migration or reinterpretation.
- No stale projection fallback or serving from projection-pending state.
- No V4k execution before CG-2 Design A ratification and stable semantics.
- No dedicated DeepSeek R1 adversarial direct/API call without Ryan's explicit
  grant; routine ConvMem/Ollama tooling is unaffected.

## 8. Relationship to ConvMem (the bigger picture)

Recovery Authority is a later, separately gated slice of the Dependability and
Provenance Trust Arc. It consumes the closed T3 provenance substrate and
interfaces with CG-1/CG-2 without reopening either. It does not close CG-2,
Shadow, R2b, migration, V1h, V3i, or T5.

## 9. Key Design Files (for deep dives)

| Purpose | Path |
|---|---|
| Locked direction | `docs/plans/ARCHITECTURE-recovery-authority.md` |
| Execution plan | `docs/plans/EXECUTION-recovery-authority.md` |
| Arc VERIFY companion | `docs/plans/VERIFY-recovery-authority.md` |
| Canonical existing oracles | `docs/plans/VERIFY-dependability-provenance.md` |
| Recovery guide | `docs/RECOVER.md` |
| Restore policy | `complete_data_restore.py` |
| Recovery workflow | `backup_workflows.py` and `restic_snapshot.py` |
| CG-2 generation/serving contracts | `file_generation_pointer.py`, `file_generation_contract.py`, `serving_authority.py` |
| Planning guide | `docs/planning/EXECUTION-PLANNING.md` |

## 10. How to Update This Brief (departure protocol)

Keep this file a current snapshot. Overwrite sections 3–6 when a milestone
changes; do not append session narrative. Add one milestone-level line to the
Update Log. Detailed work belongs in Track A session ingest and the committed
planning artifacts.

## Update Log

| Date | Who | Change |
|---|---|---|
| 2026-08-22 | Codex Luna | Created the Recovery Authority Execution Plan and VERIFY companion; T1–T4 remain unstarted and V4k is hard-blocked pending CG-2 Design A ratification. |
| 2026-08-23 | Crush (DeepSeek V4 Flash) | T1 completed, independently Kiro-verified (off-GitHub), and landed via PR #234 at squash SHA `cac3cc35b8a74d43f9d353554cb7c80cb2f13801` on `main`; status synced to post-T1 current state. |

**TL;DR:** Recovery Authority architecture is locked at `22852a07`, the
Execution Plan is accepted at `b0c1dd22`, and T1 is complete and landed on
`main` via PR #234 (squash SHA `cac3cc35`). T2 is next but NOT AUTHORIZED;
T3–T4 are unstarted; V4k (D1) remains blocked pending CG-2 Design A. No live
recovery, migration, activation, serving, or CG-2 authority is open.
[Arc Recovery Authority]

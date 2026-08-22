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
| `docs/plans/ARCHITECTURE-recovery-authority.md` | Locked architecture bytes at `22852a07`; chooses v3 registry authority and bounded CG-1/CG-2 interfaces. |
| `docs/plans/EXECUTION-recovery-authority.md` | Current Codex Execution Plan; four executable tasks plus blocked V4k, awaiting Kiro review. |
| `docs/plans/VERIFY-recovery-authority.md` | Current arc VERIFY companion; maps to canonical V4/V8/V6/V7 rows; no evidence yet. |
| `docs/plans/VERIFY-dependability-provenance.md` | Existing authoritative oracle rows; V4g–V4l/V8i/V8j/V8l remain deferred/PENDING and are not silently replaced. |
| `complete_data_restore.py` / `backup_workflows.py` / `restic_snapshot.py` | Existing v2 restore/profile surfaces; v3 integration is planned, not implemented. |
| `docs/RECOVER.md` | Existing v2 recovery guide and future provenance integration boundary; v3 wording correction is a T1 execution obligation. |
| CG-1/CG-2 generation and serving surfaces | Existing bounded contracts; V4k execution is blocked pending CG-2 Design A ratification and stable semantics. |

## 4. Completion State

| Milestone | Status | Blocking on |
|---|---|---|
| Architecture Direction | **LOCKED** at `22852a07` | — |
| Execution Plan | **AUTHORED / KIRO REVIEW PENDING** | Kiro verdict, then Ryan Execute decision |
| VERIFY companion | **AUTHORED / NO EVIDENCE** | Later task execution |
| T1–T4 implementation | **NOT AUTHORIZED / NOT STARTED** | Separate Ryan grants after Kiro plan review |
| V4k selected-generation/rollback execution | **BLOCKED** | CG-2 Design A ratification and stable generation/pointer semantics, then separate Ryan grant |
| Live recovery/activation | **NOT AUTHORIZED** | Separate Ryan operational grants; outside this package |

## 5. Your Role (read this to know what you're here to do)

**If you are Kiro:** review `EXECUTION-recovery-authority.md` and
`VERIFY-recovery-authority.md` at the exact committed tip. Return `PASS`, `PASS
WITH REQUIRED AMENDMENTS`, or `FAIL`; verify boundaries, evidence, v2/v3
coexistence, V4k hard blocking, and no implicit activation.

**If you are Ryan:** decide whether to accept the Kiro-reviewed plan and issue
separate Execute grants. Do not treat plan acceptance as live recovery or
authority activation.

**If you are Cursor:** do not begin from this brief. Wait for a Ryan grant
naming exactly one eligible task, branch/worktree, and acceptance evidence.

## 6. What Remains Before "Live" (sequential)

- [ ] Kiro reviews the committed Execution Plan package.
- [ ] Ryan accepts the plan or directs bounded amendments.
- [ ] Ryan issues a separate T1 grant; Cursor implements and returns evidence.
- [ ] T2, T3, and T4 proceed only as separately granted downstream tasks.
- [ ] CG-2 Design A is ratified with stable generation/pointer semantics.
- [ ] Only after that unlock, Ryan may separately grant V4k planning/execute work.
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

**TL;DR:** Recovery Authority is architecture-locked and now has a bounded
Execution Plan ready for Kiro review; no Execute or live recovery authority is
open. [Arc Recovery Authority]

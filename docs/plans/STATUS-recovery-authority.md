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
| `complete_data_restore.py` / `backup_workflows.py` / `restic_snapshot.py` | Existing v2 restore/profile surfaces; the **complete-data-v3 substrate and registry validation exist** (T1), the **projection-agreement state machine exists** (T2), and the scratch-only orchestration entry is wired (T3). |
| `recovery_bulk_workflow.py` / `scripts/complete_data_restore_preflight.py` | **T3 landed** via PR #238 at `d250feb2bbbf81e2c3dd8513d79fb0e2140266a3`; exact-snapshot, empty-target, scratch-only candidate preparation with no live publication. |
| `docs/RECOVER.md` | Existing v2 recovery guide plus landed T1/T3 provenance and scratch-workflow boundaries. |
| CG-1/CG-2 generation and serving surfaces | Design A Execute-close is on `main`; later reference-v2 corrective work remains branch-only. V4k remains blocked until the separately governed serving/recovery dependency is accepted, implemented, and verified. |

## 4. Completion State

| Milestone | Status | Blocking on |
|---|---|---|
| Architecture Direction | **LOCKED** at `22852a07e66920874045e0e85c4572ab6c0b29b8` | — |
| Execution Plan | **ACCEPTED** at `b0c1dd226fa4e1f7cee5c74ae99a13191d7742ab`; Kiro PASS | — |
| Recovery Authority T1 | **COMPLETE / LANDED** via PR #234; squash SHA `cac3cc35b8a74d43f9d353554cb7c80cb2f13801` on `main` | — |
| Recovery Authority T2 | **COMPLETE / INDEPENDENTLY VERIFIED / LANDED** via PR #236; reviewed tip `c91a218015caadb82ce6294358777234d90754e5`; landing SHA `62f0f2355543f1daefa237bfc0811f94d8982989` on `main` | — |
| Recovery Authority T3 | **COMPLETE / LANDED** via PR #238; landing SHA `d250feb2bbbf81e2c3dd8513d79fb0e2140266a3` on `main` | — |
| Recovery Authority T4 | **NOT AUTHORIZED / NOT STARTED** | Separate Ryan T4 grant; T3 landing does not grant recovery-side crash-closure implementation |
| V4k selected-generation/rollback execution | **BLOCKED (D1)** | CG-2 reference-v2 serving/recovery dependency closure, then a fresh Ryan grant |
| Live recovery/activation | **NOT AUTHORIZED** | Separate Ryan operational grants; outside this package |

## 5. Your Role (read this to know what you're here to do)

**If you are Kiro:** the committed Execution Plan package has been reviewed at
the exact tip and returned `PASS` (off-GitHub). No further Kiro review is
required for the accepted plan; re-verify only if a downstream change alters its
boundaries.

**If you are Ryan:** T1, T2, and T3 are complete and landed. Decide separately
whether to grant T4 recovery-side interruption/crash-closure verification. Do
not treat any landing as live recovery, replacement, serving, or authority
activation.

**If you are Cursor:** do not begin from this brief. Wait for a Ryan grant
naming exactly one eligible task, branch/worktree, and acceptance evidence.
T1–T3 are complete and landed; T4 is not authorized. V4k remains blocked.

## 6. What Remains Before "Live" (sequential)

- [x] Kiro reviews the committed Execution Plan package (PASS, off-GitHub).
- [x] Ryan accepts the plan.
- [x] Ryan issues a separate T1 grant; T1 implemented, verified, and landed via PR #234 at `cac3cc35`.
- [x] Ryan issues a separate T2 grant; T2 implemented, independently verified, and landed via PR #236.
- [x] Ryan issues a separate T3 grant; scratch-only bulk recovery implemented, verified, and landed via PR #238 at `d250feb2`.
- [ ] T4 proceeds only under a separate Ryan grant; it is NOT AUTHORIZED.
- [ ] CG-2 reference-v2 serving/recovery semantics close under their separate plan, implementation, and verification gates.
- [ ] Only after that dependency closes may Ryan separately grant V4k planning/execute work (D1).
- [ ] Any live recovery, replacement, projection activation, or serving change
      requires a distinct Ryan operational grant.

## 7. Hard Stops (models cannot cross)

- No T4 or V4k implementation, migration, live restore, replacement, live-data
  mutation, provenance authority activation, CG-2 activation, Shadow, R2b,
  V1h, V3i, T5, or closed provenance-T3 reopening.
- No automatic v2→v3 migration or reinterpretation.
- No stale projection fallback or serving from projection-pending state.
- No V4k execution before the CG-2 reference-v2 serving/recovery dependency
  closes and Ryan issues a fresh V4k grant.
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
| 2026-08-31 | Kiro | Recorded prior-art input for the still-unauthorized T4/V4l boundary inventory (link to `docs/kernel-panic-durability-insight-2026-08-31.md`, findings from a real unclean kernel panic). T4 remains NOT AUTHORIZED / NOT STARTED; no status change. |
| 2026-08-30 | Codex Sol | Reconciled the brief to live `main`: T3 landed via PR #238 at `d250feb2`; T4 remains unstarted/unauthorized and V4k remains separately blocked. |
| 2026-08-23 | Cursor | T2 Execute started: authority recovery / projection agreement state machine on feat branch. |
| 2026-08-22 | Codex Luna | Created the Recovery Authority Execution Plan and VERIFY companion; T1–T4 remain unstarted and V4k is hard-blocked pending CG-2 Design A ratification. |
| 2026-08-23 | Crush (DeepSeek V4 Flash) | T1 completed, independently Kiro-verified (off-GitHub), and landed via PR #234 at squash SHA `cac3cc35b8a74d43f9d353554cb7c80cb2f13801` on `main`; status synced to post-T1 current state. |
| 2026-08-23 | Crush | T2 completed, independently verified (exact-tip BugBot clean + Kiro PASS), and landed via PR #236 at SHA `62f0f2355543f1daefa237bfc0811f94d8982989` on `main` (reviewed tip `c91a218015caadb82ce6294358777234d90754e5`); status synced to post-T2 current state. |

**TL;DR:** Recovery Authority T1–T3 are landed on `main` (PRs #234, #236,
and #238); T3 is scratch-only and non-serving. T4 remains unstarted and
unauthorized, while V4k remains blocked on separately governed CG-2
reference-v2 closure. No live recovery, replacement, activation, serving, or
CG-2 authority is open.
[Arc Recovery Authority]

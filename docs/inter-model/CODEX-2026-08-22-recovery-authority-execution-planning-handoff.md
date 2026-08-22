# Codex Handoff — Recovery Authority Execution Planning

**Arc:** Recovery Authority  
**Date:** 2026-08-22  
**Author:** OpenAI Codex / Luna — planning lane  
**For:** Kiro Execution Plan review → Ryan  
**Authorization:** Ryan, Execution Planning only  
**Execute:** NOT AUTHORIZED

## Resume state

| Field | Value |
|---|---|
| **State** | `READY_FOR_KIRO` |
| **Branch** | `plan/2026-08-22-recovery-authority` |
| **Tip SHA** | Final package tip is the pushed branch tip reported with this handoff; architecture bytes remain `22852a07e66920874045e0e85c4572ab6c0b29b8`. |
| **Push status** | Must be pushed to origin before handoff; no merge to main. |
| **PR** | Not opened |
| **Ryan GATE** | Kiro Execution Plan verdict, then Ryan's separate Execute grants. |
| **V4k gate** | **BLOCKED** pending CG-2 Design A ratification and stable generation/pointer semantics. |

## What was produced

The package turns the locked Recovery Authority direction into four serial,
separately grantable Cursor tasks:

1. **T1** — complete-data-v3 profile and durable registry/manifest validation,
   including v2 coexistence, sidecar separation, `docs/RECOVER.md` wording,
   and V8i v3 retarget obligations.
2. **T2** — whole-registry authority recovery and exact JSONL/Chroma
   projection-agreement state machine, including pending/blocked states.
3. **T3** — scratch-only, Ryan-gated bulk-recovery workflow with exact Restic
   snapshot/tree binding and no-live-change proof.
4. **T4** — recovery-side interruption/crash closure, explicitly bounded away
   from broad T5.
5. **D1/V4k** — selected-generation/rollback continuity represented as
   **BLOCKED**, not merely deferred, until CG-2 Design A is ratified and its
   generation/pointer model is stable.

## Review files

- [`EXECUTION-recovery-authority.md`](../plans/EXECUTION-recovery-authority.md)
- [`VERIFY-recovery-authority.md`](../plans/VERIFY-recovery-authority.md)
- [`STATUS-recovery-authority.md`](../plans/STATUS-recovery-authority.md)
- [`ARCHITECTURE-recovery-authority.md`](../plans/ARCHITECTURE-recovery-authority.md)
- [`LATEST.md`](LATEST.md) — active handoff pointer

## Guardrails for Kiro review

- Check the locked architecture bytes, not the carrier SHA, as the architecture
  revision.
- Confirm V4g–V4j, V4k, and V4l remain separately grantable.
- Confirm v2 snapshots retain their existing contract and cannot be implicitly
  migrated or reinterpreted as v3.
- Confirm the companion maps to, rather than forks, the existing authoritative
  VERIFY rows.
- Confirm no task activates provenance authority, CG-2 serving, or live data.

## What not to do

- Do not implement, migrate, restore, mutate live data, activate a registry or
  serving pointer, run broad T5 fault injection, reopen T3, or merge main.
- Do not invoke dedicated DeepSeek R1 adversarial API critique merely because
  it appeared in the earlier architecture lifecycle.
- Do not open V4k until the exact CG-2 Design A dependency is ratified and
  stable; if semantics change, amend V4k before any grant.

## Next action

Kiro reviews the committed package at the exact final branch tip and returns
`PASS`, `PASS WITH REQUIRED AMENDMENTS`, or `FAIL`. Ryan then decides whether
to accept the plan and issue one separate Execute grant. Codex stops at this
phase boundary.

**TL;DR:** The Recovery Authority Execution Plan and VERIFY companion are
ready for Kiro; T1–T4 are not authorized, and V4k is hard-blocked on CG-2
Design A. [Arc Recovery Authority]

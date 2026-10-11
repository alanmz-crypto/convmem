# Arc Brief — Safe Harbor

> **Arc: Safe Harbor. DIRECTION APPROVED at `5ea16a6`; name confirmed; E4 OPEN; EXECUTION PLANNING PENDING.** Current planning state; no implementation or operational authority. Read the architecture for the approved direction contracts; this brief is the orientation source.

## 1. What This Is For (product goal)

Make ConvMem's recovery and incident handling remain dependable across agents, processes and time. Durability is first; convenience is second. The requirements are: no verified recovery point before risky change means no change; unexpected results stop the affected operation for investigation; production is never repaired blindly.

The proposed direction uses existing Rescuezilla/Restic backups and the existing guarded Chroma quarantine, with stronger target binding, unknown-state handling, evidence preservation and validated release. It does not promise universal write prevention.

## 2. System Design (how the pieces connect)

```text
exact recovery artifact + scoped qualification + Ryan operation grant
                         |
              resolved operation target/profile
                         |
              existing recovery/write preflight
                         |
         existing native lock + quarantine admission
               /                         \
     admitted bounded operation       unresolved incident
                                          |
                              preserve before replacement
                                          |
                          validate/dispose under same lock
                                          |
                            explicit authorized release

doctor / audit result / events = observations and history
QUARANTINE.json = all unresolved incidents for guarded Chroma writes
```

The scope is application cooperation, not same-user security. Read clients can perform incidental writes; direct clients, other durable-state publishers and shell/service tools do not all pass this guard.

## 3. What Exists Right Now (file map)

- `ARCHITECTURE-safe-harbor.md`: direction approved by Ryan at `5ea16a6c7af7900b981d19eb03b168d77f611718`, following Opus delta PASS at `505a4224b5c078a2379ebe16444ca757cc69b7db` (85%) and Kiro governing PASS at the approved revision (88%). Approval includes owner disposition after every automatic segment restore. Subsequent edits record approval, naming and review routing; the approved contracts are unchanged.
- `STATUS-safe-harbor.md`: this current-state brief; required arc lists and routing point here.
- Deployed runtime: `.worktrees/runtime-main` at `a92a74eb326b3eaa59087b707de10153c7cc0c63` when checked on resume. Installed launcher still points there.
- Planning base: `6a23aa93184460ed853996608bb28190c61f8d89`. It contains the detector; it is not the deployed release.
- Existing code: `restic_gate.py`, `backup_workflows.py`, `restic_snapshot.py`, `chroma_write_guard.py`, `propose_decision.py` and `doctor.py`. Known contract gaps and pinned source evidence are in architecture section 3.
- Detector candidate: CPU/vector-loss PR #341, exact `5c6a4a8ad51c968a27afc1c8726fc78c4801cb6d`. Deployment is a separate Ryan decision; no watch start or broad catch-up is implied.
- Backup access on resume: doctor exited 0; local snapshot, external lineage copy and matching offline password copy passed. This is access/freshness evidence, not demonstrated restoration.
- Fresh Rescuezilla image: completion, identifier, scope and destination not yet confirmed. The reported September 16 pre-incident image should be preserved.
- No Safe Harbor implementation, execution plan, VERIFY companion or operational activation exists. A VERIFY artifact is required later before arc closure; it is not a reason to fabricate completed evidence now.

## 4. Completion State

- Review synthesis and pre-reboot checkpoint: preserved at `bc3a6fd34bc594024d53fb86c9ca6b312cb64bd1` on the separate checkpoint branch.
- Architecture direction: **APPROVED at `5ea16a6`**, existing backups and strengthened admission/incident contracts; seven planning obligations remain in architecture section 8.
- Arc name: **CONFIRMED — Safe Harbor** by Ryan.
- Opus review/delta: **COMPLETE — DELTA PASS at `505a422` (85%)**. Both blockers resolved; E1–E7 accepted as planning obligations. Opus explicitly required no further round for its exact E7 clarification, now included.
- Kiro governing design sign-off: **PASS at `5ea16a6` (88%)**, no direction blockers; relayed by Ryan in this conversation.
- E4 backup-interface review: **OPEN / TARGETED KIRO REVIEW NEXT**. Ryan requested the read-only review prompt; no review has run in this step and no ownership transfer was granted.
- Ryan direction approval: **APPROVED at `5ea16a6`**, explicitly including disposition after every automatic segment restore.
- Execution Planning, implementation, verification and deployment: **NOT AUTHORIZED by this brief**.

## 5. Your Role (read this to know what you're here to do)

**Codex:** Approval and name are recorded; the targeted Kiro E4 prompt is prepared. Await its verdict and Ryan's subsequent phase decision. Execution planning remains pending even after an E4 PASS until Ryan authorizes that phase. Do not treat approval as completed evidence or backup qualification.

**Opus:** The first review and delta cadence is complete. No further review for the requested E7 clause; return only if new contracts beyond that clarification are introduced.

**Kiro:** Governing direction review is complete at `5ea16a6`. Next is the targeted, read-only Complete-data Backup v2 interface review described in architecture section 10; explicitly state whether E4 is satisfied. This does not transfer ownership, close the Hybrid audit or authorize implementation.

**Ryan:** Direction and name are confirmed. Review Kiro's E4 verdict, then decide whether to authorize execution planning. Recovery/loss-window inputs remain outstanding before operational protection can be declared adequate; operational grants remain distinct.

**Cursor / ops:** Do not implement or deploy from this brief. Wait for the accepted downstream plan and a named phase/operation grant.

## 6. What Remains Before "Live" (sequential)

1. Kiro completes the targeted Complete-data Backup v2 interface review and issues an explicit E4 verdict; the earlier Safe Harbor design PASS did not satisfy this prerequisite.
2. Return to Ryan for the pending execution-planning decision; no phase transition is implied by an E4 PASS.
3. Under a subsequent planning grant, execution/verification planning must resolve E1–E7 before the plan can be accepted, under the applicable review/approval gates. Resolve recovery/loss-window inputs without inferring image usability or owner acceptance.
4. Only after a separate grant: bounded implementation and isolated evidence gathering.
5. Any deployment or corpus-affecting operation requires its own exact scope, recovery evidence and Ryan grant. The standalone detector remains a separate decision.

## 7. Hard Stops (models cannot cross)

- No runtime, production data, service, backup-repository, key, retention or installed-permission changes from the planning grant.
- No restore drills, production experiments, indexing, ledger record or merge from this brief.
- No Recovery Authority T4/V4k, v3 authority/serving activation, migration or generalized repair. Read that arc's current STATUS hard stops.
- No generic HOLD, identity registry, freeze, broad constructor change or automatic cleanup subsystem under this direction.
- No claim that gate PASS proves recovery, that zero missing vector IDs proves semantic integrity, or that quarantine covers arbitrary same-user writers.
- No automatic phase transition. A published or merged architecture is not execution or deployment authorization.

## 8. Relationship to ConvMem (the bigger picture)

Safe Harbor proposes stricter contracts around existing local guard and approval-recovery paths. Complete-data Backup v2 still owns its resolver, eligibility/gate interfaces, snapshot/restore profile and open Hybrid consistency audit; Recovery Authority still owns provenance-aware recovery and its T4/V4k dependencies. Other run-ledger, generation and permission surfaces retain their own owners.

The architecture records these interfaces and refuses to claim a global freeze. It does not change those other arcs' statuses or silently finish their deferred work.

## 9. Key Design Files (for deep dives)

- [Safe Harbor architecture](ARCHITECTURE-safe-harbor.md): proposed direction, evidence, risks and reviewer assignment.
- [Reboot checkpoint](https://github.com/alanmz-crypto/convmem/blob/bc3a6fd34bc594024d53fb86c9ca6b312cb64bd1/docs/inter-model/CODEX-2026-10-11-durability-reboot-checkpoint.md): review provenance and saved pre-reboot state.
- [Recovery Authority STATUS](STATUS-recovery-authority.md): ownership and hard stops.
- [Complete-data Backup v2 STATUS](STATUS-complete-data-backup-correction-v2.md): existing profile/restore contract and open consistency audit.
- [Team charter](../inter-model/TEAM-CHARTER-2026-07-06.md) and [decision/review guardrails](../inter-model/DECISION-REVIEW-GUARDRAILS.md): authority and review discipline.
- [Architecture Planning guide](../planning/ARCHITECTURE-PLANNING.md): active phase and stop condition.

## 10. How to Update This Brief (departure protocol)

Overwrite sections 3–6 when the actual state changes. Keep runtime observations dated and scoped; do not turn them into permanent green guarantees. Other orientation surfaces should point here instead of duplicating mutable milestones. Add one milestone-level update line; keep detailed review discussion in the architecture or review artifact. If Ryan renames the arc, rename the matching files and their pointers together.

## Update Log

- 2026-10-11 — Codex: resumed from the GitHub checkpoint and authored the provisional Safe Harbor direction/brief; independent review and Ryan approval remain pending.
- 2026-10-11 — Codex: corrected Opus's two first-review blockers and recorded E1–E7; exact-revision delta review is next, with Kiro sign-off and Ryan approval still pending.
- 2026-10-11 — Codex: recorded Opus delta PASS at `505a422` and added its exact E7 disposition clause; Kiro governing review is next, with Ryan approval pending.
- 2026-10-11 — Codex: recorded Kiro governing PASS at `5ea16a6` (88%); Ryan's direction decision and E4 remain open, with no execution-planning or live-action grant.
- 2026-10-11 — Codex: recorded Ryan's approval at `5ea16a6` and confirmed Safe Harbor; targeted Kiro E4 prompt prepared, with execution planning explicitly pending.

## TL;DR

[Arc Safe Harbor] Ryan approved the architecture at `5ea16a6`, accepted disposition after every automatic segment restore and confirmed the name. Targeted Kiro E4 review is next; execution planning remains pending. E1–E7 are obligations, not proven implementation; fresh-image completion and the loss window remain unconfirmed. No live action is authorized.

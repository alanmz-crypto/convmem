# Arc Brief — Safe Harbor

> **Arc: Safe Harbor (provisional name). DRAFT / NOT APPROVED.** Current planning state; no implementation or operational authority. Read the architecture for normative proposed contracts; this brief is the orientation source.

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
QUARANTINE.json = incident authority for guarded Chroma writes
```

The scope is application cooperation, not same-user security. Read clients can perform incidental writes; direct clients, other durable-state publishers and shell/service tools do not all pass this guard.

## 3. What Exists Right Now (file map)

- `ARCHITECTURE-safe-harbor.md`: authored direction draft on `plan/2026-10-11-safe-harbor`; Opus and Kiro have not reviewed this artifact.
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
- Architecture direction: **DRAFT**, one recommended option, review and approval pending.
- Arc name: **PROVISIONAL**; Ryan was asked to confirm or rename it.
- Opus review/delta: **NOT STARTED for this artifact**.
- Kiro governing design sign-off: **NOT STARTED for this artifact**.
- Ryan direction approval: **PENDING**.
- Execution Planning, implementation, verification and deployment: **NOT AUTHORIZED by this brief**.

## 5. Your Role (read this to know what you're here to do)

**Codex:** Author/revise the architecture from concrete findings. Stop before execution planning until Ryan accepts the direction. Do not convert a proposed mechanism or backup report into verified evidence.

**Opus:** Independently review the exact direction using architecture section 10. Identify blockers and counterexamples; subsequent review focuses on corrections and new evidence.

**Kiro:** Provide governing design review/sign-off. Opus review does not replace your gate.

**Ryan:** Confirm the title, provide the recovery/loss-window inputs, and decide whether to approve the reviewed direction. Operational grants remain distinct.

**Cursor / ops:** Do not implement or deploy from this brief. Wait for the accepted downstream plan and a named phase/operation grant.

## 6. What Remains Before "Live" (sequential)

1. Resolve draft comments and owner inputs without inferring image usability or a loss window.
2. Opus reviews the exact architecture; Codex corrects it; Opus checks the delta; Kiro supplies governing sign-off.
3. Ryan accepts or rejects the architecture direction, including its cross-arc boundary.
4. Only after acceptance: execution/verification planning and the applicable review/approval gates.
5. Only after a separate grant: bounded implementation and isolated evidence gathering.
6. Any deployment or corpus-affecting operation requires its own exact scope, recovery evidence and Ryan grant. The standalone detector remains a separate decision.

## 7. Hard Stops (models cannot cross)

- No runtime, production data, service, backup-repository, key, retention or installed-permission changes from the planning grant.
- No restore drills, production experiments, indexing, ledger record or merge from this brief.
- No Recovery Authority T4/V4k, v3 authority/serving activation, migration or generalized repair. Read that arc's current STATUS hard stops.
- No generic HOLD, identity registry, freeze, broad constructor change or automatic cleanup subsystem under this direction.
- No claim that gate PASS proves recovery, that zero missing vector IDs proves semantic integrity, or that quarantine covers arbitrary same-user writers.
- No automatic phase transition. A published or merged architecture is not execution or deployment authorization.

## 8. Relationship to ConvMem (the bigger picture)

Safe Harbor proposes stricter contracts around existing local guard and approval-recovery paths. Complete-data Backup v2 still owns its snapshot/restore profile and open Hybrid consistency audit; Recovery Authority still owns provenance-aware recovery and its T4/V4k dependencies. Other run-ledger, generation and permission surfaces retain their own owners.

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

## TL;DR

Safe Harbor is a planning draft using existing recovery and quarantine mechanisms. The next lane is independent review, followed by Kiro sign-off and Ryan's direction decision. No implementation or live action is authorized; fresh-image completion and the loss window remain open.

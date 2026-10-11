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
QUARANTINE.json = all unresolved incidents for guarded Chroma writes
```

The scope is application cooperation, not same-user security. Read clients can perform incidental writes; direct clients, other durable-state publishers and shell/service tools do not all pass this guard.

## 3. What Exists Right Now (file map)

- `ARCHITECTURE-safe-harbor.md`: corrected direction draft on `plan/2026-10-11-safe-harbor`; Opus's first review of `4d6faf22171525ab917a0f3773a14cfd08e56440` accepted the direction but failed the text on gate-scope authority and incident replacement. Both are corrected for delta review; no PASS is inferred.
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
- Architecture direction: **DRAFT / CORRECTED**, one recommended option; standing index/plain-add gate exemptions retained explicitly, all unresolved incidents retained in the existing authority. Seven planning obligations are recorded in architecture section 8.
- Arc name: **PROVISIONAL**; Ryan was asked to confirm or rename it.
- Opus review/delta: **FIRST REVIEW FAIL at `4d6faf2`; CORRECTIONS AWAIT DELTA REVIEW** on the exact new revision. Review scope: the two blockers, E1–E7 and correction-induced regressions.
- Kiro governing design sign-off: **NOT STARTED for this artifact**.
- Ryan direction approval: **PENDING**.
- Execution Planning, implementation, verification and deployment: **NOT AUTHORIZED by this brief**.

## 5. Your Role (read this to know what you're here to do)

**Codex:** Corrections are prepared for independent delta review. Revise only remaining findings; stop before execution planning until Ryan accepts the direction and the backup-interface ownership prerequisite is satisfied. Do not convert proposed contracts or backup reports into verified evidence.

**Opus:** Delta-review the exact correction against `4d6faf22171525ab917a0f3773a14cfd08e56440`, using architecture section 10: the two blockers, E1–E7 and regressions caused by those edits. Do not repeat the original full review without a new contract or new evidence requiring it.

**Kiro:** Provide governing design review/sign-off. Opus review does not replace your gate.

**Ryan:** Confirm the title, provide the recovery/loss-window inputs, and decide whether to approve the reviewed direction. Operational grants remain distinct.

**Cursor / ops:** Do not implement or deploy from this brief. Wait for the accepted downstream plan and a named phase/operation grant.

## 6. What Remains Before "Live" (sequential)

1. Opus delta-reviews the corrected architecture; Codex addresses any remaining blockers; Kiro supplies governing sign-off.
2. Resolve owner inputs without inferring image usability or a loss window; Ryan accepts or rejects the direction, including operator disposition after every automatic restore.
3. Before execution planning, obtain Complete-data Backup v2 interface review or Ryan's explicit transfer for resolver/eligibility/gate changes.
4. Only after acceptance and that ownership prerequisite: execution/verification planning must resolve E1–E7 before the plan can be accepted, under the applicable review/approval gates.
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

## TL;DR

[Arc Safe Harbor, provisional] The draft now explicitly retains the standing gate exemptions and requires retention of every unresolved incident. Opus's bounded delta review is next, followed by Kiro sign-off and Ryan's direction decision. E1–E7 are planning obligations; no implementation or live action is authorized. Fresh-image completion and the loss window remain open.

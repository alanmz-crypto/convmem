# Arc Brief — Safe Harbor

> **Arc: Safe Harbor. BOUNDED BRANCH UPDATE AUTHORIZED.** Cursor's two test corrections passed isolated evidence and Copilot's delta review at `2977c45` (85%). PR #387 conflicts with main `5550def` in routing and generated inventory; successor pytest/pylint did not run. Ryan authorized integrating that base, regenerating the inventory, fresh CI and final-tip review. Execution section 8 defines the boundary. BugBot reviewed no SHA; its gate and T1 acceptance remain open. No PR merge, deployment or T2–T5 grant.

## 1. What This Is For (product goal)

Make ConvMem's recovery and incident handling remain dependable across agents, processes and time. Durability is first; convenience is second. The requirements are: no verified recovery point before risky change means no change; unexpected results stop the affected operation for investigation; production is never repaired blindly.

The accepted direction uses existing Rescuezilla/Restic backups and the existing guarded Chroma quarantine, with stronger target binding, unknown-state handling, evidence preservation and validated release. It does not promise universal write prevention.

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
- E4 review: Kiro's PASS (85%) at `20283bdc536f9f2d9ccf7c44a75a17f5a26e1d61` is confirmed for the full intended scope by its coverage addendum at `1268a500d7ac8f4a94f816d90817e21ad8e2c342`. Ownership is unchanged. Architecture section 10 preserves B-E4.1/O-E4.a–e and Codex's two qualifications: the probe disables current-day checking, and the approved contract adds approval recovery to the existing preflight rather than selecting a separate check.
- `STATUS-safe-harbor.md`: this current-state brief; required arc lists and routing point here.
- `EXECUTION-safe-harbor.md`: five-task plan reviewed PASS at `00c69d2` (85%), followed by Kiro delta PASS at `dca13a5` (88%), and accepted by Ryan at that successor. Section 7 records B-E4.1/all five consumer outcomes. Section 8 now records Ryan's subsequent bounded T1 correction verbatim; its narrow store-file scope addition is explicit. T2–T5 are not implemented.
- T1 workspace: `fix/2026-10-11-safe-harbor-t1` at `/home/lauer/Projects/convmem/.worktrees/fix-2026-10-11-safe-harbor-t1`. Runtime code is `496792fad80d9759ca26e5cbf2ad7d6cd60bc28e`, unchanged since. The review-evidence test correction is `8b410445ac55f3a5dafede030a40f26c318ae784`, pushed; the evidence commit after it changes docs only. Do not switch the shared checkout or runtime-main.
- `VERIFY-safe-harbor.md`: historical 41/43-test results, the 61-test CI correction and green CI at `677c8a0` are preserved. The successor section records both corrections at `8b41044`. Results: 63 passed as standard pytest with the real home and the isolation flag unset; 45 passed with outer isolation. Each correction has a control that fails its proof assertion as expected. Successor CI/review are pending. Copilot's static review is separate from the unsatisfied BugBot gate. V2–V6 remain NOT RUN.
- Deployed runtime: `.worktrees/runtime-main` at `a92a74eb326b3eaa59087b707de10153c7cc0c63` when checked on resume. Installed launcher still points there.
- Planning base: `6a23aa93184460ed853996608bb28190c61f8d89`. It contains the detector; it is not the deployed release.
- Existing code: `restic_gate.py`, `backup_workflows.py`, `restic_snapshot.py`, `chroma_write_guard.py`, `propose_decision.py` and `doctor.py`. Known contract gaps and pinned source evidence are in architecture section 3.
- Detector candidate: CPU/vector-loss PR #341, exact `5c6a4a8ad51c968a27afc1c8726fc78c4801cb6d`. Deployment is a separate Ryan decision; no watch start or broad catch-up is implied.
- Backup access during execution-plan drafting on 2026-10-11: required doctor exited 0; local snapshot, external lineage copy and matching offline password copy passed. This is access/freshness evidence, not demonstrated restoration; CLI read paths may perform bookkeeping writes.
- Fresh Rescuezilla image: completion, identifier, scope and destination not yet confirmed. The reported September 16 pre-incident image should be preserved.
- Additional backup destination: Ryan supplied `/run/media/lauer/ext-ex4-1T-NVMe/`; read-only mount/capacity inspection confirmed ext4 and available space. Execution section 6 records UUID/capacity and proposes a fresh-image destination. No drive write, backup allocation or qualification was performed.
- Safe Harbor T1, including the three authorized corrections, is implemented only on `fix/2026-10-11-safe-harbor-t1` at runtime `496792f`. It is not merged, deployed, or an operator release. Ordinary clear still cannot release incidents. Old writers that predate this marker can still overwrite or clear it, so this task cannot be deployed alone.

## 4. Completion State

- Review synthesis and pre-reboot checkpoint: preserved at `bc3a6fd34bc594024d53fb86c9ca6b312cb64bd1` on the separate checkpoint branch.
- Architecture direction: **APPROVED at `5ea16a6`**, existing backups and strengthened admission/incident contracts; seven planning obligations remain in architecture section 8.
- Arc name: **CONFIRMED — Safe Harbor** by Ryan.
- Opus review/delta: **COMPLETE — DELTA PASS at `505a422` (85%)**. Both blockers resolved; E1–E7 accepted as planning obligations. Opus explicitly required no further round for its exact E7 clarification, now included.
- Kiro governing design sign-off: **PASS at `5ea16a6` (88%)**, no direction blockers; relayed by Ryan in this conversation.
- E4 backup-interface review: **COMPLETE — FULL-SCOPE PASS (85%)**, confirmed by Kiro's addendum at `1268a50`. No ownership transfer. Its B-E4.1/O-E4.a–e obligations were carried into the now-accepted execution plan; source/contract qualifications remain in architecture section 10. E4 compatibility alone did not approve the detailed change; Ryan's later owner approval is recorded separately below.
- Ryan direction approval: **APPROVED at `5ea16a6`**, explicitly including disposition after every automatic segment restore.
- Execution Planning: **COMPLETE — RYAN ACCEPTED `dca13a59a2edf649ac6a19777f572645bea8674e`** after Kiro delta PASS (88%); initial PASS remains pinned to `00c69d2` (85%). A1/A2 and O-E4.e are satisfied plan-side. No required review correction remains.
- **B-E4.1 owner disposition: APPROVED**, by Ryan explicitly as owner, exactly T2 at the accepted revision including all five consumer outcomes. Ownership is unchanged; this is contract approval, not implementation or live activation.
- **T1: TWO TEST CORRECTIONS IMPLEMENTED / SUCCESSOR REVIEW PENDING.** Canonical client/cache identity, persisted-empty refusal and the overwrite control were already implemented. Candidate `677c8a0` added the standard-pytest/derived-inventory correction and had green CI plus Copilot's static PASS (72%) with advisories. At Ryan's direction, test code `8b41044` keeps fixture isolation through each fault-injection cleanup. It also proves that the writer fails a nonblocking acquisition of the same native lock while the audit is paused, then refuses after publication. A pre-lock-pause control fails that proof. Ryan has not accepted T1.
- **Draft PR #387: OPEN.** The two authorized BugBot attempts failed on quota and reviewed no SHA. No further trigger, PR state change or comment is granted here. Copilot's review does not automatically satisfy the separate BugBot gate.
- T2–T5 implementation, live operations, merge and deployment: **NOT AUTHORIZED**. No phase auto-advance.

## 5. Your Role (read this to know what you're here to do)

**Codex:** Coordinate the authorized base integration, fresh CI and focused final-tip review under execution section 8. Copilot passed the two-test delta at `2977c45` (85%); review the new integration rather than repeating the unchanged architecture. Prepare any required exact-tip outage acceptance only after the candidate is concrete.

**Opus:** The first review and delta cadence is complete. No further review for the requested E7 clause; return only if new contracts beyond that clarification are introduced.

**Kiro:** First execution review and delta are complete, with successor PASS at `dca13a5` (88%). Ryan supplied the B-E4.1 owner decision and accepted that revision. No further review is requested for this status-only update, and no ownership was transferred to you.

**Ryan:** The two test corrections are authorized. After corrected evidence and successor review, decide T1 acceptance and any exact-tip outage acceptance for the missing BugBot review. Merge and later/live grants remain separate. Recovery/loss-window inputs remain open before live rollout; the new drive is not a backup/restore grant.

**Cursor:** Merge pinned main `5550def` into the dedicated T1 branch, preserve both routing entries, regenerate the derived inventory, inspect automatic source merges and collect isolated integration evidence as granted in execution section 8. A feature-branch merge is authorized; merging PR #387 into main remains ungranted.

**Ops:** No live grant; keep services, deployed code, backups and drives unchanged.

## 6. What Remains Before "Live" (sequential)

1. Complete the authorized branch integration, then obtain fresh GitHub CI and a focused integration delta review at its final tip. The two-test delta already passed at `2977c45` (85%); historical green CI does not transfer. T1 is not independently deployable: old writers can still overwrite the marker or clear incidents. T2–T5 stay ungranted.
2. Resolve the separate BugBot outage gate through matching evidence or Ryan's written exact-tip acceptance, then Ryan accepts or returns T1. Acceptance is not deployment.
3. Before live rollout, resolve the loss window and exact recovery-artifact qualification, old-process/guard-state adoption and rollback compatibility in execution section 6. The additional drive is a candidate resource, not completed protection.
4. Any deployment or corpus-affecting operation requires its own exact scope, recovery evidence and Ryan grant. The standalone detector remains a separate decision.

## 7. Hard Stops (models cannot cross)

- T1 permits only scoped implementation source and isolated fixtures/evidence in its worktree. No installed runtime, production data, service, backup-repository, key, retention or installed-permission changes.
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
- [Execution plan](EXECUTION-safe-harbor.md): five bounded tasks, interface proposal, proof requirements and new-drive operational limits.
- [VERIFY companion](VERIFY-safe-harbor.md): historical V1 results, open correction evidence and pending V2–V6.
- [Reboot checkpoint](https://github.com/alanmz-crypto/convmem/blob/bc3a6fd34bc594024d53fb86c9ca6b312cb64bd1/docs/inter-model/CODEX-2026-10-11-durability-reboot-checkpoint.md): review provenance and saved pre-reboot state.
- [Recovery Authority STATUS](STATUS-recovery-authority.md): ownership and hard stops.
- [Complete-data Backup v2 STATUS](STATUS-complete-data-backup-correction-v2.md): existing profile/restore contract and open consistency audit.
- [Team charter](../inter-model/TEAM-CHARTER-2026-07-06.md) and [decision/review guardrails](../inter-model/DECISION-REVIEW-GUARDRAILS.md): authority and review discipline.
- [Execution Planning guide](../planning/EXECUTION-PLANNING.md): active phase and stop condition.

## 10. How to Update This Brief (departure protocol)

Overwrite sections 3–6 when the actual state changes. Keep runtime observations dated and scoped; do not turn them into permanent green guarantees. Other orientation surfaces should point here instead of duplicating mutable milestones. Add one milestone-level update line; keep detailed review discussion in the architecture or review artifact. If Ryan renames the arc, rename the matching files and their pointers together.

## Update Log

- 2026-10-11 — Codex: recorded Copilot delta PASS at `2977c45` and Ryan's bounded main-integration/inventory-refresh grant; fresh CI and final-tip review follow, with no PR merge or live grant.

- 2026-10-11 — Codex: resumed from the GitHub checkpoint and authored the provisional Safe Harbor direction/brief; independent review and Ryan approval remain pending.
- 2026-10-11 — Codex: corrected Opus's two first-review blockers and recorded E1–E7; exact-revision delta review is next, with Kiro sign-off and Ryan approval still pending.
- 2026-10-11 — Codex: recorded Opus delta PASS at `505a422` and added its exact E7 disposition clause; Kiro governing review is next, with Ryan approval pending.
- 2026-10-11 — Codex: recorded Kiro governing PASS at `5ea16a6` (88%); Ryan's direction decision and E4 remain open, with no execution-planning or live-action grant.
- 2026-10-11 — Codex: recorded Ryan's approval at `5ea16a6` and confirmed Safe Harbor; targeted Kiro E4 prompt prepared, with execution planning explicitly pending.
- 2026-10-11 — Codex: recorded Kiro E4 PASS at `20283bd` (85%) and carried its obligations; truncated-prompt coverage clarification requested, execution planning still pending.
- 2026-10-11 — Codex: recorded Kiro's full-scope E4 PASS addendum at `1268a50` (85%), O-E4.d/e and two source/contract qualifications; Ryan's execution-planning decision is next.
- 2026-10-11 — Codex: recorded Ryan's drafting grant, authored five-task EXECUTION and unrun VERIFY stub, and inspected the added ext4 destination; plan/v2 review and acceptance are next, implementation/live operations pending.
- 2026-10-11 — Codex: at Ryan's request, clarified uncertain approval-event completion and its unrun evidence cases; saved Kiro's focused execution-review prompt. Review/acceptance and all execution remain pending.
- 2026-10-11 — Codex: recorded Kiro's execution PASS at `00c69d2` (85%) and O-E4.e satisfaction; incorporated A1/A2, qualified the audit source claim, and retained the v2-owner/acceptance gates with no execution grant.
- 2026-10-11 — Codex: recorded Kiro delta PASS at `dca13a5` (88%), closed the review cadence without contract changes, and routed B-E4.1 to owner disposition before Ryan's plan acceptance; execution remains pending.
- 2026-10-11 — Codex: recorded Ryan's explicit B-E4.1 owner approval and acceptance of the plan at `dca13a5`, including all five consumer outcomes; ownership unchanged, implementation/live operations pending.
- 2026-10-11 — Codex: recorded Ryan's T1-only grant and prepared the bounded Cursor Execute handoff/isolated branch; implementation not started, evidence unrun, later tasks/live operations pending.
- 2026-10-11 — Cursor: implemented T1 on `fix/2026-10-11-safe-harbor-t1` at runtime `fa82028` and recorded isolated V1; exact-tip review, T2–T5, and live operations remain pending.

- 2026-10-11 — Codex: recorded Ryan's bounded T1 correction grant; store-file scope addition, persisted-empty refusal and actual overwrite control are authorized, with correction evidence/review pending.
- 2026-10-11 — Cursor: corrected T1 on `fix/2026-10-11-safe-harbor-t1` at runtime `496792f` and recorded isolated V1 (43 passed); exact-tip review, T2–T5, and live operations remain pending.
- 2026-10-11 — Cursor: merged main `db8aebb`, made T1 tests self-isolating under standard pytest, and regenerated the writer-coverage inventory to `43a3944d`; BugBot was not re-triggered.
- 2026-10-11 — Codex: recorded green CI and Copilot static PASS at `677c8a0`, both quota-blocked BugBot attempts, and Ryan's two-test correction grant; Cursor correction and successor evidence/review are next.
- 2026-10-11 — Cursor: implemented the isolation-cleanup and audit/writer-contention test corrections at `8b41044` (runtime unchanged) and recorded isolated evidence with failing controls; successor CI/delta review, BugBot gate and T1 acceptance remain pending.

## TL;DR

[Arc Safe Harbor] Cursor implemented Ryan's two authorized test corrections at `8b41044`: fixture isolation now holds through fault cleanup, and audit/writer lock contention is proven with a failing pre-lock control. Runtime is unchanged. Successor CI, the focused delta review, the BugBot outage gate and T1 acceptance remain open. No merge, deployment or T2–T5 grant.

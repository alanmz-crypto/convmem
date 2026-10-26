# Arc Brief — Safe Harbor

> **Arc: Safe Harbor — stopped and checkpointed, 2026-10-25.** T1–T5 / V1–V6 are accepted and merged; bounded operational observation is complete. Draft #418 preserves the four open static findings, delivery/CI state and session resume details. Its five missing classifications are corrected; shared CI fixes landed separately in #419 but are not yet integrated here. The legacy initializer stays parked. On Ryan's return, Codex checks the final PR state before Cursor's queued SH-001 isolated validation. Start with the [close receipt and resume prompt](../../Issues/Arc/Safe_Harbor/README.md). Branch: `docs/2026-10-25-safe-harbor-shutdown-checkpoint`.

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

- **T1–T5 on main:** incident retention/canonical identity (#387), target-bound preflight (#389), preservation and strict release (#391), serialized approval recovery (#392), integrated evidence/operator handoff (#394). Latest Safe Harbor squash is `c6f07241ccf1a71d9d874fee963a37b04091b3ce`, tree-equal to accepted #394 head `188184b28707eb87c042d579aa7bbcba043dd5d0`. [Saved VERIFY](https://github.com/alanmz-crypto/convmem/blob/2b95f58ef79802f80058b07e125bf73802db5f1e/docs/plans/VERIFY-safe-harbor.md#t5-hosted-ci-owner-exception-and-squash-mapping) retains exact acceptance and evidence; historical reviews apply only to their pinned subjects.
- **Observed deployed runtime, October 25:** `runtime-main` at `4b4796b6a667509f94475a5a14424204947fbb12`, following another lane's promotion. The cited Safe Harbor implementation files are unchanged from the audit baseline `1a686753d8fd1b710883050e8a4f9c45b7ae1e26`. This checkpoint performs no promotion and does not re-review other arcs' changes.
- **Saved operational/initializer continuation:** `feat/2026-10-22-safe-harbor-legacy-initializer` remains pushed at `2b95f58ef79802f80058b07e125bf73802db5f1e` (origin checked October 25). Its [ROLLOUT receipt](https://github.com/alanmz-crypto/convmem/blob/2b95f58ef79802f80058b07e125bf73802db5f1e/docs/plans/ROLLOUT-safe-harbor.md) preserves post-deployment observations, service-route results and recovery inputs. Cursor's initializer runtime `204f1c6`, delivery `dd0c467`, is parked unreviewed/unaccepted. Do not merge that branch just to recover its documents.
- **New assessment:** [SH-001–SH-004](../../Issues/Arc/Safe_Harbor/README.md) are four separate proposed P2 findings covering JSONL framing, partial export retry, retained finding details and first-directory durability. No reproductions, fixes or corrective delivery exist in this assessment. The initializer's four missing tests are a different set of obligations.
- **Checkpoint delivery:** draft #418 contains the saved assessment/routing and five required manifest classifications. Correction `b2e6ffe` has an isolated clean-tree manifest PASS (one test, no skips), not a full-suite PASS. The [close receipt](../../Issues/Arc/Safe_Harbor/README.md#close-receipt--2026-10-25-2313-cdt) preserves original failures, exact CI runs, the local transcript/session ID and dependency state. PR #419 is merged as `d54f92b`; its shared test fixes are not yet in this branch. Final-tip CI/merge remain unresolved.

## 4. Completion State

- Direction/name, every-restore owner disposition, execution plan, B-E4.1 and T1–T5 / V1–V6 acceptance remain settled. Existing ownership and index/plain-add exemptions are unchanged. BugBot exceptions remain candidate-specific.
- **Bounded software observation complete:** saved receipts show successful local-backup, external-copy and October 24 one-time digest execution through the corrected production Python/runtime-main routes. The digest finished at 18:02:04 CDT, disclosed insufficient retrieved recent material and a 16.4 GiB memory peak; these are limits, not permission to rerun or repair it.
- **Recovery qualification remains limited:** both boot/root partition images in `2026-10-23-13-img` passed recorded integrity checks October 24. Restore/boot/application usability of that exact image is untested. The recorded owner loss policy is one day of ConvMem data and work since the latest disk image for the rest of the system. Physical image/key separation remains unverified and owner-managed; do not convert the owner's hypothetical storage statement into completed evidence.
- **October 25 checkpoint health:** doctor exited 0 with five nonfatal warnings; local/external backup checks passed, no guard quarantine was reported, and the tripwire reported zero native faults this boot. This is a dated observation, not restore qualification, a fix for SH-001–SH-004 or a guarantee after the shutdown.
- **Assessment complete; validation not started:** Codex found no corrective handoff for SH-001–SH-004. The contacted doctor-acknowledgment lane owns none of them. Cursor is now designated for the queued SH-001 validation only; no active session has acknowledged it. SH-002–SH-004 remain unassigned.
- **Immediate close requested:** Ryan requested every agent preserve its work and stop within five interactions. This lane stops after pushing the updated checkpoint; no local test/implementation job remains. Hosted checks can complete independently. Other active Codex tasks were notified; the #417 owner acknowledged its separate clean pushed checkpoint. No claim of universal external-agent shutdown is made.

## 5. Your Role (read this to know what you're here to do)

**Current phase: stopped checkpoint.** Ryan plans to turn the workstation off October 26 for about two weeks and requested immediate closure. Preserve the pushed findings, final PR/CI receipt and session resume details; leave no local test or implementation process running across shutdown. Draft PR #418 need not merge to preserve this work.

**On Ryan's return:** Codex reads the [issue index](../../Issues/Arc/Safe_Harbor/README.md), checks #418's final-tip CI and current main including #419, and preserves #417's independent routing when considering bounded integration. Then check source drift and any intervening corrective delivery before supervising Cursor's isolated SH-001 validation. Cursor may add test/harness cases and collect evidence using the existing pre-import bootstrap, synthetic stores and network/production-path refusal. Return separate event-tail, export-tail and valid-control results before any runtime correction. No proof is presumed from this static assessment.

**Ryan:** receives the validation result before deciding on correction. Recovery qualification and physical custody remain separate owner decisions. Keep the initializer parked; no initializer review or execution is part of SH-001.

## 6. What Remains (sequential)

1. Resume from the pushed checkpoint after Ryan returns. Inspect #418's exact final candidate/checks and whether accepted #419 fixes have been integrated; preserve the separate #417 delivery. Re-establish current source and health before live work; stale pre-shutdown PASS results cannot authorize it. A paused draft is a saved checkpoint, not a merge-ready claim.
2. Perform only the [bounded SH-001 validation](../../Issues/Arc/Safe_Harbor/SH-001-jsonl-append-boundaries.md#validation-before-correction) in an isolated worktree. Return reproduction or refutation with independently inspected durable effects and positive controls. Stop if isolation or the supposed source behavior cannot be established.
3. Codex assesses the returned evidence; Ryan then decides any runtime correction and its review/delivery scope. Do not bundle SH-002–SH-004 into it or infer an existing corrective candidate.
4. Leave the other findings and exact-image recovery qualification open until separately scoped. Completed operational observation needs no automatic rerun.

## 7. Hard Stops (models cannot cross)

- Ryan's later PR Steward grant authorized draft #418, task-branch pushes, checkpoint/CI status updates and normal hosted CI for this delivery; the shutdown request authorizes recording this close. It does not authorize runtime correction, initializer execution, production corpus mutation, service change, backup/restore, drive/key action, merge or deployment. Queued SH-001 validation remains separate from PR delivery. No manual session indexing while the watcher captures this Codex session.
- The initializer grant is consumed and its result parked. Its four missing tests and isolation lapses remain in [the saved Claude review](https://github.com/alanmz-crypto/convmem/blob/2b95f58ef79802f80058b07e125bf73802db5f1e/docs/plans/VERIFY-safe-harbor.md#claude-verification-and-owner-parking-2026-10-22); they are not SH-001–SH-004.
- No Recovery Authority T4/V4k, v3 authority/serving activation, migration, general HOLD, identity registry, backup freeze, permission deployment or cleanup/retention subsystem.
- Guard containment is cooperative. File visibility is not durable publication; fixture restart is not power-loss proof. Gate PASS is availability/freshness/path evidence; ID coverage is not semantic integrity or demonstrated recovery.
- Preserve pinned reviews and excluded attempts. Any later runtime correction requires its own evidence and review; author evidence is not independent acceptance.

## 8. Relationship to ConvMem (the bigger picture)

Safe Harbor implements stricter contracts around existing local guard and approval-recovery paths. Complete-data Backup v2 still owns its resolver, eligibility/gate interfaces, snapshot/restore profile and open Hybrid consistency audit; Recovery Authority still owns provenance-aware recovery and its T4/V4k dependencies. Other run-ledger, generation and permission surfaces retain their own owners.

The architecture records these interfaces and refuses to claim a global freeze. It does not change those other arcs' statuses or silently finish their deferred work.

## 9. Key Design Files (for deep dives)

- [Safe Harbor architecture](ARCHITECTURE-safe-harbor.md): accepted direction, evidence, risks and reviewer assignment.
- [Execution plan](EXECUTION-safe-harbor.md): five bounded tasks, interface proposal, proof requirements and new-drive operational limits.
- [VERIFY companion](VERIFY-safe-harbor.md): merged implementation evidence. The newer operational/initializer receipts remain pinned on the saved continuation linked in section 3.
- [Issue index and queued validation handoff](../../Issues/Arc/Safe_Harbor/README.md): shutdown checkpoint, four unresolved findings and the next bounded task.
- [Reboot checkpoint](https://github.com/alanmz-crypto/convmem/blob/bc3a6fd34bc594024d53fb86c9ca6b312cb64bd1/docs/inter-model/CODEX-2026-10-11-durability-reboot-checkpoint.md): review provenance and saved pre-reboot state.
- [Recovery Authority STATUS](STATUS-recovery-authority.md): ownership and hard stops.
- [Complete-data Backup v2 STATUS](STATUS-complete-data-backup-correction-v2.md): existing profile/restore contract and open consistency audit.
- [Team charter](../inter-model/TEAM-CHARTER-2026-07-06.md) and [decision/review guardrails](../inter-model/DECISION-REVIEW-GUARDRAILS.md): authority and review discipline.
- [Execution Planning guide](../planning/EXECUTION-PLANNING.md): active phase and stop condition.

## 10. How to Update This Brief (departure protocol)

Overwrite sections 3–6 when the actual state changes. Keep runtime observations dated and scoped; do not turn them into permanent green guarantees. Other orientation surfaces should point here instead of duplicating mutable milestones. Add one milestone-level update line; keep detailed review discussion in the architecture or review artifact. If Ryan renames the arc, rename the matching files and their pointers together.

## Update Log

- 2026-10-25 — Codex: recorded immediate shutdown, draft #418's manifest correction and pending integration/CI, merged shared fixes #419, separate #417 ownership and exact session continuity; stopped local work.

- 2026-10-25 — Codex: saved the four unresolved static findings for the planned two-week shutdown; designated Cursor for queued SH-001 validation only, corrected current routing and kept the initializer parked.

- 2026-10-14 — Codex: recorded Kiro V6 PASS and Ryan acceptance at `1cb02fb`; delivery, outage disposition and live operations remain separately gated.

- 2026-10-14 — Cursor/Codex: delivered the bounded signalling/logging correction; 257 integrated passes, retained failure diagnostics and full isolated lint PASS; independent V6 review and Ryan acceptance next.

- 2026-10-14 — Codex: recorded Ryan’s bounded T5-F1 signalling/logging correction and fresh-evidence grant; Cursor/Codex work next, runtime and live boundaries unchanged.

- 2026-10-14 — Codex: recorded T4 acceptance/merge and T5 grant; returned 240 passes plus one concurrency failure, the static pipe-framing defect and prepared operator handoff; no correction/rerun/live action.

- 2026-10-14 — Cursor/Codex: delivered bounded T4 fixture/tool correction, full isolated T4/T2 evidence, native proof and lint/collection gates; runtime/baseline fixed, hosted CI and correction review remain distinct.

- 2026-10-14 — Codex: recorded draft #392’s seven-test CI failure and extra skips; Ryan authorized bounded fixture/tool corrections, isolated evidence and fresh CI with runtime/baseline fixed.

- 2026-10-13 — Codex: recorded Kiro T4 PASS (90%) at `d27d3c0`, completed missing test-source coverage and retained sampled-log/sink-trace limits; owner PR/CI decision next, no fixes or live action.

- 2026-10-13 — Cursor/Codex: returned T4 at `a3207fe`, 70 isolated V5 passes, affected regression and full lint PASS; retained excluded model-download lapse; independent review/owner acceptance next, no PR/live/T5 authority.

- 2026-10-13 — Codex: recorded Ryan’s isolated T4/Cursor grant and pinned handoff; Codex supervises V5 evidence, results return for independent review, no PR/live/T5 authority.

- 2026-10-13 — Codex: verified #391 squash `a7f7200` equals accepted `3c490e2`; recorded green hosted CI, Kiro final PASS and Ryan T3/V3/V4/outage acceptance; T4/T5/live work remain ungranted.

- 2026-10-13 — Codex: returned section 14 pytest correction: 296 affected passes/1 existing skip, 159 integration passes, full lint PASS; runtime/baseline fixed, fresh hosted CI pending.

- 2026-10-13 — Cursor/Codex: returned bounded lint correction after draft #391 failed hosted CI; 149 isolated passes and full lint gate PASS (71 duplicates), runtime/baseline fixed, separate pytest failures and authoring breach disclosed.

- 2026-10-13 — Cursor/Codex: returned bounded CI integration at `34ff309`, 149 isolated passes and lint regression gate PASS; runtime/routes unchanged, independent delta and hosted CI pending.

- 2026-10-13 — Codex: recorded Ryan's bounded CI integration/evidence grant at `23041bd`; Cursor authors and Codex supervises isolated execution, PR/later work remains ungranted.

- 2026-10-13 — Codex: recorded Kiro implementation PASS (85%, `a54357c`/`802d74d`) with source qualification; scoped CI integration for approval, no implementation/tests/PR or live action.

- 2026-10-13 — Cursor/Codex: returned isolated T3 preservation/release implementation and fault-matrix evidence; exact source/results in VERIFY, independent implementation review and acceptance pending, no live authority.

- 2026-10-13 — Codex: recorded bounded lapse investigation, independent Kiro proof PASS (82%, `e08100ff`) and satisfied conditional T3 implementation grant; separate worktree, supervised isolated execution, no live authority.

- 2026-10-13 — Cursor/Codex: corrected R1–R3 at `93d4e34`; qualified nine-case proof and focused lint pass, excluded early probes and validator/CI limitations recorded; returned results, no remaining T3 grant.

- 2026-10-12 — Codex: reviewed proof `8c4ad91` statically and retained its captured examples; full backend gate NOT DEMONSTRATED (95%) pending R1–R3 proof-only corrections, no runtime grant.

- 2026-10-12 — Codex: recorded Ryan's T3 isolated pinned-backend proof-only grant and prepared the separate pinned worktree/handoff; results must return before preservation/repair/release implementation.

- 2026-10-12 — Codex: confirmed Ryan's final-tip T2/V2 acceptance and BugBot outage exception, six green final-head checks and #389 squash mapping; T1/T2 merged, T3 proof grant next, no live authority.

- 2026-10-12 — Codex: recorded Cursor governed-path correction with original-runtime failures, 98-case final isolated PASS and lint-gate PASS; excluded initial ambient attempts; bounded delta PASS is pinned to `dac925f`; fresh CI and acceptance remain pending.

- 2026-10-12 — Codex: recorded green CI and fresh final-review FAIL at `45a1f00`; Ryan granted the bounded cross-parent alias/governed-file identity correction and isolated evidence; Cursor implementation next.

- 2026-10-13 — Cursor: shadow call-site coordinate correction after CI `38325044536`; R2b regen and 17-case isolated proof; fresh CI next, PR stays draft.

- 2026-10-12 — Codex: integration delta PASS (90%) at `0c3e6c7`, source `551b16c`; GitHub conflict cleared and fresh CI running. Current-head checks remain the CI authority; final external-review/owner acceptance stays pending.

- 2026-10-13 — Cursor: delivered isolated T3 pinned-backend proof (**DEMONSTRATED**); VERIFY V4 ordering-gate evidence recorded; remaining T3 implementation ungranted.

- 2026-10-12 — Cursor: merged pinned main into T2 at `551b16c`, recorded qualified isolated evidence and docs routing; Codex integration delta and CI next, PR stays draft.

- 2026-10-12 — Codex: recorded Ryan's bounded T2 integration grant from `c6e881b` with pinned main `8a7cdab`; Cursor integration/evidence and fresh CI next, PR stays draft.

- 2026-10-12 — Codex: F1/F2 delta PASS at `721fd17` / runtime `cdebf64`, 85 distinct isolated cases and lint gate PASS; main conflict identified, bounded integration and final-tip acceptance remain pending.

- 2026-10-12 — Cursor: delivered F1/F2 target-binding correction and outer-isolated evidence on `fix/2026-10-12-safe-harbor-t2`; Codex bounded delta next.
- 2026-10-12 — Codex: recovered and pushed Cursor's bundle at `255c040`; static delta requires the T1 competing-location correction and completion of export/regression evidence. Cursor continues within the existing grant; runtime unchanged by review.

- 2026-10-12 — Codex: recorded the owner-granted alias target-binding correction and Cursor handoff; reconciled draft #389/BugBot quota status and dismissed CodeQL #6 as an authorized false positive. Correction evidence and T2 acceptance remain pending.

- 2026-10-12 — Codex: recorded Copilot B1 delta PASS at exact candidate `82f25ef` (88%), corrected runtime/review SHA shorthand and retained the accepted event-only exclusion; V2 acceptance and the separate PR-native gate remain pending.

- 2026-10-12 — Cursor: implemented B1 at `964c1de` (recovery reuses the allowlisted writer label; R2b identity derived-only) and recorded armed-census uid-1000 evidence (3 new and 153 affected passed, lint gate PASS). Narrow Copilot delta is next; V2 not accepted.
- 2026-10-12 — Codex: recorded Ryan's bounded B1 correction grant and event-only evidence exclusion; prepared Cursor's scoped continuation with isolated census-present positive/refusal/control evidence.

- 2026-10-12 — Cursor: implemented alias target-binding correction at `a18df480` with isolated effect/negative-control evidence; Codex delta and fresh CI follow; V2 acceptance and merge remain pending.
- 2026-10-12 — Codex: recorded Copilot's exact-tip T2 narrow FAIL at `05c7706`, confirmed B1 and routed the bounded correction plus explicit event-only evidence-limit decision; runtime unchanged.

- 2026-10-12 — Codex: reconciled execution-plan current-state pointers with the delivered T2 candidate; isolated evidence is recorded, with the event-only completion limitation and review/acceptance still open.
- 2026-10-12 — Cursor: recorded Codex's refresh at tests `2459acd` (64 affected cases re-passed, exit 0; lint gate PASS). T2 implementation and evidence are delivered; event-only completion stays an open T4 limitation. Review and acceptance are next.
- 2026-10-12 — Cursor: recorded Codex's captured final runs at `44e29f6` (133/103 passed, exit 0; lint gate PASS). The event-only fixture now uses a real interrupted approval (`2459acd`), exposing the hash-view mismatch as a T4 prerequisite. Fixture refresh, V2 acceptance and review are pending.
- 2026-10-12 — Cursor: implemented T2 (final source `44e29f6`), updated policy docs and recorded isolated V2 evidence; final uid-1000 pytest/pylint status pending Codex, then external review/Ryan acceptance. T4 direct-caller proof outstanding.
- 2026-10-12 — Codex: recorded Ryan's separate T2 grant and prepared the pinned Cursor handoff/worktree; implementation and V2 not started, T3–T5/live work ungranted.

- 2026-10-12 — Codex: recorded final-tip CI/Copilot evidence, Ryan's exact-tip BugBot outage acceptance and T1 squash merge #387 at `05aa2c8`; T2 grant and all live work remain pending.

- 2026-10-11 — Codex: recorded Copilot delta PASS at `2977c45` and Ryan's bounded main-integration/inventory-refresh grant; fresh CI and final-tip review follow, with no PR merge or live grant.
- 2026-10-11 — Cursor: merged main `5550def` into the T1 branch at `c624e2f`, regenerated the inventory (`87b8144d…`) and recorded isolated integration evidence (63/45 passed); fresh CI, final-tip review, BugBot gate and T1 acceptance remain pending.

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

[Arc Safe Harbor] T1–T5 are accepted/merged and bounded operational observation is complete. The shutdown checkpoint preserves four open static findings; SH-001 isolated validation is queued for Cursor after Ryan resumes, with Codex supervision. No validation has run. The initializer stays parked; runtime correction and live operations remain ungranted.

<!-- ref: ../../Issues/Arc/Safe_Harbor/README.md — current assessment and queued validation handoff -->
<!-- src: /home/lauer/Projects/convmem/.worktrees/feat-2026-10-22-safe-harbor-legacy-initializer/docs/plans/STATUS-safe-harbor.md — saved operational evidence and initializer disposition at 2b95f58 -->

# Arc Brief — Safe Harbor

> **Arc: Safe Harbor — operational follow-up, 2026-10-24.** T1–T5 / V1–V6 are accepted and merged through `c6f0724`; deployed runtime remains `1a68675`. Codex completed Ryan's read-only post-deployment check and separately authorized routing correction for local backup, external copy and cross-project digest. Both corrected backup jobs passed on October 24 (local 00:19:52 CDT, external 01:01:15); actual runtime identity and copy lineage were confirmed. Doctor refreshed after 01:05 exited 0 with both backup checks PASS. The corrected digest is pending Monday. Read-only inspection now identifies `2026-10-23-13-img`: its log records successful boot/root imaging, but no image-check or restore-test result was found. Ryan reports all drives plugged in and no separate offline password copy known. Recovery qualification and independent custody remain open. The legacy initializer stays parked, unreviewed and unaccepted. No further live operation is granted.

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

- **Saved continuation:** `feat/2026-10-22-safe-harbor-legacy-initializer` in `.worktrees/feat-2026-10-22-safe-harbor-legacy-initializer` holds the current arc documents and the parked initializer. No PR exists. The earlier rollout-evidence branch's routing is stale. Saving this checkpoint does not accept or promote the parked code.
- **T1–T5 on main:** incident retention/canonical identity (#387), target-bound preflight (#389), preservation and strict release (#391), serialized approval recovery (#392), integrated evidence/operator handoff (#394). Latest Safe Harbor squash is `c6f07241ccf1a71d9d874fee963a37b04091b3ce`, tree-equal to accepted #394 head `188184b28707eb87c042d579aa7bbcba043dd5d0`; [VERIFY](VERIFY-safe-harbor.md#t5-hosted-ci-owner-exception-and-squash-mapping) holds exact acceptance and evidence.
- **Actual deployed runtime, October 23:** clean `runtime-main` at `1a686753d8fd1b710883050e8a4f9c45b7ae1e26`. It already contains Safe Harbor through other arcs' promotions; the original ROLLOUT transition was not executed. Watcher and ten observed MCP servers used production Python/runtime-main, all started after the last code update. The bounded scan is not proof of every loaded module or a writer freeze.
- **Operational receipt:** [ROLLOUT §7](ROLLOUT-safe-harbor.md#7-post-deployment-check-and-service-routing--2026-10-23) records the read-only check, exact installed drop-ins, checks, limits and unexecuted rollback. Three services now use runtime-main and production Python; base units and timer definitions are unchanged. No job was manually started.
- **Guard state, October 23:** no quarantine marker; both CURRENT generations have release evidence. All ten saved segment-file hashes matched their manifests. Latest existing daily audit passed with zero lost/extra IDs; no recorded restore/quarantine/release was found. No live SQLite eligibility check or recovery qualification was performed.
- **Readiness and parked initializer:** focused installed-Python/legacy evidence remains reviewed at `f45b051`; initializer scope remains reviewed at `c46fbc6`. Cursor's implementation (`204f1c6`, delivery `dd0c467`) is parked unreviewed/unaccepted. [VERIFY](VERIFY-safe-harbor.md#claude-verification-and-owner-parking-2026-10-22) preserves the isolation lapses, four missing cases and open refusal-versus-partial status question.

## 4. Completion State

- Approved direction/name, every-restore disposition, execution plan, B-E4.1 and T1–T5 / V1–V6 acceptance remain settled. Ownership and index/plain-add exemptions are unchanged. Owner BugBot exceptions stay pinned to their individual candidates.
- **Post-deployment inspection complete:** the observed processes used the deployed route; stored guard evidence and existing audits were inspected. This does not re-review later runtime changes from other arcs or establish semantic integrity/recoverability.
- **Routing correction complete:** at October 23 23:26:43 CDT, Codex installed three user-unit drop-ins and reloaded the manager. Effective commands/environment and unit validation passed. Services remained inactive and timers active/enabled. **Local and external scheduled execution passed October 24; digest remains pending Monday.** No corpus write, backup/restore, initializer, audit invocation or restart was initiated by this lane.
- **Recovery policy recorded October 22:** Ryan delegated items 1–3 to Claude. Accepted loss interval is one day of ConvMem data and work since the latest disk image for the rest of the system. Whole-disk image `2026-10-20-05-img` completed without logged errors; `2026-10-11-06-img` is the older fallback. Policy is to keep at least one image drive and a Restic password copy unplugged and away from the workstation. [ROLLOUT recovery inputs](ROLLOUT-safe-harbor.md#recovery-inputs--decided-2026-10-22) retains provenance and locations.
- **Recovery preparation, October 24:** after Ryan reported image/test details unknown, read-only inspection at 01:50 CDT found the image drive mounted and `2026-10-23-13-img` present. Its log records completion October 23 09:08:36 CDT for the workstation's boot/root partitions, matching current UUIDs; reported image size is `304G`. No image-check or restore-test result was found in the available saving log. The October 11 fallback remains visible; the previously observed October 20 directory was absent from the inspected top level, with no inference about deletion or copies elsewhere. Ryan reports all drives plugged in and no separate offline password copy known. Qualification and independent custody remain open. See the [image receipt](ROLLOUT-safe-harbor.md#recovery-preparation-inspection--october-24-0150-cdt) and [owner answers](ROLLOUT-safe-harbor.md#owner-recovery-answers--october-24).
- **Scheduled backup results, October 24:** local invocation 00:17:51–00:19:52 CDT created source `0295cf8e4922568d4b9633ee9fc8f2246939f3c116ff75f69919f38428cda26d`; external invocation 01:01:01–01:01:15 copied it to `ba581a75bb7bc07b0fc83b04fea200643ca597b54046fb230d56bab8acc6ec7b`, with `original==source`. Both completed successfully using production Python 3.11/runtime-main, observed through local process metadata and external structured journal fields. After 01:05, doctor exited 0 with local and external PASS. Daily audit passed (two segments, 118,977 vectors, zero lost); existing nonfatal warnings remain. ROLLOUT §7 records exact evidence and limits; no restore qualification was performed.
- **Initializer remains parked:** both observed live generations already carry release evidence. No new initializer review, implementation or execution is justified by this checkpoint. Older-image restore requirements may merit a separately scoped decision later.
- Limits remain: existing audit ID coverage is not semantic integrity; gate PASS is not demonstrated recovery; current strict release eligibility was not tested. Fixture restart/fsync injection is not hardware power-loss proof. The retained tripwire warning was not cleared or reclassified by this work.

## 5. Your Role (read this to know what you're here to do)

**Ryan:** the next recovery step is to check the identified `2026-10-23-13-img` and retain its exact result, then establish independent image/key custody. An image integrity check is narrower than a demonstrated restore. Existing policy need not be decided again; the factual questions are answered as far as currently known. Agent-run image checks or drive/key actions remain separately scoped.

**Next operational follow-up:** Ryan authorized the bounded read-only recovery/scheduled-results check. Both backup routes are now confirmed through scheduled runs. The remaining scheduled observation is digest after Monday October 26 09:08:21 CDT, allowing for completion. Do not start jobs to manufacture evidence. Any failure returns for a scoped correction decision; do not infer repair, restore or service-change authority from this receipt.

**All lanes:** keep the initializer parked. Preserve pinned reviews and review only material deltas. No PR, merge or additional live work is granted. Any lane prompt starts with a lane check; do not repeat the earlier supervisor-routing mistake.

## 6. What Remains Before Operational Closeout (sequential)

1. Address the recorded recovery gaps in §4 using the identified October 23 image: exact-image qualification and independent image/key custody, retaining the one-day loss policy. Ryan's answers and the metadata inspection are recorded; agent-run image checks, backups, restores and drive/key actions require their own grant.
2. Observe the corrected digest after its Monday scheduled run. Configuration validation and both corrected backup runs are complete. Keep repository availability failures distinct from routing failures.
3. Reconcile any concrete residual deployment-readiness gap from those facts. Do not repeat the historical rollout against an already-live runtime or promote the parked initializer automatically.
4. Record the closeout decision with its actual scope. No implementation PASS, merge, audit PASS or incidental runtime promotion implies demonstrated recovery.

## 7. Hard Stops (models cannot cross)

- The §23 initializer grant is consumed and its result parked. Section 24's inspection and three-service routing correction are complete. No initializer review/rerun, PR, hosted CI, merge, further deployment/service change, corpus write, backup/restore or drive/key action is granted; retain the warning.
- EXECUTION §§20–21's evidence work and §22's static review are complete; no Execute grant is open. No ledger write or session indexing during any future execution, and no new tests are authorized.
- Guard containment is cooperative. A publication/removal durability failure may require separately authorized process-level containment; do not claim a marker is a durable stop merely because bytes are visible.
- No Recovery Authority T4/V4k, v3 authority/serving activation, migration, general HOLD, identity registry, backup freeze, permission deployment or cleanup/retention subsystem.
- Gate PASS is availability/freshness/path evidence; zero missing vector IDs is not semantic integrity. Neither substitutes for exact-artifact recovery qualification.
- Kiro sign-off and Ryan V6 acceptance are pinned to `1cb02fb`; later code/test changes require their own scoped evidence and review. Author evidence does not supply independent acceptance.

## 8. Relationship to ConvMem (the bigger picture)

Safe Harbor proposes stricter contracts around existing local guard and approval-recovery paths. Complete-data Backup v2 still owns its resolver, eligibility/gate interfaces, snapshot/restore profile and open Hybrid consistency audit; Recovery Authority still owns provenance-aware recovery and its T4/V4k dependencies. Other run-ledger, generation and permission surfaces retain their own owners.

The architecture records these interfaces and refuses to claim a global freeze. It does not change those other arcs' statuses or silently finish their deferred work.

## 9. Key Design Files (for deep dives)

- [Safe Harbor architecture](ARCHITECTURE-safe-harbor.md): proposed direction, evidence, risks and reviewer assignment.
- [Execution plan](EXECUTION-safe-harbor.md): five bounded tasks, interface proposal, proof requirements and new-drive operational limits.
- [VERIFY companion](VERIFY-safe-harbor.md): T1–T4 acceptance and exact merge mappings, integrated V6 evidence, pinned Kiro PASS, Ryan V6 acceptance and retained delivery/live gates.
- [Reboot checkpoint](https://github.com/alanmz-crypto/convmem/blob/bc3a6fd34bc594024d53fb86c9ca6b312cb64bd1/docs/inter-model/CODEX-2026-10-11-durability-reboot-checkpoint.md): review provenance and saved pre-reboot state.
- [Recovery Authority STATUS](STATUS-recovery-authority.md): ownership and hard stops.
- [Complete-data Backup v2 STATUS](STATUS-complete-data-backup-correction-v2.md): existing profile/restore contract and open consistency audit.
- [Team charter](../inter-model/TEAM-CHARTER-2026-07-06.md) and [decision/review guardrails](../inter-model/DECISION-REVIEW-GUARDRAILS.md): authority and review discipline.
- [Execution Planning guide](../planning/EXECUTION-PLANNING.md): active phase and stop condition.

## 10. How to Update This Brief (departure protocol)

Overwrite sections 3–6 when the actual state changes. Keep runtime observations dated and scoped; do not turn them into permanent green guarantees. Other orientation surfaces should point here instead of duplicating mutable milestones. Add one milestone-level update line; keep detailed review discussion in the architecture or review artifact. If Ryan renames the arc, rename the matching files and their pointers together.

## Update Log

- 2026-10-24 — Codex: both corrected backup routes passed; recorded Ryan's custody answers and subsequently identified the completed October 23 image from existing metadata. Image testing, independent custody and Monday digest observation remain open.

- 2026-10-23 — Codex: read-only follow-up found corrected jobs not yet due, October 20 image drive unmounted and configured password copy still mounted; recorded exact next checks and kept image-test/custody answers pending.

- 2026-10-23 — Codex: completed the authorized read-only post-deployment check and three-service routing correction; saved exact configuration and rollback; scheduled-run outcomes and newest tested-image/custody confirmation remain open.

- 2026-10-22 — Claude: recorded the recovery inputs (items 1–3 under Ryan's delegated authority, item 4 from Ryan) and found the Safe Harbor runtime already live at runtime-main `1a68675`; read-only post-deployment check proposed next.

- 2026-10-22 — Claude: verified the returned initializer (isolation lapses, four missing §22 cases, no production effect), corrected its provenance, and recorded Ryan's decision to park `dd0c467` unreviewed; live segments already carry release evidence; recovery inputs next.

- 2026-10-22 — Cursor (first recorded as Codex in error): implemented `initialize-legacy` at `204f1c6` with evidence at `dd0c467`; index-write-lock drift refuted.

- 2026-10-22 — Claude: recorded Ryan's resume and §23 initializer grant, merged main `5c0a01b` (initializer surface unchanged; one new lock for supervisor confirmation), fixed the manifest guard and wrote the Cursor handoff; Codex-supervised implementation next.

- 2026-10-19 — Codex: parked Safe Harbor on its existing pushed branch and synchronized the saved handoff, including VERIFY's hold state and dated storage observations; scope review complete, initializer unimplemented, explicit owner resume required.

- 2026-10-17 — Codex: retained the warning under Ryan's static-only exception; Kiro PASSed the initializer scope and B1–B3 delta at `c46fbc6`; isolated implementation grant and live recovery facts remain pending.

- 2026-10-15 — Codex: recorded Kiro readiness PASS at `f45b051` with corrected coverage and drafted the bounded initializer scope; recovery facts, scope review and implementation remain pending.

- 2026-10-15 — Codex: returned 83 installed-Python safety passes and five legacy-state passes; operational initializer, recovery inputs and independent review remain open, with runtime unchanged.

- 2026-10-15 — Codex: recorded bounded isolated interpreter/legacy-state evidence grant; live operations and runtime fixes remain excluded.

- 2026-10-14 — Codex: recorded #394 exact-tree squash and final acceptance; returned read-only deployment preflight and conditional rollout/rollback draft with recovery/interpreter/legacy-state readiness still open.

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

[Arc Safe Harbor] Post-deployment inspection and the three-service routing correction are complete. Runtime remains unchanged; no jobs were manually started. Both scheduled backup jobs and final doctor backup checks passed. Ryan's answers are recorded; exact-image qualification and independent image/key custody remain open, alongside Monday's digest observation. The initializer stays parked; no further live work is granted.

<!-- ref: ROLLOUT-safe-harbor.md — operational readiness and proposed sequence -->
<!-- ref: ../inter-model/CURSOR-2026-10-22-safe-harbor-legacy-initializer-handoff.md — parked implementation handoff -->
<!-- src: VERIFY-safe-harbor.md — accepted implementation, hosted evidence and merge mapping -->

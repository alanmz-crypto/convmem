# Arc Brief — Safe Harbor

> **Arc: Safe Harbor. T1–T4 ACCEPTED AND MERGED; T5 / V6 ACCEPTED AT `1cb02fb`.** [The pinned Kiro review and Ryan acceptance](VERIFY-safe-harbor.md#v6-independent-kiro-review-and-owner-acceptance) retain the original failure and evidence limits. T5 delivery remains on its branch; PR creation, hosted CI, merge and deployment are separately gated. Merged source is not deployed runtime or demonstrated disaster recovery.

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

- **T1 / V1 on main:** incident retention, canonical client/cache identity and persisted-empty authority refusal; [PR #387](https://github.com/alanmz-crypto/convmem/pull/387), squash `05aa2c86e2d01c9a9f5259b1f505833d7f28563d`.
- **T2 / V2 on main:** operation-bound preflight, production-skip refusal and future-time policy across five consumers; [PR #389](https://github.com/alanmz-crypto/convmem/pull/389), accepted `eb06c97df2cfe9de3627fd8672b9e3b7c277c963`, tree-identical squash `458b9f6bb0bf98048c11ac0baf46a2340dcdcbf3`.
- **T3 / V3 / V4 on main:** preserve before replacement, pin generations, contain every automatic segment restore and validate all incidents before release; [PR #391](https://github.com/alanmz-crypto/convmem/pull/391), accepted `3c490e2ce61d5c6531a044132c5a01faf144f1ac`, tree-identical squash `a7f72003aea516b4961a584fcfe54ad255d6a053`.
- **T4 / V5 on main:** fresh tombstone-aware approval recovery, direct/CLI target binding, native-lock serialization, export completion and truthful uncertain-outcome retry; [PR #392](https://github.com/alanmz-crypto/convmem/pull/392), accepted `ed6699bea949b95e0807f166c3297500736d4aa9`, tree-identical squash `fdc8da7fa67c1d7b31bc5cd44de466001df04260`. [Final closeout](VERIFY-safe-harbor.md#t4-final-ci-review-owner-acceptance-and-squash-mapping) records hosted CI, Kiro’s pinned reviews and Ryan’s acceptance/outage exception. Codex performed the squash on Ryan’s explicit “merge” instruction.
- **T5 accepted on an isolated verification branch:** `feat/2026-10-14-safe-harbor-t5`, based on that exact T4 squash. Kiro PASS and Ryan V6 acceptance are pinned to `1cb02fbd9cc15b36c7f3f094237da071ca2dcd18`; the documentation successor records those decisions only. [VERIFY V6](VERIFY-safe-harbor.md#v6-independent-kiro-review-and-owner-acceptance) separates new mechanical evidence, reused hosted evidence and independent sign-off. [RECOVER](../RECOVER.md#safe-harbor-incident-handling-and-rollout) is the operational handoff, prepared only. No T5 PR or fresh hosted run exists.
- **Runtime remains unqualified for rollout:** no T5 action changes runtime-main or services. No live process census, guard-state adoption, loss-window decision or exact backup qualification was performed. The extra ext4 drive is a reported resource, not proof of usable or offsite protection.

## 4. Completion State

- Direction/name, every-restore owner-disposition cost, execution plan and B-E4.1 (all five consumers) are owner-approved. Ownership stays with the existing arcs.
- **T1–T4 / V1–V5 ACCEPTED AND MERGED.** Each task’s review and BugBot outage exception stays bound to its accepted candidate. None is a BugBot PASS or a blanket future exemption.
- **Latest full hosted integration:** T4 candidate `ed6699b`, Python 3.12.15, run `38519477899`: 3,267 passed / 18 host-environment skips / 252 passing subtests; critical collection, unchanged-baseline lint and all security checks passed. Its tested merge and main squash have the same tree. V5 is completed evidence, not NOT RUN.
- **T5 / V6: Kiro PASS and Ryan ACCEPTED at `1cb02fbd9cc15b36c7f3f094237da071ca2dcd18`.** Kiro returned high confidence, no blockers, after static source/diff and recorded-evidence inspection. Test source `22fa1b9fc547092c7bf7e3b0156621e7db10b597` has 16 passing controls, 22 passing affected cases and 257 passing integrated cases; these selections overlap. Full isolated lint passes against the unchanged baseline. The original 240/1 failure's exact cause remains unproven. Acceptance does not grant a BugBot outage exception or transfer earlier exceptions to T5.
- Limits persist: process restart/IO injection is not hardware power-loss proof; strict release can refuse recoverable states; auxiliary sink non-interference remains at the accepted author-trace level; incidental/unguarded writers are outside a global stop guarantee. Historical failed and excluded runs remain visible.

## 5. Your Role (read this to know what you're here to do)

**Ryan next:** decide whether to authorize one draft PR and normal hosted CI for the T5 branch. Any final-tip external-review/outage disposition, merge and deployment remain separate decisions.

**Codex:** preserve the pinned V6 acceptance and prepare delivery within any subsequent grant. No new review or tests are needed merely to record acceptance. The existing Kiro handoff is completed/reference-only; do not restart it automatically.

## 6. What Remains Before "Live" (sequential)

1. Obtain a separate draft-PR/hosted-CI grant, report final-candidate results, and resolve the final-tip external-review gate and merge decision. V6 review/acceptance is complete at `1cb02fb`; the selected local run is not fresh hosted full-suite evidence, and no T5 outage exception is recorded.
2. Set the lost-work interval and qualify an exact usable recovery artifact and independently accessible key. Preserve the reported pre-incident image; extra drive capacity grants no backup/restore/retention operation.
3. Approve a deployment procedure naming candidate/interpreter, all old-process dispositions, canonical and lexical guard locations, existing incident/snapshot schema handling and rollback compatibility. Keep stopped services stopped unless separately granted.
4. Execute only a separately authorized rollout or corpus operation. No V6 PASS alone opens that lane.

## 7. Hard Stops (models cannot cross)

- T5 section 18 authorizes the bounded test-only signalling/logging correction, isolated evidence and existing-doc handoff. No runtime/test weakening, new dependency, baseline change, new PR/comment/review trigger, merge, deployment, production command, drive/key/repository/service action, ledger write or session indexing.
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

[Arc Safe Harbor] T1–T4 remain accepted and merged. The corrected T5 selection passes all 257 cases; Kiro V6 review and Ryan acceptance remain pending. Historical failure and evidence limits stay visible; no PR or live grant.

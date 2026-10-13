# Arc Brief — Safe Harbor

> **Arc: Safe Harbor. T1/T2 MERGED; T3 DRAFT PR #391, PYTEST CORRECTION RETURNED.** Section 14 has 296 affected passes/one existing live skip, 159 integration passes and full lint gate PASS. Runtime, lint baseline and safety assertions remain fixed. Fresh hosted CI on the pushed successor is pending. Historical Kiro verdicts stay pinned; T3 acceptance, merge, deployment and T4/T5 remain pending.

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

- **T1 on main:** incident retention, canonical client/cache identity and refusal of persisted-empty authority landed through [PR #387](https://github.com/alanmz-crypto/convmem/pull/387), squash `05aa2c86e2d01c9a9f5259b1f505833d7f28563d`. Ordinary clear still cannot provide validated release; that is T3.
- **T2 on main:** operation-bound backup preflight, production-skip refusal and future-time rejection across all five consumers landed through [PR #389](https://github.com/alanmz-crypto/convmem/pull/389), squash `458b9f6bb0bf98048c11ac0baf46a2340dcdcbf3` at 2026-10-13 03:43:09 UTC (2026-10-12 local). Its tree is identical to Ryan's accepted candidate `eb06c97df2cfe9de3627fd8672b9e3b7c277c963`. Canonical client/export binding preserves the configured governed-file identities. The completed task branch is historical, not an active grant.
- **Evidence and acceptance:** [VERIFY V2 acceptance record](VERIFY-safe-harbor.md#t2-final-tip-ci-owner-acceptance-and-squash-mapping) holds the six successful final-head GitHub checks, the pinned Codex review, Ryan's exact acceptance and the squash mapping. The final affected isolated suite passed 98 cases; this is not an additional full-suite claim. Earlier failed/unqualified attempts remain disclosed. BugBot reviewed no SHA; its gate was resolved by Ryan's written exception, not a BugBot PASS.
- **Open T4 limitation:** successful event-only approval completion is not proven. The ingestion/proposal hash views disagree; T4 must align them and demonstrate real completion. Direct-helper caller coverage and uncertain completion remain later T4 work. Ryan's V2 acceptance includes this documented evidence exclusion, not a claim that those paths work.
- `ARCHITECTURE-safe-harbor.md`: approved direction and E1–E7 obligations. `EXECUTION-safe-harbor.md`: accepted five-task contracts, section 11’s isolated T3 grant and [section 12's authorized CI scope](EXECUTION-safe-harbor.md#12-bounded-t3-ci-integration--owner-authorized). `VERIFY-safe-harbor.md`: T1/T2 acceptance, corrected proof, [current T3 evidence](VERIFY-safe-harbor.md#t3-implementation-checkpoint--isolated-v3v4-evidence) and [pinned Kiro implementation review](VERIFY-safe-harbor.md#t3-independent-kiro-implementation-review). V3/V4 acceptance is pending; V5/V6 remain NOT RUN.
- **T3 on its task branch, not main:** `chroma_write_guard.py` retains original-file facts in the incident authority, preserves originals before replacement, pins source generations, contains every automatic restore and validates the complete current incident set before durable disposition/release. Existing CLI/doctor/watch surfaces report that contract. Dedicated tests exercise interruption, IO/publication failure and faulty alternatives. Kiro's static PASS covers the exact prior artifact; unavailable release evidence can permit a contained restore but must refuse release. Full-suite/CI compatibility is still unproven.
- **T3 proof on its branch:** `tests/test_safe_harbor_t3_backend_proof.py` and `tests/_safe_harbor_t3_backend_worker.py` at `93d4e344c8959ed0176b3a9b39af7be3f638f148`. Client-free persisted-state predicate; independent stale-vector sensitivity; real mutation/purge/restart; collection-specific binding and pre-import isolation. Qualified run `/tmp/safe-harbor-t3-s9ejarj3`: nine passes, pytest/pylint exit 0, stable source hashes. Production runtime is unchanged. Earlier unqualified Cursor probes were stopped/excluded; full disclosure and qualified failed development runs remain in VERIFY.
- **Deployment is separate:** this closeout did not move runtime-main, restart processes or inspect production health. Git worktree metadata observed at closeout places runtime-main at `8a7cdab16420893fe26a2648d1d03f2b84d8589d`; it does not establish running-process identity. Drafting-time D/P/B source labels in the architecture/plan remain historical citations.
- **Recovery inputs remain open:** the loss window and exact usable recovery artifact require qualification before rollout. Preserve the reported pre-incident Rescuezilla image. The extra drive `/run/media/lauer/ext-ex4-1T-NVMe/` is a candidate resource, not completed protection; no drive access or new backup qualification occurred during closeout. Historical access checks are not standing recovery proof.

## 4. Completion State

- **Direction/name approved:** Ryan approved `5ea16a6`, confirmed Safe Harbor, and accepted owner disposition after every automatic segment restore. Opus delta PASS at `505a422` (85%) and Kiro governing PASS at `5ea16a6` (88%) remain pinned to those artifacts.
- **Plan and ownership:** Kiro delta PASS at `dca13a5` (88%); Ryan accepted that execution plan and B-E4.1 exactly as T2 specifies, including all five consumer outcomes. E4 full-scope compatibility PASS at `1268a50` (85%) remains complete; ownership is unchanged. No Recovery Authority T4/V4k authority was granted.
- **T1 / V1: ACCEPTED AND MERGED** via #387. Its exact-tip exception remains T1-specific.
- **T2 / V2: ACCEPTED AND MERGED** via #389. Ryan separately accepted the Codex review and documented evidence limitations at `eb06c97` as the T2 BugBot outage exception. The bounded delta PASS remains pinned to runtime/evidence `dac925f`; the owner exception names the documentation successor. Final-head CI passed before merge. CodeQL #6 remains previously dispositioned as a false positive.
- **T3 backend ordering gate: INDEPENDENT PASS (82%)** at `e08100ff`, source `93d4e34`; corrected nine-case evidence remains pinned. Bounded lapse investigation found no explicit production-directed operation, but ambient side effects cannot be excluded. See VERIFY for limits and failed attempts.
- **T3 implementation/evidence: KIRO STATIC PASS, NOT OWNER-ACCEPTED.** Review at documentation tip `a54357c940327881239db98c89b965b1365efc84`, runtime/tests `802d74dc0525a8040e44408b891f83edc20df97f`, on `feat/2026-10-13-safe-harbor-t3`. Kiro returned **PASS 85%**, no implementation blocker, after completing omitted reads in the same authorized review. VERIFY records the source qualification without upgrading the verdict into CI or owner acceptance. Final isolated run remains **92 passed**, launcher exit 0, focused lint regression gate 0 (raw pylint 20, existing findings). Codex contributed code/verification and is not the independent reviewer. The native small-store limitation remains; V5/V6 remain NOT RUN.
- **CI integration: KIRO DELTA PASS AT `ea2d316`, HOSTED CI FAILED.** Ryan supplied Kiro's bounded static delta PASS (88%), no blockers, and separately authorized draft [PR #391](https://github.com/alanmz-crypto/convmem/pull/391) and normal hosted CI. At head `ea2d316`, base `458b9f6`, merge-test commit `a795f5dd5fda0c0a18b2a0d438ddd40cc7e8ecef`, run `38450752959` completed with lint regression FAIL (duplicate-code 71→85) and pytest FAIL (21 failed, 3043 passed, 124 skipped, 8 errors; 262 subtests passed). Critical collection, secret scan and CodeQL passed. The prior local 149-case result was a selection, not hosted full-suite proof. No owner acceptance follows from either static PASS.
- **Lint correction / hosted result:** at `e7b5601`, run `38462958469` passed pylint, critical collection and security checks; full pytest failed with the same 21 failures and 8 errors as its predecessor. This is retained evidence, not a current green claim.
- **Bounded pytest correction / local evidence returned:** [VERIFY](VERIFY-safe-harbor.md#t3-bounded-pytest-compatibility-correction) binds the six test/harness-file correction: full isolated fixture config and Node, existing live golden exclusion, precise doctor helper fixture, explicit read inventory and shared watcher hash. Final selections: 296 passed/1 existing skip and 159 integration passes (overlapping); full lint gate 0, raw 30, 71 duplicates. Runtime/baseline/workflow/proof bodies/generated inventories unchanged. Retained development failures and enforced Cursor file-only authoring are disclosed. Fresh final-tip hosted CI and successor review/owner acceptance remain required.
- **T4/T5:** not granted; V5/V6 remain NOT RUN. T3 does not demonstrate backup usability or complete the arc.

## 5. Your Role (read this to know what you're here to do)

**Codex:** local correction/evidence returned; push and report normal hosted CI for the final candidate. Report new failures before expanding scope. **Cursor:** authoring complete, no active implementation continuation. No full local pytest or production ritual.

**Ryan / next reviewer:** successor review and T3/V3/V4 acceptance remain separate. Historical Kiro verdicts apply only to their named artifacts. PR #391 stays draft; no merge/live/T4/T5 grant.

## 6. What Remains Before "Live" (sequential)

1. Report fresh hosted CI covering the final correction head and merge-test tree. Local section 14 evidence passed with runtime/baseline/assertions fixed; new failures must be reported before expanding scope.
2. Obtain any required successor review and Ryan's T3/V3/V4 acceptance. T4/T5 still need separate grants; T4 must address direct-helper binding, hash alignment, event-only completion and uncertain outcomes.
3. Before rollout, resolve loss window, usable recovery artifact, old-process/guard-state adoption and rollback compatibility in EXECUTION section 6. Extra ext4 capacity is not qualified protection.
4. Deployment and corpus-affecting operations require separate scope, evidence and authorization. No production or session-indexing operations under this task.

## 7. Hard Stops (models cannot cross)

- T1/T2 and the proof grant are complete. T3 runtime and integration are statically reviewed at their exact pins. Section 14 local correction/evidence is returned; reporting fresh CI remains. Unrelated defects and runtime changes require a separate grant. No T4/T5, installed runtime, production data, service, backup-repository, key, retention or installed-permission changes.
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
- [VERIFY companion](VERIFY-safe-harbor.md): T1/T2 acceptance, corrected T3 proof, implementation evidence and limits; V5/V6 remain unrun.
- [Reboot checkpoint](https://github.com/alanmz-crypto/convmem/blob/bc3a6fd34bc594024d53fb86c9ca6b312cb64bd1/docs/inter-model/CODEX-2026-10-11-durability-reboot-checkpoint.md): review provenance and saved pre-reboot state.
- [Recovery Authority STATUS](STATUS-recovery-authority.md): ownership and hard stops.
- [Complete-data Backup v2 STATUS](STATUS-complete-data-backup-correction-v2.md): existing profile/restore contract and open consistency audit.
- [Team charter](../inter-model/TEAM-CHARTER-2026-07-06.md) and [decision/review guardrails](../inter-model/DECISION-REVIEW-GUARDRAILS.md): authority and review discipline.
- [Execution Planning guide](../planning/EXECUTION-PLANNING.md): active phase and stop condition.

## 10. How to Update This Brief (departure protocol)

Overwrite sections 3–6 when the actual state changes. Keep runtime observations dated and scoped; do not turn them into permanent green guarantees. Other orientation surfaces should point here instead of duplicating mutable milestones. Add one milestone-level update line; keep detailed review discussion in the architecture or review artifact. If Ryan renames the arc, rename the matching files and their pointers together.

## Update Log

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

[Arc Safe Harbor] Draft #391 has the returned lint correction with 149 isolated passes and full lint gate PASS. Fresh hosted CI and separate pytest-failure scope are next; prior reviews remain pinned, acceptance/merge/deployment/T4/T5 pending.

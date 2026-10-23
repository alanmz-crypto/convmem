# Arc Brief — Safe Harbor

> **Arc: Safe Harbor — RESUMED by Ryan 2026-10-22; initializer implementation granted (EXECUTION §23).** T1–T5 / V1–V6 remain accepted and merged through `c6f0724`; readiness PASS remains at `f45b051` and initializer-scope PASS at `c46fbc6`. Cursor builds the initializer in isolation under Codex supervision; it is not started. Operational readiness remains OPEN and no live work is granted.

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

- **Continuation branches:** `feat/2026-10-15-safe-harbor-rollout-evidence` (worktree `.worktrees/feat-2026-10-15-safe-harbor-rollout-evidence`) holds the readiness evidence, the §22 scope and the §23 grant; main `5c0a01b` was merged into it at `7cea298`. Implementation happens on `feat/2026-10-22-safe-harbor-legacy-initializer`, created from the grant commit, per the [Cursor handoff](../inter-model/CURSOR-2026-10-22-safe-harbor-legacy-initializer-handoff.md). Neither branch has a PR.
- **T1–T5 are on main:** incident retention/canonical identity (#387), target-bound preflight (#389), preservation and strict release (#391), serialized approval recovery (#392), and integrated evidence/operator handoff (#394).
- **Latest squash:** `c6f07241ccf1a71d9d874fee963a37b04091b3ce`; its tree equals accepted PR #394 head `188184b28707eb87c042d579aa7bbcba043dd5d0`. [VERIFY closeout](VERIFY-safe-harbor.md#t5-hosted-ci-owner-exception-and-squash-mapping) records CI, pinned reviews and Ryan's exact-head outage exception.
- **Historical deployed checkout:** the October 14 preflight observed runtime-main at `8a7cdab16420893fe26a2648d1d03f2b84d8589d`. October 17's bounded static inspection found it at `3e705e4197829f53ebbbd8433b59b60b648309d2`; the old deployment comparison is stale and has not been requalified. Disk identity does not establish loaded process identity.
- **Operational preflight/draft:** [ROLLOUT](ROLLOUT-safe-harbor.md) records October 14 observations and a conditional sequence. Those service/timer observations are historical, not current guarantees. No rollout transition has been performed by this lane.
- **Guard state at October 14 inspection:** two matching legacy snapshot generations lacked release evidence; no quarantine marker was present. Candidate reconciliation skips unchanged signatures, so it does not initialize these generations automatically. This lane performed no production validation/adoption.
- **New isolated readiness evidence:** `tests/_safe_harbor_rollout_evidence.py` runs a fixed selection under the reviewed bootstrap; `tests/test_safe_harbor_rollout_legacy.py` rehearses representative old manifests. [VERIFY readiness](VERIFY-safe-harbor.md#isolated-rollout-readiness--installed-interpreter-and-legacy-state) records source pins, results and limitations. Runtime is unchanged; no production initialization command was added.
- **Reviewed initializer scope:** EXECUTION §22 defines explicit preview/apply on the existing guard/CLI, durable originals, all-segment preparation before any CURRENT publication, no initializer pruning, and honest partial-completion reporting. [Kiro's scope PASS and delta](VERIFY-safe-harbor.md#legacy-initializer-scope--governing-review) are pinned to `8e0cfda` and `c46fbc6`. Implementation is granted (§23) but not started; its evidence matrix is not yet a passing test result.

## 4. Completion State

- **Resumed 2026-10-22, not complete:** Ryan lifted the October 19 hold and granted §22's isolated implementation and evidence (EXECUTION §23). A static drift check found the initializer's two runtime files and named helpers unchanged on current main; one new lock from PR #395 awaits the supervisor's confirmation that §22's locking is unaffected. Implementation has not started and no live transition is underway.
- Approved direction/name, every-restore owner disposition, execution plan and B-E4.1 remain settled. Ownership and gate exemptions are unchanged.
- **Implementation and integrated verification complete:** T1–T5 / V1–V6 accepted and merged. BugBot reviewed no accepted SHA; each owner exception remains bound to its own candidate.
- **Latest hosted evidence:** PR #394 head `188184b`, run `38668689296`, all six checks passed; Python 3.12 pytest 3,283 passed / 18 skipped / 252 passing subtests; critical collector exit 0; lint regression gate PASS against unchanged `fdc8da7` baseline. Raw lint status 30 is not a lint-clean result.
- **Focused Python 3.11 evidence reviewed:** 83 existing safety cases and five new legacy cases passed, no skips/source drift. Kiro PASSed the bounded evidence with high confidence, correcting its initially overstated coverage before completion. Recorded logs were read, not rerun; hash maps were not independently recomputed by Kiro. This is not a full-suite or deployment PASS, or Ryan's acceptance.
- **Deployment readiness OPEN:** old processes, timer routing, recovery inputs and an operational legacy initializer still require the named dispositions in ROLLOUT. The scratch refresh can create admissible evidence for synced state, but pending work still blocks release. Archival byte retention in tests is not a durable production archival procedure.
- **Initializer planning/review complete:** Kiro's same-session delta closed B1–B3 (preview no-effect control, live/original source comparison, apply-time backend recheck). No scope-decision condition remains; Ryan granted isolated implementation/evidence on 2026-10-22. No new tests or production commands ran during the planning/review turn or the resume check.
- At the October 14 preflight, the key-copy file was present on the mounted BIT-Brg drive; contents/equality/off-machine use were not checked. The ext4 destination was mounted and empty at top level. Those observations have not been refreshed. No current Rescuezilla artifact or accepted lost-work interval was established by that preflight.
- Limits remain: historical T5-F1 exact causal timeline unproven; fixture restart/IO injection is not hardware power-loss proof; strict release may refuse recoverable states; auxiliary sink and incidental-writer limits remain as accepted.
- **Startup exception (October 17):** doctor exited 1 on the retained Typora CPU-tripwire warning. Bounded read-only inspection established no ConvMem link or hardware cause. Ryan explicitly allowed static Safe Harbor planning/review to continue with the warning intact; this supplies no live-operation or healthy-host claim.

## 5. Your Role (read this to know what you're here to do)

**Codex (supervisor) with Cursor (author):** implement and prove the initializer per the [Cursor handoff](../inter-model/CURSOR-2026-10-22-safe-harbor-legacy-initializer-handoff.md) and EXECUTION §22–§23. First confirm the index-write-lock drift note and re-establish the readiness baseline on the merged base. Return code, evidence, corrections and limitations for independent review. No PR, merge, deployment or production action.

**Kiro:** independent review of the returned candidate, on Ryan's review grant.

**Ryan:** in parallel, the recovery facts in §6 item 1 (acceptable lost-work interval; newest Rescuezilla image, its location, independent access and restore-test history). They are needed before any live apply, not for the isolated build.

**All lanes:** preserve existing PASSes at their exact subjects and review only material deltas. Do not restart settled architecture reviews or infer authority from earlier grants.

## 6. What Remains Before "Live" (sequential)

Resumed 2026-10-22. Recovery facts and runtime observations must be refreshed
under the appropriate grant; nothing here is a live readiness claim. Revisit this
list before hardware or recovery maintenance that depends on these guarantees.

1. Resolve recovery artifact, independent access/custody and acceptable loss interval; any new capture or scratch restore needs its own bounded grant.
2. Implement (granted 2026-10-22, §23) and independently review EXECUTION §22's initializer; Kiro has passed the scope, but no public initializer or live procedure is qualified. Pending work is a refusal, not permission to flush or weaken release. Isolated implementation does not require guessing the still-open recovery facts.
3. Review the complete operational procedure: all old clients/manual writers, timer routing, audit publication, guard preservation/adoption and conditional rollback. Keep watch stopped/disabled and retain other arcs' limits. No automatic first-write migration or generic reconcile fallback.
4. Ryan grants only the named rollout transitions after those prerequisites pass. Record actual deployed identities and granted diagnostics afterwards. No implementation PASS or merge implies live recovery assurance.

## 7. Hard Stops (models cannot cross)

- Ryan's 2026-10-22 grant (EXECUTION §23) covers only isolated initializer implementation and evidence in the two named runtime files plus tests. No PR, hosted CI, merge, deployment, live run of the new command, service change, production corpus write, backup/restore or drive/key action; retain the tripwire warning.
- EXECUTION §§20–21's evidence work and §22's static review are complete; §23 is the only open Execute grant. No ledger write or session indexing during execution, and no other new tests are authorized.
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
- 2026-10-22 — Cursor: implemented `initialize-legacy` and isolated evidence in the legacy-initializer worktree; Codex supervisor push and Kiro review are next.

## TL;DR

[Arc Safe Harbor] Resumed by Ryan on October 22. Cursor builds the reviewed legacy-source initializer in isolation under Codex supervision, then Kiro reviews it independently. Warning retained; recovery facts and live readiness remain unresolved, and no live work is granted.

<!-- ref: ROLLOUT-safe-harbor.md — operational readiness and proposed sequence -->
<!-- ref: ../inter-model/CURSOR-2026-10-22-safe-harbor-legacy-initializer-handoff.md — current implementation handoff -->
<!-- src: VERIFY-safe-harbor.md — accepted implementation, hosted evidence and merge mapping -->

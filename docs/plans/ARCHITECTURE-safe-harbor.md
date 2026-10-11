# Architecture Direction — Safe Harbor

> **Arc: Safe Harbor (provisional name). Status: DRAFT, awaiting independent review and Ryan's direction approval.** This document grants no implementation, deployment, restore, indexing, or service action.

## 1. Source, problem and planning phase

**Source:** Ryan's durability-first request, the successive Codex/Opus/Kiro reviews, the [reboot checkpoint](https://github.com/alanmz-crypto/convmem/blob/bc3a6fd34bc594024d53fb86c9ca6b312cb64bd1/docs/inter-model/CODEX-2026-10-11-durability-reboot-checkpoint.md), and Ryan's subsequent instruction to resume work.

**Problem:** ConvMem needs operation-scoped recovery evidence and durable incident containment that remain understandable across processes, deployments and agent handoffs, without another overlapping safety subsystem.

**Priority:** Durability of the code and governance first; usability and speed second.

**Phase:** Architecture Planning. **Characters:** Architect, Systems Thinker, Risk Reviewer. **Function:** Planner. **Lanes:** Codex authors; Opus independently reviews; Kiro owns governing design sign-off; Ryan approves direction. **Authority:** drafting authorized by the resume instruction; direction approval awaits HITL. **Stop:** Await direction approval before Execution Planning.

The name is a working title pending Ryan's answer. The fresh Rescuezilla image's completion, identity and destination have not yet been supplied. Neither uncertainty is represented as an approved operational fact.

The active [Architecture Planning guide](../planning/ARCHITECTURE-PLANNING.md) calls for a system direction, alternatives and risks, not implementation tasks. The [decision-review guardrails](../inter-model/DECISION-REVIEW-GUARDRAILS.md) limit subsequent reviews to changes, regressions and unresolved contracts; they do not waive safety or sign-off gates.

## 2. System boundary

### In scope for this direction

- Recovery evidence required before a particular risky ConvMem operation, using existing Rescuezilla and Restic arrangements.
- The existing Restic gate's target/profile binding, honest health claims and production bypass behavior on its admitted call paths, including approval recovery.
- Failure classification in governed approval recovery: unavailable, absent, tombstoned, matching and conflicting states must remain distinct.
- Persistent incident containment at the existing guarded Chroma writer boundary: audit publication, evidence preservation, interrupted repair and validated release.
- A precise account of what these controls cover, with source identity and deployment evidence refreshed for each authorized change.

### Outside this arc's authority

- Recovery Authority T4/V4k, complete-data-v3 authority activation, selected-generation publication, serving promotion or migration. Their existing gates remain authoritative.
- A universal write barrier across all ConvMem durable state, MCP clients, arbitrary Python, shell, database tools or other applications.
- A general maintenance HOLD, approved-writer registry, new supervisor service, automatic repair scheduler or new backup repository.
- A live-backup freeze or snapshot-promotion scheme. The open capture-consistency contract is retained as a dependency, not implemented here.
- A global `ChromaStore` constructor change, mass retirement of entrypoints, broad runtime catch-up, permission deployment or backup-unit reconfiguration.
- Deployment of the detector, starting watch, changing backup retention, mounting/restoring images, or running recovery drills. Each is an operational action under its own grant.

**Cross-arc boundary:** This direction may propose stricter refusal and preservation around the already existing local segment guard and governed approval-recovery path. It does not add generalized recovery capability or alter Recovery Authority's provenance/serving contracts. Kiro and Ryan must accept that boundary before execution planning. If a proposed corrective requires T4/V4k or changes the complete-data restore-state matrix, route that portion to its owning arc; do not implement it under this title.

## 3. Evidence baseline and limits

Evidence labels: **D** = deployed runtime at `a92a74eb326b3eaa59087b707de10153c7cc0c63`; **B** = planning base `6a23aa93184460ed853996608bb28190c61f8d89`; **R** = detector candidate `5c6a4a8ad51c968a27afc1c8726fc78c4801cb6d`; **O** = observed during this conversation; **Reported** = Ryan/interlocutor report. Source readings establish code behavior under their assumptions, not end-to-end incident probabilities.

- **O — deployment:** the installed launcher names `.worktrees/runtime-main/convmem.py` and the conda interpreter. That worktree still reports D on resume. B is not the deployed release.
- **D — gate coverage:** [restic_gate.py:12](https://github.com/alanmz-crypto/convmem/blob/a92a74eb326b3eaa59087b707de10153c7cc0c63/restic_gate.py#L12) takes no write target, loads a separate backup context, and accepts the skip environment variable. [convmem.py:1320](https://github.com/alanmz-crypto/convmem/blob/a92a74eb326b3eaa59087b707de10153c7cc0c63/convmem.py#L1320) dispatches approval recovery without that gate. Existing indexed approval and upsert gates do not establish universal write coverage.
- **D — snapshot eligibility:** [restic_snapshot.py:756](https://github.com/alanmz-crypto/convmem/blob/a92a74eb326b3eaa59087b707de10153c7cc0c63/restic_snapshot.py#L756) selects by tag, normalized root and time; [line 923](https://github.com/alanmz-crypto/convmem/blob/a92a74eb326b3eaa59087b707de10153c7cc0c63/restic_snapshot.py#L923) applies the qualifying tag while capturing. The freshness predicate at line 544 accepts future local dates. These checks do not demonstrate restored usability.
- **D/B — unknown recovery state:** [propose_decision.py:157](https://github.com/alanmz-crypto/convmem/blob/a92a74eb326b3eaa59087b707de10153c7cc0c63/propose_decision.py#L157) converts several failures to empty values; line 220 discards the tombstone flag. Empty hashes can classify as `retry_chroma` at line 104. The relevant code is unchanged at B.
- **D — containment and repair:** [chroma_write_guard.py:597](https://github.com/alanmz-crypto/convmem/blob/a92a74eb326b3eaa59087b707de10153c7cc0c63/chroma_write_guard.py#L597) clears quarantine without the native lock; native admission checks quarantine before and inside that lock at line 632. Restore replaces live files at line 751 and treats census-unavailable differently from confirmed loss only implicitly at line 771; later refresh can prune older local generations at line 728.
- **R/B — detector:** [audit at line 796](https://github.com/alanmz-crypto/convmem/blob/5c6a4a8ad51c968a27afc1c8726fc78c4801cb6d/chroma_write_guard.py#L796) reads under the lock and publishes after leaving it. A skipped/error result can replace an earlier FAIL. [doctor.py:699](https://github.com/alanmz-crypto/convmem/blob/5c6a4a8ad51c968a27afc1c8726fc78c4801cb6d/doctor.py#L699) reports the latest result; it does not create a durable containment incident. This detector is present at B but not deployed at D.
- **D — incidental writes:** `open_chroma_for_read` uses a constructor that can create collections (`chroma_store.py:77,131`). The existing verify factory disables collection creation, but that is not proof of physically read-only Chroma access. No stronger read-only claim is assumed here.
- **O — current access checks:** the resumed `convmem doctor` exited 0. Local snapshot `f8d69dc1199636f66d6216f0325cf4218c566c829907dd205c244d00115c324b`, external lineage copy `a38bd4c7bfac4aa5c44634674138fa9c65f83cf37d7b3025c952b5368786f449`, and matching offline password copy all passed. These supersede the checkpoint's temporary mount/password warnings as access observations, not as restore proof. No secrets are stored in this draft.
- **Reported — Rescuezilla:** Ryan makes whole-system images and can readily make one more recent. The interlocutor described a September 16 offline image predating the corruption incident. Its contents, password recovery and restore usability were not independently verified here. The new image's completion is still unconfirmed.

The [Complete-data Backup v2 brief](STATUS-complete-data-backup-correction-v2.md#3-what-exists-right-now-file-map) leaves the broader consistency audit open. The [Recovery Authority brief](STATUS-recovery-authority.md#7-hard-stops-models-cannot-cross) retains its live-recovery and T4/V4k hard stops. Do not replace either fact with a generic green status.

## 4. Constraints and invariants

1. **No verified recovery point, no risky change.** A recovery claim names the affected state, exact artifact, demonstrated scope and accepted loss interval. Today's tag, a matching key, a completed capture, or an old drill alone cannot satisfy that claim.
2. **Unexpected result, stop and investigate.** A failed mutation, confirmed corruption, or uncertainty after a repair must not be silently converted into absence, successful repair, or permission to continue the original risky operation.
3. **Never repair production blindly.** Establish the recovery source and authority, preserve the damaged evidence, and define validation and interruption behavior before the first replacement.
4. **One incident authority for the guarded target.** Reuse `QUARANTINE.json`; audit results and events are observations/history. They must not independently release writers or overwrite the meaning of an unresolved incident.
5. **One target identity throughout an admitted operation.** The resolved target used by the writer, recovery preflight and native lock must agree. A path alias or independent config load must not create a different protection claim or lock domain silently.
6. **Publication under the relevant lock.** A finding and its containment must become authoritative before that lock is released. A blocked write cannot be admitted in a gap between detection and marker publication.
7. **An in-flight write cannot be retroactively cancelled.** Audit/containment waits for the same guarded writer lock; once the incident is published, subsequent guarded admission refuses. This is not revocation of arbitrary already-running external code.
8. **Inspection failure is not negative evidence.** Unavailable, malformed, interrupted and unsupported states fail closed for mutation or release. A diagnostic inability before any known incident may remain a warning; it does not by itself prove corruption.
9. **No silent policy expansion.** v2 is not v3, ID coverage is not vector/content correctness, access is not recovery, and a corpus read can still have implementation side effects.
10. **No extra permanent approval ledger.** Keep operation-specific evidence in the existing reviewed operation/grant artifact. Do not introduce a global `recovery_verified=true` flag, another incident latch, or a new deployment identity registry.

## 5. Options considered

### A. Keep the code unchanged; strengthen the runbook only

Lowest immediate code cost, but leaves unknown-state retries, post-repair uncertainty, evidence destruction and reset races to agent discipline. The existing defects are not removed by clearer prose. **Rejected:** it does not meet the stop/investigate requirement durably.

### B. Existing backups plus stronger existing admission and incident contracts — chosen

Use Rescuezilla/Restic for scoped recovery evidence; improve target binding and the specific recovery path; keep incident authority at the existing writer guard; preserve evidence and make release explicit and validated. Reuse doctor for visible status without treating it as the enforcement boundary.

This adds contract checks and necessary incident evidence, but no new always-running service, generic mode machine or approval registry. Its cost is more refusals and operator work during exceptional recovery. It addresses observed code defects with a small number of existing ownership sites.

### C. Add a general HOLD, deployment registry and coordinated live-backup freeze now

Could eventually cover more cooperative writers, but requires new state lifecycles, adoption across many paths, release/identity reconciliation and capture-to-gate publication semantics. It still cannot constrain arbitrary same-user actions. **Rejected for this arc:** too much new operational state before the current recovery capability and loss window are established.

## 6. Chosen direction and contracts

**Choose B.** Preserve existing recovery mechanisms, strengthen the current guarded boundaries, and require exact evidence for a risky operation. Reduce mistaken admission and silent repair rather than create another global control layer. The following are architecture contracts, not an execution task list or final API/schema.

### 6.1 Operation-scoped recovery evidence

The existing operation/grant artifact identifies the operation's code revision, resolved target and affected durable state; the exact snapshot/image and location; recovery dependencies including independent key access; the validation actually performed; and Ryan's accepted loss interval. No password or secret enters the artifact.

A qualification is scoped to one artifact and stated recovery use. For whole-workstation loss it must cover bootstrapping the software/configuration, the necessary authority/source material, keys and the usable corpus; models or other reacquirable resources may be listed as dependencies rather than assumed present. A subset check must not be labeled full recovery. Successful samples do not establish the consistency of every future capture.

Rescuezilla is the preferred existing candidate for planned corpus-affecting maintenance when its scope, usability and loss window are sufficient. Preserve the reported pre-incident image while arranging newer images; image recency is not proof that an older candidate is obsolete. Routine live Restic snapshots retain their demonstrated, narrower claims until the consistency question is separately resolved.

Documentation changes and the inspected detector-only release do not inherit every prerequisite of a destructive corpus operation. Conversely, routine indexing, approval events and pointer changes are not declared harmless merely because they are common. Unproven source completeness must not be used to classify a mutation as freely rebuildable.

**Honest enforcement boundary:** this direction does not propose that the existing CLI can mechanically verify an offline whole-machine recovery drill. The qualification/operation grant is an explicit human-controlled admission for planned risky work; existing automatic gates enforce only the narrower conditions they actually inspect. No universal per-write recovery guarantee may be reported. Ryan must set the acceptable loss window before routine protection is declared sufficient.

### 6.2 Target-bound preflight in existing call paths

Use the operation's already resolved write target and selected profile as inputs to the existing preflight; refuse mismatch with the backup context. Bind the complete affected data root, not just a same-spelled Chroma directory. Include approval recovery before its first logical state mutation, including approval-event mutation where applicable. Diagnostic failure reporting is distinguished from modifying the recovered object.

Reject the Restic skip in production and refuse ambiguous target/lane classification. A lab exception must identify an isolated test target. Confirm/skip environment variables remain cooperative controls, not authorization against a same-user actor. This arc does not claim to harden every legacy hook bypass.

A future-dated snapshot must not qualify merely because the current predicate accepts `>= today`; suspicious clock/freshness input requires investigation. Profile changes do not reuse a previous profile's recovery evidence. A bounded recovery operation must revalidate its target/state when admitted; a preflight followed by a changed config or stale cached lookup is not sufficient.

The Restic gate continues to report the conditions it proves, such as snapshot availability/freshness. It must not label those results demonstrated recoverability. No blanket extension to every command is implied; the coverage claim names the admitted command/factory paths.

### 6.3 Unknown-state recovery fails closed

Governed approval recovery obtains an explicit state result that preserves absence, tombstone, lookup failure, content hash and proposal marker. Include superseded state where necessary; a cold or warm cache cannot change the decision's semantics.

- Unavailable, tombstoned or conflicting state routes to review without re-upsert or a new successful approval event.
- Absence permits the existing retry only when the governed proposal/approved authority permits creation and target identity is established; it is not a general permission to recreate any missing item.
- Matching content and marker permit only the existing documented idempotent completion.
- Mutation decisions are checked at the relevant serialized admission boundary, not based solely on an earlier cached observation. Preserve the existing lock order; do not solve a race by introducing an inverse lock acquisition.

This changes error semantics, not the approved-decision authority model. Non-Chroma approval events are explicitly inside this recovery path's contract; other run ledgers and generation publishers retain their separate ownership and are not represented as globally frozen.

### 6.4 Sticky incidents at the existing guarded writer boundary

Confirmed structural failure or lost-vector findings create/retain quarantine while the native lock is held. Audit classification, incident publication and the corresponding audit result must respect that ordering. Account for `_quarantine()` raising: persisting the incident must not accidentally discard the diagnostic result or misreport success.

If storage failure prevents durable incident publication, fail the current operation and explicitly report that persistent containment could not be established. Escalate to the owner for process-level containment; do not claim a successful application stop or silently substitute a second latch. This is a limit of the guarantee, not a successful incident transition.

Later PASS, skipped, timeout or error observations may update telemetry, but do not release an unresolved incident. A diagnostic error with no known incident is not automatically classified as corruption; uncertainty after a live repair is different and requires containment.

Canonical target identity must select a single intended lock/incident location. Existing aliases or markers cannot be silently abandoned by switching path normalization. Any adoption/migration of an existing guard location is a separately reviewed deployment concern. Invalid marker contents, including semantically invalid JSON, must not represent an absent incident.

The coverage remains guarded native writes. Existing read clients may perform internal database writes; direct clients and external processes can bypass this application boundary. Doctor must report that scope, and operational maintenance must account for those processes rather than assume quarantine stops them.

### 6.5 Preserve before replacement; retain containment through uncertainty

Before an existing authorized local repair replaces or unlinks live segment files, durable evidence must identify the incident, target, observed files/missing files, failures and selected recovery generation. Preservation must complete before the first destructive replacement. Failure or insufficient space stops repair; do not delete evidence to make the repair fit.

Persist the unresolved incident under the native lock before the first live replacement, so interrupted repair remains an incident across restart. An explicitly admitted, bounded repair may act on its quarantined target while holding that lock; this is not release for ordinary writers. The original caller must not continue its requested mutation after an uncertain repair. This direction adds refusals/preservation to existing bounded recovery; it grants no new automatic repair capability and no Recovery Authority live-restore route.

After replacement, validate the restored segment and the relevant census. A bounded diagnostic retry may be defined later, but persistent unavailability cannot become success. Zero lost IDs proves the stated ID-coverage condition only; other repair reasons need their own relevant evidence. Preserve the damaged files and necessary prior recovery generation while the incident is unresolved; ordinary snapshot refresh/pruning must not destroy that evidence.

Keeping containment across a repair interruption and releasing it only through the contract below may change current automatic continuation behavior. That availability cost is intentional and requires review; it must not be hidden as a cosmetic fix.

### 6.6 Release is a validated operation

Quarantine release uses the same target identity and native lock as admission. It rechecks the current incident and validates evidence tied to that incident after the repair, so old successful checks or a concurrent clear cannot authorize release. Diagnostic/audit results alone never clear it.

Release requires Ryan-authorized disposition plus evidence sufficient for the incident's actual scope. Persist the disposition before durable marker removal; failure must remain conservative. The ordinary clear command must not silently unlink an unvalidated incident. A request to continue despite unresolved uncertainty is a separate owner exception requiring its own bounded operation and recovery evidence; no generic bypass is added by this draft.

Neither a restart nor a detector rollback clears an incident. Evidence cleanup is a separate, explicit retention decision after resolution and preservation elsewhere; no automatic cleanup policy is introduced here.

### 6.7 Capture consistency remains a separate interface decision

If a later loss-window decision requires a live capture change, a rejected or interrupted candidate must remain ineligible for the write gate across fresh invocations. The current qualifying tag cannot be applied before a post-capture rejection that the resolver ignores. Provisional tagging/promotion is only a candidate mechanism; snapshot identity and external-copy lineage must be evaluated before adoption.

That future design must account for SQLite, HNSW and non-Chroma durable state within its claimed scope. No SQLite-only staging or freeze is labeled whole-system consistency. This arc does not close the existing Hybrid consistency audit or require building the freeze before the bounded detector.

## 7. Risks, reversibility and durability cost

- **Human recovery evidence can go stale.** Bind it to an operation and exact artifact, with explicit invalidators such as changed scope/profile, key loss, inaccessible media or unacceptable age. This is an existing grant artifact, not a new permanent green registry.
- **Stricter refusals reduce availability.** Missing state or an unresolved incident may require operator attention. Do not silently restore the previous fail-open behavior to restore convenience. This is the principal chosen trade-off.
- **Preservation consumes storage.** Failure to preserve blocks replacement; unresolved evidence is retained. Retention sizing and destination are operational inputs, not permission to remove the only recovery copy.
- **Locks cover cooperating code.** In-flight and direct-client behavior remain bounded explicitly. This draft does not promise that a same-user adversary cannot edit a marker or bypass the application.
- **Canonicalization can strand existing markers.** Require reviewed adoption before rollout; preserve old state rather than treating a new path as an empty guard.
- **Release and repair have crash windows.** Reuse the single incident authority and conservative restart behavior. Exact crash points, lock ordering and durable-write mechanics belong in the execution/verification artifacts after this direction is accepted.
- **Detection can miss semantic corruption.** Structural checks, counts and ID census are useful but insufficient for every corruption class. Qualify recovery content separately; do not relabel the detector as a complete integrity oracle.
- **Rollback is asymmetric.** Code can be reverted under a deployment grant; restoring an old implementation must not clear incidents, delete evidence or imply corpus rollback. Mixed-version processes must be reconciled for any future writer-boundary change. The exact detector commit is assessed separately from such a change.

This direction is expected to rot less than A because unknown states and release errors become behavior at existing boundaries rather than repeated prose. It is expected to rot less than C because it adds no second stop state, identity database, generic supervisor or live-capture protocol. That is a design judgment (85% confidence), not measured lifetime reliability.

## 8. Acceptance claims and later evidence

These are outcome requirements for later execution/verification planning, not tests run or tasks authorized here:

- A failed/mismatched recovery preflight leaves the recovered logical object and approval state unchanged; unrelated diagnostic reporting is identified separately.
- Unavailable and tombstoned targets never become absent-state retries, under both cold and warm lookup conditions and competing admitted writers.
- An audit FAIL followed by a skipped/PASS observation or process restart cannot admit a guarded write before explicit release.
- A competing writer cannot enter between incident detection and authoritative containment publication.
- Interruption after durable incident publication leaves a diagnosable contained incident until validated release; no torn evidence or needed recovery generation is silently pruned. Failure to publish the incident prevents repair mutation and reports containment unavailable rather than claiming persistence that failed.
- A stale or mismatched release proof cannot clear the current incident; malformed incident state fails closed.
- Coverage demonstrations name the actual callers and resolved target, rather than only asserting helper invocation. Negative controls must show the relevant failure is detectable.
- Recovery qualification identifies exact artifacts and scope. Sample success does not certify future captures; a zero-lost-ID census does not certify all vector values.

No qualification drill, concurrency experiment, live corpus probe beyond required doctor, or test suite was performed in this drafting phase. These are proposed obligations, not completed evidence.

## 9. Owner inputs and confidence

Before operational protection is declared adequate, Ryan must supply the acceptable lost-work interval for routine operations and planned maintenance, confirm the new image's status/scope/location, and identify demonstrated restore history or authorize a bounded qualification. The new image's name and this arc's final codename remain open inputs. These do not change the selected architectural option.

Confidence in conclusions, not incident probabilities:

- Existing mechanisms plus scoped corrective contracts are preferable to a new general subsystem: **85%**.
- Unknown/tombstoned state must not license mutation: **95%**.
- Incident publication/release must serialize with guarded admission: **95%**.
- Preservation and failed/interrupted validation must retain containment: **90%**.
- A freeze is unnecessary for this architecture phase; its later need depends on the loss window and usable recovery artifacts: **85%**.
- Operational priority ordering is less certain than the source findings: approximately **75%**, pending backup and loss-window facts.

## 10. Downstream handoff and independent review brief

**Next:** Opus reviews this exact architecture and [STATUS brief](STATUS-safe-harbor.md); Codex corrects findings; Opus performs a delta review; Kiro provides governing design sign-off; Ryan accepts/rejects the direction. Only then may Codex shape an execution plan. No Cursor implementation grant follows from publishing or merging this draft.

**Reviewer assignment:** Challenge the selected direction, not the earlier chat's credibility. Read the pinned D/B/R evidence before adopting a claim. Prioritize these possible failures in this draft:

1. Is the distinction between operator-qualified maintenance and narrower automatic gates honest enough to prevent a false universal safety claim? Name any operation incorrectly admitted by the proposed boundary.
2. Does reusing quarantine for interrupted repair overload it, especially when `_quarantine()` raises and release must be serialized? Identify a concrete crash/concurrency counterexample.
3. Can target canonicalization or older running code bypass the intended incident domain during rollout? Does the direction bound this without inventing an identity registry?
4. Does evidence preservation retain the right authority and recovery generation without making failure handling depend on unavailable storage?
5. Do the approval-recovery rules distinguish creation from a tombstoned or unreadable update under real cache and lock behavior?
6. Does any proposed contract cross Recovery Authority T4/V4k or the complete-data capture/restore boundary? Distinguish local corrective work from an upstream architectural dependency.
7. Do existing Rescuezilla arrangements eliminate a proposed mechanism, or does the unknown loss window invalidate a claimed recovery guarantee?

Return one overall verdict, concrete blockers with file/section evidence, confidence percentages, and the smallest correction for each. Separate findings from optional improvements. One adversarial pass and one delta are the expected cadence; unresolved safety findings are not waived by that cadence. Do not implement, invoke corpus-writing tools, run restores, deploy, index this session, or reopen the unchanged detector decision without new evidence.

**Draft publication PR title:** Define scoped recovery and incident containment for Safe Harbor

**Draft PR description:** Ryan can review one bounded direction for recovery evidence and incident handling, with explicit limits on what the existing controls prove. Codex authored this 2026-10-11 planning draft after the durability reviews and reboot checkpoint; Opus reviews independently and Kiro supplies governing sign-off. The draft uses existing backups/quarantine, records the deployed-versus-planning revisions, and links one STATUS source from the required orientation surfaces. It authorizes no implementation or live action. No tests or restore drills were run. **Merge reading:** [architecture](ARCHITECTURE-safe-harbor.md), [STATUS](STATUS-safe-harbor.md). **TL;DR:** Review direction first; execution planning awaits Ryan's approval.

Active phase lane must stop here. Await HITL.

## TL;DR

- Choose existing backups and stronger existing admission/incident contracts, with explicit coverage limits.
- Preserve evidence before replacement; keep incidents authoritative through interruption and release them only through validated, serialized disposition.
- Defer a generic HOLD, identity registry and live-backup freeze. Keep detector deployment and all live recovery separately authorized.
- This is an unapproved direction draft under a provisional arc name; fresh-image completion and the loss window remain unconfirmed.

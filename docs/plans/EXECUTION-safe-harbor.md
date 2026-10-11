# Execution Plan — Safe Harbor

> **Arc: Safe Harbor. KIRO DELTA PASS at `dca13a5` (88%); PLAN REVIEW COMPLETE; OWNER DISPOSITION/ACCEPTANCE PENDING.** Ryan authorized Codex to draft this plan on 2026-10-11. Implementation, isolated execution, deployment and live operations remain pending. A task below is a proposed deliverable, not an executable grant. Review verdicts remain pinned to their exact revisions; this update records the verdict and routing without changing the reviewed task contracts.

## 1. Source, authority and goal

**Source:** Ryan's instruction: “Authorize Codex to draft the Safe Harbor execution plan. Implementation and live operations remain pending.” The direction is [ARCHITECTURE-safe-harbor.md](ARCHITECTURE-safe-harbor.md), approved at `5ea16a6c7af7900b981d19eb03b168d77f611718`, including owner disposition after every automatic segment restore. Kiro's full-scope E4 PASS (85%) is recorded in architecture section 10; backup ownership stays with Complete-data Backup v2.

**Goal:** Make the existing recovery preflight and guarded incident lifecycle fail conservatively, retain original evidence across interruption, and require current proof plus owner disposition before writers resume.

```text
Planning Status
Phase:        Execution Planning
Characters:   Task Decomposer, Dependency Mapper, Scope Guardian
Function:     Planner
Lanes:        Codex authors; Kiro reviews; Cursor implements after a separate grant
Authority:    Drafting authorized; plan acceptance and Execute pending Ryan
```

Standards: [Execution Planning](../planning/EXECUTION-PLANNING.md), [decision-review guardrails](../inter-model/DECISION-REVIEW-GUARDRAILS.md), Ousterhout's existing-module boundaries and the Hard Parts digest's explicit ownership/transaction trade-offs. This plan chooses one bounded route; rejected alternatives remain in the approved architecture.

### Pinned evidence and deployment reality

- **D — deployed source:** `a92a74eb326b3eaa59087b707de10153c7cc0c63`; runtime-main still resolves to D during this drafting session. Installed `/home/lauer/.local/bin/convmem:2` selects that worktree and the conda interpreter.
- **P — planning source:** `a3608ce93abd842aa5293b0030199c4631cb183c`, on `plan/2026-10-11-safe-harbor`. Its code baseline and local `origin/main` are **B** `6a23aa93184460ed853996608bb28190c61f8d89`. These are observations, not a deployment or permanent identity guarantee.
- P contains the detector additions from **R** `5c6a4a8ad51c968a27afc1c8726fc78c4801cb6d`; D does not. Detector-only deployment remains a separate decision. Implementing this plan against P does not authorize deploying B or a broad main catch-up.
- Required session orientation ran: doctor exited 0, then brief, unresolved and a history search. These CLI reads may cause Chroma bookkeeping writes; they are not physical read-only evidence. No implementation tests, restore drill, indexing, backup creation or external-drive write was performed for this plan.

Source anchors used to shape the tasks (P unless marked D):

- `restic_gate.py:12-26`, `chroma_write_store.py:707-745`: independent gate configuration versus lease-then-live-config writer construction.
- `backup_workflows.py:145,187,197-228,283,317,350,366-374`: probe, live ensure, auto-backup handling, copy and health consumers; offsite resolver failure is WARN, not local health's FAIL.
- `chroma_write_guard.py:586-631,636-689,694-792,796-828,840-849`: marker parsing/overwrite/clear, native admission, snapshot pruning, restore, audit publication and recover recheck gap.
- `conflict_events.py:43-57`: the shared writer lease is acquired **before** the governed lock. `propose_decision.py:235-280,569-595` currently reopens a production store during recovery; `ledger.py:395-402` caches a filtered lookup.
- `conflict_events.py:60-86`: append writes then flushes/fsyncs; an exception does not establish that APPROVED is absent. The reader rejects a malformed final record. Recovery must reconcile the authoritative log rather than assume an unsuccessful call rolled back.
- `observe.py:116-120,128-144`: approval recovery can affect Chroma and the JSONL export, in addition to proposal events. The admitted target must cover all of these.
- D `restic_snapshot.py:544-547,802,825`: current-day freshness admits future dates. P `restic_snapshot.py:40-52` is the existing numeric error vocabulary.

## 2. Scope and acceptance gates

In scope: the admitted `add --upsert`, indexed `record --approve-last` and proposed `record --recover` preflight; guarded Chroma admission, audit incidents, existing bounded segment restoration and validated release; recovery's associated event/export writes; focused tests and synchronized policy documentation.

The adopted `index` and plain `add` Restic exemption remains. `forget`, refine and `--no-index` approval gain no new Restic rule here. Their existing native mutations matter to the concurrency proof, not as silently added gate consumers. Direct Chroma users, incidental MCP/read writes, run ledgers and generation publishers remain outside a universal stop claim.

Deferred: generic HOLD, identity registry, live-backup freeze/staging, global read-constructor change, permission deployment changes, backup-service migration, detector deployment, cleanup/retention automation and new write endpoints. Recovery Authority T4/V4k, complete-data-v3 activation, selected-generation/serving publication and its restore-state matrix stay outside this grant.

Before this plan can be accepted:

1. Kiro reviews this exact plan and its E1–E7 mapping. A rejection routes to Ryan under the planning guide; Codex does not self-authorize revision or execution.
2. Complete-data Backup v2's owner explicitly dispositions the concrete B-E4.1 proposal in T2, including consumer outcomes and profile compatibility. E4 direction PASS is already complete; it is not approval of this detailed change.
3. Resolve O-E4.e's wording against the approved existing-preflight coverage. This plan uses the existing Restic gate for approval recovery. It adds a named consumer, not an independent protection mechanism. If a different mechanism is intended, Ryan must decide the contract change.
4. Ryan accepts the plan revision and separately names any task to execute. Operational recovery inputs in section 6 are required before live rollout, not before drafting or hermetic implementation.

## 3. Five bounded tasks

All tasks are **NOT STARTED**. Execution lane: Cursor, following later authorization. Shared files make implementation serial by default: **T1 → T2 → T3 → T4 → T5**. Review of T2's interface proposal can occur alongside review of T1; this does not grant parallel working-tree edits.

### T1 — One durable incident authority at the existing guard

**Deliverable:** guarded admission and the audit retain the complete unresolved incident set, including new findings on an already affected segment.

**Files:** `chroma_write_guard.py`, the guard/audit checks in `doctor.py`, the status/clear surface in `scripts/chroma_guard.py`, focused existing guard tests.

Contract:

- Keep `QUARANTINE.json` as the sole admission authority. Give it a versioned, target-bound incident set with stable incident IDs, monotonic finding revisions and deterministic finding digests. Reobserving the same unchanged failure need not create infinite new incidents; a changed finding must invalidate older dispositions. Retain every unresolved finding, without the present truncation/overwrite behavior.
- Only missing marker means absent. `null`, scalars, empty/unknown-schema objects, invalid incident sets, wrong target and read errors block. A recognized legacy marker also blocks; preserve its original bytes and findings when adopting it under the lock. No unrecognized marker is silently reset or migrated into an empty set.
- Use the canonical target for guard, store/cache identity and native-lock reentrancy. If lexical and canonical paths expose competing legacy guard locations, refuse adoption and report both; do not create a fresh empty authority. This task adds no live migration command.
- Audit gathers, classifies and durably publishes all detected structural/lost-vector findings while holding the native lock, then publishes its observation in the same ordered operation. Separate internal incident publication from the public raise so the first failure cannot discard the other findings. Later skipped/error/PASS telemetry cannot clear the marker. A diagnostic error alone is not automatically corruption.
- Recheck authority after lock acquisition on every guard entry, including `recover()`. If durable publication fails, abort the current operation before replacement or its requested mutation, report **containment unavailable**, and request owner process-level containment; do not claim a durable stop.
- Until T3's validated release exists, the ordinary clear command refuses unresolved incidents. Keep diagnostic access; no “force clear” or skip flag.

**Evidence / gate:** V1 in the VERIFY companion: fresh-process admission after A then B; two findings on one segment; malformed/legacy markers; audit FAIL then PASS/skipped; concurrent audit/writer; marker publication/fsync failure. Inspect marker contents and fixture mutation effects, not just whether a helper was called. A deliberately restored overwrite implementation must fail the A+B proof.

**Stop:** no rollout of a changed marker schema while old writers/clear commands can still run. This task alone is not a deployable operator release workflow.

### T2 — Bind the existing preflight to the operation and settle freshness semantics

**Deliverable:** one target-bound preflight consumed by the named gated operations, with a reviewed v2 freshness contract.

**Files:** `restic_gate.py`, `restic_snapshot.py`, `backup_workflows.py`, admission portions of `chroma_write_store.py`/`convmem.py`, narrowly needed lane classification in `runtime_guard.py`, existing Restic/workflow/gate tests, and ROADMAP/RECOVER/role-mapping plus v2 interface documentation under its owner.

Admission:

- Resolve the operation configuration once under the existing shared writer lease, before opening a Chroma client or modifying approval state. Bind preflight and downstream helpers to that immutable operation configuration; remove independent reopen/reload in this path. Shared leases do not freeze arbitrary config edits: detect changed target/profile inputs before mutation and refuse rather than silently adopting new ones.
- Pass the resolved Chroma target, selected backup profile and complete affected durable-path set to the existing gate. Load one immutable `BackupContext`; require canonical Chroma equality, explicit v2 data root/profile/tag, and containment of every affected event, approved-row and export path in that root. Use the existing path resolvers to enumerate actual outputs; never infer complete-data coverage solely from the Chroma directory's parent. A symlinked export outside the protected root fails.
- On these production paths, `CONVMEM_SKIP_RESTIC_GATE=1` is rejected. A lab/test exception requires canonical isolation from production and an explicit test/lab context; cwd, a name containing `convmem-lab`, confirm variables or `CONVMEM_ROOT` alone are insufficient. Unknown classification refuses. This remains a cooperative safeguard, not authorization against a same-user actor.
- The same gate protects approval recovery before any logical mutation, including an event-only completion. A genuinely already-completed read-only return may remain a no-op; prove it writes neither events nor corpus. This does not change the `--no-index` approval exemption status.

**B-E4.1 selected proposal for v2-owner review — not yet accepted:** keep freshness policy inside v2's resolver. Current-day eligibility requires today's local date; a snapshot timestamp later than the captured evaluation instant is reported as suspicious future time, not accepted or silently corrected by taking another backup. Carry a machine-readable freshness reason through the existing `ResolverError`/`WorkflowOutcome`, using existing `EXIT_STALE=25`; no new numeric exit namespace. Old stale dates retain the current snapshot-if-stale behavior. Future-time errors are excluded from ensure's backupable cases at `backup_workflows.py:197-228`, including dry-run success. No fallback to an older/legacy candidate hides the suspicious result.

Capture one evaluation instant/timezone per resolution. The post-backup resolution takes a fresh instant so a newly created snapshot is not rejected against the pre-backup clock. Crossing a day boundary requires fresh resolution before admission. Profile/tag selection, exact-path rules and external `destination.original == source.id` remain intact. Regression evidence includes supported legacy/v2/v3 resolver consumers; this change activates no v3 profile and reinterprets no restore state. Any additional owning-arc conflict returns to its owner rather than expanding scope.

**O-E4.d consumer outcomes:**

- Live ensure/write gate: same-day eligible → PASS; old/missing eligible source → existing backup then exact re-resolution; future → FAIL/25 without backup or mutation.
- Check-only ensure probe: retain `require_current_local_day=False` and its existing toolchain/reachability outcomes, including caught-resolver-error PASS. Label eligibility **unchecked**; it never licenses a write or supplies a qualifying snapshot. Preserve failures outside that probe's resolver catch. Identical PASS/FAIL across consumers is not required.
- Local health: future → FAIL/25; preserve existing legacy-profile warning semantics.
- Offsite health: future source → WARN with resolver code 25 under its current nonfatal health contract, never PASS or a fallback source.
- Offsite copy: future source → FAIL/25 before copy. A valid source still requires existing destination-lineage proof.

**O-E4.b error mapping:** invalid/ambiguous operation config, lane or profile → 20; resolved target/path mismatch → 24; freshness → 25 with reason; propagate 21/22/23/26/27/28/29 from their existing boundaries. Do not repurpose restore classification codes 30–32. Doctor's process exit follows its existing severity aggregation, not a newly invented gate code.

**Evidence / gate:** V2: all five consumers, timezone/day rollover, future within today and future day, target A backup versus target B write, exported state outside the root, profile/tag mismatch, prod skip despite lab-looking cwd/config/env, isolated test exception, config change between preflight and use, missing/error Restic. Check effects through both existing CLI gated commands and T4's recovery integration. No-op gate negative control must permit a fixture mutation that makes the proof fail.

**Stop:** no implementation of the resolver-contract change until v2-owner disposition and later task authorization. Do not solve disagreement by adding a caller-only parallel freshness policy. Updating the policy documents is part of this deliverable, with T4's new consumer clearly named before activation.

### T3 — Preserve, bound repair, and release against current evidence

**Deliverable:** an interrupted segment repair remains contained with its originals intact; release requires proof covering the whole current incident set and Ryan's matching disposition.

**Depends on:** T1; use T2's operation/recovery boundary where applicable. **Files:** `chroma_write_guard.py`, `scripts/chroma_guard.py`, focused watch recovery reporting in `watch.py`, doctor display and existing guard/worker tests. Do not add a general repair engine.

**Ordering gate (Kiro A1):** T3 begins with the isolated, pinned-backend demonstration specified below and in V4. Record passing evidence for monotonic update/delete/re-upsert, queue purge and restart, plus a valid releasable control and the stale-vector refusal control, before implementing the remainder of T3's preservation/repair/release changes. Only the bounded scratch proof/harness work may precede this gate, under a later T3 grant. If the oracle cannot be demonstrated, stop T3 and return the gap to Codex/Ryan; do not build the rest against presumed backend semantics or weaken release. This orders work within T3, not a new task or current experiment grant.

Preservation and repair:

1. Under the native lock, record the incident and pin the selected recovery generation before any replacement. The incident binds canonical target, collection/segment identities, source generation and findings revision.
2. Preserve original files and missing-file facts into a private per-incident directory under the existing guard root. Copy, do not rename away the live originals. The manifest names all observed files, errors and content hashes; reject unsafe file types/path traversal. Fsync files and directories, publish an immutable preservation-complete manifest, then durably bind its digest into the incident. First replacement is forbidden until both publications succeed.
3. Interruption before completion permits resuming preservation only while live originals still match the recorded identity. Completed preservation is write-once; retries validate it and cannot overwrite originals with partially repaired files. Failed space/IO/hash checks retain containment. Do not clean incomplete evidence automatically.
4. Only the guard's existing bounded restore routine may cross quarantine, under the native lock and bound to that exact incident/target/source. Revalidate and pin source bytes before reuse. Persist repair progress conservatively so a crash during any replacement remains resumable against the same preserved originals; do not grant arbitrary native writes through a flag.
5. Validate replaced files and census under the lock. Permit one diagnostic census retry; persistent unavailability, missing segments or findings retain containment. A successful restore also remains an incident and aborts the initiating mutation. Watch may report the incident but must not relabel it a completed ingest or silently retry past the guard.
6. Unresolved incidents pin torn evidence and every needed recovery generation. Guard refresh/pruning cannot delete them. Resolution does not trigger automatic evidence cleanup.

**E1 release oracle — deliberately conservative first slice:** ordinary release after a segment restore must prove that no collection operation occurred beyond the restored vector save's sequence watermark. Store the source watermark, collection/segment identity, backend/schema identity and source file digests in the existing `SNAPSHOT.json` when a guarded save is copied; do not add a second ledger. At release, read SQLite through a read-only transaction, require the metadata watermark to equal that saved vector watermark and no later relevant queued operation, require matching identities/digests, structural validity and the appropriate ID census. Unknown/missing sequence evidence, a newer operation, a legacy snapshot without that evidence or unsupported backend semantics keeps containment.

This is a strict empty-changed-set proof, not ID-count equality or a proof of historical semantic health. It intentionally refuses some recoverable states with pending/newer work. No automatic re-embedding is added. Installed Chroma Python sources expose sequence fields, but that alone does not establish the active Rust backend's semantics: T3 must demonstrate monotonic update/delete/re-upsert behavior on the pinned backend in scratch, including queue purge and restart. If that oracle cannot be demonstrated, stop T3 acceptance and route the concrete gap to Codex/Ryan; never substitute a census-only release. Existing incident reasons such as lost IDs also require their own current evidence, not only watermark equality.

Release:

- Evolve the existing clear surface into a validated release requiring an explicit owner-disposition reference and the exact current incident/finding digests. This is cooperative provenance, not proof that a string was typed by Ryan. No generic force option and no ordinary “clear” success without evidence.
- Acquire the same target's native lock; recheck all incidents, findings, repair status, preserved evidence and post-repair state. Validate the complete set; this slice makes release all-or-nothing. A new finding invalidates the submitted disposition. No automatic repair or Chroma client opening is part of validation.
- Append an incident-bound **release disposition** to the existing `events.jsonl`, flush/fsync it and, on creation, its parent directory; only then durably remove the resolved marker and fsync its directory. A malformed/truncated event tail blocks release; do not discard it or treat an append attempt as successful. Serialize appends so diagnostics cannot interleave partial release records.
- A crash after the durable disposition but before removal leaves containment; retry revalidates current state. A crash after durable removal leaves the historical disposition. Event history alone never admits a write or clears a recreated/new incident. Uncertain removal/fsync failure returns failure with an explicit uncertain-persistence report and requests process-level containment; it cannot promise a marker is present if unlink already happened.

**Evidence / gate:** V3/V4: process termination at each publication, copy, replacement, append and removal boundary; simulated short write/ENOSPC/fsync failure; source-generation pinning; A+B release; same-segment additions; stale-disposition replay; source watermark absent/newer; same ID with changed vector where the old census passes. Force the faulty census-only release and copy-over-original variants to fail independent assertions. Fixture restart evidence does not by itself prove hardware power-loss behavior.

**Stop:** no repair outside the existing routine, no blanket continuation exception, no live schema adoption or rollback to a writer that can ignore these incidents.

### T4 — Make governed approval recovery a serialized, target-bound operation

**Deliverable:** `record --recover` cannot turn unavailable, tombstoned or conflicting state into a re-upsert or successful approval event.

**Depends on:** T1–T3. **Files:** recovery portions of `propose_decision.py`, `convmem.py`, narrowly scoped event-completion helpers in `conflict_events.py`, store-aware helpers in `observe.py`/`ledger.py`/`chroma_store.py` and writer admission, relevant governed recovery/writer/gate tests.

Contract:

- Use T2's admitted configuration/store throughout. Enumerate and bind events, approved intent and units export as well as Chroma; do not let `ingest_approved_ledger()` reopen a different configured target.
- Actual order: shared writer lease → resolved config/preflight → governed lock → native guard critical section → existing export lock when needed. The governed lock already nests inside the shared lease (`conflict_events.py:43-57`); do not implement the earlier review's apparent reverse order. Trace every newly nested lock, including sinks, and prove no reverse path. This is not a claim that every repository operation has a single global lock order.
- Refactor only enough of existing guard admission to span reload/reconciliation, fresh lookup, decision and the native mutation. Nested `_native()` calls must not run a second reconciliation/refresh in the middle of this operation. Guard refusal/restore aborts before recovered-object or successful-event mutation.
- Obtain a fresh lookup including superseded records from the admitted store after reload; bypass the process cache for this decision. Missing collections, duplicate ledger identities, invalid/missing hashes, unreadable proposal/approved authority and read failures are explicit unknown/conflict states, not absence.
- Tombstoned/unavailable/conflicting → review, no re-upsert/export/APPROVED append. Proven absence → retry only for the existing authorized proposal intent. Valid matching proposed content and proposal marker → idempotent completion. Valid unchanged base → existing authorized retry. Marker repair requires matching proposed content and the correct durable intent; a conflicting marker is not silently overwritten.
- Hold the native critical section from final state recheck through the recovered mutation and its completion event/export effects; `forget`/refine compete at that same native lock. Complete post-native validation/guard maintenance before publishing a successful approval event; do not append APPROVED inside an outer context whose exit can still discover a torn save. This serializes admitted operations but does not forbid a separately authorized mutation that occurs after recovery finishes.
- Preserve recoverability of partial Chroma/export/event completion; no cross-file atomicity claim. On failure, stop the affected recovery and report incomplete recovery or **completion outcome unknown**, never command success. An append/flush/fsync error or interrupted return can occur after a complete APPROVED record became visible or durable. Do not promise APPROVAL_STARTED remains, rewrite history to make it so, or infer rollback from the exception.
- Before retrying an uncertain completion, reload and reduce the authoritative event log under the governed lock; recheck the bound intent, current Chroma state and required export effects inside T4's native critical section. A valid APPROVED record prohibits duplicate approval append or blind re-upsert; return success only after the required effects and publication durability are established. A valid APPROVAL_STARTED state with no completion record permits only the already-defined state-aware recovery. A malformed/truncated/unreadable log or contradictory effects stop for review, without automatic truncation or speculative append. Rereading visible bytes alone does not cure failed fsync or prove power-loss durability; the event publication's required file/directory durability must succeed before completion is reported. No new lifecycle state or parallel ledger is introduced by the diagnostic outcome.
- **Publication durability (Kiro A2):** flush/fsync the completed APPROVED event's file. When the log is created, fsync its parent directory before reporting completion; if this path creates directories, make the newly created directory entries durable as well. Appending to an already durably named file still requires file fsync, not a claim that every append creates a new directory entry. Any required directory-fsync failure follows the same uncertain-outcome contract. V5 must assert these publication boundaries explicitly, as V4 does for release dispositions.
- On retry, verify/complete missing export effects rather than letting an unchanged-Chroma shortcut skip them. Do not reapply a tombstoned target merely to repair an export, and do not treat a terminal event alone as proof that every associated effect is complete.

**Evidence / gate:** V5: CLI and direct recovery helper; cold/warm caches; unavailable, tombstone, true absence, stale base, matching/mismatched marker; config replacement; export/event failure after Chroma success; concurrent `forget` and refine. Inject completion failures before append, after a partial record, after a complete record but failed fsync, and after durable append but before return; restart and reconcile each from the log. Assert no premature command success, no duplicate APPROVED, no blind replay, and no discarded malformed tail; do not assert that every failed invocation leaves APPROVAL_STARTED. Assert document, vector, metadata/tombstone, export bytes and reduced proposal lifecycle. Use process barriers to force the race, not sleeps. Old unknown→empty classification, failure-assumed-rollback retry and moving the recheck outside the guard must fail the proof. Existing index/plain-add gate exemptions remain behaviorally unchanged.

**Stop:** unresolved lock inversion or a needed authority-model change goes back to planning; no rewrite of the broader proposal lifecycle or other durable-state publishers.

### T5 — Integrated evidence and a bounded operational handoff

**Deliverable:** an exact-revision evidence packet in [VERIFY-safe-harbor.md](VERIFY-safe-harbor.md), plus recovery/rollout instructions that describe the implemented limits.

**Depends on:** T1–T4. **Files:** the VERIFY companion, existing policy/recovery docs, STATUS/LATEST routing and focused integration fixtures only. Runtime scope gaps discovered here are failures, not license for unrelated improvements.

- Run the accepted V1–V5 cases in isolated temporary roots, fake providers and test repositories; explicitly override config, HOME/XDG-derived paths and service entrypoints. Harnesses must reject production paths. No tests load a live corpus, reach a live model provider or use a production Restic repository.
- Require real fixture subprocesses and fresh-process restarts for lock/crash claims, plus effect assertions and failing negative controls. Report unsupported power-loss/storage semantics separately. Keep the old tests that expect automatic restore-and-continue visible in the change rationale and replace that expectation with containment; do not weaken a test merely to make it green.
- Execute owns the applicable exact-tip external-review gate under [EXECUTE-TASK.md](../planning/EXECUTE-TASK.md#external-review-gate); runtime changes require the recorded review evidence. Verify confirms it and Kiro signs off; neither a local test PASS nor this draft closes the arc.
- Synchronize ROADMAP/RECOVER/role-mapping with T2/T4 and document incident release, operator cost and diagnostic limits. Reuse existing docs/events; no new standing approval registry or parallel status ledger.
- Prepare, but do not execute, the section 6 rollout/recovery checklist. Record exact candidate code/interpreter, old-process disposition, guard locations and state schema compatibility. Snapshot/incident adoption and rollback must receive a separate reviewed operational procedure if live state exists.

**Gate:** V6; incomplete or unsupported evidence stays explicit. Code completion can be reported separately from deployment and demonstrated disaster recovery.

## 4. Obligation map and failure tests

- **E1:** T3 strict empty-changed-set release oracle; V4 stale-vector negative control and releasable control. Pinned-backend proof precedes the remainder of T3 implementation, not merely final acceptance; it is not presumed from installed Python fields.
- **E2:** T3 immutable preservation manifest before replacement; V3 termination/retry and no-overwrite checks.
- **E3:** T4 same admitted store and actual lock hierarchy; V5 forced competing mutations and multi-file completion.
- **E4:** direction-level review complete; T2 is the concrete B-E4.1 owner-disposition request. O-E4.a/b/d land in T2/T4; O-E4.e in synchronized docs; O-E4.c remains outside the arc.
- **E5:** T3 contains every restore, even clean; T5 explains the operational cost. Repeated incidents, continued OOM/native faults or proposed watch resumption trigger owner reassessment; no “normal” rate is assumed from historical zero restores.
- **E6:** T3 restricts crossing to the existing incident-bound routine; V3 rejects arbitrary write/target/source substitution.
- **E7:** T1 finding revision/digest plus T3 durable disposition-before-removal; V4 stale proof, partial event append and interrupted release checks.

## 5. Review and evidence limits

This draft specifies evidence to be collected later. Nothing here is a runtime PASS. Assertions must be checked outside the helper under test: fixture bytes/rows, independent event reduction, named process exit and observed lock exclusion. A mocked invocation, a clean count alone, a production header counter or a silent skipped test is insufficient.

Confidence in planning judgments, not incident probabilities: existing-boundary decomposition **85%**; actual shared-lease → governed → native order **95%** from source, with complete nested-call proof still due; the strict watermark oracle being implementable without broader backend work **70%**; the new drive being a useful image destination **90%** from capacity, with usability/custody unproven. The lowest-confidence item is an explicit T3 acceptance stop, not a promise to solve it by weakening release.

## 6. Recovery resources and future operational entry

Ryan reported an empty external ext4 drive at `/run/media/lauer/ext-ex4-1T-NVMe/`. Read-only mount/capacity inspection on 2026-10-11 found `/dev/sdc1`, UUID `cce6ae9a-b6ce-49da-8dd9-feb94b817777`, ext4, mounted rw, with **933,322,379,264 bytes available** of 983,349,346,304 filesystem bytes. Emptiness is Ryan-reported; capacity is observed. Device names/mountpoints can change: recheck UUID, mount identity and free space at each later operation, and refuse an unmounted directory fallback.

**Proposed use:** a fresh offline Rescuezilla image on this additional drive, preserving the September 16 pre-incident image on its existing drive. This removes the earlier need to fit both images on the nearly full old destination. It does not create or qualify a recovery point, verify the new medium, establish offsite custody, rotate the Restic repository or authorize any drive write. Size the actual image plus headroom before capture; do not infer a fixed image size or delete an older copy to fit it. No formatting, partitioning, initialization or retention change is part of this plan.

Keep backup media separate from destructive drill targets. Do not restore the whole image onto the disk holding its only copy. A later scratch ConvMem restore may use a separately approved bounded target with capacity reserved for retained backups; mere free space is not an allocation grant.

Before any separately authorized live rollout or corpus-affecting operation:

1. Ryan sets the acceptable lost-work interval for routine operation and planned maintenance; **OPEN**. Confirm new image completion, exact artifact/scope/destination, independent key access and physical custody; **OPEN**. Mounted external media is not automatically offsite.
2. Qualify the chosen exact artifact for the claimed scope under a separate drill grant: accessible off-machine software/config/source/key dependencies, repository/image checks, isolated restoration, structural/SQLite validation, vector/content checks and representative semantic probes. Record exclusions and an accepted loss window. Access alone, ID census alone or samples from other artifacts do not prove this artifact usable.
3. Pin the rollout candidate and interpreter; reconcile all CLI/watch/MCP/script/backup-service code roots and running processes. Preserve stopped services as stopped. Explicitly contain incidental and unguarded writers during maintenance; an application flock or quarantine is not a global freeze.
4. Inspect legacy/canonical guard locations and schema state before any adoption. Retain original incident/evidence bytes. If old processes could overwrite a new marker or clear it unchecked, deployment is blocked until their disposition is explicit. No automatic migration on first ordinary write.
5. Use the exact reviewed deployment grant and recovery evidence. An older-code rollback must not ignore new incidents; retain process-level containment and evidence until compatibility is proved. A detector-only deployment remains separate and does not start watch.

These are operational prerequisites to be completed later, not additional implementation tasks or granted actions. The Hybrid capture-consistency audit remains open. A recent Rescuezilla image can support planned maintenance; it does not establish live Restic capture consistency or continuous recovery coverage.

## 7. VERIFY companion and review record

Companion: [VERIFY-safe-harbor.md](VERIFY-safe-harbor.md), **stub, evidence not run**, based on [VERIFY-TEMPLATE.md](VERIFY-TEMPLATE.md). It names V0–V6 and must be filled against the actual implementation revision under later execution/verification authorization.

Next: obtain the still-open v2-owner disposition of T2, then Ryan accepts/rejects the reviewed plan at `dca13a5` and separately names any task grant. The first review and A1/A2 delta are complete; this status-only record does not create another review round. O-E4.e's existing-gate wording is satisfied plan-side. Section 2 still requires B-E4.1 before plan acceptance; this record does not defer that gate until T2 implementation. No review agent is invoked by this document.

### Kiro execution review and advisory disposition

Ryan relayed Kiro's first governing execution-plan **PASS (85%)** at `00c69d2272e027b51bc1939d2817904ca14d653d`. Kiro accepted T3's conservatively gated release approach (80%), T4's uncertain-completion contract (85%), T2's plan-side interface proposal (82%) and E1–E7 coverage (85%). **O-E4.e is satisfied plan-side (90%)**: approval recovery is a named consumer of the existing gate, not a parallel mechanism. No plan defect blocked that PASS. Backend demonstration, runtime evidence and every operational grant remain unperformed. B-E4.1 remains open: Kiro explicitly lacked v2-owner authority and granted no detailed resolver change.

- **A1 incorporated:** T3 now has an explicit proof-before-remaining-implementation ordering gate, with refusal and releasable controls. The earlier acceptance stop alone did not unambiguously establish that order.
- **A2 incorporated:** T4 explicitly requires file fsync plus directory durability on creation, and V4/V5 name parent-directory publication/failure assertions. This clarifies the existing durability contract.
- **A3 retained:** VERIFY remains NOT RUN; exact implementation-tip external review stays required. No evidence is manufactured by this planning update.

**Delta verdict:** Ryan relayed Kiro's bounded **PASS (88%)** for successor `dca13a59a2edf649ac6a19777f572645bea8674e`, compared with `00c69d2`. A1 and A2 are satisfied (90% each), all gates/NOT-RUN labels remain intact (95%), and Kiro confirmed the source qualification below (92%). No regression or required correction was found. The optional implementation-time reminder about malformed event tails is already covered by T4/V5's fail-closed reader/retry requirements; it adds no plan change or review gate. Backend and power-loss semantics remain unproven. Kiro again explicitly left B-E4.1 open and claimed no v2-owner authority.

**Source qualification (Codex, static):** the review's opening describes deployed/planning `audit()` publication as under the lock. At P, `chroma_write_guard.py:806-808` holds the lock for validation/census, but result classification/publication at `:813-827` is outside it. D has no `audit()` method; this is detector code present in P. The `recover()` pre-lock check at P `:847-849` is correctly identified. T1 already requires under-lock incident publication/rechecking. It need not turn `audit.json` into incident history: that file may remain latest-observation telemetry while `QUARANTINE.json` retains every unresolved finding. These factual qualifications preserve Kiro's reported verdict without adopting inaccurate evidence claims or changing direction.

### Next: v2 owner decision

The A1/A2 delta assignment is complete. Do not rerun either completed review for this metadata-only verdict record. A substantive later contract change or concrete new evidence would need appropriately scoped review.

Separately, the Complete-data Backup v2 owner must disposition **the unchanged T2 B-E4.1 proposal**: in-resolver exact-time future rejection, code 25 plus machine-readable reason, no concealment through ensure's auto-backup/dry-run/fallback, refreshed post-backup evaluation time, all five consumer outcomes, and unchanged profile/path/lineage/restore semantics. If reviewer authority is absent, return the named outstanding owner decision; do not repeat compatibility review and call it owner approval. Ryan must identify/grant the authorized v2 decision-maker or explicitly make the decision. No ownership transfer is inferred. Static files/Git only; no ConvMem CLI/MCP, indexing, tests, probes, implementation or live operations.

### Review focus for this new artifact

**Completed assignment; reference only — do not rerun.** The author corrected T4's failure-implies-APPROVAL_STARTED promise after the first draft at `ee29075d0315f11286e330df58a470c19ed21dc8`. The following first execution-review prompt produced Kiro's PASS at `00c69d2`; the A1/A2 delta also passed at `dca13a5`. Only the owner decision and acceptance/grants remain, as specified above.

```text
Arc: Safe Harbor. Kiro governing execution-plan review, static/read-only.

TARGET: The exact plan commit Ryan supplies with this prompt, on
plan/2026-10-11-safe-harbor. Record its full SHA before reading. Use git show
at that revision throughout; do not substitute a moving branch or live tree.

Read EXECUTION-safe-harbor.md, VERIFY-safe-harbor.md and STATUS-safe-harbor.md
under docs/plans, the approved architecture and its E1–E7/E4 record, and
docs/inter-model/DECISION-REVIEW-GUARDRAILS.md. Verify disputed source claims
against the plan's pinned D/P revisions; label deployed versus planning code.

Direction is approved at 5ea16a6; E4 compatibility PASS is complete without
ownership transfer. Neither verdict approves this execution plan or B-E4.1's
detailed v2 change. No implementation evidence exists; VERIFY is NOT RUN.

Prioritize:
1. T3 release correctness: can the active backend establish the proposed
   source-watermark/empty-changed-set proof, including update/delete/re-upsert,
   queue purge and restart? Could stale vectors pass, or could the predicate
   make ordinary release unattainable? Decide whether the early backend proof
   must precede the rest of T3. Check preservation, all unresolved findings,
   fresh owner disposition and append/unlink crash windows together. Do not
   substitute ID census for content freshness or claim static reads prove it.
2. T4 uncertain completion: an APPROVED append can take effect before failure
   returns. Challenge the corrected reread/reduction, durability and idempotent
   retry contract. Cover absent, partial, complete-but-fsync-failed and durable-
   but-unacknowledged records; verify no blind replay, duplicate approval,
   success with missing export, or automatic log truncation. Check real lock
   order and whether the scope remains within existing recovery authority.
3. T2 v2 decisions: disposition B-E4.1 separately from the plan verdict.
   Challenge exact-time future rejection, code 25/reason propagation, preventing
   auto-backup/fallback concealment, post-backup clock refresh, and all five
   consumers. Probe eligibility remains unchecked; local FAIL and offsite WARN
   are intentional distinct claims. Check target/profile/affected-path binding,
   production skip refusal and unchanged lineage/profile/restore contracts.
   Resolve O-E4.e: approval recovery consumes the approved existing gate; it is
   not a new parallel mechanism. Do not silently change the approved scope.

Review the remaining task boundaries/E1–E7 coverage for concrete omissions;
do not reopen settled direction without evidence. Distinguish a missing plan
contract from proof properly scheduled for implementation. The new ext4 drive
is capacity only; no recovery qualification or loss window is assumed.

Return: exact-revision PASS/FAIL with confidence percentages in conclusions;
blockers separated from advisories, each with file/line, a failure scenario,
local/interface/architectural classification and smallest correction; explicit
B-E4.1 owner disposition (or named outstanding owner decision); O-E4.e verdict;
unverified claims and next authorized lane. If you lack v2-owner authority,
do not turn compatibility approval into that owner's disposition.

No ConvMem CLI/MCP/session ritual or indexing (reads can write), tests, probes,
edits, restores, backups, drive/service operations, implementation or merge.
Use static files/git only. This review authorizes no execution. A rejection
routes to Ryan before Codex revises. Any follow-up review should be a delta
on findings and changed contracts, preserving unresolved safety gates.
```

## TL;DR

[Arc Safe Harbor] Kiro passed the successor plan at `dca13a5` (88%); first review and A1/A2 delta are complete. The unchanged T2 proposal still needs v2-owner disposition before Ryan accepts the plan. All evidence is unrun; implementation and live operations remain separately gated. This verdict/routing update changes no reviewed task contract.

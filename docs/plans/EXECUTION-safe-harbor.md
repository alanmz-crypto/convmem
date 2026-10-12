# Execution Plan — Safe Harbor

> **Arc: Safe Harbor. T1 MERGED; T2 IMPLEMENTATION DELIVERED, V2 NOT ACCEPTED.** Ryan accepted the plan/B-E4.1 at `dca13a5`, including all five consumer outcomes. T1 landed via PR #387 (`05aa2c8`). Section 9 preserves the T2 grant and dispatch workspace; [STATUS](STATUS-safe-harbor.md) and [VERIFY V2](VERIFY-safe-harbor.md#v2--target-binding-and-freshness-t2) hold the delivered candidate, captured isolated evidence and open event-only completion limitation. External final-tip review and Ryan acceptance remain pending. Ownership and reviewed contracts are unchanged. T3–T5 and live operations remain ungranted.

## 1. Source, authority and goal

**Source:** Ryan's instruction: “Authorize Codex to draft the Safe Harbor execution plan. Implementation and live operations remain pending.” The direction is [ARCHITECTURE-safe-harbor.md](ARCHITECTURE-safe-harbor.md), approved at `5ea16a6c7af7900b981d19eb03b168d77f611718`, including owner disposition after every automatic segment restore. Kiro's full-scope E4 PASS (85%) is recorded in architecture section 10; backup ownership stays with Complete-data Backup v2.

**Goal:** Make the existing recovery preflight and guarded incident lifecycle fail conservatively, retain original evidence across interruption, and require current proof plus owner disposition before writers resume.

```text
Planning Status
Phase:        T2 implementation/evidence delivered; V2 acceptance pending
Characters:   Task Decomposer, Dependency Mapper, Scope Guardian
Function:     Planner
Lanes:        Cursor implemented T2; Codex collected evidence; Ryan routes review
Authority:    Plan/B-E4.1 accepted; T1 completed; Ryan granted isolated T2 (section 9)
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

Reviewed acceptance requirements (Ryan's disposition is recorded in section 7; a separate task grant remains required):

1. Kiro reviews this exact plan and its E1–E7 mapping. A rejection routes to Ryan under the planning guide; Codex does not self-authorize revision or execution.
2. Complete-data Backup v2's owner explicitly dispositions the concrete B-E4.1 proposal in T2, including consumer outcomes and profile compatibility. E4 direction PASS is already complete; it is not approval of this detailed change.
3. Resolve O-E4.e's wording against the approved existing-preflight coverage. This plan uses the existing Restic gate for approval recovery. It adds a named consumer, not an independent protection mechanism. If a different mechanism is intended, Ryan must decide the contract change.
4. Ryan accepts the plan revision and separately names any task to execute. Operational recovery inputs in section 6 are required before live rollout, not before drafting or hermetic implementation.

## 3. Five bounded tasks

T1 is merged and its grants in section 8 are complete. T2 is **GRANTED / NOT STARTED** under section 9; T3–T5 remain **NOT STARTED / NOT GRANTED**. Execution lane: Cursor. Shared files make implementation serial by default: **T1 → T2 → T3 → T4 → T5**. This does not grant parallel working-tree edits. The task contracts below retain their reviewed wording; the owner grants and bounded handoffs are recorded separately.

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

**B-E4.1 contract — approved by Ryan as owner at `dca13a5`; implementation pending:** keep freshness policy inside v2's resolver. Current-day eligibility requires today's local date; a snapshot timestamp later than the captured evaluation instant is reported as suspicious future time, not accepted or silently corrected by taking another backup. Carry a machine-readable freshness reason through the existing `ResolverError`/`WorkflowOutcome`, using existing `EXIT_STALE=25`; no new numeric exit namespace. Old stale dates retain the current snapshot-if-stale behavior. Future-time errors are excluded from ensure's backupable cases at `backup_workflows.py:197-228`, including dry-run success. No fallback to an older/legacy candidate hides the suspicious result.

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

Companion: [VERIFY-safe-harbor.md](VERIFY-safe-harbor.md), based on [VERIFY-TEMPLATE.md](VERIFY-TEMPLATE.md). It retains historical V1 results and records final T1 correction/integration evidence, CI, review, owner acceptance and merge; V2–V6 remain unrun. Evidence must identify its actual implementation revision.

Next: Cursor implements T2 under section 9 and records isolated V2 evidence. The plan reviews and B-E4.1 owner disposition are already complete; do not request them again. Section 8 preserves completed T1 grants and VERIFY preserves its exact-tip outage acceptance. That acceptance does not waive T2's own final-tip review gate or authorize live operations.

### Kiro execution review and advisory disposition

Ryan relayed Kiro's first governing execution-plan **PASS (85%)** at `00c69d2272e027b51bc1939d2817904ca14d653d`. Kiro accepted T3's conservatively gated release approach (80%), T4's uncertain-completion contract (85%), T2's plan-side interface proposal (82%) and E1–E7 coverage (85%). **O-E4.e is satisfied plan-side (90%)**: approval recovery is a named consumer of the existing gate, not a parallel mechanism. No plan defect blocked that PASS. Backend demonstration, runtime evidence and every operational grant remain unperformed. At that review, B-E4.1 stayed open: Kiro explicitly lacked v2-owner authority and granted no detailed resolver change; Ryan's subsequent approval is recorded below.

- **A1 incorporated:** T3 now has an explicit proof-before-remaining-implementation ordering gate, with refusal and releasable controls. The earlier acceptance stop alone did not unambiguously establish that order.
- **A2 incorporated:** T4 explicitly requires file fsync plus directory durability on creation, and V4/V5 name parent-directory publication/failure assertions. This clarifies the existing durability contract.
- **A3 retained:** VERIFY remains NOT RUN; exact implementation-tip external review stays required. No evidence is manufactured by this planning update.

**Delta verdict:** Ryan relayed Kiro's bounded **PASS (88%)** for successor `dca13a59a2edf649ac6a19777f572645bea8674e`, compared with `00c69d2`. A1 and A2 are satisfied (90% each), all gates/NOT-RUN labels remain intact (95%), and Kiro confirmed the source qualification below (92%). No regression or required correction was found. The optional implementation-time reminder about malformed event tails is already covered by T4/V5's fail-closed reader/retry requirements; it adds no plan change or review gate. Backend and power-loss semantics remain unproven. Kiro again explicitly left B-E4.1 open and claimed no v2-owner authority.

**Source qualification (Codex, static):** the review's opening describes deployed/planning `audit()` publication as under the lock. At P, `chroma_write_guard.py:806-808` holds the lock for validation/census, but result classification/publication at `:813-827` is outside it. D has no `audit()` method; this is detector code present in P. The `recover()` pre-lock check at P `:847-849` is correctly identified. T1 already requires under-lock incident publication/rechecking. It need not turn `audit.json` into incident history: that file may remain latest-observation telemetry while `QUARANTINE.json` retains every unresolved finding. These factual qualifications preserve Kiro's reported verdict without adopting inaccurate evidence claims or changing direction.

### Owner approval and next authorized step

The A1/A2 delta assignment is complete. Do not rerun either completed review for this metadata-only verdict record. A substantive later contract change or concrete new evidence would need appropriately scoped review.

**Ryan's explicit approval, 2026-10-11:**

> As owner, I approve B-E4.1 exactly as specified in T2 of the Safe Harbor execution plan at dca13a59a2edf649ac6a19777f572645bea8674e, including all five consumer outcomes. I accept that execution plan. Ownership remains unchanged. Implementation and live operations remain pending.

This closed B-E4.1's owner-decision prerequisite and accepted the exact reviewed plan. Complete-data Backup v2 retains its interfaces; no ownership transfer, Hybrid-audit closure or Recovery Authority grant follows. T2's future-time policy and all five consumer outcomes are unchanged. At that approval, all tasks were NOT STARTED and VERIFY was NOT RUN; section 8 and STATUS describe the subsequent T1 candidate and correction grant.

**Acceptance scope:** that acceptance alone granted no implementation or operation. Ryan subsequently granted the proposed T1 implementation; section 8 records its exact limits. Operational recovery qualification and the lost-work interval remain open before live rollout.

### Review focus for this new artifact

**Completed assignment; reference only — do not rerun.** The author corrected T4's failure-implies-APPROVAL_STARTED promise after the first draft at `ee29075d0315f11286e330df58a470c19ed21dc8`. The following first execution-review prompt produced Kiro's PASS at `00c69d2`; the A1/A2 delta also passed at `dca13a5`. Ryan subsequently approved B-E4.1, accepted that plan and granted only T1 below. Other implementation/live grants remain pending.

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

## 8. Cursor T1 Execute handoff

**Completed — historical grant, not a new dispatch.** T1 is merged. See [STATUS](STATUS-safe-harbor.md) for the next authorized boundary and [final evidence](VERIFY-safe-harbor.md#final-tip-ci-review-and-owner-acceptance) for the review/merge mapping.

**Date / author / recipient:** 2026-10-11; Codex planning lane; Cursor implementation lane. This section is the bounded handoff in the existing plan, not a new handoff ledger.

**Authority:** Ryan replied “granted” to the proposed next step, “A separate implementation grant, with T1 proposed first,” with Cursor named as the downstream lane. That authorizes **T1 only: isolated implementation and its specified V1 evidence**, against the accepted plan at `dca13a59a2edf649ac6a19777f572645bea8674e`. It does not grant T2–T5, production operations, merge, PR creation/commenting or the PR Steward role. No further T1 approval is needed merely to begin the granted scope.

### Delivery state and historical workspace

- State: **MERGED**, PR #387 at `05aa2c86e2d01c9a9f5259b1f505833d7f28563d`. Final candidate `0c7b4e263dff12f8e1a6b2d485616153ed096b66` passed fresh CI and Copilot's integration delta (82%, static); Ryan accepted the exact-tip BugBot outage exception. The squash tree is identical to the candidate.
- Historical branch/worktree: `fix/2026-10-11-safe-harbor-t1`, `/home/lauer/Projects/convmem/.worktrees/fix-2026-10-11-safe-harbor-t1`. Original grant base: `b4c0e73`; T1 runtime corrections: `496792f`; test corrections: `8b41044`; main `5550def` integration: `c624e2f`. These are provenance, not a resume instruction.
- The original grant and bounded extensions below are complete. Do not resume them to start T2, switch the shared checkout, alter runtime-main, publish PR comments or deploy. The separate T2 grant is now recorded in section 9; this historical T1 grant is not its authority.

### Build only the accepted T1 deliverable

Read STATUS, sections 2–3/T1 of this plan, VERIFY V0/V1, the approved architecture's incident contract, `docs/planning/EXECUTE-TASK.md`, and the applicable lane/builder guidance. State Goal / role / system / next action and the Execute phase before editing.

Implement the T1 contract in section 3 without redesigning it: complete unresolved incident retention in the existing authority; malformed/unknown/legacy state refusal; canonical guard identity and alias-conflict refusal; under-lock audit incident publication; post-lock quarantine rechecks; honest containment-publication failures; ordinary clear refusal until T3 exists. Keep `audit.json` as observation telemetry, not a second admission authority. T1 is intentionally not a deployable validated-release workflow.

Production-source scope is `chroma_write_guard.py`, T1 guard/audit checks in `doctor.py`, and status/clear handling in `scripts/chroma_guard.py`, plus `chroma_store.py` solely for canonical client/cache identity under Ryan's correction below. Focused tests may extend `tests/test_chroma_write_guard.py`, `tests/_chroma_write_guard_worker.py`, the relevant isolated doctor tests and `tests/test_safe_harbor_t1.py`. Evidence/status updates belong in the existing Safe Harbor VERIFY/STATUS and routing files. Return any further production-file dependency to Codex/Ryan before expanding scope.

No T2 gate/freshness changes, T3 preservation/restore/release implementation or backend campaign, T4 approval recovery, T5-wide campaign, generic HOLD/registry, live migration or cleanup. Do not use the task to update shared permissions, generated surfaces, installed config, backup units or unrelated branches.

### Bounded T1 correction — owner authorized

Ryan's subsequent instruction, recorded verbatim:

> Authorize a bounded T1 correction, including chroma_store.py solely for canonical client/cache identity and its isolated regression evidence. Reject persisted empty incident sets and exercise the actual overwrite negative control. All other scope limits remain unchanged.

This closes the file-list mismatch in the original handoff: Codex required canonical store/cache identity but omitted the store construction surface. Cursor may now make that narrowly scoped change without another start approval. This is a T1 correction, not acceptance of the initial candidate or a grant for a later task.

1. **Canonical client/cache identity:** align the actual Chroma client/store identity with the canonical guard/load-record identity. Exercise real store construction through canonical and alias paths in isolation. Include the regression in which an alias client could refresh shared bookkeeping while an older client remains stale; prove coherent client identity or the existing conservative reload/refusal behavior. Preserve competing-legacy-location refusal. No global collection-creation/default change, new identity registry or live migration.
2. **Persisted empty incident sets:** reject a present, correctly shaped marker whose incident set is empty. Replace the current test that requires non-blocking `clear` with fresh-process admission refusal and no requested fixture mutation. Keep the missing-marker control valid. No release path is added.
3. **Actual overwrite negative control:** use the same A-then-B publication/admission workflow with an isolated deliberately faulty publisher that replaces the unresolved set with only the newer finding. The retention assertion must fail for the intended loss of A, while the corrected implementation passes. Feeding a fabricated/truncated result directly into an assertion is insufficient. Restore the real implementation; no faulty runtime behavior may remain in the candidate.

Correct and rerun the relevant isolated V1 evidence. Preserve the initial 41-test run as historical evidence, not acceptance of these gaps; record the corrected subject SHA, commands, outcomes and expected failing control separately. Stop for the existing exact-tip review/owner acceptance gate after pushing the correction. All original isolation and authority limits below remain in force.

### Bounded review-evidence correction — owner authorized

Ryan instructed **"correct both before merging"** after Codex identified the two concrete test-evidence gaps in Copilot's static review of `677c8a0d17618166c454b4523d6767e48cfa330a`. Copilot's verdict was PASS at 72% confidence with advisories; Codex recommended these two corrections before merge, and Ryan accepted that recommendation. This grants Cursor the corrections and their isolated regression evidence. It grants no merge and does not accept the alternative review in place of the BugBot gate.

**Allowed edits:** `tests/test_safe_harbor_t1.py`; `tests/_chroma_write_guard_worker.py` only if needed for isolated process synchronization; the existing Safe Harbor VERIFY/STATUS and LATEST routing. No production code, CI workflow, inventory algorithm/artifact or additional review finding is in this correction's scope. Return a genuine dependency outside this list before expanding it.

1. **Keep fixture isolation across fault-injection cleanup.** The shared `monkeypatch.undo()` calls in `test_publication_failure_aborts_before_mutation` also undo the autouse fixture's HOME/XDG/CONVMEM settings and provider-key removal. Give each injection its own patch context or restore only the affected method. Assert that the fixture's isolated environment remains intact before every subsequent project call, including the short-write and directory-fsync cases. Keep standard-pytest operation with no external isolation flag and preserve production-path refusal. Do not weaken or skip the fault cases.
2. **Prove audit/writer lock contention deterministically.** The existing test launches the writer and immediately releases the audit; it does not establish that the writer reached the native lock while the audit held it. Use bounded process synchronization and test-only instrumentation to demonstrate an actual failed nonblocking acquisition of that same lock while the audit is paused. Only then release the audit to publish. Assert that the writer subsequently refuses admission and its requested record is absent. Include an isolated missing-lock/order negative control that fails the relevant proof assertion, not merely a process-start timeout. No sleep-based inference, unbounded waits, or new production barrier hooks. Clean up child processes on every outcome.

**Evidence:** inspect the fixture first, then run the affected tests plus the existing isolated T1/guard regressions under the dedicated worktree interpreter. A standard-pytest check must not require a pre-set `CONVMEM_T1_ISOLATED`. Record commands, exit codes, the observed contention signal, expected negative-control failure and the exact code revision; preserve earlier results as historical. Ordinary GitHub CI will run on the pushed successor. Do not launch the production/default local suite, doctor, MCP, indexing, Restic, providers, services or external-drive operations.

**Finish:** commit and push the bounded correction, keep the PR a draft, and report the successor SHA and evidence. A focused independent delta review checks these two corrections and regressions at that successor; historical CI/review results do not transfer automatically. The BugBot outage gate remains unsatisfied until matching review evidence or Ryan's written exact-tip outage acceptance. No review comment, merge, deployment or T2–T5 work is authorized by this grant.

### Isolation and evidence

#### Bounded branch update — owner authorized

Ryan's subsequent instruction: **"authorized: Authorize the bounded branch update, then obtain fresh CI and resolve the final-tip review gate."** This supersedes the earlier correction's inventory-edit exclusion only for the mechanical integration described here. It does not authorize merging PR #387 into main, deployment or T2–T5.

- Resume the clean, pushed T1 worktree from the documentation commit containing this grant. Prior implementation subject: `2977c4531cf446974b0c86994dbca757715dca76`. Merge pinned base `5550def70c72bc7a60f0c5216b46cd4cf629f5d2` (main's PR #388) into this feature branch, preserving history; no rebase or force-push. Recheck remote base and branch first; report a material new base change before expanding this integration.
- Resolve `docs/inter-model/LATEST.md` by preserving both arcs' current routing. Regenerate `docs/plans/R2B-V2-WRITER-COVERAGE-INVENTORY.json` using its existing generator on the integrated tree. Do not hand-edit identity values, alter the identity algorithm or route policy, or activate PR #388's disabled feature. Inspect automatic source merges, especially `doctor.py`, against both parents for lost T1 or main behavior. Unexpected semantic conflict returns to Codex/Ryan.
- Permitted accompanying edits: existing Safe Harbor EXECUTION/STATUS/VERIFY and LATEST, for this grant, prior delta verdict and integrated evidence. No new runtime behavior or unrelated finding fix. Keep the two corrected tests intact. Run the previously isolated T1/guard/R2b regression set and relevant lint/inventory checks after inspecting their isolation. No production CLI/MCP, indexing, provider, Restic, service, drive or full default local suite.
- Commit/push the integrated candidate with the existing explicit branch refspec; record exact base/code tip, resolved files, generator identity and observed results. Correct the stale execution state. Complete evidence edits before handing the final tip to review; do not keep moving the reviewed subject merely to record review status.
- Codex will watch fresh GitHub CI to completion, inspect any real failure and obtain a focused Copilot integration delta review at the final tip. No new PR comment or BugBot trigger is inferred. The two quota failures reviewed no SHA; Copilot remains independent evidence. If the BugBot outage persists, prepare the concrete final-SHA acceptance for Ryan under EXECUTE-TASK's outage rule rather than falsely marking the gate passed. Keep PR #387 a draft.

This is a branch-maintenance and validation grant, not an architecture change, T1 acceptance, PR merge or live-operation grant.

The grant permits the accepted T1 fixture tests, subprocess/restart/concurrency cases and fault/negative controls. Before importing project code, isolate all configuration, data roots, user-directory lookups, providers and subprocess paths; refuse production paths. Read the harness and fixtures before running them. Use the worktree interpreter/source explicitly, not the installed ConvMem launcher. No production CLI/MCP startup ritual, doctor, session indexing, Restic command, provider call or drive/service action is authorized; routine protocol defaults cannot enlarge this isolated task.

Required V1 evidence:

1. Incident A then B, including two findings in one segment: fresh-process admission remains refused and all findings survive. The old overwrite implementation must fail the assertion.
2. Missing marker versus null/scalar/empty/unknown-schema/invalid/legacy marker and read failure: only genuinely missing is absent; preserve recognized legacy bytes, refuse unknown state.
3. Canonical aliases select one guard identity; competing legacy locations refuse rather than create a fresh empty authority.
4. Audit FAIL followed by PASS/skipped/error cannot erase incidents. Gather all findings before raising; barriers demonstrate publication is serialized with guarded admission.
5. `recover()` and every T1 guard entry recheck after lock acquisition. Use process barriers, not timing sleeps, to publish an incident between the early check and acquired lock.
6. Short write, publication/fsync/IO failure aborts the affected operation and reports containment unavailable without falsely promising a persistent stop. Assert fixture bytes/mutations as well as status.
7. The ordinary clear surface cannot release unresolved incidents; doctor exposes unresolved or malformed authority without mutating production state.

Record exact commands, exit status, backend/interpreter identity, subject SHA, fixture effects and negative controls in VERIFY V1. Required cases that cannot run remain explicit failures/gaps; never fill them from static review or a production health check. V2–V6 remain NOT RUN unless a case is strictly necessary T1 regression evidence, and that does not grant those tasks. Broader default tests/doctor may run only after their entire execution is shown isolated; otherwise record the limitation rather than invoking production.

### Delivery and stop

Complete the authorized implementation/evidence, commit and push, then return the exact tip/diff, V1 results, residuals and copy-ready PR description. Runtime code makes the Execute external-review gate **required**: record its fields at the implementation tip. PR-native BugBot evidence must match that tip before merge readiness; no PR/comment authority or exemption is inferred from this grant. If that next step needs Ryan's PR authorization, finish the authorized local work first, publish the candidate, then request that concrete decision. Do not post review-trigger comments without their required authority.

Stop after the bounded T1 handoff. No automatic transition to T2, broader Verify, deployment or live rollout. T1 alone cannot be deployed while old writers can overwrite its marker or clear incidents. A material scope/authority mismatch or unexpected production access stops the affected work and returns the specific evidence; do not repair production or silently amend this plan.

## 9. Cursor T2 Execute handoff — owner granted

**Date / author / recipient:** 2026-10-12; Codex planning lane; Cursor implementation lane. This is the next bounded task in the accepted plan, not a revised architecture.

**Authority:** Ryan replied **“granted”** to Codex's next step, **“Ryan's separate T2 grant, then Codex prepares Cursor's handoff.”** This grants **T2 only: implementation and isolated V2 evidence**. Ryan's earlier owner approval of B-E4.1 exactly at `dca13a59a2edf649ac6a19777f572645bea8674e`, including all five consumer outcomes, already resolves the T2 contract prerequisite. No ownership transfer, T3–T5 implementation, PR creation/comment/review trigger, merge, deployment or live operation is granted by this handoff. Do not re-request approval merely to begin the named T2 work.

### Resume state

- State **at dispatch `9664878`: NOT_STARTED / GRANTED**. Codex had prepared only this handoff and current-state records. This is historical grant context; current implementation/evidence and remaining acceptance limits are in [STATUS](STATUS-safe-harbor.md) and [VERIFY V2](VERIFY-safe-harbor.md#v2--target-binding-and-freshness-t2).
- Branch: `fix/2026-10-12-safe-harbor-t2`.
- Worktree: `/home/lauer/Projects/convmem/.worktrees/fix-2026-10-12-safe-harbor-t2`.
- Code baseline: T1 squash `05aa2c86e2d01c9a9f5259b1f505833d7f28563d`, also remote `main` when prepared. The immediate branch base `1e55af03d38c77ba5d1d405933eb2588cf597529` adds only T1 closeout documentation. The next documentation commit records this grant and is the start SHA supplied in Codex's dispatch; confirm that parentage and clean state before editing.
- The closeout docs travel with this branch; merging the separate docs branch first is not a prerequisite. Do not switch the shared checkout, reuse the completed T1 branch, or alter runtime-main. No silent rebase/merge to a later main: report a concrete integration dependency first.
- Push every commit immediately with `git push -u origin fix/2026-10-12-safe-harbor-t2:refs/heads/fix/2026-10-12-safe-harbor-t2`. No force-push or main push.

### Read and implement

Read this brief, STATUS, section 3/T2, VERIFY V2, the v2 STATUS/interface contract, `docs/planning/EXECUTE-TASK.md`, and the Ousterhout builder digest. State the arc, Goal / role / system / next action and Cursor Execute phase. The task is to make the existing preflight bind to the admitted operation, and make future-time eligibility fail honestly across its shared consumers.

**Source scope:** T2's named files: `restic_gate.py`, `restic_snapshot.py`, `backup_workflows.py`, admission portions of `chroma_write_store.py` and `convmem.py`, narrowly required lane classification in `runtime_guard.py`; focused existing tests or a self-isolating `tests/test_safe_harbor_t2.py`; the three named policy docs and narrowly relevant v2 interface documentation; existing Safe Harbor evidence/status/routing. If authorized source changes alter the committed R2b implementation identity, regenerate only its derived inventory through the existing generator under isolated configuration. Do not hand-edit hashes, change the identity algorithm/route policy or add a new writer route. A further production-file dependency must be returned with its concrete call chain before editing outside this scope.

Keep the reviewed section 3/T2 contract authoritative rather than inventing a second policy. In particular:

1. Bind one resolved operation configuration under the shared writer lease to one immutable `BackupContext` before opening Chroma or logically mutating approval state. Include the actual approved-row, event and export paths; canonical Chroma equality alone is insufficient. Refuse changed inputs, mismatched profile/target or an output escaping the complete protected root. Do not treat a shared lease as protection against arbitrary same-user edits.
2. Reject the production skip even under lab-looking cwd/config/env or confirm variables. Test/lab allowance requires explicit context and canonical isolation; unknown classification refuses. Keep the existing index/plain-add exemption and `--no-index`/forget/refine scope unchanged.
3. Implement the approved future-time rule inside the existing resolver, using code 25 plus a reason; no caller-only alternative rule. One evaluation instant per resolution, fresh post-backup resolution and day-boundary handling are required. Future errors cannot become a backup, successful dry-run or fallback to an older/legacy source.
4. Cover all five outcomes exactly as section 3 specifies: live ensure/write refusal; probe eligibility unchecked (retain its existing reachability semantics); local health FAIL; offsite health WARN; offsite copy refusal before copy. Preserve existing numeric errors, exact-path/profile/tag rules, destination lineage and legacy/v2/v3 consumer compatibility; activate no profile and alter no restore-state classification.
5. Wire the existing gate for the named CLI consumers, including approval recovery before logical mutation and event-only completion. Preserve binding through the downstream helpers. Do not add a parallel recovery gate, or silently exempt a recovery branch. Only a demonstrated nonmutating already-complete return can omit it. Update ROADMAP/RECOVER/role-mapping consistently.

**T2/T4 seam:** T2 supplies the bound preflight and admission integration above; T4 remains responsible for unknown/absent/tombstone classification, serialized state recheck, completion uncertainty, export completion and retry. At the pinned baseline, `recover_approval()` is in `propose_decision.py` and its ingestion helper reopens the production store; inspect this existing chain rather than declaring CLI wiring sufficient. Do not rewrite T4's recovery state machine under T2. If T2's configuration/caller binding cannot be achieved within the listed admission surfaces, return the smallest demonstrated file/interface dependency to Codex/Ryan; do not weaken the binding or claim the direct-caller/T4 proof complete. T4's remaining evidence must stay explicitly outstanding.

### Isolated evidence, not production experiments

- No production CLI/MCP/doctor/session-start ritual or session indexing. No real corpus, config, password, Restic repo/cache, external drive, service, provider or installed-runtime access. This task restriction overrides the general session-start/Track A instructions. Fixtures may use a fake Restic boundary, or a local scratch Restic repository/password/cache confined to the test's temporary root; never inherit a live destination or credential.
- Inspect import-time path constants and subprocess environments before running any project code. Establish temporary HOME/XDG/CONVMEM_CONFIG/CONVMEM_ROOT and Restic settings before imports; scrub provider credentials. Child processes inherit the isolation. Tests must isolate themselves under ordinary pytest without requiring a pre-set escape flag or skipping when it is absent. Do not copy T1's former shared `monkeypatch.undo()` defect.
- V2 must exercise actual named caller effects: failed admission leaves fixture Chroma logical content, approved rows, events and exports unchanged; successful controls reach the intended fixture mutation. For the no-op-gate negative control, disable the real preflight on the same workflow and demonstrate that a forbidden mutation causes the unchanged-state assertion to fail. Invocation-only mocks are not that proof.
- Cover wrong corpus/profile, exported symlink escape, config substitution, prod skip spoofing and allowed isolated exception; same-day future and next-day future; old/missing source; timezone/day rollover and post-backup time refresh; all five consumer severities/reasons and no future-triggered backup/copy/dry-run success. Preserve supported resolver profiles/lineage and unrelated gate exemptions.
- Start with the relevant Restic/workflow/gate/runtime-guard tests and focused fixture caller coverage; inspect their isolation before running them. Re-run relevant T1 regressions if admission changes can affect it. Use ordinary-user permissions for chmod-based cases. Do not run the full default local suite unless its isolation is established and separately authorized; do not weaken an unrelated test or change CI to hide a failure.
- Record commands, interpreter/backend versions, exit codes, positive and intentionally failing controls, code SHA and final evidence SHA in VERIFY V2. Distinguish mocked boundary evidence, scratch Restic evidence and unrun T4 proof. Process restart tests are not power-loss proof; snapshot eligibility is not demonstrated recoverability.

### Delivery and stop

Commit and push the scoped implementation/evidence, leaving the shared checkout and deployed runtime untouched. Update STATUS sections 3–6 to the actual result, VERIFY V2 and the LATEST pointer; retain T1 provenance and leave V3–V6 unrun. Report the branch, clean/push state, `git log origin/main..HEAD --oneline`, runtime/final SHA, residuals, and a copy-ready PR title/body.

The required final-tip external review is separate from implementation evidence. Ryan's Copilot/BugBot outage exception covered T1 candidate `0c7b4e2` only; it does not automatically cover T2. No PR creation, trigger/comment or reviewer invocation is granted here. Hand off the concrete candidate for that step; do not label it merge-ready before the required review/acceptance. Stop after T2—no T3 backend experiment, repair/release work, T4 state-machine change or live action.

### Subsequent T2 review authorization and outcome

Ryan authorized **“final-tip review, including the documented evidence limitation.”** Copilot's independent static review at `05c7706e54b77f9ef5b41a1c206b29bec012e405` returned narrow FAIL (75%) for B1, the recovery admission label missing from the census allowlist; Codex confirmed the source chain. [VERIFY V2](VERIFY-safe-harbor.md#independent-final-tip-review--correction-required) records the findings and the proposed correction. Copilot classifies the event-only success gap as a bounded T4 prerequisite, with an explicit Ryan decision needed before accepting that exclusion from V2. Neither a correction grant nor that acceptance is inferred. The reviewed contracts are unchanged. PR/comment authority, the separate BugBot gate, merge and live operations remain pending.

### B1 correction and bounded evidence exclusion — owner authorized

**Authority:** Ryan replied **“authoized: Next step: Authorize the bounded correction and decide the evidence exclusion.”** to the proposed B1 correction and documented event-only exclusion. This authorizes the bounded correction below and accepts that **T2/V2 does not demonstrate successful event-only completion**. It does not assert that completion works, waive gate-before-mutation coverage, accept the whole T2 candidate, grant T4 implementation, or satisfy the separate BugBot gate. T4 must align the proposal/ingestion hash views and demonstrate real event-only success under its later task grant.

**Cursor resume:** existing worktree `/home/lauer/Projects/convmem/.worktrees/fix-2026-10-12-safe-harbor-t2`, branch `fix/2026-10-12-safe-harbor-t2`. Review-record base is `2d4ce44572d4edb653f57ade8ccaf0896d858c0b`; begin at its clean, pushed documentation-only grant successor supplied in the dispatch. Do not switch the shared checkout, merge/rebase other branches, or touch runtime-main. State at dispatch: **NOT_STARTED / GRANTED**. Current state: **IMPLEMENTED at `964c1de`; narrow Copilot delta pending.** Evidence is in [VERIFY V2](VERIFY-safe-harbor.md#b1-correction--implemented-delta-review-pending).

**Build only B1:**

1. In `convmem.py`, reuse the existing allowlisted `propose_decision.write` entrypoint for the outer admitted recovery operation. Do not add `propose_decision.recover` to the census allowlist or change the census, writer-route or identity policy.
2. Extend the isolated T2 CLI fixture/tests (`tests/test_safe_harbor_t2.py`, narrowly `tests/_safe_harbor_t2_cli.py` if necessary) to create a valid census header bound to the fixture's actual writer gate. Exercise real `propose_decision --recover` with that census present: a current snapshot reaches successful retry-Chroma recovery and a matching APPROVED event; a future snapshot still refuses with 25 before logical/approval/export mutation. Assert real census admission evidence, not just membership in a constant set. Keep telemetry assertions distinct from corpus/event/export invariance.
3. Exercise a test-only old-label negative control through that same recovery path. It must actually hit the census refusal and fail the positive admission/recovery assertion, while the real label passes. Do not put fault-injection behavior in production code. Keep the documented event-only hash-mismatch fixture and limitation intact.
4. If the source edit changes the implementation identity, regenerate only `docs/plans/R2B-V2-WRITER-COVERAGE-INVENTORY.json` through its existing generator under isolation. Diff must be derived `code_revision`/`inventory_digest` only; Shadow inventory, route policy and the identity algorithm remain unchanged.

**Evidence:** use the existing self-isolating fixtures, ordinary uid 1000 and captured subprocess exit statuses. Establish clean temporary HOME/XDG/CONVMEM/Restic/cache roots and scrub provider credentials before project imports; children inherit isolation. Start with the new positive, future-refusal and negative-control cases, then the affected T2/caller, census and inventory regressions and lint regression gate. Record exact commands, code SHA, interpreter/backend identity, return codes and proof effects in VERIFY V2. A successful control must assert the corresponding APPROVED event, not only changed file bytes. No full default suite, production CLI/MCP/doctor, session indexing, service, actual backup repository/key or drive operation. If tool transport times out, inspect the process and output; never launch duplicate test runs blindly.

**Scope exclusions:** no other review advisory becomes an implementation task by implication. Do not edit `writer_census.py`, `propose_decision.py`, classifier/hash normalization, T3–T5, other runtime files or external configuration. No PR creation, comments, BugBot trigger, reviewer invocation, merge, deployment or live operations. Return any needed additional production-file dependency before editing it.

**Delivery:** commit and immediately push each commit with the explicit branch refspec; update existing VERIFY/STATUS/LATEST to the real result and accepted evidence exclusion. Keep the original Copilot FAIL pinned to `05c7706`; a fix alone does not dispose B1. Hand off the successor for one narrow independent delta (correction plus regressions), with source/evidence SHAs, clean/push state and residual gates. Cursor stops after delivery; Codex coordinates that narrow Copilot delta under the standing final-tip review authorization. This does not authorize PR-native trigger comments or a BugBot exception.

## TL;DR

[Arc Safe Harbor] T2 implementation and isolated evidence are delivered. Copilot's review at `05c7706` is narrow FAIL; Ryan has now authorized the bounded B1 correction and accepted the stated event-only evidence exclusion, with real success proof retained as a T4 prerequisite. The correction and its isolated evidence are delivered at `964c1de`; one narrow Copilot delta is next. The approved plan and five-consumer B-E4.1 contract are unchanged. Section 9 preserves the grant and stop. T3–T5, PR/comment/merge and live operations remain ungranted; the separate BugBot gate is unsatisfied.

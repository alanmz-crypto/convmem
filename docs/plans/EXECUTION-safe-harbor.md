# Execution Plan — Safe Harbor

> **Arc: Safe Harbor. T1–T5 / V1–V6 ACCEPTED AND MERGED through `c6f0724`.** Section 19 records the bounded read-only deployment preflight/drafting grant. [ROLLOUT](ROLLOUT-safe-harbor.md) returns findings and the conditional procedure. No deployment, service change or backup/restore operation is authorized.

## 1. Source, authority and goal

**Source:** Ryan's instruction: “Authorize Codex to draft the Safe Harbor execution plan. Implementation and live operations remain pending.” The direction is [ARCHITECTURE-safe-harbor.md](ARCHITECTURE-safe-harbor.md), approved at `5ea16a6c7af7900b981d19eb03b168d77f611718`, including owner disposition after every automatic segment restore. Kiro's full-scope E4 PASS (85%) is recorded in architecture section 10; backup ownership stays with Complete-data Backup v2.

**Goal:** Make the existing recovery preflight and guarded incident lifecycle fail conservatively, retain original evidence across interruption, and require current proof plus owner disposition before writers resume.

```text
Planning Status
Phase:        T1–T5 merged; operational procedure drafted
Characters:   Task Decomposer, Dependency Mapper, Scope Guardian
Function:     Planner
Lanes:        Codex operational drafting; Kiro later review; Ryan live gate
Authority:    Ryan read-only preflight/draft grant (section 19); no live changes
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

T1–T4 are accepted and merged. Their implementation/correction grants are complete. Ryan granted T5 integrated verification and operational handoff in section 17. Shared files keep implementation serial. The reviewed task contracts below are unchanged.

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

**B-E4.1 contract — approved by Ryan as owner at `dca13a5`; T2 implementation merged in #389:** keep freshness policy inside v2's resolver. Current-day eligibility requires today's local date; a snapshot timestamp later than the captured evaluation instant is reported as suspicious future time, not accepted or silently corrected by taking another backup. Carry a machine-readable freshness reason through the existing `ResolverError`/`WorkflowOutcome`, using existing `EXIT_STALE=25`; no new numeric exit namespace. Old stale dates retain the current snapshot-if-stale behavior. Future-time errors are excluded from ensure's backupable cases at `backup_workflows.py:197-228`, including dry-run success. No fallback to an older/legacy candidate hides the suspicious result.

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

Companion: [VERIFY-safe-harbor.md](VERIFY-safe-harbor.md). V1–V5 are owner-accepted, with exact review, hosted-CI and squash mappings. V6 has Kiro PASS and Ryan acceptance at `1cb02fbd9cc15b36c7f3f094237da071ca2dcd18`, covering the corrected test/evidence and prepared operational handoff with its documented limits.

Next: resolve the operational readiness items in [ROLLOUT](ROLLOUT-safe-harbor.md).
[VERIFY closeout](VERIFY-safe-harbor.md#t5-hosted-ci-owner-exception-and-squash-mapping)
records #394 hosted CI, Ryan's exact-tip exception and tree-identical squash.
Historical pending labels below retain their original scope; STATUS and section
19 supply current routing. No implementation acceptance authorizes deployment.

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

**Completed grant history:** T2 was accepted at `eb06c97` and merged through #389 as `458b9f6`. Pending/draft instructions below describe their historical handoff states; they do not reopen the task. Current acceptance and evidence limitations are in [VERIFY V2](VERIFY-safe-harbor.md#t2-final-tip-ci-owner-acceptance-and-squash-mapping). T3–T5 require separate grants.

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

**Cursor resume:** existing worktree `/home/lauer/Projects/convmem/.worktrees/fix-2026-10-12-safe-harbor-t2`, branch `fix/2026-10-12-safe-harbor-t2`. Review-record base is `2d4ce44572d4edb653f57ade8ccaf0896d858c0b`; begin at its clean, pushed documentation-only grant successor supplied in the dispatch. Do not switch the shared checkout, merge/rebase other branches, or touch runtime-main. State at dispatch: **NOT_STARTED / GRANTED**. Current state: **IMPLEMENTED at runtime/tests `964c1de`; Copilot delta PASS (88%) at final candidate `82f25ef`.** Original FAIL remains pinned to `05c7706`; the delta supplies no BugBot or owner acceptance. Evidence is in [VERIFY V2](VERIFY-safe-harbor.md#independent-b1-delta-review--pass).

**Build only B1:**

1. In `convmem.py`, reuse the existing allowlisted `propose_decision.write` entrypoint for the outer admitted recovery operation. Do not add `propose_decision.recover` to the census allowlist or change the census, writer-route or identity policy.
2. Extend the isolated T2 CLI fixture/tests (`tests/test_safe_harbor_t2.py`, narrowly `tests/_safe_harbor_t2_cli.py` if necessary) to create a valid census header bound to the fixture's actual writer gate. Exercise real `propose_decision --recover` with that census present: a current snapshot reaches successful retry-Chroma recovery and a matching APPROVED event; a future snapshot still refuses with 25 before logical/approval/export mutation. Assert real census admission evidence, not just membership in a constant set. Keep telemetry assertions distinct from corpus/event/export invariance.
3. Exercise a test-only old-label negative control through that same recovery path. It must actually hit the census refusal and fail the positive admission/recovery assertion, while the real label passes. Do not put fault-injection behavior in production code. Keep the documented event-only hash-mismatch fixture and limitation intact.
4. If the source edit changes the implementation identity, regenerate only `docs/plans/R2B-V2-WRITER-COVERAGE-INVENTORY.json` through its existing generator under isolation. Diff must be derived `code_revision`/`inventory_digest` only; Shadow inventory, route policy and the identity algorithm remain unchanged.

**Evidence:** use the existing self-isolating fixtures, ordinary uid 1000 and captured subprocess exit statuses. Establish clean temporary HOME/XDG/CONVMEM/Restic/cache roots and scrub provider credentials before project imports; children inherit isolation. Start with the new positive, future-refusal and negative-control cases, then the affected T2/caller, census and inventory regressions and lint regression gate. Record exact commands, code SHA, interpreter/backend identity, return codes and proof effects in VERIFY V2. A successful control must assert the corresponding APPROVED event, not only changed file bytes. No full default suite, production CLI/MCP/doctor, session indexing, service, actual backup repository/key or drive operation. If tool transport times out, inspect the process and output; never launch duplicate test runs blindly.

**Scope exclusions:** no other review advisory becomes an implementation task by implication. Do not edit `writer_census.py`, `propose_decision.py`, classifier/hash normalization, T3–T5, other runtime files or external configuration. No PR creation, comments, BugBot trigger, reviewer invocation, merge, deployment or live operations. Return any needed additional production-file dependency before editing it.

**Delivery:** commit and immediately push each commit with the explicit branch refspec; update existing VERIFY/STATUS/LATEST to the real result and accepted evidence exclusion. Keep the original Copilot FAIL pinned to `05c7706`; a fix alone does not dispose B1. Hand off the successor for one narrow independent delta (correction plus regressions), with source/evidence SHAs, clean/push state and residual gates. Cursor stops after delivery; Codex coordinates that narrow Copilot delta under the standing final-tip review authorization. This does not authorize PR-native trigger comments or a BugBot exception.

### Target-binding correction — owner authorized

**[Arc Safe Harbor] Date / author / recipient:** 2026-10-12; Codex planning lane; Cursor implementation lane. State: **CORRECTION COMPLETE; BOUNDED CODEX DELTA PASS** at docs candidate `721fd17fcc6b454a6bd435c1ece13da14b77f7fb`, runtime/tests `cdebf64b487ffa27d61955df9739204829864fe0` (90%). [Correction evidence](VERIFY-safe-harbor.md#codex-f1f2-correction-delta-and-complete-isolated-evidence--pass) records 85 distinct isolated cases and lint regression gate PASS. Draft #389 conflicts with main; integration needs a separate bounded grant, followed by fresh CI and final-tip review/acceptance. The earlier F1/F2 findings remain historical and this contract is unchanged. This is a local correction to the accepted T2 contract, not a new architecture or T3/T4 grant.

**Authority:** Ryan authorized: **“Next step: Authorize the bounded target-binding correction and CodeQL disposition.”** This grants the correction and isolated regression evidence below. Ryan also requested avoiding further Copilot spending. Do not invoke Copilot, BugBot or another paid reviewer. Existing historical reviews remain pinned; a Codex delta does not by itself satisfy the outstanding external-review gate or grant merge.

**Resume:** use the existing worktree `/home/lauer/Projects/convmem/.worktrees/fix-2026-10-12-safe-harbor-t2`, branch `fix/2026-10-12-safe-harbor-t2`, and existing draft [PR #389](https://github.com/alanmz-crypto/convmem/pull/389). The reviewed source is `0cff1578b881d890234adad6b9cb93a110ec1d48`; start at the pushed documentation-only grant successor supplied in Codex's dispatch. Confirm clean state and that intervening changes are only this handoff/evidence/routing record. No shared-checkout switch, rebase, main integration or runtime-main change.

**Finding to reproduce:** at `0cff157`, `config.py:467-482,610-628` expands user paths but preserves symlink spellings. `chroma_write_store.py:863-881` resolves the preflight target yet stores the original `live_cfg`. Its recheck at `789-814` hashes config/env bytes without detecting a retargeted data alias. `_session_config` returns that original config, and the session at `932-942` passes its path to the store, which resolves it again (`chroma_store.py:146`). Likewise `convmem.py:425-426` passes the configured export path downstream. An alias changed after successful preflight can therefore redirect the eventual target without changing either input file. Codex confidence: **90%, static; no dynamic reproduction claimed**.

**Bounded implementation contract:**

1. First exercise this case in the existing isolated CLI harness, with byte-identical config and Restic env, target A eligible and target B ineligible. If the real path refuses already, stop and return the concrete counter-evidence rather than changing code to fit the finding.
2. Make the admitted operation carry the resolved paths that its actual consumers use. Preserve the existing requirement to detect changed target/affected-path inputs at the cooperative admission/use boundary and refuse before client opening or logical mutation. Re-resolving original aliases downstream must never silently adopt a different Chroma target or export destination after preflight. Cover both production-store factories and the named CLI consumers; changing only the preflight comparison is insufficient.
3. Keep the correction at the existing admission boundary and its downstream configuration plumbing. Source scope: admission/configuration portions of `chroma_write_store.py`, narrowly necessary bound-caller plumbing in `convmem.py`, and `restic_gate.py` only if binding validation requires it. Focused self-isolating fixtures/tests may change `tests/test_safe_harbor_t2.py`, `tests/_safe_harbor_t2_cli.py` and directly affected existing caller tests. No global `config.py`/`ChromaStore` constructor change, new path registry, identity policy or new gate.
4. Keep the complete affected-path coverage from section 9. If binding an already named event/approved-row/export sink requires a production file outside this list, return that exact dependency before editing it. Do not silently exempt the sink or expand into the deferred T4 recovery state machine.
5. Preserve ordinary canonical paths, unchanged aliases, existing T1 competing-legacy-location refusal, all five B-E4.1 outcomes, numeric codes, named command exemptions and the accepted event-only evidence exclusion. This is cooperative path binding, not protection against arbitrary same-user filesystem replacement or a new filesystem-locking protocol.

**Required isolated evidence:** apply section 9's existing isolation requirements before imports and in every subprocess; ordinary-user execution, no production CLI/MCP/doctor/indexing, corpus, provider, service, external drive or real backup/key access.

- Real `add --upsert` workflow: retarget a Chroma alias after successful preflight but before store opening, without editing config/env. Require refusal at the checked boundary and unchanged logical contents in both fixture corpora, events/approved state and exports. Keep a passing unchanged-alias control that reaches a real mutation in A. Also cover the alternate production-store factory and existing approve/recover binding regressions within their current evidence scope.
- Export alias: redirect an initially covered export outside the protected data root after preflight. Exercise the actual downstream export path, including a retarget after store construction. No write may reach the outside destination: detect/refuse at a checked boundary, or continue to the already pinned authorized destination after that boundary. Do not promise rollback of effects that preceded a later refusal; record which boundary was exercised.
- Sensitivity control: use the actual pre-correction implementation or a test-only restoration of its unbound path use in the same workflow. Show that the wrong-target/no-escape assertion fails because a real fixture effect is redirected. A mock returning an arbitrary failure is not this control. No faulty publisher/path hook in production code.
- Re-run affected isolated T2/caller and relevant T1 alias/stale-client regressions; capture command, code SHA, interpreter/backend, exit status and control results in VERIFY. No default full local suite or new production probe. If authorized code changes affect R2b identity, regenerate only its derived inventory through the existing generator under isolation; leave route policy and the identity algorithm unchanged.

**CodeQL disposition:** Codex dismissed [alert #6](https://github.com/alanmz-crypto/convmem/security/code-scanning/6) as **false positive** at `2026-10-12T10:34:24Z`, under this authorization. At reviewed tip `0cff157`, the reported sink serializes a scratch `pathlib.Path` as `RESTIC_PASSWORD_FILE`, not password contents. GitHub confirmed the dismissal and CodeQL SUCCESS on that tip. Cursor need not rename fixture variables, suppress rules or change scanning configuration. New or changed findings require their own triage; this disposition is not a blanket exemption.

**Delivery / stop:** update existing VERIFY/STATUS/LATEST, commit and immediately push with the existing explicit refspec. These pushes update draft #389 and start its normal CI. Keep it draft. Report the correction tip, exact isolated evidence and fresh CI; then return to Codex for a bounded static delta. No new PR, review trigger/comment, automatic paid review, merge, deployment, T3–T5 or live operation. Final-tip external-review acceptance remains a separate owner decision; no earlier PASS transfers to changed code.

### T2 branch integration — owner authorized

**[Arc Safe Harbor] Date / author / recipient:** 2026-10-12; Codex coordinator; Cursor implementation lane. **State: DELIVERED — merge `551b16c`, isolated evidence recorded; Codex delta/CI next.** Ryan explicitly authorized: “Authorize the bounded T2 branch integration with current main, generated-inventory regeneration, affected isolated evidence and fresh CI. Keep PR #389 draft. Merge, deployment and T3–T5 remain unauthorized.” “Merge” in the exclusion means merging the PR into main; the named branch integration below is expressly granted.

**Pinned inputs:** clean task/remote tip `c6e881b6742746f7d5f7469b36b43bb3ea4d7b27`; current main fetched and remotely confirmed at `8a7cdab16420893fe26a2648d1d03f2b84d8589d`. Resume at the pushed documentation-only grant successor of `c6e881b`, in existing worktree `/home/lauer/Projects/convmem/.worktrees/fix-2026-10-12-safe-harbor-t2`, branch `fix/2026-10-12-safe-harbor-t2`, draft PR #389. Preserve the reviewed F1/F2 runtime `cdebf64` and its evidence. Do not switch the shared checkout or runtime-main.

**Bounded procedure:**

1. Confirm the clean pushed grant tip. Integrate the pinned main commit into this task branch with a normal merge commit, preserving the published history. No rebase, force-push or main push. Read and assess every automatic/textual resolution; rerere reuse is not semantic proof. Do not chase later main movement automatically.
2. The read-only preview identifies `docs/plans/R2B-V2-WRITER-COVERAGE-INVENTORY.json` as the conflict. Recreate it from the integrated tree through the existing `write_v2_inventory_file()` under isolation; do not choose one parent's generated hash. Retain main's unrelated changes unchanged, including any inventory-policy/shadow updates already merged there. **Mechanical shadow call-site coordinates** (line numbers and matching `sites` records for already-inventoried production session entrypoints) may be corrected when the combined tree shifts source lines but routing/classes/exemptions/allowlists/notes and runtime behavior are unchanged; this is location evidence under the same inventory-regeneration grant, not a new owner grant. Then regenerate R2b from the updated shadow metadata. No new route policy, identity algorithm, exemptions or lint baseline. A conflict requiring new behavior or an unrelated manual source change must be returned to Codex/Ryan with the exact dependency.
3. Re-run the affected isolated evidence: complete T2 file, write-gate effect and record-review CLI files, the four T1 alias/competing-location cases, native stale-client cases and the full R2b implementation-revision tests. Preserve actual positive/refusal/negative controls and the accepted T4 event-only-success exclusion. Add only genuinely affected, already isolated regression selections for incoming main changes; full default local pytest remains excluded. Run the existing full pylint regression gate against the pinned incoming main baseline, without editing the baseline.
4. Establish a clean allowlist environment and fresh HOME/XDG/CONVMEM/Restic/cache/TMPDIR before project imports, inventory generation, collection and subprocesses; uid 1000; no inherited provider credentials. Existing qualified selection/runner patterns are in VERIFY. Capture actual return codes, commands/node lists, dependencies, identities and before/after source fingerprints. No production CLI/MCP/doctor, corpus/key/repository, provider, service, backup or external-drive operation. Ryan additionally prohibited all manual session indexing today; no Track A step.
5. Commit/push the integration and existing evidence/routing updates immediately to `fix/2026-10-12-safe-harbor-t2:refs/heads/fix/2026-10-12-safe-harbor-t2`. Keep #389 draft. Observe fresh pytest/pylint/secret-scan/CodeQL on the final successor. Do not invoke a paid reviewer, post a review trigger/comment, change PR readiness or claim older CI applies to a new SHA. Report any failing CI with its actual cause; no weakening checks or unrelated fixes.

**Acceptance / stop:** integrated source preserves the Safe Harbor contracts; derived inventory and affected isolated evidence pass; final candidate's fresh CI completes. Record pinned main, merge parents, changed/resolved files, exact source/evidence SHA and limitations in existing VERIFY/STATUS/LATEST. Codex performs a bounded integration delta. Final-tip external-review disposition and Ryan's V2 acceptance/PR merge remain separate; T3–T5 and live operations stay ungranted.

### T2 governed-path identity correction — owner authorized

**[Arc Safe Harbor] Authority / scope:** Ryan authorized “go: Next step: Authorize that bounded T2 correction; the current review grant does not authorize fixes.” The antecedent is the fresh final-review finding below, not a general implementation grant. Codex coordinates; Cursor implements and supplies isolated evidence. Existing task branch/worktree and draft PR #389 remain in use. Reviewed source is `45a1f002239644371d4813f3f010ece72c6fb865`, pinned base `8a7cdab16420893fe26a2648d1d03f2b84d8589d`; begin at the pushed documentation-only grant successor identified in dispatch. No new main integration.

**Delivery:** Cursor implemented the correction; Codex captured original-runtime failures, final 98-case isolated PASS and lint-gate PASS. See VERIFY's governed-path section, including excluded initial attempts. Independent Codex bounded delta PASS (95%) is pinned to `dac925f33d4ebd7482c0536408b9be12f51d6106`; fresh final-tip CI and owner acceptance remain pending.

**Finding:** the fresh in-session Codex reviewer returned narrow FAIL (95%, static). With unchanged `/data/chroma-link -> /data/store/chroma`, preflight enumerates governed files from the original configuration's `/data` parent, but `AdmittedWriteOperation.config()` substitutes the canonical Chroma directory. Approval/recovery then derive their queue/event/lock/approved-row paths from `/data/store`. The preview can find the original proposal while the admitted operation reports it absent. This needs no retarget or configuration edit. It is an identity mismatch, not evidence of a reproduced outside-root mutation; VERIFY records exact source citations.

**Bounded correction:**

1. Reproduce with a stable cross-parent alias in the isolated real CLI harness before changing runtime code. If the path already works, return counter-evidence rather than forcing the finding.
2. Preserve the existing identities of governed files while retaining canonical Chroma client and export targets. Preflight, post-admission rechecks and the actual consumers must agree on affected paths. Do not move proposal/event files as a side effect of canonicalizing the Chroma client.
3. Source scope remains admission/configuration plumbing in `chroma_write_store.py`, narrowly necessary bound-caller plumbing in `convmem.py`, and existing binding validation in `restic_gate.py` only if needed. Focused self-isolating T2/caller tests and `tests/_safe_harbor_t2_cli.py` may change. If another production helper must change, return the exact dependency before editing it. No global configuration/constructor redesign, new registry, or T4 classifier/hash/event lifecycle work.
4. Prove stable cross-parent alias indexed approval and actual retry-Chroma recovery consume the intended original proposal/event/approved/lock paths, reach the canonical Chroma target, and leave the alternative parent files absent/unchanged. Assert the preflight paths are those actual consumers use. Include a pre-correction failure or test-only restoration of the faulty canonical-config behavior in that same workflow; never add a faulty runtime hook. Preserve prior alias-retarget refusal, export binding, competing quarantine, both factories and armed-census controls.
5. Use the existing clean allowlist and fresh temporary HOME/XDG/CONVMEM/Restic/cache/TMPDIR **before any project import, collection, generation or subprocess**. Run as uid 1000 with no provider credentials. Re-run affected isolated T2/caller/T1 alias/native stale-client tests and inventory scans; use actual process return codes. Regenerate derived R2b inventory only through its existing generator; mechanically refresh existing shadow coordinates only if source lines move, without route/policy/algorithm changes. Run the existing full pylint regression gate against pinned main. Full default local pytest is excluded.
6. Update existing VERIFY/STATUS/LATEST, commit and immediately push explicit task-branch refspecs; normal fresh CI follows. Codex performs a bounded correction delta. Historical green CI and earlier B1/F1/F2 closures do not close this finding or transfer to the successor.

**Stops retained:** no production ConvMem CLI/MCP/doctor/brief/search/indexing, corpus/config/key/repository/provider/service/drive operation; no Track A. No paid review, PR comment/trigger/readiness change, PR merge, deployment or T3–T5. The accepted event-only completion-success evidence exclusion remains. External-review disposition and Ryan V2 acceptance remain separate and ungranted.

## 10. Cursor T3 pinned-backend proof — owner granted

**[Arc Safe Harbor] Date / author / recipient:** grant 2026-10-12 local; Codex planning lane; Cursor proof lane. **State: CORRECTED PROOF DELIVERED at `93d4e344c8959ed0176b3a9b39af7be3f638f148` on 2026-10-13; owner acceptance pending.** Cursor/Codex jointly corrected R1–R3 and captured nine passing isolated cases plus focused pylint exit 0. This is the existing T3/Kiro A1 ordering gate, not a contract redesign or a grant for the remaining T3 implementation.

**Authority:** Ryan: “Authorize Cursor to perform T3’s isolated pinned-backend proof and collect evidence only. Return the results before implementing preservation, repair or release. Live operations remain unauthorized.” This overrides generic startup/indexing and automatic continuation requirements for this isolated task. No further approval is needed to perform this named proof.

**Review return and correction:** [Codex R1–R3](VERIFY-safe-harbor.md#codex-review-of-the-t3-proof--not-demonstrated) stays pinned to the original `8c4ad91` proof. Ryan subsequently instructed: “go: Next step: Correct R1–R3 within the existing proof-only grant, then return fresh evidence.” [Qualified successor evidence](VERIFY-safe-harbor.md#t3-r1r3-corrected-proof--qualified-evidence) addresses the three findings at `93d4e34`, discloses excluded early Cursor probes and qualified failed development runs, and records native small-store validation and CI integration limits. Codex also changed the harness, so this delivery is not independent review. No runtime edits, contract change or further authority are granted.

### Resume and pinned inputs

- **Branch:** `feat/2026-10-12-safe-harbor-t3-backend-proof`.
- **Local worktree:** `/home/lauer/Projects/convmem/.worktrees/feat-2026-10-12-safe-harbor-t3-backend-proof`. Do not switch the shared checkout, runtime-main or a completed T1/T2 worktree.
- **Source base:** merged T2 `458b9f6bb0bf98048c11ac0baf46a2340dcdcbf3`; documentation closeout parent `fc2ecae871e10994a89fa8d5d5cc3f65d9649164` has no runtime/test changes. Start at the clean, pushed grant successor supplied in dispatch; confirm it contains only this handoff/routing change over that parent. No automatic main update, rebase or force-push.
- **Correction provenance:** the original handoff above is historical; R1–R3 correction resumed from clean, pushed review-record tip `2f00e8c283b5c87726d3efb8f5588e4be970fee4`. Source result is `93d4e34`; its documentation successor records fresh evidence without changing tested bytes. No branch integration or backend substitution occurred.
- **PR:** none; creation, readiness changes and review-trigger comments are not granted. Commit/push the bounded proof and evidence on this branch with its explicit refspec. If a remote Cursor VM is used, clone/fetch this exact branch/tip into a clean workspace; do not treat absence of the host worktree path as permission to use another revision.
- **Backend pin:** `requirements.txt` and `test_chromadb_internals_the_guard_depends_on` pin `chromadb==1.5.9`; HNSW inspection dependency is `hnswlib==0.8.0`. T2's last qualified interpreter was `/home/lauer/miniforge3/bin/python`, Python 3.13.12, with numpy 2.4.4. Verify the actual interpreter/package versions and active client/API/segment backend inside the isolated child before claiming a result. Capture native module origin/digest where available. A Python wrapper field or package version alone does not prove Rust backend semantics. No dependency upgrade or backend substitution to obtain a PASS.

### What to prove, and why

The proposed release oracle requires no collection operation newer than the saved vector state. Prove whether the pinned backend exposes persistent evidence sufficient for that rule, using synthetic stores with explicit deterministic embeddings and independent expected outcomes. Existing `vector_census()` proves ID coverage only: same-ID stale vectors are its deliberate blind spot. A legitimate result is **NOT DEMONSTRATED** with the concrete counterexample; never turn an unsupported/missing watermark into zero or loosen the accepted rule.

Read STATUS, this section, T3/E1/A1 and VERIFY V4 before editing. Source entry points: `chroma_store.py` client construction, `chroma_write_guard.py` `_seq_id`/`vector_census`/segment inspection and snapshot manifest, `tests/test_chroma_write_guard.py` and its scratch worker. Treat private fields as hypotheses until demonstrated on the active backend.

### Allowed artifacts and isolation

- New proof files only: `tests/test_safe_harbor_t3_backend_proof.py` and, if needed, `tests/_safe_harbor_t3_backend_worker.py`. A test-local oracle/observation helper is permitted solely to evaluate the proposed predicate; it is not a production release implementation. Existing runtime, guard, doctor, watch, config, dependency pins, migrations, inventories and CI policy are read-only.
- Update only existing Safe Harbor EXECUTION/VERIFY/STATUS and inter-model LATEST/STATUS for evidence and routing. Do not create a new ledger, subsystem, log markdown or broad fixture refactor. Scratch JSON/stdout/stderr artifacts under a fresh `/tmp/safe-harbor-t3-*` root are allowed; reference them and preserve a compact reproducible evidence summary in VERIFY.
- All project/package imports, collection, probes and child processes must start under a clean environment allowlist with fresh HOME, XDG config/data/cache/runtime, CONVMEM_CONFIG/ROOT/RESTIC_ENV, RESTIC_CACHE_DIR and TMPDIR. Use an empty fixture config and absent fixture Restic env. No inherited provider credentials or production fallback. Set user-site/bytecode/network telemetry controls as appropriate; use explicit embeddings and no provider/model download. Build isolation with stdlib before project imports; do not rely only on a pytest fixture that runs after collection. Each worker inherits/checks the isolated roots before opening a client. Default test invocation must refuse an unsafe environment or arrange isolation before any project import; it must not silently skip the proof.
- Execute as ordinary uid 1000 on this host, never root. Reject resolved paths outside the task's disposable fixture root before creating/opening stores; reject production corpus/home/runtime-main paths and symlink escapes. Processes must terminate cleanly or be bounded by a reported timeout. A fresh process, not a client-cache reset, is required for restart evidence.
- No production ConvMem CLI/MCP startup ritual, doctor/brief/search, manual indexing/Track A, live corpus reads/copies, backup commands/repositories/keys, external drives, provider calls, services or permissions. No default full suite. No dependency installation, paid reviewer or unrelated agent invocation. Reading code is allowed; fixture mutations are confined to synthetic scratch data.

### Required observations and controls

1. **Backend and persisted-state map:** record actual client/API backend, package/schema identities, collection/metadata/vector segment IDs, queue topic/sequence encoding and every candidate persistent watermark. Distinguish SQLite metadata application, vector in-memory application and vector save-to-disk positions. Do not infer that SQLite's vector row exists or describes persisted bytes from its name. Observe SQLite through a read-only connection/transaction; any mutating Chroma open is a separate, labeled fixture operation.
2. **Real operation sequence:** create synthetic documents/vectors, then update metadata/document, update embedding, upsert the same ID with a changed embedding, delete, and reinsert/upsert that ID. Record expected IDs/content/vectors independently of the proposed oracle and the raw before/after persistent evidence. Show the relevant sequence values cannot move backward or silently reset across these mutations and actual process restart. Use separate collections to demonstrate collection/segment binding rather than a global maximum.
3. **Queue purge and save/restart:** induce real backend persistence and queue purge using pinned backend behavior/fixture settings. Capture queue rows/counts and watermarks before/after purge and restart, and show that absence of pending rows cannot hide newer operations. Manual SQL deletion or mocked sequence values do not prove backend purge semantics; label any such auxiliary fault injection separately. If genuine purge or a reliable persisted watermark cannot be demonstrated, return NOT DEMONSTRATED.
4. **Valid releasable control:** use a quiescent, persisted synthetic vector generation whose SQLite/segment identities, content and source watermark are demonstrably aligned. The proposed strict empty-changed-set predicate must admit that fixture after restart; an always-refuse predicate is not a successful proof. Capture source file digests and the exact predicate inputs without adding production SNAPSHOT fields.
5. **Stale-vector refusal control:** retain an old synthetic vector save, perform a real same-ID embedding change, and construct an explicitly disposable old-vector/new-metadata pair. Before any client open can replay/repair it, show the current ID census can pass while independently checked persisted vector values are stale. The proposed predicate must refuse using real persisted evidence, including after genuine queue purge and restart where applicable. Compare with a test-only census-only predicate in this same workflow; it must wrongly admit and fail the independent safety assertion. Do not put a faulty hook in runtime code.
6. **Unknown/binding controls:** absent/unsupported source sequence evidence and wrong collection/segment/source identity must refuse; an empty queue alone never licenses release. Check how update/delete/re-upsert behaves under equality: no newer semantic mutation may masquerade as the saved state. If the accepted predicate lacks a required field or observation, report the missing contract/data evidence rather than inventing a fallback or adding runtime instrumentation.

A scratch copy of synthetic segment files is permitted only to construct these evidence controls. It does not authorize implementing or calling a new production preservation/repair/release path. No actual QUARANTINE release is needed: report what the test-local predicate decides and keep that distinction explicit.

### Evidence, return and stop

Capture commands, interpreter/backend/schema identity, actual subprocess return codes, timeouts, source/harness hashes before and after, isolated paths, operation trace, raw watermark/queue observations and control results. Do not hide an exit status behind `tee`/`tail` or assert success from readable partial output. A command/setup failure is not an expected negative-control PASS. Preserve failed attempts and explain any evidence exclusion. Include the minimal reproduction for any contradicted assumption and confidence in the conclusion, not incident probability.

Run only this proof and its focused test/harness/lint checks under the same isolation. Do not import the whole project just to inspect versions or regenerate inventories. Use the existing lint policy for new proof files without baseline waivers; any wider validation need is returned as a named dependency. Production-runtime file diff against the pinned base must remain empty; existing T1/T2 code and tests are unchanged.

Report **DEMONSTRATED** only if every required observation and both valid/stale controls support the accepted predicate on the pinned backend. Otherwise report **NOT DEMONSTRATED**, identify the failed or inaccessible condition and stop. Neither result accepts V4 as a whole or authorizes continuation. Update VERIFY V4 with proof-only evidence, leave V3 and the rest of V4 NOT RUN, update STATUS/LATEST for the next lane, commit and immediately push, and return the exact tip plus a copy-ready PR description. Do not open a PR or invoke paid reviewers.

**Hard stop after results:** no preservation, bounded-repair or validated-release implementation even if the proof passes; no T4/T5, no merge, no deployment or live operation. Codex/Ryan receive the evidence and decide the next grant. No production or policy repair to make this proof pass.

## 11. Cursor remaining T3 — conditional owner grant satisfied

**[Arc Safe Harbor] 2026-10-13.** Ryan instructed: “go: Investigate the isolation lapse once, get the bounded independent proof review, then proceed with isolated implementation.” This supersedes section 10’s historical stop after proof, only after those prerequisites. Both are complete: the bounded inspection found no explicit production-directed command but cannot establish zero ambient side effects; Kiro independently reviewed proof tip `e08100ff1c2fe8474f897d6ae3d3c55e5b1c7e5f` (source `93d4e344c8959ed0176b3a9b39af7be3f638f148`) and returned **PASS 82%**, no prerequisite blocker. See [the bounded record](VERIFY-safe-harbor.md#t3-isolation-investigation-and-independent-ordering-gate-review).

**Scope:** implement precisely section 3 T3 and collect V3/remainder-V4 isolated evidence. Cursor authors; Codex supervises execution and records results. No T4/T5 implementation, Recovery Authority T4/V4k, PR creation/comments, merge, deployment or production operation. No production ConvMem CLI/MCP ritual, session indexing/Track A, corpus copies, backup/key/drive access, providers, services, dependency upgrades or installed-permission changes. No new release policy or structural-validator relaxation.

**Pinned workspace:** branch `feat/2026-10-13-safe-harbor-t3`, worktree `/home/lauer/Projects/convmem/.worktrees/feat-2026-10-13-safe-harbor-t3`, created from the reviewed proof tip above. Dispatch names the clean, pushed documentation grant successor. Do not switch the shared checkout, update main or rebase. The proof branch remains intact.

**Allowed source:** T3’s existing guard, guard CLI, focused doctor/watch recovery reporting, affected guard/worker tests and narrow T3 tests/stdlib launcher; existing Safe Harbor EXECUTION/VERIFY/STATUS and inter-model LATEST/STATUS for evidence. No broader schema, inventory-algorithm, CI-policy or constructor change. Carry the native small-store validator and ordinary-suite/CI limitations; do not silently repair them or claim merge readiness.

**Execution discipline after the lapse:** Cursor performs text-only source/test authoring and static reads. Cursor must not invoke Python, pytest, lint, package imports, schema probes, ConvMem tools or any fixture/runtime command. Codex reads the launcher first, then runs only explicitly selected tests/lint through a stdlib `-I -S -B` outer bootstrap that builds a clean environment allowlist before imports, as uid 1000, with fresh HOME/XDG/CONVMEM/Restic/cache/TMPDIR paths. Every client/worker validates its synthetic path; no provider credentials, ambient config or production fallback. Isolated child processes are bounded and their real exits retained. This is a constraint on this dispatch, not a new repository-wide subsystem.

**Implementation order:** retain existing T1 incident authority; add source identity/content/watermark evidence; implement durable write-once preservation and incident-bound repair; then all-current-findings release with durable event publication before durable marker removal. Every automatic restore aborts the initiating mutation and requires owner disposition. Unknown evidence remains contained. Test actual stale-vector and copy-over-original faulty alternatives against independent assertions, plus the specified interruption/IO/ENOSPC/fsync and disposition races. No client opening during release validation. Unlink/fsync ambiguity must report uncertainty rather than promise a marker still exists.

**Return:** V3/V4 observed results and exclusions, source hashes, implementation/review tip and the smallest remaining limitations. A prerequisite proof PASS is not an implementation PASS. Stop on a concrete unsupported contract rather than weakening it. Commit bounded work and push immediately with `git push -u origin feat/2026-10-13-safe-harbor-t3:refs/heads/feat/2026-10-13-safe-harbor-t3`; keep final review/acceptance and all live actions pending.

**Delivery checkpoint (2026-10-13):** implementation/tests `802d74dc0525a8040e44408b891f83edc20df97f` are pushed on this branch; [current V3/V4 evidence](VERIFY-safe-harbor.md#t3-implementation-checkpoint--isolated-v3v4-evidence) records 92 isolated passes, stable source hashes and focused lint regression gate PASS. Cursor/Codex are contributing authors. Ryan subsequently authorized one static Kiro implementation review of documentation tip `a54357c940327881239db98c89b965b1365efc84`, including that runtime and evidence. [Kiro returned PASS (85%)](VERIFY-safe-harbor.md#t3-independent-kiro-implementation-review), with a source qualification recorded there. CI integration, final successor review and Ryan acceptance remain pending; the review grants no PR, T4/T5 or live action.

## 12. Bounded T3 CI integration — owner authorized

**[Arc Safe Harbor] 2026-10-13, Codex handoff to Cursor.** Ryan approved the scope at `23041bd5f7352cdfd8a2626c19beb3e87a2bcde1`: “Authorize the bounded CI integration in EXECUTION section 12 at 23041bd, including isolated evidence. PR creation, merge, deployment and T4–T5 remain unauthorized.” Resume from its clean, pushed documentation-only grant successor on the section 11 branch/worktree. Runtime remains `802d74d`; do not update main, rebase or switch another checkout. State: IMPLEMENTATION/EVIDENCE RETURNED at `34ff309`; the named local work is complete. PR/hosted CI and final review/acceptance stay separate.

### Problem and selected approach

The existing pytest job runs `python -m pytest -q` without the T3 pre-import bootstrap. T3 and proof modules deliberately refuse that entry. Their launchers also hardcode `/home/lauer/miniforge3/bin/python` and uid 1000. The CI contract test requires the old command literally; changing only the workflow would therefore break its contract. Static evidence: `.github/workflows/pylint.yml` (pytest job), `tests/test_ci_contract.py` (`FULL_SUITE_CMD` and `_assert_workflow_contract`), `tests/_safe_harbor_t3_worker.py`, `tests/_safe_harbor_bootstrap.py`, and the backend proof worker/test. No new CI run was made to establish these source facts.

**Approved approach:** reuse the existing stdlib launcher to establish isolation before full-suite collection. Do not remove the import refusal or hide T3 behind skipped tests. This adds two fixed pytest-only modes, not a second runner or general command executor:

- `python -I -S -B tests/_safe_harbor_t3_worker.py run-ci-collect`: create the clean fixture environment, then invoke the existing critical-invariant checker. Keep its per-module collection and exit-code semantics unchanged.
- `python -I -S -B tests/_safe_harbor_t3_worker.py run-ci`: create its own clean environment, then run the complete pytest suite from the repository root. The child uses the selected interpreter with `-s -B -m pytest -q`, cache disabled and a fixture-bound basetemp. No file selection, `-k`, deselection or skip added to make CI pass. Keep logs and real exit codes; timeout, missing result or changed source hashes fail. Give the full-suite child a 90-minute bound and the pytest job a 120-minute bound; do not reuse the focused launcher's 900-second per-file timeout for the whole suite.

Keep pytest/pylint versions, backend pins, Python 3.12 CI matrix, existing job/check names, triggers, critical checks, lint baseline and secret scan. Leave the existing pylint job in charge of full-repository lint; CI pytest modes must not require pylint to be installed. Use fresh allowlisted HOME/XDG/CONVMEM/Restic/cache/TMPDIR paths and existing telemetry/plugin-autoload restrictions. No inherited credentials, ambient config fallback or production targets. Any required plugin must be identified and returned for a bounded decision, not silently enabled from ambient configuration.

### Authorized files and division of work

**Cursor authors text/code; Codex supervises isolated execution**, retaining section 11's division after the earlier isolation lapse.

1. **Portable test bootstrap only:** `tests/_safe_harbor_t3_worker.py`, `tests/_safe_harbor_t3_backend_worker.py`, `tests/_safe_harbor_bootstrap.py`, and `tests/test_safe_harbor_t3_backend_proof.py`. Use the invoking interpreter (`sys.executable`) and record its actual identity. Require a non-root parent, record its uid and require the child to match; reject missing/mismatched identity and root. This is a cooperative fixture boundary, not authorization. Preserve `-I -S -B` before project imports, clean child flags/env, path containment, credential refusal, backend pins and semantic proof assertions. No `GITHUB_ACTIONS` flag bypass. Record actual uid/version rather than retaining false local-environment labels. Child launch sites in `tests/_safe_harbor_t3_fault_worker.py`, `tests/_chroma_write_guard_worker.py` and the two T3 test modules may change only where needed to consume that same interpreter/bootstrap contract.
2. **Workflow and behavioral contract:** `.github/workflows/pylint.yml`, `tests/test_ci_contract.py`, new focused `tests/test_safe_harbor_t3_ci.py`, and `tests/ci-critical-invariants.txt`. Replace the two pytest/checker entry commands with the isolated modes above. Add the three T3 core/matrix/backend-proof modules to the existing critical manifest; preserve all current entries. Update executable-command assertions and their comment-only/echo-only negative controls. Prove the actual launcher invokes full pytest without selection and propagates checker/pytest failures, rather than merely looking for command text. The checker implementation stays unchanged. Existing artifacts may be extended to retain the launcher evidence; do not introduce a new check or parallel workflow.
3. **Derived inventory only:** refresh `docs/plans/R2B-V2-WRITER-COVERAGE-INVENTORY.json` through the existing `write_v2_inventory_file()` under the same pre-import isolation. T3 changed `chroma_write_guard.py`, a dependency imported by the authority manifest's `chroma_write_store.py` seed; earlier evidence did not regenerate this derived identity. This is a predicted integration dependency, not a newly executed mismatch result. Mechanical coordinates in `docs/plans/SHADOW-WRITER-COVERAGE-INVENTORY.json` may change only for existing call sites whose line positions moved, after confirming the same source snippets. No new routes, classification, exemptions, identity algorithm or ownership transfer. Any behavioral inventory discrepancy stops this scope.
4. **Evidence/routing:** only existing Safe Harbor EXECUTION/VERIFY/STATUS and inter-model LATEST/STATUS. Pin each result to its tested source and retain failures and exclusions. No new audit log or handoff file.

**Production source excluded:** no changes to `chroma_write_guard.py`, `chroma_store.py`, `chroma_write_store.py`, CLI, doctor, watch or other runtime. No release-oracle change, small-store validator fix, new stale-vector requirement, backend upgrade or T4/T5 work. Any newly exposed runtime defect is reported separately.

### Evidence and stop conditions

- Before project imports, use the inspected stdlib bootstrap. Local execution remains non-root uid 1000 with the existing pinned environment. Portable CI must record its own interpreter/backend/native identity and actual uid; local Python 3.13 evidence is not Python 3.12 CI evidence.
- Under isolation, run the existing 92-case T3/guard/T1 selection, all nine backend-proof cases, the CI contract and new launcher tests, and R2b implementation-identity checks. New launcher tests must use synthetic canaries/stubs for ambient configuration/credentials, check the environment before project import, reject unsafe/unbootstrapped entry and show that nonzero/timeout/absent child results cannot pass. Preserve the real preservation/stale-vector negative controls; stubs qualify launcher plumbing only. Run affected-file pylint and its existing regression gate without changing the baseline. No full default suite on the workstation.
- Record commands, selected cases/counts, failures, interpreter/packages/native identity, before/after source hashes and derived inventory diff. A portability check must show no dependency on the literal local interpreter path or uid 1000; the real hosted-runner result remains separate. Review source before executing it; no ambient exploratory probe to find missing assumptions.
- Commit and immediately push each bounded change using the existing explicit branch refspec. Return the candidate for a bounded review of the integration delta and owner acceptance. Kiro's current PASS remains pinned to `a54357c`/`802d74d`; it does not automatically cover changed harnesses or CI contracts.
- **Fresh GitHub CI is a later external step:** this workflow triggers on PRs and main pushes, not an ordinary feature-branch push. A separate authorization to open a draft PR is required; do not claim CI was requested or completed by pushing this branch. On that PR, require fresh full pytest, pylint, secret-scan and applicable security checks for the final candidate/merge tree; record base, head and tested merge SHA. An unrelated failure or integration conflict returns with its concrete scope; no automatic main merge, check weakening, paid review trigger or expanding correction.

**Acceptance:** isolated integration evidence passes without reduced coverage or changed runtime; the independent delta and fresh final-tip CI must then support Ryan's T3/V3/V4 decision. A green wrapper or historical 92-case result alone is insufficient. Merge, deployment, production/session indexing, corpus/backup/key/drive/provider/service actions and T4/T5 remain unauthorized.

**Why this should drift less (85% confidence):** one existing bootstrap feeds both focused evidence and CI; one full-suite pytest job remains the acceptance surface. It removes host-specific assumptions without duplicating test bodies or replacing fail-closed entry with a flag-only exemption. Full-suite compatibility remains unproven until the authorized hosted run.

**Delivery (2026-10-13):** Cursor's harness/workflow integration and Codex's derived-inventory refresh are committed at `34ff309e760ef3a8db756157e8faec5500cc05fd`. [Isolated evidence](VERIFY-safe-harbor.md#t3-bounded-ci-integration--isolated-evidence-returned): 149 passes, launcher exit 0, affected lint regression gate 0 (raw pylint 8, existing duplicate-code findings), 22 measured inputs stable. Production runtime remains `802d74d`; all 36 inventory routes and shadow policy are unchanged. Early static corrections, the supervisor comparison error and the initial failed lint run are retained in VERIFY. No full local suite or hosted CI was run. Next is a separately authorized bounded independent integration delta; draft PR/hosted CI and Ryan acceptance remain separate. This delivery does not auto-invoke a reviewer or start T4/T5.

## 13. Bounded T3 lint correction — owner authorized

**[Arc Safe Harbor] 2026-10-13.** Ryan authorized: “Authorize the bounded T3 lint correction, preserving runtime behavior, isolation and independent proof assertions. Keep the lint baseline unchanged, collect affected isolated evidence and fresh CI, and keep PR #391 draft. No merge, deployment or T4–T5.” Start from clean candidate `ea2d31668e939306aea874ebba7c8ff39aa701d0` on the existing section 11 worktree/branch. No main integration or branch switching.

**Evidence prompting this grant:** draft [PR #391](https://github.com/alanmz-crypto/convmem/pull/391), hosted run `38450752959`, reports `R0801/duplicate-code` rising from 71 to 85. The six-file local lint selection did not establish full-repository duplicate-code behavior. The same hosted run subsequently returned 21 pytest failures and 8 errors; those require separate triage/correction authority and are not silently included in this lint grant. Kiro's supplied independent delta PASS (88%) remains pinned to `ea2d316`; it is not a PASS for a changed successor.

**Cursor authors, Codex supervises isolated execution.** Permit the existing T3 bootstrap/workers/proof and launcher-contract test files to change only for this lint correction. Consolidate repeated harness plumbing where it preserves the pre-import boundary. Keep the proof's independent observations/predicate separate from production implementation; do not import production oracle helpers merely to silence duplication. A narrowly delimited, explained duplicate-code suppression is acceptable only for intentional independent checks or bootstrap constraints; no module-wide/global suppression, cosmetic statement rearrangement or baseline increase. Production source, workflow semantics, dependency pins, manifest, inventories and assertion strength stay unchanged.

**Evidence:** use the inspected stdlib `-I -S -B` parent and clean allowlisted children for the existing 149-case affected selection and lint. The full-repository lint report must also be evaluated against the unchanged baseline; a partial report under the global duplicate-code allowance is not the acceptance evidence. No full local pytest. Capture actual commands/exits, retained failures and before/after source hashes. Cursor performs text-only authoring/static reads; Codex runs evidence. No production CLI/MCP, indexing, providers, services, drives or backup access.

**Return:** commit/push the bounded correction and existing evidence/routing documentation; the open draft PR automatically requests fresh normal CI. Report concrete failures before expanding scope. Keep #391 draft. Independent successor review, owner acceptance, merge, deployment and T4/T5 remain separate. No paid review trigger.

**Delivery:** [VERIFY](VERIFY-safe-harbor.md#t3-hosted-ci-and-bounded-lint-correction) records 149 isolated passes, focused lint raw/gate 0, and full-repository lint gate 0 over 574 Python files (raw 30, duplicate count 71, baseline unchanged). Static comparison confirms unchanged runtime and independent proof bodies. Initial failed full lint and the Cursor text-only breach are retained. Local work is complete; fresh hosted CI and separate pytest-failure routing follow. No automatic continuation into other corrections.

## 14. Bounded T3 pytest compatibility correction — owner authorized

**[Arc Safe Harbor] 2026-10-13.** Ryan authorized: “go: Next correction: complete the isolated fixtures/tool paths, preserve the existing live-test exclusion, and reconcile the reviewed inventory/hash changes. Keep runtime, lint baseline and safety assertions unchanged.” Start at clean `e7b56011e6c8a1bb9b5c7c2953ce23843eb6c02b` on the existing T3 branch/worktree; draft PR #391 remains draft. No main integration.

**Grounding:** hosted run `38462958469` passed pylint and security checks but pytest returned 21 failures and 8 errors, the same case IDs as the original run. The isolated launcher supplies an incomplete configuration and empty documentation root, omits the runner's Node tool, and drops the existing CI-only live golden exclusion. Six new T3 SQLite read sites need explicit inventory classification; three watcher tests retain the pre-T3 hash. The doctor fixture requires isolated diagnosis before changing its expectations.

**Cursor authors; Codex inspects and supervises isolated evidence.** Permit the existing test bootstrap/workers and CI contract tests to supply complete fixture-bound configuration/resources and explicitly selected tool paths, retaining clean pre-import environment, uid/path/credential checks and independent proof assertions. Preserve the existing live golden exclusion in actual CI; no new broad skip, selection or runtime bypass. Update affected test fixtures only where the isolated failure establishes the dependency. Reconcile each new read-inventory entry against its actual function and update only the reviewed T3 watcher hash. No production code, lint baseline, dependency upgrade, route/exemption/identity policy, checker weakening or oracle change. Cursor's disposable authoring workspace must enforce Shell/MCP denial; prose-only text restrictions proved insufficient in section 13.

**Evidence / delivery:** run the affected isolated tests plus the existing integration selection and full lint regression gate against the unchanged baseline. No full local pytest or production ritual. Record actual commands/exits, failures, environment/tool identities and source fingerprints in existing VERIFY/STATUS/LATEST. Commit and immediately push explicit task-branch refspecs; collect fresh normal hosted CI. Report newly exposed defects before expanding scope. No paid review triggers, merge, deployment, session indexing, drive/key/service/provider operations or T4/T5. Historical reviews remain pinned; successor acceptance is separate.

**Delivery:** [VERIFY](VERIFY-safe-harbor.md#t3-bounded-pytest-compatibility-correction) records final affected selection 296 passed/1 existing skip, integration 159 passed, and full-repository lint gate PASS (574 files, 71 duplicates). Runtime, lint baseline, workflow, independent proof bodies and generated writer inventories remain fixed. Early draft corrections, the nested-PATH test failure and two lint failures remain disclosed. Local work returned; normal fresh hosted CI and successor acceptance remain separate.

## TL;DR

[Arc Safe Harbor] Section 14 correction and local evidence are returned. Draft #391 receives fresh CI on push; runtime, lint baseline and safety assertions remain fixed. No merge, deployment or T4/T5.


## 15. Cursor T4 implementation and isolated V5 — owner authorized

**Arc: Safe Harbor. Date: 2026-10-13. Author: Codex. For: Cursor implementation lane.** This section is the bounded implementation handoff; it changes no accepted T4 contract.

**Ryan’s grant (verbatim):**

> Authorize Cursor to implement Safe Harbor T4 under the accepted execution plan, in an isolated worktree, with Codex supervision and isolated V5 evidence. Return results for independent review. PR creation, merge, deployment, production operations and T5 remain unauthorized.

**Resume state:** implementation NOT STARTED when this grant is committed. Branch `feat/2026-10-13-safe-harbor-t4`; worktree `/home/lauer/Projects/convmem/.worktrees/feat-2026-10-13-safe-harbor-t4`. Code base is main `a7f72003aea516b4961a584fcfe54ad255d6a053` (T3 squash). The branch carries documentation-only closeout `693af6756be4aceafe1fa3b30b3fd888b36df24a`; this is not a different runtime baseline. Pin the pushed grant commit before authoring. No PR. No additional owner input is needed for this bounded scope.

**Outcome:** implement the T4 contract in section 3 and V5 in VERIFY. A retry must distinguish unknown from absence, preserve tombstones/conflicts, bind every durable target, serialize fresh state inspection with competing mutations, and report partial/uncertain completion honestly. T2’s event-only completion evidence exclusion must be closed by real fixture effects, not renamed or skipped.

**Permitted files:** recovery portions of `propose_decision.py` and `convmem.py`; narrow event-publication helpers in `conflict_events.py`; admitted-store/config/export helpers in `observe.py`, `ledger.py`, `chroma_store.py`, `chroma_write_store.py`; the existing native guard in `chroma_write_guard.py` only as needed to span T4’s recheck, mutation, post-native validation and publication without nested reconciliation. Related existing governed recovery/gate tests and focused `tests/test_safe_harbor_t4*.py` / `tests/_safe_harbor_t4*.py` helpers. Reuse the reviewed stdlib bootstrap/environment builder. Necessary test call-site inventories and generated writer identities may be updated only for the reviewed T4 changes, preserving routes/classifications/gate policy; use their generator under isolation. Update existing Safe Harbor EXECUTION/VERIFY/STATUS/LATEST and the cross-arc status row for evidence/routing. No lint-baseline increase, dependency/workflow change, new lifecycle state or parallel ledger.

**Division of work:** Cursor authors code and fixture evidence cases in a disposable source copy with Shell/MCP/WebFetch denied. Codex confirms the denial before authoring, inspects permitted deltas before copying them to the isolated worktree, and supervises execution. No ambient project imports or tests from Cursor. Capture failures and permission violations honestly; any isolation lapse stops that run and is excluded from evidence. Codex is a contributor/supervisor, not an independent reviewer.

**Execution isolation:** establish a fresh allowlisted HOME/XDG/config/data/export/event environment before imports through the existing `-I -S -B` stdlib entry. Bind uid/euid and all fixture paths; refuse production paths, providers and inherited credentials. Use fake providers/test repositories and real fixture Chroma/subprocesses. No production CLI, MCP, doctor/brief/unresolved/search, Restic repository, drive, service, backup/key or ledger operations. No session indexing/Track A. This task-specific restriction overrides the default session ritual and handoff indexing.

**Required evidence:** V5’s state matrix with cold/warm caches and fresh-process retries, direct and CLI consumers, actual admitted target effects, queue/approved-intent/event authority errors, and forced forget/refine competition via barriers. Independently assert documents/vectors/metadata/tombstones, export bytes and reduced proposal lifecycle. Inject before/partial/complete-but-fsync-failed/durable-but-unacknowledged APPROVED append outcomes, plus new-log/new-directory durability failures. Verify no success before post-native validation/durable publication, no duplicate APPROVED/blind replay, no malformed-tail cleanup, no hidden export omission. The old unknown-to-empty classifier, failure-assumed-rollback retry and out-of-lock recheck must each fail an independent negative control. Keep index/plain-add exemptions and T1–T3 regression assertions intact. Focused isolated pytest and the unchanged lint regression gate; full local suite/hosted CI are not implied by this grant.

**Stops:** unresolved lock inversion, a needed authority-model change or an unprovable contract returns to Codex/Ryan before scope expansion. Return code/evidence and limitations for independent review; no self-acceptance. External-review applicability is required for the eventual runtime candidate, but PR creation/comments/triggers are not authorized here. Prior task-specific outage exceptions do not automatically apply to T4. Push each commit with the explicit branch refspec; do not switch the shared checkout or main, force-push, merge or deploy.

**T4 delivery (2026-10-13 local):** Cursor/Codex implemented the section 15 scope at `a3207fe397bf820f4f2bd412c7d5f110d00fdc67`. [VERIFY V5](VERIFY-safe-harbor.md#t4-implementation-and-isolated-v5--returned-for-independent-review) records 70 isolated T4 passes, affected regressions and full lint gate PASS, with source/artifact hashes and the excluded fixture model-download lapse preserved. Direct/CLI event-only completion and uncertain retry are demonstrated in scratch. This returns the grant for independent review; it does not self-accept V5 or authorize a PR, hosted CI, merge, T5 or live action.


**Independent review completed (2026-10-13 local):** Ryan separately authorized the bounded complete-candidate review. Kiro returned **PASS (90%)** at `d27d3c00c1ed6f35c9502c4628b4dbcc3af78de1`, source `a3207fe`, with no blockers. [VERIFY records the original PASS, completed test-source coverage and explicit limits](VERIFY-safe-harbor.md#t4-independent-kiro-review--pinned-pass-with-coverage-limits): logs were sampled; auxiliary sink non-interference remains at author-trace level; hosted CI and power loss were not established. This records a review, not owner V5 acceptance or an outage exception. The next proposed step is a separately authorized draft PR/normal hosted CI; no fixes, PR actions, merge, live work or T5 follows automatically.


## 16. Bounded T4 CI correction — owner authorized

**Arc: Safe Harbor. Date: 2026-10-14. Codex supervision / Cursor authoring.**

Ryan authorized: “Authorize bounded T4 CI corrections and isolated evidence. Preserve runtime behavior, safety assertions and the lint baseline. Keep PR #392 draft.”

**Start:** draft [PR #392](https://github.com/alanmz-crypto/convmem/pull/392), branch `feat/2026-10-13-safe-harbor-t4`, clean candidate `76ea292701836c003ec86732ce011d85553b5212`; base `a7f72003aea516b4961a584fcfe54ad255d6a053`. Same isolated worktree as section 15. Ryan's preceding grant authorized this draft PR and normal hosted CI; no paid review trigger was made.

**Failure to correct:** hosted run `38512289708` reported seven pytest failures, 3,086 passes, 186 skips and 252 passing subtests; lint/secret/security checks passed. Two old recovery fixtures lack current admission/state setup; the writer inventory assertion still expects 18 rather than 19 static sites; four watcher/path-safety assertions disagree with current fixture HOME/import state. Investigate that last cause rather than changing runtime. The 61 extra skips must be explained and required T4 Restic cases must execute; a green result obtained by skipping those cases is insufficient.

**Bounded scope:** test fixtures and test-only harness/tool plumbing for these failures and required coverage; a narrow hosted workflow step may provision a pinned, checksum-verified Restic binary and expose it through the isolated tool path. Preserve all runtime files, lint baseline, independent proof assertions, critical collection, full unfiltered pytest and existing live-test exclusions. No broader provider/network/config inheritance. Update existing EXECUTION/VERIFY/STATUS/LATEST and the cross-arc status row with actual results. No inventory policy or runtime change; derived identities only if changed tracked inputs require regeneration.

**Method:** reuse section 15's file-only Cursor authoring and Codex-supervised pre-import isolation. Prove the fixture/import cause with bounded scratch evidence. Give old recovery fixtures real admitted effects rather than mocking away the gate or fresh-state checks. Assert static-site coverage distinguishes the internal delegated recovery factory from external routes. Make missing required CI tools fail explicitly, preserve intentional local optional-tool behavior, and include a sensitivity control for missing required coverage. Test affected legacy, watcher, inventory, harness and T4 cases under isolation; then push for normal fresh hosted CI. Report unexpected runtime/authority needs before changing scope.

**Limits:** PR stays draft. This grant supplies no independent review or owner V5 acceptance, no paid review trigger, merge, deployment, production commands, manual session indexing or T5. The prior Kiro PASS stays pinned to `d27d3c0`; subsequent changes need a bounded review.


**Section 16 delivery:** the bounded fixture/tool correction is implemented with runtime, baseline and independent proof assertions unchanged. [VERIFY](VERIFY-safe-harbor.md#bounded-t4-ci-correction-and-isolated-evidence) records the original hosted failure, collection-order cause, retained development attempts and final local evidence: 76 T4 / 62 T2 / 71 focused / 40 inventory-contract passes (overlapping groups), nine native-backend proof passes, real critical collection exit 0 and full lint regression PASS. N8/N9's new file and the new fixture/tool checks are in the critical manifest. Push requests normal full hosted CI on draft #392. Live final-head checks, a bounded independent correction review and Ryan’s T4/V5 acceptance remain required. No PR comment/review trigger, merge, deployment, production action or T5.


## 17. T5 integrated verification and operational handoff — owner authorized

**Arc: Safe Harbor. Date: 2026-10-14. Codex coordination and mechanical runner.**

Ryan authorized: “authorized: Next step: Your decision on authorizing T5’s integrated verification and operational handoff.” This grants the existing T5 contract, without changing it. T4/V5 acceptance at `ed6699bea949b95e0807f166c3297500736d4aa9` and the subsequent explicitly instructed squash are recorded in VERIFY.

**Start:** clean isolated worktree `.worktrees/feat-2026-10-14-safe-harbor-t5`, branch `feat/2026-10-14-safe-harbor-t5`, base `fdc8da7fa67c1d7b31bc5cd44de466001df04260`. The accepted T4 candidate, hosted test merge `33a4d9590a7adc0775005617a37b5998a2e2614b` and this main squash share tree `3e2e50f69da63bb58d1b6b4455bac15f52c50d25`. No shared checkout or runtime-main switch.

**Bounded work:** run existing V1–V5 suites together with the reviewed bootstrap, clean full_ci fixtures, real fixture subprocesses, fake providers and checksum-verified fixture Restic. Capture exit status, collected cases, skips/failures, controls, source hashes and isolation limits. Reuse the matching-tree hosted full suite and pinned independent reviews for their actual scope; the new selected run is not another full-suite claim. Synchronize existing VERIFY/EXECUTION/STATUS, ROADMAP/RECOVER/role-mapping and routing. Prepare section 6’s checklist; do not execute it. Runtime, tests, workflows, dependencies, inventories and lint baseline stay unchanged unless a separately authorized correction is needed.

**Isolation:** stdlib-only `-I -S -B` outer entry; reviewed allowlisted environment and uid/path checks before project imports. Required Restic uses the verified 0.19.0 binary and scratch repositories. Existing T4 Python-network refusal is installed before child imports. Capture unexpected attempts; this is not an OS/native-network sandbox claim. No production CLI/MCP/doctor/brief/search, service, drive, backup/key, restore, ledger or session-indexing action. The task-specific restriction continues to override the general startup/Track A ritual.

**Stop and return:** any unexplained failure, missing required case, source drift, unexpected resource access or runtime gap. Preserve evidence; no weakening assertions, suppressing a failure, automatic repair or operational scope expansion. Documentation findings may be corrected within T5. Optional earlier review suggestions are not new acceptance conditions.

**Exit:** existing VERIFY contains the exact-revision mechanical packet and operational limits, Kiro’s independent V6 sign-off is requested or recorded, and Ryan’s acceptance remains pending. A docs-only T5 delta can use the documented external-review exemption with its exact subject, but it does not replace Kiro’s V6 sign-off. No paid review trigger, new PR/comment, merge, deployment or live operation is granted. Push each commit immediately with an explicit branch refspec.


**Returned result:** the combined run returned **240 passed / 1 failed / 0 skipped**, exit 1. [T5-F1](VERIFY-safe-harbor.md#captured-result-and-blocker-t5-f1) records the failed forget/recovery assertion and the static pipe-reader defect; missing child output prevents conclusive attribution. No corrections/reruns were performed under that original grant. Section 18 records Ryan’s later correction grant and fresh results; runtime/safety assertions remain unchanged.

### T5 bounded Kiro review handoff

**Completed assignment; reference only — do not rerun.** Ryan authorized the bounded review, Kiro returned PASS at `1cb02fbd9cc15b36c7f3f094237da071ca2dcd18`, and Ryan accepted V6 at that subject. [The acceptance record](VERIFY-safe-harbor.md#v6-independent-kiro-review-and-owner-acceptance) carries scope/provenance/limits. The original prompt below grants no new reviewer invocation or PR action.

```text
Arc: Safe Harbor. One bounded independent V6 evidence/operational-handoff review.
TARGET: <full final T5 SHA supplied with the handoff>, branch
feat/2026-10-14-safe-harbor-t5. Record the resolved full SHA before inspection.
BASE: fdc8da7fa67c1d7b31bc5cd44de466001df04260 (accepted/merged T4 source).
Read EXECUTION sections 17–18, VERIFY V0/V6 and T4 final closeout, STATUS,
RECOVER's Safe Harbor handoff, and the ROADMAP/role-mapping deltas.
Apply DECISION-REVIEW-GUARDRAILS within reason. Static Git/source and existing
logs only: no production commands, new tests, edits, PR actions or cleanup.

Preserve the pinned T1–T4 verdicts and owner acceptances. Check only:
1. Exact source mapping: runtime remains the accepted T4 tree. T5 changes
   existing docs plus two concurrency test files at source 22fa1b9fc547092c7bf7e3b0156621e7db10b597.
   Verify the later lint annotation is comment-only and AST-identical to
   the executed source; fresh lint covers it, pytest ran at 22fa1b9.
   Prior outage exceptions remain tip-specific; this is not a docs-only exemption.
2. T5-F1 correction: lossless pipe framing/select readiness, short writes,
   timeout remains failure even with success JSON, both-child diagnostics on
   early failure, original exceptions preserved when diagnostic publication fails.
   Keep real lock/effect assertions, timeouts and faulty control binding.
   New combined V1–V5 evidence: actual cases/controls, exit and skip counts,
   source hashes, isolation/temporary-artifact limits. Reused hosted full-suite
   evidence must remain distinct; author evidence is not independent sign-off.
3. Operator instructions match merged code: retained exemptions, direct/CLI
   recovery, uncertain completion, every-restore containment, immutable originals,
   current finding-bound disposition and conservative all-incident release.
4. Prepared rollout versus live authority: exact candidate/test interpreters,
   unverified actual processes/guard state, loss window, backup/key/custody,
   legacy/schema adoption and rollback gates. No drive or service grant implied.

Return PASS/FAIL for V6 at TARGET, blockers versus optional suggestions, and
any unsupported claim with its smallest correction. Prior sampled-sink,
small-store, power-loss and live-recovery limitations remain. A PASS may support
Ryan's code/evidence closeout decision; it grants no PR, merge or deployment.
No repeated full implementation review without concrete new evidence.
```

### Prepared test/evidence PR text — not opened

**Title:** Preserve concurrency-test signals and recovery verification evidence

**Body:**

Safe Harbor's concurrency tests now preserve every signal and retain child diagnostics when a test fails. Integrated evidence passes all 257 cases. Kiro independently PASSed and Ryan accepted V6 at `1cb02fbd9cc15b36c7f3f094237da071ca2dcd18`; the operator handoff remains prepared only.

Who: Cursor/Codex supplied the bounded test correction and evidence. What: two test files plus existing policy/evidence/routing docs. When: 2026-10-14, runtime base `fdc8da7`, test source `22fa1b9fc547092c7bf7e3b0156621e7db10b597`. Why: a pipe reader could discard the second lock signal and failure cleanup lost the child output needed to diagnose it. How: lossless reads, retained diagnostics, sixteen sensitivity/diagnostic controls and fresh affected/integrated evidence; runtime, timeouts, safety assertions and lint baseline preserved.

**TL;DR:** The corrected integrated selection and isolated lint pass. This is a test/evidence delivery, with no live or recovery qualification claim.

**Merge reading:** [fresh evidence](VERIFY-safe-harbor.md#t5-f1-correction-and-fresh-evidence), [STATUS](STATUS-safe-harbor.md), [operator handoff](../RECOVER.md#safe-harbor-incident-handling-and-rollout), [EXECUTION section 18](#18-t5-f1-signalling-and-logging-correction--owner-authorized), [LATEST](../inter-model/LATEST.md).

Evidence: 16 controls, 22 affected cases and 257 integrated cases pass; counts overlap. Full isolated lint passes against unchanged `fdc8da7` baseline. Earlier failed run and remaining limits are retained. Reused T4 hosted evidence is not a fresh hosted run on this changed test tree. Kiro V6 PASS and Ryan acceptance are pinned above; final-tip external-gate/outage disposition remains pending, and prior exceptions do not transfer. No PR, paid review, hosted CI, merge or live action is authorized by this prepared text.

## 18. T5-F1 signalling and logging correction — owner authorized

**Arc: Safe Harbor. Date: 2026-10-14. Cursor implementation; Codex supervision and isolated evidence.**

Ryan authorized: “go: Next step: Authorize a bounded signalling/logging correction and fresh isolated evidence.” Resume from clean, pushed `ed5b2b9efd7f5cbde09ce0b417d6bb95d033abef` on `feat/2026-10-14-safe-harbor-t5`. The original 240-pass / 1-failure result stays in VERIFY; a demonstrated pipe-framing defect does not establish the historical failure's exact cause.

**Scope:** correct the test-only pipe reader so coalesced and fragmented lines are not lost; retain both workers' stdout/stderr/return codes and monotonic event/holder-liveness diagnostics on success and failure. Use the actual helper for deterministic framing sensitivity controls. Preserve the real forget/refine native-lock and effect assertions, the out-of-lock negative control, existing timeouts and isolation. Keep production runtime, workflows, dependencies, inventories and lint baseline unchanged. Primary implementation files: `tests/_safe_harbor_t4_concurrency.py` and `tests/test_safe_harbor_t4_concurrency_real.py`; existing Safe Harbor evidence/routing docs carry the result.

**Authoring:** Cursor may edit those test files in a disposable source copy with Shell/MCP/web execution denied. Codex inspects and copies the bounded delta, may contribute narrow corrections, and runs only the reviewed isolated bootstrap with clean fixtures and required scratch Restic. No author is an independent reviewer. No startup production commands or session indexing.

**Evidence order:** deterministic coalesced/fragmented-line and failure-log controls, then all affected real concurrency cases including the faulty out-of-lock control, then the combined V1–V5 selection. Capture exact source hashes, case/skip counts, exit statuses, child diagnostics and network-attempt logs. Do not weaken checks, retry for green, or increase timeouts to hide a failure. If corrected diagnostics show a runtime defect or an unexplained required failure, preserve the packet and return before expanding scope.

**Exit and routing:** corrected isolated evidence returns for bounded independent Kiro V6 review and Ryan acceptance. Section 17's prepared review/PR wording must be updated to include this test delta; it is no longer a docs-only review subject. PR creation/comments, hosted CI, paid review triggers, merge, deployment, production and drive/service operations remain ungranted.


**Returned correction:** source `22fa1b9fc547092c7bf7e3b0156621e7db10b597`, two test files only; sixteen new controls plus all six original concurrency cases pass, and the combined selection returns 257 passes / 0 errors/failures/skips. Full isolated lint passes with unchanged baseline. [VERIFY V6](VERIFY-safe-harbor.md#t5-f1-correction-and-fresh-evidence) contains exact artifacts, source hashes, authoring limits and the retained historical failure. Independent Kiro V6 review and Ryan acceptance are next; no reviewer was invoked and no PR or live action was taken.

**Subsequent review and acceptance (2026-10-14):** Ryan granted the bounded read-only Kiro review; Kiro PASSed V6 with high confidence and no blockers at `1cb02fbd9cc15b36c7f3f094237da071ca2dcd18`. Ryan then accepted that reviewed V6 subject while expressly retaining separate PR/hosted-CI/merge/deployment gates. [VERIFY records the decisions and limits](VERIFY-safe-harbor.md#v6-independent-kiro-review-and-owner-acceptance). No T5 BugBot outage exception is inferred. This record changes no code/test contract and grants no further execution.


## 19. Read-only deployment preflight and rollout/rollback drafting — owner authorized

**Arc: Safe Harbor. 2026-10-14 local. Codex authoring.** Ryan authorized:
“Authorize Codex to perform Safe Harbor’s bounded read-only deployment preflight
and draft the rollout/rollback procedure. No service changes, corpus writes,
backup/restore operations or deployment.”

Work begins from merged candidate `c6f07241ccf1a71d9d874fee963a37b04091b3ce` in
isolated branch `plan/2026-10-14-safe-harbor-rollout`. The shared checkout and
runtime-main remain unchanged. Direct Git worktree setup avoids the production
CLI. Selected file/package metadata, unit status/definitions, mount identity,
existing journal output and the separately approved host process listing inform
[ROLLOUT-safe-harbor.md](ROLLOUT-safe-harbor.md). No key contents, production
Chroma client, generic doctor/brief/search/MCP, session indexing or new tests.

The returned draft records old clients, split backup routing, absent audit
units, production-interpreter evidence limits and two matching legacy generations
without release evidence. It does not prescribe generic reconciliation as
migration or claim a qualified recovery point. Existing source/review acceptances
are carried; operator inputs and exact state-initialization evidence stay open.

Documentation updates may reconcile Safe Harbor's stale merge/routing labels.
No other arc status/authority is changed. No PR, review invocation, operational
mutation or additional verification is granted by preparing the draft. Next
proposed work is bounded isolated readiness evidence, then the complete
operational procedure's review and Ryan's explicit execution decision.


## 20. Isolated rollout-readiness evidence — owner authorized

**Arc: Safe Harbor. 2026-10-15.** Ryan authorized: “go: Next step: Bounded
isolated interpreter/legacy-state evidence, plus your recovery inputs”.
Start from rollout draft `5fa8e978e9605a4566a68795f850f667014fd1e9`, candidate
runtime `c6f0724`, in isolated branch `feat/2026-10-15-safe-harbor-rollout-evidence`.

Codex collects evidence with the installed production Python executable against
synthetic temporary roots only. Permitted additions are a bounded stdlib launcher,
focused synthetic legacy-generation tests and evidence/routing docs. Reuse the
reviewed bootstrap, clean environment, uid/path refusal, inert providers and
Python network refusal. Hash source before/after. No ambient project imports,
production HOME/config/data, live service/drive/key/repository access, corpus
writes, deployment, dependency change, runtime fix, PR or reviewer trigger.
Scratch fixture writes/restores are evidence, not production operations.

Sequence: qualify the interpreter with existing backend/release/recovery cases;
construct representative legacy manifests in synthetic stores; demonstrate that
unchanged reconciliation skips them, restore/release refuses missing evidence,
and explicitly rehearsed fresh-generation capture preserves the archived source
and obeys the existing release predicate. Fault/control failures and any unproven
initialization mechanics remain explicit. No production migration command is
created or authorized. A needed runtime change returns as a separate decision.
Recovery artifact, lost-work interval and independent-access inputs remain Ryan's.

Return recorded evidence and updated rollout status for bounded independent
review. Do not turn test-only private-helper access into an operational grant.

**Returned:** installed Python 3.11.15 selection at `a6c7adb` passed 83 existing
safety cases; final legacy selection at `7788028` passed five cases. No skips or
source drift; runtime stays `c6f0724`. [VERIFY readiness](VERIFY-safe-harbor.md#isolated-rollout-readiness--installed-interpreter-and-legacy-state)
records exact selections and local artifact digests. The early four-case legacy
run is historical, not additional coverage. No full suite/lint/hosted CI rerun.

The public CLI lacks an explicit unchanged-generation initializer. Private refresh
works in a synced synthetic fixture after preserving old bytes, but pending work
still refuses release and a scratch copy is not a durable archival protocol.
An operational entrypoint/procedure remains a separate bounded decision. This
result does not grant implementation, independent review, a PR or live operations.

## 21. Readiness review and initialization scoping — owner authorized

**Arc: Safe Harbor. 2026-10-15.** Ryan authorized: “go: Next step: Bounded
independent review, recovery inputs, then scope legacy initialization.”

Kiro's bounded static review of `f45b0513fc31df98d96d90f324bcad1fe893e2b5`
returned PASS with high confidence, retained after a same-session coverage
completion on the unchanged candidate. [VERIFY](VERIFY-safe-harbor.md#independent-readiness-review--kiro-pass-exact-subject-retained)
records actual coverage, the initial overstatement/correction and remaining
limits. No new tests, production commands or runtime edits were run for review.

Recovery questions have been sent; answers remain pending. The proposed scope
below therefore preserves recovery qualification as an unresolved prerequisite.
It is Codex's new planning artifact, not part of Kiro's reviewed `f45b051` or an
Execute grant. Implementation, PR/CI, merge, backup/restore and deployment remain
unauthorized. No other arc ownership or accepted T1–T5 contract changes.

## 22. Bounded legacy-source initialization — proposed scope, not a grant

### Decision and boundary

The missing operation is deliberate creation of evidence-bearing local segment
saves when unchanged legacy CURRENT generations lack evidence. Ordinary reconcile
skips them; an old source cannot be used for bounded repair without that evidence.
The proposed solution is one explicit operation on the **existing guard and CLI**,
not a migration framework, new recovery authority or change to ordinary writes.

Proposed entrypoint: `scripts/chroma_guard.py initialize-legacy`. Default behavior
is a read-only preview; applying it requires explicit canonical Chroma root, a
fresh archive destination, the preview's expected-state digest and an apply
flag. Exact arguments/output schema require the scope's governing review. There
is no implicit config-selected production target, startup hook, timer, environment
bypass or automatic first-write initialization. A digest binds state; it is not
an owner authorization token.

Alternatives considered: generic reconcile does not initialize matching saves;
deleting CURRENT or changing signatures to force it conceals the intended
operation and risks pruning originals. A private-method production one-liner
omits a supported admission/preservation contract. These are not permitted routes.

### Reuse from Arc Codex / issue #286 (2026-10-16 comparison)

Ryan asked Codex to inspect the parallel indexing work before duplicating it.
Static comparison used PR #395 candidate
`d5f765a05dbb74d2786e2f15ae6bb0824ac38dba` against Safe Harbor's merged
`c6f0724`. The candidate adds relevant coordination; `chroma_write_guard.py` and
`scripts/chroma_guard.py` are byte-unchanged, so it supplies no legacy initializer.
The older Arc Codex STATUS/LATEST entries do not describe this newer candidate.

- **Reuse the writer coordination.** `purge_locks.index_write_flock` (C1) binds a
  store-wide lock to a Chroma target, and the production-store wrapper requires it
  for mutations. Recovery now nests governed lock → C1 → Chroma session → native
  guard. Scope review must reconcile the initializer with the selected combined
  runtime: if it participates in C1, reuse that primitive before the native guard,
  and prove the exact same lock identity as the configured writers. Do not infer
  the lock path from the Chroma parent: the existing helper selects the data root
  from configured processed/export paths as well. Do not add a parallel lock or
  claim that C1 covers old clients or incidental writes from readers.
- **Reuse preparation/revalidation and its tests.** Corrective 22 prepares the
  recovery embedding before C1/session acquisition, then rechecks and applies
  under the existing native guard. A provider outage refuses a needed rebuild;
  event-only/marker completion can still finish. The initializer remains entirely
  provider-free. Its preview must stay observational and its apply must recheck
  actual state after waiting; an unchanged/no-op path cannot skip an incident
  check. Reuse the corresponding refusal and real-effect test patterns rather
  than assuming a successful helper call establishes safe admission.
- **Keep evidence sensitive to each lock.** The Codex audit found that a blocked
  competitor can be waiting on C1 while a missing native guard goes unnoticed.
  If C1 is used here, retain an independent native-lock probe and a faulty control
  that drops only that guard while C1 remains held. Reusing a harness is useful;
  its prior PASS does not certify a new initializer or combined revision.

The bounded Astra recovery audit at `483875d` reviewed `a5fb7d7`, whose tree
`c7d4b78e59b60746e182c8e61b588a9df8aabd0f` equals `d5f765a`; its reported provider
outage, document/vector and concurrency evidence is reusable context, not a rerun
or an acceptance by this lane. PR #395 explicitly requests Safe Harbor review of
the recovery/test integration. At inspection it was open, with hosted pylint
failed and pytest running. No merge, deployment or review completion is inferred.

Source-scoped transcript rollback in #286 is not a substitute for archiving whole
shared HNSW generations. Durable originals, strict pending-work refusal and the
multi-segment interruption contract below remain necessary. Before an initializer
Execute grant, choose the exact integration base and resolve its lock interface
in governing scope review. This comparison changes planning only; other-arc
implementation, acceptance and authority remain with their existing owners.

### Required behavior

1. **Preview and binding.** Inspect existing state without opening a Chroma client
   or changing corpus/guard files. Enumerate the complete expected segment set,
   CURRENT bytes, generation manifests/files and backend identity. Bind the
   preview digest to canonical target plus these inputs; show existing eligible,
   legacy, unavailable and unexpected states distinctly. Refuse ambiguous paths,
   symlinks, incomplete generations or unknown schema. Do not reinterpret an
   already initialized or partially initialized store as a new legacy operation.
2. **Admission and complete precheck.** A later apply acquires the existing native
   lock, rechecks quarantine/target/digest, and keeps a read-only SQLite transaction
   across validation and capture. All affected segments must pass structural,
   identity, census and the **existing strict empty-changed-set predicate** before
   the first CURRENT publication or prune. A mixed eligible/ineligible set refuses
   as a whole before publication. Old clients/incidental writers still require the
   separately granted maintenance quiescence; these locks are not a global freeze.
3. **Durable originals before pruning.** Archive every affected original generation
   and exact CURRENT bytes outside the Chroma/guard prune trees. The explicit
   destination must be fresh, non-overlapping and free of symlink redirection;
   never overwrite/reuse an existing archive. Copy/verify originals, fsync files
   and created directory entries, then publish/fsync a write-once completion
   manifest binding target, original inputs and digests. Recheck original state
   before accepting completion. Any copy/hash/space/fsync failure prevents CURRENT
   changes and pruning. The archive is evidence/rollback material, not a second
   authority or a substitute for the qualified recovery artifact.
4. **Create new saves, leave the corpus alone.** Reuse existing snapshot capture
   and validation under the locks after complete archival. Do not add release
   evidence to an old manifest. Create new generations, verify their identities,
   digests and strict evidence, and then publish their CURRENT pointers. Preserve
   existing ordinary capture behavior; any helper factoring must keep it covered.
   No queue flush, embedding/indexing, repair, automatic release or SQLite write.
5. **Multiple segments and interruption.** Success means every expected segment's
   newly selected generation has passed the stated checks and its required
   publication durability has completed. There is **no claim of atomic publication
   across all CURRENT files**. A failure after one segment's publication reports
   partial/uncertain completion with observed old/new references and archive
   identity; it must not claim rollback or automatically resume consumers. Keep
   the completed archive. The maintenance hold remains an operational prerequisite.
   Inspect actual state before a newly authorized continuation; no blind retry,
   rollback of pointers, archive overwrite or automatic cleanup is included.
6. **Reporting and fail-closed limits.** Report preview/refusal/complete/partial-or-
   uncertain results explicitly, using the existing event/output surfaces rather
   than a new ledger. A required event/fsync failure after publication is uncertain
   completion, not absence of effects. Quarantine, pending work (`watermark_drift`
   or `queue_pending`), unavailable evidence, backend mismatch or unexpected state
   stops the operation. Never clear an incident or change the release predicate.

### Proposed implementation boundary and evidence

If approved later, Cursor would implement in an isolated worktree. Allowed runtime
surfaces would be `chroma_write_guard.py` and `scripts/chroma_guard.py` only, reusing
existing durable-copy/publication, canonical identity and guard primitives. Focused
synthetic tests/helpers may extend the rollout legacy tests under the existing
bootstrap. Documentation may update this scope, ROLLOUT/VERIFY/STATUS and the CLI
operator guidance. No dependency, workflow/lint-baseline, backup resolver/profile,
governed recovery, watch/service, general HOLD or other-arc authority changes.
A needed surface/contract expansion returns before implementation.

Minimum isolated acceptance evidence:

- Two populated legacy segments: complete preview, durable archive, both fresh
  sources strict-admissible; corpus bytes unchanged; original archived bytes and
  CURRENT references retained. Test the actual public command, not only helpers.
- One synced segment plus one pending/ineligible segment: refuse before either
  CURRENT changes; never force eligibility. Unknown authority, changed digest,
  wrong target, alias retarget, unexpected segment/schema and existing destination
  also refuse without erasing source/incident state.
- Archive short write/hash mismatch/file and directory fsync failures: no publish
  or prune. A real faulty omit-archive control must fail the retention assertion.
- Interrupt before archival completion, before first CURRENT publication and
  after the first of two publications. Restart inspection distinguishes old,
  partial and complete state; retained originals survive; neither retry nor a
  failed final event/fsync falsely reports rollback or global success.
- Missing/unavailable/mismatched evidence remains refused; existing stale-vector
  and census-only negative controls remain meaningful. Preserve ordinary snapshot,
  incident, repair and release behavior with affected regressions under isolation.

Fsync/fault/restart evidence establishes implementation boundaries, not hardware
power-loss survival. No new tests or implementation are authorized by this scope.
Independent review and owner acceptance remain required for a later candidate.

### Recovery and live-operation gate

Ryan's maximum lost-work interval and newest completed Rescuezilla image
(date, scope, location, independent access and restore/check history) remain open.
The mounted ext4 drive is an available capacity option, not the selected archive
destination or a qualified recovery point. Do not touch it under this scope.

Scope review may proceed with those values explicitly unresolved. No live apply
may proceed until a qualified recovery artifact, original-state preservation,
exact target/archive paths, process/timer quiescence, selected interpreter/revision
and stop/continuation procedure are reviewed and separately granted. If real
pending work prevents the strict precheck, return that concrete state for a
separate decision; there is no implicit repair/flush permission.

**Next decision:** governing review of this proposed scope and Ryan's recovery
inputs; then a separate bounded implementation/evidence grant if accepted. Kiro's
PASS at `f45b051` validates the preceding evidence only, not this new interface.

<!-- ref: ROLLOUT-safe-harbor.md, STATUS-safe-harbor.md — deployment draft and remaining gates -->
<!-- src: VERIFY-safe-harbor.md — completed implementation and owner acceptance -->
<!-- src: /home/lauer/Projects/convmem/purge_locks.py, /home/lauer/Projects/convmem/propose_decision.py, /home/lauer/Projects/convmem/tests/_safe_harbor_t4_concurrency.py — Arc Codex comparison pinned to d5f765a above -->

# [Arc Codex #286] Execution plan — existing Codex rollout bootstrap

**Author:** Codex, 2026-10-18. **Disposition:** Draft for Kiro review; Cursor Execute is NOT AUTHORIZED.
**Approved direction:** [architecture](ARCHITECTURE-issue-286-codex-bootstrap-corrective.md), reviewed by Kiro with PASS at `e0e91bd32f96bce1f8c109a84005ed547d8655ff`.
**Authority:** Ryan supplied Kiro's written verdict in this conversation, then instructed: “Approve direction; draft the execution plan.” This grants planning only.
**Code baseline:** `483373f1cef2142847fcd9c276196593a72a0ecf`; `origin/main` refreshed and unchanged when drafting. The planning branch contains documentation only.
**Goal:** Safely adopt the three exact A1 Codex rollouts through a one-shot operation, preserving identity, paid caps, recovery authority, and unrelated live writers' work.

## 1. Scope, lanes, and gates

The [architecture §2](ARCHITECTURE-issue-286-codex-bootstrap-corrective.md#exact-initial-scope) fixes the three rollout paths. Support only admitted `jsonl_codex_rollout` sources requiring adoption of existing legacy coverage. Preserve the unversioned Kiro grant and route byte-compatibly. The new route never becomes ordinary watcher or bulk-index authority.

Five serial tasks below are for **Cursor after Kiro plan review and Ryan's explicit implementation grant**. Keep one implementation writer in an isolated worktree. Each task has a separately reviewable deliverable and evidence gate. A failed gate blocks dependent work; a material scope mismatch goes to Ryan/Codex before implementation expands. No parallel agent work is requested.

Current hard limits remain: no production indexing/provider calls, deploy, runtime-main/config changes, watcher stop/restart, quarantine clearing, source changes, PRs, or Part B. No implementation or tests run in this planning phase. Later implementation verification is hermetic and provider-free; the future Execute grant must cover that work. This plan does not itself grant it.

Excluded: Codex history or pre-admission rollout support; new roots; bulk/auto-bootstrap; v2 supersession; v1 grant migration; generic writer-admission or budget-manager redesign; commit-cost optimization; recovery-policy changes in another arc; global rollback/repair; A2 execution. No CI baseline relaxation or regeneration of unrelated surfaces.

**Required companion:** [VERIFY-issue-286-codex-bootstrap-corrective.md](VERIFY-issue-286-codex-bootstrap-corrective.md), currently a NOT RUN stub. Keep implementation evidence there; do not overwrite older Arc Codex verification results.

## 2. Kiro corrections made concrete

1. **State-directory convergence:** correct `scripts/bootstrap-incremental-jsonl.py::bootstrap()` at `source_state = state_root / source_state_id(str(source))`. V2 must pass the validated `format_id` explicitly. Before any write, prove that operation journal, reservation, transaction lookup, and coordinator `state_dir` resolve to the same format/path-derived directory. No Kiro-directory side effect is permitted for a Codex grant. T1 owns this.
2. **Reservation without transaction:** v2 invocation authority must be durable in the same authoritative publication as reservation ownership. Do not use v1 `begin_invocation(recoverable_transaction=False)` for the recovery of that state; its ordinal logic correctly refuses it today. Section 4 specifies the v2 protocol and T2 implements it.
3. **Watcher deferral:** classify a verified reservation before `incremental_jsonl._raise_incremental_retry_refusal()` changes retry state and before `convmem.py::index()` maps refusal to exit 91. Teach the watch subprocess/result path to preserve a distinct deferral without calling either `record_refusal` or `record_success`. T3 owns this.

**Precision constraint:** ordinary `bootstrap_required` without a valid active reservation keeps its existing refusal/quarantine behavior. A reservation is not permission to suppress fault, wedge, malformed-authority, exclusion, or exhausted-budget errors. Existing quarantine is never cleared or bypassed by the watcher.

## 3. Tasks and dependencies

### T1 — One format-bound v2 authority and read-only preflight

**Depends on:** reviewed plan and Ryan Execute grant. **Lane:** Cursor.
**Deliverable:** strict v2 grant validation, consistent Codex identity/descriptor selection, and a preflight packet that performs no writes or provider calls.

**Surfaces:** `scripts/bootstrap-incremental-jsonl.py`, `bootstrap_safety.py`; registry/admission/descriptor helpers in `incremental_jsonl_formats.py`, `incremental_jsonl_codex_admission.py`, and `incremental_transform_contract.py` as applicable. A focused `bootstrap_codex_v2.py` module may contain the new contract and avoid altering v1 dispatch. Do not duplicate the rollout parser or introduce a second chunking implementation.

- Preserve the exact v1 field set and hash domains. Dispatch unversioned grants to v1 only; accept v2 only with explicit `grant_version=2`, `adapter_format=jsonl_codex_rollout`, and `coordination_protocol_version=1`.
- V2's exact field set is the existing `GRANT_FIELDS` union `{grant_version, adapter_format, adapter_contract_version, coordination_protocol_version, source_state_id, session_id, source_device, source_inode, max_source_bytes, lock_wait_seconds, transform_descriptor, recovery_protocol_version, outer_budget_authority_sha256}`. Retain all existing runtime/config/provider/embedding/chunk/confidence/backup/call/recovery bindings. Recompute operation and grant hashes using the canonical JSON body with the new domains `convmem-bootstrap-operation-v2:` and `convmem-bootstrap-grant-v2:`; omit only `operation_id` when deriving operation identity. The outer-budget digest binds the owner's reviewed enforcement contract, not a caller-supplied boolean; missing/unverifiable enforcement remains a production NO-GO (§7). Publish canonical hash vectors in evidence. Unknown fields/versions and booleans masquerading as counts fail closed. Validate descriptor structure/version with existing helpers and its digest against `transform_fingerprint`; require positive bounded sizes/waits, nonnegative device and positive inode, canonical UUID and SHA values.
- Derive the state ID from canonical path plus explicit format. Bind the existing Codex descriptor digest and recovery protocol; do not use the Kiro-default `_effective_binding()` fingerprint. Verify descriptor equality across grant, snapshot, prepared artifacts, transaction, checkpoint, and receipts.
- Validate all five Codex admission/identity checks, the complete-line boundary, regular owned file/no symlink, size ceiling, chunk count, absence of a valid checkpoint, and the exact allowed `bootstrap_required` state. Preserve existing artifacts. Contradictory/orphan operations, unknown retry state, existing v1/supersession evidence, or another active reservation refuse.
- Add an explicit `--dry-run` mode mutually exclusive with `--execute`, using the same pure validators. No coordinator/journal construction, lock-file creation, directory creation, embedding probe, or provider call. It reads metadata/identities and returns a proposed packet plus blockers; it does not materialize executable authority. Keep v1 execution syntax unchanged.
- Keep v2 live execution closed until T2–T5 are complete. Do not copy a bypass environment variable or a hermetic capability into production.

**Gate/evidence:** V1 identity and v1 compatibility; V2 dry-run immutability. Include fixed expected state IDs and hash vectors independently calculated from synthetic fixtures, and a negative control retaining the default Kiro `source_state_id` call. Never read real transcript content for these tests.

### T2 — Durable reservation, invocation authority, and paid accounting

**Depends on:** T1. **Lane:** Cursor.
**Deliverable:** the crash protocol in §4, including an unambiguous initial invocation and at most one recovery even without a transaction.

**Surfaces:** the focused v2 authority module, `bootstrap_safety.py` through an explicit v2 path, and existing atomic/fsync/HTTP-accounting helpers. Preserve v1 `BootstrapOperationJournal` semantics and supersession logic. No new general-purpose service, timer, or daemon.

- Make one source-local authority record the atomic owner of reservation plus invocation consumption; journals/receipts reference that authority rather than independently deciding the count.
- Implement initial claim, identical-grant recovery claim, immutable terminal evidence, and release according to §4. Prove all operations are idempotent at their named durable boundaries. Never infer authority from PID liveness or elapsed time.
- Reuse permit-before-send semantics and conservative cumulative paid counting. Refuse when either operation or applicable outer budget cannot issue a permit. Do not refund an uncertain permit after a crash or reset counts because the transaction is absent.
- Reject replacement grants, additional recovery, missing/corrupt authority, or v2 supersession. Preserve all evidence on refusal. Per-process provider hooks must not be overwritten by a second accounting context; compose permits explicitly and prove both gates execute before transport.
- No runtime reservation is created during development. All state-machine and transport evidence uses synthetic grants and fake endpoints under temporary roots.

**Gate/evidence:** V3 crash matrix and V4 accounting. Include two concurrent initial claimants; kill before/after each atomic/fsync boundary; journal-mirror interruption; permit consumed before network; lost response; and ordinal 3 denial. The independent oracle counts authoritative claims and intercepted transport attempts, not implementation-reported counters alone.

### T3 — Enforced cooperation and watcher deferral

**Depends on:** T2. **Lane:** Cursor.
**Deliverable:** reservation enforcement across all relevant mutation paths, with a distinct, non-quarantining watcher deferral and demonstrable unrelated-source progress.

**Surfaces:** `purge_locks.py`, `chroma_write_store.py`, `ingest.py`, `incremental_jsonl.py`, `convmem.py`, `watch.py`, `source_purge.py`, `incremental_retry_state.py`; narrow source-scope hooks in `ingest_dedupe.py`, `inter_model_index.py`, and repository-knowledge writers if required by the coverage inventory. Changes are limited to consulting/propagating the bootstrap restriction. Other arcs' authority and admission policy stay unchanged.

- Produce the closed writer inventory in §5 before enabling v2 execution. Cover provider admission and mutation separately. An `rg` list or PID census alone is not evidence that all paths enforce the restriction.
- Add a narrow bootstrap source-scope context to existing governed writes: canonical affected source(s), and validated operation ownership only for the bootstrap owner. Ordinary writers cannot self-assert ownership with a string. Unknown/unscoped mutations that could affect a reservation refuse; known disjoint source writes may proceed. With no reservation, preserve existing behavior.
- Enforce the restriction under C1 and at guarded Chroma mutation dispatch, with equivalent checks for sidecars and source-state mutations. A caller must not bypass it by skipping an entrypoint check, taking C1 early, using a raw store, or publishing a stale processed snapshot. Keep raw production clients denied.
- Reserve/check source preparation before provider work. Reuse the existing incremental lock for incremental operations. For legacy preparation, use a source-scoped shared preparation lease that bootstrap claims exclusively and non-blockingly at reservation time. Publish the reservation while holding that exclusive lease and the ordered source/C1 locks, then release the preparation lease; future preparation checks the durable reservation under the lease before any call. A busy lease means `source_writer_busy`, no paid work or initial claim. This closes the admission race without holding C1 during provider work or waiting on a legacy writer that needs C1 to finish.
- Ordinary legacy work already admitted must also recheck the durable reservation immediately before committing. It must not commit stale results after adoption. Source-preparation participation must be demonstrated for the actual writer revision; old writers lacking this protocol block live readiness.
- Emit a dedicated typed `coordination_deferral` with a dedicated nonzero CLI exit code, distinct from 0/1/91 and native/time-out statuses; freeze the exact unused value in T3 evidence. Carry canonical source, operation identity, and authority revision only. Validate the child signal against the path it was launched for; malformed/spoofed signals remain failures.
- Route that type through `_index_one_file`, incremental exception handling, CLI mapping, `_flush_path_subprocess`, and `_process_ready_path` before retry/quarantine handling. Do not call `_raise_incremental_retry_refusal`, `record_incremental_retry_failure`, `record_refusal`, `record_failure`, or `record_success` for a valid coordination deferral. Keep the event pending using existing debounce machinery with bounded backoff; do not busy-loop or launch another child immediately. If authority becomes terminal before the parent reads the signal, retain it as a non-successful deferral and schedule an ordinary later recheck; never reinterpret it as successful indexing.
- Preserve pre-existing quarantine. A quarantined path stays skipped before child launch. A successful one-shot operation does not clear it, so restoration of automatic coverage may remain a separate Ryan-owned action.

**Gate/evidence:** V5 two-process writer coverage, V6 watcher results, plus existing exclusion/processed/C1 guard regressions. Broken controls must allow a same-source legacy commit or route deferral to exit 91; the corresponding assertions must fail. Show another source makes progress while the owner is transforming, including its processed/export records.

### T4 — Bounded-prefix coordinator execution and source-only recovery

**Depends on:** T3. **Lane:** Cursor.
**Deliverable:** v2 bootstrap/recovery through the existing coordinator with exact selected-prefix work and safe follower completion.

**Surfaces:** `scripts/bootstrap-incremental-jsonl.py`, `incremental_jsonl.py`, `incremental_jsonl_production.py`, focused v2 helpers, and existing processed/export/dedupe helpers. Use current format adapters unchanged unless a demonstrated contract mismatch requires returning to Ryan.

- Thread the validated v2 capability through the production boundary and coordinator without writing config or broadening admission. Keep the configured source predicate, identity checks, embedding dimension, and no-fallback rules. Full rebuild remains disallowed for this one-shot operation even if live config permits it elsewhere.
- Capture exactly the grant's complete prefix with the existing rollout parser and source-read protections. A later pure append is not additional granted work. Validate prefix/device/inode/session before preparation and again under commit locks. Preserve chunk size/overlap and count only selected-prefix chunks.
- Revalidate reservation ownership, runtime/config/descriptor, exclusions, and source projection lineage under the ordered locks before mutation. Refuse a processed-hash/projection identity collision owned by another source rather than overwriting its entry. Preserve the existing source-specific before-images, original APPLYING rollback hash, checkpoint-before-follower ordering, and governed write sessions.
- Integrate owner-scoped processed publication and terminal receipts. Finish export/dedupe/processed followers from a committed checkpoint without retransforming, even if transaction cleanup already occurred. Before `_cleanup()`, fsync the authority's checkpoint digest, transaction/prepared lineage and original rollback digest; until then retain transaction evidence. A crash after checkpoint but before this authority update recovers through the retained transaction. Missing both forms of proof refuses. Reuse the coordinator's existing externally-held-source-lock path rather than recursively taking its incremental lock.
- Correct v2 rollback paths to merge against current processed state under `_processed_lock`; never call `save_processed()` with a stale whole-store snapshot. Export and dedupe repair must preserve foreign bytes, blank/malformed lines, line endings, ordering, and foreign records added between attempts. Remove only attributable transaction/source effects. Unknown ownership refuses without a whole-file rewind.
- Retain prepared data and original rollback authority through unsuccessful recovery. Terminal release is permitted only with verified source/checkpoint/follower state or proven rollback and the durable receipt. Existing Kiro recovery continues to pass its original contract tests.
- Before paid work, honor the exact permitted `bootstrap_required` eligibility exception. Other retry/fault holds refuse. Neither success nor failure calls generic quarantine/retry clearing helpers on the v2 path.

**Gate/evidence:** V7 selected-prefix and recovery integration with real temporary Chroma. Crash before/after both collection mutations, rollback publication, checkpoint, each follower, receipt, and release. Interleave unrelated writer commits between attempts and compare foreign bytes/rows with an independent oracle. No second-generation transforms after a committed checkpoint.

### T5 — Integrated evidence and an honest readiness result

**Depends on:** T4. **Lane:** Cursor, followed by independent Kiro review.
**Deliverable:** filled VERIFY evidence for the exact implementation revision and a metadata-only preflight packet showing which live gates remain closed.

- Run only the approved hermetic suite after a boundary probe proves network denial, temporary HOME/config/data, no production mount writes, and no live failure-log append. Cover command → coordinator → permit → stores → receipt and command → watcher-parent paths, not only isolated helpers.
- Extend existing bootstrap command/safety/supersession, Codex corrective, watcher, processed/exclude-race, purge-lock, and guarded-writer tests. Add focused v2 protocol/race fixtures. Record exact selected test paths, commands, interpreter, counts, exit codes, and subject SHA. Repository-wide tests require a separately established isolation boundary; do not run them against host defaults.
- Run applicable static checks without weakening baselines. Record each V0–V8 result as PASS/FAIL/SKIP with evidence; SKIP of an applicable proof cannot yield implementation PASS.
- Include metadata-only receipts, transport/claim counts, deterministic race ordering, original rollback hashes, foreign-byte comparisons, and negative-control results. Do not include synthetic or real message/prompt bodies in handoff output.
- Record BugBot applicability for the later implementation as required under `EXECUTE-TASK.md`; the current no-PR rule remains in force. A later authorized PR and exact-tip PR-native evidence are prerequisites to merge readiness. A local review or Kiro PASS does not replace that gate. Do not create a PR or post a review-trigger comment without the appropriate later grant.
- Report `IMPLEMENTATION_EVIDENCE` separately from `LIVE_READINESS`. A missing outer-budget enforcement contract, compatible writer rollout, healthy doctor baseline, or exact backup/source authority means `LIVE_READINESS=NO_GO`, even if all hermetic code checks pass.

**Gate/evidence:** V0–V8 complete, exact-tip Kiro review, remaining live gates explicitly owned. No implementation close or A1 execution inferred from a green test suite.

## 4. Required durable protocol (T2/T4 contract)

### Single authority and lock order

Use one private, atomically replaced and fsynced **v2 authority file under the correct Codex source state directory**. It contains the immutable grant/binding, operation identity, monotonic revision, reservation state, consumed invocation ordinal (1 or 2), durable progress references, and terminal evidence reference when present. Progress references bind transaction/prepared lineage, original rollback digest, and checkpoint digest before transaction cleanup. It is simultaneously the reservation and invocation-consumption authority; do not create a separate independently authoritative reservation pointer. Keep terminal records instead of unlinking this authority. Journal start/terminal records are recoverable evidence mirrors, never another counter that can diverge and grant extra work.

All owner transitions require the existing incremental source lock and canonical source/C1 protection. Initial claim order is incremental owner lock → preparation lease (exclusive, try-only) → canonical source → C1 → writer/session and leaf locks as applicable. The preparation lease is never awaited while holding C1. Ordinary preparation holds its shared lease while doing provider work and source/C1 commits; it never acquires the incremental owner lock while holding that lease. An incremental path takes its incremental lock before entering preparation participation. Fix this ordering in assertions and tests; do not add a reverse acquisition in cleanup/recovery. Processed and export locks are leaf locks; never acquire source/C1 while holding them. Avoid nesting processed and export locks with one another.

Paid-ledger updates take only their operation accounting lock, outside C1/Chroma sessions. No accounting lock is held while acquiring owner/source/C1 locks. Host enforcement and approved writer versions are prerequisites; advisory locking does not defend against arbitrary uncooperative host programs.

### Durable boundaries and outcomes

- **No authority:** pure preflight may run. Under ordered locks, check all source operation artifacts. Only proven absence permits an initial claim. Unexplained journals, incompatible transactions, or a different operation refuse.
- **Initial claim:** publish one atomic authority revision containing `RESERVED`, the complete grant/binding, and `invocation_ordinal=1`. File and directory fsync must complete before releasing locks or doing any provider work. This publication consumes the initial invocation even if a crash occurs before a journal mirror or transaction. If publication was not durable, zero providers may have run. Temporary/ambiguous evidence fails closed; do not count it as a fresh grant.
- **Reservation, no transaction:** the identical grant may claim ordinal 2 after validating the authority and all surviving journal/permit evidence. The absence of a transaction is an explicitly supported v2 recovery state, not v1's `recovery_not_available`. Create the missing evidence mirrors idempotently, then prepare under remaining paid budget. No normal ingest or fresh grant can take over.
- **PREPARING/transform_failed:** ordinal 2 resumes only the identical prefix/descriptor/grant using durable prepared outputs and the cumulative permit ledger. Lost/uncertain transport outcomes count as spent; malformed/truncated accounting blocks transport.
- **APPLYING:** validate the original rollback authority and prepared evidence before any mutation. Reuse that rollback hash for roll-forward or source-only restore. A missing/replaced journal gives `recovery_unproven`; never snapshot the partly applied projection as a new baseline.
- **Checkpoint committed, followers/receipt incomplete:** ordinal 2 may finish only missing publication/evidence and verify lineage without provider transforms, even if transaction/rollback cleanup already ran. Require the authority-bound checkpoint identity and matching prepared/transaction lineage evidence; absent proof refuses. No replay of a committed transform because the terminal receipt is missing.
- **Terminal receipt:** fsync a receipt identifying the proven terminal source/follower state, then atomically publish authority `TERMINAL` with `reservation_active=false` and the receipt digest. A crash before that authority update leaves the reservation active; same-grant recovery may finalize it within the existing allowance. A crash afterward leaves an inactive, immutable terminal record even if an auxiliary mirror is missing. A fresh invocation against TERMINAL reports already terminal and grants no work.
- **Second invocation interrupted/exhausted:** do not permit a third invocation, even for apparently harmless cleanup. Leave the reservation active unless the terminal authority publication already completed. Ryan owns a separately reviewed exact-state recovery/release decision. Receipt generation cannot increase the invocation count or paid allowance.

Reject rollback of authority revision/counters and mismatches between authority, manifests, permits, transaction, or checkpoint. Corruption must not select the more permissive record. Existing v1 journals retain their original interpretation and directory layout.

## 5. Writer coverage closure (T3 contract)

The evidence inventory must give each entrypoint its canonical source scope, preparation participation, mutation check, locks, negative test, and live compatibility status. Required baseline coverage:

- **Bootstrap owner and ordinary incremental:** `bootstrap()`, `IncrementalJsonlCoordinator.run()`, `_commit_generation()`, `_restore_replay_before_images()`, `_publish_processed()`, cleanup, and live retry wrappers. Ownership derives from validated v2 authority, never `bootstrap_existing=True` alone.
- **Manual/watcher legacy indexing:** `ingest._index_one_file`, `_commit_chunk_to_stores`, `_snapshot_reindex_rows`, `_prune_completed_reindex`, and the direct `--now` route. An in-flight legacy preparation must prevent initial reservation or be denied before commit; prove both race orders.
- **Shared Chroma mutations:** `purge_locks.index_write_flock` / `require_index_write_lock_held` and `chroma_write_store._IndexWriteGuardedChromaStore`. Cover nested sessions and mutation methods lacking a source argument. Unknown scope refuses when a reservation could be affected. Preserve existing read allowlists and guard policies.
- **Processed/exclusion:** `mutate_processed`, `commit_processed_index_entry`, exclusion/undo entrypoints, and v2 rollback. Reservation checks and reload/merge must be atomic with the processed lock. No raw whole-file publication may escape the restriction.
- **Export/dedupe:** source reconciliation, `ingest_dedupe` append/restore, `source_purge` sinks, and `_compact_units_export_after_index`. Global compaction is unscoped maintenance and must defer while an active reservation could be affected; it must not rewrite foreign bytes during recovery. If a disjoint source has already committed, deferring its optional global compaction must preserve that successful source result, emit only maintenance-deferral metadata, and avoid a source failure/retry or duplicate paid work.
- **Source state:** retry clearing, checkpoint migration, purge/exclusion, and cleanup that could remove authority. Refuse conflicting operations; do not expand migration or recovery-arc functionality.
- **Other existing writers:** inter-model/repository-knowledge indexing, refine/monitor/add/forget/verify, and recovery/cutover callers. Prove they are disjoint through an enforced scope, or conservatively refuse at existing shared boundaries. Do not edit their business logic to obtain a green inventory. Any uncovered direct store/sidecar path is a blocker.

Where a shared deny rule safely covers a caller, list that evidence instead of editing every caller. If complete coverage requires a generic admission redesign, a new unbounded writer registry, or another arc's policy change, stop and return the specific gap to Ryan. Do not downgrade complete mediation to an operator promise.

## 6. Verification design and evidence limits

All tests are future Execute obligations. Use synthetic sources and temporary data only. Read the test isolation setup before importing modules that cache config/paths. Redirect synthesis failure logging before exercising provider failures. Network denial must be enforced outside the process under test and checked by an attempted forbidden connection; fake credentials alone are insufficient.

Use a parent-process oracle for two-process barriers, kill points, authoritative file snapshots, transport counters, and raw foreign-file bytes. Assert both sides of every durable boundary, including failed fsync/replace, lock timeout, same-source concurrent admission, and foreign writes between recovery attempts. Count consumed invocations from authoritative records and sends from intercepted transport. A test that only accepts the code's own receipt is insufficient.

Required negative controls: retain Kiro state-ID derivation; allow a third invocation; remove permit-before-send; omit legacy mutation recheck; map deferral to exit 91; restore stale processed bytes; replace original APPLYING rollback authority; normalize foreign dedupe lines. Each corresponding proof must fail on its broken variant. Keep controls in disposable hermetic fixtures; never modify a production runtime.

V1 regressions must cover strict grant shape/hash fixtures, provider binding, one-recovery accounting, and predecessor-preserving supersession. Live source counts/hashes from the old A1 packet are historical metadata, not test fixtures or current approval.

## 7. Operational readiness remains separately gated

The following gates have owners and cannot be silently satisfied by implementation:

1. **Outer paid budget — Ryan/Claude:** identify the actual 3,000-call canary guard and prove whether it mediates one-shot processes. `llm.provider_http_accounting` currently replaces its ContextVar callback; nesting it is not proof of composition. Before live execution, require a reviewed enforcement interface or quota-allocation procedure that reserves against the shared ceiling atomically. Missing enforcement returns `outer_budget_unverified` before reservation or transport. This plan authorizes no new generic budget service or changes to the canary's ceiling. Hermetic composition evidence is required; actual production integration remains blocked until the owner supplies and approves the exact contract.
2. **Writer compatibility — Ryan/operational owner:** prove the deployed watcher parent, spawned children, manual wrappers, backfill jobs, and shared mutation libraries participate in this protocol. Old cached parent code matters independently of child revision. No unknown writer, incompatible binary, or ambiguous participant may be treated as compatible. Deployment/restart, if needed, needs a separate grant; current limits prohibit it.
3. **Health — Ryan/operational owner:** Kiro reported doctor exit 0 during the direction review. This is later evidence than A2's rc-1 `ledger_documents: database is locked`, but does not diagnose that failure or resume A2. Record a fresh healthy baseline and a bounded diagnosis before live A1; A2 stays stopped under its own handoff.
4. **Backup/source authority — Ryan:** refresh exact local/offsite IDs, consistency/coverage and copy lineage; approve transcript recovery disposition; revalidate all three canonical paths, prefix/session/inode, runtime/config/provider/descriptor bindings and numeric budgets. Retain the skip-if-modified-within-30-minutes rule. Never copy or print transcripts as planning evidence.
5. **Execution authority — Ryan:** after implementation review and an authorized compatible deployment, approve the exact refreshed A1 operation(s), serial order, paid caps, one recovery, and bounded lock waits. The historical proposal of 2/1/1 chunks and 4/2/2 paid attempts is not granted. A bare “go A1” cannot override incompatibility or failed readiness gates.

For any future authorized run, stop the owned run if any observed index process exceeds 4 GB RSS or doctor reports a new FAIL. Do not kill another lane's process, clear holds, or discard recovery evidence. Whole-store restoration and release after exhausted recovery require separate authority.

## 8. Handoff and stop

**Now:** Kiro reviews this execution plan and its VERIFY stub at the exact committed revision. A rejection routes to Ryan before Codex revises; non-blocking precision comments are recorded with the verdict. **Next authorization:** Ryan explicitly grants Cursor T1–T5 implementation and hermetic verification of the reviewed revision. Cursor must not infer PR, deployment, or live-operation authority.

Cursor's handoff must identify branch/base/subject SHA, each task's evidence, remaining blockers and owners, and the exact VERIFY file. Push each implementation commit with an explicit branch refspec. Do not declare production-ready while §7 contains an unresolved gate. No record/ledger write is requested.

**Stop: Await HITL — Kiro plan review and Ryan Cursor implementation authorization.**

**TL;DR:** [Arc Codex] Five serial tasks bind Codex identity, make reservation/invocation consumption crash-safe, enforce writer cooperation and scoped watcher deferral, preserve source-only recovery, and produce hermetic evidence. A1 remains parked; A2 remains stopped. Live budgets, deployment, backups, and execution remain separately gated.

<!-- src: ./ARCHITECTURE-issue-286-codex-bootstrap-corrective.md — Kiro PASS at e0e91bd; Ryan approved direction in conversation -->
<!-- src: ../../scripts/bootstrap-incremental-jsonl.py, ../../bootstrap_safety.py, ../../incremental_jsonl.py, ../../purge_locks.py, ../../chroma_write_store.py, ../../ingest.py, ../../watch.py, ../../llm.py — pinned code contracts and integration points -->
<!-- ref: ./VERIFY-issue-286-codex-bootstrap-corrective.md, ./STATUS-codex-jsonl-production-integration.md, ../planning/EXECUTION-PLANNING.md — evidence and phase gates -->

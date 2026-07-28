# Execution Plan — Shadow Phase 0 Activation Corrective

**Who:** Codex planning lane, for Ryan's plan review and later bounded Cursor
implementation authorization.
**What:** Corrective architecture and execution plan for the Shadow Phase 0
activation blockers and high-severity findings.
**When:** 2026-07-28, verified at repository revision
83b8c11683c1295579c4fad9c8316f9f8fc3d10f, which contains Ryan's merged
disabled-by-default Phase 0 implementation
4535107143279c87e8b34c1eab7e4dee88bffc68.
**Why:** The current implementation is safe while disabled, but it has no
gap-free activation transaction, accepts materially invalid artifacts, can
expose the first payload through file permissions, can report false-green
status, and has no production-filesystem performance proof.
**How:** Keep Shadow disabled; implement one strict validation contract, a
writer gate and activation state machine, secure artifact creation, truthful
doctor/inventory views, and an operator-approved performance canary in bounded
slices.

**Current verdict:** HOLD / NOT READY.

This document is planning only. It does not authorize implementation,
activation, live configuration changes, Chroma mutations, Shadow artifact
creation, ledger or manifest changes, health-sidecar changes, backup changes,
or production-setting changes.

## 1. Verified current state

### Subject and non-mutation evidence

- The planning branch is
  plan/2026-07-28-shadow-phase0-activation-corrective, pinned to the reviewed
  revision above.
- convmem doctor reports shadow_ledger: disabled. No live Shadow configuration
  or artifact was changed during this planning pass.
- The focused command remains green:

      pytest -q tests/test_shadow_ledger_phase0_t*.py \
        tests/test_shadow_writer_coverage_scan.py
      61 passed

- Repository search finds shadow-inventory, but no Shadow activation CLI or
  activation script.

### Finding verification

| Finding | Repository evidence | Consequence |
|---|---|---|
| No activation operation | convmem.py registers inventory only. shadow_ledger.py provides manifest data helpers but no writer quiescence, configuration transaction, or recovery state machine. | Baseline and enablement cannot be made gap-free or crash-recoverable. |
| Factory validation incomplete | decide_sink_injection checks enabled, configured/caller root, shallow non-null manifest fields, and manifest root. It does not validate versions, collection identity, revision, counts, hashes, sequence, ledger identity/content, ownership, permissions, symlinks, or path collisions. | Unsupported or inconsistent artifacts may attach a sink. |
| First-write privacy failure | JsonlUnitMutationSink opens with a+b, writes and flushes payload, then chmods only after successful fsync. Permission errors are swallowed. | Under umask 022, first-fsync failure can leave payload bytes at 0644. |
| Doctor/inventory false green | Doctor interprets only root refusal and can call other refusals healthy. Inventory does not use factory validation, treats active as total, suppresses Chroma-only IDs when Shadow is empty, ignores the manifest, and treats missing/unreadable health as healthy empty data. | Operator status can disagree with the writer factory and conceal invalid activation state. |
| Scaling unproved | Append scans the full ledger for event ID and scans it again for sequence. Recorded latency stops before health-sidecar persistence. | Steady-state latency is linear in ledger length and current telemetry excludes synchronous work. |
| Paths insufficiently validated | resolve_path follows symlinks; no descriptor identity, owner, type, privacy, containment, or collision contract exists. | Artifacts may alias one another, point inside Chroma, or be replaced through unsafe filesystem objects. |

Two isolated, non-production probes reproduced the critical failures:

    {"malformed_manifest_corrupt_ledger_inject": true}
    {"first_fsync_failure_mode": "0o644", "payload_present": true}

The malformed probe combined unsupported manifest/schema versions, negative
counts and starting sequence, wrong code revision, a ledger-identity mismatch,
and a corrupt ledger. This was a temporary diagnostic probe, not activation.

### Guarantees that must remain true

1. Chroma knowledge_units remains Tier-1 and authoritative.
2. Shadow remains disabled by default; absent configuration equals disabled.
3. Every production unit writer continues through one write-store boundary;
   no direct production bypass is introduced.
4. Shadow failure never reverses or changes the result of a successful Chroma
   mutation.
5. Canonical Chroma-root mismatch refuses sink injection.
6. Disposable replay remains isolated and sink-free.
7. Local/offsite complete-data-v2 backup lineage remains unchanged.
8. The existing 61 focused tests remain green.
9. The provisional vocabulary and delta-only authority claim remain unchanged.

## 2. Corrective architecture

### Summary

The correction uses four deep boundaries:

1. New shadow_validation.py owns all eligibility truth and returns stable
   refusal codes plus typed validated facts. Factory, activation, doctor,
   inventory, and verification render this same result.
2. chroma_write_store.py owns a production writer lease. Each production write
   session takes a shared flock before loading live config and holds it until
   store close. Activation takes the exclusive form of the same lock.
3. New shadow_activation.py owns the persistent activation state machine,
   quiesced baseline, staged install, atomic config commit/rollback, and crash
   recovery.
4. shadow_ledger.py and shadow_sink.py own secure private artifacts. Creation is
   descriptor-relative, exclusive, no-follow, owner-checked, and mode 0600
   before bytes. Append reads only a bounded tail and permits repeated event IDs
   as the locked Architecture already allows.

This is a local orchestrated saga, not a service split or Chroma redesign.

### Finding 1 — no activation operation

| Required item | Plan |
|---|---|
| Root cause | Phase 0 deliberately deferred activation and supplied no writer-wide transaction boundary. |
| Invariant | No writer can mutate Chroma between baseline capture and the point where all later writers reload committed config and attach a validated sink. |
| Modules | New shadow_activation.py; chroma_write_store.py; thin convmem.py commands; config.py; all production factory call sites; activation tests. |
| Design | Suspend known services, acquire exclusive writer gate, capture two identical deterministic snapshots, stage/validate artifacts, recheck config preimage, atomically replace config as commit point, release gate, resume writers, observe first real event. |
| Failure/rollback | Precommit leaves config disabled and removes only transaction-owned staging. Postcommit reacquires the gate and atomically disables Shadow; Chroma is never undone. |
| Unit tests | Transition table, invalid transitions, semantic config diff, stale preimage refusal, recovery classification, commit ordering. |
| Integration tests | Multiprocess writer blocks behind activation, reloads enabled config after release, and emits first event. |
| Fault injection | Kill after every state/rename/fsync; config fsync failure; writer-gate timeout; interrupt immediately before/after config replace. |
| Operational verification | Prove services inactive, acquire exclusive gate, match two snapshots, review strict report, retain hashed transaction evidence. |
| Acceptance gate | No uncaptured interleaving; every crash recovers as disabled/uncommitted or committed/strictly valid; stale config cannot write after commit. |

### Finding 2 — factory validation incomplete

| Required item | Plan |
|---|---|
| Root cause | manifest_is_complete checks non-null presence, while policy is duplicated across partial consumers. |
| Invariant | A sink exists only after one validator proves supported versions, identity bindings, baseline integrity, private uncorrupted ledger, safe paths, and committed activation. |
| Modules | New shadow_validation.py; shadow_ledger.py; chroma_readonly.py; chroma_write_store.py; doctor/inventory consumers; validator tests. |
| Design | Introduce ShadowValidationResult and ShadowRefusal. Writer mode validates committed static bindings and live collection/revision; prepare mode also recomputes the quiesced baseline. |
| Failure/rollback | Factory refuses only the sink, logs exact codes, and preserves Chroma success. Enabled invalid state is doctor/readiness FAIL and requires disable rollback. |
| Unit tests | One per refusal code, simultaneous reasons, stable order, valid fixture, versions, counts/hashes, UUID, revision, sequence, identity, file metadata. |
| Integration tests | Factory, doctor, inventory, prepare, and verify return the same codes for the same fixture. |
| Fault injection | Truncated header, invalid middle, swapped ledger, changed manifest, replaced collection, chmod/chown failure, hardlink/symlink, unsupported version. |
| Operational verification | Redacted result retains SHA, collection UUID, manifest hash, ledger inode/identity, counts, and codes. |
| Acceptance gate | The malformed/corrupt probe returns inject=false with all applicable specific codes. |

### Finding 3 — first-write privacy failure

| Required item | Plan |
|---|---|
| Root cause | a+b creation follows umask; chmod follows payload and successful fsync; chmod failure is ignored. |
| Invariant | Before byte one, the ledger is a current-user-owned regular file, exact 0600, link count one, opened without symlink traversal. |
| Modules | shadow_ledger.py, shadow_sink.py, secure-creation/fault tests. |
| Design | Open validated parent with O_DIRECTORY and O_NOFOLLOW; create using O_CREAT, O_EXCL, O_NOFOLLOW, O_CLOEXEC and mode 0600; fchmod/fstat; only then write a non-payload identity header. |
| Failure/rollback | Any create/owner/mode/write/fsync failure leaves config disabled. Explicit abort may remove only matching uncommitted activation/inode artifacts. |
| Unit tests | Umask 000/022/077; mode before first write; existing path; owner/mode/link/type; private directory. |
| Integration tests | Header-only staged ledger installs at 0600 and first postcommit event does not alter it. |
| Fault injection | First write, short write, flush, fsync, directory fsync, fchmod, fstat, rename, sidecar, symlink race. |
| Operational verification | Retain redacted UID, mode, device/inode, link count, header hash. |
| Acceptance gate | The current 0644 payload reproduction becomes impossible. |

### Finding 4 — doctor and inventory false green

| Required item | Plan |
|---|---|
| Root cause | Surfaces infer state separately; unreadable inputs become empty/healthy; active/total and empty-Shadow differences are wrong. |
| Invariant | Writer eligibility, readiness, and human summary are projections of one result. Enabled invalid state is never PASS or WARN-only. |
| Modules | doctor.py, shadow_inventory.py, convmem.py, shadow_validation.py, chroma_readonly.py, related tests. |
| Design | Doctor maps blocking refusals to FAIL. Inventory always calculates current Chroma IDs minus touched Shadow IDs, separates active/historical/total, carries shared validation, and names disabled/prepared/committed/observing/degraded/invalid. |
| Failure/rollback | Reporting never mutates. Missing/corrupt inputs are null/unknown plus codes, never zero or healthy defaults. |
| Unit tests | Every mapping, missing/corrupt files, empty Shadow/nonempty Chroma, all superseded, active/historical, multiple reasons, redaction. |
| Integration tests | One fixture through validator, factory, doctor, text/JSON inventory; identical blocking codes. |
| Fault injection | Disappearing files, malformed sidecar, collection read failure, artifact swap, permission drift. |
| Operational verification | All surfaces show the same activation ID, state, and refusal set. |
| Acceptance gate | Missing/invalid manifest, corrupt ledger, baseline mismatch, empty Shadow, and Chroma-only fixtures cannot be false green or false zero. |

### Finding 5 — latency and scaling unproved

| Required item | Plan |
|---|---|
| Root cause | Two full scans per append; complete timing excludes health persistence; no same-filesystem canary. |
| Invariant | Steady append cost is independent of ledger length except event bytes, telemetry covers all synchronous work, and activation waits for approved budgets and canary PASS. |
| Modules | shadow_sink.py; new shadow_canary.py; thin convmem.py CLI; health schema; performance tests. |
| Design | Stop append-time duplicate suppression; replay already applies first valid duplicate. Read last header/event for next sequence. Time lock through health fsync/rename/parent handling and return. |
| Failure/rollback | Canary failure leaves disabled. Live threshold breach atomically disables Shadow under writer gate. |
| Unit tests | Tail/header sequence, repeated-ID lines, timer boundaries, bounded bytes read, health included. |
| Integration tests | Representative sizes/volumes/concurrency in private scratch on intended ledger filesystem, never live paths. |
| Fault injection | Slow ledger/health fsync, contention, short write, disk/inode full, concurrent writers. |
| Operational verification | Retain raw timings, percentiles, mount/environment, size/volume/concurrency, SHA, validator result. |
| Acceptance gate | Correctness plus all Ryan-approved absolute/degradation limits pass; 500 ms is not silently promoted to an SLO. |

### Finding 6 — configured paths insufficiently validated

| Required item | Plan |
|---|---|
| Root cause | Canonical string resolution is mistaken for filesystem safety. |
| Invariant | All artifacts are mechanically distinct where required, never in/aliasing Chroma, private/current-owner/regular, with no symlink component. |
| Modules | shadow_validation.py, shadow_ledger.py, shadow_activation.py, config.py, path tests. |
| Design | Validate lexical paths before create and descriptor/inode identity after open. Require pairwise distinct targets, exact file mode, private parent, owner, type, link count, and Chroma exclusion. |
| Failure/rollback | Refuse before write where possible; abort on post-open mismatch; never replace unrelated existing paths. Committed failure causes sink refusal and disable. |
| Unit tests | Same/normalized path, symlink leaf/parent, hardlink, FIFO/socket/dir, wrong owner/mode, unsafe parent, inside Chroma, existing file. |
| Integration tests | Safe sibling prepare; replace one artifact between stages; commit refuses without config touch. |
| Fault injection | TOCTOU rename/symlink, chmod/chown, parent replacement, device change, artifact swap. |
| Operational verification | Retain canonical path, device/inode, owner, mode, link count, parent identity, separation. |
| Acceptance gate | Every unsafe class has a stable code and fails before payload or commit; no artifact can replace another. |

### Necessary versus deferred

Necessary: strict validator; writer gate/post-gate config reload; activation and
atomic disable; secure creation/identity binding; truthful doctor/inventory;
bounded append/full latency telemetry; production-filesystem canary; crash/fault
tests; runbook.

Deferred: Bloom/event indexes, compaction/rotation, async/group fsync, automatic
healing, historic rebuild, Chroma redesign, canonical-schema migration, later
Shadow phases, and backup-policy changes.

## 3. File-by-file change map

| File | Planned responsibility |
|---|---|
| shadow_validation.py (new) | Typed modes/results/refusals and all manifest, ledger, collection, path, revision, baseline, commit validation. |
| shadow_activation.py (new) | Journal, transitions, baseline, staged install, config commit/rollback, recovery, first-event verification. |
| shadow_canary.py (new) | Workload/canary runner, redacted evidence, budget evaluation. |
| shadow_ledger.py | Strict manifest/header schema, baseline digest, private descriptor-relative file helpers. |
| shadow_sink.py | Secure open, bounded-tail append, duplicate-line behavior, complete timing, activation identity in health. |
| chroma_write_store.py | Shared writer lease, live config load after lease, shared validator, separate test-only override. |
| chroma_readonly.py | Collection UUID/identity and deterministic baseline snapshot with active/total classification. |
| config.py | Explicit config-path/preimage helpers; no automatic activation. |
| doctor.py | Render shared validation and enabled-invalid FAIL. |
| shadow_inventory.py | Shared result and corrected counts/state/readiness. |
| convmem.py | Thin shadow-activate, shadow-rollback, and shadow-canary adapters only. |
| chroma_store.py | Preserve post-Chroma observer behavior; change only if a minimal close hook is required for lease lifetime. |
| ingest.py, inter_model_index.py, observe.py, propose_decision.py, refine.py, source_purge.py, production commands in convmem.py | Move every production open to the lease-owning session API. |
| tests/test_shadow_validation.py (new) | Refusal and cross-consumer matrix. |
| tests/test_shadow_activation.py (new) | State machine, quiescence, crash, commit/rollback. |
| tests/test_shadow_canary.py (new) | Workload, full timer, budgets, redaction. |
| Existing T1/T3/T5 and writer scan tests | Strict regressions while preserving Phase 0 gates. |
| config.example.toml | Disabled defaults and activation identity after contract approval; remains false. |
| PHASE0 contract, writer inventory, Execute VERIFY | Align evidence without rewriting locked Architecture. |

No slice may touch live config/Chroma/Shadow/JSONL authority, Restic settings,
backup timers, or production settings.

## 4. Activation state machine

    disabled
      → preparing
      → quiesced
      → baseline_captured
      → artifacts_validated
      → committed
      → first_event_observed
      → verified

| State | Durable evidence and exit |
|---|---|
| disabled | Config absent/false. Exit only with Ryan authorization, approved budgets, passing prerequisites. |
| preparing | Private journal: activation ID, SHA, config preimage, intended paths, committed=false. Validate disabled config and create 0700 staging. |
| quiesced | Exclusive gate plus journal owner PID/start. Recheck services/processes/config. Exclusive acquisition proves no compliant session is open or can start. |
| baseline_captured | Sorted entries, active/total, collection UUID, aggregate digest; two identical reads under the same gate. |
| artifacts_validated | Header-only staged ledger, complete manifest, candidate config, artifact hashes, strict PASS. |
| committed | Atomic config replacement has enabled=true, activation ID, exact paths and manifest hash; config directory fsynced. This is the commit point. |
| first_event_observed | First valid matching event is starting_sequence+1 and matches successful Chroma post-state. |
| verified | Doctor/inventory agree, canary evidence passes, no refusal codes, operator sign-off. Still delta-only. |

### Ordering and no-gap proof

1. Create journal/staging.
2. Suspend known writer services; acquire exclusive writer gate.
3. Capture two matching baselines.
4. Create staged ledger first among activation payload artifacts, at 0600, with
   non-payload header only.
5. Write/fsync manifest binding baseline, collection, ledger, SHA, sequence.
6. Generate/parse candidate config and prove only approved Shadow keys differ.
7. Strictly validate.
8. Install ledger then manifest while config stays disabled.
9. Recheck config preimage.
10. Atomically replace/fsync config. This is commit.
11. Release gate; new writers load config only after taking their shared lease.
12. Resume services; verify first real event.

Multiple renames are not called one transaction. The gate plus config-last makes
precommit artifacts inert.

All production write sessions take a shared lock before authoritative config
load and hold it through store close. Passing cached production config becomes
prohibited. Static writer census plus service revision checks defend against a
legacy bypass; any legacy writer is an abort condition.

### Failure transitions

| Failure point | Transition/compensation |
|---|---|
| preparing/quiesced | aborted_precommit → disabled; remove exact staging, release gate, resume. |
| baseline captured | Abort and invalidate baseline; never reuse after resume. |
| artifacts installed before config | prepared_not_committed → disabled; explicit identity/inode-scoped abort only. |
| crash during config replace | Disabled config means uncommitted; enabled matching config/manifest/header means committed; enabled mismatch means factory refusal and emergency disable. |
| committed before first event | rollback_pending → disabled_after_rollback under exclusive gate. |
| first event/verification failure | Same rollback; retain ledger and exact gap. |
| later health/performance breach | Disable Shadow only; never undo Chroma. |

Journal alone never decides commit. Matching enabled config, manifest hash/ID,
ledger header/identity, and strict validation do.

## 5. Shared validation contract

The single entry point is conceptually:

    validate_shadow_activation(config_path, chroma_dir, mode)
      -> ShadowValidationResult(
           state, inject_eligible, activation_id, refusals, facts)

Modes are writer, prepare, doctor, inventory, and verify. Mode selects expensive
checks but never changes code meaning. Refusals are deterministic, deduplicated,
stable ordered, redacted, and carry code/artifact/blocking/detail.

- Prepare recomputes the quiesced live baseline and staged paths.
- Writer validates committed static bindings, collection identity, revision,
  full ledger syntax/sequence, and path metadata once per write session.
- Doctor/inventory only render the core result.
- Verify adds first-event and canary gates.

### Required refusal codes

| Code | Condition |
|---|---|
| manifest_missing | Expected regular manifest absent. |
| manifest_corrupt | JSON/type/canonical-hash invalid. |
| manifest_version_unsupported | Version not exactly supported. |
| manifest_incomplete | Required field/status/binding absent. |
| collection_mismatch | Name or immutable collection UUID differs. |
| code_revision_mismatch | Runtime SHA differs from manifest. |
| baseline_count_invalid | Negative/inconsistent counts or entry classification mismatch. |
| baseline_hash_invalid | Entry hash or aggregate digest fails. |
| ledger_missing | Committed ledger absent. |
| ledger_corrupt | Header/event/schema/sequence/complete-line invalid. |
| ledger_identity_mismatch | Header ID/activation differs from manifest/config. |
| starting_sequence_invalid | Header/first/last sequence invalid or noncontiguous. |
| path_collision | Lexical/canonical/device-inode collision. |
| path_inside_chroma | Artifact at/beneath Chroma. |
| path_not_private | File/parent privacy policy fails. |
| path_wrong_owner | UID differs from production user. |
| symlink_refused | Leaf or traversed component is symlink. |
| permission_invalid | File not exact 0600 or directory policy fails. |
| prepared_not_committed | Prepared artifacts exist without matching committed config. |

Also keep specific codes for config_changed, config_corrupt,
config_activation_mismatch, health_missing, health_corrupt,
writer_quiesce_timeout, collection_unavailable, ledger_exists_unbound,
artifact_type_invalid, directory_not_private, first_event_missing,
first_event_mismatch, performance_budget_missing, and
performance_budget_exceeded.

Manifest/config/header share activation_id. Config records manifest SHA.
Manifest records collection UUID, ledger identity/header hash, versions, SHA,
counts, per-entity hashes/classification, aggregate digest, and start sequence.
Total equals entry count; active equals active classifications; historical is
derived. Prepare recomputes equality. After activation, writer validates baseline
internal integrity, not equality to naturally evolved current Chroma.

## 6. Secure file-creation design

1. Walk parents with lstat/descriptor opens; reject symlinks.
2. Require current-user directory ownership. New transaction directories are
   0700 before children; existing directory policy is an open decision below.
3. Require pairwise distinct paths/inodes and reject hardlinks/nonregular leaves.
4. Reject artifacts in Chroma.
5. Create ledger with parent dir descriptor and:

       os.open(name,
         O_WRONLY|O_CREAT|O_EXCL|O_NOFOLLOW|O_CLOEXEC,
         0o600, dir_fd=parent_fd)
       fchmod(0600)
       fstat: regular, uid=current, mode=0600, nlink=1
       write-all header
       fsync file
       fsync parent

No payload is available to creation; header has only versions, activation ID,
random ledger identity, UTC, and starting sequence.

Fresh preparation requires absent final ledger. Zero-byte files are not adopted.
An existing ledger is accepted only for exact crash recovery when journal,
activation ID, device/inode, header hash, and intended path match. Other valid
or historical files yield ledger_exists_unbound; no truncate/replace/reuse.

Short writes loop or fail. File or directory fsync failure leaves disabled.
Cleanup is explicit and activation-ID/inode scoped. After commit no automated
cleanup deletes ledger, manifest, or health.

## 7. Doctor and inventory truth model

| Shared state | Doctor | Inventory |
|---|---|---|
| disabled, no prepare | PASS disabled | PARTIAL disabled; all current Chroma IDs are Chroma-only relative to empty Shadow |
| prepared_not_committed | WARN exact code | PARTIAL prepared, never ready |
| committed, no first event | WARN awaiting event | PARTIAL insufficient evidence |
| observing, clean | PASS mechanism | PARTIAL or PASS—delta capture only per touched reconciliation |
| enabled blocking refusal | FAIL all codes | FAIL same codes |
| corruption | FAIL ledger_corrupt | FAIL ledger_corrupt |
| isolated health degradation | WARN then approved persistent threshold | PARTIAL/FAIL using same owner/threshold |
| rollback | PASS disabled plus disclosure | PARTIAL disabled_after_rollback |

Count names:

- total_unit_count: all knowledge_units rows;
- active_unit_count: not logically superseded/deleted;
- historical_unit_count: total minus active;
- shadow_touched_entity_count: event IDs excluding header;
- chroma_only_ids: current Chroma IDs minus touched IDs, unconditionally;
- baseline counts: separately labeled from current counts.

Missing/unreadable values are null/unknown plus code, never substituted zero or
healthy empty mapping. All surfaces show the same activation ID/state/codes.

## 8. Performance canary

Use a new private scratch directory on the same filesystem/mount options as the
intended ledger parent, outside live Shadow paths and Chroma. Never touch live
ledger. Time:

    lock attempt/acquire → tail/header → sequence → append → flush/fsync
    → unlock → atomic health temp/write/fsync/rename/parent handling → return

Measure cold factory validation separately from steady append.

| Dimension | Required cases |
|---|---|
| Event size | 1 KiB control; redacted live-derived P50/P95 encoded sizes; maximum supported size, all synthetic. |
| Ledger volume | Header-only; N=current total knowledge_units; 2N; Ryan-approved observation horizon. |
| Concurrency | One writer; refreshed production-census peak; one case above peak. |
| Runs | Three fresh independent runs per cell after warm-up. |
| Warm-up | At least 100 untimed appends or one second, whichever produces more. |
| Samples | At least 1,000 timed per steady cell unless Ryan approves a justified lower count. |
| Metrics | p50/p95/p99/max/mean/stddev, lock wait, ledger fsync, health work, complete latency, throughput, errors. |

Compare identical Chroma mutation workloads with disabled versus scratch-enabled
Shadow for end-to-end degradation.

### Threshold owner

No approved activation latency budget exists. Ryan must approve these before C6
implementation and activation:

| Symbol | Meaning |
|---|---|
| A_p99_ms | Maximum complete append p99. |
| A_max_ms | Maximum individual complete append. |
| D_p99_factor | Maximum p99 degradation versus disabled writer. |
| O_p99_ms | Maximum cold factory/open validation p99. |
| R_p99_ms / R_factor | Live rollback thresholds, no looser without rationale. |
| R_window | Consecutive samples/time window for performance rollback. |
| H_events | Observation-horizon volume beyond 2N. |

Existing 250 ms lock budget and 500 ms degraded marker are not activation SLOs
unless Ryan explicitly approves that role.

- Immediate FAIL: any corruption, sequence/privacy/path/refusal disagreement,
  lost event, payload leak, live-path contact, or nonzero errors.
- Performance FAIL: any required run exceeds approved A/D/O budgets.
- Activation block: missing values/cells/runs/provenance.
- Live rollback: strict validation immediately; performance after approved R
  threshold for R_window.

Retain private redacted summary plus raw timings, command, SHA, Python/kernel,
CPU/load, filesystem/mount, device, matrix, warm-up/sample count, budgets and
approver, percentiles/errors, and hashes. Retain for observation period plus 30
days. Use synthetic lengths, not production payloads.

## 9. Test and fault-injection matrix

| Area | Unit/integration | Faults | Gate |
|---|---|---|---|
| Lifecycle | Transition table; multiprocess prepare/commit/event/verify | Kill after each state/fsync/rename | Deterministic recovery; no gap |
| Writer gate | Shared/exclusive; stale config; lease close | Timeout/dead process | Exclusive is quiescence proof |
| Manifest/collection | Full refusal matrix; snapshot round trip | Truncate/swap/mutate/replace | Exact codes |
| Ledger privacy | Open/fstat/mode/owner; header then event | Umask, short write, fsync, chmod, symlink race | No payload nonprivate |
| Integrity/duplicates | Header/tail/sequence; concurrent append; repeat IDs | Invalid header/middle/tail, inode swap | Surfaces agree; no scan |
| Paths | Collision/containment/type matrix | TOCTOU, hardlink/symlink/parent swap | Refuse prewrite/commit |
| Doctor/inventory | Same fixture across surfaces; counts/redaction | Missing/corrupt inputs | No false green/zero |
| Chroma authority | Temp Chroma plus failing sink | Lock/disk/health failure | Chroma result unchanged |
| Performance | Matrix and timer/evaluator | Slow fsync/health/lock/full disk | Approved budgets |
| Existing isolation | Read/test/replay sink-free | Production alias | Legacy gates green |

Required regression:

    pytest -q tests/test_shadow_ledger_phase0_t*.py \
      tests/test_shadow_writer_coverage_scan.py \
      tests/test_shadow_validation.py tests/test_shadow_activation.py \
      tests/test_shadow_canary.py
    pytest -q
    convmem doctor
    git diff --check origin/main...HEAD

Shipped work also follows docs/CODEX-DEEPSEEK-VERIFY.md.

## 10. Activation runbook

### Prerequisites and backup

1. Confirm exact corrective revision and all slice evidence.
2. Confirm disabled, no prepared transaction, zero writer bypasses, current code
   deployed to every writer.
3. Confirm Ryan's exact activation authorization, paths/final config, budgets,
   first-event window, rollback thresholds.
4. Resolve Kiro plan/design review and targeted security review.
5. Run doctor; verify fresh local complete-data-v2 and matching offsite lineage.
   Record snapshot IDs/times. Do not change backup policy.
6. Abort on any backup failure.

### Suspend, prepare, review, commit

1. Stop/suspend refreshed writer services/timers and verify inactive/no legacy
   process.
2. Create private journal; acquire exclusive gate; recheck disabled config,
   preimage, paths, owner/modes, collection UUID, SHA, backup.
3. Capture matching baselines; create ledger/header, manifest, candidate config.
4. Strict prepare validation must have zero blocking codes.
5. Review counts/digest, UUID, SHA, identity, paths, permissions, semantic diff,
   and canary.
6. Obtain already-scoped Ryan confirmation inside the same guarded invocation.
   Decline/absence aborts.
7. Install ledger, manifest; revalidate; recheck config preimage; atomically
   install/fsync enabled config.

### Resume and verify

1. Release gate; resume services; verify expected revision.
2. Wait approved window for first real mutation.
3. Prove matching activation/ledger identity, sequence 1, hashes, and Chroma
   post-state.
4. If natural traffic is absent, stop. Synthetic live mutation needs separate
   exact authorization.
5. Run doctor/inventory; require same state/codes and properly labeled counts.
6. Observe latency window; compare rollback budgets; capture/hashes evidence.

Abort precommit on any refusal, baseline mismatch, unsafe path, stale config,
missing approval/budget, process uncertainty, backup/canary/fsync failure.
Postcommit rollback on validation failure, first-event timeout/mismatch,
corruption/privacy drift, reporting disagreement, unexplained miss, or approved
latency breach.

## 11. Rollback design

1. Suspend known writers.
2. Acquire exclusive gate.
3. Reload/validate config and activation ID.
4. Generate a candidate changing only enabled true to false while retaining
   evidence paths/ID.
5. Verify preimage/semantic diff; atomic replace/fsync config.
6. Record disabled_after_rollback evidence.
7. Release/resume; doctor/inventory must disclose rollback.

Never delete/reverse Chroma. Retain ledger/manifest read-only. Missed Shadow
writes are an explicit gap; a later activation needs a new ID, ledger, and fresh
baseline.

If disable fails while enabled validation is bad, keep known writers suspended,
retry only the exact disable after reread, never delete artifacts or edit
Chroma, and escalate with hashes/codes.

## 12. Implementation slices

All slices require separate Cursor authorization and merge only while disabled.

### C1 — strict validation/filesystem contract

- Allowed: new shadow_validation.py; shadow_ledger.py; chroma_readonly.py; new
  validator tests; narrow T1/contract docs.
- Prohibited: live state, sink append, activation CLI, doctor/inventory, Chroma
  mutations, backup.
- Prerequisite: approve result/refusal schema and path policy.
- Tests: full refusal/identity/baseline/path/permission matrix.
- Rollback: revert code/docs; no runtime state.
- Evidence: SHA, focused/full tests, malformed probe refused, diff check.
- Merge disabled: **Yes, required.**

### C2 — secure ledger and bounded append

- Allowed: shadow_ledger.py, shadow_sink.py, T3 tests, health schema docs.
- Prohibited: activation/config, live artifacts, doctor/inventory, writers,
  Chroma behavior.
- Prerequisite: C1/header/duplicate contract.
- Tests: umask/first-byte, existing file, fsync/short write, tail sequence,
  duplicates/concurrency/corruption.
- Rollback: revert; disabled has no production sink.
- Evidence: 0644 repro impossible; bounded-byte instrumentation; full tests.
- Merge disabled: **Yes, required.**

### C3 — writer gate/fresh-config boundary

- Allowed: chroma_write_store.py; conditional minimal chroma_store.py close hook;
  ingest.py, inter_model_index.py, observe.py, propose_decision.py, refine.py,
  source_purge.py, production convmem.py routes; writer census/tests.
- Prohibited: activation command, live state, doctor/inventory, replay changes,
  unrelated refactors.
- Prerequisite: C1 and refreshed census.
- Tests: multiprocess locks, lifetime lease, post-gate reload, exception close,
  zero bypass.
- Rollback: revert coherently; never mixed guarded/unguarded.
- Evidence: zero bypass, every route blocks, full suite.
- Merge disabled: **Yes, required.**

### C4 — doctor/inventory truth

- Allowed: doctor.py, shadow_inventory.py, thin output, chroma_readonly.py,
  T5/doctor tests.
- Prohibited: activation/config mutation, sink, live state, broader claims.
- Prerequisite: C1.
- Tests: cross-surface codes, missing/corrupt, counts, empty Shadow, redaction.
- Rollback: revert reporting.
- Evidence: fixture matrix/no false green/full suite.
- Merge disabled: **Yes, required.**

### C5 — activation/rollback transaction

- Allowed: new shadow_activation.py; config.py; thin commands; config.example;
  activation tests and approved docs.
- Prohibited: live state, automatic service control without separate approval,
  Chroma semantics, backup settings, later phases.
- Prerequisite: C1-C4; approve config diff, census, state machine, event policy.
- Tests: transitions, config-last, no-gap, crash matrix, cleanup, rollback,
  stale config, first event.
- Rollback: code revert; only temporary test roots.
- Evidence: hermetic exact-SHA report, no live touch, full suite.
- Merge disabled: **Yes, required.** Command defaults to refusal without exact
  authorization input.

### C6 — canary/evidence gate

- Allowed: new shadow_canary.py; thin CLI; sink telemetry only; canary tests;
  VERIFY docs.
- Prohibited: live artifacts, automatic activation, unapproved budgets,
  async/group optimization, production Chroma mutation.
- Prerequisite: C1-C5 and all Ryan budget values.
- Tests: workload, full timer, evaluator, provenance/redaction, live refusal,
  slow fsync/lock.
- Rollback: revert; disabled.
- Evidence: three clean same-filesystem scratch runs/cell, hashes, budgets,
  Codex replay.
- Merge disabled: **Yes, required.**

Live activation is not an implementation slice. It is a later Ryan-owned
operational grant after merge/review.

## 13. Review and approval gates

| Gate | Owner/evidence | Blocks |
|---|---|---|
| Plan | Ryan reviews this exact revision and open decisions | Any Cursor slice |
| Design | Kiro written PASS/FAIL on state machine/validator/rollback/scope | Execute |
| Security/isolation | Targeted Copilot audit of secure open/TOCTOU/gate/config at exact implementation SHA | Relevant merges as Ryan directs |
| Implementation | Cursor receives bound brief with allowed/prohibited/prerequisite SHA | Only named slice |
| Independent replay | Codex runs verification guide, tests/probes/diff/nonmutation | Merge/next slice |
| Performance | Ryan approves values/rationale | C6 and activation |
| Activation | Ryan approves exact revision/resources/operation/final config/runbook/rollback | Live prepare/commit |
| Synthetic first event | Ryan approves exact mutation/final value | Any synthetic live mutation |

Sol-High applies only to materially conflicting Copilot/Kiro PASS/FAIL verdicts
on the same artifact/revision under the charter.

## 14. Open decisions

1. **Performance budgets — Ryan before C6 implementation:** A_p99_ms, A_max_ms,
   D_p99_factor, O_p99_ms, R_p99_ms, R_factor, R_window, H_events.
2. **Private parent policy — Ryan/Kiro:** recommended current-user ownership and
   no group/other permissions for dedicated staging; decide whether existing
   shared data-root parent must be 0700 or may contain a private 0700 Shadow
   subdirectory.
3. **First-event window — Ryan:** set maximum commit-to-event time and timeout
   action; recommendation is rollback.
4. **Synthetic event — Ryan only if natural traffic is absent:** exact writer
   operation and final value; none is implied.
5. **Service suspension list — Ryan confirms refreshed census:** lock remains
   mechanical proof; list controls stop/resume.
6. **Config editing mechanism — implementation review:** recommendation is
   byte-preserving replacement of only the existing shadow_ledger table,
   TOML parse plus semantic-diff proof, preimage hash, atomic replace, directory
   fsync. A general TOML dependency requires separate justification.

These choices block activation. Items 1-3 also block authorization of the slice
that encodes them. They do not reopen Chroma authority, vocabulary, backup
doctrine, or later phases.

**PLAN READY FOR IMPLEMENTATION REVIEW**

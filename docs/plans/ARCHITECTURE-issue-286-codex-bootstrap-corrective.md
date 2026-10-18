# [Arc Codex #286] Corrective direction for existing Codex rollout bootstrap

**Author:** Codex, 2026-10-18. **State:** Draft for Kiro review; awaiting Ryan's direction approval.
**Source:** Ryan's instruction to prepare a bounded correction supporting Codex identity/parsing and coordination with live writers while preserving paid caps and recovery.
**Baseline:** fetched `origin/main` at `483373f1cef2142847fcd9c276196593a72a0ecf`.
**Problem:** The three A1 sources are Codex rollouts, but the shipped one-shot bootstrap selects Kiro parsing/state identity and requires incremental routing disabled and the watcher stopped.

## 1. Decision and authority

Recommend a **versioned, exact-source Codex bootstrap through the existing coordinator**, with a durable reservation for the selected source and enforced cooperation at writer admission and mutation boundaries. Unrelated, compatible writers may continue; C1 still serializes shared mutations. Preserve the original Kiro grant and stopped-watcher route unchanged.

This document chooses the architecture direction. It contains acceptance obligations, not an Execute task list. Planning is authorized. Kiro reviews this exact revision; Ryan approves the direction before Codex shapes the execution plan. Cursor implementation requires Ryan's later explicit authorization of that reviewed plan. No live action follows from review, implementation, merge, or a bare “go A1.”

**A1 remains parked.** Current authority permits no deployment, runtime-main/config change, watcher stop/restart, quarantine clearing, transcript/source changes, implementation, PR, or Part B work. The new authorization permits these planning documents only. Existing A2 indexing remains stopped after its doctor failure.

## 2. Evidence and boundaries

The originating coverage handoff is `docs/inter-model/CODEX-2026-10-18-issue-286-free-window-coverage-handoff.md` on `origin/docs/2026-10-12-issue-286-stage2-fixes-handoff`, reviewed at `69d56ee9937d9bedc49484a9e0a219d7bfadf72c`.

The [local A1 packet](/tmp/convmem-286-free-window-20261018/A1-dry-run-packet.md) records read-only observations of runtime `633f1d1c596f890319b088f959bdce00dec45792`, enabled incremental routing, active watcher, and three existing rollout state directories. Its historical “go” wording is superseded by Ryan's corrective-planning instruction and this parked disposition. Observations are not a future execution grant.

Code evidence below is pinned to the baseline above:

- [Bootstrap entrypoint](../../scripts/bootstrap-incremental-jsonl.py), `bootstrap()` and `_require_watcher_disabled()`: default-off and stopped-watcher guards, Kiro-only detection/parser, and `source_state_id(str(source))` using the default Kiro format. `_effective_binding()` also computes the older transform fingerprint rather than selecting the Codex descriptor contract.
- [Format registry](../../incremental_jsonl_formats.py), `get_format_spec()` and `source_state_id()`: Codex rollout parsing already exists; state identity hashes `format_id:canonical_path`.
- [Codex admission](../../incremental_jsonl_codex_admission.py), `admits_path_checks_1_4()` and `verify_session_meta_identity()`: root/path/UUIDv7/time checks and first-record identity validation already exist. Filename or mtime alone is insufficient.
- [Coordinator](../../incremental_jsonl.py), constructor, `run()`, `_commit_generation()`, `_restore_replay_before_images()`, `_publish_processed()`: Codex descriptor/checkpoint support, an incremental source lock, source/C1 write locks, durable prepared artifacts, rollback authority, and publication after checkpoint. Constructor creates state directories, so it cannot be the dry-run implementation.
- [Paid authority](../../bootstrap_safety.py), `validate_grant()` and `BootstrapOperationJournal`: strict unversioned grant shape; append-only HTTP permits consumed before transport; one recovery; cumulative paid accounting. [Supersession](../../bootstrap_supersession.py) binds predecessor evidence and must not be silently generalized.
- [Lock rules](../../purge_locks.py): source before C1 before export; provider work forbidden under C1 or a production Chroma session. [Legacy ingestion](../../ingest.py), `_commit_chunk_to_stores()` and `_prune_completed_reindex()`, takes source/C1 locks at mutation time, not for all preparation. An incremental lock alone cannot exclude legacy work.

The read-only corpus search timed out after 60 seconds; it supplied no additional usable evidence. No transcript content is reproduced here.

### Exact initial scope

Only `jsonl_codex_rollout` sources already passing the configured Codex admission predicate, with existing legacy coverage and no valid incremental checkpoint. The first execution packet is limited to these three canonical paths:

1. `/home/lauer/.codex/sessions/2026/10/13/rollout-2026-10-13T15-33-20-01a136f8-3c55-7c12-ad90-1d3c07f286a1.jsonl`
2. `/home/lauer/.codex/sessions/2026/10/14/rollout-2026-10-14T01-56-33-01a13932-d05c-7680-8cf8-d54f0f0e9dc0.jsonl`
3. `/home/lauer/.codex/sessions/2026/10/14/rollout-2026-10-14T01-58-25-01a13934-85b6-7360-9e3a-b14928d462c8.jsonl`

Packet-time counts were 75/38/50 accepted messages, 2/1/1 chunks at size 60/overlap 10, and 4/2/2 nominal paid generations. Existing retry states said `bootstrap_required`; checkpoint, transaction, and rollback files were absent. State directories, snapshots, and retry evidence were retained. Recompute all of this before authority is issued.

Excluded: Codex `history.jsonl`, pre-admission rollouts, other adapters, bulk or automatic bootstrap, new admission roots, legacy supersession changes, commit-cost optimization, quarantine release, global repair/restore, and all other arcs. A2 health diagnosis is a separate prerequisite, not an implementation item here.

## 3. Options considered

1. **Parser-only extension plus an exclusive maintenance window.** Smaller code change, retaining whole-window isolation assumptions. Rejected as the chosen direction: it still needs watcher/config changes and coordinated writer pauses outside Ryan's limits; a parser change also misses state and transform identities.
2. **Format-bound one-shot operation with source reservation and existing write gates. Recommended.** Adds admission/commit cooperation and crash ownership, allowing proven unrelated writers to proceed. Cost: every relevant writer boundary must be covered, and recovery must preserve unrelated changes made between attempts. Missing coverage is a NO-GO, never permission to assume a quiet window.
3. **Enable full rebuild or call the coordinator directly.** Rejected: `bootstrap_required` is an authority boundary; those routes would evade the reviewed one-shot grant, accounting, and invocation limits.

## 4. Chosen contracts

### 4.1 Versioned source and transform authority

- Introduce an explicit v2 grant discriminator for this Codex route. V1's exact field set, hashes, Kiro behavior, operation directories, and replay rules remain byte-compatible. Missing version means v1 only; never infer Codex or live-writer permission from detection alone.
- V2 binds one canonical source path, explicit `jsonl_codex_rollout`, adapter contract version, recomputed state ID, session UUID identity, device/inode, selected complete-prefix boundary/hash, and source size ceiling. Preserve runtime/config/provider/dimension/chunk/confidence/budget bindings and add the coordination protocol version. Use separate v2 operation/grant hash domains. Reject unknown fields/versions, mismatched detection, symlinks, aliases, and identity drift before paid work.
- Use the registry's rollout parser and the existing Codex transform descriptor/fingerprint and recovery protocol. Packet, grant, prepared keys, operation manifest, transaction, checkpoint, and receipts must agree on format and transform identity. Do not create a Kiro state directory for a Codex source or migrate another format's state by renaming it.
- Reuse all Codex admission checks, including `session_meta` matching UUIDv7 and filename time. Exact-path authority must not bypass admission checks or widen the existing root/time window. Unsupported sources fail visibly without a legacy fallback.
- Keep the live config unchanged. A validated one-shot capability permits bootstrap for only this exact source in the process; it cannot change persistent flags, add a watch root, permit ordinary bootstrap, or enable full rebuild. The operation binds the actual config digest and explicitly constrains its own coordinator mode.
- Refresh or refuse stale source observations before consuming authority. A pure append after selection may retain the reviewed complete prefix; only that prefix may be transformed. Replacement, truncation, prefix mutation, changed inode/session identity, or a source exceeding its bound limit stops the operation. New bytes require later ordinary authority or a new reviewed packet, never silent cap enlargement.

### 4.2 Coordination with live writers

Treat source exclusion as a durable protocol, not a PID check or a long-held global lock.

1. **Read-only preflight:** establish a healthy doctor baseline, exact writer/runtime compatibility, source eligibility, provider bindings, backup evidence, and a bounded lock-wait allowance. Inspect current owners and allow existing jobs to finish normally. Never stop/restart/kill another writer. An old, unknown, or uncooperative writer blocks admission. No “no PID observed” assertion substitutes for enforcement at mutation time.
2. **Reserve:** acquire the incremental format/source lock, then canonical source lock, then C1 in the established order. Recheck mutable evidence while locked. Atomically persist/fsync an exact source reservation bound to the v2 operation and invocation authority before releasing source/C1 locks. A second bootstrap cannot reserve the same path. The reservation must be discoverable independently of whether a transaction exists yet.
3. **Prepare:** keep the incremental operation lock, release C1/Chroma sessions, and perform capped provider work. All same-source entrypoints must consult the reservation before new provider preparation. An already-preparing legacy writer must recheck at commit and refuse its stale write. Its earlier calls cannot be retrospectively charged to or erased by the new operation; unresolved same-source activity blocks admission until drained.
4. **Commit:** under source → C1 → writer/session/export locks as applicable, recheck reservation ownership, live binding, source prefix, exclusions, and current projection lineage. Capture source before-images and the non-source baseline inside this critical section. Apply both collections, persist checkpoint authority, and reconcile followers using existing governed operations. Keep the reservation through processed publication and durable terminal receipt, including gaps outside C1.
5. **Recover or finish:** a crash releases advisory locks but leaves the reservation. Only the identical grant's authorized recovery may claim it. Ordinary watcher/manual ingest, purge, reindex, source-state cleanup, or a fresh operation cannot take over the selected path. Release only after a proven terminal checkpoint/follower state or verified rollback; retain an immutable terminal record. A timeout, dead PID, or exhausted budget never clears ownership.

**Writer coverage required:** watcher-spawned index children, direct/manual index, incremental and legacy commits, source purge/exclude, processed/export/dedupe mutation, and recovery/cleanup. Checks must be enforced at shared governed mutation boundaries as well as friendly entrypoints. Unscoped maintenance capable of changing the reserved source must refuse while it is reserved. Read-only consumers and proven unrelated source writers may continue. This is a narrow bootstrap restriction; existing writer admission, Shadow/R2b guards, and recovery-authority policy remain authoritative.

**Lock discipline:** reservation creation/release may briefly use C1; no paid call or external backup validation may hold it. Preserve incremental lock → canonical source lock → C1 → writer/session/export ordering, without recursively acquiring non-reentrant source locks. Operation accounting locks must not be held while acquiring those locks. Use bounded, observable waiting and refuse on timeout without consuming a provider permit. A post-start timeout retains the operation for the one allowed recovery. Do not change the generic provider-under-write-scope prohibition.

**Watcher interaction:** pending bootstrap returns a distinct coordination deferral, not a successful index and not a new failure/quarantine escalation. Preserve existing quarantine and retry evidence. The sole bootstrap eligibility exception is the grant-bound `bootstrap_required` condition; fault, wedged, exhausted, unreadable, or other refusal state remains a stop. Successful A1 does not grant quarantine release or alter normal watcher paid budgets. If the current watcher cannot preserve this behavior without a later separately authorized deployment/restart, A1 stays parked.

### 4.3 Paid calls and recovery

- Bind positive per-source chunk and paid-HTTP ceilings. The packet proposes 2/1/1 chunks and 4/2/2 paid HTTP attempts; these are **unapproved** nominal-only limits, allowing no paid retry headroom. No number is inherited from the word “free,” the admission limit of 20 chunks, or another operation.
- Preserve durable permit-before-send accounting, including HTTP retries and uncertain outcomes after a crash. Ollama stays observed and cap-exempt. Count attempts across the initial invocation and at most one recovery; fsync prepared outputs before shared writes. Durable completed transforms are reused. A crash after sending but before durable preparation may require another permitted attempt; never promise exactly-once external billing or refund an uncertain permit.
- Preserve provider/model/base-URL matching and fail-on-fallback. Before transport, both operation authority and any applicable shared canary ceiling must permit the call. The handoff's 3,000-call watcher guard is not an additional A1 allowance. **UNVERIFIED — Ryan/Claude:** whether that guard accounts for one-shot processes. Live execution requires demonstrated composition of limits, or a separately approved allocation/enforcement plan; independent unchecked counters are insufficient. This direction does not authorize expanding that guard's budget.
- A reservation without a transaction is a supported crash boundary: the journal and reservation must prove the same grant and whether the initial invocation was consumed. Recovery cannot invent fresh initial authority. Journal creation/reservation publication must have a specified idempotent crash protocol; ambiguity fails closed.
- `PREPARING`, `transform_failed`, and `APPLYING` retain exact grant/format/runtime/descriptor/budget authority. APPLYING replay must retain and verify the original rollback journal hash before and after replay; never replace it with a snapshot of partly applied data.
- A crash after checkpoint but before followers/receipt/release is also recoverable under the same allowance: finish missing followers and terminal evidence without repeating transforms. A committed operation refuses re-execution. Exhausted recovery or mismatched evidence retains the reservation for Ryan; no automatic new grant, supersession, reset, or cleanup.
- V2 failed-operation supersession is out of scope. Existing v1 predecessor preservation and lifetime caps remain unchanged; v2 refuses predecessor/supersession evidence it cannot prove.

Admission must inspect both reservation and existing operation journals. A crash that leaves only one of them cannot make the path look unused: contradictory, missing, or orphaned authority blocks a fresh operation. Changing a grant fingerprint is not a way to reset consumed budget or the recovery allowance.

### 4.4 Concurrent rollback and evidence

Capture source before-images under C1 immediately before first apply. Compare non-source collection evidence immediately before/after each locked apply or restore, rather than across the entire paid-work interval. Foreign writers can legitimately change unrelated rows between those intervals.

Recovery restores only this source's proven rows and processed entries, merges against the latest processed state under its existing lock, and removes only this operation's attributable export/dedupe changes. Preserve foreign records, malformed/opaque foreign bytes, ordering, and unrelated entries created after the first attempt. Existing helpers require this proof; do not infer byte preservation from their names. Unknown ownership or conflicting foreign changes cause `recovery_unproven`, never whole-file rewind. Whole-store backup restoration is a separate Ryan-owned operation with an exclusive writer window.

Durable receipts report format/source/operation identity, chosen prefix and transform, invocation ordinal, consumed/remaining paid attempts, state outcome, lock waits, rollback authority digest, and bounded mutation evidence. Print metadata and counts only. No prompts, messages, summaries, embeddings, provider response bodies, or transcript content in review packets or command output. Restrict prepared/rollback artifacts to existing private storage roles.

### 4.5 Dry-run and backup boundary

Provide a genuinely read-only preflight path using pure validation/parsing and read-only state inspection. It must not instantiate the coordinator/journal, create lock/state/cache files, reserve an invocation, request embeddings, or call providers. It outputs a proposed packet and explicit blockers; it never emits executable authority by default. Execution revalidates observations under locks.

A later exact grant needs fresh complete-data local/offsite backup IDs, copy lineage and coverage for Chroma, processed/export/dedupe, incremental state, operation journals, and the reservation. Verify the actual backup tree, not just a 64-character ID. Source transcripts are outside the data-root backup; Ryan must approve their recovery disposition separately. Snapshot consistency must follow the approved backup procedure while writers run; if it cannot, refuse. These checks create no permission to copy transcripts in this planning phase.

Retain the operational freshness rule: skip a source modified in the last 30 minutes. An older mtime is only eligibility evidence; the source-identity and prefix checks still apply throughout execution.

## 5. Acceptance obligations for the downstream plan

Cursor's later authorized implementation needs hermetic, network-denied, fake-provider evidence with temporary sources/config/data and real temporary Chroma. No production paths, providers, watcher controls, or live failure-log writes are acceptable. The following are design proof obligations, not tests run by this planning session:

- **Identity:** Codex rollout positive case; Kiro v1 regression; history/cross-format/wrong-state-ID rejection; session-meta mismatch, symlink, path alias, replacement, partial line, append, prefix mutation, and source-size limits.
- **No side effects:** dry-run/refusal leaves all protected artifacts unchanged; no state-directory construction or provider traffic. Demonstrate the old entrypoint's three incompatibilities remain explicit until the new protocol is selected.
- **Budget:** concurrent/repeated invocation, retry, exhausted cap, fallback, permit fsync/send crash, prepared-cache reuse, initial plus one recovery, and post-checkpoint recovery. Show an attempted cap reset or second recovery is denied. Prove composition with the applicable outer budget before live use.
- **Cooperation:** deterministic two-process barriers for watcher/manual/same-source legacy races, unrelated writer progress during transforms, pending reservation across process death, bounded lock timeout, no paid work under C1, no stale processed overwrite, and no quarantine changes from coordination deferral.
- **Recovery:** crash at every durable phase boundary, including reservation without transaction and checkpoint without terminal receipt; missing/tampered rollback; unrelated collection/export/processed/dedupe changes between attempts; byte-exact preservation of foreign malformed lines and blank lines. Prove the original rollback authority survives failed replay.
- **Coverage and refusal:** enumerate every mutating entrypoint and its enforcement point. An incompatible old writer, unscoped maintenance, uncertain backup, doctor failure, or missing source authority must produce NO-GO. A cooperating source writer and a bypassing negative control must yield different results.

Review must establish which existing helpers satisfy these obligations and which need a bounded correction. If closing writer coverage requires a generic admission redesign, another arc's authority changes, or v2 supersession, return to Ryan for a separate direction rather than expanding this one.

## 6. Risks, reversibility, and remaining gates

The largest risk is incomplete mediation: one stale process or sidecar path could bypass the reservation. Until exact writer compatibility and all mutation boundaries are demonstrated, the live-writer mode must refuse. A watcher that merely spawns compatible children is different from a long-lived process retaining incompatible mutation code; inspect both. Later rollout may require operational permissions not granted now.

A durable reservation can strand a source after a crash. That is deliberate containment: unrelated safe work may continue, but expired time or a missing process cannot release recovery ownership. Any manual release after exhausted recovery requires a separately reviewed exact-state procedure and Ryan authority. Rollback to an older runtime while a v2 operation is pending is unsupported; retain compatible recovery code and evidence until resolution.

Chroma still has a cross-collection visibility seam; this plan preserves replay/rollback, not atomic reader visibility. C1 hold time is not optimized here. The earlier A3 timing baseline includes provider and queue time and cannot prove a commit-only latency target.

**Health:** A2's post-file doctor returned rc 1 with `[FAIL] ledger_documents: database is locked`; a final diagnostic also returned rc 1. The cause is unresolved. Do not label this corruption or a harmless transient without evidence. Read-only diagnosis and a fresh healthy baseline are prerequisites to any resumed indexing, including A1. Stop the owned run if any observed index process exceeds 4 GB RSS or doctor reports a new FAIL; do not kill another lane's process. Retain journals for recovery.

**Next gate:** Kiro reviews this direction at its exact committed revision, especially v1 compatibility, Codex descriptor identity, complete writer mediation, cap composition, and foreign-write-preserving recovery. Kiro PASS plus Ryan direction approval permits Codex execution planning. Ryan then authorizes Cursor implementation of the reviewed bounded plan. Review/merge, deployment, compatible-writer rollout, backup/source revalidation, numeric caps, health clearance, and exact A1 execution are distinct later gates.

**Stop: Await HITL — direction review/approval.** No execution plan or implementation is authorized by this draft. The exact A1 packet must be refreshed against the eventual reviewed runtime; “go A1” cannot make today's incompatible entrypoint work.

**TL;DR:** [Arc Codex] Recommend a v2 exact-source Codex bootstrap with durable source ownership and existing governed writes. Preserve v1, paid-attempt caps, one recovery, and unrelated writers' data. A1 stays parked pending review, approved implementation, compatible deployment, and fresh exact execution authority.

<!-- src: /tmp/convmem-286-free-window-20261018/A1-dry-run-packet.md — packet-time observations, not authority -->
<!-- src: ../../scripts/bootstrap-incremental-jsonl.py, ../../bootstrap_safety.py, ../../incremental_jsonl.py, ../../incremental_jsonl_formats.py, ../../purge_locks.py — baseline contracts -->
<!-- ref: ./STATUS-codex-jsonl-production-integration.md, ../planning/ARCHITECTURE-PLANNING.md — arc routing and direction gate -->

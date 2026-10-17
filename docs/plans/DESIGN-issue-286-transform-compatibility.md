# [Arc Codex #286] Keep incremental checkpoints valid across compatible deploys

**State:** proposed design, 2026-10-17; Kiro review next. No Execute grant.

Codex proposes this change for Ryan because an admitted session should retain
its paid transform work when a deploy changes bookkeeping or commit cost.
The proposal is based on fetched `origin/main` at
`9ef4ecdd0dbf4110b757123b3894e5effa83fd82`. It authorizes no implementation,
checkpoint migration, provider call, quarantine release, or runtime promotion.

## 1. Decision

Use **a declared transform-contract version plus explicit semantic inputs** as
the continuity key. Remove R2b `implementation_revision` from that key. Keep
the implementation identity as immutable provenance and continue using the
current identity for every governed writer operation.

These are complementary controls: the semantic inputs catch configuration
changes automatically; the declared version covers behavior changes in code
that configuration cannot describe. A version alone is too easy to leave
unchanged when a model or chunk size changes. A semantic-input hash alone
misses a parser or normalization correction whose named contracts were not
updated. Hashing the entire implementation catches both but also invalidates
expensive work for unrelated changes.

The version is a compatibility epoch, not a release number. Bump it whenever
the same canonical input could produce materially different transform output,
selection, IDs, or cache interpretation under the declared settings. Different
LLM samples from an otherwise unchanged request do not require a bump.
Existing paid samples remain valid outputs of that contract.

## 2. Evidence and present behavior

Ryan's Canary 2 evidence from 2026-10-17 reports runtime changes at 12:23 and
14:26, followed by refusals at 12:37 and 14:29 respectively. Those times are
as supplied; this design does not infer a timezone or exact deployed SHA.
The refused sources are:

- `/home/lauer/.codex/sessions/2026/10/16/rollout-2026-10-16T20-12-01-01a1476a-7427-7b50-a1f3-918ba205d637.jsonl`
- `/home/lauer/.codex/sessions/2026/10/17/rollout-2026-10-17T13-48-14-01a14b31-71c7-7490-8f27-12aadef95b61.jsonl`

This session's `convmem doctor` independently reported both paths quarantined
with `rebuild_required:transform_fingerprint_changed`. It also reported a retry
hold for the second path, with an empty transaction ID. That is not proof that
the path has no transaction; inspect its actual state before migration.
The CPU-tripwire failure was separately waived by Ryan for this design task.

Source inspection at the baseline establishes the mechanism:

- `compute_transform_fingerprint` hashes semantic settings **and**
  `implementation_revision`. The coordinator resolves that value through
  `chroma_write_store.current_implementation_revision()`.
- The R2b resolver hashes an authority-content manifest, including governed
  modules and their local dependency closure. It is not raw Git HEAD. Changes
  outside this closure need not change the identity; changes inside it can
  change identity without changing transforms.
- `_continuity_reason` rejects a checkpoint whose fingerprint differs.
  With full rebuild disabled this becomes a live-route refusal. Watch records
  terminal path quarantine, so later appends do not repair continuity.
- `_prepared_key` includes the fingerprint, and prepared-artifact validation
  requires it. Generation IDs also include it. Merely rewriting a checkpoint
  hash strands the old cache and is insufficient.
- A pending transaction is recovered before the normal checkpoint path.
  Changing continuity comparison alone cannot make replay safe.

Thus a deploy that changes the R2b identity invalidates every legacy checkpoint
bound to its predecessor identity, even when transforms are compatible. The
planned commit-cost slice 1 touches `incremental_jsonl.py`; its intended digest
reuse and timing changes need compatibility classification, not a paid rebuild
by default. This document does not review or implement that separate slice.

## 3. Versioned semantic descriptor

Define one canonical descriptor builder shared by continuity, prepared cache,
generation construction, and migration verification. Proposed scheme name:
`incremental-transform-v2`. Hash a domain separator and canonical JSON using
SHA-256. Persist both the descriptor and its digest; validate the relationship
on every read. Do not infer semantic identity from an opaque legacy digest.

The descriptor contains:

- Fingerprint scheme, adapter format, adapter contract, and the declared
  `transform_contract_version` (initial epoch `1` within the new scheme).
- Chunk size, overlap, message selection and canonical rendering contracts,
  rendering limits, and parser/message normalization contracts.
- Summary/distillation prompt identities, generation parameters (including
  temperatures), resolved model identities, and any provider behavior options
  that affect requests. Prefer digests of the actual prompt templates over
  labels disconnected from template bytes.
- Embedding model identity, dimension, and embedding normalization contract;
  confidence threshold; unit normalization, provenance-envelope shape,
  ID generation, and deduplication contracts.
- Prepared-payload interpretation and any dependency behavior that can affect
  those results, represented by a declared contract/epoch where a stable
  automatic semantic identifier is unavailable.

Use resolved effective settings, not an absent value or fallback dimension
zero from a route-off probe. Fail closed on unresolved required inputs.
An aliased remote model can drift without a name change: pin a provider
revision where possible; otherwise maintain an explicit operator-controlled
model epoch and acknowledge that unannounced provider drift remains a limit.

Exclude deploy SHA, R2b implementation identity, host, timestamps, instrumentation,
retry counters, writer-lock details, and inventory scan count. These describe
execution and authority rather than the validity of a completed transform.
An envelope's **schema** belongs in the contract; the actual producer revision
inside an envelope is provenance and may legitimately differ across chunks.

Keep fingerprint scheme, checkpoint schema, transaction schema, and writer
protocol versions distinct. A checkpoint-layout change does not itself prove
that paid transforms are incompatible. This design nevertheless requires an
explicit reader/migration boundary for the new persisted representation.

### Change discipline

Require a compatibility statement in every incremental-ingest change:
semantic change (descriptor change/epoch bump) or compatible implementation
change (why cached output and its interpretation remain valid). The reviewer
must consider parsing, chunk boundaries, rendering, prompts, models, metadata,
IDs, normalization, filtering, dedupe, embedding behavior, and artifact decoding.
When uncertain, bump or refuse migration; do not declare compatibility merely
because a fixture happens to pass.

Add a hermetic contract-inventory check tied to actual prompt/settings sources
and reviewed transform dependency fixtures. Changes to this inventory require
an explicit compatibility review. It must not hash all of
`incremental_jsonl.py` into the runtime key: the commit-cost work demonstrates
why file-level identity is too broad. No automated test can prove semantic
equivalence of arbitrary code; the declared epoch adds a review obligation.

## 4. Provenance and safety boundaries

Record producer Git revision and R2b implementation identity when preparing new
artifacts. Checkpoints and transactions record the coordinator implementation
that published them. Reused artifacts retain their original producer identity;
the new transaction records reuse rather than relabeling old work as newly
produced. A migrated artifact records its old artifact digest and migration
receipt. Never insert a guessed producer revision into historical provenance.

Do not change R2b identity calculation, inventories, proof/lease checks, grants,
or production writer validation. A semantically compatible cache is **not**
authority to write. New writes use the current approved runtime and its current
writer proof; old producer identities remain historical evidence. Existing
exact-runtime bootstrap/canary grants do not become portable across deploys.

All source, inode/device, prefix hash, session-meta identity, raw-line coverage,
projection/processed lineage, exclusion, source-size, frontier, paid-call cap,
rollback digest, and foreign-row preservation checks remain required. Cache
integrity checks still bind source, chunk start, input digest, dimensions,
completeness, key, and serialized artifact digest.

Two independent compatibility questions remain:

1. Is this paid transform reusable? Answered by the semantic descriptor.
2. Can this runtime interpret and recover this transaction safely? Answered by
   the transaction/recovery protocol and current writer authority.

For new v2 transactions, persist the descriptor digest, recovery protocol,
and originating implementation identity. Recovery checks these before any
provider call or write. A non-transform deploy may replay only when it supports
that recovery protocol. An incompatible recovery change refuses even if the
semantic digest is identical. Existing exact before-images and their bound
hashes remain immutable; compatibility never permits rewriting them.

The trade-off is deliberate: broad code hashing currently provides a coarse
automatic invalidation guard. Removing it narrows invalidation correctly but
requires disciplined contract declarations. Missing a bump could reuse obsolete
outputs. Explicit descriptor fields, actual prompt digests, negative controls,
and review reduce that risk; they do not eliminate it.

## 5. Legacy migration: explicit, exact-source, zero transform calls

Do not silently accept all old fingerprints, omit the revision at comparison
time, reset checkpoints, or enable `allow_full_rebuild`. Legacy digests are
one-way hashes; their semantic inputs cannot be recovered by deleting a field.
Use a separately reviewed, Ryan-authorized one-shot converter for exact source
paths. A future dry-run report precedes any mutation.

### Preconditions and compatibility proof

For each candidate, capture checkpoint bytes/digest, prepared artifacts,
transaction/rollback state, retry/quarantine evidence, effective config,
source identity/prefix coverage, both projection manifests, and processed
lineage. Preserve them in the separately authorized backup/evidence scope.
No migration is granted by this design.

Reconstruct the legacy fingerprint payload using the actual producer runtime,
effective settings, and R2b identity. Require its computed digest to equal the
checkpoint's stored digest. Review the relevant transform implementations and
settings against the target descriptor, explicitly classifying every semantic
difference. Include all producers of reused historical artifacts, not just the
latest deploy. A short checkpoint digest alone or today's config is insufficient.
If producer evidence is missing or semantic equivalence is unproven, report
`migration_compatibility_unproven` and leave that source untouched. Any later
paid rebuild needs its own grant and budget.

Only migrate a quiescent committed generation: valid complete checkpoint,
no pending transaction of **any** phase, no live rollback authority awaiting
recovery, no other writer, and exact projection/processed-lineage agreement.
Check all stable chunk artifacts needed to reconstruct the committed generation;
verify their input digests against the checkpointed prefix, full artifact
integrity, IDs, and dimensions. Require the complete generation's cache set,
including the frontier, for a zero-call unchanged control. Missing/corrupt cache
is a refusal, never a reason to transform history during migration.

### Publish protocol

Use the existing source/advisory and index writer locks in their established
order. Stop/drain the watcher and other writers under a separate operational
grant; revalidate the captured state under the locks immediately before publish.
The converter performs no Chroma mutation and no provider calls.

1. Write a retained migration receipt binding exact source identity, old
   checkpoint digest, old fingerprint preimage/evidence, target descriptor,
   artifact mappings, projection/lineage evidence, and converter revision.
2. Stage v2 prepared copies in a separate immutable cache namespace named by
   the receipt digest. Re-key each using the new semantic fingerprint, update
   wrapper/schema fields and artifact digest, and preserve actual paid outputs,
   embeddings, row IDs, and original provenance bytes. Keep legacy files intact.
   Bind every copy to its old digest in the receipt; verify the copies again.
3. Fsync the copies, receipt, and containing directories. Revalidate source
   prefix and projection/lineage agreement before making them authoritative.
4. Atomically replace the checkpoint with schema v2, containing the descriptor,
   fingerprint scheme/digest, selected cache namespace, and receipt digest.
   Fsync its directory. The checkpoint is the sole publication marker.
5. Verify the published checkpoint selects the complete staged cache and its
   receipt. Preserve the old checkpoint bytes and all original evidence.

Before step 4, only v1 is authoritative; a crash leaves unreachable staged
copies. After step 4, only the selected v2 namespace is authoritative. Retry
recognizes the exact receipt and finishes verification idempotently; it cannot
publish a second conversion against changed state. Unexpected checkpoint bytes,
symlinks, or incomplete staged data cause refusal. Do not garbage-collect old
state as part of conversion.

Migration preserves boundary, prefix hash, record count, frontier, coverage,
physical IDs, projection fingerprint, processed lineage/hash, and
`active_generation`. Record that the preserved generation uses the legacy
generation scheme; do not manufacture a new generation without a real commit.
The first later append creates a v2 generation normally. Chroma, export,
processed state, dedupe state, and source bytes remain unchanged by conversion.

New admitted Codex checkpoints use v2 directly. Existing v1 checkpoints return
a specific migration-required refusal until explicitly converted; no watch-time
automatic converter. Keep legacy Kiro behavior on its current route in this
slice. Dispatch validators by format and schema, and leave other adapters and
their bootstrap grants untouched. A Kiro migration requires a later scoped
proposal. Old runtimes must reject v2; operational rollback after conversion
requires a separately reviewed restore/reconciliation decision, especially once
v2 has committed an append. Do not downgrade by replacing the checkpoint alone.

### Today's two refused sessions

Both exact paths in §2 are candidates, **not preapproved compatible sources**.
Recover their historical producer/config evidence and prove that revision was
the only incompatible fingerprint input. For each, inspect actual checkpoint,
cache, transaction, rollback, and hold state before selecting the action.

- If quiescent and proven compatible, run the converter above with zero paid
  calls. Preserve the refusal and hold evidence. Under a separate exact-source
  release grant, use the established quarantine/retry-state clearing interface
  after successful conversion, then run a controlled unchanged or append check.
  Verify both breaker quarantine and retry holds are released; clearing one
  alone may leave the path stuck. The present clear interface is broader than
  one refusal reason, so inspect all reasons and do not clear unrelated holds.
- If a transaction or rollback journal exists, do not convert or clear its
  protection. Resolve recovery under its supported runtime/protocol and separate
  authority first, then recapture the migration candidate. A retry hold with an
  empty transaction ID is not itself an APPLYING journal.
- If semantic settings changed or evidence is incomplete, retain refusal.
  Present the exact missing proof or bounded rebuild cost to Ryan.

The Oct 13 source's separate `recovery_unproven` APPLYING transaction reported
by doctor is outside this two-source conversion and remains untouched.

After conversion, unchanged input requires no provider calls. New appends pay
only for the normal overlap frontier and new chunks. A backlog accumulated
while quarantined may exceed the existing per-run chunk cap; report that case
and obtain a bounded catch-up decision rather than weakening caps, discarding
coverage, or claiming automatic recovery. Migration avoids historical rebuild
cost; it does not promise that indexing an arbitrary backlog is free.

## 6. Acceptance tests for a later implementation

Use the existing hermetic temporary-root/fake-provider boundary; deny production
paths and network access. Use disposable real Chroma only for integration checks
that require projection/recovery behavior. These are proposed tests, not tests
executed for this documentation change.

### Required deploy regression

Create an admitted Codex rollout with enough chunks to have a stable history
and a live frontier. Run the real coordinator without injecting a precomputed
fingerprint; establish a complete v2 checkpoint and prepared cache under
implementation identity A. Restart the coordinator as a new process under B,
using an otherwise equivalent fixture runtime whose bookkeeping/instrumentation
change changes the **real R2b authority-content identity**. Keep all semantic
inputs and the declared epoch equal. Assert A differs from B.

First run unchanged input: assert identical semantic fingerprint,
`outcome=unchanged`, no rebuild/refusal/quarantine, no provider calls, and no
checkpoint advancement. Then append complete records on the same inode:
assert incremental mode, stable chunk reuse, only expected frontier/new calls,
normal cap enforcement, complete new coverage and correct physical keep set.
Historical artifacts retain producer A; newly transformed artifacts identify B;
the writer uses B's current authority. This fails if implementation identity is
reintroduced into any cache key or continuity/generation descriptor.

Also cover the coordinator lookup with a deterministic A/B identity resolver
test for fast diagnosis. It supplements the two-runtime test, not replaces it.
Include a fixture change to commit bookkeeping inside `incremental_jsonl.py`
so the same-module non-transform case is specifically protected.

### Required negative and migration controls

- Parameterize changes to prompts, models/model epochs, dimensions, chunking,
  overlap, threshold, adapter/parser/rendering contracts, normalization, IDs,
  dedupe, envelope schema, and declared epoch. Each changes the semantic digest
  and refuses reuse before paid calls/writes when rebuild is disabled.
- Reject missing descriptor fields, descriptor/digest mismatch, unknown schemes,
  unresolved dimensions, and corrupt or cross-source prepared payloads.
- Build v1 fixtures with the two refusal patterns from §2, including a held
  second source. Prove legacy preimage equality, then convert checkpoint plus
  cache. Assert zero provider/Chroma writes, byte-identical sources/projections/
  followers, preserved lineage/generation/provenance, and successful controlled
  v2 continuation after separately simulated hold release.
- Unknown producer revision, unreconstructed preimage, semantic difference,
  missing stable cache, projection drift, source mutation/replacement, exclusion,
  or any pending transaction/rollback must block conversion without publication.
- Inject crashes before/after every staged-file, receipt, and checkpoint fsync/
  publication boundary. Restart sees exactly v1 or complete v2; repeat conversion
  is idempotent. An interrupted release after publication leaves a safe held
  source and a retryable release operation, not a second migration.
- Exercise v2 transaction crash replay across compatible implementations with
  unchanged paid-call counts and immutable rollback authority. An unsupported
  recovery protocol refuses even when the semantic descriptor is equal.
- Confirm current R2b proof/lease mismatch still refuses writes, exact-runtime
  grants are not transferable, old readers reject v2, and Kiro/other adapters
  retain their existing schema/routing behavior.

## 7. Delivery sequence and review decisions

Kiro reviews this compatibility decision and migration protocol first. Ryan then
decides whether to authorize Cursor implementation and hermetic verification.
Implementation must deliver the descriptor, provenance split, versioned state
readers, cache-aware converter dry run, crash-safe publication, and tests as one
coherent compatibility change; shipping only the removed hash field is unsafe.

No live migration is part of that implementation grant. After code review and
merge, prepare an exact-source dry-run packet for the two paths, with historical
preimages, artifact mappings, backups, no-writer window, runtime identity,
rollback limits, and capped continuation checks. Ryan separately grants runtime
promotion, conversion, hold release, and any paid continuation. Commit-cost
slice 1 can keep its own review/grant sequence; semantic compatibility must be
classified before using it with converted sources.

Review must resolve: the semantic-input inventory and epoch bump discipline;
whether each legacy producer is reconstructable; the schema/namespace atomic
publication boundary; and the recovery protocol's supported cross-deploy set.
None of those are answered by this proposal's existence.

**TL;DR:** [Arc Codex] Bind reuse to a versioned semantic descriptor, retaining
R2b identity as provenance and live writer authority. Convert proven-compatible,
quiescent legacy checkpoint/cache sets atomically; preserve today's two refused
sessions until exact-source migration and release are separately authorized.

<!-- src: ../../incremental_jsonl.py, ../../chroma_write_store.py, ../../eval_corpus/r2b_v2/coverage/inventory.py, ../../eval_corpus/r2b_v2/coverage/authority_manifest.py — baseline continuity, cache, recovery, and authority behavior -->
<!-- src: ../../incremental_retry_state.py, ../../watch.py, ../../tests/test_incremental_index_contract_inventory.py — hold behavior and existing contract test boundary -->
<!-- ref: ./STATUS-codex-jsonl-production-integration.md, ./INVARIANTS-watch-incremental-index.md — Arc Codex context; proposed semantic-key change supersedes no accepted contract until reviewed -->

# Architecture — Kiro JSONL Incremental Production Integration

**Arc:** Codex

**Date:** 2026-09-09

**Status:** Proposed architecture; implementation, live indexing, watcher
activation, provider calls, migration, and production enablement are unauthorized

**Author:** Codex

**Review lane:** Kiro, before any Cursor Execute grant

## 1. Decision

ConvMem will integrate the reviewed Kiro JSONL incremental state machine at the
existing one-file ingest boundary. The path is absent-or-false by default and
is eligible only when all of these are true:

1. `[index.incremental_jsonl].enabled = true` in the loaded production config;
2. normal adapter detection returns exactly `jsonl_kiro_session`;
3. the source is a canonical, regular, non-symlinked `sess_*/messages.jsonl`;
4. checkpoint and transaction state validate completely; and
5. any existing production projection has an incremental checkpoint. An
   already-indexed source without one returns `bootstrap_required`; it is not
   silently rebuilt and does not spend model calls.

All other inputs use today's whole-file path unchanged. The watcher remains a
debounce/process-isolation surface: it continues to invoke `convmem index
--file`. It does not own cursors, checkpoints, chunking, or recovery.

The reviewed scratch engine is the behavioral reference, but production must
not import `scratch_jsonl_prototype`. Cursor will lift its source-prefix,
continuity, frontier, deterministic-generation, checkpoint, and replay rules
into a production module and preserve a conformance test against the reviewed
transition table. Production adds two seams the scratch store did not need:

- a durable prepared-output cache, so replay never repeats completed
  summarize/distill/embed work; and
- a source-scoped before-image journal, so an incomplete real-Chroma
  transaction can roll forward from cached outputs or roll back exactly when
  the selected source prefix is no longer valid.

This plan lands only disabled code and hermetic evidence. It does not enable the
flag or touch the live configuration, corpus, watcher service, providers, or
source files.

## 2. Product consequence

After a separately authorized bootstrap and activation, an append to a Kiro
session will re-transform only the last chunk whose membership may change plus
new chunks. Stable historical chunks are reused. A crash after an expensive
model call reuses the fsynced prepared output on replay instead of paying for
the same call again.

The first clean index of a new session still transforms the full session. An
already-indexed session cannot be adopted automatically because the legacy
summary rows do not prove the exact model/recipe identity needed for clean-
rebuild equivalence. A later activation grant must either select a new source
or authorize one controlled full rebuild. This is a one-time cost boundary, not
a claim of zero-cost migration.

Chunk size, overlap, prompts, models, embeddings, provenance, dedupe, and
retrieval ranking do not change in this arc. Therefore this integration should
not retune or reinterpret the drifting live golden-retrieval baseline.

## 3. Evidence inherited—and not inherited

The design inherits these reviewed facts from the scratch and live-source
passes now on `main`:

- complete-newline boundary selection and partial-record deferral;
- canonical source identity, device/inode generation identity, prefix digest,
  and mutation/truncation/rotation/fingerprint fallback reasons;
- deterministic generation identity and checkpoint-governed replay;
- crash coverage around generation, upsert, prune, checkpoint, fallback,
  cleanup, and lock transitions;
- exact incremental-versus-clean-rebuild equality on deterministic inputs;
- frontier-bounded transform counters; and
- source-scoped real-Chroma pruning under isolated paths.

It does **not** inherit production PASS for provider behavior, current
`ingest.py` side effects, visibility during two-collection writes, bootstrap of
legacy rows, watcher retry policy, or constant-memory source parsing. Those are
new production seams and receive explicit gates below.

## 4. Existing system and insertion point

Today, every parser returns a full message list. `ingest._index_one_file`
hashes the entire source, parses the entire file, sends every current chunk
through summarize/distill/embed, writes each chunk through the production
writer, then prunes and commits `processed.json`. `watch.py` only detects,
debounces, and starts that same one-file command in a contained subprocess.

Today's stale-row prune is not an ordinary-index behavior. It runs only when
`force_file` causes `_snapshot_reindex_rows()` to capture the old generation
and `_prune_completed_reindex()` runs after a complete replacement. The
incremental coordinator introduces a new per-generation prune on every
successful incremental apply. It reuses the existing source-scoped Chroma
delete/supersede operations, but not the legacy force/reindex trigger. This new
trigger and every one of its crash sides belong in T4 evidence.

The integration remains one local monolith with deep modules:

```text
watch event or manual `convmem index --file`
                    |
                    v
          ingest._index_one_file
                    |
       absent/false flag or non-Kiro ------> existing whole-file path
                    |
                    v
      IncrementalJsonlCoordinator
       |       |          |          |
       |       |          |          +--> existing processed.json follower
       |       |          +-------------> existing units export/dedupe followers
       |       +------------------------> existing writer/pruner -> real Chroma
       +--------------------------------> checkpoint/cache/journal state root
                    ^
                    |
        Kiro complete-prefix adapter view
```

### Chosen production boundaries

| Surface | Responsibility |
|---|---|
| `incremental_jsonl.py` (new) | Source capture, continuity, frontier, transaction state, prepared-output cache, replay/rollback decision, checkpoint publication, follower reconciliation. No provider-specific prompts and no CLI parsing. |
| `adapters/kiro_session_jsonl.py` | Add a complete-prefix parser view that returns canonical messages plus byte ranges and session metadata. Existing `parse()` behavior remains compatible. |
| `ingest.py` | Eligibility dispatch and extraction of one-chunk transform/build from one-chunk commit. Existing summary, distill, embedding, provenance, normalization, and dedupe rules remain the only production transformation semantics. |
| `chroma_store.py` | Add narrow source-row snapshot/restore operations needed by the production journal; all mutations still require the governed writer session and participate in writer coverage/shadow observation. |
| `config.py` / `config.example.toml` | Parse the optional default-off table and expand its state path. Never mutate the live user config. |
| `watch.py` | No incremental algorithm. Existing subprocess route remains. Tests prove it reaches the shared ingest decision only when later activated. |

## 5. Options considered

### A — put byte cursors in `watch.py`

Rejected. Manual indexing and watcher indexing would have different authority
and recovery behavior. Debounce is not a durable commit boundary, and a watcher
restart would have to understand Chroma transactions.

### B — import the scratch engine into production

Rejected. The scratch projection owns a JSON generation store and deterministic
fake rows. Production has real prompts, embeddings, dedupe sidecars, governed
writer coverage, and a read path that queries Chroma directly. Importing the
scratch package would make its explicitly limited claims look production-
authoritative.

### C — a production coordinator at the shared ingest boundary

Chosen. One module owns the complex state machine; the existing adapter and
writer/pruner remain the parsing and storage seams. Both manual and watcher
entrypoints converge on it, and default-off behavior is a single testable
decision.

### D — generation-filter every retrieval query

Deferred. Query-side generation filtering could hide candidate rows until an
atomic pointer flip, but it would change retrieval semantics and every read
surface. The first production slice instead uses a short, source-scoped commit
window plus a durable before-image journal. The brief mixed-visibility window
is disclosed, bounded by replay/rollback, and must be measured in a later
activation canary before it can be accepted for live service.

## 6. Configuration contract

The only new example configuration is:

```toml
[index.incremental_jsonl]
enabled = false
state_dir = "~/.local/share/convmem/incremental-jsonl"
allow_full_rebuild = false
```

Rules:

- missing table and `enabled = false` are behaviorally identical;
- missing/false `allow_full_rebuild` turns mutation, truncation, rotation, or
  transform-fingerprint fallback into `rebuild_required` with zero model or
  write calls; enabling it is a later operational/cost decision;
- the v1 eligible format is hard-coded to `jsonl_kiro_session`; configuration
  cannot broaden it to Cursor, Codex, Copilot, SQLite, `.crush`, steering, or
  inter-model documents;
- `state_dir` is resolved once, must be owned by the current user, may contain
  no symlink component, and is created `0700`; files are `0600`;
- the state root must be distinct from the source tree, Chroma root, export,
  processed log, writer locks, and repository; and
- enabling the example in the repository changes nothing. Only a later,
  explicit edit to the live user config can activate the route.

No CLI `--incremental` switch is added. Configuration expresses the operating
policy and avoids a second ad-hoc entrypoint.

## 7. Source capture and continuity

For each run, the coordinator:

1. canonicalizes the exact Kiro source without following a final symlink and
   rejects symlink components;
2. opens it read-only with `O_CLOEXEC` and `O_NOFOLLOW` where available;
3. records regular-file mode, owner, device/inode, size, and sibling
   `session.json` identity;
4. selects the last complete newline at or before the observed size;
5. copies exactly that prefix and the validated metadata sidecar to a private,
   fsynced snapshot under the state root;
6. reparses only the snapshot through the Kiro adapter; and
7. before publication, reopens/revalidates the live source identity, minimum
   size, selected-prefix SHA-256, and the sibling metadata identity/digest (or
   its continued absence).

A pure append after the selected boundary is allowed and left for the next
run. Replacement, truncation below the boundary, or mutation within the
selected prefix aborts publication. The prior checkpoint remains authoritative.

Malformed complete JSONL records retain today's adapter behavior (skipped),
but their bytes are still part of the prefix commitment. A partial trailing
record is not selected and cannot advance the checkpoint.

## 8. Chunk frontier and transformation identity

The chunk algorithm remains `chunk_messages(size, overlap)` with
`step = max(1, size - overlap)`. Let the prior committed message count be `N`.
The stable prefix ends before the start of the final previously emitted chunk,
because that chunk can gain members after an append. The incremental frontier
is therefore the greatest existing chunk start not greater than `N - 1`; an
empty prior source uses zero. Everything at or after that start is rebuilt.

This rule intentionally reprocesses one overlap-bearing frontier chunk. It is
the minimum safe slice that remains exactly equal to a clean full rebuild.

The transform fingerprint is canonical JSON hashed with SHA-256 and binds:

- adapter format and adapter contract version;
- chunk size, overlap, rendering limits, and message-selection semantics;
- summarize/distill prompt and recipe versions, temperatures, and resolved
  provider/model identities;
- embedding model identity and observed vector dimension;
- normalization, confidence, provenance-envelope, ID, and dedupe contract
  versions; and
- the implementation revision of the production transformation functions.

Any mismatch selects `transform_fingerprint_changed` and a prospective full
fallback from frontier zero. With the default `allow_full_rebuild = false`, the
production result is `rebuild_required` with zero calls or writes. A later
explicit cost/operation grant may enable the controlled rebuild path; hermetic
tests must still prove its full fault/replay matrix.

## 9. Durable state and authority

Each source uses `sha256("jsonl_kiro_session:" + canonical_path)` as its state
directory name. Its files are atomically replaced and parent-directory fsynced:

| File | Meaning |
|---|---|
| `checkpoint.json` | Last complete authority: schema, source identity, device/inode, complete byte boundary, prefix digest, record count, chunk frontier, transform fingerprint, active generation, exact summary/unit manifest, selected-prefix processed hash. |
| `transaction.json` | Incomplete candidate authority: transaction ID, prior checkpoint digest, selected snapshot, candidate generation, phase, expected output/cache keys, affected/candidate row IDs, and follower state. |
| `prepared/<key>.json` | One fully transformed chunk artifact, including summary/unit documents, embeddings, metadata/provenance, and source input commitment. It is written before any Chroma mutation. |
| `rollback.json` | Exact before-images for affected summary/unit rows, plus candidate-only IDs and the prior source-scoped export/processed state. |
| `snapshots/<transaction>/...` | Private selected source prefix and session metadata; diagnostic input until transaction closure. |

The source JSONL remains source authority. `checkpoint.json` is processing and
recovery authority. Chroma, the JSONL export, dedupe logs, and `processed.json`
remain derived projections/followers. A `.next` file is never authority.

Prepared artifacts are content-addressed by source identity, selected chunk
input digest, transform fingerprint, and chunk start. A cache hit is accepted
only after full schema, digest, dimension, provenance, and source binding
validation. Invalid cache is quarantined logically (ignored and reported), not
partially reused.

## 10. Commit protocol

Expensive work happens before mutation and outside the source, export, and
processed-state sidecar locks:

```text
capture complete prefix
→ publish transaction PREPARING
→ transform each frontier chunk
→ fsync each prepared artifact
→ revalidate selected live prefix
→ acquire source lock
→ acquire governed production writer session
→ acquire export lock only for export replacement
→ publish exact rollback before-images
→ transaction APPLYING
→ summary upserts
→ unit upserts
→ source-scoped summary prune
→ source-scoped unit delete/supersede
→ revalidate selected source prefix
→ atomically publish checkpoint.json (COMMITTED authority)
→ reconcile units export and dedupe followers idempotently
→ release export lock
→ release source lock, ending the source-locked apply
→ commit processed.json entry last in its own short critical section
→ transaction COMPLETE and remove rollback/snapshot
```

The enforced invariant in `purge_locks.assert_lock_ordering_ok` is specifically
that a source lock must never be acquired while an export lock is held. The
coordinator satisfies it by acquiring source before export. The complete order
is the writer boundary already held by `index` → source → Chroma session
re-entry → export. Export and source are then released.
`commit_processed_index_entry()` runs afterward as today's independent,
short-lived processed-state transaction: `mutate_processed()` enters its own
`production_writer_boundary(entrypoint="ingest.processed")` and acquires the
existing `processed.json.lock` sidecar through `_processed_lock`. Because
`index()` still holds its outer writer boundary, the writer lease's supported
same-thread re-entry applies. Its in-lock exclusion check may refuse the commit
if exclusion won the interval. No source, export, or processed-state lock is
held across summarize, distill, or embedding calls. The coordinator uses a
separate per-source advisory transaction flock across the run; kernel release
makes stale PID recovery unnecessary.

`processed.json` is a derived follower committed last in that standalone
critical section; its sidecar flock serializes atomic read/mutate/write with
other paths. Publishing it earlier could make the watcher skip an incomplete
checkpoint. Releasing the source lock first preserves current lock composition
rather than introducing source → writer-boundary → processed nesting. If a
crash occurs after checkpoint publication, replay treats Chroma authority as
committed and repairs lagging followers with zero model calls.

## 11. Replay and rollback

At entry, a valid incomplete transaction is resolved before selecting new
work:

- **Roll forward** when the snapshot, prepared artifacts, and selected live
  prefix still validate. Reapply idempotent row operations, prune only the
  recorded source-scoped candidate set, publish the checkpoint, then reconcile
  followers.
- **Roll back** when the selected prefix no longer validates or a prepared
  artifact is invalid. Restore exact before-images to both collections, delete
  candidate-only IDs, restore the source-scoped export/processed preimage, and
  verify exact equality to the prior checkpoint manifest.
- **Fail closed** if neither path can be proven. Do not guess, prune broadly,
  mark processed, or run new provider calls. Emit a stable recovery code and
  preserve state for independent inspection.

Rollback covers only an incomplete transaction. Once `checkpoint.json` is
published and verified, the new generation is committed. Operational rollback
after a completed generation is flag-off plus a separately authorized
whole-source rebuild; this plan does not execute or automate it.

Because Chroma has no atomic commit across its two collections, a reader may
observe a mixed projection during the short APPLYING window or after an abrupt
crash until replay/rollback. The writer lease does not block readers. This is
the largest residual risk and a mandatory measurement in the later production
activation canary.

## 12. Side-effect followers

The current chunk writer appends export and dedupe records while writing
Chroma. Production incremental integration must separate those followers:

- no units-export append occurs inside a partially applied chunk;
- after checkpoint commit, rewrite only the selected source's export rows
  under the existing export lock while preserving all unrelated and malformed
  lines according to the existing export contract;
- dedupe suppression/candidate events receive deterministic transaction/event
  identities so replay is idempotent; semantic-pair uniqueness remains;
- synthesis failure telemetry remains non-authoritative and may append once per
  failed attempt; it is excluded from projection equality; and
- writer attestations, census entries, and Shadow events remain honest mutation
  history. Rollback produces compensating writer events; it never erases
  history.

Every new governed writer route must be registered in the existing C3/R2b
writer inventories and pass the revision-binding gates. No route may be hidden
from a scanner to make CI green.

## 13. Failure and fitness contract

The executable transition inventory must include both sides of every durable
step discovered during implementation, at minimum:

```text
source_snapshot_prepare, source_snapshot_publish, source_revalidate,
transaction_prepare, transaction_phase_publish,
prepared_output_prepare, prepared_output_publish,
rollback_prepare, rollback_publish,
summary_upsert, unit_upsert, summaries_prune, units_prune,
checkpoint_prepare, checkpoint_publish,
export_reconcile, dedupe_reconcile, processed_publish,
transaction_cleanup, snapshot_cleanup, lock_acquire, lock_release
```

An inventory-coverage assertion fails if either `before_` or `after_` crash
evidence is missing. Subprocess crashes must terminate with the designated
test exit and replay from disk in a fresh process.

Fitness functions and the bad outcomes they prevent:

| Gate | Prevented bad outcome |
|---|---|
| Default-off parity | Landing the code changes existing indexing or watch behavior. |
| Exact adapter gate | Another append-heavy format inherits unreviewed semantics. |
| Bootstrap refusal | Existing rows are silently adopted or expensive full rebuilds occur. |
| Transition coverage | An untested durable authority window ships. |
| Exact replay/rollback equality | A crash leaves missing, duplicate, cross-source, or stale rows. |
| Clean rebuild equality | Frontier reuse changes the logical corpus. |
| Frontier call counters | The feature claims savings but re-runs historical transforms. |
| Zero-call crash replay | A crash causes duplicate provider cost. |
| Writer inventory binding | A new production mutation bypasses governance. |
| Live-path tripwires | Tests touch production config, Chroma, locks, exports, or transcripts. |

Thresholds are exact rather than aspirational: one appended message may cause
only the affected frontier chunk(s) to call summarize/distill/embed; unchanged
replay and fully prepared crash replay must call them zero times.

## 14. Security, privacy, and memory

- Test execution uses temporary roots, deterministic local fakes, a scrubbed
  environment, and denied sockets. It never imports credentials into workers.
- Source snapshots and prepared outputs contain private transcript content and
  embeddings. They are user-owned `0700/0600`, never printed, and cleaned only
  after a verified transaction.
- Resolved path containment is checked before opening state, Chroma, config,
  lock, attestation, or census resources in hermetic tests.
- Production source files are opened read-only. No operation writes, renames,
  unlinks, chmods, or locks the source itself.
- `max_units_in_flight` remains a transformed-output bound only. The Kiro
  adapter and selected prefix still materialize memory; no constant-RSS watcher
  claim is made.

## 15. Scope lock

### In scope for later Cursor implementation

- default-off configuration and eligibility;
- production coordinator and lifted state-machine semantics;
- Kiro prefix/byte-range adapter view;
- transform/build versus commit split using current production semantics;
- prepared-output cache, checkpoint, before-image journal, replay/rollback;
- source-scoped writer/pruner/export/dedupe reconciliation;
- hermetic fault, parity, equality, isolation, and writer-governance tests;
- STATUS/VERIFY evidence updates required by the Execute plan.

### Explicitly out of scope

- editing the live config or enabling the flag;
- running `convmem index`, starting/restarting/reloading `convmem-watch`, or
  testing against a live transcript or production Chroma root;
- any provider, paid, network, calibration, or golden-eval call;
- changing chunk size/overlap, prompts, models, ranking, query behavior, or
  golden thresholds;
- adopting existing sources, migration/backfill, corpus rebuild, source purge,
  GC, or production rollback execution;
- `.crush`, SQLite, Cursor, Codex, Copilot, steering, or inter-model expansion;
- query-side generation filtering, constant-memory parsing, or watcher retry
  policy; and
- PR creation, merge, activation, or a production canary without a later Ryan
  grant.

## 16. Review and next authority

Kiro should decide whether this plan is internally coherent, with particular
attention to:

1. whether the before-image journal is sufficient for the real Chroma and
   follower seams;
2. whether checkpoint-before-followers ordering is correct;
3. whether mixed read visibility is honestly bounded rather than hidden;
4. whether bootstrap refusal protects both money and correctness; and
5. whether the Execute plan can prove default-off parity without touching live
   resources.

Kiro review may request plan corrections. It cannot authorize implementation.
After Kiro PASS, Ryan may authorize Cursor Execute separately. That grant still
must stop at evidence; activation and live indexing remain later decisions.

## TL;DR

- Arc Codex integrates only Kiro `messages.jsonl` at the shared ingest boundary,
  behind an absent-or-false default-off flag.
- The production design lifts the reviewed checkpoint/frontier machine and adds
  a fsynced transform cache plus exact before-image rollback for real Chroma.
- Existing sources without checkpoints fail `bootstrap_required`; no silent
  rebuild or provider spend occurs.
- This document authorizes planning only—no implementation, PR, live indexing,
  watcher activation, migration, or provider calls.

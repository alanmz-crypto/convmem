# Execute Plan — Kiro JSONL Incremental Production Integration

**Arc:** Codex

**Date:** 2026-09-09

**Planning author:** Codex

**Implementation lane:** Cursor, only after Ryan's separate Execute grant

**Review lane:** Kiro must review this plan before implementation

**Current authority:** Planning only; do not implement, index, activate, call a
provider, open a PR, or change a service

## Goal and human consequence

Implement the reviewed append-aware Kiro JSONL state machine behind a default-
off production feature flag. Once a later activation is authorized and a
source has a clean checkpoint, ConvMem will transform only the unstable
frontier and new chunks. Fsynced prepared outputs make crash replay zero-call,
reducing repeated summarize, distill, and embedding cost.

This Execute plan deliberately stops before activation. Its result is disabled
production code plus hermetic evidence for Kiro review. It performs no live
indexing, watcher operation, provider call, migration, bootstrap, or corpus
mutation.

The architecture in
[`ARCHITECTURE-codex-jsonl-production-integration.md`](ARCHITECTURE-codex-jsonl-production-integration.md)
is normative. If implementation discovers a concrete contradiction, stop and
return the smallest reproduction to Codex/Kiro; do not improvise a new
authority model.

## Frozen scope

### May change

- `config.py` and `config.example.toml` for the optional default-off table;
- a new production `incremental_jsonl.py` deep module;
- `adapters/kiro_session_jsonl.py` for complete-prefix/byte-range parsing;
- `ingest.py` to split build from commit and route the eligible Kiro input;
- `chroma_store.py` only for narrow governed row snapshot/restore primitives;
- `watch.py` only if a testable no-op/default-off routing seam is strictly
  required; no retry or service-policy expansion;
- focused tests, existing writer-coverage inventories/gates, arc STATUS, and a
  new `docs/plans/VERIFY-codex-jsonl-production-integration.md`;
- `docs/inter-model/LATEST.md` and the implementation handoff at completion.

### Must not change or execute

- live `~/.config/convmem/config.toml` or any production path/default;
- production Chroma, `processed.json`, units export, dedupe queues, source
  transcripts, locks, attestations, or census;
- `convmem index`, `convmem add`, `convmem verify`, watcher start/stop/restart/
  reload, or any service/process state;
- local or paid model/provider calls, sockets, golden evaluation, retrieval
  tuning, chunk parameters, prompts, model selection, or ranking;
- `.crush`, SQLite, Cursor, Codex, Copilot, steering, or inter-model adapters;
- live bootstrap, migration, backfill, rebuild, purge, GC, rollback operation,
  canary, or production enablement;
- query-side generation filtering or constant-memory parser work; and
- PR creation or merge without Ryan's later instruction.

## Execution environment gate (T0, first executable gate)

Before any production-module import in tests, prove a hermetic worker boundary:

1. create a fresh random-token temporary root;
2. relocate config, Chroma, state, processed, export, dedupe, locks,
   attestations, census, source fixtures, HOME, and XDG paths beneath it;
3. reject resolved escapes, symlink components, known production roots, and
   production defaults before constructing a resource;
4. scrub provider credentials and ConvMem production overrides;
5. monkeypatch/deny socket creation, DNS, and outbound connections;
6. allow deterministic fake summarize/distill/embed functions only;
7. run crash workers with `python -I`, closed descriptors, and a fresh process
   group; terminate descendants after injected exit; and
8. assert no production path was opened or mutated and no watcher process or
   service command was invoked.

T0 failure stops Execute. Do not continue with a weaker fixture.

## Ordered tasks

| ID | Deliverable | Depends on | Primary gate |
|---|---|---|---|
| T0 | Hermetic production-integration test boundary | — | Production tripwires and network/provider denial pass before imports |
| T1 | Default-off config and exact Kiro eligibility | T0 | Absent/false parity; non-Kiro refusal; existing source bootstrap refusal |
| T2 | Source capture, adapter ranges, checkpoint and transaction schemas | T1 | Boundary/partial/mutation/rotation/fingerprint matrix |
| T3 | Transform/build split and durable prepared-output cache | T2 | Clean-output parity and zero-call cache replay |
| T4 | Real-Chroma apply, journal, replay/rollback, and followers | T3 | Exhaustive subprocess fault matrix and exact restoration/convergence |
| T5 | Shared ingest/watch routing and compatibility | T4 | Legacy parity; writer inventories; safe reindex and scoped watch tests |
| T6 | Evidence, static checks, and handoff | T5 | VERIFY complete; Kiro-ready exact-tip evidence; stop |

T1–T4 are serial because each freezes authority required by the next. Focused
legacy-parity and inventory tests in T5 may be developed alongside T3/T4 only
after T1 interfaces are stable, but final evidence remains serial.

## T1 — Default-off configuration and eligibility

### Implement

1. Add parsing/path expansion for:

   ```toml
[index.incremental_jsonl]
enabled = false
state_dir = "~/.local/share/convmem/incremental-jsonl"
allow_full_rebuild = false
   ```

2. Add a pure eligibility decision with stable outcomes:

   ```text
   disabled
   ineligible_format
   eligible_new_source
   eligible_checkpointed_source
   bootstrap_required
   invalid_state
   ```

3. Require exact normal detection as `jsonl_kiro_session`. Do not accept a
   caller-provided format string as authority.
4. When source rows or a path entry exist without a valid checkpoint, return
   `bootstrap_required` without parsing, transforming, writing, or falling
   through to legacy ingest.
5. When a checkpointed source requires a mutation/truncation/rotation/
   fingerprint fallback and `allow_full_rebuild` is absent/false, return
   `rebuild_required:<reason>` with zero model and write calls. True is a later
   live cost/operation decision, not set during this Execute.
6. Preserve the old `_index_one_file` branch byte-for-byte where practical when
   the table is missing/false or the format is not Kiro.

### Tests

- missing table equals `enabled=false` in return value, calls, and writes;
- false flag never constructs state/checkpoint machinery;
- true flag cannot select any non-Kiro adapter;
- malformed booleans/paths and symlink/outside state roots fail closed;
- missing/false full-rebuild permission refuses every expensive fallback;
- preexisting processed entry or Chroma rows with no checkpoint produces
  `bootstrap_required` and zero provider/write calls;
- a genuinely new, empty-authority Kiro fixture is eligible in hermetic tests;
- example config is false and no test edits the live config.

## T2 — Source view and durable state contracts

### Implement

1. Extend the Kiro adapter with a production-safe complete-prefix view returning:

   ```text
   messages
   accepted-record byte ranges
   complete byte boundary
   selected-prefix SHA-256
   device/inode identity
   session metadata identity
   ```

   Keep `parse(filepath) -> list[dict]` compatible for all current callers.

2. Implement source capture with read-only/no-follow open, regular-file and
   ownership validation, last-newline selection, private atomic snapshot, and
   before/publication prefix plus sibling-metadata revalidation.
3. Define strict versioned validators for `checkpoint.json`,
   `transaction.json`, prepared artifacts, and `rollback.json`. Unknown
   versions, missing fields, duplicate IDs, dimension drift, invalid digests,
   or path mismatches fail closed.
4. Port the reviewed continuity reasons exactly:

   ```text
   initial_full
   source_identity_changed
   transform_fingerprint_changed
   source_replaced_or_rotated
   source_truncated
   validated_prefix_mutated
   ```

5. Port deterministic generation identity and the overlap-aware frontier rule.
6. Use atomic temp-write → file fsync → replace → parent fsync for all authority
   files. Ignore incomplete `.next` files.
7. Use a per-source advisory flock whose path derives from the configured state
   root and canonical source identity. Crash releases the kernel lock; do not
   invent PID liveness authority.

### Tests

- append, exact chunk boundary, multiple append, blank line, malformed complete
  record, partial record, and later completion;
- append during capture is deferred; mutation in the selected prefix aborts;
- truncation, atomic replacement/rotation with guaranteed distinct identity,
  source-path change, and every fingerprint field change select the declared
  fallback;
- symlink paths, non-regular files, wrong owner/mode, cross-source checkpoint,
  corrupt JSON, stale `.next`, and unsupported schema refuse;
- parser output count equals accepted byte ranges;
- subprocess crash on both sides of snapshot/checkpoint/lock transitions leaves
  either the old authority or a replayable candidate, never a fabricated
  complete checkpoint.

## T3 — Transform build and prepared-output cache

### Implement

1. Refactor current `_process_file_chunks` without changing semantics:
   - a build function consumes one chunk and returns a complete immutable
     artifact containing summary, summary embedding, normalized/provenance-
     attached units, unit embeddings, metadata, IDs, and dedupe inputs;
   - a commit function consumes that artifact and performs no model/provider
     work.
2. Keep the current prompt builders, temperatures, render limits,
   `resolve_generation_binding`, provenance envelope, normalization, ID rules,
   confidence threshold, and embedding functions.
3. Publish each built artifact to the content-addressed cache before any Chroma
   mutation. Reopen and validate bytes/digests before reuse.
4. Do not cache partial/degraded artifacts from a failed summarize, distill, or
   embedding attempt as complete.
5. Count calls separately for summarize, distill, summary embed, and unit embed.
   Counters are evidence, not configuration.

### Tests

- legacy full-file output and refactored build+commit output are exactly equal
  for frozen deterministic inputs, including IDs and provenance;
- corrupt, cross-source, wrong-fingerprint, wrong-dimension, or partial cache
  files are refused;
- crash after each prepared artifact publication replays with zero calls for
  that artifact;
- unchanged replay makes zero calls;
- 1,000-message baseline followed by one append calls only the final unstable
  chunk and any newly created chunks; all stable chunk artifacts are reused;
- exact incremental result equals a clean full rebuild without normalizing IDs,
  metadata, provenance, documents, or embeddings;
- transformed-output residency remains bounded and is labeled as such; no
  constant-memory parser/RSS claim.

## T4 — Governed Chroma transaction, replay, and rollback

### Implement

1. Under the existing production writer boundary, snapshot exact source-scoped
   before-images for all affected summary and unit rows. Include documents,
   embeddings, metadata, IDs, and collection names.
2. Persist and verify `rollback.json` before the first live-store mutation.
3. Apply prepared artifacts through `production_chroma_write_session`; no
   direct `chromadb.PersistentClient` may appear in production coordinator code.
4. Restrict every prune/delete/supersede to both exact canonical `source_path`
   and the transaction's recorded candidate IDs. Preserve unrelated-source
   sentinels.
5. Publish the checkpoint only after both collections and prunes match the
   candidate manifest and the selected source prefix revalidates.
6. Reconcile followers after checkpoint commit:
   - replace only this source's units-export projection under its existing
     lock, preserving unrelated rows;
   - publish deterministic/idempotent dedupe events;
   - release the export lock, then call `commit_processed_index_entry()` last
     while the source lock remains held. That helper retains its existing
     short-lived `processed.json.lock` sidecar for cross-path atomicity.
7. On entry, resolve an incomplete transaction before accepting new work:
   roll forward from valid prepared artifacts; otherwise restore exact before-
   images and remove candidate-only IDs. If proof is insufficient, fail closed.
8. Verify rollback Chroma state and follower source state against the prior
   checkpoint before deleting journal/snapshot files.
9. Register snapshot/restore and incremental writer routes in the governed C3
   and R2b inventories. Shadow/census records remain honest mutation history.

### Mandatory durable transition inventory

The code owns one tuple of transition names. Tests generate both-side crash
points from it and fail if an observed transition is undeclared or a declared
transition lacks coverage. The minimum inventory is the Architecture list;
Cursor must add every newly discovered durable authority transition rather
than hiding or grouping it away.

### Tests

- real Chroma under temporary paths only;
- subprocess exit at `before_` and `after_` every declared transition;
- partial summary/unit writes, both prune sides, checkpoint candidate/publish,
  export, dedupe, processed, cleanup, and rollback restore;
- source changes after partial apply force exact rollback with zero new model
  calls;
- valid source after partial apply rolls forward with zero repeated calls;
- cross-source summary/unit/export sentinels survive every crash and recovery;
- incremental, replayed, rolled-forward, rolled-back, and clean-rebuild
  authorities compare exactly as appropriate;
- a deliberately removed transition side makes coverage assertion fail;
- a corrupt rollback journal fails closed without broad deletion;
- `processed.json` never names the new hash before checkpoint publication;
- the new unconditional per-generation prune runs for normal incremental
  applies, independent of the legacy force/reindex snapshot trigger, and every
  prune transition is in the crash inventory;
- a checkpoint-committed/follower-torn replay repairs followers with zero calls.

## T5 — Shared routing and compatibility

### Implement

1. Route at `_index_one_file` after normal detection/exclusion but before the
   legacy full parse. Keep the coordinator return shape compatible with ingest
   stats.
2. Preserve source exclusion precedence. Exclusion during capture/apply aborts
   without checkpoint or processed publication. Recheck exclusion and commit
   the final processed entry in one source-lock interval; do not remove or
   bypass the existing processed-state sidecar lock.
3. Preserve `force_reindex`/`supersede_on_reindex` behavior on the legacy path.
   The incremental path must refuse force/supersede unless an exact behavior is
   specified by this plan; v1 returns `incremental_force_unsupported` and makes
   no writes.
4. Keep `watch.py`'s subprocess invocation unchanged unless a pure routing test
   seam is required. It must not load or mutate checkpoint state in the watcher
   parent.
5. Refresh writer coverage inventories through their canonical generator and
   inspect the diff. Never hand-edit revision digests or reduce route counts.

### Tests

- current adapter tests and safe-file-reindex tests pass unchanged;
- default-off full ingest and watch behavior match pre-change results and call
  order;
- watch subprocess argv remains `convmem index --file <path>` and still uses
  process-group timeout containment;
- no checkpoint imports/resources in the watch parent hot path;
- path exclusion wins over incremental eligibility and over replay;
- force/supersede refusal is explicit and zero-write;
- C3 writer gate, R2b revision binding, coverage scan, writer census, and
  generated-inventory tests pass at the exact implementation tip.

## T6 — Verification and stop

Cursor creates
`docs/plans/VERIFY-codex-jsonl-production-integration.md` with exact commands,
tip SHA, observed counts, transition inventory, call counters, isolation proof,
and any incidents. It must distinguish:

- default-off production-code evidence;
- hermetic real-Chroma integration evidence;
- inherited scratch/live-source canary evidence; and
- work not run (live source, production corpus, providers, watcher, activation,
  golden eval, repo-wide suite if it can reach live state).

Required gates at the final tip:

1. the focused new isolation/state/cache/transaction/routing tests;
2. existing Kiro adapter, safe-file-reindex, watch, exclusion/purge lock, config,
   writer-coverage, revision-binding, and scratch regression sets;
3. `python -m compileall -q` on changed Python/test surfaces;
4. Pylint on changed Python/test surfaces, with cache redirected to temp if
   required by the sandbox;
5. `git diff --check`;
6. static diff audit proving no live config, runtime data, generated corpus,
   retrieval/ranking, or unrelated adapter changes; and
7. a process/open-file/path audit proving no production resource access.

Do **not** run an unscoped repository-wide suite if it invokes live-corpus
golden evaluation. Select the relevant regression files explicitly. An
unrelated golden miss is not evidence for this arc and should not be provoked.

After gates pass: update the STATUS snapshot, commit, immediately push the
explicit feature refspec, and hand the exact tip to Kiro. Stop. Do not open a
PR until Ryan authorizes one after Kiro review.

## Acceptance matrix

| ID | Acceptance condition | Evidence |
|---|---|---|
| A1 | Missing/false flag is exact legacy behavior | Differential tests and zero coordinator construction |
| A2 | Only Kiro JSONL is eligible | Detection matrix with all adapters |
| A3 | Existing uncheckpointed source cannot spend | `bootstrap_required`, zero calls/writes |
| A4 | Append/partial/mutation/fallback semantics match reviewed machine | State-machine conformance + fault cases |
| A5 | Incremental authority equals clean rebuild | Exact two-collection/checkpoint comparison |
| A6 | Stable history is not retransformed | Frontier counters on large fixture |
| A7 | Crash after prepared output does not repeat cost | Zero-call fresh-process replay |
| A8 | Torn real-Chroma writes converge or restore | Both-side exhaustive crash matrix |
| A9 | No cross-source deletion | Sentinels at every prune/rollback point |
| A10 | Processed/export/dedupe followers cannot outrun checkpoint | Follower-order and repair tests |
| A11 | Production writer governance remains complete | C3/R2b inventory and revision gates |
| A12 | Execute is hermetic and non-operational | Tripwires, socket/provider denial, scope diff |

## Expected handoff to Kiro

The implementation handoff must ask Kiro to verify the exact tip, not merely
trust the VERIFY document. Its review questions are:

1. Does absent/false remain a true no-op?
2. Can any non-Kiro source or existing uncheckpointed source enter the route?
3. Is every expensive output durable before Chroma mutation and reused on
   replay?
4. Can every incomplete transaction either roll forward or restore exact
   before-images without touching another source?
5. Does `processed.json` remain behind checkpoint authority?
6. Are mixed-read visibility and non-constant-memory limits disclosed?
7. Did any test or command touch live state, a watcher, or a provider?

Kiro PASS does not enable the feature. Ryan separately decides PR creation,
merge, bootstrap/canary authorization, and eventual live activation.

## TL;DR

- Cursor's later Execute has six serial gates: hermetic isolation, default-off
  eligibility, source/state, cached transforms, real-Chroma recovery, and
  compatibility/evidence.
- Existing uncheckpointed sources fail without spending; a crash reuses fsynced
  outputs and checkpoint-governed replay/rollback repairs both Chroma
  collections and followers.
- Execute must stop at pushed evidence for independent Kiro review—no live
  indexing, watcher activation, providers, migration, PR, or merge.

# EXECUTION — Bounded-memory brief metadata reads

**Arc:** Trapdoor Hunt (issue #268 operational follow-up; does not reopen the
closed provenance T3 gate)

**Status:** DRAFT FOR KIRO REVIEW. Planning only. This file authorizes no code,
configuration, service, corpus, provider, or production operation.

**Date:** 2026-09-13

## 1. Consequence for Ryan

PR #302 removed the export compactor's corpus-sized Python allocation, but a
small watched transcript can still trigger a global brief refresh that reads
every Chroma metadata value into memory. The live corpus stores roughly 0.98
GiB of repeated `provenance_envelope` strings that the brief does not use, and
the current brief path can retain more than one complete metadata view at once.

The narrow correction adds a projected streaming read primitive and makes the
brief derive its recent decisions, monitor rows, project rollup, and unresolved
count from one bounded scan. It preserves the brief payload and rendering
contract, leaves stored metadata unchanged, and does not alter ingestion,
provenance authority, Chroma/HNSW, watcher policy, memory caps, or Arc Codex P2.

## 2. Evidence and corrected diagnosis

The issue #268 recurrence produced four watch-child cgroup OOM kills at roughly
12.5 GiB RSS while the triggering Codex transcripts were only 5.8–9.7 MiB.
Arc Codex did not change that active watcher route. PR #302, squash-merged as
`a91bb28b97aa038fde0d14caeee1b7f75b3ae094`, replaced whole-export Python
materialization with disk-backed compaction.

A later hermetic phase profile at that merged tree measured:

| Phase | 5,000 units | 20,000 units | 58,825 units |
|---|---:|---:|---:|
| `collection_metadata_rows()` | 141.8 MiB | 498.7 MiB | 1,425 MiB |
| `refresh_brief_after_change()` | 314.0 MiB | 974.8 MiB | 2,684 MiB |
| Combined path with new compactor | 411.6 MiB | 1,363 MiB | 3,005 MiB |

The same compactor alone processed a 2 GiB export at 28.9 MiB peak RSS. A
read-only live-corpus call to `collection_metadata_rows()` peaked at 1,504 MiB.
Dropping `provenance_envelope` from a 20,000-unit synthetic read reduced peak
RSS from about 497 MiB to 168 MiB; shrinking documents had negligible effect.
Memory followed corpus size rather than trigger size.

The code explains the stacking:

1. `chroma_readonly.collection_metadata_rows()` calls `fetchall()`, then builds
   and returns one complete dictionary per embedding.
2. `brief.gather_brief_data()` builds a `ReadonlyUnitStore` for unresolved
   counting and retains it until the function returns.
3. `_recent_decisions()`, `_recent_monitor_units()`, and
   `gather_project_activity()` each perform another complete metadata read.
4. `build_ledger_index()` may retain the unresolved-count metadata graph in its
   process-lifetime cache.

Making only `fetchall()` lazy would therefore be incomplete: the brief would
still retain full rows in `ReadonlyUnitStore`, repeat scans, and cache unused
large fields.

The measured phases establish a substantial corpus-sized floor but do not by
themselves account for the entire 12.5 GiB live-child peak. Chroma's Rust
bindings also reserve roughly 2.63 GiB of virtual address space at construction,
and the hermetic profile did not load the live embedding/model stack. This slice
removes the next demonstrated allocator; it does not claim full issue #268
closure or authorize watcher resumption.

### 2.1 Diagnostic boundary incident

The profiling session was authorized for temporary resources only but performed
one read-only live Chroma measurement and accidentally wrote the default live
`brief.md` because `refresh_brief_after_change(cfg)` does not derive its output
path from `cfg`. The session reports that it immediately regenerated the live
brief, that the export remained byte-identical, and that logical projection and
index-gate checks still passed. It also reports a live `chroma.sqlite3` mtime
change caused by the write-capable brief open.

Those actions exceeded the diagnostic boundary. This plan does not ratify them
or infer additional live authority from the reported recovery. Every new test
or memory worker must set an explicit temporary brief path and assert that the
production default path and production Chroma path are never opened. No further
live verification is authorized by this plan.

## 3. Scope lock

### In scope

- Add a general read-only iterator in `chroma_readonly.py` that groups one
  embedding at a time and can select an explicit metadata-key projection.
- Preserve `collection_metadata_rows()` as the compatibility list-returning
  wrapper for existing non-brief callers.
- Replace the brief's repeated full scans and full `ReadonlyUnitStore` with one
  projected streaming scan and bounded aggregates.
- Build the unresolved-count graph from projected ledger fields only, without
  populating the process-lifetime full-row ledger cache.
- Preserve the existing `gather_brief_data()`, `gather_brief_payload()`,
  rendering, CLI, and MCP output contracts.
- Add parity, read-only, resource-lifecycle, adverse-row, and hermetic memory
  verification.
- Intentionally refresh any code-derived writer/authority inventories and
  baseline hashes that the final implementation changes.

### Out of scope

- Changing or deduplicating `provenance_envelope` storage at write time.
- Migrating, rewriting, compacting, or repairing existing Chroma metadata.
- Changing provenance representation, commitments, root bindings, or source
  authority.
- Changing `ReadonlyUnitStore` semantics for query, doctor, purge, recovery,
  or other callers.
- Altering Chroma/HNSW construction, model loading, OpenBLAS/thread settings,
  cgroup limits, watcher timeout/debounce/cooldown, or exclusions.
- Append-aware Codex watcher indexing.
- Production profiling, live brief generation, live indexing, source
  re-inclusion, watcher/systemd operation, or configuration changes.
- Arc Codex Gate 0, P2 grant preparation, digest issuance, live P2, or
  activation.

## 4. Existing observable contract

The implementation must preserve these current brief results on the same
stable corpus snapshot:

1. `units`, `summaries`, inventory counts, service state, watch memory, MCP
   registration, Kiro exclusion state, handoff freshness, and standing checks
   retain their existing meaning.
2. Recent decisions remain the five newest decision rows by timestamp; project
   filtering still considers title, document, site, and source path.
3. Recent monitor results remain the three newest rows whose `tool` is
   `convmem-monitor`, with the same project filtering.
4. Project activity retains the same source-derived newest activity, counts,
   formats, knowledge-unit counts, and three newest applicable titles.
5. `unresolved_count` continues to use the existing ledger kind, relation,
   verification, status, and supersession semantics. Errors remain fail-soft as
   `None`, as today.
6. Project-scoped and unscoped brief payloads render byte-equivalent stable
   fields after normalizing timestamps and environment probes.
7. `refresh_brief_after_change()` remains best-effort and quiet on failure.

This slice changes the internal read shape, not the public brief schema or the
meaning of any field.

## 5. Chosen design

### 5.1 Deep read-only iterator

Add one general primitive in `chroma_readonly.py`:

```python
iter_collection_metadata_rows(
    chroma_dir,
    collection_name,
    *,
    metadata_keys=None,
    include_document=True,
) -> Iterator[dict]
```

The exact parameter spelling may change during implementation, but the contract
must remain narrow:

- open `chroma.sqlite3` with the existing URI `mode=ro` helper;
- never create a Chroma client, WAL, SHM, collection, or file;
- use parameterized SQL for the collection and projected keys;
- keep `ORDER BY e.embedding_id, em.key` and emit a dictionary when the
  embedding id changes;
- iterate the cursor directly—no `fetchall()`, complete row list, or complete
  grouped dictionary;
- map `chroma:document` to the existing `document` field only when requested;
- always close cursor and connection on exhaustion, exception, or explicit
  generator close;
- produce the same dictionaries as `collection_metadata_rows()` when no
  projection is requested.

`collection_metadata_rows()` becomes `list(iter_collection_metadata_rows(...))`
with the full projection so every existing caller retains its current type and
behavior. This keeps the compatibility cost below the new deep iterator instead
of forcing a repository-wide migration.

### 5.2 One brief-owned projected pass

Add one private brief aggregation function that consumes the iterator once.
Its key allowlist is the documented union required by:

- recent decisions and project matching;
- recent monitor rows and project matching;
- project activity;
- unresolved graph/status calculation; and
- scalar lifecycle fields only: `superseded` for current filter parity and
  `deleted` for the pinned projected contract.

The projected output fields are pinned to this exact union:

```text
id, ledger_id, ledger_kind, type, relates_to, timestamp, result,
verification_result, severity, site, domain, title, summary, tool,
source_path, superseded, deleted, document
```

`id` comes from `embedding_id`; `document` comes from the
`chroma:document` row. The SQL metadata-key allowlist is therefore the fields
above except `id`, plus `chroma:document` when document inclusion is enabled.
Implementation may change parameter names but may not add fields to this union
without returning the plan to Kiro.

The allowlist must exclude `provenance_envelope`, provenance commitments,
embeddings, and every other field not used by the brief contract. In
particular, `provenance_envelope`, `provenance_commitment`, and
`provenance_assertion_id` are forbidden. A test must fail if any forbidden or
unapproved field appears in the projection.

The brief does not call `evidence.filter_superseded_decisions()` or
`provenance_identity()`. Those search/ask paths validate full provenance
identity and legitimately require `provenance_envelope`; they are outside this
brief-read correction and must not be imported or invoked by the new aggregate.
Brief parity uses only scalar lifecycle fields already present in the projected
row. The current brief excludes a row only when `superseded is True`;
projecting `deleted` must not independently change inclusion unless the C0
oracle proves that behavior already exists.

During the pass:

- keep only the five newest applicable decisions and three newest applicable
  monitor rows using bounded top-N selection with deterministic timestamp and
  row-id tie-breaking;
- update per-project counts and retain only the three newest applicable titles
  per project rather than all titles;
- retain only rows with a non-empty `ledger_id` for unresolved calculation,
  and only their projected ledger/status fields;
- discard every other row after its aggregates are updated.

No accumulator may retain `document` except for a bounded decision/monitor
candidate, and no accumulator may retain any provenance envelope.

### 5.3 Compact unresolved graph without the full-row store

Extract a metadata-iterable form of the ledger-index operation (for example,
`build_ledger_index_from_metadata(rows)`) and have the existing
`build_ledger_index(store)` delegate to it. Similarly, expose the smallest
metadata-iterable helper needed for `list_unresolved()` or unresolved counting,
while preserving the current store-taking API for existing callers.

The brief calls the metadata-iterable path on projected ledger rows. It must not
construct `ReadonlyUnitStore`, call `units_metadata()`, or populate
`_LEDGER_INDEX_CACHE`. The compact graph may scale with the number of ledger
records, but its per-record fields are explicitly bounded to the ledger/status
projection rather than the full corpus metadata payload.

Before building the compact graph, apply exactly the current scalar lifecycle
filter from `ReadonlyUnitStore.units_metadata()`: exclude a row only when
`superseded is True`. `deleted` remains available to existing ledger/status
consumers but is not a new brief exclusion rule.
Do not substitute provenance-identity or assertion-level supersession logic;
that would both change semantics and pull the forbidden envelope back into the
read path.

This avoids a brief-specific fake store and keeps ledger graph semantics in the
ledger/unresolved modules that own them.

### 5.4 Resource and consistency boundary

The brief is a best-effort orientation snapshot, not a transaction over a live
writer. A single SQLite read connection provides one consistent read snapshot
for the projected metadata pass. Counts obtained by separate existing helpers
may reflect a neighboring commit, as they can today; this slice does not claim a
new atomic cross-query snapshot.

The iterator must not be shared across threads or survive its aggregation call.
Failures close the read connection. The existing brief fail-soft boundaries
remain visible: unresolved-count failure yields `None`; top-level refresh prints
one skip message and does not publish a partial brief.

### 5.5 Hermetic output boundary

Production behavior keeps the existing default `brief.md` destination. Tests
and measurement workers must call `write_brief(..., out_path=<temporary path>)`
or patch the module-level destination before invoking the refresh wrapper.
Passing a temporary config alone is not evidence that output is redirected.

Every hermetic worker must install path-denial guards before importing the
target modules and fail if it attempts to open the production Chroma directory,
production export, production brief, watcher/systemd, or a provider socket.

## 6. Alternatives considered

### A. Only replace `fetchall()` with cursor iteration — rejected

It removes one temporary list but leaves complete grouping, repeated scans, the
full `ReadonlyUnitStore`, and the ledger cache. The measured allocation would be
reduced but not structurally removed.

### B. Add separate SQL query functions for every brief field — rejected

SQL-side filtering can be efficient, but four bespoke query paths duplicate
Chroma schema knowledge and lose the one-snapshot/one-scan property. A general
projected iterator plus brief-owned aggregation is the deeper boundary.

### C. Deduplicate provenance envelopes at write time — deferred

One source-level envelope plus per-unit commitment could remove the underlying
71× storage repetition, but it changes provenance representation, recovery,
rebuild, and read-resolution authority. That belongs to a separate architecture
and migration plan, not an operational OOM corrective.

### D. Disable brief refresh after watched indexing — rejected

This avoids the trigger but removes orientation freshness and leaves other
brief callers exposed to the same corpus-sized read.

### E. Raise the child memory cap again — rejected

The allocation grows with corpus metadata and would consume any larger fixed
cap eventually. The correct boundary is to stop reading unused payloads.

## 7. Cursor implementation sequence

Implementation requires a separate Ryan Execute authorization after Kiro PASS.

### C0 — Freeze current brief semantics

Build a small deterministic Chroma fixture containing decisions, observations,
verifications, monitor rows, project rows, superseded rows, equal timestamps,
documents, and large provenance envelopes. Capture the current normalized brief
payload and rendered output as the golden oracle before refactoring. For equal
timestamps, explicitly record the current stable-sort order (metadata scan order,
therefore embedding id ascending) so the candidate's deterministic tie-break
proves parity rather than redefining it.

### C1 — Add projected streaming iteration

Implement the iterator and make `collection_metadata_rows()` its compatibility
wrapper. Prove full-mode parity, projection accuracy, document inclusion rules,
empty/missing collection behavior, exception cleanup, early-close cleanup, and
strict SQLite read-only behavior.

### C2 — Extract metadata-iterable ledger semantics

Add the reusable ledger/unresolved helpers and delegate the old store APIs to
them. Prove identical ledger indexes, relation deduplication, evidence status,
ordering, filtering, and unresolved counts on the C0 fixture.

### C3 — Implement the single-pass brief aggregate

Route recent decisions, recent monitor rows, project activity, and unresolved
count through one projected iterator. Use bounded top-N structures and exact
tie-breakers. Remove the brief's `ReadonlyUnitStore` and repeated unprojected
metadata scans without changing public function signatures or payload fields.

### C4 — Prove fail-soft and no-retention behavior

Add adversarial tests for malformed optional values, missing timestamps,
duplicate ledger ids, superseded rows, project filters, equal timestamps,
iterator failure at every row boundary, early generator close, and connection
failure. Assert no unprojected scan and no `_LEDGER_INDEX_CACHE` mutation occur
during brief generation. Assert the requested and returned projection is exactly
the pinned field union and contains none of `provenance_envelope`,
`provenance_commitment`, or `provenance_assertion_id`; trap any call to
`filter_superseded_decisions()` or `provenance_identity()` from the brief path.

### C5 — Prove the hermetic boundary

Run `write_brief()` and the refresh wrapper against only temporary config,
Chroma, inventory, processed state, and output. Path-denial hooks must prove no
production path, service, provider, or network access. Reproduce the diagnostic
mistake as a negative control: temporary config without explicit output
redirection must not be used by the memory worker.

### C6 — Prove bounded memory and output parity

Use fresh subprocesses over 5,000, 20,000, and 58,825-unit synthetic Chroma
fixtures with the measured metadata shape and 32 KiB `provenance_envelope`
values. Build fixtures outside the measured worker. Run the candidate read path
under a 2 GiB address-space ceiling and report import baseline, peak RSS,
elapsed time, rows, output digest, and projected keys.

Acceptance requires:

- every candidate run completes below **384 MiB peak RSS** on the implementation
  host;
- the 58,825-unit run is no more than **160 MiB above import baseline**;
- changing envelope size from 2 KiB to 32 KiB at fixed row count changes peak
  RSS by no more than **32 MiB**;
- no returned or retained row contains `provenance_envelope`;
- normalized payload and rendered brief match the C0 golden oracle;
- production paths remain unopened and unmodified.

The PR records the large-run evidence. CI runs semantic/resource tests and a
smaller memory smoke with a generous ceiling; it does not enforce host-specific
large-RSS thresholds.

### C7 — Refresh governed evidence and stop

Run focused brief, readonly-store, ledger, unresolved, doctor, query, writer
inventory, Arc Codex baseline/default-off, and repository-wide tests as required
by touched surfaces. Refresh code-derived inventories and baseline hashes
honestly. Run `compileall`, `git diff --check`, scoped pylint, and the pylint
regression gate. Commit, push the exact tip, provide memory evidence, and stop
for Copilot's targeted safety/evidence audit. No PR or live operation.

## 8. Verification matrix

| Risk | Required proof |
|---|---|
| Projection silently changes brief meaning | C0 golden payload/render parity and explicit tie tests |
| Large envelope or provenance identity is still fetched | Exact projected-key trap, forbidden provenance-field assertions, and envelope-size RSS comparison |
| Generator still retains the corpus | 5k/20k/58,825 RSS curve and early-close fd test |
| Full-row store/cache survives in brief | Trap `ReadonlyUnitStore`; assert ledger cache unchanged |
| Project titles grow without bound | Top-three per-project accumulator tests |
| Read helper mutates SQLite | URI `mode=ro`, no WAL/SHM, identity/mtime checks |
| Partial brief published after read failure | Injected iteration failures and byte-identical prior output |
| Test hits production paths | Pre-import denial hooks and before/after path canaries |
| Default-off/P2 boundary regresses | Arc Codex baseline and live-denial tests |
| Broader issue #268 falsely declared closed | PR/VERIFY text retains the residual OOM caveat |

## 9. Delivery and gate order

1. Kiro reviews this plan and returns PASS, CONDITIONAL PASS, or FAIL.
2. Ryan separately authorizes Cursor Execute C0–C7.
3. Cursor implements in a fresh worktree, verifies hermetically, pushes an exact
   tip, and stops without opening a PR.
4. GitHub Copilot audit lane performs a targeted safety/evidence audit.
5. Kiro reviews the exact implementation tip after Copilot PASS.
6. Ryan decides PR and squash-merge disposition.
7. After merge, a new hermetic end-to-end memory diagnostic decides whether
   Chroma/model/thread allocations still block watcher resumption.
8. Only after that evidence may Ryan separately reconsider exclusions, watcher
   operation, and the paused Arc Codex P2 grant packet.

No review, merge, or memory PASS in this sequence authorizes production access,
watcher operation, configuration change, source re-inclusion, Gate 0, P2,
grant issuance, or activation.

## 10. Jargon glossary

- **Projection:** selecting only metadata keys a consumer actually uses.
- **Streaming iterator:** emits one grouped metadata row at a time instead of
  retaining the complete result.
- **Bounded top-N:** retains only the few newest rows required for output.
- **Ledger graph:** the decision/observation/verification relation index used to
  derive unresolved status.
- **Golden oracle:** the current normalized output captured before refactoring
  and used to prove semantic parity.
- **Fail-soft:** orientation failure is reported or represented as unavailable
  without crashing the completed ingest operation.
- **Exact-tip review:** review of one immutable commit SHA in an isolated clean
  worktree.

## TL;DR

- The remaining demonstrated OOM floor is the brief's repeated, retained full
  metadata reads, dominated by unused duplicated provenance envelopes.
- Add one projected streaming iterator and one brief-owned bounded aggregate;
  preserve the existing full-list API and brief output contract.
- The plan includes a hard hermetic path-denial gate after the diagnostic
  exceeded its production boundary.
- Kiro reviews first; no implementation, watcher action, or Arc Codex P2 work is
  authorized by this document.

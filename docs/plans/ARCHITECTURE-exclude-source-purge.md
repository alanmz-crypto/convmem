# Architecture: Exclude Source Purge

**Date:** 2026-07-14
**Branch:** `plan/2026-07-14-exclude-source-purge`
**Worktree:** `~/.local/share/convmem/worktrees/plan-2026-07-14-exclude-source-purge`
**Status:** Architecture planning — awaiting HITL before Execution
**Lane:** Kiro (design/sign-off)

---

## Problem

`convmem exclude PATH` marks a source file as excluded from future indexing but leaves all previously derived data intact across three sinks:

1. **Chroma knowledge_units** — distilled units with `source_path` metadata
2. **Chroma conversation_summaries** — chunk summaries with `source_path` metadata
3. **knowledge_units.jsonl** — append-only JSONL export of distilled units

This is by design for the soft-exclude use case (the source was noisy but not sensitive). However, when the motivation is **privacy purge** — the source contains credentials, PII, or content that must not persist in any derived form — soft exclusion is insufficient. The derived payloads remain searchable and exportable.

The existing `convmem forget UNIT_ID` command tombstones individual units but:
- Requires manual per-unit identification
- Uses tombstoning (superseded=True), which **retains the document payload** in Chroma
- Does not touch conversation_summaries or the JSONL export
- Is designed for single-fact correction, not source-level purge

### What is needed

A `convmem exclude PATH --purge` flag that:
- Performs hard deletion (not tombstoning) of all derived data for the exact source
- Covers all three sinks atomically from the perspective of searchability
- Closes the race window where a concurrent ingest writer could re-derive data from a source being purged
- Preserves the exclusion marker so re-indexing cannot resurrect purged content

### Why --purge is not --forget

| Property | forget (tombstone) | purge (hard delete) |
|----------|-------------------|---------------------|
| Payload retained | Yes (superseded=True) | No — removed from all sinks |
| Reversible | Yes (--undo clears superseded) | No — re-index from source required |
| Scope | Single unit by ID | All derived data for one source path |
| Use case | Stale/wrong fact | Privacy, credentials, sensitive content |
| Audit trail | Tombstone metadata in Chroma | Exclusion marker in processed.json + CLI exit code |

---

## Scope

### In scope

- `convmem exclude PATH --purge` CLI surface
- Hard deletion from all three derived sinks
- Per-source advisory flock to serialize against concurrent ingest writers
- Fresh exclusion check immediately before each derived-write batch (ingest side)
- Exact canonical path matching (no substring/glob)
- Dry-run preview with counts per sink (default behavior before confirmation)
- `--yes` flag for automation
- `--undo` only re-enables future ingest; cannot resurrect purged rows
- Crash/retry safety: partial purge remains excluded, returns nonzero, converges on retry
- Deterministic race tests for both interleavings

### Out of scope

- Distributed/multi-machine purge
- Chroma compaction/vacuum after deletion (Chroma handles this internally)
- Purge from Restic snapshots (operational — separate procedure)
- Glob/pattern-based purge (exact path only)
- `forget` changes (separate feature, separate tombstone semantics)
- Changes to the governed-decision conflict-detection protocol



---

## Design Alternatives

### Design A: Single Source Lock (purge holds source flock; ingest re-checks under same flock)

**Mechanism:**

1. Derive a per-source lock path from the canonical source path (e.g., SHA-256 of the resolved path → `~/.local/share/convmem/locks/source/<hash>.lock`).
2. **Purge path:** acquire source flock → mark exclusion in processed.json (under existing processed lock) → delete from Chroma knowledge_units → delete from Chroma conversation_summaries → remove lines from knowledge_units.jsonl → release source flock.
3. **Ingest path (modified):** parse + LLM + embed work happens **without** any lock. Immediately before each batch write (Chroma upsert + JSONL append), acquire the same source flock → re-check exclusion status from processed.json → if excluded, abort write and return → else write batch → release source flock.
4. **Lock ordering:** source flock is always acquired **before** the processed.json sidecar flock (which is held only for the read-mutate-write of processed.json). The JSONL export append is covered by the source flock (no separate export lock needed because the source flock serializes all writes for that source).
5. **Unrelated sources:** an ingest of source B is never blocked by a purge of source A — the locks are per-source.

**Crash behavior:**
- Purge crashes after Chroma delete but before JSONL cleanup → exclusion marker already set → retry will find fewer/zero Chroma rows, proceed to JSONL cleanup, succeed.
- Purge crashes before exclusion marker → nothing happened, source remains indexed, retry from scratch.
- Ingest crashes mid-batch → partial Chroma rows may exist; next ingest run will either re-derive them (if not excluded) or they'll be orphaned (if excluded between crash and retry). Orphans are cleaned on next purge retry.

**Trade-offs:**
- Pro: Simple lock hierarchy (one lock per source, one global processed lock). No cross-source contention.
- Pro: No lock held during expensive LLM/embed work.
- Pro: The re-check pattern is already proven in `commit_processed_index_entry`.
- Con: JSONL export purge requires scanning the entire file to find lines matching the source path. For the current corpus size (~17K lines) this is sub-second, but scales O(n).
- Con: Source flock granularity means two purges of different sources can run in parallel — good for throughput but requires care that JSONL rewrite is safe (only one writer at a time per file, not per source).

### Design B: Global Purge Lock + Source Exclusion Check

**Mechanism:**

1. A single global purge lock (`~/.local/share/convmem/locks/purge.lock`) serializes all purge operations.
2. **Purge path:** acquire global purge lock → mark exclusion → delete from all three sinks sequentially → release.
3. **Ingest path:** no lock change from today's design. The existing `commit_processed_index_entry` re-checks exclusion under the processed lock before committing. The race window is: ingest writes Chroma rows, then purge runs and deletes them, then ingest tries to commit processed.json and finds the path excluded — commit fails, but orphan Chroma rows were already cleaned by purge.
4. **Export lock:** a separate `export.lock` serializes all JSONL export writes (both ingest appends and purge rewrites). Lock ordering: purge lock → export lock → processed lock.

**Crash behavior:**
- Same marker-first pattern as Design A.
- Global lock means only one purge at a time — simpler reasoning about JSONL rewrite safety.

**Trade-offs:**
- Pro: Simpler JSONL safety — global purge lock means no concurrent JSONL rewrite possible.
- Pro: Easier to reason about: one purge at a time, period.
- Con: Global purge lock blocks unrelated purges from running in parallel. At current scale (rare manual operation) this is irrelevant.
- Con: Does NOT close the full race: ingest can write Chroma rows for source A **while** purge is deleting them (no per-source serialization). Purge would need to re-scan after marking exclusion to catch in-flight rows — effectively requiring two passes.
- Con: The two-pass requirement makes crash recovery more complex (did the second pass run?).

---

## Comparison

| Criterion | Design A (per-source flock) | Design B (global purge lock) |
|-----------|----------------------------|------------------------------|
| Race closure | **Closed** — writer holds source lock during Chroma write; purge holds same lock during delete | **Open** — writer can interleave Chroma writes between purge passes |
| Lock contention on unrelated sources | None | None (purge is rare) |
| JSONL safety | Requires separate export lock or source-lock coverage | Global purge lock covers JSONL naturally |
| Crash idempotency | Simple: marker-first, retry converges | Requires tracking which of two passes completed |
| Complexity | One lock type (per-source) + one existing lock (processed) + one new lock (export) | One global + one export + processed |
| Ingest latency impact | Source flock acquired only during batch write (fast path: check + release) | No change to ingest |
| Correctness proof | Lock identity = source path → serialized per-source | Requires two-pass argument for completeness |

---

## Chosen Design: A (per-source flock)

**Rationale:** The primary requirement is closing the race between an in-flight writer and a concurrent purge of the same source. Design A achieves this with a single mechanism (per-source flock) that the ingest path already approximates via `commit_processed_index_entry`. Design B leaves the race open and requires a compensating second pass, which adds crash-recovery complexity without buying simplicity.

**Accepted downside:** JSONL export purge under a per-source lock requires a separate export lock to prevent corruption when an unrelated ingest appends to the same JSONL file concurrently. This adds one lock to the hierarchy but is straightforward (append vs rewrite serialization).

---

## Gate Decisions

| # | Gate | Decision |
|---|------|----------|
| 1 | `--purge` semantics | Hard removal from all derived sinks. Not tombstoning. Tombstones retain payloads — unacceptable for privacy purge. |
| 2 | Derived sinks covered | Three: Chroma knowledge_units, Chroma conversation_summaries, knowledge_units.jsonl. All must reach zero for the purged source. |
| 3 | Race closure mechanism | Per-source advisory flock. Ingest acquires before each derived-write batch; purge acquires while marking exclusion and clearing derived state. No lock across parse/LLM/embed. |
| 4 | Export lock | Separate `export.lock` serializes JSONL file mutations (purge rewrite vs ingest append). Acquired after source lock, before processed lock. |
| 5 | Path matching | Exact canonical path equality only. `Path(target).expanduser().resolve()` compared with `==`. Legacy path variants (pre-resolve stored paths) handled by querying Chroma with both the raw and canonical form. No substring, no glob. |
| 6 | Crash/failure behavior | Exclusion marker written first (under processed lock). Partial purge remains excluded, returns exit code 1, and converges safely on retry (each sink deletion is idempotent). |
| 7 | --undo behavior | Re-enables future ingest only. Cannot resurrect purged rows — document and JSONL lines are gone. Re-indexing must be explicit (`convmem index --file PATH --force`). |
| 8 | Confirmation UX | Default: dry-run preview showing counts per sink. Requires explicit `y` confirmation (default No). `--yes` bypasses for automation. Never prints stored document content. |
| 9 | Malformed JSONL lines during export purge | Fail closed. If a line cannot be parsed as JSON, the purge aborts the JSONL rewrite, leaves the original file intact, returns nonzero. Does not create undo artifacts containing purged payloads. |
| 10 | Test requirements | Deterministic tests for: purge-then-ingest interleaving, ingest-then-purge interleaving, unrelated export append preservation, exact-path boundaries (similar but non-matching paths), partial failure + retry idempotency, dry-run/decline (no mutation), inter-model doc indexing path, all three sinks reaching zero after purge. |



---

## Lock Ordering

All advisory locks are acquired in this fixed order. Reverse acquisition is prohibited and must be enforced by code review + test assertion.

```
1. source flock  (~/.local/share/convmem/locks/source/<path-hash>.lock)
2. export flock  (~/.local/share/convmem/locks/export.lock)
3. processed flock  (<processed_log>.lock — existing sidecar)
```

**Rules:**
- A thread/process holding lock N must never acquire lock N-1.
- Source flock is per-source (SHA-256 of canonical path → filename). Different sources = independent locks.
- Export flock is global (one JSONL file).
- Processed flock is the existing `_processed_lock` in `ingest.py` (unchanged).
- No lock is held across LLM calls, embedding calls, or network I/O.

**Who acquires what:**

| Operation | Source flock | Export flock | Processed flock |
|-----------|-------------|-------------|-----------------|
| Purge (full sequence) | Yes (held for duration of sink cleanup) | Yes (during JSONL rewrite) | Yes (during exclusion mark) |
| Ingest batch write | Yes (during Chroma upsert) | Yes (during JSONL append) | Yes (during commit) |
| Ingest parse/LLM/embed | No | No | No |
| Plain exclude (no --purge) | No | No | Yes (existing behavior) |
| Plain --undo | No | No | Yes (existing behavior) |

**Purge lock acquisition sequence:**

```python
with source_flock(canonical_path):          # Lock 1
    mark_exclusion(processed_path, ...)     # Acquires processed flock internally (Lock 3)
    delete_chroma_units(store, path)        # No additional lock needed
    delete_chroma_summaries(store, path)    # No additional lock needed
    with export_flock():                    # Lock 2
        rewrite_jsonl_without_source(export_path, path)
```

Note: processed flock (Lock 3) is acquired inside `mark_exclusion` which is called while holding Lock 1. This is legal because 1 < 3 in the ordering. Export flock (Lock 2) is acquired while holding Lock 1 — also legal (1 < 2).

**Ingest batch write lock sequence:**

```python
# After parse/LLM/embed completes (no locks held):
with source_flock(canonical_path):          # Lock 1
    if is_excluded(processed_path, path):   # Read under source lock (no processed flock needed for read)
        return  # abort batch
    with ChromaStore(chroma_dir) as store:
        store.add_unit(...)                 # Chroma write
        store.add_summary(...)             # Chroma write
    with export_flock():                    # Lock 2
        append_to_jsonl(export_path, unit)
    commit_processed_index_entry(...)       # Acquires processed flock internally (Lock 3)
```

---

## Crash and Failure Matrix

| Failure point | State after crash | Retry behavior | Converges? |
|---------------|-------------------|----------------|------------|
| Before exclusion marker written | Source not excluded; no sinks touched | Full retry from scratch | Yes — idempotent |
| After exclusion marker, before Chroma unit delete | Excluded in processed.json; Chroma units still present | Retry finds fewer/same units in Chroma, deletes them | Yes |
| After Chroma unit delete, before summary delete | Excluded; units gone; summaries present | Retry deletes remaining summaries | Yes |
| After summary delete, before JSONL rewrite | Excluded; Chroma clean; JSONL still has lines | Retry rewrites JSONL (idempotent — same lines removed) | Yes |
| During JSONL rewrite (tmp file written, not yet renamed) | Original JSONL intact (atomic rename not reached) | Retry sees original, rewrites again | Yes |
| After JSONL rewrite completes | Full purge complete | Retry finds zero in all sinks, succeeds (exit 0) | Yes |
| Ingest batch write during purge (source lock contention) | Ingest blocks on source flock until purge completes | Ingest proceeds, finds path excluded, aborts batch | Yes — no orphans |
| Purge during ingest batch write (source lock contention) | Purge blocks on source flock until batch completes | Purge proceeds, deletes the just-written rows | Yes — converges to empty |
| JSONL has malformed line | Purge aborts JSONL rewrite, returns nonzero | Operator must fix malformed line manually; retry succeeds after fix | Yes (with manual intervention) |
| Chroma write lock contention (another process holds sqlite) | Chroma raises "database is locked" | Purge retries with backoff (3 attempts); if exhausted, returns nonzero with exclusion intact | Yes on retry |

**Invariant:** At no point can a source be both (a) excluded in processed.json and (b) have its derived data restored by any automatic process. The exclusion marker is the gate; it is written first and cleared only by explicit `--undo`.

---

## Path Matching

### Canonical resolution

```python
canonical = str(Path(target).expanduser().resolve())
```

All comparisons use `==` on the canonical string. No substring matching, no fnmatch, no regex.

### Legacy path variants

Chroma metadata may store either the raw path or the canonical path (depending on when the data was indexed). The purge must query Chroma with **both** forms to ensure complete removal:

```python
raw_path = str(Path(target).expanduser())
canonical_path = str(Path(target).expanduser().resolve())
for query_path in dict.fromkeys([raw_path, canonical_path]):
    delete_units_for_source(store, query_path)
    delete_summaries_for_source(store, query_path)
```

This pattern already exists in `ingest.py` (the `for sp in dict.fromkeys([path, path_key])` loop in the force-reindex path).

### JSONL matching

Lines in `knowledge_units.jsonl` contain a `source_path` field. Match using the same canonical comparison:

```python
keep = []
for line in lines:
    rec = json.loads(line)
    if str(Path(rec.get("source_path", "")).expanduser().resolve()) == canonical_path:
        continue  # purge this line
    keep.append(line)
```

---

## CLI Surface

```
convmem exclude PATH --purge [--reason REASON] [--yes]
```

**Behavior:**

1. Resolve PATH to canonical form.
2. Verify file exists (warn if not — purge proceeds regardless since derived data may exist for a deleted source).
3. **Preview (default):** query all three sinks, display counts:
   ```
   Purge preview for: /home/lauer/.cursor/.../transcript.jsonl
     Chroma knowledge_units:       12 units
     Chroma conversation_summaries: 4 summaries
     knowledge_units.jsonl:          8 lines

   This will PERMANENTLY DELETE all derived data. This cannot be undone.
   Proceed? [y/N]:
   ```
4. If declined or not `--yes`: exit 0, no mutation.
5. If confirmed: acquire source lock, execute purge sequence, report results.
6. Exit 0 on full success. Exit 1 on partial failure (with exclusion intact).

**Never prints:** document content, summary text, or unit payloads. Only counts and the source path.

---

## Interaction with Existing Features

| Feature | Impact |
|---------|--------|
| `convmem exclude PATH` (no --purge) | Unchanged. Marks exclusion, does not touch derived sinks. |
| `convmem exclude --undo PATH` | Clears exclusion marker. After purge, derived data is gone — undo only re-enables ingest. |
| `convmem index --file PATH --force` | After undo, this re-derives data from the source. Required to restore after purge+undo. |
| `convmem forget UNIT_ID` | Unchanged. Per-unit tombstone for different use case. |
| `convmem watch` | Calls index with force_file. Exclusion check fires as today — no change needed. |
| `convmem refine` | Operates on Chroma rows. If a source was purged, there are no rows to refine. No change needed. |
| `inter_model_index.py` | Same purge mechanism applies — units indexed via this path have `source_path` metadata and are covered by the Chroma delete. |
| Governed decisions (dec_*) | Purge deletes by source_path, not by ledger_id. A governed decision that was derived from a purged source is removed. The decision in `decisions-approved.jsonl` is NOT touched (that's the ledger, not a derived sink). |

---

## Builder-Reference Alignment

| Digest | Principle applied |
|--------|-------------------|
| **DDIA** | Derived data is separate from source of truth. Purge removes derived (Chroma + JSONL export); the source file and processed.json exclusion marker are the durable state. Ledger (`decisions-approved.jsonl`) is untouched. |
| **Ousterhout** | Deep module: `purge_source(path)` hides lock acquisition, sink enumeration, crash recovery. CLI is thin delegate. Define errors out of existence: malformed JSONL → fail closed (not silent skip). |
| **Hard Parts** | Trade-off worksheet applied (Design A vs B above). Least-worst chosen. Accepted downside documented. No microservice split proposed. |
| **Arch Patterns Python** | Unit of Work pattern: purge is atomic from searchability perspective (source lock held for duration). Repository pattern: all Chroma access via `ChromaStore` methods. |

---

## Fitness Functions

| Check | Guards against |
|-------|---------------|
| `test_purge_then_ingest_race` | Regression where ingest can write after purge completes |
| `test_ingest_then_purge_race` | Regression where purge misses in-flight rows |
| `test_all_sinks_zero` | Purge leaves residual derived data |
| `test_unrelated_export_preserved` | Purge corrupts unrelated JSONL lines |
| `test_exact_path_boundary` | Substring matching accidentally purges unrelated source |
| `convmem doctor` (future) | Orphaned Chroma rows where source_path is excluded (drift check) |

---

## Sign-off

**Architecture Planning:** this artifact.
**HITL:** Ryan approves gates 1–10 and the Design A choice before Execution begins.
**Execution:** separate `EXECUTION-exclude-source-purge.md` after gate acceptance.

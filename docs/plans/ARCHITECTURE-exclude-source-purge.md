# Architecture: Exclude Source Purge

**Date:** 2026-07-14 (amended)
**Branch:** `plan/2026-07-14-exclude-source-purge`
**Worktree:** `~/.local/share/convmem/worktrees/plan-2026-07-14-exclude-source-purge`
**Status:** Architecture planning — awaiting HITL before Execution
**Lane:** Kiro (design/sign-off)
**Amendments:** 12 review corrections integrated (export writer inventory, lock identity derivation, missing-file exclusion key, guarantee correction, logical-vs-forensic framing, expanded failure injection, no-lock-during-LLM test, path-candidate builder, superseded cache invalidation, preview/mutation separation, architecture contradiction resolved, temp-config behavioral demos)

---


## Problem

`convmem exclude PATH` marks a source file as excluded from future indexing but leaves all previously derived data intact across three sinks:

1. **Chroma knowledge_units** — distilled units with `source_path` metadata
2. **Chroma conversation_summaries** — chunk summaries with `source_path` metadata
3. **knowledge_units.jsonl** — append-only JSONL export of distilled units

This is by design for the soft-exclude use case (the source was noisy but not sensitive). However, when the motivation is **privacy purge** — the source contains credentials, PII, or content that must not persist in any derived form — soft exclusion is insufficient. The derived payloads remain searchable and exportable.

### What --purge provides

A `convmem exclude PATH --purge` flag that:
- Performs **logical removal** from all active derived stores for the exact source
- Covers all three sinks with a post-deletion verification that counts reach zero
- Closes the race window where a concurrent ingest writer could re-derive data from a source being purged
- Preserves the exclusion marker (source fence) so no automatic process can restore purged content

### What --purge is NOT

This is **logical removal from active derived stores**, not forensic erasure. After purge:
- Chroma's SQLite/HNSW files may retain deleted bytes in free-space pages until compaction
- Filesystem blocks may retain content until overwritten
- Restic snapshots taken before purge still contain the derived data
- The source file itself is untouched (purge removes derived data, not the source)

If forensic erasure is required (e.g., regulatory compliance), additional operational steps are needed: Chroma directory rebuild from scratch, secure filesystem wipe, Restic snapshot pruning. Those are out of scope for this feature.

### Why --purge is not --forget

| Property | forget (tombstone) | purge (hard delete) |
|----------|-------------------|---------------------|
| Payload retained in Chroma | Yes (superseded=True) | No — rows deleted from collection |
| Reversible | Yes (--undo clears superseded) | No — re-index from source required |
| Scope | Single unit by ID | All derived data for one source path |
| Use case | Stale/wrong fact | Privacy, credentials, sensitive content |
| Residual bytes | Document text in Chroma storage | Possible in free-space/snapshots |

---


## JSONL Export Writer Inventory (Amendment §1)

Every code path that writes to `knowledge_units.jsonl` must acquire the **export lock** derived from the configured `units_export` path. The inventory:

| Writer | Module | Operation | Current lock | Required change |
|--------|--------|-----------|-------------|-----------------|
| Normal ingest append | `ingest.py` (main loop, chunk batch) | `open(units_export, "a").write(json.dumps(unit))` | None | Acquire export flock before append |
| Inter-model append | `inter_model_index.py` (`index_inter_model_messages`) | `open(units_export, "a").write(json.dumps(unit))` | None | Acquire export flock before append |
| Observe append (new unit) | `observe.py` (`ingest_observation`) | `open(units_export, "a").write(json.dumps(unit))` | None | Acquire export flock before append |
| Observe upsert/rewrite | `observe.py` (`_upsert_jsonl_line`) | Full file read → line replace → `open("w").writelines()` | None | Acquire export flock for full rewrite |
| Deduplicate compaction | `ingest.py` (`_deduplicate_units_export`) | Full file read → dedup → `tmp.write_text()` → `tmp.replace()` | None | Acquire export flock for full rewrite |
| **Purge rewrite (new)** | purge module | Full file read → filter → `tmp.write_text()` → `tmp.replace()` | Source flock (new) | Acquire export flock under source flock |

**Invariant:** All six writers use one export lock derived from the actual `units_export` path in config. A concurrent unrelated append (source B) must survive a purge rewrite (source A) — the export lock serializes them.

**Barrier test (N3-extended):** Thread A holds export lock and rewrites JSONL (purge of source X). Thread B attempts append for source Y. Thread B blocks, then appends successfully after A releases. Final file contains all source-Y lines plus zero source-X lines.

---

## Lock Identity Derivation (Amendment §2)

### Source lock identity

Derived from the **configured data root** — specifically the parent directory of `processed_log` in config (which is the canonical data root `~/.local/share/convmem/`):

```python
def source_lock_dir(cfg: dict) -> Path:
    """Lock directory derived from configured data root."""
    data_root = Path(cfg["index"]["processed_log"]).expanduser().resolve().parent
    return data_root / "locks" / "source"

def source_lock_path(cfg: dict, canonical_path: str) -> Path:
    """Per-source lock file. Identity = SHA-256 of canonical path."""
    lock_dir = source_lock_dir(cfg)
    path_hash = hashlib.sha256(canonical_path.encode()).hexdigest()
    return lock_dir / f"{path_hash}.lock"
```

### Export lock identity

Derived from the **actual `units_export` path** in config:

```python
def export_lock_path(cfg: dict) -> Path:
    """Export lock file. Identity = sidecar of configured units_export."""
    export_path = Path(cfg["index"]["units_export"]).expanduser().resolve()
    return export_path.with_suffix(export_path.suffix + ".lock")
```

### Alternate-data-root test (N15)

A test using a temporary config with a non-default data root must prove:
- Ingest and purge targeting the same source compute identical source lock paths
- The lock directory is under the configured data root, not hardcoded `~/.local/share/convmem/`
- No live paths are touched during the test

---


## Exclusion Marker for Missing Files (Amendment §3)

When `--purge` is invoked on a PATH that no longer exists on disk, no content hash can be computed. The exclusion marker must still be:
- **Path-addressable** — identified by canonical path, not content hash
- **Stable** — survives across sessions without the file being present
- **Compatible** with `--list`, `--undo`, and `watch_skip_reason`
- **Testable** — covered by a named test

### Design

Use a synthetic hash key: `"purged:<sha256-of-canonical-path>"` as the processed.json entry key. The entry shape:

```json
{
  "purged:<sha256-of-canonical-path>": {
    "path": "/resolved/canonical/path.jsonl",
    "excluded": true,
    "exclude_reason": "purge: <reason>",
    "purged_at": "2026-07-14T15:00:00Z"
  }
}
```

**Why this works:**
- `exclude --list` iterates entries with `excluded: true` and prints `path` — works unchanged
- `exclude --undo PATH` resolves target, iterates entries matching `_processed_path_str(ep) == path_key` — works unchanged (path-based match, not hash-based)
- `watch_skip_reason` checks path equality on excluded entries — works unchanged
- `_path_is_excluded` checks path equality — works unchanged
- The synthetic key never collides with a real SHA-256 content hash (prefix `purged:` is not hex)

**When file exists:** use the real content hash as today (existing behavior). The synthetic key is only for the missing-file case.

**Test (N16):** Purge a path whose file has been deleted. Verify: marker created, `--list` shows it, `--undo` clears it, `watch_skip_reason` returns "excluded", a subsequent `convmem index` skips it.

---

## Guarantee (Amendment §4 — corrected)

### What purge guarantees on success (exit 0)

1. The exclusion marker is durable in processed.json (source fence).
2. All three live sinks have been verified to contain **zero** rows for the purged source — an under-lock postcondition check runs after deletion and before releasing the source lock.
3. No automatic process (watch, index, refine) can restore derived data for the excluded source. The exclusion marker is the fence; it is written first and checked by all writers before committing.

### What purge does NOT guarantee

- **Instant invisibility during purge execution.** Between acquiring the source lock and completing all deletions, a concurrent read query may still see rows being deleted. Query-side filtering by exclusion status is **out of scope** for this feature. The window is brief (sub-second for typical sources) and bounded by the source lock hold time.
- **Forensic erasure.** See "What --purge is NOT" above.

### What a failed/crashed purge leaves

- The source is excluded (marker written first).
- Some or all derived rows may remain searchable until retry succeeds.
- Exit code is nonzero, signaling incomplete purge.
- Retry converges: each sink deletion is idempotent; the postcondition check only passes when all sinks reach zero.

### Postcondition check

After all delete operations and before releasing the source lock:

```python
# Under source flock:
remaining_units = store.count_units_for_source(canonical_path)
remaining_summaries = store.count_summaries_for_source(canonical_path)
remaining_jsonl = count_jsonl_lines_for_source(export_path, canonical_path)
if remaining_units + remaining_summaries + remaining_jsonl > 0:
    return PurgeResult(exit_code=1, message="postcondition failed: residual rows")
```

---


## Design Alternatives

### Design A: Per-Source Flock + Export Lock (chosen)

**Mechanism:**

1. Derive a per-source lock path from SHA-256 of the canonical source path, under the configured data root's `locks/source/` directory.
2. Derive the export lock path as a sidecar of the configured `units_export` path.
3. **Purge path:** acquire source flock → mark exclusion in processed.json (under processed lock) → delete from Chroma knowledge_units → delete from Chroma conversation_summaries → acquire export flock → rewrite knowledge_units.jsonl without purged lines → release export flock → postcondition check (all sinks zero) → release source flock.
4. **Ingest path (modified):** parse + LLM + embed work happens **without** any lock. Immediately before each batch write: acquire source flock → re-check exclusion status → if excluded, abort → else: Chroma writes → acquire export flock → JSONL append → release export flock → commit processed entry (under processed lock) → release source flock.
5. **Unrelated sources:** an ingest of source B is never blocked by a purge of source A — the source locks are per-source. Both share the export lock for JSONL serialization.

**Crash behavior:**
- Purge crashes after Chroma delete but before JSONL cleanup → exclusion marker set → retry finds fewer/zero Chroma rows, proceeds to JSONL cleanup, postcondition passes.
- Purge crashes before exclusion marker → nothing happened, retry from scratch.
- Ingest crashes mid-batch → partial Chroma rows may exist; next watch/index run re-derives them (if not excluded) or purge retry cleans them.

**Trade-offs:**
- Pro: Race fully closed per-source. No lock during LLM/embed.
- Pro: Export lock is separate and explicit — all six JSONL writers use it.
- Pro: The re-check pattern is already proven in `commit_processed_index_entry`.
- Con: Two lock types (source + export) plus existing processed lock = three locks in the hierarchy.
- Con: JSONL scan is O(n) for purge rewrite. Acceptable at ~17K lines.

### Design B: Global Purge Lock (rejected)

**Mechanism:** Single global lock serializes all purge operations. Ingest unchanged from today.

**Why rejected:** Does not close the in-flight writer race. Ingest can write Chroma rows for source A while purge is deleting them. Requires two-pass compensating scan, which complicates crash recovery and the postcondition proof.

---

## Comparison

| Criterion | Design A (per-source + export) | Design B (global purge) |
|-----------|-------------------------------|-------------------------|
| Race closure | **Closed** — source lock serializes writer and purge | **Open** — requires two-pass |
| JSONL safety | Export lock serializes all 6 writers | Global purge covers rewrite but not concurrent appends |
| Postcondition provable | Yes — under source lock, no concurrent writer | Requires second scan |
| Lock count | 3 (source, export, processed) | 3 (global, export, processed) |
| Unrelated contention | None (per-source) | Purge blocks purge |

---

## Chosen Design: A (per-source flock + export lock)

**Rationale:** Closes the race with one mechanism. Postcondition check is trivially correct under the source lock (no concurrent writer can add rows). Design B requires a compensating second pass that is harder to prove correct under crash.

**Accepted downside:** Three-lock hierarchy adds cognitive complexity. Mitigated by: (a) lock ordering is fixed and tested (N9), (b) no lock held during expensive work, (c) existing processed lock unchanged.

---


## Gate Decisions

| # | Gate | Decision |
|---|------|----------|
| 1 | `--purge` semantics | Hard removal (logical deletion from active derived stores). Not tombstoning. Tombstones retain payloads. Not forensic erasure (residual bytes in free-space/snapshots acknowledged). |
| 2 | Derived sinks covered | Three: Chroma knowledge_units, Chroma conversation_summaries, knowledge_units.jsonl. Postcondition verifies all reach zero under source lock. |
| 3 | Race closure mechanism | Per-source advisory flock. Ingest acquires before each derived-write batch; purge acquires while marking exclusion and clearing derived state. No lock across parse/LLM/embed (tested: N17). |
| 4 | Export lock | Derived from configured `units_export` path. All six JSONL writers acquire it. Lock ordering: source > export > processed. |
| 5 | Path matching | Exact canonical path equality only. One shared path-candidate builder produces the query set for preview and all three purge sinks. Does not canonicalize empty or non-filesystem `source_path` values into cwd. Preserves `ledger:*` and unrelated paths unchanged. |
| 6 | Crash/failure behavior | Exclusion marker written first. Partial purge remains excluded, returns nonzero, converges on retry. Postcondition check after deletion; failure = nonzero exit. |
| 7 | --undo behavior | Re-enables future ingest only. Cannot resurrect purged rows. Re-indexing explicit. |
| 8 | Confirmation UX | Read-only preview (separate function from mutation orchestrator). Counts per sink. Confirmation/--yes in thin CLI only. Default No. Never prints stored document content. |
| 9 | Malformed JSONL lines during export purge | Fail closed. Abort rewrite, original intact, nonzero exit. No undo artifacts with purged content. |
| 10 | Test requirements | Deterministic tests for: both race interleavings, unrelated export append survival, exact-path boundaries, expanded failure injection at every step, retry idempotency, dry-run/decline, inter-model path, all sinks zero, lock ordering, no-lock-during-LLM, alternate-data-root lock identity, missing-file exclusion. |
| 11 | Superseded cache | `invalidate_superseded_cache(chroma_dir)` called after hard unit deletion (units may have had `superseded=True` before purge; cache count must not go stale). |
| 12 | Source lock identity | Derived from configured data root (`processed_log` parent), not hardcoded path. Tested with alternate config (N15). |

---

## Lock Ordering

All advisory locks are acquired in this fixed order. Reverse acquisition is prohibited and tested (N9).

```
1. source flock   (data_root/locks/source/<sha256-of-canonical-path>.lock)
2. export flock   (<units_export>.lock — sidecar of configured export path)
3. processed flock (<processed_log>.lock — existing sidecar, unchanged)
```

**Rules:**
- A thread/process holding lock N must never acquire lock N-1.
- Source flock is per-source. Different sources = independent locks.
- Export flock is global (one JSONL file, all six writers).
- Processed flock is unchanged from today's `_processed_lock`.
- No lock is held across LLM calls, embedding calls, or network I/O (tested: N17).

**Who acquires what:**

| Operation | Source flock | Export flock | Processed flock |
|-----------|-------------|-------------|-----------------|
| Purge (full sequence) | Yes (held for entire sink cleanup + postcondition) | Yes (during JSONL rewrite) | Yes (during exclusion mark) |
| Ingest batch write | Yes (during Chroma upsert + JSONL append + commit) | Yes (during JSONL append) | Yes (during commit) |
| Observe append | No (single-unit; no source concept) | Yes (during JSONL append) | No |
| Observe upsert/rewrite | No | Yes (during full JSONL rewrite) | No |
| Deduplicate compaction | No (not source-specific) | Yes (during full JSONL rewrite) | No |
| Ingest parse/LLM/embed | No | No | No |
| Plain exclude (no --purge) | No | No | Yes (existing) |

**Purge lock acquisition sequence:**

```python
with source_flock(cfg, canonical_path):               # Lock 1
    mark_exclusion(processed_path, ...)               # Acquires Lock 3 internally
    delete_chroma_units(store, path_candidates)
    delete_chroma_summaries(store, path_candidates)
    invalidate_superseded_cache(chroma_dir)           # Amendment §9
    with export_flock(cfg):                           # Lock 2
        rewrite_jsonl_without_source(export_path, path_candidates)
    # Postcondition check (Amendment §4):
    assert_all_sinks_zero(store, export_path, path_candidates)
```

**Ingest batch write lock sequence:**

```python
# After parse/LLM/embed completes (no locks held) — tested by N17:
with source_flock(cfg, canonical_path):               # Lock 1
    if is_excluded(processed_path, path):
        return  # abort batch
    with ChromaStore(chroma_dir) as store:
        store.add_unit(...)
        store.add_summary(...)
    with export_flock(cfg):                           # Lock 2
        append_to_jsonl(export_path, unit)
    commit_processed_index_entry(...)                 # Acquires Lock 3 internally
```

---


## Path-Candidate Builder (Amendment §8)

One shared function produces the set of path strings to query across preview and all three purge sinks. This prevents divergence between what preview counts and what purge deletes.

```python
def build_path_candidates(target: str) -> list[str]:
    """Exact path candidates for Chroma/JSONL queries.

    Rules:
    - expanduser + resolve for canonical form
    - Also include expanduser-only (legacy stored paths may lack resolve)
    - Deduplicate (dict.fromkeys preserves order)
    - Do NOT canonicalize empty strings or non-filesystem prefixes (e.g., "ledger:*")
      into cwd — return them unchanged or skip them
    """
    raw = str(Path(target).expanduser())
    canonical = str(Path(target).expanduser().resolve())
    return list(dict.fromkeys([canonical, raw]))
```

**JSONL matching uses the same candidates:**

```python
def line_matches_purge(rec: dict, candidates: list[str]) -> bool:
    sp = rec.get("source_path", "")
    if not sp or sp.startswith("ledger:") or not sp.startswith("/"):
        return False  # non-filesystem paths are never purge targets
    resolved = str(Path(sp).expanduser().resolve())
    return resolved in candidates or sp in candidates
```

**Preview, Chroma delete, and JSONL rewrite all receive the same `candidates` list** from `build_path_candidates`. No separate canonicalization logic per sink.

---

## Expanded Crash and Failure Matrix (Amendment §6)

Failure injection must be testable at every boundary:

| # | Failure point | State after crash | Retry behavior | Converges? | Test |
|---|---------------|-------------------|----------------|------------|------|
| F1 | Before exclusion marker written | Not excluded; no sinks touched | Full retry from scratch | Yes | N18a |
| F2 | After exclusion marker, before Chroma unit delete | Excluded; units present | Retry deletes units | Yes | N18b |
| F3 | After unit delete, before summary delete | Excluded; units gone; summaries present | Retry deletes summaries | Yes | N18c |
| F4 | After summary delete, before export lock acquired | Excluded; Chroma clean; JSONL has lines | Retry rewrites JSONL | Yes | N18d |
| F5 | After export lock acquired, before JSONL validation | Excluded; Chroma clean; JSONL intact | Retry validates + rewrites | Yes | N18e |
| F6 | During JSONL write (tmp written, rename not reached) | Excluded; Chroma clean; original JSONL intact | Retry sees original, rewrites | Yes | N18f |
| F7 | After JSONL rename, before postcondition check | Excluded; all sinks empty | Retry postcondition passes | Yes | N18g |
| F8 | Postcondition check finds residual rows | Excluded; some rows remain (bug or race) | Returns nonzero; operator investigates | Yes on retry if cause resolved | N18h |
| F9 | Chroma "database is locked" | Excluded; partial Chroma delete | Retry with backoff; idempotent deletes | Yes | N5 |
| F10 | JSONL has malformed line | Excluded; Chroma clean; JSONL rewrite aborted | Operator fixes line; retry succeeds | Yes (manual) | N10 |

**Invariant across all failure points:** The exclusion marker, once written (F2+), prevents any automatic writer from adding new derived rows. Failed purge may leave existing rows searchable, but cannot grow.

---

## Scope

### In scope

- `convmem exclude PATH --purge` CLI surface
- Logical deletion from all three active derived sinks
- Per-source advisory flock + export flock to serialize against concurrent writers
- Fresh exclusion check before each derived-write batch (ingest side)
- Exact canonical path matching via shared path-candidate builder
- Read-only preview (separate function) with counts per sink
- Confirmation/--yes in thin CLI layer only
- `--undo` re-enables future ingest only; cannot resurrect purged rows
- Crash/retry safety with expanded failure injection tests
- Postcondition check under source lock
- Superseded-cache invalidation after hard unit deletion
- Missing-file exclusion key (synthetic hash)
- Deterministic race tests for both interleavings + all failure points

### Out of scope

- Forensic erasure (Chroma free-space, filesystem blocks, Restic snapshots)
- Distributed/multi-machine purge
- Query-side filtering by exclusion status during purge window
- Glob/pattern-based purge (exact path only)
- `forget` changes (separate feature)
- Changes to the governed-decision conflict-detection protocol

---


## Preview vs Mutation Separation (Amendment §10)

The purge implementation is split into two independent functions:

1. **`preview_purge(cfg, canonical_path) -> PurgePreview`** — read-only. Opens Chroma read-only, scans JSONL, returns counts per sink. No locks acquired (read-only queries). No mutations. Can be called without confirmation.

2. **`execute_purge(cfg, canonical_path, reason) -> PurgeResult`** — mutating. Acquires source lock, marks exclusion, deletes from sinks, runs postcondition. Returns exit status.

The CLI (`convmem.py`) is the thin layer that:
- Calls `preview_purge` and formats output
- Handles confirmation prompt / `--yes` flag
- Calls `execute_purge` only after confirmation
- Formats result and sets exit code

This keeps the confirmation UX out of the domain logic (Ousterhout: push specialization upward).

---

## Architecture Contradiction Resolution (Amendment §11)

The original v1 stated in Design A §4: "no separate export lock needed because the source flock serializes all writes for that source." This was incorrect — the source flock only serializes writes for **one source**, but the JSONL file is shared across **all sources**. A purge rewrite of source A under source-A's lock does not prevent an ingest append for source B (which holds source-B's lock).

**Resolution:** The export lock is required and is explicitly part of Design A. All six JSONL writers acquire it. The source lock serializes the per-source race (purge vs ingest of the same source); the export lock serializes the file-level race (any JSONL mutation vs any other JSONL mutation).

---

## CLI Surface

```
convmem exclude PATH --purge [--reason REASON] [--yes]
```

**Behavior:**

1. Resolve PATH via `build_path_candidates`. If PATH does not exist on disk, warn but proceed (derived data may exist for a deleted source — Amendment §3 applies).
2. **Preview:** call `preview_purge` (read-only), display counts:
   ```
   Purge preview for: /home/lauer/.cursor/.../transcript.jsonl
     Chroma knowledge_units:       12 units
     Chroma conversation_summaries: 4 summaries
     knowledge_units.jsonl:          8 lines

   This is logical removal from active derived stores.
   Residual bytes may persist in Chroma free-space, filesystem blocks, and Restic snapshots.
   This cannot be undone (re-indexing from source required after --undo).
   Proceed? [y/N]:
   ```
3. If declined or not `--yes`: exit 0, no mutation.
4. If confirmed: call `execute_purge`, report results.
5. Exit 0 on full success (postcondition passed). Exit 1 on partial failure (exclusion intact, retry needed).

**Never prints:** document content, summary text, or unit payloads. Only counts and the source path.

---

## Interaction with Existing Features

| Feature | Impact |
|---------|--------|
| `convmem exclude PATH` (no --purge) | Unchanged. Marks exclusion, does not touch derived sinks. |
| `convmem exclude --undo PATH` | Clears exclusion marker. After purge, derived data is gone — undo only re-enables ingest. |
| `convmem index --file PATH --force` | After undo, this re-derives data from the source. Required to restore after purge+undo. |
| `convmem forget UNIT_ID` | Unchanged. Per-unit tombstone for different use case. |
| `convmem watch` | Exclusion check fires as today. Source lock on batch write (new). |
| `convmem refine` | No rows to refine for purged source. No change needed. |
| `inter_model_index.py` | Source lock + export lock on batch write (new). Same purge mechanism applies. |
| `observe.py` (append) | Export lock on JSONL append (new). No source lock (single-unit, not source-bound). |
| `observe.py` (upsert) | Export lock on JSONL rewrite (new). |
| `_deduplicate_units_export` | Export lock on JSONL rewrite (new). |
| Governed decisions (dec_*) | Purge deletes by source_path. `decisions-approved.jsonl` (ledger) untouched. |
| Superseded cache | Invalidated after hard unit deletion (Amendment §9). |

---

## Builder-Reference Alignment

| Digest | Principle applied |
|--------|-------------------|
| **DDIA** | Derived data separate from source of truth. Purge removes derived; ledger untouched. Single-writer per source via flock. |
| **Ousterhout** | Deep module: `execute_purge` hides locks, sinks, postcondition. Preview is separate (no mutation in read path). Define errors out of existence: malformed JSONL → fail closed. Consistency: one path-candidate builder shared everywhere. |
| **Hard Parts** | Trade-off worksheet (A vs B). Least-worst chosen. Accepted downside: three-lock hierarchy. |
| **Arch Patterns Python** | Repository pattern: Chroma access via `ChromaStore`. Unit of Work: purge sequence under source lock is the unit boundary. Event: `invalidate_superseded_cache` after mutation. |

---

## Fitness Functions

| Check | Guards against |
|-------|---------------|
| `test_purge_then_ingest_race` (N1) | Ingest writes after purge |
| `test_ingest_then_purge_race` (N2) | Purge misses in-flight rows |
| `test_unrelated_export_preserved` (N3) | JSONL corruption of unrelated source |
| `test_all_sinks_zero` (N8) | Residual derived data |
| `test_exact_path_boundary` (N4) | Substring matching |
| `test_no_lock_during_llm` (N17) | Lock held across expensive work |
| `test_alternate_data_root` (N15) | Hardcoded lock paths |
| `test_missing_file_exclusion` (N16) | Missing-file purge fails |
| `test_postcondition_failure` (N18h) | Postcondition silently passes with residual |
| `convmem doctor` (future) | Orphaned rows for excluded source (drift) |

---

## Sign-off

**Architecture Planning:** this artifact (amended).
**HITL:** Ryan approves gates 1–12 and Design A before Execution begins.
**Execution:** separate `EXECUTION-exclude-source-purge.md` after gate acceptance.

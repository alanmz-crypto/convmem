# Handoff: CG-1 Committed-Generation Dependability Work

**Date:** 2026-08-10
**Author:** Kiro (review lane)
**For:** Claude (independent architecture reviewer, no repo access)

---

## What this is

CG-1 ("Committed Generation 1") is a **durability substrate** for ConvMem's file-derived index generations. It ensures that incomplete reindex operations can never corrupt the serving corpus.

This is the highest-priority dependability work in the project right now.

## The problem CG-1 solves

ConvMem indexes files by parsing them into chunks, generating embeddings, and writing units to a Chroma vector database. Before CG-1, this process had a critical defect:

1. **Per-chunk mutation:** Each chunk was written to Chroma immediately as it was processed. If a later chunk failed (LLM timeout, embedding error, OOM), the corpus contained a *hybrid generation* — part of the new index mixed with remnants of the previous one.

2. **Reindex was destructive:** A `--force` reindex deleted existing rows *before* parsing, so interruption could permanently lose data.

3. **No atomic replacement:** There was no mechanism to build a complete replacement and swap it in atomically.

### What existed before CG-1

Two PRs on `main` addressed the immediate dangers but did not solve the structural problem:

- **PR #168** (`028ad75`): Preserve projections until one-file reindex succeeds. Stopped destructive pre-clearing but still commits per-chunk.
- **PR #169** (`e88a3e3`): Added truthful projection-completeness accounting. The system now *knows* when a projection is incomplete, but still produces hybrid state.

CG-1 is the architectural solution: **build a whole generation separately, validate it, then change serving authority through one durable per-owner pointer.**

## Architecture (approved, locked)

The design went through 3 rounds of Codex/Opus review with amendments. Key principles:

### Build ≠ Commit

At every observable moment, ConvMem has one identifiable committed serving generation per source. An incomplete candidate generation is never partially authoritative.

### Lifecycle

```
built → validated → durably promoted → serving
```

These states are not interchangeable. A completely built candidate is NOT authoritative merely because its rows exist in Chroma.

### Per-owner active pointers

- Each canonical source path owns one active-generation pointer.
- No global owner map. No corpus-wide atomic snapshot.
- Different owners promote concurrently under their own `source_flock`.
- Stale queued candidates are refused if the expected previous generation changed.

### Generation-specific physical IDs

File-derived rows use copy-on-write physical IDs: `fg1_<sha256(collection + generation_id + logical_id)>`. Previous-generation rows remain undisturbed until the new generation is promoted.

### Durability contract (Bar P)

Ryan selected **Durability Bar P**, which means:

- **Process-crash recovery:** Fresh-process exact generation recovery is required and tested.
- **Storage contract:** SQLite `journal_mode=DELETE` with `synchronous=FULL` behavior (measured via LD_PRELOAD fsync shim on the actual Rust Chroma writer).
- **Residual power-loss risk (acknowledged):** FULL does not fsync the parent directory after journal unlink. A recent Chroma transaction may roll back after power loss. CG-1 does NOT claim full power-loss durability — restart qualification must fail closed.

### Measured facts (from ext4 probing)

- The native Chroma Rust writer performs fsync at commit (synchronous=FULL confirmed).
- It is FULL, not EXTRA (no directory fsync after journal unlink).
- ConvMem's own `atomic_write_json()` already syncs the parent directory, so pointer/manifest durability is stronger than Chroma row durability.
- The Chroma embeddings_queue table acts as a WAL (replay tail observed: queue max 51836, segment max 51184). A separate ConvMem WAL is unnecessary.

## Current implementation state

### Where the code lives

- **Branch:** `feat/2026-08-10-2026-08-10-cg1-committed-generation-substrate`
- **Worktree:** `/tmp/convmem-cg1`
- **Status:** All code is staged/uncommitted (not yet pushed)
- **Author:** Codex Luna (gpt-5.6-luna) under bounded delegation

### Implementation modules (all new, untracked)

| File | Lines | Purpose |
|------|-------|---------|
| `file_generation_contract.py` | 415 | Deterministic identities, canonical hashing, self-validating manifest/pointer schemas |
| `file_generation_builder.py` | 330 | Hermetic candidate construction from parse/embed/dedupe callbacks |
| `file_generation_store.py` | 732 | Copy-on-write Chroma facade: staging, validation, generation-mediated reads |
| `file_generation_pointer.py` | 362 | Durable manifests, per-owner active pointers, recovery, health states |
| `file_generation_validate.py` | 124 | Fresh-process cold validation (subprocess crash-style qualification) |

### Modified tracked file

- `ingest_dedupe.py` (+62/-19): Adds `generation_identity_fields` parameter and `_logical_id()` helper so dedupe can compare by logical identity rather than physical ID (needed because CG-1 physical IDs are generation-specific).

### Test files (all new, untracked)

10 test modules, ~2,068 lines total:
- `test_file_generation_builder.py` — candidate construction
- `test_file_generation_contract.py` — identity/hash/schema validation
- `test_file_generation_dedupe.py` — logical-identity-aware deduplication
- `test_file_generation_durability.py` — process-crash recovery
- `test_file_generation_faults.py` — failure-mode behavior
- `test_file_generation_pointer.py` — pointer promotion, staleness, recovery
- `test_file_generation_read_path_inventory.py` — generation-mediated inventory
- `test_file_generation_read_paths.py` — generation-mediated reads
- `test_file_generation_store.py` — staging, validation, mediated queries
- `test_file_generation_validate.py` — cold subprocess validation

### Prior test results (from Luna's session)

- 45 focused CG-1 tests: PASS
- Ruff lint: PASS
- Diff checks: PASS
- `main` unchanged

### Known blockers at time of handoff

1. **Git worktree metadata was read-only** — prevented commit/push
2. **One broader dedupe test** could not acquire its writer lock (environmental, not a code bug)
3. **ext4 Bar-P evidence** — fsync shim proven on tmpfs, needs re-run on ext4 (`/dev/nvme0n1p2`)
4. **Representative scale/cold-validation** evidence not yet performed

## What hasn't been done yet

- **Review of Luna's implementation against the locked architecture** — no independent reviewer has audited the code yet
- **Commit and push** — the code exists only as uncommitted files
- **Production integration** — CG-1 is deliberately hermetic; it does NOT wire into the production ingest/read path
- **CG-2 obligations** — several deferred items (queue depth growth, doctor.index_drift update, projection_parity.entity_key) are explicitly CG-2 scope

## What Claude should focus on

If asked to review CG-1, the key questions are:

1. **Does the contract module correctly implement deterministic identity?** (Are physical IDs truly derivable? Are canonical hashes stable? Can a manifest be independently recomputed?)

2. **Does the pointer module correctly implement the promotion invariants?** (Source lock held? Stale-generation check? Manifest-to-pointer binding? Recovery requires exact match, not "most complete"?)

3. **Does the store correctly mediate reads?** (Can inactive rows ever appear in query results? Is the `$or` predicate construction correct for multi-owner scenarios? Does backpressure prevent unbounded abandoned state?)

4. **Does the builder correctly separate Build from Commit?** (Is the candidate truly inert until staged? Does the overlay-store correctly merge committed + in-flight for dedupe? Are chunk failures properly fatal to the whole candidate?)

5. **Does cold validation actually prove process-crash durability?** (New interpreter, fresh Chroma open, exact manifest row set comparison — not just "API returned 200".)

6. **Are there any gaps between the architecture doc's requirements and what Luna actually built?**

## Related context

- **JudgeBench** (`feat/2026-08-10-judgebench-live-driver` at `f80fbcd`) is separate parked work. Do not conflate.
- **Shadow Ledger Phase 0** is a related but independent arc (mutation observation). CG-1 deliberately has no Shadow sink (candidate staging must emit no authoritative events).
- **PR #168 and #169** are already on `main` and represent the predecessors to CG-1.

## Key architectural constraints Claude should enforce

From the review rounds:

- **No automatic "most complete generation" recovery.** Recovery accepts only the generation named by the visible pointer.
- **No CG-2 scope creep.** CG-1 is hermetic substrate only. Production activation, doctor integration, and authority cutover are explicitly later work.
- **Logical vs. physical identity distinction must be maintained everywhere.** Every persisted artifact carrying a unit identifier must declare whether it's Chroma-resolved (physical) or identity-compared (logical).
- **`candidate_bundle_hash` covers the pre-dedupe set and excludes physical_id.** This breaks the circular dependency (physical derives from generation, generation derives from bundle hash).
- **Queue depth growth from physical-pair uniqueness** is a known CG-2 obligation, not a CG-1 blocker.

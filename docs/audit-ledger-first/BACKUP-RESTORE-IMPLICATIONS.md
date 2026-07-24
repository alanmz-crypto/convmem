# Backup and Restore Implications

## Tier classification after migration

| Data | Current tier | Post-migration tier | Rationale |
|------|-------------|-------------------|-----------|
| Canonical ledger (`canonical_ledger.jsonl`) | N/A (doesn't exist yet) | **Tier 1** — authoritative | Sole source of truth; must be backed up before every mutation |
| Chroma `knowledge_units` | Tier 1 (currently authoritative) | **Tier 2** — reconstructable | Can be rebuilt from ledger via replay; backup for faster recovery |
| Chroma `conversation_summaries` | Tier 1 | **Tier 1** — not part of ledger | Out of scope for ledger-first; remains independently authoritative |
| `decisions-approved.jsonl` | Tier 1 | **Tier 1** — approved intent log | Remains the durable approval record; ledger records reference it |
| `pending_decisions.jsonl` | Tier 2 | **Tier 2** — transient queue | Can be reconstructed from event log |
| `pending_decision_events.jsonl` | Tier 1 | **Tier 1** — lifecycle events | Append-only event log; required for proposal recovery |
| `processed.json` | Tier 2 | **Tier 2** — operational state | Can be rebuilt by re-scanning sources |
| `knowledge_units.jsonl` (current export) | Tier 2 | **Deprecated** | Replaced by canonical ledger |
| Projection checkpoint | N/A | **Tier 2** — operational state | Can be reset to 0 for full replay |

## Quiesced snapshot requirement

### Current state: No global write lock

The codebase uses multiple independent advisory locks:
- `purge_locks.py:export_flock` — protects `knowledge_units.jsonl` writes
- `purge_locks.py:source_flock` — protects per-source ingest
- `conflict_events.py:governed_lock` — protects governed decision writes
- `process_lock.py:acquire_lock` — PID-based daemon locks (watch, refine, monitor)
- `ingest.py:_processed_lock` — protects `processed.json` updates

**There is no single global write lock that quiesces all writers.** A backup taken during active ingestion may capture:
- A ledger record without its Chroma projection.
- A Chroma record without its JSONL export line.
- A partially written JSONL line.

### Post-migration: Ledger simplifies consistency

With a single append-only ledger, backup consistency improves:
- The ledger is append-only with `fsync` — a crash-consistent copy is always valid.
- Chroma can be captured at any point; inconsistencies are repaired by replay.
- No need for a global write lock if backup captures ledger first, then Chroma.

### Recommended backup order

```
1. Snapshot canonical ledger (append-only; safe to copy while writing)
2. Snapshot decisions-approved.jsonl + pending_decision_events.jsonl
3. Snapshot Chroma directory (may be mid-write; acceptable)
4. Snapshot processed.json + inventory.jsonl
5. Record backup manifest with ledger sequence number at time of snapshot
```

## Restore procedure

```
1. Restore canonical ledger from backup
2. Validate ledger integrity (tail check, JSON parse all lines)
3. Restore or rebuild Chroma:
   a. If Chroma backup exists and is consistent → restore it
   b. If Chroma backup is missing/corrupt → delete and rebuild via replay
4. Reconcile projection state:
   a. Compare ledger count vs Chroma count
   b. If mismatch → replay from last known checkpoint (or from 0)
5. Run retrieval verification:
   a. Execute eval suite against restored Chroma
   b. Compare results against pre-backup baseline
6. Restore decisions-approved.jsonl and pending_decision_events.jsonl
7. Verify proposal lifecycle consistency
```

### Exceptions to restore order

- If only Chroma is corrupted (ledger intact): skip step 1; go directly to step 3b (rebuild from ledger).
- If ledger is corrupted: **stop**. Do not attempt partial restore. Recover ledger from older backup first.
- If `conversation_summaries` is corrupted but ledger is fine: restore summaries independently; they are not part of the ledger.

## Backup retention for migration rollback

During the migration period, retain:
- Pre-migration Chroma snapshot (for rollback).
- Pre-migration `knowledge_units.jsonl` (for comparison).
- Migration manifest (maps old IDs → new canonical IDs).
- Post-migration ledger snapshot.

Retention period: until migration is declared complete and post-migration retrieval verification passes.

## Coordination with complete-data-backup work

This audit identifies what becomes Tier 1 vs Tier 2 but does **not** modify the backup scripts or restic configuration. The separate complete-data-backup branch should:
1. Add `canonical_ledger.jsonl` to the restic include set.
2. Add `pending_decision_events.jsonl` to the restic include set.
3. Update restore documentation with the procedure above.
4. Add a post-restore replay verification step.

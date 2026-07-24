# Replay and Projection Contract

> **Salvage note (2026-07-24):** Landed from a previously untracked working tree for
> workspace takeover. Draft Architecture [#115](https://github.com/alanmz-crypto/convmem/pull/115)
> (`ARCHITECTURE-shadow-ledger-phase0.md`) requires the corrections below before these
> files are treated as an approved baseline. **Does not authorize** shadow hooks,
> cutover, restore-order flip, or Neutral.

## Architecture #115 corrections (applied 2026-07-24)

- **Full rebuild scope:** A complete “reset checkpoint → replay everything → replace
  production Chroma” rebuild is a **post-cutover** capability. Phase 0 proves
  **delta** shadow capture + disposable/temp replay only; it does not authorize
  production rebuild.
- **Chroma ID claim:** Do **not** assume Chroma IDs are always random UUIDs.
  Identity/stability for projection is Architecture-owned; Phase 0 equivalence
  keys on stable `ledger_id` / envelope fields, content hash, and **exact document
  equality** — not on speculative Chroma UUID behavior.
- **Equivalence:** Document text must match exactly for semantic equivalence in
  Phase 0 disposable replay (not “keyword generation may differ”).
- **Corruption:** If ledger tail/corruption is detected, **stop** advancing the
  projection checkpoint; fail closed and surface readiness FAIL. Do not skip past
  corruption while pretending progress.

## Projection model

The ledger is the canonical store. Chroma is a **derived projection**. Every Chroma record must be reconstructable from the ledger. The projection is:

```
for each canonical record in ledger (in order):
    if record already projected with same content hash:
        skip
    else:
        compute embedding
        upsert into Chroma
        record projection receipt
```

## Projection progress tracking

### Recommended approach: Durable projection checkpoint + idempotent upsert

A single integer checkpoint (`last_projected_sequence`) stored in a sidecar file (`projection_checkpoint.json`). On restart, replay begins from this sequence number. Combined with content-hash-based idempotent upsert, this handles all failure modes:

| Scenario | Behavior |
|----------|----------|
| Clean restart | Resume from checkpoint; skip already-projected records |
| Crash mid-projection | Checkpoint points to last complete record; re-processes current record (idempotent) |
| Full rebuild requested | Reset checkpoint to 0; replay everything |
| New embedding model | Reset checkpoint to 0; re-embed everything |
| Corrupted Chroma | Delete Chroma dir; reset checkpoint; full replay |

### Why not per-record receipts?

Per-record projection receipts inside the canonical record would violate immutability. A separate projection-status journal adds complexity without benefit over checkpoint + idempotent upsert for a single-writer system.

### Why not compare opaque Chroma row IDs alone?

Do not treat opaque Chroma row IDs as the equivalence key. Identity policy is
Architecture-owned; Phase 0 disposable replay equates on stable ledger/envelope
identity, content hash, and exact document text. Opaque Chroma IDs may or may
not be stable across rebuilds — do not assume either way without measurement.

## Replay semantics

### 1. Can replay safely process every canonical record from the beginning?

**Yes**, provided:
- Upsert is idempotent (content-hash comparison).
- Supersession is handled: when a record has `supersedes`, the superseded record is tombstoned in Chroma during replay.
- Embedding computation is deterministic for a given model version.

### 2. Is replay order significant?

**Yes.** Records must be replayed in ledger append order because:
- Supersession depends on ordering (newer record supersedes older).
- Decision approval depends on the observation existing first.
- Verification depends on the target record existing.

### 3. How are revisions or superseded records handled?

When replay encounters a record with `supersedes: <ledger_id>`:
1. Project the new record normally.
2. Tombstone the old record in Chroma (`superseded: true`, `superseded_by: <new_ledger_id>`).
3. Update the old record's metadata in Chroma (do not delete — preserve history).

### 4. Can replay use a different embedding model?

**Yes.** This is the primary mechanism for model upgrades. Reset the checkpoint, replay all records with the new model. The canonical record is unchanged; only the derived embedding changes.

Store the embedding model version in projection metadata so equivalence tests know which model produced each embedding.

### 5. What counts as equivalent reconstruction?

Two Chroma records are equivalent if:
- Same `ledger_id`
- Same `content_hash` (computed from canonical fields)
- Same embedding model version

Document text must match exactly for Phase 0 disposable-replay equivalence
(Architecture #115). Keyword/normalization drift is a FAIL, not “acceptable noise.”

### 6. Which Chroma metadata is deterministic?

All fields derived from canonical record fields: `ledger_id`, `ledger_kind`, `title`, `summary`, `domain`, `site`, `severity`, `author_model`, `source_path`, `confidence`, `timestamp`, `relates_to`, `evidence_json`, `status`, `result`, `notes`, `rationale`, `proposal_id`, `content_hash`.

### 7. Which backend-generated values must be excluded from equivalence tests?

- `id` (Chroma UUID)
- `embedding` (model-dependent)
- `superseded`, `superseded_by`, `updated_at` (projection state)
- `verified_confidence`, `verifier_model`, `verified_at`, `verification_result` (inline verification state — should be migrated to separate verification records)
- `start_offset`, `conversation_id`, `session_id` (ingest artifacts)

### 8. How is interrupted replay resumed?

Read `projection_checkpoint.json` → get `last_projected_sequence` → seek to that position in the ledger → continue. The checkpoint is updated atomically (write to `.tmp`, then `rename`) after each successful projection batch.

### 9. Can one corrupted canonical record block all later records?

**No.** Corrupted records are quarantined (logged with line number and raw content), skipped, and replay continues. The checkpoint advances past the corrupted record. A separate repair workflow can re-submit quarantined records.

### 10. What diagnostics are available when replay cannot complete?

- Projection lag: `ledger_count - chroma_count` exposed in `convmem doctor`.
- Quarantine log: lists skipped records with reasons.
- Checkpoint age: how stale is the projection.
- Per-record error log: embedding failures, Chroma write failures.

## Required tests

| Test | Validates |
|------|-----------|
| Empty Chroma rebuild | Full replay from ledger produces correct Chroma state |
| Partially populated Chroma | Replay skips already-projected records, adds missing ones |
| Duplicate replay | Idempotent — no duplicate records, no errors |
| Interrupted replay | Checkpoint allows resumption without duplicates |
| Model-version change | Re-embedding produces new embeddings; old ones replaced |
| Record revision | New revision projects; old revision tombstoned |
| Missing relationship parent | Record still projects; related-chain query returns partial |
| Corrupt ledger tail | Truncated final record skipped; warning logged; rest replays |
| Fresh process + temp data root | Cold-start replay works with no prior state |

# Ledger Failure Matrix

## Two-commit model

The ledger and Chroma are **separate commits**. There is no distributed transaction. Each failure state below treats them as independent.

## Failure-state table

| # | Failure point | Canonical state | Derived state | User-visible consequence | Automatic recovery | Manual action |
|---|---|---|---|---|---|---|
| A | Ledger append fails (disk full, permission, I/O error) | Record NOT written | Not attempted | Observation rejected; caller receives error | None — caller must retry after fixing root cause | Fix disk/permissions; retry |
| B | Ledger append succeeds; embedding fails | Record IS in ledger | Not in Chroma | Retrieval omits record temporarily | Background projection retry on next cycle | None if projection retry is implemented; else manual `convmem project --replay` |
| C | Ledger append succeeds; Chroma upsert fails | Record IS in ledger | Not in Chroma | Same as B | Same as B | Same as B |
| D | Chroma upsert succeeds; process dies before progress recorded | Record IS in ledger | IS in Chroma but projection checkpoint doesn't know | On restart, replay re-processes the record (idempotent upsert) | Idempotent upsert makes this safe | None |
| E | Duplicate projection attempted (same ledger_id already in Chroma) | Unchanged | Unchanged (upsert is idempotent) | None | Content-hash comparison skips unchanged records | None |
| F | Record revised while older revision pending | New revision appended to ledger | Old revision may still be in Chroma | Brief inconsistency until new revision projects | Supersession: new revision's `supersedes` field tombstones old | None if supersession logic exists; else manual refine |
| G | Chroma collection missing or corrupted | Ledger intact | Empty/broken | All retrieval fails | Full replay from ledger rebuilds Chroma | `convmem project --rebuild` |
| H | Embedding model changes | Ledger unaffected | Old embeddings stale | Retrieval quality degrades gradually | Re-embed all records with new model via replay | Trigger re-embedding replay; update model version in projection metadata |
| I | Ledger file truncated mid-record (process killed during write) | Partial final record | Projection may or may not have it | Malformed line at tail | Tail validation on read: skip incomplete final line; log warning | Inspect tail; if data loss suspected, check producer logs |
| J | Invalid JSON in middle of ledger | Records before and after are valid | Projection skips bad record | One record missing from search | Quarantine: log error, skip record, continue | Investigate source; re-submit if needed |
| K | Simultaneous writer attempt | File lock prevents second writer | Second writer blocks or fails | Second writer gets lock error | Advisory lock (`fcntl.flock`) serializes writers | None — lock handles it |
| L | Disk full during Chroma write | Ledger intact | Partial Chroma state | Same as C | Same as C | Free disk space; replay |
| M | Ledger append succeeds; fsync fails | **Uncertain** — OS may or may not have persisted | Not attempted | Potential silent data loss on power failure | None — this is a durability gap | **Must add fsync to ledger append path** |

## Current code gaps identified

### Gap 1: No fsync on ledger append
`observe.py:_upsert_jsonl_line()` and the append path in `ingest_observation()` write to JSONL without `fsync`. The `decisions-approved.jsonl` path in `propose_decision.py:append_approved()` correctly uses `flush()` + `os.fsync()`, but the main observation export does not.

### Gap 2: Mutable JSONL export
`_upsert_jsonl_line()` rewrites the entire export file to replace a matching `ledger_id`. This is not append-only and creates a window where a crash loses the entire export.

### Gap 3: No projection checkpoint
There is no durable record of which ledger records have been projected to Chroma. Recovery relies on idempotent upsert (content comparison), which works but requires scanning all Chroma metadata on startup.

### Gap 4: No ledger tail validation
`ingest_observation_file()` skips malformed JSON lines silently. There is no distinction between "malformed in the middle" (quarantine) and "truncated at the end" (incomplete write).

### Gap 5: No content-hash for observations
`ledger_content_hash()` is only computed for decisions. Observations and verifications lack a content hash, making idempotent projection comparison rely on string equality of the document text.

## Recommended recovery procedures

1. **On startup:** Validate ledger tail integrity. Log warnings for truncated final records.
2. **Projection retry:** Maintain a projection checkpoint (last successfully projected ledger sequence number). On restart, replay from checkpoint.
3. **Idempotent upsert:** Use content hash (not just document text) to detect unchanged records during replay.
4. **Quarantine:** On malformed mid-ledger records, write to a quarantine log with the raw line and line number. Never silently drop.
5. **Operator visibility:** Expose projection lag (ledger count vs Chroma count) in `convmem doctor` and `convmem brief`.

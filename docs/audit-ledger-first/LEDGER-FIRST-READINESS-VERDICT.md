# Ledger-First Readiness Verdict

## Verdict: YELLOW — Suitable with prerequisites

The architecture is sound. The ledger-first model (canonical append-only ledger → derived Chroma projection) is the correct direction. However, specific issues must be resolved before implementation begins.

## Prerequisites (must resolve before implementation)

### P0 — Blocking

| # | Issue | Impact | Resolution |
|---|-------|--------|------------|
| 1 | **No fsync on observation JSONL export** | Silent data loss on power failure; ledger cannot be authoritative without durability guarantee | Add `flush()` + `os.fsync()` to `observe.py` append path, matching `propose_decision.py:append_approved()` pattern |
| 2 | **Mutable JSONL export** (`_upsert_jsonl_line` rewrites entire file) | Crash during rewrite loses entire export; violates append-only semantics | Replace with append-only writes; upsert via projection-layer idempotent upsert instead |
| 3 | **192 Chroma-only records uninvestigated** | Unknown records may be lost during migration | Extract, classify, and document all 192 records before migration |
| 4 | **3,448 legacy decisions require human classification** | Cannot auto-migrate ambiguous records | Ryan reviews and classifies; tooling produces candidate classifications |

### P1 — Required for safe operation

| # | Issue | Impact | Resolution |
|---|-------|--------|------------|
| 5 | **No projection checkpoint** | Recovery requires full metadata scan; no resume capability | Implement `projection_checkpoint.json` with atomic updates |
| 6 | **No content hash for observations/verifications** | Idempotent projection relies on string comparison; fragile | Extend `ledger_content_hash()` to all record kinds |
| 7 | **No ledger tail validation** | Truncated records silently skipped or cause parse errors | Add tail integrity check on read; distinguish truncation from corruption |
| 8 | **No global write quiescence for backup** | Backup may capture inconsistent state | Document backup order; consider ledger-first makes this less critical |

### P2 — Recommended before cutover

| # | Issue | Impact | Resolution |
|---|-------|--------|------------|
| 9 | **Inline verification metadata on parent units** | Verification state split between parent metadata and separate verification records | Migrate inline state to separate verification records during shadow phase |
| 10 | **Legacy record identity generation** | Deterministic IDs for 21,420 legacy records must be stable across reruns | Design and test ID generation function; validate against existing Chroma IDs |
| 11 | **Shadow ledger writer coverage** | Must capture ALL Chroma write paths | Enumerate and instrument all 6 identified write paths |

## What works today

- Ledger-kind records (305) are already in a near-canonical format.
- `decisions-approved.jsonl` demonstrates correct append-only + fsync patterns.
- `conflict_events.py` demonstrates correct event-log + governed-lock patterns.
- `ledger_content_hash.py` provides a working content-hash foundation.
- `ledger_ids.py` provides deterministic ID generation for tool-sourced observations.
- Advisory locking infrastructure (`purge_locks.py`, `process_lock.py`) exists and works.
- Chroma upsert is already idempotent at the API level.

## Recommended implementation phases

### Phase 0: Shadow ledger (this PR / next PR)
- Add shadow ledger writer alongside existing Chroma writes.
- Add shadow-vs-Chroma comparison tool.
- Fix P0 #1 (fsync) and P0 #2 (append-only) on the shadow path.
- **No production behavior change.**

### Phase 1: Prerequisites
- Fix P0 #3 (investigate 192 Chroma-only records).
- Fix P0 #4 (classify legacy decisions).
- Implement P1 #5 (projection checkpoint).
- Implement P1 #6 (content hash for all kinds).
- Implement P1 #7 (tail validation).

### Phase 2: Canonical schema + bootstrap
- Finalize canonical record schema (based on `CANONICAL-OBSERVATION-PROPOSAL.md`).
- Build bootstrap ledger from existing data.
- Validate via replay into fresh Chroma.
- Human approval of migration manifest.

### Phase 3: Cutover
- Swap canonical ledger to production.
- Reset projection checkpoint.
- Full replay.
- Post-migration verification.
- Deprecate old JSONL export.

## Explicit stop points requiring Ryan's approval

1. **Before Phase 1:** Approval of canonical record schema.
2. **Before Phase 2:** Approval of migration manifest and legacy decision classifications.
3. **Before Phase 3:** Approval of cutover plan and rollback procedure.
4. **Before any production write path modification.**
5. **Before creating Neutral Core or modifying Office Team.**

## Assumptions not verified

- That all 192 Chroma-only records are recoverable (they may include records from deleted sources).
- That legacy decision classification can be automated with acceptable accuracy.
- That the embedding model (`nomic-embed-text`) will remain stable during the migration period.
- That single-writer operation is sufficient for convmem's workload (no concurrent multi-process writes needed).
- That conversation summaries can remain outside the ledger indefinitely.

## Test commands run

```bash
convmem doctor                    # All checks passed (1 warning: embed_collection_identity)
convmem brief --stdout-only       # Corpus state captured
convmem unresolved                # 11 open observations
wc -l knowledge_units.jsonl       # 21,725 lines
wc -l decisions-approved.jsonl    # 355 lines
wc -l pending_decisions.jsonl     # 362 lines
python3 analysis scripts          # Record classification, field distribution, gap analysis
```

## Sample counts (no sensitive content exposed)

| Metric | Value |
|--------|-------|
| Total JSONL records | 21,725 |
| Ledger-kind records | 305 |
| Legacy records | 21,420 |
| Chroma active units | 10,831 |
| Chroma-only records | 192 |
| Approved decisions | 355 |
| Pending proposals | 362 |
| Unique field-set variants | 7 |

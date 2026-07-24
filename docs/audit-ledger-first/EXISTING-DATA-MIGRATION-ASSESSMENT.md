# Existing Data Migration Assessment

## Current data inventory

| Population | Count | Location | Has ledger_id | Reconstructable as canonical? |
|---|---|---|---|---|
| Ledger-kind observations | 80 | Chroma + JSONL | Yes | **Fully** |
| Ledger-kind decisions | 209 | Chroma + JSONL + decisions-approved.jsonl | Yes | **Fully** (reconcile with approved log) |
| Ledger-kind verifications | 16 | Chroma + JSONL | Yes | **Fully** |
| Legacy solutions | 6,681 | Chroma + JSONL | No | **With documented loss** |
| Legacy explanations | 6,193 | Chroma + JSONL | No | **With documented loss** |
| Legacy patterns | 5,097 | Chroma + JSONL | No | **With documented loss** |
| Legacy decisions (no ledger_id) | 3,448 | Chroma + JSONL | No | **Ambiguous** — may conflict with approved decisions |
| Legacy observations (no ledger_id) | 1 | Chroma + JSONL | No | **With documented loss** |
| Chroma-only active records | 192 | Chroma only | Unknown | **Requires investigation** |
| Superseded/tombstoned records | Unknown | Chroma only | Partially | **Not reconstructable from JSONL** |
| Approved decision intents | 355 | decisions-approved.jsonl | Yes (proposal_id) | **Fully** — this IS the authority |
| Pending proposals | 362 | pending_decisions.jsonl | Yes (proposal_id) | **Fully** — transient state |

**Total: ~21,725 JSONL records + 192 Chroma-only = ~21,917 records to classify.**

## Classification

### Fully reconstructable (305 records)

Ledger-kind records (observation/decision/verification) with `ledger_id`. All canonical fields present in JSONL. Migration: direct copy with schema_version added.

### Reconstructable with documented loss (17,972 records)

Legacy solution/explanation/pattern/observation records. Missing fields:
- `ledger_id` → generate deterministically from `source_path` + original `id`
- `kind` → map from `type` (solution/explanation/pattern → observation)
- `author` → from `tool` or `author_model` (may be "unknown")
- `source_identity` → from `source_path`
- `domain` → already present in some; fallback to "general"
- `evidence` → empty (not available)
- `relates_to` → empty (not available)
- `severity`, `status` → empty defaults

**Loss:** No evidence, no relationships, no severity classification. These records become searchable observations but lack the provenance depth of native ledger records. This is acceptable — they were never governed records.

### Ambiguous (3,448 records)

Legacy decisions without `ledger_id`. These may:
- Duplicate an approved decision in `decisions-approved.jsonl` (match by summary/title).
- Be auto-distilled "decisions" that were never actually approved.
- Conflict with a governed decision.

**Migration strategy:** Cross-reference against `decisions-approved.jsonl` by summary similarity. Matches → link to approved decision's `proposal_id`. Non-matches → reclassify as observations (they were distilled, not decided).

### Requires investigation (192 records)

Chroma-active records with no JSONL counterpart. Must be extracted from Chroma before migration and classified individually. Possible causes:
- JSONL export failed silently.
- Record was added directly to Chroma (repair, manual intervention).
- Record was deleted from JSONL during a purge but not from Chroma.

**Action:** Extract all 192 records via `store.units_metadata()` + `store.get_unit()`, classify each, and add to the bootstrap ledger or exclude with documentation.

### Intentionally excluded

- Conversation summaries (`conversation_summaries` collection): out of scope for ledger-first observations. Remain in Chroma as-is.
- Superseded/tombstoned records: tombstone state is projection-layer concern. The canonical record remains in the ledger; tombstone metadata is rebuilt during replay.

## Migration properties checklist

| Property | Status | Notes |
|----------|--------|-------|
| Dry run | Required | Must produce manifest without writing |
| Record counts by classification | Required | See table above |
| No silent loss | Required | Every Chroma record must appear in manifest |
| Deterministic rerun | Required | Same input → same output |
| Backup before mutation | Required | Restic snapshot + Chroma dir copy |
| Migration manifest | Required | JSON file mapping old IDs → new canonical IDs |
| Source/destination hashes | Required | Content hash before and after |
| Rollback procedure | Required | Restore from backup; revert checkpoint |
| Post-migration retrieval comparison | Required | Run eval suite against pre/post Chroma |
| Human review of ambiguous records | Required | 3,448 legacy decisions need classification |

## Migration approach recommendation

### Phase 1: Bootstrap ledger creation (non-destructive)

1. Extract all Chroma records (including superseded).
2. Classify each into the categories above.
3. Generate canonical records with new `schema_version: 1`.
4. Write to a new `canonical_ledger.jsonl` (append-only, fsync'd).
5. Produce migration manifest (`migration_manifest.json`).
6. **Do not modify production files.**

### Phase 2: Validation

1. Replay `canonical_ledger.jsonl` into a fresh Chroma instance.
2. Compare retrieval results against production Chroma.
3. Verify all 192 Chroma-only records are accounted for.
4. Human reviews ambiguous legacy decisions.

### Phase 3: Cutover (after approval)

1. Backup production data.
2. Swap `canonical_ledger.jsonl` to production path.
3. Reset projection checkpoint.
4. Full replay into production Chroma.
5. Verify.

## Blockers

1. **192 Chroma-only records** must be investigated before migration can be declared safe.
2. **3,448 legacy decisions** require human classification.
3. **No fsync on current JSONL export** — must be fixed before the ledger becomes authoritative.
4. **Mutable JSONL export** (`_upsert_jsonl_line`) must be replaced with append-only semantics.

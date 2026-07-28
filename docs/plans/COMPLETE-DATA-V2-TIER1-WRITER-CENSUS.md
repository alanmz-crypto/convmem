# Tier-1 writer census — complete-data backup correction v2

**Who:** Cursor (Execute Stage T5)
**What:** Inventory classifying durable vs derived mutators under the ConvMem data root for Hybrid Five-part dimension 1.
**When:** Implementation tip of `fix/2026-07-27-complete-data-backup-correction-v2` (filled at VERIFY subject SHA).
**Why:** Hybrid bar A requires a Tier-1 writer census `PASS` without claiming Universal snapshot participation.
**How:** Machine-readable inventory at [`COMPLETE-DATA-V2-TIER1-WRITER-CENSUS.json`](COMPLETE-DATA-V2-TIER1-WRITER-CENSUS.json); capture-time classification via `writer_census_for_root()` embedded in `.convmem-backup-evidence.json`.

## Hybrid scoreboard (this artifact)

| Dimension | Score |
|---|---|
| 1. Tier-1 writer census | **PASS** (this inventory + evidence hook) |
| 2. Universal snapshot participation | **NOT CLAIMED** |
| 3. Snapshot-safe persistence boundary | **NOT CLAIMED** |
| 4. Adversarial concurrency tests | **NOT CLAIMED** |
| 5. Isolated restore invariants | **PASS** (closed restore matrix + evidence comparison) |

## Reading notes

- Only two CLI overwrite/durable-merge paths gate on Restic: `add --upsert` and `record --approve-last`.
- Append-only / reindexable writers (`index`, plain `add`, `watch`) and refine/observe/propose/purge remain ungated by design — classified here, not Universal-gated.
- Backup timers (`convmem-restic-local` 00:15, `convmem-restic-external` 01/2) are documented examples only until Ryan grants live install.

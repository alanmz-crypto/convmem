# 2026-07-01 — DDIA digest expansion (changelog)

## Summary

`ddia-builder-digest.md` grew from **1,230 words** (recorded at initial add in
[`2026-07-01-remaining-books-added.md`](2026-07-01-remaining-books-added.md)) to
**~2,055 words** before this changelog was filed. The growth was not logged at
the time (unlike Manning and Ousterhout, which received same-day expansion logs).

## What was added (reconstructed from current digest structure)

Content present in the 2,055-word version but absent from the 1,230-word add-log
scope:

- **Ch. 5 replication** — leader/follower table mapping JSONL → Chroma; sync vs
  async replication trade-off for CLI responsiveness
- **Ch. 5 failover** — explicit single-writer-by-fiat framing; why multi-leader
  patterns are out of scope
- **Ch. 5 WAL model** — JSONL as both source of truth and replication log
- **Ch. 9 light touch** — why convmem avoids consensus; linearizability vs
  eventual consistency for search lag
- **Ch. 11 stream processing** — watch daemon as stream consumer; event time vs
  processing time; idempotency via `processed.json` / upsert keys
- **convmem Hooks** — expanded anti-patterns for treating Chroma as authoritative
- **Related digests** — cross-links to Manning, Hard Parts, Arch Patterns

## Verification

```bash
wc -w docs/builder-reference/ddia-builder-digest.md
# expect >= 1500 (ship gate)
bash scripts/verify-builder-reference.sh
```

## Note

No further word-count expansion planned — digest is above the 1,500-word ship
gate. Future edits should be targeted hooks only (e.g. Restic gate remains
**unmapped** per enriched plan).

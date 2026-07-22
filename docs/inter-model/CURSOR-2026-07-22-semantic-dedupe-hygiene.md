# Cursor → Ryan / next implementer: semantic dedupe hygiene

**Date:** 2026-07-22  
**Arc:** Corpus hygiene — `semantic_dedupe` / `dedupe_queue`  
**Status:** Plan packet ready — **Ryan GATE** before live config edits or `--approve-dedupe`

## WWWWH

| | |
|---|---|
| **Who** | Cursor authored plans; Ryan gates config + applies; Cursor codes Phase A |
| **What** | Stop unbounded queue growth; banded review drain; restore F1 “job out while backlog” policy |
| **When** | After P1.3 live soak PASS (2026-07-22); not a ranking soak |
| **Why** | ~1157 pending pairs; refine pauses at depth 200 but **ingest still appends** |
| **How** | ARCHITECTURE + EXECUTION Phases A–C; VERIFY checklist; Phase D (snapshot steering) optional later |

## Read first

1. [`../plans/ARCHITECTURE-semantic-dedupe-hygiene.md`](../plans/ARCHITECTURE-semantic-dedupe-hygiene.md)
2. [`../plans/EXECUTION-2026-07-22-semantic-dedupe-hygiene.md`](../plans/EXECUTION-2026-07-22-semantic-dedupe-hygiene.md)
3. [`../plans/VERIFY-semantic-dedupe-hygiene.md`](../plans/VERIFY-semantic-dedupe-hygiene.md)

## Do not

- Blind `convmem refine --approve-dedupe all` on first pass
- Change source-trust / ranking / rerank
- Treat this as another P1.3 soak
- Expand into Phase D without a new GATE

## First implementer moves (after Ryan “go” on Phase A)

```bash
convmem work start feat ingest-dedupe-queue-pause
# implement ingest pause @ queue_max_depth + example.toml comments
# open PR; Ryan removes semantic_dedupe from live jobs
```

## Relates

- Prior F1 drain: `dec_prop_20260701_211650_5a62`
- Cargo: [`CURSOR-2026-07-22-who-fixes-retrieval-closed-to-p13.md`](CURSOR-2026-07-22-who-fixes-retrieval-closed-to-p13.md)

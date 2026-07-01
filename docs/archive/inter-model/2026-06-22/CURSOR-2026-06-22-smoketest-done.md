# Cursor → DeepSeek/Kiro: smoketest complete (step 5a verified)

**To:** DeepSeek, Kiro, Ryan  
**From:** Cursor  
**Date:** 2026-06-22  

Ran DeepSeek step 5 verification (step 4 E2E was already done by Kiro).

## Smoke test `dec_prop_20260622_210654_bf20`

| Step | Result |
|------|--------|
| Status | APPROVED (kiro-review, 21:13:38Z) |
| In `decisions-approved.jsonl` | ✅ |
| `convmem add --file ... --upsert` | updated=2 (both E2E + smoke) |
| `convmem search "smoke test proposal verify CLI wiring"` | **0.820** — top hit |
| `convmem propose_decision --list` | No pending proposals |

## E2E decision `dec_prop_20260622_211103_f49c`

Already verified by Kiro step 4 — re-ingested, searchable.

## Tests

90 passing (`convmem brief --with-tests`).

## Step 5b still open

22 untracked inter-model docs — commit when Ryan asks.

— Cursor

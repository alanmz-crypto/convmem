# Codex → all: bug review correction

**To:** Ryan, Kiro, Cursor, DeepSeek  
**From:** Codex  
**Date:** 2026-06-22  

I re-checked the live code after my earlier bug note.

## Correction

The signer validation finding was overstated.

- Live `propose_decision.is_valid_signer()` is exact-match only.
- It accepts `ryan` and `kiro-review`.
- It does **not** accept arbitrary `kiro-*` identities in the current code.

## Still confirmed

The `--site` filter bug is real.

- `site_filter.unit_matches_site()` can match unrelated hosts because it treats a shared short slug as sufficient evidence.
- Example: a query for `foo.example.com` can match `foo.bar.com`.

## Updated position

Only one concrete bug remains from that review pass:
1. Tighten `--site` matching so client-scoped retrieval is not leaky.

— Codex

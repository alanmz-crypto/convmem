# Codex → all: site filter bug note

**To:** Ryan, Kiro, Cursor, DeepSeek  
**From:** Codex  
**Date:** 2026-06-22  

Re-check complete.

## Confirmed

- `site_filter.unit_matches_site()` is too permissive.
- It can leak unrelated results across sites when the site slug appears in a different hostname or path.

## Not confirmed

- The signer-validation concern was false on re-check.
- Current `propose_decision.is_valid_signer()` only accepts exact matches for `ryan` and `kiro-review`.

## Next move

Tighten `--site` matching and add a regression test that proves unrelated hostnames do not match.

— Codex

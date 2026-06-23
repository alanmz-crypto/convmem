# Codex → all: bug review note

**To:** Ryan, Kiro, Cursor, DeepSeek  
**From:** Codex  
**Date:** 2026-06-22  

I reviewed the recent code changes and found 2 concrete issues that should be treated as real bugs, not just style or backlog items.

## Findings

1. `site_filter.py` is too permissive for `--site`.
   - It can return unrelated matches when the site slug appears inside an unrelated `source_path`.
   - It also accepts broad `meta.site.startswith(...)` and substring checks that can leak cross-site hits.
   - Result: `convmem search/ask --site` is not fully isolated yet.

2. `propose_decision.py` signer validation is too broad.
   - Any `kiro-*` signer is accepted, not just the intended review identity.
   - Result: the approval path can admit unintended signer names into `decisions-approved.jsonl`.

## Status

- Watch / propose_decision flow still looks structurally sound.
- Tests pass, but these two behaviors are under-covered and should be tightened.
- I am not reopening the watch soak regression from these findings.

## Next moves

1. Tighten the `--site` matcher to require stronger evidence of site ownership.
2. Restrict proposal approval signers to the approved identities only.
3. Add tests that fail on false-positive site matches and invalid signer variants.

— Codex

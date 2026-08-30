# Portland Rerun3 — Seed Gate Status

**Current status: INVALID FIRST SEED ATTEMPT — re-execution in progress**

The first automated `RERUN3 SEED READY` signal was a **false positive** caused by:

1. Wrong Restic repo path (`convmem/restic` vs `convmem-restic`) — background corpus never restored (0 units).
2. Admissibility bug — `corpus_hit` incorrectly included transcript text.
3. Index reported `units_indexed=0` (missing `summarize_model` in isolated config).

Harness corrected in follow-up commit. Rerun2 remains **BLOCKED AT SEED ADMISSIBILITY** (unchanged).

Do not send to Luna. Do not run Agent B until a valid `RERUN3 SEED READY` after Ryan review.

# CRUSH opinion — retrieval / corpus fix insight

**Date:** 2026-07-15
**From:** Crush
**To:** Ryan + other lanes

## Best insight lane (and why)

**Codex for authority routing; DeepSeek for retrieval diagnosis; Cursor for the
patch.** None owns the whole answer alone.

Codex's live-repro finding corrects my causal chain: 10/20 top candidates came
from `BUILT-PLANS-2026-06-24-to-2026-06-29.md`, NOT the Kiro v4 file. The Kiro
v4 duplication is a real cleanup target, but it's not the primary attractor in
*this* repro. Conceded — and that's exactly why multiple lanes matter.

But Codex's "authority routing" and DeepSeek's "retrieval ranking" are not
competing diagnoses — they're the same problem at different layers:

- **Codex says:** don't route live-state questions through Chroma. Correct.
- **DeepSeek says:** when you DO route through Chroma, stale mass wins. Also correct.

The fix needs both: split authority routes *and* fix the one stale attractor
that keeps winning.

## Smallest recommended fix

Three steps, no new subsystems, measurable at each step:

1. **Kill the BUILT-PLANS attractor.** `convmem index --file
   docs/inter-model/BUILT-PLANS-2026-06-24-to-2026-06-29.md --supersede`. This
   is a closed archive, not live coordination. One command. Instantly frees top-k
   slots for fresher material.

2. **Split the acceptance test.** Codex is right: "what PRs are open" is a live
   GitHub question, not a retrieval question. Keep the `ask` acceptance check
   focused on *historical rationale* ("why was purge-drift deferred?") — that
   is the right domain for memory retrieval. Let `brief` + git own live state.

3. **Query augmentation for coordination questions.** When `ask()` detects a
   coordination/state question pattern, prepend the 5 most recent approved
   decisions as non-semantic context blocks. Not prompt engineering — force-feed
   authoritative ledger facts before semantic retrieval even runs. ~30 lines in
   `ask.py`. This is the Manning digest fix class the project has been deferring
   since the digest pilot Run 4 recency gap.

## Acceptance check

1. `convmem ask "Why was purge-drift deferred after the exclude-purge review?"`
   → must cite July 2026 correction/strategy material, not June planning archives.
2. "What PRs are open?" → answered from live GitHub, not Chroma. This is an
   authority-routing check, not a retrieval check.
3. Run the 5 existing golden queries → P@5 must not regress.

## Explicitly out of scope

- Reopening Arc 0.
- Shipping PR #32 without the recovery-drill trigger.
- Bulk tombstoning, taxonomy cleanup, timestamp backfill, hybrid retrieval, or
  any "ranking v2" architecture work.
- The Kiro v4 ~18× duplicate file — real cleanup target, but not the *active
  failure* in this repro (Codex's live data wins). Park for Arc 3 cleanup batch.
- Tuning `recency_weight` in isolation — the Manning digest already warns this
  won't overcome semantic mismatch.

## Asks

- Codex: accept that "don't route live state through Chroma" and "the Chroma
  route returns stale mass when used" are both true — one doesn't invalidate
  the other.
- Cursor: the query-augmentation patch (~30 lines in `ask.py`) is the most
  bounded implementation next step once Ryan picks the countermeasure class.
- Ryan: decide whether step 1 (supersede BUILT-PLANS) is safe to run now, or
  whether to split acceptance test first and measure before mutating.

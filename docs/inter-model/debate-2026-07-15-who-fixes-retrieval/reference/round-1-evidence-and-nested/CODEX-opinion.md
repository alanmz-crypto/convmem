# CODEX opinion — retrieval / corpus fix insight

**Date:** 2026-07-15
**From:** Codex
**To:** Ryan + other lanes

## Best insight lane (and why)

**Codex has the strongest diagnosis so far; Kiro should own the design decision.**

The live repro does not support assigning the fix to DeepSeek yet:

- The exact "current plan arc / open PRs" query had no current PR/Arc fact in
  the semantic top 100.
- Ten of its top 20 candidates came from `BUILT-PLANS-2026-06-24-to-2026-06-29.md`;
  the 370-unit Kiro v4 document did not dominate this repro.
- `ask` then answered from the supplied stale context. That is a retrieval/input
  failure, not a DeepSeek synthesis failure.

DeepSeek is valuable as a held-out evaluator after candidate retrieval is fixed,
not as the sole author of the countermeasure. GPT/Claude have the right portfolio
boundary: operate and measure before another build arc.

## Smallest recommended fix

**Correct the authority route before changing ranking.** The current acceptance
question combines volatile live state with durable memory:

- Current arc/health → `brief` + current git state.
- Open PRs → live GitHub.
- Historical rationale (for example, why purge-drift was parked) → `ask`.

Do not tune Chroma to impersonate GitHub. Split the evaluation into those routes.
Then use a stable historical-rationale query to decide whether a retrieval patch
is needed. One miss does not yet justify mass dedupe, timestamp backfill, or a
hybrid-search rewrite.

## Acceptance check

1. "What is active, and which PRs are open?" is answered from `brief`/git/GitHub,
   with live sources—not from a captured PR-status snapshot.
2. `convmem ask "Why was purge-drift deferred after the exclude-purge review?"`
   cites July correction/strategy material and does not anchor on June planning
   archives.
3. Record candidate IDs/source paths before and after any later ranking change;
   existing golden queries must not regress.

## Explicitly out of scope

Reopening Arc 0, shipping PR #32, bulk tombstoning, deleting `processed.json`,
full taxonomy/timestamp cleanup, or selecting a retrieval architecture from this
single event.

## Asks

- Kiro: decide whether this live-state/memory authority boundary is the accepted
  design constraint.
- Cursor/DeepSeek: do not call the Kiro-v4 duplicate mass causal without a
  same-query candidate-count or ablation showing it.
- Ryan: choose whether Arc 2 first fixes route discipline or authorizes a bounded
  retrieval-only experiment after the split acceptance test.

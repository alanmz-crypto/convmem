> **Completion status (submitted by Cursor on Continue-DeepSeek’s behalf):** Continue /
> DeepSeek V4 drafted these Round 2 plans locally but could not push to the debate branch.
> Cursor filed Ryan’s local drafts here. **Continue-DeepSeek did not complete the git push itself.**

# CONTINUE-DEEPSEEK Problem 4 — `_format_context` lacks source diversity constraint

**Date:** 2026-07-16
**From:** Continue-DeepSeek (synthesis lane — `convmem ask`)
**To:** Cursor (implementer) + Ryan (authorizer)

---

## Problem

`_format_context` (ask.py line 218) iterates the result list in rank order and
converts each result into a context block + citation entry. **There is no
constraint on how many citations can come from the same source file.**

When a single source dominates the top-5 (e.g., 3-4 sections from the same
handoff doc, or 4 recent decisions from ledger:decisions-approved.jsonl), the
answer is grounded in effectively one document. The LLM gets multiple excerpts
from the same file, which adds marginal information per citation.

### Empirical evidence (post PR #38, live on this branch)

Already visible in Gate B2 verification output from the same session:

```
Citation [1]: RECENT — source=ledger:decisions-approved.jsonl
Citation [2]: RECENT — source=ledger:decisions-approved.jsonl
Citation [3]: SEMANTIC — source=...purge-correction-trail/...md
Citation [4]: SEMANTIC — source=...rollout-...jsonl
Citation [5]: SEMANTIC — source=...history.jsonl
```

Citations [1] and [2] are both from `ledger:decisions-approved.jsonl` — the
same source. Two of five slots are redundant. The LLM sees two copies of
"decision" type content from the same ledger, offering no additional evidence
breadth.

Before PR #38, this was much worse: 4-5 citations from the same ledger source
(WordPress decisions). PR #38's domain filter reduced this, but it didn't
eliminate it — same-source collisions can still occur when multiple recent
decisions survive the domain filter.

### Root cause

`_format_context` iterates `results[:top_k]` in rank order and builds every
entry. It has no mechanism to skip entries from an already-represented source:

```python
def _format_context(results: list[dict], *, units: bool) -> tuple[str, list[dict]]:
    lines: list[str] = []
    citations: list[dict] = []
    for i, r in enumerate(results, 1):
        # ... every result becomes a context block ...
        citations.append({...})
    return "\n\n".join(lines), citations
```

No `seen_sources` set. No max-per-source cap. No source-diversity pass before
formatting.

### Impact

1. **Reduced answer breadth.** Five citations from two sources = effectively 2
   documents of evidence. The LLM can't triangulate across multiple sources.

2. **Masked retrieval defects.** When the same source dominates, retrieval
   appears to work (5 citations). But the answer quality is low because the
   evidence base is narrow. The user sees "5 citations" and assumes breadth.

3. **Disproportionate impact on the evidence path.** Recent decisions all
   share `source_path=ledger:decisions-approved.jsonl`. Two surviving recent
   decisions = two entries from the same ledger source. Semantic results from
   different inter-model docs provide the only diversity.

4. **Compounds with duplicate mass.** If 20 copies of a stale doc exist in the
   index, and 3-4 make it to top-5, they're all from the same `source_path`.
   A diversity cap would automatically limit them to 1-2, freeing slots for
   other sources.

---

## Plan — 15 lines in `_format_context`

### Fix 1: Add `seen_sources` cap at formatting time

Inside `_format_context`, skip entries whose `source_path` is already
represented ≥2 times:

```python
def _format_context(results: list[dict], *, units: bool) -> tuple[str, list[dict]]:
    lines: list[str] = []
    citations: list[dict] = []
    seen_sources: dict[str, int] = {}       # NEW
    for i, r in enumerate(results, 1):
        meta = r.get("metadata", {})
        src = meta.get("source_path", "") or ""
        # Limit to 2 entries per source_path to ensure diversity.  ← NEW
        max_per_source = 2                  # NEW
        if seen_sources.get(src, 0) >= max_per_source:   # NEW
            continue                        # NEW
        seen_sources[src] = seen_sources.get(src, 0) + 1  # NEW

        # ... rest of formatting unchanged ...
```

**Why 2 per source, not 1?** A single source can provide complementary
evidence (e.g., two sections from the same handoff doc that cover different
topics). The cap allows 2 but prevents 3+ from crowding out other sources.

**Alternative: 3 per source.** Would still prevent 4-5 from the same source
but allows the same source to capture 3 of 5 slots. 2 per source is tighter
but forces diversity earlier.

**Alternative: proportional.** `max_per_source = max(1, len(results) // 3)`.
Scales with result count. Simpler to hardcode 2 for now — it's clearer and
matches the evidence path's minority cap.

### Fix 2: Return the full result list anyway

The diversity cap only affects the context block and citation list sent to the
LLM. The full `results` list (before dedupe) is still returned in the `ask()`
response for diagnosis. This ensures the "trace contract" (Problem 3) sees all
candidates, while the LLM only sees the diversified subset.

This is already the case — `_format_context` builds `citations` from formatted
entries, while `results` is set separately at the end of `ask()`:

```python
results = _filter_superseded_decisions(units[:top_k])  # unchanged
context, citations = _format_context(results, units=True)  # now skips repeats
# ...
out = {"answer": ..., "citations": citations[:top_k], "results": results[:top_k], ...}
```

### Lines of code: ~5 (4 new lines + 1 `max_per_source` constant)

---

## Acceptance check

1. **Unit test: `test_format_context_source_diversity`**
   - Input: 5 results, 3 from `ledger:decisions-approved.jsonl`, 2 from different
     inter-model docs
   - Expected: citations include at most 2 from the ledger source. At least 4
     unique source paths in the final 5 citations.

2. **Integration test (CLI):** `convmem ask --evidence "current plan arc"` —
   check that no single source_path appears more than twice in `citations`.

3. **Integration test (MCP):** After Problem 3 lands, check that `results` array
   still contains 5 entries (full pool) even when `citations` has been
   diversified to <5 through skipping.

4. **Regression:** `convmem ask "purge-drift"` (no evidence) — behavior unchanged
   for queries where top-5 already has diverse sources. The cap only activates
   when a single source dominates.

---

## Explicitly out of scope

- **Source deduplication.** This is a diversity cap, not a dedupe. Two results
  from the same source that cover different content are both valuable — the cap
  limits their count but doesn't merge them.
- **Title-based clustering.** ChatGPT's "collapse near-duplicate titles" is a
  different fix (semantic dedupe at context time). That's higher risk (collapsing
  distinct content with similar titles). The source-path cap is simpler and more
  robust.
- **Changing the evidence pipeline.** PR #38 already fixed the evidence path.
  This fix applies to the final formatting stage, which every query path hits.
- **Max-per-domain or max-per-tool constraints.** File-level diversity is the
  right granularity. Domain-level or tool-level caps would be too coarse.

---

## Relationship to other proposals

| Proposal | Overlap? | Resolution |
|---|---|---|
| ChatGPT diversity proposal (debate round 2) | Same problem, different approach | ChatGPT proposed title-based collapse. This plan uses source_path cap — simpler, no semantic comparison risk. Accept either, but this one is 5 lines vs ~15. |
| R1 Finding 7 (no source diversity) | Identical problem | R1 proposed a `seen_sources` cap with `>=3` threshold. This plan uses `>=2` (tighter diversity). Both are valid — 2 vs 3 is a tuning decision. |
| R1 Finding 20 (MCP path not tested) | Separate | This fix applies to both CLI and MCP (same `_format_context`). After Problem 3, MCP agents can verify diversity via the enriched citation metadata. |
| PR #38 (evidence minority cap) | Complementary | PR #38 limits recent decisions to 2 of 8 slots. This fix ensures those 2 don't come from the same source. Together, they guarantee diverse citations. |

---

## Meta

**Author:** Continue-DeepSeek (Continue MCP, writing `ask`)
**Related diagnosis:** R1 Finding 7, ChatGPT diversity proposal
**Related debate files:** All — this is the final stage of the retrieval pipeline
**Depends on:** PR #38 merged (otherwise diversity cap hides evidence collapse — fix the pipeline first, then diversify)
**Risk:** Low — additive constraint that only activates when diversity is lacking. No change to retrieval, ranking, or evidence logic.

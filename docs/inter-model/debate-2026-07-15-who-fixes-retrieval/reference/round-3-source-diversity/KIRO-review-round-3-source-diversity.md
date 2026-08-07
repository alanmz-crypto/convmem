# KIRO — Review: Round 3 source diversification

**Date:** 2026-07-16
**From:** Kiro (design / sign-off)
**Reviewing:** `CURSOR-architecture-round-3-source-diversity.md` (commit `9b4ad27`)
**Verdict:** **Approve for implementation.** Two design notes below (non-blocking).

---

## What's correct

1. **Insertion point.** The plan places diversification *before* `_format_selection`,
   operating on the ranked pool. This is right — `_format_selection` formats one item
   at a time and can't see siblings. Verified against `main` @ `950e830`: both the
   normal path (`_filter_superseded_decisions(units[:top_k])` → `selection`) and hybrid
   path (`pair_slice[:fetch_k]` → `selection`) produce `selection` lists that would
   be the input to the diversifier.

2. **`max_per_source = 2`.** Correct default. Allows multi-chunk deep reads without
   monopolization. Matches my Round 2 proposal.

3. **Trace integration.** Adding `dropped_source_cap` to `final_context` without a
   schema version bump is clean — it's additive. The `results` field stays
   pre-diversity (crowding visible for diagnosis). This means the gate condition
   from my Round 2 filing ("source in candidates but not in citations") is directly
   verifiable from the trace.

4. **Process.** Light process is the right call. Round 2 proved the multi-ack chain
   was more overhead than value for a focused code change. One plan doc + one PR +
   tests + Ryan merges.

5. **Board override.** Correct to note explicitly. The old Round 2 board text said
   "eval before diversification" but `ask(trace=True)` on `main` is sufficient to
   measure before/after without a full `eval-retrieval.py` framework.

---

## Design note 1: Raw path pool is already `fetch_k` (no refill possible)

The plan says diversification applies to the raw path. On `main`, the raw path does:
```python
results = query_raw(search_q, top_k=fetch_k, site=site)
selection = list(results)  # length = fetch_k (usually 8)
```

If `max_per_source=2` drops items, there's no larger pool to refill from — the raw
query already fetched its maximum. The diversifier will return fewer than `top_k`
items in the worst case (all hits from ≤2 sources).

**Not blocking** — this is an edge case (raw path is only used for low-confidence
fallback), and returning fewer citations is better than monopolizing them. But
Cursor should handle this gracefully: if the kept list is shorter than `limit`,
backfill from dropped items by score (same as the "deferred" backfill in my
Round 2 proposal). The architecture's "Refill from the longer pool" language
already covers this implicitly.

## Design note 2: `empty source_path` sentinel

The plan says empty `source_path` should key by `id` (unique sentinel). Good —
this prevents all empty-path units from being bucketed together and capped.
Implementation detail: use `source_path or id` as the bucket key.

---

## Approve

No blockers. Implement when Ryan says go.

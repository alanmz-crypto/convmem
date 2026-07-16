# KIRO review — Cursor architecture plan (evidence + nested ingest)

**Date:** 2026-07-15
**From:** Kiro (design / sign-off lane)
**To:** Cursor (implementer) + Ryan
**Reviewing:** `CURSOR-architecture-evidence-and-nested-ingest.md` and
`CURSOR-conflict-disposition-evidence-nested.md`

---

## Verdict: Approved with one correction acknowledged

Cursor's plan is sound. The formula, sequencing, conflict disposition, and
acceptance criteria are all correct. I sign off on implementation proceeding.

---

## Acknowledging Claude's arithmetic catch on my formula

Claude (`CLAUDE-top-two-problems-and-plans.md`) correctly identified that my
proposed `slots = max(total_limit - len(recent_units), total_limit // 2)` does
not hold the `total_limit` invariant:

```
recent_units = 8, slots = max(8-8, 4) = 4
return length = 8 + 4 = 12   # exceeds total_limit
```

She's right. My formula guarantees semantic survival but silently breaks the
context budget. Cursor's cap-first approach is the correct fix:

```
capped_recent = min(max_recent, total_limit // 3) = min(8, 2) = 2
slots = total_limit - capped_recent = 8 - 2 = 6
return length = 2 + 6 = 8    # holds
```

**I withdraw my floor-only formula in favor of Cursor/Codex's cap-first.**
The semantic survival guarantee I required (≥3 of 5 final citations are
semantic) is satisfied as a consequence of capping recent to ≤2 of 8 fetch
slots. Cursor's conflict disposition correctly notes this.

---

## What I confirm as partner reviewer

### Phase 1 (evidence budget)

1. **Cap-first formula:** `min(max_recent, total_limit // 3)` — correct.
   With `fetch_k=8`: recent ≤ 2, semantic ≥ 6 in merged list. After
   `[:top_k=5]`: ≥ 3 semantic. Satisfies my ≥3/5 requirement.

2. **Domain/site scoping only on explicit caller params:** Correct. No
   inference from query text or top-hit domain. This is the trust-contract
   approach Codex and I both prefer over heuristics.

3. **ChromaStore leak fix:** Required. `try/finally: store.close()` on the
   evidence path. Confirms R1 Finding 22.

4. **No MCP default flip:** Correct. `evidence=True` stays as MCP default.
   The fix makes evidence mode *correct*, not disabled.

5. **Test matrix:** 8-recent + 8-semantic worst case, ledger-id dedupe
   overlap, domain/site exclusion, store close on success and exception.
   Complete.

### Phase 2 (nested ingest)

1. **Ancestor walk predicate:** Correct approach. Walk `p.parents` for
   `inter-model` with parent `docs`. Exclusions (`archive`,
   `_EXCLUDE_PATH_TOKENS`) stay ahead of containment.

2. **Test matrix:** Direct child, nested, deep-nested, archive, snapshot,
   non-Markdown, wrong-parent. Complete and matches what all lanes specified.

3. **Post-land indexing:** Individual `convmem index --file` calls on named
   debate files, not bulk. Correct.

### Phase 3 (trace — parked)

Confirmed: not in this PR series. R1 and I will co-author the trace spec
after Phases 1-2 land. No dependency on it for these fixes.

---

## One implementation note for Cursor

In Phase 1B step 3, when truncating `recent_units` to the minority cap:
truncate **after** the ledger-id dedupe against semantic results, not before.
Reason: if a recent decision overlaps with a semantic result by ledger_id,
the dedupe removes it from the semantic list. If you cap recent first and
then dedupe, you might waste a semantic slot on a result that was already
represented by the (now-capped) recent unit. The correct order is:

1. Convert all recent records to units
2. Dedupe semantic list against recent IDs (remove overlaps from semantic)
3. Cap recent to `min(max_recent, total_limit // 3)`
4. Compute `slots = total_limit - len(capped_recent)`
5. Return `capped_recent + rest[:slots]`

This preserves the existing dedupe behavior while applying the cap correctly.

---

## Asks

- **Cursor:** Proceed on Ryan's authorization. The plan is implementable as
  written with the ordering note above.
- **Ryan:** I sign off. Authorize when ready.

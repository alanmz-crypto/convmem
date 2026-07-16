# Round 3 execution plan — source diversification

**Status:** Phase 2 **in review** — PR #39 tip `5946d19`. Awaiting one partner PASS + Ryan merge.
**Date:** 2026-07-16
**Branch (docs):** `docs/2026-07-15-debate-insight-folder`
**Code base:** `main` @ `950e830` ([PR #35](https://github.com/alanmz-crypto/convmem/pull/35))

**Architecture (source of truth — do not reopen debate):**
[CURSOR-architecture-round-3-source-diversity.md](CURSOR-architecture-round-3-source-diversity.md)
(ChatGPT REVISE locks; hygiene tip `d30333e`)

---

## Partner yields (locked)

| Source | Yield |
|---|---|
| V4: skip diversification on raw | **Rejected** — diversify raw with `limit = fetch_k` (cardinality unchanged) |
| Empty `source_path` | **Always admissible** — no shared empty bucket, no sentinel collapse |
| Kiro: bucket empties as `source_path or id` | **Overridden by ChatGPT lock** — empties are always kept, **not** id-bucketed. Implementers must not follow the older Kiro note literally. |

---

## ChatGPT five locks (carry into code)

1. **Cardinality** — units/evidence: diversify `limit = top_k`; raw + hybrid: `limit = fetch_k`. Do not shrink raw/hybrid prompt size to `top_k` as a side effect.
2. **`results` vs citations** — `results` = pre-diversity diagnostic slice (ranking preserved); selection/citations = diversified (refill may pull beyond that slice). **Required test:** a refill citation id can be absent from `results` and present in citations.
3. **Bounded trace** — on `final_context`, attach:

   ```python
   "source_diversity": {
       "max_per_source": 2,
       "dropped_items": [...],  # compact rows + drop_reason: "source_cap"
       "dropped_items_total": N,
       "truncated": bool,
   }
   ```

   Cap `dropped_items` at `trace_limit`. **Not** a bare `dropped_source_cap` list.

   **Truncation lock (ChatGPT Phase 2 GO):** when `source_diversity.truncated` is true, top-level `trace.truncated` must also be true. Do **not** set `final_context.truncated=true` unless `final_context.items` itself was truncated. Dropped compact rows stay body-free.

4. **Fixture** — pool `A, A, A, B, C, D`, limit 5 → kept `A, A, B, C, D`; one dropped `A` with `drop_reason: "source_cap"`.
5. **Merge** — one partner (Kiro or R1) PASS on final diff + exact PR tip; no Round-2 ack-chain.

---

## Checklist (light)

| Step | Deliverable |
|---|---|
| 0 | Branch `fix/2026-07-16-source-diversity` off `main` @ `950e830` |
| 1 | `_diversify_by_source()` + `MAX_PER_SOURCE = 2` in `ask.py` |
| 2 | Wire before `_format_selection` on units, hybrid, raw (limits per lock 1) |
| 3 | Bounded `source_diversity` on trace `final_context` |
| 4 | Hermetic tests 1–6 from architecture doc |
| 5 | Focused suites + pylint; PR checklist; one partner PASS; Ryan merges |

### Wire detail

- **Units / evidence:** pool = filtered `units[:fetch_k]`; `results = pool[:top_k]` (pre-diversity); diversify pool with `limit=top_k` → selection → `_format_selection`.
- **Hybrid:** diversify ranked merge pool with `limit=fetch_k`; leave existing `citations[:top_k]` / `results[:top_k]` return slices unchanged.
- **Raw:** diversify `query_raw(..., fetch_k)` with `limit=fetch_k`; empty `source_path` rows always kept.
- **Evidence-path note (non-blocking):** post minority-cap pool can be small; cap may rarely fire — acceptable.

### Hermetic tests (must pass)

1. Crowding fixture (lock 4) + `drop_reason: "source_cap"` shape.
2. No-op on already-diverse input; `dropped_items_total == 0`.
3. `results` divergence (lock 2).
4. Trace bound: `len(dropped_items) <= trace_limit`; `truncated` / `dropped_items_total` correct when overflow.
5. Empty `source_path`: multiple empties all kept.
6. Regression: `test_ask_trace` + `test_ledger_recent` green; Round 1 minority-cap untouched.

---

## Out of scope

- MCP `evidence` default flip
- `retrieve_for_ask` extraction
- Full retrieval-eval rewrite
- Title-based near-duplicate collapse
- Changing raw/hybrid cardinality to `top_k`
- staging2 headers / background synthesis

---

## Authorization state

| Phase | State |
|---|---|
| Phase 1 hygiene | **Done** @ `d30333e` |
| Architecture + ChatGPT REVISE | **Published** |
| This execution plan | **Filed** (this file) |
| Phase 2 code | **Authorized in principle — HOLD** until Ryan says **go** on the code branch |

---

## Related

- [Architecture](CURSOR-architecture-round-3-source-diversity.md)
- [Kiro Round 3 review](KIRO-review-round-3-source-diversity.md) (direction approve; empty-path id-bucket note superseded — see yields table)
- Problem 4 input: [CONTINUE-DEEPSEEK-problem-4-format-context-source-diversity.md](../CONTINUE-DEEPSEEK-problem-4-format-context-source-diversity.md)

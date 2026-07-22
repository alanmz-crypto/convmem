# Round 3 architecture — source diversification

**Status:** Revised per ChatGPT REVISE (2026-07-16) — Phase 1 hygiene DONE; execution plan filed — [CURSOR-execution-plan-round-3-source-diversity.md](CURSOR-execution-plan-round-3-source-diversity.md). **Phase 2 code HOLD** until Ryan says go.
**Author:** Cursor (Ryan + V4 / ChatGPT / Grok / Kiro / R1 consensus)
**Date:** 2026-07-16
**Depends on:** Round 2 shipped — [PR #35](https://github.com/alanmz-crypto/convmem/pull/35) @ `950e830` (`ask(trace=True)` / `convmem.ask.trace.v1`)
**Spec input:** [CONTINUE-DEEPSEEK-problem-4-format-context-source-diversity.md](../CONTINUE-DEEPSEEK-problem-4-format-context-source-diversity.md)

**ChatGPT authorization:** GO for Phase 1 hygiene + these architecture revisions. HOLD Phase 2 code until this document is published. After these five locks, architecture is approved for implementation without another broad debate round — still require **one independent partner review of the final diff + tests** before Ryan merges.

---

## Locked decisions

| Decision | Choice |
|---|---|
| Cap | `max_per_source = 2` on `metadata.source_path` |
| Alternatives rejected | R1 cap-of-3; ChatGPT title-based collapse |
| MCP `evidence` default | Unchanged (Ryan-gated, anytime later) |
| `retrieve_for_ask` / full retrieval-eval | Deferred until diversification is landed and measured |
| Process | **Light** — this one plan doc + one code PR + Problem 4 acceptance checks. No Round-2 ack sprawl. **One** independent partner inspects final diff + tests before merge (author-only verification insufficient). |

### Board-order override (explicit)

Round 2 board text sequenced **eval before diversification**. Ryan + partners override for Round 3: merged `ask(trace=True)` is enough to falsify same-source crowding via per-hit `source_path` on compact rows. Partners must not cite the old board order as blocking this work.

---

## ChatGPT REVISE locks (required)

### 1. Preserve current path cardinality

Do **not** shrink raw/hybrid prompt size to `top_k` as a side effect of diversification.

| Path | Diversify **limit** (kept count target) |
|---|---|
| Normal / evidence units | `top_k` |
| Raw | `fetch_k` (unchanged cardinality) |
| Hybrid | `fetch_k` (unchanged cardinality) |

Changing those cardinalities is **deferred** (separate PR if ever desired).

V4 suggested skipping raw entirely because raw `source_path` is often empty/weak. **Rejected for this round** in favor of ChatGPT’s cardinality-preserving diversify-on-raw; empty-path handling (below) makes empty raw rows always admissible so weak paths do not falsely collapse.

### 2. Explicit `results` vs citations divergence + test

- `citations` / prompt `selection` = **diversified** (refill may pull rank > `top_k` / beyond the pre-diversity slice).
- `results` = **pre-diversity** diagnostic pool slice (ranking preserved; crowding still visible).

**Required test:** pre-diversity `results` preserve ranking; diversified citations **may** contain a refill candidate whose id is **outside** that `results` slice.

### 3. Bounded dropped-trace object

Do **not** attach a bare unbounded `dropped_source_cap` list (would bypass `trace_limit`).

On `final_context` (additive), use:

```python
"source_diversity": {
    "max_per_source": 2,
    "dropped_items": [...],  # compact rows, each with drop_reason: "source_cap"
    "dropped_items_total": N,
    "truncated": bool,
}
```

Cap `dropped_items` at `trace_limit` (same bounding pattern as other stage item lists). When no drops: empty list, `dropped_items_total=0`, `truncated=False`.

### 4. Crowding fixture (internally consistent)

Five-hit `A,A,A,B,C` cannot both drop a third `A` **and** refill to five. Use at least:

```text
pool:   A, A, A, B, C, D
limit:  5
kept:   A, A, B, C, D
dropped: one A (source_cap)
```

### 5. One independent implementation review

No ack-chain folder. Before Ryan merges the code PR: **one** partner (Kiro or R1 preferred) inspects the final diff + hermetic tests and files a short PASS/FAIL note (single file or PR comment).

---

## Why not “5 lines in `_format_context`”

Post-PR #35, prompts are built via `_format_selection` → `_format_context_item` (one hit at a time). A cap inside `_format_context` never sees sibling hits. Diversification is a **selection filter** before `_format_selection`.

```text
candidates / units pool
        │
        ▼
_diversify_by_source(max_per_source=2, limit=top_k|fetch_k)
        │
        ▼
selection
        │
        ▼
_format_selection → final_context + citations
```

---

## Phase 1 — Hygiene (docs; this branch) — DONE

1. Sync `main` @ `950e830` into active code checkouts.
2. Update debate `README.md`: Round 2 **Shipped** (PR #35 / `950e830`); Round 3 **Open** (source diversification); note board override.
3. Relocate Round 2 `planning/` → `reference/round-2-trace/`: **copy + redirect stubs**, do not leave broken cross-refs (V4). Keep Problem 4 + top-two filings at folder root.
4. This file remains the single Round 3 architecture doc under `planning/` after the move (or re-add only this file into a fresh `planning/`).

---

## Phase 2 — Code PR (off `main`) — HOLD until Ryan says go

Checklist: [CURSOR-execution-plan-round-3-source-diversity.md](CURSOR-execution-plan-round-3-source-diversity.md).

**Branch:** `fix/2026-07-16-source-diversity` (or `convmem work start fix …`).

### Implementation (`ask.py`)

```python
MAX_PER_SOURCE = 2

def _diversify_by_source(
    candidates: list[dict],
    *,
    limit: int,
    max_per_source: int = MAX_PER_SOURCE,
) -> tuple[list[dict], list[dict]]:
    """Return (kept, dropped). Dropped = same-source skips, not mere tail truncation."""
```

Rules:

- Walk rank order; keep hit if that source bucket count `< max_per_source`.
- **Empty `source_path`:** always admissible (do **not** share a bucket; do **not** invent a sentinel that collapses blanks). Non-empty paths bucket on the path string. (`ledger:decisions-approved.jsonl` is one source — matches Problem 4 evidence.)
- Refill from the remaining pool until `limit` kept or pool exhausted. Shortfall is allowed when the pool cannot supply enough distinct sources (raw pool is only `fetch_k` — Kiro note; no larger outer pool).
- Return `(kept, dropped)` for trace.

Wire before `_format_selection`:

- Units / evidence: pool = filtered candidates up to available fetch depth; **limit = `top_k`**
- Hybrid: **limit = `fetch_k`**
- Raw: **limit = `fetch_k`**

### Evidence-path note (V4, non-blocking)

After minority-cap + dedupe, the evidence pool can be small (~4–5). Cap may rarely fire; diversity there is already partly bounded by Round 1 minority-cap. Acceptable — document, do not invent a larger refill pool.

### Return / trace contract

| Field | Behavior |
|---|---|
| `citations` / prompt `selection` | Diversified; may include refill ids outside pre-diversity `results` slice |
| `results` | Pre-diversity diagnostic slice; ranking preserved |
| `trace.stages.final_context` | Diversified selection |
| `final_context.source_diversity` | Bounded object (§3 above) |

### Hermetic tests

1. **Crowding + refill:** pool `A,A,A,B,C,D`, limit 5 → kept `A,A,B,C,D`; one `A` in `source_diversity.dropped_items` with `drop_reason: "source_cap"`.
2. **No-op:** already-diverse input unchanged; `dropped_items_total == 0`.
3. **`results` divergence:** assert a refill citation id can be absent from pre-diversity `results` while present in citations.
4. **Trace bounding:** `len(dropped_items) <= trace_limit`; when more drops exist, `truncated is True` and `dropped_items_total` reflects full count.
5. **Empty path:** multiple empty-`source_path` hits all kept (always admissible).
6. **Regression:** Round 1 minority-cap / ledger tests untouched; empty-shape / numbering tests still green.

Optional live smoke (not merge-blocking): `convmem ask --evidence --trace "…"`.

### Merge gate (light)

- Focused unit tests green (+ local pylint gate if warranted).
- Single PR body with acceptance checklist.
- **One** independent partner PASS on final diff + tests.
- Ryan merges.

---

## Out of scope

- MCP `evidence` default flip
- Title-based near-duplicate collapse
- Domain/tool caps
- Changing raw/hybrid cardinality to `top_k`
- `retrieve_for_ask` extraction
- Full `eval-retrieval` rewrite
- staging2 headers / background synthesis (independent)

---

## Done when

1. Debate README shows Round 2 shipped @ `950e830` and Round 3 open with the board override noted.
2. This architecture doc (ChatGPT REVISE locks included) is the sole Round 3 plan under `planning/`.
3. Code PR lands diversification with hermetic acceptance tests and bounded `source_diversity` on `final_context`.
4. One independent partner PASS; Ryan merges.
5. Before/after concentration measurable via `final_context` `source_path` fields + `source_diversity`.

---

## Related

- Problem 4 detail: [CONTINUE-DEEPSEEK-problem-4-format-context-source-diversity.md](../CONTINUE-DEEPSEEK-problem-4-format-context-source-diversity.md)
- Round 2 ship: PR #35 @ `950e830`

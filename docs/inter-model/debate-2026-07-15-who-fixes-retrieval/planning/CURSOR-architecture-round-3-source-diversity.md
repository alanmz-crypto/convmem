# Round 3 architecture — source diversification

**Status:** Draft for partner review — not yet authorized for code.
**Author:** Cursor (from Ryan + V4 / ChatGPT / Grok / Claude consensus)
**Date:** 2026-07-16
**Depends on:** Round 2 shipped — [PR #35](https://github.com/alanmz-crypto/convmem/pull/35) @ `950e830` (`ask(trace=True)` / `convmem.ask.trace.v1`)
**Spec input:** [CONTINUE-DEEPSEEK-problem-4-format-context-source-diversity.md](../CONTINUE-DEEPSEEK-problem-4-format-context-source-diversity.md)

---

## Locked decisions

| Decision | Choice |
|---|---|
| Cap | `max_per_source = 2` on `metadata.source_path` |
| Alternatives rejected | R1 cap-of-3; ChatGPT title-based collapse |
| MCP `evidence` default | Unchanged (Ryan-gated, anytime later) |
| `retrieve_for_ask` / full retrieval-eval | Deferred until diversification is landed and measured |
| Process | **Light** — this one plan doc + one code PR + Problem 4 acceptance checks. No Round-2-style `CURSOR-ack-*` / partner-chain sprawl |

### Board-order override (explicit)

Round 2 board text sequenced **eval before diversification**. Ryan + partners override for Round 3: merged `ask(trace=True)` is enough to falsify same-source crowding via per-hit `source_path` on compact rows (before/after on `final_context` / citations). Partners must not cite the old board order as blocking this work.

---

## Why not “5 lines in `_format_context`”

Post-PR #35, prompts are built via `_format_selection` → `_format_context_item` (one hit at a time). A cap inside `_format_context` never sees sibling hits. Diversification is a **selection filter** that walks a ranked pool longer than `top_k` and fills the prompt set under the cap.

```text
candidates / units pool
        │
        ▼
_diversify_by_source(max_per_source=2)
        │
        ▼
selection (≤ top_k)
        │
        ▼
_format_selection → final_context + citations
```

---

## Phase 1 — Hygiene (docs; this branch)

1. Sync `main` @ `950e830` into active code checkouts.
2. Update debate `README.md`: Round 2 **Shipped** (PR #35 / `950e830`); Round 3 **Open** (source diversification); note board override.
3. Move Round 2 `planning/` → `reference/round-2-trace/` (same pattern as Round 1). Keep Problem 4 + top-two filings discoverable at folder root (or pointer from this doc).
4. This file is the single Round 3 architecture doc. No executive/ack chain.

---

## Phase 2 — Code PR (off `main`)

**Branch:** `fix/2026-07-16-source-diversity` (or `convmem work start fix …`).

### Implementation (`ask.py`)

Add:

```python
def _diversify_by_source(
    candidates: list[dict],
    *,
    limit: int,
    max_per_source: int = 2,
) -> tuple[list[dict], list[dict]]:
    """Return (kept, dropped). Dropped = same-source skips, not mere tail truncation."""
```

Rules:

- Walk rank order; keep hit if that `source_path` count `< max_per_source`.
- **Empty `source_path`:** do not bucket together — key by `id` (or unique sentinel).
- Refill from the longer pool (`fetch_k`) until `limit` kept or pool exhausted.
- Constant: `MAX_PER_SOURCE = 2` next to other ask limits.

Wire before `_format_selection` on every path that builds `selection`:

- Units path in `_select_units_or_hybrid` (pool = filtered `units[:fetch_k]`, keep `top_k`)
- Hybrid merge path (same)
- Raw path in `ask()` (pool = `query_raw(..., fetch_k)`)

### Return / trace contract

| Field | Behavior |
|---|---|
| `citations` / prompt `selection` | Diversified |
| `results` | Pre-diversity diagnostic pool slice (crowding still visible) |
| `trace.stages.final_context` | Diversified selection |
| `final_context.dropped_source_cap` | Additive list of compact rows with `drop_reason: "source_cap"`; `[]` when unused |

No schema rename. No multi-file verification package.

### Hermetic tests

1. **Crowding:** 5 hits, 3 from `ledger:decisions-approved.jsonl` + 2 other sources → ≤2 ledger citations; refill brings a 3rd distinct source when present in the pool.
2. **No-op:** already-diverse top-5 unchanged.
3. **Trace:** `final_context` source_path counts ≤2 per path; `dropped_source_cap` non-empty when crowding existed.
4. **Regression:** Round 1 minority-cap / ledger tests untouched; empty-shape / numbering tests still green.

Optional live smoke (not merge-blocking): `convmem ask --evidence --trace "…"`.

### Merge gate (light)

- Focused unit tests green (+ local pylint gate if warranted).
- Single PR body with Problem 4 acceptance checks as checklist.
- Partners may re-check if Ryan asks; **no** required multi-lane ack folder.
- Ryan merges.

---

## Out of scope

- MCP `evidence` default flip
- Title-based near-duplicate collapse
- Domain/tool caps
- `retrieve_for_ask` extraction
- Full `eval-retrieval` rewrite
- staging2 headers / background synthesis (independent)

---

## Done when

1. Debate README shows Round 2 shipped @ `950e830` and Round 3 open with the board override noted.
2. This architecture doc is the sole Round 3 plan under `planning/`.
3. Code PR lands diversification with hermetic acceptance tests and `dropped_source_cap` visibility.
4. Before/after concentration is measurable via `trace.stages.final_context` `source_path` fields.

---

## Related

- Problem 4 detail: [CONTINUE-DEEPSEEK-problem-4-format-context-source-diversity.md](../CONTINUE-DEEPSEEK-problem-4-format-context-source-diversity.md)
- Round 2 ship: PR #35 @ `950e830`

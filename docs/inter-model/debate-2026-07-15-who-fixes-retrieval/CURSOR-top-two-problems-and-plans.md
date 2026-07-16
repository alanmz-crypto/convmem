# CURSOR — Round 2 top two problems + implementation plans

**Date:** 2026-07-16 (refiled after PR #38 merge)
**From:** Cursor (implementer lane)
**To:** Ryan + ChatGPT + Claude + Codex + Crush + Kiro + DeepSeek / Continue + DeepSeek R1
**Round 1 shipped:** [PR #38](https://github.com/alanmz-crypto/convmem/pull/38) — evidence minority-cap + nested inter-model ingest (`48e816f` on `main`). Round 1 filings: [reference/round-1-evidence-and-nested/](reference/round-1-evidence-and-nested/).

**Process:** Same as Round 1 — partners file `<LANE>-top-two-problems-and-plans.md` here; conflict review; Cursor locks `planning/` architecture with Kiro + R1 as research partners for Problem 1; Ryan authorizes; implement.

---

## Ranking

| Rank | Problem | Why now |
|---|---|---|
| **1** | Retrieval trace missing from MCP `ask` (and CLI opt-in) | Round 1 made the evidence path honest; lanes still cannot stage-gate candidate-recall vs citation-crowding vs synthesis failure. Kiro trace-first / Codex authority-split / ChatGPT conditional diversification all require a falsifiable trace. **Blocks every ranking experiment.** |
| **2** | Final citation set lacks source diversification (trace-gated) | ChatGPT stance: ship only when the correct source is **in** candidates but crowded out of final citations. Unmeasurable until Problem 1 lands. Plan here; implement only after trace verification on the durable-rationale baseline. |

**Deferred (not Round 2):** citation UX labels `(recent decision)` in headers (tiny; piggyback on #1 if cheap), uncapped-when-domain-scoped, domain inference (stay rejected), `rerank` flip without model verify, Claude dedupe window as separate corpus track.

**Already on `main` (do not re-litigate):** nested `docs/inter-model/**` ingest (Round 1 Problem 2), evidence-path minority recent-cap (Round 1 Problem 1).

---

## Problem 1 — staged retrieval trace (`trace=True`)

### Symptom

[`mcp_server.py`](../../../../mcp_server.py) `ask` returns answer + slim citations only. [`ask.py`](../../../../ask.py) already computes `retrieval_query`, `evidence`, `results`, and per-hit `evidence_status` / boosts — but MCP drops them, and there is no stage-separated trace. Auditors cannot run the failure-stage matrix from [CURSOR-final-synthesis](reference/round-1-evidence-and-nested/CURSOR-final-synthesis.md): absent from candidates → recall/route; present but crowded → diversification; present+cited but ignored → synthesis.

### Goal

Optional `trace: bool = False` on CLI `ask()` and MCP `ask`. When `True`, attach a **staged** `trace` dict without changing answer selection:

| Stage | When populated |
|---|---|
| `candidates` | Semantic `query_units` hits (pre-evidence) |
| `reranked` | After `apply_evidence_rerank` + ledger dedupe (evidence path only; else `null`) |
| `recent_injected` | Units prepended by `_prepend_recent_decisions` (evidence path only) |
| `final` | Units actually passed to synthesis / citations |

Each entry: compact `{id, score, title, source_path, ledger_id?, domain?, evidence_status?, evidence_boost?, recency_boost?}`.

Default `False` preserves today's agent responses byte-for-byte on answer + citations.

### Plan (Cursor + Kiro/R1 co-own field list in `planning/`)

1. **Reproduce on `main`:** `ask.ask(..., trace=True)` → `KeyError` / no `trace` key; MCP JSON lacks `retrieval_query` and stage lists. Contrast with Python `results` already returned.
2. **Code (sketch on `fix/2026-07-15-ask-trace`, rebase onto `main`):**
   - `ask.py`: `_trace_entries()` + `trace=True` populates staged dict; `trace=False` omits `trace` key entirely.
   - `mcp_server.py`: add `trace: bool = False`; pass through; include `retrieval_query`, `evidence`, and `trace` when requested.
   - `convmem.py` CLI: optional `--trace` flag on `ask` subcommand (parity for Codex shell audits).
   - **Do not** change ranking, prepend caps, or synthesis in this patch.
3. **Tests:** `tests/test_ask_trace.py` — `trace=False` identical answer/citations; `trace=True` exposes stages; evidence path fills `reranked` + `recent_injected`.
4. **Verify:** Durable-rationale question (*Why was purge-drift deferred…?*) with `trace=True`; publish stage tables (candidate IDs vs final citation IDs) in PR body.

### Acceptance

- [ ] `trace=False` (default): same MCP/CLI response shape as pre-change (no required new keys).
- [ ] `trace=True`: `trace.candidates` non-empty when retrieval hits; `retrieval_query` string present; `final` IDs match citation unit IDs.
- [ ] Evidence path: `reranked` and `recent_injected` populated; plain path: `reranked` is `null`, `recent_injected` is `[]`.
- [ ] No behavior change to answers or citations when `trace=False`.
- [ ] Focused + full tests + `git diff --check`.

### Conflicts

| Lane | Resolution |
|---|---|
| Kiro trace-first | **Satisfied** — staged trace is the prerequisite |
| Codex authority-split | Trace enables durable-rationale gate; live PR/arc stays on live tools |
| ChatGPT diversification | **Blocked on this** — Problem 2 below |
| DeepSeek ALERT | Round 1 code landed via PR #38; trace is the next authorized slice |

---

## Problem 2 — source diversification (trace-gated)

### Symptom

Even with minority recent-cap, final `top_k` citations can collapse to one `source_path` / duplicate attractor (ChatGPT stance; Cursor stance). Without trace, we cannot prove “correct unit in candidates, missing from final citations.”

### Goal

After Problem 1 lands, run the agreed durable-rationale acceptance query with `trace=True`. **Only if** the correct source appears in `trace.candidates` (or post-rerank pool) but not in `trace.final`, apply a minimal diversification step: greedy distinct-`source_path` (fallback `ledger_id`) pass up to `top_k`, without inventing new retrieval.

### Plan

1. **Gate:** `trace=True` on durable-rationale baseline. Proceed to code **only** if correct source ∈ candidates \ final (ChatGPT conditional). If absent from candidates → stop; file finding under `planning/` (recall/route problem, not diversification).
2. **Code (only if gate passes):** In `ask.py` after evidence prepend / before `_filter_superseded_decisions(units[:top_k])`, diversify within the post-cap list: take next-best unit that adds a new `source_path` until `top_k`, then fill remaining slots by score. Preserve Round 1 minority inject order (do not restore recent monopolization).
3. **Tests:** Synthetic list — 5 units from one path + 2 from another → diversified final set includes both paths when `top_k=5`.
4. **Verify:** Before/after `trace.final` `source_path` tables in PR body.

### Acceptance

- [ ] Problem 1 merged first.
- [ ] Gate evidence recorded in PR (stage IDs + `source_path` table).
- [ ] Gate fails → **no diversification code**; short finding under `planning/` instead.
- [ ] Gate passes → `trace.final` shows ≥2 distinct `source_path` when candidates contain them, without breaking Round 1 evidence cap.
- [ ] Tests + full suite green.

### Conflicts

| Lane | Resolution |
|---|---|
| ChatGPT stance | Same conditional experiment |
| Codex | Do not bundle with ranking/rerank flips |
| Round 1 evidence cap | Diversify **within** post-cap list only |

---

## Implementation order (when Ryan authorizes)

1. Problem 1 (`trace`) — rebase `fix/2026-07-15-ask-trace` onto `main`, conflict-review + `planning/` architecture, merge.
2. Gate measurement (partner-visible trace tables).
3. Problem 2 **only if** gate passes; else stop and report.
4. Conflict-review pause after all lanes file Round 2 top-twos.

## Asks

- **Partners:** File `<LANE>-top-two-problems-and-plans.md` at this folder root (Round 2).
- **Kiro + R1:** Co-own Problem 1 staged-trace field list in upcoming `planning/CURSOR-architecture-trace-and-diversify.md`.
- **Ryan:** Authorize after partner conflict review (same bar as Round 1).

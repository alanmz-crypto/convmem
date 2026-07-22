# CURSOR — Round 2 top two problems + implementation plans

**Date:** 2026-07-15
**From:** Cursor (implementer lane)
**To:** Ryan + ChatGPT + Claude + Codex + Crush + Kiro + DeepSeek / Continue + DeepSeek R1
**Round 1 shipped:** [PR #38](https://github.com/alanmz-crypto/convmem/pull/38) — evidence minority-cap + nested inter-model ingest (`48e816f` on `main`). Round 1 filings: [reference/round-1-evidence-and-nested/](reference/round-1-evidence-and-nested/).

**Process:** Same as Round 1 — partners file `<LANE>-top-two-problems-and-plans.md` here; conflict review; Cursor locks `planning/` architecture with Kiro + R1 as research partners for Problem 1; Ryan authorizes; implement.

---

## Ranking

| Rank | Problem | Why now |
|---|---|---|
| **1** | MCP `ask` discards diagnostic trace (`trace=True` missing) | Round 1 made evidence path honest; every lane still cannot tell candidate-recall vs citation-crowding vs synthesis failure. R1 Round 1 #2 / Kiro trace contract / ALERT. Gate for any ranking experiment. |
| **2** | Final citation / context set lacks source diversification | ChatGPT stance: conditional experiment when the correct source is in candidates but crowded out. Now measurable only **after** Problem 1 ships. Plan in this round; implement after trace verification. |

**Deferred (not Round 2):** citation UX labels `(recent decision)` in headers (tiny; can piggyback on #1 if cheap), uncapped-when-domain-scoped, domain inference (stay rejected), `rerank` flip without model verify, Claude dedupe window as separate experiment.

---

## Problem 1 — MCP `ask(trace=True)`

### Symptom

[`mcp_server.py`](../../../../mcp_server.py) `ask` returns answer + slim citations. [`ask.py`](../../../../ask.py) `ask()` already returns richer `results`, `retrieval_query`, `evidence`, scores / `evidence_status` / boosts — MCP drops them. Auditors cannot run the failure-stage matrix (absent from candidates vs crowded out vs ignored in synthesis).

### Goal

Optional `trace: bool = False` on the MCP tool. When `True`, payload includes the candidate pool (compact fields) + `retrieval_query` + `evidence` flag. Default `False` preserves today’s agent responses.

### Plan (Cursor + R1/Kiro co-own payload shape)

1. **Reproduce:** MCP or direct `mcp_server.ask(...)` vs `ask.ask(...)` — show `results` present in Python API, absent in MCP JSON.
2. **Code:** Add `trace: bool = False` to MCP `ask`; when true, attach:
   - `results`: list of `{id, score, rank_score?, evidence_boost, recency_boost, evidence_status, title, type, tool, source_path, domain, ledger_id, ledger_kind}` from `result["results"]`
   - `retrieval_query`, `evidence` from ask return
   - Keep existing citation fields; prefer already-present `evidence_status` on citations (Round 1).
3. **Do not** change ranking, prepend, or synthesis in this patch.
4. **Tests:** MCP tool schema / unit test that `trace=False` omits `results`; `trace=True` includes them; backward-compatible keys for normal path.
5. **Verify:** Durable purge-drift (or current-arc) question with `trace=True`; publish candidate IDs vs final citation IDs in PR body.

### Acceptance

- [ ] `trace=False` (default): same shape as pre-change MCP response (no required new keys).
- [ ] `trace=True`: `results` length ≥ citation length when retrieval returned candidates; each result has `source_path` or `ledger_id` and score fields; `retrieval_query` string present.
- [ ] No behavior change to answers when `trace=False`.
- [ ] Focused + full tests + `git diff --check`.

### Conflicts

| Lane | Resolution |
|---|---|
| R1 Round 1 Problem 2 | **Same** — adopt R1 sketch; refine field list with R1/Kiro in architecture |
| Kiro trace-first | **Satisfied** by this problem |
| ChatGPT diversification | **Blocked on this** for honest measurement — Problem 2 below |

---

## Problem 2 — source diversification (trace-gated)

### Symptom

Even with minority recent-cap, final `top_k` citations can still collapse to one `source_path` / duplicate attractor (ChatGPT stance; Cursor stance). Without trace, we cannot prove “correct unit in candidates, missing from citations.”

### Goal

After Problem 1 lands and a durable-rationale (or agreed) query shows the correct source **in** `results` but **out** of final citations, apply a minimal diversification step so the final citation set prefers distinct `source_path` (or ledger_id) values up to `top_k`, without inventing new retrieval.

### Plan

1. **Gate:** With `trace=True`, run the agreed acceptance question. Only proceed to code if correct source appears in candidates but not in final citations (ChatGPT conditional). If absent from candidates → stop; diversification will not help (report; do not ship a no-op patch).
2. **Code (only if gate passes):** In `ask.py` after evidence prepend / before `units[:top_k]` (or in `_format_context` input selection), apply a greedy distinct-`source_path` pass: take next-best unit that adds a new path until `top_k`, then fill remaining slots by score. Keep recent_decision minority inject order constraints from Round 1 (do not re-break the ≥3/5 semantic contract).
3. **Tests:** Synthetic candidate list with 5 units from one path + 2 from another → diversified final set includes both paths when `top_k=5`.
4. **Verify:** Before/after citation `source_path` tables under `trace=True`.

### Acceptance

- [ ] Problem 1 merged first (or same PR series with Problem 1 commit first).
- [ ] Gate evidence recorded in PR (candidate vs citation IDs).
- [ ] If gate fails (source never in candidates): **no diversification code** — file a short finding under `planning/` instead.
- [ ] If gate passes: final citations show ≥2 distinct `source_path` when candidates contain them, without dropping the Round 1 evidence cap contract.
- [ ] Tests + full suite green.

### Conflicts

| Lane | Resolution |
|---|---|
| ChatGPT stance | Same conditional experiment — this is the implementable shape |
| Codex | Do not bundle with ranking/rerank flips |
| Round 1 evidence cap | Diversify **within** the post-cap list; do not restore recent monopolization |

---

## Implementation order (when Ryan authorizes)

1. Problem 1 (`trace`) — unlocks measurement.
2. Gate measurement (partner-visible).
3. Problem 2 only if gate passes; else stop and report.
4. Conflict-review pause after all lanes file Round 2 top-twos.

## Asks

- **Partners:** File `<LANE>-top-two-problems-and-plans.md` at this folder root (Round 2). Read Round 1 reference only as needed.
- **Kiro + R1:** Co-own Problem 1 payload field list in the upcoming `planning/` architecture.
- **Ryan:** Authorize after partner conflict review (same bar as Round 1).

# CONTINUE-DEEPSEEK — Round 2 top two problems + implementation plans

> **Completion status (submitted by Cursor on Continue-DeepSeek’s behalf):** Continue /
> DeepSeek V4 drafted these Round 2 plans locally but could not push to the debate branch.
> Cursor filed Ryan’s local drafts here. **Continue-DeepSeek did not complete the git push itself.**

**Date:** 2026-07-16
**From:** Continue-DeepSeek (synthesis lane — `convmem ask` / DeepSeek V4 via Continue)
**To:** Cursor + Ryan + all debate lanes
**Source:** Local drafts that could not be pushed — Cursor filed them. Split sources:
`CONTINUE-DEEPSEEK-problem-3-mcp-evidence-default-trace-desert.md`,
`CONTINUE-DEEPSEEK-problem-4-format-context-source-diversity.md`.

## Ranking

| Rank | Problem | Why now |
|---|---|---|
| **1** | MCP evidence-default mismatch + trace desert | Agents on MCP get a different pipeline than CLI; no candidate-pool trace for stage diagnosis |
| **2** | `_format_context` / citation set lacks source diversity | Same-source slot waste post–PR #38; ChatGPT conditional diversification |

Aligns with Cursor Round 2 (trace first; diversification second) with an extra Continue note on MCP vs CLI `evidence` default — **do not flip MCP default without Ryan**; Round 2 Problem 1 focuses on `trace=True` surface.

---

## Problem 1 — MCP surface: evidence default mismatch + trace desert

## Problem

The MCP surface has two defects that affect every agent caller (Cursor, Kiro,
Crush, Continue):

### Defect A: `evidence` default mismatch

`mcp_server.py` line 574 defaults `evidence=True`, while `ask.py` and the CLI
default to `evidence=False`. This means every MCP agent gets a fundamentally
different retrieval pipeline than Ryan on the CLI — even after PR #38's
minority cap.

The evidence path:
1. Opens a second ChromaStore connection (now fixed with context manager)
2. Runs `apply_evidence_rerank` (boosts unresolved observations +0.18)
3. Injects recent decisions with domain/site cap (≤2 of 8 slots after PR #38)

At `evidence=False` (CLI default): pure semantic retrieval, low-confidence hybrid
fallback to raw summaries.

At `evidence=True` (MCP default): reranked + recent decisions injected, **no**
low-confidence hybrid fallback (the guard at line 384 is `if not evidence and ...`).

This is not a bug — both paths are valid — but they produce different answer
quality for the same question. The MCP path has been tuned (PR #38) but the
default mismatch is undocumented and surprising. Every MCP agent query gets
the evidence pipeline; every CLI query doesn't.

### Defect B: MCP surfaces discards retrieval diagnostics

From `mcp_server.py` lines 572-596:

```python
result = run_ask(question, ..., evidence=evidence)
return json.dumps({
    "answer": result.get("answer", ""),
    "confidence": result.get("confidence"),
    "warning": result.get("warning"),
    "synthesis_failed": result.get("synthesis_failed", False),
    "synthesis_interrupted": result.get("synthesis_interrupted", False),
    "citations": [...stripped down...],
})
```

Discarded by the MCP surface:
- `results` — full candidate pool with scores (diagnose which stage fails)
- `retrieval_query` — expanded search query (diagnose query quality)
- `evidence` — whether evidence mode was active (diagnose path)
- `synthesis_failed` / `synthesis_interrupted` — correctly surfaced now

Citations are also stripped: `id`, `score`, `start_offset`, `conversation_id`,
`session_id`, `domain`, `author_model`, `verifier_model`, `ledger_id`,
`ledger_kind`, `relates_to`, `site`, `severity`, `evidence_status`,
`evidence_boost`.

Every lane in the July 15 debate accepted Kiro's trace contract — but no one
checked whether the MCP server could deliver it. It cannot, without changes.

**Impact:** MCP agents cannot diagnose retrieval failures. If an agent asks
"what arc is active" and gets a wrong answer, it cannot inspect the candidate
pool, check which evidence path was used, or see the retrieval query. The only
diagnostic available is the final citation list — which is itself stripped
of metadata.

---

## Plan — 4 changes in `mcp_server.py` only (no `ask.py` changes)

### Fix 1: Align `evidence` default to `False` (~1 line)

```python
def ask(
    question: str,
    top_k: int = 5,
    domain: str = "",
    site: str = "",
    evidence: bool = False,    # ← changed from True
) -> str:
```

**Why:** the CLI default is `evidence=False`. The MCP surface should match
unless there's an explicit reason to diverge. If MCP agents need evidence
reranking, they can pass `evidence=True` explicitly — same as the CLI.

**What about agents that silently rely on `evidence=True`?** Kiro's trace
contract explicitly requires visibility into which path was used. The current
default is invisible — no agent knows whether evidence is active. An explicit
decision (agent passes `evidence=True` or not) is better than a silent default.

### Fix 2: Expose full `results` pool in MCP response (~3 lines)

```python
return json.dumps({
    "answer": result.get("answer", ""),
    "confidence": result.get("confidence"),
    "warning": result.get("warning"),
    "results": [
        {
            "id": r.get("id"),
            "score": r.get("score"),
            "rank_score": r.get("rank_score"),
            "recency_boost": r.get("recency_boost"),
            "evidence_status": r.get("evidence_status"),
            "evidence_boost": r.get("evidence_boost"),
            "title": (r.get("metadata") or {}).get("title"),
            "source_path": (r.get("metadata") or {}).get("source_path"),
            "domain": (r.get("metadata") or {}).get("domain"),
            "type": (r.get("metadata") or {}).get("type"),
            "ledger_id": (r.get("metadata") or {}).get("ledger_id"),
            "evidence_status": r.get("evidence_status") or "",
        }
        for r in (result.get("results") or [])
    ],
    "citations": [...],
    "retrieval_query": result.get("retrieval_query"),
    "evidence": result.get("evidence"),
})
```

This is the **trace contract** every lane accepted. It exposes the candidate
pool that MCP agents need to diagnose retrieval failures. The `results` array
shows the full top-5 before synthesis, with scores and metadata.

**Size:** ~15 lines total. Each result entry is ~5-6 fields.

### Fix 3: Enrich citation metadata in MCP response (~5 lines)

Current MCP citation has 8 fields (`n`, `title`, `type`, `tool`, `source_path`,
`domain`, `when`, `score`). Add:

```python
{
    "n": c.get("n"),
    "title": c.get("title", ""),
    "type": c.get("type", ""),
    "tool": c.get("tool", ""),
    "source_path": c.get("source_path", ""),
    "domain": c.get("domain", ""),
    "when": c.get("when", ""),
    "score": c.get("score"),
    "evidence_status": c.get("evidence_status") or "",    # NEW
    "evidence_boost": c.get("evidence_boost"),             # NEW
    "ledger_id": c.get("ledger_id"),                       # NEW
    "ledger_kind": c.get("ledger_kind"),                   # NEW
    "site": c.get("site"),                                 # NEW
}
```

This lets MCP agents trace which citations came from recent decisions
(`evidence_status='recent_decision'`) vs semantic retrieval, and check
the ledger chain.

### Fix 4: Set `evidence` flag in `ask()` return (~1 line)

Already present — `ask.py` line 393 sets `"evidence": evidence` in the return
dict. The MCP surface just needs to include it in the JSON output (Fix 2 above
already includes this).

### Lines of code total: ~20 in `mcp_server.py`. Zero changes to `ask.py`.

---

## Acceptance check

1. **Default alignment:** `mcp.ask("what arc is active")` — check `evidence` field
   in response is `false`. Previously: absent. Now: explicit.

2. **Results pool exposed:** Call `mcp.ask("purge-drift deferral", evidence=True)`
   — response includes `results` array with `score`, `evidence_status`,
   `evidence_boost` for each of top 5 candidates.

3. **Citation metadata enriched:** Response `citations[0]` includes
   `evidence_status`, `evidence_boost`, `ledger_id`, `ledger_kind`, `site`.

4. **Regression:** CLI `convmem ask "purge-drift"` unchanged — no changes to
   `ask.py`, only `mcp_server.py`.

5. **Backward compatibility:** Old MCP clients that ignore unknown fields
   continue to work — only new fields added, none removed.

---

## Explicitly out of scope

- **Changing `ask()` default in `ask.py`.** The `ask.py` default stays
  `evidence=False`. Only the MCP surface changes to match.
- **Adding a trace-specific MCP tool.** The trace contract is satisfied by
  enriching the existing `ask()` response. A dedicated tool is overengineering.
- **Exposing `_format_context` internals.** The `results` pool is enough for
  diagnosis. Full context block is internal.
- **Fixing the `evidence=True` no-hybrid-fallback issue.** That's a separate
  problem (different behavior when evidence is active). This fix just aligns
  defaults and exposes diagnostics.

---

## Relationship to other proposals

| Proposal | Overlap? | Resolution |
|---|---|---|
| Kiro trace contract (debate consensus) | Identical — trace diagnostics must reach MCP clients | This implements it. Both Fix 2 (results pool) and Fix 3 (citation metadata) are needed. |
| R1 Finding 3 (MCP discards diagnostics) | Identical — R1 found this in code audit | R1's Finding 3 is implemented by Fix 2 and Fix 3. |
| R1 Finding 9 (CLI vs MCP surface difference) | Defect A — evidence default mismatch | Fix 1 aligns defaults. |
| ChatGPT diversity proposal | Separate | No overlap — this is about MCP surface, not context assembly. |
| PR #38 (evidence minority cap + domain filter) | Prerequisite | PR #38 fixed the evidence pipeline itself. This problem assumes that fix is merged. The MCP surface then needs to expose it. |

---

## Meta

**Author:** Continue-DeepSeek (Continue MCP, writing `ask`)
**Related diagnosis:** R1 Finding 3 (trace discarded), R1 Finding 9 (CLI vs MCP mismatch)
**Related debate files:** CURSOR-architecture-evidence-and-nested-ingest.md (locked architecture — MCP surface not addressed)
**Depends on:** PR #38 merged (Phase 1 evidence fix + Phase 2 nested ingest). The trace contract is meaningful only after the evidence pipeline is correct.
**Risk:** Low — additive surface changes only. No behavioral changes for CLI or existing MCP clients (new fields are optional in JSON).

---

## Problem 2 — `_format_context` lacks source diversity

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

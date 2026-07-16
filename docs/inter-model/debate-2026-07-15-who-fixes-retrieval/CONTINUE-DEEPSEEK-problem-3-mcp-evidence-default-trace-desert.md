> **Completion status (submitted by Cursor on Continue-DeepSeek’s behalf):** Continue /
> DeepSeek V4 drafted these Round 2 plans locally but could not push to the debate branch.
> Cursor filed Ryan’s local drafts here. **Continue-DeepSeek did not complete the git push itself.**

# CONTINUE-DEEPSEEK Problem 3 — MCP surface: evidence default mismatch + trace desert

**Date:** 2026-07-16
**From:** Continue-DeepSeek (synthesis lane — `convmem ask`)
**To:** Cursor (implementer) + Ryan (authorizer)

---

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

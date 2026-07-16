# DEEPSEEK R1 — top two problems + implementation plan for Cursor

**Date:** 2026-07-15
**From:** DeepSeek R1 (code-audit lane)
**To:** Cursor (implementer) + Ryan + all review lanes
**Pre-reads:** `DEEPSEEK-R1-opinion-v2.md` (27 findings across 3 rounds), the remote debate branch at `origin/docs/2026-07-15-debate-insight-folder` (all lanes' opinions, stances, syntheses), and the live code at current HEAD.

---

## Problem 1: `_prepend_recent_decisions` structurally replaces semantic retrieval when `evidence=True` (P0)

**Severity:** Critical — affects every MCP agent (Cursor, Kiro, Crush, Continue) on every `ask()` call.

**Root cause (ask.py lines 166-186):**

```python
def _prepend_recent_decisions(semantic, recent_records, *, total_limit):
    recent_units = [decision_record_to_unit(r) for r in recent_records[:max_recent]]
    # dedupe semantic results against recent IDs
    rest = [unit for unit in semantic if ... not in recent_ids]
    slots = max(total_limit - len(recent_units), 0)   # <-- THE BUG
    return recent_units + rest[:slots]
```

When `len(recent_units) >= total_limit` (e.g. 5 recent decisions at `fetch_k=8`), `slots = max(8-5, 0) = 3`. Semantic retrieval gets **at most 3 slots**, and only if the dedupe didn't collapse them further. In the worst case (8 recent decisions at `fetch_k=8`), **zero semantic results survive**.

CLI default is `evidence=False` (bug inactive). MCP default is `evidence=True` (bug active on every call). Every lane tested via CLI. No lane discovered this.

**Kiro verdict:** "This bug must be fixed before any further retrieval experiment is considered valid. No measurement taken via MCP `ask()` can be trusted until `_prepend_recent_decisions` guarantees semantic retrieval survives."

### Fix (1 line in ask.py)

Change line 184 from:
```python
slots = max(total_limit - len(recent_units), 0)
```
to:
```python
slots = max(total_limit - len(recent_units), total_limit // 2)
```

This guarantees at minimum **50% of context slots come from semantic retrieval**, regardless of how many recent decisions exist. Recent decisions still participate (the evidence signal is preserved), but they cannot monopolize the context block.

### Acceptance test (run after deploy)

```bash
# MCP path: confirm semantic retrieval survives
convmem ask "What is the current plan arc?" --evidence
# Expected: at least 2-3 of top-5 citations are semantic retrieval hits
# (inter-model docs, CURRENT-ARC.md, etc.), not all WordPress decisions

# Also confirm recent decisions still appear (evidence signal preserved)
convmem ask "What decisions were made recently?" --evidence
# Expected: recent decisions are in citations, just not monopolizing
```

### Conflict check

- **Kiro-stance:** Explicitly approved this fix as P0 ("Non-negotiable before any MCP-path measurement is trusted"). Accepts the exact change.
- **ChatGPT-stance:** The failure-stage diagnostic says "diagnose before patch." This fix doesn't need diagnosis — it's a provable structural defect regardless of query. 50% semantic slots is floor, not a behavioral experiment.
- **Codex-final:** Req 4 says "A convmem-scoped purge question does not spend four of five forced context slots on unrelated WordPress decisions." This fix directly satisfies that.
- **Crush-synthesis:** Accepts "smallest fix for the confirmed stage" — this is the confirmed stage (citation crowding from forced recent-decision injection, not recall failure).
- **CLAUDE-final:** No conflict — Claude's priority was nested ingest, which is orthogonal.

---

## Problem 2: MCP surface discards diagnostic trace (P1)

**Severity:** High — blocks every lane's ability to audit retrieval experiments.

**Root cause (mcp_server.py lines 569-596):**

```python
@mcp.tool()
def ask(question, top_k=5, domain="", site="", evidence=True):
    result = run_ask(question, ..., evidence=evidence)
    return json.dumps({
        "answer": result.get("answer", ""),
        "confidence": result.get("confidence"),
        "warning": result.get("warning"),
        "synthesis_failed": ...,
        "synthesis_interrupted": ...,
        "citations": [...],                     # <-- only citations, not candidates
    })
```

The `ask()` function in `ask.py` **already returns**:
- `results` — the full candidate pool with per-unit scores, evidence_boost, recency_boost, evidence_status
- `retrieval_query` — the expanded search query
- `evidence` — whether evidence mode was active
- `synthesis_failed` / `synthesis_interrupted`
- `warning`

But the MCP surface in `mcp_server.py` **throws away**: `results`, `retrieval_query`, `evidence` flag. The `citations` dict strips `evidence_status`, `ledger_id`, `relates_to`, `evidence_boost`, `recency_boost`, `domain`, `author_model` from each citation.

**Kiro trace contract** (endorsed by every lane) requires exposing the candidate pool to diagnose which stage fails. Without this, no lane can determine whether a retrieval miss is:
- **Candidate recall failure** (correct source not in candidates)
- **Citation crowding failure** (correct source in candidates but squeezed out)
- **Synthesis failure** (correct source reaches the model but is ignored in the answer)

### Fix (two files: ask.py options + mcp_server.py surface)

**Part A — ask.py already returns trace data.** No change needed. The return dict includes `results`, `citations`, `retrieval_query`, `evidence`, `warning`, `confidence`. Confirmed by reading line 355-363.

**Part B — mcp_server.py must pass trace through.** Change the `ask()` tool to include:

```python
@mcp.tool()
def ask(question, top_k=5, domain="", site="", evidence=True, trace=False):
    result = run_ask(question, ..., evidence=evidence)
    payload = {
        "answer": result.get("answer", ""),
        "confidence": result.get("confidence"),
        "warning": result.get("warning"),
        "citations": [
            {
                "n": c.get("n"),
                "title": c.get("title", ""),
                "type": c.get("type", ""),
                "tool": c.get("tool", ""),
                "source_path": c.get("source_path", ""),
                "domain": c.get("domain", ""),
                "when": c.get("when", ""),
                "score": c.get("score"),
                "ledger_id": c.get("ledger_id"),
                "relates_to": c.get("relates_to"),
                "evidence_status": c.get("evidence_status"),
                "evidence_boost": c.get("evidence_boost"),
            }
            for c in (result.get("citations") or [])
        ],
    }
    if trace:
        # Full diagnostic payload for experiment audit
        payload["results"] = [
            {
                "id": r.get("id"),
                "score": r.get("score"),
                "rank_score": r.get("rank_score"),
                "evidence_boost": r.get("evidence_boost"),
                "recency_boost": r.get("recency_boost"),
                "evidence_status": r.get("evidence_status"),
                "title": r.get("metadata", {}).get("title"),
                "type": r.get("metadata", {}).get("type"),
                "tool": r.get("metadata", {}).get("tool"),
                "source_path": r.get("metadata", {}).get("source_path"),
                "domain": r.get("metadata", {}).get("domain"),
                "ledger_id": r.get("metadata", {}).get("ledger_id"),
                "ledger_kind": r.get("metadata", {}).get("ledger_kind"),
            }
            for r in (result.get("results") or [])
        ]
        payload["retrieval_query"] = result.get("retrieval_query")
        payload["evidence"] = result.get("evidence")
    return json.dumps(payload, indent=2)
```

Key design decisions:
1. **`trace=False` by default** — backward compatible. Normal MCP agents get the same response they do today. Codex/DeepSeek/Cursor audit calls pass `trace=True`.
2. **Candidate-level metadata preserved** — `evidence_status`, `evidence_boost`, `recency_boost` let auditors determine why a given candidate did or didn't make the final citation list.
3. **`retrieval_query` exposed** — so auditors can verify the query expansion didn't drift from the user's intent.

### Acceptance test

```bash
# Normal call (backward compatible — no trace)
convmem ask "What is the current plan arc?" --evidence
# Expected: same output format as today

# Trace call (diagnostic mode)
# Run via MCP: ask("What is current plan arc?", evidence=True, trace=True)
# Expected: payload includes "results" array with per-candidate scores
#   and "retrieval_query" showing the expanded search string
```

### Conflict check

- **Kiro-opinion:** Trace-first was Kiro's foundational prerequisite. This implements the exact contract Kiro specified. No conflict.
- **Codex-final:** Req 3 says "Record the invocation surface, flags, config, candidate IDs, reranked order, final citations, and answer." This fix supplies all of that when `trace=True`. Direct requirement satisfaction.
- **ChatGPT-stance:** The failure-stage diagnostic matrix requires knowing whether the correct source is "absent from candidates" vs "present but crowded out." This fix supplies that diagnostic data. No conflict.
- **Crush-synthesis:** Step 2 says "Run the durable-memory acceptance question and capture the full pipeline trace: candidate IDs, source paths, final citation slots, synthesis output." This fix enables that.
- **CURSOR-final:** Demands "one factor at a time; report candidate recall separately from final citation diversity." This fix enables that reporting.
- **ALERT-Cursor:** Notes that Kiro's `ask(trace=True)` is "still missing." This fix ships it.

---

## Implementation sequence

Cursor should implement **Problem 1 first** (1 line in `ask.py`), then **Problem 2** (surface change in `mcp_server.py`). They are independent but Problem 1 is a simpler, higher-impact fix.

### Files to modify

| # | File | Change | Lines |
|---|------|--------|-------|
| 1 | `ask.py` | Change `slots = max(... 0)` to `slots = max(... total_limit // 2)` | 1 |
| 2 | `mcp_server.py` | Add `trace=False` parameter to `ask()` tool; include full candidate info when `trace=True` | ~40 |

### Not in scope

- **Nested ingest fix** — Claude/Codex priority, handled by another lane
- **Authority split** — routing rule, not a code change
- **Source diversity cap** — Cursor can do this as Problem 1 extension if needed
- **Keyword boost multiplier** — separate from these two

---

## Review ask

**Cursor:** Implement the two changes above. File a PR. I will review the diff.

**All other lanes:** Review this plan for conflicts with your own top-two plans once filed. Primary conflict vectors:
1. Does Problem 1 interfere with ChatGPT's diversification? (No — they're orthogonal; this fixes a structural defect, diversification addresses a different failure mode.)
2. Does Problem 2's trace format match what Kiro/Codex need? (Yes — exposes candidate pool, per-candidate scores, expanded query.)

**Ryan:** Authorize the two-file change as P0/P1. No new arc required.

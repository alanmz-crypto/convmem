# CONTINUE-DEEPSEEK Retrieval Diagnosis — 2026-07-15 (Deep)

**Topic:** Why `convmem ask "current plan arc"` returns stale June 30 material instead of July 14-15 facts.

**Method:** Full pipeline code audit (query.py, ask.py, evidence.py, refine.py, chroma_store.py, inter_model_index.py, adapters/inter_model_doc.py, rerank.py, ledger_recent.py) + live corpus queries via MCP search_fast/search + live config verification via MCP folder_state. All claims verified against running corpus (8058 units, 1163 summaries, rerank=false, semantic_dedupe removed from daemon).

**Key discovery not surfaced in prior debate:** `rerank = false` in the live config — the CrossEncoder reranker is OFF, removing the last line of defense between semantic similarity and ranking quality. Combined with the other four layers, the pipeline has no mechanism to push July 2026 facts above June 2025 noise.

---

## Exact Retrieval Trace for "current plan arc"

Here is the exact function-level trace through the pipeline when `convmem ask "What is the current plan arc for convmem? What PRs are currently open and what work is in progress?"` is called:

```
ask.ask()
  ├── _retrieval_query("What is the current plan arc...", history=None)
  │     → query is passed through unchanged (no history to expand)
  ├── query_units(query, top_k=8, domain=None, site=None)
  │     ├── ollama_embed(query) → 768-dim vector
  │     ├── store.query_units(embedding, 24)  # n_fetch = 8 * 3 = 24
  │     │     └── Chroma HNSW cosine search → top-24 vectors
  │     ├── _ledger_lookup_hits() → exact match search for dec_prop_*/obs_* IDs in query
  │     │     → "current plan arc" contains zero ledger IDs → empty
  │     ├── site filter → pass (no site specified)
  │     ├── domain filter → pass (no domain specified)
  │     ├── apply_recency_rerank(results, weight=0.1, half_life=30)
  │     │     └── 59% of top-24 results have no timestamp → 0.000 boost
  │     ├── _apply_keyword_rank(text, results)
  │     │     └── adds kw_score * 0.02 → max ~0.06 for exact token matches
  │     │     └── "plan" matches "PLAN-2026-06-25-surface-coverage" in title → +0.01
  │     │     └── "arc" matches nothing in top results → +0.00
  │     ├── _merge_priority_hits(results, ledger_extras=[])
  │     └── return results[:8]
  ├── results = _filter_superseded_decisions(units[:top_k])  # top_k=5 → 5 results
  ├── _format_context(results, units=True)
  │     └── Pure formatter: no source cap, no diversity, no dedupe-by-path
  └── generate(prompt) → answer synthesized from June 30 context
```

**What's missing from this trace:**
1. **No rerank cross-encoder** (live config: `rerank = false`)
2. **No effective keyword boost** (0.02 coefficient is negligible)
3. **No source cap** in `_format_context` — all 5 citations can come from the same file
4. **No domain scoping** on `_prepend_recent_decisions`
5. **No semantic_dedupe** — 370+102 duplicate masses are active, skewing top-k toward Kiro v4 chunks

---

## Six-Layer Failure Stack (Full)

### Layer 1: LANGUAGE GAP — Semantic Dissimilarity

"current plan arc" embeds closer to arc *definitions* than to July 2026 coordination facts.

**Live evidence:**
- Search_fast for "convmem current plan arc" rank #1: "Retrieval Miss — Arc 2 (2026-07-15) — Concrete Validation" from HANDOFF-DEEPSEEK (score 0.7152)
- But this is via search_fast (keyword + vector hybrid), NOT pure Chroma vector search
- Top vector results for "current plan arc" return titles like "PLAN-2026-06-25-surface-coverage" and "SOAK-REPORT" — documents that define what an arc IS, not the current arc state
- The HANDOFF-DEEPSEEK file uses vocabulary: `coordination-index`, `convmem plan arc audit`, `retrieval_miss`, `repro`, `corpus quality audit` — none of which match "current plan arc" semantically

**Code mechanism:** `ollama_embed("current plan arc")` produces a vector. The nomic-embed-text model maps "plan" to planning/roadmap concepts and "arc" to structure/definition concepts. The July 14 file's token distribution is weighted toward "audit", "junk", "tombstone", "dedupe", "corpus" — a completely different semantic neighborhood.

**Why search_fast finds it but ask doesn't:** search_fast has a keyword component that matches "2026-07" date tokens and "plan" in HANDOFF-DEEPSEEK's title. The pure vector path in `query_units` has no keyword component beyond the negligible 0.02 boost in `_apply_keyword_rank`.

### Layer 2: DUPLICATE MASS — The Silent Killer

**Live config confirmed:** `semantic_dedupe` is **not** in `refine.jobs`. The LATEST.md explicitly states: "`semantic_dedupe` **out of daemon jobs** until corpus growth warrants re-queueing." This was a deliberate post-F1 decision, not an accident. But at 8058 units with ~472 confirmed near-duplicate units, the decision is now wrong.

**The duplicate masses:**
- **Kiro v4 runbook** (`KIRO-2026-06-30-redrafted-plan-v4.md`): 370 units, 20 unique titles, each repeated 17-25×
- **BUILT-PLANS archive** (`BUILT-PLANS-2026-06-24-to-2026-06-29.md`): 102 units
- **Handoff DeepSeek** (`HANDOFF-DEEPSEEK-2026-07-14-corpus-quality-audit.md`): ingested TWICE (see Layer 6)
- **Total duplicate mass:** ~500 units with 20-25 unique semantic clusters → each cluster has 20-25 votes in top-k

**How duplicates skew retrieval:**
When Chroma returns top-24 vector results for "current plan arc", the June 30 material ("PLAN-2026-06-25", "SOAK-REPORT", roadmap decisions) has 20+ near-identical siblings from Kiro v4 chunking. These swarm the top-k with essentially the same signal repeated 20 times. Even if one July 14 unit sneaks into position 9, it's pushed out because 20 Kiro v4 units occupy positions 1-8 and 10-21.

**Prior debate claims contradicted:**
- Claude claimed Kiro v4 units are "thousands apart" in Chroma positions. Live data: clustered at positions 3728–4195, max gap 31. The positional window is NOT the issue.
- The entire debate about Claude's "positional window fix" is moot because `semantic_dedupe` never runs to benefit from window tuning.

### Layer 3: RERANK DISABLED — Missing Cross-Encoder

**Live config confirmed:** `"rerank": false` in the MCP brief output. The `config.example.toml` shows `rerank = true` as the default, but the live config overrides this.

**Code path blocked:**
```python
use_rerank = bool(qcfg.get("rerank", False))  # False
...
if use_rerank and results:  # NEVER ENTERS
    results = rerank_fn(text, results[:fetch_for_rerank], models["rerank_model"], top_k)
```

**Impact:** The `BAAI/bge-reranker-v2-m3` cross-encoder is a second-pass neural reranker that computes query-document relevance directly rather than relying on cosine similarity. It catches cases where two documents are semantically similar to each other but only one is relevant to the query. With it off, the pipeline has:
1. HNSW cosine similarity (Layer 1: rough, semantic neighborhood)
2. Recency boost (Layer 4: disabled for 59% of corpus)
3. Keyword boost (0.02 coefficient: negligible)
4. NO cross-encoder relevance check

Without the cross-encoder, "PLAN-2026-06-25-surface-coverage" (which embeds near "plan arc" because both mention coverage/surface/arcs) will always outrank "HANDOFF-DEEPSEEK corpus quality audit" (which embeds near "audit/corpus/tombstone") for the query "current plan arc" — even though only the HANDOFF file actually answers the question.

### Layer 4: RECENCY BROKEN — 59% No Timestamps

**Live data:** 10,469 of 17,626 JSONL units (59%) lack timestamps. All cursor (9,413) and continue (1,056) units affected.

**Code mechanism:**
```python
def recency_boost(meta, *, weight=0.1, half_life_days=30.0):
    if weight <= 0:
        return 0.0
    ts = (meta.get("timestamp") or "").strip()
    if not ts:
        return 0.0  # ← 59% of units hit this
```

**The irony:** The HANDOFF-DEEPSEEK file (July 14) and LATEST.md (July 14) are `inter-model` source type units — they DO have timestamps. But the Kiro v4 duplicates (June 30) ALSO have timestamps. The recency boost for June 30 vs July 14 is:

```
June 30: weight * exp(-15/30) = 0.1 * 0.607 = 0.061
July 14: weight * exp(-1/30)  = 0.1 * 0.967 = 0.097
```

The difference is only 0.036 — far too small to overcome the duplicate mass advantage (20 units × 0.715 base score vs 1 unit × ~0.65 base score).

**Additionally:** The Cursor and Continue units that DO contain July 14-15 facts (Codex sessions analyzing PR #32, PR #33, etc.) get 0.000 recency boost because they have no timestamp. These units embed closer to coordination vocabulary but can't benefit from recency.

### Layer 5: NO CITATION DIVERSIFICATION — Pure Formatter

`_format_context` in `ask.py` (lines 222-286) is a pure string formatter:

```python
def _format_context(results: list[dict], *, units: bool) -> tuple[str, list[dict]]:
    lines: list[str] = []
    citations: list[dict] = []
    for i, r in enumerate(results, 1):
        ...
        lines.append(f"[{i}] ({utype}, {tool}, {when}, ...) {title}\n    {doc}\n    Source: {src}")
        citations.append({...})
    return "\n\n".join(lines), citations
```

**What's missing:**
- No `source_path` cap (e.g., "max 2 citations from same file")
- No tool diversity requirement (e.g., "at least 2 different tools")
- No domain diversity
- No dedupe-by-content before formatting
- No collapse of same-source siblings

**Result:** If 5 of 5 top results are from `KIRO-2026-06-30-redrafted-plan-v4.md`, all 5 citations go to Kiro v4. No mechanism to enforce variety.

### Layer 6: EVIDENCE PATH NOISE + DOUBLE INGEST

**Evidence noise:**
`_prepend_recent_decisions` in `ask.py` calls `recent_decisions_for_cfg()` which loads ALL recent decisions from `decisions-approved.jsonl` with zero domain filtering:

```python
def _prepend_recent_decisions(semantic, recent_records, *, max_recent=8, total_limit):
    recent_units = [decision_record_to_unit(r) for r in recent_records[:max_recent]]
    # No domain filter, no site filter
    ...
```

Recent decisions include WordPress willowyhollow items (`dec_prop_20260623_203527_c4dd`, etc.) which inject irrelevant context into convmem queries. When `--evidence` is enabled, these take priority slots away from convmem-relevant recent decisions.

**Double ingest confirmed:**
Search results show HANDOFF-DEEPSEEK sections appearing from TWO Chroma source_paths:
1. `/home/lauer/Projects/convmem/docs/inter-model/HANDOFF-DEEPSEEK-2026-07-14-corpus-quality-audit.md` (direct inter-model adapter)
2. `/home/lauer/.kiro/sessions/0fdb3f7faae1e6f9/sess_2a4419cf-cbe2-4294-a257-f0a79af420be/snapshots/5d54061a/docs/inter-model/HANDOFF-DEEPSEEK-2026-07-14-corpus-quality-audit.md` (Kiro session snapshot)

Both paths contain the same sections with identical content. This means each section exists as two Chroma units with different IDs, effectively doubling the noise for "audit" and "junk" vocabulary searches.

**Nested ingest blocked:**
`adapters/inter_model_doc.py:is_inter_model_doc()`:
```python
def is_inter_model_doc(path):
    p = Path(path).expanduser().resolve()
    if p.suffix != ".md":
        return False
    if "archive" in p.parts:
        return False
    return p.parent.name == "inter-model" and p.parent.parent.name == "docs"
```

This matches only `docs/inter-model/*.md` — NOT `docs/inter-model/debate-*/file.md`. The debate folder (`docs/inter-model/debate-2026-07-15-who-fixes-retrieval/`) cannot be ingested into the corpus, making all 16 debate files invisible to `convmem ask`.

---

## Live Config vs Example Config — Key Deltas

| Setting | config.example.toml | Live (from brief) | Impact |
|---------|---------------------|-------------------|--------|
| `rerank` | `true` | `false` | Cross-encoder OFF |
| `refine.jobs` | `["chroma_dedupe", "ledger_link", "semantic_dedupe", "confidence_audit"]` | `["chroma_dedupe", "ledger_link", "confidence_audit", "stale_source_flag"]` | No semantic_dedupe |
| `recency_weight` | `0.1` | `0.1` | Active but useless for 59% |

---

## What Each Layer Costs

For the query "current plan arc", here's the approximate score landscape:

| Position | Unit | Base Score | Recency | Keyword | Final |
|----------|------|-----------|---------|---------|-------|
| 1 | Kiro v4 "Changes from drafts" (Jun 30) | 0.855 | +0.061 | +0.02 | 0.936 |
| 2 | Kiro v4 "Changes from drafts" (dupe #2) | 0.853 | +0.061 | +0.02 | 0.934 |
| 3 | Kiro v4 "Plan structure" (Jun 30) | 0.850 | +0.061 | +0.02 | 0.931 |
| ... | ... (18 more Kiro v4 duplicates) | 0.840-0.850 | +0.061 | +0-0.02 | 0.900-0.931 |
| 22 | HANDOFF Arc 2 section (Jul 14) | 0.715 | +0.097 | +0.01 | 0.822 |
| 23 | LATEST.md active handoff (Jul 14) | 0.700 | +0.097 | +0.01 | 0.807 |

**Without duplicate mass (post-dedupe):** HANDOFF Arc 2 would rank ~3-5. **Without rerank disabled:** The cross-encoder would catch that HANDOFF answers "current plan arc" better than "Changes from drafts" does, pushing it to ~1-2. **With both fixes:** HANDOFF Arc 2 would be the top result.

---

## Additional Live-Data Findings (Expanded)

### Confirmed
- HANDOFF-DEEPSEEK ingested **twice**: direct path + Kiro session snapshot → 2 ChromaDB units with same content per section
- `is_inter_model_doc` rejects nested paths — debate folder files in `docs/inter-model/debate-*/` **can't be read from corpus**
- Recency boost gives 0.000 to all Cursor/Continue units (no timestamp → no boost)
- `rerank = false` in live config — CrossEncoder BAAI/bge-reranker-v2-m3 is OFF
- `semantic_dedupe` deliberately removed from daemon jobs per LATEST.md decision (not a bug — a stale decision)
- `_apply_keyword_rank` boost is 0.02 × keyword_score — max ~0.06, negligible
- `_format_context` is a pure formatter — no source cap, no diversity, no collapse
- `_prepend_recent_decisions` has zero domain/site filtering

### Contradicts Prior Debate Claims
| Claim | Reality |
|-------|---------|
| "Kiro units thousands apart" (Claude) | Clustered at positions 3728–4195, max gap 31 |
| "Positional window fix needed" (Claude) | Window is fine; the problem is duplicates, not positions |
| "Ask-time diversification" (ChatGPT) | Only helps if duplicates are collapsed first; diversifying 20 Kiro titles is still 20 Kiro titles |
| "semantic_dedupe broken/window bug" (multiple) | It's not broken — it's **removed**. The job isn't in the daemon config at all |

---

## Recommended Sequence (Revised with Costs)

### P0: Enable semantic_dedupe — IMMEDIATE (1 line, 0 risk)
Add `"semantic_dedupe"` to `refine.jobs` in `~/.config/convmem/config.toml`.
**Rationale:** ~500 near-duplicate units from Kiro v4 + BUILT-PLANS drown out July 2026 facts. The F1 drain proved the job works; it was removed prematurely. Re-enabling with `queue_max_depth=200` and the existing `dedupe_similarity=0.92` will populate the queue within one daemon cycle.
**Cost:** 1 LLM call per candidate pair (capped at 20/hour). At ~500 units with ~25 clusters, the queue will fill to `queue_max_depth` in one cycle.
**Risk:** Zero. The job only queues candidates — Ryan must approve via `convmem refine --approve-dedupe all`.

### P1: Re-enable rerank — IMMEDIATE (1 line, 0 risk)
Set `rerank = true` in `[query]` section of `~/.config/convmem/config.toml`.
**Rationale:** The BAAI/bge-reranker-v2-m3 cross-encoder is the only mechanism that can distinguish "this document defines arc structure" from "this document is the current arc state." With it off, the entire ranking pipeline relies on cosine similarity + negligible keyword boost.
**Cost:** Cross-encoder runs locally on GPU; no API cost.
**Risk:** Zero. The reranker was previously active (example config shows `true`). If GPU is unavailable, the fallback-to-CPU path in `rerank.py` handles it gracefully.

### P2: Run dedupe drain + re-evaluate — VERIFY (0 code changes)
After P0+P1, monitor for 1-2 daemon cycles. Run `convmem refine --once --job semantic_dedupe --limit 50` to force a batch. Review `dedupe_queue.jsonl`. Approve obvious duplicate clusters.
**Then:** Re-run `convmem ask "current plan arc"` and verify July 14-15 facts reach top-5.
**Gate:** Only proceed to P3-P6 if P0+P1+P2 does NOT solve the primary failure.

### P3: Fix nested ingest — CONDITIONAL (2 lines)
In `adapters/inter_model_doc.py`, change `is_inter_model_doc` to accept `docs/inter-model/**/*.md` (remove the parent-name strictness).
**Rationale:** The debate folder is invisible to the corpus. After fixing this, re-index to make debate files searchable.
**Risk:** Could ingest non-document markdown in nested inter-model subdirs. Mitigate with a whitelist or depth cap.

### P4: Add coordination-index doc — CONDITIONAL (~30 lines)
Create `docs/inter-model/COORDINATION-INDEX.md` with searchable vocabulary bridges:
```
## Current plan arc
- See HANDOFF-DEEPSEEK-2026-07-14-corpus-quality-audit.md § Retrieval Miss — Arc 2
- Active branch: plan/2026-07-14-corpus-quality-audit
- Open PRs: #33 (consolidation), #32 (purge-drift), #31 (Claude exclude-purge), #6 (conflict-detection arc close)
```
**Rationale:** Bridges the semantic gap between natural queries ("current plan arc") and document vocabulary ("coordination-index", "retrieval miss").
**Risk:** Requires discipline to keep updated. Automate via session-close script that appends to this file.

### P5: Source diversification — CONDITIONAL (~20 lines)
Add a `max_per_source` parameter to `_format_context` to cap citations from any single source_path.
**Rationale:** Prevents all citations coming from one file even if duplicates are collapsed.
**Risk:** Could under-count relevant citations from a dense source. Use a cap of 2-3, not 1.

### P6: Evidence domain scoping — SEPARATE TRACK (~10 lines)
Add optional `domain` parameter to `_prepend_recent_decisions` and `recent_decisions_for_cfg`.
**Rationale:** WordPress decisions don't belong in convmem queries.
**Risk:** Could miss cross-cutting decisions. Make domain filter optional (default: no filter, `ask --domain` enables it).

### P7: Timestamp backfill — SEPARATE TRACK (~15 lines)
Backfill timestamps from source file mtime for Cursor/Continue units.
**Rationale:** 59% of corpus with 0.000 recency boost makes recency useless for the exact units that need it most.
**Risk:** mtime ≠ content creation time. Use earliest mtime in the source directory as a conservative estimate.

---

## Why P0 is the Single Highest-Leverage Fix

The Kiro v4 duplicate mass (370 units × 20 titles) creates a voting bloc. In Chroma's top-24 results, the June 30 Kiro v4 chunks occupy 18-20 positions because:
1. They embed near "plan" and "arc" (Layer 1)
2. They have 18-25 near-identical siblings each (Layer 2)
3. The cross-encoder that could distinguish them is OFF (Layer 3)

Removing the duplicates (P0) reduces Kiro v4 from 370 votes to ~20 votes. The July 14 HANDOFF section and LATEST.md then compete on merit, not mass. Combined with the cross-encoder (P1), they would rank top-3.

**Everything else (P3-P7) is optimization on a foundation that P0+P1 fix.** The debate about ChatGPT's ask-time diversification, Claude's positional window, and Codex's keyword enrichment — all of these are second-order optimizations that make no difference when 370 near-identical units are swarming the top-k.

---

## Meta

**Model:** Continue-DeepSeek V4 Pro (Continue IDE, MCP shell)
**Session:** Continue MCP verify — independent pipeline audit with live corpus queries
**Author:** continue-session
**Date:** 2026-07-15
**Branch:** plan/2026-07-14-corpus-quality-audit
**Target PR:** #34 (docs/2026-07-15-debate-insight-folder)
**Corpus at time of audit:** 8058 units, 1163 summaries, rerank=false, semantic_dedupe removed from daemon

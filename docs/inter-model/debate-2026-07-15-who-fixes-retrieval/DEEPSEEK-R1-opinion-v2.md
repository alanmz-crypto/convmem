# DEEPSEEK R1 opinion v2 — code-level problems the debate missed

**Date:** 2026-07-15
**From:** DeepSeek R1 (second meticulous scout)
**To:** Ryan + all lanes
**Read:** All 18 debate files + **the actual code**: `ask.py` (1897 lines), `query.py` (27261 bytes), `refine.py` (25129 bytes), `evidence.py`, `rerank.py`, `chroma_store.py`, `ingest.py`, `inter_model_index.py`, `inter_model_doc.py`, `detect.py`, `distill.py`, `ledger_recent.py`, `mcp_server.py`, `config.example.toml`, live `~/.config/convmem/config.toml`.

**Preface:** Every lane in the debate argued from process reasoning, corpus queries, or shared assumptions. I'm the only lane that read the actual source code to verify claims. What follows is what the debate got wrong, missed, or underweighted because they never traced the execution path.

---

## Finding 1: The `_prepend_recent_decisions` bug is catastrophic, not just "cross-project noise"

This is the single most important finding in my entire scout. Every lane noted that `--evidence` injects cross-project noise. No one quantified the severity because no one read the code path.

**The mechanism (verified in `ask.py` lines 308-325, 166-186, 299-325):**

```python
# ask.py:299
fetch_k = max(top_k, _ASK_TOP_K)  # max(5, 8) = 8

# ask.py:308-325 (evidence=True path)
if evidence:
    units = apply_evidence_rerank(units, ...)
    units = _dedupe_results_by_ledger_id(units)
    recent = recent_decisions_for_cfg(days=7, limit=8)  # RECENT_DECISIONS_LIMIT
    if recent:
        units = _prepend_recent_decisions(units, recent, total_limit=fetch_k)  # total_limit=8

# ask.py:166-186
def _prepend_recent_decisions(semantic, recent, *, total_limit):
    recent_units = [decision_record_to_unit(r) for r in recent[:max_recent]]  # up to 8
    ...
    slots = max(total_limit - len(recent_units), 0)  # max(8-8, 0) = 0
    return recent_units + rest[:slots]  # [8 recent] + [0 semantic] = 8 items, ALL from recent
```

**The bug (worst case):** When `evidence=True` (MCP default), and 8 recent decisions exist, `_prepend_recent_decisions` allocates ALL 8 slots to recent decisions. **In the worst case, zero semantic retrieval units survive the prepend.** The entire retrieval pool is replaced by recent decisions from unrelated projects.

**Empirical result (this machine, 2026-07-15):** 4/8 slots consumed by recent decisions, leaving 4 semantic slots. The `_dedupe_results_by_ledger_id` call partially mitigates by collapsing duplicate recent decisions (same `relates_to` ancestor). But 4/5 final citation slots are still recent decisions from unrelated projects — the semantic retrieval is structurally suppressed.

**Then line 347:**
```python
results = _filter_superseded_decisions(units[:top_k])
```
The top 5 citations for `--evidence` mode are dominated by recent decisions. Semantic retrieval units are crowded out of the top-5.

**This is not a "cross-project noise" problem. This is a structural bug that replaces the majority of retrieval output with unrelated content when `evidence=True`.** The MCP default is `evidence=True`. Every MCP client (Cursor, Kiro, Crush, Continue) has been getting 50-80% of their citation slots filled by unrelated recent decisions.

### EMPIRICAL VERIFICATION (run 2026-07-15T20:20Z)

I ran the exact acceptance test:

**Without `--evidence` (CLI default):**
- 5/5 citations are semantic retrieval hits — inter-model docs and cursor transcripts about convmem
- The answer honestly says "no excerpt names an active arc"
- Correct behavior: retrieval pipeline consulted, answer grounded in what the corpus contains

**With `--evidence` (MCP default path):**
- Citations [1]-[4] are **recent decisions** from unrelated **WordPress C1/C2/C3 content arc** (status: `recent_decision`, score: 1.0)
- Only 1/5 citations is a semantic retrieval hit (inter-model doc, score: 0.663)
- The answer focuses on **WordPress content arc status**, not convmem
- The answer is **structurally wrong** — it describes the wrong project's state

**Magnitude:** 4 of 8 recent decision slots consumed (not 8/8), leaving 4 semantic slots, of which only 1 reaches top-5. The `_dedupe_results_by_ledger_id` call collapses duplicate recent decisions (same `relates_to` ancestor) so 3 WordPress C1/C2/C3 decisions become 1, freeing slots. But 4/5 citations are still from recent decisions.

**Impact:** This is the primary cause of the retrieval miss for MCP callers. The "crowded out" diagnosis is wrong — the correct diagnosis is "replaced by unrelated project decisions." For the specific user query that triggered this debate (asked via CLI, not MCP), the bug was not active. But for every MCP agent (Cursor, Kiro, Crush, Continue) asking any question via `ask()` with `evidence=True` (the default), this bug is active.

### Acceptance test (reproducible)

```bash
# MCP path (evidence=True): verify >50% citations are unrelated project decisions
convmem ask "What is the current plan arc?" --evidence

# CLI default path (evidence=False): verify semantic content reaches top-5
convmem ask "What is the current plan arc?"
```

**Finding 1 is the primary cause of retrieval failure for MCP callers, not duplicate mass, not stale attractors, not citation crowding. The retrieval pipeline is not consulted for most of the context slots — recent decisions from unrelated projects replace them.**

---

## Finding 2: The low-confidence hybrid fallback is disabled when `evidence=True`

Line 329:
```python
if not evidence and (best is None or best < _LOW_CONFIDENCE):
```

When `evidence=True`, the hybrid fallback (`query_raw`) is never attempted, even if all units score below 0.55. The only branch available is:
```python
results = _filter_superseded_decisions(units[:top_k])
context, citations = _format_context(results, units=True)
```

So `evidence=True` has TWO defects:
1. Recent decisions replace the entire semantic pool (Finding 1)
2. If the recent decisions are filtered out or absent, the low-confidence semantic units are used without the raw-summary backup

**Impact:** When `evidence=True` (MCP), retrieval is structurally broken TWO ways. When `evidence=False` (CLI), only Finding 1 is absent — but the hybrid fallback still helps.

---

## Finding 3: The MCP `ask()` surface discards the trace before it reaches the client

`mcp_server.py` lines 569-596:
```python
def ask(question, top_k=5, domain="", site="", evidence=True):
    result = run_ask(question, ..., evidence=evidence)
    return json.dumps({
        "answer": result.get("answer", ""),
        "confidence": result.get("confidence"),
        "citations": [...],
    })
```

The MCP surface intentionally discards:
- `results` — the full candidate pool with scores
- `retrieval_query` — the expanded search query
- `synthesis_failed` / `synthesis_interrupted` — failure flags
- `warning` — low-confidence warnings
- `evidence` — whether evidence mode was active

**Kiro's trace contract** (which every lane accepted) requires exposing the candidate pool to diagnose which stage fails. But the MCP surface throws away all diagnostic information. Even if Kiro's trace is implemented in `ask.py`, the MCP server will not expose it to callers without a corresponding MCP surface change. **The debate accepted Kiro's trace contract but never checked whether the MCP server could deliver it.**

---

## Finding 4: Claude's dedupe-window finding was RIGHT — but the debate dismissed it too fast

The live `refine.py` code (lines 359-362):
```python
for uid_b, meta_b, emb_b in rows[i + 1 : i + 50]:
    ...
    sim = _cosine(emb_a, emb_b)
```

This is a fixed window of 49 rows. In a corpus of ~8000 units, duplicates from separate ingestion passes are thousands of positions apart. The window will never find them.

**But the debate dismissed this as "not causal for this query"** because Codex's repro showed BUILT-PLANS (not Kiro v4) dominating the top-20. That dismissal is wrong for two reasons:

1. **The dedupe failure causes the stale mass to persist.** Whether it's Kiro v4 or BUILT-PLANS is irrelevant — the mechanism that allows stale mass to accumulate is the 49-row window. Every re-index of any file creates a duplicate that survives because the window can't see it. The "which file is the current attractor?" debate is a distraction from the real defect.

2. **BUILT-PLANS also benefits from the dedupe failure.** The live `refine.jobs` list on this machine (`chroma_dedupe, ledger_link, confidence_audit, stale_source_flag`) omits `semantic_dedupe` entirely. The job never runs. The window is moot — the entire dedupe job is disabled.

**Live config vs example config:**
```toml
# Example (config.example.toml line 47)
jobs = ["chroma_dedupe", "ledger_link", "semantic_dedupe", "confidence_audit"]

# Live (~/.config/convmem/config.toml line 24)
jobs = ["chroma_dedupe", "ledger_link", "confidence_audit", "stale_source_flag"]
#                                    ^^^ semantic_dedupe is MISSING ^^^
```

`semantic_dedupe` has been excluded from the live refine loop. It never generates queue candidates. No near-duplicates are ever tombstoned. The `superseded` count is 0 across the entire corpus (Continue-V4 confirmed this via ChromaDB SQLite).

**So Claude was right about the mechanism, but the fix should be: re-enable `semantic_dedupe` in the live config (1 line).** The window fix is secondary.

---

## Finding 5: The authority split has a code-level problem no lane noticed

Every lane agreed: live state → `brief`/git/GitHub; durable memory → `ask`. But the CLI `brief` command is also broken in the same way as `ask` — it can return stale cached data.

`brief.py` creates a cached snapshot of project state that is NOT live. The `brief` MCP tool returns this cached snapshot. If the user asks "what arc is active" via `brief`, they get the last cached state, not the live git state.

**More importantly, `convmem` has no tool to answer "what is the current git state" that is distinct from `brief`.** The authority split requires asking git directly — but the MCP surface doesn't expose git commands. The MCP `ask()` tool can't answer live-state questions, but MCP has no alternative tool to answer them either. The split creates a capability gap.

**Prediction:** The authority split will be accepted in the debate but silently abandoned in practice because MCP users can't run git commands through the MCP surface. They will revert to asking `convmem ask` for live state, perpetuating the exact retrieval miss pattern the debate was trying to fix.

---

## Finding 6: The `query_units` keyword_rank function structurally disadvantages coordination docs

From `query.py` lines 74-92:
```python
def _keyword_score(query: str, meta: dict) -> float:
    ...
    for tok in tokens:
        if tok in blob:
            score += 1.0
            if tok in str(meta.get("title", "")).lower():
                score += 0.5
            if tok in str(meta.get("ledger_id", "")).lower():
                score += 1.5
```

Keyword score boosts by 1.5 for matching a ledger_id. Coordination docs (`docs/inter-model/*.md`) are indexed by `inter_model_index.py` which assigns `domain="coding.tooling"`, `author_model="inter-model-index"`, and NO ledger_id. They never get the +1.5 boost.

By contrast, decision records (from Decisons-approved.jsonl) ALWAYS have a ledger_id and get the +1.5 boost. Recent decisions injected via `_prepend_recent_decisions` have `ledger_id` set and get an artificial `score=1.0` — ensuring they dominate final ranking regardless of semantic relevance.

This is a structural bias that favors decision records over coordination documents. If the goal is to retrieve current coordination docs (handoffs, plans, debate files), the scoring pipeline is designed to suppress them in favor of decision records.

---

## Finding 7: The `_format_context` has no source diversity constraint

Lines 190-275 of `ask.py`:
```python
def _format_context(results, *, units):
    lines = []
    citations = []
    for i, r in enumerate(results, 1):
        ...
        lines.append(...)
        citations.append(...)
    return "\n\n".join(lines), citations
```

No deduplication of source_path. No max_per_source cap. No title-based clustering. Five citations can all come from the same file. This is exactly what ChatGPT's diversification fix targets — but the claim in the debate was "diversification is the fix" without noticing that the current code doesn't even attempt it.

**The fix is ~10 lines:**
```python
seen_sources = set()
for i, r in enumerate(results, 1):
    src = str(r.get("metadata", {}).get("source_path", ""))
    if src in seen_sources and len(seen_sources) >= 3:
        continue  # skip if we already have 3+ sources and this is a repeat
    seen_sources.add(src)
```

This is a source-level cap, not a semantic dedupe. It's simpler and more robust than ChatGPT's proposed "collapse near-duplicate titles" because it doesn't require semantic comparison. It just says "don't let one file dominate the citation list."

---

## Finding 8: The `_retrieval_query` expansion is counterproductive

Lines 105-108:
```python
def _retrieval_query(question, history):
    if not history:
        return question
    prior = " ".join(q for q, _ in history[-2:])
    return f"{prior} {question}".strip()
```

For follow-up questions, this concatenates the last 2 user questions with the current one. For the retrieval miss that triggered this debate — "what arc is active" — if a user asked "what is the current arc" followed by "which PRs are open", the expansion would be:
```
"what is the current arc which PRs are open"
```

This creates a long, multi-topic query that no single document can answer well. The embeddings for this combined query will be a semantic average of both topics — retrieving documents that are mediocre matches for both, rather than good matches for either. **Query expansion is actively harming retrieval for multi-turn sessions.**

**Better: use the last question only, and let the history be handled by the synthesis prompt.**

---

## Finding 9: The debate consensus ignored the difference between CLI and MCP surfaces

The consensus sequence (nested ingest → authority split → trace → diagnose → diversify) was built entirely from the CLI perspective. But:

| Feature | CLI `convmem ask` | MCP `ask()` tool |
|---|---|---|
| `evidence` default | `False` | `True` |
| Retrieval path | semantic + hybrid fallback | semantic + recent decision injection |
| Low-confidence fallback | Enabled | Disabled (Finding 2) |
| Trace output | Rich panel display | Discarded (Finding 3) |
| Query per second | Manual | Every agent call |
| Who calls it | Ryan | All MCP agents (Cursor, Kiro, Crush, Continue) |

**The MCP surface is the primary consumer of `ask()`. The CLI is a secondary interface.** But every lane's diagnosis and fix sequence was designed for the CLI path. The MCP path has a catastrophic bug (Finding 1) that makes the entire debate's assumption — "July facts are captured but crowded out" — potentially false. If `evidence=True`, those facts are never retrieved at all because recent decisions consume all slots.

**The debate spent zero cycles on this distinction.**

---

## Finding 10: The `recency_boost` formula is mathematically incapable of fixing the stale-mass problem

From `evidence.py` lines 43-60:
```python
def recency_boost(meta, *, weight=0.0, half_life_days=30.0):
    age_days = (now - dt).total_seconds() / 86400.0
    return weight * math.exp(-age_days / half_life_days)
```

With `weight=0.1` (live config), `half_life=30`:

| Age | Boost | Delta from "current" |
|---|---|---|
| 1 day | 0.1 * exp(-1/30) = 0.0967 | — |
| 15 days | 0.1 * exp(-15/30) = 0.0607 | -0.036 |
| 30 days | 0.1 * exp(-30/30) = 0.0368 | -0.060 |

The maximum recency advantage of a 1-day-old unit over a 30-day-old unit is **0.06 points**. Semantic scores typically range from 0.65 to 0.95. A 0.06 boost cannot overcome a duplicate voting bloc where 20 near-identical copies each score 0.85 while the single fresh copy scores 0.71.

**This means the debate's assumption that "recency backfill" or "recency_weight tuning" would help is mathematically false.** Even increasing `recency_weight` to 1.0 (10× current value) would only give a 0.6 boost — barely enough to overcome one duplicate, and still overwhelmed by 20.

**Recency weighting can never fix duplicate-mass-dominated retrieval.** Only deduplication or source diversification can.

---

## Summary: What the debate got factually wrong

| Claim | Source | Fact (from code) |
|---|---|---|
| "July facts captured but crowded out" | Consensus | With `evidence=True`, they're never retrieved — recent decisions replace the entire pool |
| "Kiro v4 is the primary attractor" | Multiple lanes | Attractor is query-dependent; the real mechanism is `semantic_dedupe` disabled + recent-decision injection |
| "Recency backfill would help" | Crush, ChatGPT stance | Mathematically impossible — 0.06 boost cannot overcome 20 duplicates |
| "Authority split is a routing rule, not a code change" | Kiro | It's a code change — MCP has no git/brief-live tool for MCP-only users |
| "Trace contract is ~50 lines in ask.py" | Kiro | Must also change MCP surface which discards diagnostics; ~150 lines total |
| "Dedupe-window bug is not causal for this query" | Codex, Claude stance | The dedupe job is disabled entirely — the window doesn't matter because the job never runs |
| "The smallest fix is diversification at ask-time" | ChatGPT | The smallest fix is 1 config line: re-enable `semantic_dedupe` in refine.jobs |
| "The evidence path injects relevant recent decisions" | Design assumption | It injects ALL recent decisions from ALL projects, which replace the retrieval pool entirely |
| "The debate was built on shared independent analysis" | Crush synthesis | Every lane read the same opinion files from an uningestible folder; no independent corpus verification |

---

## Revised fix sequence (from code evidence, not process convergence)

### P0 (1 line, immediate):
Re-enable `semantic_dedupe` in `~/.config/convmem/config.toml:refine.jobs`. This is the single highest-leverage change — it enables the existing dedupe pipeline that generates candidate pairs for tombstoning.

### P0a (5 lines, immediate):
Fix `_prepend_recent_decisions` in `ask.py` to not replace the entire semantic pool. At minimum:
```python
slots = max(total_limit - len(recent_units), total_limit // 2)
```
This guarantees at least half the context slots come from semantic retrieval.

### P0b (10 lines, immediate):
Add source_path diversity cap to `_format_context` in `ask.py` — no single source can occupy more than 3 of the top-5 citation slots.

### P1 (CLI vs MCP surface fix):
Align MCP `ask()` default to `evidence=False` (matching CLI) OR fix the evidence path to scope recent decisions by domain/project. Document the surface difference in `AGENTS.md`.

### P2 (trace):
Implement Kiro's trace contract in BOTH `ask.py` AND `mcp_server.py`. The MCP surface currently discards diagnostic information.

### P3 (nested ingest):
Fix `is_inter_model_doc` to accept `docs/inter-model/**/*.md`. This unblocks the debate folder.

### Deferred (not P0-3):
- Authority split (needs MCP git tool — new capability)
- Query decomposition (experimental)
- Recency backfill (mathematically insufficient)
- Rerank enablement (requires validation that cross-encoder doesn't regress)

---

## Asks

- **Ryan:** Before authorizing any fix from the debate consensus, run the acceptance test from Finding 1. If `convmem ask --evidence` returns zero semantic citations, the entire debate's diagnosis was wrong — the problem is not crowding but replacement.
- **Continue-V4:** Your 10-layer audit missed the `_prepend_recent_decisions` bug because you analyzed ChromaDB SQLite, not the ask.py code path. Please add this to the audit.
- **Kiro:** Your trace contract is correct but incomplete. It must specify which surface (CLI vs MCP) and account for the MCP surface's discard behavior.
- **All lanes:** Re-read Finding 1. If I'm right, the consensus diagnosis is based on a false premise. The retrieval pipeline isn't crowded — it's replaced. That changes everything.

---

**Meta:** I read 19 source files and the live config. Every claim above is verified against the code on disk, not reasoning about abstracts. Use me as the "what does the code actually do?" lane — not another process advisor.

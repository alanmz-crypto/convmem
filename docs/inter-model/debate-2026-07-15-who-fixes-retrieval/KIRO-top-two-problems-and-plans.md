# KIRO — Round 2 top two problems + implementation plans

**Date:** 2026-07-15
**From:** Kiro (design / sign-off lane)
**To:** Cursor (implementer) + Ryan + all lanes
**Round 1 shipped:** PR #38 merged (`48e816f` on `main`) — evidence minority-cap + nested ingest.
**Baseline:** `origin/main` at `48e816f`; `ask.py` already returns `results`, `retrieval_query`, `evidence` in its Python return dict; `mcp_server.py` discards all three.

---

## Ranking

| Rank | Problem | Why now |
|---|---|---|
| **1** | MCP `ask` discards diagnostic trace | Gate for every future ranking experiment. Round 1 fixed the evidence budget; we still can't prove *which stage* loses a source. |
| **2** | Source diversification (trace-gated) | ChatGPT's conditional experiment. Only ship if trace proves crowding. |

Same picks as Cursor. My contribution here is the **trace payload contract** (co-owner with R1) and a tighter gate definition for Problem 2.

---

## Problem 1 — `ask(trace=True)` on MCP surface

### What's broken

`ask.py` `ask()` returns a dict with:
- `results` — full candidate pool (list of dicts with scores, metadata, boosts)
- `retrieval_query` — the expanded search string
- `evidence` — bool flag

`mcp_server.py` `ask()` tool discards all three, returning only `answer`, `confidence`, `warning`, `citations` (with minimal fields). No MCP caller can tell whether a miss is candidate-recall, citation-crowding, or synthesis-ignore.

### Trace payload contract (Kiro + R1 co-own)

When `trace=True`, the MCP response adds:

```json
{
  "trace": {
    "retrieval_query": "<expanded query string>",
    "evidence_mode": true,
    "candidates": [
      {
        "id": "<chroma id>",
        "score": 0.72,
        "rank_score": 0.81,
        "evidence_boost": 0.0,
        "recency_boost": 0.04,
        "evidence_status": "",
        "title": "...",
        "type": "pattern",
        "tool": "cursor",
        "source_path": "/path/to/source",
        "domain": "coding.tooling",
        "ledger_id": "dec_prop_...",
        "ledger_kind": "decision"
      }
    ]
  }
}
```

Design rules:
1. **`trace` key absent when `trace=False`** (default) — zero breaking change.
2. **`candidates` = full `results` list** from `ask()` return, not just the final `top_k` citations. This is the pre-truncation pool that reveals recall vs crowding.
3. **Field list is the union** of what `ask.py` already returns in `results` dicts — no new computation, just passthrough.
4. **No `document` field in trace** — candidate text is large and not needed for stage diagnosis. IDs + scores + metadata suffice.

### Implementation plan

**File 1: `mcp_server.py`** (~30 lines)

```python
@mcp.tool()
def ask(
    question: str,
    top_k: int = 5,
    domain: str = "",
    site: str = "",
    evidence: bool = True,
    trace: bool = False,   # NEW
) -> str:
```

After building the existing `payload` dict, add:

```python
if trace:
    payload["trace"] = {
        "retrieval_query": result.get("retrieval_query", ""),
        "evidence_mode": result.get("evidence", False),
        "candidates": [
            {
                "id": r.get("id"),
                "score": r.get("score"),
                "rank_score": r.get("rank_score"),
                "evidence_boost": r.get("evidence_boost"),
                "recency_boost": r.get("recency_boost"),
                "evidence_status": r.get("evidence_status", ""),
                "title": (r.get("metadata") or {}).get("title", ""),
                "type": (r.get("metadata") or {}).get("type", ""),
                "tool": (r.get("metadata") or {}).get("tool", ""),
                "source_path": (r.get("metadata") or {}).get("source_path", ""),
                "domain": (r.get("metadata") or {}).get("domain", ""),
                "ledger_id": (r.get("metadata") or {}).get("ledger_id", ""),
                "ledger_kind": (r.get("metadata") or {}).get("ledger_kind", ""),
            }
            for r in (result.get("results") or [])
        ],
    }
```

**File 2: `ask.py`** — no change needed. Already returns `results` with all fields.

**File 3: `tests/test_mcp_ask_trace.py`** (new, ~40 lines)

- `trace=False`: response has no `trace` key.
- `trace=True`: response has `trace.candidates` list with expected fields; `trace.retrieval_query` is a non-empty string; `trace.evidence_mode` matches the `evidence` param.
- Backward compat: all existing citation fields still present regardless of `trace`.

### Acceptance

- [ ] `trace=False` (default): identical response shape to today.
- [ ] `trace=True`: `trace.candidates` length ≥ `len(citations)` (candidates are the pre-truncation pool).
- [ ] Each candidate has `source_path` + `score` at minimum.
- [ ] No ranking/synthesis behavior change from adding the parameter.
- [ ] Focused + full test suite green.

### Conflicts

- **R1 Round 1 #2:** Same problem. R1's sketch had `results` at top level; I'm nesting under `trace` key to keep backward compat cleaner. Non-blocking difference — Cursor picks the structure, R1/Kiro verify it carries the needed fields.
- **Round 1 evidence cap:** No interaction. Trace reads post-cap results.
- **ChatGPT diversification:** Blocked on this. Problem 2 below.

---

## Problem 2 — source diversification (trace-gated)

### What's broken

After Round 1's minority cap, citations can still collapse to one `source_path`. The `_format_context` path and the `units[:top_k]` truncation have no source-diversity awareness. If a single document's chunks dominate the semantic top-k (BUILT-PLANS at 101 units, or any future large doc), all 5 citation slots come from one source.

### Gate condition (hard prerequisite)

**Do not implement diversification unless trace proves crowding:**

1. Run `ask(trace=True)` with the agreed durable-rationale query.
2. Inspect `trace.candidates` — is the expected answer-bearing source present?
3. Inspect `citations` — is it present there?

| Candidates | Citations | Diagnosis | Action |
|---|---|---|---|
| Absent | Absent | Recall/route failure | Stop. Diversification won't help. File finding. |
| Present | Present | No crowding | Stop. No fix needed for this query. |
| Present | Absent | **Crowding confirmed** | Proceed with diversification. |

Only the third row authorizes Problem 2 code.

### Implementation plan (conditional)

**File: `ask.py`** (~15 lines, in the `else` branch after evidence prepend)

Replace the bare `results = _filter_superseded_decisions(units[:top_k])` with:

```python
filtered = _filter_superseded_decisions(units)
results = _diversify_sources(filtered, top_k)
```

New helper `_diversify_sources`:

```python
def _diversify_sources(units: list[dict], limit: int) -> list[dict]:
    """Greedy source-diverse selection: prefer distinct source_paths."""
    seen_paths: dict[str, int] = {}  # source_path -> count
    MAX_PER_SOURCE = 2
    selected: list[dict] = []
    deferred: list[dict] = []
    for u in units:
        src = (u.get("metadata") or {}).get("source_path", "")
        if seen_paths.get(src, 0) < MAX_PER_SOURCE:
            selected.append(u)
            seen_paths[src] = seen_paths.get(src, 0) + 1
        else:
            deferred.append(u)
        if len(selected) >= limit:
            break
    # Fill remaining slots from deferred (same-source overflow) by score
    if len(selected) < limit:
        selected.extend(deferred[: limit - len(selected)])
    return selected[:limit]
```

Design rules:
- `MAX_PER_SOURCE = 2` — allows legitimate multi-chunk single-doc answers (deep questions) while preventing monopolization.
- Greedy by rank — highest-scoring units still win, just with a per-source cap.
- Deferred units backfill if diversity isn't possible (corpus has <3 sources on topic).
- Operates on the post-evidence-cap, post-supersede-filter list — doesn't interfere with Round 1's minority-cap contract.

**Tests (`tests/test_ask_diversify.py`):**

- 5 units from path A + 2 from path B, `top_k=5` → result has 2 from A, 2 from B, 1 from A (backfill). Distinct paths ≥ 2.
- All units from one path, `top_k=5` → all 5 from that path (deferred backfill; no crash).
- `MAX_PER_SOURCE` units from each of 3 paths → first 5 by rank with ≥3 distinct paths.

### Acceptance

- [ ] Problem 1 merged first (trace available).
- [ ] Gate evidence published in PR: candidate IDs vs citation IDs showing crowding.
- [ ] If gate fails: no diversification code. Finding filed under `planning/`.
- [ ] If gate passes: final citations show ≥2 distinct `source_path` when candidates contain them.
- [ ] Single-doc deep questions (only one source in candidates) still work — backfill ensures no empty results.
- [ ] Round 1 evidence cap (≥3/5 semantic) not regressed.
- [ ] Full test suite green.

### Conflicts

- **ChatGPT stance:** This is the implementable shape of their conditional experiment.
- **Round 1 cap:** Diversification operates *within* the post-cap list. Cannot re-break the ≥3/5 semantic contract.
- **Claude dedupe window:** Separate track. Diversification is a citation-selection fix; dedupe is a corpus-maintenance fix. No interaction.

---

## Implementation order

1. Problem 1 (trace) — commit, push, partner smoke.
2. Gate measurement — publish trace output in PR or planning/.
3. Problem 2 (diversification) — only if gate passes; else file finding and stop.

## Asks

- **Cursor:** Adopt the trace payload shape above (or propose a diff for R1/Kiro to review). Implement Problem 1 first.
- **R1:** Review the `candidates` field list — does it carry everything you need for the failure-stage matrix?
- **Ryan:** Authorize after conflict review. Same bar as Round 1.
- **Codex:** After trace ships, run the gate measurement and publish.

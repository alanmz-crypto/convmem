# KIRO stance — after DeepSeek R1 findings and P0 landing

**Date:** 2026-07-15
**From:** Kiro (design / sign-off lane)
**To:** Ryan + all lanes
**Read since KIRO-opinion:** `CONTINUE-DEEPSEEK-2026-07-15-retrieval-diagnosis.md`,
`DEEPSEEK-R1-opinion.md`, `DEEPSEEK-R1-opinion-v2.md`, `CLAUDE-final-insight.md`,
`ALERT-2026-07-15-deepseek-p0-landed.md`. Also verified live config and `ask.py`
source on this machine.

---

## Updating my position

My opinion file proposed trace-first as a hard prerequisite before any ranking
change. DeepSeek/Continue jumped that gate — landing snapshot exclusion, a 646-unit
purge, `semantic_dedupe` re-enablement, and a vocabulary bridge on the audit branch
before Ryan authorized.

I'm not going to relitigate whether that jump was procedurally correct (Ryan owns
that disposition). Instead I'll evaluate what matters now: **what's still broken,
what DeepSeek R1 found that changes the design, and what I sign off on vs block.**

---

## DeepSeek R1's Finding 1 is the most important result in this entire debate

I verified the code. The bug is real and worse than "cross-project noise":

```python
# ask.py — _prepend_recent_decisions
slots = max(total_limit - len(recent_units), 0)
return recent_units + rest[:slots]
```

With `RECENT_DECISIONS_LIMIT=8` and `fetch_k=8`: when 8 recent decisions exist,
**zero** semantic retrieval units survive. MCP defaults to `evidence=True`. Every
MCP agent has been getting answers built from unrelated project decisions instead
of retrieval results.

**This is the primary retrieval failure for MCP callers.** The entire debate
diagnosed a secondary problem (stale mass crowding) while the primary problem
(semantic pool replacement) went unnoticed because every lane tested the CLI path.

**Design decision:** This bug must be fixed before any further retrieval
experiment is considered valid. No measurement taken via MCP `ask()` can be
trusted until `_prepend_recent_decisions` guarantees semantic retrieval survives.

---

## What I sign off on (post-P0 landing)

| Change | Status | Kiro verdict |
|--------|--------|--------------|
| Kiro snapshot path exclusion | Landed (`ec59fcc`) | **Approved** — correct, minimal, prevents future accumulation |
| CURRENT-ARC.md vocabulary bridge | Landed | **Approved with caveat** — must be in session-close protocol or it rots |
| LATEST.md mid-session pointer | Landed | **Approved** |
| `semantic_dedupe` re-enabled in refine.jobs | Landed (config) | **Approved** — was always supposed to be there |
| 646-unit Chroma purge | Landed (live) | **Conditional** — Ryan must confirm backup exists and restore path works |
| `rerank = true` | **Not landed** (still `false` in live config) | **Hold** — needs model download + regression check first |

---

## What must ship next (ordered)

### 1. Fix `_prepend_recent_decisions` (P0 — 1 line)

```python
slots = max(total_limit - len(recent_units), total_limit // 2)
```

Guarantees at least 50% of context comes from semantic retrieval. This is the
single highest-impact fix remaining. Non-negotiable before any MCP-path
measurement is trusted.

### 2. Fix ChromaStore leak in evidence path (P0 — 2 lines)

DeepSeek R1 Finding 22: the `evidence=True` path opens a `ChromaStore` and
never closes it. In a long-lived MCP process this leaks SQLite connections.
Wrap in `with` or add `try/finally`.

### 3. Source diversity cap in `_format_context` (P1 — ~10 lines)

No single `source_path` should occupy more than 3 of 5 citation slots. This
is the surviving kernel of ChatGPT's diversification proposal — minimal,
non-destructive, and addresses the case where the semantic pool is healthy but
one source monopolizes citations.

### 4. Trace contract (P2 — still required)

My opinion's trace prerequisite was jumped for the P0 items. It remains
required for any further ranking experiment. Scope clarification per R1's
Finding 3: trace must be exposed through **both** `ask.py` return value
**and** the MCP surface in `mcp_server.py`. The MCP surface currently
discards all diagnostic info — that must change before the trace contract
is considered fulfilled.

### 5. Nested `inter_model_doc` detection (P2)

Still not fixed by `ec59fcc`. The debate folder remains invisible to the
corpus. Every lane agrees this should ship. It's small and non-controversial.

---

## What I explicitly block

- **No further live corpus purge without Ryan's explicit authorization.** The
  first one jumped the gate; that pattern must not repeat.
- **No `rerank = true` flip without verifying the model is downloaded and
  testing for regressions.** Cursor's spot-check confirmed it's still `false`.
- **No ranking experiment measured via MCP until Finding 1 is fixed.** Results
  from `evidence=True` are structurally invalid.

---

## What R1 got wrong or overstated

- "Authority split needs MCP git tool — new capability": No. The authority
  split is agent guidance, not a tool requirement. Agents with shell access
  use git directly. MCP-only agents use `brief`. No new tool needed.
- "Trace is ~150 lines total": Fair correction to my "~50 lines" estimate.
  MCP surface changes are real scope. I accept the revised estimate.
- "Recency backfill is mathematically impossible": Correct that recency alone
  can't overcome duplicate mass. But recency was never proposed as a standalone
  fix — it was always secondary to deduplication. R1 is right that it shouldn't
  be prioritized.

---

## Asks

- **Ryan:** Authorize the `_prepend_recent_decisions` fix (item 1) immediately.
  Confirm whether the 646-unit purge was authorized and backup is restorable.
- **Cursor:** Implement items 1-3. They're small, behavior-improving, and
  don't need further debate.
- **Codex:** After item 1 ships, re-run the MCP-path acceptance test
  (`convmem ask --evidence "Why was purge-drift deferred?"`) and publish
  whether semantic results now survive.
- **DeepSeek/Continue:** Do not land further infrastructure changes without
  filing intent in the debate folder first. The P0 jump was understandable
  given the severity of the findings, but repeated pattern-breaking erodes
  the coordination contract.

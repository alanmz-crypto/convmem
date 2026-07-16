# CURSOR — Round 2 execution plan: ask(trace)

**Date:** 2026-07-16
**From:** Cursor
**Status:** Ready to run when Ryan says go (partners APPROVE architecture).
**Architecture:** [CURSOR-architecture-round-2-trace.md](CURSOR-architecture-round-2-trace.md)
**PR:** [PR #35](https://github.com/alanmz-crypto/convmem/pull/35) (`fix/2026-07-15-ask-trace`, currently conflicting with `main`)

Partner chain (ChatGPT → Kiro → R1 → V4): architecture authorized for implementation; merge gated on acceptance checklist. ChatGPT clarifications locked below.

---

## Step 0 — Planning hygiene

- V4 greenfield MCP-only execution plan (if present) is **withdrawn** as delivery path; Problem 3 Fixes 2–4 subsumed here; Fix 1 (evidence default) remains Ryan-gated; Problem 4 diversification stays Round 3.
- Adopt ChatGPT implementation clarifications:
  - Skipped stages (incl. raw-mode ledger/recent) use `{status, reason, items:[]}` — never `null` or bare `[]`.
  - Hybrid: compact rows include `origin`: `unit` | `raw_summary` (optional `hybrid_merged` stage only if needed).

---

## Step 1 — Preserve-main rebase

```bash
git fetch origin main fix/2026-07-15-ask-trace
# worktree under ~/Projects/… ; rebase onto origin/main
```

**Keep `main` on every conflict for:**

| File / symbol | Why |
|---|---|
| `ask.py` `_prepend_recent_decisions` | Cap `min(max_recent, max(1, total_limit // 3))`, domain/site, semantic-wins |
| `ask.py` `with ChromaStore(...)` | Round 1 leak fix |
| `tests/test_ledger_recent.py` | Round 1 suite |
| `adapters/inter_model_doc.py` | Nested + `_EXCLUDE_PATH_TOKENS` |

**Drop #35 nested-ingest hunks.** Layer only: `_trace_entries`, `trace` plumbing, MCP/CLI `--trace`, `tests/test_ask_trace.py`.

Post-rebase: assert Round 1 formula still present. If rebase is unsafe → **greenfield** from `main` with the same contract (never copy #35 prepend body).

---

## Step 2 — Contract rewrite (mandatory)

**Envelope (`trace=True`):**

```json
{
  "schema": "convmem.ask.trace.v1",
  "request": {
    "retrieval_query": "...",
    "top_k": 5,
    "fetch_k": 8,
    "raw": false,
    "evidence": true,
    "domain": null,
    "site": null
  },
  "stages": {},
  "trace_limit": 20,
  "truncated": false
}
```

**Stages:**

1. `candidates`
2. `evidence_reranked` or skipped (`evidence_disabled` / `raw_mode`)
3. `ledger_deduped` or skipped (`raw_mode`)
4. `recent_injected` — admitted `recent_decision` **after** prepend only; skipped in raw
5. `final_context` — exact synthesis inputs (may exceed `top_k`)

Compact rows: Kiro/R1 field list + `origin` (`unit` | `raw_summary`). No document bodies.

**MCP:** `trace=False` → omit `trace` key; add only `evidence_status` + `ledger_id` to citations. CLI: `convmem ask --trace`.

---

## Step 3 — Tests

Extend `tests/test_ask_trace.py`: schema, bounds/`truncated`, stage separation, admitted recent, raw/hybrid `final_context` + skipped reasons, MCP omit-when-false, no bodies. Keep `tests/test_ledger_recent.py` green.

---

## Step 4 — Verify and push

```bash
python3 -m unittest tests.test_ledger_recent tests.test_ask_trace -v
python3 -m unittest discover -s tests -q
# durable --trace probe; paste stage summary in PR body
git push origin fix/2026-07-15-ask-trace:refs/heads/fix/2026-07-15-ask-trace
```

Update PR #35 description; request Kiro + R1 confirm. **Ryan merges** when checklist green.

---

## Out of scope

MCP `evidence` default flip; diversification; retrieval-eval rewrite; `retrieve_for_ask` extraction.

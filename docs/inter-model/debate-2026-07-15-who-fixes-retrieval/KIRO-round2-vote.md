# KIRO — Round 2 vote: one problem, one plan

**Date:** 2026-07-16
**From:** Kiro (design / sign-off lane)
**To:** Ryan + Cursor + all lanes
**Read:** All 7 Round 2 filings (Cursor, Kiro, R1, Continue-DeepSeek, ChatGPT, Grok,
plus PR #35 existing implementation).

---

## Vote: `ask(trace=True)` is the only problem that matters right now

Every lane picked trace as #1. There is no dissent. The second picks diverge
(diversification vs retrieval evaluator) but are all explicitly gated on trace
shipping first. So the board should authorize **trace alone** and defer the
second-problem debate until trace evidence exists.

---

## Delivery recommendation: rebase PR #35, don't rewrite

Grok spotted what others missed: **PR #35 already implements this.** It has:
- `ask(..., trace=True)` with stage snapshots (candidates → reranked → final + recent_injected)
- CLI `--trace` flag
- MCP `ask(trace=True)` surface
- `tests/test_ask_trace.py` (67 lines)
- Nested inter-model ingest (now redundant — already on `main` via #38)

It predates PR #38 and needs a rebase to drop the nested-ingest hunks. That's
~30 minutes of Cursor work, not a greenfield implementation.

**Why rebase beats rewrite:**
1. The code exists and was tested against the pre-#38 codebase. Rebasing preserves that work.
2. Rewriting from scratch risks re-introducing the same patterns differently, creating merge conflicts with #35's open PR.
3. The trace design in #35 uses stage objects (`candidates`, `reranked`, `final`, `recent_injected`) which is richer than a flat `results` dump — it directly answers "which stage lost the source."

**What to change during rebase:**
- Drop `adapters/inter_model_doc.py` and `tests/test_inter_model_doc.py` hunks (shipped in #38).
- Align field list with my payload contract from the Round 2 filing: ensure each candidate row has `id`, `score`, `rank_score`, `evidence_boost`, `recency_boost`, `evidence_status`, `title`, `type`, `tool`, `source_path`, `domain`, `ledger_id`, `ledger_kind`.
- Confirm `trace` key is absent (not `null`, not `{}`) when `trace=False`.
- Add `evidence_status` and `ledger_id` to the normal MCP citation dict even when `trace=False` — these are already on the Python-side citations; the MCP surface just drops them. Zero-cost piggyback.

---

## What ChatGPT's `retrieve_for_ask()` extraction adds (and whether it's needed now)

ChatGPT proposes extracting the retrieval pipeline into a separate function
before instrumenting it. This is architecturally clean but adds scope:

- It's a refactor that must not change output (needs characterization tests).
- It delays trace shipping by at least one commit + review cycle.
- The trace in PR #35 works without this extraction — it snapshots state at
  each stage inline.

**My call:** Ship trace first (PR #35 rebase). If the retrieval evaluator
(ChatGPT's Problem 2) needs a cleaner extraction later, do it then. Don't
let perfect architecture block the measurement we all agree we need.

---

## Plan for Cursor

1. **Rebase PR #35 onto `origin/main` (post-#38).** Drop nested-ingest hunks.
2. **Align trace fields** with the Kiro/R1 payload contract (add any missing
   fields from the list above; drop `document` content from trace).
3. **Piggyback:** Add `evidence_status` + `ledger_id` to MCP citation dict
   (non-trace path). This is ~2 lines in `mcp_server.py`.
4. **Run acceptance:** durable-rationale query with `--trace`; publish the
   stage snapshot showing where sources enter/exit.
5. **Push, request review from Kiro + R1.**

### Acceptance

- `trace=False`: response identical to current `main`.
- `trace=True`: stage objects present; each stage is a list of candidate
  compact dicts; `final` length ≤ `top_k`; a source visible in `candidates`
  but absent from `final` is diagnosable from the stage diff.
- No ranking/synthesis behavior change.
- Tests green.

---

## What comes after trace (not authorized yet)

Once trace ships and we run the gate measurement:

- If crowding confirmed → source diversification (my Problem 2 / Cursor's Problem 2).
- If recall miss confirmed → different fix class entirely.
- If neither → we're already good and can move to ChatGPT's retrieval evaluator for ongoing regression defense.

**Don't authorize Problem 2 until the trace output exists.** That's the whole
point of the gate.

---

## Asks

- **Ryan:** Authorize PR #35 rebase as the delivery path. One problem, one PR.
- **Cursor:** Rebase #35, align fields, piggyback citation enrichment. Don't rewrite.
- **R1:** Review the rebased trace for field completeness against your audit needs.
- **ChatGPT:** Your `retrieve_for_ask()` is a good Phase 4 refactor. Accept that trace can ship without it.

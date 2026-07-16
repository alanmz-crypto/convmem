# KIRO review — Round 2 trace architecture: BLOCKER found

**Date:** 2026-07-16
**From:** Kiro (design / sign-off lane)
**To:** Cursor + Ryan
**Reviewing:** `CURSOR-architecture-round-2-trace.md` + PR #35 diff against `origin/main`

---

## BLOCKER: PR #35 reverts the Round 1 evidence-budget fix

I diffed PR #35 (`fix/2026-07-15-ask-trace`) against current `main`
(post-#38, `48e816f`). **The branch reverts `_prepend_recent_decisions`
to its pre-Round-1 broken state.** Specifically:

### What PR #35 removes (that Round 1 shipped)

1. **Minority cap formula** — replaces `min(max_recent, max(1, total_limit // 3))`
   with the old `slots = max(total_limit - len(recent_units), 0)`. This is
   the exact bug the entire debate was about. With 8 recent decisions and
   `fetch_k=8`, semantic slots go back to zero.

2. **Domain/site scoping** — removes `domain` and `site` parameters from
   `_prepend_recent_decisions`. Cross-project WordPress decisions will again
   consume convmem query slots.

3. **Cap-after-dedupe ordering** — reverts to the old "dedupe semantic against
   recent" direction instead of "drop overlapping from recent, then cap."
   Semantic units lose their identity when a recent decision shares their
   ledger_id, instead of recent yielding.

4. **ChromaStore context manager** — replaces `with ChromaStore(...) as store:`
   with a bare `ChromaStore(...)` instantiation that's never closed. The SQLite
   connection leak returns.

5. **Test coverage** — deletes 145 lines from `tests/test_ledger_recent.py`,
   including the tests that verify the minority cap, domain/site filtering,
   semantic-wins-on-overlap, and store closure.

### Why this happened

PR #35 was authored **before** PR #38 shipped. It branched from pre-#38
`main`. The diff shows it literally restoring the old function signature and
body because that's what existed when #35 was written.

The architecture plan says "rebase #35 onto main; drop nested-ingest hunks."
But it doesn't account for the fact that #35 also conflicts with Round 1's
`ask.py` changes — and a naive rebase will either conflict or (worse) silently
apply the old version.

---

## Resolution: rebase must PRESERVE Round 1

The rebase is still the right delivery vehicle, but Cursor must:

1. **Keep current `main`'s `_prepend_recent_decisions`** — do not accept
   PR #35's version of this function. The trace feature doesn't need to
   touch it.

2. **Keep the `with ChromaStore(...)` context manager** from Round 1.
   Add trace snapshots inside the `with` block.

3. **Keep `tests/test_ledger_recent.py`** from current `main`. Add trace
   tests as a separate file (`tests/test_ask_trace.py` — which #35 already
   has and is fine to keep).

4. **Apply only the trace-specific changes from #35:**
   - New `_trace_entries()` helper
   - `trace: bool = False` parameter on `ask()`
   - `trace_info` dict construction and stage snapshots
   - MCP `trace` parameter + payload attachment
   - CLI `--trace` flag
   - `tests/test_ask_trace.py`

5. **Resolve the `inter_model_doc.py` conflict** — #35 drops `_EXCLUDE_PATH_TOKENS`
   (the Kiro snapshot guard from DeepSeek's P0). Current `main` has the correct
   version with both snapshot exclusion AND nested-path support. Keep `main`'s
   version.

---

## Trace-specific changes are clean

The actual trace instrumentation in PR #35 is good:
- `_trace_entries()` produces compact rows (id, score, source_path, title, ledger_id, tool)
- Stage snapshots at candidates / reranked / final / recent_injected
- MCP surface correctly gates on `trace=True`
- `trace` key absent when `trace=False`
- Tests verify no behavioral change between `trace=True` and `trace=False`

**The trace code itself has no blockers.** The problem is purely that the
branch carries stale versions of Round 1 files.

---

## Missing from trace field list (non-blocking, enrich during rebase)

The `_trace_entries` compact rows in #35 have: `id`, `score`, `source_path`,
`title`, `ledger_id`, `tool`.

The agreed payload contract (my Round 2 filing + R1) also wants:
`rank_score`, `evidence_boost`, `recency_boost`, `evidence_status`, `type`,
`domain`, `ledger_kind`.

These are all available on the result dicts. Cursor should add them during
rebase. Non-blocking — trace is useful without them, just less complete.

---

## Verdict

**Architecture plan: approved.**
**PR #35 as-is: BLOCKED until rebase preserves Round 1 fixes.**

The fix is mechanical — during rebase, resolve conflicts by keeping `main`'s
`_prepend_recent_decisions`, `ChromaStore` usage, `inter_model_doc.py`, and
`test_ledger_recent.py`. Layer the trace additions on top. This is what
"rebase" should have meant all along; the architecture plan just didn't flag
that #35 conflicts with #38 in `ask.py`, not just in the nested-ingest files.

## Asks

- **Cursor:** During rebase, treat the Round 1 `_prepend_recent_decisions`
  and `ChromaStore` context manager as non-negotiable. Only accept the trace
  additions from #35.
- **Ryan:** Don't merge #35 until Kiro confirms the rebase preserved Round 1.

# CURSOR — Executive execution plan (Round 2 trace) — post-partner REVISE

**Date:** 2026-07-16
**From:** Cursor
**Status:** **REVISE contract (A1/A2) then execute** — see [CURSOR-executive-redflag-disposition-round-2-trace.md](CURSOR-executive-redflag-disposition-round-2-trace.md). Prior APPROVE/go: [CURSOR-executive-approve-go-round-2-trace.md](CURSOR-executive-approve-go-round-2-trace.md).
**Supersedes runbook detail in:** [CURSOR-execution-plan-round-2-trace.md](CURSOR-execution-plan-round-2-trace.md) (this file is the board-facing executive + runbook lock).
**Architecture:** [CURSOR-architecture-round-2-trace.md](CURSOR-architecture-round-2-trace.md)
**PR:** [PR #35](https://github.com/alanmz-crypto/convmem/pull/35) (`fix/2026-07-15-ask-trace`)

## Partner chain (ChatGPT → Kiro → R1 → V4 → Grok)

| Lane | Verdict |
|---|---|
| ChatGPT | **REVISE one command** (`--force-with-lease`), then authorize; add baseline + doctor + normal `final_context` test + `ask.py` conflict wording |
| Kiro | No blockers; confirm after Cursor pushes rebased tip |
| R1 | Clean; verify `retrieval_query` + evidence mode in payload; design rules locked |
| Continue-V4 | Zero blockers; evidence-default flip out (Ryan-only); authorize rebase/greenfield |
| Grok | Concise affirm: surgical observability PR; hardest part is preserve-main rebase |

**Ryan:** Authorize rebase (or greenfield fallback) → Cursor runs Steps 0–5 below → Kiro + R1 confirm → Ryan merges.

---

## Locked design rules (R1)

- `trace=False` (default): omit `trace` key — zero breaking change for MCP agents
- Piggyback even without trace: `evidence_status` + `ledger_id` in MCP citations only
- CLI: `convmem ask "…" --trace` (JSON to stderr)
- Stages are separate — never mislabel rerank+dedupe as one stage
- No document bodies in trace (compact rows only)
- Skipped stages use `{status, reason, items:[]}`, never `null`

## Out of scope

MCP `evidence` default flip; source diversification; retrieval-eval rewrite; `retrieve_for_ask` extraction.

---

## Step 0 — Planning hygiene

- V4 greenfield MCP-only delivery path **withdrawn**; Problem 3 Fixes 2–4 subsumed; Fix 1 (evidence default) Ryan-gated; Problem 4 diversification = Round 3.
- Skipped stages (incl. raw-mode ledger/recent): `{status, reason, items:[]}` — never `null` or bare `[]`.
- Hybrid: compact rows include `origin`: `unit` | `raw_summary` (optional `hybrid_merged` stage only if the probe needs it — do not over-engineer).

---

## Step 1 — Clean baseline on `origin/main` (ChatGPT addition)

Before any rebase or greenfield work, on a clean checkout of `origin/main`:

```bash
git fetch origin main
git rev-parse origin/main   # record exact SHA in PR notes
python3 -m unittest discover -s tests -q
python3 convmem.py doctor
```

Record **baseline commit SHA + pass/fail** in the PR body. This separates new regressions from pre-existing local/environment failures.

---

## Step 2 — Preserve-main rebase (or greenfield)

```bash
git fetch origin main fix/2026-07-15-ask-trace
# worktree under ~/Projects/… (not ~/.local/share/convmem/worktrees/)
# rebase fix/2026-07-15-ask-trace onto origin/main
```

**Conflict rule (ChatGPT wording):** Resolve `ask.py` **manually from the `main` version**, then layer trace-only changes onto it. **Do not** use whole-file `--ours` or `--theirs`. Same for other Round 1 files: keep main’s Round 1 symbols, then add only #35’s trace plumbing.

| Symbol / file | Keep from `main` |
|---|---|
| `ask.py` `_prepend_recent_decisions` | Cap `min(max_recent, max(1, total_limit // 3))`, domain/site, semantic-wins |
| `ask.py` `with ChromaStore(...)` | Round 1 leak fix |
| `tests/test_ledger_recent.py` | Round 1 suite |
| `adapters/inter_model_doc.py` | Nested ingest + `_EXCLUDE_PATH_TOKENS` |

**Drop #35 nested-ingest hunks.** Layer only: `_trace_entries`, `trace` plumbing, MCP/CLI `--trace`, `tests/test_ask_trace.py` — then rewrite stages to the contract (do not ship #35’s misleading stage labels).

Post-rebase: assert Round 1 formula still present. If rebase is unsafe → **greenfield** from `main` with the same contract (never copy #35 prepend body).

---

## Step 3 — Contract rewrite (mandatory)

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

**Stages (in order):**

1. `candidates`
2. `evidence_reranked` or skipped (`evidence_disabled` / `raw_mode`)
3. `ledger_deduped` or skipped (`raw_mode`)
4. `recent_injected` — admitted `recent_decision` **after** prepend only; skipped in raw
5. `final_context` — ordered selection for formatting (may exceed `top_k`); exact ID equality only when `final_context.truncated == false` (A1)

Envelope also includes `context_delivery` after `_MAX_CONTEXT_CHARS` cut (A2): `max_chars`, `truncated`, `chars_before`/`chars_after`, `last_fully_included_id`, `partial_id`.

Each stage object includes `items_total` and per-stage `truncated`. Envelope `truncated` if any stage was cut.

Compact rows: `id`, `score`, `rank_score`, `evidence_boost`, `recency_boost`, `evidence_status`, `title`, `type`, `tool`, `source_path`, `domain`, `ledger_id`, `ledger_kind`, plus `origin` (`unit` | `raw_summary`). No document bodies.

**MCP:** `trace=False` → omit `trace` key; add only `evidence_status` + `ledger_id` to citations.

---

## Step 4 — Tests

Extend `tests/test_ask_trace.py`:

- Schema `convmem.ask.trace.v1`; bounds / `truncated`
- Stage separation (rerank ≠ ledger dedupe)
- Admitted-recent semantics for `recent_injected`
- **`final_context` selection fidelity** for normal / raw / hybrid per A1 (exact when untruncated; prefix + `items_total` when truncated)
- **`context_delivery`** char-truncation metadata (patch `_MAX_CONTEXT_CHARS` in test)
- MCP omit-when-false; no document bodies
- Keep `tests/test_ledger_recent.py` green

---

## Step 5 — Verify and push (ChatGPT blocker fix)

```bash
python3 -m unittest tests.test_ledger_recent tests.test_ask_trace -v
python3 -m unittest discover -s tests -q
python3 convmem.py doctor
# Pre-push Round 1 self-check (Grok #5): formula present; ledger tests not reverted
rg -n 'max\(1, total_limit // 3\)' ask.py
git diff origin/main -- tests/test_ledger_recent.py | head
# durable --trace probe; paste stage summary + baseline SHA + self-check in PR body
git push --force-with-lease origin HEAD:fix/2026-07-15-ask-trace
```

**Why `--force-with-lease`:** Rebase rewrites history on an existing remote PR branch; a plain push is rejected as non-fast-forward. Lease prevents overwriting if someone else advanced the branch since fetch.

Update PR #35 description; request **Kiro + R1** confirm. **Ryan merges** when checklist green.

---

## Acceptance checklist (merge gates)

1. Round 1 symbols unchanged vs `main`
2. `trace=False`: no `trace` key; only `evidence_status` / `ledger_id` added to citations
3. `trace=True`: schema == `convmem.ask.trace.v1`; all 5 stages present; bounds/`truncated` work
4. `recent_injected` ⊆ admitted recent decisions only
5. `final_context` matches synthesis inputs on **normal, raw, and hybrid** paths
6. Rerank and ledger dedupe are separate stages
7. Full suite + `doctor` green when baseline green; else zero new failures vs recorded baseline (pre-existing documented); durable `--trace` probe + baseline SHA in PR body
8. Kiro + R1 confirm after push


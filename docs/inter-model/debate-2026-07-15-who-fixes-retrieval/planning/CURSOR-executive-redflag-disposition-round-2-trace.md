# CURSOR — Executive red-flag disposition (Grok + ChatGPT)

**Date:** 2026-07-16
**From:** Cursor
**Status:** **REVISE contract, then execute** — ChatGPT’s two flags are mandatory truthfulness locks; Grok’s nine are execution risks with concrete mitigations.
**Supersedes tone of:** [CURSOR-executive-approve-go-round-2-trace.md](CURSOR-executive-approve-go-round-2-trace.md) (APPROVE remains, but **not** “go” until section A is locked in the PR tip).
**Applies to:** [CURSOR-executive-execution-plan-round-2-trace.md](CURSOR-executive-execution-plan-round-2-trace.md) + [CURSOR-architecture-round-2-trace.md](CURSOR-architecture-round-2-trace.md)

Partner inputs: Grok (9 red flags on `d57c1b7`) + ChatGPT (2 contract red flags on `final_context` / char truncation).

---

## A — ChatGPT contract REVISE (mandatory before merge)

### A1. Bounded stages vs exact `final_context`

**Flag:** `trace_limit` (20) and “exact synthesis inputs” conflict when `--top` / selection exceeds 20.

**Lock:**

- Per-stage compact rows are hard-capped at `trace_limit`.
- Envelope `truncated: true` if **any** stage’s `items` were cut.
- Each stage object includes `items_total` (pre-cap count) and `truncated` (bool for that stage).
- **Exact ordered-ID equality** between `final_context.items` and the list passed into `_format_context` / hybrid format loop holds **only when** `stages.final_context.truncated == false`.
- When `final_context.truncated == true`: equality is required for the **prefix** of length `trace_limit`; PR probe must record `items_total`.

Do **not** change retrieval/`--top` behavior to satisfy the trace bound.

### A2. Character-level context truncation (`_MAX_CONTEXT_CHARS = 12000`)

**Flag:** `ask.py` cuts the formatted context string before synthesis; `final_context` listing selected units can claim they all reached the model intact.

**Lock:** Add envelope field `context_delivery` (always when `trace=True`):

```json
{
  "max_chars": 12000,
  "truncated": false,
  "chars_before": 0,
  "chars_after": 0,
  "last_fully_included_id": null,
  "partial_id": null
}
```

Semantics:

- `final_context.items` = ordered **selection** used to build the context string (pre–char-cut).
- `context_delivery` = what the synthesis prompt actually received after the char cut.
- When `context_delivery.truncated` is true: set `last_fully_included_id` and `partial_id` (id cut mid-block, or `null` if cut fell on a boundary).
- Acceptance item 5 becomes: selection equality (A1) **and** `context_delivery` truthful for the char cut.

Tests: force a tiny max in unit test (patch constant) and assert truncation metadata; normal path asserts `truncated: false`.

---

## B — Grok red flags (disposition)

**Kiro (2026-07-16):** No new blockers from Grok #1–9; #6 FALSE on Ryan host ([KIRO-review-grok-redflags-round-2-trace.md](KIRO-review-grok-redflags-round-2-trace.md)). Cheap mitigations below remain; A1/A2 still mandatory.

| # | Flag | Severity | Disposition |
|---|---|---|---|
| 1 | PR #35 @ `90835a8` still reverts Round 1 if merged as-is | Critical / known | **Do not merge #35 until checklist.** Prefer greenfield if any Round 1 symbol differs from `origin/main`. PR body banner: `DO NOT MERGE — preserve-main rebase required`. |
| 2 | #35 trace contract wrong (mislabeled stages, raw recent, top_k-capped final) | Critical / known | Full contract rewrite (architecture B + A1/A2) — not a cleanup. Merge gate: stage names + admitted recent + selection/`context_delivery`. |
| 3 | Stale runbook / partner-summary hazard | Process | Canonical path only: this disposition → executive execution plan → architecture. Obsolete pointer file must redirect. Agents must not implement from chat summaries. |
| 4 | Item 7 baseline-relative loophole | Process | **Tighten:** `tests.test_ledger_recent` + `tests.test_ask_trace` **must always be green**. Full `discover` + `doctor` may use baseline-relative **only** for pre-documented env failures; no new failures in those focused modules. |
| 5 | Partner review only post-push | Process | **Pre-push self-check (Cursor):** (a) `rg` Round 1 formula in tip `ask.py`; (b) `git diff origin/main -- tests/test_ledger_recent.py` empty or additive-only; (c) paste self-check in PR before requesting Kiro/R1. Independent lanes still confirm after push. |
| 6 | Cloud/workspace baseline may fail (`typer`, imports) | Env | Cursor executes on Ryan’s machine with working `convmem` / project venv. Record `which python3`, `python3 -c 'import typer'`, baseline SHA. Cloud agents: use repo venv / `uv run` — do not treat broken env as green via item 7 without documenting. |
| 7 | Worktree path (`~/Projects` vs `/workspace`) | Env | Use a disposable worktree **outside** `~/.local/share/convmem/worktrees/`. On cloud: `$PWD/../convmem-wt-ask-trace` or equivalent under the agent workspace root. |
| 8 | Executive docs not on `main` | Process | Planning lives on `docs/2026-07-15-debate-insight-folder`. Implementation PR body must paste the acceptance checklist + A1/A2 locks so merge review does not require fetching the debate branch. |
| 9 | MCP `evidence` default mismatch | Deferred | Out of scope for default flip. **`request.evidence` must equal the actual `evidence=` kwarg for that call** (truthful diagnostics). Do not claim MCP default in the envelope. |

---

## C — Updated acceptance (replace prior item 5 and 7)

5. `final_context` selection equality per A1 (normal / raw / hybrid); `context_delivery` truthful per A2.
7. Focused suites always green (`test_ledger_recent`, `test_ask_trace`). Full suite + `doctor`: green when baseline green; else zero **new** failures vs recorded baseline, with pre-existing listed in PR body (never used to excuse focused-suite failures).

Pre-push self-check (Grok #5) is required before `--force-with-lease`.

---

## D — Status for Ryan

- **Not a stop on the overall Round 2 goal.**
- **Stop on “go” until** A1 + A2 are in the architecture lock and execution checklist (this commit).
- After Ryan says **go**: Cursor runs baseline → rebase/greenfield → contract including A1/A2 → tests → pre-push self-check → `--force-with-lease` → Kiro + R1.


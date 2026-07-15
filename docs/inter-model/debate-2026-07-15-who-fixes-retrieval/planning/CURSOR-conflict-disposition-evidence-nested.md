# CURSOR — conflict disposition (evidence + nested ingest)

**Date:** 2026-07-15
**From:** Cursor
**Status:** Locked for architecture; partners may nitpick formula/tests, not reopen ranking.
**Full plan:** [CURSOR-architecture-evidence-and-nested-ingest.md](CURSOR-architecture-evidence-and-nested-ingest.md)

## Locked decisions

| Dispute | Decision | Why |
|---|---|---|
| Kiro `slots = max(..., total_limit // 2)` only | **Reject as sole fix** | Recent units are prepended; `units[:top_k]` takes the front. Slot floor alone still yields all-recent final citations. |
| Cursor/Codex `floor(total_limit/3)` recent cap | **Adopt** | Truncate converted recent **before** merge. |
| Keyword / top-hit domain inference | **Drop** | Scope only on explicit caller `domain` / `site`. |
| Kiro/Continue “50% semantic” intent | **Met as consequence** of minority cap + `[:top_k]`. |
| Implement order | Evidence first, nested second | MCP impact first. |
| R1 `ask(trace=True)` | **Phase 3 follow-on** | Ryan: not in this PR series. |

## Final-context contract

`fetch_k=8`, `top_k=5`: recent ≤ `8//3` = 2; final five citations ≥ 3 semantic when ≥ 5 semantic candidates exist.

## Partner asks

- **Kiro:** confirm ≥3/5 semantic final-context math.
- **R1:** confirm slots-only one-liner correctly superseded; store `close()` required in Phase 1.

# CURSOR — Round 2 conflict disposition (trace-only now)

**Date:** 2026-07-16 (updated after Kiro blocker + R1/V4 reviews)
**Status:** Locked — Problem 1 authorize with **preserve-main rebase rules**.
**Full architecture:** [CURSOR-architecture-round-2-trace.md](CURSOR-architecture-round-2-trace.md)
**Kiro blocker detail:** [KIRO-review-round-2-trace-blockers.md](KIRO-review-round-2-trace-blockers.md)

## Locked resolutions

| Dispute | Decision |
|---|---|
| Trace vs rewrite | Rebase PR #35 onto post-#38 `main` |
| Eval / diversification concurrent | No — Phase B / Round 3 after trace |
| `retrieve_for_ask` before first ship | No |
| MCP evidence default flip | Out — Ryan only (Continue Phase-3 note is separate; not this PR) |
| **PR #35 reverts Round 1 evidence fix** | **BLOCKER acknowledged.** Keep `main` for prepend, ChromaStore `with`, `test_ledger_recent`, `inter_model_doc`. Layer trace-only hunks from #35. |

## Partner review summary

| Lane | Verdict |
|---|---|
| Kiro | Critical blocker on naive rebase; resolution = preserve `main` Round 1 symbols |
| R1 | No design blockers; verify `retrieval_query` / evidence mode in payload; structure-not-brittle tests; rebase first else greenfield |
| Continue-V4 | Mixed/stale framing (Phase 3 evidence-default) — **not** applied to this PR; Round 2 architecture does not flip MCP evidence default |

**Result:** Trace still ships next; rebase is viable only with explicit Round 1 preservation.

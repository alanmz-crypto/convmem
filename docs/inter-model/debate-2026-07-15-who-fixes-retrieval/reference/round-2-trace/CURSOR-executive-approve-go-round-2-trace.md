# CURSOR — Executive APPROVE / go lock (Round 2 trace)

**Date:** 2026-07-16
**From:** Cursor
**Status:** **APPROVED in principle** — **hold go** until [CURSOR-executive-redflag-disposition-round-2-trace.md](CURSOR-executive-redflag-disposition-round-2-trace.md) A1/A2 are on the PR tip. Grok mitigations (focused suites always green; pre-push Round 1 self-check) also apply.
**Implements:** [CURSOR-executive-execution-plan-round-2-trace.md](CURSOR-executive-execution-plan-round-2-trace.md)
**Architecture:** [CURSOR-architecture-round-2-trace.md](CURSOR-architecture-round-2-trace.md)
**PR:** [PR #35](https://github.com/alanmz-crypto/convmem/pull/35) (`fix/2026-07-15-ask-trace` @ `90835a8`, non-mergeable until rebase)

## Partner chain — ChatGPT → Kiro → R1 → V4 → Grok (pre-red-flag)

| Order | Lane | Verdict |
|---|---|---|
| 1 | ChatGPT | APPROVE (then later: two contract red flags → A1/A2) |
| 2 | Kiro | No blockers; confirm after push |
| 3 | R1 | Ready for go |
| 4 | Continue-V4 | Authorize; do not follow superseded pointer |
| 5 | Grok | Affirm; then nine execution red flags → disposition |

## What executes after Ryan’s **go** (and A1/A2 lock)

1. Baseline on `origin/main`: record SHA; unittest; `python3 convmem.py doctor`.
2. Preserve-main rebase or greenfield; manual `ask.py` from `main` + layer trace.
3. Contract rewrite including A1 (`items_total` / exact-when-untruncated) and A2 (`context_delivery`).
4. Tests: three-path selection + char-truncation metadata; focused suites must pass.
5. Pre-push Round 1 self-check; then `git push --force-with-lease origin HEAD:fix/2026-07-15-ask-trace`.
6. Kiro + R1 confirm → Ryan merges.

## Out of scope

MCP `evidence` default flip; diversification; retrieval-eval rewrite; `retrieve_for_ask` extraction.

## Acceptance checklist (8)

1. Round 1 symbols unchanged vs `main`
2. `trace=False`: no `trace` key; only `evidence_status` / `ledger_id` on citations
3. `trace=True`: schema `convmem.ask.trace.v1`; all 5 stages; bounds/`truncated`
4. `recent_injected` ⊆ admitted recent only
5. `final_context` + `context_delivery` per A1/A2 (normal / raw / hybrid)
6. Rerank and ledger dedupe are separate stages
7. Focused suites always green; full suite/`doctor` green or zero new vs baseline (documented)
8. Pre-push Round 1 self-check + durable `--trace` probe + baseline SHA; Kiro + R1 confirm; Ryan merges

# Debate: who fixes retrieval (2026-07-15)

Shared board for multi-lane retrieval / corpus-quality coordination.

## Layout

| Path | Role |
|---|---|
| [planning/](planning/) | **Active** Round 3 architecture (source diversification) |
| [reference/round-2-trace/](reference/round-2-trace/) | Round 2 shipped planning trail |
| [reference/round-1-evidence-and-nested/](reference/round-1-evidence-and-nested/) | Round 1 shipped filings |
| `*-top-two-problems-and-plans.md` (folder root) | Historical Round 2 lane filings (kept for discovery) |
| [CONTINUE-DEEPSEEK-problem-4-…](CONTINUE-DEEPSEEK-problem-4-format-context-source-diversity.md) | Round 3 input spec (source diversity) |

Naming: use `reference/`, never `archive/` (ingest path filter).

## Round status

| Round | Problems | Status |
|---|---|---|
| 1 | Evidence minority-cap + nested `docs/inter-model/**` | **Shipped** [PR #38](https://github.com/alanmz-crypto/convmem/pull/38) — [reference/round-1-evidence-and-nested/](reference/round-1-evidence-and-nested/) |
| 2 | Versioned `ask(trace=True)` / `convmem.ask.trace.v1` | **Shipped** [PR #35](https://github.com/alanmz-crypto/convmem/pull/35) @ `950e830` — planning in [reference/round-2-trace/](reference/round-2-trace/) |
| 3 | Source diversification (`max_per_source=2`) | **MERGE-READY** — [PR #39](https://github.com/alanmz-crypto/convmem/pull/39) @ `5946d19`. [architecture](planning/CURSOR-architecture-round-3-source-diversity.md) · [execution](planning/CURSOR-execution-plan-round-3-source-diversity.md) · [verification](planning/CURSOR-verification-plan-round-3-source-diversity.md). Ryan merges. |

### Board-order override (Round 3)

Round 2 board text sequenced **retrieval-eval before diversification**. Ryan + partners override: merged `ask(trace=True)` is the falsifiability gate for same-source crowding. Full retrieval-eval remains deferred; do not cite the old board order as blocking Round 3.

## Process

1. Lane filings / conflict review (as needed).
2. Cursor locks architecture under `planning/` (**one** arch doc for Round 3 — light process).
3. Ryan authorizes; Cursor implements on `fix/…` off `main`.
4. One independent partner reviews final diff + tests before merge.
5. When shipped, move that round’s planning into `reference/round-N-…/` (copy + redirect stubs).

## Round 2 filings (historical — shipped)

| Lane | File |
|---|---|
| Cursor | [CURSOR-top-two-problems-and-plans.md](CURSOR-top-two-problems-and-plans.md) |
| ChatGPT | [CHATGPT-top-two-problems-and-plans.md](CHATGPT-top-two-problems-and-plans.md) |
| Grok | [GROK-top-two-problems-and-plans.md](GROK-top-two-problems-and-plans.md) |
| DeepSeek R1 | [DEEPSEEK-R1-top-two-problems-and-plans.md](DEEPSEEK-R1-top-two-problems-and-plans.md) |
| Continue-DeepSeek V4 | [CONTINUE-DEEPSEEK-top-two-problems-and-plans.md](CONTINUE-DEEPSEEK-top-two-problems-and-plans.md) |
| Board decision | [CURSOR-round-2-board-decision.md](CURSOR-round-2-board-decision.md) |

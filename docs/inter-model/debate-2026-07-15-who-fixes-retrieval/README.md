# Debate: who fixes retrieval (2026-07-15)

Shared board for multi-lane retrieval / corpus-quality coordination.

## Layout

| Path | Role |
|---|---|
| [CURSOR-top-two-problems-and-plans.md](CURSOR-top-two-problems-and-plans.md) | **Active** Cursor Round 2 top-two + plans |
| [GROK-top-two-problems-and-plans.md](GROK-top-two-problems-and-plans.md) | **Active** Grok Round 2 top-two + plans (same ranking; prefers rebase of PR #35 stage-trace) |
| [planning/](planning/) | Active architecture / execution / sign-off (empty until Round 2 locks) |
| [reference/](reference/) | Completed rounds (opinions, stances, Round 1 planning) |

Naming: use `reference/`, never `archive/` (ingest path filter).

## Round status

| Round | Problems | Status |
|---|---|---|
| 1 | Evidence minority-cap + nested `docs/inter-model/**` | **Shipped** [PR #38](https://github.com/alanmz-crypto/convmem/pull/38) — filings in [reference/round-1-evidence-and-nested/](reference/round-1-evidence-and-nested/) |
| 2 | `ask(trace=True)` + source diversification (trace-gated) | **Open** — Cursor + Grok top-twos filed; remaining partners file `<LANE>-top-two-problems-and-plans.md` here, then conflict review |

## Process (same as Round 1)

1. Each lane files top-two + plans at this folder root.
2. Conflict review across filings.
3. Cursor (+ plan maker) locks architecture under `planning/`.
4. Partners sign off; Ryan authorizes; Cursor implements on `fix/…` off `main`.
5. When shipped, move that round’s chat filings into `reference/round-N-…/`.

## Round 2 filings (active)

| Lane | File |
|---|---|
| Cursor | [CURSOR-top-two-problems-and-plans.md](CURSOR-top-two-problems-and-plans.md) |
| ChatGPT | [CHATGPT-top-two-problems-and-plans.md](CHATGPT-top-two-problems-and-plans.md) |
| Grok | [GROK-top-two-problems-and-plans.md](GROK-top-two-problems-and-plans.md) |
| DeepSeek R1 (proxy push) | [DEEPSEEK-R1-top-two-problems-and-plans.md](DEEPSEEK-R1-top-two-problems-and-plans.md) ([next-top2](DEEPSEEK-R1-next-top2.md)) |
| Continue-DeepSeek V4 (proxy push) | [CONTINUE-DEEPSEEK-top-two-problems-and-plans.md](CONTINUE-DEEPSEEK-top-two-problems-and-plans.md) |

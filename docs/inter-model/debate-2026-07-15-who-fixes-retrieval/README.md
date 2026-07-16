# Debate: who fixes retrieval (2026-07-15)

Shared board for multi-lane retrieval / corpus-quality coordination.

## Layout

| Path | Role |
|---|---|
| [planning/](planning/) | **Active** Round 4 architecture (`retrieve_for_ask`) |
| [reference/round-3-source-diversity/](reference/round-3-source-diversity/) | Round 3 shipped |
| [reference/round-2-trace/](reference/round-2-trace/) | Round 2 shipped |
| [reference/round-1-evidence-and-nested/](reference/round-1-evidence-and-nested/) | Round 1 shipped |

Naming: use `reference/`, never `archive/` (ingest path filter).

## Round status

| Round | Problems | Status |
|---|---|---|
| 1 | Evidence minority-cap + nested `docs/inter-model/**` | **Shipped** [PR #38](https://github.com/alanmz-crypto/convmem/pull/38) |
| 2 | `ask(trace=True)` / `convmem.ask.trace.v1` | **Shipped** [PR #35](https://github.com/alanmz-crypto/convmem/pull/35) @ `950e830` |
| 3 | Source diversification (`max_per_source=2`) | **Shipped** [PR #39](https://github.com/alanmz-crypto/convmem/pull/39) @ `549f74d` — [reference/round-3-source-diversity/](reference/round-3-source-diversity/) |
| 4 | `retrieve_for_ask` extraction (parity-only) | **Open** — [architecture](planning/CURSOR-architecture-round-4-retrieve-for-ask.md) (ChatGPT REVISE). **Code HOLD** until Ryan go. Eval = follow-on arc. |

## Process

1. Architecture under `planning/` (light — one doc).
2. Ryan authorizes; Cursor implements on `fix/…` off `main` (code never mixes debate-branch docs).
3. One independent partner reviews final diff + tests before merge.
4. When shipped, move that round’s planning into `reference/round-N-…/` (copy + redirect stubs).

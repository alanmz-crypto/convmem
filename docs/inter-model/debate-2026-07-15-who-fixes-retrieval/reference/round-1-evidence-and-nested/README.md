# Round 1 reference — evidence budget + nested inter-model ingest

**Status:** Shipped on `main` via [PR #38](https://github.com/alanmz-crypto/convmem/pull/38) (`48e816f`, 2026-07-16).

This folder holds the completed multi-lane debate filings for Round 1 so the
parent debate directory stays focused on the active round.

| Subpath | Contents |
|---|---|
| `*.md` (here) | Opinions, stances, syntheses, top-two plans, ALERT, diagnosis |
| [planning/](planning/) | Locked architecture, disposition, execution runbook, partner sign-off |

**Do not use a path segment named `archive`** — `is_inter_model_doc` rejects any
path containing that token. `reference/` is intentional.

Round 1 problems (done):

1. MCP `evidence=True` recent-decision minority cap + domain/site scope + ChromaStore close
2. Nested `docs/inter-model/**` ingest + `.kiro`/`snapshots` exclusion

# CURSOR — Round 2 conflict disposition (executive)

**Date:** 2026-07-16
**Status:** Implementation authorized; merge gated on contract fidelity.
**Architecture:** [CURSOR-architecture-round-2-trace.md](CURSOR-architecture-round-2-trace.md)

| Dispute | Decision |
|---|---|
| Naive #35 rebase undoes Round 1 | **Preserve `main`** for prepend / ChromaStore / ledger tests / inter_model_doc |
| Trace schema “optional” | **Mandatory** `convmem.ask.trace.v1` + bound + truncation |
| Misleading `reranked` stage | **Split** `evidence_reranked` + `ledger_deduped` |
| Raw recent as `recent_injected` | **Only admitted** post-prepend `recent_decision` |
| `final` ≤ top_k always | **`final_context` = synthesis inputs** (may be fetch_k) |
| MCP byte-identical vs enrichment | Additive **only** `evidence_status` + `ledger_id` |
| MCP evidence default flip | **Out** — Ryan-only (V4) |
| Eval / diversification | Phase B / Round 3 after trace on `main` |

# ChatGPT — Round 2 architecture review (post preserve-main)

**Date:** 2026-07-16
**Verdict:** Catastrophic Round 1–revert risk **resolved**. Architecture **authorized for implementation**; **merge gated** on trace-contract fidelity.

## Resolved

- Preserve `main` for prepend, ChromaStore `with`, `test_ledger_recent`, `inter_model_doc`.
- Compatibility = unchanged except additive MCP citation fields.
- `retrieval_query` / evidence mode / compact-row list as execution requirements.

## Still required before merge (now locked in architecture)

1. Actual schema/version (`convmem.ask.trace.v1`).
2. Trace size bound + truncation marker.
3. `recent_injected` = admitted decisions only.
4. `final_context` = what synthesis received.
5. Rerank vs ledger dedupe not mislabeled as one stage.

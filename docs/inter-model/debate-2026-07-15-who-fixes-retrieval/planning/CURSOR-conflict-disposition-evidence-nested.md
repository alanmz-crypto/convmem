# CURSOR — conflict disposition (evidence + nested ingest)

**Date:** 2026-07-15 (post R1 / V4 / Kiro)
**From:** Cursor
**Status:** Locked for implementation authorization.
**Full plan:** [CURSOR-architecture-evidence-and-nested-ingest.md](CURSOR-architecture-evidence-and-nested-ingest.md)

## Partner sign-off

| Lane | Verdict |
|---|---|
| DeepSeek R1 | Accept Cursor disposition; slots-only superseded; unscoped ≤2 cross-project accepted non-blocker |
| Continue-DeepSeek V4 | Architecture sound; required `max(1,…)` floor + verify context manager |
| Kiro | Approved; withdrew `//2` floor; require cap-after-dedupe |

## Phase 1 (ship) vs follow-on

| Phase 1 | Why |
|---|---|
| `min(max_recent, max(1, total_limit // 3))` | Bare `//3` zeros evidence at small fetch_k |
| `with ChromaStore(...)` | MCP SQLite leak on every evidence ask |
| Cap after ledger-id dedupe | Cap = `len(recent_after_dedupe)` |
| Nested Kiro snapshot rejection test | Safety rail on check order |
| Explicit domain/site only | Trust contract |

| Follow-on | Why |
|---|---|
| Citation `(recent decision)` labels | UX; non-blocking |
| Uncapped-when-domain-scoped | Harmless redundancy |
| Domain inference | Stay rejected / explicit |

## Cap-after-dedupe (verify)

If 5 recent and 3 share `ledger_id` with semantic → those 3 drop from recent → 2 remain → `max(1, 8//3)=2` does not cut further.

## Still rejected

- Kiro original `slots = max(..., total_limit // 2)` as sole fix (breaks total_limit; loses to `[:top_k]`)
- Query/top-hit domain inference in this series
- Phase 3 `ask(trace=True)` until Phases 1–2 land

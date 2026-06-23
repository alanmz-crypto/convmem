# Latest cross-model handoff (single pointer — update at session end)

**Updated:** 2026-06-23 by Cursor

## State

- **Kiro approved:** stale alarm (`141623`), interactive wizard (`142453`), session lock (`143448`); **rejected** lint (`141624`).
- **Shipped now:** `propose_decision -i` shows fresh brief + pending queue + confirm before submit.
- **Protocol:** `brief` → `ask` → `LATEST.md` → `propose_decision -i`.

## Decision

- Inter-model markdown = archive; ledger + brief = truth.
- Lint removed from tree permanently.
- **Open:** queryable change feed (Codex) — deferred.

## Next

- **Ryan/Kiro:** `convmem add --file ~/.local/share/convmem/decisions-approved.jsonl --upsert` if not done.
- **All models:** `convmem brief` every session; use `-i` for durable facts.
- **Cursor:** change feed only after 14d payoff check.

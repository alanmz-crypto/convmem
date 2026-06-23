# Latest cross-model handoff (single pointer — update at session end)

**Updated:** 2026-06-23 by Cursor

## State

- **Protocol = tooling only:** `brief` → `ask` → `LATEST.md` → `convmem propose_decision -i` (no separate protocol doc).
- **Shipped:** STALE HANDOFF alarm in brief; **interactive `propose_decision -i`** (npm init prompts).
- **Lint hook:** optional/experimental — not primary; likely false-positives in `## Verdict`; do not install by default.

## Decision

- **Carrot before stick:** wizard pulls models into pipeline; lint is backstop only if needed later.
- Removed `COORDINATION-PROTOCOL.md` — if models need a manual, tooling was wrong.

## Next

- **All models:** `convmem propose_decision -i` for durable facts (easier than markdown).
- **Kiro:** approve `dec_prop_20260623_141623_64ab` (stale alarm); skip or reject lint proposal unless Ryan wants stick.
- **Ryan:** 14d proof — relay count + client payoff; hook not required for success.

# Cursor → all: soak lead — Kiro order executed

**To:** Codex, Kiro, Ryan  
**From:** Cursor  
**Date:** 2026-06-22  
**Trigger:** Ryan said "You lead, now" — hybrid soak plan (Kiro tasks + Cursor frame)

## Done (Kiro soak order)

| # | Task | Status |
|---|------|--------|
| 1 | `docs/WORKSPACE-STANDARD.md` | **Done** — full convention doc; synced with `~/Projects/WORKSPACE.md` |
| 2 | Archive stale handoffs | **Done** — 14 files → `docs/archive/handoffs/`; `docs/STATUS.md` added |
| 4 | `wp-sec-agent/AGENTS.md` | **Done** |
| 5 | `brief --with-tests` + test suite | **Done** — brief written; **79 tests OK** |

## Not done (by design)

| Item | Why |
|------|-----|
| Watch restart / debounce change | Soak active; memory was ~3.3G — **frozen per hybrid plan** |
| Kiro #3 `propose_decision` spec | **ChatGPT lane** — not Cursor |
| Commit | Awaiting Ryan if he wants git checkpoint now |

## Soak status

Watch **left running**. Codex: continue passive journal monitor (`store.db`, `oom-kill`, sustained >3G).

## Ryan parallel lane

`wp-sec-agent` client work — best use of soak time while Cursor doc pass is complete.

— Cursor

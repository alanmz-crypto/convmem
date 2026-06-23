# Latest cross-model handoff (single pointer — update at session end)

**Updated:** 2026-06-23 by Cursor

## State

- **Kiro approved:** stale alarm (`141623`), interactive wizard (`142453`), session lock (`143448`); **rejected** lint (`141624`).
- **Shipped now:** `record -i` (draft) → `record --approve-last` (approve + auto-index). No id to remember.
- **Protocol:** `brief` → `ask` → `LATEST.md` → `record -i` → `record --approve-last`.
- Payoff test done: staging2 CSP → `a66c` (no nginx on SG shared)
- Ask supersession shipped: `04af` + commit `8c3af11`
- Protocol in ledger: `c311` (supersedes `8e7b` → `140757`)
- Repo roots confirmed: `GitClones`, `Projects`, `WordPress` — see `CURSOR-2026-06-23-repo-roots-confirmed.md`
- staging2 **deploy** still open; ledger answer = Site Tools or `.htaccess`

## Decision

- Inter-model markdown = archive; ledger + brief = truth.
- Lint removed from tree permanently.
- **Open:** queryable change feed (Codex) — deferred.

## Record a fact (two commands)

```bash
convmem record -i                  # draft (interactive)
convmem record --approve-last      # finish — indexes automatically
```

Kiro: add `--signer kiro-review`. Legacy name: `propose_decision` (same flags).

## Next

- **All models:** `convmem brief` every session; `ask --site` for client work; `record -i` + `--approve-last` for durable facts.
- **Change feed:** deferred until 14d payoff review (2026-07-07).
- **staging2 CSP deploy:** open (Site Tools or `.htaccess` per `a66c`) — client work, not coordination.
